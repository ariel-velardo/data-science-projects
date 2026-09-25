"""D17 — auditoria diagnóstica pré-estimação do desenho causal.

As funções deste módulo são puras: não estimam ATT, não executam matching,
não selecionam a amostra causal e não gravam artefatos. Modelos de
classificação, quando usados, servem exclusivamente ao diagnóstico de
overlap com covariáveis medidas antes do tratamento.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import analisa_amostra_causal as d16


PAPEL_TRATADO = d16.PAPEL_TRATADO
PAPEL_CONTROLE = d16.PAPEL_CONTROLE
OUTCOME_PRIMARIO = "pessoal_ocupado_assalariado"
ANO_BASE_COMUM = 2007
COORTES = (2009, 2010, 2011, 2012, 2013)

COVARIAVEIS_CEMPRE = (
    "qt_unidades_locais",
    "pessoal_ocupado_total",
    "pessoal_ocupado_assalariado",
    "pessoal_assalariado_medio",
    "salarios_remuneracoes_mil_reais_nominal",
    "salario_medio_salarios_minimos_nominal",
    "salario_medio_reais_nominal",
)

COVARIAVEIS_PROIBIDAS_AJUSTE = {
    "papel_causal",
    "coorte_g",
    "ano_coorte_candidata",
    "tempo_relativo",
    "periodo_pos_coorte",
    "elegivel_estimacao_principal",
    "motivo_nao_elegibilidade_estimacao",
    "primeiro_ano_exposicao_observada",
    "fl_elegivel_controle_candidato",
    "sem_exposicao_observada_2007_2019",
    "fl_municipio_fase_ii",
    "fl_excluir_exposicao_observada",
    "fl_excluir_fase_ii",
    "fase_ii",
    "ever_treated",
    "pode_ser_controle",
    "tratamento_absorvente",
    "candidato_amostra_principal",
    "ano_inicio_observado_censo",
    "ano_evento_institucional",
    "ano_transicao",
    "primeiro_ano_completo",
}

UF_PARA_REGIAO = {
    "11": "Norte", "12": "Norte", "13": "Norte", "14": "Norte",
    "15": "Norte", "16": "Norte", "17": "Norte",
    "21": "Nordeste", "22": "Nordeste", "23": "Nordeste", "24": "Nordeste",
    "25": "Nordeste", "26": "Nordeste", "27": "Nordeste", "28": "Nordeste",
    "29": "Nordeste",
    "31": "Sudeste", "32": "Sudeste", "33": "Sudeste", "35": "Sudeste",
    "41": "Sul", "42": "Sul", "43": "Sul",
    "50": "Centro-Oeste", "51": "Centro-Oeste", "52": "Centro-Oeste",
    "53": "Centro-Oeste",
}


def _codigos(frame: pd.DataFrame) -> pd.Series:
    return frame["codigo_municipio_ibge"].astype("string").str.zfill(7)


def sha256_arquivo(caminho: str | Path) -> str:
    """Calcula SHA-256 em leitura incremental, sem alterar o arquivo."""
    digest = sha256()
    with Path(caminho).open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def auditar_input_congelado(amostra: pd.DataFrame) -> dict[str, Any]:
    """Reproduz os contratos D15/D16 e valida outcome/coortes da D17."""
    resultado: dict[str, Any] = dict(d16.validar_amostra_causal(amostra))
    trabalho = amostra.copy()
    trabalho["codigo_municipio_ibge"] = _codigos(trabalho)

    if trabalho[["codigo_municipio_ibge", "ano"]].duplicated().any():
        raise ValueError("chave municipio-ano duplicada")
    if trabalho[OUTCOME_PRIMARIO].isna().any():
        raise ValueError("outcome primário contém missing inesperado")
    status = set(trabalho["status_pessoal_ocupado_assalariado"].dropna())
    if not status.issubset({"observado", "zero_real"}):
        raise ValueError(f"outcome primário contém status incompatível: {sorted(status)}")

    coortes = d16.distribuicao_coortes(trabalho)
    resultado["coortes"] = {
        int(linha.coorte_g): int(linha.n_tratados) for linha in coortes.itertuples()
    }
    resultado["n_missing_outcome"] = int(trabalho[OUTCOME_PRIMARIO].isna().sum())
    resultado["status_outcome"] = sorted(status)
    resultado["codigo_sigilo_presente"] = bool(
        trabalho["codigo_municipio_ibge"].eq("5003900").any()
    )
    inelegiveis = trabalho.loc[~trabalho["elegivel_estimacao_principal"]]
    resultado["n_cabo_frio_2009_inelegivel"] = int(
        (
            inelegiveis["codigo_municipio_ibge"].eq("3300704")
            & inelegiveis["ano"].eq(2009)
        ).sum()
    )
    return resultado


def inventariar_covariaveis_disponiveis(amostra: pd.DataFrame) -> pd.DataFrame:
    """Classifica variáveis reais da amostra para uso diagnóstico D17."""
    linhas: list[dict[str, Any]] = []

    def adicionar(
        variavel: str,
        fonte: str,
        tipo: str,
        anos: str,
        uso: str,
        risco: str,
        decisao: str,
    ) -> None:
        if variavel not in amostra.columns:
            return
        linhas.append(
            {
                "variavel": variavel,
                "fonte": fonte,
                "tipo": tipo,
                "anos_disponiveis": anos,
                "missing": int(amostra[variavel].isna().sum()),
                "missing_pct": float(amostra[variavel].isna().mean() * 100),
                "uso_potencial": uso,
                "risco_pos_tratamento": risco,
                "decisao_D17": decisao,
            }
        )

    adicionar(
        "uf_codigo", "cadastro territorial", "ESTRUTURAL_FIXA", "fixa",
        "composição geográfica e efeito fixo apenas diagnóstico",
        "BAIXO", "USAR_DESCRITIVAMENTE_E_NO_OVERLAP",
    )
    adicionar(
        "municipio_fonte", "cadastro territorial", "ESTRUTURAL_FIXA", "fixa",
        "identificação e auditoria", "BAIXO", "NAO_USAR_COMO_PREDITOR",
    )
    adicionar(
        "status_territorial", "calendário territorial IBGE", "ESTRUTURAL_FIXA", "2007-2019",
        "qualidade/cobertura", "BAIXO", "USAR_APENAS_VALIDACAO",
    )
    for variavel in COVARIAVEIS_CEMPRE:
        adicionar(
            variavel,
            "CEMPRE/SIDRA",
            "VARIANTE_NO_TEMPO_PRE",
            "2007-2019",
            "nível municipal em baseline comum 2007",
            "ALTO se medida em/apos g; possível mediador/outcome",
            "USAR_SOMENTE_BASELINE_2007_DIAGNOSTICO",
        )
    for variavel in sorted(COVARIAVEIS_PROIBIDAS_AJUSTE):
        adicionar(
            variavel,
            "cadastro causal/exposição",
            "POS_TRATAMENTO",
            "fixa ou derivada de 2007-2019",
            "definição/auditoria do tratamento, nunca ajuste",
            "DETERMINA tratamento, coorte ou elegibilidade",
            "REJEITAR_COMO_COVARIAVEL",
        )
    return pd.DataFrame(linhas).sort_values(["tipo", "variavel"]).reset_index(drop=True)


def construir_baseline_comum(
    amostra: pd.DataFrame,
    covariaveis: Sequence[str],
    ano_base: int = ANO_BASE_COMUM,
) -> pd.DataFrame:
    """Materializa uma linha por município em ano comum anterior a todas as coortes."""
    proibidas = sorted(set(covariaveis) & COVARIAVEIS_PROIBIDAS_AJUSTE)
    if proibidas:
        raise ValueError(
            "covariável pós-tratamento/definidora do tratamento não permitida: "
            f"{proibidas}"
        )
    faltantes = sorted(set(covariaveis) - set(amostra.columns))
    if faltantes:
        raise ValueError(f"covariáveis ausentes: {faltantes}")
    if not covariaveis:
        raise ValueError("ao menos uma covariável pré-tratamento é necessária")

    coortes = amostra.loc[amostra["papel_causal"].eq(PAPEL_TRATADO), "coorte_g"].dropna()
    if coortes.empty or ano_base >= int(coortes.min()):
        raise ValueError("ano baseline deve ser estritamente anterior à primeira coorte")

    colunas = [
        "codigo_municipio_ibge", "papel_causal", "coorte_g", "uf_codigo",
        "municipio_fonte", *covariaveis,
    ]
    colunas = list(dict.fromkeys(colunas))
    faltantes_identidade = sorted(set(colunas) - set(amostra.columns))
    if faltantes_identidade:
        raise ValueError(f"colunas necessárias ao baseline ausentes: {faltantes_identidade}")
    base = amostra.loc[amostra["ano"].eq(ano_base), colunas].copy()
    base["codigo_municipio_ibge"] = _codigos(base)
    if base["codigo_municipio_ibge"].duplicated().any():
        raise ValueError("baseline comum não possui uma linha única por município")
    if base[covariaveis].isna().any().any():
        missing = base[covariaveis].isna().sum()
        raise ValueError(f"baseline comum contém missing: {missing[missing.gt(0)].to_dict()}")
    base["tratado"] = base["papel_causal"].eq(PAPEL_TRATADO)
    base["ano_baseline"] = ano_base
    base["macrorregiao"] = base["uf_codigo"].astype("string").map(UF_PARA_REGIAO)
    if base["macrorregiao"].isna().any():
        raise ValueError("UF sem mapeamento para macrorregião")
    return base.sort_values("codigo_municipio_ibge").reset_index(drop=True)


def standardized_mean_difference(
    tratados: pd.Series | Iterable[float],
    controles: pd.Series | Iterable[float],
) -> float:
    """Diferença de médias padronizada pelo desvio-padrão agrupado."""
    tratados_s = pd.Series(tratados, dtype="float64").dropna()
    controles_s = pd.Series(controles, dtype="float64").dropna()
    if len(tratados_s) < 2 or len(controles_s) < 2:
        return float("nan")
    variancia_agrupada = (tratados_s.var(ddof=1) + controles_s.var(ddof=1)) / 2.0
    diferenca = float(tratados_s.mean() - controles_s.mean())
    if variancia_agrupada == 0:
        return 0.0 if diferenca == 0 else float(np.sign(diferenca) * np.inf)
    return diferenca / float(np.sqrt(variancia_agrupada))


def balanco_descritivo_baseline(
    baseline: pd.DataFrame,
    covariaveis: Sequence[str],
) -> pd.DataFrame:
    """Resume níveis e SMD no baseline comum, sem excluir unidades."""
    linhas: list[dict[str, Any]] = []
    for variavel in covariaveis:
        tratados = baseline.loc[baseline["tratado"], variavel].astype(float)
        controles = baseline.loc[~baseline["tratado"], variavel].astype(float)
        linha: dict[str, Any] = {
            "variavel": variavel,
            "n_tratados": len(tratados),
            "n_controles": len(controles),
            "media_tratados": tratados.mean(),
            "mediana_tratados": tratados.median(),
            "desvio_padrao_tratados": tratados.std(ddof=1),
            "p10_tratados": tratados.quantile(0.10),
            "p25_tratados": tratados.quantile(0.25),
            "p75_tratados": tratados.quantile(0.75),
            "p90_tratados": tratados.quantile(0.90),
            "media_controles": controles.mean(),
            "mediana_controles": controles.median(),
            "desvio_padrao_controles": controles.std(ddof=1),
            "p10_controles": controles.quantile(0.10),
            "p25_controles": controles.quantile(0.25),
            "p75_controles": controles.quantile(0.75),
            "p90_controles": controles.quantile(0.90),
            "smd": standardized_mean_difference(tratados, controles),
        }
        linha["smd_absoluto"] = abs(linha["smd"])
        linhas.append(linha)
    return pd.DataFrame(linhas).sort_values("smd_absoluto", ascending=False).reset_index(drop=True)


def selecionar_periodos_pre(amostra: pd.DataFrame, coorte: int) -> pd.DataFrame:
    """Seleciona tratados da coorte e never-treated nos mesmos anos, somente k<0."""
    tratados = amostra.loc[
        amostra["papel_causal"].eq(PAPEL_TRATADO)
        & amostra["coorte_g"].eq(coorte)
        & amostra["ano"].lt(coorte)
        & amostra["elegivel_estimacao_principal"]
    ].copy()
    controles = amostra.loc[
        amostra["papel_causal"].eq(PAPEL_CONTROLE)
        & amostra["ano"].lt(coorte)
    ].copy()
    tratados["grupo"] = "TRATADOS_COORTE"
    controles["grupo"] = "CONTROLES_NEVER_TREATED"
    resultado = pd.concat([tratados, controles], ignore_index=True)
    resultado["coorte_referencia"] = int(coorte)
    resultado["tempo_relativo_pre"] = resultado["ano"] - int(coorte)
    if not resultado["tempo_relativo_pre"].lt(0).all():
        raise ValueError("seleção pré-tratamento contém k >= 0")
    return resultado


def _resumo_serie(valores: pd.Series) -> dict[str, float | int]:
    valores = pd.to_numeric(valores, errors="coerce").dropna()
    return {
        "n_unidades": int(len(valores)),
        "media": float(valores.mean()) if len(valores) else np.nan,
        "mediana": float(valores.median()) if len(valores) else np.nan,
        "desvio_padrao": float(valores.std(ddof=1)) if len(valores) > 1 else np.nan,
        "p10": float(valores.quantile(0.10)) if len(valores) else np.nan,
        "p25": float(valores.quantile(0.25)) if len(valores) else np.nan,
        "p75": float(valores.quantile(0.75)) if len(valores) else np.nan,
        "p90": float(valores.quantile(0.90)) if len(valores) else np.nan,
    }


def comparar_coorte_never_pre(
    amostra: pd.DataFrame,
    coorte: int,
    outcome: str = OUTCOME_PRIMARIO,
) -> pd.DataFrame:
    """Resume outcome pré-tratamento da coorte contra never-treated por k."""
    if outcome not in amostra.columns:
        raise ValueError(f"outcome ausente: {outcome}")
    base = selecionar_periodos_pre(amostra, coorte)
    linhas: list[dict[str, Any]] = []
    n_tratados_coorte = int(
        amostra.loc[
            amostra["papel_causal"].eq(PAPEL_TRATADO) & amostra["coorte_g"].eq(coorte),
            "codigo_municipio_ibge",
        ].nunique()
    )
    alerta = (
        "COORTE_PEQUENA_PRECISAO_LIMITADA" if n_tratados_coorte < 20 else "SEM_ALERTA_TAMANHO"
    )
    for (ano, k, grupo), parte in base.groupby(
        ["ano", "tempo_relativo_pre", "grupo"], sort=True
    ):
        linha = {
            "coorte_g": int(coorte),
            "ano": int(ano),
            "tempo_relativo_pre": int(k),
            "grupo": grupo,
            "alerta_tamanho_coorte": alerta,
        }
        linha.update(_resumo_serie(parte[outcome]))
        linhas.append(linha)
    return pd.DataFrame(linhas)


def diferencas_medias_pre_com_ic(
    amostra: pd.DataFrame,
    coorte: int,
    outcome: str = OUTCOME_PRIMARIO,
) -> pd.DataFrame:
    """Diferenças descritivas de médias e IC normal de Welch por k<0."""
    base = selecionar_periodos_pre(amostra, coorte)
    linhas: list[dict[str, Any]] = []
    for (ano, k), parte in base.groupby(["ano", "tempo_relativo_pre"], sort=True):
        tratados = pd.to_numeric(
            parte.loc[parte["grupo"].eq("TRATADOS_COORTE"), outcome], errors="coerce"
        ).dropna()
        controles = pd.to_numeric(
            parte.loc[parte["grupo"].eq("CONTROLES_NEVER_TREATED"), outcome], errors="coerce"
        ).dropna()
        diferenca = float(tratados.mean() - controles.mean())
        se = float(
            np.sqrt(
                (tratados.var(ddof=1) / len(tratados) if len(tratados) > 1 else 0.0)
                + (controles.var(ddof=1) / len(controles) if len(controles) > 1 else 0.0)
            )
        )
        linhas.append(
            {
                "coorte_g": int(coorte),
                "ano": int(ano),
                "tempo_relativo_pre": int(k),
                "n_tratados": int(len(tratados)),
                "n_controles": int(len(controles)),
                "media_tratados": float(tratados.mean()),
                "media_controles": float(controles.mean()),
                "diferenca_media": diferenca,
                "erro_padrao_welch": se,
                "ic95_inferior": diferenca - 1.96 * se,
                "ic95_superior": diferenca + 1.96 * se,
                "rotulo_inferencia": "DIAGNOSTICO_DESCRITIVO_NAO_CAUSAL",
            }
        )
    return pd.DataFrame(linhas)


def diagnostico_slopes_pre(
    amostra: pd.DataFrame,
    coorte: int,
    outcome: str = OUTCOME_PRIMARIO,
) -> pd.DataFrame:
    """Compara slopes lineares por município usando somente anos k<0."""
    base = selecionar_periodos_pre(amostra, coorte)
    trabalho = base[["grupo", "codigo_municipio_ibge", "ano", outcome]].dropna().copy()
    chaves = ["grupo", "codigo_municipio_ibge"]
    trabalho["x"] = trabalho["ano"].astype(float)
    trabalho["y"] = trabalho[outcome].astype(float)
    trabalho["x_centrado"] = trabalho["x"] - trabalho.groupby(chaves)["x"].transform("mean")
    trabalho["y_centrado"] = trabalho["y"] - trabalho.groupby(chaves)["y"].transform("mean")
    trabalho["numerador"] = trabalho["x_centrado"] * trabalho["y_centrado"]
    trabalho["denominador"] = trabalho["x_centrado"] ** 2
    slopes_df = (
        trabalho.groupby(chaves, as_index=False)
        .agg(
            n_periodos=("ano", "nunique"),
            numerador=("numerador", "sum"),
            denominador=("denominador", "sum"),
        )
    )
    slopes_df = slopes_df.loc[
        slopes_df["n_periodos"].ge(2) & slopes_df["denominador"].gt(0)
    ].copy()
    slopes_df["slope_pre"] = slopes_df["numerador"] / slopes_df["denominador"]
    linhas: list[dict[str, Any]] = []
    for grupo, parte in slopes_df.groupby("grupo"):
        media = float(parte["slope_pre"].mean())
        se = float(parte["slope_pre"].std(ddof=1) / np.sqrt(len(parte))) if len(parte) > 1 else np.nan
        linhas.append(
            {
                "coorte_g": int(coorte),
                "grupo": grupo,
                "n_unidades_com_slope": int(len(parte)),
                "slope_medio_pre": media,
                "erro_padrao": se,
                "ic95_inferior": media - 1.96 * se if pd.notna(se) else np.nan,
                "ic95_superior": media + 1.96 * se if pd.notna(se) else np.nan,
                "rotulo_inferencia": "DIAGNOSTICO_DE_PODER_LIMITADO",
            }
        )
    return pd.DataFrame(linhas)


def identificar_suporte_empirico(
    scores: pd.DataFrame,
    coluna_score: str = "propensity_score",
    coluna_tratado: str = "tratado",
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Marca o intervalo empírico comum; não remove nem seleciona unidades."""
    obrigatorias = {coluna_score, coluna_tratado}
    faltantes = obrigatorias - set(scores.columns)
    if faltantes:
        raise ValueError(f"scores sem colunas obrigatórias: {sorted(faltantes)}")
    tratados = scores.loc[scores[coluna_tratado].eq(True), coluna_score].dropna()  # noqa: E712
    controles = scores.loc[scores[coluna_tratado].eq(False), coluna_score].dropna()  # noqa: E712
    if tratados.empty or controles.empty:
        raise ValueError("diagnóstico de suporte exige tratados e controles")
    inferior = float(max(tratados.min(), controles.min()))
    superior = float(min(tratados.max(), controles.max()))
    if inferior > superior:
        raise ValueError("não há interseção empírica entre os scores dos grupos")
    resultado = scores.copy()
    resultado["em_suporte_empirico"] = resultado[coluna_score].between(inferior, superior)
    resultado["fora_suporte_empirico"] = ~resultado["em_suporte_empirico"]
    resumo = {
        "limite_inferior": inferior,
        "limite_superior": superior,
        "n_tratados": int(len(tratados)),
        "n_controles": int(len(controles)),
        "n_tratados_fora": int(
            (~resultado.loc[resultado[coluna_tratado], "em_suporte_empirico"]).sum()
        ),
        "n_controles_fora": int(
            (~resultado.loc[~resultado[coluna_tratado], "em_suporte_empirico"]).sum()
        ),
    }
    return resultado, resumo


def ajustar_propensity_diagnostico(
    baseline: pd.DataFrame,
    covariaveis_numericas: Sequence[str],
    covariaveis_categoricas: Sequence[str] = ("macrorregiao",),
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Ajusta regressão logística simples apenas para diagnosticar overlap."""
    if not covariaveis_numericas:
        raise ValueError("modelo diagnóstico exige covariável numérica pré-tratamento")
    proibidas = sorted(
        (set(covariaveis_numericas) | set(covariaveis_categoricas))
        & COVARIAVEIS_PROIBIDAS_AJUSTE
    )
    if proibidas:
        raise ValueError(f"covariável pós-tratamento não permitida no overlap: {proibidas}")
    colunas = list(covariaveis_numericas) + list(covariaveis_categoricas)
    faltantes = sorted(set(colunas + ["tratado", "codigo_municipio_ibge"]) - set(baseline.columns))
    if faltantes:
        raise ValueError(f"baseline sem colunas necessárias ao overlap: {faltantes}")
    if baseline[colunas].isna().any().any():
        raise ValueError("overlap diagnóstico não aceita missing nas covariáveis")

    numericas = baseline[list(covariaveis_numericas)].astype(float).copy()
    numericas = np.log1p(numericas.clip(lower=0))
    scaler = StandardScaler()
    matriz_num = pd.DataFrame(
        scaler.fit_transform(numericas),
        columns=[f"log1p_z__{c}" for c in covariaveis_numericas],
        index=baseline.index,
    )
    matriz_cat = pd.get_dummies(
        baseline[list(covariaveis_categoricas)].astype("string"),
        prefix=list(covariaveis_categoricas),
        drop_first=True,
        dtype=float,
    )
    matriz = pd.concat([matriz_num, matriz_cat], axis=1)
    alvo = baseline["tratado"].astype(int)
    modelo = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000)
    modelo.fit(matriz, alvo)

    scores = baseline[
        ["codigo_municipio_ibge", "tratado", "papel_causal", "coorte_g", "uf_codigo", "macrorregiao"]
    ].copy()
    scores["propensity_score"] = modelo.predict_proba(matriz)[:, 1]
    scores, suporte = identificar_suporte_empirico(scores)
    coeficientes = pd.DataFrame(
        {"termo": matriz.columns, "coeficiente_logit": modelo.coef_[0]}
    ).sort_values("coeficiente_logit", key=lambda s: s.abs(), ascending=False)
    metadados: dict[str, Any] = {
        **suporte,
        "modelo": "regressao_logistica_L2_diagnostica",
        "ano_baseline": int(baseline["ano_baseline"].iloc[0]),
        "covariaveis_numericas": list(covariaveis_numericas),
        "covariaveis_categoricas": list(covariaveis_categoricas),
        "propensity_score_diagnostico_nao_matching": True,
    }
    return scores, coeficientes.reset_index(drop=True), metadados


def resumir_overlap_por_segmento(
    scores: pd.DataFrame,
    segmento: str,
) -> pd.DataFrame:
    """Resume caudas e suporte por coorte, região ou porte, sem filtrar."""
    if segmento not in scores.columns:
        raise ValueError(f"segmento ausente nos scores: {segmento}")
    return (
        scores.groupby([segmento, "tratado"], dropna=False, as_index=False)
        .agg(
            n_unidades=("codigo_municipio_ibge", "nunique"),
            score_min=("propensity_score", "min"),
            score_p10=("propensity_score", lambda s: s.quantile(0.10)),
            score_mediana=("propensity_score", "median"),
            score_p90=("propensity_score", lambda s: s.quantile(0.90)),
            score_max=("propensity_score", "max"),
            n_fora_suporte=("fora_suporte_empirico", "sum"),
        )
    )


def classificar_spillover_controles(
    amostra: pd.DataFrame,
    distancias: pd.DataFrame,
) -> pd.DataFrame:
    """Anexa classificação temporária de spillover sem mudar ``papel_causal``."""
    obrigatorias = {
        "codigo_municipio_ibge", "distancia_sedes_km", "fl_ate_25_km",
        "fl_ate_50_km", "fl_ate_100_km",
    }
    faltantes = obrigatorias - set(distancias.columns)
    if faltantes:
        raise ValueError(f"diagnóstico espacial sem colunas: {sorted(faltantes)}")
    resultado = amostra.copy()
    resultado["_codigo_merge_d17"] = _codigos(resultado)
    espacial = distancias[list(obrigatorias)].copy()
    espacial["_codigo_merge_d17"] = _codigos(espacial)
    espacial = espacial.drop(columns="codigo_municipio_ibge")
    if espacial["_codigo_merge_d17"].duplicated().any():
        raise ValueError("diagnóstico espacial duplicado por município")
    papel_original = resultado["papel_causal"].copy()
    resultado = resultado.merge(
        espacial, on="_codigo_merge_d17", how="left", validate="many_to_one", sort=False
    )
    resultado = resultado.drop(columns="_codigo_merge_d17")
    resultado["classificacao_spillover_diagnostica"] = "TRATADO_NAO_CLASSIFICADO_COMO_CONTROLE"
    controle = resultado["papel_causal"].eq(PAPEL_CONTROLE)
    resultado.loc[controle, "classificacao_spillover_diagnostica"] = "CONTROLE_NEVER_TREATED"
    resultado.loc[
        controle & resultado["fl_ate_100_km"].fillna(False),
        "classificacao_spillover_diagnostica",
    ] = "CONTROLE_NEVER_TREATED_POTENCIALMENTE_EXPOSTO_A_SPILLOVER"
    if not resultado["papel_causal"].reset_index(drop=True).equals(papel_original.reset_index(drop=True)):
        raise ValueError("classificação diagnóstica alterou papel_causal")
    return resultado


def diagnosticar_cobertura_cabo_frio(amostra: pd.DataFrame) -> pd.DataFrame:
    """Explicita suporte de calendário e perda única pela máscara Cabo Frio/2009."""
    diagnostico = d16.diagnostico_janelas(amostra).rename(
        columns={
            "n_tratados_populacao": "n_populacao_calendario",
            "n_tratados_janela_completa_elegivel": "n_janela_completa_elegivel",
        }
    )
    diagnostico["perda_cabo_frio"] = (
        diagnostico["n_populacao_calendario"]
        - diagnostico["n_janela_completa_elegivel"]
    )
    inelegiveis = amostra.loc[~amostra["elegivel_estimacao_principal"]]
    somente_cabo = (
        len(inelegiveis) == 1
        and _codigos(inelegiveis).eq("3300704").all()
        and inelegiveis["ano"].eq(2009).all()
    )
    if not somente_cabo:
        raise ValueError("máscara de elegibilidade não é exclusivamente Cabo Frio/2009")
    diagnostico["unica_mascara_observacional"] = "CABO_FRIO_2009"
    return diagnostico


def composicao_geografica(baseline: pd.DataFrame) -> pd.DataFrame:
    """Conta unidades por papel, macrorregião, UF e coorte no baseline comum."""
    return (
        baseline.groupby(
            ["papel_causal", "macrorregiao", "uf_codigo", "coorte_g"],
            dropna=False,
            as_index=False,
        )
        .agg(n_municipios=("codigo_municipio_ibge", "nunique"))
    )


def diagnostico_influencia_baseline(
    baseline: pd.DataFrame,
    variavel: str = OUTCOME_PRIMARIO,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lista extremos e concentração no baseline sem excluir observações."""
    if variavel not in baseline.columns:
        raise ValueError(f"variável ausente no baseline: {variavel}")
    trabalho = baseline.sort_values(variavel, ascending=False).copy()
    trabalho["participacao_no_total_grupo"] = trabalho[variavel] / trabalho.groupby(
        "papel_causal"
    )[variavel].transform("sum")
    trabalho["percentil_no_grupo"] = trabalho.groupby("papel_causal")[variavel].rank(pct=True)
    extremos = trabalho.loc[trabalho["percentil_no_grupo"].ge(0.99)].copy()
    linhas: list[dict[str, Any]] = []
    for papel, parte in trabalho.groupby("papel_causal"):
        ordenada = parte.sort_values(variavel, ascending=False)
        total = float(ordenada[variavel].sum())
        for n in (1, 5, 10):
            linhas.append(
                {
                    "papel_causal": papel,
                    "top_n": n,
                    "participacao_top_n": float(ordenada.head(n)[variavel].sum() / total),
                    "n_unidades_grupo": int(len(ordenada)),
                }
            )
    return extremos, pd.DataFrame(linhas)
