"""DR-Learner com três papéis disjuntos: auxiliares, regressão e avaliação."""
import hashlib
import duckdb
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits

from src.estima_aipw import calcular_aipw
from src.modelagem_preditiva import (validar_x,criar_modelo,ajustar_modelo,predizer,SEED)


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
