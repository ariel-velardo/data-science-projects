"""
constroi_diagnostico_arranjos_populacionais_fase_ii.py
======================================================
Constrói um diagnóstico EXCLUSIVAMENTE DESCRITIVO de integração funcional
entre os 4.964 municípios candidatos a controle e os 147 municípios da
Expansão Fase II, usando os Arranjos Populacionais do IBGE (Censo
Demográfico 2010) — agrupamentos de municípios com forte integração por
deslocamento pendular (trabalho/estudo) ou contiguidade de manchas
urbanizadas.

Esta rotina NÃO:
  - escolhe definitivamente a regra causal de spillover;
  - exclui nenhum município do pool candidato já aprovado;
  - modifica os artefatos do pool candidato ou do diagnóstico de distâncias;
  - usa CEMPRE, RAIS, PIB ou qualquer outcome econômico;
  - faz matching;
  - estima propensity score ou qualquer efeito causal.

Produz apenas: pertencimento a arranjo populacional, lista determinística
de municípios Fase II no mesmo arranjo (quando existir) e uma flag
diagnóstica de integração funcional, cruzadas com as distâncias e flags
de 25/50/100 km já calculadas (preservadas sem alteração). Pertencer ao
mesmo arranjo populacional NÃO demonstra contaminação efetiva por
spillover; não pertencer a nenhum arranjo NÃO demonstra ausência de
integração territorial (ver
docs/methodology/DIAGNOSTICO_ARRANJOS_POPULACIONAIS_FASE_II.md).

Fontes (lidas, nunca recalculadas ou redefinidas):
  data/processed/pool_candidato_controles_sem_exposicao_2007_2019.parquet
  data/processed/fase_ii_municipios.parquet
  data/processed/diagnostico_distancias_spillover_fase_ii.parquet
  data/raw/ibge/arranjos_populacionais_2010/tab01_municipios_arranjos_populacionais_2010.xlsx
      (IBGE, Censo Demográfico 2010; ver source_manifest.json no mesmo diretório)

Saídas:
  data/interim/arranjos_populacionais_municipios_2010.parquet
  data/processed/diagnostico_arranjos_populacionais_fase_ii.parquet
  outputs/diagnostics/resumo_arranjos_populacionais_fase_ii.csv

Uso:
  python src/constroi_diagnostico_arranjos_populacionais_fase_ii.py
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import openpyxl
import pandas as pd

# ---------------------------------------------------------------------------
# Configuração global
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS_DIAGNOSTICS = ROOT / "outputs" / "diagnostics"

POOL_CANDIDATO_PATH = DATA_PROCESSED / "pool_candidato_controles_sem_exposicao_2007_2019.parquet"
FASE_II_MUNICIPIOS_PATH = DATA_PROCESSED / "fase_ii_municipios.parquet"
DIAGNOSTICO_DISTANCIAS_PATH = DATA_PROCESSED / "diagnostico_distancias_spillover_fase_ii.parquet"
ARRANJOS_BRUTO_PATH = (
    DATA_RAW / "ibge" / "arranjos_populacionais_2010" / "tab01_municipios_arranjos_populacionais_2010.xlsx"
)

OUT_ARRANJOS_INTERIM = DATA_INTERIM / "arranjos_populacionais_municipios_2010.parquet"
OUT_DIAGNOSTICO = DATA_PROCESSED / "diagnostico_arranjos_populacionais_fase_ii.parquet"
OUT_RESUMO = OUTPUTS_DIAGNOSTICS / "resumo_arranjos_populacionais_fase_ii.csv"

N_POOL_ESPERADO = 4964
N_FASE_II_ESPERADO = 147

LIMIARES_KM = (25, 50, 100)

CODIGO_MUNICIPIO_RE = re.compile(r"^\d{7}$")

UF_PARA_REGIAO = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste",
    "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}


# ---------------------------------------------------------------------------
# 1. Leitura dos insumos
# ---------------------------------------------------------------------------


def load_pool_candidato(path: Path = POOL_CANDIDATO_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


def load_fase_ii_municipios(path: Path = FASE_II_MUNICIPIOS_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


def load_diagnostico_distancias(path: Path = DIAGNOSTICO_DISTANCIAS_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


def load_arranjos_bruto(path: Path = ARRANJOS_BRUTO_PATH) -> list[tuple[str, int]]:
    """Lê a Tabela 1.1 bruta e devolve pares (nome_do_arranjo, codigo_municipio)
    na ordem original — sem qualquer coerção de tipo além da leitura da
    célula, para que erros de formato cheguem intactos à validação."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    linhas = list(ws.iter_rows(values_only=True))
    # linha 0 = título da tabela; linha 1 = cabeçalho de colunas; última
    # linha = nota de fonte — nenhuma delas contém dado municipal.
    pares: list[tuple[str, Any]] = []
    arranjo_atual: str | None = None
    for row in linhas[2:-1]:
        nome_ou_codigo_ausente, codigo = row[0], row[1]
        if codigo is None:
            arranjo_atual = nome_ou_codigo_ausente
            continue
        pares.append((arranjo_atual, codigo))
    return pares


# ---------------------------------------------------------------------------
# 2. Validações de código municipal (compartilhadas)
# ---------------------------------------------------------------------------


def _validar_codigos_municipais(codes: pd.Series, contexto: str) -> None:
    if codes.isna().any():
        raise ValueError(f"{contexto}: codigo_municipio_ibge contém valor nulo ({int(codes.isna().sum())} casos).")
    textos = codes.astype(str)
    invalidos = textos.loc[~textos.str.fullmatch(CODIGO_MUNICIPIO_RE)]
    if not invalidos.empty:
        raise ValueError(
            f"{contexto}: codigo_municipio_ibge inválido (esperado 7 dígitos numéricos) em "
            f"{len(invalidos)} casos. Exemplos: {invalidos.head(5).tolist()}"
        )


def _rejeitar_codigos_duplicados(codes: pd.Series, contexto: str) -> None:
    duplicados = codes[codes.duplicated(keep=False)]
    if not duplicados.empty:
        raise ValueError(
            f"{contexto}: codigo_municipio_ibge duplicado em {duplicados.nunique()} códigos. "
            f"Exemplos: {sorted(set(duplicados))[:5]}"
        )


# ---------------------------------------------------------------------------
# 3. Validações dos insumos autorizados
# ---------------------------------------------------------------------------


def validate_pool_candidato(pool: pd.DataFrame) -> None:
    contexto = "pool candidato a controles"
    if "codigo_municipio_ibge" not in pool.columns:
        raise ValueError(f"{contexto}: coluna codigo_municipio_ibge ausente.")
    _validar_codigos_municipais(pool["codigo_municipio_ibge"], contexto)
    _rejeitar_codigos_duplicados(pool["codigo_municipio_ibge"], contexto)
    n_unicos = pool["codigo_municipio_ibge"].nunique()
    if n_unicos != N_POOL_ESPERADO:
        raise ValueError(
            f"{contexto}: esperado exatamente {N_POOL_ESPERADO} códigos municipais únicos; "
            f"encontrado {n_unicos}."
        )


def validate_fase_ii_municipios(fase_ii: pd.DataFrame) -> None:
    contexto = "lista Fase II"
    if "codigo_municipio_ibge" not in fase_ii.columns:
        raise ValueError(f"{contexto}: coluna codigo_municipio_ibge ausente.")
    _validar_codigos_municipais(fase_ii["codigo_municipio_ibge"], contexto)
    _rejeitar_codigos_duplicados(fase_ii["codigo_municipio_ibge"], contexto)
    n_unicos = fase_ii["codigo_municipio_ibge"].nunique()
    if n_unicos != N_FASE_II_ESPERADO:
        raise ValueError(
            f"{contexto}: esperado exatamente {N_FASE_II_ESPERADO} códigos municipais únicos; "
            f"encontrado {n_unicos}."
        )


def validate_diagnostico_distancias_bruto(diag_dist: pd.DataFrame) -> None:
    contexto = "diagnóstico de distâncias (insumo)"
    colunas_exigidas = {
        "codigo_municipio_ibge", "distancia_sedes_km",
        "fl_ate_25_km", "fl_ate_50_km", "fl_ate_100_km",
    }
    faltantes = colunas_exigidas - set(diag_dist.columns)
    if faltantes:
        raise ValueError(f"{contexto}: colunas obrigatórias ausentes: {sorted(faltantes)}.")
    _validar_codigos_municipais(diag_dist["codigo_municipio_ibge"], contexto)
    _rejeitar_codigos_duplicados(diag_dist["codigo_municipio_ibge"], contexto)


# ---------------------------------------------------------------------------
# 4. Construção e validação da composição de arranjos populacionais
# ---------------------------------------------------------------------------


def _slug_arranjo(nome: str) -> str:
    """Identificador determinístico derivado do nome oficialmente publicado
    do arranjo (Tabela 1.1) — NÃO é o código numérico interno (`CodArranjo`)
    da geodatabase Access do IBGE, que não foi extraída nesta rotina (ver
    limitações em DIAGNOSTICO_ARRANJOS_POPULACIONAIS_FASE_II.md)."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", "_", sem_acento.upper()).strip("_")


def build_arranjos_populacionais(pares_brutos: list[tuple[str, Any]]) -> pd.DataFrame:
    """Reconcilia a composição bruta (nome do arranjo, código do município)
    para o schema interino — nenhuma geocodificação por nome de município
    (a chave é sempre o código IBGE), nenhuma coordenada ou composição
    inferida manualmente."""
    if any(codigo is None for _, codigo in pares_brutos):
        raise ValueError(
            "arranjos populacionais IBGE 2010: código de município contém valor nulo na composição bruta."
        )
    nomes = pd.Series([nome for nome, _ in pares_brutos])
    codigos_brutos = pd.Series([codigo for _, codigo in pares_brutos])
    try:
        codigos = codigos_brutos.astype("int64").astype(str).str.zfill(7)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"arranjos populacionais IBGE 2010: código de município não numérico: {exc}") from exc

    arranjos = pd.DataFrame(
        {
            "codigo_municipio_ibge": codigos,
            "nome_arranjo_populacional": nomes,
        }
    )
    arranjos["codigo_arranjo_populacional"] = arranjos["nome_arranjo_populacional"].map(_slug_arranjo)
    arranjos = arranjos.sort_values("codigo_municipio_ibge", kind="stable").reset_index(drop=True)
    return arranjos[["codigo_municipio_ibge", "codigo_arranjo_populacional", "nome_arranjo_populacional"]]


def validate_arranjos_populacionais(arranjos: pd.DataFrame) -> None:
    contexto = "arranjos populacionais IBGE 2010"
    _validar_codigos_municipais(arranjos["codigo_municipio_ibge"], contexto)
    _rejeitar_codigos_duplicados(arranjos["codigo_municipio_ibge"], contexto)
    for coluna in ("codigo_arranjo_populacional", "nome_arranjo_populacional"):
        if arranjos[coluna].isna().any() or (arranjos[coluna] == "").any():
            raise ValueError(f"{contexto}: {coluna} contém valor nulo ou vazio.")


# ---------------------------------------------------------------------------
# 5. Construção do diagnóstico de integração funcional
# ---------------------------------------------------------------------------


def build_diagnostico(
    pool: pd.DataFrame,
    fase_ii: pd.DataFrame,
    diagnostico_distancias: pd.DataFrame,
    arranjos: pd.DataFrame,
) -> pd.DataFrame:
    """Para cada candidato do pool, identifica o arranjo populacional (se
    houver), verifica se algum município Fase II compartilha esse arranjo
    e preserva, sem alteração, a distância e as flags de 25/50/100 km já
    calculadas. Não altera, filtra nem reordena o pool de entrada."""
    base = pool[["codigo_municipio_ibge", "municipio", "uf"]].merge(
        diagnostico_distancias[
            ["codigo_municipio_ibge", "distancia_sedes_km", "fl_ate_25_km", "fl_ate_50_km", "fl_ate_100_km"]
        ],
        on="codigo_municipio_ibge",
        how="left",
        validate="one_to_one",
    )
    if base["distancia_sedes_km"].isna().any():
        faltantes = base.loc[base["distancia_sedes_km"].isna(), "codigo_municipio_ibge"].tolist()
        raise ValueError(f"diagnóstico: candidato(s) sem distância pré-calculada após o merge: {faltantes[:5]}.")

    base = base.merge(
        arranjos,
        on="codigo_municipio_ibge",
        how="left",
        validate="many_to_one",
    )
    base["fl_pertence_arranjo_populacional"] = base["codigo_arranjo_populacional"].notna()

    # Arranjos que contêm ao menos um município Fase II, com a lista
    # determinística (ordenada pelo menor código) dos códigos Fase II
    # pertencentes a cada um desses arranjos.
    fase_ii_com_arranjo = fase_ii[["codigo_municipio_ibge"]].merge(
        arranjos, on="codigo_municipio_ibge", how="inner", validate="one_to_one"
    )
    fase_ii_por_arranjo = (
        fase_ii_com_arranjo.groupby("codigo_arranjo_populacional")["codigo_municipio_ibge"]
        .apply(lambda s: ";".join(sorted(s)))
        .rename("codigos_fase_ii_no_arranjo")
    )

    base = base.merge(
        fase_ii_por_arranjo, on="codigo_arranjo_populacional", how="left", validate="many_to_one"
    )
    base["codigos_fase_ii_no_arranjo"] = base["codigos_fase_ii_no_arranjo"].fillna("")
    base["quantidade_fase_ii_no_arranjo"] = base["codigos_fase_ii_no_arranjo"].apply(
        lambda s: 0 if s == "" else len(s.split(";"))
    )
    base["fl_mesmo_arranjo_populacional_fase_ii"] = base["quantidade_fase_ii_no_arranjo"] > 0

    colunas_finais = [
        "codigo_municipio_ibge", "municipio", "uf",
        "fl_pertence_arranjo_populacional",
        "codigo_arranjo_populacional", "nome_arranjo_populacional",
        "quantidade_fase_ii_no_arranjo", "codigos_fase_ii_no_arranjo",
        "fl_mesmo_arranjo_populacional_fase_ii",
        "distancia_sedes_km", "fl_ate_25_km", "fl_ate_50_km", "fl_ate_100_km",
    ]
    return base[colunas_finais]


# ---------------------------------------------------------------------------
# 6. Validações do diagnóstico
# ---------------------------------------------------------------------------


def validate_diagnostico(
    diagnostico: pd.DataFrame,
    pool: pd.DataFrame,
    fase_ii_codes: set[str],
    diagnostico_distancias: pd.DataFrame,
) -> None:
    contexto = "diagnóstico de arranjos populacionais"

    if diagnostico["codigo_municipio_ibge"].duplicated().any():
        raise ValueError(f"{contexto}: codigo_municipio_ibge duplicado no resultado.")
    if len(diagnostico) != len(pool):
        raise ValueError(f"{contexto}: esperado exatamente {len(pool)} linhas (uma por candidato); encontrado {len(diagnostico)}.")
    if set(diagnostico["codigo_municipio_ibge"]) != set(pool["codigo_municipio_ibge"]):
        raise ValueError(f"{contexto}: conjunto de candidatos do resultado diverge do pool de entrada.")

    for col in ("fl_pertence_arranjo_populacional", "fl_mesmo_arranjo_populacional_fase_ii"):
        if diagnostico[col].isna().any():
            raise ValueError(f"{contexto}: {col} contém valor nulo.")
        if diagnostico[col].dtype != bool:
            raise ValueError(f"{contexto}: {col} deve ser booleana; dtype observado {diagnostico[col].dtype}.")

    sem_arranjo = diagnostico.loc[~diagnostico["fl_pertence_arranjo_populacional"]]
    if sem_arranjo["codigo_arranjo_populacional"].notna().any():
        raise ValueError(f"{contexto}: candidato(s) sem arranjo com codigo_arranjo_populacional não nulo.")
    if sem_arranjo["nome_arranjo_populacional"].notna().any():
        raise ValueError(f"{contexto}: candidato(s) sem arranjo com nome_arranjo_populacional não nulo.")
    if (sem_arranjo["quantidade_fase_ii_no_arranjo"] != 0).any():
        raise ValueError(f"{contexto}: candidato(s) sem arranjo com quantidade_fase_ii_no_arranjo diferente de zero.")
    if sem_arranjo["fl_mesmo_arranjo_populacional_fase_ii"].any():
        raise ValueError(f"{contexto}: candidato(s) sem arranjo marcado(s) como fl_mesmo_arranjo_populacional_fase_ii=True.")

    com_arranjo = diagnostico.loc[diagnostico["fl_pertence_arranjo_populacional"]]
    if com_arranjo["codigo_arranjo_populacional"].isna().any():
        raise ValueError(f"{contexto}: candidato(s) com arranjo mas codigo_arranjo_populacional nulo.")

    esperado_qtd = diagnostico["codigos_fase_ii_no_arranjo"].apply(lambda s: 0 if s == "" else len(s.split(";")))
    if not (diagnostico["quantidade_fase_ii_no_arranjo"] == esperado_qtd).all():
        raise ValueError(f"{contexto}: quantidade_fase_ii_no_arranjo não bate com a lista codigos_fase_ii_no_arranjo.")

    esperado_flag = diagnostico["quantidade_fase_ii_no_arranjo"] > 0
    if not (diagnostico["fl_mesmo_arranjo_populacional_fase_ii"] == esperado_flag).all():
        raise ValueError(f"{contexto}: fl_mesmo_arranjo_populacional_fase_ii não é coerente com quantidade > 0.")

    todos_codigos_listados: set[str] = set()
    for lista in diagnostico.loc[diagnostico["codigos_fase_ii_no_arranjo"] != "", "codigos_fase_ii_no_arranjo"]:
        codigos = lista.split(";")
        if codigos != sorted(codigos):
            raise ValueError(f"{contexto}: lista codigos_fase_ii_no_arranjo não está ordenada deterministicamente: {lista}.")
        todos_codigos_listados |= set(codigos)
    fora_da_fase_ii = todos_codigos_listados - fase_ii_codes
    if fora_da_fase_ii:
        raise ValueError(
            f"{contexto}: código(s) em codigos_fase_ii_no_arranjo fora do conjunto oficial da Fase II: "
            f"{sorted(fora_da_fase_ii)[:5]}."
        )

    dist_original = diagnostico_distancias.set_index("codigo_municipio_ibge")
    dist_resultado = diagnostico.set_index("codigo_municipio_ibge")
    comuns = dist_resultado.index.intersection(dist_original.index)
    for col in ("distancia_sedes_km", "fl_ate_25_km", "fl_ate_50_km", "fl_ate_100_km"):
        if not dist_resultado.loc[comuns, col].equals(dist_original.loc[comuns, col]):
            raise ValueError(f"{contexto}: coluna {col} foi alterada em relação ao diagnóstico de distâncias original.")


# ---------------------------------------------------------------------------
# 7. Resumo diagnóstico
# ---------------------------------------------------------------------------


def build_resumo_diagnostico(diagnostico: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    total = len(diagnostico)
    pertence = diagnostico["fl_pertence_arranjo_populacional"]
    mesmo_arranjo = diagnostico["fl_mesmo_arranjo_populacional_fase_ii"]

    linhas_geral: list[tuple[str, Any]] = [
        ("total_candidatos", total),
        ("candidatos_em_algum_arranjo", int(pertence.sum())),
        ("candidatos_fora_de_arranjo", int((~pertence).sum())),
        ("candidatos_mesmo_arranjo_fase_ii", int(mesmo_arranjo.sum())),
        ("candidatos_em_arranjo_sem_fase_ii", int((pertence & ~mesmo_arranjo).sum())),
        ("arranjos_distintos_com_candidato", int(diagnostico.loc[pertence, "codigo_arranjo_populacional"].nunique())),
        ("arranjos_distintos_com_candidato_e_fase_ii", int(diagnostico.loc[mesmo_arranjo, "codigo_arranjo_populacional"].nunique())),
    ]
    for limiar in LIMIARES_KM:
        col = f"fl_ate_{limiar}_km"
        linhas_geral.append((f"mesmo_arranjo_e_ate_{limiar}_km", int((mesmo_arranjo & diagnostico[col]).sum())))
        linhas_geral.append((f"mesmo_arranjo_e_acima_{limiar}_km", int((mesmo_arranjo & ~diagnostico[col]).sum())))
        linhas_geral.append((f"ate_{limiar}_km_e_fora_do_mesmo_arranjo", int((diagnostico[col] & ~mesmo_arranjo).sum())))
    resumo_geral = pd.DataFrame(linhas_geral, columns=["metrica", "valor"])
    resumo_geral.insert(0, "secao", "geral")

    linhas_uf = []
    for uf, grupo in diagnostico.groupby("uf", sort=True):
        linhas_uf.append({
            "secao": "por_uf", "uf": uf, "macrorregiao": UF_PARA_REGIAO[uf],
            "total_candidatos": len(grupo),
            "em_algum_arranjo": int(grupo["fl_pertence_arranjo_populacional"].sum()),
            "mesmo_arranjo_fase_ii": int(grupo["fl_mesmo_arranjo_populacional_fase_ii"].sum()),
        })
    resumo_uf = pd.DataFrame(linhas_uf)

    linhas_regiao = []
    diagnostico_com_regiao = diagnostico.assign(macrorregiao=diagnostico["uf"].map(UF_PARA_REGIAO))
    for regiao, grupo in diagnostico_com_regiao.groupby("macrorregiao", sort=True):
        linhas_regiao.append({
            "secao": "por_macrorregiao", "macrorregiao": regiao,
            "total_candidatos": len(grupo),
            "em_algum_arranjo": int(grupo["fl_pertence_arranjo_populacional"].sum()),
            "mesmo_arranjo_fase_ii": int(grupo["fl_mesmo_arranjo_populacional_fase_ii"].sum()),
        })
    resumo_regiao = pd.DataFrame(linhas_regiao)

    return resumo_geral, resumo_uf, resumo_regiao


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def main() -> dict[str, Any]:
    print("=" * 70)
    print("DIAGNÓSTICO DE INTEGRAÇÃO FUNCIONAL (ARRANJOS POPULACIONAIS) — POOL x FASE II")
    print("=" * 70)
    print("\nATENÇÃO: rotina exclusivamente diagnóstica. Não escolhe regra causal,")
    print("não exclui municípios do pool, não usa outcomes econômicos.")

    print("\n[1] Lendo insumos autorizados...")
    pool = load_pool_candidato()
    fase_ii = load_fase_ii_municipios()
    diagnostico_distancias = load_diagnostico_distancias()
    pares_brutos = load_arranjos_bruto()
    print(f"    pool candidato: {len(pool):,} linhas")
    print(f"    lista Fase II: {len(fase_ii):,} linhas")
    print(f"    diagnóstico de distâncias: {len(diagnostico_distancias):,} linhas")
    print(f"    composição bruta de arranjos: {len(pares_brutos):,} pares (arranjo, município)")

    print("\n[2] Validando insumos...")
    validate_pool_candidato(pool)
    validate_fase_ii_municipios(fase_ii)
    validate_diagnostico_distancias_bruto(diagnostico_distancias)
    fase_ii_codes = set(fase_ii["codigo_municipio_ibge"])
    print("    OK — pool, Fase II e diagnóstico de distâncias válidos.")

    print("\n[3] Construindo e validando composição de arranjos populacionais...")
    arranjos = build_arranjos_populacionais(pares_brutos)
    validate_arranjos_populacionais(arranjos)
    print(f"    arranjos reconciliados: {len(arranjos):,} municípios em "
          f"{arranjos['codigo_arranjo_populacional'].nunique():,} arranjos distintos.")

    print("\n[4] Construindo diagnóstico de integração funcional...")
    diagnostico = build_diagnostico(pool, fase_ii, diagnostico_distancias, arranjos)
    print(f"    Linhas do diagnóstico: {len(diagnostico):,}")

    print("\n[5] Validando diagnóstico...")
    validate_diagnostico(diagnostico, pool, fase_ii_codes, diagnostico_distancias)
    print("    OK — validações estruturais e lógicas do diagnóstico passaram.")

    print("\n[6] Construindo resumo diagnóstico...")
    resumo_geral, resumo_uf, resumo_regiao = build_resumo_diagnostico(diagnostico)

    print("\n[7] Salvando artefatos...")
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIAGNOSTICS.mkdir(parents=True, exist_ok=True)
    arranjos.to_parquet(OUT_ARRANJOS_INTERIM, index=False, engine="pyarrow")
    diagnostico.to_parquet(OUT_DIAGNOSTICO, index=False, engine="pyarrow")
    with open(OUT_RESUMO, "w", newline="", encoding="utf-8") as f:
        resumo_geral.to_csv(f, index=False)
        f.write("\n")
        resumo_uf.to_csv(f, index=False)
        f.write("\n")
        resumo_regiao.to_csv(f, index=False)
    print(f"    {OUT_ARRANJOS_INTERIM}")
    print(f"    {OUT_DIAGNOSTICO}")
    print(f"    {OUT_RESUMO}")

    valores = dict(zip(resumo_geral["metrica"], resumo_geral["valor"]))

    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)
    print(f"Total de candidatos: {valores['total_candidatos']:,}")
    print(f"Em algum arranjo populacional: {valores['candidatos_em_algum_arranjo']:,}")
    print(f"Fora de qualquer arranjo: {valores['candidatos_fora_de_arranjo']:,}")
    print(f"No mesmo arranjo de algum Fase II: {valores['candidatos_mesmo_arranjo_fase_ii']:,}")
    print(f"Em arranjo sem Fase II: {valores['candidatos_em_arranjo_sem_fase_ii']:,}")
    for limiar in LIMIARES_KM:
        print(f"Mesmo arranjo Fase II e > {limiar} km: {valores[f'mesmo_arranjo_e_acima_{limiar}_km']:,}")
        print(f"Até {limiar} km mas fora do mesmo arranjo: {valores[f'ate_{limiar}_km_e_fora_do_mesmo_arranjo']:,}")
    print("\nATENÇÃO: pertencer ao mesmo arranjo não demonstra contaminação efetiva;")
    print("não pertencer a nenhum arranjo não demonstra ausência de integração.")
    print("Nenhum município foi removido do pool. Nenhum outcome econômico foi")
    print("consultado. Nenhuma regra causal definitiva foi escolhida (ver")
    print("docs/methodology/DIAGNOSTICO_ARRANJOS_POPULACIONAIS_FASE_II.md).")

    return {
        "pool": pool, "fase_ii": fase_ii, "arranjos": arranjos,
        "diagnostico": diagnostico, "resumo_geral": resumo_geral,
        "resumo_uf": resumo_uf, "resumo_regiao": resumo_regiao,
        **valores,
    }


if __name__ == "__main__":
    main()
