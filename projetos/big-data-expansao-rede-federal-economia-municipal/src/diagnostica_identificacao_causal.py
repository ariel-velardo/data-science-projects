"""D13 — diagnósticos offline do gate de identificação causal.

Este módulo não estima nenhum efeito causal, não faz matching, não define
`post`/`event_time`, não seleciona controles individualmente e não altera o
painel integrado (D11) nem a auditoria de suporte temporal (D12). Ele produz
apenas: auditoria do pool de controles candidato, diagnóstico de nível e de
pré-tendência descritiva (estritamente pré-tratamento) e uma tabela de gate
por coorte, reaproveitando `audita_populacao_causal_cempre` (D12) sem
duplicar suas regras de elegibilidade temporal.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

import audita_populacao_causal_cempre as d12

CHAVE_MUNICIPIO = d12.CHAVE_MUNICIPIO
COLUNA_OUTCOME_708 = d12.COLUNA_OUTCOME_708
COORTES_DIAGNOSTICO = d12.COORTES_DIAGNOSTICO
ANO_INICIAL_PAINEL = 2007

carrega_painel_integrado = d12.carrega_painel_integrado


# ---------------------------------------------------------------------------
# Seção 4 — auditoria do pool de controles candidato (4.964)
# ---------------------------------------------------------------------------

def auditar_pool_controles(painel: pd.DataFrame) -> dict[str, Any]:
    """Audita empiricamente o pool `fl_elegivel_controle_candidato=True`.

    Não substitui o pool 4.964 pelo conjunto de nunca expostos (4.970,
    tipicamente maior): apenas mede a relação entre os dois conjuntos e
    reporta qualquer exceção institucional encontrada, sem escondê-la.
    """
    obrigatorias = {
        CHAVE_MUNICIPIO, "fl_elegivel_controle_candidato",
        "sem_exposicao_observada_2007_2019", "fase_ii", "motivos_exclusao",
    }
    ausentes = sorted(obrigatorias - set(painel.columns))
    if ausentes:
        raise ValueError(f"painel integrado sem colunas necessárias à auditoria do pool: {ausentes}")

    por_municipio = painel.groupby(CHAVE_MUNICIPIO, sort=False).first()
    pool = por_municipio.loc[por_municipio["fl_elegivel_controle_candidato"] == True]  # noqa: E712
    nunca_expostos = por_municipio.loc[por_municipio["sem_exposicao_observada_2007_2019"] == True]  # noqa: E712

    pool_nao_nunca_exposto = pool.loc[pool["sem_exposicao_observada_2007_2019"] != True]  # noqa: E712
    pool_fase_ii = pool.loc[pool["fase_ii"] == True]  # noqa: E712
    nunca_exposto_fora_do_pool = nunca_expostos.index.difference(pool.index)

    return {
        "n_pool_elegivel": int(len(pool)),
        "n_nunca_expostos": int(len(nunca_expostos)),
        "n_pool_nao_nunca_exposto": int(len(pool_nao_nunca_exposto)),
        "codigos_pool_nao_nunca_exposto": sorted(pool_nao_nunca_exposto.index),
        "n_pool_fase_ii": int(len(pool_fase_ii)),
        "codigos_pool_fase_ii": sorted(pool_fase_ii.index),
        "n_nunca_exposto_fora_do_pool": int(len(nunca_exposto_fora_do_pool)),
        "motivos_nunca_exposto_fora_do_pool": (
            por_municipio.loc[nunca_exposto_fora_do_pool, "motivos_exclusao"]
            .value_counts().to_dict()
        ),
        "pool_e_subconjunto_de_nunca_expostos": bool(len(pool_nao_nunca_exposto) == 0),
        "pool_sem_fase_ii": bool(len(pool_fase_ii) == 0),
    }


# ---------------------------------------------------------------------------
# Seções 10-11 — nível pré-tratamento no baseline (g-1)
# ---------------------------------------------------------------------------

def baseline_pre_tratamento_por_coorte(
    painel: pd.DataFrame, coortes: list[int] | None = None
) -> pd.DataFrame:
    """Distribuição do outcome 708 em `g-1`, tratados da coorte vs. pool de
    controles elegíveis. Não faz matching nem exclui controle por outcome —
    usa o pool inteiro de `fl_elegivel_controle_candidato=True`.
    """
    coortes = coortes or COORTES_DIAGNOSTICO
    controles_pool = painel.loc[painel["fl_elegivel_controle_candidato"] == True]  # noqa: E712
    linhas: list[dict[str, Any]] = []
    for coorte in coortes:
        ano_baseline = coorte - 1
        tratados = painel.loc[
            (painel["candidato_amostra_principal"] == True)  # noqa: E712
            & (painel["ano_coorte_candidata"] == coorte)
            & (painel["ano"] == ano_baseline),
            COLUNA_OUTCOME_708,
        ].dropna()
        controles = controles_pool.loc[
            controles_pool["ano"] == ano_baseline, COLUNA_OUTCOME_708
        ].dropna()
        linhas.append({
            "ano_coorte_candidata": coorte,
            "ano_baseline_g_menos_1": ano_baseline,
            "n_tratados": int(len(tratados)),
            "n_controles": int(len(controles)),
            "media_tratados": float(tratados.mean()) if len(tratados) else None,
            "mediana_tratados": float(tratados.median()) if len(tratados) else None,
            "p25_tratados": float(tratados.quantile(0.25)) if len(tratados) else None,
            "p75_tratados": float(tratados.quantile(0.75)) if len(tratados) else None,
            "media_controles": float(controles.mean()) if len(controles) else None,
            "mediana_controles": float(controles.median()) if len(controles) else None,
            "p25_controles": float(controles.quantile(0.25)) if len(controles) else None,
            "p75_controles": float(controles.quantile(0.75)) if len(controles) else None,
        })
    return pd.DataFrame(linhas)


def distribuicao_baseline_longa(
    painel: pd.DataFrame, coortes: list[int] | None = None
) -> pd.DataFrame:
    """Formato longo (uma linha por observação) do outcome em `g-1`, para o
    boxplot de distribuição. Mesma regra de grupos da função anterior.
    """
    coortes = coortes or COORTES_DIAGNOSTICO
    controles_pool = painel.loc[painel["fl_elegivel_controle_candidato"] == True]  # noqa: E712
    partes: list[pd.DataFrame] = []
    for coorte in coortes:
        ano_baseline = coorte - 1
        tratados = painel.loc[
            (painel["candidato_amostra_principal"] == True)  # noqa: E712
            & (painel["ano_coorte_candidata"] == coorte)
            & (painel["ano"] == ano_baseline),
            [CHAVE_MUNICIPIO, COLUNA_OUTCOME_708],
        ].dropna(subset=[COLUNA_OUTCOME_708]).copy()
        tratados["grupo"] = "tratados"
        controles = controles_pool.loc[
            controles_pool["ano"] == ano_baseline, [CHAVE_MUNICIPIO, COLUNA_OUTCOME_708]
        ].dropna(subset=[COLUNA_OUTCOME_708]).copy()
        controles["grupo"] = "controles"
        for parte in (tratados, controles):
            parte["ano_coorte_candidata"] = coorte
        partes.append(tratados)
        partes.append(controles)
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(
        columns=[CHAVE_MUNICIPIO, COLUNA_OUTCOME_708, "grupo", "ano_coorte_candidata"]
    )


# ---------------------------------------------------------------------------
# Seções 12-14 — pré-tendência descritiva (níveis e índice normalizado)
# ---------------------------------------------------------------------------

def serie_pre_tendencia_niveis(painel: pd.DataFrame, coorte: int) -> pd.DataFrame:
    """Mediana do outcome 708 por ano, tratados da coorte vs. pool de
    controles — SOMENTE anos anteriores a `coorte` (nenhum ano pós usado).

    Usa toda a história pré disponível no painel (não trava em 2 anos):
    para a coorte 2009 isso são só 2007-2008; para 2013, 2007-2012.
    """
    anos_pre = [ano for ano in range(ANO_INICIAL_PAINEL, coorte)]
    tratados = painel.loc[
        (painel["candidato_amostra_principal"] == True)  # noqa: E712
        & (painel["ano_coorte_candidata"] == coorte)
        & (painel["ano"].isin(anos_pre)),
    ]
    controles = painel.loc[
        (painel["fl_elegivel_controle_candidato"] == True)  # noqa: E712
        & (painel["ano"].isin(anos_pre)),
    ]
    linhas: list[dict[str, Any]] = []
    for ano in anos_pre:
        med_tratados = tratados.loc[tratados["ano"] == ano, COLUNA_OUTCOME_708].median()
        med_controles = controles.loc[controles["ano"] == ano, COLUNA_OUTCOME_708].median()
        linhas.append({"ano_coorte_candidata": coorte, "ano": ano, "grupo": "tratados", "mediana_708": med_tratados})
        linhas.append({"ano_coorte_candidata": coorte, "ano": ano, "grupo": "controles", "mediana_708": med_controles})
    return pd.DataFrame(linhas)


def indice_pre_tendencia_normalizado(serie_niveis: pd.DataFrame, coorte: int) -> pd.DataFrame:
    """Normaliza a série de níveis pré-tratamento com `g-1 = 100`, somente
    para visualização de trajetória relativa — não altera o outcome usado
    por qualquer estimador futuro.
    """
    ano_baseline = coorte - 1
    resultado = serie_niveis.copy()
    resultado["indice_708"] = pd.NA
    for grupo in resultado["grupo"].unique():
        mascara = resultado["grupo"] == grupo
        base = resultado.loc[mascara & (resultado["ano"] == ano_baseline), "mediana_708"]
        if base.empty or pd.isna(base.iloc[0]) or base.iloc[0] <= 0:
            continue
        valor_base = float(base.iloc[0])
        resultado.loc[mascara, "indice_708"] = resultado.loc[mascara, "mediana_708"] / valor_base * 100.0
    return resultado


# ---------------------------------------------------------------------------
# Seção 16 — mudança descritiva g-2 -> g-1
# ---------------------------------------------------------------------------

def mudanca_pre_g2_g1(painel: pd.DataFrame, coortes: list[int] | None = None) -> pd.DataFrame:
    """Variação descritiva da mediana do outcome entre `g-2` e `g-1`, para
    tratados e para o pool de controles. Não é um teste formal de tendências
    paralelas — apenas um número descritivo adicional.
    """
    coortes = coortes or COORTES_DIAGNOSTICO
    controles_pool = painel.loc[painel["fl_elegivel_controle_candidato"] == True]  # noqa: E712
    linhas: list[dict[str, Any]] = []
    for coorte in coortes:
        ano_g2, ano_g1 = coorte - 2, coorte - 1
        tratados = painel.loc[
            (painel["candidato_amostra_principal"] == True)  # noqa: E712
            & (painel["ano_coorte_candidata"] == coorte)
        ]
        for grupo_nome, grupo_df in (("tratados", tratados), ("controles", controles_pool)):
            valor_g2 = grupo_df.loc[grupo_df["ano"] == ano_g2, COLUNA_OUTCOME_708].median()
            valor_g1 = grupo_df.loc[grupo_df["ano"] == ano_g1, COLUNA_OUTCOME_708].median()
            variacao_abs = (
                float(valor_g1 - valor_g2) if pd.notna(valor_g2) and pd.notna(valor_g1) else None
            )
            variacao_pct = (
                float((valor_g1 - valor_g2) / valor_g2 * 100.0)
                if pd.notna(valor_g2) and pd.notna(valor_g1) and valor_g2 != 0
                else None
            )
            linhas.append({
                "ano_coorte_candidata": coorte,
                "grupo": grupo_nome,
                "ano_g2": ano_g2,
                "ano_g1": ano_g1,
                "mediana_g2": float(valor_g2) if pd.notna(valor_g2) else None,
                "mediana_g1": float(valor_g1) if pd.notna(valor_g1) else None,
                "variacao_absoluta": variacao_abs,
                "variacao_percentual": variacao_pct,
            })
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# Seção 22 — tabela de gate por coorte
# ---------------------------------------------------------------------------

def tabela_gate_por_coorte(painel: pd.DataFrame, coortes: list[int] | None = None) -> pd.DataFrame:
    """Combina o suporte temporal já diagnosticado no D12 com a categoria
    objetiva/descritiva de pré-tendência (nunca subjetiva) por coorte.
    """
    coortes = coortes or COORTES_DIAGNOSTICO
    resumo = d12.resumo_por_coorte(painel)
    controles = d12.auditar_controles_por_coorte(painel, coortes)

    linhas: list[dict[str, Any]] = []
    for coorte in coortes:
        linha_resumo = resumo.loc[resumo["ano_coorte_candidata"] == coorte].iloc[0]
        linha_controles = controles.loc[controles["ano_coorte_candidata"] == coorte].iloc[0]
        n_pre_disponiveis = coorte - ANO_INICIAL_PAINEL
        if n_pre_disponiveis <= 2:
            observacao = "LIMITADA_2_PERIODOS_PRE"
        else:
            observacao = "DIAGNOSTICO_PRE_DISPONIVEL"
        linhas.append({
            "ano_coorte_candidata": coorte,
            "n_tratados": int(linha_resumo["n_candidatos"]),
            "n_pre_disponiveis": int(n_pre_disponiveis),
            "suporte_2pre3pos": int(linha_resumo["n_elegivel_diag_2pre_3pos"]),
            "suporte_3pre3pos": int(linha_resumo["n_elegivel_diag_3pre_3pos"]),
            "controles_2pre3pos": int(linha_controles["controles_2pre_3pos"]),
            "controles_3pre3pos": int(linha_controles["controles_3pre_3pos"]),
            "observacao_pre_tendencia": observacao,
        })
    return pd.DataFrame(linhas)


def main() -> None:
    painel = carrega_painel_integrado()
    print("Auditoria do pool de controles:")
    print(auditar_pool_controles(painel))
    print("\nBaseline pré-tratamento (g-1):")
    print(baseline_pre_tratamento_por_coorte(painel).to_string(index=False))
    print("\nTabela de gate por coorte:")
    print(tabela_gate_por_coorte(painel).to_string(index=False))


if __name__ == "__main__":
    main()
