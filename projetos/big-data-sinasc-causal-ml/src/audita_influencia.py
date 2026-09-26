"""AUDITORIA FASE 3: implementação independente, concentração e perfis."""
import numpy as np
import pandas as pd

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
