"""D18 — reavaliação do gate pré-estimação e ameaças de identificação.

Este módulo contém apenas diagnósticos descritivos com informação anterior ao
tratamento, características estruturais e metadados congelados do desenho.
Ele não estima ATT, event-study causal, TWFE, pesos, matching ou trimming e não
altera a amostra D15.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

import diagnostica_pre_estimacao as d17


PAPEL_TRATADO = d17.PAPEL_TRATADO
PAPEL_CONTROLE = d17.PAPEL_CONTROLE
OUTCOME_PRIMARIO = d17.OUTCOME_PRIMARIO
COORTES = d17.COORTES
ROTULO_LOG_DIAGNOSTICO = "APENAS_DIAGNOSTICO_NAO_ALTERA_OUTCOME_PRINCIPAL"
ROTULO_INFLUENCIA = "ANALISE_DE_INFLUENCIA_PRE_TRATAMENTO__NAO_REGRA_DE_EXCLUSAO"
ROTULO_SPILLOVER = "CENARIO_HIPOTETICO_DE_SENSIBILIDADE__NAO_AMOSTRA_PRINCIPAL"


def _codigos(frame: pd.DataFrame) -> pd.Series:
    return frame["codigo_municipio_ibge"].astype("string").str.zfill(7)


def selecionar_painel_pre_coorte(
    amostra: pd.DataFrame,
    coorte: int,
) -> pd.DataFrame:
    """Seleciona tratados de ``coorte`` e never-treated usando somente ``t < g``."""
    tratados = amostra.loc[
        amostra["papel_causal"].eq(PAPEL_TRATADO)
        & amostra["coorte_g"].eq(coorte)
        & amostra["ano"].lt(coorte)
        & amostra["elegivel_estimacao_principal"].fillna(False)
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
    if resultado.empty:
        raise ValueError(f"nenhuma observação pré-tratamento para a coorte {coorte}")
    if not resultado["ano"].lt(coorte).all() or not resultado["tempo_relativo_pre"].lt(0).all():
        raise ValueError("diagnóstico D18 recebeu período contemporâneo ou pós-tratamento")
    grupos = set(resultado["grupo"])
    if grupos != {"TRATADOS_COORTE", "CONTROLES_NEVER_TREATED"}:
        raise ValueError(f"comparação pré exige tratados e never-treated; observado={grupos}")
    return resultado.sort_values(["grupo", "codigo_municipio_ibge", "ano"]).reset_index(drop=True)


def classificar_suporte_att(
    scores: pd.DataFrame,
    coluna_score: str = "propensity_score",
    coluna_tratado: str = "tratado",
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Separa falta de suporte para tratados das caudas excedentes de controles.

    A classificação é descritiva e não remove unidades. Para ATT, controles em
    regiões onde não há tratados não implicam, por si, falta de suporte para os
    tratados; tratados além do alcance observado dos controles são o caso
    diretamente relevante.
    """
    faltantes = {coluna_score, coluna_tratado} - set(scores.columns)
    if faltantes:
        raise ValueError(f"scores sem colunas obrigatórias: {sorted(faltantes)}")
    resultado = scores.copy()
    tratado = resultado[coluna_tratado].astype(bool)
    scores_t = pd.to_numeric(resultado.loc[tratado, coluna_score], errors="coerce").dropna()
    scores_c = pd.to_numeric(resultado.loc[~tratado, coluna_score], errors="coerce").dropna()
    if scores_t.empty or scores_c.empty:
        raise ValueError("suporte ATT exige tratados e controles com score")

    min_t, max_t = float(scores_t.min()), float(scores_t.max())
    min_c, max_c = float(scores_c.min()), float(scores_c.max())
    s = pd.to_numeric(resultado[coluna_score], errors="coerce")
    resultado["status_suporte_att"] = ""
    resultado.loc[tratado & s.lt(min_c), "status_suporte_att"] = "TRATADO_ABAIXO_MIN_CONTROLES"
    resultado.loc[tratado & s.gt(max_c), "status_suporte_att"] = "TRATADO_ACIMA_MAX_CONTROLES"
    resultado.loc[
        tratado & s.between(min_c, max_c), "status_suporte_att"
    ] = "TRATADO_DENTRO_FAIXA_CONTROLES"
    resultado.loc[(~tratado) & s.lt(min_t), "status_suporte_att"] = "CONTROLE_ABAIXO_MIN_TRATADOS"
    resultado.loc[(~tratado) & s.gt(max_t), "status_suporte_att"] = "CONTROLE_ACIMA_MAX_TRATADOS"
    resultado.loc[
        (~tratado) & s.between(min_t, max_t), "status_suporte_att"
    ] = "CONTROLE_NA_FAIXA_TRATADOS"
    if resultado["status_suporte_att"].eq("").any():
        raise ValueError("há score ausente ou não classificável")

    falta_t = resultado["status_suporte_att"].isin(
        ["TRATADO_ABAIXO_MIN_CONTROLES", "TRATADO_ACIMA_MAX_CONTROLES"]
    )
    cauda_c = resultado["status_suporte_att"].isin(
        ["CONTROLE_ABAIXO_MIN_TRATADOS", "CONTROLE_ACIMA_MAX_TRATADOS"]
    )
    resultado["implicacao_att"] = "DENTRO_DA_FAIXA_EMPIRICA_RELEVANTE"
    resultado.loc[falta_t, "implicacao_att"] = "FALTA_DE_SUPORTE_EMPIRICO_PARA_TRATADO"
    resultado.loc[cauda_c, "implicacao_att"] = (
        "CAUDA_DE_CONTROLES_NAO_E_FALTA_DE_SUPORTE_DO_TRATADO"
    )
    resumo: dict[str, float | int] = {
        "score_min_tratados": min_t,
        "score_max_tratados": max_t,
        "score_min_controles": min_c,
        "score_max_controles": max_c,
        "n_tratados_abaixo_min_controles": int((tratado & s.lt(min_c)).sum()),
        "n_tratados_acima_max_controles": int((tratado & s.gt(max_c)).sum()),
        "n_controles_abaixo_min_tratados": int(((~tratado) & s.lt(min_t)).sum()),
        "n_controles_acima_max_tratados": int(((~tratado) & s.gt(max_t)).sum()),
        "n_tratados_dentro_faixa_controles": int((tratado & s.between(min_c, max_c)).sum()),
        "n_controles_na_faixa_tratados": int(((~tratado) & s.between(min_t, max_t)).sum()),
    }
    return resultado, resumo


def nearest_support_descritivo(
    baseline: pd.DataFrame,
    scores_classificados: pd.DataFrame,
    covariaveis: Sequence[str],
    k_vizinhos: int = 5,
) -> pd.DataFrame:
    """Descreve vizinhos de tratados sem suporte em covariáveis baseline padronizadas."""
    if k_vizinhos < 1:
        raise ValueError("k_vizinhos deve ser positivo")
    faltantes = set(covariaveis) - set(baseline.columns)
    if faltantes:
        raise ValueError(f"covariáveis ausentes no baseline: {sorted(faltantes)}")
    base = baseline.copy()
    base["codigo_municipio_ibge"] = _codigos(base)
    scores = scores_classificados.copy()
    scores["codigo_municipio_ibge"] = _codigos(scores)
    base = base.merge(
        scores[["codigo_municipio_ibge", "propensity_score", "status_suporte_att", "implicacao_att"]],
        on="codigo_municipio_ibge",
        how="inner",
        validate="one_to_one",
    )
    numericas = np.log1p(base[list(covariaveis)].astype(float).clip(lower=0))
    matriz = StandardScaler().fit_transform(numericas)
    matriz = pd.DataFrame(matriz, index=base.index, columns=list(covariaveis))
    if "macrorregiao" in base.columns:
        dummies = pd.get_dummies(base["macrorregiao"].astype("string"), prefix="regiao", dtype=float)
        matriz = pd.concat([matriz, dummies], axis=1)

    mask_t = base["implicacao_att"].eq("FALTA_DE_SUPORTE_EMPIRICO_PARA_TRATADO")
    mask_c = base["papel_causal"].eq(PAPEL_CONTROLE)
    if not mask_t.any():
        return pd.DataFrame()
    controles = base.loc[mask_c].copy()
    x_controles = matriz.loc[mask_c].to_numpy(dtype=float)
    linhas: list[dict[str, Any]] = []
    for indice, tratado in base.loc[mask_t].iterrows():
        distancias = np.sqrt(((x_controles - matriz.loc[indice].to_numpy(dtype=float)) ** 2).sum(axis=1))
        ordem = np.argsort(distancias)[: min(k_vizinhos, len(controles))]
        vizinhos = controles.iloc[ordem]
        linha: dict[str, Any] = {
            "codigo_municipio_ibge": tratado["codigo_municipio_ibge"],
            "municipio": tratado.get("municipio_fonte", pd.NA),
            "uf": tratado.get("uf_codigo", pd.NA),
            "coorte_g": tratado.get("coorte_g", pd.NA),
            "propensity_score": tratado["propensity_score"],
            "status_suporte_att": tratado["status_suporte_att"],
            "codigo_controle_mais_proximo": vizinhos.iloc[0]["codigo_municipio_ibge"],
            "municipio_controle_mais_proximo": vizinhos.iloc[0].get("municipio_fonte", pd.NA),
            "score_controle_mais_proximo": vizinhos.iloc[0]["propensity_score"],
            "distancia_padronizada_mais_proximo": float(distancias[ordem[0]]),
            "distancia_padronizada_media_k": float(distancias[ordem].mean()),
            "k_vizinhos": int(len(ordem)),
            "rotulo_uso": "NEAREST_SUPPORT_DESCRITIVO__NAO_MATCHING_NAO_TRIMMING",
        }
        for covariavel in covariaveis:
            linha[f"tratado__{covariavel}"] = tratado[covariavel]
            linha[f"controle_mais_proximo__{covariavel}"] = vizinhos.iloc[0][covariavel]
        linhas.append(linha)
    return pd.DataFrame(linhas).sort_values("propensity_score", ascending=False).reset_index(drop=True)


def normalizar_indice_g_menos_1(
    painel_pre: pd.DataFrame,
    coorte: int,
    outcome: str = OUTCOME_PRIMARIO,
) -> pd.DataFrame:
    """Cria índice diagnóstico com ``g-1 = 100`` sem usar qualquer período pós."""
    resultado = painel_pre.copy()
    if not resultado["ano"].lt(coorte).all():
        raise ValueError("normalização g-1 recebeu período não pré-tratamento")
    resultado["codigo_municipio_ibge"] = _codigos(resultado)
    base = resultado.loc[
        resultado["ano"].eq(coorte - 1), ["codigo_municipio_ibge", outcome]
    ].rename(columns={outcome: "outcome_g_menos_1"})
    if base["codigo_municipio_ibge"].duplicated().any():
        raise ValueError("g-1 duplicado por município")
    resultado = resultado.merge(base, on="codigo_municipio_ibge", how="left", validate="many_to_one")
    denominador = pd.to_numeric(resultado["outcome_g_menos_1"], errors="coerce")
    resultado["indice_g_menos_1"] = np.where(
        denominador.gt(0), 100.0 * pd.to_numeric(resultado[outcome], errors="coerce") / denominador, np.nan
    )
    resultado["normalizacao_valida"] = denominador.gt(0)
    resultado["rotulo_uso_indice"] = "INDICE_RELATIVO_DIAGNOSTICO_G_MENOS_1_IGUAL_100"
    return resultado


def _slopes_por_unidade(
    painel_pre: pd.DataFrame,
    outcome: str,
    transformacao: str = "nivel",
) -> pd.DataFrame:
    trabalho = painel_pre[["grupo", "codigo_municipio_ibge", "ano", outcome]].copy()
    trabalho["y"] = pd.to_numeric(trabalho[outcome], errors="coerce")
    if transformacao == "log1p":
        if trabalho["y"].lt(0).any():
            raise ValueError("log1p não definido para outcome negativo")
        trabalho["y"] = np.log1p(trabalho["y"])
    elif transformacao != "nivel":
        raise ValueError(f"transformação desconhecida: {transformacao}")
    trabalho = trabalho.dropna(subset=["y"])
    chaves = ["grupo", "codigo_municipio_ibge"]
    trabalho["x"] = trabalho["ano"].astype(float)
    trabalho["x_c"] = trabalho["x"] - trabalho.groupby(chaves)["x"].transform("mean")
    trabalho["y_c"] = trabalho["y"] - trabalho.groupby(chaves)["y"].transform("mean")
    trabalho["xy"] = trabalho["x_c"] * trabalho["y_c"]
    trabalho["xx"] = trabalho["x_c"] ** 2
    slopes = trabalho.groupby(chaves, as_index=False).agg(
        n_periodos=("ano", "nunique"), numerador=("xy", "sum"), denominador=("xx", "sum")
    )
    slopes = slopes.loc[slopes["n_periodos"].ge(2) & slopes["denominador"].gt(0)].copy()
    slopes["slope"] = slopes["numerador"] / slopes["denominador"]
    slopes["transformacao"] = transformacao
    return slopes


def _mudanca_percentual_por_unidade(
    painel_pre: pd.DataFrame,
    coorte: int,
    outcome: str,
) -> pd.DataFrame:
    trabalho = painel_pre.copy()
    trabalho["codigo_municipio_ibge"] = _codigos(trabalho)
    finais = trabalho.loc[trabalho["ano"].eq(coorte - 1), ["codigo_municipio_ibge", outcome]].rename(
        columns={outcome: "valor_final"}
    )
    iniciais = (
        trabalho.sort_values("ano")
        .groupby(["grupo", "codigo_municipio_ibge"], as_index=False)
        .first()[["grupo", "codigo_municipio_ibge", "ano", outcome]]
        .rename(columns={"ano": "ano_inicial", outcome: "valor_inicial"})
    )
    resultado = iniciais.merge(finais, on="codigo_municipio_ibge", how="inner", validate="one_to_one")
    resultado["mudanca_percentual"] = np.where(
        resultado["valor_inicial"].gt(0),
        100.0 * (resultado["valor_final"] / resultado["valor_inicial"] - 1.0),
        np.nan,
    )
    return resultado


def resumir_tendencias_escala(
    amostra: pd.DataFrame,
    coortes: Sequence[int] = COORTES,
    outcome: str = OUTCOME_PRIMARIO,
) -> pd.DataFrame:
    """Compara slopes em nível/log e mudança percentual usando somente o pré."""
    linhas: list[dict[str, Any]] = []
    for coorte in coortes:
        painel = selecionar_painel_pre_coorte(amostra, int(coorte))
        slopes_nivel = _slopes_por_unidade(painel, outcome, "nivel")
        slopes_log = _slopes_por_unidade(painel, outcome, "log1p")
        mudancas = _mudanca_percentual_por_unidade(painel, int(coorte), outcome)
        medias_nivel = slopes_nivel.groupby("grupo")["slope"].mean()
        medias_log = slopes_log.groupby("grupo")["slope"].mean()
        medias_pct = mudancas.groupby("grupo")["mudanca_percentual"].mean()
        st = float(medias_nivel["TRATADOS_COORTE"])
        sc = float(medias_nivel["CONTROLES_NEVER_TREATED"])
        slt = float(medias_log["TRATADOS_COORTE"])
        slc = float(medias_log["CONTROLES_NEVER_TREATED"])
        diferenca_log = slt - slc
        if np.sign(st - sc) != np.sign(diferenca_log) and not np.isclose(diferenca_log, 0):
            diagnostico = "SINAL_DIVERGENCIA_MUDA_APOS_RETIRAR_ESCALA"
        elif abs(diferenca_log) < 0.02:
            diagnostico = "DIVERGENCIA_LOG_PEQUENA_MAS_NAO_TESTE_DE_PARALLEL_TRENDS"
        else:
            diagnostico = "DIVERGENCIA_PERSISTE_EM_LOG_COM_MAGNITUDE_DESCRITIVA"
        linhas.append(
            {
                "coorte_g": int(coorte),
                "n_tratados": int(painel.loc[painel["grupo"].eq("TRATADOS_COORTE"), "codigo_municipio_ibge"].nunique()),
                "slope_nivel_tratados": st,
                "slope_nivel_controles": sc,
                "diferenca_slope_nivel": st - sc,
                "slope_log_tratados": slt,
                "slope_log_controles": slc,
                "diferenca_slope_log": diferenca_log,
                "mudanca_percentual_tratados": float(medias_pct.get("TRATADOS_COORTE", np.nan)),
                "mudanca_percentual_controles": float(medias_pct.get("CONTROLES_NEVER_TREATED", np.nan)),
                "diagnostico": diagnostico,
                "uso_log1p": ROTULO_LOG_DIAGNOSTICO,
                "rotulo_inferencia": "DESCRITIVO_NAO_TESTE_DE_TENDENCIAS_PARALELAS",
            }
        )
    return pd.DataFrame(linhas)


def calcular_primeiras_diferencas(
    painel_pre: pd.DataFrame,
    outcome: str = OUTCOME_PRIMARIO,
) -> pd.DataFrame:
    """Calcula ``Delta Y_it`` apenas entre anos pré consecutivos da mesma unidade."""
    trabalho = painel_pre.copy()
    chaves = ["grupo", "codigo_municipio_ibge"]
    trabalho = trabalho.sort_values([*chaves, "ano"])
    trabalho["ano_anterior"] = trabalho.groupby(chaves)["ano"].shift(1)
    trabalho["outcome_anterior"] = trabalho.groupby(chaves)[outcome].shift(1)
    trabalho["intervalo_anos"] = trabalho["ano"] - trabalho["ano_anterior"]
    trabalho["delta_outcome"] = pd.to_numeric(trabalho[outcome], errors="coerce") - pd.to_numeric(
        trabalho["outcome_anterior"], errors="coerce"
    )
    trabalho = trabalho.loc[trabalho["intervalo_anos"].eq(1)].copy()
    if not trabalho["tempo_relativo_pre"].lt(0).all():
        raise ValueError("primeiras diferenças contêm período não pré-tratamento")
    trabalho["rotulo_inferencia"] = "INCERTEZA_DESCRITIVA_NAO_P_VALOR_DE_GATE"
    return trabalho


def resumir_primeiras_diferencas(
    amostra: pd.DataFrame,
    coortes: Sequence[int] = COORTES,
    outcome: str = OUTCOME_PRIMARIO,
) -> pd.DataFrame:
    """Resume distribuições de primeiras diferenças e incerteza descritiva."""
    linhas: list[dict[str, Any]] = []
    for coorte in coortes:
        deltas = calcular_primeiras_diferencas(selecionar_painel_pre_coorte(amostra, int(coorte)), outcome)
        tratados = deltas.loc[deltas["grupo"].eq("TRATADOS_COORTE"), "delta_outcome"].dropna()
        controles = deltas.loc[deltas["grupo"].eq("CONTROLES_NEVER_TREATED"), "delta_outcome"].dropna()
        medias_unidade = (
            deltas.groupby(["grupo", "codigo_municipio_ibge"], as_index=False)["delta_outcome"]
            .mean()
        )
        medias_unidade_t = medias_unidade.loc[
            medias_unidade["grupo"].eq("TRATADOS_COORTE"), "delta_outcome"
        ]
        medias_unidade_c = medias_unidade.loc[
            medias_unidade["grupo"].eq("CONTROLES_NEVER_TREATED"), "delta_outcome"
        ]
        diferenca = float(tratados.mean() - controles.mean())
        se = float(
            np.sqrt(
                medias_unidade_t.var(ddof=1) / len(medias_unidade_t)
                + medias_unidade_c.var(ddof=1) / len(medias_unidade_c)
            )
        )
        linhas.append(
            {
                "coorte_g": int(coorte),
                "n_deltas_tratados": int(len(tratados)),
                "n_deltas_controles": int(len(controles)),
                "n_unidades_tratados": int(len(medias_unidade_t)),
                "n_unidades_controles": int(len(medias_unidade_c)),
                "media_tratados": float(tratados.mean()),
                "mediana_tratados": float(tratados.median()),
                "p10_tratados": float(tratados.quantile(0.10)),
                "p25_tratados": float(tratados.quantile(0.25)),
                "p75_tratados": float(tratados.quantile(0.75)),
                "p90_tratados": float(tratados.quantile(0.90)),
                "media_controles": float(controles.mean()),
                "mediana_controles": float(controles.median()),
                "p10_controles": float(controles.quantile(0.10)),
                "p25_controles": float(controles.quantile(0.25)),
                "p75_controles": float(controles.quantile(0.75)),
                "p90_controles": float(controles.quantile(0.90)),
                "diferenca_media": diferenca,
                "smd_primeiras_diferencas": d17.standardized_mean_difference(tratados, controles),
                "erro_padrao_descritivo_por_unidade": se,
                "ic95_descritivo_inferior": diferenca - 1.96 * se,
                "ic95_descritivo_superior": diferenca + 1.96 * se,
                "rotulo_inferencia": "INCERTEZA_DESCRITIVA_NAO_P_VALOR_DE_GATE",
            }
        )
    return pd.DataFrame(linhas)


def diagnostico_influencia_pre(
    amostra: pd.DataFrame,
    coortes: Sequence[int] = COORTES,
    outcome: str = OUTCOME_PRIMARIO,
) -> pd.DataFrame:
    """Recalcula slopes pré omitindo grandes tratados apenas no diagnóstico."""
    baseline_tratados = amostra.loc[
        amostra["papel_causal"].eq(PAPEL_TRATADO) & amostra["ano"].eq(2007),
        ["codigo_municipio_ibge", outcome],
    ].copy()
    baseline_tratados["codigo_municipio_ibge"] = _codigos(baseline_tratados)
    ranking = baseline_tratados.sort_values(outcome, ascending=False)["codigo_municipio_ibge"].tolist()
    cenarios = {
        "SEM_OMISSAO": set(),
        "OMITE_MAIOR_1": set(ranking[:1]),
        "OMITE_TOP_5": set(ranking[:5]),
        "OMITE_TOP_10": set(ranking[:10]),
    }
    linhas: list[dict[str, Any]] = []
    for coorte in coortes:
        painel = selecionar_painel_pre_coorte(amostra, int(coorte))
        painel["codigo_municipio_ibge"] = _codigos(painel)
        n_original = int(painel.loc[painel["grupo"].eq("TRATADOS_COORTE"), "codigo_municipio_ibge"].nunique())
        for cenario, omitir in cenarios.items():
            diagnostico = painel.loc[
                ~(
                    painel["grupo"].eq("TRATADOS_COORTE")
                    & painel["codigo_municipio_ibge"].isin(omitir)
                )
            ].copy()
            slopes = _slopes_por_unidade(diagnostico, outcome, "nivel")
            medias = slopes.groupby("grupo")["slope"].mean()
            n_diag = int(diagnostico.loc[diagnostico["grupo"].eq("TRATADOS_COORTE"), "codigo_municipio_ibge"].nunique())
            linhas.append(
                {
                    "coorte_g": int(coorte),
                    "cenario": cenario,
                    "n_tratados_original": n_original,
                    "n_tratados_diagnostico": n_diag,
                    "n_tratados_omitidos_apenas_diagnostico": n_original - n_diag,
                    "slope_nivel_tratados": float(medias.get("TRATADOS_COORTE", np.nan)),
                    "slope_nivel_controles": float(medias.get("CONTROLES_NEVER_TREATED", np.nan)),
                    "diferenca_slope_nivel": float(
                        medias.get("TRATADOS_COORTE", np.nan) - medias.get("CONTROLES_NEVER_TREATED", np.nan)
                    ),
                    "rotulo_uso": ROTULO_INFLUENCIA,
                }
            )
    resultado = pd.DataFrame(linhas)
    referencia = resultado.loc[resultado["cenario"].eq("SEM_OMISSAO"), ["coorte_g", "diferenca_slope_nivel"]].rename(
        columns={"diferenca_slope_nivel": "diferenca_sem_omissao"}
    )
    resultado = resultado.merge(referencia, on="coorte_g", how="left", validate="many_to_one")
    resultado["mudanca_diferenca_vs_sem_omissao"] = (
        resultado["diferenca_slope_nivel"] - resultado["diferenca_sem_omissao"]
    )
    return resultado


def cenarios_spillover_hipoteticos(
    amostra: pd.DataFrame,
    distancias: pd.DataFrame,
    arranjos: pd.DataFrame,
) -> pd.DataFrame:
    """Quantifica controles remanescentes sem alterar o papel causal original."""
    papel_original = amostra["papel_causal"].copy(deep=True)
    unidades = amostra.sort_values("ano").drop_duplicates("codigo_municipio_ibge").copy()
    unidades["codigo_municipio_ibge"] = _codigos(unidades)
    controles = unidades.loc[unidades["papel_causal"].eq(PAPEL_CONTROLE)].copy()
    tratados = unidades.loc[unidades["papel_causal"].eq(PAPEL_TRATADO)].copy()
    controles["macrorregiao"] = controles["uf_codigo"].astype("string").map(d17.UF_PARA_REGIAO)

    dist = distancias.copy()
    dist["codigo_municipio_ibge"] = _codigos(dist)
    arr = arranjos.copy()
    arr["codigo_municipio_ibge"] = _codigos(arr)
    flags = dist[["codigo_municipio_ibge", "fl_ate_25_km", "fl_ate_50_km", "fl_ate_100_km"]].merge(
        arr[["codigo_municipio_ibge", "fl_mesmo_arranjo_populacional_fase_ii"]],
        on="codigo_municipio_ibge",
        how="outer",
        validate="one_to_one",
    )
    controles = controles.merge(flags, on="codigo_municipio_ibge", how="left", validate="one_to_one")
    mapa = {
        "ATE_25_KM": "fl_ate_25_km",
        "ATE_50_KM": "fl_ate_50_km",
        "ATE_100_KM": "fl_ate_100_km",
        "MESMO_ARRANJO_POPULACIONAL": "fl_mesmo_arranjo_populacional_fase_ii",
    }
    coortes = sorted(int(v) for v in tratados["coorte_g"].dropna().unique())
    linhas: list[dict[str, Any]] = []
    n_original = int(len(controles))
    for cenario, coluna in mapa.items():
        contaminado = controles[coluna].fillna(False).astype(bool)
        remanescentes = controles.loc[~contaminado].copy()
        por_regiao = remanescentes.groupby("macrorregiao").size().to_dict()
        for coorte in coortes:
            n_tratados = int(tratados["coorte_g"].eq(coorte).sum())
            for regiao in ["TOTAL", *sorted(por_regiao)]:
                n_regiao = len(remanescentes) if regiao == "TOTAL" else int(por_regiao[regiao])
                linhas.append(
                    {
                        "cenario": cenario,
                        "coorte_g": coorte,
                        "macrorregiao": regiao,
                        "n_controles_original": n_original,
                        "n_potencialmente_contaminados": int(contaminado.sum()),
                        "n_remanescentes": int(len(remanescentes)),
                        "n_remanescentes_regiao": int(n_regiao),
                        "proporcao_regional_remanescente": float(n_regiao / len(remanescentes)) if len(remanescentes) else np.nan,
                        "n_tratados_coorte": n_tratados,
                        "controles_remanescentes_por_tratado_coorte": float(len(remanescentes) / n_tratados),
                        "rotulo_uso": ROTULO_SPILLOVER,
                    }
                )
    resultado = pd.DataFrame(linhas)
    if not amostra["papel_causal"].equals(papel_original):
        raise AssertionError("papel_causal foi alterado")
    return resultado


def diagnostico_antecipacao_pre(
    amostra: pd.DataFrame,
    coortes: Sequence[int] = COORTES,
    outcome: str = OUTCOME_PRIMARIO,
) -> pd.DataFrame:
    """Resume padrões em k=-2/-3 sem redefinir g ou a janela de antecipação."""
    linhas: list[pd.DataFrame] = []
    for coorte in coortes:
        painel = selecionar_painel_pre_coorte(amostra, int(coorte))
        painel = normalizar_indice_g_menos_1(painel, int(coorte), outcome)
        recorte = painel.loc[painel["tempo_relativo_pre"].isin([-3, -2])].copy()
        resumo = recorte.groupby(["grupo", "tempo_relativo_pre"], as_index=False).agg(
            n_unidades=("codigo_municipio_ibge", "nunique"),
            media_nivel=(outcome, "mean"),
            mediana_nivel=(outcome, "median"),
            media_indice_g_menos_1=("indice_g_menos_1", "mean"),
            mediana_indice_g_menos_1=("indice_g_menos_1", "median"),
        )
        resumo["coorte_g"] = int(coorte)
        linhas.append(resumo)
    resultado = pd.concat(linhas, ignore_index=True)
    resultado["fato_timing"] = "128_DE_129_TIMINGS_PROXY_CENSO"
    resultado["hipotese_congelada"] = "ANTICIPATION_0_PERIODOS"
    resultado["rotulo_inferencia"] = "DIAGNOSTICO_PRE_NAO_REDEFINE_G_NEM_ANTECIPACAO"
    return resultado


def plano_robustez_pre_especificado() -> pd.DataFrame:
    """Plano futuro, não executado, justificado sem resultados pós-tratamento."""
    linhas = [
        ("PRINCIPAL_NIVEL", "Outcome primário D14 em nível", "CONGELADA", "FUTURA_ESTIMACAO"),
        ("SENSIBILIDADE_LOG1P", "Assimetria e escala observadas no baseline/pré", "PRE_ESPECIFICADA_D14", "FUTURA_ESTIMACAO"),
        ("JANELA_K_MENOS3_A_MAIS2", "Avaliar lead adicional com coortes 2010-2013", "PRE_ESPECIFICADA_D14", "FUTURA_ESTIMACAO"),
        ("AGREGACAO_POR_COORTE", "Heterogeneidade e tamanhos de coorte distintos", "JUSTIFICATIVA_METODOLOGICA", "FUTURA_ESTIMACAO"),
        ("COORTE_2013", "n=2 implica precisão muito limitada", "JUSTIFICATIVA_PRE_TRATAMENTO", "DIAGNOSTICO_E_REPORTE_SEPARADO"),
        ("SPILLOVER_25_KM", "Cenário espacial documentado antes da estimação", "PRE_ESPECIFICADA_D14", "FUTURA_SENSIBILIDADE"),
        ("SPILLOVER_50_KM", "Cenário espacial documentado antes da estimação", "PRE_ESPECIFICADA_D14", "FUTURA_SENSIBILIDADE"),
        ("SPILLOVER_100_KM", "Cenário espacial documentado antes da estimação", "PRE_ESPECIFICADA_D14", "FUTURA_SENSIBILIDADE"),
        ("ARRANJO_POPULACIONAL_2010", "Integração funcional potencial e limitação temporal conhecida", "PRE_ESPECIFICADA_D14", "FUTURA_SENSIBILIDADE"),
        ("COVARIAVEIS_BASELINE_EXISTENTES", "Ajuste apenas com medidas disponíveis antes do tratamento", "CONDICIONAL_A_METODO_E_OVERLAP", "FUTURA_SENSIBILIDADE"),
        ("RESTRICAO_SUPORTE_ATT", "Cinco tratados acima do máximo dos controles no score D17", "SOMENTE_SENSIBILIDADE_SE_FORMALIZADA", "NAO_EXECUTAR_NA_D18"),
    ]
    return pd.DataFrame(linhas, columns=["item", "justificativa_ex_ante", "status_pre_especificacao", "uso_futuro"])
