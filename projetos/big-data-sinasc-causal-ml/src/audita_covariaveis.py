"""Contrato de covariáveis, guarda de leakage e balanceamento bruto."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


COLUNAS_PROPENSITY_PRINCIPAL = (
    "IDADEMAE_NUM",
    "ESCOLARIDADE_MAE",
    "RACA_COR_MAE",
    "SITUACAO_CONJUGAL",
    "PARIDADE_CAT",
    "PERDAS_FETAIS_CAT",
    "UF_RESIDENCIA",
)

VARIAVEIS_PROIBIDAS_PROPENSITY = frozenset(
    {
        "PESO",
        "Y_BAIXO_PESO",
        "Y_BAIXO_PESO_P0",
        "GESTACAO",
        "SEMAGESTAC",
        "CONSPRENAT",
        "CONSULTAS",
        "PARTO",
        "APGAR1",
        "APGAR5",
        "KOTELCHUCK",
        "TPAPRESENT",
        "STTRABPART",
        "STCESPARTO",
        "TPROBSON",
        "IDANOMAL",
        "CODANOMAL",
        "LOCNASC",
        "CODESTAB",
        "TPNASCASSI",
        "DTNASC",
        "HORANASC",
        "RACACOR",
        "SEXO",
        "TPMETESTIM",
    }
)


def validar_colunas_propensity(colunas: Sequence[str]) -> None:
    """Falha se outcome, mediadores ou variáveis posteriores entrarem em X."""

    normalizadas = {str(coluna).upper() for coluna in colunas}
    proibidas = sorted(normalizadas & VARIAVEIS_PROIBIDAS_PROPENSITY)
    if proibidas:
        raise ValueError(
            "Variáveis proibidas no propensity por leakage/pós-tratamento: "
            + ", ".join(proibidas)
        )


def _smd_numerico(tratados: pd.Series, controles: pd.Series) -> float:
    media_t = tratados.mean()
    media_c = controles.mean()
    variancia_pooled = (tratados.var(ddof=1) + controles.var(ddof=1)) / 2
    if pd.isna(variancia_pooled) or variancia_pooled == 0:
        return 0.0 if media_t == media_c else float("inf")
    return float((media_t - media_c) / np.sqrt(variancia_pooled))


def _smd_categorico(tratados: pd.Series, controles: pd.Series) -> float:
    categorias = sorted(set(tratados.dropna().astype(str)) | set(controles.dropna().astype(str)))
    maior = 0.0
    for categoria in categorias:
        p_t = tratados.astype("string").eq(categoria).mean()
        p_c = controles.astype("string").eq(categoria).mean()
        variancia_pooled = (p_t * (1 - p_t) + p_c * (1 - p_c)) / 2
        if variancia_pooled == 0:
            smd = 0.0 if p_t == p_c else float("inf")
        else:
            smd = float((p_t - p_c) / np.sqrt(variancia_pooled))
        maior = max(maior, abs(smd))
    return maior


def calcular_smd(
    dados: pd.DataFrame,
    tratamento: str,
    numericas: Sequence[str],
    categoricas: Sequence[str],
) -> pd.DataFrame:
    """Calcula SMD absoluto; para categóricas, retorna o pior nível observado."""

    linhas: list[dict[str, float | str]] = []
    grupo_t = dados.loc[dados[tratamento].eq(1)]
    grupo_c = dados.loc[dados[tratamento].eq(0)]
    if grupo_t.empty or grupo_c.empty:
        raise ValueError("SMD requer observações em T=1 e T=0.")

    for coluna in numericas:
        t = pd.to_numeric(grupo_t[coluna], errors="coerce").dropna()
        c = pd.to_numeric(grupo_c[coluna], errors="coerce").dropna()
        smd = _smd_numerico(t, c)
        linhas.append(
            {
                "variavel": coluna,
                "tipo": "numerica",
                "media_t1": float(t.mean()),
                "media_t0": float(c.mean()),
                "smd": smd,
                "smd_abs": abs(smd),
            }
        )

    for coluna in categoricas:
        t = grupo_t[coluna].fillna("IGNORADO")
        c = grupo_c[coluna].fillna("IGNORADO")
        smd_abs = _smd_categorico(t, c)
        linhas.append(
            {
                "variavel": coluna,
                "tipo": "categorica_max_nivel",
                "media_t1": np.nan,
                "media_t0": np.nan,
                "smd": smd_abs,
                "smd_abs": smd_abs,
            }
        )
    return pd.DataFrame(linhas).sort_values("smd_abs", ascending=False).reset_index(drop=True)
