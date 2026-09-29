"""DR-Learner e avaliação externa."""
from __future__ import annotations

import hashlib
import duckdb
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits
from src.inferencia_causal import calcular_aipw
from src.modelagem_preditiva import validar_x
from src.modelagem_preditiva import criar_modelo
from src.modelagem_preditiva import ajustar_modelo
from src.modelagem_preditiva import predizer
from src.modelagem_preditiva import SEED
import json
from pathlib import Path
from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL
from src.amostra import carregar_amostra
from src.sinasc import calcular_sha256 as sha256
from itertools import combinations
from scipy.stats import spearmanr,t as student_t
from src.robustez import resumo_cluster

def pseudo_desfecho(y,t,e,m0,m1):
    return calcular_aipw(y,t,e,m0,m1)[1]

def particoes_municipais(grupos,seed=SEED):
    grupos=np.asarray(grupos)
    if pd.isna(grupos).any() or np.any(grupos==''): raise ValueError('Município ausente.')
    nomes,inverso=np.unique(grupos,return_inverse=True)
    if len(nomes)<3: raise ValueError('Requer três municípios ou mais.')
    sorteio=np.random.default_rng(seed).permutation(len(nomes))
    f=np.empty(len(nomes),int); f[sorteio]=np.arange(len(nomes))%3+1
    return f[inverso]

def rotacoes(fold,grupos):
    fold,grupos=np.asarray(fold),np.asarray(grupos)
    if fold.ndim!=1 or len(fold)!=len(grupos) or set(np.unique(fold))!={1,2,3}:
        raise ValueError('Partições inválidas.')
    for k in (1,2,3):
        a=np.flatnonzero(fold==k); b=np.flatnonzero(fold==k%3+1); c=np.flatnonzero(fold==(k+1)%3+1)
        conjuntos=[set(grupos[i]) for i in (a,b,c)]
        if any(conjuntos[i]&conjuntos[j] for i,j in ((0,1),(0,2),(1,2))):
            raise ValueError('Município compartilhado entre papéis.')
        yield a,b,c

def criar_regressor(tipo,min_folha=2000):
    if tipo=='hgb':
        modelo=clone(criar_modelo('hgb'))
        modelo.set_params(modelo=HistGradientBoostingRegressor(
            loss='squared_error',max_iter=100,max_leaf_nodes=7,min_samples_leaf=min_folha,
            learning_rate=.1,l2_regularization=1.,early_stopping=False,
            categorical_features=[False]+[True]*6,random_state=SEED))
        return modelo
    if tipo=='ridge':
        modelo=clone(criar_modelo('logistica'))
        modelo.set_params(modelo=Ridge(alpha=10.,solver='lsqr',tol=1e-6))
        return modelo
    raise ValueError('Regressor desconhecido.')

def ajustar_regressor(modelo,x,psi):
    validar_x(x)
    psi=np.asarray(psi,float)
    if psi.ndim!=1 or len(x)!=len(psi) or not np.isfinite(psi).all():
        raise ValueError('Pseudo-desfecho inválido.')
    with threadpool_limits(limits=4): modelo.fit(x,psi)
    return modelo

def prever_regressor(modelo,x):
    validar_x(x)
    with threadpool_limits(limits=4): p=modelo.predict(x)
    if not np.isfinite(p).all(): raise ValueError('CATE não finito.')
    return p

def ajuste_honesto(x,t,y,fold,grupos):
    validar_x(x); t,y=np.asarray(t),np.asarray(y)
    if not x.index.is_unique or len(x)!=len(t) or len(y)!=len(t):
        raise ValueError('Chaves ou dimensões inválidas.')
    if set(np.unique(t))!={0,1} or not set(np.unique(y))<={0,1}:
        raise ValueError('T/Y devem ser binários.')
    saida={k:np.full(len(t),np.nan) for k in ('e','m0','m1','psi','cate_hgb','cate_ridge')}
    saida['cobertura']=np.zeros(len(t),int); saida['fold_id']=np.asarray(fold).copy()
    logs=[]
    for rodada,(a,b,c) in enumerate(rotacoes(fold,grupos),1):
        info=dict(rodada=rodada,particao_auxiliares=int(fold[a[0]]),particao_cate=int(fold[b[0]]),
                  particao_avaliacao=int(fold[c[0]]),n_auxiliares=len(a),n_cate=len(b),n_avaliacao=len(c),
                  intersecoes_registros=0,intersecoes_municipios=0,ajustes={},
                  indices_sha256={nome:hashlib.sha256(i.tobytes()).hexdigest() for nome,i in zip(('A','B','C'),(a,b,c))},
                  uf_nova_no_cate=sorted(set(x.iloc[c].UF_RESIDENCIA)-set(x.iloc[b].UF_RESIDENCIA)),
                  uf_nova_nos_auxiliares=sorted(set(x.iloc[c].UF_RESIDENCIA)-set(x.iloc[a].UF_RESIDENCIA)))
        print(f'Rodada {rodada}: auxiliares={len(a)}, CATE={len(b)}, avaliação={len(c)}',flush=True)
        pb={}
        for nome,tipo in (('e','logistica'),('m0','hgb'),('m1','hgb')):
            treino=a if nome=='e' else a[t[a]==int(nome[1])]
            alvo=t if nome=='e' else y
            if set(np.unique(alvo[treino]))!={0,1}: raise ValueError('Falta de classe no treino auxiliar.')
            print(f'  Ajuste {nome}',flush=True)
            m,log=ajustar_modelo(criar_modelo(tipo),x.iloc[treino],alvo[treino])
            pb[nome]=predizer(m,x.iloc[b]); saida[nome][c]=predizer(m,x.iloc[c]); info['ajustes'][nome]=log
        psi_b=pseudo_desfecho(y[b],t[b],pb['e'],pb['m0'],pb['m1'])
        for tipo in ('hgb','ridge'):
            print(f'  Regressão DR {tipo}',flush=True)
            m=ajustar_regressor(criar_regressor(tipo),x.iloc[b],psi_b)
            saida['cate_'+tipo][c]=prever_regressor(m,x.iloc[c])
        saida['psi'][c]=pseudo_desfecho(y[c],t[c],saida['e'][c],saida['m0'][c],saida['m1'][c])
        saida['cobertura'][c]+=1; logs.append(info)
    if not np.all(saida['cobertura']==1) or any(not np.isfinite(v).all() for v in saida.values()):
        raise ValueError('Cobertura incompleta ou valores não finitos.')
    return saida,logs

def quintis(cate,seed=SEED):
    cate=np.asarray(cate,float)
    if cate.ndim!=1 or len(cate)<5 or not np.isfinite(cate).all(): raise ValueError('CATE inválido para quintis.')
    desempate=np.random.default_rng(seed).permutation(len(cate))
    ordem=np.lexsort((desempate,cate)); q=np.empty(len(cate),int)
    q[ordem]=np.arange(len(cate))*5//len(cate)+1
    return q

def resumo_distribuicao(cate):
    a=np.asarray(cate,float)
    if len(a)==0 or not np.isfinite(a).all(): raise ValueError('Distribuição inválida.')
    qs=np.quantile(a,[.05,.25,.5,.75,.95])
    return dict(n=len(a),media_pp=float(100*a.mean()),mediana_pp=float(100*qs[2]),
        p05_pp=float(100*qs[0]),p25_pp=float(100*qs[1]),p75_pp=float(100*qs[3]),p95_pp=float(100*qs[4]),
        amplitude_robusta_pp=float(100*(qs[4]-qs[0])),min_pp=float(100*a.min()),max_pp=float(100*a.max()),
        proporcao_negativa=float(np.mean(a<0)),proporcao_positiva=float(np.mean(a>0)),
        proporcao_zero=float(np.mean(a==0)),n_fora_limite_teorico=int(np.sum(np.abs(a)>1)))

def resumir_grupos(cate,grupos):
    tabela=pd.DataFrame(dict(grupo=grupos,cate=np.asarray(cate,float)))
    if len(tabela)==0 or tabela.isna().any().any(): raise ValueError('Grupos ou CATE ausentes.')
    with duckdb.connect() as con:
        con.register('tabela',tabela)
        r=con.execute('''SELECT CAST(grupo AS VARCHAR) grupo, count(*) n, 100*avg(cate) media_pp,
            100*quantile_cont(cate,.05) p05_pp,100*quantile_cont(cate,.25) p25_pp,
            100*median(cate) mediana_pp,100*quantile_cont(cate,.75) p75_pp,
            100*quantile_cont(cate,.95) p95_pp FROM tabela GROUP BY grupo ORDER BY grupo''').df()
    return r.to_dict('records')


ROOT=Path(__file__).resolve().parents[1]

def salvar_heterogeneidade(nome,objeto):
    if not nome.startswith('fase4_'): raise ValueError('Saída fora da Fase 4.')
    (ROOT/'outputs/diagnostics'/nome).write_text(json.dumps(objeto,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def executar_heterogeneidade():
    from src.validacao import historico
    from src.validacao import patrimonio
    from src.validacao import verificar_preservacao
    ler=lambda p:json.loads(p.read_text(encoding='utf-8'))
    gate=ler(ROOT/'outputs/diagnostics/fase3_gate.json')
    if not gate['permite_exercicio_didatico_fase4'] or gate['gate']=='NOVO_PROBLEMA_METODOLOGICO_IDENTIFICADO':
        raise ValueError('Fase 3 não autoriza o exercício de heterogeneidade.')
    verificar_preservacao(ROOT,historico(ROOT),ler(ROOT/'outputs/diagnostics/fase3_preservacao.json')['historico_sha256'])
    antes=patrimonio(); preservacao=ROOT/'outputs/diagnostics/fase4_preservacao.json'
    if preservacao.exists(): verificar_preservacao(ROOT, antes, ler(preservacao)['sha256'])
    else: salvar_heterogeneidade('fase4_preservacao.json',dict(checkpoint='1d27ab4e40b5f49ecd53ef0b73134f9e66c28325',sha256=antes))
    dados,auditoria=carregar_amostra(ROOT/'data/processed/sinasc_2024.parquet')
    x=dados.loc[:,list(COLUNAS_PROPENSITY_PRINCIPAL)]
    t=dados.tratamento.to_numpy(); y=dados.Y_BAIXO_PESO.to_numpy(); grupos=dados.CODMUNRES.to_numpy()
    assert len(dados)==2251570 and t.sum()==1942045 and (t==0).sum()==309525
    f=particoes_municipais(grupos)
    particoes=[]
    for k in (1,2,3):
        m=f==k
        assert set(np.unique(t[m]))=={0,1} and set(np.unique(y[m]))=={0,1}
        particoes.append(dict(particao=k,n=int(m.sum()),n_t1=int(t[m].sum()),n_t0=int((t[m]==0).sum()),
            n_y1=int(y[m].sum()),n_municipios=len(np.unique(grupos[m]))))
    list(rotacoes(f,grupos))
    contrato=dict(dados_sha256=sha256(ROOT/'data/processed/sinasc_2024.parquet'),
        chaves_sha256=auditoria['sha256_ordem_contador'],x=list(x.columns),n=len(dados),semente=20240925,
        particoes=particoes,codigo={p:sha256(ROOT/'src'/p) for p in ('heterogeneidade.py',
        'modelagem_preditiva.py','inferencia_causal.py','diagnosticos.py','amostra.py')})
    salvar_heterogeneidade('fase4_preflight.json',dict(status='APROVADO',amostra=auditoria,contrato=contrato,
        sem_novas_features=True,municipio_somente_separacao=True,particoes_independentes_de_t_y=True))
    cache=ROOT/'outputs/tables/fase4_predicoes_oof.npz'; logp=ROOT/'outputs/diagnostics/fase4_ajustes.json'
    if cache.exists():
        log=ler(logp)
        from src.validacao import conferir_contrato
        conferir_contrato(ROOT, log['contrato'], contrato)
        if log['cache_sha256']!=sha256(cache):
            raise ValueError('Cache incompatível; preservar e investigar.')
        print('Predições da Fase 4 já existem e correspondem ao contrato.',flush=True)
    else:
        pred,logs=ajuste_honesto(x,t,y,f,grupos)
        pred['contador']=dados.contador.to_numpy(dtype=str)
        np.savez_compressed(cache,**pred)
        salvar_heterogeneidade('fase4_ajustes.json',dict(contrato=contrato,rotacoes=logs,cache_sha256=sha256(cache)))
    assert patrimonio()==antes,'Um artefato histórico foi alterado.'
    print('Fase 4: ajuste integral concluído; histórico preservado.',flush=True)


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

def resumir_heterogeneidade():
    from src.validacao import patrimonio
    from src.validacao import verificar_preservacao
    ler=lambda nome:json.loads((ROOT/'outputs/diagnostics'/nome).read_text(encoding='utf-8'))
    verificar_preservacao(ROOT, patrimonio(), ler('fase4_preservacao.json')['sha256'])
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
    salvar_heterogeneidade('fase4_resultados.json',resultado)
    salvar_heterogeneidade('fase4_gate.json',dict(gate=gate,regra='Protocolo anterior ao ajuste em HETEROGENEIDADE_FASE4.md',
        evidencia=estabilidade,causalidade_provada=False,uso='Exclusivamente exploratório/didático; sem priorização clínica.'))
    print(json.dumps(dict(principal=resultado['principal'],estabilidade=estabilidade,gate=gate),ensure_ascii=False,indent=2))
    return resultado
