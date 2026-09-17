"""
constroi_painel_cempre_cadastro_causal.py
==========================================
D11 — Integra o painel analítico CEMPRE município-ano (D10) aos
cadastros causais/nacionais já aprovados, produzindo um painel
integrado que preserva TODA a população analítica nacional (72.378
município-ano) e adiciona somente METADADOS CAUSAIS já definidos — não
altera o outcome, não seleciona amostra, não estima nada.

Esta rotina NÃO faz matching, NÃO avalia suporte comum, NÃO calcula
ATT/Callaway-Sant'Anna e NÃO declara desenho causal aprovado (ver
`docs/methodology/CONTRATO_CAUSAL.md` e
`docs/methodology/PROTOCOLO_PRE_ANALISE.md`).

Artefatos canônicos reaproveitados (nunca recalculados aqui):

- Painel CEMPRE (D10, espinha dorsal município-ano):
  `data/processed/cempre_painel_analitico_2007_2019.parquet`
  (produzido por `constroi_painel_analitico_cempre.py`).

- Cadastro nacional de exposição/elegibilidade a controle (universo
  estrutural completo, 1 linha por município, 5.570 municípios):
  `data/processed/cadastro_elegibilidade_controles_2007_2019.parquet`
  (produzido por `constroi_pool_candidato_controles.py`, que por sua
  vez reaproveita — sem recalcular — o cadastro nacional de exposição
  de `constroi_cadastro_nacional_exposicao_rede_federal.py`). Já
  consolida exposição observada à Rede Federal (`sem_exposicao_observada_2007_2019`)
  e elegibilidade estrutural a controle (`fl_elegivel_controle_candidato`)
  — não há necessidade de ler separadamente o resumo de exposição.

- Cadastro causal Fase II (população institucional, 147 municípios,
  timing/coortes/exceções já auditados):
  `outputs/diagnostics/cadastro_causal_tratamento_fase_ii.csv`
  (produzido por `constroi_cadastro_causal_fase_ii.py`, que já
  incorpora `src/excecoes_institucionais_fase_ii.json`).

Princípio da integração (`ESTADO_ATUAL.md`/tarefa D11): o painel CEMPRE
é a espinha dorsal município-ano; a integração faz dois merges
many-to-one (nunca many-to-many) — todas as linhas município-ano do
painel D10 encontram exatamente 1 linha no cadastro nacional (5.570
municípios cobrem o universo estrutural inteiro) e, quando aplicável,
exatamente 1 linha no cadastro causal Fase II (só os 147 têm
correspondência; as demais 5.423 ficam com essas colunas ausentes/NaN
— nunca preenchidas com um valor inventado). O painel integrado
continua com 72.378 linhas — a mesma população do D10, nunca reduzida
para tratados/candidatos/controles.

Nomenclatura: os nomes de campo dos dois cadastros de origem são
preservados EXATAMENTE como estão (`fl_municipio_fase_ii` do cadastro
nacional e `fase_ii` do cadastro causal, por exemplo, não são
unificados nem renomeados silenciosamente) — evita apagar a semântica
canônica já auditada de cada fonte. `municipio`/`uf`/`co_uf` dos dois
cadastros de origem NÃO são reincorporados (o painel D10 já traz
`municipio_fonte`/`uf_codigo` como identidade territorial única —
evita 3 colunas de nome/UF redundantes e potencialmente divergentes).

Esta etapa deliberadamente NÃO cria `post`/`tratado_ano`/`event_time`:
o contrato causal ainda não fixou antecipação, grupo de comparação nem
elegibilidade final — qualquer uma dessas transformações seria
prematura e arriscaria pré-julgar o desenho (`CONTRATO_CAUSAL.md`,
"Itens ainda abertos"). Fica para o próximo gate causal.

Saídas:
  data/processed/cempre_painel_analitico_com_cadastro_causal_2007_2019.parquet
  outputs/diagnostics/cempre_painel_integrado_diagnostico_populacional.csv

Uso:
  python src/constroi_painel_cempre_cadastro_causal.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import constroi_painel_analitico_cempre as analitico  # noqa: E402

# ---------------------------------------------------------------------------
# Configuração global
# ---------------------------------------------------------------------------

DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS_DIAGNOSTICS = ROOT / "outputs" / "diagnostics"

PAINEL_CEMPRE_PATH = DATA_PROCESSED / "cempre_painel_analitico_2007_2019.parquet"
CADASTRO_NACIONAL_PATH = DATA_PROCESSED / "cadastro_elegibilidade_controles_2007_2019.parquet"
CADASTRO_CAUSAL_FASE_II_PATH = OUTPUTS_DIAGNOSTICS / "cadastro_causal_tratamento_fase_ii.csv"

OUT_PAINEL_INTEGRADO = DATA_PROCESSED / "cempre_painel_analitico_com_cadastro_causal_2007_2019.parquet"
OUT_DIAGNOSTICO_POPULACIONAL = OUTPUTS_DIAGNOSTICS / "cempre_painel_integrado_diagnostico_populacional.csv"

N_LINHAS_PAINEL_ESPERADO = 72378
N_MUNICIPIOS_NACIONAL_ESPERADO = 5570
N_FASE_II_ESPERADO = 147
N_CANDIDATOS_PRINCIPAIS_ESPERADO = 129

# Colunas de identidade dos cadastros de origem que NÃO são reincorporadas
# ao painel integrado (o painel D10 já traz identidade territorial única:
# `municipio_fonte`/`uf_codigo`) — evita duplicação/ambiguidade de nome/UF.
_COLUNAS_IDENTIDADE_CADASTRO_NACIONAL = ["municipio", "uf", "co_uf"]
_COLUNAS_IDENTIDADE_CADASTRO_CAUSAL = ["municipio", "uf"]

COLUNAS_CADASTRO_NACIONAL = [
    "primeiro_ano_exposicao_observada", "n_anos_no_universo", "anos_ausentes_do_universo",
    "sem_exposicao_observada_2007_2019", "presente_nos_13_anos_do_universo",
    "fl_municipio_fase_ii", "fl_excluir_exposicao_observada", "fl_excluir_universo_incompleto",
    "fl_excluir_fase_ii", "fl_elegivel_controle_candidato", "motivos_exclusao",
]

COLUNAS_CADASTRO_CAUSAL = [
    "fase_ii", "ano_inicio_observado_censo", "intermitencia_observada_no_painel",
    "ano_evento_institucional", "ano_transicao", "primeiro_ano_completo",
    "ano_coorte_candidata", "origem_coorte", "anos_sensibilidade", "anos_excluir_estimacao",
    "tratamento_absorvente", "tratamento_preexistente_painel", "ever_treated",
    "pode_ser_controle", "n_pre_limpo", "n_pos_disponivel",
    "elegivel_temporal_2pre_3pos", "elegivel_temporal_3pre_3pos",
    "candidato_amostra_principal", "motivo_exclusao_principal",
    "validacao_institucional_individual", "revisao_prioritaria", "nivel_evidencia",
    "status_institucional", "status_timing", "status_populacao_causal",
    "motivo_decisao", "fonte_decisao",
]

# Colunas do painel D10 que devem permanecer byte/logicamente idênticas
# após o merge (item H/O da validação/testes) — as 7 variáveis CEMPRE e
# seus status espelhados.
COLUNAS_OUTCOME_CEMPRE = list(analitico.MAPA_VARIAVEL_COLUNA.values())
COLUNAS_STATUS_CEMPRE = [f"status_{c}" for c in COLUNAS_OUTCOME_CEMPRE]


# ---------------------------------------------------------------------------
# 1. Carga dos artefatos canônicos (nunca recalculados)
# ---------------------------------------------------------------------------


def carrega_painel_cempre(caminho: Path | None = None) -> pd.DataFrame:
    """Carrega o painel analítico CEMPRE (D10) já construído. Somente
    leitura — nunca reconstrói, nunca chama rede."""
    return pd.read_parquet(caminho or PAINEL_CEMPRE_PATH)


def carrega_cadastro_nacional(caminho: Path | None = None) -> pd.DataFrame:
    """Carrega o cadastro nacional de exposição/elegibilidade a
    controle (universo estrutural completo, 1 linha por município)."""
    df = pd.read_parquet(caminho or CADASTRO_NACIONAL_PATH)
    df["codigo_municipio_ibge"] = df["codigo_municipio_ibge"].astype(str)
    return df


def carrega_cadastro_causal_fase_ii(caminho: Path | None = None) -> pd.DataFrame:
    """Carrega o cadastro causal Fase II (147 municípios, timing/
    coortes/exceções já auditados)."""
    df = pd.read_csv(caminho or CADASTRO_CAUSAL_FASE_II_PATH, dtype={"codigo_municipio_ibge": str})
    return df


# ---------------------------------------------------------------------------
# 2-10. Construção do painel integrado (dois merges many-to-one)
# ---------------------------------------------------------------------------


def build_painel_integrado(
    painel_cempre: pd.DataFrame,
    cadastro_nacional: pd.DataFrame,
    cadastro_causal: pd.DataFrame,
) -> pd.DataFrame:
    """Integra o painel CEMPRE (D10) aos dois cadastros canônicos via
    merge many-to-one em `codigo_municipio_ibge`. NUNCA reduz a
    população: todas as linhas município-ano do painel de entrada
    permanecem na saída, na mesma quantidade. Município fora do
    cadastro causal (não é Fase II) recebe NaN nas colunas causais —
    nunca um valor substituto inventado.
    """
    n_entrada = len(painel_cempre)

    cadastro_nacional_util = cadastro_nacional.drop(
        columns=[c for c in _COLUNAS_IDENTIDADE_CADASTRO_NACIONAL if c in cadastro_nacional.columns]
    )
    cadastro_causal_util = cadastro_causal.drop(
        columns=[c for c in _COLUNAS_IDENTIDADE_CADASTRO_CAUSAL if c in cadastro_causal.columns]
    )

    if cadastro_nacional_util["codigo_municipio_ibge"].duplicated().any():
        raise ValueError("cadastro nacional com codigo_municipio_ibge duplicado — merge many-to-one violado")
    if cadastro_causal_util["codigo_municipio_ibge"].duplicated().any():
        raise ValueError("cadastro causal Fase II com codigo_municipio_ibge duplicado — merge many-to-one violado")

    ausentes_do_nacional = set(painel_cempre["codigo_municipio_ibge"]) - set(cadastro_nacional_util["codigo_municipio_ibge"])
    if ausentes_do_nacional:
        raise ValueError(
            f"{len(ausentes_do_nacional)} município(s) do painel CEMPRE sem correspondência "
            f"no cadastro nacional: {sorted(ausentes_do_nacional)[:10]}"
        )

    integrado = painel_cempre.merge(
        cadastro_nacional_util, on="codigo_municipio_ibge", how="left", validate="many_to_one",
    )
    integrado = integrado.merge(
        cadastro_causal_util, on="codigo_municipio_ibge", how="left", validate="many_to_one",
    )

    if len(integrado) != n_entrada:
        raise ValueError(
            f"painel integrado com {len(integrado)} linhas, esperado {n_entrada} "
            "(merge many-to-one não deveria alterar a contagem de linhas)"
        )

    if integrado.duplicated(subset=["codigo_municipio_ibge", "ano"]).any():
        raise ValueError("painel integrado com chave (codigo_municipio_ibge, ano) duplicada após o merge")

    return integrado


# ---------------------------------------------------------------------------
# 15. Validações de merge
# ---------------------------------------------------------------------------


def validate_painel_integrado(
    painel_original: pd.DataFrame,
    painel_integrado: pd.DataFrame,
    cadastro_causal: pd.DataFrame,
    n_linhas_esperado: int = N_LINHAS_PAINEL_ESPERADO,
    n_fase_ii_esperado: int = N_FASE_II_ESPERADO,
    n_candidatos_esperado: int = N_CANDIDATOS_PRINCIPAIS_ESPERADO,
) -> dict[str, Any]:
    """Validações A-H da integração (seção 15 do D11). Levanta
    `ValueError` para qualquer violação — nunca corrige silenciosamente."""
    # A. número de linhas preservado
    if len(painel_integrado) != n_linhas_esperado:
        raise ValueError(f"A: painel integrado com {len(painel_integrado)} linhas, esperado {n_linhas_esperado}")

    # B. chave município-ano única
    if painel_integrado.duplicated(subset=["codigo_municipio_ibge", "ano"]).any():
        raise ValueError("B: chave (codigo_municipio_ibge, ano) não é única no painel integrado")

    # E. todos os 147 Fase II presentes
    municipios_fase_ii_causal = set(cadastro_causal["codigo_municipio_ibge"])
    municipios_fase_ii_no_painel = set(
        painel_integrado.loc[painel_integrado["fase_ii"] == True, "codigo_municipio_ibge"]  # noqa: E712
    )
    if municipios_fase_ii_no_painel != municipios_fase_ii_causal:
        faltando = municipios_fase_ii_causal - municipios_fase_ii_no_painel
        extra = municipios_fase_ii_no_painel - municipios_fase_ii_causal
        raise ValueError(f"E: Fase II divergente no painel integrado — faltando={sorted(faltando)} extra={sorted(extra)}")
    if len(municipios_fase_ii_no_painel) != n_fase_ii_esperado:
        raise ValueError(f"E: {len(municipios_fase_ii_no_painel)} municípios Fase II no painel, esperado {n_fase_ii_esperado}")

    # F. todos os 129 candidatos principais presentes
    municipios_candidatos_causal = set(
        cadastro_causal.loc[cadastro_causal["candidato_amostra_principal"] == True, "codigo_municipio_ibge"]  # noqa: E712
    )
    municipios_candidatos_no_painel = set(
        painel_integrado.loc[painel_integrado["candidato_amostra_principal"] == True, "codigo_municipio_ibge"]  # noqa: E712
    )
    if municipios_candidatos_no_painel != municipios_candidatos_causal:
        raise ValueError("F: candidatos principais divergentes entre painel integrado e cadastro causal")
    if len(municipios_candidatos_no_painel) != n_candidatos_esperado:
        raise ValueError(f"F: {len(municipios_candidatos_no_painel)} candidatos principais, esperado {n_candidatos_esperado}")

    # G. flags Fase II/coorte batem exatamente com o cadastro causal original
    colunas_causais_presentes = [c for c in COLUNAS_CADASTRO_CAUSAL if c in painel_integrado.columns]
    municipio_ano = painel_integrado[["codigo_municipio_ibge"] + colunas_causais_presentes].drop_duplicates(
        subset="codigo_municipio_ibge"
    ).set_index("codigo_municipio_ibge")
    causal_indexado = cadastro_causal.set_index("codigo_municipio_ibge")[colunas_causais_presentes]
    comparacao = municipio_ano.loc[sorted(municipios_fase_ii_causal)].sort_index()
    esperado = causal_indexado.loc[sorted(municipios_fase_ii_causal)].sort_index()
    # check_dtype=False: o merge left pode fazer upcast de dtype (ex.: bool
    # -> object) em colunas com NaN para município não-Fase II — isso não é
    # uma divergência de VALOR, só de representação; comparamos o conteúdo
    # lógico, não o dtype exato da coluna inteira.
    try:
        pd.testing.assert_frame_equal(comparacao, esperado, check_dtype=False, check_like=False)
    except AssertionError as exc:
        raise ValueError(f"G: colunas causais no painel integrado divergem do cadastro causal original para algum dos 147 Fase II: {exc}") from exc

    # H. outcome CEMPRE idêntico antes/depois (byte/logicamente)
    a = painel_original[["codigo_municipio_ibge", "ano"] + COLUNAS_OUTCOME_CEMPRE + COLUNAS_STATUS_CEMPRE].sort_values(
        ["codigo_municipio_ibge", "ano"]
    ).reset_index(drop=True)
    b = painel_integrado[["codigo_municipio_ibge", "ano"] + COLUNAS_OUTCOME_CEMPRE + COLUNAS_STATUS_CEMPRE].sort_values(
        ["codigo_municipio_ibge", "ano"]
    ).reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(a, b, check_like=False)
    except AssertionError as exc:
        raise ValueError(f"H: outcome/status CEMPRE mudou após o merge: {exc}") from exc

    return {
        "n_linhas": len(painel_integrado),
        "n_fase_ii": len(municipios_fase_ii_no_painel),
        "n_candidatos_principais": len(municipios_candidatos_no_painel),
    }


# ---------------------------------------------------------------------------
# 14. Diagnóstico da população
# ---------------------------------------------------------------------------


def build_diagnostico_populacional(painel_integrado: pd.DataFrame) -> pd.DataFrame:
    """Diagnóstico pequeno de contagens populacionais do painel
    integrado — NÃO é usado como input causal, apenas rastreabilidade."""
    por_municipio = painel_integrado.drop_duplicates(subset="codigo_municipio_ibge")

    linhas: list[dict[str, Any]] = [
        {"metrica": "municipios_totais", "valor": int(por_municipio["codigo_municipio_ibge"].nunique())},
        {"metrica": "municipio_ano_totais", "valor": int(len(painel_integrado))},
        {"metrica": "fase_ii", "valor": int((por_municipio["fase_ii"] == True).sum())},  # noqa: E712
        {"metrica": "candidatos_principais", "valor": int((por_municipio["candidato_amostra_principal"] == True).sum())},  # noqa: E712
        {"metrica": "sob_revisao", "valor": int((por_municipio["status_populacao_causal"] == "sob_revisao").sum())},
        {"metrica": "excluidos_principal", "valor": int((por_municipio["status_populacao_causal"] == "excluido_principal").sum())},
        {"metrica": "especial_estimando", "valor": int((por_municipio["status_populacao_causal"] == "especial_estimando").sum())},
        {"metrica": "candidatos_com_ressalva", "valor": int((por_municipio["status_populacao_causal"] == "candidato_com_ressalva").sum())},
        {"metrica": "elegiveis_a_controle", "valor": int((por_municipio["fl_elegivel_controle_candidato"] == True).sum())},  # noqa: E712
        {"metrica": "nao_elegiveis_a_controle", "valor": int((por_municipio["fl_elegivel_controle_candidato"] == False).sum())},  # noqa: E712
        {"metrica": "expostos_rede_federal", "valor": int((por_municipio["sem_exposicao_observada_2007_2019"] == False).sum())},  # noqa: E712
        {"metrica": "nunca_expostos_rede_federal", "valor": int((por_municipio["sem_exposicao_observada_2007_2019"] == True).sum())},  # noqa: E712
        {
            "metrica": "fase_ii_sem_coorte_candidata",
            "valor": int(((por_municipio["fase_ii"] == True) & por_municipio["ano_coorte_candidata"].isna()).sum()),  # noqa: E712
        },
    ]

    for ano_coorte, contagem in sorted(
        por_municipio.loc[por_municipio["candidato_amostra_principal"] == True, "ano_coorte_candidata"]  # noqa: E712
        .value_counts().items()
    ):
        linhas.append({"metrica": f"coorte_candidata_{int(ano_coorte)}", "valor": int(contagem)})

    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> dict[str, Any]:
    print("=" * 70)
    print("D11 — Integração do painel analítico CEMPRE ao cadastro causal")
    print("=" * 70)

    print("\n[1] Carregando artefatos canônicos (somente leitura)...")
    painel_cempre = carrega_painel_cempre()
    cadastro_nacional = carrega_cadastro_nacional()
    cadastro_causal = carrega_cadastro_causal_fase_ii()
    print(f"    painel CEMPRE: {len(painel_cempre):,} linhas, {painel_cempre['codigo_municipio_ibge'].nunique():,} municípios")
    print(f"    cadastro nacional: {len(cadastro_nacional):,} municípios")
    print(f"    cadastro causal Fase II: {len(cadastro_causal):,} municípios")

    print("\n[2] Construindo o painel integrado (2 merges many-to-one)...")
    painel_integrado = build_painel_integrado(painel_cempre, cadastro_nacional, cadastro_causal)
    print(f"    linhas={len(painel_integrado):,} colunas={len(painel_integrado.columns)}")

    print("\n[3] Validando o merge...")
    resultado_validacao = validate_painel_integrado(painel_cempre, painel_integrado, cadastro_causal)
    print(f"    OK — validações A-H passaram. {resultado_validacao}")

    print("\n[4] Construindo diagnóstico populacional...")
    diagnostico = build_diagnostico_populacional(painel_integrado)
    print(diagnostico.to_string(index=False))

    print("\n[5] Salvando artefatos...")
    OUT_PAINEL_INTEGRADO.parent.mkdir(parents=True, exist_ok=True)
    OUT_DIAGNOSTICO_POPULACIONAL.parent.mkdir(parents=True, exist_ok=True)
    painel_integrado.to_parquet(OUT_PAINEL_INTEGRADO, index=False, engine="pyarrow")
    diagnostico.to_csv(OUT_DIAGNOSTICO_POPULACIONAL, index=False, encoding="utf-8")
    print(f"    {OUT_PAINEL_INTEGRADO}")
    print(f"    {OUT_DIAGNOSTICO_POPULACIONAL}")

    return {
        "n_painel_integrado": len(painel_integrado),
        "validacao": resultado_validacao,
        "diagnostico": diagnostico,
    }


if __name__ == "__main__":
    main()
