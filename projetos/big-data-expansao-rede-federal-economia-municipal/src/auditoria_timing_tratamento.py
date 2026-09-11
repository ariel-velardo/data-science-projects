"""Audita o timing observável da presença federal EPT na Fase II.

Usa exclusivamente os Parquets processados do cadastro oficial e do painel
municipal do Censo Escolar. A auditoria descreve presença observada; não
atribui tratamento causal, não reconstrói matching e não estima efeitos.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
from pandas.api.types import is_bool_dtype

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FASE_II_PATH = PROJECT_ROOT / "data" / "processed" / "fase_ii_municipios.parquet"
PAINEL_PATH = PROJECT_ROOT / "data" / "processed" / "painel_presenca_federal_ept_fase_ii_2007_2019.parquet"
OUTPUT_CSV = PROJECT_ROOT / "outputs" / "diagnostics" / "auditoria_timing_tratamento.csv"

ANO_INICIAL = 2007
ANO_FINAL = 2019
ANOS_ESPERADOS = list(range(ANO_INICIAL, ANO_FINAL + 1))
PRESENCE_DEFINITIONS = {
    "presenca_federal": "fl_presenca_federal",
    "presenca_federal_ept": "fl_presenca_federal_ept",
    "presenca_federal_ept_ativa": "fl_presenca_federal_ept_ativa",
}


def read_processed_parquet(path: Path) -> pd.DataFrame:
    """Lê um Parquet processado localmente via DuckDB, em memória."""
    if not path.exists():
        raise FileNotFoundError(f"Parquet processado não encontrado: {path}")
    connection = duckdb.connect(database=":memory:")
    try:
        return connection.execute("SELECT * FROM read_parquet(?)", [str(path)]).fetchdf()
    finally:
        connection.close()


def require_columns(df: pd.DataFrame, columns: list[str], source: str) -> None:
    missing = sorted(set(columns) - set(df.columns))
    if missing:
        raise ValueError(f"{source}: colunas obrigatórias ausentes: {missing}")


def validate_input_data(fase_ii: pd.DataFrame, painel: pd.DataFrame) -> None:
    """Valida o contrato estrutural das duas fontes processadas."""
    require_columns(fase_ii, ["codigo_municipio_ibge", "municipio", "uf"], "Cadastro Fase II")
    require_columns(
        painel,
        ["CO_MUNICIPIO", "NU_ANO_CENSO", *PRESENCE_DEFINITIONS.values()],
        "Painel de presença",
    )
    codes = fase_ii["codigo_municipio_ibge"].astype("string").str.zfill(7)
    if codes.isna().any() or codes.nunique() != 147 or codes.duplicated().any():
        raise ValueError("Cadastro Fase II deve conter exatamente 147 códigos IBGE distintos e não nulos.")

    panel_codes = painel["CO_MUNICIPIO"].astype("string").str.zfill(7)
    years = pd.to_numeric(painel["NU_ANO_CENSO"], errors="coerce")
    if panel_codes.isna().any() or years.isna().any():
        raise ValueError("Painel possui código municipal ou ano nulo/inválido.")
    if set(years.astype(int).unique()) != set(ANOS_ESPERADOS):
        raise ValueError(f"Painel deve cobrir exatamente 2007–2019; encontrados {sorted(years.astype(int).unique())}.")
    chave_municipio_ano = pd.DataFrame({"code": panel_codes, "year": years.astype(int)})
    if chave_municipio_ano.duplicated().any():
        raise ValueError("Painel possui mais de uma observação por município-ano.")
    if set(panel_codes) != set(codes):
        raise ValueError("Conjunto de municípios do painel diverge do cadastro oficial Fase II.")

    if len(painel) != 1911:
        raise ValueError(
            f"Painel deve conter exatamente 1.911 linhas (147 municípios × 13 anos); "
            f"encontradas {len(painel)}."
        )

    anos_por_municipio = chave_municipio_ano.groupby("code")["year"]
    contagem_por_municipio = anos_por_municipio.count()
    fora_de_13 = contagem_por_municipio[contagem_por_municipio != 13]
    if not fora_de_13.empty:
        raise ValueError(
            "Painel deve conter exatamente 13 observações para cada um dos 147 "
            f"municípios; municípios com contagem diferente de 13: {fora_de_13.index.tolist()}."
        )

    anos_esperados_set = set(ANOS_ESPERADOS)
    cobertura_incorreta = anos_por_municipio.apply(lambda s: set(s) != anos_esperados_set)
    municipios_incompletos = cobertura_incorreta[cobertura_incorreta].index.tolist()
    if municipios_incompletos:
        raise ValueError(
            "Painel deve conter exatamente os anos de 2007 a 2019 para cada "
            f"município; municípios com cobertura de anos incorreta: {municipios_incompletos}."
        )

    for flag in PRESENCE_DEFINITIONS.values():
        if not is_bool_dtype(painel[flag]) or painel[flag].isna().any():
            raise ValueError(f"{flag} deve ser booleano e não nulo no painel.")
        if not set(painel[flag].unique()).issubset({True, False}):
            raise ValueError(f"{flag} possui valores fora de True/False.")


def summarize_presence_trajectory(years: list[int], values: list[bool]) -> dict[str, int | bool | None]:
    """Resume uma trajetória anual sem corrigir ou imputar presenças."""
    if years != ANOS_ESPERADOS or len(values) != len(ANOS_ESPERADOS):
        raise ValueError("A trajetória deve cobrir cada ano de 2007 a 2019, em ordem.")
    if any(value not in (True, False) for value in values):
        raise ValueError("A trajetória contém valor não booleano.")

    true_positions = [index for index, value in enumerate(values) if value]
    if not true_positions:
        return {
            "n_anos_presenca": 0, "primeiro_ano": None, "ultimo_ano": None,
            "censura_esquerda": False, "tem_interrupcao_interna": False,
            "n_interrupcoes_internas": 0, "trajetoria_monotonica": False,
        }

    first, last = true_positions[0], true_positions[-1]
    internal = values[first:last + 1]
    interruptions = sum(
        not value and (index == 0 or internal[index - 1])
        for index, value in enumerate(internal)
    )
    return {
        "n_anos_presenca": len(true_positions),
        "primeiro_ano": years[first],
        "ultimo_ano": years[last],
        "censura_esquerda": first == 0,
        "tem_interrupcao_interna": interruptions > 0,
        "n_interrupcoes_internas": interruptions,
        "trajetoria_monotonica": all(values[first:]),
    }


def first_persistent_year(years: list[int], values: list[bool]) -> int | None:
    """Retorna o início da sequência final contínua de presença até 2019."""
    if years != ANOS_ESPERADOS or len(values) != len(ANOS_ESPERADOS):
        raise ValueError("A trajetória deve cobrir cada ano de 2007 a 2019, em ordem.")
    if not values[-1]:
        return None
    position = len(values) - 1
    while position > 0 and values[position - 1]:
        position -= 1
    return years[position]


def add_definition_diagnostics(
    audit: pd.DataFrame, panel: pd.DataFrame, definition: str, flag: str
) -> pd.DataFrame:
    rows = []
    for code, group in panel[["CO_MUNICIPIO", "NU_ANO_CENSO", flag]].groupby("CO_MUNICIPIO", sort=False):
        group = group.sort_values("NU_ANO_CENSO")
        rows.append({
            "codigo_municipio_ibge": code,
            **summarize_presence_trajectory(
                group["NU_ANO_CENSO"].tolist(), group[flag].astype(bool).tolist()
            ),
        })
    diagnostics = pd.DataFrame(rows).rename(columns={
        "n_anos_presenca": f"n_anos_{definition}",
        "primeiro_ano": f"primeiro_ano_{definition}",
        "ultimo_ano": f"ultimo_ano_{definition}",
        "censura_esquerda": f"censura_esquerda_{definition}",
        "tem_interrupcao_interna": f"tem_interrupcao_interna_{definition}",
        "n_interrupcoes_internas": f"n_interrupcoes_internas_{definition}",
        "trajetoria_monotonica": f"trajetoria_monotonica_{definition}",
    })
    audit = audit.merge(diagnostics, on="codigo_municipio_ibge", how="left", validate="one_to_one")
    first = audit[f"primeiro_ano_{definition}"]
    audit[f"n_pre_{definition}"] = first - ANO_INICIAL
    audit[f"n_pos_{definition}"] = ANO_FINAL - first
    return audit


def build_audit_table(fase_ii: pd.DataFrame, painel: pd.DataFrame) -> pd.DataFrame:
    """Cria a tabela final, uma linha por código IBGE oficial da Fase II."""
    validate_input_data(fase_ii, painel)
    audit = fase_ii[["codigo_municipio_ibge", "municipio", "uf"]].copy()
    audit["codigo_municipio_ibge"] = audit["codigo_municipio_ibge"].astype("string").str.zfill(7)
    audit["fase_ii"] = True
    panel = painel.copy()
    panel["CO_MUNICIPIO"] = panel["CO_MUNICIPIO"].astype("string").str.zfill(7)
    panel["NU_ANO_CENSO"] = pd.to_numeric(panel["NU_ANO_CENSO"], errors="raise").astype(int)

    for definition, flag in PRESENCE_DEFINITIONS.items():
        audit = add_definition_diagnostics(audit, panel, definition, flag)

    persistent_rows = []
    active_flag = PRESENCE_DEFINITIONS["presenca_federal_ept_ativa"]
    for code, group in panel[["CO_MUNICIPIO", "NU_ANO_CENSO", active_flag]].groupby("CO_MUNICIPIO", sort=False):
        group = group.sort_values("NU_ANO_CENSO")
        persistent_rows.append({
            "codigo_municipio_ibge": code,
            "primeiro_ano_persistente_presenca_federal_ept_ativa": first_persistent_year(
                group["NU_ANO_CENSO"].tolist(), group[active_flag].astype(bool).tolist()
            ),
        })
    audit = audit.merge(pd.DataFrame(persistent_rows), on="codigo_municipio_ibge", how="left", validate="one_to_one")

    active = "presenca_federal_ept_ativa"
    first = audit[f"primeiro_ano_{active}"]
    audit["elegivel_ept_federal_ativa_pre2_pos3"] = first.notna() & (audit[f"n_pre_{active}"] >= 2) & (audit[f"n_pos_{active}"] >= 3)
    audit["elegivel_ept_federal_ativa_pre3_pos3"] = first.notna() & (audit[f"n_pre_{active}"] >= 3) & (audit[f"n_pos_{active}"] >= 3)
    audit["coorte_ept_federal_ativa_2010_2013"] = first.between(2010, 2013)
    audit["coorte_ept_federal_ativa_2010_2011"] = first.between(2010, 2011)
    audit["trajetoria_intermitente_ept_federal_ativa"] = audit[f"tem_interrupcao_interna_{active}"]

    audit = audit.sort_values(["uf", "municipio", "codigo_municipio_ibge"], kind="stable").reset_index(drop=True)
    validate_audit_table(audit)
    return audit


def validate_audit_table(audit: pd.DataFrame) -> None:
    """Falha antes da escrita se a tabela final violar o contrato da auditoria."""
    if len(audit) != 147 or audit["codigo_municipio_ibge"].isna().any() or audit["codigo_municipio_ibge"].duplicated().any():
        raise ValueError("Tabela final deve ter 147 códigos IBGE distintos e não nulos.")
    for definition in PRESENCE_DEFINITIONS:
        first = audit[f"primeiro_ano_{definition}"]
        last = audit[f"ultimo_ano_{definition}"]
        n_pre = audit[f"n_pre_{definition}"]
        n_pos = audit[f"n_pos_{definition}"]
        censored = audit[f"censura_esquerda_{definition}"]
        interrupted = audit[f"tem_interrupcao_interna_{definition}"]
        n_interruptions = audit[f"n_interrupcoes_internas_{definition}"]
        monotonic = audit[f"trajetoria_monotonica_{definition}"]
        if not first.dropna().between(ANO_INICIAL, ANO_FINAL).all() or not last.dropna().between(ANO_INICIAL, ANO_FINAL).all():
            raise ValueError(f"{definition}: ano fora da janela 2007–2019.")
        if not (first.isna() == last.isna()).all() or not (last.dropna() >= first.dropna()).all():
            raise ValueError(f"{definition}: primeiro e último ano incoerentes.")
        if not (n_pre[first.notna()] == first[first.notna()] - ANO_INICIAL).all() or not (n_pos[first.notna()] == ANO_FINAL - first[first.notna()]).all():
            raise ValueError(f"{definition}: n_pre ou n_pos incoerente.")
        if not (censored == first.eq(ANO_INICIAL)).all() or not (interrupted == n_interruptions.gt(0)).all():
            raise ValueError(f"{definition}: diagnósticos de trajetória incoerentes.")
        if (monotonic & ((last != ANO_FINAL) | interrupted)).any():
            raise ValueError(f"{definition}: monotonicidade incoerente com último ano ou interrupção.")

    first = audit["primeiro_ano_presenca_federal_ept_ativa"]
    expected_2_3 = first.notna() & (first - ANO_INICIAL >= 2) & (ANO_FINAL - first >= 3)
    expected_3_3 = first.notna() & (first - ANO_INICIAL >= 3) & (ANO_FINAL - first >= 3)
    if not (audit["elegivel_ept_federal_ativa_pre2_pos3"] == expected_2_3).all() or not (audit["elegivel_ept_federal_ativa_pre3_pos3"] == expected_3_3).all():
        raise ValueError("Elegibilidade 2/3 ou 3/3 inconsistente com n_pre e n_pos.")


def format_distribution(series: pd.Series) -> str:
    counts = series.dropna().astype(int).value_counts().sort_index()
    return ", ".join(f"{year}: {count}" for year, count in counts.items()) or "sem presença"


def print_summary(audit: pd.DataFrame) -> None:
    print("AUDITORIA DE TIMING DO TRATAMENTO — FASE II")
    print(f"Total oficial de municípios: {len(audit)}")
    for definition in PRESENCE_DEFINITIONS:
        print(f"Primeiro ano — {definition}: {format_distribution(audit[f'primeiro_ano_{definition}'])}")
        print(f"  Censura à esquerda: {int(audit[f'censura_esquerda_{definition}'].sum())}; monotônica: {int(audit[f'trajetoria_monotonica_{definition}'].sum())}; intermitente: {int(audit[f'tem_interrupcao_interna_{definition}'].sum())}")
    print(f"Elegível EPT federal ativa (2 pré / 3 pós): {int(audit['elegivel_ept_federal_ativa_pre2_pos3'].sum())}")
    print(f"Elegível EPT federal ativa (3 pré / 3 pós): {int(audit['elegivel_ept_federal_ativa_pre3_pos3'].sum())}")
    print(f"Coortes EPT federal ativa 2010–2013: {int(audit['coorte_ept_federal_ativa_2010_2013'].sum())}")
    print(f"Coortes EPT federal ativa 2010–2011: {int(audit['coorte_ept_federal_ativa_2010_2011'].sum())}")
    print("Municípios intermitentes em EPT federal ativa:")
    intermittent = audit[audit["trajetoria_intermitente_ept_federal_ativa"]]
    for row in intermittent.itertuples(index=False):
        print(f"  {row.municipio}/{row.uf} ({row.codigo_municipio_ibge})")
    if intermittent.empty:
        print("  nenhum")


def main() -> None:
    audit = build_audit_table(read_processed_parquet(FASE_II_PATH), read_processed_parquet(PAINEL_PATH))
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print_summary(audit)
    print(f"CSV gravado em: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
