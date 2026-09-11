"""Audita a correspondência entre os 147 municípios da Fase II, as
entidades federais observadas no Censo Escolar e as unidades candidatas
da base MEC/SISTEC "Unidades da Rede Federal de EPCT".

Esta auditoria é preliminar e descritiva. Ela produz candidatos,
diagnósticos e uma fila priorizada para validação institucional — não
define ano de tratamento, não escolhe automaticamente "a" unidade da
Fase II e não executa matching, common support, ATT ou regressão causal.

Fonte MEC/SISTEC
-----------------
Título: "2008 a 2019 - Unidades da Rede Federal de EPCT"
Órgão: Portal de Dados Abertos do Ministério da Educação (seção PRONATEC)
URL original do recurso:
    https://dadosabertos.mec.gov.br/images/conteudo/pronatec/Unidades_da_Rede_Federal_de_EPCT.csv

A URL original está, nesta auditoria, bloqueada por desafio Cloudflare
(HTTP 403, cabeçalho `Cf-Mitigated: challenge`) e o `robots.txt` do
domínio proíbe explicitamente `ClaudeBot`; nenhuma tentativa de
contornar essa proteção foi feita. O arquivo foi obtido por uma via
pública alternativa e legítima: a cópia já arquivada pelo Internet
Archive, independente do servidor do MEC.

URL arquivada (fonte efetivamente usada):
    https://web.archive.org/web/20250424052536id_/https://dadosabertos.mec.gov.br/images/conteudo/pronatec/Unidades_da_Rede_Federal_de_EPCT.csv
Captura de 2025-04-24 05:25:36 UTC. O dígest do arquivo é idêntico em
todas as capturas do Internet Archive entre 2020-01-29 e 2025-04-24,
indicando conteúdo estável por mais de cinco anos.

Preservada localmente em:
    data/raw/institutional/mec_sistec/Unidades_da_Rede_Federal_de_EPCT.csv
SHA-256 esperado: ff48f76f4fed741514032edd6b67373b80e0791345a9dba593c6d93396015dc3
Tamanho esperado: 105.709 bytes
O hash é conferido em tempo de execução antes de qualquer leitura.

Limitações conhecidas da base MEC/SISTEC — ver
docs/methodology/AUDITORIA_CORRESPONDENCIA_UNIDADES_FASE_II.md para o
detalhamento completo:
  - `dt_autorizacao` é um carimbo de sistema do SISTEC (tem hora, minuto
    e segundo), não uma data legal de autorização confirmada no Diário
    Oficial. A própria base contém um registro de teste
    ("Escola teste - manual sistec") com o mesmo formato de data, o que
    evidencia isso. Por isso, `dt_autorizacao` é preservado apenas como
    referência descritiva e NUNCA é usado para decidir categoria,
    prioridade ou qualquer noção de "ano de tratamento" nesta auditoria.
  - 183 das 977 linhas têm `sigla_unidade_ensino` igual à string literal
    "null".
  - a base mistura, sem filtro, entidades da Rede Federal com outras
    entidades cadastradas no SISTEC (inclusive privadas e de teste).
  - não há código IBGE nem CO_ENTIDADE/INEP na base MEC/SISTEC — a única
    chave de correspondência possível com os 147 municípios é
    UF + nome do município, normalizado.

Uso:
    python src/auditoria_correspondencia_unidades_fase_ii.py
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

import duckdb
import pandas as pd

# ---------------------------------------------------------------------------
# Configuração global
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

FASE_II_PATH = PROJECT_ROOT / "data" / "processed" / "fase_ii_municipios.parquet"
ESCOLAS_PATH = PROJECT_ROOT / "data" / "interim" / "censo_escolas_federais_2007_2019.parquet"
PAINEL_PATH = PROJECT_ROOT / "data" / "processed" / "painel_presenca_federal_ept_fase_ii_2007_2019.parquet"
SISTEC_PATH = PROJECT_ROOT / "data" / "raw" / "institutional" / "mec_sistec" / "Unidades_da_Rede_Federal_de_EPCT.csv"

SISTEC_SHA256_ESPERADO = "ff48f76f4fed741514032edd6b67373b80e0791345a9dba593c6d93396015dc3"
SISTEC_TAMANHO_ESPERADO = 105_709

OUTPUT_LONGO = PROJECT_ROOT / "outputs" / "diagnostics" / "auditoria_correspondencia_unidades_fase_ii.csv"
OUTPUT_RESUMO = PROJECT_ROOT / "outputs" / "diagnostics" / "resumo_correspondencia_unidades_fase_ii.csv"

ANO_LIMITE_PREEXISTENTE = 2009  # presença em 2007 ou 2008 conta como "anterior à Fase II"

# Municípios com pesquisa institucional específica já realizada (ver
# docs/methodology/AUDITORIA_CORRESPONDENCIA_UNIDADES_FASE_II.md): cada
# um mistura uma entidade federal preexistente com o polo real da Fase
# II, ou agrega múltiplas ondas de implantação sob um único código IBGE.
# Marcados como prioridade alta independentemente das regras automáticas.
MUNICIPIOS_PRIORIDADE_FORCADA: dict[str, str] = {
    "3143302": (
        "Montes Claros/MG: Colegio Agricola Antonio Versiani Athayde (UFMG, "
        "EPT ativa 2007-2008) x Campus Montes Claros do IFNMG (2011-)."
    ),
    "4314902": (
        "Porto Alegre/RS: Campus Porto Alegre do IFRS, ex-Escola Tecnica da "
        "UFRGS (EPT ativa desde 2007) x Campus Restinga, polo real da Fase "
        "II (2011-)."
    ),
    "5300108": (
        "Brasilia/DF: Campus Planaltina preexistente (absorvido em 2008) "
        "agregado, sob o mesmo codigo IBGE, a multiplas ondas de "
        "implantacao (Gama/Samambaia/Taguatinga/Brasilia 2009-2012 e "
        "unidades posteriores ate 2018)."
    ),
}


# ---------------------------------------------------------------------------
# Normalização de nomes (apenas para gerar candidatos de correspondência)
# ---------------------------------------------------------------------------


def normaliza(texto: str) -> str:
    """Maiúsculas, sem acento, espaços colapsados — somente para comparação.

    Mesma lógica já usada em ``constroi_lista_fase_ii.py`` (função
    ``normaliza``) para associar nomes de município ao código IBGE.
    """
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s


# Abreviações municipais simples e inequívocas. Deliberadamente NÃO inclui
# "S." (ambíguo entre São/Santo/Santa) nem qualquer forma que exija
# desambiguação — apenas prefixos já sem ambiguidade em português.
ABREVIACOES_MUNICIPAIS: dict[str, str] = {
    "STO": "SANTO",
    "STA": "SANTA",
}


def normaliza_municipio(texto: str) -> str:
    """``normaliza()`` + pontuação neutralizada + abreviações simples expandidas.

    Usada apenas para GERAR candidatos de correspondência entre a lista
    Fase II e a base MEC/SISTEC. Nunca substitui o nome original nas
    saídas e nunca decide sozinha uma correspondência definitiva — o
    resultado da comparação é sempre registrado como candidato,
    rotulado por qualidade ("exata" ou "normalizada").
    """
    s = normaliza(texto)
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    tokens = [ABREVIACOES_MUNICIPAIS.get(tok, tok) for tok in s.split()]
    return " ".join(tokens)


def normaliza_nome_unidade(texto: str) -> str:
    """``normaliza()`` + pontuação simples neutralizada — só para DETECTAR
    possíveis duplicatas de nome de unidade MEC/SISTEC (ex.: mesma unidade
    registrada duas vezes com caixa diferente).

    Deliberadamente NÃO usa ``ABREVIACOES_MUNICIPAIS`` (é um dicionário de
    topônimos, não de nomes de instituição) e não tenta nenhuma outra forma
    de inferir que duas descrições diferentes são a mesma unidade física —
    isso é decisão institucional, não desta auditoria. Só sinaliza.
    """
    s = normaliza(texto)
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# Leitura e validação das fontes
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    """Retorna hash SHA-256 hexadecimal do arquivo.

    Mesmo padrão já usado em ``constroi_painel_censo_escolar.py``.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def require_columns(df: pd.DataFrame, columns: list[str], source: str) -> None:
    missing = sorted(set(columns) - set(df.columns))
    if missing:
        raise ValueError(f"{source}: colunas obrigatórias ausentes: {missing}")


def read_processed_parquet(path: Path) -> pd.DataFrame:
    """Lê um Parquet processado localmente via DuckDB, em memória.

    Mesmo padrão já usado em ``auditoria_timing_tratamento.py``.
    """
    if not path.exists():
        raise FileNotFoundError(f"Parquet não encontrado: {path}")
    connection = duckdb.connect(database=":memory:")
    try:
        return connection.execute("SELECT * FROM read_parquet(?)", [str(path)]).fetchdf()
    finally:
        connection.close()


def read_sistec_csv(path: Path) -> pd.DataFrame:
    """Lê o CSV MEC/SISTEC após validar tamanho e SHA-256 esperados.

    Esta auditoria não baixa dados: o arquivo precisa já existir no
    caminho esperado, já validado em sessão de pesquisa institucional
    anterior (ver docstring do módulo).
    """
    if not path.exists():
        raise FileNotFoundError(
            f"CSV MEC/SISTEC não encontrado em {path}. Recupere o arquivo "
            "já validado (ver docstring deste módulo para a URL arquivada "
            "no Internet Archive) antes de rodar esta auditoria."
        )
    tamanho = path.stat().st_size
    if tamanho != SISTEC_TAMANHO_ESPERADO:
        raise ValueError(
            f"Tamanho do CSV MEC/SISTEC divergente do esperado: esperado "
            f"{SISTEC_TAMANHO_ESPERADO} bytes, encontrado {tamanho} bytes."
        )
    hash_encontrado = sha256_file(path)
    if hash_encontrado != SISTEC_SHA256_ESPERADO:
        raise ValueError(
            "SHA-256 do CSV MEC/SISTEC divergente do esperado: esperado "
            f"{SISTEC_SHA256_ESPERADO}, encontrado {hash_encontrado}."
        )
    # keep_default_na=False: a base tem 183 linhas com a string literal
    # "null" em sigla_unidade_ensino (achado documentado da fonte). Sem
    # isso, o na_values padrão do pandas ("null" incluso) converteria essa
    # string em NaN, silenciosamente contradizendo o que a documentação
    # afirma sobre os dados preservados.
    sistec = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    require_columns(
        sistec,
        [
            "sigla_unidade_ensino",
            "nome_unidade_ensino",
            "dt_autorizacao",
            "sigla_uf_unidade_ensino",
            "nome_municipio_unidade_ensino",
        ],
        "CSV MEC/SISTEC",
    )
    return sistec


def validate_fase_ii(fase_ii: pd.DataFrame) -> None:
    require_columns(fase_ii, ["codigo_municipio_ibge", "municipio", "uf"], "Cadastro Fase II")
    codes = fase_ii["codigo_municipio_ibge"].astype("string").str.zfill(7)
    if codes.isna().any() or codes.nunique() != 147 or codes.duplicated().any():
        raise ValueError("Cadastro Fase II deve conter exatamente 147 códigos IBGE distintos e não nulos.")


# ---------------------------------------------------------------------------
# Candidatos: Censo Escolar
# ---------------------------------------------------------------------------


def build_censo_candidates(fase_ii_codes: set[str], escolas: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (município Fase II, CO_ENTIDADE) observado no Censo Escolar."""
    require_columns(
        escolas,
        [
            "CO_MUNICIPIO", "NU_ANO_CENSO", "CO_ENTIDADE", "NO_ENTIDADE",
            "fl_em_atividade", "fl_presenca_federal_ept_ativa",
        ],
        "Censo Escolar (escola-ano)",
    )
    escolas = escolas.copy()
    escolas["CO_MUNICIPIO"] = escolas["CO_MUNICIPIO"].astype("string").str.zfill(7)
    escolas["NU_ANO_CENSO"] = pd.to_numeric(escolas["NU_ANO_CENSO"], errors="raise").astype(int)
    escolas = escolas[escolas["CO_MUNICIPIO"].isin(fase_ii_codes)]

    rows = []
    for (codigo, co_entidade), grupo in escolas.groupby(["CO_MUNICIPIO", "CO_ENTIDADE"], sort=False):
        grupo = grupo.sort_values("NU_ANO_CENSO")
        anos_ativa = grupo.loc[grupo["fl_em_atividade"].astype(bool), "NU_ANO_CENSO"]
        anos_ept_ativa = grupo.loc[grupo["fl_presenca_federal_ept_ativa"].astype(bool), "NU_ANO_CENSO"]
        nomes_historicos = list(dict.fromkeys(grupo["NO_ENTIDADE"].tolist()))
        rows.append({
            "codigo_municipio_ibge": codigo,
            "co_entidade": co_entidade,
            "nomes_historicos_censo": "; ".join(nomes_historicos),
            "primeiro_ano_registro_censo": int(grupo["NU_ANO_CENSO"].min()),
            "ultimo_ano_registro_censo": int(grupo["NU_ANO_CENSO"].max()),
            "primeiro_ano_ativa_censo": int(anos_ativa.min()) if not anos_ativa.empty else pd.NA,
            "ultimo_ano_ativa_censo": int(anos_ativa.max()) if not anos_ativa.empty else pd.NA,
            "primeiro_ano_ept_ativa_censo": int(anos_ept_ativa.min()) if not anos_ept_ativa.empty else pd.NA,
            "ultimo_ano_ept_ativa_censo": int(anos_ept_ativa.max()) if not anos_ept_ativa.empty else pd.NA,
        })
    colunas = [
        "codigo_municipio_ibge", "co_entidade", "nomes_historicos_censo",
        "primeiro_ano_registro_censo", "ultimo_ano_registro_censo",
        "primeiro_ano_ativa_censo", "ultimo_ano_ativa_censo",
        "primeiro_ano_ept_ativa_censo", "ultimo_ano_ept_ativa_censo",
    ]
    return pd.DataFrame(rows, columns=colunas)


# ---------------------------------------------------------------------------
# Candidatos: MEC/SISTEC
# ---------------------------------------------------------------------------


def index_sistec(sistec: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta chaves normalizadas ao CSV MEC/SISTEC, preservando as colunas originais."""
    sistec = sistec.copy()
    sistec["uf_norm"] = sistec["sigla_uf_unidade_ensino"].astype(str).str.strip().str.upper()
    sistec["municipio_norm_exato"] = sistec["nome_municipio_unidade_ensino"].map(normaliza)
    sistec["municipio_norm_ampliado"] = sistec["nome_municipio_unidade_ensino"].map(normaliza_municipio)
    return sistec


def match_sistec_candidates(fase_ii: pd.DataFrame, sistec_idx: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (município Fase II, linha do CSV MEC/SISTEC) correspondente por UF + nome.

    A correspondência exata (``normaliza``) é sempre um subconjunto da
    correspondência ampliada (``normaliza_municipio``): toda linha é
    classificada por qualidade própria, nunca descartada em favor de
    "a melhor" — todos os candidatos de um município são preservados.
    """
    rows = []
    for municipio in fase_ii.itertuples(index=False):
        uf = str(municipio.uf).strip().upper()
        municipio_exato = normaliza(municipio.municipio)
        municipio_ampliado = normaliza_municipio(municipio.municipio)
        mesma_uf = sistec_idx[sistec_idx["uf_norm"] == uf]
        for linha in mesma_uf.itertuples(index=False):
            if linha.municipio_norm_exato == municipio_exato:
                qualidade = "exata"
            elif linha.municipio_norm_ampliado == municipio_ampliado:
                qualidade = "normalizada"
            else:
                continue
            rows.append({
                "codigo_municipio_ibge": municipio.codigo_municipio_ibge,
                "sigla_unidade_sistec": linha.sigla_unidade_ensino,
                "nome_unidade_sistec": linha.nome_unidade_ensino,
                "dt_autorizacao_sistec": linha.dt_autorizacao,
                "uf_unidade_sistec": linha.sigla_uf_unidade_ensino,
                "municipio_unidade_sistec": linha.nome_municipio_unidade_ensino,
                "correspondencia_municipio": qualidade,
            })
    colunas = [
        "codigo_municipio_ibge", "sigla_unidade_sistec", "nome_unidade_sistec",
        "dt_autorizacao_sistec", "uf_unidade_sistec", "municipio_unidade_sistec",
        "correspondencia_municipio",
    ]
    return pd.DataFrame(rows, columns=colunas)


# ---------------------------------------------------------------------------
# Diagnósticos município-ano (a partir do painel processado)
# ---------------------------------------------------------------------------


def tem_lacuna_interna(anos: list[int], ativa: list[bool]) -> bool:
    """True se existir ao menos um ano False entre o primeiro e o último True.

    Mesmo conceito de "interrupção interna" já usado em
    ``auditoria_timing_tratamento.py``, reimplementado aqui de forma
    mínima (apenas o booleano) para não acoplar este script ao módulo
    de timing.
    """
    posicoes = sorted(range(len(anos)), key=lambda i: anos[i])
    ativa_ordenada = [ativa[i] for i in posicoes]
    verdadeiras = [i for i, v in enumerate(ativa_ordenada) if v]
    if len(verdadeiras) < 2:
        return False
    primeiro, ultimo = verdadeiras[0], verdadeiras[-1]
    return not all(ativa_ordenada[primeiro:ultimo + 1])


def build_painel_diagnostics(fase_ii_codes: set[str], painel: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por município: presença federal antes de 2009 (geral e EPT
    ativa, separadas) e lacuna interna em EPT ativa.

    ``presenca_federal_geral_antes_2009`` inclui qualquer escola federal
    (inclusive sem nenhuma relação com EPT, ex.: escola militar) e é só
    diagnóstico. ``presenca_federal_ept_ativa_antes_2009`` é a única usada
    para a categoria B — nenhuma das duas prova preexistência institucional
    de um campus da Fase II; são sinais mecânicos de timing que pedem
    validação (ver docs/methodology/AUDITORIA_CORRESPONDENCIA_UNIDADES_FASE_II.md).
    """
    require_columns(
        painel,
        ["CO_MUNICIPIO", "NU_ANO_CENSO", "fl_presenca_federal", "fl_presenca_federal_ept_ativa"],
        "Painel de presença federal",
    )
    painel = painel.copy()
    painel["CO_MUNICIPIO"] = painel["CO_MUNICIPIO"].astype("string").str.zfill(7)
    painel["NU_ANO_CENSO"] = pd.to_numeric(painel["NU_ANO_CENSO"], errors="raise").astype(int)
    painel = painel[painel["CO_MUNICIPIO"].isin(fase_ii_codes)]

    rows = []
    for codigo, grupo in painel.groupby("CO_MUNICIPIO", sort=False):
        antes = grupo["NU_ANO_CENSO"] < ANO_LIMITE_PREEXISTENTE
        geral_antes = grupo.loc[antes, "fl_presenca_federal"]
        ept_antes = grupo.loc[antes, "fl_presenca_federal_ept_ativa"]
        rows.append({
            "codigo_municipio_ibge": codigo,
            "presenca_federal_geral_antes_2009": bool(geral_antes.astype(bool).any()) if not geral_antes.empty else False,
            "presenca_federal_ept_ativa_antes_2009": bool(ept_antes.astype(bool).any()) if not ept_antes.empty else False,
            "trajetoria_intermitente_ept_ativa": tem_lacuna_interna(
                grupo["NU_ANO_CENSO"].tolist(),
                grupo["fl_presenca_federal_ept_ativa"].astype(bool).tolist(),
            ),
        })
    colunas = [
        "codigo_municipio_ibge", "presenca_federal_geral_antes_2009",
        "presenca_federal_ept_ativa_antes_2009", "trajetoria_intermitente_ept_ativa",
    ]
    return pd.DataFrame(rows, columns=colunas)


# ---------------------------------------------------------------------------
# Classificação diagnóstica (regras explícitas, categorias múltiplas)
# ---------------------------------------------------------------------------


def sistec_tem_duplicata_ambigua(candidatos_sistec_municipio: pd.DataFrame) -> bool:
    """True se dois candidatos tiverem o mesmo nome de unidade (por
    ``normaliza_nome_unidade`` — insensível a caixa, acento, espaço e
    pontuação simples) com ``dt_autorizacao`` diferente.
    """
    if candidatos_sistec_municipio.empty:
        return False
    nomes_normalizados = candidatos_sistec_municipio["nome_unidade_sistec"].map(normaliza_nome_unidade)
    por_nome = candidatos_sistec_municipio.groupby(nomes_normalizados)["dt_autorizacao_sistec"].nunique()
    return bool((por_nome > 1).any())


def classify_municipio(
    n_entidades_censo_com_ept_ativa: int,
    n_nomes_unidade_sistec_distintos: int,
    n_registros_sistec: int,
    presenca_federal_ept_ativa_antes_2009: bool,
    trajetoria_intermitente_ept_ativa: bool,
    correspondencia_municipio: str,
    duplicata_ambigua_sistec: bool,
) -> list[str]:
    """Categorias B-F são alertas mecânicos independentes; A_SEM_ALERTA_MECANICO
    só existe quando NENHUM outro alerta foi encontrado — por construção
    (é adicionada por último, apenas se a lista ainda está vazia), não pode
    coexistir com B/C/D/E/F. Nenhuma categoria aqui prova preexistência,
    tratamento ou identidade institucional — são candidatos e sinais
    mecânicos para revisão humana.
    """
    categorias: list[str] = []

    sem_candidato = n_registros_sistec == 0
    multiplas_entidades = n_entidades_censo_com_ept_ativa > 1 or n_nomes_unidade_sistec_distintos > 1
    apenas_normalizada = (not sem_candidato) and correspondencia_municipio != "exata"
    ambiguo = (
        duplicata_ambigua_sistec
        or (n_entidades_censo_com_ept_ativa > 1 and n_nomes_unidade_sistec_distintos > 1)
        or (apenas_normalizada and n_nomes_unidade_sistec_distintos > 1)
    )

    if presenca_federal_ept_ativa_antes_2009:
        categorias.append("B_EPT_ATIVA_ANTES_2009")
    if multiplas_entidades:
        categorias.append("C_MULTIPLAS_ENTIDADES")
    if trajetoria_intermitente_ept_ativa:
        categorias.append("D_INTERMITENTE")
    if sem_candidato:
        categorias.append("E_SEM_CANDIDATO_MEC")
    if ambiguo:
        categorias.append("F_AMBIGUO")
    if not categorias:
        categorias.append("A_SEM_ALERTA_MECANICO")
    return categorias


def prioridade_revisao(
    codigo: str, categorias: list[str], presenca_federal_ept_ativa_antes_2009: bool, multiplas_entidades: bool
) -> str:
    if codigo in MUNICIPIOS_PRIORIDADE_FORCADA:
        return "alta"
    if "F_AMBIGUO" in categorias or (presenca_federal_ept_ativa_antes_2009 and multiplas_entidades):
        return "alta"
    if any(c in categorias for c in ("B_EPT_ATIVA_ANTES_2009", "C_MULTIPLAS_ENTIDADES", "D_INTERMITENTE", "E_SEM_CANDIDATO_MEC")):
        return "media"
    return "baixa"


# ---------------------------------------------------------------------------
# Montagem das tabelas de saída
# ---------------------------------------------------------------------------


def build_long_table(
    fase_ii: pd.DataFrame, censo_candidatos: pd.DataFrame, sistec_candidatos: pd.DataFrame
) -> pd.DataFrame:
    """Formato longo: uma linha por candidato (Censo Escolar OU MEC/SISTEC), nunca cruzados."""
    base = fase_ii[["codigo_municipio_ibge", "municipio", "uf"]]

    censo_longo = base.merge(censo_candidatos, on="codigo_municipio_ibge", how="inner")
    censo_longo["tipo_candidato"] = "CENSO_ESCOLAR"
    censo_longo["correspondencia_municipio"] = "codigo_ibge"

    sistec_longo = base.merge(sistec_candidatos, on="codigo_municipio_ibge", how="inner")
    sistec_longo["tipo_candidato"] = "MEC_SISTEC"

    colunas = [
        "codigo_municipio_ibge", "municipio", "uf", "tipo_candidato",
        "co_entidade", "nomes_historicos_censo",
        "primeiro_ano_registro_censo", "ultimo_ano_registro_censo",
        "primeiro_ano_ativa_censo", "ultimo_ano_ativa_censo",
        "primeiro_ano_ept_ativa_censo", "ultimo_ano_ept_ativa_censo",
        "sigla_unidade_sistec", "nome_unidade_sistec", "dt_autorizacao_sistec",
        "uf_unidade_sistec", "municipio_unidade_sistec",
        "correspondencia_municipio",
    ]
    longo = pd.concat([censo_longo, sistec_longo], ignore_index=True, sort=False)
    for coluna in colunas:
        if coluna not in longo.columns:
            longo[coluna] = pd.NA
    longo = longo[colunas]
    return longo.sort_values(["uf", "municipio", "tipo_candidato"], kind="stable").reset_index(drop=True)


def build_summary_table(
    fase_ii: pd.DataFrame,
    censo_candidatos: pd.DataFrame,
    sistec_candidatos: pd.DataFrame,
    painel_diag: pd.DataFrame,
) -> pd.DataFrame:
    """Uma linha por município Fase II (147 linhas).

    Todas as entidades do Censo continuam preservadas na tabela longa;
    aqui elas só são CONTADAS em três recortes separados
    (``n_entidades_censo_total`` / ``_com_alguma_atividade`` /
    ``_com_ept_ativa``) para que uma entidade sem nenhuma relação com EPT
    (ex.: escola militar) não infle silenciosamente o alerta de
    múltiplas entidades. O mesmo vale do lado MEC/SISTEC:
    ``n_registros_sistec`` (linhas brutas) nunca é chamado de "unidades
    físicas"; ``n_nomes_unidade_sistec_distintos`` (nomes normalizados) é
    quem alimenta o alerta de multiplicidade/ambiguidade.
    """
    n_censo = censo_candidatos.groupby("codigo_municipio_ibge").agg(
        n_entidades_censo_total=("co_entidade", "size"),
        n_entidades_censo_com_alguma_atividade=("primeiro_ano_ativa_censo", lambda s: int(s.notna().sum())),
        n_entidades_censo_com_ept_ativa=("primeiro_ano_ept_ativa_censo", lambda s: int(s.notna().sum())),
    )

    sistec_com_nome_norm = sistec_candidatos.copy()
    sistec_com_nome_norm["nome_unidade_sistec_normalizado"] = sistec_com_nome_norm["nome_unidade_sistec"].map(
        normaliza_nome_unidade
    )
    n_sistec = sistec_com_nome_norm.groupby("codigo_municipio_ibge").agg(
        n_registros_sistec=("nome_unidade_sistec", "size"),
        n_nomes_unidade_sistec_distintos=("nome_unidade_sistec_normalizado", "nunique"),
    )

    resumo = fase_ii[["codigo_municipio_ibge", "municipio", "uf"]].copy()
    resumo = resumo.merge(n_censo, on="codigo_municipio_ibge", how="left")
    resumo = resumo.merge(n_sistec, on="codigo_municipio_ibge", how="left")
    for coluna in [
        "n_entidades_censo_total", "n_entidades_censo_com_alguma_atividade", "n_entidades_censo_com_ept_ativa",
        "n_registros_sistec", "n_nomes_unidade_sistec_distintos",
    ]:
        resumo[coluna] = resumo[coluna].fillna(0).astype(int)
    resumo = resumo.merge(painel_diag, on="codigo_municipio_ibge", how="left")

    linhas = []
    for row in resumo.itertuples(index=False):
        candidatos_municipio = sistec_candidatos[sistec_candidatos["codigo_municipio_ibge"] == row.codigo_municipio_ibge]
        if row.n_registros_sistec == 0:
            correspondencia = "sem_candidato"
        elif (candidatos_municipio["correspondencia_municipio"] == "exata").any():
            correspondencia = "exata"
        else:
            correspondencia = "normalizada"
        duplicata_ambigua = sistec_tem_duplicata_ambigua(candidatos_municipio)

        categorias = classify_municipio(
            n_entidades_censo_com_ept_ativa=row.n_entidades_censo_com_ept_ativa,
            n_nomes_unidade_sistec_distintos=row.n_nomes_unidade_sistec_distintos,
            n_registros_sistec=row.n_registros_sistec,
            presenca_federal_ept_ativa_antes_2009=bool(row.presenca_federal_ept_ativa_antes_2009),
            trajetoria_intermitente_ept_ativa=bool(row.trajetoria_intermitente_ept_ativa),
            correspondencia_municipio=correspondencia,
            duplicata_ambigua_sistec=duplicata_ambigua,
        )
        multiplas_entidades = row.n_entidades_censo_com_ept_ativa > 1 or row.n_nomes_unidade_sistec_distintos > 1
        prioridade = prioridade_revisao(
            row.codigo_municipio_ibge, categorias, bool(row.presenca_federal_ept_ativa_antes_2009), multiplas_entidades
        )
        forcado = row.codigo_municipio_ibge in MUNICIPIOS_PRIORIDADE_FORCADA
        observacoes = []
        if forcado:
            observacoes.append(MUNICIPIOS_PRIORIDADE_FORCADA[row.codigo_municipio_ibge])
        if duplicata_ambigua:
            observacoes.append("candidatos MEC/SISTEC com o mesmo nome normalizado e dt_autorizacao divergente")
        if row.n_entidades_censo_total > row.n_entidades_censo_com_ept_ativa:
            observacoes.append(
                f"{row.n_entidades_censo_total - row.n_entidades_censo_com_ept_ativa} de "
                f"{row.n_entidades_censo_total} entidade(s) do Censo nunca tiveram EPT ativa "
                "(preservadas na tabela longa, excluidas da contagem de alerta)"
            )
        if correspondencia == "sem_candidato":
            observacoes.append("nenhum candidato MEC/SISTEC encontrado por UF + nome do municipio")
        elif correspondencia == "normalizada":
            observacoes.append("correspondencia com a base MEC/SISTEC exigiu normalizacao (nao e correspondencia literal)")

        linhas.append({
            "codigo_municipio_ibge": row.codigo_municipio_ibge,
            "municipio": row.municipio,
            "uf": row.uf,
            "n_entidades_censo_total": row.n_entidades_censo_total,
            "n_entidades_censo_com_alguma_atividade": row.n_entidades_censo_com_alguma_atividade,
            "n_entidades_censo_com_ept_ativa": row.n_entidades_censo_com_ept_ativa,
            "n_registros_sistec": row.n_registros_sistec,
            "n_nomes_unidade_sistec_distintos": row.n_nomes_unidade_sistec_distintos,
            "presenca_federal_geral_antes_2009": bool(row.presenca_federal_geral_antes_2009),
            "presenca_federal_ept_ativa_antes_2009": bool(row.presenca_federal_ept_ativa_antes_2009),
            "multiplas_entidades_censo": row.n_entidades_censo_com_ept_ativa > 1,
            "multiplas_unidades_sistec": row.n_nomes_unidade_sistec_distintos > 1,
            "trajetoria_intermitente_ept_ativa": bool(row.trajetoria_intermitente_ept_ativa),
            "correspondencia_municipio": correspondencia,
            "categorias": "; ".join(categorias),
            "prioridade_revisao": prioridade,
            "prioridade_forcada": forcado,
            "observacoes_diagnosticas": "; ".join(observacoes),
        })
    resultado = pd.DataFrame(linhas)
    return resultado.sort_values(["uf", "municipio", "codigo_municipio_ibge"], kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Validação da tabela final
# ---------------------------------------------------------------------------


def validate_summary_table(resumo: pd.DataFrame, fase_ii_codes: set[str]) -> None:
    if "ano_tratamento" in resumo.columns:
        raise ValueError("A tabela-resumo não pode conter uma coluna chamada 'ano_tratamento'.")
    if len(resumo) != 147:
        raise ValueError(f"Resumo deve ter exatamente 147 municípios; encontrados {len(resumo)}.")
    codes = resumo["codigo_municipio_ibge"]
    if codes.isna().any() or codes.nunique() != 147 or codes.duplicated().any():
        raise ValueError("Resumo deve conter exatamente 147 códigos IBGE distintos e não nulos.")
    if set(codes) != fase_ii_codes:
        raise ValueError("Cobertura do resumo diverge do cadastro oficial dos 147 municípios da Fase II (município ausente ou extra).")

    faltando_prioridade_alta = [
        codigo for codigo in MUNICIPIOS_PRIORIDADE_FORCADA
        if resumo.loc[resumo["codigo_municipio_ibge"] == codigo, "prioridade_revisao"].iloc[0] != "alta"
    ]
    if faltando_prioridade_alta:
        raise ValueError(f"Municípios de prioridade forçada sem prioridade alta: {faltando_prioridade_alta}.")

    # A_SEM_ALERTA_MECANICO só pode significar "nenhum outro alerta" — nunca
    # pode coexistir com B/C/D/E/F. Isso já é garantido por construção em
    # classify_municipio (só é adicionada se a lista ainda está vazia), mas
    # esta checagem falha alto e explícito caso a garantia seja quebrada no
    # futuro, em vez de deixar a inconsistência passar silenciosamente.
    outras_categorias = ("B_EPT_ATIVA_ANTES_2009", "C_MULTIPLAS_ENTIDADES", "D_INTERMITENTE", "E_SEM_CANDIDATO_MEC", "F_AMBIGUO")
    categorias_series = resumo["categorias"]
    tem_sem_alerta = categorias_series.str.contains("A_SEM_ALERTA_MECANICO", regex=False)
    tem_outro_alerta = pd.Series(False, index=categorias_series.index)
    for outra in outras_categorias:
        tem_outro_alerta = tem_outro_alerta | categorias_series.str.contains(outra, regex=False)
    conflito = resumo.loc[tem_sem_alerta & tem_outro_alerta, "codigo_municipio_ibge"].tolist()
    if conflito:
        raise ValueError(f"A_SEM_ALERTA_MECANICO coexistindo com outra categoria nos municípios: {conflito}.")

    # Casos intermitentes já confirmados por investigação direta dos dados
    # nesta auditoria institucional (Jequié/BA, Nossa Senhora da
    # Glória/SE, Piracicaba/SP e Montes Claros/MG) devem permanecer
    # marcados como D_INTERMITENTE — a auditoria não pode fazer essa
    # informação desaparecer silenciosamente.
    intermitentes_conhecidos = {"2918001", "2804508", "3538709", "3143302"}
    nao_preservados = [
        codigo for codigo in intermitentes_conhecidos
        if "D_INTERMITENTE" not in resumo.loc[resumo["codigo_municipio_ibge"] == codigo, "categorias"].iloc[0]
    ]
    if nao_preservados:
        raise ValueError(f"Casos intermitentes conhecidos perderam a categoria D_INTERMITENTE: {nao_preservados}.")


# ---------------------------------------------------------------------------
# Relato em console
# ---------------------------------------------------------------------------


def print_summary(resumo: pd.DataFrame) -> None:
    print("AUDITORIA DE CORRESPONDÊNCIA — UNIDADES DA FASE II")
    print(f"Total de municípios: {len(resumo)}")
    print()
    print("Contagem por categoria (não mutuamente exclusivas):")
    for categoria in ["A_SEM_ALERTA_MECANICO", "B_EPT_ATIVA_ANTES_2009", "C_MULTIPLAS_ENTIDADES", "D_INTERMITENTE", "E_SEM_CANDIDATO_MEC", "F_AMBIGUO"]:
        n = int(resumo["categorias"].str.contains(categoria, regex=False).sum())
        print(f"  {categoria}: {n}")
    print()
    print("Distribuição de prioridade de revisão:")
    print(resumo["prioridade_revisao"].value_counts().to_string())
    print()
    print("Correspondência com a base MEC/SISTEC:")
    print(resumo["correspondencia_municipio"].value_counts().to_string())
    print()
    print("Municípios de prioridade forçada (revisão institucional já iniciada):")
    for codigo, motivo in MUNICIPIOS_PRIORIDADE_FORCADA.items():
        linha = resumo.loc[resumo["codigo_municipio_ibge"] == codigo].iloc[0]
        print(f"  {linha.municipio}/{linha.uf} ({codigo}): categorias=[{linha.categorias}] prioridade={linha.prioridade_revisao}")
    print()
    sem_candidato = resumo[resumo["correspondencia_municipio"] == "sem_candidato"]
    print(f"Municípios sem candidato MEC/SISTEC: {len(sem_candidato)}")
    for row in sem_candidato.itertuples(index=False):
        print(f"  {row.municipio}/{row.uf} ({row.codigo_municipio_ibge})")


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------


def build_audit(
    fase_ii: pd.DataFrame, escolas: pd.DataFrame, painel: pd.DataFrame, sistec: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    validate_fase_ii(fase_ii)
    fase_ii = fase_ii.copy()
    fase_ii["codigo_municipio_ibge"] = fase_ii["codigo_municipio_ibge"].astype("string").str.zfill(7)
    fase_ii_codes = set(fase_ii["codigo_municipio_ibge"])

    censo_candidatos = build_censo_candidates(fase_ii_codes, escolas)
    sistec_idx = index_sistec(sistec)
    sistec_candidatos = match_sistec_candidates(fase_ii, sistec_idx)
    painel_diag = build_painel_diagnostics(fase_ii_codes, painel)

    longo = build_long_table(fase_ii, censo_candidatos, sistec_candidatos)
    resumo = build_summary_table(fase_ii, censo_candidatos, sistec_candidatos, painel_diag)
    validate_summary_table(resumo, fase_ii_codes)
    return longo, resumo


def main() -> None:
    fase_ii = read_processed_parquet(FASE_II_PATH)
    escolas = read_processed_parquet(ESCOLAS_PATH)
    painel = read_processed_parquet(PAINEL_PATH)
    sistec = read_sistec_csv(SISTEC_PATH)

    longo, resumo = build_audit(fase_ii, escolas, painel, sistec)

    OUTPUT_LONGO.parent.mkdir(parents=True, exist_ok=True)
    longo.to_csv(OUTPUT_LONGO, index=False, encoding="utf-8-sig")
    resumo.to_csv(OUTPUT_RESUMO, index=False, encoding="utf-8-sig")

    print_summary(resumo)
    print()
    print(f"CSV longo gravado em:  {OUTPUT_LONGO} ({len(longo)} linhas)")
    print(f"CSV resumo gravado em: {OUTPUT_RESUMO} ({len(resumo)} linhas)")


if __name__ == "__main__":
    main()
