"""AUDITORIA / SENSIBILIDADE FASE 3. Nunca escreve no histórico da Fase 2."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src.executa_fase1 import _criar_views, _salvar_json
from src.audita_covariaveis import COLUNAS_PROPENSITY_PRINCIPAL
from src.audita_influencia import aipw_independente, concentracao, ess_grupos, perfil_extremos
from src.inferencia_cluster import resumo_cluster, bootstrap_cluster, leave_one_out, folds_agrupados
from src.estima_aipw import gerar_folds, calcular_aipw, diagnosticos_influencia
from src.modelagem_preditiva import validar_x, criar_modelo, ajustar_modelo, predizer, avaliar_probabilidades
from src.diagnostica_overlap import resumir_overlap
from src.simulacao_gate_influencia import simular

SEED = 20240925
ROOT = Path(__file__).resolve().parents[1]


def sha256(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for bloco in iter(lambda:f.read(1024*1024), b''):
            h.update(bloco)
    return h.hexdigest()


def salvar_fase3(p, objeto):
    p=Path(p)
    if not p.name.startswith('fase3_'):
        raise ValueError('Escrita permitida somente em artefatos fase3_.')
    _salvar_json(p,objeto)


def historico(raiz):
    paths=set()
    for pasta in ('outputs/diagnostics','outputs/tables','docs/methodology','notebooks','src','data/raw','data/processed'):
        for p in (raiz/pasta).glob('*'):
            if p.is_file() and ('fase2' in p.name.lower() or 'FASE2' in p.name or
                p.name in ('03_ml_preditivo_e_aipw.ipynb','sinasc_2024.parquet','SINASC_2024_csv.zip',
                           'estima_aipw.py','modelagem_preditiva.py','diagnostica_overlap.py')):
                paths.add(p)
    return {str(p.relative_to(raiz)).replace('\\','/'):sha256(p) for p in sorted(paths)}


def carregar_amostra(parquet, cenario='P1'):
    """Reutiliza a projeção SQL congelada; altera somente filtros de sensibilidade."""
    filtros={
        'P1':'tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num = 1',
        'CONSPRENAT':'tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num = 1 AND (try_cast(CONSPRENAT AS INTEGER) IS DISTINCT FROM 0)',
        'P0':'tratamento IS NOT NULL AND y_p0 IS NOT NULL AND gravidez_num = 1',
        'MULTIPLAS':'tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num IN (1,2,3)',
    }
    if cenario not in filtros:
        raise ValueError('Cenário desconhecido.')
    with duckdb.connect() as c:
        _criar_views(c,Path(parquet))
        sql=c.execute("SELECT sql FROM duckdb_views() WHERE view_name='amostra_principal'").fetchone()[0]
        inicio=sql.index(' AS SELECT ')+4
        fim=sql.index(' FROM fase1_base')
        projecao=sql[inicio:fim]
        if cenario=='P0':
            projecao=projecao.replace('y_p1 AS Y_BAIXO_PESO','y_p0 AS Y_BAIXO_PESO')
        consulta=(projecao+', CODMUNRES, try_cast(CONSPRENAT AS INTEGER) AS CONSPRENAT_NUM, '
                  'gravidez_num, peso_num FROM fase1_base WHERE '+filtros[cenario]+' ORDER BY contador')
        dados=c.execute(consulta).df()
        datas=c.execute("SELECT count(*) FILTER (WHERE try_strptime(DTNASC,'%d%m%Y') IS NULL OR year(try_strptime(DTNASC,'%d%m%Y'))<>2024) FROM sinasc").fetchone()[0]
    if datas or dados.empty or dados.contador.isna().any() or dados.contador.duplicated().any():
        raise ValueError('Datas/chave/população inválidas.')
    if dados.CODMUNRES.isna().any() or not dados.CODMUNRES.astype(str).str.fullmatch(r'\d{6}').all():
        raise ValueError('Município ausente ou malformado: não agrupar missing silenciosamente.')
    return dados, dict(cenario=cenario,n=len(dados),n_t1=int(dados.tratamento.sum()),
        n_t0=int((dados.tratamento==0).sum()),prevalencia=float(dados.Y_BAIXO_PESO.mean()),
        n_clusters=int(dados.CODMUNRES.nunique()),n_consprenat_zero=int((dados.CONSPRENAT_NUM==0).sum()),
        codigos_municipio_nao_especificado={str(k):int(v) for k,v in dados.loc[dados.CODMUNRES.str.endswith('0000'),'CODMUNRES'].value_counts().items()},
        n_multipla=int((dados.gravidez_num!=1).sum()),n_peso_fora_p1=int((~dados.peso_num.between(500,6000)).sum()),
        datas_invalidas=int(datas),chave='contador única, não nula; ordem explícita',sql=consulta,
        sha256_ordem_contador=hashlib.sha256('\n'.join(dados.contador.astype(str)).encode()).hexdigest())


def crossfit_auditoria(x,t,y,grupos=None,c3=False):
    """Nuisances congelados; C3 acrescenta apenas propensity HGB."""
    validar_x(x)
    t,y=np.asarray(t),np.asarray(y)
    if len(x)!=len(t):
        raise ValueError('Tamanho X/T divergente.')
    folds=folds_agrupados(t,y,grupos) if grupos is not None else gerar_folds(t,y,3,SEED)
    nomes=['e','m0_C1','m1_C1','m0_C2','m1_C2']+(['e_C3'] if c3 else [])
    pred={k:np.full(len(t),np.nan) for k in nomes}
    pred['fold_id']=np.zeros(len(t),int); cobertura=np.zeros(len(t),int); logs=[]
    for f,(tr,va) in enumerate(folds,1):
        log=dict(fold=f,n_treino=len(tr),n_validacao=len(va),intersecao_registros=0,
                 validacao_ty={str(s):int(np.sum((2*t[va]+y[va])==s)) for s in range(4)},ajustes={})
        if grupos is not None:
            log.update(n_clusters_treino=len(np.unique(grupos[tr])),n_clusters_validacao=len(np.unique(grupos[va])),
                       intersecao_clusters=len(set(grupos[tr]) & set(grupos[va])))
        ajustes=[('e','logistica',tr,t[tr])]
        if c3:
            ajustes.append(('e_C3','hgb',tr,t[tr]))
        ajustes += [(f'm{g}_{s}',tipo,tr[t[tr]==g],y[tr[t[tr]==g]])
                    for s,tipo in [('C1','logistica'),('C2','hgb')] for g in (0,1)]
        for nome,tipo,ix,target in ajustes:
            print(f'Fase3 fold {f}/3 {nome}: treino={len(ix)}',flush=True)
            modelo,info=ajustar_modelo(criar_modelo(tipo),x.iloc[ix],target)
            pred[nome][va]=predizer(modelo,x.iloc[va]); log['ajustes'][nome]=info
        pred['fold_id'][va]=f; cobertura[va]+=1; logs.append(log)
    if not np.all(cobertura==1) or any(not np.isfinite(pred[k]).all() for k in nomes):
        raise ValueError('OOF incompleto.')
    pred['cobertura']=cobertura
    return pred,logs


def carregar_ou_ajustar(raiz,nome,dados,grupos=None,c3=False):
    """Cache local com hashes de dados, chaves, X e código; nunca usa cache sem contrato."""
    p=raiz/'outputs/tables'/f'fase3_{nome}_oof.npz'
    logp=raiz/'outputs/diagnostics'/f'fase3_{nome}_ajustes.json'
    contrato=dict(n=len(dados),chaves=hashlib.sha256('\n'.join(dados.contador.astype(str)).encode()).hexdigest(),
        dados=sha256(raiz/'data/processed/sinasc_2024.parquet'),agrupado=grupos is not None,c3=c3,
        x=list(COLUNAS_PROPENSITY_PRINCIPAL),seed=SEED,
        codigo={f:sha256(raiz/'src'/f) for f in ('executa_robustez_fase3.py','modelagem_preditiva.py','inferencia_cluster.py')})
    if p.exists() and logp.exists():
        salvo=json.loads(logp.read_text(encoding='utf-8'))
        if salvo['contrato']!=contrato or salvo['cache_sha256']!=sha256(p):
            raise ValueError('Cache Fase3 não corresponde ao contrato; preservar e investigar.')
        with np.load(p) as a:
            pred={k:a[k] for k in a.files}
        print(f'Cache validado: {nome}',flush=True)
        return pred,salvo['folds']
    x=dados.loc[:,list(COLUNAS_PROPENSITY_PRINCIPAL)]
    pred,logs=crossfit_auditoria(x,dados.tratamento.to_numpy(),dados.Y_BAIXO_PESO.to_numpy(),grupos,c3)
    np.savez_compressed(p,**pred)
    salvar_fase3(logp,dict(contrato=contrato,folds=logs,cache_sha256=sha256(p)))
    return pred,logs


def resumo_predicoes(dados,pred,specs=('C1','C2'),bootstrap=False):
    t=dados.tratamento.to_numpy(); y=dados.Y_BAIXO_PESO.to_numpy(); g=dados.CODMUNRES.to_numpy()
    linhas=[]; metricas={}
    for s in specs:
        e=pred['e_C3' if s=='C3' else 'e']; outcome='C2' if s=='C3' else s
        m0=pred['m0_'+outcome]; m1=pred['m1_'+outcome]
        metricas[s]=dict(propensity=avaliar_probabilidades(t,e),overlap=resumir_overlap(e,t),
            outcomes={str(v):avaliar_probabilidades(y[t==v],(m1 if v else m0)[t==v]) for v in (0,1)})
        for regra,lo,hi in [('sem_trimming',0,1),('0.05_0.95',.05,.95)]:
            mask=(e>=lo)&(e<=hi)
            r,psi=aipw_independente(y[mask],t[mask],e[mask],m0[mask],m1[mask])
            clu=resumo_cluster(psi,g[mask]); d=diagnosticos_influencia(psi,t[mask],e[mask])
            linha=dict(especificacao=s,populacao=regra,n_excluido=int((~mask).sum()),
                **(r | clu),ess=ess_grupos(t[mask],e[mask]),top1_if2=d['frac_variancia_top1pct'],
                n_t1=int(t[mask].sum()),n_t0=int((t[mask]==0).sum()))
            if bootstrap:
                linha['bootstrap']=bootstrap_cluster(psi,g[mask])
            linhas.append(linha)
    return dict(resultados=linhas,nuisance=metricas)


def auditar_original(raiz,dados,pred):
    hist=json.loads((raiz/'outputs/diagnostics/fase2_aipw.json').read_text(encoding='utf-8'))
    if sha256(raiz/'data/processed/sinasc_2024.parquet')!=hist['provenance']['parquet_sha256']:
        raise ValueError('Hash da base histórica divergente.')
    if len(dados)!=2251570 or dados.tratamento.sum()!=1942045:
        raise ValueError('População histórica divergente.')
    t=dados.tratamento.to_numpy(); y=dados.Y_BAIXO_PESO.to_numpy(); e=pred['e']
    reconc=[]; influencia={}; loo=[]
    for s in ('C1','C2'):
        m0,m1=pred['m0_'+s],pred['m1_'+s]
        for regra,lo,hi in [('sem_trimming',0,1),('0.01_0.99',.01,.99),('0.05_0.95',.05,.95)]:
            mask=(e>=lo)&(e<=hi)
            r,psi=aipw_independente(y[mask],t[mask],e[mask],m0[mask],m1[mask])
            antigo,psi_antigo=calcular_aipw(y[mask],t[mask],e[mask],m0[mask],m1[mask])
            salvo=next(a for a in hist['resultados'] if a['especificacao']==s and a['populacao']==regra)
            np.testing.assert_allclose(psi,psi_antigo,rtol=0,atol=1e-12)
            for k in ('estimativa','se'):
                np.testing.assert_allclose(r[k],salvo[k],rtol=0,atol=1e-12)
            if len(psi)!=salvo['n']:
                raise ValueError('N não reconciliado.')
            diag=diagnosticos_influencia(psi,t[mask],e[mask]); indep=concentracao(psi,t[mask],y[mask],e[mask])
            top=next(f['fracao_if2'] for f in indep['faixas'] if f['top_pct']==1)
            np.testing.assert_allclose(top,diag['frac_variancia_top1pct'],rtol=0,atol=1e-12)
            for g,w in ess_grupos(t[mask],e[mask]).items():
                np.testing.assert_allclose(w['ess'],diag['pesos_por_grupo'][g]['ess'],rtol=1e-12)
            reconc.append(dict(especificacao=s,populacao=regra,n=r['n'],delta_estimativa=r['estimativa']-salvo['estimativa'],
                               delta_se=r['se']-salvo['se'],max_delta_psi=float(np.max(np.abs(psi-psi_antigo))),
                               delta_top1=top-diag['frac_variancia_top1pct']))
            if regra=='sem_trimming':
                influencia[s]=dict(**indep,perfis=perfil_extremos(dados,psi,e))
                loo.extend(dict(especificacao=s,**row) for row in leave_one_out(psi,dados.UF_RESIDENCIA.to_numpy()))
    return dict(rotulo='AUDITORIA FASE 3; histórico preservado',tolerancia_absoluta=1e-12,
                reconciliacao=reconc,especificacoes=influencia,leave_one_uf_out=loo)


def validar_fase2_sem_escrita(raiz):
    """Executa o validador herdado interceptando só a persistência histórica."""
    import src.valida_resultados_fase2 as validador
    original=validador._salvar_json
    captura={}
    def conferir(p,objeto):
        salvo=json.loads(p.read_text(encoding='utf-8'))
        if objeto!=salvo:
            raise ValueError('Validação histórica não reproduziu o JSON salvo.')
        captura.update(objeto)
    try:
        validador._salvar_json=conferir
        validador.validar(raiz)
    finally:
        validador._salvar_json=original
    return captura


def executar(raiz=ROOT,etapa='tudo'):
    inicio=time.time(); pasta=raiz/'outputs/diagnostics'
    antes=historico(raiz)
    manifesto=pasta/'fase3_preservacao.json'
    if manifesto.exists():
        from src.valida_apresentacao import verificar_preservacao
        verificar_preservacao(raiz,antes,json.loads(manifesto.read_text(encoding='utf-8'))['historico_sha256'])
    else:
        salvar_fase3(manifesto,dict(head_inicial='e9dfc2a05b58b91d48ec253739768048c892bfd0',historico_sha256=antes))
    dados,auditoria=carregar_amostra(raiz/'data/processed/sinasc_2024.parquet')
    with np.load(raiz/'outputs/tables/fase2_predicoes_oof.npz') as a:
        pred={k:a[k] for k in a.files}
    if etapa in ('tudo','diagnosticos'):
        inf=auditar_original(raiz,dados,pred)
        salvar_fase3(pasta/'fase3_influencia.json',inf)
        cluster=resumo_predicoes(dados,pred,bootstrap=True)
        cluster['amostra']=auditoria
        valido=~dados.CODMUNRES.str.endswith('0000').to_numpy()
        cluster['sensibilidade_sem_municipio_nao_especificado']=resumo_predicoes(
            dados.loc[valido].reset_index(drop=True),{k:v[valido] for k,v in pred.items()})
        salvar_fase3(pasta/'fase3_cluster.json',cluster)
        salvar_fase3(pasta/'fase3_monte_carlo.json',simular())
    if etapa in ('tudo','modelos'):
        agrupado,folds=carregar_ou_ajustar(raiz,'geografico',dados,dados.CODMUNRES.to_numpy())
        comparacao=dict(aleatorio=resumo_predicoes(dados,pred),agrupado=resumo_predicoes(dados,agrupado),folds=folds)
        salvar_fase3(pasta/'fase3_crossfit_geografico.json',comparacao)
        # C3 usa exatamente folds e outcomes C2 históricos; só e recebe novo HGB OOF.
        x=dados.loc[:,list(COLUNAS_PROPENSITY_PRINCIPAL)]; t=dados.tratamento.to_numpy(); y=dados.Y_BAIXO_PESO.to_numpy()
        e3=np.full(len(t),np.nan); logs=[]
        for f,(tr,va) in enumerate(gerar_folds(t,y),1):
            np.testing.assert_array_equal(np.where(pred['fold_id']==f)[0],va)
            print(f'C3 propensity HGB fold {f}/3',flush=True)
            modelo,log=ajustar_modelo(criar_modelo('hgb'),x.iloc[tr],t[tr])
            e3[va]=predizer(modelo,x.iloc[va]); logs.append(log)
        pred['e_C3']=e3
        np.savez_compressed(raiz/'outputs/tables/fase3_c3_propensity_oof.npz',e_C3=e3,contador=dados.contador.to_numpy(dtype=str))
        sensibilidades=dict(S0=resumo_predicoes(dados,pred,specs=('C1','C2','C3')),c3_ajustes=logs,amostras={'P1':auditoria})
        for nome in ('CONSPRENAT','P0','MULTIPLAS'):
            amostra,info=carregar_amostra(raiz/'data/processed/sinasc_2024.parquet',nome)
            # Reajuste em cada elegibilidade para respeitar o novo alvo condicional.
            p,logs=carregar_ou_ajustar(raiz,nome.lower(),amostra)
            resultado=resumo_predicoes(amostra,p)
            resultado['folds']=logs
            for row in resultado['resultados']:
                base=next(a for a in sensibilidades['S0']['resultados'] if a['especificacao']==row['especificacao'] and a['populacao']==row['populacao'])
                row['diferenca_p1_pp']=row['estimativa_pp']-base['estimativa_pp']
                row['diferenca_relativa_abs_p1']=row['diferenca_p1_pp']/abs(base['estimativa_pp'])
            sensibilidades[nome]=resultado; sensibilidades['amostras'][nome]=info
            salvar_fase3(pasta/'fase3_sensibilidades.json',sensibilidades)
    if antes!=historico(raiz):
        raise ValueError('Histórico alterado durante execução.')
    validar_fase2_sem_escrita(raiz)
    print(f'Fase3 {etapa}: concluída em {time.time()-inicio:.1f}s; histórico intacto',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--etapa',choices=['tudo','diagnosticos','modelos'],default='tudo')
    executar(etapa=parser.parse_args().etapa)
