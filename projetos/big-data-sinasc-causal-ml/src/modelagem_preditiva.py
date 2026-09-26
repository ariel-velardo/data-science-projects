"""Modelos congelados e benchmark de risco; não estima efeitos causais."""
import warnings

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import (average_precision_score, brier_score_loss, roc_auc_score,
                             precision_recall_fscore_support, roc_curve, precision_recall_curve)
from sklearn.calibration import calibration_curve
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder
from threadpoolctl import threadpool_limits

from src.audita_covariaveis import COLUNAS_PROPENSITY_PRINCIPAL, validar_colunas_propensity
from src.diagnostica_overlap import construir_pipeline_propensity

SEED = 20240925
NUM = ['IDADEMAE_NUM']
CAT = [c for c in COLUNAS_PROPENSITY_PRINCIPAL if c not in NUM]


def validar_x(x):
    validar_colunas_propensity(x.columns)
    if set(x.columns) != set(COLUNAS_PROPENSITY_PRINCIPAL):
        raise ValueError('X deve conter exatamente as sete covariáveis congeladas, sem T ou Y.')


def criar_modelo(tipo):
    if tipo == 'logistica':
        return construir_pipeline_propensity(NUM, CAT)
    if tipo != 'hgb':
        raise ValueError('Modelo desconhecido.')
    prep = ColumnTransformer([
        ('idade', 'passthrough', NUM),
        ('categorias', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=np.nan), CAT),
    ])
    return Pipeline([
        ('preprocessamento', prep),
        ('modelo', HistGradientBoostingClassifier(
            max_iter=100, max_leaf_nodes=15, min_samples_leaf=100,
            learning_rate=.1, l2_regularization=1.,
            categorical_features=[False] + [True]*len(CAT),
            early_stopping=True, validation_fraction=.1, random_state=SEED,
        )),
    ])


def ajustar_modelo(modelo, x, y):
    """Captura convergência; um retry técnico explícito para logística."""
    validar_x(x)
    tentativas = []
    for tentativa in range(2):
        with threadpool_limits(limits=4), warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter('always', ConvergenceWarning)
            modelo.fit(x, y)
        problemas = [str(a.message) for a in avisos if issubclass(a.category, ConvergenceWarning)]
        tentativas.append({'tentativa': tentativa + 1, 'convergence_warnings': problemas})
        if not problemas:
            n_iter = int(np.max(modelo['modelo'].n_iter_))
            return modelo, {'n_iter': n_iter, 'convergence_warning': False, 'tentativas': tentativas,
                            'early_stopping': modelo['modelo'].__class__.__name__.startswith('Hist')}
        if 'max_iter' in modelo['modelo'].get_params():
            modelo.set_params(modelo__max_iter=1500)
    raise RuntimeError('Modelo não convergiu após ajuste técnico de max_iter.')


def predizer(modelo, x):
    with threadpool_limits(limits=4):
        return modelo.predict_proba(x)[:, 1]


def avaliar_probabilidades(y, p):
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError('Probabilidades inválidas.')
    precision, recall, f1, _ = precision_recall_fscore_support(y, p >= .5, average='binary', zero_division=0)
    return {'roc_auc': float(roc_auc_score(y, p)), 'pr_auc_ap': float(average_precision_score(y, p)),
            'brier': float(brier_score_loss(y, p)), 'precision_05': float(precision),
            'recall_05': float(recall), 'f1_05': float(f1), 'limiar': .5,
            'prevalencia': float(np.mean(y)), 'media_predita': float(np.mean(p))}


def _reduzir_curva(a, b, n=201):
    i = np.unique(np.linspace(0, len(a)-1, min(n, len(a))).astype(int))
    return {'x': np.asarray(a)[i].tolist(), 'y': np.asarray(b)[i].tolist()}


def benchmark(x, y):
    validar_x(x)
    y = np.asarray(y, dtype=int)
    tr, te = train_test_split(np.arange(len(y)), test_size=.2, stratify=y, random_state=SEED)
    resultados = []
    for tipo in ('logistica', 'hgb'):
        print(f'Benchmark {tipo}: treino={len(tr)}, teste={len(te)}', flush=True)
        modelo, ajuste = ajustar_modelo(criar_modelo(tipo), x.iloc[tr], y[tr])
        p = predizer(modelo, x.iloc[te])
        fpr, tpr, _ = roc_curve(y[te], p)
        prec, rec, _ = precision_recall_curve(y[te], p)
        observado, previsto = calibration_curve(y[te], p, n_bins=10, strategy='quantile')
        resultados.append({'modelo': tipo, **avaliar_probabilidades(y[te], p), 'ajuste': ajuste,
                           'roc': _reduzir_curva(fpr, tpr), 'pr': _reduzir_curva(rec, prec),
                           'calibracao': {'previsto': previsto.tolist(), 'observado': observado.tolist()}})
    return {'n': len(y), 'n_treino': len(tr), 'n_teste': len(te), 'seed': SEED,
            'x': list(x.columns), 'usa_tratamento': False, 'modelos': resultados,
            'nota_pr_auc': 'Average precision; não área trapezoidal.',
            'brier_baseline_prevalencia_treino': float(np.mean((y[te]-y[tr].mean())**2))}
