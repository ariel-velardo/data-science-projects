"""AIPW transparente com predições OOF e SE por função de influência."""
import hashlib
import numpy as np
from sklearn.model_selection import StratifiedKFold

from src.modelagem_preditiva import (SEED, validar_x, criar_modelo, ajustar_modelo,
                                     predizer, avaliar_probabilidades)


def calcular_aipw(y, t, e, m0, m1):
    vetores = [np.asarray(v, dtype=float) for v in (y, t, e, m0, m1)]
    if any(v.ndim != 1 for v in vetores) or len({len(v) for v in vetores}) != 1:
        raise ValueError('Vetores devem ser unidimensionais e ter mesmo N.')
    y, t, e, m0, m1 = vetores
    if len(y) < 2 or not all(np.isfinite(v).all() for v in vetores):
        raise ValueError('Dados vazios, NaN ou infinito.')
    if set(np.unique(t)) != {0, 1} or not set(np.unique(y)).issubset({0, 1}):
        raise ValueError('Requer T binário com ambos os grupos e Y binário.')
    if np.any((e <= 0) | (e >= 1)) or any(np.any((m < 0) | (m > 1)) for m in (m0, m1)):
        raise ValueError('Propensity deve estar estritamente em (0,1); outcomes em [0,1].')
    psi = m1 - m0 + t*(y-m1)/e - (1-t)*(y-m0)/(1-e)
    estimativa = float(psi.mean())
    se = float(psi.std(ddof=1) / np.sqrt(len(psi)))
    r = {'n': len(y), 'n_t1': int(t.sum()), 'n_t0': int((1-t).sum()),
         'estimativa': estimativa, 'se': se, 'ic95_inferior': estimativa-1.96*se,
         'ic95_superior': estimativa+1.96*se}
    for campo in ('estimativa', 'se', 'ic95_inferior', 'ic95_superior'):
        r[campo+'_pp'] = 100*r[campo]
    return r, psi


def gerar_folds(t, y, n_folds=3, seed=SEED):
    t, y = np.asarray(t), np.asarray(y)
    if set(np.unique(t)) != {0, 1} or not set(np.unique(y)).issubset({0, 1}) or len(t) != len(y):
        raise ValueError('T/Y inválidos ou ausência de grupo.')
    estratos = 2*t + y
    if np.unique(estratos, return_counts=True)[1].min() < n_folds:
        raise ValueError('Poucas observações por estrato para cross-fitting.')
    return list(StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed).split(np.zeros(len(t)), estratos))


def cross_fitting(x, t, y, n_folds=3):
    validar_x(x)
    t, y = np.asarray(t), np.asarray(y)
    folds = gerar_folds(t, y, n_folds)
    t, y = t.astype(int), y.astype(int)
    if len(x) != len(t):
        raise ValueError('X e T com tamanhos diferentes.')
    r = {c: np.full(len(t), np.nan) for c in ('e', 'm0_C1', 'm1_C1', 'm0_C2', 'm1_C2')}
    r['cobertura'] = np.zeros(len(t), dtype=int)
    r['fold_id'] = np.full(len(t), -1, dtype=int)
    r['folds'] = []
    for f, (tr, va) in enumerate(folds, 1):
        if np.intersect1d(tr, va).size:
            raise ValueError('Sobreposição treino/validação.')
        info = {'fold': f, 'n_treino': len(tr), 'n_validacao': len(va), 'intersecao': 0,
                'sha256_indices_validacao': hashlib.sha256(va.tobytes()).hexdigest(), 'ajustes': {}}
        print(f'AIPW fold {f}/{n_folds}: propensity', flush=True)
        modelo, log = ajustar_modelo(criar_modelo('logistica'), x.iloc[tr], t[tr])
        r['e'][va] = predizer(modelo, x.iloc[va])
        info['ajustes']['e'] = log
        for spec, tipo in (('C1', 'logistica'), ('C2', 'hgb')):
            for grupo in (0, 1):
                indices = tr[t[tr] == grupo]
                print(f'AIPW fold {f}: {spec} m{grupo}, N treino={len(indices)}', flush=True)
                modelo, log = ajustar_modelo(criar_modelo(tipo), x.iloc[indices], y[indices])
                r[f'm{grupo}_{spec}'][va] = predizer(modelo, x.iloc[va])
                info['ajustes'][f'm{grupo}_{spec}'] = log
        r['cobertura'][va] += 1
        r['fold_id'][va] = f
        r['folds'].append(info)
    if not np.all(r['cobertura'] == 1):
        raise ValueError('Cobertura OOF inválida.')
    for spec in ('C1', 'C2'):
        calcular_aipw(y, t, r['e'], r[f'm0_{spec}'], r[f'm1_{spec}'])
    return r


def diagnosticos_influencia(psi, t, e):
    psi, t, e = map(np.asarray, (psi, t, e))
    influencia = psi - psi.mean()
    quadrados = influencia**2
    k = max(1, int(np.ceil(len(psi)*.01)))
    top = float(np.partition(quadrados, -k)[-k:].sum() / quadrados.sum()) if quadrados.sum() else 0.
    pesos = {}
    for grupo in (0, 1):
        w = 1 / (e[t == grupo] if grupo else 1-e[t == grupo])
        pesos[str(grupo)] = {'n': len(w), 'ess': float(w.sum()**2 / np.sum(w*w)),
                              'media': float(w.mean()), 'max': float(w.max()),
                              'p99': float(np.quantile(w, .99))}
    q = [0, .01, .05, .5, .95, .99, 1]
    return {'pesos_por_grupo': pesos, 'frac_variancia_top1pct': top,
            'max_abs_influencia': float(np.max(np.abs(influencia))),
            'psi_percentis': dict(zip(map(str, q), np.quantile(psi, q).tolist())),
            'if_percentis': dict(zip(map(str, q), np.quantile(influencia, q).tolist())),
            'max_contribuicao_individual_pp': float(100*np.max(np.abs(influencia))/len(psi))}


def resumir_especificacoes(y, t, predicoes):
    e = predicoes['e']
    linhas = []
    diagnosticos = {}
    for spec in ('C1', 'C2'):
        for regra, lo, hi in (('sem_trimming', 0, 1), ('0.01_0.99', .01, .99), ('0.05_0.95', .05, .95)):
            mask = (e >= lo) & (e <= hi)
            r, psi = calcular_aipw(y[mask], t[mask], e[mask], predicoes[f'm0_{spec}'][mask], predicoes[f'm1_{spec}'][mask])
            r.update(especificacao=spec, populacao=regra, n_excluido=int((~mask).sum()))
            linhas.append(r)
            diagnosticos[f'{spec}_{regra}'] = diagnosticos_influencia(psi, t[mask], e[mask])
    return linhas, diagnosticos
