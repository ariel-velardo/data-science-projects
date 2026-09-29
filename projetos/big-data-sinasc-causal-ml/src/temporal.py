"""Extensão temporal: ano como parâmetro, caminhos por ano e schema entre anos.

Módulo novo e isolado. Não altera nem substitui o baseline certificado de 2024:
para ``ano=2024`` os caminhos resolvidos são exatamente os arquivos legados
(``data/raw/SINASC_2024_csv.zip`` e ``data/processed/sinasc_2024.parquet``),
que nunca são reescritos. Anos novos usam pastas próprias por ano. Nenhuma
função aqui estima efeito causal.
"""
from __future__ import annotations

import csv
import io
import json
import struct
import zlib
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import requests

from src.sinasc import baixar_arquivo_oficial
from src.sinasc import converter_zip_para_parquet
from src.sinasc import detectar_formato_csv
from src.sinasc import verificar_arquivo_existente

ANO_BASELINE = 2024
ANO_MINIMO_PUBLICADO = 1996
URL_SINASC_CSV = (
    "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINASC/csv/SINASC_{ano}_csv.zip"
)
PAGINA_OFICIAL = (
    "https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc"
)

# Papel de cada campo bruto no desenho certificado de 2024 (amostra.py,
# auditoria_dados.py, robustez.py). Um campo pode ter mais de um papel.
VARIAVEIS_CRITICAS: dict[str, tuple[str, ...]] = {
    "A_outcome": ("PESO",),
    "B_tratamento": ("MESPRENAT",),
    "C_covariaveis_pre_tratamento": (
        "IDADEMAE", "ESCMAE2010", "RACACORMAE", "ESTCIVMAE", "PARIDADE", "QTDFILMORT",
    ),
    "D_auxiliares": ("GRAVIDEZ", "CONSPRENAT", "DTNASC", "CONTADOR"),
    "E_geograficas": ("CODMUNRES",),
    "F_auditoria_diagnostico": (
        "CONSULTAS", "SEMAGESTAC", "GESTACAO", "PARTO", "KOTELCHUCK", "ESCMAE", "QTDGESTANT",
    ),
}

# Sem estes campos o desenho de 2024 não pode ser replicado no ano.
VARIAVEIS_ESSENCIAIS = frozenset(
    VARIAVEIS_CRITICAS["A_outcome"]
    + VARIAVEIS_CRITICAS["B_tratamento"]
    + VARIAVEIS_CRITICAS["C_covariaveis_pre_tratamento"]
    + VARIAVEIS_CRITICAS["E_geograficas"]
    + ("GRAVIDEZ", "DTNASC")
)


# Rótulos publicados na página oficial do conjunto (acesso em 2026-09-29).
# Anos ausentes deste mapa são publicados sem qualificador (tratados como definitivos).
STATUS_OFICIAL_OBSERVADO = {
    2025: "preliminar",
    2026: "1ª prévia",
}
DATA_CONSULTA_STATUS = "2026-09-29"

CLASSES_ANO = (
    "JANELA_PRINCIPAL",
    "EXCLUIDO_DADO_NAO_CONSOLIDADO",
    "SENSIBILIDADE_PENDENTE_COVARIAVEIS_AUSENTES",
    "INCOMPATIVEL_SEM_T_OU_Y",
)


def validar_ano(ano: Any, ano_maximo: int | None = None) -> int:
    """Aceita somente inteiros no intervalo publicado; rejeita bool, texto e float."""

    if isinstance(ano, bool) or not isinstance(ano, int):
        raise TypeError(f"Ano deve ser inteiro; recebido {ano!r}.")
    limite = ano_maximo if ano_maximo is not None else date.today().year
    if not ANO_MINIMO_PUBLICADO <= ano <= limite:
        raise ValueError(
            f"Ano fora do intervalo publicado ({ANO_MINIMO_PUBLICADO}-{limite}): {ano}."
        )
    return ano


def url_sinasc(ano: int) -> str:
    return URL_SINASC_CSV.format(ano=validar_ano(ano))


@dataclass(frozen=True)
class CaminhosAno:
    """Caminhos locais de um ano. Para 2024 apontam para os arquivos legados."""

    ano: int
    zip_bruto: Path
    parquet: Path
    manifesto: Path | None
    baseline: bool


def caminhos_ano(raiz_projeto: str | Path, ano: int) -> CaminhosAno:
    """Resolve caminhos sem criar nada. Anos novos nunca compartilham arquivos com 2024."""

    raiz = Path(raiz_projeto)
    ano = validar_ano(ano)
    if ano == ANO_BASELINE:
        return CaminhosAno(
            ano=ano,
            zip_bruto=raiz / "data" / "raw" / f"SINASC_{ano}_csv.zip",
            parquet=raiz / "data" / "processed" / f"sinasc_{ano}.parquet",
            manifesto=None,  # proveniência já está em data/raw/source_manifest.json
            baseline=True,
        )
    return CaminhosAno(
        ano=ano,
        zip_bruto=raiz / "data" / "raw" / "sinasc" / str(ano) / f"SINASC_{ano}_csv.zip",
        parquet=raiz / "data" / "processed" / "sinasc" / f"sinasc_{ano}.parquet",
        manifesto=raiz / "outputs" / "temporal" / "manifestos" / f"sinasc_{ano}.json",
        baseline=False,
    )


def _sha256_baseline(raiz: Path) -> str:
    manifesto = json.loads(
        (raiz / "data" / "raw" / "source_manifest.json").read_text(encoding="utf-8")
    )
    return next(
        f["sha256"] for f in manifesto["fontes"] if f.get("arquivo") == f"SINASC_{ANO_BASELINE}_csv.zip"
    )


def baixar_sinasc_ano(
    raiz_projeto: str | Path, ano: int, sha256_esperado: str | None = None
) -> dict[str, Any]:
    """Baixa/reutiliza o ZIP oficial do ano e registra manifesto próprio do ano.

    Para 2024 apenas verifica o ZIP certificado contra o hash do manifesto
    histórico, sem baixar e sem escrever qualquer arquivo.
    """

    raiz = Path(raiz_projeto).resolve()
    caminhos = caminhos_ano(raiz, ano)
    if caminhos.baseline:
        resultado = verificar_arquivo_existente(caminhos.zip_bruto, _sha256_baseline(raiz))
        return {**resultado, "ano": ano, "baseline": True, "reutilizado": True}

    resultado = baixar_arquivo_oficial(url_sinasc(ano), caminhos.zip_bruto, sha256_esperado)
    registro = {
        "dataset": "Sistema de Informação sobre Nascidos Vivos - SINASC",
        "pagina_oficial": PAGINA_OFICIAL,
        "ano": ano,
        "url": url_sinasc(ano),
        "arquivo_local": caminhos.zip_bruto.relative_to(raiz).as_posix(),
        "tamanho_bytes": resultado["bytes"],
        "sha256": resultado["sha256"],
        "reutilizado": resultado["reutilizado"],
        "data_acesso": date.today().isoformat(),
    }
    if caminhos.manifesto.exists():
        anterior = json.loads(caminhos.manifesto.read_text(encoding="utf-8"))
        if anterior["sha256"] != registro["sha256"]:
            raise ValueError(
                f"ZIP de {ano} diverge do manifesto registrado; preservar e investigar."
            )
        return {**resultado, "ano": ano, "baseline": False, "manifesto": anterior}
    caminhos.manifesto.parent.mkdir(parents=True, exist_ok=True)
    caminhos.manifesto.write_text(
        json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {**resultado, "ano": ano, "baseline": False, "manifesto": registro}


def converter_sinasc_ano(
    raiz_projeto: str | Path, ano: int, colunas_obrigatorias: set[str] | None = None
):
    """Converte o ZIP do ano para Parquet textual; reutiliza sem sobrescrever se existir."""

    caminhos = caminhos_ano(raiz_projeto, ano)
    if caminhos.baseline:
        if not caminhos.parquet.exists():
            raise FileNotFoundError(
                "Parquet certificado de 2024 ausente; reproduzir pelo pipeline histórico."
            )
        # Parquet existente é apenas reutilizado; nunca é reconvertido.
        return converter_zip_para_parquet(caminhos.zip_bruto, caminhos.parquet)
    obrigatorias = colunas_obrigatorias
    if obrigatorias is None:
        formato = detectar_formato_csv(caminhos.zip_bruto)
        validar_schema_temporal(formato.colunas, VARIAVEIS_ESSENCIAIS)
        obrigatorias = {c for c in formato.colunas if c.upper() in {"PESO", "MESPRENAT"}}
    return converter_zip_para_parquet(caminhos.zip_bruto, caminhos.parquet,
                                      colunas_obrigatorias=obrigatorias)


def normalizar_colunas(colunas: Iterable[str]) -> dict[str, str]:
    """Mapeia nome em maiúsculas -> nome original; falha em colisão de caixa."""

    mapa: dict[str, str] = {}
    for coluna in colunas:
        chave = coluna.strip().lstrip("﻿").upper()
        if chave in mapa:
            raise ValueError(f"Colunas ambíguas por caixa: {mapa[chave]!r} e {coluna!r}.")
        mapa[chave] = coluna
    return mapa


def comparar_schema(colunas: Sequence[str], referencia: Sequence[str]) -> dict[str, Any]:
    """Compara nomes (sem diferenciar caixa) com o schema de referência."""

    atual, ref = normalizar_colunas(colunas), normalizar_colunas(referencia)
    return {
        "n_colunas": len(atual),
        "ausentes_vs_referencia": sorted(set(ref) - set(atual)),
        "extras_vs_referencia": sorted(set(atual) - set(ref)),
        "diferenca_de_caixa": sorted(k for k in set(ref) & set(atual) if ref[k] != atual[k]),
        "identico": list(atual) == list(ref),
    }


def validar_schema_temporal(colunas: Sequence[str], obrigatorias: Iterable[str]) -> None:
    """Falha explicitamente se o ano não tiver os campos obrigatórios do desenho."""

    presentes = set(normalizar_colunas(colunas))
    ausentes = sorted({o.upper() for o in obrigatorias} - presentes)
    if ausentes:
        raise ValueError(f"Schema incompatível; campos ausentes: {', '.join(ausentes)}")


def disponibilidade_variaveis(colunas: Sequence[str]) -> dict[str, dict[str, bool]]:
    presentes = set(normalizar_colunas(colunas))
    return {
        grupo: {campo: campo in presentes for campo in campos}
        for grupo, campos in VARIAVEIS_CRITICAS.items()
    }


# --- Inspeção remota por HTTP Range (sem baixar o ZIP inteiro) ---

def _intervalo(url: str, inicio: int, fim: int, sessao=None) -> bytes:
    http = sessao or requests
    resposta = http.get(url, headers={"Range": f"bytes={inicio}-{fim}"}, timeout=(30, 120))
    resposta.raise_for_status()
    if resposta.status_code != 206:
        raise ValueError("Servidor não respeitou a requisição parcial (HTTP Range).")
    return resposta.content


def _zip64_extra(extra: bytes, campos: list[int]) -> list[int]:
    posicao = 0
    while posicao + 4 <= len(extra):
        cabecalho, tamanho = struct.unpack_from("<HH", extra, posicao)
        if cabecalho == 0x0001:
            valores = iter(struct.unpack_from(f"<{tamanho // 8}Q", extra, posicao + 4))
            return [next(valores) if c == 0xFFFFFFFF else c for c in campos]
        posicao += 4 + tamanho
    return campos


def ler_diretorio_zip_remoto(url: str, tamanho: int, sessao=None) -> list[dict[str, Any]]:
    """Lê o diretório central do ZIP remoto (inclusive Zip64)."""

    cauda = _intervalo(url, max(0, tamanho - 65_558), tamanho - 1, sessao)
    fim = cauda.rfind(b"PK\x05\x06")
    if fim < 0:
        raise ValueError("Fim do diretório central do ZIP não encontrado.")
    _, _, _, _, n, tam_cd, ini_cd, _ = struct.unpack_from("<IHHHHIIH", cauda, fim)
    if ini_cd == 0xFFFFFFFF or tam_cd == 0xFFFFFFFF or n == 0xFFFF:
        localizador = cauda.rfind(b"PK\x06\x07", 0, fim)
        (pos64,) = struct.unpack_from("<Q", cauda, localizador + 8)
        registro64 = _intervalo(url, pos64, pos64 + 55, sessao)
        n, tam_cd, ini_cd = struct.unpack_from("<QQQ", registro64, 32)
    diretorio = _intervalo(url, ini_cd, ini_cd + tam_cd - 1, sessao)
    entradas, posicao = [], 0
    while diretorio[posicao:posicao + 4] == b"PK\x01\x02":
        (metodo,) = struct.unpack_from("<H", diretorio, posicao + 10)
        comp, descomp, n_nome, n_extra, n_coment = struct.unpack_from("<IIHHH", diretorio, posicao + 20)
        (local,) = struct.unpack_from("<I", diretorio, posicao + 42)
        nome = diretorio[posicao + 46:posicao + 46 + n_nome].decode("cp437")
        extra = diretorio[posicao + 46 + n_nome:posicao + 46 + n_nome + n_extra]
        descomp, comp, local = _zip64_extra(extra, [descomp, comp, local])
        entradas.append(dict(nome=nome, metodo=metodo, bytes_comprimido=comp,
                             bytes_descomprimido=descomp, offset_local=local))
        posicao += 46 + n_nome + n_extra + n_coment
    return entradas


def inspecionar_zip_remoto(
    url: str, bytes_amostra: int = 1_500_000, campos_dominio: Iterable[str] = (), sessao=None
) -> dict[str, Any]:
    """Obtém cabeçalho e um prefixo do CSV interno sem baixar o arquivo completo.

    A amostra é o início físico do arquivo (em geral ordenado por lote/UF); serve
    para detectar schema, formato e códigos, nunca para estimar prevalências.
    """

    cabecalho = (sessao or requests).head(url, timeout=30)
    cabecalho.raise_for_status()
    tamanho = int(cabecalho.headers["Content-Length"])
    entradas = [e for e in ler_diretorio_zip_remoto(url, tamanho, sessao)
                if e["nome"].lower().endswith(".csv")]
    if len(entradas) != 1:
        raise ValueError(f"Esperado um CSV no ZIP; encontrados {[e['nome'] for e in entradas]}.")
    entrada = entradas[0]
    local = _intervalo(url, entrada["offset_local"], entrada["offset_local"] + 29, sessao)
    n_nome, n_extra = struct.unpack_from("<HH", local, 26)
    inicio = entrada["offset_local"] + 30 + n_nome + n_extra
    fim = min(inicio + bytes_amostra, inicio + entrada["bytes_comprimido"]) - 1
    bruto = _intervalo(url, inicio, fim, sessao)
    if entrada["metodo"] == 8:
        texto_bytes = zlib.decompressobj(-15).decompress(bruto)
    elif entrada["metodo"] == 0:
        texto_bytes = bruto
    else:
        raise ValueError(f"Método de compressão ZIP não suportado: {entrada['metodo']}.")
    texto_bytes = texto_bytes[: texto_bytes.rfind(b"\n") + 1]
    encoding = "utf-8"
    for candidato in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            texto = texto_bytes.decode(candidato)
            encoding = "utf-8" if candidato == "utf-8-sig" else candidato
            break
        except UnicodeDecodeError:
            continue
    dialeto = csv.Sniffer().sniff(texto[:65_536], delimiters=";,|\t")
    linhas = list(csv.reader(io.StringIO(texto), dialeto))
    colunas = [c.lstrip("﻿").strip() for c in linhas[0]]
    registros = [l for l in linhas[1:] if len(l) == len(colunas)]
    indice = normalizar_colunas(colunas)
    dominios = {}
    for campo in campos_dominio:
        original = indice.get(campo.upper())
        if original is None:
            dominios[campo] = None
            continue
        j = colunas.index(original)
        contagem = Counter(r[j].strip() if r[j].strip() else "<VAZIO>" for r in registros)
        dominios[campo] = dict(sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))[:30])
    return {
        "url": url,
        "bytes_zip": tamanho,
        "csv_interno": entrada["nome"],
        "bytes_csv_descomprimido": entrada["bytes_descomprimido"],
        "encoding": encoding,
        "separador": dialeto.delimiter,
        "colunas": colunas,
        "n_linhas_amostra": len(registros),
        "n_linhas_malformadas_amostra": len(linhas) - 1 - len(registros),
        "bytes_lidos": len(bruto),
        "dominios_amostra": dominios,
    }


def resumir_compatibilidade(
    inspecoes: Mapping[int, Mapping[str, Any]], ano_referencia: int = ANO_BASELINE
) -> list[dict[str, Any]]:
    """Tabela ano a ano: schema versus referência e presença das variáveis críticas."""

    referencia = inspecoes[ano_referencia]["colunas"]
    linhas = []
    for ano in sorted(inspecoes):
        colunas = inspecoes[ano]["colunas"]
        presentes = set(normalizar_colunas(colunas))
        comparacao = comparar_schema(colunas, referencia)
        linhas.append({
            "ano": ano,
            "n_colunas": comparacao["n_colunas"],
            "separador": inspecoes[ano]["separador"],
            "encoding": inspecoes[ano]["encoding"],
            "tratamento_MESPRENAT": "MESPRENAT" in presentes,
            "outcome_PESO": "PESO" in presentes,
            "essenciais_ausentes": sorted(VARIAVEIS_ESSENCIAIS - presentes),
            "ausentes_vs_2024": comparacao["ausentes_vs_referencia"],
            "extras_vs_2024": comparacao["extras_vs_referencia"],
            "caixa_diferente_vs_2024": comparacao["diferenca_de_caixa"],
        })
    return linhas


def classificar_ano(linha: Mapping[str, Any], status_oficial: str | None = None) -> str:
    """Aplica os critérios de admissão, em ordem de gravidade.

    1. sem MESPRENAT ou PESO o desenho não existe no ano;
    2. sem alguma variável essencial o X congelado não é replicável;
    3. dado oficial não consolidado (preliminar/prévia) fica fora da janela principal.
    """

    if not (linha["tratamento_MESPRENAT"] and linha["outcome_PESO"]):
        return "INCOMPATIVEL_SEM_T_OU_Y"
    if linha["essenciais_ausentes"]:
        return "SENSIBILIDADE_PENDENTE_COVARIAVEIS_AUSENTES"
    if status_oficial is not None:
        return "EXCLUIDO_DADO_NAO_CONSOLIDADO"
    return "JANELA_PRINCIPAL"
