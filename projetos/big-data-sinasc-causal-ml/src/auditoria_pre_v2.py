"""Auditoria empírica pré-V2 da definição temporal de MESPRENAT (notebook 09c).

Módulo DIAGNÓSTICO e NÃO CAUSAL. Não ajusta modelos, não calcula propensity,
não calcula AIPW, não escolhe V2 e não altera a V1 (``MESPRENAT`` 1-3 vs 4-9).
Lê os Parquets anuais somente pelas colunas necessárias, agrega em DuckDB um
ano por vez e devolve apenas tabelas agregadas. Nenhum registro é excluído,
imputado ou reclassificado: 99, vazio e outros códigos inválidos permanecem
categorias próprias e nunca entram em T.

Idade gestacional (SEMAGESTAC/GESTACAO) é usada exclusivamente como variável
diagnóstica da estrutura temporal da exposição, nunca como ajuste.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Contrato fixo da auditoria (registrado ANTES da leitura dos resultados D1-D8)
# ---------------------------------------------------------------------------

VERSAO_AUDITORIA = "pre-v2-1 (critérios fixados em 2026-10-01 antes das agregações D1-D8)"
ANOS_AUDITORIA = tuple(range(2014, 2025))

MESES_VALIDOS = tuple(f"{m:02d}" for m in range(1, 10))
CATEGORIAS_MESPRENAT = MESES_VALIDOS + ("99", "VAZIO", "OUTRO_INVALIDO")
STATUS_MESPRENAT = ("CONHECIDO", "99", "VAZIO", "OUTRO_INVALIDO")
GRUPOS_D3 = ("1-3", "4-5", "6", "7-9", "99", "VAZIO", "OUTRO_INVALIDO")
FAIXAS_IG = ("<22", "22-26", "27-31", "32-36", "37-41", ">=42", "AUSENTE_OU_INVALIDA")
FAIXAS_IG_CURTAS_A_TERMO = ("<22", "22-26", "27-31", "32-36", "37-41")
CATEGORIAS_CONSPRENAT = ("0", "01-03", "04-06", "07-98", "99", "VAZIO", "OUTRO_INVALIDO")

# Rótulos de procedência semântica dos códigos.
ROTULO_99_MESPRENAT = "CODIFICACAO_OPERACIONAL_OBSERVADA"
ROTULO_99_CONSPRENAT = "CODIFICACAO_OPERACIONAL_OBSERVADA"

# Controles da V1 e das sensibilidades candidatas. Nenhuma é estimada aqui.
ALTERNATIVAS_CONTROLE: dict[str, tuple[int, ...]] = {
    "A_V1_4_9": (4, 5, 6, 7, 8, 9),
    "B_4_6": (4, 5, 6),
    "C_4_5": (4, 5),
}
MESES_TRATADOS_V1 = (1, 2, 3)

# Leituras mecânicas mês -> semanas. NÃO são regra oficial: o Manual DNV 2022 não
# traz equivalência mês/semana. Servem para classificar combinações como
# POTENCIALMENTE incompatíveis, nunca como impossíveis.
LEITURAS_MES_SEMANA = {
    "L1": {"semanas_por_mes": 4.0, "deslocamento_meses": 1,
           "descricao": "mês k começa em 4·(k-1) semanas completas (leitura permissiva)"},
    "L2": {"semanas_por_mes": 4.345, "deslocamento_meses": 1,
           "descricao": "mês k começa em 4,345·(k-1) semanas (mês civil médio de 30,4 dias)"},
    "L1_TOLERANCIA": {"semanas_por_mes": 4.0, "deslocamento_meses": 2,
                      "descricao": "L1 com tolerância de um mês a favor do registro: 4·(k-2) semanas"},
}
STATUS_CONSISTENCIA = (
    "POTENCIALMENTE_INCOMPATIVEL_MESMO_COM_TOLERANCIA",
    "POTENCIALMENTE_INCOMPATIVEL_L1",
    "POTENCIALMENTE_INCOMPATIVEL_SOMENTE_L2",
    "SEM_INCOMPATIBILIDADE_DETECTADA",
)
REGRA_CONSISTENCIA = (
    "Semana completa S implica duração G em [S, S+1). Mês k é potencialmente incompatível na "
    "leitura X se S+1 <= início_X(k), isto é, a gestação terminou antes de o mês k começar. "
    "início_L1(k)=4(k-1); início_L2(k)=4,345(k-1); início_L1_TOLERANCIA(k)=4(k-2). "
    "Sem regra oficial mês->semana: nada é classificado como impossível."
)

# Convenções numéricas reutilizadas do projeto (não criadas após os resultados).
SMD_REFERENCIA = 0.10           # contrato_diagnostico_temporal.json, limite smd_abs
CELULA_MINIMA = 100             # contrato_diagnostico_temporal.json, celula_minima_por_grupo
MAIORIA = 0.50                  # maioria simples, usada só em regras de bloqueio
LIMITE_VIABILIDADE_FAIXA = 22   # limite inferior da 2ª faixa descritiva (semanas)
# Triagem descritiva do D5 (sem base científica; só lista UF-anos para leitura):
# proporção de MESPRENAT desconhecido >= 2x a nacional do mesmo ano, em UF-ano com >= 100 registros.
FATOR_DISCREPANCIA_UF = 2.0

INDICADORES_HEAPING = {
    "p_mes": "n_mes / n_meses_1_9",
    "razao_3_4": "n_03 / n_04",
    "razao_2_3": "n_02 / n_03",
    "vizinhanca_3": "n_03 / ((n_02 + n_04) / 2)",
    "vizinhanca_2": "n_02 / ((n_01 + n_03) / 2)",
    "salto_3_4_pp": "100 * (p_03 - p_04)",
}

CRITERIOS_GATES: dict[str, dict[str, str]] = {
    "G1": {
        "pergunta": "A codificação de 'sem pré-natal' é suficientemente estável para permitir landmark?",
        "populacao": "ELEGIVEL (gestação única, PESO 500-6000 g), qualquer MESPRENAT",
        "C1_documental": "Existe semântica oficial para ausência de pré-natal (CONSPRENAT=0, Manual DNV 2022).",
        "C2_ignorado_distinto": "Em todos os anos CONSPRENAT tem categoria de desconhecido (99 ou VAZIO) distinta de 0.",
        "C3_contradicao": "Em todos os anos, < 50% dos registros CONSPRENAT=0 têm MESPRENAT 01-09.",
        "C4_estabilidade_temporal": "A categoria D3 dominante de MESPRENAT entre CONSPRENAT=0 é a mesma em todos os anos.",
        "C5_estabilidade_uf": ("Em toda UF-ano com >= 100 registros CONSPRENAT=0, a categoria dominante é igual "
                               "à nacional do mesmo ano."),
        "BLOQUEADO": "C1, C2 ou C3 falha.",
        "APROVADO": "C1 a C5 verdadeiros.",
        "SINALIZADO": "C1-C3 verdadeiros e C4 ou C5 falha.",
        "PENDENTE": "CONSPRENAT ou MESPRENAT ausente em algum ano.",
        "limite": "Avalia estabilidade da codificação; não demonstra que CONSPRENAT=0 seja ausência real de pré-natal.",
    },
    "G2": {
        "pergunta": "MESPRENAT apresenta inconsistências temporais materiais?",
        "populacao": "ELEGIVEL com MESPRENAT 01-09 e SEMAGESTAC válida",
        "BLOQUEADO": ("Em algum ano, para algum mês k com >= 100 registros com SEMAGESTAC válida, registros "
                      "POTENCIALMENTE_INCOMPATIVEL em L1 (ou com tolerância) são >= 50% desses registros."),
        "SINALIZADO": "Existe ao menos um registro potencialmente incompatível em L1, ou código fora do domínio oficial (ex.: 10).",
        "APROVADO": "Nenhum registro potencialmente incompatível em L1 e nenhum código fora do domínio.",
        "PENDENTE": "SEMAGESTAC ausente.",
        "limite": "L2 é reportada mas não decide; nenhuma combinação é chamada de impossível.",
    },
    "G3": {
        "pergunta": "O missing de MESPRENAT parece diferencial por Y ou X?",
        "populacao": "ELEGIVEL; grupos 99, VAZIO e OUTRO_INVALIDO (este só em anos com N >= 100) versus CONHECIDO",
        "medida": ("|SMD| por nível (Y=BPN, escolaridade, raça/cor, situação conjugal, paridade, perdas "
                   "fetais, UF, idade ausente) e SMD contínua de idade; referência 0,10 do contrato 08."),
        "APROVADO": "Todo |SMD| < 0,10 em todos os anos e grupos.",
        "SINALIZADO": "Algum |SMD| >= 0,10 (separando se por Y, por X ou ambos).",
        "BLOQUEADO": "Não aplicável: diferencial de missing não bloqueia, descreve seleção.",
        "PENDENTE": "Nenhum grupo desconhecido com N >= 100 em nenhum ano.",
        "limite": "Diagnóstico de seleção/missingness; não é balanceamento causal.",
    },
    "G4": {
        "pergunta": "Qual parcela do controle V1 está em meses particularmente vulneráveis ao truncamento?",
        "populacao": "População principal V1 (ELEGIVEL e MESPRENAT 01-09), T=0",
        "meses_vulneraveis": "07-09 (exigem duração >= 24/28/32 semanas em L1); 6 reportado à parte",
        "APROVADO": "Parcela 07-09 igual a zero em todos os anos.",
        "SINALIZADO": "Parcela 07-09 positiva em algum ano (magnitude reportada, sem limiar).",
        "PENDENTE": "Quantificação impossível.",
        "evidencia_auxiliar": ("Padrão de truncamento P1: proporção 07-09 entre meses conhecidos não decrescente "
                               "em <22, 22-26, 27-31, 32-36, 37-41; reportado por ano, não decide o gate."),
    },
    "G5": {
        "pergunta": "A alternativa 4-6 reduz substancialmente a região estruturalmente problemática?",
        "metrica_M1": ("M1(X, leitura) = fração dos nascimentos ELEGIVEL com SEMAGESTAC válida tais que "
                       "S+1 <= início_leitura(último mês de controle de X)."),
        "APROVADO": ("(i) início_L1 e início_L2 do último mês de B < 22 semanas e (ii) M1(B) < M1(A) em todos "
                     "os anos, em L1 e L2."),
        "SINALIZADO": "(ii) verdadeiro e (i) falso.",
        "BLOQUEADO": "(ii) falso em algum ano.",
        "PENDENTE": "SEMAGESTAC ausente.",
    },
    "G6": {
        "pergunta": "A alternativa 4-5 reduz ainda mais?",
        "APROVADO": "M1(C) < M1(B) em todos os anos, em L1 e L2.",
        "SINALIZADO": "M1(C) <= M1(B) sempre, com igualdade em algum ano/leitura.",
        "BLOQUEADO": "M1(C) = M1(B) em todos os anos e leituras, ou M1(C) > M1(B) em algum.",
        "PENDENTE": "SEMAGESTAC ausente.",
        "nota": "Custo (controles adicionais excluídos) é reportado e não entra na regra.",
    },
    "G7": {
        "pergunta": "Há evidência empírica suficiente para levar B, C ou D à avaliação metodológica?",
        "B": "pior status entre G5, G2 e G3 (G3 BLOQUEADO não existe).",
        "C": "pior status entre G6, G2 e G3.",
        "D": ("G1 BLOQUEADO -> BLOQUEADO; G1 SINALIZADO ou PENDENTE -> PENDENTE; G1 APROVADO -> pior entre "
              "SINALIZADO, G2 e G3 (validade de CONSPRENAT=0 não é demonstrável)."),
        "ordem_gravidade": "BLOQUEADO > PENDENTE > SINALIZADO > APROVADO",
        "G7": "melhor status entre B, C e D; avançar = APROVADO ou SINALIZADO.",
        "limite": "G7 não escolhe V2; nenhum valor de AIPW de B, C ou D é calculado ou consultado.",
    },
}

ORDEM_GRAVIDADE = {"APROVADO": 0, "SINALIZADO": 1, "PENDENTE": 2, "BLOQUEADO": 3}

# Colunas lidas do Parquet (nomes sem diferenciar caixa; 2016 usa minúsculas).
COLUNAS_LIDAS = (
    "MESPRENAT", "CONSPRENAT", "SEMAGESTAC", "GESTACAO", "KOTELCHUCK", "TPMETESTIM",
    "DTULTMENST", "CODMUNRES", "PESO", "GRAVIDEZ", "IDADEMAE", "ESCMAE2010",
    "RACACORMAE", "ESTCIVMAE", "PARIDADE", "QTDFILMORT",
)
CAMPOS_INVENTARIO = COLUNAS_LIDAS + ("CONSULTAS", "QTDGESTANT", "QTDFILVIVO", "CONTADOR", "DTNASC")

VARIAVEIS_PERFIL = ("Y_BAIXO_PESO", "FAIXA_IG", "ESCOLARIDADE_MAE", "RACA_COR_MAE",
                    "SITUACAO_CONJUGAL", "PARIDADE_CAT", "PERDAS_FETAIS_CAT", "UF_RESIDENCIA",
                    "IDADE_AUSENTE")
VARIAVEIS_X_G3 = ("ESCOLARIDADE_MAE", "RACA_COR_MAE", "SITUACAO_CONJUGAL", "PARIDADE_CAT",
                  "PERDAS_FETAIS_CAT", "UF_RESIDENCIA", "IDADE_AUSENTE")


def hash_criterios() -> str:
    """SHA-256 do texto dos critérios, das leituras e das convenções numéricas."""

    conteudo = {
        "versao": VERSAO_AUDITORIA, "criterios": CRITERIOS_GATES, "leituras": LEITURAS_MES_SEMANA,
        "regra_consistencia": REGRA_CONSISTENCIA, "alternativas": ALTERNATIVAS_CONTROLE,
        "faixas_ig": FAIXAS_IG, "indicadores_heaping": INDICADORES_HEAPING,
        "smd": SMD_REFERENCIA, "celula_minima": CELULA_MINIMA, "maioria": MAIORIA,
        "limite_viabilidade_faixa": LIMITE_VIABILIDADE_FAIXA,
        "fator_discrepancia_uf": FATOR_DISCREPANCIA_UF,
    }
    texto = json.dumps(conteudo, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# SQL de derivação (um registro de entrada -> um registro derivado, sem filtro)
# ---------------------------------------------------------------------------

def _texto(campo: str) -> str:
    return f"trim(CAST({campo} AS VARCHAR))"


def _vazio(campo: str) -> str:
    return f"({campo} IS NULL OR {_texto(campo)} = '')"


def sql_base_derivada(fonte: str, ano: int) -> str:
    """SELECT com colunas diagnósticas derivadas; ``fonte`` é tabela ou read_parquet(...).

    Não filtra linhas: o número de linhas de saída é exatamente o da fonte.
    """

    mes_int = "try_cast(MESPRENAT AS INTEGER)"
    sem_int = "try_cast(SEMAGESTAC AS INTEGER)"
    cons_int = "try_cast(CONSPRENAT AS INTEGER)"
    peso_int = "try_cast(PESO AS INTEGER)"
    return f"""
    SELECT
        CAST({int(ano)} AS INTEGER) AS ano,
        CASE WHEN regexp_full_match(CAST(CODMUNRES AS VARCHAR), '[0-9]{{6}}')
             THEN substr(CAST(CODMUNRES AS VARCHAR), 1, 2) ELSE 'IGNORADO' END AS uf,
        CASE WHEN {_vazio('MESPRENAT')} THEN 'VAZIO'
             WHEN {mes_int} BETWEEN 1 AND 9 THEN lpad(CAST({mes_int} AS VARCHAR), 2, '0')
             WHEN {mes_int} = 99 THEN '99'
             ELSE 'OUTRO_INVALIDO' END AS mes,
        CASE WHEN {sem_int} BETWEEN 0 AND 98 THEN {sem_int} END AS semanas,
        CASE WHEN {_vazio('SEMAGESTAC')} THEN 'VAZIO'
             WHEN {sem_int} BETWEEN 0 AND 98 THEN 'VALIDA' ELSE 'INVALIDA' END AS semanas_status,
        CASE WHEN NOT ({sem_int} BETWEEN 0 AND 98) OR {sem_int} IS NULL THEN 'AUSENTE_OU_INVALIDA'
             WHEN {sem_int} < 22 THEN '<22'
             WHEN {sem_int} <= 26 THEN '22-26'
             WHEN {sem_int} <= 31 THEN '27-31'
             WHEN {sem_int} <= 36 THEN '32-36'
             WHEN {sem_int} <= 41 THEN '37-41'
             ELSE '>=42' END AS faixa_ig,
        CASE WHEN {_vazio('GESTACAO')} THEN 'VAZIO' ELSE {_texto('GESTACAO')} END AS gestacao,
        CASE WHEN {_vazio('CONSPRENAT')} THEN 'VAZIO'
             WHEN {cons_int} = 0 THEN '0'
             WHEN {cons_int} BETWEEN 1 AND 3 THEN '01-03'
             WHEN {cons_int} BETWEEN 4 AND 6 THEN '04-06'
             WHEN {cons_int} BETWEEN 7 AND 98 THEN '07-98'
             WHEN {cons_int} = 99 THEN '99'
             ELSE 'OUTRO_INVALIDO' END AS consprenat,
        CASE WHEN {_vazio('KOTELCHUCK')} THEN 'VAZIO' ELSE {_texto('KOTELCHUCK')} END AS kotelchuck,
        CASE WHEN {_vazio('TPMETESTIM')} THEN 'VAZIO' ELSE {_texto('TPMETESTIM')} END AS tpmetestim,
        CASE WHEN {_vazio('DTULTMENST')} THEN 'AUSENTE'
             WHEN try_strptime({_texto('DTULTMENST')}, '%d%m%Y') IS NOT NULL THEN 'PRESENTE_VALIDA'
             ELSE 'PRESENTE_INVALIDA' END AS dum,
        coalesce(try_cast(GRAVIDEZ AS INTEGER) = 1 AND {peso_int} BETWEEN 500 AND 6000, false) AS elegivel,
        CASE WHEN {peso_int} BETWEEN 500 AND 6000 THEN CAST({peso_int} < 2500 AS INTEGER) END AS y,
        CASE WHEN try_cast(IDADEMAE AS INTEGER) BETWEEN 10 AND 59
             THEN try_cast(IDADEMAE AS DOUBLE) END AS idade,
        CASE WHEN try_cast(ESCMAE2010 AS INTEGER) = 9 OR ESCMAE2010 IS NULL
             THEN 'IGNORADO' ELSE CAST(try_cast(ESCMAE2010 AS INTEGER) AS VARCHAR) END AS escolaridade,
        CASE WHEN try_cast(RACACORMAE AS INTEGER) = 9 OR RACACORMAE IS NULL
             THEN 'IGNORADO' ELSE CAST(try_cast(RACACORMAE AS INTEGER) AS VARCHAR) END AS raca,
        CASE WHEN try_cast(ESTCIVMAE AS INTEGER) = 9 OR ESTCIVMAE IS NULL
             THEN 'IGNORADO' ELSE CAST(try_cast(ESTCIVMAE AS INTEGER) AS VARCHAR) END AS estciv,
        CASE WHEN try_cast(PARIDADE AS INTEGER) IN (9, 99) OR PARIDADE IS NULL
             THEN 'IGNORADO' ELSE CAST(try_cast(PARIDADE AS INTEGER) AS VARCHAR) END AS paridade,
        CASE WHEN try_cast(QTDFILMORT AS INTEGER) = 0 THEN '0'
             WHEN try_cast(QTDFILMORT AS INTEGER) = 1 THEN '1'
             WHEN try_cast(QTDFILMORT AS INTEGER) BETWEEN 2 AND 98 THEN '2_OU_MAIS'
             ELSE 'IGNORADO' END AS perdas
    FROM {fonte}
    """


def fonte_parquet(caminho: str | Path) -> str:
    """Leitura seletiva de colunas: só os campos necessários saem do Parquet."""

    texto = Path(caminho).as_posix().replace("'", "''")
    colunas = ", ".join(COLUNAS_LIDAS)
    return f"(SELECT {colunas} FROM read_parquet('{texto}'))"


# Agregações (uma leitura do Parquet por ano; todas rodam sobre a tabela temporária).
CUBOS_SQL: dict[str, str] = {
    "ig_uf": "SELECT ano, uf, elegivel, mes, faixa_ig, count(*) AS n FROM base GROUP BY ALL",
    "semanas": ("SELECT ano, elegivel, mes, semanas_status, semanas, count(*) AS n "
                "FROM base GROUP BY ALL"),
    "gestacao": "SELECT ano, elegivel, mes, gestacao, faixa_ig, count(*) AS n FROM base GROUP BY ALL",
    "consprenat": "SELECT ano, uf, elegivel, consprenat, mes, count(*) AS n FROM base GROUP BY ALL",
    "processo": ("SELECT ano, elegivel, mes, tpmetestim, dum, semanas_status, count(*) AS n "
                 "FROM base GROUP BY ALL"),
    "kotelchuck": "SELECT ano, elegivel, kotelchuck, consprenat, mes, count(*) AS n FROM base GROUP BY ALL",
    "perfil_categorico": " UNION ALL ".join(
        f"SELECT ano, mes, '{nome}' AS variavel, CAST({expr} AS VARCHAR) AS nivel, count(*) AS n "
        f"FROM base WHERE elegivel GROUP BY ALL"
        for nome, expr in (
            ("Y_BAIXO_PESO", "y"), ("FAIXA_IG", "faixa_ig"), ("ESCOLARIDADE_MAE", "escolaridade"),
            ("RACA_COR_MAE", "raca"), ("SITUACAO_CONJUGAL", "estciv"), ("PARIDADE_CAT", "paridade"),
            ("PERDAS_FETAIS_CAT", "perdas"), ("UF_RESIDENCIA", "uf"),
            ("IDADE_AUSENTE", "CASE WHEN idade IS NULL THEN '1' ELSE '0' END"),
        )
    ),
    "perfil_numerico": ("SELECT ano, mes, count(*) AS n, count(idade) AS n_idade, sum(idade) AS soma_idade, "
                        "sum(idade * idade) AS soma2_idade, count(y) AS n_y, sum(y) AS soma_y "
                        "FROM base WHERE elegivel GROUP BY ALL"),
}
DIAGNOSTICOS_POR_CUBO = {
    "ig_uf": ("D1", "D5", "D6", "D7"), "semanas": ("D2", "D7"), "gestacao": ("D1",),
    "consprenat": ("D3",), "processo": ("D6",), "kotelchuck": ("D8",),
    "perfil_categorico": ("D4", "D7"), "perfil_numerico": ("D4", "D7"),
}


def agregar_fonte(con: duckdb.DuckDBPyConnection, fonte: str, ano: int) -> tuple[dict[str, pd.DataFrame], dict[str, float]]:
    """Materializa a base derivada uma vez e executa todos os cubos; devolve tempos por etapa."""

    tempos: dict[str, float] = {}
    inicio = time.perf_counter()
    con.execute(f"CREATE OR REPLACE TEMP TABLE base AS {sql_base_derivada(fonte, ano)}")
    tempos["leitura_derivacao"] = time.perf_counter() - inicio
    cubos = {}
    for nome, sql in CUBOS_SQL.items():
        inicio = time.perf_counter()
        cubos[nome] = con.execute(sql).df()
        tempos[nome] = time.perf_counter() - inicio
    n_base = con.execute("SELECT count(*) FROM base").fetchone()[0]
    con.execute("DROP TABLE base")
    cubos["n_base"] = pd.DataFrame({"ano": [ano], "n": [int(n_base)]})
    return cubos, tempos


def agregar_ano(caminho_parquet: str | Path, ano: int, threads: int | None = None):
    with duckdb.connect() as con:
        if threads:
            con.execute(f"SET threads = {int(threads)}")
        return agregar_fonte(con, fonte_parquet(caminho_parquet), ano)


def concatenar_cubos(por_ano: Sequence[Mapping[str, pd.DataFrame]]) -> dict[str, pd.DataFrame]:
    nomes = por_ano[0].keys()
    return {nome: pd.concat([c[nome] for c in por_ano], ignore_index=True) for nome in nomes}


# ---------------------------------------------------------------------------
# Mapeamentos puros
# ---------------------------------------------------------------------------

def status_mesprenat(mes: pd.Series) -> pd.Series:
    """CONHECIDO (01-09), 99, VAZIO ou OUTRO_INVALIDO; nunca converte desconhecido em T."""

    return mes.where(~mes.isin(MESES_VALIDOS), "CONHECIDO")


def grupo_d3(mes: pd.Series) -> pd.Series:
    mapa = {"01": "1-3", "02": "1-3", "03": "1-3", "04": "4-5", "05": "4-5", "06": "6",
            "07": "7-9", "08": "7-9", "09": "7-9"}
    return mes.map(mapa).fillna(mes)


def tratamento_v1(mes: pd.Series) -> pd.Series:
    """T da V1 apenas para leitura descritiva: 1 (01-03), 0 (04-09), NA no resto."""

    t = pd.Series(pd.NA, index=mes.index, dtype="Int8")
    t[mes.isin(MESES_VALIDOS[:3])] = 1
    t[mes.isin(MESES_VALIDOS[3:])] = 0
    return t


def inicio_mes_semanas(mes: int, leitura: str) -> float:
    regra = LEITURAS_MES_SEMANA[leitura]
    return regra["semanas_por_mes"] * max(mes - regra["deslocamento_meses"], 0)


def status_consistencia(semanas: int | float | None, mes: int | None) -> str:
    """Status diagnóstico de (SEMAGESTAC, MESPRENAT); NA quando não avaliável."""

    if semanas is None or mes is None or pd.isna(semanas) or pd.isna(mes) or not 1 <= int(mes) <= 9:
        return "NAO_AVALIAVEL"
    fim = float(semanas) + 1.0
    if fim <= inicio_mes_semanas(int(mes), "L1_TOLERANCIA"):
        return STATUS_CONSISTENCIA[0]
    if fim <= inicio_mes_semanas(int(mes), "L1"):
        return STATUS_CONSISTENCIA[1]
    if fim <= inicio_mes_semanas(int(mes), "L2"):
        return STATUS_CONSISTENCIA[2]
    return STATUS_CONSISTENCIA[3]


def limiar_semanas_afetadas(ultimo_mes: int, leitura: str) -> int:
    """Maior semana completa S com S+1 <= início do mês (nascimentos estruturalmente afetados)."""

    return int(math.floor(inicio_mes_semanas(ultimo_mes, leitura) - 1.0))


def smd_binario(p1: float, p0: float) -> float:
    denominador = math.sqrt((p1 * (1 - p1) + p0 * (1 - p0)) / 2)
    return 0.0 if denominador == 0 else (p1 - p0) / denominador


def smd_continuo(m1: float, v1: float, m0: float, v0: float) -> float:
    denominador = math.sqrt((v1 + v0) / 2)
    return 0.0 if denominador == 0 else (m1 - m0) / denominador


def _com_total(tabela: pd.DataFrame, chaves: Sequence[str], coluna: str, rotulo: Any = "2014-2024") -> pd.DataFrame:
    """Acrescenta linhas agregadas de todos os anos (ano = rótulo) somando contagens."""

    total = tabela.groupby([c for c in chaves if c != "ano"], dropna=False, as_index=False)[coluna].sum()
    total.insert(0, "ano", rotulo)
    saida = tabela.copy()
    saida["ano"] = saida["ano"].astype(str)
    return pd.concat([saida, total], ignore_index=True)


def _proporcao(tabela: pd.DataFrame, grupo: Sequence[str], coluna: str = "n") -> pd.Series:
    soma = tabela.groupby(list(grupo), dropna=False)[coluna].transform("sum")
    return tabela[coluna] / soma.where(soma > 0)


# ---------------------------------------------------------------------------
# D1 - idade gestacional x MESPRENAT
# ---------------------------------------------------------------------------

def d1_tabelas(ig_uf: pd.DataFrame, gestacao: pd.DataFrame) -> dict[str, pd.DataFrame]:
    elegivel = ig_uf[ig_uf["elegivel"]]
    brasil = elegivel.groupby(["ano", "mes", "faixa_ig"], as_index=False)["n"].sum()
    brasil = _com_total(brasil, ["ano", "mes", "faixa_ig"], "n")
    brasil["prop_no_estrato_ig"] = _proporcao(brasil, ["ano", "faixa_ig"])
    brasil["prop_no_mes"] = _proporcao(brasil, ["ano", "mes"])
    conhecidos = brasil[brasil["mes"].isin(MESES_VALIDOS)].copy()
    conhecidos["prop_entre_meses_conhecidos_no_estrato_ig"] = _proporcao(conhecidos, ["ano", "faixa_ig"])
    brasil = brasil.merge(conhecidos[["ano", "mes", "faixa_ig", "prop_entre_meses_conhecidos_no_estrato_ig"]],
                          on=["ano", "mes", "faixa_ig"], how="left")
    brasil.insert(1, "nivel", "BRASIL")

    uf = elegivel.groupby(["ano", "uf", "mes", "faixa_ig"], as_index=False)["n"].sum()
    uf["prop_no_estrato_ig"] = _proporcao(uf, ["ano", "uf", "faixa_ig"])
    uf["prop_no_mes"] = _proporcao(uf, ["ano", "uf", "mes"])

    oficial = gestacao[gestacao["elegivel"]].groupby(["ano", "mes", "gestacao"], as_index=False)["n"].sum()
    oficial = _com_total(oficial, ["ano", "mes", "gestacao"], "n")
    oficial["prop_no_estrato_gestacao"] = _proporcao(oficial, ["ano", "gestacao"])
    oficial["prop_no_mes"] = _proporcao(oficial, ["ano", "mes"])
    cruzada = gestacao[gestacao["elegivel"]].groupby(["ano", "gestacao", "faixa_ig"], as_index=False)["n"].sum()
    cruzada = _com_total(cruzada, ["ano", "gestacao", "faixa_ig"], "n")
    return {"brasil": brasil, "uf": uf, "gestacao_oficial": oficial, "gestacao_x_faixa": cruzada,
            "padrao_truncamento": padrao_truncamento(brasil)}


def padrao_truncamento(d1_brasil: pd.DataFrame) -> pd.DataFrame:
    """Evidência auxiliar P1 (pré-registrada): parcela 07-09 nas faixas curtas até a termo."""

    base = d1_brasil[d1_brasil["mes"].isin(MESES_VALIDOS) & d1_brasil["faixa_ig"].isin(FAIXAS_IG_CURTAS_A_TERMO)]
    tardio = base[base["mes"].isin(("07", "08", "09"))].groupby(["ano", "faixa_ig"])["n"].sum()
    total = base.groupby(["ano", "faixa_ig"])["n"].sum()
    tabela = (tardio.reindex(total.index, fill_value=0) / total).rename("prop_07_09").reset_index()
    tabela = tabela.merge(total.rename("n_meses_conhecidos").reset_index(), on=["ano", "faixa_ig"])
    ordem = {f: i for i, f in enumerate(FAIXAS_IG_CURTAS_A_TERMO)}
    tabela["ordem"] = tabela["faixa_ig"].map(ordem)
    tabela = tabela.sort_values(["ano", "ordem"])
    monotono = tabela.groupby("ano")["prop_07_09"].apply(lambda s: bool(np.all(np.diff(s.to_numpy()) >= 0)))
    tabela["P1_nao_decrescente_no_ano"] = tabela["ano"].map(monotono)
    return tabela.drop(columns="ordem").reset_index(drop=True)


# ---------------------------------------------------------------------------
# D2 - consistência MESPRENAT x SEMAGESTAC
# ---------------------------------------------------------------------------

def d2_tabelas(semanas: pd.DataFrame) -> dict[str, pd.DataFrame]:
    base = semanas[semanas["elegivel"] & semanas["mes"].isin(MESES_VALIDOS) & (semanas["semanas_status"] == "VALIDA")]
    matriz = base.groupby(["ano", "semanas", "mes"], as_index=False)["n"].sum()
    matriz = _com_total(matriz, ["ano", "semanas", "mes"], "n")
    matriz["semanas"] = matriz["semanas"].astype(int)
    matriz["prop_na_semana"] = _proporcao(matriz, ["ano", "semanas"])
    matriz["prop_no_mes"] = _proporcao(matriz, ["ano", "mes"])
    matriz["status_diagnostico"] = [status_consistencia(s, int(m)) for s, m in zip(matriz["semanas"], matriz["mes"])]
    matriz["regra"] = REGRA_CONSISTENCIA

    resumo = matriz.groupby(["ano", "mes", "status_diagnostico"], as_index=False)["n"].sum()
    resumo["prop_no_mes"] = _proporcao(resumo, ["ano", "mes"])
    sem_ig = semanas[semanas["elegivel"] & semanas["mes"].isin(MESES_VALIDOS)]
    sem_ig = sem_ig.assign(valida=sem_ig["semanas_status"] == "VALIDA").groupby(["ano", "valida"])["n"].sum()
    return {"matriz": matriz, "resumo_mes": resumo, "cobertura_semagestac": sem_ig.reset_index()}


# ---------------------------------------------------------------------------
# D3 - CONSPRENAT=0 x MESPRENAT
# ---------------------------------------------------------------------------

def _populacoes(tabela: pd.DataFrame, chaves: Sequence[str]) -> pd.DataFrame:
    """BRUTA (todos os registros) e ELEGIVEL (gestação única, PESO 500-6000)."""

    bruta = tabela.groupby(list(chaves), as_index=False)["n"].sum().assign(populacao="BRUTA")
    eleg = tabela[tabela["elegivel"]].groupby(list(chaves), as_index=False)["n"].sum().assign(populacao="ELEGIVEL")
    return pd.concat([bruta, eleg], ignore_index=True)


def d3_tabelas(consprenat: pd.DataFrame) -> dict[str, pd.DataFrame]:
    tabela = consprenat.assign(grupo_mesprenat=grupo_d3(consprenat["mes"]))
    uf = _populacoes(tabela, ["ano", "uf", "consprenat", "grupo_mesprenat"])
    brasil = uf.groupby(["populacao", "ano", "consprenat", "grupo_mesprenat"], as_index=False)["n"].sum()
    brasil["uf"] = "BRASIL"
    longa = pd.concat([brasil, uf], ignore_index=True)
    chave = ["populacao", "ano", "uf"]
    longa["denominador_total"] = longa.groupby(chave)["n"].transform("sum")
    longa["denominador_consprenat"] = longa.groupby(chave + ["consprenat"])["n"].transform("sum")
    longa["denominador_grupo_mesprenat"] = longa.groupby(chave + ["grupo_mesprenat"])["n"].transform("sum")
    longa["prop_no_total"] = longa["n"] / longa["denominador_total"]
    longa["prop_dentro_consprenat"] = longa["n"] / longa["denominador_consprenat"]
    longa["prop_dentro_grupo_mesprenat"] = longa["n"] / longa["denominador_grupo_mesprenat"]
    longa["nivel"] = np.where(longa["uf"] == "BRASIL", "BRASIL", "UF")
    zero = longa[longa["consprenat"] == "0"].copy()
    return {"longa": longa, "consprenat_zero": zero}


# ---------------------------------------------------------------------------
# D4 - perfil dos MESPRENAT desconhecidos (descritivo; SMD de missingness)
# ---------------------------------------------------------------------------

def _perfil_por_grupo(categorico: pd.DataFrame, numerico: pd.DataFrame, coluna_grupo: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    cat = categorico.groupby(["ano", coluna_grupo, "variavel", "nivel"], dropna=False, as_index=False)["n"].sum()
    cat["n_grupo"] = cat.groupby(["ano", coluna_grupo, "variavel"])["n"].transform("sum")
    cat["prop"] = cat["n"] / cat["n_grupo"]
    num = numerico.groupby(["ano", coluna_grupo], as_index=False)[
        ["n", "n_idade", "soma_idade", "soma2_idade", "n_y", "soma_y"]].sum()
    num["idade_media"] = num["soma_idade"] / num["n_idade"]
    num["idade_var"] = (num["soma2_idade"] - num["n_idade"] * num["idade_media"] ** 2) / (num["n_idade"] - 1)
    num["idade_dp"] = np.sqrt(num["idade_var"])
    num["prevalencia_bpn"] = num["soma_y"] / num["n_y"]
    return cat, num


def d4_tabelas(perfil_categorico: pd.DataFrame, perfil_numerico: pd.DataFrame) -> dict[str, pd.DataFrame]:
    cat = perfil_categorico.assign(grupo=status_mesprenat(perfil_categorico["mes"]))
    num = perfil_numerico.assign(grupo=status_mesprenat(perfil_numerico["mes"]))
    cat = _com_total(cat, ["ano", "grupo", "variavel", "nivel"], "n")
    num_total = num.groupby("grupo", as_index=False)[["n", "n_idade", "soma_idade", "soma2_idade", "n_y", "soma_y"]].sum()
    num_total.insert(0, "ano", "2014-2024")
    num = pd.concat([num.assign(ano=num["ano"].astype(str)), num_total], ignore_index=True)
    perfil, numerico = _perfil_por_grupo(cat, num, "grupo")
    perfil["rotulo"] = "DESCRITIVO / NÃO CAUSAL"
    numerico["rotulo"] = "DESCRITIVO / NÃO CAUSAL"
    return {"perfil": perfil, "numerico": numerico, "smd": d4_smd(perfil, numerico)}


def d4_smd(perfil: pd.DataFrame, numerico: pd.DataFrame) -> pd.DataFrame:
    """SMD de cada grupo desconhecido versus CONHECIDO: diagnóstico de seleção, não balanceamento."""

    linhas = []
    for ano, bloco in perfil.groupby("ano"):
        ref = bloco[bloco["grupo"] == "CONHECIDO"].set_index(["variavel", "nivel"])["prop"]
        n_grupo = numerico[numerico["ano"] == ano].set_index("grupo")["n"]
        for grupo in ("99", "VAZIO", "OUTRO_INVALIDO"):
            if n_grupo.get(grupo, 0) < CELULA_MINIMA:
                continue
            alvo = bloco[bloco["grupo"] == grupo].set_index(["variavel", "nivel"])["prop"]
            for (variavel, nivel) in ref.index.union(alvo.index):
                if variavel == "FAIXA_IG" or (variavel == "Y_BAIXO_PESO" and nivel != "1"):
                    continue
                if variavel == "IDADE_AUSENTE" and nivel != "1":
                    continue
                p1, p0 = float(alvo.get((variavel, nivel), 0.0)), float(ref.get((variavel, nivel), 0.0))
                linhas.append({"ano": ano, "grupo": grupo, "variavel": variavel, "nivel": nivel,
                               "prop_grupo": p1, "prop_conhecido": p0, "smd": smd_binario(p1, p0)})
            num = numerico[numerico["ano"] == ano].set_index("grupo")
            linhas.append({"ano": ano, "grupo": grupo, "variavel": "IDADEMAE_NUM", "nivel": "media",
                           "prop_grupo": float(num.loc[grupo, "idade_media"]),
                           "prop_conhecido": float(num.loc["CONHECIDO", "idade_media"]),
                           "smd": smd_continuo(num.loc[grupo, "idade_media"], num.loc[grupo, "idade_var"],
                                               num.loc["CONHECIDO", "idade_media"], num.loc["CONHECIDO", "idade_var"])})
    smd = pd.DataFrame(linhas, columns=["ano", "grupo", "variavel", "nivel", "prop_grupo", "prop_conhecido", "smd"])
    smd["abs_smd"] = smd["smd"].abs()
    smd["tipo"] = np.where(smd["variavel"] == "Y_BAIXO_PESO", "Y", "X")
    smd["rotulo"] = "DIAGNÓSTICO DE SELEÇÃO/MISSINGNESS - NÃO É BALANCEAMENTO CAUSAL"
    return smd


# ---------------------------------------------------------------------------
# D5 - missing de MESPRENAT por ano x UF
# ---------------------------------------------------------------------------

def d5_tabelas(ig_uf: pd.DataFrame) -> pd.DataFrame:
    tabela = ig_uf.assign(status=status_mesprenat(ig_uf["mes"]))
    uf = _populacoes(tabela, ["ano", "uf", "status"])
    brasil = uf.groupby(["populacao", "ano", "status"], as_index=False)["n"].sum().assign(uf="BRASIL")
    longa = pd.concat([brasil, uf], ignore_index=True)
    larga = longa.pivot_table(index=["populacao", "ano", "uf"], columns="status", values="n",
                              aggfunc="sum", fill_value=0).reset_index()
    for status in STATUS_MESPRENAT:
        if status not in larga:
            larga[status] = 0
    larga["denominador"] = larga[list(STATUS_MESPRENAT)].sum(axis=1)
    for status in ("99", "VAZIO", "OUTRO_INVALIDO"):
        larga[f"prop_{status}"] = larga[status] / larga["denominador"]
    larga["prop_desconhecido_total"] = (larga["99"] + larga["VAZIO"] + larga["OUTRO_INVALIDO"]) / larga["denominador"]
    larga.columns.name = None
    larga = larga.rename(columns={s: f"n_{s}" for s in STATUS_MESPRENAT})
    larga["nivel"] = np.where(larga["uf"] == "BRASIL", "BRASIL", "UF")
    nacional = larga[larga["uf"] == "BRASIL"].set_index(["populacao", "ano"])["prop_desconhecido_total"]
    referencia = pd.Series(list(zip(larga["populacao"], larga["ano"]))).map(nacional).to_numpy()
    larga["razao_vs_brasil"] = larga["prop_desconhecido_total"] / referencia
    larga["triagem_discrepante"] = ((larga["nivel"] == "UF") & (larga["denominador"] >= CELULA_MINIMA)
                                    & (larga["razao_vs_brasil"] >= FATOR_DISCREPANCIA_UF))
    return larga


# ---------------------------------------------------------------------------
# D6 - heaping / distribuição 1-9
# ---------------------------------------------------------------------------

def indicadores_heaping(contagens: Mapping[str, float]) -> dict[str, float]:
    n = {m: float(contagens.get(m, 0)) for m in MESES_VALIDOS}
    total = sum(n.values())

    def razao(a: float, b: float) -> float:
        return a / b if b > 0 else float("nan")

    return {
        "n_meses_1_9": total,
        "razao_3_4": razao(n["03"], n["04"]),
        "razao_2_3": razao(n["02"], n["03"]),
        "vizinhanca_3": razao(n["03"], (n["02"] + n["04"]) / 2),
        "vizinhanca_2": razao(n["02"], (n["01"] + n["03"]) / 2),
        "salto_3_4_pp": 100 * (razao(n["03"], total) - razao(n["04"], total)),
    }


def d6_tabelas(ig_uf: pd.DataFrame, processo: pd.DataFrame) -> dict[str, pd.DataFrame]:
    validos = ig_uf[ig_uf["mes"].isin(MESES_VALIDOS)]
    uf = _populacoes(validos, ["ano", "uf", "mes"])
    brasil = uf.groupby(["populacao", "ano", "mes"], as_index=False)["n"].sum().assign(uf="BRASIL")
    dist = pd.concat([brasil, uf], ignore_index=True)
    dist["prop_meses_1_9"] = _proporcao(dist, ["populacao", "ano", "uf"])
    dist["nivel"] = np.where(dist["uf"] == "BRASIL", "BRASIL", "UF")

    def indicadores(tabela: pd.DataFrame, chaves: Sequence[str]) -> pd.DataFrame:
        linhas = []
        for chave, bloco in tabela.groupby(list(chaves)):
            linhas.append({**dict(zip(chaves, chave)), **indicadores_heaping(dict(zip(bloco["mes"], bloco["n"])))})
        return pd.DataFrame(linhas)

    ind = indicadores(dist, ["populacao", "ano", "uf"])
    proc = processo[processo["mes"].isin(MESES_VALIDOS)]
    proc_dum = _populacoes(proc, ["ano", "dum", "mes"])
    ind_dum = indicadores(proc_dum, ["populacao", "ano", "dum"])
    proc_tpm = _populacoes(proc, ["ano", "tpmetestim", "mes"])
    ind_tpm = indicadores(proc_tpm, ["populacao", "ano", "tpmetestim"])
    cruz = _populacoes(processo, ["ano", "dum", "tpmetestim", "semanas_status"])
    cruz["prop_no_ano"] = _proporcao(cruz, ["populacao", "ano"])
    return {"distribuicao": dist, "indicadores": ind, "indicadores_dum": ind_dum,
            "indicadores_tpmetestim": ind_tpm, "dum_tpmetestim": cruz}


# ---------------------------------------------------------------------------
# D7 - populações candidatas A/B/C (descritivo; nenhum efeito)
# ---------------------------------------------------------------------------

def d7_tabelas(ig_uf: pd.DataFrame, semanas: pd.DataFrame, perfil_categorico: pd.DataFrame,
               perfil_numerico: pd.DataFrame) -> dict[str, pd.DataFrame]:
    v1 = ig_uf[ig_uf["elegivel"] & ig_uf["mes"].isin(MESES_VALIDOS)]
    mes_ig = v1.groupby(["ano", "mes", "faixa_ig"], as_index=False)["n"].sum()
    mes_ig = _com_total(mes_ig, ["ano", "mes", "faixa_ig"], "n")
    mes_ig["T_V1"] = tratamento_v1(mes_ig["mes"])
    controles = mes_ig[mes_ig["T_V1"] == 0]

    linhas, ig_linhas, mes_linhas = [], [], []
    for ano, bloco in controles.groupby("ano"):
        n_t0 = bloco["n"].sum()
        por_mes = bloco.groupby("mes")["n"].sum()
        fracoes = {
            "fracao_controle_4_5": por_mes.reindex(["04", "05"], fill_value=0).sum() / n_t0,
            "fracao_controle_4_6": por_mes.reindex(["04", "05", "06"], fill_value=0).sum() / n_t0,
            "fracao_controle_6": por_mes.get("06", 0) / n_t0,
            "fracao_controle_7_9": por_mes.reindex(["07", "08", "09"], fill_value=0).sum() / n_t0,
        }
        for nome, meses in ALTERNATIVAS_CONTROLE.items():
            rotulos = [f"{m:02d}" for m in meses]
            mantidos = bloco[bloco["mes"].isin(rotulos)]
            n_mantidos = int(mantidos["n"].sum())
            linhas.append({"ano": ano, "alternativa": nome, "meses_controle": "-".join(rotulos),
                           "n_controle_v1": int(n_t0), "n_controles_mantidos": n_mantidos,
                           "n_controles_excluidos": int(n_t0 - n_mantidos),
                           "proporcao_mantida": n_mantidos / n_t0, **fracoes})
            ig = mantidos.groupby("faixa_ig")["n"].sum()
            for faixa in FAIXAS_IG:
                ig_linhas.append({"ano": ano, "alternativa": nome, "faixa_ig": faixa,
                                  "n": int(ig.get(faixa, 0)), "prop": ig.get(faixa, 0) / n_mantidos})
            for mes in rotulos:
                mes_linhas.append({"ano": ano, "alternativa": nome, "mes": mes,
                                   "n": int(por_mes.get(mes, 0)), "prop": por_mes.get(mes, 0) / n_mantidos})
    resumo = pd.DataFrame(linhas)
    resumo = resumo.merge(metricas_truncamento(semanas), on=["ano", "alternativa"], how="left")
    return {"resumo": resumo, "idade_gestacional": pd.DataFrame(ig_linhas),
            "mesprenat": pd.DataFrame(mes_linhas), "controle_mes_ig": controles,
            "perfil": d7_perfil(perfil_categorico, perfil_numerico)}


def metricas_truncamento(semanas: pd.DataFrame) -> pd.DataFrame:
    """M1(X, leitura): fração dos nascimentos ELEGIVEL com S válida e S+1 <= início do último mês de X."""

    base = semanas[semanas["elegivel"] & (semanas["semanas_status"] == "VALIDA")]
    por_semana = base.groupby(["ano", "semanas"], as_index=False)["n"].sum()
    por_semana = _com_total(por_semana, ["ano", "semanas"], "n")
    linhas = []
    for ano, bloco in por_semana.groupby("ano"):
        total = bloco["n"].sum()
        for nome, meses in ALTERNATIVAS_CONTROLE.items():
            linha = {"ano": ano, "alternativa": nome}
            for leitura in ("L1", "L2"):
                limite = limiar_semanas_afetadas(max(meses), leitura)
                n_afetados = int(bloco.loc[bloco["semanas"] <= limite, "n"].sum())
                linha[f"semana_maxima_afetada_{leitura}"] = limite
                linha[f"inicio_ultimo_mes_{leitura}"] = inicio_mes_semanas(max(meses), leitura)
                linha[f"n_afetados_{leitura}"] = n_afetados
                linha[f"M1_{leitura}"] = n_afetados / total
            linha["n_nascimentos_semana_valida"] = int(total)
            linhas.append(linha)
    return pd.DataFrame(linhas)


def d7_perfil(perfil_categorico: pd.DataFrame, perfil_numerico: pd.DataFrame) -> pd.DataFrame:
    """Perfil X/Y dos controles mantidos por alternativa; sem contraste com T=1."""

    blocos_cat, blocos_num = [], []
    for nome, meses in ALTERNATIVAS_CONTROLE.items():
        rotulos = [f"{m:02d}" for m in meses]
        blocos_cat.append(perfil_categorico[perfil_categorico["mes"].isin(rotulos)].assign(alternativa=nome))
        blocos_num.append(perfil_numerico[perfil_numerico["mes"].isin(rotulos)].assign(alternativa=nome))
    cat = pd.concat(blocos_cat, ignore_index=True)
    num = pd.concat(blocos_num, ignore_index=True)
    cat = _com_total(cat, ["ano", "alternativa", "variavel", "nivel"], "n")
    num_total = num.groupby("alternativa", as_index=False)[["n", "n_idade", "soma_idade", "soma2_idade", "n_y", "soma_y"]].sum()
    num_total.insert(0, "ano", "2014-2024")
    num = pd.concat([num.assign(ano=num["ano"].astype(str)), num_total], ignore_index=True)
    perfil, numerico = _perfil_por_grupo(cat, num, "alternativa")
    resumo_num = numerico.melt(id_vars=["ano", "alternativa"], value_vars=["idade_media", "idade_dp", "prevalencia_bpn"],
                               var_name="nivel", value_name="prop").assign(variavel="NUMERICO", n=np.nan, n_grupo=np.nan)
    saida = pd.concat([perfil, resumo_num], ignore_index=True)
    saida["rotulo"] = "DESCRITIVO / NÃO CAUSAL - controles mantidos, sem comparação com T=1"
    return saida


# ---------------------------------------------------------------------------
# D8 - KOTELCHUCK
# ---------------------------------------------------------------------------

def d8_tabelas(kotelchuck: pd.DataFrame) -> dict[str, pd.DataFrame]:
    tabela = kotelchuck.assign(grupo_mesprenat=grupo_d3(kotelchuck["mes"]))
    cons = _populacoes(tabela, ["ano", "kotelchuck", "consprenat"])
    cons["prop_dentro_kotelchuck"] = _proporcao(cons, ["populacao", "ano", "kotelchuck"])
    cons["prop_dentro_consprenat"] = _proporcao(cons, ["populacao", "ano", "consprenat"])
    mes = _populacoes(tabela, ["ano", "kotelchuck", "grupo_mesprenat"])
    mes["prop_dentro_kotelchuck"] = _proporcao(mes, ["populacao", "ano", "kotelchuck"])
    mes["prop_dentro_grupo_mesprenat"] = _proporcao(mes, ["populacao", "ano", "grupo_mesprenat"])
    return {"x_consprenat": cons, "x_mesprenat": mes}


# ---------------------------------------------------------------------------
# Gates (aplicação mecânica dos critérios pré-registrados)
# ---------------------------------------------------------------------------

def pior_status(*status: str) -> str:
    return max(status, key=lambda s: ORDEM_GRAVIDADE[s])


def melhor_status(*status: str) -> str:
    return min(status, key=lambda s: ORDEM_GRAVIDADE[s])


def avaliar_g1(d3_zero: pd.DataFrame, d3_longa: pd.DataFrame, semantica_oficial: bool) -> dict[str, Any]:
    eleg = d3_longa[(d3_longa["populacao"] == "ELEGIVEL")]
    br = eleg[eleg["uf"] == "BRASIL"]
    anos = sorted(br["ano"].unique())
    c2 = all(br[(br["ano"] == a) & br["consprenat"].isin(("99", "VAZIO"))]["n"].sum() > 0 for a in anos)
    zero = d3_zero[(d3_zero["populacao"] == "ELEGIVEL")]
    zero_br = zero[zero["uf"] == "BRASIL"]
    contraditorio = zero_br["n"].where(zero_br["grupo_mesprenat"].isin(("1-3", "4-5", "6", "7-9")), 0)
    contradicao = contraditorio.groupby(zero_br["ano"]).sum() / zero_br.groupby("ano")["n"].sum()
    c3 = bool((contradicao < MAIORIA).all())
    dominante = zero_br.sort_values("n", ascending=False).groupby("ano")["grupo_mesprenat"].first()
    c4 = dominante.nunique() == 1
    zero_uf = zero[zero["uf"] != "BRASIL"]
    n_uf = zero_uf.groupby(["ano", "uf"])["n"].sum()
    elegiveis_uf = n_uf[n_uf >= CELULA_MINIMA].index
    dom_uf = zero_uf.sort_values("n", ascending=False).groupby(["ano", "uf"])["grupo_mesprenat"].first()
    divergentes = [(a, u, dom_uf[(a, u)], dominante[a]) for a, u in elegiveis_uf if dom_uf[(a, u)] != dominante[a]]
    c5 = not divergentes
    if not (semantica_oficial and c2 and c3):
        status = "BLOQUEADO"
    elif c4 and c5:
        status = "APROVADO"
    else:
        status = "SINALIZADO"
    return {"status": status, "C1_documental": semantica_oficial, "C2_ignorado_distinto": c2,
            "C3_contradicao_minoritaria": c3, "C4_estabilidade_temporal": bool(c4), "C5_estabilidade_uf": c5,
            "fracao_contraditoria_por_ano": {str(k): float(v) for k, v in contradicao.items()},
            "categoria_dominante_por_ano": {str(k): v for k, v in dominante.items()},
            "n_uf_anos_avaliados": int(len(elegiveis_uf)), "n_uf_anos_divergentes": len(divergentes),
            "uf_anos_divergentes": [{"ano": str(a), "uf": u, "dominante_uf": d, "dominante_brasil": b}
                                    for a, u, d, b in divergentes]}


def avaliar_g2(d2_matriz: pd.DataFrame, codigos_fora_dominio: Mapping[str, int]) -> dict[str, Any]:
    anual = d2_matriz[d2_matriz["ano"] != "2014-2024"]
    l1 = anual["status_diagnostico"].isin(STATUS_CONSISTENCIA[:2])
    chave = [anual["ano"], anual["mes"]]
    n_mes = anual["n"].groupby(chave).sum()
    por_mes = anual["n"].where(l1, 0).groupby(chave).sum() / n_mes
    por_mes_avaliavel = por_mes[n_mes >= CELULA_MINIMA]
    n_l1 = int(anual.loc[l1, "n"].sum())
    n_tol = int(anual.loc[anual["status_diagnostico"] == STATUS_CONSISTENCIA[0], "n"].sum())
    n_l2 = int(anual.loc[anual["status_diagnostico"] == STATUS_CONSISTENCIA[2], "n"].sum())
    fora = int(sum(codigos_fora_dominio.values()))
    if (por_mes_avaliavel >= MAIORIA).any():
        status = "BLOQUEADO"
    elif n_l1 > 0 or fora > 0:
        status = "SINALIZADO"
    else:
        status = "APROVADO"
    return {"status": status, "n_potencialmente_incompativel_L1_ou_tolerancia": n_l1,
            "n_potencialmente_incompativel_mesmo_com_tolerancia": n_tol,
            "n_potencialmente_incompativel_somente_L2": n_l2,
            "n_total_avaliado": int(anual["n"].sum()),
            "maior_fracao_L1_em_um_mes_ano": float(por_mes.max()),
            "mes_ano_da_maior_fracao": [str(x) for x in por_mes.idxmax()],
            "codigos_fora_do_dominio_oficial": dict(codigos_fora_dominio)}


def avaliar_g3(d4_smd: pd.DataFrame) -> dict[str, Any]:
    anual = d4_smd[d4_smd["ano"] != "2014-2024"]
    if anual.empty:
        return {"status": "PENDENTE", "motivo": "nenhum grupo desconhecido com N >= 100"}
    acima = anual[anual["abs_smd"] >= SMD_REFERENCIA]
    por_y, por_x = bool((acima["tipo"] == "Y").any()), bool((acima["tipo"] == "X").any())
    status = "SINALIZADO" if (por_y or por_x) else "APROVADO"
    pior = anual.loc[anual.groupby(["grupo", "variavel"])["abs_smd"].idxmax()].sort_values("abs_smd", ascending=False)
    return {"status": status, "diferencial_por_Y": por_y, "diferencial_por_X": por_x,
            "n_comparacoes": int(len(anual)), "n_comparacoes_acima_referencia": int(len(acima)),
            "grupos_avaliados": sorted(anual["grupo"].unique()),
            "pior_por_grupo_variavel": pior[["ano", "grupo", "variavel", "nivel", "smd"]].to_dict("records")}


def avaliar_g4(d7_resumo: pd.DataFrame, padrao: pd.DataFrame) -> dict[str, Any]:
    a = d7_resumo[d7_resumo["alternativa"] == "A_V1_4_9"].set_index("ano")
    anual = a.drop(index="2014-2024", errors="ignore")
    status = "SINALIZADO" if (anual["fracao_controle_7_9"] > 0).any() else "APROVADO"
    p1 = padrao[padrao["ano"] != "2014-2024"].groupby("ano")["P1_nao_decrescente_no_ano"].first()
    return {"status": status,
            "fracao_controle_7_9": {str(k): float(v) for k, v in a["fracao_controle_7_9"].items()},
            "fracao_controle_6": {str(k): float(v) for k, v in a["fracao_controle_6"].items()},
            "fracao_controle_4_5": {str(k): float(v) for k, v in a["fracao_controle_4_5"].items()},
            "fracao_controle_4_6": {str(k): float(v) for k, v in a["fracao_controle_4_6"].items()},
            "P1_padrao_truncamento_anos_verdadeiro": int(p1.sum()), "P1_anos_avaliados": int(len(p1))}


def _m1(d7_resumo: pd.DataFrame, alternativa: str, leitura: str) -> pd.Series:
    t = d7_resumo[(d7_resumo["alternativa"] == alternativa) & (d7_resumo["ano"] != "2014-2024")]
    return t.set_index("ano")[f"M1_{leitura}"]


def avaliar_g5(d7_resumo: pd.DataFrame) -> dict[str, Any]:
    ultimo_b = max(ALTERNATIVAS_CONTROLE["B_4_6"])
    estrutural = all(inicio_mes_semanas(ultimo_b, l) < LIMITE_VIABILIDADE_FAIXA for l in ("L1", "L2"))
    reduz = all((_m1(d7_resumo, "B_4_6", l) < _m1(d7_resumo, "A_V1_4_9", l)).all() for l in ("L1", "L2"))
    status = "BLOQUEADO" if not reduz else ("APROVADO" if estrutural else "SINALIZADO")
    return {"status": status, "i_estrutural_ultimo_mes_B_antes_de_22_semanas": estrutural,
            "ii_M1_B_menor_que_A_todos_os_anos": reduz,
            "M1": {l: {"A": _m1(d7_resumo, "A_V1_4_9", l).to_dict(), "B": _m1(d7_resumo, "B_4_6", l).to_dict()}
                   for l in ("L1", "L2")}}


def avaliar_g6(d7_resumo: pd.DataFrame) -> dict[str, Any]:
    pares = [(_m1(d7_resumo, "C_4_5", l), _m1(d7_resumo, "B_4_6", l)) for l in ("L1", "L2")]
    estrito = all((c < b).all() for c, b in pares)
    nao_maior = all((c <= b).all() for c, b in pares)
    alguma_reducao = any((c < b).any() for c, b in pares)
    if estrito:
        status = "APROVADO"
    elif nao_maior and alguma_reducao:
        status = "SINALIZADO"
    else:
        status = "BLOQUEADO"
    return {"status": status, "reducao_estrita_todos_anos": estrito, "alguma_reducao": alguma_reducao,
            "M1": {l: {"B": b.to_dict(), "C": c.to_dict()} for l, (c, b) in zip(("L1", "L2"), pares)}}


def avaliar_g7(g: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    g2, g3 = g["G2"]["status"], g["G3"]["status"]
    g3_efetivo = "APROVADO" if g3 == "PENDENTE" else g3
    b = pior_status(g["G5"]["status"], g2, g3_efetivo)
    c = pior_status(g["G6"]["status"], g2, g3_efetivo)
    g1 = g["G1"]["status"]
    if g1 == "BLOQUEADO":
        d = "BLOQUEADO"
    elif g1 in ("SINALIZADO", "PENDENTE"):
        d = "PENDENTE"
    else:
        d = pior_status("SINALIZADO", g2, g3_efetivo)
    formulacoes = {"B_4_6": b, "C_4_5": c, "D_landmark": d}
    return {"status": melhor_status(*formulacoes.values()), "formulacoes": formulacoes,
            "avancam_para_discussao_metodologica": [k for k, v in formulacoes.items() if v in ("APROVADO", "SINALIZADO")],
            "permanecem_bloqueadas_ou_pendentes": [k for k, v in formulacoes.items() if v in ("BLOQUEADO", "PENDENTE")],
            "V2_escolhida": False}


# ---------------------------------------------------------------------------
# Inventário de schema e utilitários de execução
# ---------------------------------------------------------------------------

def inventario_schema(caminho_parquet: str | Path, ano: int) -> pd.DataFrame:
    import pyarrow.parquet as pq

    arquivo = pq.ParquetFile(caminho_parquet)
    nomes = arquivo.schema_arrow.names
    indice = {n.strip().upper(): n for n in nomes}
    linhas = []
    for campo in CAMPOS_INVENTARIO:
        original = indice.get(campo)
        linhas.append({"ano": ano, "campo": campo, "presente": original is not None,
                       "nome_original": original, "caixa_diferente": bool(original and original != campo),
                       "tipo_parquet": str(arquivo.schema_arrow.field(original).type) if original else None,
                       "n_colunas_arquivo": len(nomes), "n_registros": arquivo.metadata.num_rows})
    return pd.DataFrame(linhas)


def dominios_codigos(caminho_parquet: str | Path, ano: int,
                     campos: Iterable[str] = ("MESPRENAT", "GESTACAO", "KOTELCHUCK", "TPMETESTIM", "CONSULTAS")) -> pd.DataFrame:
    texto = Path(caminho_parquet).as_posix().replace("'", "''")
    linhas = []
    with duckdb.connect() as con:
        for campo in campos:
            valores = con.execute(
                f"SELECT list(DISTINCT coalesce(trim(CAST({campo} AS VARCHAR)), '<NULL>') "
                f"ORDER BY coalesce(trim(CAST({campo} AS VARCHAR)), '<NULL>')) FROM read_parquet('{texto}')").fetchone()[0]
            linhas.append({"ano": ano, "campo": campo, "codigos_distintos": "|".join(valores)})
    return pd.DataFrame(linhas)


def codigos_fora_dominio_mesprenat(ig_uf: pd.DataFrame) -> dict[str, int]:
    fora = ig_uf[ig_uf["mes"] == "OUTRO_INVALIDO"].groupby("ano")["n"].sum()
    return {str(k): int(v) for k, v in fora.items() if v > 0}


def salvar_csv(tabela: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(caminho, index=False, float_format="%.12g", lineterminator="\n")


def sha256_arquivo(caminho: str | Path, bloco: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for parte in iter(lambda: arquivo.read(bloco), b""):
            h.update(parte)
    return h.hexdigest()


def memoria_processo_mb() -> dict[str, float]:
    import psutil

    info = psutil.Process().memory_info()
    pico = getattr(info, "peak_wset", None)
    return {"rss_mb": info.rss / 2**20, "pico_mb": (pico / 2**20) if pico else float("nan")}
