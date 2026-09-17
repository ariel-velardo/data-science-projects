"""
constroi_painel_analitico_cempre.py
====================================
D10 — Constrói o painel analítico CEMPRE município-ano (2007-2019) a
partir da long técnica já aprovada (D8/D9, ver `ESTADO_ATUAL.md`).

A long técnica (`data/interim/cempre_long_2007_2019.parquet`) é
IMUTÁVEL e preserva tudo que a API retornou, inclusive linhas de
município-ano que ainda não existia territorialmente naquele ano. Este
script NUNCA lê nem escreve rede, NUNCA altera a long técnica, o
manifesto ou os caches — apenas deriva um painel wide a partir do que
já está persistido.

Regra territorial analítica (única regra de inclusão/exclusão deste
script): o painel analítico principal contém somente observações
`(codigo_municipio_ibge, ano)` com `status_territorial ==
"existia_no_ano"`. A exclusão é determinada EXCLUSIVAMENTE pelo
calendário territorial (contrato já existente na long técnica) — nunca
pelo valor retornado pela API. Por isso, dois município-ano com valor
`observado` (Balneário Rincão/SC e Paraíso das Águas/MS, ambos 2012)
são excluídos do painel analítico principal mesmo tendo valor
numérico, porque o calendário territorial (DTB) diz que esses
municípios ainda não existiam formalmente naquele ano — o mesmo
tratamento que já era dado a município-ano com valor `indisponivel`
(ex.: Pescaria Brava/2007). Esses casos ficam preservados, com
rastreabilidade completa, no diagnóstico de exclusão territorial
(`outputs/diagnostics/cempre_municipio_ano_excluidos_territorio.csv`)
— não são apagados nem usados como input causal.

Granularidade do painel analítico: uma linha por
`(codigo_municipio_ibge, ano)`, chave única. As 7 variáveis contratadas
(662, 706, 707, 708, 1606, 5944, 10143) viram colunas numéricas
(`valor_numerico`, sem reparsear `valor_bruto`) mais uma coluna de
status espelhada por variável (`status_<coluna>`), para nunca perder a
distinção entre NA-por-sigilo, NA-por-indisponibilidade e ausência de
outro tipo. A variável 1606 é incluída, mas permanece OPCIONAL no
contrato de aquisição — sua ausência/status especial nunca determina
exclusão de município-ano.

`status_valor_api == "desconhecido"` é um bloqueador: `build_painel_analitico`
levanta `ValueError` se encontrar qualquer linha desconhecida no
subconjunto `existia_no_ano` (não deveria existir — D8/D9 já
confirmaram `desconhecido = 0` na long técnica inteira).

Nomenclatura das colunas reaproveita a convenção já existente em
`constroi_painel_cempre._VARIAVEL_PARA_COLUNA` (usada por
`validate_cross_measures`), estendida com a variável 1606 no mesmo
estilo.

Outcome CEMPRE principal contratado (apenas registrado, nunca filtrado
ou usado como critério de exclusão nesta etapa):
`constroi_painel_cempre.VARIAVEL_OUTCOME_PRIMARIO` (708 — pessoal
ocupado assalariado).

Este script NÃO integra o painel ao cadastro causal nacional e NÃO
inicia nenhuma estimação/seleção causal — isso pertence a uma etapa
posterior, após aprovação isolada deste painel analítico.

Saídas:
  data/processed/cempre_painel_analitico_2007_2019.parquet
  outputs/diagnostics/cempre_municipio_ano_excluidos_territorio.csv

Proveniência: o painel é derivado inteiramente de
`data/interim/cempre_long_2007_2019.parquet` (e seu manifesto,
`data/raw/ibge/cempre/source_manifest.json`, já é a fonte de verdade
da coleta) — não é criado nenhum sistema de manifesto novo aqui.

Uso:
  python src/constroi_painel_analitico_cempre.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import constroi_painel_cempre as cempre  # noqa: E402

# ---------------------------------------------------------------------------
# Configuração global
# ---------------------------------------------------------------------------

DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS_DIAGNOSTICS = ROOT / "outputs" / "diagnostics"

LONG_TECNICA_PATH = DATA_INTERIM / "cempre_long_2007_2019.parquet"
FASE_II_MUNICIPIOS_PATH = DATA_PROCESSED / "fase_ii_municipios.parquet"
CADASTRO_CAUSAL_FASE_II_PATH = ROOT / "outputs" / "diagnostics" / "cadastro_causal_tratamento_fase_ii.csv"

OUT_PAINEL_ANALITICO = DATA_PROCESSED / "cempre_painel_analitico_2007_2019.parquet"
OUT_DIAGNOSTICO_EXCLUSAO = OUTPUTS_DIAGNOSTICS / "cempre_municipio_ano_excluidos_territorio.csv"

STATUS_EXISTIA = "existia_no_ano"

# codigo_variavel_sidra -> nome de coluna na wide analítica. Reaproveita a
# convenção já existente em `constroi_painel_cempre._VARIAVEL_PARA_COLUNA`
# (usada por `validate_cross_measures`), estendida com 1606 no mesmo estilo
# (variável opcional/diagnóstica, nunca antes mapeada porque a validação
# cruzada não a usa).
MAPA_VARIAVEL_COLUNA: dict[int, str] = {
    **cempre._VARIAVEL_PARA_COLUNA,
    1606: "salario_medio_salarios_minimos_nominal",
}
assert set(MAPA_VARIAVEL_COLUNA) == cempre.VARIAVEIS_ESPERADAS

COLUNAS_TERRITORIAIS_PRESERVADAS = ["municipio_fonte"]


# ---------------------------------------------------------------------------
# 1. Carga e auditoria da população antes da transformação
# ---------------------------------------------------------------------------


def carrega_long_tecnica(caminho: Path | None = None) -> pd.DataFrame:
    """Carrega a long técnica já persistida. Somente leitura — nunca
    chama rede, nunca reconstrói nada."""
    return cempre.load_long_parquet(caminho or LONG_TECNICA_PATH)


def auditar_populacao(df_long: pd.DataFrame) -> dict[str, Any]:
    """Audita a população município-ano da long técnica ANTES de
    qualquer transformação (seção 1 do D10): confirma as contagens já
    aprovadas em D9 e separa o universo único `(codigo_municipio_ibge,
    ano)` em existente/não-existente segundo `status_territorial`. Não
    decide nada com base no valor observado pela API — só lê a coluna
    `status_territorial`, já derivada do calendário territorial pelo
    pipeline técnico (D2).
    """
    chave_var = ["codigo_municipio_ibge", "ano", "codigo_variavel_sidra"]
    if df_long.duplicated(subset=chave_var).any():
        raise ValueError("long técnica com duplicatas na chave (codigo_municipio_ibge, ano, codigo_variavel_sidra)")

    municipio_ano = df_long[["codigo_municipio_ibge", "ano", "status_territorial"]].drop_duplicates(
        subset=["codigo_municipio_ibge", "ano"]
    )
    existentes = municipio_ano[municipio_ano["status_territorial"] == STATUS_EXISTIA]
    nao_existentes = municipio_ano[municipio_ano["status_territorial"] != STATUS_EXISTIA].sort_values(
        ["codigo_municipio_ibge", "ano"]
    ).reset_index(drop=True)

    return {
        "n_linhas": len(df_long),
        "n_municipios": int(df_long["codigo_municipio_ibge"].nunique()),
        "n_anos": int(df_long["ano"].nunique()),
        "n_variaveis": int(df_long["codigo_variavel_sidra"].nunique()),
        "n_municipio_ano_existente": len(existentes),
        "n_municipio_ano_nao_existente": len(nao_existentes),
        "municipio_ano_nao_existente": nao_existentes,
    }


# ---------------------------------------------------------------------------
# 2. Diagnóstico de exclusão territorial (rastreabilidade, NÃO é input causal)
# ---------------------------------------------------------------------------


def build_diagnostico_exclusao_territorial(df_long: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (município, ano, variável) excluída do painel
    analítico por `status_territorial != "existia_no_ano"` — 32
    combinações município-ano × 7 variáveis esperadas = 224 linhas na
    long técnica atual. Preserva `valor_bruto`/`valor_numerico`,
    `status_valor_api` e `incompatibilidade_territorial` originais,
    sem alterar nada. Uso exclusivamente diagnóstico/rastreabilidade —
    NÃO é usado como input causal.
    """
    excluidos = df_long[df_long["status_territorial"] != STATUS_EXISTIA].copy()
    colunas = [
        "codigo_municipio_ibge", "ano", "municipio_fonte",
        "codigo_variavel_sidra", "nome_variavel",
        "valor_bruto", "valor_numerico", "status_valor_api",
        "status_territorial", "incompatibilidade_territorial",
    ]
    return excluidos[colunas].sort_values(
        ["codigo_municipio_ibge", "ano", "codigo_variavel_sidra"]
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3-8. Construção do painel analítico (long -> wide, município-ano)
# ---------------------------------------------------------------------------


def build_painel_analitico(df_long: pd.DataFrame) -> pd.DataFrame:
    """Constrói o painel analítico CEMPRE município-ano a partir da
    long técnica: filtra somente `status_territorial == "existia_no_ano"`
    (regra territorial analítica única), pivota as 7 variáveis
    contratadas para colunas numéricas (`valor_numerico`, sem
    reparsear `valor_bruto`) mais uma coluna de status espelhada por
    variável. Uma linha por `(codigo_municipio_ibge, ano)`.

    Bloqueia (`ValueError`) se encontrar `status_valor_api ==
    "desconhecido"` ou variável contratada ausente no subconjunto
    incluído — nunca imputa, nunca ignora silenciosamente.
    """
    incluidos = df_long[df_long["status_territorial"] == STATUS_EXISTIA].copy()

    n_desconhecido = int((incluidos["status_valor_api"] == "desconhecido").sum())
    if n_desconhecido:
        raise ValueError(
            f"painel analítico CEMPRE bloqueado: {n_desconhecido} linha(s) com "
            "status_valor_api='desconhecido' entre município-ano existentes"
        )

    colunas_valor = [MAPA_VARIAVEL_COLUNA[v] for v in sorted(MAPA_VARIAVEL_COLUNA)]
    colunas_status = [f"status_{c}" for c in colunas_valor]
    ordem = (
        ["codigo_municipio_ibge", "ano", "uf_codigo", "municipio_fonte", "status_territorial"]
        + colunas_valor
        + colunas_status
    )

    if incluidos.empty:
        # Nenhum município-ano existente nesta long (ex.: subconjunto sintético
        # só com casos pré-existência) — painel vazio, mas com o schema correto.
        return pd.DataFrame(columns=ordem)

    variaveis_presentes = set(incluidos["codigo_variavel_sidra"].unique())
    faltantes = set(MAPA_VARIAVEL_COLUNA) - variaveis_presentes
    if faltantes:
        raise ValueError(
            f"painel analítico CEMPRE bloqueado: variável(is) contratada(s) ausente(s) "
            f"no subconjunto existente: {sorted(faltantes)}"
        )

    incluidos["coluna_valor"] = incluidos["codigo_variavel_sidra"].map(MAPA_VARIAVEL_COLUNA)
    incluidos["coluna_status"] = "status_" + incluidos["coluna_valor"]

    chave = ["codigo_municipio_ibge", "ano"]

    # dropna=False: uma variável inteiramente NA (ex.: sigilo em todas as
    # linhas de um lote sintético pequeno) não pode desaparecer da wide —
    # isso apagaria silenciosamente a coluna em vez de preservar o NA.
    valor_wide = incluidos.pivot_table(
        index=chave, columns="coluna_valor", values="valor_numerico", aggfunc="first", dropna=False,
    )
    valor_wide.columns.name = None

    status_wide = incluidos.pivot_table(
        index=chave, columns="coluna_status", values="status_valor_api", aggfunc="first", dropna=False,
    )
    status_wide.columns.name = None

    territorial = incluidos.groupby(chave, as_index=True).agg(
        municipio_fonte=("municipio_fonte", "first"),
        status_territorial=("status_territorial", "first"),
    )

    painel = territorial.join(valor_wide).join(status_wide).reset_index()

    painel["uf_codigo"] = painel["codigo_municipio_ibge"].str[:2]

    painel = painel[ordem].sort_values(["codigo_municipio_ibge", "ano"]).reset_index(drop=True)

    if painel.duplicated(subset=["codigo_municipio_ibge", "ano"]).any():
        raise ValueError("painel analítico CEMPRE com chave (codigo_municipio_ibge, ano) duplicada")

    return painel


# ---------------------------------------------------------------------------
# 10. Diagnóstico de missing analítico
# ---------------------------------------------------------------------------


def relatorio_missing_por_variavel(painel: pd.DataFrame) -> pd.DataFrame:
    """Para cada variável analítica, reporta n_total/n_na/pct_na e o
    missing separado por status de origem (sigilo/indisponível/zero) —
    nunca soma tudo num único "missing" genérico."""
    linhas = []
    for coluna in [MAPA_VARIAVEL_COLUNA[v] for v in sorted(MAPA_VARIAVEL_COLUNA)]:
        status_col = f"status_{coluna}"
        n_total = len(painel)
        n_na = int(painel[coluna].isna().sum())
        contagem_status = painel[status_col].value_counts()
        linhas.append({
            "coluna": coluna,
            "n_total": n_total,
            "n_na": n_na,
            "pct_na": round(100 * n_na / n_total, 4) if n_total else 0.0,
            "n_sigilo": int(contagem_status.get("sigilo", 0)),
            "n_indisponivel": int(contagem_status.get("indisponivel", 0)),
            "n_zero_real": int(contagem_status.get("zero_real", 0)),
            "n_zero_arredondado": int(contagem_status.get("zero_arredondado", 0)),
        })
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# 11. Validações estruturais
# ---------------------------------------------------------------------------


def validate_painel_analitico(
    painel: pd.DataFrame,
    df_long: pd.DataFrame,
    fase_ii_codigos: set[str] | None = None,
    candidatos_codigos: set[str] | None = None,
) -> dict[str, Any]:
    """Validações estruturais do painel analítico (seção 11 do D10).
    Levanta `ValueError` para qualquer violação de correção (A-H);
    reconciliações de cobertura (I, J) retornam contagens para o
    chamador decidir/reportar, mas também levantam se a cobertura cair
    abaixo do esperado (município Fase II/candidato ausente num ano em
    que deveria existir)."""
    # A. chave única
    if painel.duplicated(subset=["codigo_municipio_ibge", "ano"]).any():
        raise ValueError("A: chave (codigo_municipio_ibge, ano) não é única no painel analítico")

    # B. zero município-ano que não existia
    nao_existentes = set(
        map(tuple, df_long[df_long["status_territorial"] != STATUS_EXISTIA][["codigo_municipio_ibge", "ano"]]
            .drop_duplicates().itertuples(index=False, name=None))
    )
    presentes = set(map(tuple, painel[["codigo_municipio_ibge", "ano"]].itertuples(index=False, name=None)))
    intersecao = nao_existentes & presentes
    if intersecao:
        raise ValueError(f"B: {len(intersecao)} município-ano não-existente presente no painel analítico: {sorted(intersecao)[:5]}")

    # C. zero status desconhecido
    colunas_status = [f"status_{c}" for c in MAPA_VARIAVEL_COLUNA.values()]
    for col in colunas_status:
        if (painel[col] == "desconhecido").any():
            raise ValueError(f"C: coluna {col} contém status_valor_api='desconhecido'")

    # D. 7 variáveis numéricas presentes
    colunas_valor = list(MAPA_VARIAVEL_COLUNA.values())
    faltantes_valor = [c for c in colunas_valor if c not in painel.columns]
    if faltantes_valor:
        raise ValueError(f"D: coluna(s) de variável numérica ausente(s): {faltantes_valor}")

    # E. 7 status correspondentes presentes
    faltantes_status = [c for c in colunas_status if c not in painel.columns]
    if faltantes_status:
        raise ValueError(f"E: coluna(s) de status ausente(s): {faltantes_status}")

    # F. anos dentro da janela 2007-2019
    anos = sorted(painel["ano"].unique().tolist())
    fora_da_janela = [a for a in anos if a not in range(2007, 2020)]
    if fora_da_janela:
        raise ValueError(f"F: ano(s) fora da janela 2007-2019: {fora_da_janela}")

    # G. nenhum valor negativo nas medidas ja proibidas por validate_cross_measures
    for coluna in ["pessoal_ocupado_total", "pessoal_ocupado_assalariado", "pessoal_assalariado_medio",
                    "qt_unidades_locais", "salarios_remuneracoes_mil_reais_nominal", "salario_medio_reais_nominal"]:
        negativos = painel[coluna].dropna()
        if (negativos < 0).any():
            raise ValueError(f"G: valores negativos encontrados em {coluna}")

    # H. 708 <= 707 quando ambos observados
    ambos = painel[["pessoal_ocupado_assalariado", "pessoal_ocupado_total"]].dropna()
    violacoes_h = ambos[ambos["pessoal_ocupado_assalariado"] > ambos["pessoal_ocupado_total"]]
    if len(violacoes_h):
        raise ValueError(f"H: {len(violacoes_h)} linha(s) com pessoal_ocupado_assalariado > pessoal_ocupado_total")

    resultado: dict[str, Any] = {
        "n_linhas": len(painel),
        "n_municipios": int(painel["codigo_municipio_ibge"].nunique()),
        "anos": anos,
    }

    # I. Fase II preservada nos anos em que os municípios existem
    if fase_ii_codigos is not None:
        ausentes_do_long = fase_ii_codigos - set(df_long["codigo_municipio_ibge"].unique())
        if ausentes_do_long:
            raise ValueError(f"I: {len(ausentes_do_long)} município(s) Fase II ausente(s) da long técnica: {sorted(ausentes_do_long)}")
        long_fase_ii_existente = df_long[
            (df_long["codigo_municipio_ibge"].isin(fase_ii_codigos)) & (df_long["status_territorial"] == STATUS_EXISTIA)
        ][["codigo_municipio_ibge", "ano"]].drop_duplicates()
        esperado = set(map(tuple, long_fase_ii_existente.itertuples(index=False, name=None)))
        painel_fase_ii = set(map(tuple, painel[painel["codigo_municipio_ibge"].isin(fase_ii_codigos)]
                                  [["codigo_municipio_ibge", "ano"]].itertuples(index=False, name=None)))
        faltando = esperado - painel_fase_ii
        if faltando:
            raise ValueError(f"I: {len(faltando)} município-ano Fase II existente ausente do painel analítico")
        resultado["fase_ii_municipios_cobertos"] = len({c for c, _ in painel_fase_ii})
        resultado["fase_ii_municipio_ano_cobertos"] = len(painel_fase_ii)

    # J. candidatos principais preservados
    if candidatos_codigos is not None:
        ausentes_cand_do_long = candidatos_codigos - set(df_long["codigo_municipio_ibge"].unique())
        if ausentes_cand_do_long:
            raise ValueError(f"J: {len(ausentes_cand_do_long)} candidato(s) principal(is) ausente(s) da long técnica: {sorted(ausentes_cand_do_long)}")
        long_cand_existente = df_long[
            (df_long["codigo_municipio_ibge"].isin(candidatos_codigos)) & (df_long["status_territorial"] == STATUS_EXISTIA)
        ][["codigo_municipio_ibge", "ano"]].drop_duplicates()
        esperado_cand = set(map(tuple, long_cand_existente.itertuples(index=False, name=None)))
        painel_cand = set(map(tuple, painel[painel["codigo_municipio_ibge"].isin(candidatos_codigos)]
                               [["codigo_municipio_ibge", "ano"]].itertuples(index=False, name=None)))
        faltando_cand = esperado_cand - painel_cand
        if faltando_cand:
            raise ValueError(f"J: {len(faltando_cand)} município-ano candidato-principal existente ausente do painel analítico")
        resultado["candidatos_municipios_cobertos"] = len({c for c, _ in painel_cand})
        resultado["candidatos_municipio_ano_cobertos"] = len(painel_cand)

    return resultado


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> dict[str, Any]:
    print("=" * 70)
    print("D10 — Painel analítico CEMPRE município-ano (2007-2019)")
    print("=" * 70)

    print("\n[1] Carregando long técnica e auditando a população...")
    df_long = carrega_long_tecnica()
    auditoria = auditar_populacao(df_long)
    print(f"    linhas={auditoria['n_linhas']:,} municipios={auditoria['n_municipios']:,} "
          f"anos={auditoria['n_anos']} variaveis={auditoria['n_variaveis']}")
    print(f"    municipio-ano existente: {auditoria['n_municipio_ano_existente']:,}")
    print(f"    municipio-ano NAO existente: {auditoria['n_municipio_ano_nao_existente']:,}")

    print("\n[2] Construindo diagnóstico de exclusão territorial...")
    diagnostico_exclusao = build_diagnostico_exclusao_territorial(df_long)
    print(f"    {len(diagnostico_exclusao):,} linhas (município × ano × variável excluídos)")

    print("\n[3] Construindo o painel analítico (long -> wide)...")
    painel = build_painel_analitico(df_long)
    print(f"    linhas={len(painel):,} municipios={painel['codigo_municipio_ibge'].nunique():,}")

    print("\n[4] Relatório de missing por variável...")
    missing = relatorio_missing_por_variavel(painel)
    print(missing.to_string(index=False))

    print("\n[5] Validações estruturais...")
    fase_ii = pd.read_parquet(FASE_II_MUNICIPIOS_PATH)
    fase_ii_codigos = set(fase_ii["codigo_municipio_ibge"].astype(str))
    cadastro_causal = pd.read_csv(CADASTRO_CAUSAL_FASE_II_PATH, dtype={"codigo_municipio_ibge": str})
    candidatos_codigos = set(cadastro_causal[cadastro_causal["candidato_amostra_principal"] == True]["codigo_municipio_ibge"])

    resultado_validacao = validate_painel_analitico(painel, df_long, fase_ii_codigos, candidatos_codigos)
    print("    OK — validações A-J passaram.")
    print(f"    Fase II: {resultado_validacao.get('fase_ii_municipios_cobertos')} municípios, "
          f"{resultado_validacao.get('fase_ii_municipio_ano_cobertos')} município-ano cobertos")
    print(f"    Candidatos principais: {resultado_validacao.get('candidatos_municipios_cobertos')} municípios, "
          f"{resultado_validacao.get('candidatos_municipio_ano_cobertos')} município-ano cobertos")

    print(f"\n[6] Outcome CEMPRE principal contratado (registro, sem filtrar): "
          f"variável {cempre.VARIAVEL_OUTCOME_PRIMARIO} (pessoal_ocupado_assalariado)")

    print("\n[7] Salvando artefatos...")
    OUT_PAINEL_ANALITICO.parent.mkdir(parents=True, exist_ok=True)
    OUT_DIAGNOSTICO_EXCLUSAO.parent.mkdir(parents=True, exist_ok=True)
    painel.to_parquet(OUT_PAINEL_ANALITICO, index=False, engine="pyarrow")
    diagnostico_exclusao.to_csv(OUT_DIAGNOSTICO_EXCLUSAO, index=False, encoding="utf-8")
    print(f"    {OUT_PAINEL_ANALITICO}")
    print(f"    {OUT_DIAGNOSTICO_EXCLUSAO}")

    return {
        "auditoria": auditoria,
        "n_diagnostico_exclusao": len(diagnostico_exclusao),
        "n_painel": len(painel),
        "missing": missing,
        "validacao": resultado_validacao,
    }


if __name__ == "__main__":
    main()
