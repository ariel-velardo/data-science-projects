"""Regras reproduzíveis da amostra analítica candidata da Fase 1."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


COLUNAS_BRUTAS_X_PRINCIPAL = (
    "IDADEMAE",
    "ESCMAE2010",
    "RACACORMAE",
    "ESTCIVMAE",
    "PARIDADE",
    "QTDFILMORT",
    "CODMUNRES",
)

COLUNAS_DERIVADAS_X_PRINCIPAL = (
    "IDADEMAE_NUM",
    "ESCOLARIDADE_MAE",
    "RACA_COR_MAE",
    "SITUACAO_CONJUGAL",
    "PARIDADE_CAT",
    "PERDAS_FETAIS_CAT",
    "UF_RESIDENCIA",
)


def construir_tratamento(mes_inicio_prenatal: pd.Series) -> pd.Series:
    """Define T=1 para meses 1-3, T=0 para 4-9 e NA nos demais casos."""

    mes = pd.to_numeric(mes_inicio_prenatal, errors="coerce")
    tratamento = pd.Series(pd.NA, index=mes_inicio_prenatal.index, dtype="Int8")
    tratamento.loc[mes.between(1, 3)] = 1
    tratamento.loc[mes.between(4, 9)] = 0
    return tratamento


def construir_outcome_baixo_peso(
    peso: pd.Series, regra_peso: str = "P1"
) -> pd.Series:
    """Define Y (<2.500 g) sob P0 (>0 g) ou P1 (500-6.000 g)."""

    regra = regra_peso.upper()
    if regra not in {"P0", "P1"}:
        raise ValueError("regra_peso deve ser 'P0' ou 'P1'.")
    peso_num = pd.to_numeric(peso, errors="coerce")
    valido = peso_num.gt(0)
    if regra == "P1":
        valido &= peso_num.between(500, 6000)
    outcome = pd.Series(pd.NA, index=peso.index, dtype="Int8")
    outcome.loc[valido] = peso_num.loc[valido].lt(2500).astype("Int8")
    return outcome


def identificar_gestacao_unica(gravidez: pd.Series) -> pd.Series:
    """Retorna True somente para GRAVIDEZ=1; múltipla/ignorada/missing são False."""

    return pd.to_numeric(gravidez, errors="coerce").eq(1).fillna(False).astype(bool)


def derivar_uf_residencia(codigo_municipio: pd.Series) -> pd.Series:
    """Deriva os dois primeiros dígitos da UF sem modificar CODMUNRES."""

    codigo = codigo_municipio.astype("string")
    valido = codigo.str.fullmatch(r"\d{6}", na=False)
    uf = pd.Series(pd.NA, index=codigo.index, dtype="string")
    uf.loc[valido] = codigo.loc[valido].str[:2]
    return uf


def _categoria_com_ignorado(
    serie: pd.Series, codigos_ignorados: Iterable[str] = ("9", "99")
) -> pd.Series:
    categoria = serie.astype("string").str.strip()
    ignorado = categoria.isna() | categoria.isin(tuple(codigos_ignorados))
    return categoria.mask(ignorado, "IGNORADO").fillna("IGNORADO")


def _categorizar_perdas_fetais(serie: pd.Series) -> pd.Series:
    valor = pd.to_numeric(serie, errors="coerce")
    valor = valor.mask(valor.eq(99))
    saida = pd.Series("IGNORADO", index=serie.index, dtype="string")
    saida.loc[valor.eq(0)] = "0"
    saida.loc[valor.eq(1)] = "1"
    saida.loc[valor.ge(2)] = "2_OU_MAIS"
    return saida


def preparar_covariaveis_principais(dados: pd.DataFrame) -> pd.DataFrame:
    """Cria o X principal parcimonioso, preservando as colunas geográficas brutas."""

    ausentes = sorted(set(COLUNAS_BRUTAS_X_PRINCIPAL) - set(dados.columns))
    if ausentes:
        raise ValueError(f"Colunas necessárias para X ausentes: {', '.join(ausentes)}")

    preparado = dados.copy()
    idade = pd.to_numeric(preparado["IDADEMAE"], errors="coerce")
    preparado["IDADEMAE_NUM"] = idade.mask(~idade.between(10, 59))
    preparado["ESCOLARIDADE_MAE"] = _categoria_com_ignorado(
        preparado["ESCMAE2010"], ("9",)
    )
    preparado["RACA_COR_MAE"] = _categoria_com_ignorado(
        preparado["RACACORMAE"], ("9",)
    )
    preparado["SITUACAO_CONJUGAL"] = _categoria_com_ignorado(
        preparado["ESTCIVMAE"], ("9",)
    )
    preparado["PARIDADE_CAT"] = _categoria_com_ignorado(
        preparado["PARIDADE"], ("9", "99")
    )
    preparado["PERDAS_FETAIS_CAT"] = _categorizar_perdas_fetais(
        preparado["QTDFILMORT"]
    )
    preparado["UF_RESIDENCIA"] = derivar_uf_residencia(
        preparado["CODMUNRES"]
    ).fillna("IGNORADO")
    return preparado


def construir_cenarios_amostra(
    dados: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Constrói A0-A3 e um fluxo reconciliável, sem estimar efeito causal."""

    obrigatorias = {"MESPRENAT", "PESO", "GRAVIDEZ", *COLUNAS_BRUTAS_X_PRINCIPAL}
    ausentes = sorted(obrigatorias - set(dados.columns))
    if ausentes:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(ausentes)}")

    trabalho = dados.copy()
    trabalho["tratamento"] = construir_tratamento(trabalho["MESPRENAT"])
    trabalho["Y_BAIXO_PESO_P0"] = construir_outcome_baixo_peso(
        trabalho["PESO"], "P0"
    )
    trabalho["Y_BAIXO_PESO"] = construir_outcome_baixo_peso(
        trabalho["PESO"], "P1"
    )
    trabalho["GESTACAO_UNICA"] = identificar_gestacao_unica(trabalho["GRAVIDEZ"])

    etapas: list[dict[str, int | float | str]] = []
    total_inicial = len(trabalho)

    def aplicar(etapa: str, motivo: str, mascara: pd.Series) -> None:
        nonlocal trabalho
        n_antes = len(trabalho)
        trabalho = trabalho.loc[mascara.loc[trabalho.index]].copy()
        n_restante = len(trabalho)
        etapas.append(
            {
                "etapa": etapa,
                "n_antes": n_antes,
                "n_excluido": n_antes - n_restante,
                "motivo": motivo,
                "n_restante": n_restante,
                "percentual_base_inicial": (
                    round(100 * n_restante / total_inicial, 6) if total_inicial else 0.0
                ),
            }
        )

    aplicar(
        "A0",
        "T conhecido (MESPRENAT 1-9) e PESO numérico positivo",
        trabalho["tratamento"].notna() & trabalho["Y_BAIXO_PESO_P0"].notna(),
    )
    aplicar(
        "A1",
        "Qualidade P1: 500 g <= PESO <= 6.000 g",
        trabalho["Y_BAIXO_PESO"].notna(),
    )
    aplicar(
        "A2",
        "Amostra principal restrita a gestação única (GRAVIDEZ=1)",
        trabalho["GESTACAO_UNICA"],
    )
    n_antes_x = len(trabalho)
    trabalho = preparar_covariaveis_principais(trabalho)
    etapas.append(
        {
            "etapa": "A3",
            "n_antes": n_antes_x,
            "n_excluido": 0,
            "motivo": (
                "X principal preparado; missing tratado no pipeline, sem exclusão "
                "complete-case"
            ),
            "n_restante": len(trabalho),
            "percentual_base_inicial": (
                round(100 * len(trabalho) / total_inicial, 6) if total_inicial else 0.0
            ),
        }
    )
    return trabalho, pd.DataFrame(etapas)
