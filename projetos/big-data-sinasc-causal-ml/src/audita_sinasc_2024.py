"""Regras diagnósticas, não causais, para a auditoria do SINASC 2024."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.baixa_dados_sinasc import verificar_arquivo_existente
from src.carrega_sinasc import detectar_formato_csv
from src.dicionario_sinasc import (
    CODIGOS_ESPECIAIS_DOCUMENTADOS,
    DESCRICOES_OFICIAIS,
    X_PROVAVEL_PRE_TRATAMENTO,
    grupo_temporal,
    papel_analitico,
)


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


if __name__ == "__main__":
    resultado = executar_auditoria_projeto(Path(__file__).resolve().parents[1])
    print(json.dumps({
        "dimensoes": resultado["dimensoes"],
        "tratamento": resultado["tratamento_candidato"],
        "outcome": resultado["outcome_candidato"],
        "gate": resultado["gate_viabilidade"],
    }, ensure_ascii=False, indent=2))
