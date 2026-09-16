"""constroi_painel_cempre.py
============================
Componentes técnicos do painel CEMPRE município-ano, 2007-2019.

Inclui os componentes da Fase 0 exigidos pelo gate
`PILOTO_TECNICO_APROVADO` — parser de `V`, normalização da long a partir da
resposta bruta da API SIDRA, reconciliação territorial, validação de chave
canônica/duplicidade e mecânica de requests/retries/cache —, a integração
territorial e o D1: plano nacional determinístico de requests e contrato
offline de completude.

NÃO executa extração nacional, NÃO persiste a long nacional, NÃO possui
manifesto ou orquestrador nacional, NÃO constrói wide nacional, NÃO faz merge
com o cadastro causal e NÃO estima efeitos.

Fonte: IBGE/SIDRA, Tabela 1685 (API `apisidra.ibge.gov.br/values`, sem
autenticação). `V` é sempre string e nunca é convertido silenciosamente.

Uso (piloto, escala mínima — ver `docs/data/AUDITORIA_PILOTO_CEMPRE.md`):
    python src/constroi_painel_cempre.py
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger("constroi_painel_cempre")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "data" / "raw" / "ibge" / "cempre" / "fixtures"
DIAGNOSTICS_DIR = ROOT / "outputs" / "diagnostics"
# Cache operacional de requests (seção 9) — NÃO é a fixture versionada.
# Conteúdo nacional futuro deste diretório não será versionado (.gitignore).
CACHE_DIR = ROOT / "data" / "raw" / "ibge" / "cempre" / "requests"
CALENDARIO_TERRITORIAL_PATH = (
    ROOT / "data" / "processed" / "calendario_territorial_municipios_2007_2019.parquet"
)

FONTE_TABELA = 1685
ANO_MIN, ANO_MAX = 2007, 2019

# Seção 2/8 da especificação — as sete variáveis confirmadas nos metadados
# oficiais da Tabela 1685. 708 é o outcome primário; 1606 é opcional/
# diagnóstica e sua ausência não bloqueia nenhum gate.
VARIAVEIS_ESPERADAS: set[int] = {706, 707, 708, 5944, 662, 1606, 10143}
VARIAVEL_OUTCOME_PRIMARIO = 708

STATUS_VALOR_API_COM_NUMERO = {
    "observado", "zero_real", "zero_arredondado", "zero_arredondado_negativo",
}

_RE_CODIGO_MUNICIPIO = re.compile(r"^\d{7}$")

# Bloqueador 1 (auditoria independente, ver AUDITORIA_PILOTO_CEMPRE.md):
# números NÃO-ZERO só são aceitos com PONTO decimal — o único formato
# comprovado pelas fixtures reais desta Fase 0 (ex.: "512.40", "213.96").
# Vírgula em um número não-zero (ex.: "1,234", "12,5") é ambígua — pode
# ser separador decimal ou de milhar — e não tem evidência empírica na API
# `apisidra`. Por isso NÃO é aceita para números genéricos; cai em
# `desconhecido` em vez de ser convertida silenciosamente. Isso é distinto
# dos literais de zero abaixo, que são estados discretos documentados pela
# fonte (seção 6.1), não números genéricos.
_RE_NUMERO = re.compile(r"^-?\d+(\.\d+)?$")

# Literais documentados pela fonte (seção 6.1 da especificação e p.4 do
# `liv101720.pdf`). A fonte descreve esses símbolos com vírgula decimal
# (convenção da publicação em PDF); a API `apisidra` observada nesta Fase 0
# usa PONTO como separador decimal para números reais (ex.: "512.40",
# "213.96" — ver fixtures). Não observamos, nesta Fase 0, nenhum valor
# arredondado a zero vinda ao vivo da API (ver AUDITORIA_PILOTO_CEMPRE.md).
# Por isso os dois separadores são aceitos defensivamente para ESTES
# LITERAIS EXATOS (conjunto fechado, comparação por igualdade de string —
# não por regex/parsing genérico), sem alterar a classificação de números
# não-zero (que seguem o formato realmente observado, com ponto).
_ZERO_ARREDONDADO_POSITIVO = {"0", "0,0", "0,00", "0.0", "0.00"}
_ZERO_ARREDONDADO_NEGATIVO = {"-0", "-0,0", "-0,00", "-0.0", "-0.00"}


# ---------------------------------------------------------------------------
# Parser de V (seção 6.1)
# ---------------------------------------------------------------------------


def parse_sidra_value(v_raw: str) -> tuple[str, float | None]:
    """Classifica o valor bruto `V` retornado pela API SIDRA.

    Retorna (status_valor_api, valor_numerico). `valor_numerico` só é
    preenchido para observado/zero_real/zero_arredondado/
    zero_arredondado_negativo; nulo nos demais casos. Símbolo/formato não
    previsto é classificado como `desconhecido` e nunca convertido
    silenciosamente em zero ou NA.
    """
    if v_raw is None:
        return "desconhecido", None

    v = v_raw.strip()

    if v == "-":
        return "zero_real", 0.0
    if v in _ZERO_ARREDONDADO_POSITIVO:
        return "zero_arredondado", 0.0
    if v in _ZERO_ARREDONDADO_NEGATIVO:
        return "zero_arredondado_negativo", 0.0
    if v == "x":
        return "sigilo", None
    if v == "..":
        return "nao_aplicavel", None
    if v == "...":
        return "indisponivel", None

    if _RE_NUMERO.fullmatch(v):
        valor = float(v)
        if valor == 0.0:
            # Zero numérico fora dos literais documentados acima (ex.:
            # "0.000") não é uma forma prevista pela fonte — bloqueia em
            # vez de presumir qual classe de zero seria.
            return "desconhecido", None
        return "observado", valor

    return "desconhecido", None


# ---------------------------------------------------------------------------
# normalize_long (seção 5)
# ---------------------------------------------------------------------------

_COLUNAS_LONG = [
    "codigo_municipio_ibge", "ano", "codigo_variavel_sidra",
    "municipio_fonte", "uf_fonte", "nome_variavel", "unidade",
    "valor_bruto", "valor_numerico", "status_valor_api",
    "fonte_tabela", "request_id", "data_extracao",
    "hash_resposta_raw", "versao_metadados", "observacao_status",
]


# Campos que uma observação real precisa ter para o parser/normalização
# conseguirem identificar com segurança município, variável, ano e valor
# (seção 7/8 do pedido de correção). Baseado exatamente nos campos
# presentes nas fixtures reais (data/raw/ibge/cempre/fixtures/).
_CAMPOS_OBRIGATORIOS_OBSERVACAO = {"D1C", "D2C", "D3C", "V"}


def _e_linha_de_cabecalho(row: dict[str, Any]) -> bool:
    # A API `apisidra` sempre retorna, como primeiro elemento da lista, um
    # dicionário de RÓTULOS (não uma observação). Identificamos pela
    # assinatura literal desse cabeçalho, observada em todas as fixtures
    # reais desta Fase 0: V == "Valor" e D1C == "Município (Código)".
    # Isso é deliberadamente mais estrito do que checar "D2C não numérico"
    # (heurística anterior): uma observação real com campo ausente/corrompido
    # não deve ser silenciosamente confundida com o cabeçalho — ela deve
    # falhar a validação de schema (`validate_sidra_payload`), não desaparecer.
    return row.get("V") == "Valor" and row.get("D1C") == "Município (Código)"


def validate_sidra_payload(payload: Any) -> tuple[bool, str | None]:
    """Valida a forma estrutural do payload bruto retornado por
    `apisidra.ibge.gov.br/values` (Bloqueador 2 — contrato explícito do
    payload SIDRA), ANTES de qualquer tentativa de normalização.

    Baseado exatamente nos campos observados nas fixtures reais desta Fase
    0 — não presume nenhum contrato diferente do que foi observado.
    Retorna (valido, motivo). `motivo` é `None` quando válido e uma
    mensagem específica o suficiente para diagnóstico quando inválido.
    """
    if not isinstance(payload, list):
        return False, f"payload não é uma lista (tipo recebido: {type(payload).__name__})"

    if len(payload) == 0:
        return False, "payload é uma lista vazia ([]) — não é sucesso para um request obrigatório do piloto"

    observacoes_validas = 0
    for indice, item in enumerate(payload):
        if not isinstance(item, dict):
            return False, f"item no índice {indice} do payload não é um dicionário (tipo: {type(item).__name__})"

        if _e_linha_de_cabecalho(item):
            continue

        campos_faltantes = _CAMPOS_OBRIGATORIOS_OBSERVACAO - item.keys()
        if campos_faltantes:
            return False, (
                f"observação no índice {indice} não tem campo(s) obrigatório(s) "
                f"{sorted(campos_faltantes)} — schema não permite identificar "
                f"município/variável/ano/V com segurança"
            )
        observacoes_validas += 1

    if observacoes_validas == 0:
        return False, "payload não contém nenhuma observação real após o cabeçalho"

    return True, None


def normalize_long(
    raw_rows: list[dict[str, Any]],
    request_id: str,
    fonte_tabela: int = FONTE_TABELA,
    data_extracao: str | None = None,
    hash_resposta_raw: str | None = None,
    versao_metadados: str | None = None,
) -> pd.DataFrame:
    """Traduz linhas brutas da API SIDRA (`values/t/...`) para a long
    normalizada da fonte (seção 5). Levanta `ValueError` para código
    municipal, ano ou variável fora do esperado — essas são falhas de
    schema, não estados a preservar como `desconhecido`.
    """
    valido, motivo = validate_sidra_payload(raw_rows)
    if not valido:
        raise ValueError(f"payload SIDRA estruturalmente inválido: {motivo}")

    linhas: list[dict[str, Any]] = []
    for row in raw_rows:
        if _e_linha_de_cabecalho(row):
            continue

        codigo = str(row["D1C"]).strip()
        if not _RE_CODIGO_MUNICIPIO.match(codigo):
            raise ValueError(f"código municipal inválido em D1C: {codigo!r}")

        ano = int(row["D3C"])
        if not (ANO_MIN <= ano <= ANO_MAX):
            raise ValueError(f"ano fora da janela {ANO_MIN}-{ANO_MAX}: {ano}")

        variavel = int(row["D2C"])
        if variavel not in VARIAVEIS_ESPERADAS:
            raise ValueError(f"código de variável não esperado: {variavel}")

        valor_bruto = str(row["V"])
        status_valor_api, valor_numerico = parse_sidra_value(valor_bruto)

        linhas.append({
            "codigo_municipio_ibge": codigo,
            "ano": ano,
            "codigo_variavel_sidra": variavel,
            "municipio_fonte": row.get("D1N"),
            "uf_fonte": None,
            "nome_variavel": row.get("D2N"),
            "unidade": row.get("MN"),
            "valor_bruto": valor_bruto,
            "valor_numerico": valor_numerico,
            "status_valor_api": status_valor_api,
            "fonte_tabela": fonte_tabela,
            "request_id": request_id,
            "data_extracao": data_extracao,
            "hash_resposta_raw": hash_resposta_raw,
            "versao_metadados": versao_metadados,
            "observacao_status": None if status_valor_api != "desconhecido" else "símbolo não reconhecido",
        })

    return pd.DataFrame(linhas, columns=_COLUNAS_LONG)


_COLUNAS_CALENDARIO_OBRIGATORIAS = {
    "codigo_municipio_ibge", "ano", "municipio_existia_no_ano",
}
_CHAVE_CALENDARIO = ["codigo_municipio_ibge", "ano"]


def load_calendar_territorial(caminho: str | Path | None = None) -> pd.DataFrame:
    """Carrega e valida o calendário territorial oficial município-ano.

    O caminho padrão é o Parquet nacional produzido pela frente territorial.
    Um caminho explícito permite testes com calendários sintéticos pequenos.
    """
    caminho_calendario = Path(caminho) if caminho is not None else CALENDARIO_TERRITORIAL_PATH
    if not caminho_calendario.exists():
        raise FileNotFoundError(f"calendário territorial não encontrado: {caminho_calendario}")
    if caminho_calendario.suffix.lower() != ".parquet":
        raise ValueError(
            f"formato não suportado para calendário territorial: {caminho_calendario.suffix!r}; "
            "esperado '.parquet'"
        )

    calendario = pd.read_parquet(caminho_calendario)
    colunas_ausentes = sorted(_COLUNAS_CALENDARIO_OBRIGATORIAS - set(calendario.columns))
    if colunas_ausentes:
        raise ValueError(f"coluna(s) obrigatória(s) ausente(s) no calendário territorial: {colunas_ausentes}")

    if calendario[list(_COLUNAS_CALENDARIO_OBRIGATORIAS)].isna().any().any():
        raise ValueError("calendário territorial tem nulo em coluna estrutural obrigatória")

    calendario = calendario.copy()
    calendario["codigo_municipio_ibge"] = calendario["codigo_municipio_ibge"].astype("string").str.strip()
    codigos_validos = calendario["codigo_municipio_ibge"].str.fullmatch(_RE_CODIGO_MUNICIPIO)
    if not bool(codigos_validos.all()):
        codigos_invalidos = calendario.loc[~codigos_validos, "codigo_municipio_ibge"].tolist()
        raise ValueError(f"código municipal inválido no calendário territorial: {codigos_invalidos[:5]}")

    if not pd.api.types.is_integer_dtype(calendario["ano"]):
        raise ValueError("ano inválido no calendário territorial: deve ser inteiro")
    anos_validos = calendario["ano"].between(ANO_MIN, ANO_MAX)
    if not bool(anos_validos.all()):
        anos_invalidos = calendario.loc[~anos_validos, "ano"].tolist()
        raise ValueError(f"ano inválido no calendário territorial: {anos_invalidos[:5]}")

    if not pd.api.types.is_bool_dtype(calendario["municipio_existia_no_ano"]):
        raise ValueError("municipio_existia_no_ano deve ser booleano no calendário territorial")

    duplicadas = calendario.duplicated(_CHAVE_CALENDARIO, keep=False)
    if bool(duplicadas.any()):
        chaves_duplicadas = calendario.loc[duplicadas, _CHAVE_CALENDARIO].head().to_dict("records")
        raise ValueError(f"chave duplicada no calendário territorial: {chaves_duplicadas}")

    return calendario


def reconcile_territorial(df_long: pd.DataFrame, calendario: pd.DataFrame) -> pd.DataFrame:
    """Cruza `(codigo_municipio_ibge, ano)` com o calendário territorial e
    deriva `status_territorial` (seção 6.2) e `incompatibilidade_territorial`
    (seção 6.3), sem alterar `valor_bruto`, `valor_numerico` ou
    `status_valor_api`.
    """
    df = df_long.copy()
    cal = calendario[["codigo_municipio_ibge", "ano", "municipio_existia_no_ano"]]
    df = df.merge(cal, on=["codigo_municipio_ibge", "ano"], how="left")

    def _status_territorial(existia: Any) -> str:
        if pd.isna(existia):
            return "indeterminado"
        return "existia_no_ano" if bool(existia) else "nao_existia_no_ano"

    df["status_territorial"] = df["municipio_existia_no_ano"].apply(_status_territorial)
    df["incompatibilidade_territorial"] = (
        (df["status_territorial"] == "nao_existia_no_ano")
        & (df["status_valor_api"].isin(STATUS_VALOR_API_COM_NUMERO))
    )
    df = df.drop(columns=["municipio_existia_no_ano"])
    return df


# ---------------------------------------------------------------------------
# validate_long (seção 11) — chave canônica e duplicidade entre request_id
# ---------------------------------------------------------------------------

_CHAVE_CANONICA = ["codigo_municipio_ibge", "ano", "codigo_variavel_sidra"]


def validate_long(df_long: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Valida a long: unicidade da chave canônica (resolvendo duplicidade
    consistente entre `request_id` distintos, seção 5/10) e ausência de
    `status_valor_api == desconhecido`. Levanta `ValueError` se a mesma
    chave aparecer com `valor_bruto`/`status_valor_api` inconsistentes
    entre lotes — isso nunca é resolvido silenciosamente.
    """
    relatorio: dict[str, Any] = {
        "linhas_totais_antes": len(df_long),
        "duplicatas_resolvidas": [],
        "motivos_bloqueio": [],
        "aprovado": True,
    }

    grupos = df_long.groupby(_CHAVE_CANONICA, dropna=False)
    linhas_resolvidas = []
    for chave, grupo in grupos:
        if len(grupo) > 1:
            consistente = (
                grupo["valor_bruto"].nunique(dropna=False) == 1
                and grupo["status_valor_api"].nunique(dropna=False) == 1
            )
            if not consistente:
                raise ValueError(
                    f"duplicidade inconsistente da chave canônica {dict(zip(_CHAVE_CANONICA, chave))}: "
                    f"valor_bruto={grupo['valor_bruto'].unique().tolist()}, "
                    f"status_valor_api={grupo['status_valor_api'].unique().tolist()}"
                )
            linha_retida = grupo.sort_values("request_id").iloc[[0]]
            relatorio["duplicatas_resolvidas"].append({
                "chave": dict(zip(_CHAVE_CANONICA, chave)),
                "request_ids": sorted(grupo["request_id"].tolist()),
            })
            linhas_resolvidas.append(linha_retida)
        else:
            linhas_resolvidas.append(grupo)

    df_validado = pd.concat(linhas_resolvidas, ignore_index=True) if linhas_resolvidas else df_long.iloc[0:0]

    n_desconhecido = int((df_validado["status_valor_api"] == "desconhecido").sum())
    if n_desconhecido > 0:
        relatorio["aprovado"] = False
        relatorio["motivos_bloqueio"].append(
            f"{n_desconhecido} linha(s) com status_valor_api = desconhecido (símbolo/formato não previsto)"
        )

    relatorio["linhas_totais_depois"] = len(df_validado)
    return df_validado, relatorio


# ---------------------------------------------------------------------------
# build_requests / fetch_request (seção 9)
# ---------------------------------------------------------------------------


def _territorio_path(territorio: dict[str, str]) -> str:
    if territorio["tipo"] == "municipio":
        return f"n6/{territorio['codigo']}"
    if territorio["tipo"] == "uf":
        return f"n6/in%20n3%20{territorio['codigo']}"
    raise ValueError(f"tipo de território não suportado: {territorio['tipo']!r}")


def build_requests(
    anos: list[int],
    territorios: list[dict[str, str]],
    variaveis: list[int],
    fonte_tabela: int = FONTE_TABELA,
) -> list[dict[str, Any]]:
    """Monta as requisições candidatas (estratégia ano × UF/município ×
    grupo de variáveis, seção 9), com `request_id` determinístico (hash
    dos parâmetros — não depende de ordem de execução nem de horário).
    """
    variaveis_ordenadas = sorted(variaveis)
    requests_spec: list[dict[str, Any]] = []
    for territorio in territorios:
        caminho_territorio = _territorio_path(territorio)
        for ano in anos:
            chave = f"{fonte_tabela}|{caminho_territorio}|{','.join(map(str, variaveis_ordenadas))}|{ano}"
            request_id = hashlib.sha256(chave.encode("utf-8")).hexdigest()[:16]
            url = (
                f"https://apisidra.ibge.gov.br/values/t/{fonte_tabela}/{caminho_territorio}"
                f"/v/{','.join(map(str, variaveis_ordenadas))}/p/{ano}"
            )
            requests_spec.append({
                "request_id": request_id,
                "url": url,
                "params": {},
                "ano": ano,
                "territorio": territorio,
                "variaveis": variaveis_ordenadas,
                "fonte_tabela": fonte_tabela,
            })
    return requests_spec


# ---------------------------------------------------------------------------
# Plano nacional de requests (bloco 1 da infraestrutura de extração
# nacional). Gera, de forma determinística e offline, o conjunto completo
# de lotes esperados para a estratégia vigente (ano × UF × grupo de
# variáveis, seção 9 da especificação). NÃO chama rede, NÃO extrai dados —
# apenas monta e valida o plano e compara com resultados já obtidos em
# outro momento (execução real é responsabilidade de outro módulo/tarefa).
# ---------------------------------------------------------------------------

_COLUNAS_UF_CALENDARIO = {"uf_codigo", "uf_sigla"}
_RE_UF_CODIGO = re.compile(r"^\d{2}$")
_RE_UF_SIGLA = re.compile(r"^[A-Z]{2}$")


def uf_list_from_calendario(calendario: pd.DataFrame) -> list[dict[str, str]]:
    """Deriva a lista oficial de UFs (território de segmentação nacional)
    a partir do calendário territorial já validado por
    `load_calendar_territorial` — não de nomes de município, não de uma
    lista digitada à parte. Isso garante que a segmentação nacional usa
    exatamente as mesmas UFs que a reconciliação territorial já usa.

    Falha explicitamente se `uf_codigo`/`uf_sigla` estiverem ausentes,
    inconsistentes entre si (mesmo código com siglas diferentes ou
    vice-versa) ou com formato de código inválido (2 dígitos).
    """
    colunas_ausentes = sorted(_COLUNAS_UF_CALENDARIO - set(calendario.columns))
    if colunas_ausentes:
        raise ValueError(
            f"calendário territorial sem coluna(s) necessária(s) para derivar UFs: {colunas_ausentes}"
        )

    ufs = calendario[["uf_codigo", "uf_sigla"]].dropna().drop_duplicates()

    siglas_por_codigo = ufs.groupby("uf_codigo")["uf_sigla"].nunique()
    inconsistentes = siglas_por_codigo[siglas_por_codigo > 1]
    if not inconsistentes.empty:
        raise ValueError(
            f"uf_codigo associado a mais de uma uf_sigla no calendário territorial: {inconsistentes.index.tolist()}"
        )
    codigos_por_sigla = ufs.groupby("uf_sigla")["uf_codigo"].nunique()
    inconsistentes_sigla = codigos_por_sigla[codigos_por_sigla > 1]
    if not inconsistentes_sigla.empty:
        raise ValueError(
            f"uf_sigla associada a mais de um uf_codigo no calendário territorial: {inconsistentes_sigla.index.tolist()}"
        )

    codigos_invalidos = [
        codigo for codigo in ufs["uf_codigo"].astype(str) if not _RE_UF_CODIGO.fullmatch(codigo)
    ]
    if codigos_invalidos:
        raise ValueError(f"uf_codigo com formato inválido no calendário territorial (esperado 2 dígitos): {codigos_invalidos}")

    return [
        {"tipo": "uf", "codigo": str(linha.uf_codigo), "sigla": str(linha.uf_sigla)}
        for linha in ufs.sort_values("uf_codigo").itertuples()
    ]


def _validate_ufs_esperadas(ufs_esperadas: list[dict[str, str]]) -> list[dict[str, str]]:
    """Valida a referência EXTERNA de UFs do contrato nacional.

    A referência não pode ser derivada do plano avaliado: é ela que define
    a cobertura contratada. O contrato vigente exige as 27 UFs brasileiras,
    com código e sigla únicos e consistentes. O retorno ordenado impede que
    a ordem fornecida altere a validação lógica do plano.
    """
    if len(ufs_esperadas) != 27:
        raise ValueError(
            f"referência externa de UFs deve conter exatamente 27 UFs; recebeu {len(ufs_esperadas)}"
        )

    ufs_normalizadas: list[dict[str, str]] = []
    for uf in ufs_esperadas:
        if not isinstance(uf, dict) or uf.get("tipo") != "uf":
            raise ValueError(f"UF inválida na referência externa: {uf!r}")
        codigo = str(uf.get("codigo", ""))
        sigla = str(uf.get("sigla", ""))
        if not _RE_UF_CODIGO.fullmatch(codigo):
            raise ValueError(f"código de UF inválido na referência externa: {codigo!r}")
        if not _RE_UF_SIGLA.fullmatch(sigla):
            raise ValueError(f"sigla de UF inválida na referência externa: {sigla!r}")
        ufs_normalizadas.append({"tipo": "uf", "codigo": codigo, "sigla": sigla})

    codigos = [uf["codigo"] for uf in ufs_normalizadas]
    if len(codigos) != len(set(codigos)):
        raise ValueError("código de UF duplicado na referência externa")
    siglas = [uf["sigla"] for uf in ufs_normalizadas]
    if len(siglas) != len(set(siglas)):
        raise ValueError("sigla de UF duplicada na referência externa")

    return sorted(ufs_normalizadas, key=lambda uf: uf["codigo"])


def build_national_request_plan(
    calendario: pd.DataFrame | None = None,
    anos: list[int] | None = None,
    variaveis: set[int] | list[int] | None = None,
    fonte_tabela: int = FONTE_TABELA,
) -> list[dict[str, Any]]:
    """Gera deterministicamente o plano nacional completo de requests
    (seção 9 da especificação): ano × UF × grupo de variáveis, cobrindo
    2007-2019 e o território nacional segmentado por UF.

    Reutiliza `build_requests` (não duplica a lógica de `request_id`/URL).
    A origem das UFs é o calendário territorial oficial já validado por
    `load_calendar_territorial` (via `uf_list_from_calendario`), nunca uma
    lista paralela. Sem `calendario` explícito, carrega o Parquet nacional
    padrão (`CALENDARIO_TERRITORIAL_PATH`) — uso apenas para gerar o plano,
    sem qualquer chamada de rede.

    `anos`/`variaveis` têm como padrão a janela e o conjunto contratados
    (`ANO_MIN..ANO_MAX`, `VARIAVEIS_ESPERADAS`); passar valores explícitos
    serve para testes ou planos parciais deliberados, nunca para hardcodar
    o total esperado — o total é sempre derivado de `len(anos) *
    len(territorios)`.
    """
    if calendario is None:
        calendario = load_calendar_territorial()

    anos_plano = sorted(range(ANO_MIN, ANO_MAX + 1)) if anos is None else sorted(anos)
    variaveis_plano = sorted(VARIAVEIS_ESPERADAS if variaveis is None else variaveis)
    territorios_plano = _validate_ufs_esperadas(uf_list_from_calendario(calendario))
    plano = build_requests(
        anos=anos_plano,
        territorios=territorios_plano,
        variaveis=variaveis_plano,
        fonte_tabela=fonte_tabela,
    )
    validate_national_request_plan(
        plano,
        ufs_esperadas=territorios_plano,
        anos_esperados=anos_plano,
        variaveis_esperadas=variaveis_plano,
    )
    return plano


def validate_national_request_plan(
    plano: list[dict[str, Any]],
    ufs_esperadas: list[dict[str, str]],
    anos_esperados: list[int] | None = None,
    variaveis_esperadas: set[int] | list[int] | None = None,
) -> dict[str, Any]:
    """Valida explicitamente o plano nacional de requests antes de qualquer
    execução. Levanta `ValueError` (nunca falha silenciosa) se o plano
    estiver malformado. Não chama rede.

    Verifica o produto cartesiano contratado entre uma referência EXTERNA
    de UFs, anos e um grupo contratado de variáveis: `request_id` não nulo
    e único; combinação lógica `(uf, ano)` única; anos dentro de
    2007-2019; UFs e siglas aderentes à referência; grupo de variáveis
    igual ao contratado; e nenhuma combinação esperada ausente ou
    inesperada.

    Retorna um relatório com o total esperado derivado dos componentes do
    próprio plano (nunca um número fixo hardcoded).
    """
    ufs_esperadas_normalizadas = _validate_ufs_esperadas(ufs_esperadas)
    anos_esperados_normalizados = (
        sorted(range(ANO_MIN, ANO_MAX + 1)) if anos_esperados is None else sorted(anos_esperados)
    )
    if not anos_esperados_normalizados:
        raise ValueError("referência de anos esperados vazia")
    if any(not isinstance(ano, int) or not (ANO_MIN <= ano <= ANO_MAX) for ano in anos_esperados_normalizados):
        raise ValueError(f"ano fora do contrato {ANO_MIN}-{ANO_MAX} na referência externa")
    variaveis_esperadas_normalizadas = sorted(
        VARIAVEIS_ESPERADAS if variaveis_esperadas is None else variaveis_esperadas
    )
    if variaveis_esperadas_normalizadas != sorted(VARIAVEIS_ESPERADAS):
        raise ValueError("grupo de variáveis da referência diverge do contrato CEMPRE")
    if not plano:
        raise ValueError("plano nacional de requests vazio")

    ids = [item.get("request_id") for item in plano]
    if any(not rid for rid in ids):
        raise ValueError("request_id nulo/vazio encontrado no plano nacional")
    if len(ids) != len(set(ids)):
        duplicados = sorted({rid for rid in ids if ids.count(rid) > 1})
        raise ValueError(f"request_id duplicado no plano nacional: {duplicados[:5]}")

    ufs_por_codigo = {uf["codigo"]: uf for uf in ufs_esperadas_normalizadas}
    combinacoes: set[tuple[str, int]] = set()
    for item in plano:
        ano = item.get("ano")
        if not isinstance(ano, int) or not (ANO_MIN <= ano <= ANO_MAX):
            raise ValueError(f"ano fora da janela {ANO_MIN}-{ANO_MAX} no plano nacional: {ano!r}")

        territorio = item.get("territorio") or {}
        if territorio.get("tipo") != "uf":
            raise ValueError(f"território inválido no plano nacional (esperado tipo 'uf'): {territorio!r}")
        codigo_uf = str(territorio.get("codigo"))
        if not _RE_UF_CODIGO.fullmatch(codigo_uf):
            raise ValueError(f"código de UF inválido no plano nacional: {codigo_uf!r}")
        if codigo_uf not in ufs_por_codigo:
            raise ValueError(f"UF fora do contrato nacional: {codigo_uf!r}")
        if territorio.get("sigla") != ufs_por_codigo[codigo_uf]["sigla"]:
            raise ValueError(f"sigla de UF divergente do contrato para código {codigo_uf!r}")

        variaveis_item = sorted(item.get("variaveis") or [])
        if variaveis_item != variaveis_esperadas_normalizadas:
            raise ValueError(
                f"grupo de variáveis inesperado no request_id={item.get('request_id')}: {variaveis_item}"
            )

        chave = (codigo_uf, ano)
        if chave in combinacoes:
            raise ValueError(f"combinação (UF, ano) duplicada no plano nacional: {chave}")
        combinacoes.add(chave)

    combinacoes_esperadas = {
        (uf["codigo"], ano) for uf in ufs_esperadas_normalizadas for ano in anos_esperados_normalizados
    }
    ausentes = sorted(combinacoes_esperadas - combinacoes)
    if ausentes:
        raise ValueError(f"combinação(ões) (UF, ano) ausente(s) no plano nacional: {ausentes[:5]}")
    inesperadas = sorted(combinacoes - combinacoes_esperadas)
    if inesperadas:
        raise ValueError(f"combinação(ões) (UF, ano) inesperada(s) no plano nacional: {inesperadas[:5]}")

    n_grupos_variaveis = 1
    total_esperado = len(ufs_esperadas_normalizadas) * len(anos_esperados_normalizados) * n_grupos_variaveis
    if total_esperado != len(plano):
        raise ValueError(
            f"total de requests do plano nacional ({len(plano)}) diverge do total derivado "
            f"({total_esperado} = {len(ufs_esperadas_normalizadas)} UFs × "
            f"{len(anos_esperados_normalizados)} anos × {n_grupos_variaveis} grupo de variáveis)"
        )

    return {
        "total_requests_esperados": total_esperado,
        "n_ufs": len(ufs_esperadas_normalizadas),
        "n_anos": len(anos_esperados_normalizados),
        "n_grupos_variaveis": n_grupos_variaveis,
        "anos": anos_esperados_normalizados,
        "ufs": [uf["codigo"] for uf in ufs_esperadas_normalizadas],
        "variaveis": variaveis_esperadas_normalizadas,
        "aprovado": True,
    }


def _resultado_e_sucesso(resultado: dict[str, Any]) -> bool:
    """Um resultado é sucesso somente se não houver erro registrado e o
    payload estiver presente — independentemente de ter vindo de cache
    (`de_cache=True`) ou de rede. Cache hit válido é sucesso; qualquer
    `erro` não-nulo ou `resultado` ausente é falha, nunca completude.
    """
    return resultado.get("erro") is None and resultado.get("resultado") is not None


def avalia_completude_plano(
    plano: list[dict[str, Any]],
    resultados: list[dict[str, Any]],
) -> dict[str, Any]:
    """Contrato de completude (bloco 1, seção 5): compara PURAMENTE OFFLINE
    o plano esperado com os resultados já obtidos (formato de
    `fetch_request`, seção 9 — chave `request_id`, `erro`, `resultado`,
    `de_cache`). Não chama rede; não executa nenhum request.

    Detecta lote faltante (`request_ids_ausentes`), resultado que não
    corresponde a nenhum lote do plano (`request_ids_inesperados`) e
    `request_id` com mais de um resultado (`request_ids_duplicados` —
    ambíguo qual é o válido, portanto nunca contado como sucesso).

    `completo=True` somente quando todos os lotes esperados têm exatamente
    um resultado válido (`_resultado_e_sucesso`) e não há ausência,
    duplicidade nem resultado inesperado. Falha HTTP/payload/schema
    (resultado com `erro` preenchido) sempre impede completude.
    """
    ids_esperados = [item["request_id"] for item in plano]
    set_esperados = set(ids_esperados)
    if len(ids_esperados) != len(set_esperados):
        raise ValueError("plano de requests com request_id duplicado — valide o plano antes de avaliar completude")

    resultados_por_id: dict[str, list[dict[str, Any]]] = {}
    resultados_malformados: list[dict[str, Any]] = []
    for indice, resultado in enumerate(resultados):
        if not isinstance(resultado, dict):
            resultados_malformados.append({"indice": indice, "motivo": "resultado não é dicionário"})
            continue
        request_id = resultado.get("request_id")
        if not request_id:
            resultados_malformados.append({"indice": indice, "motivo": "request_id ausente ou vazio"})
            continue
        resultados_por_id.setdefault(request_id, []).append(resultado)

    ids_recebidos = set(resultados_por_id)
    request_ids_ausentes = sorted(set_esperados - ids_recebidos)
    request_ids_inesperados = sorted(ids_recebidos - set_esperados)
    request_ids_duplicados = sorted(rid for rid, entradas in resultados_por_id.items() if len(entradas) > 1)

    n_sucessos = 0
    n_falhas = 0
    for rid in sorted(set_esperados & ids_recebidos):
        entradas = resultados_por_id[rid]
        if len(entradas) != 1:
            # Duplicidade é ambígua — nunca decidimos arbitrariamente qual
            # resultado é o válido; conta como falha de completude.
            n_falhas += 1
            continue
        if _resultado_e_sucesso(entradas[0]):
            n_sucessos += 1
        else:
            n_falhas += 1

    completo = (
        not request_ids_ausentes
        and not request_ids_inesperados
        and not request_ids_duplicados
        and not resultados_malformados
        and n_falhas == 0
        and n_sucessos == len(set_esperados)
    )

    return {
        "n_requests_esperados": len(set_esperados),
        "n_requests_recebidos": len(resultados),
        "n_sucessos": n_sucessos,
        "n_falhas": n_falhas,
        "request_ids_ausentes": request_ids_ausentes,
        "request_ids_inesperados": request_ids_inesperados,
        "request_ids_duplicados": request_ids_duplicados,
        "resultados_malformados": resultados_malformados,
        "completo": completo,
    }


# ---------------------------------------------------------------------------
# Cache operacional por request_id (Bloqueador 3) — DISTINTO da fixture
# versionada em FIXTURES_DIR. O cache é um mecanismo de reprocessamento
# local (não versionado; ver .gitignore), não uma amostra congelada para
# teste de schema.
# ---------------------------------------------------------------------------


def cache_path_for_request(request_id: str, cache_dir: Path = CACHE_DIR) -> Path:
    """Caminho determinístico do arquivo de cache para este `request_id`."""
    return Path(cache_dir) / f"{request_id}.json"


def save_cached_request(
    request_id: str,
    texto_resposta_raw: str,
    hash_resposta_raw: str,
    cache_dir: Path = CACHE_DIR,
) -> Path:
    """Persiste a resposta bruta (texto exato + hash) em disco, indexada
    por `request_id`. Salva o TEXTO, não o JSON já parseado, para que a
    integridade possa ser reverificada byte a byte no carregamento.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    caminho = cache_path_for_request(request_id, cache_dir)
    envelope = {
        "request_id": request_id,
        "hash_resposta_raw": hash_resposta_raw,
        "texto_resposta_raw": texto_resposta_raw,
    }
    caminho.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    return caminho


def load_cached_request(request_id: str, cache_dir: Path = CACHE_DIR) -> dict[str, Any] | None:
    """Carrega a resposta em cache para `request_id`. Retorna `None` em
    cache miss (arquivo inexistente). Levanta `ValueError` se o cache
    existir mas estiver corrompido (JSON do envelope inválido, campos
    ausentes, hash não confere ou texto da resposta não é JSON válido) —
    corrupção NUNCA é aceita silenciosamente nem cai de volta para a rede
    automaticamente: quem chama decide o que fazer com o erro.
    """
    caminho = cache_path_for_request(request_id, cache_dir)
    if not caminho.exists():
        return None

    texto_envelope = caminho.read_text(encoding="utf-8")
    try:
        envelope = json.loads(texto_envelope)
    except json.JSONDecodeError as exc:
        raise ValueError(f"cache corrompido para request_id={request_id} ({caminho}): envelope não é JSON válido: {exc}") from exc

    if not isinstance(envelope, dict) or not {"texto_resposta_raw", "hash_resposta_raw"} <= envelope.keys():
        raise ValueError(f"cache corrompido para request_id={request_id} ({caminho}): envelope malformado")

    texto_resposta = envelope["texto_resposta_raw"]
    hash_esperado = envelope["hash_resposta_raw"]
    hash_real = hashlib.sha256(texto_resposta.encode("utf-8")).hexdigest()
    if hash_real != hash_esperado:
        raise ValueError(f"cache corrompido para request_id={request_id} ({caminho}): hash não confere")

    try:
        dados = json.loads(texto_resposta)
    except json.JSONDecodeError as exc:
        raise ValueError(f"cache corrompido para request_id={request_id} ({caminho}): payload não é JSON válido: {exc}") from exc

    return {"resultado": dados, "hash_resposta_raw": hash_esperado, "tamanho": len(texto_resposta)}


def _resultado_a_partir_do_cache(
    request_id: str,
    url: str | None,
    cache_dir: Path,
) -> tuple[dict[str, Any] | None, bool]:
    """Monta um resultado no contrato de `fetch_request` (e do D2)
    exclusivamente a partir do cache, sem NUNCA chamar rede.

    Retorna `(resultado, ausente)`. `ausente=True` significa cache miss
    (arquivo não existe) — nesse caso `resultado` é `None` e cabe ao
    chamador decidir o que fazer (`fetch_request` cai para rede;
    `load_results_from_cache`/D2 nunca cai, e trata isso como falha
    explícita). Quando `ausente=False`, `resultado` já é o resultado final
    (sucesso, cache corrompido ou payload com schema inválido), sempre com
    `de_cache=True` e nunca decidido silenciosamente.
    """
    try:
        em_cache = load_cached_request(request_id, cache_dir)
    except ValueError as exc:
        logger.error("request_id=%s cache corrompido: %s", request_id, exc)
        return {
            "request_id": request_id, "url": url, "tentativas": 0,
            "status_http": None, "tamanho": None, "hash_resposta_raw": None,
            "resultado": None, "erro": str(exc), "de_cache": True,
        }, False

    if em_cache is None:
        return None, True

    valido, motivo = validate_sidra_payload(em_cache["resultado"])
    if not valido:
        logger.error("request_id=%s payload em cache é inválido: %s", request_id, motivo)
        return {
            "request_id": request_id, "url": url, "tentativas": 0,
            "status_http": None, "tamanho": em_cache["tamanho"],
            "hash_resposta_raw": em_cache["hash_resposta_raw"],
            "resultado": None, "erro": f"payload em cache inválido: {motivo}", "de_cache": True,
        }, False

    logger.info("request_id=%s cache hit — nenhuma chamada de rede", request_id)
    return {
        "request_id": request_id, "url": url, "tentativas": 0,
        "status_http": 200, "tamanho": em_cache["tamanho"],
        "hash_resposta_raw": em_cache["hash_resposta_raw"],
        "resultado": em_cache["resultado"], "erro": None, "de_cache": True,
    }, False


def fetch_request(
    spec: dict[str, Any],
    session: requests.Session | None = None,
    timeout: float = 15.0,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Executa uma requisição com retries limitados e backoff exponencial.

    Só é sucesso: HTTP 200 + JSON válido + payload estruturalmente válido
    (`validate_sidra_payload`, seção 9). `[]` e payload com schema alterado
    NUNCA são sucesso. Uma falha de schema (payload bem formado mas com
    forma errada) é tratada como permanente e falha imediatamente, sem
    gastar retries (retry não conserta uma mudança estrutural); já um erro
    de decodificação JSON (resposta truncada/corrompida em trânsito) ainda
    é tentado novamente, por ser potencialmente transitório. Falha
    persistente retorna `resultado=None` — o chamador deve tratar isso como
    lote obrigatório falho, nunca como extração completa.

    Se `cache_dir` for informado: cache hit não chama rede nenhuma (nem
    para validar) e cache corrompido/com schema inválido falha
    explicitamente sem tentar a rede (ver `load_cached_request`).
    """
    if cache_dir is not None:
        resultado_cache, ausente = _resultado_a_partir_do_cache(spec["request_id"], spec["url"], cache_dir)
        if not ausente:
            return resultado_cache

    sess = session or requests
    ultima_resposta_http: int | None = None
    ultimo_erro: str | None = None

    for tentativa in range(1, max_retries + 1):
        inicio = time.monotonic()
        try:
            resp = sess.get(spec["url"], params=spec.get("params", {}), timeout=timeout)
        except Exception as exc:  # noqa: BLE001 — falha de rede é um resultado válido a registrar, não um bug
            ultimo_erro = str(exc)
            logger.warning("request_id=%s tentativa=%d falhou: %s", spec["request_id"], tentativa, exc)
            if tentativa < max_retries:
                time.sleep(backoff_base * (2 ** (tentativa - 1)))
            continue

        duracao = time.monotonic() - inicio
        ultima_resposta_http = resp.status_code
        texto = resp.text

        if resp.status_code == 200:
            hash_resposta = hashlib.sha256(texto.encode("utf-8")).hexdigest()
            try:
                dados = resp.json()
            except Exception as exc:  # noqa: BLE001 — resposta corrompida/truncada é potencialmente transitória
                ultimo_erro = f"JSON inválido: {exc}"
                logger.warning("request_id=%s tentativa=%d HTTP 200 mas JSON inválido: %s", spec["request_id"], tentativa, exc)
                if tentativa < max_retries:
                    time.sleep(backoff_base * (2 ** (tentativa - 1)))
                continue

            valido, motivo = validate_sidra_payload(dados)
            if not valido:
                # Falha de schema é tratada como permanente: falha imediatamente,
                # sem gastar as tentativas restantes (Bloqueador 2/8).
                ultimo_erro = f"payload estruturalmente inválido: {motivo}"
                logger.error("request_id=%s HTTP 200 mas payload inválido: %s", spec["request_id"], motivo)
                return {
                    "request_id": spec["request_id"],
                    "url": spec["url"],
                    "tentativas": tentativa,
                    "status_http": resp.status_code,
                    "tamanho": len(texto),
                    "hash_resposta_raw": hash_resposta,
                    "resultado": None,
                    "erro": ultimo_erro,
                    "de_cache": False,
                }

            logger.info(
                "request_id=%s sucesso tentativa=%d duracao=%.3fs tamanho=%d",
                spec["request_id"], tentativa, duracao, len(texto),
            )
            if cache_dir is not None:
                save_cached_request(spec["request_id"], texto, hash_resposta, cache_dir)
            return {
                "request_id": spec["request_id"],
                "url": spec["url"],
                "tentativas": tentativa,
                "status_http": resp.status_code,
                "tamanho": len(texto),
                "hash_resposta_raw": hash_resposta,
                "resultado": dados,
                "erro": None,
                "de_cache": False,
            }
        else:
            logger.warning(
                "request_id=%s tentativa=%d HTTP %s", spec["request_id"], tentativa, resp.status_code,
            )
            ultimo_erro = f"HTTP {resp.status_code}"

        if tentativa < max_retries:
            time.sleep(backoff_base * (2 ** (tentativa - 1)))

    logger.error("request_id=%s falha persistente após %d tentativas", spec["request_id"], max_retries)
    return {
        "request_id": spec["request_id"],
        "url": spec["url"],
        "tentativas": max_retries,
        "status_http": ultima_resposta_http,
        "tamanho": None,
        "hash_resposta_raw": None,
        "resultado": None,
        "erro": ultimo_erro,
        "de_cache": False,
    }


def fetch_metadata(table_id: int = FONTE_TABELA, timeout: float = 15.0) -> dict[str, Any]:
    """Consulta os metadados oficiais da tabela (seção 2). Chamada única,
    pequena — usada para confirmar o contrato, não para extrair dados.
    """
    url = f"https://servicodados.ibge.gov.br/api/v3/agregados/{table_id}/metadados"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# build_diagnostics (seção 11) — resumo mínimo do piloto
# ---------------------------------------------------------------------------


def build_diagnostics(df_long: pd.DataFrame) -> pd.DataFrame:
    """Produz `ano × codigo_variavel_sidra × status_valor_api × n`
    (seção 11), suficiente para inspecionar a cobertura do piloto. Não
    substitui a wide nem faz validação cruzada entre medidas.
    """
    resumo = (
        df_long.groupby(["ano", "codigo_variavel_sidra", "status_valor_api"], dropna=False)
        .size()
        .reset_index(name="n")
    )
    total_por_grupo = resumo.groupby(["ano", "codigo_variavel_sidra"])["n"].transform("sum")
    resumo["percentual"] = (resumo["n"] / total_por_grupo * 100).round(2)
    return resumo.sort_values(["ano", "codigo_variavel_sidra", "status_valor_api"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# validate_cross_measures (seção 11/12) — validações cruzadas reproduzíveis
# ---------------------------------------------------------------------------

# codigo_variavel_sidra -> nome de coluna na wide conceitual (seção 8).
_VARIAVEL_PARA_COLUNA: dict[int, str] = {
    706: "qt_unidades_locais",
    707: "pessoal_ocupado_total",
    708: "pessoal_ocupado_assalariado",
    5944: "pessoal_assalariado_medio",
    662: "salarios_remuneracoes_mil_reais_nominal",
    10143: "salario_medio_reais_nominal",
}

# Regras de não-negatividade simples (seção 11). A relação aproximada entre
# salários e outras remunerações, pessoal assalariado médio e salário médio
# mensal NÃO é implementada aqui: as unidades disponíveis (mil reais,
# pessoas, reais) permitiriam uma fórmula aproximada, mas transformar uma
# aproximação incerta em regra de validação corre o risco de sinalizar como
# "violação" uma diferença de arredondamento legítima. Fica deliberadamente
# para uma etapa posterior, com decisão humana explícita sobre a tolerância.
_REGRAS_NAO_NEGATIVIDADE = [
    ("pessoal_ocupado_total", "pessoal_ocupado_total < 0"),
    ("pessoal_ocupado_assalariado", "pessoal_ocupado_assalariado < 0"),
    ("pessoal_assalariado_medio", "pessoal_assalariado_medio < 0"),
    ("qt_unidades_locais", "qt_unidades_locais < 0"),
    ("salarios_remuneracoes_mil_reais_nominal", "salarios_remuneracoes_mil_reais_nominal < 0"),
    ("salario_medio_reais_nominal", "salario_medio_reais_nominal < 0"),
]

_COLUNAS_VIOLACAO = ["codigo_municipio_ibge", "ano", "regra_violada"]


def _pivot_para_validacao_cruzada(df_long: pd.DataFrame) -> pd.DataFrame:
    relevante = df_long[df_long["codigo_variavel_sidra"].isin(_VARIAVEL_PARA_COLUNA)].copy()
    relevante = relevante[relevante["status_valor_api"].isin(STATUS_VALOR_API_COM_NUMERO)]
    if relevante.empty:
        return pd.DataFrame(columns=["codigo_municipio_ibge", "ano", *_VARIAVEL_PARA_COLUNA.values()])
    relevante["coluna"] = relevante["codigo_variavel_sidra"].map(_VARIAVEL_PARA_COLUNA)
    wide = relevante.pivot_table(
        index=["codigo_municipio_ibge", "ano"], columns="coluna", values="valor_numerico", aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    return wide


def validate_cross_measures(df_long: pd.DataFrame) -> pd.DataFrame:
    """Validações cruzadas diagnósticas (seção 11/12): só compara medidas
    quando AMBAS têm valor numérico observado (`status_valor_api` em
    `observado`/uma classe de zero) para o mesmo `(codigo_municipio_ibge,
    ano)`. Não corrige nada — retorna uma linha por violação encontrada
    (DataFrame vazio se não houver nenhuma). Deve ser chamada sobre a long
    já validada por `validate_long` (chave canônica única).
    """
    wide = _pivot_para_validacao_cruzada(df_long)
    violacoes: list[dict[str, Any]] = []

    def _registrar(mascara: pd.Series, regra: str) -> None:
        for _, linha in wide[mascara].iterrows():
            violacoes.append({
                "codigo_municipio_ibge": linha["codigo_municipio_ibge"],
                "ano": linha["ano"],
                "regra_violada": regra,
            })

    if {"pessoal_ocupado_assalariado", "pessoal_ocupado_total"} <= set(wide.columns):
        _registrar(
            wide["pessoal_ocupado_assalariado"] > wide["pessoal_ocupado_total"],
            "pessoal_ocupado_assalariado > pessoal_ocupado_total",
        )

    for coluna, regra in _REGRAS_NAO_NEGATIVIDADE:
        if coluna in wide.columns:
            _registrar(wide[coluna] < 0, regra)

    return pd.DataFrame(violacoes, columns=_COLUNAS_VIOLACAO)


# ---------------------------------------------------------------------------
# D2 — persistência e reconstrução offline da long CEMPRE
#
# Fluxo: cache raw → leitura offline → normalize_long → concatenação →
# validate_long → reconcile_territorial → persistência Parquet → reload →
# validação/equivalência. NENHUMA função desta seção chama `fetch_request`
# ou rede — leem exclusivamente o cache já existente em disco. Isso NÃO é
# o orquestrador nacional (D4) nem faz extração nacional.
# ---------------------------------------------------------------------------


def load_results_from_cache(
    plano: list[dict[str, Any]],
    cache_dir: str | Path,
) -> list[dict[str, Any]]:
    """Reconstrói offline os resultados de um plano de requests A PARTIR
    SOMENTE do cache já existente (D2, seção 2). NUNCA chama rede.

    Contrato de saída idêntico ao de `fetch_request`/`avalia_completude_plano`
    (D1): `request_id`, `resultado`, `hash_resposta_raw`, `erro`,
    `de_cache=True` para cada item. Cache ausente, corrompido ou com
    payload de schema inválido nunca são convertidos silenciosamente em
    sucesso — cada caso produz um resultado com `erro` explícito, para que
    `avalia_completude_plano` os trate como lote obrigatório falho.
    """
    cache_dir = Path(cache_dir)
    resultados: list[dict[str, Any]] = []
    for item in plano:
        resultado_cache, ausente = _resultado_a_partir_do_cache(
            item["request_id"], item.get("url"), cache_dir,
        )
        if ausente:
            resultado_cache = {
                "request_id": item["request_id"],
                "url": item.get("url"),
                "tentativas": 0,
                "status_http": None,
                "tamanho": None,
                "hash_resposta_raw": None,
                "resultado": None,
                "erro": (
                    "cache ausente para este request_id — reconstrução offline "
                    "não pode prosseguir sem rede"
                ),
                "de_cache": True,
            }
        resultados.append(resultado_cache)
    return resultados


def build_long_from_results(
    plano: list[dict[str, Any]],
    resultados: list[dict[str, Any]],
    calendario: pd.DataFrame,
    data_extracao: str | None = None,
    versao_metadados: str | None = None,
) -> pd.DataFrame:
    """Constrói a long CEMPRE reconciliada a partir de resultados já
    carregados (offline ou não) e do plano esperado (D2, seção 3).

    Usa `avalia_completude_plano` ANTES de normalizar: se `completo=False`
    (lote ausente, duplicado, inesperado, malformado ou com erro), levanta
    `ValueError` explícito e NÃO constrói uma long considerada completa.
    Para cada resultado válido, reutiliza `normalize_long` (request_id/hash
    reais, sem duplicar lógica de parsing); concatena, aplica
    `validate_long` (falha explícita se `aprovado=False`) e
    `reconcile_territorial`; retorna a long ordenada deterministicamente
    (seção 4: `codigo_municipio_ibge`, `ano`, `codigo_variavel_sidra`,
    `request_id`).
    """
    relatorio_completude = avalia_completude_plano(plano, resultados)
    if not relatorio_completude["completo"]:
        raise ValueError(
            "plano incompleto — a long completa NÃO será construída "
            f"(ausentes={relatorio_completude['request_ids_ausentes']}, "
            f"inesperados={relatorio_completude['request_ids_inesperados']}, "
            f"duplicados={relatorio_completude['request_ids_duplicados']}, "
            f"n_falhas={relatorio_completude['n_falhas']}, "
            f"malformados={relatorio_completude['resultados_malformados']})"
        )

    resultados_por_id = {resultado["request_id"]: resultado for resultado in resultados}
    longs_por_request: list[pd.DataFrame] = []
    for item in plano:
        resultado = resultados_por_id[item["request_id"]]
        long_request = normalize_long(
            resultado["resultado"],
            request_id=item["request_id"],
            fonte_tabela=item.get("fonte_tabela", FONTE_TABELA),
            data_extracao=data_extracao,
            hash_resposta_raw=resultado.get("hash_resposta_raw"),
            versao_metadados=versao_metadados,
        )
        longs_por_request.append(long_request)

    long_bruta = (
        pd.concat(longs_por_request, ignore_index=True)
        if longs_por_request
        else pd.DataFrame(columns=_COLUNAS_LONG)
    )

    df_validado, relatorio_validacao = validate_long(long_bruta)
    if not relatorio_validacao["aprovado"]:
        raise ValueError(
            "validate_long reprovou a long construída a partir dos resultados: "
            f"{relatorio_validacao['motivos_bloqueio']}"
        )

    df_reconciliada = reconcile_territorial(df_validado, calendario)
    return _ordenar_long_deterministicamente(df_reconciliada)


# Ordem determinística da long persistida (seção 4): mesmo conjunto de
# caches deve sempre produzir a mesma ordem lógica, nunca a ordem do
# filesystem ou de execução.
_COLUNAS_ORDENACAO_LONG = ["codigo_municipio_ibge", "ano", "codigo_variavel_sidra", "request_id"]


def _ordenar_long_deterministicamente(df_long: pd.DataFrame) -> pd.DataFrame:
    colunas_ordenacao = [coluna for coluna in _COLUNAS_ORDENACAO_LONG if coluna in df_long.columns]
    return df_long.sort_values(colunas_ordenacao, kind="mergesort").reset_index(drop=True)


# Schema mínimo contratado da long persistida (seção 5): tudo o que
# `normalize_long` já produz, mais os dois campos de reconciliação
# territorial. Nenhum desses campos é removido nem convertido.
_COLUNAS_LONG_PERSISTIDA = _COLUNAS_LONG + ["status_territorial", "incompatibilidade_territorial"]
_STATUS_TERRITORIAL_VALIDOS = {"existia_no_ano", "nao_existia_no_ano", "indeterminado"}


def _validar_schema_long_persistida(df_long: pd.DataFrame) -> None:
    """Validação estrutural única do contrato da long persistida (D2, seção
    5), reutilizada tanto por `write_long_parquet` (antes de qualquer
    `to_parquet`) quanto por `load_long_parquet` (no reload) — o que não
    pode ser carregado como long válida também não pode ser gravado como
    long válida. Nunca corrige silenciosamente: levanta `ValueError`
    explícito no primeiro contrato violado.

    Reflete exatamente o artefato real produzido por `normalize_long` +
    `reconcile_territorial` (não inventa política de nullable boolean:
    `incompatibilidade_territorial` já sai sempre booleana e sem nulos do
    pipeline, então aqui isso é exigido, não relaxado).
    """
    colunas_ausentes = sorted(set(_COLUNAS_LONG_PERSISTIDA) - set(df_long.columns))
    if colunas_ausentes:
        raise ValueError(f"long persistida sem coluna(s) obrigatória(s): {colunas_ausentes}")

    chave_duplicada = df_long.duplicated(_CHAVE_CANONICA, keep=False)
    if bool(chave_duplicada.any()):
        exemplos = df_long.loc[chave_duplicada, _CHAVE_CANONICA].head().to_dict("records")
        raise ValueError(f"chave canônica duplicada na long persistida: {exemplos}")

    if not pd.api.types.is_integer_dtype(df_long["ano"]):
        raise ValueError("coluna 'ano' inválida na long persistida: deve ser inteiro")
    anos_invalidos = sorted(set(df_long.loc[~df_long["ano"].between(ANO_MIN, ANO_MAX), "ano"].tolist()))
    if anos_invalidos:
        raise ValueError(f"ano fora da janela {ANO_MIN}-{ANO_MAX} na long persistida: {anos_invalidos[:5]}")

    codigos_validos = df_long["codigo_municipio_ibge"].astype(str).str.fullmatch(_RE_CODIGO_MUNICIPIO)
    if not bool(codigos_validos.all()):
        codigos_invalidos = sorted(set(df_long.loc[~codigos_validos, "codigo_municipio_ibge"].tolist()))
        raise ValueError(f"código municipal inválido na long persistida: {codigos_invalidos[:5]}")

    variaveis_invalidas = sorted(set(df_long["codigo_variavel_sidra"].tolist()) - VARIAVEIS_ESPERADAS)
    if variaveis_invalidas:
        raise ValueError(f"código de variável fora do contrato CEMPRE na long persistida: {variaveis_invalidas}")

    if df_long["status_territorial"].isna().any():
        raise ValueError("status_territorial ausente (nulo) em uma ou mais linhas da long persistida")
    status_territorial_invalidos = sorted(set(df_long["status_territorial"].tolist()) - _STATUS_TERRITORIAL_VALIDOS)
    if status_territorial_invalidos:
        raise ValueError(f"status_territorial fora do contrato na long persistida: {status_territorial_invalidos}")

    if df_long["incompatibilidade_territorial"].isna().any():
        raise ValueError("incompatibilidade_territorial ausente (nulo) em uma ou mais linhas da long persistida")
    if not pd.api.types.is_bool_dtype(df_long["incompatibilidade_territorial"]):
        raise ValueError(
            "incompatibilidade_territorial deve ser booleana na long persistida "
            f"(dtype recebido: {df_long['incompatibilidade_territorial'].dtype})"
        )


def write_long_parquet(
    df_long: pd.DataFrame,
    caminho: str | Path,
    overwrite: bool = False,
) -> Path:
    """Persiste a long CEMPRE reconciliada em Parquet (D2, seção 6).

    Valida estruturalmente a long via `_validar_schema_long_persistida`
    (mesmo contrato usado por `load_long_parquet` — o que não pode ser
    recarregado como long válida também não pode ser gravado como long
    válida) ANTES de qualquer `to_parquet`; falha explicitamente
    (`ValueError`) e não cria o arquivo de saída se a long for
    estruturalmente inválida (schema incompleto, chave canônica
    duplicada, ano fora de 2007-2019, código municipal/variável fora do
    contrato, `status_territorial`/`incompatibilidade_territorial`
    ausente ou fora do tipo/contrato). Por padrão (`overwrite=False`)
    falha explicitamente (`FileExistsError`) se `caminho` já existir —
    nunca sobrescreve silenciosamente. Cria o diretório pai quando
    necessário e escreve a long já ordenada deterministicamente (seção
    4), sem alterar conteúdo substantivo.
    """
    caminho = Path(caminho)
    if caminho.suffix.lower() != ".parquet":
        raise ValueError(f"caminho de persistência deve terminar em '.parquet': {caminho}")

    _validar_schema_long_persistida(df_long)

    if caminho.exists() and not overwrite:
        raise FileExistsError(
            f"arquivo já existe e overwrite=False (padrão) — persistência não sobrescreve "
            f"silenciosamente: {caminho}"
        )

    caminho.parent.mkdir(parents=True, exist_ok=True)
    df_ordenado = _ordenar_long_deterministicamente(df_long)
    df_ordenado.to_parquet(caminho, index=False)
    return caminho


def load_long_parquet(caminho: str | Path) -> pd.DataFrame:
    """Carrega e valida a long CEMPRE persistida em Parquet (D2, seção 7).

    Nunca "corrige" silenciosamente um artefato inválido: falha
    explicitamente (`FileNotFoundError`/`ValueError`) para arquivo
    ausente, formato não suportado, ou qualquer violação do contrato
    estrutural verificado por `_validar_schema_long_persistida` — o mesmo
    validador reutilizado por `write_long_parquet`, incluindo schema
    incompleto, duplicidade da chave canônica (`_CHAVE_CANONICA`, reaproveitada
    de `validate_long`), ano fora de 2007-2019, código municipal ou
    variável fora do contrato, `status_territorial` ausente/fora do
    contrato e `incompatibilidade_territorial` ausente ou não booleana.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"long persistida não encontrada: {caminho}")
    if caminho.suffix.lower() != ".parquet":
        raise ValueError(
            f"formato não suportado para long persistida: {caminho.suffix!r}; esperado '.parquet'"
        )

    try:
        df_long = pd.read_parquet(caminho)
    except Exception as exc:  # noqa: BLE001 — arquivo corrompido/não-Parquet deve falhar explicitamente
        raise ValueError(f"long persistida não está em formato Parquet válido ({caminho}): {exc}") from exc

    _validar_schema_long_persistida(df_long)

    return df_long


# Campos mínimos comparados na equivalência lógica de round-trip (seção 8):
# chave canônica, proveniência, valores e os dois status de reconciliação.
_COLUNAS_EQUIVALENCIA_ROUND_TRIP = [
    "codigo_municipio_ibge", "ano", "codigo_variavel_sidra",
    "valor_bruto", "valor_numerico", "status_valor_api",
    "request_id", "hash_resposta_raw",
    "status_territorial", "incompatibilidade_territorial",
]


def validate_round_trip_equivalencia(
    long_antes: pd.DataFrame,
    long_depois: pd.DataFrame,
) -> dict[str, Any]:
    """Checa equivalência LÓGICA (não bytes físicos) entre a long antes de
    persistir e a long recarregada do Parquet (D2, seção 8).

    Normaliza a ordem de ambos os lados antes de comparar (a ordem não
    deve importar para a equivalência). Falha explicitamente
    (`ValueError`) se colunas contratadas estiverem ausentes, a
    quantidade de linhas divergir, ou o conteúdo lógico divergir —
    incluindo NA em `valor_numerico`.
    """
    colunas_ausentes_antes = sorted(set(_COLUNAS_EQUIVALENCIA_ROUND_TRIP) - set(long_antes.columns))
    colunas_ausentes_depois = sorted(set(_COLUNAS_EQUIVALENCIA_ROUND_TRIP) - set(long_depois.columns))
    if colunas_ausentes_antes or colunas_ausentes_depois:
        raise ValueError(
            "round-trip: coluna(s) contratada(s) ausente(s) — "
            f"antes={colunas_ausentes_antes}, depois={colunas_ausentes_depois}"
        )

    if len(long_antes) != len(long_depois):
        raise ValueError(
            f"round-trip: quantidade de linhas divergente (antes={len(long_antes)}, "
            f"depois={len(long_depois)})"
        )

    a = _ordenar_long_deterministicamente(long_antes)[_COLUNAS_EQUIVALENCIA_ROUND_TRIP].reset_index(drop=True)
    b = _ordenar_long_deterministicamente(long_depois)[_COLUNAS_EQUIVALENCIA_ROUND_TRIP].reset_index(drop=True)

    try:
        pd.testing.assert_frame_equal(a, b, check_dtype=False, check_like=False)
    except AssertionError as exc:
        raise ValueError(
            f"round-trip: conteúdo lógico divergente entre a long original e a recarregada: {exc}"
        ) from exc

    return {
        "equivalente": True,
        "n_linhas": len(long_antes),
        "colunas_comparadas": list(_COLUNAS_EQUIVALENCIA_ROUND_TRIP),
    }


def rebuild_long_from_cache(
    plano: list[dict[str, Any]],
    cache_dir: str | Path,
    calendario: pd.DataFrame,
    data_extracao: str | None = None,
    versao_metadados: str | None = None,
    caminho_persistencia: str | Path | None = None,
    overwrite: bool = False,
) -> pd.DataFrame:
    """Reconstrução offline de alto nível (D2, seção 9): plano + cache_dir +
    calendário → long validada/reconciliada e, opcionalmente, persistida.

    NUNCA chama `fetch_request` nem rede — lê exclusivamente o cache já
    existente via `load_results_from_cache`. Isso NÃO é o orquestrador
    nacional (D4): não decide política de execução, não faz retry e não
    extrai nada da API.
    """
    resultados = load_results_from_cache(plano, cache_dir)
    long_reconciliada = build_long_from_results(
        plano=plano,
        resultados=resultados,
        calendario=calendario,
        data_extracao=data_extracao,
        versao_metadados=versao_metadados,
    )
    if caminho_persistencia is not None:
        write_long_parquet(long_reconciliada, caminho_persistencia, overwrite=overwrite)
    return long_reconciliada


# ---------------------------------------------------------------------------
# D3 — manifesto e proveniência do pipeline CEMPRE
#
# Registra FATOS sobre o plano, a execução/completude e os artefatos já
# produzidos (seção 10 da especificação: `source_manifest.json`). NÃO
# executa requests, NÃO é o orquestrador nacional (D4) e NÃO autoriza
# nenhum gate — nenhuma função desta seção declara
# `EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA` nem `PAINEL_TECNICO_CONSTRUIDO`.
# ---------------------------------------------------------------------------

_VERSAO_SCHEMA_MANIFESTO = "cempre_manifesto_v1"
_RE_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_RE_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(caminho: str | Path, tamanho_chunk: int = 65536) -> str:
    """Calcula o SHA-256 de um arquivo em disco (D3, seção 2).

    Leitura binária em chunks (não carrega o arquivo inteiro em memória de
    uma vez); nunca chama rede. Falha explicitamente (`FileNotFoundError`)
    se o arquivo não existir. Usado para registrar artefatos no manifesto
    (calendário territorial, long Parquet, outros artefatos futuros).
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"arquivo não encontrado para cálculo de hash SHA-256: {caminho}")

    hasher = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(tamanho_chunk), b""):
            hasher.update(bloco)
    return hasher.hexdigest()


def hash_plano_canonico(plano: list[dict[str, Any]]) -> str:
    """Hash lógico/canônico do plano de requests (D3, seção 3).

    Independente da ordem incidental da lista e da ordem de chaves dos
    dicionários — usa apenas o conteúdo contratual de cada request
    (`request_id`, `ano`, `territorio`, `variaveis`, `fonte_tabela`,
    `url`), ordena os itens por `request_id` e serializa em JSON canônico
    (`sort_keys=True`, separadores compactos) antes de aplicar SHA-256.
    Mesmo plano lógico em ordem diferente produz o mesmo hash; qualquer
    mudança real em um lote produz um hash diferente.
    """
    itens_canonicos = []
    for item in plano:
        territorio = item.get("territorio") or {}
        itens_canonicos.append({
            "request_id": item["request_id"],
            "ano": item["ano"],
            "territorio": dict(territorio),
            "variaveis": sorted(item.get("variaveis") or []),
            "fonte_tabela": item.get("fonte_tabela"),
            "url": item.get("url"),
        })
    itens_canonicos.sort(key=lambda item: item["request_id"])

    texto_canonico = json.dumps(itens_canonicos, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(texto_canonico.encode("utf-8")).hexdigest()


def build_request_provenance(
    plano: list[dict[str, Any]],
    resultados: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Proveniência compacta por request (D3, seção 4): uma entrada por
    request ESPERADO do plano, nunca o payload bruto nem a long inteira.

    Para cada request, registra `request_id`, `ano`, território, variáveis,
    `status_execucao` (`sucesso`/`falha`/`ausente`/`duplicado`), `de_cache`
    (quando conhecido), `hash_resposta_raw` (quando disponível) e `erro`
    (quando houver). Reutiliza `_resultado_e_sucesso` — não duplica a
    lógica de sucesso já usada por `avalia_completude_plano`.
    """
    resultados_por_id: dict[str, list[dict[str, Any]]] = {}
    for resultado in resultados:
        if isinstance(resultado, dict) and resultado.get("request_id"):
            resultados_por_id.setdefault(resultado["request_id"], []).append(resultado)

    provenance: list[dict[str, Any]] = []
    for item in plano:
        entradas = resultados_por_id.get(item["request_id"], [])
        if not entradas:
            status_execucao, de_cache, hash_resposta_raw, erro = "ausente", None, None, None
        elif len(entradas) > 1:
            status_execucao = "duplicado"
            de_cache, hash_resposta_raw = None, None
            erro = f"{len(entradas)} resultados para este request_id — ambíguo"
        else:
            resultado = entradas[0]
            status_execucao = "sucesso" if _resultado_e_sucesso(resultado) else "falha"
            de_cache = resultado.get("de_cache")
            hash_resposta_raw = resultado.get("hash_resposta_raw")
            erro = resultado.get("erro")

        provenance.append({
            "request_id": item["request_id"],
            "ano": item["ano"],
            "territorio": dict(item.get("territorio") or {}),
            "variaveis": sorted(item.get("variaveis") or []),
            "status_execucao": status_execucao,
            "de_cache": de_cache,
            "hash_resposta_raw": hash_resposta_raw,
            "erro": erro,
        })
    return provenance


def get_git_head(cwd: str | Path | None = None) -> str:
    """Consulta o commit Git atual via `git rev-parse HEAD` (D3, seção 6).

    Somente leitura (`subprocess`): nunca altera o repositório, nunca
    chama rede. Retorna sempre o hash COMPLETO (40 hex), nunca abreviado.
    Levanta `RuntimeError` explícito se o commit não puder ser
    determinado (comando ausente, fora de um repositório Git, saída em
    formato inesperado).
    """
    diretorio = Path(cwd) if cwd is not None else ROOT
    try:
        resultado = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=diretorio,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"não foi possível executar 'git rev-parse HEAD': {exc}") from exc

    if resultado.returncode != 0:
        raise RuntimeError(
            f"'git rev-parse HEAD' falhou (código {resultado.returncode}): {resultado.stderr.strip()}"
        )

    commit = resultado.stdout.strip()
    if not _RE_GIT_COMMIT.fullmatch(commit):
        raise RuntimeError(f"'git rev-parse HEAD' retornou formato inesperado (esperado 40 hex): {commit!r}")
    return commit


def timestamp_utc_iso(agora: datetime | None = None) -> str:
    """Timestamp UTC em ISO-8601 (D3, seção 7).

    Aceita `agora` explícito para tornar testes determinísticos (nunca
    depende do relógio real quando informado); normaliza qualquer
    `datetime` com fuso para UTC e assume UTC para um `datetime` "naive".
    Sem `agora`, usa `datetime.now(timezone.utc)`.
    """
    momento = agora if agora is not None else datetime.now(timezone.utc)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    else:
        momento = momento.astimezone(timezone.utc)
    return momento.isoformat()


def _registrar_artefatos(artefatos: dict[str, dict[str, Any]] | None) -> dict[str, Any]:
    """Calcula SHA-256/tamanho de cada artefato informado (D3, seção 5).

    `artefatos` mapeia um nome lógico (ex.: `"calendario_territorial"`,
    `"long_parquet"`) para um dict com `caminho` (obrigatório) e quaisquer
    campos extras já conhecidos pelo chamador (ex.: `n_linhas`, `colunas`
    para a long Parquet) — esses extras são preservados como estão, sem
    recalcular nada que o chamador já validou.
    """
    if not artefatos:
        return {}

    registrados: dict[str, Any] = {}
    for nome, info in artefatos.items():
        caminho = Path(info["caminho"])
        entrada: dict[str, Any] = {
            "caminho": str(caminho),
            "sha256": sha256_file(caminho),
            "tamanho_bytes": caminho.stat().st_size,
        }
        entrada.update({chave: valor for chave, valor in info.items() if chave != "caminho"})
        registrados[nome] = entrada
    return registrados


def build_manifest(
    plano: list[dict[str, Any]],
    resultados: list[dict[str, Any]],
    ufs_esperadas: list[dict[str, str]],
    anos_esperados: list[int] | None = None,
    variaveis_esperadas: set[int] | list[int] | None = None,
    artefatos: dict[str, dict[str, Any]] | None = None,
    git_commit: str | None = None,
    timestamp_geracao: str | None = None,
    modo_geracao: str = "reconstrucao_offline_cache",
) -> dict[str, Any]:
    """Constrói o manifesto de proveniência do pipeline CEMPRE (D3, seção 5).

    Reutiliza `validate_national_request_plan` (contrato do plano) e
    `avalia_completude_plano` (execução/completude) — nunca recalcula essa
    lógica em paralelo. NÃO executa requests, NÃO é o orquestrador D4 e
    NÃO declara nenhum gate de autorização.
    """
    relatorio_plano = validate_national_request_plan(
        plano,
        ufs_esperadas=ufs_esperadas,
        anos_esperados=anos_esperados,
        variaveis_esperadas=variaveis_esperadas,
    )
    relatorio_completude = avalia_completude_plano(plano, resultados)

    anos_plano = sorted({item["ano"] for item in plano})
    variaveis_plano = sorted({variavel for item in plano for variavel in (item.get("variaveis") or [])})

    return {
        "schema_manifesto": _VERSAO_SCHEMA_MANIFESTO,
        "fonte": {
            "fonte_tabela": FONTE_TABELA,
            "ano_min": ANO_MIN,
            "ano_max": ANO_MAX,
            "variaveis_contratadas": sorted(VARIAVEIS_ESPERADAS),
            "segmentacao_territorial": "uf",
        },
        "codigo": {
            "git_commit": git_commit if git_commit is not None else get_git_head(),
            "versao_manifesto": _VERSAO_SCHEMA_MANIFESTO,
        },
        "plano": {
            "n_requests_esperados": relatorio_plano["total_requests_esperados"],
            "hash_plano": hash_plano_canonico(plano),
            "anos": anos_plano,
            "ufs": relatorio_plano["ufs"],
            "variaveis": variaveis_plano,
        },
        "execucao": {
            "n_requests_esperados": relatorio_completude["n_requests_esperados"],
            "n_requests_recebidos": relatorio_completude["n_requests_recebidos"],
            "n_sucessos": relatorio_completude["n_sucessos"],
            "n_falhas": relatorio_completude["n_falhas"],
            "request_ids_ausentes": relatorio_completude["request_ids_ausentes"],
            "request_ids_inesperados": relatorio_completude["request_ids_inesperados"],
            "request_ids_duplicados": relatorio_completude["request_ids_duplicados"],
            "resultados_malformados": relatorio_completude["resultados_malformados"],
            "completo": relatorio_completude["completo"],
        },
        "requests": build_request_provenance(plano, resultados),
        "artefatos": _registrar_artefatos(artefatos),
        "geracao": {
            "timestamp_utc": timestamp_geracao if timestamp_geracao is not None else timestamp_utc_iso(),
            "modo": modo_geracao,
        },
    }


_ESTADOS_PROVENIENCIA_VALIDOS = {"sucesso", "falha", "ausente", "duplicado"}


def _validar_consistencia_execucao_requests(
    execucao_info: dict[str, Any],
    requests_prov: list[dict[str, Any]],
) -> None:
    """Confronta `manifesto["execucao"]` com `manifesto["requests"]` (D3,
    correção focal do spot-check — Bloqueador 1).

    NÃO recalcula `avalia_completude_plano`: só verifica se as duas
    representações já armazenadas no manifesto são coerentes entre si.
    Preserva exatamente a semântica de `avalia_completude_plano`: request
    ausente não conta em `n_falhas`; request duplicado conta em
    `n_falhas`.
    """
    status_por_id: dict[str, str] = {}
    for item in requests_prov:
        status = item.get("status_execucao")
        if status not in _ESTADOS_PROVENIENCIA_VALIDOS:
            raise ValueError(
                f"status_execucao inválido na proveniência do request {item.get('request_id')!r}: {status!r}"
            )
        status_por_id[item["request_id"]] = status

    ids_sucesso = {rid for rid, status in status_por_id.items() if status == "sucesso"}
    ids_ausente = {rid for rid, status in status_por_id.items() if status == "ausente"}
    ids_duplicado = {rid for rid, status in status_por_id.items() if status == "duplicado"}
    ids_falha_ou_duplicado = {
        rid for rid, status in status_por_id.items() if status in ("falha", "duplicado")
    }

    n_sucessos_execucao = execucao_info.get("n_sucessos")
    if n_sucessos_execucao != len(ids_sucesso):
        raise ValueError(
            f"execucao.n_sucessos ({n_sucessos_execucao!r}) diverge da proveniência "
            f"({len(ids_sucesso)} request(s) com status_execucao='sucesso')"
        )

    n_falhas_execucao = execucao_info.get("n_falhas")
    if n_falhas_execucao != len(ids_falha_ou_duplicado):
        raise ValueError(
            f"execucao.n_falhas ({n_falhas_execucao!r}) diverge da proveniência "
            f"({len(ids_falha_ou_duplicado)} request(s) com status_execucao em "
            f"{{'falha','duplicado'}})"
        )

    ausentes_execucao = set(execucao_info.get("request_ids_ausentes") or [])
    if ausentes_execucao != ids_ausente:
        raise ValueError(
            f"execucao.request_ids_ausentes ({sorted(ausentes_execucao)}) diverge da proveniência "
            f"(status_execucao='ausente' em: {sorted(ids_ausente)})"
        )

    duplicados_execucao = set(execucao_info.get("request_ids_duplicados") or [])
    if duplicados_execucao != ids_duplicado:
        raise ValueError(
            f"execucao.request_ids_duplicados ({sorted(duplicados_execucao)}) diverge da proveniência "
            f"(status_execucao='duplicado' em: {sorted(ids_duplicado)})"
        )

    if execucao_info.get("completo") and ids_sucesso != set(status_por_id.keys()):
        nao_sucesso = sorted(set(status_por_id.keys()) - ids_sucesso)
        raise ValueError(
            "manifesto inconsistente: completo=True mas nem todo request esperado tem "
            f"status_execucao='sucesso' na proveniência: {nao_sucesso}"
        )


def _validar_consistencia_plano_requests(
    plano_info: dict[str, Any],
    requests_prov: list[dict[str, Any]],
) -> None:
    """Confronta `manifesto["plano"]` com `manifesto["requests"]` (D3,
    correção focal do spot-check — Bloqueador 2).

    Valida o formato do que já está armazenado em `plano` (hash SHA-256
    completo, anos e variáveis dentro do contrato CEMPRE) e confronta com
    o que a proveniência realmente registra. NUNCA recomputa
    `hash_plano_canonico` aqui — o plano completo pode não estar
    disponível no reload; só valida o contrato disponível, sem inventar
    informação.
    """
    hash_plano = plano_info.get("hash_plano")
    if not isinstance(hash_plano, str) or not _RE_SHA256.fullmatch(hash_plano):
        raise ValueError(
            f"manifesto com hash_plano malformado (esperado SHA-256 hex de 64 caracteres): {hash_plano!r}"
        )

    anos_plano = plano_info.get("anos")
    if not isinstance(anos_plano, list) or not anos_plano:
        raise ValueError(f"manifesto com plano.anos vazio ou inválido: {anos_plano!r}")
    if any(not isinstance(ano, int) for ano in anos_plano):
        raise ValueError(f"manifesto com plano.anos contendo valor não inteiro: {anos_plano!r}")
    if len(anos_plano) != len(set(anos_plano)):
        raise ValueError(f"manifesto com plano.anos duplicado: {anos_plano!r}")
    anos_fora_da_janela = sorted(ano for ano in anos_plano if not (ANO_MIN <= ano <= ANO_MAX))
    if anos_fora_da_janela:
        raise ValueError(f"manifesto com plano.anos fora da janela {ANO_MIN}-{ANO_MAX}: {anos_fora_da_janela}")

    anos_proveniencia = {item.get("ano") for item in requests_prov}
    if set(anos_plano) != anos_proveniencia:
        raise ValueError(
            f"manifesto com plano.anos ({sorted(anos_plano)}) divergente dos anos presentes na "
            f"proveniência de requests ({sorted(anos_proveniencia)})"
        )

    variaveis_plano = plano_info.get("variaveis")
    if variaveis_plano is None or sorted(variaveis_plano) != sorted(VARIAVEIS_ESPERADAS):
        raise ValueError(f"manifesto com plano.variaveis fora do contrato CEMPRE: {variaveis_plano!r}")
    for item in requests_prov:
        variaveis_item = item.get("variaveis")
        if variaveis_item is None or sorted(variaveis_item) != sorted(VARIAVEIS_ESPERADAS):
            raise ValueError(
                f"manifesto com variaveis fora do contrato CEMPRE na proveniência do request "
                f"{item.get('request_id')!r}: {variaveis_item!r}"
            )

    ufs_plano = plano_info.get("ufs")
    if not isinstance(ufs_plano, list):
        raise ValueError(f"manifesto com plano.ufs inválido: {ufs_plano!r}")
    ufs_proveniencia = {(item.get("territorio") or {}).get("codigo") for item in requests_prov}
    if set(ufs_plano) != ufs_proveniencia:
        raise ValueError(
            f"manifesto com plano.ufs ({sorted(ufs_plano)}) divergente das UFs presentes na "
            f"proveniência de requests ({sorted(ufs_proveniencia)})"
        )


def validate_manifest(manifesto: dict[str, Any]) -> dict[str, Any]:
    """Valida o contrato estrutural do manifesto CEMPRE (D3, seção 8).

    Rejeita explicitamente (`ValueError`) inconsistências evidentes: seção
    obrigatória ausente; `fonte`/anos/variáveis fora do contrato CEMPRE;
    `git_commit` que não é um hash completo de 40 hex; divergência entre
    `n_requests_esperados` do plano, da execução e da quantidade real de
    entradas em `requests`; request esperado sem entrada correspondente
    em `requests` (ou duplicado/sem `request_id`); contradição entre
    `execucao` e a proveniência por request (`_validar_consistencia_execucao_requests`
    — Bloqueador 1 do spot-check); contradição entre `plano` (hash,
    anos, variáveis, UFs) e a proveniência (`_validar_consistencia_plano_requests`
    — Bloqueador 2); `completo=True` acompanhado de falhas, ausentes,
    duplicados, inesperados ou malformados; e `sha256` malformado em
    qualquer artefato registrado. Não é um framework genérico de JSON
    Schema — só valida o contrato CEMPRE necessário. Não corrige nada
    silenciosamente.
    """
    secoes_obrigatorias = {"schema_manifesto", "fonte", "codigo", "plano", "execucao", "requests", "artefatos", "geracao"}
    secoes_ausentes = sorted(secoes_obrigatorias - set(manifesto.keys()))
    if secoes_ausentes:
        raise ValueError(f"manifesto sem seção(ões) obrigatória(s): {secoes_ausentes}")

    fonte = manifesto["fonte"]
    if fonte.get("fonte_tabela") != FONTE_TABELA:
        raise ValueError(f"manifesto com fonte_tabela fora do contrato CEMPRE: {fonte.get('fonte_tabela')!r}")
    if fonte.get("ano_min") != ANO_MIN or fonte.get("ano_max") != ANO_MAX:
        raise ValueError(
            f"manifesto com janela de anos fora do contrato CEMPRE: "
            f"{fonte.get('ano_min')!r}-{fonte.get('ano_max')!r}"
        )
    variaveis_contratadas = fonte.get("variaveis_contratadas")
    if variaveis_contratadas is None or sorted(variaveis_contratadas) != sorted(VARIAVEIS_ESPERADAS):
        raise ValueError(f"manifesto com variaveis_contratadas fora do contrato CEMPRE: {variaveis_contratadas!r}")

    git_commit = manifesto["codigo"].get("git_commit")
    if not isinstance(git_commit, str) or not _RE_GIT_COMMIT.fullmatch(git_commit):
        raise ValueError(f"manifesto com git_commit inválido (esperado hash completo de 40 hex): {git_commit!r}")

    plano_info = manifesto["plano"]
    execucao_info = manifesto["execucao"]
    requests_prov = manifesto["requests"]
    if not isinstance(requests_prov, list):
        raise ValueError("manifesto['requests'] deve ser uma lista")

    n_esperados_plano = plano_info.get("n_requests_esperados")
    n_esperados_execucao = execucao_info.get("n_requests_esperados")
    if not (n_esperados_plano == n_esperados_execucao == len(requests_prov)):
        raise ValueError(
            f"n_requests_esperados inconsistente: plano={n_esperados_plano!r}, "
            f"execucao={n_esperados_execucao!r}, len(requests)={len(requests_prov)}"
        )

    request_ids_prov = [item.get("request_id") for item in requests_prov]
    if any(not rid for rid in request_ids_prov):
        raise ValueError("manifesto contém request na proveniência sem request_id")
    if len(request_ids_prov) != len(set(request_ids_prov)):
        raise ValueError("manifesto contém request_id duplicado na proveniência de requests")

    _validar_consistencia_execucao_requests(execucao_info, requests_prov)
    _validar_consistencia_plano_requests(plano_info, requests_prov)

    completo = execucao_info.get("completo")
    n_falhas = execucao_info.get("n_falhas")
    ausentes = execucao_info.get("request_ids_ausentes") or []
    inesperados = execucao_info.get("request_ids_inesperados") or []
    duplicados = execucao_info.get("request_ids_duplicados") or []
    malformados = execucao_info.get("resultados_malformados") or []
    if completo:
        if ausentes:
            raise ValueError(f"manifesto inconsistente: completo=True mas há request_ids ausentes: {ausentes}")
        if duplicados:
            raise ValueError(f"manifesto inconsistente: completo=True mas há request_ids duplicados: {duplicados}")
        if malformados:
            raise ValueError(f"manifesto inconsistente: completo=True mas há resultados malformados: {malformados}")
        if inesperados:
            raise ValueError(f"manifesto inconsistente: completo=True mas há request_ids inesperados: {inesperados}")
        if n_falhas:
            raise ValueError(f"manifesto inconsistente: completo=True mas n_falhas={n_falhas}")

    for nome_artefato, entrada in (manifesto.get("artefatos") or {}).items():
        sha = entrada.get("sha256") if isinstance(entrada, dict) else None
        if not isinstance(sha, str) or not _RE_SHA256.fullmatch(sha):
            raise ValueError(f"manifesto com sha256 malformado para artefato {nome_artefato!r}: {sha!r}")

    return manifesto


def write_manifest(
    manifesto: dict[str, Any],
    caminho: str | Path,
    overwrite: bool = False,
) -> Path:
    """Persiste o manifesto CEMPRE em JSON (D3, seção 9).

    Valida estruturalmente o manifesto (`validate_manifest`) ANTES de
    qualquer escrita — um manifesto estruturalmente inconsistente nunca é
    gravado. Um manifesto que registra uma execução INCOMPLETA
    (`completo=False`, com ausentes/falhas registrados) não é rejeitado
    por isso — só inconsistência lógica é rejeitada (seção 12). Por
    padrão (`overwrite=False`) falha explicitamente (`FileExistsError`)
    se `caminho` já existir. Cria o diretório pai quando necessário;
    escreve UTF-8, `ensure_ascii=False`, indentado e com chaves
    ordenadas.
    """
    caminho = Path(caminho)
    if caminho.suffix.lower() != ".json":
        raise ValueError(f"caminho do manifesto deve terminar em '.json': {caminho}")

    validate_manifest(manifesto)

    if caminho.exists() and not overwrite:
        raise FileExistsError(
            f"arquivo já existe e overwrite=False (padrão) — manifesto não sobrescreve silenciosamente: {caminho}"
        )

    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(manifesto, ensure_ascii=False, indent=2, sort_keys=True)
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def load_manifest(caminho: str | Path) -> dict[str, Any]:
    """Carrega e valida o manifesto CEMPRE persistido em JSON (D3, seção 10).

    Falha explicitamente (`FileNotFoundError`/`ValueError`) para arquivo
    ausente, formato não suportado, JSON inválido, conteúdo que não é um
    objeto JSON, ou qualquer violação do contrato verificado por
    `validate_manifest` — nunca corrige campos silenciosamente.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"manifesto não encontrado: {caminho}")
    if caminho.suffix.lower() != ".json":
        raise ValueError(f"formato não suportado para manifesto: {caminho.suffix!r}; esperado '.json'")

    texto = caminho.read_text(encoding="utf-8")
    try:
        manifesto = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ValueError(f"manifesto não é JSON válido ({caminho}): {exc}") from exc

    if not isinstance(manifesto, dict):
        raise ValueError(f"manifesto deve ser um objeto JSON (dict); recebido: {type(manifesto).__name__}")

    validate_manifest(manifesto)
    return manifesto


# ---------------------------------------------------------------------------
# D4 — orquestração nacional (dry run offline)
#
# COMPÕE D1 (build_national_request_plan/validate_national_request_plan),
# D2 (load_results_from_cache) e D3 (hash_plano_canonico/get_git_head) —
# nenhuma lógica de parsing, cache, long ou manifesto é duplicada aqui.
#
# `dry_run_national_pipeline` é inteiramente offline: NUNCA chama
# `fetch_request`, NUNCA chama `requests`, NUNCA escreve cache, long ou
# manifesto. É só uma simulação/diagnóstico. `run_national_pipeline` é o
# único ponto de entrada e recusa qualquer tentativa de execução real sem
# `autorizacao_extracao=True` explícito — ANTES de qualquer rede. Mesmo
# autorizado, a execução real ainda não está implementada nesta etapa
# (ver `run_national_pipeline`): a infraestrutura foi orquestrada e
# validada via dry run; o branch de execução real será habilitado somente
# após gate explícito de autorização de extração nacional
# (`docs/playbooks/ESTADO_ATUAL.md`).
# ---------------------------------------------------------------------------

MODO_DRY_RUN = "dry_run"
MODO_EXECUCAO_REAL = "execute"

_CAMINHO_LONG_NACIONAL_PADRAO = ROOT / "data" / "interim" / "cempre_long_2007_2019.parquet"
_CAMINHO_MANIFESTO_NACIONAL_PADRAO = ROOT / "data" / "raw" / "ibge" / "cempre" / "source_manifest.json"


@dataclass(frozen=True)
class NationalRunConfig:
    """Configuração explícita de um run nacional do pipeline CEMPRE (D4).

    Contrato específico do CEMPRE — não é um framework de configuração
    genérico. `modo` distingue `MODO_DRY_RUN` (padrão, seguro por
    construção) de `MODO_EXECUCAO_REAL` (guardado por
    `autorizacao_extracao`, ver `run_national_pipeline`). `anos`/
    `variaveis`/`fonte_tabela` são repassados diretamente para
    `build_national_request_plan` (D1) — `None` usa o contrato padrão
    (janela 2007-2019 completa e `VARIAVEIS_ESPERADAS`).
    """

    cache_dir: Path = CACHE_DIR
    calendario_path: Path | None = None
    caminho_long: Path = _CAMINHO_LONG_NACIONAL_PADRAO
    caminho_manifesto: Path = _CAMINHO_MANIFESTO_NACIONAL_PADRAO
    modo: str = MODO_DRY_RUN
    overwrite: bool = False
    anos: list[int] | None = None
    variaveis: set[int] | list[int] | None = None
    fonte_tabela: int = FONTE_TABELA


def _garantir_autorizacao_execucao_real(modo: str, autorizacao_extracao: bool) -> None:
    """Guarda explícita (D4, seção 4): nenhuma execução real prossegue sem
    `autorizacao_extracao=True` passado como parâmetro explícito da
    operação — nunca uma variável global escondida. Falha ANTES de
    qualquer chamada a `fetch_request`/rede.
    """
    if modo == MODO_EXECUCAO_REAL and not autorizacao_extracao:
        raise PermissionError(
            "execução real do pipeline nacional CEMPRE requer autorizacao_extracao=True "
            "explícito. Isso NÃO ocorreu automaticamente — extração nacional CEMPRE "
            "permanece NÃO AUTORIZADA (ver docs/playbooks/ESTADO_ATUAL.md)."
        )


def _classificar_resultado_cache(resultado: dict[str, Any]) -> str:
    """Classifica um resultado de `load_results_from_cache` (D2) em
    `'valido'` / `'ausente'` / `'invalido'` para o dry run (D4).

    NÃO duplica leitura/parsing de cache — só interpreta o contrato já
    produzido por `load_results_from_cache`/`_resultado_a_partir_do_cache`.
    Cache corrompido e payload com schema inválido caem ambos em
    `'invalido'` (comportamento conservador — seção 7: bloqueador
    operacional, nunca tratado automaticamente como cache miss).
    """
    if resultado.get("erro") is None and resultado.get("resultado") is not None:
        return "valido"
    erro = resultado.get("erro") or ""
    if erro.startswith("cache ausente"):
        return "ausente"
    return "invalido"


def dry_run_national_pipeline(config: NationalRunConfig) -> dict[str, Any]:
    """Simula, inteiramente OFFLINE, uma execução nacional do pipeline
    CEMPRE (D4, seção 5): responde "se a extração nacional fosse
    executada agora, exatamente o que aconteceria?" sem nunca chamar rede.

    Compõe (não duplica): `load_calendar_territorial` + `uf_list_from_calendario`,
    `build_national_request_plan` (que já chama `validate_national_request_plan`
    internamente, D1), `load_results_from_cache` (D2) e `hash_plano_canonico`/
    `get_git_head` (D3). NUNCA chama `fetch_request`, `requests.get`, nem
    escreve cache, long ou manifesto.

    `n_requests_que_exigiriam_rede` conta APENAS cache ausente — cache
    inválido/corrompido é um bloqueador operacional distinto (requer
    intervenção manual antes de qualquer execução real, seção 7), não uma
    simples falta de dado que uma execução real resolveria sozinha.
    Cache ausente, por si só, NUNCA é bloqueador: é exatamente o que uma
    futura execução real buscaria preencher (seção 9).
    """
    calendario = load_calendar_territorial(config.calendario_path)
    plano = build_national_request_plan(
        calendario=calendario,
        anos=config.anos,
        variaveis=config.variaveis,
        fonte_tabela=config.fonte_tabela,
    )

    resultados_cache = load_results_from_cache(plano, config.cache_dir)
    ids_validos: list[str] = []
    ids_ausentes: list[str] = []
    ids_invalidos: list[str] = []
    for resultado in resultados_cache:
        categoria = _classificar_resultado_cache(resultado)
        if categoria == "valido":
            ids_validos.append(resultado["request_id"])
        elif categoria == "ausente":
            ids_ausentes.append(resultado["request_id"])
        else:
            ids_invalidos.append(resultado["request_id"])

    caminho_long = Path(config.caminho_long)
    caminho_manifesto = Path(config.caminho_manifesto)
    conflito_long_existente = caminho_long.exists() and not config.overwrite
    conflito_manifesto_existente = caminho_manifesto.exists() and not config.overwrite

    bloqueadores: list[str] = []
    if ids_invalidos:
        bloqueadores.append(
            f"{len(ids_invalidos)} cache(s) inválido(s)/corrompido(s) — requer intervenção "
            f"manual antes de qualquer execução real: {sorted(ids_invalidos)}"
        )
    if conflito_long_existente:
        bloqueadores.append(f"long já existe e overwrite=False: {caminho_long}")
    if conflito_manifesto_existente:
        bloqueadores.append(f"manifesto já existe e overwrite=False: {caminho_manifesto}")

    anos_plano = sorted({item["ano"] for item in plano})
    variaveis_plano = sorted({variavel for item in plano for variavel in (item.get("variaveis") or [])})

    return {
        "modo": MODO_DRY_RUN,
        "fonte_tabela": config.fonte_tabela,
        "anos": anos_plano,
        "variaveis": variaveis_plano,
        "n_requests_esperados": len(plano),
        "hash_plano": hash_plano_canonico(plano),
        "n_cache_validos": len(ids_validos),
        "n_cache_ausentes": len(ids_ausentes),
        "n_cache_invalidos": len(ids_invalidos),
        "request_ids_cache_validos": sorted(ids_validos),
        "request_ids_cache_ausentes": sorted(ids_ausentes),
        "request_ids_cache_invalidos": sorted(ids_invalidos),
        "n_requests_que_exigiriam_rede": len(ids_ausentes),
        "request_ids_que_exigiriam_rede": sorted(ids_ausentes),
        "caminho_long_previsto": str(caminho_long),
        "caminho_manifesto_previsto": str(caminho_manifesto),
        "conflito_long_existente": conflito_long_existente,
        "conflito_manifesto_existente": conflito_manifesto_existente,
        "git_commit": get_git_head(),
        "pronto_para_execucao_real": not bloqueadores,
        "bloqueadores": bloqueadores,
    }


def format_dry_run_summary(relatorio: dict[str, Any]) -> str:
    """Resumo humano curto do relatório de dry run (D4, seção 10).

    Apenas formata campos já calculados por `dry_run_national_pipeline` —
    não decide nenhum gate (`pronto_para_execucao_real` é diagnóstico
    técnico, não `EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA`).
    """
    linhas = [
        f"Modo: {relatorio['modo']}",
        f"Requests esperados: {relatorio['n_requests_esperados']}",
        f"Caches válidos: {relatorio['n_cache_validos']}",
        f"Caches ausentes: {relatorio['n_cache_ausentes']}",
        f"Caches inválidos: {relatorio['n_cache_invalidos']}",
        f"Requests que exigiriam rede: {relatorio['n_requests_que_exigiriam_rede']}",
        f"Long prevista: {relatorio['caminho_long_previsto']}",
        f"Manifesto previsto: {relatorio['caminho_manifesto_previsto']}",
        f"Bloqueadores: {len(relatorio['bloqueadores'])}",
        f"Pronto tecnicamente para execução: {'SIM' if relatorio['pronto_para_execucao_real'] else 'NÃO'}",
    ]
    return "\n".join(linhas)


def run_national_pipeline(
    config: NationalRunConfig,
    modo: str = MODO_DRY_RUN,
    autorizacao_extracao: bool = False,
) -> dict[str, Any]:
    """Ponto de entrada único do orquestrador nacional CEMPRE (D4, seção 11).

    `dry_run=True` (via `modo=MODO_DRY_RUN`) é o padrão e nunca chama
    rede. Qualquer tentativa de `modo=MODO_EXECUCAO_REAL` sem
    `autorizacao_extracao=True` explícito falha imediatamente
    (`PermissionError`), ANTES de qualquer request — ver
    `_garantir_autorizacao_execucao_real`.

    A execução real ainda NÃO está implementada nesta etapa: mesmo
    autorizada, levanta `NotImplementedError` explícito. A infraestrutura
    (D1-D3) já foi orquestrada e validada via dry run; o branch de
    execução real será habilitado somente após gate explícito de
    autorização de extração nacional — isto NÃO é esse gate.
    """
    _garantir_autorizacao_execucao_real(modo, autorizacao_extracao)

    if modo == MODO_DRY_RUN:
        return dry_run_national_pipeline(config)

    if modo == MODO_EXECUCAO_REAL:
        raise NotImplementedError(
            "execução real do pipeline nacional CEMPRE ainda não está implementada (D4). "
            "A infraestrutura foi orquestrada e validada via dry run; o branch de execução "
            "real será habilitado somente após gate explícito de autorização de extração "
            "nacional (ver docs/playbooks/ESTADO_ATUAL.md)."
        )

    raise ValueError(f"modo de execução desconhecido: {modo!r} (esperado {MODO_DRY_RUN!r} ou {MODO_EXECUCAO_REAL!r})")
