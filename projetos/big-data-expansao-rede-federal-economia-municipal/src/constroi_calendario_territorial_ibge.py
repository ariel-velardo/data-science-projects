"""
constroi_calendario_territorial_ibge.py
=======================================
Constrói o calendário territorial município-ano OFICIAL para 2007–2019 a
partir das edições anuais da Divisão Territorial Brasileira (DTB) do IBGE.

Pergunta operacional: para cada código municipal IBGE que aparece em alguma
edição anual da DTB de 2007 a 2019, o município constava da divisão
territorial oficial daquele ano?

Regra única de derivação:
    municipio_existia_no_ano = código presente na lista de municípios da
    edição DTB do próprio ano.

Nenhuma contagem histórica, lista de municípios novos ou data de criação é
fixada neste código: toda a história territorial emerge dos arquivos
oficiais. O código fixa apenas o FORMATO de cada edição (arquivo, aba,
colunas) e a impressão digital (tamanho/SHA-256) dos arquivos oficiais, para
que qualquer alteração da fonte seja detectada em vez de absorvida em
silêncio.

Esta rotina NÃO:
  - lê, extrai ou altera dados do CEMPRE;
  - altera cadastros causais, tratamento ou controles (a reconciliação com
    os códigos do projeto é somente leitura e somente diagnóstica);
  - resolve identidade de município por nome;
  - faz matching, estimação ou qualquer análise causal.

Fonte (ver outputs/diagnostics/calendario_territorial_manifest.json):
  IBGE, Divisão Territorial Brasileira, edições 2007–2019
  https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/divisao_territorial/
  Arquivos .zip originais em data/raw/ibge/territorio/dtb/ (não versionados;
  lidos em memória, sem extração em disco).

Saídas:
  data/processed/calendario_territorial_municipios_2007_2019.parquet
  outputs/diagnostics/calendario_territorial_contagem_por_ano.csv
  outputs/diagnostics/calendario_territorial_transicoes.csv
  outputs/diagnostics/calendario_territorial_reconciliacao_projeto.csv
  outputs/diagnostics/calendario_territorial_manifest.json

Uso:
  python src/constroi_calendario_territorial_ibge.py                 # baixa só o que faltar
  python src/constroi_calendario_territorial_ibge.py --sem-download  # exige os .zip locais
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import xlrd

# ---------------------------------------------------------------------------
# Configuração global
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DTB_RAW_DIR = ROOT / "data" / "raw" / "ibge" / "territorio" / "dtb"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS_DIAGNOSTICS = ROOT / "outputs" / "diagnostics"

OUT_CALENDARIO = DATA_PROCESSED / "calendario_territorial_municipios_2007_2019.parquet"
OUT_CONTAGEM = OUTPUTS_DIAGNOSTICS / "calendario_territorial_contagem_por_ano.csv"
OUT_TRANSICOES = OUTPUTS_DIAGNOSTICS / "calendario_territorial_transicoes.csv"
OUT_RECONCILIACAO = OUTPUTS_DIAGNOSTICS / "calendario_territorial_reconciliacao_projeto.csv"
OUT_MANIFEST = OUTPUTS_DIAGNOSTICS / "calendario_territorial_manifest.json"

# Insumos do projeto lidos SOMENTE para a reconciliação estrutural de códigos.
FASE_II_MUNICIPIOS_PATH = DATA_PROCESSED / "fase_ii_municipios.parquet"
POOL_CANDIDATO_PATH = DATA_PROCESSED / "pool_candidato_controles_sem_exposicao_2007_2019.parquet"
CADASTRO_ELEGIBILIDADE_PATH = DATA_PROCESSED / "cadastro_elegibilidade_controles_2007_2019.parquet"

ANO_INICIAL, ANO_FINAL = 2007, 2019
ANOS_JANELA = tuple(range(ANO_INICIAL, ANO_FINAL + 1))

COD = "codigo_municipio_ibge"
EXISTIA = "municipio_existia_no_ano"

CODIGO_MUNICIPIO_RE = re.compile(r"[0-9]{7}")
CODIGO_PARCIAL_RE = re.compile(r"[0-9]{5}")
CODIGO_UF_RE = re.compile(r"[0-9]{2}")

ORGAO = "Instituto Brasileiro de Geografia e Estatística (IBGE)"
FONTE_TERRITORIAL = "IBGE - Divisão Territorial Brasileira (DTB)"
PAGINA_PRODUTO = (
    "https://www.ibge.gov.br/geociencias/organizacao-do-territorio/estrutura-territorial/"
    "23701-divisao-territorial-brasileira.html"
)
DTB_FTP_BASE = "https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/divisao_territorial"
# Instante do download original dos 13 arquivos (registrado na sessão de
# construção). Arquivos baixados por uma execução futura recebem o instante
# real do novo download.
DATA_ACESSO_REGISTRADA = "2026-09-15T03:08:26Z"

# Usado SOMENTE para imprimir/registrar a auditoria do caso já conhecido no
# CEMPRE. Nunca participa da construção do calendário.
CASO_AUDITORIA_PESCARIA_BRAVA = "4212650"

# Tabela estática de UFs (código IBGE de 2 dígitos -> sigla, nome). Não é
# história territorial: é conferida, em cada edição, contra a coluna Nome_UF
# da própria DTB.
UF_CODIGO_PARA_SIGLA_NOME = {
    "11": ("RO", "Rondônia"), "12": ("AC", "Acre"), "13": ("AM", "Amazonas"),
    "14": ("RR", "Roraima"), "15": ("PA", "Pará"), "16": ("AP", "Amapá"),
    "17": ("TO", "Tocantins"), "21": ("MA", "Maranhão"), "22": ("PI", "Piauí"),
    "23": ("CE", "Ceará"), "24": ("RN", "Rio Grande do Norte"), "25": ("PB", "Paraíba"),
    "26": ("PE", "Pernambuco"), "27": ("AL", "Alagoas"), "28": ("SE", "Sergipe"),
    "29": ("BA", "Bahia"), "31": ("MG", "Minas Gerais"), "32": ("ES", "Espírito Santo"),
    "33": ("RJ", "Rio de Janeiro"), "35": ("SP", "São Paulo"), "41": ("PR", "Paraná"),
    "42": ("SC", "Santa Catarina"), "43": ("RS", "Rio Grande do Sul"),
    "50": ("MS", "Mato Grosso do Sul"), "51": ("MT", "Mato Grosso"), "52": ("GO", "Goiás"),
    "53": ("DF", "Distrito Federal"),
}


def _esq(
    subdiretorio_ftp: str, arquivo: str, tamanho_bytes: int, sha256: str,
    membro_xls: str, aba: str, nivel: str, coluna_uf: str, coluna_codigo: str,
    formato_codigo: str, coluna_nome_municipio: str, coluna_codigo_parcial: str | None = None,
) -> dict[str, Any]:
    return {
        "subdiretorio_ftp": subdiretorio_ftp, "arquivo": arquivo,
        "tamanho_bytes": tamanho_bytes, "sha256": sha256,
        "membro_xls": membro_xls, "aba": aba, "nivel": nivel,
        "coluna_uf": coluna_uf, "coluna_nome_uf": "Nome_UF",
        "coluna_codigo": coluna_codigo, "formato_codigo": formato_codigo,
        "coluna_codigo_parcial": coluna_codigo_parcial,
        "coluna_nome_municipio": coluna_nome_municipio,
    }


# Formato de cada edição anual, conforme inspecionado nos arquivos oficiais.
#   nivel="distrito": uma linha por distrito/subdistrito (código municipal repetido);
#   nivel="municipio": uma linha por município.
#   formato_codigo="uf+5": código municipal de 5 dígitos, prefixado pela coluna de UF;
#   formato_codigo="completo7": código municipal de 7 dígitos já completo.
_COLS_2015_2019 = dict(coluna_uf="UF", coluna_codigo="Código Município Completo", formato_codigo="completo7",
                       coluna_nome_municipio="Nome_Município", coluna_codigo_parcial="Município")
ESQUEMAS_DTB: dict[int, dict[str, Any]] = {
    2007: _esq("2007", "dtb_2007.zip", 461511,
               "dab746c294e13db3892b959258d84d4cc8dd5e2d0cb5e9cbc6e02a03ff58c3c9",
               "DTB_2007.xls", "DTB_Nome_Comum", "distrito", "UF", "Município", "uf+5", "Nome_Município"),
    2008: _esq("2008", "dtb_2008.zip", 483339,
               "562e92c558a7180165032b352d2da9daf06b5fe7930e499b6f5bc365c832914a",
               "DTB_2008.xls", "DTB_Nome_Comum", "distrito", "UF", "Município", "uf+5", "Nome_Município"),
    2009: _esq("2009", "dtb_05_05_2009.zip", 482249,
               "40771908994960ed0037d8e925998e078263f91559956ac251d48ce7dcbdbea6",
               "DTB_05_05_2009.xls", "DTB_05_05_2009n", "distrito", "UF", "Município", "completo7",
               "Município_Nome"),
    2010: _esq("2010", "dtb_2010.zip", 206919,
               "4cfbe9ae50b6e5d67179050a9041993940a2548abdba0057e6b9677f49fa95e1",
               "dtb_2010.xls", "Município", "municipio", "UF", "Município", "completo7", "Nome_Munic"),
    2011: _esq("2011", "dtb_2011.zip", 194667,
               "1981ccf854e78be8206f9cc6ac90c16ae5206d4bf2650e725750bf56b9e60f16",
               "dtb_2011.xls", "DTB_2011", "municipio", "UF", "Munic", "uf+5", "Nome_Munic"),
    2012: _esq("2012", "dtb_2012.zip", 178326,
               "4c13cebe5116bc9f8a76f6074ae40e757d45afb1c7147ff04ed261d69369aca0",
               "dtb_2012.xls", "Estrutura_2012___Município", "municipio", "UF", "Munic", "uf+5", "Nome_Munic"),
    2013: _esq("2013", "dtb_2013.zip", 469155,
               "eeec2bde37b901a363f4a3973fb65ca028edaa481212253cc8b821db5f3d2c54",
               "dtb_2013.xls", "dtb_2013", "distrito", "Uf", "Município", "uf+5", "Nome_Município"),
    2014: _esq("2014", "dtb_2014_v2.zip", 2229161,
               "ceed87ef11e1477eaf3ad4f5f948746ca699187f6558e98e91589210af0a48d1",
               "DTB_2014_v2/DTB_2014_Municipio.xls", "Plan1", "municipio", "UF", "Cod Municipio Completo",
               "completo7", "Nome_Município", "Município"),
    2015: _esq("2015", "dtb_2015_v2.zip", 1494824,
               "d101cffe61a81c8a4b8dedae29ee0dea429fd07e7816225d88d5c51b98ab5fd3",
               "dtb_2015/RELATORIO_DTB_BRASIL_MUNICIPIO.xls", "DTB_2015_Municipio", "municipio", **_COLS_2015_2019),
    2016: _esq("2016", "DTB_2016_v2.zip", 1514388,
               "d5ce045b0fe4a9f5316625c9922bb95013b0ed8113b39efe76340fce89fabdac",
               "DTB_2016_v2/DTB_2016/DTB_BRASIL_MUNICIPIO.xls", "DTB_2016_Municipio", "municipio", **_COLS_2015_2019),
    2017: _esq("2017", "DTB_2017.zip", 1492911,
               "9788c2192465bc2f09c9163aa456332db5a489b9be7fe7e15ff076206b00e983",
               "DTB_BRASIL_MUNICIPIO.xls", "DTB_2017_Municipio", "municipio", **_COLS_2015_2019),
    2018: _esq("2018", "DTB_2018.zip", 1482231,
               "7e6237235cbf2a04b245f6e4d085f608de10ce674f64c93ba5b523b57c0cdb0d",
               "RELATORIO_DTB_BRASIL_MUNICIPIO.xls", "DTB_2018_Municipio", "municipio", **_COLS_2015_2019),
    2019: _esq("2019", "DTB_2019_v2.zip", 1928272,
               "2aee1cfc43471245903aa2d27f4e42da4f465089a52c8c0f12a4221e32572fd3",
               "RELATORIO_DTB_BRASIL_MUNICIPIO.xls", "DTB_2019_Municipio", "municipio", **_COLS_2015_2019),
}

COLUNAS_LISTA_ANUAL = ["ano", COD, "nome_municipio", "uf_codigo", "uf_sigla", "nome_uf_fonte"]

COLUNAS_CALENDARIO = [
    COD, "ano", EXISTIA, "nome_municipio_ano", "uf_codigo", "uf_sigla",
    "fonte_territorial", "versao_fonte", "fonte_ano", "observacao_territorial",
]

CLASSES_EVENTO = (
    "entrada", "saida", "mudanca_nome", "mudanca_uf", "possivel_mudanca_codigo", "lacuna_intermediaria",
)

COLUNAS_TRANSICOES = [
    "tipo_registro", "tipo_evento", "n_casos", COD, "ano_anterior", "ano_evento",
    "nome_anterior", "nome_novo", "uf_sigla", "nome_igual_apos_normalizacao", "observacao",
]


# ---------------------------------------------------------------------------
# 1. Utilitários e validações elementares
# ---------------------------------------------------------------------------


def _nfc(texto: str) -> str:
    return unicodedata.normalize("NFC", texto)


def normaliza_nome_para_comparacao(nome: str) -> str:
    """Somente para DIAGNÓSTICO (nunca para identidade): remove acentos,
    caixa, espaços e pontuação."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", sem_acento.casefold())


def valida_codigo_municipal(codigo: Any, contexto: str = "código municipal") -> str:
    if not isinstance(codigo, str) or not CODIGO_MUNICIPIO_RE.fullmatch(codigo):
        raise ValueError(
            f"{contexto}: codigo_municipio_ibge inválido (esperado texto com exatamente 7 dígitos): {codigo!r}."
        )
    return codigo


def _valida_serie_codigos(codigos: Any, contexto: str) -> None:
    invalidos = [c for c in codigos if not isinstance(c, str) or not CODIGO_MUNICIPIO_RE.fullmatch(c)]
    if invalidos:
        raise ValueError(
            f"{contexto}: codigo_municipio_ibge inválido (esperado texto com exatamente 7 dígitos) em "
            f"{len(invalidos)} casos. Exemplos: {invalidos[:5]}"
        )


def valida_ano(ano: Any, contexto: str = "ano") -> int:
    if isinstance(ano, (bool, np.bool_)) or not isinstance(ano, (int, np.integer)):
        raise ValueError(f"{contexto}: ano deve ser inteiro; recebido {ano!r}.")
    if not ANO_INICIAL <= int(ano) <= ANO_FINAL:
        raise ValueError(f"{contexto}: ano {ano} fora da janela {ANO_INICIAL}–{ANO_FINAL}.")
    return int(ano)


def _celula_texto(valor: Any, coluna: str, contexto: str) -> str:
    if not isinstance(valor, str):
        raise ValueError(
            f"{contexto}: coluna '{coluna}' contém célula não textual ({valor!r}); formato inesperado para a edição."
        )
    return valor.strip()


def sha256_bytes(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# 2. Obtenção e integridade dos arquivos oficiais
# ---------------------------------------------------------------------------


def url_dtb(esquema: dict[str, Any]) -> str:
    return f"{DTB_FTP_BASE}/{esquema['subdiretorio_ftp']}/{esquema['arquivo']}"


def verifica_integridade_arquivo(caminho: Path, sha256_esperado: str, tamanho_esperado: int) -> dict[str, Any]:
    tamanho = caminho.stat().st_size
    sha = sha256_arquivo(caminho)
    if tamanho != tamanho_esperado or sha != sha256_esperado:
        raise ValueError(
            f"{caminho.name}: arquivo local difere do registrado (tamanho {tamanho} vs {tamanho_esperado}; "
            f"sha256 {sha} vs {sha256_esperado}). A fonte não é usada em silêncio: investigar antes de prosseguir."
        )
    return {"tamanho_bytes": tamanho, "sha256": sha}


def garante_arquivo_dtb(
    ano: int, destino: Path = DTB_RAW_DIR, permitir_download: bool = True,
    sessao: Any = None, timeout: int = 180,
) -> dict[str, Any]:
    """Usa o .zip local se existir (validando tamanho/SHA-256); senão baixa da
    URL oficial e só grava depois de confirmar o SHA-256 registrado."""
    esquema = ESQUEMAS_DTB[valida_ano(ano, "garante_arquivo_dtb")]
    caminho = destino / esquema["arquivo"]
    url = url_dtb(esquema)
    if caminho.exists():
        integridade = verifica_integridade_arquivo(caminho, esquema["sha256"], esquema["tamanho_bytes"])
        return {**integridade, "caminho": caminho, "url": url, "data_acesso": DATA_ACESSO_REGISTRADA,
                "origem_local": "arquivo_preexistente_validado_por_sha256"}
    if not permitir_download:
        raise FileNotFoundError(f"DTB {ano}: arquivo oficial ausente em {caminho} e download desabilitado.")

    sessao = sessao or requests.Session()
    resposta = sessao.get(url, timeout=timeout)
    resposta.raise_for_status()
    conteudo = resposta.content
    sha = sha256_bytes(conteudo)
    if sha != esquema["sha256"] or len(conteudo) != esquema["tamanho_bytes"]:
        raise ValueError(
            f"DTB {ano}: conteúdo baixado de {url} difere do registrado (tamanho {len(conteudo)} vs "
            f"{esquema['tamanho_bytes']}; sha256 {sha} vs {esquema['sha256']}). Arquivo NÃO gravado."
        )
    destino.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(conteudo)
    return {"tamanho_bytes": len(conteudo), "sha256": sha, "caminho": caminho, "url": url,
            "data_acesso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "origem_local": "baixado_nesta_execucao"}


def le_planilha_dtb(caminho_zip: Path, esquema: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Lê a aba municipal da edição diretamente de dentro do .zip, preservando
    todas as células como vieram (sem coerção de tipo)."""
    with zipfile.ZipFile(caminho_zip) as zf:
        membros = zf.namelist()
        if esquema["membro_xls"] not in membros:
            raise ValueError(
                f"{caminho_zip.name}: membro esperado '{esquema['membro_xls']}' ausente; membros: {membros}."
            )
        conteudo = zf.read(esquema["membro_xls"])
    with open(os.devnull, "w") as silencioso:  # xlrd emite avisos OLE2 inofensivos em 2 edições
        livro = xlrd.open_workbook(file_contents=conteudo, logfile=silencioso)
        abas = [_nfc(nome) for nome in livro.sheet_names()]
        if _nfc(esquema["aba"]) not in abas:
            raise ValueError(f"{caminho_zip.name}: aba esperada '{esquema['aba']}' ausente; abas: {abas}.")
        planilha = livro.sheet_by_index(abas.index(_nfc(esquema["aba"])))
        cabecalho = [_nfc(str(v)).strip() for v in planilha.row_values(0)]
        linhas = [planilha.row_values(r) for r in range(1, planilha.nrows)]
    if len(set(cabecalho)) != len(cabecalho):
        raise ValueError(f"{caminho_zip.name}: cabeçalho com nomes de coluna repetidos: {cabecalho}.")
    raw = pd.DataFrame(linhas, columns=cabecalho, dtype=object)
    meta = {
        "membro_xls": esquema["membro_xls"], "sha256_membro_xls": sha256_bytes(conteudo),
        "tamanho_membro_xls_bytes": len(conteudo), "aba": esquema["aba"], "abas_disponiveis": abas,
        "colunas_originais": cabecalho, "n_linhas_brutas": len(raw),
    }
    return raw, meta


# ---------------------------------------------------------------------------
# 3. Normalização e validação das listas anuais
# ---------------------------------------------------------------------------


def colunas_usadas_do_esquema(esquema: dict[str, Any]) -> list[str]:
    colunas = [esquema["coluna_uf"], esquema["coluna_nome_uf"], esquema["coluna_codigo"],
               esquema["coluna_nome_municipio"]]
    if esquema.get("coluna_codigo_parcial"):
        colunas.append(esquema["coluna_codigo_parcial"])
    return colunas


def normaliza_lista_anual(raw: pd.DataFrame, ano: int, esquema: dict[str, Any]) -> pd.DataFrame:
    """Traduz a planilha bruta de uma edição para uma linha por código
    municipal: ano, código (7 dígitos), nome, UF. Qualquer desvio de formato
    interrompe a construção."""
    contexto = f"DTB {ano}"
    ano = valida_ano(ano, contexto)
    faltantes = [c for c in colunas_usadas_do_esquema(esquema) if c not in raw.columns]
    if faltantes:
        raise ValueError(
            f"{contexto}: schema anual inesperado — colunas ausentes {faltantes}; "
            f"colunas encontradas {list(raw.columns)}."
        )
    if esquema["nivel"] not in ("municipio", "distrito"):
        raise ValueError(f"{contexto}: nível de planilha desconhecido {esquema['nivel']!r}.")
    if esquema["formato_codigo"] not in ("completo7", "uf+5"):
        raise ValueError(f"{contexto}: formato de código desconhecido {esquema['formato_codigo']!r}.")
    if raw.empty:
        raise ValueError(f"{contexto}: planilha sem linhas de dados.")

    uf = [_celula_texto(v, esquema["coluna_uf"], contexto) for v in raw[esquema["coluna_uf"]]]
    ufs_invalidas = sorted({u for u in uf if not CODIGO_UF_RE.fullmatch(u) or u not in UF_CODIGO_PARA_SIGLA_NOME})
    if ufs_invalidas:
        raise ValueError(f"{contexto}: código de UF inválido ou desconhecido: {ufs_invalidas[:5]}.")

    codigo_bruto = [_celula_texto(v, esquema["coluna_codigo"], contexto) for v in raw[esquema["coluna_codigo"]]]
    if esquema["formato_codigo"] == "uf+5":
        parciais_invalidos = [c for c in codigo_bruto if not CODIGO_PARCIAL_RE.fullmatch(c)]
        if parciais_invalidos:
            raise ValueError(
                f"{contexto}: código municipal de 5 dígitos inválido em {len(parciais_invalidos)} linhas. "
                f"Exemplos: {parciais_invalidos[:5]}"
            )
        codigos = [u + c for u, c in zip(uf, codigo_bruto)]
    else:
        codigos = codigo_bruto
    _valida_serie_codigos(codigos, contexto)

    prefixo_divergente = [(c, u) for c, u in zip(codigos, uf) if c[:2] != u]
    if prefixo_divergente:
        raise ValueError(
            f"{contexto}: prefixo do código municipal diverge da coluna de UF em {len(prefixo_divergente)} linhas. "
            f"Exemplos: {prefixo_divergente[:5]}"
        )
    if esquema.get("coluna_codigo_parcial"):
        coluna = esquema["coluna_codigo_parcial"]
        parcial = [_celula_texto(v, coluna, contexto) for v in raw[coluna]]
        divergentes = [(c, p) for c, p in zip(codigos, parcial) if c[2:] != p]
        if divergentes:
            raise ValueError(
                f"{contexto}: código completo diverge de UF + '{coluna}' em {len(divergentes)} linhas. "
                f"Exemplos: {divergentes[:5]}"
            )

    nome_uf = [_celula_texto(v, esquema["coluna_nome_uf"], contexto) for v in raw[esquema["coluna_nome_uf"]]]
    nome_uf_divergente = sorted({
        (u, n) for u, n in zip(uf, nome_uf)
        if normaliza_nome_para_comparacao(n) != normaliza_nome_para_comparacao(UF_CODIGO_PARA_SIGLA_NOME[u][1])
    })
    if nome_uf_divergente:
        raise ValueError(f"{contexto}: Nome_UF incompatível com o código de UF: {nome_uf_divergente[:5]}.")

    nomes = [_celula_texto(v, esquema["coluna_nome_municipio"], contexto) for v in raw[esquema["coluna_nome_municipio"]]]
    if any(n == "" for n in nomes):
        raise ValueError(f"{contexto}: nome de município vazio em {sum(n == '' for n in nomes)} linhas.")

    lista = pd.DataFrame({COD: codigos, "nome_municipio": nomes, "uf_codigo": uf, "nome_uf_fonte": nome_uf})
    if esquema["nivel"] == "municipio":
        duplicados = lista.loc[lista[COD].duplicated(keep=False), COD]
        if not duplicados.empty:
            raise ValueError(
                f"{contexto}: codigo_municipio_ibge duplicado na lista municipal ({duplicados.nunique()} códigos). "
                f"Exemplos: {sorted(set(duplicados))[:5]}"
            )
    else:
        variantes = lista.drop_duplicates().groupby(COD).size()
        conflitantes = variantes[variantes > 1]
        if not conflitantes.empty:
            raise ValueError(
                f"{contexto}: nomes/UF divergentes para o mesmo código entre linhas de distrito "
                f"({len(conflitantes)} códigos). Exemplos: {conflitantes.index[:5].tolist()}"
            )
        lista = lista.drop_duplicates(subset=[COD])

    lista.insert(0, "ano", ano)
    lista["uf_sigla"] = lista["uf_codigo"].map(lambda u: UF_CODIGO_PARA_SIGLA_NOME[u][0])
    return lista.sort_values(COD, kind="stable").reset_index(drop=True)[COLUNAS_LISTA_ANUAL]


def valida_lista_anual(lista: pd.DataFrame, ano: int) -> None:
    contexto = f"lista anual DTB {ano}"
    valida_ano(ano, contexto)
    faltantes = [c for c in COLUNAS_LISTA_ANUAL if c not in lista.columns]
    if faltantes:
        raise ValueError(f"{contexto}: colunas ausentes {faltantes}.")
    if lista.empty:
        raise ValueError(f"{contexto}: lista vazia.")
    _valida_serie_codigos(lista[COD], contexto)
    if (lista["ano"] != ano).any():
        raise ValueError(f"{contexto}: coluna ano contém valor diferente de {ano}.")
    duplicados = lista.loc[lista[COD].duplicated(keep=False), COD]
    if not duplicados.empty:
        raise ValueError(
            f"{contexto}: duplicidade de código-ano na fonte anual ({duplicados.nunique()} códigos). "
            f"Exemplos: {sorted(set(duplicados))[:5]}"
        )


# ---------------------------------------------------------------------------
# 4. União, grade município-ano e validação do calendário
# ---------------------------------------------------------------------------


def constroi_uniao_codigos(listas: dict[int, pd.DataFrame]) -> list[str]:
    if not listas:
        raise ValueError("união de códigos: nenhuma lista anual informada.")
    return sorted(set().union(*(set(lista[COD]) for lista in listas.values())))


def _observacoes_territoriais(calendario: pd.DataFrame, anos: list[int]) -> list[str | None]:
    """Espera o calendário ordenado por (código, ano) com todos os anos para
    cada código. Texto derivado apenas da presença/nome nas listas anuais."""
    ano_anterior = {atual: anterior for anterior, atual in zip(anos, anos[1:])}
    presentes = calendario.loc[calendario[EXISTIA]]
    primeiro = presentes.groupby(COD)["ano"].min().to_dict()
    ultimo = presentes.groupby(COD)["ano"].max().to_dict()

    observacoes: list[str | None] = []
    codigo_anterior = existia_anterior = nome_anterior = None
    for codigo, ano, existia, nome in zip(
        calendario[COD], calendario["ano"], calendario[EXISTIA], calendario["nome_municipio_ano"]
    ):
        if codigo != codigo_anterior:
            existia_anterior, nome_anterior = None, None
        partes = []
        p, u = primeiro[codigo], ultimo[codigo]
        if not existia:
            if ano < p:
                partes.append(f"código ausente da DTB {ano}; primeira presença na janela: DTB {p}")
            elif ano > u:
                partes.append(f"código ausente da DTB {ano}; última presença na janela: DTB {u}")
            else:
                partes.append(f"código ausente da DTB {ano}; lacuna entre presenças (DTB {p} a DTB {u})")
        else:
            anterior = ano_anterior.get(int(ano))
            if existia_anterior is False:
                sufixo = "" if ano == p else " (reentrada após lacuna)"
                partes.append(f"entrada no calendário: código ausente da DTB {anterior}{sufixo}")
            if existia_anterior is True and nome != nome_anterior:
                partes.append(f"nome difere da DTB {anterior}: '{nome_anterior}'")
        observacoes.append("; ".join(partes) if partes else None)
        codigo_anterior, existia_anterior, nome_anterior = codigo, bool(existia), nome
    return observacoes


def constroi_calendario(
    listas: dict[int, pd.DataFrame], proveniencia_por_ano: dict[int, dict[str, str]]
) -> pd.DataFrame:
    anos = sorted(listas)
    for ano in anos:
        valida_ano(ano, "constroi_calendario")
    sem_proveniencia = [a for a in anos if a not in proveniencia_por_ano]
    if sem_proveniencia:
        raise ValueError(f"constroi_calendario: proveniência ausente para os anos {sem_proveniencia}.")

    codigos = constroi_uniao_codigos(listas)
    grade = pd.DataFrame([(c, a) for c in codigos for a in anos], columns=[COD, "ano"])
    presentes = pd.concat([listas[a][[COD, "ano", "nome_municipio"]] for a in anos], ignore_index=True)
    calendario = grade.merge(presentes, on=[COD, "ano"], how="left", validate="one_to_one", indicator=True)
    calendario[EXISTIA] = (calendario["_merge"] == "both").astype(bool)
    calendario = calendario.drop(columns="_merge").rename(columns={"nome_municipio": "nome_municipio_ano"})

    calendario["uf_codigo"] = calendario[COD].str[:2]
    calendario["uf_sigla"] = calendario["uf_codigo"].map(lambda u: UF_CODIGO_PARA_SIGLA_NOME[u][0])
    calendario["fonte_territorial"] = FONTE_TERRITORIAL
    calendario["versao_fonte"] = calendario["ano"].map(lambda a: proveniencia_por_ano[a]["versao_fonte"])
    calendario["fonte_ano"] = calendario["ano"].map(lambda a: proveniencia_por_ano[a]["fonte_ano"])
    calendario = calendario.sort_values([COD, "ano"], kind="stable").reset_index(drop=True)
    calendario["observacao_territorial"] = _observacoes_territoriais(calendario, anos)
    return calendario[COLUNAS_CALENDARIO]


def valida_calendario(calendario: pd.DataFrame, listas: dict[int, pd.DataFrame]) -> None:
    contexto = "calendário territorial"
    faltantes = [c for c in COLUNAS_CALENDARIO if c not in calendario.columns]
    if faltantes:
        raise ValueError(f"{contexto}: colunas ausentes {faltantes}.")
    _valida_serie_codigos(calendario[COD], contexto)
    for ano in calendario["ano"].unique():
        valida_ano(ano, contexto)
    if set(calendario["ano"].unique()) != set(ANOS_JANELA) or set(listas) != set(ANOS_JANELA):
        raise ValueError(
            f"{contexto}: anos do calendário {sorted(calendario['ano'].unique())} / das listas {sorted(listas)} "
            f"não cobrem exatamente {ANO_INICIAL}–{ANO_FINAL}."
        )
    duplicados = calendario.duplicated([COD, "ano"], keep=False)
    if duplicados.any():
        raise ValueError(f"{contexto}: duplicidade (codigo_municipio_ibge, ano) em {int(duplicados.sum())} linhas.")
    if calendario[EXISTIA].isna().any():
        raise ValueError(f"{contexto}: {EXISTIA} contém nulo.")
    if calendario[EXISTIA].dtype != bool:
        raise ValueError(f"{contexto}: {EXISTIA} deve ser bool; dtype observado {calendario[EXISTIA].dtype}.")

    linhas_por_codigo = calendario.groupby(COD).size()
    fora = linhas_por_codigo[linhas_por_codigo != len(ANOS_JANELA)]
    if not fora.empty:
        raise ValueError(
            f"{contexto}: {len(fora)} código(s) não tem exatamente {len(ANOS_JANELA)} linhas. "
            f"Exemplos: {fora.head(5).to_dict()}"
        )
    if set(calendario[COD]) != set(constroi_uniao_codigos(listas)):
        raise ValueError(f"{contexto}: conjunto de códigos difere da união das listas anuais oficiais.")

    for ano in ANOS_JANELA:
        verdadeiros = set(calendario.loc[(calendario["ano"] == ano) & calendario[EXISTIA], COD])
        oficiais = set(listas[ano][COD])
        sem_fonte = sorted(verdadeiros - oficiais)
        if sem_fonte:
            raise ValueError(
                f"{contexto}: {len(sem_fonte)} código(s) marcado True sem constar da lista oficial DTB {ano}. "
                f"Exemplos: {sem_fonte[:5]}"
            )
        marcados_falso = sorted(oficiais - verdadeiros)
        if marcados_falso:
            raise ValueError(
                f"{contexto}: {len(marcados_falso)} código(s) consta da lista oficial DTB {ano} mas está marcado "
                f"False. Exemplos: {marcados_falso[:5]}"
            )
        if len(verdadeiros) != len(listas[ano]):
            raise ValueError(
                f"{contexto}: contagem anual {ano} ({len(verdadeiros)}) difere da lista oficial ({len(listas[ano])})."
            )

    if (calendario[EXISTIA] != calendario["nome_municipio_ano"].notna()).any():
        raise ValueError(f"{contexto}: nome_municipio_ano deve estar preenchido se e somente se o município existia.")
    if (calendario["uf_codigo"] != calendario[COD].str[:2]).any():
        raise ValueError(f"{contexto}: uf_codigo diverge do prefixo do código municipal.")


# ---------------------------------------------------------------------------
# 5. Diagnósticos
# ---------------------------------------------------------------------------


def constroi_contagem_por_ano(
    calendario: pd.DataFrame, listas: dict[int, pd.DataFrame], proveniencia_por_ano: dict[int, dict[str, str]]
) -> pd.DataFrame:
    n_uniao = calendario[COD].nunique()
    linhas = []
    for ano in sorted(listas):
        n_existentes = int(calendario.loc[calendario["ano"] == ano, EXISTIA].sum())
        linhas.append({
            "ano": ano,
            "n_municipios_existentes": n_existentes,
            "n_municipios_lista_oficial": len(listas[ano]),
            "n_codigos_na_uniao": n_uniao,
            "n_codigos_inexistentes_no_ano": n_uniao - n_existentes,
            "versao_fonte": proveniencia_por_ano[ano]["versao_fonte"],
        })
    return pd.DataFrame(linhas)


def _evento(tipo: str, codigo: str, ano_anterior: int | None, ano_evento: int | None,
            nome_anterior: str | None, nome_novo: str | None, uf_sigla: str,
            nome_igual: bool | None, observacao: str) -> dict[str, Any]:
    return {
        "tipo_registro": "evento", "tipo_evento": tipo, "n_casos": None, COD: codigo,
        "ano_anterior": ano_anterior, "ano_evento": ano_evento, "nome_anterior": nome_anterior,
        "nome_novo": nome_novo, "uf_sigla": uf_sigla, "nome_igual_apos_normalizacao": nome_igual,
        "observacao": observacao,
    }


def constroi_transicoes(listas: dict[int, pd.DataFrame]) -> pd.DataFrame:
    """Compara edições consecutivas. Todas as classes de evento aparecem no
    resumo, inclusive com zero casos. A DTB anual não informa a CAUSA de uma
    saída (extinção, incorporação, fusão), nem crosswalk de código."""
    anos = sorted(listas)
    indexadas = {a: listas[a].set_index(COD) for a in anos}
    eventos: list[dict[str, Any]] = []

    for anterior, atual in zip(anos, anos[1:]):
        a, b = indexadas[anterior], indexadas[atual]
        entradas = sorted(set(b.index) - set(a.index))
        saidas = sorted(set(a.index) - set(b.index))
        for c in entradas:
            eventos.append(_evento("entrada", c, anterior, atual, None, b.at[c, "nome_municipio"], b.at[c, "uf_sigla"],
                                   None, f"código ausente da DTB {anterior} e presente na DTB {atual}"))
        for c in saidas:
            eventos.append(_evento("saida", c, anterior, atual, a.at[c, "nome_municipio"], None, a.at[c, "uf_sigla"],
                                   None, f"código presente na DTB {anterior} e ausente da DTB {atual}"))
        for c in sorted(set(a.index) & set(b.index)):
            if a.at[c, "uf_codigo"] != b.at[c, "uf_codigo"]:
                eventos.append(_evento("mudanca_uf", c, anterior, atual, a.at[c, "nome_municipio"],
                                       b.at[c, "nome_municipio"], b.at[c, "uf_sigla"], None,
                                       f"UF {a.at[c, 'uf_sigla']} na DTB {anterior} e {b.at[c, 'uf_sigla']} na DTB {atual}"))
            nome_a, nome_b = a.at[c, "nome_municipio"], b.at[c, "nome_municipio"]
            if nome_a != nome_b:
                igual = normaliza_nome_para_comparacao(nome_a) == normaliza_nome_para_comparacao(nome_b)
                eventos.append(_evento("mudanca_nome", c, anterior, atual, nome_a, nome_b, b.at[c, "uf_sigla"], igual,
                                       "mesmo código nas duas edições; nome literal difere"))

        entradas_por_chave = {
            (normaliza_nome_para_comparacao(b.at[c, "nome_municipio"]), b.at[c, "uf_codigo"]): c for c in entradas
        }
        for c in saidas:
            chave = (normaliza_nome_para_comparacao(a.at[c, "nome_municipio"]), a.at[c, "uf_codigo"])
            if chave in entradas_por_chave:
                eventos.append(_evento(
                    "possivel_mudanca_codigo", c, anterior, atual, a.at[c, "nome_municipio"],
                    b.at[entradas_por_chave[chave], "nome_municipio"], a.at[c, "uf_sigla"], True,
                    f"saída de {c} e entrada de {entradas_por_chave[chave]} na mesma transição com mesmo nome "
                    f"normalizado e mesma UF — sinal diagnóstico, não crosswalk oficial",
                ))

    presencas: dict[str, list[int]] = {}
    for ano in anos:
        for c in indexadas[ano].index:
            presencas.setdefault(c, []).append(ano)
    for c, anos_presentes in sorted(presencas.items()):
        ausentes = [a for a in anos if anos_presentes[0] < a < anos_presentes[-1] and a not in anos_presentes]
        if ausentes:
            ultima = indexadas[anos_presentes[-1]]
            eventos.append(_evento("lacuna_intermediaria", c, None, None, None, ultima.at[c, "nome_municipio"],
                                   ultima.at[c, "uf_sigla"], None,
                                   f"código ausente das DTB {ausentes} entre presenças"))

    notas_resumo = {
        "saida": "extinção, incorporação ou fusão apareceriam como saída; a DTB anual não informa a causa",
        "possivel_mudanca_codigo": "heurística diagnóstica (saída+entrada com mesmo nome normalizado e UF)",
    }
    resumo = []
    for classe in CLASSES_EVENTO:
        n = sum(e["tipo_evento"] == classe for e in eventos)
        nota = notas_resumo.get(classe, "")
        if n == 0:
            nota = "zero casos nas edições DTB 2007–2019" + (f"; {nota}" if nota else "")
        resumo.append({
            "tipo_registro": "resumo_classe", "tipo_evento": classe, "n_casos": n, COD: None,
            "ano_anterior": None, "ano_evento": None, "nome_anterior": None, "nome_novo": None,
            "uf_sigla": None, "nome_igual_apos_normalizacao": None, "observacao": nota,
        })
    transicoes = pd.DataFrame(resumo + eventos, columns=COLUNAS_TRANSICOES)
    for coluna in ("n_casos", "ano_anterior", "ano_evento"):
        transicoes[coluna] = transicoes[coluna].astype("Int64")
    transicoes["nome_igual_apos_normalizacao"] = transicoes["nome_igual_apos_normalizacao"].astype("boolean")
    return transicoes


def reconcilia_codigos_projeto(
    calendario: pd.DataFrame,
    grupos: dict[str, set[str]],
    anos_ausentes_universo_inep: dict[str, set[int]] | None = None,
) -> pd.DataFrame:
    """Reconciliação ESTRUTURAL, somente diagnóstica: não exclui, não
    seleciona e não altera nenhum município ou cadastro."""
    anos_inexistentes = (
        calendario.loc[~calendario[EXISTIA]].groupby(COD)["ano"].apply(lambda s: sorted(int(x) for x in s)).to_dict()
    )
    uniao = set(calendario[COD])
    linhas: list[tuple[str, str, int, str]] = []
    for grupo, codigos in grupos.items():
        codigos_ordenados = sorted(codigos, key=str)
        invalidos = [c for c in codigos_ordenados if not isinstance(c, str) or not CODIGO_MUNICIPIO_RE.fullmatch(c)]
        validos = [c for c in codigos_ordenados if c not in invalidos]
        fora = [c for c in validos if c not in uniao]
        no_calendario = [c for c in validos if c in uniao]
        com_inexistencia = [c for c in no_calendario if c in anos_inexistentes]
        linhas += [
            (grupo, "n_codigos_unicos", len(codigos_ordenados), ""),
            (grupo, "n_codigos_formato_invalido", len(invalidos), ";".join(map(str, invalidos))),
            (grupo, "n_codigos_fora_da_uniao_do_calendario", len(fora), ";".join(fora)),
            (grupo, "n_codigos_existentes_nos_13_anos", len(no_calendario) - len(com_inexistencia), ""),
            (grupo, "n_codigos_inexistentes_em_algum_ano", len(com_inexistencia),
             ";".join(f"{c}[{','.join(map(str, anos_inexistentes[c]))}]" for c in com_inexistencia)),
        ]
    if anos_ausentes_universo_inep is not None:
        grupo = "cadastro_elegibilidade_controles_anos_ausentes_universo_inep"
        iguais, divergentes = [], []
        for c, anos_inep in sorted(anos_ausentes_universo_inep.items()):
            if c not in uniao:
                divergentes.append(f"{c}[fora_do_calendario]")
                continue
            anos_cal = set(anos_inexistentes.get(c, []))
            if anos_cal == set(anos_inep):
                iguais.append(c)
            else:
                divergentes.append(f"{c}[inep={sorted(anos_inep)};calendario={sorted(anos_cal)}]")
        ausentes_do_cadastro = sorted(uniao - set(anos_ausentes_universo_inep))
        linhas += [
            (grupo, "n_codigos_unicos", len(anos_ausentes_universo_inep), ""),
            (grupo, "n_codigos_anos_ausentes_inep_iguais_anos_inexistentes_calendario", len(iguais), ""),
            (grupo, "n_codigos_divergentes", len(divergentes), ";".join(divergentes)),
            (grupo, "n_codigos_do_calendario_ausentes_do_cadastro", len(ausentes_do_cadastro),
             ";".join(ausentes_do_cadastro)),
        ]
    return pd.DataFrame(linhas, columns=["grupo", "metrica", "valor", "codigos"])


def carrega_codigos_projeto() -> tuple[dict[str, set[str]], dict[str, set[int]] | None, list[str]]:
    """Leitura somente de códigos (e anos ausentes do universo INEP) dos
    artefatos já existentes. Ausência de arquivo apenas pula o grupo."""
    grupos: dict[str, set[str]] = {}
    notas: list[str] = []
    for grupo, caminho in (("fase_ii_147_municipios", FASE_II_MUNICIPIOS_PATH),
                           ("pool_candidato_controles_4964", POOL_CANDIDATO_PATH)):
        if caminho.exists():
            grupos[grupo] = set(pd.read_parquet(caminho, columns=[COD])[COD])
        else:
            notas.append(f"{grupo}: arquivo ausente ({caminho}); reconciliação não executada")
    anos_ausentes = None
    if CADASTRO_ELEGIBILIDADE_PATH.exists():
        cadastro = pd.read_parquet(CADASTRO_ELEGIBILIDADE_PATH, columns=[COD, "anos_ausentes_do_universo"])
        anos_ausentes = {
            c: {int(a) for a in re.findall(r"[0-9]{4}", s if isinstance(s, str) else "")}
            for c, s in zip(cadastro[COD], cadastro["anos_ausentes_do_universo"])
        }
    else:
        notas.append(f"cadastro de elegibilidade ausente ({CADASTRO_ELEGIBILIDADE_PATH})")
    return grupos, anos_ausentes, notas


# ---------------------------------------------------------------------------
# 6. Proveniência
# ---------------------------------------------------------------------------


def descreve_transformacao(esquema: dict[str, Any]) -> str:
    partes = []
    if esquema["nivel"] == "distrito":
        partes.append("planilha com uma linha por distrito/subdistrito: linhas colapsadas para uma por código "
                      "municipal após verificar que nome do município e UF são únicos por código")
    else:
        partes.append("planilha com uma linha por município: código duplicado é erro")
    if esquema["formato_codigo"] == "uf+5":
        partes.append(f"código de 7 dígitos = '{esquema['coluna_uf']}' (2 dígitos) + "
                      f"'{esquema['coluna_codigo']}' (5 dígitos)")
    else:
        partes.append(f"código de 7 dígitos lido de '{esquema['coluna_codigo']}' e conferido contra "
                      f"'{esquema['coluna_uf']}'" + (f" e '{esquema['coluna_codigo_parcial']}'"
                                                     if esquema.get("coluna_codigo_parcial") else ""))
    partes.append(f"nome de '{esquema['coluna_nome_municipio']}' com remoção apenas de espaços externos")
    partes.append("Nome_UF conferido contra tabela estática de UFs; sigla derivada do código de UF")
    return "; ".join(partes)


def _git_commit() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
        return r.stdout.strip() or None
    except OSError:
        return None


def constroi_manifesto(
    fontes_por_ano: list[dict[str, Any]], calendario: pd.DataFrame, contagem: pd.DataFrame,
    transicoes: pd.DataFrame, reconciliacao: pd.DataFrame, notas_reconciliacao: list[str],
    artefatos: list[Path],
) -> dict[str, Any]:
    caso = calendario.loc[calendario[COD] == CASO_AUDITORIA_PESCARIA_BRAVA,
                          ["ano", EXISTIA, "nome_municipio_ano", "uf_sigla", "observacao_territorial"]]
    resumo_eventos = transicoes.loc[transicoes["tipo_registro"] == "resumo_classe", ["tipo_evento", "n_casos"]]
    return {
        "orgao": ORGAO,
        "produto": FONTE_TERRITORIAL,
        "pagina_produto": PAGINA_PRODUTO,
        "diretorio_ftp_oficial": DTB_FTP_BASE + "/",
        "janela": [ANO_INICIAL, ANO_FINAL],
        "regra_derivacao": f"{EXISTIA} = código presente na lista de municípios da edição DTB do próprio ano",
        "data_execucao_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
        "sha256_script": sha256_arquivo(Path(__file__).resolve()),
        "git_commit_head": _git_commit(),
        "ambiente": {"python": platform.python_version(), "pandas": pd.__version__, "xlrd": xlrd.__version__},
        "raw_versionado_no_git": False,
        "nota_raw": "arquivos .zip originais mantidos em data/raw/ibge/territorio/dtb/ (ignorados por *.zip); "
                    "lidos em memória, sem extração de .xls em disco",
        "fontes_por_ano": fontes_por_ano,
        "resultado": {
            "n_codigos_uniao": int(calendario[COD].nunique()),
            "n_linhas_calendario": int(len(calendario)),
            "contagem_por_ano": {int(r.ano): int(r.n_municipios_existentes) for r in contagem.itertuples()},
            "eventos_por_classe": {r.tipo_evento: int(r.n_casos) for r in resumo_eventos.itertuples()},
        },
        "caso_auditoria_pescaria_brava": {
            "codigo_municipio_ibge": CASO_AUDITORIA_PESCARIA_BRAVA,
            "nota": "derivado do calendário construído; não participa da construção",
            "linhas": [
                {"ano": int(r.ano), EXISTIA: bool(getattr(r, EXISTIA)),
                 "nome_municipio_ano": None if pd.isna(r.nome_municipio_ano) else r.nome_municipio_ano,
                 "observacao_territorial": None if pd.isna(r.observacao_territorial) else r.observacao_territorial}
                for r in caso.itertuples()
            ],
        },
        "reconciliacao_projeto": {
            "natureza": "estrutural, somente leitura e somente diagnóstica; nenhum município excluído ou selecionado",
            "metricas": [{"grupo": r.grupo, "metrica": r.metrica, "valor": int(r.valor)} for r in reconciliacao.itertuples()],
            "notas": notas_reconciliacao,
        },
        "artefatos": [
            {"caminho": str(p.relative_to(ROOT)).replace("\\", "/"), "tamanho_bytes": p.stat().st_size,
             "sha256": sha256_arquivo(p)}
            for p in artefatos
        ],
    }


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def main(permitir_download: bool = True) -> dict[str, Any]:
    print("=" * 70)
    print("CALENDÁRIO TERRITORIAL MUNICÍPIO-ANO — IBGE/DTB 2007–2019")
    print("=" * 70)

    print("\n[1] Garantindo arquivos oficiais DTB (tamanho/SHA-256)...")
    arquivos = {ano: garante_arquivo_dtb(ano, permitir_download=permitir_download) for ano in ANOS_JANELA}
    for ano, info in arquivos.items():
        print(f"    {ano}: {info['caminho'].name} ({info['tamanho_bytes']:,} bytes; {info['origem_local']})")

    print("\n[2] Lendo, normalizando e validando as listas anuais...")
    listas: dict[int, pd.DataFrame] = {}
    fontes_por_ano: list[dict[str, Any]] = []
    proveniencia: dict[int, dict[str, str]] = {}
    for ano in ANOS_JANELA:
        esquema = ESQUEMAS_DTB[ano]
        raw, meta = le_planilha_dtb(arquivos[ano]["caminho"], esquema)
        lista = normaliza_lista_anual(raw, ano, esquema)
        valida_lista_anual(lista, ano)
        listas[ano] = lista
        proveniencia[ano] = {
            "versao_fonte": f"DTB {ano} ({esquema['arquivo']}; sha256={esquema['sha256']})",
            "fonte_ano": arquivos[ano]["url"],
        }
        fontes_por_ano.append({
            "ano_referencia": ano, "url": arquivos[ano]["url"], "arquivo_original": esquema["arquivo"],
            "caminho_local": str(arquivos[ano]["caminho"].relative_to(ROOT)).replace("\\", "/"),
            "data_acesso": arquivos[ano]["data_acesso"], "origem_local": arquivos[ano]["origem_local"],
            "tamanho_bytes": arquivos[ano]["tamanho_bytes"], "sha256": arquivos[ano]["sha256"],
            **meta, "nivel_planilha": esquema["nivel"], "formato_codigo": esquema["formato_codigo"],
            "colunas_usadas": colunas_usadas_do_esquema(esquema),
            "transformacao": descreve_transformacao(esquema),
            "n_municipios": len(lista),
        })
        print(f"    {ano}: {meta['n_linhas_brutas']:,} linhas brutas ({esquema['nivel']}) -> {len(lista):,} municípios")

    print("\n[3] Construindo união de códigos e grade município-ano...")
    calendario = constroi_calendario(listas, proveniencia)
    valida_calendario(calendario, listas)
    print(f"    união: {calendario[COD].nunique():,} códigos; {len(calendario):,} linhas — validações OK")

    print("\n[4] Diagnósticos (contagem anual e transições)...")
    contagem = constroi_contagem_por_ano(calendario, listas, proveniencia)
    transicoes = constroi_transicoes(listas)

    print("\n[5] Reconciliação estrutural com códigos do projeto (somente leitura)...")
    grupos, anos_ausentes_inep, notas = carrega_codigos_projeto()
    reconciliacao = reconcilia_codigos_projeto(calendario, grupos, anos_ausentes_inep)

    print("\n[6] Salvando artefatos...")
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIAGNOSTICS.mkdir(parents=True, exist_ok=True)
    calendario.to_parquet(OUT_CALENDARIO, index=False, engine="pyarrow")
    contagem.to_csv(OUT_CONTAGEM, index=False, encoding="utf-8")
    transicoes.to_csv(OUT_TRANSICOES, index=False, encoding="utf-8")
    reconciliacao.to_csv(OUT_RECONCILIACAO, index=False, encoding="utf-8")
    manifesto = constroi_manifesto(fontes_por_ano, calendario, contagem, transicoes, reconciliacao, notas,
                                   [OUT_CALENDARIO, OUT_CONTAGEM, OUT_TRANSICOES, OUT_RECONCILIACAO])
    with open(OUT_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2)
        f.write("\n")
    for caminho in (OUT_CALENDARIO, OUT_CONTAGEM, OUT_TRANSICOES, OUT_RECONCILIACAO, OUT_MANIFEST):
        print(f"    {caminho}")

    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(contagem[["ano", "n_municipios_existentes"]].to_string(index=False))
    print("\nEventos por classe:", manifesto["resultado"]["eventos_por_classe"])
    print(f"\nCaso de auditoria {CASO_AUDITORIA_PESCARIA_BRAVA} (derivado do calendário):")
    print(calendario.loc[calendario[COD] == CASO_AUDITORIA_PESCARIA_BRAVA,
                         ["ano", EXISTIA, "nome_municipio_ano", "uf_sigla"]].to_string(index=False))
    print("\nReconciliação estrutural (diagnóstica):")
    print(reconciliacao[["grupo", "metrica", "valor"]].to_string(index=False))

    return {"listas": listas, "calendario": calendario, "contagem": contagem, "transicoes": transicoes,
            "reconciliacao": reconciliacao, "manifesto": manifesto}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sem-download", action="store_true", help="não baixa arquivos ausentes")
    args = parser.parse_args()
    main(permitir_download=not args.sem_download)
