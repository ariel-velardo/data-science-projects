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
import time
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
        try:
            em_cache = load_cached_request(spec["request_id"], cache_dir)
        except ValueError as exc:
            logger.error("request_id=%s cache corrompido: %s", spec["request_id"], exc)
            return {
                "request_id": spec["request_id"], "url": spec["url"], "tentativas": 0,
                "status_http": None, "tamanho": None, "hash_resposta_raw": None,
                "resultado": None, "erro": str(exc), "de_cache": True,
            }
        if em_cache is not None:
            valido, motivo = validate_sidra_payload(em_cache["resultado"])
            if not valido:
                logger.error("request_id=%s payload em cache é inválido: %s", spec["request_id"], motivo)
                return {
                    "request_id": spec["request_id"], "url": spec["url"], "tentativas": 0,
                    "status_http": None, "tamanho": em_cache["tamanho"],
                    "hash_resposta_raw": em_cache["hash_resposta_raw"],
                    "resultado": None, "erro": f"payload em cache inválido: {motivo}", "de_cache": True,
                }
            logger.info("request_id=%s cache hit — nenhuma chamada de rede", spec["request_id"])
            return {
                "request_id": spec["request_id"], "url": spec["url"], "tentativas": 0,
                "status_http": 200, "tamanho": em_cache["tamanho"],
                "hash_resposta_raw": em_cache["hash_resposta_raw"],
                "resultado": em_cache["resultado"], "erro": None, "de_cache": True,
            }

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
