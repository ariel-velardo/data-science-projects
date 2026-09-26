"""Executa a auditoria descritiva e o diagnostico de overlap da Fase 1.

O modulo nao estima efeito causal. O propensity score e usado apenas para
caracterizar assignment e suporte comum.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from src.audita_covariaveis import (
    COLUNAS_PROPENSITY_PRINCIPAL,
    VARIAVEIS_PROIBIDAS_PROPENSITY,
)
from src.diagnostica_overlap import estimar_propensity_oof, resumir_overlap


SEMENTE = 20240925
NUMERICAS_PROPENSITY = ("IDADEMAE_NUM",)
CATEGORICAS_PROPENSITY = tuple(
    coluna for coluna in COLUNAS_PROPENSITY_PRINCIPAL if coluna not in NUMERICAS_PROPENSITY
)


def _normalizar_json(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {str(chave): _normalizar_json(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_normalizar_json(item) for item in valor]
    if isinstance(valor, (np.integer,)):
        return int(valor)
    if isinstance(valor, (np.floating,)):
        return None if np.isnan(valor) else float(valor)
    if isinstance(valor, (pd.Timestamp,)):
        return valor.isoformat()
    if pd.isna(valor):
        return None
    return valor


def _salvar_json(caminho: Path, conteudo: dict[str, Any]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(_normalizar_json(conteudo), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _registros(tabela: pd.DataFrame) -> list[dict[str, Any]]:
    return _normalizar_json(tabela.to_dict(orient="records"))


def _markdown_tabela(tabela: pd.DataFrame) -> str:
    exibicao = tabela.copy()
    for coluna in exibicao.select_dtypes(include="float").columns:
        exibicao[coluna] = exibicao[coluna].map(
            lambda valor: "" if pd.isna(valor) else f"{valor:.6f}"
        )
    cabecalho = "| " + " | ".join(map(str, exibicao.columns)) + " |"
    separador = "| " + " | ".join(["---"] * len(exibicao.columns)) + " |"
    linhas = [
        "| " + " | ".join(str(valor) for valor in linha) + " |"
        for linha in exibicao.itertuples(index=False, name=None)
    ]
    return "\n".join([cabecalho, separador, *linhas]) + "\n"


def _criar_views(conexao: duckdb.DuckDBPyConnection, parquet: Path) -> None:
    caminho = parquet.as_posix().replace("'", "''")
    conexao.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW sinasc AS
        SELECT * FROM read_parquet('{caminho}')
        """
    )
    conexao.execute(
        """
        CREATE OR REPLACE TEMP VIEW fase1_base AS
        SELECT
            *,
            try_cast(MESPRENAT AS INTEGER) AS mesprenat_num,
            try_cast(PESO AS INTEGER) AS peso_num,
            try_cast(GRAVIDEZ AS INTEGER) AS gravidez_num,
            CASE
                WHEN try_cast(MESPRENAT AS INTEGER) BETWEEN 1 AND 3 THEN 1
                WHEN try_cast(MESPRENAT AS INTEGER) BETWEEN 4 AND 9 THEN 0
            END AS tratamento,
            CASE WHEN try_cast(PESO AS INTEGER) > 0
                 THEN CAST(try_cast(PESO AS INTEGER) < 2500 AS INTEGER) END AS y_p0,
            CASE WHEN try_cast(PESO AS INTEGER) BETWEEN 500 AND 6000
                 THEN CAST(try_cast(PESO AS INTEGER) < 2500 AS INTEGER) END AS y_p1
        FROM sinasc
        """
    )
    conexao.execute(
        """
        CREATE OR REPLACE TEMP VIEW amostra_principal AS
        SELECT
            contador,
            tratamento,
            y_p1 AS Y_BAIXO_PESO,
            CASE WHEN try_cast(IDADEMAE AS INTEGER) BETWEEN 10 AND 59
                 THEN try_cast(IDADEMAE AS DOUBLE) END AS IDADEMAE_NUM,
            CASE WHEN try_cast(ESCMAE2010 AS INTEGER) = 9 OR ESCMAE2010 IS NULL
                 THEN 'IGNORADO' ELSE CAST(try_cast(ESCMAE2010 AS INTEGER) AS VARCHAR)
            END AS ESCOLARIDADE_MAE,
            CASE WHEN try_cast(RACACORMAE AS INTEGER) = 9 OR RACACORMAE IS NULL
                 THEN 'IGNORADO' ELSE CAST(try_cast(RACACORMAE AS INTEGER) AS VARCHAR)
            END AS RACA_COR_MAE,
            CASE WHEN try_cast(ESTCIVMAE AS INTEGER) = 9 OR ESTCIVMAE IS NULL
                 THEN 'IGNORADO' ELSE CAST(try_cast(ESTCIVMAE AS INTEGER) AS VARCHAR)
            END AS SITUACAO_CONJUGAL,
            CASE WHEN try_cast(PARIDADE AS INTEGER) IN (9, 99) OR PARIDADE IS NULL
                 THEN 'IGNORADO' ELSE CAST(try_cast(PARIDADE AS INTEGER) AS VARCHAR)
            END AS PARIDADE_CAT,
            CASE
                WHEN try_cast(QTDFILMORT AS INTEGER) = 0 THEN '0'
                WHEN try_cast(QTDFILMORT AS INTEGER) = 1 THEN '1'
                WHEN try_cast(QTDFILMORT AS INTEGER) BETWEEN 2 AND 98 THEN '2_OU_MAIS'
                ELSE 'IGNORADO'
            END AS PERDAS_FETAIS_CAT,
            CASE WHEN regexp_full_match(CAST(CODMUNRES AS VARCHAR), '[0-9]{6}')
                 THEN substr(CAST(CODMUNRES AS VARCHAR), 1, 2)
                 ELSE 'IGNORADO' END AS UF_RESIDENCIA
        FROM fase1_base
        WHERE tratamento IS NOT NULL
          AND y_p1 IS NOT NULL
          AND gravidez_num = 1
        """
    )


def _auditar_base(conexao: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    linha = conexao.execute(
        """
        SELECT
            count(*) AS n_registros,
            count(DISTINCT contador) AS n_contador_distinto,
            count(*) - count(DISTINCT contador) AS n_duplicados_contador,
            count(*) FILTER (WHERE contador IS NULL) AS n_contador_missing
        FROM fase1_base
        """
    ).fetchdf().iloc[0]
    return {
        "granularidade": "um registro por nascido vivo",
        "chave_tecnica": "contador",
        **_normalizar_json(linha.to_dict()),
    }


def _auditar_tratamento(conexao: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conexao.execute(
        """
        SELECT
            CASE
                WHEN mesprenat_num BETWEEN 1 AND 3 THEN '1-3 (T=1)'
                WHEN mesprenat_num BETWEEN 4 AND 9 THEN '4-9 (T=0)'
                WHEN mesprenat_num = 99 THEN '99 (ignorado)'
                WHEN MESPRENAT IS NULL OR trim(CAST(MESPRENAT AS VARCHAR)) = '' THEN 'missing'
                ELSE 'outro/invalido'
            END AS categoria_mesprenat,
            count(*) AS n,
            round(100.0 * count(*) / sum(count(*)) OVER (), 6) AS percentual,
            count(*) FILTER (WHERE try_cast(CONSPRENAT AS INTEGER) = 0) AS n_consprenat_zero
        FROM fase1_base
        GROUP BY 1
        ORDER BY 1
        """
    ).fetchdf()


def _auditar_peso(conexao: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conexao.execute(
        """
        SELECT * FROM (
            SELECT
                'P0_peso_positivo' AS regra,
                count(*) FILTER (WHERE y_p0 IS NOT NULL) AS n_valido,
                count(*) FILTER (WHERE y_p0 IS NULL) AS n_excluido,
                count(*) FILTER (WHERE y_p0 = 1) AS n_baixo_peso,
                round(100.0 * avg(y_p0) FILTER (WHERE y_p0 IS NOT NULL), 6) AS prevalencia_baixo_peso_pct
            FROM fase1_base
            UNION ALL
            SELECT
                'P1_500_a_6000g',
                count(*) FILTER (WHERE y_p1 IS NOT NULL),
                count(*) FILTER (WHERE y_p1 IS NULL),
                count(*) FILTER (WHERE y_p1 = 1),
                round(100.0 * avg(y_p1) FILTER (WHERE y_p1 IS NOT NULL), 6)
            FROM fase1_base
        )
        ORDER BY regra
        """
    ).fetchdf()


def _distribuicao_peso(conexao: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conexao.execute(
        """
        SELECT
            floor(peso_num / 250) * 250 AS inicio_faixa_g,
            count(*) AS n
        FROM fase1_base
        WHERE peso_num BETWEEN 0 AND 7000
        GROUP BY 1
        ORDER BY 1
        """
    ).fetchdf()


def _auditar_gravidez(conexao: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conexao.execute(
        """
        SELECT
            CASE
                WHEN gravidez_num = 1 THEN '1_unica'
                WHEN gravidez_num = 2 THEN '2_dupla'
                WHEN gravidez_num = 3 THEN '3_tripla_ou_mais'
                WHEN gravidez_num = 9 THEN '9_ignorada'
                WHEN GRAVIDEZ IS NULL OR trim(CAST(GRAVIDEZ AS VARCHAR)) = '' THEN 'missing'
                ELSE 'outro_invalido'
            END AS tipo_gravidez,
            count(*) AS n_total,
            count(*) FILTER (WHERE y_p1 IS NOT NULL) AS n_y_valido_p1,
            round(100.0 * avg(y_p1) FILTER (WHERE y_p1 IS NOT NULL), 6) AS baixo_peso_pct,
            count(*) FILTER (WHERE tratamento IS NOT NULL) AS n_t_valido,
            round(100.0 * avg(tratamento) FILTER (WHERE tratamento IS NOT NULL), 6) AS t1_pct
        FROM fase1_base
        GROUP BY 1
        ORDER BY 1
        """
    ).fetchdf()


def _fluxo_amostra(conexao: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    contagens = conexao.execute(
        """
        SELECT
            count(*) AS base,
            count(*) FILTER (WHERE tratamento IS NOT NULL AND y_p0 IS NOT NULL) AS a0,
            count(*) FILTER (WHERE tratamento IS NOT NULL AND y_p1 IS NOT NULL) AS a1,
            count(*) FILTER (
                WHERE tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num = 1
            ) AS a2
        FROM fase1_base
        """
    ).fetchdf().iloc[0]
    total = int(contagens["base"])
    definicoes = (
        ("A0", "T conhecido e PESO numerico positivo", total, int(contagens["a0"])),
        ("A1", "A0 + 500 g <= PESO <= 6.000 g", int(contagens["a0"]), int(contagens["a1"])),
        ("A2", "A1 + gestacao unica (GRAVIDEZ=1)", int(contagens["a1"]), int(contagens["a2"])),
        (
            "A3",
            "A2 + X principal preparado; missing tratado no pipeline",
            int(contagens["a2"]),
            int(contagens["a2"]),
        ),
    )
    return pd.DataFrame(
        [
            {
                "etapa": etapa,
                "n_antes": antes,
                "n_excluido": antes - restante,
                "motivo": motivo,
                "n_restante": restante,
                "percentual_base_inicial": round(100 * restante / total, 6),
            }
            for etapa, motivo, antes, restante in definicoes
        ]
    )


def _auditar_missing(conexao: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    regras = {
        "IDADEMAE": "try_cast(IDADEMAE AS INTEGER) IS NULL OR try_cast(IDADEMAE AS INTEGER) NOT BETWEEN 10 AND 59",
        "ESCMAE2010": "try_cast(ESCMAE2010 AS INTEGER) IS NULL OR try_cast(ESCMAE2010 AS INTEGER) = 9",
        "RACACORMAE": "try_cast(RACACORMAE AS INTEGER) IS NULL OR try_cast(RACACORMAE AS INTEGER) = 9",
        "ESTCIVMAE": "try_cast(ESTCIVMAE AS INTEGER) IS NULL OR try_cast(ESTCIVMAE AS INTEGER) = 9",
        "PARIDADE": "try_cast(PARIDADE AS INTEGER) IS NULL OR try_cast(PARIDADE AS INTEGER) IN (9, 99)",
        "QTDFILMORT": "try_cast(QTDFILMORT AS INTEGER) IS NULL OR try_cast(QTDFILMORT AS INTEGER) = 99",
        "CODMUNRES": "NOT regexp_full_match(CAST(CODMUNRES AS VARCHAR), '[0-9]{6}') OR CODMUNRES IS NULL",
    }
    linhas: list[dict[str, Any]] = []
    for variavel, condicao in regras.items():
        resultado = conexao.execute(
            f"""
            SELECT
                count(*) AS n_total,
                count(*) FILTER (WHERE {condicao}) AS n_missing,
                count(*) FILTER (WHERE tratamento = 1) AS n_t1,
                count(*) FILTER (WHERE tratamento = 1 AND ({condicao})) AS n_missing_t1,
                count(*) FILTER (WHERE tratamento = 0) AS n_t0,
                count(*) FILTER (WHERE tratamento = 0 AND ({condicao})) AS n_missing_t0,
                count(*) FILTER (WHERE y_p1 = 1) AS n_y1,
                count(*) FILTER (WHERE y_p1 = 1 AND ({condicao})) AS n_missing_y1,
                count(*) FILTER (WHERE y_p1 = 0) AS n_y0,
                count(*) FILTER (WHERE y_p1 = 0 AND ({condicao})) AS n_missing_y0
            FROM fase1_base
            WHERE tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num = 1
            """
        ).fetchdf().iloc[0]
        linha = {"variavel": variavel, **resultado.to_dict()}
        for sufixo, numerador, denominador in (
            ("pct_total", "n_missing", "n_total"),
            ("pct_t1", "n_missing_t1", "n_t1"),
            ("pct_t0", "n_missing_t0", "n_t0"),
            ("pct_y1", "n_missing_y1", "n_y1"),
            ("pct_y0", "n_missing_y0", "n_y0"),
        ):
            linha[sufixo] = round(100 * linha[numerador] / linha[denominador], 6)
        linhas.append(linha)
    return pd.DataFrame(linhas).sort_values("pct_total", ascending=False)


def _smd_balanceamento(conexao: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    idade = conexao.execute(
        """
        SELECT tratamento, avg(IDADEMAE_NUM) AS media, stddev_samp(IDADEMAE_NUM) AS dp
        FROM amostra_principal
        GROUP BY tratamento
        ORDER BY tratamento
        """
    ).fetchdf().set_index("tratamento")
    media_t0, media_t1 = idade.loc[0, "media"], idade.loc[1, "media"]
    dp_pooled = np.sqrt((idade.loc[0, "dp"] ** 2 + idade.loc[1, "dp"] ** 2) / 2)
    linhas = [
        {
            "variavel": "IDADEMAE_NUM",
            "tipo": "numerica",
            "media_t1": media_t1,
            "media_t0": media_t0,
            "smd": (media_t1 - media_t0) / dp_pooled,
            "smd_abs": abs((media_t1 - media_t0) / dp_pooled),
        }
    ]
    for coluna in CATEGORICAS_PROPENSITY:
        tabela = conexao.execute(
            f"""
            WITH contagens AS (
                SELECT tratamento, {coluna} AS nivel, count(*) AS n
                FROM amostra_principal
                GROUP BY tratamento, nivel
            ), totais AS (
                SELECT tratamento, sum(n) AS total FROM contagens GROUP BY tratamento
            ), niveis AS (SELECT DISTINCT nivel FROM contagens)
            SELECT
                niveis.nivel,
                coalesce(t1.n, 0) / CAST(tt1.total AS DOUBLE) AS p_t1,
                coalesce(t0.n, 0) / CAST(tt0.total AS DOUBLE) AS p_t0
            FROM niveis
            CROSS JOIN (SELECT total FROM totais WHERE tratamento = 1) tt1
            CROSS JOIN (SELECT total FROM totais WHERE tratamento = 0) tt0
            LEFT JOIN contagens t1 ON t1.tratamento = 1 AND t1.nivel = niveis.nivel
            LEFT JOIN contagens t0 ON t0.tratamento = 0 AND t0.nivel = niveis.nivel
            """
        ).fetchdf()
        denominador = np.sqrt(
            (tabela["p_t1"] * (1 - tabela["p_t1"]) + tabela["p_t0"] * (1 - tabela["p_t0"])) / 2
        )
        tabela["smd"] = np.where(
            denominador.eq(0),
            np.where(tabela["p_t1"].eq(tabela["p_t0"]), 0.0, np.inf),
            (tabela["p_t1"] - tabela["p_t0"]) / denominador,
        )
        pior = tabela.loc[tabela["smd"].abs().idxmax()]
        linhas.append(
            {
                "variavel": coluna,
                "tipo": "categorica_pior_nivel",
                "nivel_pior_smd": pior["nivel"],
                "proporcao_t1": pior["p_t1"],
                "proporcao_t0": pior["p_t0"],
                "smd": pior["smd"],
                "smd_abs": abs(pior["smd"]),
            }
        )
    return pd.DataFrame(linhas).sort_values("smd_abs", ascending=False).reset_index(drop=True)


def _perfil_tratamento(conexao: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conexao.execute(
        """
        SELECT
            tratamento,
            count(*) AS n,
            round(100.0 * count(*) / sum(count(*)) OVER (), 6) AS percentual,
            avg(IDADEMAE_NUM) AS idade_media,
            stddev_samp(IDADEMAE_NUM) AS idade_dp,
            median(IDADEMAE_NUM) AS idade_mediana,
            round(100.0 * avg(Y_BAIXO_PESO), 6) AS baixo_peso_pct_descritivo
        FROM amostra_principal
        GROUP BY tratamento
        ORDER BY tratamento DESC
        """
    ).fetchdf()


def _positividade(conexao: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    expressoes = {
        "UF_RESIDENCIA": "UF_RESIDENCIA",
        "FAIXA_IDADE_MAE": "CASE WHEN IDADEMAE_NUM < 20 THEN '<20' WHEN IDADEMAE_NUM < 30 THEN '20-29' WHEN IDADEMAE_NUM < 40 THEN '30-39' WHEN IDADEMAE_NUM IS NULL THEN 'IGNORADO' ELSE '40+' END",
        "ESCOLARIDADE_MAE": "ESCOLARIDADE_MAE",
        "RACA_COR_MAE": "RACA_COR_MAE",
        "PARIDADE_CAT": "PARIDADE_CAT",
    }
    tabelas = []
    for perfil, expressao in expressoes.items():
        tabela = conexao.execute(
            f"""
            SELECT
                '{perfil}' AS perfil,
                CAST({expressao} AS VARCHAR) AS categoria,
                count(*) AS n,
                count(*) FILTER (WHERE tratamento = 1) AS n_t1,
                count(*) FILTER (WHERE tratamento = 0) AS n_t0,
                round(avg(tratamento), 6) AS proporcao_t1
            FROM amostra_principal
            GROUP BY 1, 2
            ORDER BY 1, 2
            """
        ).fetchdf()
        tabela["flag_quase_deterministico"] = (
            tabela["proporcao_t1"].le(0.01) | tabela["proporcao_t1"].ge(0.99)
        )
        tabela["flag_celula_pequena"] = tabela[["n_t1", "n_t0"]].min(axis=1).lt(100)
        tabelas.append(tabela)
    return pd.concat(tabelas, ignore_index=True)


def _executar_propensity(
    conexao: duckdb.DuckDBPyConnection,
    diagnostico_dir: Path,
    tabelas_dir: Path,
) -> dict[str, Any]:
    dados = conexao.execute(
        "SELECT tratamento, " + ", ".join(COLUNAS_PROPENSITY_PRINCIPAL) + " FROM amostra_principal"
    ).fetchdf()
    x = dados.loc[:, COLUNAS_PROPENSITY_PRINCIPAL]
    propensity, metricas = estimar_propensity_oof(
        x=x,
        tratamento=dados["tratamento"],
        colunas_numericas=NUMERICAS_PROPENSITY,
        colunas_categoricas=CATEGORICAS_PROPENSITY,
        n_folds=5,
    )
    resumo = resumir_overlap(propensity, dados["tratamento"])
    resumo["status"] = "CONCLUIDO"
    resumo["metodo"] = {
        "modelo": "regressao logistica L2",
        "previsoes": "out-of-fold estratificadas",
        "semente": SEMENTE,
        "covariaveis": list(COLUNAS_PROPENSITY_PRINCIPAL),
        "outcome_usado": False,
        **metricas,
    }
    limites = np.linspace(0, 1, 101)
    hist = []
    t = dados["tratamento"].to_numpy()
    for grupo, nome in ((0, "T=0"), (1, "T=1")):
        contagens, _ = np.histogram(propensity[t == grupo], bins=limites)
        hist.extend(
            {
                "grupo": nome,
                "limite_inferior": limites[indice],
                "limite_superior": limites[indice + 1],
                "n": int(n),
            }
            for indice, n in enumerate(contagens)
        )
    pd.DataFrame(hist).to_csv(tabelas_dir / "histograma_propensity.csv", index=False)
    _salvar_json(diagnostico_dir / "fase1_overlap.json", resumo)
    return resumo


def executar_fase1(raiz: Path, executar_propensity: bool = True) -> dict[str, Any]:
    parquet = raiz / "data" / "processed" / "sinasc_2024.parquet"
    if not parquet.exists():
        raise FileNotFoundError(f"Parquet da Fase 0 nao encontrado: {parquet}")
    diagnostico_dir = raiz / "outputs" / "diagnostics"
    tabelas_dir = raiz / "outputs" / "tables"
    tabelas_dir.mkdir(parents=True, exist_ok=True)
    diagnostico_dir.mkdir(parents=True, exist_ok=True)

    conexao = duckdb.connect()
    try:
        _criar_views(conexao, parquet)
        base = _auditar_base(conexao)
        if base["n_duplicados_contador"] or base["n_contador_missing"]:
            raise ValueError("A chave tecnica contador deixou de ser completa e unica.")

        tratamento = _auditar_tratamento(conexao)
        peso = _auditar_peso(conexao)
        gravidez = _auditar_gravidez(conexao)
        fluxo = _fluxo_amostra(conexao)
        missing = _auditar_missing(conexao)
        perfil_t = _perfil_tratamento(conexao)
        balanceamento = _smd_balanceamento(conexao)
        positividade = _positividade(conexao)
        distribuicao_peso = _distribuicao_peso(conexao)

        fluxo.to_csv(tabelas_dir / "fluxo_amostra.csv", index=False)
        balanceamento.to_csv(tabelas_dir / "balanceamento_bruto.csv", index=False)
        missing.to_csv(tabelas_dir / "missing_x_principal.csv", index=False)
        positividade.to_csv(tabelas_dir / "positividade_perfis.csv", index=False)
        distribuicao_peso.to_csv(tabelas_dir / "distribuicao_peso_250g.csv", index=False)

        (diagnostico_dir / "fluxo_amostra.md").write_text(
            "# Fluxo da amostra - Fase 1\n\n" + _markdown_tabela(fluxo), encoding="utf-8"
        )
        (diagnostico_dir / "balanceamento_bruto.md").write_text(
            "# Balanceamento bruto - Fase 1\n\n"
            "SMD absoluto; para variaveis categoricas, o pior nivel observado.\n\n"
            + _markdown_tabela(balanceamento),
            encoding="utf-8",
        )
        (diagnostico_dir / "positividade_perfis.md").write_text(
            "# Positividade por perfis - Fase 1\n\n" + _markdown_tabela(positividade),
            encoding="utf-8",
        )

        amostra = {
            "fase": "FASE_1_DESENHO_E_OVERLAP",
            "efeito_causal_estimado": False,
            "base": base,
            "tratamento": _registros(tratamento),
            "outcome_peso": _registros(peso),
            "gravidez": _registros(gravidez),
            "fluxo_amostra": _registros(fluxo),
            "perfil_tratamento_amostra_principal": _registros(perfil_t),
            "missing_x_principal": _registros(missing),
            "balanceamento_bruto": _registros(balanceamento),
            "positividade_perfis": _registros(positividade),
            "x_principal": list(COLUNAS_PROPENSITY_PRINCIPAL),
            "variaveis_proibidas_propensity": sorted(VARIAVEIS_PROIBIDAS_PROPENSITY),
            "populacao_principal": (
                "nascidos vivos SINASC 2024, MESPRENAT 1-9, peso 500-6000 g "
                "e gestacao unica"
            ),
            "sensibilidades": [
                "P0: todo peso numerico positivo",
                "todas as gestacoes validas, com multipla apenas como sensibilidade",
                "registros CONSPRENAT=0 analisados separadamente, nao incorporados ao controle",
            ],
        }
        _salvar_json(diagnostico_dir / "fase1_amostra.json", amostra)

        if executar_propensity:
            try:
                overlap = _executar_propensity(conexao, diagnostico_dir, tabelas_dir)
            except RuntimeError as erro:
                if "scikit-learn" not in str(erro):
                    raise
                overlap = {
                    "status": "BLOQUEADO_DEPENDENCIA",
                    "erro": str(erro),
                    "efeito_causal_estimado": False,
                    "diagnosticos_disponiveis": [
                        "balanceamento bruto por SMD",
                        "positividade por perfis observados",
                    ],
                    "diagnosticos_pendentes": [
                        "propensity OOF",
                        "distribuicao e percentis de propensity",
                        "suporte comum",
                        "trimming diagnostico",
                    ],
                }
                _salvar_json(diagnostico_dir / "fase1_overlap.json", overlap)
        else:
            overlap = {
                "status": "NAO_EXECUTADO",
                "motivo": "execucao solicitada sem propensity",
                "efeito_causal_estimado": False,
            }
            _salvar_json(diagnostico_dir / "fase1_overlap.json", overlap)
    finally:
        conexao.close()
    return {"amostra": amostra, "overlap": overlap}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sem-propensity",
        action="store_true",
        help="Gera apenas auditorias descritivas; nao tenta importar scikit-learn.",
    )
    argumentos = parser.parse_args()
    raiz = Path(__file__).resolve().parents[1]
    resultado = executar_fase1(raiz, executar_propensity=not argumentos.sem_propensity)
    print(json.dumps(_normalizar_json({
        "n_final": resultado["amostra"]["fluxo_amostra"][-1]["n_restante"],
        "status_overlap": resultado["overlap"]["status"],
    }), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
