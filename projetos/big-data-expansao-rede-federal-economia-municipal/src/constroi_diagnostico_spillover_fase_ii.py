"""
constroi_diagnostico_spillover_fase_ii.py
======================================================
Constrói uma base EXCLUSIVAMENTE DIAGNÓSTICA de proximidade espacial entre
os 4.964 municípios candidatos a controle (ver
`docs/methodology/POOL_CANDIDATO_CONTROLES.md`) e os 147 municípios da
Expansão Fase II, usando a distância geodésica de Haversine entre sedes
municipais (IBGE, 2010).

Esta rotina NÃO:
  - escolhe definitivamente o filtro de spillover;
  - exclui nenhum município do pool já aprovado;
  - modifica os artefatos do pool candidato;
  - usa CEMPRE, RAIS, PIB ou qualquer outcome econômico;
  - faz matching;
  - estima propensity score ou qualquer efeito causal.

Produz apenas: distância geodésica entre sedes municipais e flags
diagnósticas booleanas para os limiares exploratórios de 25 km, 50 km e
100 km (ver `docs/methodology/DIAGNOSTICO_SPILLOVER_FASE_II.md` para a
justificativa de cada limiar e suas limitações). Nenhum dos três limiares
é apresentado como "o raio verdadeiro" do spillover.

Fontes (lidas, nunca recalculadas ou redefinidas):
  data/processed/pool_candidato_controles_sem_exposicao_2007_2019.parquet
  data/processed/fase_ii_municipios.parquet
  data/raw/geobr/sedes_municipais/municipalseats_2010.parquet (IBGE via geobr,
      ver data/raw/geobr/sedes_municipais/source_manifest.json)

Saídas:
  data/interim/sedes_municipais_ibge_2010.parquet
  data/processed/diagnostico_distancias_spillover_fase_ii.parquet
  outputs/diagnostics/resumo_distancias_spillover_fase_ii.csv

Uso:
  python src/constroi_diagnostico_spillover_fase_ii.py
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path
from typing import Any

import numpy as np
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
SEDES_BRUTO_PATH = DATA_RAW / "geobr" / "sedes_municipais" / "municipalseats_2010.parquet"

OUT_SEDES_INTERIM = DATA_INTERIM / "sedes_municipais_ibge_2010.parquet"
OUT_DIAGNOSTICO = DATA_PROCESSED / "diagnostico_distancias_spillover_fase_ii.parquet"
OUT_RESUMO = OUTPUTS_DIAGNOSTICS / "resumo_distancias_spillover_fase_ii.csv"

N_POOL_ESPERADO = 4964
N_FASE_II_ESPERADO = 147

RAIO_TERRA_KM = 6371.0088  # raio médio da Terra (IUGG), usado pela fórmula de Haversine

LIMIARES_KM = (25, 50, 100)

# Faixa geográfica plausível do território brasileiro (com folga), usada
# apenas para rejeitar coordenadas manifestamente inválidas — não uma
# fronteira administrativa exata.
LAT_MIN_BR, LAT_MAX_BR = -35.0, 6.0
LON_MIN_BR, LON_MAX_BR = -75.0, -30.0

CODIGO_MUNICIPIO_RE = re.compile(r"^\d{7}$")


# ---------------------------------------------------------------------------
# 1. Leitura dos insumos
# ---------------------------------------------------------------------------


def load_pool_candidato(path: Path = POOL_CANDIDATO_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


def load_fase_ii_municipios(path: Path = FASE_II_MUNICIPIOS_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


def load_sedes_municipais_bruto(path: Path = SEDES_BRUTO_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


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


def validate_fase_ii_not_in_pool(pool_codes: set[str], fase_ii_codes: set[str]) -> None:
    intersecao = sorted(pool_codes & fase_ii_codes)
    if intersecao:
        raise ValueError(
            f"pool candidato a controles: {len(intersecao)} município(s) da Fase II presente(s) no "
            f"pool candidato (não deveria ocorrer, pool já exclui Fase II). Exemplos: {intersecao[:5]}."
        )


# ---------------------------------------------------------------------------
# 4. Construção e validação da fonte espacial (sedes municipais IBGE 2010)
# ---------------------------------------------------------------------------


def _parse_wkb_point(wkb: bytes) -> tuple[float, float]:
    """Extrai (longitude, latitude) de um ponto WKB little-endian de 21
    bytes (1 byte de ordem + 4 bytes de tipo geométrico + 2 doubles).
    Implementado sem shapely/geopandas (não instalados no ambiente) porque
    o formato de um ponto WKB é fixo e documentado (ISO 13249-3 / OGC)."""
    byte_order, geom_type = wkb[0], struct.unpack_from("<I", wkb, 1)[0]
    if byte_order != 1:
        raise ValueError(f"sedes municipais IBGE: WKB com ordem de bytes não suportada ({byte_order}).")
    if geom_type != 1:
        raise ValueError(f"sedes municipais IBGE: WKB não é um Point (geom_type={geom_type}).")
    lon, lat = struct.unpack_from("<dd", wkb, 5)
    return lon, lat


def build_sedes_municipais(bruto: pd.DataFrame) -> pd.DataFrame:
    """Reconcilia os códigos municipais da fonte bruta (float, ex.:
    1100015.0) para string de 7 dígitos e extrai latitude/longitude do WKB
    — nenhuma geocodificação por nome, nenhuma coordenada inferida
    manualmente."""
    contexto = "sedes municipais IBGE 2010"
    if bruto["code_muni"].isna().any():
        raise ValueError(f"{contexto}: code_muni contém valor nulo ({int(bruto['code_muni'].isna().sum())} casos).")
    if bruto["geometry"].isna().any():
        raise ValueError(f"{contexto}: geometry contém valor nulo ({int(bruto['geometry'].isna().sum())} casos).")

    codigos = bruto["code_muni"].astype("int64").astype(str).str.zfill(7)
    coords = bruto["geometry"].apply(_parse_wkb_point)
    sedes = pd.DataFrame(
        {
            "codigo_municipio_ibge": codigos,
            "longitude_sede": [c[0] for c in coords],
            "latitude_sede": [c[1] for c in coords],
        }
    )
    sedes = sedes.sort_values("codigo_municipio_ibge", kind="stable").reset_index(drop=True)
    return sedes


def validate_sedes_municipais(sedes: pd.DataFrame) -> None:
    contexto = "sedes municipais IBGE 2010"
    _validar_codigos_municipais(sedes["codigo_municipio_ibge"], contexto)
    _rejeitar_codigos_duplicados(sedes["codigo_municipio_ibge"], contexto)

    for coluna, minimo, maximo in (
        ("latitude_sede", LAT_MIN_BR, LAT_MAX_BR),
        ("longitude_sede", LON_MIN_BR, LON_MAX_BR),
    ):
        if sedes[coluna].isna().any():
            raise ValueError(f"{contexto}: {coluna} contém valor nulo ({int(sedes[coluna].isna().sum())} casos).")
        fora_do_intervalo = sedes.loc[(sedes[coluna] < minimo) | (sedes[coluna] > maximo)]
        if not fora_do_intervalo.empty:
            raise ValueError(
                f"{contexto}: {coluna} fora do intervalo geográfico válido [{minimo}, {maximo}] em "
                f"{len(fora_do_intervalo)} caso(s). Exemplos: "
                f"{fora_do_intervalo['codigo_municipio_ibge'].head(5).tolist()}"
            )


def validate_cobertura_espacial(pool_codes: set[str], fase_ii_codes: set[str], sedes_codes: set[str]) -> None:
    contexto = "cobertura espacial"
    faltantes_pool = sorted(pool_codes - sedes_codes)
    if faltantes_pool:
        raise ValueError(
            f"{contexto}: {len(faltantes_pool)} candidato(s) sem sede municipal na fonte espacial. "
            f"Exemplos: {faltantes_pool[:5]}."
        )
    faltantes_fase_ii = sorted(fase_ii_codes - sedes_codes)
    if faltantes_fase_ii:
        raise ValueError(
            f"{contexto}: {len(faltantes_fase_ii)} município(s) Fase II sem sede municipal na fonte "
            f"espacial. Exemplos: {faltantes_fase_ii[:5]}."
        )


# ---------------------------------------------------------------------------
# 5. Distância geodésica de Haversine
# ---------------------------------------------------------------------------


def haversine_km(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Distância geodésica entre sedes municipais (não confundir com
    distância rodoviária, tempo de viagem, fluxo pendular ou área de
    influência efetiva). Aceita arrays broadcastable do numpy."""
    lat1_r, lon1_r, lat2_r, lon2_r = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return RAIO_TERRA_KM * c


# ---------------------------------------------------------------------------
# 6. Construção do diagnóstico de distâncias
# ---------------------------------------------------------------------------


def build_diagnostico(pool: pd.DataFrame, fase_ii: pd.DataFrame, sedes: pd.DataFrame) -> pd.DataFrame:
    """Para cada candidato do pool, calcula a distância geodésica de
    Haversine (sede a sede) até cada um dos 147 municípios Fase II e
    identifica o mais próximo, com desempate determinístico pelo menor
    código IBGE Fase II. Não altera, filtra nem reordena o pool de
    entrada — cada linha do resultado corresponde a exatamente um
    candidato do pool."""
    candidatos = pool[["codigo_municipio_ibge", "municipio", "uf"]].merge(
        sedes[["codigo_municipio_ibge", "latitude_sede", "longitude_sede"]],
        on="codigo_municipio_ibge",
        how="left",
        validate="many_to_one",
    )
    if candidatos["latitude_sede"].isna().any() or candidatos["longitude_sede"].isna().any():
        faltantes = candidatos.loc[candidatos["latitude_sede"].isna(), "codigo_municipio_ibge"].tolist()
        raise ValueError(f"diagnóstico: candidato(s) sem sede municipal após o merge: {faltantes[:5]}.")

    tratados = fase_ii[["codigo_municipio_ibge", "municipio", "uf"]].merge(
        sedes[["codigo_municipio_ibge", "latitude_sede", "longitude_sede"]],
        on="codigo_municipio_ibge",
        how="left",
        validate="many_to_one",
    )
    if tratados["latitude_sede"].isna().any() or tratados["longitude_sede"].isna().any():
        faltantes = tratados.loc[tratados["latitude_sede"].isna(), "codigo_municipio_ibge"].tolist()
        raise ValueError(f"diagnóstico: município(s) Fase II sem sede municipal após o merge: {faltantes[:5]}.")

    # Desempate determinístico pelo menor código IBGE Fase II: ordenar os
    # tratados por código ascendente antes de montar a matriz de distâncias
    # faz com que `argmin` (que retorna a primeira ocorrência do mínimo em
    # caso de empate exato) já devolva o índice do menor código.
    tratados = tratados.sort_values("codigo_municipio_ibge", kind="stable").reset_index(drop=True)

    dist_matrix = haversine_km(
        candidatos["latitude_sede"].to_numpy()[:, None],
        candidatos["longitude_sede"].to_numpy()[:, None],
        tratados["latitude_sede"].to_numpy()[None, :],
        tratados["longitude_sede"].to_numpy()[None, :],
    )
    idx_mais_proximo = np.argmin(dist_matrix, axis=1)
    distancia_min = dist_matrix[np.arange(len(candidatos)), idx_mais_proximo]

    diagnostico = pd.DataFrame(
        {
            "codigo_municipio_ibge": candidatos["codigo_municipio_ibge"],
            "municipio": candidatos["municipio"],
            "uf": candidatos["uf"],
            "latitude_sede": candidatos["latitude_sede"],
            "longitude_sede": candidatos["longitude_sede"],
            "codigo_municipio_fase_ii_mais_proximo": tratados["codigo_municipio_ibge"].to_numpy()[idx_mais_proximo],
            "municipio_fase_ii_mais_proximo": tratados["municipio"].to_numpy()[idx_mais_proximo],
            "uf_fase_ii_mais_proximo": tratados["uf"].to_numpy()[idx_mais_proximo],
            "latitude_sede_fase_ii": tratados["latitude_sede"].to_numpy()[idx_mais_proximo],
            "longitude_sede_fase_ii": tratados["longitude_sede"].to_numpy()[idx_mais_proximo],
            "distancia_sedes_km": distancia_min,
        }
    )
    for limiar in LIMIARES_KM:
        diagnostico[f"fl_ate_{limiar}_km"] = (diagnostico["distancia_sedes_km"] <= limiar).astype(bool)

    return diagnostico


# ---------------------------------------------------------------------------
# 7. Validações do diagnóstico
# ---------------------------------------------------------------------------


def validate_diagnostico(diagnostico: pd.DataFrame, pool: pd.DataFrame, fase_ii_codes: set[str]) -> None:
    contexto = "diagnóstico de distâncias"

    if diagnostico["codigo_municipio_ibge"].duplicated().any():
        raise ValueError(f"{contexto}: codigo_municipio_ibge duplicado no resultado (mais de uma correspondência).")

    if len(diagnostico) != len(pool):
        raise ValueError(f"{contexto}: esperado exatamente {len(pool)} linhas (uma por candidato); encontrado {len(diagnostico)}.")

    if set(diagnostico["codigo_municipio_ibge"]) != set(pool["codigo_municipio_ibge"]):
        raise ValueError(f"{contexto}: conjunto de candidatos do resultado diverge do pool de entrada.")

    fora_da_fase_ii = set(diagnostico["codigo_municipio_fase_ii_mais_proximo"]) - fase_ii_codes
    if fora_da_fase_ii:
        raise ValueError(
            f"{contexto}: município(s) mais próximo(s) fora do conjunto oficial da Fase II: "
            f"{sorted(fora_da_fase_ii)[:5]}."
        )

    dist = diagnostico["distancia_sedes_km"]
    if not np.isfinite(dist).all():
        raise ValueError(f"{contexto}: distancia_sedes_km contém valor não finito.")
    if (dist < 0).any():
        raise ValueError(f"{contexto}: distancia_sedes_km contém valor negativo.")

    for limiar in LIMIARES_KM:
        col = f"fl_ate_{limiar}_km"
        if diagnostico[col].isna().any():
            raise ValueError(f"{contexto}: {col} contém valor nulo.")
        if diagnostico[col].dtype != bool:
            raise ValueError(f"{contexto}: {col} deve ser booleana; dtype observado {diagnostico[col].dtype}.")

    # Checada antes da equivalência com a distância: uma violação de
    # monotonicidade também violaria a equivalência de algum dos dois
    # limiares envolvidos, mas a mensagem de monotonicidade é mais
    # específica sobre a natureza estrutural do problema.
    if not (diagnostico["fl_ate_25_km"] <= diagnostico["fl_ate_50_km"]).all():
        raise ValueError(f"{contexto}: monotonicidade violada entre fl_ate_25_km e fl_ate_50_km.")
    if not (diagnostico["fl_ate_50_km"] <= diagnostico["fl_ate_100_km"]).all():
        raise ValueError(f"{contexto}: monotonicidade violada entre fl_ate_50_km e fl_ate_100_km.")

    for limiar in LIMIARES_KM:
        col = f"fl_ate_{limiar}_km"
        esperado = dist <= limiar
        if not (diagnostico[col] == esperado).all():
            raise ValueError(f"{contexto}: {col} não é exatamente equivalente a distancia_sedes_km <= {limiar}.")


# ---------------------------------------------------------------------------
# 8. Resumo diagnóstico
# ---------------------------------------------------------------------------

PERCENTIS = (1, 5, 10, 25, 50, 75, 90, 95, 99)


def build_resumo_diagnostico(diagnostico: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    dist = diagnostico["distancia_sedes_km"]
    total = len(diagnostico)

    linhas: list[tuple[str, Any]] = [
        ("total_candidatos", total),
        ("distancia_minima_km", float(dist.min())),
    ]
    for p in PERCENTIS:
        linhas.append((f"distancia_percentil_{p}_km", float(np.percentile(dist, p))))
    linhas.append(("distancia_maxima_km", float(dist.max())))

    for limiar in LIMIARES_KM:
        flag = diagnostico[f"fl_ate_{limiar}_km"]
        linhas.append((f"quantidade_ate_{limiar}_km", int(flag.sum())))
        linhas.append((f"proporcao_ate_{limiar}_km", float(flag.mean())))

    acima_100 = ~diagnostico["fl_ate_100_km"]
    linhas.append(("quantidade_acima_100_km", int(acima_100.sum())))
    linhas.append(("proporcao_acima_100_km", float(acima_100.mean())))

    resumo = pd.DataFrame(linhas, columns=["metrica", "valor"])
    resumo.insert(0, "secao", "geral")

    linhas_uf = []
    for uf, grupo in diagnostico.groupby("uf", sort=True):
        linha_uf: dict[str, Any] = {"secao": "por_uf", "uf": uf, "total_candidatos": len(grupo)}
        for limiar in LIMIARES_KM:
            flag = grupo[f"fl_ate_{limiar}_km"]
            linha_uf[f"quantidade_ate_{limiar}_km"] = int(flag.sum())
            linha_uf[f"proporcao_ate_{limiar}_km"] = float(flag.mean())
        linhas_uf.append(linha_uf)
    resumo_uf = pd.DataFrame(linhas_uf)

    return resumo, resumo_uf


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def main() -> dict[str, Any]:
    print("=" * 70)
    print("DIAGNÓSTICO DE PROXIMIDADE ESPACIAL — POOL CANDIDATO x FASE II")
    print("=" * 70)
    print("\nATENÇÃO: rotina exclusivamente diagnóstica. Não escolhe filtro de")
    print("spillover, não exclui municípios do pool, não usa outcomes econômicos.")

    print("\n[1] Lendo insumos autorizados...")
    pool = load_pool_candidato()
    fase_ii = load_fase_ii_municipios()
    sedes_bruto = load_sedes_municipais_bruto()
    print(f"    pool candidato: {len(pool):,} linhas")
    print(f"    lista Fase II: {len(fase_ii):,} linhas")
    print(f"    sedes municipais (bruto): {len(sedes_bruto):,} linhas")

    print("\n[2] Validando insumos...")
    validate_pool_candidato(pool)
    validate_fase_ii_municipios(fase_ii)
    pool_codes = set(pool["codigo_municipio_ibge"])
    fase_ii_codes = set(fase_ii["codigo_municipio_ibge"])
    validate_fase_ii_not_in_pool(pool_codes, fase_ii_codes)
    print("    OK — pool e Fase II válidos e mutuamente exclusivos.")

    print("\n[3] Construindo e validando fonte espacial (sedes municipais IBGE 2010)...")
    sedes = build_sedes_municipais(sedes_bruto)
    validate_sedes_municipais(sedes)
    sedes_codes = set(sedes["codigo_municipio_ibge"])
    validate_cobertura_espacial(pool_codes, fase_ii_codes, sedes_codes)
    print(f"    sedes reconciliadas: {len(sedes):,} linhas — cobertura exata confirmada.")

    print("\n[4] Construindo diagnóstico de distâncias...")
    diagnostico = build_diagnostico(pool, fase_ii, sedes)
    print(f"    Linhas do diagnóstico: {len(diagnostico):,}")

    print("\n[5] Validando diagnóstico...")
    validate_diagnostico(diagnostico, pool, fase_ii_codes)
    print("    OK — validações estruturais e lógicas do diagnóstico passaram.")

    print("\n[6] Construindo resumo diagnóstico...")
    resumo_geral, resumo_uf = build_resumo_diagnostico(diagnostico)

    print("\n[7] Salvando artefatos...")
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIAGNOSTICS.mkdir(parents=True, exist_ok=True)
    sedes.to_parquet(OUT_SEDES_INTERIM, index=False, engine="pyarrow")
    diagnostico.to_parquet(OUT_DIAGNOSTICO, index=False, engine="pyarrow")
    with open(OUT_RESUMO, "w", newline="", encoding="utf-8") as f:
        resumo_geral.to_csv(f, index=False)
        f.write("\n")
        resumo_uf.to_csv(f, index=False)
    print(f"    {OUT_SEDES_INTERIM}")
    print(f"    {OUT_DIAGNOSTICO}")
    print(f"    {OUT_RESUMO}")

    valores = dict(zip(resumo_geral["metrica"], resumo_geral["valor"]))

    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)
    print(f"Total de candidatos: {valores['total_candidatos']:,.0f}")
    print(f"Distância mínima: {valores['distancia_minima_km']:.2f} km")
    print(f"Distância mediana: {valores['distancia_percentil_50_km']:.2f} km")
    print(f"Distância máxima: {valores['distancia_maxima_km']:.2f} km")
    for limiar in LIMIARES_KM:
        qtd = valores[f"quantidade_ate_{limiar}_km"]
        prop = valores[f"proporcao_ate_{limiar}_km"]
        print(f"Até {limiar} km: {qtd:,.0f} candidatos ({prop:.2%})")
    print(f"Acima de 100 km: {valores['quantidade_acima_100_km']:,.0f} candidatos ({valores['proporcao_acima_100_km']:.2%})")
    print("\nATENÇÃO: nenhum limiar acima é 'o raio verdadeiro' do spillover.")
    print("Nenhum município foi removido do pool. Nenhum outcome econômico foi")
    print("consultado. A escolha do filtro principal ocorrerá antes da estimação")
    print("dos efeitos, acompanhada de análises de sensibilidade (ver")
    print("docs/methodology/DIAGNOSTICO_SPILLOVER_FASE_II.md).")

    return {
        "pool": pool, "fase_ii": fase_ii, "sedes": sedes,
        "diagnostico": diagnostico, "resumo_geral": resumo_geral, "resumo_uf": resumo_uf,
        **valores,
    }


if __name__ == "__main__":
    main()
