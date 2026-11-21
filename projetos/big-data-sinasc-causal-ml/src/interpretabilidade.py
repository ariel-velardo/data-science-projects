"""Interpretabilidade do M3 do desfecho (notebook 06) por valores SHAP na escala do logit (log-odds).

Explica a regressão logística do **desfecho**, P(Y=1 | X), não o escore de propensão do notebook 03, P(T=1 | X).

Para um modelo linear no logit, com preditores tratados como independentes (perturbação intervencional), o valor SHAP
do termo j numa observação é exato e tem forma fechada:

    φ_j(x) = β_j · (x_j − E_fundo[x_j]),      η(x) = φ_0 + Σ_j φ_j(x),      φ_0 = β_0 + Σ_j β_j · E_fundo[x_j]

em que η é o logit (log-odds) previsto e E_fundo é a média na amostra de fundo. As contribuições somam-se em log-odds,
não em probabilidade nem em pontos percentuais. A padronização da idade não muda φ: β·(z − z̄) = (β/σ)·(x − x̄).

Termos derivados da mesma variável são agregados somando φ linha a linha (idade + idade²; indicadores de uma mesma
categórica). Importância global = média de |φ agregado|, que mede quanto o termo move a previsão do modelo em relação
à previsão média: não é efeito causal, significância estatística nem magnitude de efeito clínico.
"""
from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.logistica_desfecho import CATEGORIAS, NUMERICAS, SEMENTE, X1

TAMANHO_AMOSTRA_SHAP = 10_000
ROTULOS_GRUPOS = {X1: "Início do pré-natal (X1)", "IDADE": "Idade (idade + idade²)",
                  "ESCOLARIDADE_MAE": "Escolaridade", "RACA_COR_MAE": "Raça/cor",
                  "PARIDADE_CAT": "Paridade", "PERDAS_FETAIS_CAT": "Perdas fetais anteriores"}


def amostra_reprodutivel(n_universo: int, tamanho: int = TAMANHO_AMOSTRA_SHAP, semente: int = SEMENTE) -> np.ndarray:
    """Posições (ordenadas) de uma amostra aleatória simples sem reposição, reprodutível pela semente."""
    if not 0 < tamanho <= n_universo:
        raise ValueError("Tamanho da amostra deve estar entre 1 e o tamanho do universo.")
    return np.sort(np.random.default_rng(semente).choice(n_universo, size=tamanho, replace=False))


def _desenho(modelo: Pipeline, x: pd.DataFrame) -> pd.DataFrame:
    """Matriz que o LogisticRegression recebe (idade padronizada, X1 e indicadores 0/1), com nomes dos termos."""
    return pd.DataFrame(np.asarray(modelo[:-1].transform(x), dtype=float),
                        columns=list(modelo[:-1].get_feature_names_out()), index=x.index)


def contribuicoes_lineares(modelo: Pipeline, x_explicar: pd.DataFrame,
                           x_fundo: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """Decomposição exata do logit: φ_j = β_j (x_j − média de fundo); devolve (φ por termo, valor-base φ_0)."""
    desenho, fundo = _desenho(modelo, x_explicar), _desenho(modelo, x_fundo)
    beta = pd.Series(modelo[-1].coef_.ravel(), index=desenho.columns)
    media = fundo.mean()
    phi = (desenho - media) * beta
    base = float(modelo[-1].intercept_[0] + (media * beta).sum())
    return phi, base


def contribuicoes_shap(modelo: Pipeline, x_explicar: pd.DataFrame,
                       x_fundo: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """Valores SHAP pelo ``shap.LinearExplainer`` (perturbação intervencional), na escala do logit.

    O fundo inteiro entra no masker (``max_samples`` = tamanho do fundo), para que o valor-base seja a média exata
    e não a de uma subamostra de 100 linhas, o padrão do SHAP.
    """
    import shap

    desenho, fundo = _desenho(modelo, x_explicar), _desenho(modelo, x_fundo)
    regressao = modelo[-1]
    explicador = shap.LinearExplainer((regressao.coef_.ravel(), float(regressao.intercept_[0])),
                                      shap.maskers.Independent(fundo.to_numpy(), max_samples=len(fundo)))
    valores = np.asarray(explicador.shap_values(desenho.to_numpy()), dtype=float)
    base = float(np.ravel(explicador.expected_value)[0])
    return pd.DataFrame(valores, columns=desenho.columns, index=x_explicar.index), base


def grupos_de_termos(termos: Sequence[str]) -> dict[str, list[str]]:
    """Agrupa termos do desenho pela variável de origem: idade com idade²; indicadores pela categórica."""
    grupos: dict[str, list[str]] = {}
    for termo in termos:
        if termo == X1:
            chave = X1
        elif termo in NUMERICAS:
            chave = "IDADE"
        else:
            chave = next((v for v in CATEGORIAS if termo.startswith(v + "_")), None)
            if chave is None:
                raise ValueError(f"Termo sem variável de origem: {termo}")
        grupos.setdefault(chave, []).append(termo)
    return grupos


def agrupar_contribuicoes(phi: pd.DataFrame, grupos: Mapping[str, Sequence[str]]) -> pd.DataFrame:
    """Soma φ dos termos de cada grupo, linha a linha (antes de qualquer valor absoluto)."""
    usados = [t for termos in grupos.values() for t in termos]
    if sorted(usados) != sorted(phi.columns):
        raise ValueError("Os grupos devem cobrir cada termo exatamente uma vez.")
    return pd.DataFrame({g: phi[list(termos)].sum(axis=1) for g, termos in grupos.items()}, index=phi.index)


def importancia_global(phi: pd.DataFrame) -> pd.Series:
    """Média de |φ| por coluna, em ordem decrescente (log-odds)."""
    return phi.abs().mean().sort_values(ascending=False)


def erro_reconstrucao(phi: pd.DataFrame, base: float, logito: np.ndarray) -> float:
    """Maior |φ_0 + Σ φ_j − logit do modelo|: deve ser da ordem do erro de arredondamento."""
    return float(np.max(np.abs(base + phi.sum(axis=1).to_numpy() - np.asarray(logito, dtype=float))))


def contribuicao_por_nivel(phi_agrupado: pd.DataFrame, x: pd.DataFrame) -> pd.DataFrame:
    """φ agregado por valor observado de cada variável: n, % da amostra e φ médio, mínimo e máximo.

    Para X1 e categóricas, φ é constante dentro do nível; para a idade, cada idade em anos tem um único φ.
    """
    linhas = []
    for grupo in phi_agrupado.columns:
        origem = "IDADEMAE_NUM" if grupo == "IDADE" else grupo
        valores = x.loc[phi_agrupado.index, origem]
        resumo = phi_agrupado[grupo].groupby(valores.to_numpy()).agg(["size", "mean", "min", "max"])
        for nivel, r in resumo.iterrows():
            linhas.append({"grupo": grupo, "nivel": nivel, "n": int(r["size"]), "pct": 100 * r["size"] / len(x.loc[phi_agrupado.index]),
                           "phi_medio": r["mean"], "phi_min": r["min"], "phi_max": r["max"]})
    return pd.DataFrame(linhas)
