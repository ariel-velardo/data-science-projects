"""
constroi_pool_candidato_controles.py
======================================================
Constrói o pool inicial de municípios CANDIDATOS a controle para a
Expansão Fase II — apenas com base em ausência de exposição federal
observada, presença completa no universo municipal 2007-2019 e
não-pertencimento à lista oficial da Fase II.

Esta rotina NÃO faz matching, NÃO usa outcomes econômicos (CEMPRE ou
qualquer outro), NÃO estima efeito causal e NÃO define controles finais.
Um município `fl_elegivel_controle_candidato=True` é apenas um
"candidato a controle sem exposição observada em 2007-2019" — nunca um
"never-treated" comprovado fora da janela, nem um controle causal
definitivo (ver `docs/methodology/POOL_CANDIDATO_CONTROLES.md` e
`docs/methodology/CONTRATO_CAUSAL.md`).

Regra de elegibilidade (não redefine exposição observada — reaproveita
o campo já documentado `sem_exposicao_observada_2007_2019` do cadastro
nacional de exposição):

    elegivel =
        sem_exposicao_observada_2007_2019
        AND presente_nos_13_anos_do_universo
        AND NOT fl_municipio_fase_ii

Fontes (lidas, nunca recalculadas ou redefinidas):
  data/processed/resumo_exposicao_rede_federal_municipio_2007_2019.parquet
  data/processed/fase_ii_municipios.parquet

Saídas:
  data/processed/cadastro_elegibilidade_controles_2007_2019.parquet
  data/processed/pool_candidato_controles_sem_exposicao_2007_2019.parquet
  outputs/diagnostics/resumo_pool_candidato_controles.csv

Uso:
  python src/constroi_pool_candidato_controles.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Configuração global
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS_DIAGNOSTICS = ROOT / "outputs" / "diagnostics"

RESUMO_NACIONAL_PATH = DATA_PROCESSED / "resumo_exposicao_rede_federal_municipio_2007_2019.parquet"
FASE_II_MUNICIPIOS_PATH = DATA_PROCESSED / "fase_ii_municipios.parquet"

OUT_CADASTRO = DATA_PROCESSED / "cadastro_elegibilidade_controles_2007_2019.parquet"
OUT_POOL = DATA_PROCESSED / "pool_candidato_controles_sem_exposicao_2007_2019.parquet"
OUT_DIAGNOSTICO = OUTPUTS_DIAGNOSTICS / "resumo_pool_candidato_controles.csv"

N_MUNICIPIOS_ESPERADO = 5570
N_FASE_II_ESPERADO = 147

CODIGO_MUNICIPIO_RE = re.compile(r"^\d{7}$")

# Colunas do resumo nacional preservadas por serem úteis ao diagnóstico,
# sem criar ambiguidade com as flags de elegibilidade — só entram se
# existirem na fonte (dados sintéticos de teste não precisam tê-las).
EXTRA_COLUNAS_UTEIS = [
    "primeiro_ano_exposicao_observada",
    "n_anos_no_universo",
    "anos_ausentes_do_universo",
]

MOTIVOS_EXCLUSAO: list[tuple[str, str]] = [
    ("fl_excluir_exposicao_observada", "exposicao_observada"),
    ("fl_excluir_universo_incompleto", "universo_incompleto"),
    ("fl_excluir_fase_ii", "fase_ii"),
]


# ---------------------------------------------------------------------------
# 1. Leitura dos insumos
# ---------------------------------------------------------------------------


def load_resumo_nacional(path: Path = RESUMO_NACIONAL_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


def load_fase_ii_municipios(path: Path = FASE_II_MUNICIPIOS_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


# ---------------------------------------------------------------------------
# 2. Validações dos insumos (validações 1-6)
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


def _validar_flag_booleana(series: pd.Series, nome: str) -> None:
    if series.isna().any():
        raise ValueError(f"{nome} contém valor nulo ({int(series.isna().sum())} casos).")
    if series.dtype != bool and str(series.dtype) != "boolean":
        raise ValueError(f"{nome} deve ser booleana; dtype observado: {series.dtype}.")


def validate_resumo_nacional(resumo: pd.DataFrame) -> None:
    """Valida o resumo nacional de exposição observada. Não recalcula nem
    redefine `sem_exposicao_observada_2007_2019` — apenas confirma que o
    campo existe e está bem formado, exatamente como documentado em
    `CADASTRO_NACIONAL_EXPOSICAO_REDE_FEDERAL.md`."""
    contexto = "resumo nacional de exposição"
    colunas_exigidas = {
        "codigo_municipio_ibge", "municipio", "uf", "co_uf",
        "sem_exposicao_observada_2007_2019", "presente_nos_13_anos_do_universo",
    }
    faltantes = colunas_exigidas - set(resumo.columns)
    if faltantes:
        raise ValueError(f"{contexto}: colunas obrigatórias ausentes: {sorted(faltantes)}.")

    for col in ("municipio", "uf", "co_uf"):
        if resumo[col].isna().any():
            raise ValueError(f"{contexto}: coluna {col} contém valor nulo.")

    _validar_codigos_municipais(resumo["codigo_municipio_ibge"], contexto)
    _rejeitar_codigos_duplicados(resumo["codigo_municipio_ibge"], contexto)
    _validar_flag_booleana(
        resumo["sem_exposicao_observada_2007_2019"], f"{contexto}: sem_exposicao_observada_2007_2019"
    )
    _validar_flag_booleana(
        resumo["presente_nos_13_anos_do_universo"], f"{contexto}: presente_nos_13_anos_do_universo"
    )

    n_unicos = resumo["codigo_municipio_ibge"].nunique()
    if n_unicos != N_MUNICIPIOS_ESPERADO:
        raise ValueError(
            f"{contexto}: esperado exatamente {N_MUNICIPIOS_ESPERADO} códigos municipais únicos; "
            f"encontrado {n_unicos}."
        )


def validate_fase_ii_municipios(fase_ii: pd.DataFrame) -> None:
    """Valida a lista oficial da Fase II. Não recalcula nem redefine a
    lista — apenas confirma formato, unicidade e cardinalidade."""
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


def validate_fase_ii_subset_universo(fase_ii_codes: set[str], universo_codes: set[str]) -> None:
    """Confirma que todo código da lista Fase II pertence ao universo
    municipal nacional do resumo (validação 6)."""
    fora_do_universo = sorted(fase_ii_codes - universo_codes)
    if fora_do_universo:
        raise ValueError(
            f"{len(fora_do_universo)} código(s) da lista Fase II não pertencem ao universo "
            f"nacional do resumo de exposição. Exemplos: {fora_do_universo[:5]}."
        )


# ---------------------------------------------------------------------------
# 3. Construção do cadastro de elegibilidade
# ---------------------------------------------------------------------------


def _monta_motivos_exclusao(cadastro: pd.DataFrame) -> pd.Series:
    """Concatena, sem hierarquia, todos os motivos de exclusão aplicáveis
    a cada linha — nunca esconde sobreposições entre motivos."""

    def motivos_da_linha(row: pd.Series) -> str:
        return ";".join(rotulo for coluna, rotulo in MOTIVOS_EXCLUSAO if row[coluna])

    return cadastro.apply(motivos_da_linha, axis=1)


def build_cadastro_elegibilidade(resumo: pd.DataFrame, fase_ii_codes: set[str]) -> pd.DataFrame:
    """Constrói o cadastro completo de elegibilidade — uma linha por
    município do resumo nacional, com todas as flags de exclusão e a
    flag final `fl_elegivel_controle_candidato`, sem apagar nenhum
    município inelegível."""
    colunas_base = ["codigo_municipio_ibge", "municipio", "uf", "co_uf"]
    colunas_extras = [c for c in EXTRA_COLUNAS_UTEIS if c in resumo.columns]
    colunas_fonte = [
        *colunas_base, *colunas_extras,
        "sem_exposicao_observada_2007_2019", "presente_nos_13_anos_do_universo",
    ]
    cadastro = resumo[colunas_fonte].copy()
    cadastro["codigo_municipio_ibge"] = (
        cadastro["codigo_municipio_ibge"].astype(str).str.strip().str.zfill(7)
    )

    cadastro["fl_municipio_fase_ii"] = cadastro["codigo_municipio_ibge"].isin(fase_ii_codes)
    cadastro["fl_excluir_exposicao_observada"] = ~cadastro["sem_exposicao_observada_2007_2019"]
    cadastro["fl_excluir_universo_incompleto"] = ~cadastro["presente_nos_13_anos_do_universo"]
    cadastro["fl_excluir_fase_ii"] = cadastro["fl_municipio_fase_ii"]
    cadastro["fl_elegivel_controle_candidato"] = (
        cadastro["sem_exposicao_observada_2007_2019"]
        & cadastro["presente_nos_13_anos_do_universo"]
        & ~cadastro["fl_municipio_fase_ii"]
    )
    cadastro["motivos_exclusao"] = _monta_motivos_exclusao(cadastro)

    colunas_finais = [
        *colunas_base, *colunas_extras,
        "sem_exposicao_observada_2007_2019", "presente_nos_13_anos_do_universo",
        "fl_municipio_fase_ii",
        "fl_excluir_exposicao_observada", "fl_excluir_universo_incompleto", "fl_excluir_fase_ii",
        "fl_elegivel_controle_candidato", "motivos_exclusao",
    ]
    cadastro = cadastro[colunas_finais]
    cadastro = cadastro.sort_values("codigo_municipio_ibge", kind="stable").reset_index(drop=True)
    return cadastro


# ---------------------------------------------------------------------------
# 4. Validações do cadastro de elegibilidade (validações 7-13, 16)
# ---------------------------------------------------------------------------


def validate_cadastro_elegibilidade(
    cadastro: pd.DataFrame, resumo: pd.DataFrame, fase_ii_codes: set[str]
) -> None:
    contexto = "cadastro de elegibilidade"
    codigos = cadastro["codigo_municipio_ibge"]

    _rejeitar_codigos_duplicados(codigos, contexto)

    if set(codigos) != set(resumo["codigo_municipio_ibge"].astype(str).str.strip().str.zfill(7)):
        raise ValueError(f"{contexto}: conjunto de municípios diverge do resumo nacional de exposição.")

    marcados = set(cadastro.loc[cadastro["fl_municipio_fase_ii"], "codigo_municipio_ibge"])
    if marcados != set(fase_ii_codes):
        raise ValueError(
            f"{contexto}: marcação fl_municipio_fase_ii diverge do conjunto oficial da Fase II. "
            f"Ausentes: {sorted(set(fase_ii_codes) - marcados)[:5]}; "
            f"Excedentes: {sorted(marcados - set(fase_ii_codes))[:5]}."
        )

    esperado_excl_exp = ~cadastro["sem_exposicao_observada_2007_2019"]
    if not (cadastro["fl_excluir_exposicao_observada"] == esperado_excl_exp).all():
        raise ValueError(f"{contexto}: fl_excluir_exposicao_observada não é o inverso lógico esperado.")

    esperado_excl_univ = ~cadastro["presente_nos_13_anos_do_universo"]
    if not (cadastro["fl_excluir_universo_incompleto"] == esperado_excl_univ).all():
        raise ValueError(f"{contexto}: fl_excluir_universo_incompleto não é o inverso lógico esperado.")

    if not (cadastro["fl_excluir_fase_ii"] == cadastro["fl_municipio_fase_ii"]).all():
        raise ValueError(f"{contexto}: fl_excluir_fase_ii diverge de fl_municipio_fase_ii.")

    esperado_elegivel = (
        cadastro["sem_exposicao_observada_2007_2019"]
        & cadastro["presente_nos_13_anos_do_universo"]
        & ~cadastro["fl_municipio_fase_ii"]
    )
    divergentes = cadastro.loc[cadastro["fl_elegivel_controle_candidato"] != esperado_elegivel]
    if not divergentes.empty:
        raise ValueError(
            f"{contexto}: fl_elegivel_controle_candidato diverge da regra lógica em "
            f"{len(divergentes)} caso(s). Exemplos: {divergentes['codigo_municipio_ibge'].head(5).tolist()}"
        )

    elegiveis = cadastro.loc[cadastro["fl_elegivel_controle_candidato"]]
    fase_ii_elegivel = elegiveis.loc[elegiveis["fl_municipio_fase_ii"]]
    if not fase_ii_elegivel.empty:
        raise ValueError(f"{contexto}: município(s) da Fase II marcado(s) como elegível(is).")
    exposto_elegivel = elegiveis.loc[~elegiveis["sem_exposicao_observada_2007_2019"]]
    if not exposto_elegivel.empty:
        raise ValueError(f"{contexto}: município(s) com exposição observada marcado(s) como elegível(is).")
    incompleto_elegivel = elegiveis.loc[~elegiveis["presente_nos_13_anos_do_universo"]]
    if not incompleto_elegivel.empty:
        raise ValueError(f"{contexto}: município(s) com universo incompleto marcado(s) como elegível(is).")

    for row in cadastro.itertuples():
        motivos_declarados = {m for m in row.motivos_exclusao.split(";") if m}
        motivos_esperados = {
            rotulo for coluna, rotulo in MOTIVOS_EXCLUSAO if getattr(row, coluna)
        }
        if motivos_declarados != motivos_esperados:
            raise ValueError(
                f"{contexto}: motivos_exclusao inconsistente para {row.codigo_municipio_ibge}: "
                f"esperado {sorted(motivos_esperados)}, obtido {sorted(motivos_declarados)}."
            )
        if row.fl_elegivel_controle_candidato and row.motivos_exclusao != "":
            raise ValueError(
                f"{contexto}: {row.codigo_municipio_ibge} é elegível mas motivos_exclusao não está vazio."
            )

    for flag in [
        "fl_municipio_fase_ii", "fl_excluir_exposicao_observada", "fl_excluir_universo_incompleto",
        "fl_excluir_fase_ii", "fl_elegivel_controle_candidato",
    ]:
        if cadastro[flag].dtype != bool:
            raise ValueError(f"{contexto}: {flag} deve ser bool; dtype observado {cadastro[flag].dtype}.")


# ---------------------------------------------------------------------------
# 5. Pool filtrado
# ---------------------------------------------------------------------------


def build_pool_filtrado(cadastro: pd.DataFrame) -> pd.DataFrame:
    """Seleção exata dos elegíveis do cadastro completo — sem transformação
    adicional."""
    return cadastro.loc[cadastro["fl_elegivel_controle_candidato"]].reset_index(drop=True)


def validate_pool_filtrado(pool: pd.DataFrame, cadastro: pd.DataFrame) -> None:
    contexto = "pool candidato a controles"

    if pool["codigo_municipio_ibge"].duplicated().any():
        raise ValueError(f"{contexto}: códigos municipais duplicados no pool filtrado.")

    if set(pool.columns) != set(cadastro.columns):
        raise ValueError(f"{contexto}: colunas do pool divergem do cadastro completo.")

    esperado = cadastro.loc[cadastro["fl_elegivel_controle_candidato"]]
    colunas = cadastro.columns.tolist()
    pool_ordenado = pool.sort_values("codigo_municipio_ibge")[colunas].reset_index(drop=True)
    esperado_ordenado = esperado.sort_values("codigo_municipio_ibge")[colunas].reset_index(drop=True)
    if not pool_ordenado.equals(esperado_ordenado):
        raise ValueError(
            f"{contexto}: conteúdo diverge do subconjunto elegível do cadastro completo "
            f"(não é uma seleção exata)."
        )

    if pool["fl_municipio_fase_ii"].any():
        raise ValueError(f"{contexto}: município(s) da Fase II presente(s) no pool filtrado.")
    if (~pool["sem_exposicao_observada_2007_2019"]).any():
        raise ValueError(f"{contexto}: município(s) com exposição observada presente(s) no pool filtrado.")
    if (~pool["presente_nos_13_anos_do_universo"]).any():
        raise ValueError(f"{contexto}: município(s) com universo incompleto presente(s) no pool filtrado.")


# ---------------------------------------------------------------------------
# 6. Diagnóstico resumido
# ---------------------------------------------------------------------------


def build_resumo_diagnostico(cadastro: pd.DataFrame) -> pd.DataFrame:
    total = len(cadastro)
    excl_exp = cadastro["fl_excluir_exposicao_observada"]
    excl_univ = cadastro["fl_excluir_universo_incompleto"]
    excl_fase_ii = cadastro["fl_excluir_fase_ii"]

    linhas = [
        ("total_municipios", total),
        ("sem_exposicao_observada_2007_2019", int(cadastro["sem_exposicao_observada_2007_2019"].sum())),
        ("com_exposicao_observada_2007_2019", int((~cadastro["sem_exposicao_observada_2007_2019"]).sum())),
        ("presente_nos_13_anos_do_universo", int(cadastro["presente_nos_13_anos_do_universo"].sum())),
        ("universo_incompleto", int((~cadastro["presente_nos_13_anos_do_universo"]).sum())),
        ("pertence_fase_ii", int(cadastro["fl_municipio_fase_ii"].sum())),
        ("nao_pertence_fase_ii", int((~cadastro["fl_municipio_fase_ii"]).sum())),
        ("elegivel_controle_candidato", int(cadastro["fl_elegivel_controle_candidato"].sum())),
        ("inelegivel_controle_candidato", int((~cadastro["fl_elegivel_controle_candidato"]).sum())),
        ("excluido_por_exposicao_observada", int(excl_exp.sum())),
        ("excluido_por_universo_incompleto", int(excl_univ.sum())),
        ("excluido_por_fase_ii", int(excl_fase_ii.sum())),
        ("sobreposicao_exposicao_e_universo_incompleto", int((excl_exp & excl_univ).sum())),
        ("sobreposicao_exposicao_e_fase_ii", int((excl_exp & excl_fase_ii).sum())),
        ("sobreposicao_universo_incompleto_e_fase_ii", int((excl_univ & excl_fase_ii).sum())),
        ("sobreposicao_tres_motivos", int((excl_exp & excl_univ & excl_fase_ii).sum())),
    ]
    return pd.DataFrame(linhas, columns=["metrica", "valor"])


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def main() -> dict[str, Any]:
    print("=" * 70)
    print("POOL CANDIDATO A CONTROLES SEM EXPOSIÇÃO OBSERVADA — 2007-2019")
    print("=" * 70)

    print("\n[1] Lendo insumos (não recalcula exposição nem lista Fase II)...")
    resumo = load_resumo_nacional()
    fase_ii = load_fase_ii_municipios()
    print(f"    resumo nacional: {len(resumo):,} linhas")
    print(f"    lista Fase II: {len(fase_ii):,} linhas")

    print("\n[2] Validando insumos...")
    validate_resumo_nacional(resumo)
    validate_fase_ii_municipios(fase_ii)
    fase_ii_codes = set(fase_ii["codigo_municipio_ibge"].astype(str).str.strip().str.zfill(7))
    universo_codes = set(resumo["codigo_municipio_ibge"].astype(str).str.strip().str.zfill(7))
    validate_fase_ii_subset_universo(fase_ii_codes, universo_codes)
    print("    OK — insumos válidos e Fase II contida no universo nacional.")

    print("\n[3] Construindo cadastro de elegibilidade...")
    cadastro = build_cadastro_elegibilidade(resumo, fase_ii_codes)
    print(f"    Linhas do cadastro: {len(cadastro):,}")

    print("\n[4] Validando cadastro de elegibilidade...")
    validate_cadastro_elegibilidade(cadastro, resumo, fase_ii_codes)
    print("    OK — validações estruturais e lógicas do cadastro passaram.")

    print("\n[5] Construindo pool filtrado...")
    pool = build_pool_filtrado(cadastro)
    print(f"    Linhas do pool filtrado: {len(pool):,}")

    print("\n[6] Validando pool filtrado...")
    validate_pool_filtrado(pool, cadastro)
    print("    OK — pool filtrado é seleção exata dos elegíveis do cadastro.")

    print("\n[7] Construindo diagnóstico resumido...")
    diagnostico = build_resumo_diagnostico(cadastro)

    print("\n[8] Salvando artefatos...")
    OUT_CADASTRO.parent.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIAGNOSTICS.mkdir(parents=True, exist_ok=True)
    cadastro.to_parquet(OUT_CADASTRO, index=False, engine="pyarrow")
    pool.to_parquet(OUT_POOL, index=False, engine="pyarrow")
    diagnostico.to_csv(OUT_DIAGNOSTICO, index=False)
    print(f"    {OUT_CADASTRO}")
    print(f"    {OUT_POOL}")
    print(f"    {OUT_DIAGNOSTICO}")

    valores = dict(zip(diagnostico["metrica"], diagnostico["valor"]))

    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)
    print(f"Total de municípios: {valores['total_municipios']:,}")
    print(f"Sem exposição observada: {valores['sem_exposicao_observada_2007_2019']:,}")
    print(f"Presentes nos 13 anos do universo: {valores['presente_nos_13_anos_do_universo']:,}")
    print(f"Pertencentes à Fase II: {valores['pertence_fase_ii']:,}")
    print(f"Elegíveis (candidatos a controle): {valores['elegivel_controle_candidato']:,}")
    print(f"Excluídos por exposição observada: {valores['excluido_por_exposicao_observada']:,}")
    print(f"Excluídos por universo incompleto: {valores['excluido_por_universo_incompleto']:,}")
    print(f"Excluídos por Fase II: {valores['excluido_por_fase_ii']:,}")
    print(f"Sobreposição exposição+universo incompleto: {valores['sobreposicao_exposicao_e_universo_incompleto']:,}")
    print(f"Sobreposição exposição+Fase II: {valores['sobreposicao_exposicao_e_fase_ii']:,}")
    print(f"Sobreposição universo incompleto+Fase II: {valores['sobreposicao_universo_incompleto_e_fase_ii']:,}")
    print(f"Sobreposição dos três motivos: {valores['sobreposicao_tres_motivos']:,}")
    print("\nATENÇÃO: este pool é apenas um conjunto de candidatos a controle sem")
    print("exposição observada em 2007-2019 — NÃO é o conjunto final de controles")
    print("causais. Matching, suporte comum, spillovers e covariáveis permanecem")
    print("pendentes (ver docs/methodology/POOL_CANDIDATO_CONTROLES.md).")

    return {"cadastro": cadastro, "pool": pool, "diagnostico": diagnostico, **valores}


if __name__ == "__main__":
    main()
