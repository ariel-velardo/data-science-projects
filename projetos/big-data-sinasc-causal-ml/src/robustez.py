"""Influência, inferência municipal e sensibilidades."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from sklearn.model_selection import StratifiedGroupKFold
import argparse
import hashlib
import json
import time
from pathlib import Path
import duckdb
from sklearn.metrics import roc_auc_score
from src.amostra import _criar_views
from src.sinasc import _salvar_json
from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL
from src.inferencia_causal import gerar_folds
from src.inferencia_causal import calcular_aipw
from src.inferencia_causal import diagnosticos_influencia
from src.modelagem_preditiva import validar_x
from src.modelagem_preditiva import criar_modelo
from src.modelagem_preditiva import ajustar_modelo
from src.modelagem_preditiva import predizer
from src.modelagem_preditiva import avaliar_probabilidades
from src.diagnosticos import resumir_overlap
from src.sinasc import calcular_sha256 as sha256
from src.amostra import carregar_amostra

TOP_PCT = (.01, .05, .1, .5, 1., 2., 5., 10.)

def aipw_independente(y, t, e, m0, m1):
    """Calcula correções separadas por grupo, sem chamar calcular_aipw."""
    a = [np.asarray(v, dtype=float) for v in (y, t, e, m0, m1)]
    if any(v.ndim != 1 for v in a) or len({v.size for v in a}) != 1:
        raise ValueError('Vetores incompatíveis.')
    y, t, e, m0, m1 = a
    if len(y) < 2 or not all(np.isfinite(v).all() for v in a):
        raise ValueError('Dados insuficientes ou não finitos.')
    if set(np.unique(t)) != {0, 1} or not set(np.unique(y)) <= {0, 1}:
        raise ValueError('T/Y inválidos.')
    if np.any((e <= 0) | (e >= 1)) or any(np.any((m < 0) | (m > 1)) for m in (m0, m1)):
        raise ValueError('Probabilidades inválidas.')
    tratado = t == 1
    psi = (m1 - m0).copy()
    psi[tratado] += (y[tratado] - m1[tratado]) / e[tratado]
    psi[~tratado] -= (y[~tratado] - m0[~tratado]) / (1 - e[~tratado])
    theta = float(np.mean(psi))
    se = float(np.sqrt(np.sum(np.square(psi-theta)) / (len(psi)*(len(psi)-1))))
    return dict(n=len(y), estimativa=theta, se=se, estimativa_pp=100*theta, se_pp=100*se,
                ic95_inferior_pp=100*(theta-1.96*se), ic95_superior_pp=100*(theta+1.96*se)), psi

def ess_grupos(t, e):
    t, e = np.asarray(t), np.asarray(e)
    resultado = {}
    for g in (0, 1):
        w = 1/(e[t == g] if g else 1-e[t == g])
        if not len(w) or not np.isfinite(w).all() or np.any(w <= 0):
            raise ValueError('Pesos inválidos.')
        resultado[str(g)] = dict(n=len(w), ess=float(w.sum()**2/np.dot(w,w)),
                                 max=float(w.max()), media=float(w.mean()))
    return resultado

def quantis(v):
    return {str(q): float(np.quantile(v,q)) for q in (0,.01,.05,.25,.5,.75,.95,.99,1)}

def concentracao(psi, t=None, y=None, e=None):
    """Top cumulativo em ordem DECRESCENTE de |IF|; ceil determina N."""
    psi = np.asarray(psi, float)
    if psi.ndim != 1 or len(psi) < 2 or not np.isfinite(psi).all():
        raise ValueError('Pseudo-outcomes inválidos.')
    inf = psi-psi.mean()
    ordem = np.argsort(-np.abs(inf), kind='stable')
    q = inf**2
    totalq, totala = q.sum(), np.abs(inf).sum()
    faixas = []
    for pct in TOP_PCT:
        k = max(1,int(np.ceil(len(psi)*pct/100)))
        ix = ordem[:k]
        linha = dict(top_pct=pct, n=k, fracao_observacoes=k/len(psi),
                     fracao_if2=float(q[ix].sum()/totalq) if totalq else 0.,
                     fracao_abs_if=float(np.abs(inf[ix]).sum()/totala) if totala else 0.,
                     contribuicao_psi_pp=float(100*psi[ix].sum()/len(psi)),
                     contribuicao_if_pp=float(100*inf[ix].sum()/len(psi)))
        if t is not None:
            linha.update(prop_t1=float(np.mean(np.asarray(t)[ix])), prop_t0=float(1-np.mean(np.asarray(t)[ix])))
        if y is not None:
            linha.update(prop_y1=float(np.mean(np.asarray(y)[ix])), prop_y0=float(1-np.mean(np.asarray(y)[ix])))
        if e is not None:
            linha['propensity'] = quantis(np.asarray(e)[ix])
        faixas.append(linha)
    pontos = np.unique(np.r_[0, np.ceil(np.geomspace(1,len(psi),300)),
                             [d['n'] for d in faixas],len(psi)]).astype(int)
    acumulada = np.r_[0.,np.cumsum(q[ordem])]
    curva = dict(fracao_observacoes=(pontos/len(psi)).tolist(),
                 fracao_if2=(acumulada[pontos]/totalq if totalq else np.zeros(len(pontos))).tolist())
    return dict(faixas=faixas, curva=curva, variancia_nula=bool(totalq==0),
                max_fracao_if2=float(q.max()/totalq) if totalq else 0.,
                max_contribuicao_individual_pp=float(100*np.abs(inf).max()/len(psi)),
                soma_if=float(inf.sum()), soma_if2=float(totalq))

def perfil_extremos(dados, psi, e):
    ordem = np.argsort(-np.abs(psi-np.mean(psi)),kind='stable')
    categorias = ['tratamento','Y_BAIXO_PESO','ESCOLARIDADE_MAE','RACA_COR_MAE',
                  'SITUACAO_CONJUGAL','PARIDADE_CAT','PERDAS_FETAIS_CAT','UF_RESIDENCIA']
    perfis = {}
    for pct in (100., .1, 1., 5.):
        ix = ordem[:max(1,int(np.ceil(len(psi)*pct/100)))]
        sub = dados.iloc[ix]
        idade = sub.IDADEMAE_NUM.dropna().to_numpy()
        perfis[str(pct)] = dict(n=len(ix), propensity=quantis(e[ix]),
            idade=quantis(idade), idade_missing=int(sub.IDADEMAE_NUM.isna().sum()),
            categorias={col: {str(k):dict(n=int(v),proporcao=float(v/len(ix)))
                        for k,v in sub[col].value_counts(dropna=False).items()} for col in categorias},
            cruzamento_ty=[dict(t=int(t),y=int(y),n=int(n),proporcao=float(n/len(ix)))
                          for (t,y),n in sub.groupby(['tratamento','Y_BAIXO_PESO']).size().items()])
    return perfis


SEED = 20240925

def agregar(psi, grupos):
    psi, grupos = np.asarray(psi,float), np.asarray(grupos)
    if psi.ndim != 1 or len(psi) != len(grupos) or len(psi)<2 or not np.isfinite(psi).all():
        raise ValueError('Vetores inválidos.')
    if pd.isna(grupos).any() or np.any(grupos == ''):
        raise ValueError('Cluster ausente.')
    nomes, codigos = np.unique(grupos,return_inverse=True)
    if len(nomes)<2:
        raise ValueError('Pelo menos dois clusters são necessários.')
    n = np.bincount(codigos)
    somas = np.bincount(codigos,weights=psi)
    return nomes, n, somas

def resumo_cluster(psi, grupos):
    psi = np.asarray(psi,float)
    nomes, n, somas = agregar(psi,grupos)
    theta = float(psi.mean()); N=len(psi); G=len(nomes)
    # A média é por nascido vivo: U_g = soma(psi_i) - n_g * theta.
    u = somas-n*theta
    se = float(np.sqrt(G/(G-1)*np.dot(u,u)/N**2))
    iid = float(psi.std(ddof=1)/np.sqrt(N))
    critico = float(student_t.ppf(.975,G-1))
    v = u*u
    return dict(n=N,n_clusters=G,estimativa=theta,estimativa_pp=100*theta,
        se_iid=iid,se_iid_pp=100*iid,se_cluster=se,se_cluster_pp=100*se,
        razao_se=se/iid if iid else None,correcao=G/(G-1),critico_t=critico,
        ic95_cluster_inferior_pp=100*(theta-critico*se),
        ic95_cluster_superior_pp=100*(theta+critico*se),
        ic95_iid_inferior_pp=100*(theta-1.96*iid),ic95_iid_superior_pp=100*(theta+1.96*iid),
        max_fracao_variancia_cluster=float(v.max()/v.sum()) if v.sum() else 0.,
        cluster_maior_if2=str(nomes[np.argmax(v)]),
        tamanhos={str(q):float(np.quantile(n,q)) for q in (0,.01,.05,.5,.95,.99,1)},
        clusters_n_menor_10=int(np.sum(n<10)),clusters_n_maior_10000=int(np.sum(n>10000)),
        max_fracao_n=float(n.max()/N))

def bootstrap_cluster(psi, grupos, replicas=500, seed=SEED):
    nomes, n, somas = agregar(psi,grupos)
    if replicas<2:
        raise ValueError('Requer ao menos duas réplicas.')
    rng=np.random.default_rng(seed); valores=[]; ns=[]; G=len(nomes)
    for _ in range(replicas):
        sorteio=rng.integers(0,G,size=G)
        denom=int(n[sorteio].sum()); ns.append(denom)
        valores.append(float(somas[sorteio].sum()/denom))
    return dict(seed=seed,n_replicas=replicas,se_bootstrap_pp=float(100*np.std(valores,ddof=1)),
        ic95_percentil_pp=(100*np.quantile(valores,[.025,.975])).tolist(),
        replicas=valores,n_bootstrap_min=min(ns),n_bootstrap_max=max(ns),
        metodo='pairs cluster; G sorteios uniformes com reposição; denominador N* variável',
        limitacao='Nuisances fixos; não incorpora sua incerteza completa nem confundimento/seleção.')

def leave_one_out(psi, grupos):
    nomes,n,somas=agregar(psi,grupos)
    N=len(psi); total=float(np.sum(psi)); theta=total/N
    return [dict(grupo=str(g),n_removido=int(k),estimativa_pp=100*(total-s)/(N-k),
                 mudanca_pp=100*((total-s)/(N-k)-theta)) for g,k,s in zip(nomes,n,somas)]

def folds_agrupados(t,y,grupos,n_folds=3,seed=SEED):
    t,y,grupos=map(np.asarray,(t,y,grupos))
    if len(t)!=len(y) or len(t)!=len(grupos) or pd.isna(grupos).any():
        raise ValueError('Grupos/T/Y incompatíveis.')
    if set(np.unique(t))!={0,1} or not set(np.unique(y))<={0,1}:
        raise ValueError('T/Y inválidos.')
    if len(np.unique(grupos))<n_folds:
        raise ValueError('Clusters insuficientes.')
    estratos=2*t+y
    folds=list(StratifiedGroupKFold(n_splits=n_folds,shuffle=True,random_state=seed).split(
        np.zeros(len(t)),estratos,grupos))
    cobertura=np.zeros(len(t),int)
    for tr,va in folds:
        if set(grupos[tr]) & set(grupos[va]):
            raise ValueError('Município presente em treino e validação.')
        for ix in (tr,va):
            if set(np.unique(estratos[ix])) != {0,1,2,3}:
                raise ValueError('Fold sem as quatro combinações T/Y.')
        cobertura[va]+=1
    if not np.all(cobertura==1):
        raise ValueError('Cobertura OOF inválida.')
    return folds


def simular(n=50000, replicas=200, seed=20240925):
    """DGPs fixados antes de executar; efeito de risco constante -0,01."""
    if n<100 or replicas<2:
        raise ValueError('Experimento insuficiente.')
    cenarios=[]
    for j,nome in enumerate(('S1','S2','S3','S4')):
        rng=np.random.default_rng(seed+j)
        linhas=[]
        for rep in range(replicas):
            x=rng.uniform(-1,1,n)
            if nome=='S1':
                e=np.full(n,.5); m0=np.full(n,.105)
            elif nome=='S2':
                e=np.full(n,.85); m0=np.full(n,.1085)
            elif nome=='S3':
                e=.85+.10*x; m0=.0885+.02*x
            else:
                # 20% com e=.995; demais .81375: E[e]=.85.
                e=np.where(x>.6,.995,.81375); m0=.0885+.02*x
            m1=m0-.01
            t=rng.binomial(1,e); y=rng.binomial(1,np.where(t==1,m1,m0))
            r,psi=aipw_independente(y,t,e,m0,m1)
            q=(psi-psi.mean())**2; k=max(1,int(np.ceil(.01*n)))
            top=float(np.partition(q,-k)[-k:].sum()/q.sum())
            ess=ess_grupos(t,e)
            linhas.append(dict(replica=rep,estimativa=r['estimativa'],erro=r['estimativa']+.01,
                erro_quadratico=(r['estimativa']+.01)**2,se=r['se'],
                cobertura=bool(abs(r['estimativa']+.01)<=1.96*r['se']),top1_if2=top,gate=bool(top>.5),
                ess_t0=ess['0']['ess'],ess_t1=ess['1']['ess'],prop_t1=float(t.mean()),prev_y=float(y.mean())))
        erros=np.array([r['erro'] for r in linhas]); gate=np.mean([r['gate'] for r in linhas])
        cobertura=np.mean([r['cobertura'] for r in linhas])
        cenarios.append(dict(cenario=nome,n=n,n_replicas=replicas,efeito_verdadeiro=-.01,
            bias=float(erros.mean()),rmse=float(np.sqrt(np.mean(erros**2))),
            mcse_bias=float(erros.std(ddof=1)/np.sqrt(replicas)),cobertura=float(cobertura),
            mcse_cobertura=float(np.sqrt(cobertura*(1-cobertura)/replicas)),
            prob_gate=float(gate),mcse_prob_gate=float(np.sqrt(gate*(1-gate)/replicas)),
            top1_if2_medio=float(np.mean([r['top1_if2'] for r in linhas])),
            ess_t0_medio=float(np.mean([r['ess_t0'] for r in linhas])),
            ess_t1_medio=float(np.mean([r['ess_t1'] for r in linhas])),replicas=linhas))
    return dict(seed=seed,metodo='AIPW com e,m0,m1 verdadeiros (oráculo), observações iid',
        dgp={'X':'Uniforme(-1,1)','S1':'e=.5; m0=.105',
             'S2':'e=.85; m0=.1085','S3':'e=.85+.10X; m0=.0885+.02X',
             'S4':'e=.995 se X>.6; .81375 caso contrário; m0=.0885+.02X',
             'todos':'m1=m0-.01; T~Bernoulli(e); Y~Bernoulli(mT); E[Y]=.10 S1/S2 e .08 S3/S4'},
        limitacao='Oráculo isola a heurística; não simula ajuste ML, clusters ou seleção SINASC. Não valida o estudo.',
        cenarios=cenarios)


SEED = 20240925

ROOT = Path(__file__).resolve().parents[1]

def salvar_fase3(p, objeto):
    p=Path(p)
    if not p.name.startswith('fase3_'):
        raise ValueError('Escrita permitida somente em artefatos fase3_.')
    _salvar_json(p,objeto)

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
        codigo={f:sha256(raiz/'src'/f) for f in ('robustez.py','modelagem_preditiva.py','amostra.py','diagnosticos.py','inferencia_causal.py')})
    if p.exists() and logp.exists():
        salvo=json.loads(logp.read_text(encoding='utf-8'))
        from src.validacao import conferir_contrato
        conferir_contrato(raiz, salvo['contrato'], contrato)
        if salvo['cache_sha256']!=sha256(p):
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

def executar_robustez(raiz=ROOT,etapa='tudo'):
    from src.validacao import historico
    from src.validacao import verificar_preservacao
    from src.validacao import validar_fase2_sem_escrita
    inicio=time.time(); pasta=raiz/'outputs/diagnostics'
    antes=historico(raiz)
    manifesto=pasta/'fase3_preservacao.json'
    if manifesto.exists():
        from src.validacao import verificar_preservacao
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
