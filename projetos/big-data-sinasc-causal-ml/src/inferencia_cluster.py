"""Sandwich e bootstrap de clusters para a média de pseudo-outcomes fixos."""
import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from sklearn.model_selection import StratifiedGroupKFold

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
