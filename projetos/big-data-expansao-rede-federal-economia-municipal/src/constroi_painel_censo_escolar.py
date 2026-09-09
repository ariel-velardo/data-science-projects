"""
constroi_painel_censo_escolar.py
=================================
Constrói o painel do Censo Escolar 2007-2019 para escolas federais.

Saídas:
  data/interim/censo_escolas_federais_2007_2019.parquet       – escola-ano
  data/interim/censo_federal_municipio_ano_2007_2019.parquet  – município-ano
  data/processed/painel_presenca_federal_ept_fase_ii_2007_2019.parquet – Fase II × anos

Uso:
  python src/constroi_painel_censo_escolar.py

Requer apenas: stdlib + pandas + pyarrow.
Não extrai CSVs para disco; usa zipfile + usecols + chunks.
"""

from __future__ import annotations

import hashlib
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuração global
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw" / "inep" / "censo_escolar"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"

FASE_II_PATH = DATA_PROCESSED / "fase_ii_municipios.parquet"

ANOS = list(range(2007, 2020))  # 2007 … 2019

COLS_USECOLS = [
    "NU_ANO_CENSO",
    "CO_ENTIDADE",
    "NO_ENTIDADE",
    "CO_MUNICIPIO",
    "NO_MUNICIPIO",
    "SG_UF",
    "CO_UF",
    "TP_DEPENDENCIA",
    "TP_SITUACAO_FUNCIONAMENTO",
    "TP_LOCALIZACAO",
    "TP_LOCALIZACAO_DIFERENCIADA",
    "IN_PROF",
    "IN_PROF_TEC",
    "QT_MAT_PROF",
    "QT_MAT_PROF_TEC",
    "QT_TUR_PROF",
    "QT_TUR_PROF_TEC",
    "QT_DOC_PROF",
    "QT_DOC_PROF_TEC",
]

# Dtype explícito de leitura (códigos como string para preservar zeros à esquerda)
DTYPE_READ: dict[str, str] = {
    "CO_ENTIDADE": "str",
    "CO_MUNICIPIO": "str",
    "CO_UF": "str",
    "NU_ANO_CENSO": "str",
    "NO_ENTIDADE": "str",
    "NO_MUNICIPIO": "str",
    "SG_UF": "str",
}

CHUNKSIZE = 50_000

# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    """Retorna hash SHA-256 hexadecimal do arquivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def csv_path_in_zip(year: int) -> tuple[Path, str]:
    """Retorna (caminho do ZIP, nome do CSV interno)."""
    zip_path = DATA_RAW / "microdados_censo_escolar_{}.zip".format(year)
    with zipfile.ZipFile(zip_path) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
    assert len(csvs) == 1, "Esperado 1 CSV no ZIP {}, encontrado {}".format(year, len(csvs))
    return zip_path, csvs[0]


def read_federal_from_zip(year: int) -> pd.DataFrame:
    """
    Lê apenas escolas federais (TP_DEPENDENCIA == 1) de um ano do Censo Escolar.
    Usa chunks para limitar uso de memória; nunca extrai o CSV inteiro para disco.
    Lê bytes do ZIP e passa diretamente ao pandas com encoding declarado.
    """
    zip_path, csv_name = csv_path_in_zip(year)
    chunks: list[pd.DataFrame] = []

    with zipfile.ZipFile(zip_path) as z:
        raw_bytes = z.read(csv_name)

    buf = io.BytesIO(raw_bytes)
    reader = pd.read_csv(
        buf,
        sep=";",
        usecols=COLS_USECOLS,
        dtype=DTYPE_READ,
        chunksize=CHUNKSIZE,
        low_memory=False,
        encoding="latin-1",
        encoding_errors="replace",
    )
    for chunk in reader:
        # Converte TP_DEPENDENCIA para int para filtrar
        chunk["TP_DEPENDENCIA"] = pd.to_numeric(
            chunk["TP_DEPENDENCIA"], errors="coerce"
        )
        federal = chunk[chunk["TP_DEPENDENCIA"] == 1].copy()
        if not federal.empty:
            chunks.append(federal)

    if not chunks:
        return pd.DataFrame(columns=COLS_USECOLS)

    df = pd.concat(chunks, ignore_index=True)

    # Garante que NU_ANO_CENSO seja string "YYYY" e coincide com year
    df["NU_ANO_CENSO"] = df["NU_ANO_CENSO"].astype(str).str.strip()

    # Verifica se o ano do arquivo coincide com o dado
    anos_no_dado = df["NU_ANO_CENSO"].unique().tolist()
    esperado = str(year)
    discordantes = [a for a in anos_no_dado if a != esperado]
    if discordantes:
        print(
            "  [AVISO] Ano {}: NU_ANO_CENSO contém valores inesperados: {}".format(year, discordantes),
            file=sys.stderr,
        )

    # Normaliza comprimentos dos códigos
    df["CO_ENTIDADE"] = df["CO_ENTIDADE"].astype(str).str.strip().str.zfill(8)
    df["CO_MUNICIPIO"] = df["CO_MUNICIPIO"].astype(str).str.strip().str.zfill(7)
    df["CO_UF"] = df["CO_UF"].astype(str).str.strip().str.zfill(2)

    # Converte colunas numéricas
    num_cols = [
        "TP_SITUACAO_FUNCIONAMENTO", "TP_LOCALIZACAO", "TP_LOCALIZACAO_DIFERENCIADA",
        "IN_PROF", "IN_PROF_TEC",
        "QT_MAT_PROF", "QT_MAT_PROF_TEC",
        "QT_TUR_PROF", "QT_TUR_PROF_TEC",
        "QT_DOC_PROF", "QT_DOC_PROF_TEC",
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Cria flags derivadas
    df["fl_em_atividade"] = (df["TP_SITUACAO_FUNCIONAMENTO"] == 1)
    df["fl_oferta_ept"] = (df["IN_PROF"] == 1)
    df["fl_oferta_ept_tecnica"] = (df["IN_PROF_TEC"] == 1)
    df["fl_presenca_federal_ept_ativa"] = (
        (df["TP_DEPENDENCIA"] == 1)
        & (df["TP_SITUACAO_FUNCIONAMENTO"] == 1)
        & (df["IN_PROF"] == 1)
    )

    return df


def audit_contradictions(df: pd.DataFrame, year: int) -> dict:
    """
    Audita contradições entre flag IN_PROF/IN_PROF_TEC e as quantidades.
    Retorna dicionário com contagens de contradições.
    """
    contradictions = {}

    # IN_PROF == 1 mas todas as quantidades EPT são 0 ou nulas
    mask_prof_sem_qt = (
        (df["IN_PROF"] == 1)
        & (
            (df["QT_MAT_PROF"].fillna(0) == 0)
            & (df["QT_TUR_PROF"].fillna(0) == 0)
            & (df["QT_DOC_PROF"].fillna(0) == 0)
        )
    )
    contradictions["in_prof_1_sem_quantidades"] = int(mask_prof_sem_qt.sum())

    # IN_PROF == 0 ou nulo, mas tem quantidades EPT > 0
    mask_qt_sem_prof = (
        (df["IN_PROF"] != 1)
        & (
            (df["QT_MAT_PROF"].fillna(0) > 0)
            | (df["QT_TUR_PROF"].fillna(0) > 0)
            | (df["QT_DOC_PROF"].fillna(0) > 0)
        )
    )
    contradictions["in_prof_0_com_quantidades"] = int(mask_qt_sem_prof.sum())

    # IN_PROF_TEC == 1 mas sem quantidades técnicas
    mask_tec_sem_qt = (
        (df["IN_PROF_TEC"] == 1)
        & (
            (df["QT_MAT_PROF_TEC"].fillna(0) == 0)
            & (df["QT_TUR_PROF_TEC"].fillna(0) == 0)
            & (df["QT_DOC_PROF_TEC"].fillna(0) == 0)
        )
    )
    contradictions["in_prof_tec_1_sem_quantidades"] = int(mask_tec_sem_qt.sum())

    # IN_PROF_TEC == 0 mas com quantidades técnicas
    mask_qt_tec_sem_flag = (
        (df["IN_PROF_TEC"] != 1)
        & (
            (df["QT_MAT_PROF_TEC"].fillna(0) > 0)
            | (df["QT_TUR_PROF_TEC"].fillna(0) > 0)
            | (df["QT_DOC_PROF_TEC"].fillna(0) > 0)
        )
    )
    contradictions["in_prof_tec_0_com_quantidades"] = int(mask_qt_tec_sem_flag.sum())

    return contradictions


def aggregate_municipio_ano(df_escola_ano: pd.DataFrame) -> pd.DataFrame:
    """Agrega tabela escola-ano para município-ano."""
    grp = df_escola_ano.groupby(["NU_ANO_CENSO", "CO_MUNICIPIO"])

    agg = grp.agg(
        NO_MUNICIPIO=("NO_MUNICIPIO", "first"),
        SG_UF=("SG_UF", "first"),
        CO_UF=("CO_UF", "first"),
        qt_escolas_federais=("CO_ENTIDADE", "count"),
        qt_escolas_em_atividade=("fl_em_atividade", "sum"),
        qt_escolas_com_ept=("fl_oferta_ept", "sum"),
        qt_escolas_com_ept_tecnica=("fl_oferta_ept_tecnica", "sum"),
        qt_escolas_federal_ept_ativa=("fl_presenca_federal_ept_ativa", "sum"),
        qt_mat_prof=("QT_MAT_PROF", "sum"),
        qt_mat_prof_tec=("QT_MAT_PROF_TEC", "sum"),
        qt_tur_prof=("QT_TUR_PROF", "sum"),
        qt_tur_prof_tec=("QT_TUR_PROF_TEC", "sum"),
        qt_doc_prof=("QT_DOC_PROF", "sum"),
        qt_doc_prof_tec=("QT_DOC_PROF_TEC", "sum"),
    ).reset_index()

    # Converte somas de bool para Int64
    count_cols = [
        "qt_escolas_federais", "qt_escolas_em_atividade", "qt_escolas_com_ept",
        "qt_escolas_com_ept_tecnica", "qt_escolas_federal_ept_ativa",
        "qt_mat_prof", "qt_mat_prof_tec", "qt_tur_prof", "qt_tur_prof_tec",
        "qt_doc_prof", "qt_doc_prof_tec",
    ]
    for col in count_cols:
        agg[col] = agg[col].fillna(0).astype("Int64")

    return agg


def build_fase_ii_panel(
    df_mun_ano: pd.DataFrame,
    fase_ii_mun: list[str],
    anos: list[int],
    df_fase_ii: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Cria grade completa Fase II × anos (1.911 linhas esperadas)
    e faz left join com município-ano.
    Preenche NO_MUNICIPIO, SG_UF e CO_UF para evitar nulos nos anos pré-tratamento.
    """
    # Grade completa
    grade = pd.MultiIndex.from_product(
        [fase_ii_mun, [str(a) for a in anos]],
        names=["CO_MUNICIPIO", "NU_ANO_CENSO"],
    )
    df_grade = pd.DataFrame(index=grade).reset_index()

    # Prepara referência cadastral de Fase II caso fornecida
    if df_fase_ii is not None:
        cad = df_fase_ii[["codigo_municipio_ibge", "municipio", "uf"]].copy()
        cad["CO_MUNICIPIO"] = cad["codigo_municipio_ibge"].astype(str).str.zfill(7)
        cad["NO_MUNICIPIO_REF"] = cad["municipio"].astype(str).str.strip()
        cad["SG_UF_REF"] = cad["uf"].astype(str).str.strip()
        cad["CO_UF_REF"] = cad["CO_MUNICIPIO"].str[:2]
        cad = cad[["CO_MUNICIPIO", "NO_MUNICIPIO_REF", "SG_UF_REF", "CO_UF_REF"]].drop_duplicates()
        df_grade = df_grade.merge(cad, on="CO_MUNICIPIO", how="left")

    # Join com município-ano
    df = df_grade.merge(
        df_mun_ano,
        on=["CO_MUNICIPIO", "NU_ANO_CENSO"],
        how="left",
    )

    # Preenche NO_MUNICIPIO, SG_UF, CO_UF a partir do cadastro de referência se houver nulos
    if "NO_MUNICIPIO_REF" in df.columns:
        df["NO_MUNICIPIO"] = df["NO_MUNICIPIO"].fillna(df["NO_MUNICIPIO_REF"])
        df["SG_UF"] = df["SG_UF"].fillna(df["SG_UF_REF"])
        df["CO_UF"] = df["CO_UF"].fillna(df["CO_UF_REF"])
        df = df.drop(columns=["NO_MUNICIPIO_REF", "SG_UF_REF", "CO_UF_REF"])

    # Preenche zeros nas colunas de contagem
    count_cols = [
        "qt_escolas_federais", "qt_escolas_em_atividade", "qt_escolas_com_ept",
        "qt_escolas_com_ept_tecnica", "qt_escolas_federal_ept_ativa",
        "qt_mat_prof", "qt_mat_prof_tec", "qt_tur_prof", "qt_tur_prof_tec",
        "qt_doc_prof", "qt_doc_prof_tec",
    ]
    for col in count_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype("Int64")
        else:
            df[col] = pd.array([0] * len(df), dtype="Int64")

    # Flags de presença no painel
    df["fl_presenca_federal"] = df["qt_escolas_federais"] > 0
    df["fl_presenca_federal_ept"] = df["qt_escolas_com_ept"] > 0
    df["fl_presenca_federal_ept_ativa"] = df["qt_escolas_federal_ept_ativa"] > 0

    # Garante ordem lógica e determinística das colunas
    id_cols = ["CO_MUNICIPIO", "NU_ANO_CENSO", "NO_MUNICIPIO", "SG_UF", "CO_UF"]
    other_cols = [c for c in df.columns if c not in id_cols]
    df = df[id_cols + other_cols]

    # Ordena deterministicamente
    df = df.sort_values(["CO_MUNICIPIO", "NU_ANO_CENSO"]).reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# Validações
# ---------------------------------------------------------------------------


def validate_escola_ano(df: pd.DataFrame) -> list[str]:
    """Retorna lista de mensagens de erro (vazia = OK)."""
    erros = []

    # Unicidade (NU_ANO_CENSO, CO_ENTIDADE)
    dup = df.duplicated(subset=["NU_ANO_CENSO", "CO_ENTIDADE"])
    if dup.any():
        erros.append("Unicidade escola-ano VIOLADA: {} duplicatas em (NU_ANO_CENSO, CO_ENTIDADE)".format(dup.sum()))

    # Comprimentos de códigos
    wrong_ent = (df["CO_ENTIDADE"].str.len() != 8).sum()
    wrong_mun = (df["CO_MUNICIPIO"].str.len() != 7).sum()
    wrong_uf = (df["CO_UF"].str.len() != 2).sum()
    if wrong_ent:
        erros.append("CO_ENTIDADE com comprimento != 8: {} registros".format(wrong_ent))
    if wrong_mun:
        erros.append("CO_MUNICIPIO com comprimento != 7: {} registros".format(wrong_mun))
    if wrong_uf:
        erros.append("CO_UF com comprimento != 2: {} registros".format(wrong_uf))

    # Todos são federais
    nao_federal = (df["TP_DEPENDENCIA"] != 1).sum()
    if nao_federal:
        erros.append("Escolas não-federais na tabela: {}".format(nao_federal))

    # Anos esperados
    anos_presentes = sorted(df["NU_ANO_CENSO"].unique().tolist())
    anos_esperados = [str(a) for a in range(2007, 2020)]
    if anos_presentes != anos_esperados:
        erros.append("Anos presentes diferem do esperado. Presentes={}".format(anos_presentes))

    return erros


def validate_municipio_ano(df: pd.DataFrame) -> list[str]:
    erros = []
    dup = df.duplicated(subset=["NU_ANO_CENSO", "CO_MUNICIPIO"])
    if dup.any():
        erros.append("Unicidade município-ano VIOLADA: {} duplicatas".format(dup.sum()))

    count_cols = [
        "qt_escolas_federais", "qt_escolas_em_atividade", "qt_escolas_com_ept",
        "qt_escolas_com_ept_tecnica", "qt_escolas_federal_ept_ativa",
        "qt_mat_prof", "qt_mat_prof_tec", "qt_tur_prof", "qt_tur_prof_tec",
        "qt_doc_prof", "qt_doc_prof_tec",
    ]
    for col in count_cols:
        neg = (df[col].fillna(0) < 0).sum()
        if neg:
            erros.append("Contagem negativa em {}: {} registros".format(col, neg))

    return erros


def validate_panel_fase_ii(df: pd.DataFrame, fase_ii_mun: list[str]) -> list[str]:
    erros = []

    # Unicidade
    dup = df.duplicated(subset=["NU_ANO_CENSO", "CO_MUNICIPIO"])
    if dup.any():
        erros.append("Unicidade painel VIOLADA: {} duplicatas".format(dup.sum()))

    # 147 municípios
    n_mun = df["CO_MUNICIPIO"].nunique()
    if n_mun != 147:
        erros.append("Esperado 147 municípios, encontrado {}".format(n_mun))

    # 13 anos
    n_anos = df["NU_ANO_CENSO"].nunique()
    if n_anos != 13:
        erros.append("Esperado 13 anos, encontrado {}".format(n_anos))

    # 1.911 linhas
    if len(df) != 1911:
        erros.append("Esperado 1.911 linhas, encontrado {}".format(len(df)))

    # Zero nulos em identificação municipal
    for col in ["CO_MUNICIPIO", "NO_MUNICIPIO", "SG_UF", "CO_UF"]:
        if col in df.columns:
            nulos = df[col].isna().sum()
            if nulos:
                erros.append("{} nulo no painel: {} registros".format(col, nulos))
        else:
            erros.append("Coluna {} ausente no painel".format(col))

    # Verifica que todos os municípios Fase II estão no painel
    mun_painel = set(df["CO_MUNICIPIO"].unique())
    mun_esperados = set(fase_ii_mun)
    faltando = mun_esperados - mun_painel
    sobrando = mun_painel - mun_esperados
    if faltando:
        erros.append("Municípios Fase II ausentes do painel: {}".format(len(faltando)))
    if sobrando:
        erros.append("Municípios extras no painel (não são Fase II): {}".format(len(sobrando)))

    # Contagens nunca negativas
    count_cols = [
        "qt_escolas_federais", "qt_escolas_em_atividade", "qt_escolas_com_ept",
        "qt_escolas_com_ept_tecnica", "qt_escolas_federal_ept_ativa",
    ]
    for col in count_cols:
        neg = (df[col].fillna(0) < 0).sum()
        if neg:
            erros.append("Contagem negativa em {} no painel: {}".format(col, neg))

    return erros


def audit_entradas_saidas(df_escola_ano: pd.DataFrame) -> dict:
    """
    Registra entradas, saídas, lacunas e reversões de presença federal EPT por município.
    Não decide tratamento.
    """
    anos_str = [str(a) for a in ANOS]
    mun_anos = (
        df_escola_ano[df_escola_ano["fl_presenca_federal_ept_ativa"]]
        .groupby("CO_MUNICIPIO")["NU_ANO_CENSO"]
        .apply(lambda x: sorted(x.unique().tolist()))
        .to_dict()
    )

    entradas = []
    saidas = []
    lacunas = []
    reversoes = []

    for mun, anos_presentes in mun_anos.items():
        idx_presentes = [anos_str.index(a) for a in anos_presentes if a in anos_str]
        if not idx_presentes:
            continue

        primeiro = idx_presentes[0]
        ultimo = idx_presentes[-1]

        if primeiro > 0:
            entradas.append({"mun": mun, "primeiro_ano": anos_str[primeiro]})

        if ultimo < len(anos_str) - 1:
            saidas.append({"mun": mun, "ultimo_ano": anos_str[ultimo]})

        # Lacunas: buracos entre primeiro e último
        conjunto = set(idx_presentes)
        for i in range(primeiro, ultimo + 1):
            if i not in conjunto:
                lacunas.append({"mun": mun, "ano_ausente": anos_str[i]})
                reversoes.append({"mun": mun, "ano_lacuna": anos_str[i]})

    return {
        "municipios_com_ept_federal_ativa": len(mun_anos),
        "entradas": entradas,
        "saidas": saidas,
        "lacunas": lacunas,
        "reversoes": reversoes,
    }


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def main() -> dict:
    print("=" * 70)
    print("CONSTRUÇÃO DO PAINEL DO CENSO ESCOLAR 2007-2019")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Carrega lista de municípios Fase II
    # ------------------------------------------------------------------
    print("\n[1] Carregando municípios Fase II...")
    df_fase_ii = pd.read_parquet(FASE_II_PATH)
    fase_ii_mun: list[str] = sorted(
        df_fase_ii["codigo_municipio_ibge"].astype(str).str.zfill(7).tolist()
    )
    print("    Municípios Fase II: {}".format(len(fase_ii_mun)))
    assert len(fase_ii_mun) == 147, "Esperado 147, encontrado {}".format(len(fase_ii_mun))

    # ------------------------------------------------------------------
    # 2. Lê e filtra escolas federais de cada ano
    # ------------------------------------------------------------------
    print("\n[2] Lendo CSVs dos ZIPs (escolas federais apenas)...")
    dfs_por_ano: list[pd.DataFrame] = []
    contagens_por_ano: dict[int, dict] = {}
    contradictions_por_ano: dict[int, dict] = {}

    for year in ANOS:
        print("    {}...".format(year), end=" ", flush=True)
        df_year = read_federal_from_zip(year)

        n_total = len(df_year)
        n_ativas = int(df_year["fl_em_atividade"].sum())
        n_ept = int(df_year["fl_oferta_ept"].sum())
        n_ept_tec = int(df_year["fl_oferta_ept_tecnica"].sum())
        n_ept_ativa = int(df_year["fl_presenca_federal_ept_ativa"].sum())

        contagens_por_ano[year] = {
            "total_escolas_federais": n_total,
            "em_atividade": n_ativas,
            "com_ept": n_ept,
            "com_ept_tecnica": n_ept_tec,
            "federal_ept_ativa": n_ept_ativa,
        }

        contradictions_por_ano[year] = audit_contradictions(df_year, year)
        dfs_por_ano.append(df_year)

        print(
            "federal={} | ativa={} | EPT={} | EPTtec={} | EPTativa={}".format(
                n_total, n_ativas, n_ept, n_ept_tec, n_ept_ativa
            )
        )

    # ------------------------------------------------------------------
    # 3. Tabela escola-ano
    # ------------------------------------------------------------------
    print("\n[3] Concatenando tabela escola-ano...")
    df_escola_ano = pd.concat(dfs_por_ano, ignore_index=True)
    print("    Total de linhas escola-ano: {:,}".format(len(df_escola_ano)))

    # Ordena deterministicamente
    df_escola_ano = df_escola_ano.sort_values(
        ["NU_ANO_CENSO", "CO_ENTIDADE"]
    ).reset_index(drop=True)

    # ------------------------------------------------------------------
    # 4. Validações escola-ano
    # ------------------------------------------------------------------
    print("\n[4] Validando tabela escola-ano...")
    erros_escola = validate_escola_ano(df_escola_ano)
    if erros_escola:
        for e in erros_escola:
            print("    [ERRO] {}".format(e))
    else:
        print("    OK – todas as validações passaram.")

    # ------------------------------------------------------------------
    # 5. Salva escola-ano
    # ------------------------------------------------------------------
    print("\n[5] Salvando escola-ano...")
    out_escola = DATA_INTERIM / "censo_escolas_federais_2007_2019.parquet"
    df_escola_ano.to_parquet(out_escola, index=False, engine="pyarrow")
    hash_escola = sha256_file(out_escola)
    print("    Salvo: {}".format(out_escola))
    print("    SHA-256: {}".format(hash_escola))

    # ------------------------------------------------------------------
    # 6. Agrega município-ano
    # ------------------------------------------------------------------
    print("\n[6] Agregando por município-ano...")
    df_mun_ano = aggregate_municipio_ano(df_escola_ano)
    print("    Linhas município-ano: {:,}".format(len(df_mun_ano)))

    erros_mun = validate_municipio_ano(df_mun_ano)
    if erros_mun:
        for e in erros_mun:
            print("    [ERRO] {}".format(e))
    else:
        print("    OK – validações município-ano passaram.")

    # ------------------------------------------------------------------
    # 7. Salva município-ano
    # ------------------------------------------------------------------
    print("\n[7] Salvando município-ano...")
    out_mun = DATA_INTERIM / "censo_federal_municipio_ano_2007_2019.parquet"
    df_mun_ano.to_parquet(out_mun, index=False, engine="pyarrow")
    hash_mun = sha256_file(out_mun)
    print("    Salvo: {}".format(out_mun))
    print("    SHA-256: {}".format(hash_mun))

    # ------------------------------------------------------------------
    # 8. Painel Fase II
    # ------------------------------------------------------------------
    print("\n[8] Construindo painel Fase II × anos...")
    df_painel = build_fase_ii_panel(df_mun_ano, fase_ii_mun, ANOS, df_fase_ii=df_fase_ii)
    print("    Linhas no painel: {:,}".format(len(df_painel)))

    erros_painel = validate_panel_fase_ii(df_painel, fase_ii_mun)
    if erros_painel:
        for e in erros_painel:
            print("    [ERRO] {}".format(e))
    else:
        print("    OK – validações painel Fase II passaram.")

    # ------------------------------------------------------------------
    # 9. Salva painel Fase II
    # ------------------------------------------------------------------
    print("\n[9] Salvando painel Fase II...")
    out_painel = DATA_PROCESSED / "painel_presenca_federal_ept_fase_ii_2007_2019.parquet"
    df_painel.to_parquet(out_painel, index=False, engine="pyarrow")
    hash_painel = sha256_file(out_painel)
    print("    Salvo: {}".format(out_painel))
    print("    SHA-256: {}".format(hash_painel))

    # ------------------------------------------------------------------
    # 10. Auditoria de entradas, saídas e reversões
    # ------------------------------------------------------------------
    print("\n[10] Auditando entradas, saídas e reversões...")
    auditoria_es = audit_entradas_saidas(df_escola_ano)
    print("    Municípios com EPT federal ativa em algum ano: {}".format(
        auditoria_es["municipios_com_ept_federal_ativa"]))
    print("    Entradas (primeiro ano != 2007): {}".format(len(auditoria_es["entradas"])))
    print("    Saídas (último ano != 2019): {}".format(len(auditoria_es["saidas"])))
    print("    Lacunas/Reversões registradas: {}".format(len(auditoria_es["reversoes"])))

    # ------------------------------------------------------------------
    # 11. Resumo final
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)

    print("\nContagens por ano:")
    print("{:>6} | {:>7} | {:>7} | {:>7} | {:>7} | {:>9}".format(
        "Ano", "Total", "Ativas", "EPT", "EPTtec", "EPTativa"))
    print("-" * 55)
    for yr, c in sorted(contagens_por_ano.items()):
        print("{:>6} | {:>7} | {:>7} | {:>7} | {:>7} | {:>9}".format(
            yr,
            c["total_escolas_federais"],
            c["em_atividade"],
            c["com_ept"],
            c["com_ept_tecnica"],
            c["federal_ept_ativa"],
        ))

    total_contradictions = sum(
        sum(v.values()) for v in contradictions_por_ano.values()
    )
    print("\nTotal de contradições IN_PROF × quantidades: {}".format(total_contradictions))

    if total_contradictions > 0:
        print("\nDetalhe de contradições por ano:")
        for yr, c in sorted(contradictions_por_ano.items()):
            if any(v > 0 for v in c.values()):
                print("  {}: {}".format(yr, c))

    print("\nArquivos criados:")
    print("  {}".format(out_escola))
    print("  {}".format(out_mun))
    print("  {}".format(out_painel))

    print("\nHashes SHA-256:")
    print("  escola-ano     : {}".format(hash_escola))
    print("  município-ano  : {}".format(hash_mun))
    print("  painel Fase II : {}".format(hash_painel))

    print("\nErros de validação:")
    total_erros = len(erros_escola) + len(erros_mun) + len(erros_painel)
    print("  escola-ano     : {}".format(len(erros_escola)))
    print("  município-ano  : {}".format(len(erros_mun)))
    print("  painel Fase II : {}".format(len(erros_painel)))
    print("  TOTAL          : {}".format(total_erros))

    print("\n" + "=" * 70)

    return {
        "contagens_por_ano": contagens_por_ano,
        "contradictions_por_ano": contradictions_por_ano,
        "auditoria_entradas_saidas": auditoria_es,
        "hashes": {
            "escola_ano": hash_escola,
            "municipio_ano": hash_mun,
            "painel_fase_ii": hash_painel,
        },
        "erros": {
            "escola_ano": erros_escola,
            "municipio_ano": erros_mun,
            "painel_fase_ii": erros_painel,
        },
        "n_escola_ano": len(df_escola_ano),
        "n_municipio_ano": len(df_mun_ano),
        "n_painel": len(df_painel),
    }


if __name__ == "__main__":
    main()
