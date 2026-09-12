"""Constrói o cadastro causal preliminar da Expansão Fase II.

Combina o cadastro oficial, o timing observado diretamente no painel do Censo
Escolar e decisões institucionais versionadas. Não estima efeitos, não altera
os Parquets de entrada e não define tratamento causal definitivo.

O tratamento operacional candidato é "presença operacional de campus da
Expansão Fase II no município". Sob essa definição o tratamento é absorvente,
mas a flag anual de EPT ativa do Censo é apenas evidência observacional — ela
não representa automaticamente abertura ou fechamento institucional do campus.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

import auditoria_timing_tratamento as auditoria

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FASE_II_PATH = PROJECT_ROOT / "data" / "processed" / "fase_ii_municipios.parquet"
PAINEL_PATH = PROJECT_ROOT / "data" / "processed" / "painel_presenca_federal_ept_fase_ii_2007_2019.parquet"
# CSV ignorado pelo Git: conferência opcional, nunca fonte obrigatória do cálculo.
TIMING_AUDIT_CSV = PROJECT_ROOT / "outputs" / "diagnostics" / "auditoria_timing_tratamento.csv"
EXCEPTIONS_PATH = PROJECT_ROOT / "src" / "excecoes_institucionais_fase_ii.json"
OUTPUT_CSV = PROJECT_ROOT / "outputs" / "diagnostics" / "cadastro_causal_tratamento_fase_ii.csv"

ANO_INICIAL = 2007
ANO_FINAL = 2019
# Permite eventos institucionais documentados como anteriores ao painel
# (ex.: Duque de Caxias, UNED em funcionamento desde 2006).
ANO_MINIMO_ADMITIDO = 2006

STATUS_POPULACAO_CAUSAL_VALIDOS = {
    "candidato_principal",
    "excluido_principal",
    "especial_estimando",
    "sob_revisao",
    "institucional_inelegivel_janelas",
    "candidato_com_ressalva",
}
ORIGEM_COORTE_VALIDA = {"institucional_validada", "proxy_censo", "nao_aplicavel"}
NIVEL_EVIDENCIA_INSTITUCIONAL = {
    "indicio_secundario", "fonte_institucional_oficial", "fonte_primaria_legislativa",
}
NIVEL_EVIDENCIA_VALIDO = NIVEL_EVIDENCIA_INSTITUCIONAL | {"nenhuma", "auditoria_local_dados"}

STATUS_QUE_EXIGEM_MOTIVO = {
    "excluido_principal", "especial_estimando", "sob_revisao",
    "institucional_inelegivel_janelas", "candidato_com_ressalva",
}

REQUIRED_COLUMNS = [
    "codigo_municipio_ibge", "municipio", "uf", "fase_ii",
    "ano_inicio_observado_censo", "intermitencia_observada_no_painel",
    "ano_evento_institucional", "ano_transicao", "primeiro_ano_completo",
    "ano_coorte_candidata", "origem_coorte",
    "anos_sensibilidade", "anos_excluir_estimacao",
    "tratamento_absorvente", "tratamento_preexistente_painel",
    "ever_treated", "pode_ser_controle",
    "n_pre_limpo", "n_pos_disponivel",
    "elegivel_temporal_2pre_3pos", "elegivel_temporal_3pre_3pos",
    "candidato_amostra_principal", "motivo_exclusao_principal",
    "validacao_institucional_individual", "revisao_prioritaria", "nivel_evidencia",
    "status_institucional", "status_timing", "status_populacao_causal",
    "motivo_decisao", "fonte_decisao",
]

EXCEPTION_REQUIRED_FIELDS = {
    "ano_evento_institucional", "ano_transicao", "primeiro_ano_completo",
    "ano_coorte_candidata", "origem_coorte", "anos_sensibilidade",
    "anos_excluir_estimacao", "tratamento_absorvente", "tratamento_preexistente_painel",
    "status_institucional", "status_timing", "status_populacao_causal",
    "validacao_institucional_individual", "revisao_prioritaria", "nivel_evidencia",
    "motivo_decisao", "fonte_decisao",
}
EXCEPTION_CAMPOS_PERMITIDOS = EXCEPTION_REQUIRED_FIELDS | {"fontes"}
FONTE_CAMPOS_OBRIGATORIOS = {
    "url_ou_caminho", "titulo", "orgao", "data_evidencia_ou_acesso",
    "nivel_evidencia", "descricao_factual", "campo_sustentado",
}
CAMPOS_POPULACIONAIS_PROIBIDOS_EM_EXCECAO = {"ever_treated", "pode_ser_controle", "fase_ii"}


# ---------------------------------------------------------------------------
# Leitura e validação estrutural do painel (Correções 1 e 2)
# ---------------------------------------------------------------------------

def is_missing_year(value: Any) -> bool:
    """Trata None, NaN e pandas.NA como ano ausente."""
    return bool(pd.isna(value))


def compute_timing_observado_censo(fase_ii: pd.DataFrame, painel: pd.DataFrame) -> pd.DataFrame:
    """Calcula, diretamente do painel município-ano, o primeiro ano observado
    de EPT federal ativa e se a trajetória tem interrupção interna.

    Reusa a validação estrutural completa do painel já implementada na
    auditoria de timing (exatamente 1.911 linhas, 147 códigos únicos, chave
    município-ano única, exatamente 13 observações por município, anos
    exatamente 2007–2019 por município, sem códigos fora da lista oficial e
    sem município oficial sem observação) para nunca calcular sobre um painel
    malformado. Não depende do CSV de auditoria, que é ignorado pelo Git.
    """
    auditoria.validate_input_data(fase_ii, painel)
    panel = painel.copy()
    panel["CO_MUNICIPIO"] = panel["CO_MUNICIPIO"].astype("string").str.zfill(7)
    panel["NU_ANO_CENSO"] = pd.to_numeric(panel["NU_ANO_CENSO"], errors="raise").astype(int)
    flag = auditoria.PRESENCE_DEFINITIONS["presenca_federal_ept_ativa"]

    rows = []
    for code, group in panel[["CO_MUNICIPIO", "NU_ANO_CENSO", flag]].groupby("CO_MUNICIPIO", sort=False):
        group = group.sort_values("NU_ANO_CENSO")
        summary = auditoria.summarize_presence_trajectory(
            group["NU_ANO_CENSO"].tolist(), group[flag].astype(bool).tolist()
        )
        rows.append({
            "codigo_municipio_ibge": code,
            "ano_inicio_observado_censo": summary["primeiro_ano"],
            "intermitencia_observada_no_painel": bool(summary["tem_interrupcao_interna"]),
        })
    result = pd.DataFrame(rows)
    if len(result) != 147:
        raise ValueError(f"Cálculo direto do painel produziu {len(result)} municípios; esperado 147.")
    return result


def _years_equal(a: pd.Series, b: pd.Series) -> pd.Series:
    a_na, b_na = a.isna(), b.isna()
    both_present_equal = (~a_na) & (~b_na) & (a.astype("Float64") == b.astype("Float64"))
    return (a_na & b_na) | both_present_equal


def cross_check_timing_csv(computed: pd.DataFrame, csv_path: Path = TIMING_AUDIT_CSV) -> None:
    """Confere opcionalmente o cálculo direto contra o CSV de auditoria.

    O CSV é ignorado pelo Git e pode faltar num clone limpo — nesse caso a
    conferência é simplesmente pulada. Quando presente, exige igualdade exata
    e falha com mensagem clara diante de qualquer divergência; nunca é usado
    como substituto do cálculo direto.
    """
    if not csv_path.exists():
        return
    audit = pd.read_csv(csv_path, dtype={"codigo_municipio_ibge": "string"})
    coluna = "primeiro_ano_presenca_federal_ept_ativa"
    if coluna not in audit.columns:
        raise ValueError(
            f"{csv_path}: coluna '{coluna}' ausente; não é possível conferir contra o "
            "cálculo direto do painel."
        )
    audit = audit[["codigo_municipio_ibge", coluna]].copy()
    audit["codigo_municipio_ibge"] = audit["codigo_municipio_ibge"].astype("string").str.zfill(7)

    if audit["codigo_municipio_ibge"].isna().any():
        raise ValueError(f"{csv_path}: CSV de auditoria contém código municipal nulo.")
    duplicados = sorted(
        audit.loc[audit["codigo_municipio_ibge"].duplicated(keep=False), "codigo_municipio_ibge"].unique()
    )
    if duplicados:
        raise ValueError(f"{csv_path}: código municipal duplicado no CSV de auditoria: {duplicados}.")
    codigos_csv = set(audit["codigo_municipio_ibge"])
    codigos_calculado = set(computed["codigo_municipio_ibge"])
    ausentes_no_csv = sorted(codigos_calculado - codigos_csv)
    excedentes_no_csv = sorted(codigos_csv - codigos_calculado)
    if ausentes_no_csv or excedentes_no_csv:
        raise ValueError(
            f"{csv_path}: conjunto de códigos municipais do CSV de auditoria diverge do cálculo "
            f"direto do painel. Ausentes no CSV: {ausentes_no_csv}. Excedentes no CSV: {excedentes_no_csv}."
        )

    merged = computed.merge(audit, on="codigo_municipio_ibge", how="left", validate="one_to_one")
    divergentes = merged.loc[
        ~_years_equal(merged["ano_inicio_observado_censo"], merged[coluna]), "codigo_municipio_ibge"
    ].tolist()
    if divergentes:
        raise ValueError(
            "Divergência entre o primeiro ano calculado diretamente do painel e o CSV de "
            f"auditoria opcional ({csv_path}) para os municípios: {divergentes}. O CSV de "
            "auditoria é apenas conferência opcional, nunca a fonte do cálculo; regenere-o "
            "com src/auditoria_timing_tratamento.py ou remova-o."
        )


# ---------------------------------------------------------------------------
# Exceções institucionais (Correções 3, 4, 5, 6, 7, 8)
# ---------------------------------------------------------------------------

def validate_exception_schema(code: str, exception: dict[str, Any]) -> None:
    """Valida integralmente uma exceção institucional individual.

    Cobre: schema/campos obrigatórios, tipos, anos plausíveis, valores
    permitidos de status/origem/nível de evidência, coerência cronológica,
    coerência entre tratamento_preexistente_painel e coorte, coerência entre
    anos_excluir_estimacao e ano de transição, e proveniência mínima sempre
    que uma validação institucional individual é reivindicada.
    """
    faltantes = sorted(EXCEPTION_REQUIRED_FIELDS - set(exception))
    if faltantes:
        raise ValueError(f"{code}: exceção sem campos obrigatórios: {faltantes}")

    desconhecidos = sorted(set(exception) - EXCEPTION_CAMPOS_PERMITIDOS)
    if desconhecidos:
        raise ValueError(f"{code}: exceção com campos desconhecidos: {desconhecidos}")

    proibidos_presentes = sorted(CAMPOS_POPULACIONAIS_PROIBIDOS_EM_EXCECAO & set(exception))
    if proibidos_presentes:
        raise ValueError(
            f"{code}: campos {proibidos_presentes} são fixos para toda a população institucional "
            "(ever_treated=true, pode_ser_controle=false, fase_ii=true) e não podem ser "
            "sobrescritos por exceção."
        )

    ano_fields = ["ano_evento_institucional", "ano_transicao", "primeiro_ano_completo", "ano_coorte_candidata"]
    for field in ano_fields:
        value = exception[field]
        if value is not None:
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"{code}: '{field}' deve ser inteiro ou null; recebido {value!r}.")
            if not (ANO_MINIMO_ADMITIDO <= value <= ANO_FINAL):
                raise ValueError(
                    f"{code}: '{field}'={value} fora da janela admitida "
                    f"[{ANO_MINIMO_ADMITIDO}, {ANO_FINAL}]."
                )

    for field in ["anos_sensibilidade", "anos_excluir_estimacao"]:
        value = exception[field]
        if not isinstance(value, list) or any(not isinstance(v, int) or isinstance(v, bool) for v in value):
            raise ValueError(f"{code}: '{field}' deve ser uma lista de inteiros.")
        for year in value:
            if not (ANO_MINIMO_ADMITIDO <= year <= ANO_FINAL):
                raise ValueError(f"{code}: '{field}' contém ano fora da janela admitida: {year}.")

    for field in ["tratamento_absorvente", "tratamento_preexistente_painel",
                  "validacao_institucional_individual", "revisao_prioritaria"]:
        if not isinstance(exception[field], bool):
            raise ValueError(f"{code}: '{field}' deve ser booleano.")

    for field in ["status_institucional", "status_timing", "motivo_decisao", "fonte_decisao"]:
        if not isinstance(exception[field], str) or not exception[field].strip():
            raise ValueError(f"{code}: '{field}' deve ser texto não vazio.")

    status = exception["status_populacao_causal"]
    if status not in STATUS_POPULACAO_CAUSAL_VALIDOS:
        raise ValueError(
            f"{code}: status_populacao_causal={status!r} inválido; "
            f"esperado um de {sorted(STATUS_POPULACAO_CAUSAL_VALIDOS)}."
        )
    origem = exception["origem_coorte"]
    if origem not in ORIGEM_COORTE_VALIDA:
        raise ValueError(f"{code}: origem_coorte={origem!r} inválido; esperado um de {sorted(ORIGEM_COORTE_VALIDA)}.")
    nivel = exception["nivel_evidencia"]
    if nivel not in NIVEL_EVIDENCIA_VALIDO:
        raise ValueError(f"{code}: nivel_evidencia={nivel!r} inválido; esperado um de {sorted(NIVEL_EVIDENCIA_VALIDO)}.")

    fontes = exception.get("fontes", [])
    if not isinstance(fontes, list):
        raise ValueError(f"{code}: 'fontes' deve ser uma lista.")
    for indice, fonte in enumerate(fontes):
        if not isinstance(fonte, dict):
            raise ValueError(f"{code}: 'fontes[{indice}]' deve ser um objeto.")
        faltantes_fonte = sorted(FONTE_CAMPOS_OBRIGATORIOS - set(fonte))
        if faltantes_fonte:
            raise ValueError(f"{code}: 'fontes[{indice}]' sem campos obrigatórios: {faltantes_fonte}.")
        desconhecidos_fonte = sorted(set(fonte) - FONTE_CAMPOS_OBRIGATORIOS)
        if desconhecidos_fonte:
            raise ValueError(f"{code}: 'fontes[{indice}]' com campos desconhecidos: {desconhecidos_fonte}.")
        for campo, valor in fonte.items():
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(f"{code}: 'fontes[{indice}].{campo}' deve ser texto não vazio.")
        if fonte["nivel_evidencia"] not in NIVEL_EVIDENCIA_VALIDO:
            raise ValueError(f"{code}: 'fontes[{indice}].nivel_evidencia'={fonte['nivel_evidencia']!r} inválido.")

    # --- coerência cronológica e estrutural ---
    evento, transicao = exception["ano_evento_institucional"], exception["ano_transicao"]
    completo, coorte = exception["primeiro_ano_completo"], exception["ano_coorte_candidata"]
    preexistente, absorvente = exception["tratamento_preexistente_painel"], exception["tratamento_absorvente"]
    excluir, validado = set(exception["anos_excluir_estimacao"]), exception["validacao_institucional_individual"]

    if transicao is not None and evento is not None and transicao != evento:
        raise ValueError(
            f"{code}: ano_transicao ({transicao}) deve coincidir com ano_evento_institucional "
            f"({evento}) quando ambos definidos."
        )
    if completo is not None and transicao is not None and completo < transicao:
        raise ValueError(f"{code}: primeiro_ano_completo ({completo}) não pode preceder ano_transicao ({transicao}).")
    if completo is not None and evento is not None and completo < evento:
        raise ValueError(
            f"{code}: primeiro_ano_completo ({completo}) não pode preceder ano_evento_institucional ({evento})."
        )
    if transicao is not None and transicao not in excluir:
        raise ValueError(f"{code}: ano_transicao ({transicao}) deve constar em anos_excluir_estimacao.")
    if completo is not None and any(year >= completo for year in excluir):
        raise ValueError(
            f"{code}: anos_excluir_estimacao não pode conter anos a partir de primeiro_ano_completo ({completo})."
        )

    if preexistente:
        if coorte is not None or completo is not None:
            raise ValueError(
                f"{code}: tratamento_preexistente_painel=true exige ano_coorte_candidata e "
                "primeiro_ano_completo nulos (não há coorte dentro do painel)."
            )
        if status != "excluido_principal":
            raise ValueError(f"{code}: tratamento_preexistente_painel=true exige status_populacao_causal='excluido_principal'.")

    if absorvente and coorte is None and origem != "proxy_censo":
        raise ValueError(f"{code}: tratamento_absorvente=true exige ano_coorte_candidata definida.")

    if origem == "proxy_censo" and coorte is not None:
        raise ValueError(
            f"{code}: origem_coorte='proxy_censo' exige ano_coorte_candidata nulo no JSON "
            "(preenchida automaticamente a partir do painel)."
        )
    if origem == "institucional_validada" and coorte is None:
        raise ValueError(f"{code}: origem_coorte='institucional_validada' exige ano_coorte_candidata definida.")
    if origem == "nao_aplicavel" and (coorte is not None or completo is not None):
        raise ValueError(f"{code}: origem_coorte='nao_aplicavel' exige ano_coorte_candidata e primeiro_ano_completo nulos.")

    if validado and nivel not in NIVEL_EVIDENCIA_INSTITUCIONAL:
        raise ValueError(
            f"{code}: validacao_institucional_individual=true exige nivel_evidencia institucional "
            f"(um de {sorted(NIVEL_EVIDENCIA_INSTITUCIONAL)}); recebido {nivel!r}."
        )
    if not validado and nivel in NIVEL_EVIDENCIA_INSTITUCIONAL:
        raise ValueError(f"{code}: nivel_evidencia={nivel!r} é institucional, mas validacao_institucional_individual=false.")
    if validado and not fontes:
        raise ValueError(f"{code}: validacao_institucional_individual=true exige ao menos uma entrada em 'fontes'.")

    if status in STATUS_QUE_EXIGEM_MOTIVO and not exception["motivo_decisao"].strip():
        raise ValueError(f"{code}: status_populacao_causal={status!r} exige motivo_decisao não vazio.")


def load_exceptions(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"JSON de exceções não encontrado: {path}")
    with path.open(encoding="utf-8") as file:
        try:
            raw = json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}: JSON inválido: {error}") from error
    if not isinstance(raw, dict):
        raise ValueError("JSON de exceções deve ser um objeto indexado por código IBGE.")

    exceptions: dict[str, dict[str, Any]] = {}
    for raw_code, exception in raw.items():
        code = str(raw_code).zfill(7)
        if code in exceptions:
            raise ValueError(f"Código IBGE duplicado após normalização: {code} (original: {raw_code}).")
        if not isinstance(exception, dict):
            raise ValueError(f"{code}: cada exceção deve ser um objeto JSON.")
        validate_exception_schema(code, exception)
        exceptions[code] = exception
    return exceptions


def validate_exception_codes(fase_ii: pd.DataFrame, exceptions: dict[str, dict[str, Any]]) -> None:
    official = set(fase_ii["codigo_municipio_ibge"].astype("string").str.zfill(7))
    unknown = sorted(set(exceptions) - official)
    if unknown:
        raise ValueError(f"Exceções com código IBGE inexistente no cadastro oficial: {unknown}")


# ---------------------------------------------------------------------------
# Construção da decisão por município (Correções 3, 4, 5)
# ---------------------------------------------------------------------------

def build_default_decision(code: str, observed_year: Any, intermitencia: bool = False) -> dict[str, Any]:
    """Decisão padrão para município sem exceção institucional individual.

    Não presume primeiro ano completo: o primeiro ano observado no Censo é
    mantido apenas como proxy anual (`origem_coorte='proxy_censo'`), nunca
    como data institucional confirmada.
    """
    observed = None if is_missing_year(observed_year) else int(observed_year)
    return {
        "codigo_municipio_ibge": str(code).zfill(7),
        "ano_inicio_observado_censo": observed,
        "intermitencia_observada_no_painel": bool(intermitencia),
        "ano_evento_institucional": None,
        "ano_transicao": None,
        "primeiro_ano_completo": None,
        "ano_coorte_candidata": observed,
        "origem_coorte": "proxy_censo" if observed is not None else "nao_aplicavel",
        "anos_sensibilidade": [],
        "anos_excluir_estimacao": [],
        "tratamento_absorvente": observed is not None,
        "tratamento_preexistente_painel": False,
        "ever_treated": True,
        "pode_ser_controle": False,
        "validacao_institucional_individual": False,
        "revisao_prioritaria": observed is None,
        "nivel_evidencia": "nenhuma",
        "status_institucional": (
            "proxy_censo_sem_validacao_individual" if observed is not None else "sem_presenca_ept_ativa_observada"
        ),
        "status_timing": "proxy_primeiro_ept_federal_ativa" if observed is not None else "indeterminado",
        "status_populacao_causal": "candidato_principal" if observed is not None else "sob_revisao",
        "motivo_decisao": (
            "Primeiro ano de EPT federal ativa usado como proxy automática do Censo; sem "
            "validação institucional individual. Não confirma criação, autorização, "
            "inauguração ou início das aulas."
        ) if observed is not None else (
            "Nenhuma presença federal com EPT ativa observada no painel 2007-2019; "
            "requer revisão institucional individual."
        ),
        "fonte_decisao": "painel_censo_escolar",
        "fontes": [],
    }


def apply_exception(decision: dict[str, Any], exception: dict[str, Any]) -> dict[str, Any]:
    """Aplica uma exceção institucional sobre a decisão padrão.

    Quando `origem_coorte='proxy_censo'`, a coorte candidata (e a decorrente
    `tratamento_absorvente`) é sempre recalculada a partir do valor
    reproduzível do painel — nunca copiada literalmente do JSON — para que a
    fonte do número continue sendo o painel, não um valor congelado no texto.
    """
    merged = {**decision, **exception}
    merged["codigo_municipio_ibge"] = str(merged["codigo_municipio_ibge"]).zfill(7)
    if merged["origem_coorte"] == "proxy_censo":
        merged["ano_coorte_candidata"] = merged["ano_inicio_observado_censo"]
        merged["tratamento_absorvente"] = merged["ano_inicio_observado_censo"] is not None
    return merged


def calculate_n_pre_limpo(decision: dict[str, Any]) -> int | None:
    cohort = decision["ano_coorte_candidata"]
    if is_missing_year(cohort):
        return None
    transition = decision.get("ano_transicao")
    pre_end = cohort if is_missing_year(transition) else transition
    return int(pre_end) - ANO_INICIAL


def calculate_n_pos_disponivel(decision: dict[str, Any]) -> int | None:
    cohort = decision["ano_coorte_candidata"]
    return None if is_missing_year(cohort) else ANO_FINAL - int(cohort)


def eligible(decision: dict[str, Any], pre: int, post: int, end_year: int = ANO_FINAL) -> bool:
    cohort = decision["ano_coorte_candidata"]
    if is_missing_year(cohort):
        return False
    n_pre = calculate_n_pre_limpo(decision)
    n_pos = end_year - int(cohort)
    return bool(n_pre is not None and n_pre >= pre and n_pos >= post)


def absorbing_treatment_series(cohort: int | None, start_year: int = ANO_INICIAL, end_year: int = ANO_FINAL) -> list[bool]:
    if is_missing_year(cohort):
        return [False] * (end_year - start_year + 1)
    return [year >= cohort for year in range(start_year, end_year + 1)]


def compute_candidato_amostra_principal(decision: dict[str, Any]) -> tuple[bool, str]:
    """Decide a candidatura à amostra principal sem transformar a elegibilidade
    temporal bruta em pertencimento automático (Correção 4).

    Exige, simultaneamente: status curado como 'candidato_principal', ausência
    de tratamento preexistente ao painel, uma coorte candidata definida e
    elegibilidade temporal mínima (2 pré / 3 pós).
    """
    status = decision["status_populacao_causal"]
    coorte = decision["ano_coorte_candidata"]
    if status != "candidato_principal":
        return False, f"status_populacao_causal={status}: {decision['motivo_decisao']}"
    if decision["tratamento_preexistente_painel"]:
        return False, "tratamento_preexistente_painel=true: sem período pré-tratamento observável no painel."
    if is_missing_year(coorte):
        return False, "ano_coorte_candidata indefinida: sem coorte para estimação."
    if not decision["elegivel_temporal_2pre_3pos"]:
        return False, (
            "elegibilidade_temporal_insuficiente (mínimo 2 pré / 3 pós): "
            f"n_pre_limpo={decision['n_pre_limpo']}, n_pos_disponivel={decision['n_pos_disponivel']}."
        )
    return True, ""


def normalize_year_list(years: list[int] | None) -> str:
    if not years:
        return ""
    return ";".join(str(int(year)) for year in years)


def parse_year_list(value: Any) -> list[int]:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
        return []
    return [int(year) for year in str(value).split(";") if year]


# ---------------------------------------------------------------------------
# Montagem e validação do cadastro (Correções 2, 4, 8)
# ---------------------------------------------------------------------------

def build_causal_registry(
    fase_ii: pd.DataFrame,
    painel: pd.DataFrame,
    exceptions: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    fase = fase_ii[["codigo_municipio_ibge", "municipio", "uf"]].copy()
    fase["codigo_municipio_ibge"] = fase["codigo_municipio_ibge"].astype("string").str.zfill(7)
    validate_exception_codes(fase, exceptions)

    timing = compute_timing_observado_censo(fase_ii, painel)
    cross_check_timing_csv(timing)

    merged = fase.merge(timing, on="codigo_municipio_ibge", how="left", validate="one_to_one")
    if len(merged) != 147:
        raise ValueError(f"Junção entre cadastro oficial e painel produziu {len(merged)} municípios; esperado 147.")

    rows = []
    for row in merged.itertuples(index=False):
        decision = build_default_decision(
            row.codigo_municipio_ibge, row.ano_inicio_observado_censo, row.intermitencia_observada_no_painel
        )
        if row.codigo_municipio_ibge in exceptions:
            decision = apply_exception(decision, exceptions[row.codigo_municipio_ibge])
        decision.update({"municipio": row.municipio, "uf": row.uf, "fase_ii": True})
        decision["n_pre_limpo"] = calculate_n_pre_limpo(decision)
        decision["n_pos_disponivel"] = calculate_n_pos_disponivel(decision)
        decision["elegivel_temporal_2pre_3pos"] = eligible(decision, pre=2, post=3)
        decision["elegivel_temporal_3pre_3pos"] = eligible(decision, pre=3, post=3)
        candidato, motivo = compute_candidato_amostra_principal(decision)
        decision["candidato_amostra_principal"] = candidato
        decision["motivo_exclusao_principal"] = motivo
        decision["anos_sensibilidade"] = normalize_year_list(decision["anos_sensibilidade"])
        decision["anos_excluir_estimacao"] = normalize_year_list(decision["anos_excluir_estimacao"])
        decision.pop("fontes", None)
        rows.append(decision)

    registry = pd.DataFrame(rows)
    registry = registry[REQUIRED_COLUMNS].sort_values(
        ["uf", "municipio", "codigo_municipio_ibge"], kind="stable"
    ).reset_index(drop=True)
    validate_causal_registry(registry, exceptions)
    return registry


def validate_causal_registry(registry: pd.DataFrame, exceptions: dict[str, dict[str, Any]]) -> None:
    missing_cols = sorted(set(REQUIRED_COLUMNS) - set(registry.columns))
    if missing_cols:
        raise ValueError(f"Cadastro causal sem colunas obrigatórias: {missing_cols}")

    codes = registry["codigo_municipio_ibge"].astype("string").str.zfill(7)
    if len(registry) != 147 or codes.isna().any() or codes.nunique() != 147:
        raise ValueError("Cadastro causal deve conter exatamente 147 códigos IBGE únicos e não nulos.")
    if set(exceptions) - set(codes):
        raise ValueError("Cadastro causal não contém todas as exceções declaradas.")

    if not registry["fase_ii"].all():
        raise ValueError("fase_ii deve ser verdadeiro para todos os 147 municípios.")
    if not registry["ever_treated"].all():
        raise ValueError("ever_treated deve ser verdadeiro para todos os 147 municípios da população institucional oficial.")
    if registry["pode_ser_controle"].any():
        raise ValueError("pode_ser_controle deve ser falso para todos os 147 municípios; nenhum pode ser never-treated.")

    year_columns = ["ano_inicio_observado_censo", "ano_evento_institucional", "ano_transicao",
                     "primeiro_ano_completo", "ano_coorte_candidata"]
    for column in year_columns:
        numeric = pd.to_numeric(registry[column], errors="coerce")
        if not numeric.dropna().between(ANO_MINIMO_ADMITIDO, ANO_FINAL).all():
            raise ValueError(f"{column}: ano fora da janela admitida.")

    comparable = registry["ano_evento_institucional"].notna() & registry["primeiro_ano_completo"].notna()
    if (registry.loc[comparable, "primeiro_ano_completo"].astype(int) < registry.loc[comparable, "ano_evento_institucional"].astype(int)).any():
        raise ValueError("Primeiro ano completo não pode preceder o evento institucional.")

    partial = registry["ano_transicao"].notna() & registry["ano_coorte_candidata"].notna()
    esperado_n_pre = registry.loc[partial, "ano_transicao"].astype(int) - ANO_INICIAL
    if (registry.loc[partial, "n_pre_limpo"].astype(int) != esperado_n_pre).any():
        raise ValueError("Ano de transição foi contado indevidamente como pré-tratamento limpo.")

    for row in registry.itertuples(index=False):
        excluir = parse_year_list(row.anos_excluir_estimacao)
        if not is_missing_year(row.ano_transicao) and int(row.ano_transicao) not in excluir:
            raise ValueError(f"{row.codigo_municipio_ibge}: ano_transicao ausente de anos_excluir_estimacao.")

    excluded_like = registry["status_populacao_causal"].isin(STATUS_QUE_EXIGEM_MOTIVO)
    if registry.loc[excluded_like, "motivo_decisao"].astype(str).str.strip().eq("").any():
        raise ValueError("Exclusões e casos especiais exigem motivo_decisao obrigatório.")
    if registry.loc[excluded_like, "candidato_amostra_principal"].any():
        raise ValueError(
            "Município excluído, especial, sob revisão, com ressalva ou institucionalmente "
            "inelegível não pode ser candidato_amostra_principal."
        )

    principal_sem_coorte = registry["candidato_amostra_principal"] & registry["ano_coorte_candidata"].isna()
    if principal_sem_coorte.any():
        raise ValueError("candidato_amostra_principal=true exige ano_coorte_candidata definida.")
    principal_inelegivel = registry["candidato_amostra_principal"] & ~registry["elegivel_temporal_2pre_3pos"]
    if principal_inelegivel.any():
        raise ValueError("candidato_amostra_principal=true exige elegibilidade temporal mínima (2 pré / 3 pós).")
    nao_candidato_sem_motivo = (~registry["candidato_amostra_principal"]) & registry["motivo_exclusao_principal"].astype(str).str.strip().eq("")
    if nao_candidato_sem_motivo.any():
        raise ValueError("Município fora da amostra principal exige motivo_exclusao_principal preenchido.")

    preexistente = registry["tratamento_preexistente_painel"]
    if (preexistente & registry["ano_coorte_candidata"].notna()).any():
        raise ValueError("tratamento_preexistente_painel=true não pode ter ano_coorte_candidata definida dentro do painel.")
    if (preexistente & (registry["status_populacao_causal"] != "excluido_principal")).any():
        raise ValueError("tratamento_preexistente_painel=true exige status_populacao_causal='excluido_principal'.")

    expected_2_3 = registry.apply(lambda r: eligible(r.to_dict(), pre=2, post=3), axis=1)
    expected_3_3 = registry.apply(lambda r: eligible(r.to_dict(), pre=3, post=3), axis=1)
    if not registry["elegivel_temporal_2pre_3pos"].eq(expected_2_3).all() or not registry["elegivel_temporal_3pre_3pos"].eq(expected_3_3).all():
        raise ValueError("Elegibilidade temporal inconsistente com as regras declaradas.")

    if registry["tratamento_absorvente"].isna().any():
        raise ValueError("Tratamento absorvente não pode ser nulo.")
    for row in registry.itertuples(index=False):
        if row.tratamento_absorvente and not is_missing_year(row.ano_coorte_candidata):
            series = absorbing_treatment_series(int(row.ano_coorte_candidata))
            if any(later is False and earlier is True for earlier, later in zip(series, series[1:])):
                raise ValueError(f"{row.codigo_municipio_ibge}: tratamento absorvente não é monotônico.")
        # Uma trajetória intermitente observada no painel só pode ser tratada
        # como absorvente (isto é, a lacuna não é lida como reversão) quando
        # houver validação institucional individual documentada — nunca por
        # padrão/proxy. Isso impede classificar automaticamente qualquer
        # intermitência agregada (ex.: Montes Claros) como não-reversão sem
        # justificativa registrada.
        if row.intermitencia_observada_no_painel and row.tratamento_absorvente and not row.validacao_institucional_individual:
            raise ValueError(
                f"{row.codigo_municipio_ibge}: trajetória intermitente no painel não pode ser tratada "
                "como absorvente sem validacao_institucional_individual=true documentada."
            )

    inst_true = registry["validacao_institucional_individual"]
    nivel_institucional = registry["nivel_evidencia"].isin(sorted(NIVEL_EVIDENCIA_INSTITUCIONAL))
    if (inst_true & ~nivel_institucional).any() or (~inst_true & nivel_institucional).any():
        raise ValueError("validacao_institucional_individual inconsistente com nivel_evidencia.")

    if not registry["status_populacao_causal"].isin(STATUS_POPULACAO_CAUSAL_VALIDOS).all():
        raise ValueError("status_populacao_causal inválido em pelo menos um município.")
    if not registry["origem_coorte"].isin(ORIGEM_COORTE_VALIDA).all():
        raise ValueError("origem_coorte inválido em pelo menos um município.")
    if not registry["nivel_evidencia"].isin(NIVEL_EVIDENCIA_VALIDO).all():
        raise ValueError("nivel_evidencia inválido em pelo menos um município.")


def build_status_crosstab(registry: pd.DataFrame) -> pd.DataFrame:
    """Gera a tabela cruzando status populacional, elegibilidade temporal,
    candidatura à amostra principal, validação institucional e revisão
    prioritária — para uso na documentação, sempre a partir do cadastro atual
    (nunca números manuais congelados em texto).
    """
    table = registry.groupby(
        [
            "status_populacao_causal", "elegivel_temporal_2pre_3pos", "elegivel_temporal_3pre_3pos",
            "candidato_amostra_principal", "validacao_institucional_individual", "revisao_prioritaria",
        ],
        dropna=False,
    ).size().reset_index(name="n_municipios")
    if int(table["n_municipios"].sum()) != len(registry):
        raise ValueError("Tabela de status não preserva o total de municípios do cadastro.")
    return table.sort_values(
        ["status_populacao_causal", "candidato_amostra_principal"], kind="stable"
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------

def print_summary(registry: pd.DataFrame) -> None:
    print("CADASTRO CAUSAL PRELIMINAR — EXPANSAO FASE II")
    print(f"Municípios oficiais: {len(registry)}")
    print(f"Candidatos à amostra principal: {int(registry['candidato_amostra_principal'].sum())}")
    print(f"Excluídos da população causal principal: {int(registry['status_populacao_causal'].eq('excluido_principal').sum())}")
    print(f"Especiais/estimando: {int(registry['status_populacao_causal'].eq('especial_estimando').sum())}")
    print(f"Sob revisão (status): {int(registry['status_populacao_causal'].eq('sob_revisao').sum())}")
    print(f"Com ressalva: {int(registry['status_populacao_causal'].eq('candidato_com_ressalva').sum())}")
    print(f"Institucionalmente inelegíveis pela janela: {int(registry['status_populacao_causal'].eq('institucional_inelegivel_janelas').sum())}")
    print(f"Revisão prioritária (flag): {int(registry['revisao_prioritaria'].sum())}")
    print(f"Validação institucional individual: {int(registry['validacao_institucional_individual'].sum())}")
    print(f"Elegíveis 2 pré / 3 pós: {int(registry['elegivel_temporal_2pre_3pos'].sum())}")
    print(f"Elegíveis 3 pré / 3 pós: {int(registry['elegivel_temporal_3pre_3pos'].sum())}")
    print(f"pode_ser_controle=true: {int(registry['pode_ser_controle'].sum())} (deve ser 0)")
    print("Coortes candidatas (candidato_amostra_principal apenas):")
    principais = registry.loc[registry["candidato_amostra_principal"], "ano_coorte_candidata"]
    print(principais.dropna().astype(int).value_counts().sort_index().to_string() or "  nenhuma")
    print("Municípios fora da amostra principal:")
    fora = registry[~registry["candidato_amostra_principal"]]
    for row in fora.itertuples(index=False):
        print(f"  {row.municipio}/{row.uf} ({row.codigo_municipio_ibge}): {row.motivo_exclusao_principal}")


def main() -> None:
    fase_ii = auditoria.read_processed_parquet(FASE_II_PATH)
    painel = auditoria.read_processed_parquet(PAINEL_PATH)
    exceptions = load_exceptions(EXCEPTIONS_PATH)
    registry = build_causal_registry(fase_ii, painel, exceptions)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    registry.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print_summary(registry)
    print(f"CSV gravado em: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
