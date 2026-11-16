"""Peso ao nascer contínuo (notebook 06): medidas por grupo, comparação de Welch e ANOVA de Welch.

Análise descritiva e inferencial sobre médias; não é estimação causal. Os IC supõem nascimentos independentes.
"""
from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd
from scipy import stats


def resumir_peso(peso: pd.Series, grupo: pd.Series) -> pd.DataFrame:
    """Uma linha por grupo: n, média com IC 95% (t), DP, percentis e % abaixo de 2.500 e de 2.600 g."""
    peso = pd.Series(peso, dtype=float).reset_index(drop=True)
    grupo = pd.Series(grupo).reset_index(drop=True)
    if peso.isna().any() or grupo.isna().any():
        raise ValueError("Peso ou grupo nulo: a elegibilidade deve ser resolvida antes do resumo.")
    linhas = {}
    for nome, x in peso.groupby(grupo, sort=False):
        x = x.to_numpy()
        n, media, dp = len(x), x.mean(), x.std(ddof=1)
        meia = stats.t.ppf(0.975, n - 1) * dp / np.sqrt(n)
        p10, p25, p50, p75, p90 = np.percentile(x, [10, 25, 50, 75, 90])
        linhas[nome] = {"n": n, "media": media, "ic95_inf": media - meia, "ic95_sup": media + meia, "dp": dp,
                        "p10": p10, "p25": p25, "mediana": p50, "p75": p75, "p90": p90,
                        "pct_menor_2500": 100 * (x < 2500).mean(), "pct_menor_2600": 100 * (x < 2600).mean()}
    return pd.DataFrame.from_dict(linhas, orient="index")


def comparar_medias_welch(a: np.ndarray, b: np.ndarray) -> dict:
    """Diferença de médias (a − b) com IC 95% de Welch, estatística t, graus de liberdade e valor-p bilateral."""
    r = stats.ttest_ind(a, b, equal_var=False)
    ic = r.confidence_interval(0.95)
    return {"n_a": len(a), "n_b": len(b), "diferenca": float(np.mean(a) - np.mean(b)),
            "ic95_inf": float(ic.low), "ic95_sup": float(ic.high),
            "t": float(r.statistic), "gl": float(r.df), "p": float(r.pvalue)}


def anova_welch(amostras: Mapping[str, np.ndarray]) -> dict:
    """ANOVA de Welch (Welch, 1951, Biometrika 38:330–336): não exige variâncias iguais entre os grupos.

    Calculada pela fórmula para expor os graus de liberdade; os testes conferem com
    ``scipy.stats.f_oneway(equal_var=False)`` quando disponível (SciPy ≥ 1.16).
    """
    grupos = [np.asarray(v, dtype=float) for v in amostras.values()]
    k = len(grupos)
    n = np.array([len(g) for g in grupos], dtype=float)
    medias = np.array([g.mean() for g in grupos])
    w = n / np.array([g.var(ddof=1) for g in grupos])
    media_ponderada = (w * medias).sum() / w.sum()
    a = (w * (medias - media_ponderada) ** 2).sum() / (k - 1)
    termo = ((1 - w / w.sum()) ** 2 / (n - 1)).sum()
    f = a / (1 + 2 * (k - 2) / (k ** 2 - 1) * termo)
    gl2 = (k ** 2 - 1) / (3 * termo)
    return {"F": float(f), "gl1": k - 1, "gl2": float(gl2), "p": float(stats.f.sf(f, k - 1, gl2))}
