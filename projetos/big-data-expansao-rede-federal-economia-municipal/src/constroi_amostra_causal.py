"""Funções puras para materializar a amostra causal congelada D15.

Não estima efeitos causais e não grava artefatos. A persistência permanece
explícita no notebook ``02_construcao_amostra_causal.ipynb``.
"""
from __future__ import annotations

import pandas as pd

import define_especificacao_causal as d14


ANOS_BASE = set(range(2007, 2020))
COLUNAS_OBRIGATORIAS = {
    "codigo_municipio_ibge",
    "ano",
    "candidato_amostra_principal",
    "fl_elegivel_controle_candidato",
    "ano_coorte_candidata",
}


def _validar_painel(painel: pd.DataFrame) -> None:
    faltantes = COLUNAS_OBRIGATORIAS - set(painel.columns)
    if faltantes:
        raise ValueError(f"painel causal: colunas obrigatórias ausentes: {sorted(faltantes)}")
    if painel.duplicated(["codigo_municipio_ibge", "ano"]).any():
        raise ValueError("painel causal: chave codigo_municipio_ibge-ano duplicada")


def _validar_balanceamento_base(amostra: pd.DataFrame) -> None:
    anos_por_unidade = amostra.groupby("codigo_municipio_ibge").ano.agg(set)
    incompletas = anos_por_unidade.loc[anos_por_unidade.ne(ANOS_BASE)]
    if not incompletas.empty:
        raise ValueError(
            "painel causal base exige exatamente os 13 anos de 2007 a 2019; "
            f"unidades inválidas: {incompletas.index.astype(str).tolist()[:5]}"
        )


def construir_amostra_causal(painel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Classifica tratados e controles e aplica as exclusões D15.

    Retorna ``(amostra, exclusoes)``. ``amostra`` é o painel base retangular;
    a elegibilidade do estimador é uma máscara anual, de modo que Cabo
    Frio/2009 não remove a unidade inteira do painel populacional.
    """
    _validar_painel(painel)
    trabalho = painel.copy()
    trabalho["codigo_municipio_ibge"] = trabalho["codigo_municipio_ibge"].astype(str).str.zfill(7)

    tratados = set(
        trabalho.loc[trabalho["candidato_amostra_principal"], "codigo_municipio_ibge"]
    )
    controles_pool = set(
        trabalho.loc[trabalho["fl_elegivel_controle_candidato"], "codigo_municipio_ibge"]
    )
    conflito = tratados & controles_pool
    if conflito:
        raise ValueError(f"painel causal: tratado também marcado como controle: {sorted(conflito)[:5]}")

    codigo_sigilo = d14.CODIGO_MUNICIPIO_SIGILO_EXCLUIR
    controles = controles_pool - {codigo_sigilo}
    selecionadas = tratados | controles
    amostra = trabalho.loc[trabalho["codigo_municipio_ibge"].isin(selecionadas)].copy()
    _validar_balanceamento_base(amostra)

    amostra["papel_causal"] = "CONTROLE_NEVER_TREATED"
    amostra.loc[amostra["codigo_municipio_ibge"].isin(tratados), "papel_causal"] = "TRATADO_PRINCIPAL"
    amostra["coorte_g"] = amostra["ano_coorte_candidata"].where(
        amostra["papel_causal"].eq("TRATADO_PRINCIPAL")
    )
    amostra["tempo_relativo"] = (amostra["ano"] - amostra["coorte_g"]).where(
        amostra["papel_causal"].eq("TRATADO_PRINCIPAL")
    )
    amostra["periodo_pos_coorte"] = (amostra["ano"] >= amostra["coorte_g"]).where(
        amostra["papel_causal"].eq("TRATADO_PRINCIPAL")
    )
    mascara_cabo = (
        amostra["codigo_municipio_ibge"].eq(d14.CODIGO_CABO_FRIO) & amostra["ano"].eq(2009)
    )
    amostra["elegivel_estimacao_principal"] = ~mascara_cabo
    amostra["motivo_nao_elegibilidade_estimacao"] = pd.NA
    amostra.loc[mascara_cabo, "motivo_nao_elegibilidade_estimacao"] = (
        "ANO_TRANSICAO_INSTITUCIONAL_CABO_FRIO_2009"
    )

    exclusoes = pd.DataFrame([
        {
            "codigo_municipio_ibge": codigo_sigilo,
            "ano": pd.NA,
            "tipo_exclusao": "UNIDADE",
            "motivo": "SIGILO_OUTCOME_708_2012",
            "origem_regra": "D14",
            "status_outcome": "sigilo",
        },
        {
            "codigo_municipio_ibge": d14.CODIGO_CABO_FRIO,
            "ano": 2009,
            "tipo_exclusao": "OBSERVACAO",
            "motivo": "ANO_TRANSICAO_INSTITUCIONAL",
            "origem_regra": "cadastro_causal_D11_D14",
            "status_outcome": "observado",
        },
    ])
    return amostra.sort_values(["codigo_municipio_ibge", "ano"]).reset_index(drop=True), exclusoes


def selecionar_janela_principal(amostra: pd.DataFrame) -> pd.DataFrame:
    """Recorta observações tratadas elegíveis em k=-2…+2.

    A função não afirma que cada unidade possui todos os valores de k;
    essa cobertura completa é diagnosticada separadamente na D16.
    """
    return amostra.loc[
        amostra["papel_causal"].eq("TRATADO_PRINCIPAL")
        & amostra["tempo_relativo"].between(-2, 2)
        & amostra["elegivel_estimacao_principal"]
    ].copy()


def selecionar_janela_sensibilidade(amostra: pd.DataFrame) -> pd.DataFrame:
    """Recorta observações da sensibilidade k=-3…+2 (g >= 2010).

    ``g >= 2010`` define a população de 108 tratados com suporte de
    calendário. A completude após máscaras observacionais é uma medida
    distinta e fica a cargo dos diagnósticos D16.
    """
    return amostra.loc[
        amostra["papel_causal"].eq("TRATADO_PRINCIPAL")
        & amostra["coorte_g"].ge(2010)
        & amostra["tempo_relativo"].between(-3, 2)
        & amostra["elegivel_estimacao_principal"]
    ].copy()
