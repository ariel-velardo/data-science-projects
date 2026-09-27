"""Resumos descritivos e avaliação externa de heterogeneidade; nenhum reajuste."""
import json
from itertools import combinations
import duckdb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr,t as student_t
from src.executa_fase4 import ROOT,salvar,patrimonio
from src.executa_robustez_fase3 import carregar_amostra,sha256
from src.heterogeneidade_dr import quintis,resumo_distribuicao,resumir_grupos
from src.inferencia_cluster import resumo_cluster


def contraste_extremos(psi,cate,grupos):
    """Quintis dentro da avaliação; variância municipal de diferença de médias."""
    psi,cate,grupos=np.asarray(psi),np.asarray(cate),np.asarray(grupos)
    q=quintis(cate); baixo=q==1; alto=q==5
    n0,n1=int(baixo.sum()),int(alto.sum()); m0,m1=psi[baixo].mean(),psi[alto].mean()
    contribuicao=np.where(alto,(psi-m1)/n1,0)-np.where(baixo,(psi-m0)/n0,0)
    _,cod=np.unique(grupos,return_inverse=True); G=int(cod.max()+1)
    if G<2: raise ValueError('Contraste requer pelo menos dois municípios.')
    u=np.bincount(cod,weights=contribuicao); se=np.sqrt(G/(G-1)*np.dot(u,u))
    crit=student_t.ppf(.975,G-1); delta=float(m1-m0)
    return dict(n=len(psi),n_q1=n0,n_q5=n1,contraste_dr_q5_q1_pp=100*delta,se_municipal_pp=float(100*se),
        ic95_inferior_pp=float(100*(delta-crit*se)),ic95_superior_pp=float(100*(delta+crit*se)),
        contraste_cate_q5_q1_pp=float(100*(cate[alto].mean()-cate[baixo].mean())),
        metodo='Quintis definidos dentro da partição externa; IC municipal condicional aos modelos fixos.')


def classificar(estabilidade):
    contrastes=estabilidade['contrastes_externos']
    if all(r['ic95_inferior_pp']<=0<=r['ic95_superior_pp'] for r in contrastes):
        return 'HETEROGENEIDADE_NAO_EVIDENCIADA'
    if (estabilidade['spearman_hgb_ridge']<.5 or estabilidade['mediana_spearman_perfis']<.5
        or any(r['contraste_dr_q5_q1_pp']<0 for r in contrastes)):
        return 'HETEROGENEIDADE_SENSIVEL_A_MODELO'
    return 'HETEROGENEIDADE_EXPLORATORIA_ESTAVEL'


def resumo():
    ler=lambda nome:json.loads((ROOT/'outputs/diagnostics'/nome).read_text(encoding='utf-8'))
    assert patrimonio()==ler('fase4_preservacao.json')['sha256']
    log=ler('fase4_ajustes.json'); cache=ROOT/'outputs/tables/fase4_predicoes_oof.npz'
    assert log['cache_sha256']==sha256(cache)
    dados,auditoria=carregar_amostra(ROOT/'data/processed/sinasc_2024.parquet')
    with np.load(cache) as a: p={k:a[k] for k in a.files}
    np.testing.assert_array_equal(p['contador'],dados.contador.to_numpy(dtype=str))
    cate,alt,psi,fold=p['cate_hgb'],p['cate_ridge'],p['psi'],p['fold_id']
    grupos=dados.CODMUNRES.to_numpy(); idade=dados.IDADEMAE_NUM.to_numpy(dtype=float)
    faixas=np.select([np.isnan(idade),idade<20,idade<30,idade<35],['Ausente','<20','20–29','30–34'],default='≥35')
    dimensoes={'Faixa etária':faixas,'Escolaridade':dados.ESCOLARIDADE_MAE.to_numpy(),
               'Raça/cor':dados.RACA_COR_MAE.to_numpy(),'Paridade':dados.PARIDADE_CAT.to_numpy()}
    perfis=[]; perfis_particao=[]
    for dim,g in dimensoes.items():
        for r in resumir_grupos(cate,g):
            mask=g==r['grupo']; cl=resumo_cluster(psi[mask],grupos[mask])
            perfis.append(dict(dimensao=dim,**r,contraste_dr_pp=cl['estimativa_pp'],
                ic95_dr_inferior_pp=cl['ic95_cluster_inferior_pp'],ic95_dr_superior_pp=cl['ic95_cluster_superior_pp']))
        for f in (1,2,3):
            m=fold==f
            perfis_particao.extend(dict(dimensao=dim,particao=f,**r) for r in resumir_grupos(cate[m],g[m]))
    q=quintis(cate)
    base=dados.copy(); base['quintil']=q; base['cate']=cate; base['cate_ridge']=alt; base['psi']=psi
    with duckdb.connect() as con:
        con.register('base',base)
        qs=con.execute('''SELECT quintil,count(*) n,100*avg(cate) cate_medio_pp,
            100*avg(cate_ridge) ridge_medio_pp,avg(IDADEMAE_NUM) idade_media,
            100*avg(Y_BAIXO_PESO) prevalencia_observada_pct,100*avg(tratamento) proporcao_t1_pct,
            min(cate)*100 cate_min_pp,max(cate)*100 cate_max_pp
            FROM base GROUP BY quintil ORDER BY quintil''').df().to_dict('records')
        proporcoes=[]
        for col in log['contrato']['x'][1:]:
            rs=con.execute(f'''SELECT quintil,CAST({col} AS VARCHAR) categoria,count(*) n,
                100.0*count(*)/sum(count(*)) OVER (PARTITION BY quintil) percentual
                FROM base GROUP BY quintil,{col} ORDER BY quintil,{col}''').df().to_dict('records')
            proporcoes.extend(dict(variavel=col,**r) for r in rs)
    externo=[]; distribuicao_particao=[]
    for f in (1,2,3):
        m=fold==f
        externo.append(dict(particao=f,**contraste_extremos(psi[m],cate[m],grupos[m])))
        distribuicao_particao.append(dict(particao=f,**resumo_distribuicao(cate[m]),
            media_psi_pp=float(100*psi[m].mean()),media_ridge_pp=float(100*alt[m].mean())))
    perf=pd.DataFrame(perfis_particao)
    medias=perf.pivot(index=['dimensao','grupo'],columns='particao',values='media_pp')
    ns=perf.pivot(index=['dimensao','grupo'],columns='particao',values='n')
    correlacoes=[]
    for f1,f2 in combinations((1,2,3),2):
        mask=(ns[f1]>=1000)&(ns[f2]>=1000)&medias[[f1,f2]].notna().all(axis=1)
        rho=float(spearmanr(medias.loc[mask,f1],medias.loc[mask,f2]).statistic)
        correlacoes.append(dict(particao1=f1,particao2=f2,n_categorias=int(mask.sum()),spearman=rho))
    estabilidade=dict(spearman_hgb_ridge=float(spearmanr(cate,alt).statistic),
        diferenca_absoluta_media_pp=float(100*np.mean(np.abs(cate-alt))),
        concordancia_sinal=float(np.mean(np.sign(cate)==np.sign(alt))),
        correlacoes_perfis=correlacoes,mediana_spearman_perfis=float(np.median([r['spearman'] for r in correlacoes])),
        contrastes_externos=externo,distribuicao_particao=distribuicao_particao)
    if not all(np.isfinite(estabilidade[k]) for k in ('spearman_hgb_ridge','mediana_spearman_perfis')):
        raise ValueError('Estabilidade não quantificável; investigar antes de classificar.')
    hist,limites=np.histogram(100*cate,bins=70)
    gate=classificar(estabilidade)
    resultado=dict(populacao=auditoria,metodo='DR-Learner; três papéis municipais disjuntos e três rotações',
        principal=resumo_distribuicao(cate),alternativo=resumo_distribuicao(alt),perfis=perfis,
        perfis_por_particao=perfis_particao,quintis=qs,quintis_composicao_x=proporcoes,
        estabilidade=estabilidade,histograma=dict(contagens=hist.tolist(),limites_pp=limites.tolist()),
        media_psi_pp=float(100*psi.mean()),diferenca_media_cate_psi_pp=float(100*(cate.mean()-psi.mean())),
        gate=gate,causalidade_provada=False,politica_clinica_recomendada=False,
        limitacao_ic='ICs municipais de contrastes DR com funções fixas; não são ICs do CATE previsto nem incorporam toda a incerteza de aprendizagem.',
        n_predicoes_distintas=len(np.unique(cate)),sem_recorte_ou_winsorizacao=True)
    # Buscar C2/P1 explicitamente: nunca depender da ordem das linhas históricas.
    resultado['ate_fase2_c2_pp']=next(r['estimativa_pp'] for r in ler('fase2_aipw.json')['resultados']
                                    if r['especificacao']=='C2' and r['populacao']=='sem_trimming')
    salvar('fase4_resultados.json',resultado)
    salvar('fase4_gate.json',dict(gate=gate,regra='Protocolo anterior ao ajuste em HETEROGENEIDADE_FASE4.md',
        evidencia=estabilidade,causalidade_provada=False,uso='Exclusivamente exploratório/didático; sem priorização clínica.'))
    print(json.dumps(dict(principal=resultado['principal'],estabilidade=estabilidade,gate=gate),ensure_ascii=False,indent=2))
    return resultado


if __name__=='__main__': resumo()
