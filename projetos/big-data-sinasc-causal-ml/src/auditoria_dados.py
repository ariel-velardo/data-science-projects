"""Auditorias descritivas de schema, chave, qualidade e amostra."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import duckdb
import pandas as pd
from src.sinasc import verificar_arquivo_existente
from src.sinasc import detectar_formato_csv
from src.sinasc import CODIGOS_ESPECIAIS_DOCUMENTADOS
from src.sinasc import DESCRICOES_OFICIAIS
from src.sinasc import X_PROVAVEL_PRE_TRATAMENTO
from src.sinasc import grupo_temporal
from src.sinasc import papel_analitico
import argparse
import numpy as np
from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL
from src.diagnosticos import VARIAVEIS_PROIBIDAS_PROPENSITY
from src.diagnosticos import estimar_propensity_oof
from src.diagnosticos import resumir_overlap
from src.amostra import _criar_views
from src.sinasc import _normalizar_json
from src.sinasc import _salvar_json
from src.sinasc import _registros
from src.sinasc import _markdown_tabela

def construir_baixo_peso_candidato(peso: pd.Series) -> pd.Series:
    """Cria Y candidato (< 2.500 g) somente quando o peso é numérico e positivo."""

    peso_numerico = pd.to_numeric(peso, errors="coerce")
    valido = peso_numerico.gt(0)
    resultado = pd.Series(pd.NA, index=peso.index, dtype="Int8")
    resultado.loc[valido] = peso_numerico.loc[valido].lt(2500).astype("Int8")
    return resultado

def construir_tratamento_candidato(mes_inicio_prenatal: pd.Series) -> pd.Series:
    """Cria T candidato: meses 1-3 versus 4-9; demais códigos ficam ausentes."""

    mes_numerico = pd.to_numeric(mes_inicio_prenatal, errors="coerce")
    resultado = pd.Series(pd.NA, index=mes_inicio_prenatal.index, dtype="Int8")
    resultado.loc[mes_numerico.between(1, 3)] = 1
    resultado.loc[mes_numerico.between(4, 9)] = 0
    return resultado

def resumir_tratamento(mes_inicio_prenatal: pd.Series) -> dict[str, int | float]:
    """Resume a capacidade diagnóstica de construir T sem congelar elegibilidade."""

    tratamento = construir_tratamento_candidato(mes_inicio_prenatal)
    total = len(mes_inicio_prenatal)
    utilizavel = int(tratamento.notna().sum())
    return {
        "n_total": total,
        "n_utilizavel": utilizavel,
        "percentual_utilizavel": round(100 * utilizavel / total, 6) if total else 0.0,
        "n_inicio_ate_terceiro_mes": int(tratamento.eq(1).sum()),
        "n_inicio_apos_terceiro_mes": int(tratamento.eq(0).sum()),
        "n_codigo_99": int(mes_inicio_prenatal.eq("99").sum()),
        "n_missing": int(mes_inicio_prenatal.isna().sum()),
    }

def resumir_outcome(peso: pd.Series) -> dict[str, int | float | None]:
    """Resume Y candidato e mantém extremos como alertas, sem exclusão automática."""

    peso_numerico = pd.to_numeric(peso, errors="coerce")
    valido = peso_numerico.gt(0)
    pesos_validos = peso_numerico.loc[valido]
    total = len(peso)
    n_valido = int(valido.sum())
    n_baixo_peso = int(pesos_validos.lt(2500).sum())
    return {
        "n_total": total,
        "n_valido": n_valido,
        "percentual_valido": round(100 * n_valido / total, 6) if total else 0.0,
        "n_baixo_peso": n_baixo_peso,
        "prevalencia_baixo_peso_percentual": (
            round(100 * n_baixo_peso / n_valido, 6) if n_valido else None
        ),
        "n_missing_invalido": total - n_valido,
        "peso_minimo_gramas": float(pesos_validos.min()) if n_valido else None,
        "peso_maximo_gramas": float(pesos_validos.max()) if n_valido else None,
        "n_abaixo_500g": int(pesos_validos.lt(500).sum()),
        "n_acima_6000g": int(pesos_validos.gt(6000).sum()),
    }

def _identificador_sql(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'

def _percentual(parte: int, total: int) -> float:
    return round(100 * parte / total, 6) if total else 0.0

def gerar_auditoria_parquet(caminho_parquet: str | Path) -> dict[str, Any]:
    """Audita o Parquet com consultas colunares e resultados JSON-serializáveis."""

    caminho = Path(caminho_parquet).resolve()
    if not caminho.is_file():
        raise FileNotFoundError(f"Parquet não encontrado: {caminho}")
    caminho_sql = caminho.as_posix().replace("'", "''")
    conexao = duckdb.connect()
    conexao.execute(f"CREATE VIEW dados AS SELECT * FROM read_parquet('{caminho_sql}')")
    descricao = conexao.execute("DESCRIBE dados").fetchall()
    colunas = [linha[0] for linha in descricao]
    total = int(conexao.execute("SELECT count(*) FROM dados").fetchone()[0])

    schema_auditado: list[dict[str, Any]] = []
    for nome in colunas:
        coluna = _identificador_sql(nome)
        missing, distintos = conexao.execute(
            f"SELECT count(*) - count({coluna}), count(DISTINCT {coluna}) FROM dados"
        ).fetchone()
        exemplos = [
            linha[0]
            for linha in conexao.execute(
                f"""
                SELECT {coluna}
                FROM dados
                WHERE {coluna} IS NOT NULL
                GROUP BY {coluna}
                ORDER BY count(*) DESC, {coluna}
                LIMIT 5
                """
            ).fetchall()
        ]
        campo = nome.upper()
        codigo_especial = CODIGOS_ESPECIAIS_DOCUMENTADOS.get(campo)
        if campo == "MESPRENAT":
            codigo_especial = "99 observado; não documentado no PDF oficial 1996-2019"
        schema_auditado.append(
            {
                "coluna": nome,
                "descricao_oficial": DESCRICOES_OFICIAIS.get(
                    campo, "Não localizada no dicionário oficial 1996-2019."
                ),
                "tipo_observado": "texto (VARCHAR; preservado do CSV)",
                "exemplos_frequentes": exemplos,
                "valores_distintos": int(distintos),
                "n_missing": int(missing),
                "percentual_missing": _percentual(int(missing), total),
                "codigos_especiais_documentados": codigo_especial,
                "papel_analitico_provisorio": papel_analitico(nome),
                "grupo_temporal_provisorio": grupo_temporal(nome),
            }
        )

    identificador: dict[str, Any]
    if "contador" in colunas:
        n_preenchido, n_distintos = conexao.execute(
            'SELECT count("contador"), count(DISTINCT "contador") FROM dados'
        ).fetchone()
        identificador = {
            "coluna": "contador",
            "n_preenchido": int(n_preenchido),
            "n_distintos": int(n_distintos),
            "n_missing": total - int(n_preenchido),
            "n_duplicados": int(n_preenchido) - int(n_distintos),
            "contador_unico": int(n_preenchido) == total == int(n_distintos),
            "observacao": (
                "Identificador técnico único no arquivo; sua estabilidade entre versões "
                "não foi estabelecida pelo dicionário."
            ),
        }
    else:
        identificador = {"coluna": None, "contador_unico": False}

    tratamento_linha = conexao.execute(
        """
        SELECT
            count(*),
            count_if(try_cast(MESPRENAT AS INTEGER) BETWEEN 1 AND 9),
            count_if(try_cast(MESPRENAT AS INTEGER) BETWEEN 1 AND 3),
            count_if(try_cast(MESPRENAT AS INTEGER) BETWEEN 4 AND 9),
            count_if(MESPRENAT = '99'),
            count_if(MESPRENAT IS NULL),
            count_if(
                MESPRENAT IS NOT NULL
                AND MESPRENAT <> '99'
                AND NOT coalesce(try_cast(MESPRENAT AS INTEGER) BETWEEN 1 AND 9, false)
            )
        FROM dados
        """
    ).fetchone()
    dominio_tratamento = {
        str(valor): int(n)
        for valor, n in conexao.execute(
            """
            SELECT coalesce(MESPRENAT, '<MISSING>'), count(*)
            FROM dados
            GROUP BY MESPRENAT
            ORDER BY MESPRENAT NULLS LAST
            """
        ).fetchall()
    }
    tratamento = {
        "coluna": "MESPRENAT",
        "semantica_oficial": DESCRICOES_OFICIAIS["MESPRENAT"],
        "n_total": int(tratamento_linha[0]),
        "n_utilizavel": int(tratamento_linha[1]),
        "percentual_utilizavel": _percentual(int(tratamento_linha[1]), total),
        "n_inicio_ate_terceiro_mes": int(tratamento_linha[2]),
        "n_inicio_apos_terceiro_mes": int(tratamento_linha[3]),
        "n_codigo_99": int(tratamento_linha[4]),
        "n_missing": int(tratamento_linha[5]),
        "n_outros_invalidos": int(tratamento_linha[6]),
        "dominio_observado": dominio_tratamento,
        "regra_diagnostica": "T=1 para meses 1-3; T=0 para meses 4-9; 99/missing fora de T.",
        "questao_aberta": (
            "O PDF 1996-2019 não documenta o código 99 para MESPRENAT; "
            "sua interpretação como ignorado é operacional e deve ser confirmada."
        ),
    }

    outcome_linha = conexao.execute(
        """
        WITH pesos AS (
            SELECT try_cast(PESO AS DOUBLE) AS peso
            FROM dados
        )
        SELECT
            count(*),
            count_if(peso > 0),
            count_if(peso > 0 AND peso < 2500),
            count_if(peso IS NULL OR peso <= 0),
            min(peso) FILTER (WHERE peso > 0),
            max(peso) FILTER (WHERE peso > 0),
            quantile_cont(peso, 0.01) FILTER (WHERE peso > 0),
            quantile_cont(peso, 0.05) FILTER (WHERE peso > 0),
            quantile_cont(peso, 0.50) FILTER (WHERE peso > 0),
            quantile_cont(peso, 0.95) FILTER (WHERE peso > 0),
            quantile_cont(peso, 0.99) FILTER (WHERE peso > 0),
            count_if(peso > 0 AND peso < 500),
            count_if(peso > 6000)
        FROM pesos
        """
    ).fetchone()
    n_valido = int(outcome_linha[1])
    n_baixo = int(outcome_linha[2])
    outcome = {
        "coluna": "PESO",
        "semantica_oficial": DESCRICOES_OFICIAIS["PESO"],
        "unidade": "gramas",
        "n_total": int(outcome_linha[0]),
        "n_valido": n_valido,
        "percentual_valido": _percentual(n_valido, total),
        "n_baixo_peso": n_baixo,
        "prevalencia_baixo_peso_percentual": _percentual(n_baixo, n_valido),
        "n_missing_invalido": int(outcome_linha[3]),
        "peso_minimo_gramas": float(outcome_linha[4]),
        "peso_maximo_gramas": float(outcome_linha[5]),
        "percentis_gramas": {
            "p01": float(outcome_linha[6]),
            "p05": float(outcome_linha[7]),
            "p50": float(outcome_linha[8]),
            "p95": float(outcome_linha[9]),
            "p99": float(outcome_linha[10]),
        },
        "n_abaixo_500g_alerta": int(outcome_linha[11]),
        "n_acima_6000g_alerta": int(outcome_linha[12]),
        "regra_diagnostica": "Y=1 para peso numérico positivo inferior a 2.500 g.",
        "questao_aberta": (
            "Pesos extremos são mantidos no diagnóstico bruto e sinalizados; "
            "uma regra de exclusão biológica exige decisão metodológica posterior."
        ),
    }

    missing_ordenado = sorted(
        (
            {
                "coluna": item["coluna"],
                "n_missing": item["n_missing"],
                "percentual_missing": item["percentual_missing"],
            }
            for item in schema_auditado
        ),
        key=lambda item: (-item["percentual_missing"], item["coluna"]),
    )
    grupos = {
        "A_provavelmente_pre_tratamento": sorted(
            item["coluna"]
            for item in schema_auditado
            if item["grupo_temporal_provisorio"] == "A. provavelmente pré-tratamento"
        ),
        "B_provavelmente_pos_tratamento_mediadora": sorted(
            item["coluna"]
            for item in schema_auditado
            if item["grupo_temporal_provisorio"]
            == "B. provavelmente pós-tratamento/mediadora"
        ),
        "C_temporalidade_ou_papel_duvidoso": sorted(
            item["coluna"]
            for item in schema_auditado
            if item["grupo_temporal_provisorio"]
            == "C. temporalidade ou papel causal duvidoso"
        ),
    }
    conexao.close()
    return {
        "dimensoes": {"registros": total, "colunas": len(colunas)},
        "granularidade_candidata": "um registro de nascido vivo",
        "identificador": identificador,
        "tratamento_candidato": tratamento,
        "outcome_candidato": outcome,
        "covariaveis_por_temporalidade": grupos,
        "n_x_pre_tratamento_candidatos": len(grupos["A_provavelmente_pre_tratamento"]),
        "principais_campos_missing": missing_ordenado[:15],
        "schema_auditado": schema_auditado,
    }

def _markdown_auditoria(auditoria: dict[str, Any]) -> str:
    tratamento = auditoria["tratamento_candidato"]
    outcome = auditoria["outcome_candidato"]
    grupos = auditoria["covariaveis_por_temporalidade"]
    linhas = [
        "# Auditoria de Viabilidade - SINASC 2024",
        "",
        "> Esta auditoria é descritiva. Nenhum efeito causal foi estimado.",
        "",
        "## Dimensões e granularidade",
        "",
        f"- Registros: {auditoria['dimensoes']['registros']:,}.",
        f"- Colunas: {auditoria['dimensoes']['colunas']}.",
        f"- Granularidade candidata: {auditoria['granularidade_candidata']}.",
        f"- `contador` único: {auditoria['identificador'].get('contador_unico')}.",
        "",
        "## Tratamento candidato",
        "",
        f"- Campo: `{tratamento['coluna']}` - {tratamento['semantica_oficial']}",
        f"- Utilizável para meses 1-9: {tratamento['n_utilizavel']:,} "
        f"({tratamento['percentual_utilizavel']:.3f}%).",
        f"- Início até o 3º mês: {tratamento['n_inicio_ate_terceiro_mes']:,}.",
        f"- Início após o 3º mês: {tratamento['n_inicio_apos_terceiro_mes']:,}.",
        f"- Código 99: {tratamento['n_codigo_99']:,}; missing: {tratamento['n_missing']:,}.",
        f"- QUESTAO_ABERTA: {tratamento['questao_aberta']}",
        "",
        "## Outcome candidato",
        "",
        f"- Campo: `{outcome['coluna']}` em {outcome['unidade']}.",
        f"- Pesos válidos: {outcome['n_valido']:,} ({outcome['percentual_valido']:.3f}%).",
        f"- Baixo peso (<2.500 g): {outcome['n_baixo_peso']:,} "
        f"({outcome['prevalencia_baixo_peso_percentual']:.3f}%).",
        f"- Faixa observada: {outcome['peso_minimo_gramas']:.0f} a "
        f"{outcome['peso_maximo_gramas']:.0f} g.",
        f"- Alertas: {outcome['n_abaixo_500g_alerta']:,} abaixo de 500 g e "
        f"{outcome['n_acima_6000g_alerta']:,} acima de 6.000 g.",
        f"- QUESTAO_ABERTA: {outcome['questao_aberta']}",
        "",
        "## Covariáveis por temporalidade",
        "",
    ]
    for titulo, campos in grupos.items():
        linhas.append(f"### {titulo.replace('_', ' ')}")
        linhas.append("")
        linhas.append(", ".join(f"`{campo}`" for campo in campos) or "Nenhuma.")
        linhas.append("")
    linhas.extend(
        [
            "## Gate de viabilidade",
            "",
            "**VIÁVEL_COM_RESSALVAS**",
            "",
            "T e Y são construíveis para a grande maioria dos registros e há volume e "
            "covariáveis pré-tratamento candidatas. As ressalvas materiais são o dicionário "
            "oficial limitado a 2019, o código 99 de `MESPRENAT` não documentado nesse PDF, "
            "missing de T, extremos de peso e a ausência, nesta fase, de uma estratégia causal "
            "final capaz de resolver confundimento residual.",
            "",
            "Este gate avalia dados e desenho candidato; não valida causalidade.",
        ]
    )
    return "\n".join(linhas) + "\n"

def executar_auditoria_projeto(raiz_projeto: str | Path) -> dict[str, Any]:
    """Executa a auditoria factual e grava apenas diagnósticos pequenos."""

    raiz = Path(raiz_projeto).resolve()
    zip_path = raiz / "data" / "raw" / "SINASC_2024_csv.zip"
    pdf_path = raiz / "data" / "raw" / "SINASC_Estrutura.pdf"
    parquet_path = raiz / "data" / "processed" / "sinasc_2024.parquet"
    auditoria = gerar_auditoria_parquet(parquet_path)
    formato = detectar_formato_csv(zip_path)
    auditoria["fonte"] = {
        "instituicao": "Ministério da Saúde - Portal de Dados Abertos do SUS",
        "recurso": "Nascidos Vivos - 2024",
        "url": "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINASC/csv/SINASC_2024_csv.zip",
        "zip": verificar_arquivo_existente(zip_path),
        "csv_interno": formato.arquivo_interno,
        "csv_bytes_descompactado": 561_812_933,
        "encoding": formato.encoding,
        "separador": formato.separador,
        "dicionario": verificar_arquivo_existente(pdf_path),
        "limitacao_dicionario": "O PDF oficial descreve a estrutura de 1996 a 2019.",
    }
    auditoria["parquet"] = verificar_arquivo_existente(parquet_path)
    auditoria["principais_alertas_qualidade"] = [
        "Dicionário oficial disponível cobre 1996-2019, não uma versão específica de 2024.",
        "Código 99 observado em MESPRENAT não é definido no PDF oficial localizado.",
        "Registros com MESPRENAT missing ou 99 não entram na definição diagnóstica de T.",
        "Pesos extremos são sinalizados, mas não excluídos automaticamente.",
        "Número total de consultas, parto, idade gestacional e características neonatais são pós-tratamento ou mediadoras potenciais.",
        "Dados observacionais não resolvem, por si, confundimento residual.",
    ]
    auditoria["tratamento_candidato_identificavel"] = True
    auditoria["outcome_identificavel"] = True
    auditoria["gate_viabilidade"] = "VIÁVEL_COM_RESSALVAS"
    auditoria["efeito_causal_estimado"] = False

    diagnosticos = raiz / "outputs" / "diagnostics"
    metodologia = raiz / "docs" / "methodology"
    diagnosticos.mkdir(parents=True, exist_ok=True)
    metodologia.mkdir(parents=True, exist_ok=True)
    (diagnosticos / "auditoria_viabilidade_sinasc_2024.json").write_text(
        json.dumps(auditoria, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (diagnosticos / "auditoria_schema_sinasc_2024.json").write_text(
        json.dumps(auditoria["schema_auditado"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (metodologia / "AUDITORIA_VIABILIDADE.md").write_text(
        _markdown_auditoria(auditoria), encoding="utf-8"
    )
    return auditoria


SEMENTE = 20240925

NUMERICAS_PROPENSITY = ("IDADEMAE_NUM",)

CATEGORICAS_PROPENSITY = tuple(
    coluna for coluna in COLUNAS_PROPENSITY_PRINCIPAL if coluna not in NUMERICAS_PROPENSITY
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

def executar_auditoria_amostra(raiz: Path, executar_propensity: bool = True) -> dict[str, Any]:
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
