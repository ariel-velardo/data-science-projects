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
import time
import zipfile
import zlib
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pyarrow.parquet as pq
import requests

from src.amostra import _criar_views
from src.auditoria_dados import _auditar_missing
from src.auditoria_dados import _fluxo_amostra
from src.sinasc import calcular_sha256
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
    raiz_projeto: str | Path, ano: int, sha256_esperado: str | None = None, sessao=None
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

    anterior = ler_manifesto_ano(raiz, ano)
    if caminhos.zip_bruto.exists():
        # Reutilização: integridade do ZIP e hash conferidos antes de qualquer uso.
        conteudo = verificar_zip_sinasc(caminhos.zip_bruto)
        resultado = {"arquivo": str(caminhos.zip_bruto), "bytes": caminhos.zip_bruto.stat().st_size,
                     "sha256": calcular_sha256(caminhos.zip_bruto), "reutilizado": True}
        remoto: dict[str, Any] = {}
    else:
        remoto = baixar_zip_retomavel(url_sinasc(ano), caminhos.zip_bruto, sessao=sessao)
        conteudo = remoto.pop("conteudo")
        resultado = {"arquivo": str(caminhos.zip_bruto), "bytes": remoto["bytes"],
                     "sha256": remoto["sha256"], "reutilizado": False}
    if sha256_esperado and resultado["sha256"] != sha256_esperado.lower():
        raise ValueError(f"SHA-256 do ZIP de {ano} diverge do esperado.")
    if anterior is not None:
        if (anterior["sha256"], anterior["tamanho_bytes"]) != (resultado["sha256"], resultado["bytes"]):
            raise ValueError(
                f"ZIP de {ano} diverge do manifesto registrado; preservar e investigar."
            )
        return {**resultado, "ano": ano, "baseline": False, "manifesto": anterior}
    registro = {
        "dataset": "Sistema de Informação sobre Nascidos Vivos - SINASC",
        "pagina_oficial": PAGINA_OFICIAL,
        "ano": ano,
        "url": url_sinasc(ano),
        "arquivo_local": caminhos.zip_bruto.relative_to(raiz).as_posix(),
        "tamanho_bytes": resultado["bytes"],
        "sha256": resultado["sha256"],
        **conteudo,
        "ultima_modificacao_remota": remoto.get("ultima_modificacao"),
        "tentativas_com_falha": remoto.get("falhas", []),
        "reutilizado": resultado["reutilizado"],
        "data_acesso": date.today().isoformat(),
    }
    gravar_manifesto_ano(raiz, ano, registro)
    return {**resultado, "ano": ano, "baseline": False, "manifesto": registro}


def ler_manifesto_ano(raiz_projeto: str | Path, ano: int) -> dict[str, Any] | None:
    caminho = caminhos_ano(raiz_projeto, ano).manifesto
    if caminho is None:
        raise ValueError("2024 não tem manifesto temporal; usar data/raw/source_manifest.json.")
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else None


def gravar_manifesto_ano(raiz_projeto: str | Path, ano: int, registro: Mapping[str, Any]) -> None:
    caminho = caminhos_ano(raiz_projeto, ano).manifesto
    if caminho is None:
        raise ValueError("Escrita de manifesto temporal proibida para o baseline 2024.")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verificar_zip_sinasc(caminho: str | Path) -> dict[str, Any]:
    """Exige exatamente um CSV interno e CRC íntegro em todos os membros."""

    with zipfile.ZipFile(caminho) as arquivo:
        csvs = [i for i in arquivo.infolist() if not i.is_dir() and i.filename.lower().endswith(".csv")]
        if len(csvs) != 1:
            raise ValueError(f"Esperado um CSV no ZIP {caminho}; encontrados {len(csvs)}.")
        corrompido = arquivo.testzip()
        if corrompido is not None:
            raise ValueError(f"CRC inválido no membro {corrompido} de {caminho}.")
    return {"csv_interno": csvs[0].filename, "csv_bytes_descomprimido": csvs[0].file_size,
            "crc_verificado": True}


def baixar_zip_retomavel(
    url: str, destino: str | Path, sessao=None, tentativas: int = 3,
    espera_segundos: float = 10.0, tamanho_bloco: int = 1024 * 1024,
) -> dict[str, Any]:
    """Download retomável: continua o ``.part`` por HTTP Range, verifica tamanho e CRC.

    O arquivo final só aparece após verificação completa. Um parcial nunca é
    apagado: falhas deixam o ``.part`` para retomada e são relatadas.
    """

    destino = Path(destino)
    if destino.exists():
        raise FileExistsError(f"Destino já existe: {destino}; reutilizar em vez de baixar.")
    parcial = destino.with_suffix(destino.suffix + ".part")
    http = sessao or requests.Session()
    cabecalho = http.head(url, timeout=30)
    cabecalho.raise_for_status()
    total = int(cabecalho.headers["Content-Length"])
    destino.parent.mkdir(parents=True, exist_ok=True)
    falhas: list[dict[str, Any]] = []
    for tentativa in range(1, tentativas + 1):
        ja_baixado = parcial.stat().st_size if parcial.exists() else 0
        if ja_baixado > total:
            raise ValueError(f"Parcial maior que o arquivo remoto: {parcial}; preservar e investigar.")
        if ja_baixado == total:
            break
        try:
            extra = {"Range": f"bytes={ja_baixado}-"} if ja_baixado else {}
            with http.get(url, headers=extra, stream=True, timeout=(30, 300)) as resposta:
                resposta.raise_for_status()
                if ja_baixado and resposta.status_code != 206:
                    raise ValueError("Servidor ignorou Range; retomada insegura.")
                with parcial.open("ab") as arquivo:
                    for bloco in resposta.iter_content(chunk_size=tamanho_bloco):
                        if bloco:
                            arquivo.write(bloco)
        except (requests.RequestException, OSError) as erro:
            falhas.append({"tentativa": tentativa, "erro": repr(erro),
                           "bytes_parcial": parcial.stat().st_size if parcial.exists() else 0})
            if tentativa < tentativas:
                time.sleep(espera_segundos * tentativa)
    tamanho = parcial.stat().st_size if parcial.exists() else 0
    if tamanho != total:
        raise RuntimeError(
            f"Download incompleto de {url}: {tamanho}/{total} bytes; parcial preservado em "
            f"{parcial}. Falhas: {falhas}"
        )
    conteudo = verificar_zip_sinasc(parcial)
    sha256 = calcular_sha256(parcial)
    parcial.replace(destino)
    return {"bytes": total, "sha256": sha256, "conteudo": conteudo, "falhas": falhas,
            "ultima_modificacao": cabecalho.headers.get("Last-Modified")}


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


# --- Conversão, orquestração sequencial e proteção do baseline ---

def registrar_conversao(raiz_projeto: str | Path, ano: int) -> dict[str, Any]:
    """Converte (ou reutiliza) o Parquet do ano e registra metadados no manifesto."""

    raiz = Path(raiz_projeto).resolve()
    caminhos = caminhos_ano(raiz, ano)
    manifesto = ler_manifesto_ano(raiz, ano)
    if manifesto is None:
        raise ValueError(f"Manifesto de download de {ano} ausente; baixar antes de converter.")
    if calcular_sha256(caminhos.zip_bruto) != manifesto["sha256"]:
        raise ValueError(f"ZIP de {ano} diverge do manifesto; não converter.")
    inicio = time.perf_counter()
    resultado = converter_sinasc_ano(raiz, ano)
    duracao = time.perf_counter() - inicio
    formato = detectar_formato_csv(caminhos.zip_bruto)
    metadados = pq.ParquetFile(caminhos.parquet).metadata
    conversao = {
        "arquivo_local": caminhos.parquet.relative_to(raiz).as_posix(),
        "csv_interno": formato.arquivo_interno,
        "encoding": formato.encoding,
        "separador": formato.separador,
        "colunas_originais": list(formato.colunas),
        "n_colunas": len(formato.colunas),
        "n_registros": metadados.num_rows,
        "parquet_bytes": caminhos.parquet.stat().st_size,
        "parquet_sha256": calcular_sha256(caminhos.parquet),
        "tipo_colunas": "texto (VARCHAR), como no Parquet certificado de 2024",
    }
    anterior = manifesto.get("conversao")
    if anterior is not None:
        chaves = ("parquet_sha256", "n_registros", "colunas_originais")
        if any(anterior[k] != conversao[k] for k in chaves):
            raise ValueError(f"Parquet de {ano} diverge da conversão registrada; preservar e investigar.")
        return anterior
    conversao["segundos_conversao"] = None if resultado.reutilizado else round(duracao, 1)
    conversao["convertido_em"] = datetime.now().isoformat(timespec="seconds")
    gravar_manifesto_ano(raiz, ano, {**manifesto, "conversao": conversao})
    return conversao


def impressao_baseline(raiz_projeto: str | Path) -> dict[str, str]:
    """Hashes dos arquivos certificados de 2024 que a extensão nunca pode alterar."""

    raiz = Path(raiz_projeto)
    c = caminhos_ano(raiz, ANO_BASELINE)
    return {nome: calcular_sha256(p) for nome, p in (
        ("zip_2024", c.zip_bruto), ("parquet_2024", c.parquet),
        ("source_manifest", raiz / "data" / "raw" / "source_manifest.json"))}


def preparar_anos(raiz_projeto: str | Path, anos: Iterable[int], sessao=None,
                  registro_execucao: str | Path | None = None) -> list[dict[str, Any]]:
    """Baixa e converte UM ano por vez; para no primeiro erro, sem seguir com parcial."""

    raiz = Path(raiz_projeto).resolve()
    log = (Path(registro_execucao) if registro_execucao
           else raiz / "data" / "interim" / "temporal_registro_execucao.jsonl")
    log.parent.mkdir(parents=True, exist_ok=True)
    antes = impressao_baseline(raiz)

    def registrar(evento: dict[str, Any]) -> None:
        with log.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps({"momento": datetime.now().isoformat(timespec="seconds"), **evento},
                                     ensure_ascii=False) + "\n")

    resultados = []
    for ano in anos:
        if validar_ano(ano) == ANO_BASELINE:
            raise ValueError("2024 é o baseline certificado; não é baixado nem reconvertido.")
        try:
            inicio = time.perf_counter()
            download = baixar_sinasc_ano(raiz, ano, sessao=sessao)
            registrar({"ano": ano, "etapa": "download", "status": "ok", "reutilizado": download["reutilizado"],
                       "segundos": round(time.perf_counter() - inicio, 1)})
            inicio = time.perf_counter()
            conversao = registrar_conversao(raiz, ano)
            registrar({"ano": ano, "etapa": "conversao", "status": "ok",
                       "segundos": round(time.perf_counter() - inicio, 1)})
        except Exception as erro:
            registrar({"ano": ano, "status": "falha", "erro": repr(erro)})
            raise
        resultados.append({"ano": ano, "zip_sha256": download["sha256"], **conversao})
    if impressao_baseline(raiz) != antes:
        raise RuntimeError("Arquivo certificado de 2024 alterado durante a preparação.")
    return resultados


# --- Critérios de admissão (versão 1) ---
# Fixados em 2026-09-29, ANTES da leitura dos arquivos completos de 2014-2023
# e sem qualquer estimativa multianual. Alterações exigem nova versão documentada.

# Cronologia (não reescrever): a v1 foi fixada ANTES da leitura dos arquivos completos;
# a H1 foi identificada DEPOIS dessa leitura e aprovada em revisão humana, sempre
# ANTES de qualquer estimação causal multianual. A v1 continua válida e é o contrato
# da janela de sensibilidade.
VERSAO_CRITERIOS_V1 = "1 (fixada em 2026-09-29, antes da leitura dos arquivos completos)"
VERSAO_CRITERIOS_V1_1 = ("1.1 = v1 + H1 (H1 identificada em 2026-09-29 após a leitura completa; aprovada em "
                         "revisão humana em 2026-09-30; antes de qualquer estimação causal multianual)")
VERSAO_CRITERIOS = VERSAO_CRITERIOS_V1_1

# Harmonizações documentadas. Cada uma só vale se a verificação empírica passar no ano.
HARMONIZACOES = (
    {
        "id": "H1",
        "tipo": "harmonização de identificador",
        "variavel": "CONTADOR",
        "anos": (2014, 2015, 2016, 2017),
        "valor_original": "CONTADOR único apenas dentro da UF de residência (reinicia em 1 em cada UF)",
        "valor_harmonizado": "chave (ano, substr(CODMUNRES, 1, 2), CONTADOR)",
        "justificativa": ("Contador técnico por UF no arquivo publicado (27 sequências); linhas completas "
                          "distintas e N bruto correto; a chave composta é verificada única no ano."),
        "nao_altera": ("tratamento", "desfecho", "covariáveis", "regras de inclusão", "frequências",
                       "valores científicos"),
        "identificada_em": "2026-09-29, após a leitura dos arquivos completos",
        "aprovada_em": "2026-09-30, revisão humana, antes de qualquer estimação causal multianual",
    },
)

CONTRATOS = {
    "v1": {"versao": VERSAO_CRITERIOS_V1, "harmonizacoes": ()},
    "v1.1": {"versao": VERSAO_CRITERIOS_V1_1, "harmonizacoes": ("H1",)},
}

# Janelas congeladas em 2026-09-30, antes de qualquer estimação multianual. A escolha
# entre elas NÃO pode depender de resultados futuros: as duas são sempre reportadas.
JANELAS = {
    "principal": {"anos": tuple(range(2014, 2025)), "contrato": "v1.1"},
    "sensibilidade": {"anos": tuple(range(2018, 2025)), "contrato": "v1", "obrigatoria_em": ("08", "09")},
}

# Chave uniforme da camada temporal. Identifica registros em todos os anos da janela
# (em 2018-2024 equivale a CONTADOR, que já é único); NÃO define ordem de processamento
# e NÃO altera o contrato certificado de 2024, que continua usando CONTADOR.
CHAVE_TEMPORAL = ("ano", "UF_RESIDENCIA_CHAVE", "CONTADOR")
SQL_UF_RESIDENCIA_CHAVE = "substr(CAST(CODMUNRES AS VARCHAR), 1, 2)"
TOLERANCIA_CATEGORIAS_INESPERADAS = 0.001   # fração dos registros brutos, por variável
TOLERANCIA_HARMONIZACAO_REGISTROS = 0.0001  # datas/municípios problemáticos excluíveis com documentação
ALERTA_DIFERENCA_IGNORADOS_PP = 5.0         # diferença absoluta frente a 2024; só alerta

DOMINIOS_CATEGORICOS: dict[str, frozenset[int]] = {
    "MESPRENAT": frozenset(range(1, 10)) | {99},
    "GRAVIDEZ": frozenset({1, 2, 3, 9}),
    "ESCMAE2010": frozenset({0, 1, 2, 3, 4, 5, 9}),
    "RACACORMAE": frozenset({1, 2, 3, 4, 5, 9}),
    "ESTCIVMAE": frozenset({1, 2, 3, 4, 5, 9}),
    "PARIDADE": frozenset({0, 1, 9}),
    "QTDFILMORT": frozenset(range(0, 100)),
}

COLUNAS_DERIVADAS_CATEGORICAS = (
    "ESCOLARIDADE_MAE", "RACA_COR_MAE", "SITUACAO_CONJUGAL",
    "PARIDADE_CAT", "PERDAS_FETAIS_CAT", "UF_RESIDENCIA",
)

CRITERIOS_ADMISSAO = {
    "C01_arquivo_integro": "ZIP oficial com SHA-256 igual ao manifesto, CRC íntegro e um único CSV.",
    "C02_esquema_identificavel": "Cabeçalho lido; nomes únicos sem diferenciar caixa; leitura por nome.",
    "C03_desfecho_presente": "Campo PESO presente.",
    "C04_tratamento_presente": "Campo MESPRENAT presente.",
    "C05_covariaveis_presentes": ("IDADEMAE, ESCMAE2010, RACACORMAE, ESTCIVMAE, PARIDADE, QTDFILMORT, "
                                  "CODMUNRES, GRAVIDEZ e DTNASC presentes."),
    "C06_codificacao_compativel": ("Valores fora do domínio documentado de cada campo categórico crítico "
                                   "<= 0,1% dos registros; acima disso, só com mapeamento documentado."),
    "C07_datas_do_ano": ("DTNASC válida e no ano do arquivo em todos os registros; até 0,01% admite "
                         "exclusão documentada (harmonização)."),
    "C08_contador_utilizavel": "CONTADOR completo e único dentro do ano; chave temporal (ano, CONTADOR).",
    "C09_tratamento_dominio": "T construível pela regra 1-3 vs 4-9, com T=1 e T=0 na população principal.",
    "C10_desfecho_dominio": "PESO não numérico <= 0,1% dos registros; Y=0 e Y=1 na população principal.",
    "C11_categorias_covariaveis": ("Categorias derivadas da população principal contidas nas de 2024; "
                                   "município com 6 dígitos (até 0,01% exclusível com documentação)."),
    "C12_ignorados_quantificados": ("Ausentes/ignorados de T e X quantificados; diferença > 5 p.p. frente "
                                    "a 2024 gera alerta, não exclusão."),
    "C13_baseline_protegido": "Caminhos distintos de 2024 e hashes certificados de 2024 inalterados.",
    "C14_fluxo_reconciliavel": "Fluxo A0-A3 monótono, A3 = A2 > 0.",
    "C15_dado_consolidado": "Arquivo publicado sem qualificador preliminar/prévia.",
}


def _codigo_inteiro(valor: Any) -> int | None:
    texto = str(valor).strip()
    return int(texto) if texto.isdigit() else None


def auditar_ano(parquet: str | Path, ano: int) -> dict[str, Any]:
    """Auditoria completa de um ano com as MESMAS views congeladas de 2024 (amostra._criar_views)."""

    parquet = Path(parquet)
    ano = validar_ano(ano)
    colunas = pq.ParquetFile(parquet).schema_arrow.names
    presentes = set(normalizar_colunas(colunas))
    resultado: dict[str, Any] = {
        "ano": ano, "colunas_originais": colunas,
        "essenciais_ausentes": sorted(VARIAVEIS_ESSENCIAIS - presentes),
        "criticas_ausentes": sorted({c for g in VARIAVEIS_CRITICAS.values() for c in g} - presentes),
    }
    if resultado["essenciais_ausentes"]:
        return resultado
    with duckdb.connect() as con:
        _criar_views(con, parquet)
        n_bruto = con.execute("SELECT count(*) FROM sinasc").fetchone()[0]
        datas = con.execute(f"""
            WITH d AS (SELECT try_strptime(CAST(DTNASC AS VARCHAR), '%d%m%Y') AS data FROM sinasc)
            SELECT count(*) FILTER (WHERE data IS NULL), count(*) FILTER (WHERE year(data) <> {ano}),
                   CAST(min(data) AS VARCHAR), CAST(max(data) AS VARCHAR) FROM d""").fetchone()
        chave = con.execute("""
            SELECT count(*) - count(contador), count(contador) - count(DISTINCT contador),
                   count(*) - count(DISTINCT (substr(CAST(CODMUNRES AS VARCHAR), 1, 2), contador)),
                   count(*) FILTER (WHERE try_cast(contador AS BIGINT) = 1)
            FROM sinasc""").fetchone()
        dominios, inesperados = {}, {}
        for campo, dominio in DOMINIOS_CATEGORICOS.items():
            contagem = con.execute(f"SELECT CAST({campo} AS VARCHAR), count(*) FROM sinasc GROUP BY 1").fetchall()
            dominios[campo] = {}
            for valor, n in contagem:
                rotulo = "<AUSENTE>" if valor is None or not str(valor).strip() else str(valor)
                dominios[campo][rotulo] = dominios[campo].get(rotulo, 0) + int(n)
            dominios[campo] = dict(sorted(dominios[campo].items()))
            fora = {k: v for k, v in dominios[campo].items()
                    if k != "<AUSENTE>" and _codigo_inteiro(k) not in dominio}
            inesperados[campo] = {"n": sum(fora.values()), "fracao": sum(fora.values()) / n_bruto,
                                  "valores": dict(sorted(fora.items(), key=lambda kv: -kv[1])[:10])}
        for campo in ("PESO", "IDADEMAE"):
            n, exemplos = con.execute(f"""
                SELECT count(*), list(DISTINCT CAST({campo} AS VARCHAR)) FROM sinasc
                WHERE {campo} IS NOT NULL AND trim(CAST({campo} AS VARCHAR)) <> ''
                  AND try_cast({campo} AS INTEGER) IS NULL""").fetchone()
            inesperados[campo] = {"n": int(n), "fracao": n / n_bruto,
                                  "valores": sorted(exemplos or [])[:10]}
        municipio = con.execute("""
            SELECT (SELECT count(*) FROM sinasc WHERE NOT coalesce(
                        regexp_full_match(CAST(CODMUNRES AS VARCHAR), '[0-9]{6}'), false)),
                   (SELECT count(*) FROM amostra_principal WHERE UF_RESIDENCIA = 'IGNORADO')""").fetchone()
        fluxo = _fluxo_amostra(con)
        missing_x = _auditar_missing(con)
        tratamento = con.execute("""
            SELECT count(*) FILTER (WHERE tratamento = 1), count(*) FILTER (WHERE tratamento = 0),
                   count(*) FILTER (WHERE mesprenat_num = 99),
                   count(*) FILTER (WHERE MESPRENAT IS NULL OR trim(CAST(MESPRENAT AS VARCHAR)) = ''),
                   count(*) FILTER (WHERE tratamento IS NULL AND mesprenat_num IS DISTINCT FROM 99
                                    AND MESPRENAT IS NOT NULL AND trim(CAST(MESPRENAT AS VARCHAR)) <> '')
            FROM fase1_base""").fetchone()
        peso = con.execute("""
            SELECT count(*) FILTER (WHERE y_p0 IS NULL), count(*) FILTER (WHERE y_p1 IS NULL),
                   count(*) FILTER (WHERE peso_num > 0 AND peso_num < 500),
                   count(*) FILTER (WHERE peso_num > 6000),
                   avg(peso_num) FILTER (WHERE peso_num > 0), stddev_samp(peso_num) FILTER (WHERE peso_num > 0),
                   quantile_cont(peso_num, [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]) FILTER (WHERE peso_num > 0),
                   100.0 * avg(y_p1) FILTER (WHERE y_p1 IS NOT NULL)
            FROM fase1_base""").fetchone()
        mes = con.execute("""SELECT mesprenat_num, count(*) FROM fase1_base
                             WHERE mesprenat_num BETWEEN 1 AND 9 GROUP BY 1 ORDER BY 1""").fetchall()
        principal = con.execute("""
            SELECT count(*), sum(tratamento), sum(Y_BAIXO_PESO),
                   avg(Y_BAIXO_PESO) FILTER (WHERE tratamento = 1), avg(Y_BAIXO_PESO) FILTER (WHERE tratamento = 0),
                   count(*) - count(IDADEMAE_NUM), avg(IDADEMAE_NUM), stddev_samp(IDADEMAE_NUM),
                   quantile_cont(IDADEMAE_NUM, [0.05, 0.5, 0.95])
            FROM amostra_principal""").fetchone()
        niveis = []
        for coluna in COLUNAS_DERIVADAS_CATEGORICAS:
            for nivel, n, n_t1, n_y1 in con.execute(f"""
                    SELECT CAST({coluna} AS VARCHAR), count(*), sum(tratamento), sum(Y_BAIXO_PESO)
                    FROM amostra_principal GROUP BY 1 ORDER BY 1""").fetchall():
                niveis.append({"ano": ano, "variavel": coluna, "categoria": nivel, "n": int(n),
                               "n_t1": int(n_t1), "n_y1": int(n_y1)})
        geografia = con.execute("""
            SELECT CASE WHEN regexp_full_match(CAST(CODMUNRES AS VARCHAR), '[0-9]{6}')
                        THEN substr(CAST(CODMUNRES AS VARCHAR), 1, 2) ELSE 'IGNORADO' END AS uf,
                   count(*) AS n_bruto,
                   count(*) FILTER (WHERE tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num = 1) AS n_principal,
                   coalesce(sum(tratamento) FILTER (WHERE y_p1 IS NOT NULL AND gravidez_num = 1), 0) AS n_t1,
                   coalesce(sum(y_p1) FILTER (WHERE tratamento IS NOT NULL AND gravidez_num = 1), 0) AS n_y1
            FROM fase1_base GROUP BY 1 ORDER BY 1""").df()
    geografia.insert(0, "ano", ano)
    n_principal, n_t1, n_y1 = int(principal[0]), int(principal[1]), int(principal[2])
    return {
        **resultado,
        "n_bruto": int(n_bruto),
        "n_dtnasc_invalida": int(datas[0]), "n_dtnasc_fora_do_ano": int(datas[1]),
        "n_valido_dtnasc": int(n_bruto - datas[0] - datas[1]),
        "dtnasc_minima": datas[2], "dtnasc_maxima": datas[3],
        "n_contador_ausente": int(chave[0]), "n_contador_duplicado": int(chave[1]),
        "n_chave_uf_contador_duplicada": int(chave[2]), "n_contador_igual_1": int(chave[3]),
        "dominios_brutos": dominios, "inesperados": inesperados,
        "n_codmunres_malformado_bruto": int(municipio[0]),
        "n_codmunres_malformado_principal": int(municipio[1]),
        "fluxo": fluxo.assign(ano=ano).to_dict("records"),
        "n_principal": n_principal, "n_t1": n_t1, "n_t0": n_principal - n_t1,
        "n_y1": n_y1, "n_y0": n_principal - n_y1,
        "tratamento_bruto": {"n_t1": int(tratamento[0]), "n_t0": int(tratamento[1]), "n_99": int(tratamento[2]),
                             "n_vazio": int(tratamento[3]), "n_outro": int(tratamento[4])},
        "mesprenat_valido": {str(int(k)): int(v) for k, v in mes},
        "peso": {"n_y_p0_ausente": int(peso[0]), "n_y_p1_ausente": int(peso[1]),
                 "n_abaixo_500": int(peso[2]), "n_acima_6000": int(peso[3]),
                 "media": float(peso[4]), "dp": float(peso[5]),
                 "percentis": dict(zip(("p01", "p05", "p25", "p50", "p75", "p95", "p99"), map(float, peso[6]))),
                 "prevalencia_baixo_peso_p1_bruto_pct": float(peso[7])},
        "principal": {"risco_t1": float(principal[3]), "risco_t0": float(principal[4]),
                      "idade_ausente": int(principal[5]), "idade_media": float(principal[6]),
                      "idade_dp": float(principal[7]),
                      "idade_percentis": dict(zip(("p05", "p50", "p95"), map(float, principal[8])))},
        "missing_x": missing_x.assign(ano=ano).to_dict("records"),
        "niveis_derivados": niveis,
        "geografia": geografia.to_dict("records"),
    }


def harmonizacao_chave(ano: int) -> Mapping[str, Any] | None:
    return next((h for h in HARMONIZACOES if h["variavel"] == "CONTADOR" and ano in h["anos"]), None)


def _avaliar_chave(a: Mapping[str, Any]) -> tuple[str, str]:
    """C08: chave (ano, CONTADOR); só a harmonização H1 documentada admite a chave composta."""

    base = f"ausentes={a['n_contador_ausente']}, duplicados={a['n_contador_duplicado']}"
    if a["n_contador_ausente"]:
        return "FALHA", base
    if a["n_contador_duplicado"] == 0:
        return "OK", base
    h = harmonizacao_chave(a["ano"])
    if h and a.get("n_chave_uf_contador_duplicada", 1) == 0:
        return "HARMONIZACAO", (f"{base}; {h['id']}: {h['valor_harmonizado']} única "
                                f"({a['n_contador_igual_1']} sequências iniciadas em 1)")
    return "FALHA", base + "; sem harmonização documentada e verificada"


def _faixa(n_problema: int, n_total: int) -> str:
    if n_problema == 0:
        return "OK"
    return "HARMONIZACAO" if n_problema / n_total <= TOLERANCIA_HARMONIZACAO_REGISTROS else "FALHA"


def avaliar_criterios(
    auditoria: Mapping[str, Any], referencia_2024: Mapping[str, Any], integridade_ok: bool,
    baseline_intacto: bool, caminhos_distintos: bool, status_oficial: str | None = None,
) -> list[dict[str, Any]]:
    """Aplica C01-C15 (versão 1). Resultado por critério: OK, HARMONIZACAO, ALERTA ou FALHA."""

    a, ref = auditoria, referencia_2024
    ausentes = a["essenciais_ausentes"]

    def linha(cid, resultado, evidencia):
        return {"ano": a["ano"], "criterio": cid, "resultado": resultado, "evidencia": evidencia}

    linhas = [
        linha("C01_arquivo_integro", "OK" if integridade_ok else "FALHA", "SHA-256 e CRC conferidos"),
        linha("C02_esquema_identificavel", "OK", f"{len(a['colunas_originais'])} colunas, nomes únicos por caixa"),
        linha("C03_desfecho_presente", "FALHA" if "PESO" in ausentes else "OK", "PESO"),
        linha("C04_tratamento_presente", "FALHA" if "MESPRENAT" in ausentes else "OK", "MESPRENAT"),
        linha("C05_covariaveis_presentes", "FALHA" if ausentes else "OK", ", ".join(ausentes) or "todas"),
    ]
    if ausentes:
        return linhas
    n = a["n_bruto"]
    categoricos = {k: v for k, v in a["inesperados"].items() if k in DOMINIOS_CATEGORICOS and v["n"]}
    linhas.append(linha(
        "C06_codificacao_compativel",
        "FALHA" if any(v["fracao"] > TOLERANCIA_CATEGORIAS_INESPERADAS for v in categoricos.values()) else "OK",
        "; ".join(f"{k}: {v['n']} ({100 * v['fracao']:.4f}%) {list(v['valores'])}" for k, v in categoricos.items())
        or "nenhum valor fora do domínio"))
    problemas_data = a["n_dtnasc_invalida"] + a["n_dtnasc_fora_do_ano"]
    linhas.append(linha("C07_datas_do_ano", _faixa(problemas_data, n),
                        f"inválidas={a['n_dtnasc_invalida']}, fora do ano={a['n_dtnasc_fora_do_ano']}"))
    linhas.append(linha("C08_contador_utilizavel", *_avaliar_chave(a)))
    linhas.append(linha("C09_tratamento_dominio", "OK" if a["n_t1"] and a["n_t0"] else "FALHA",
                        f"T=1: {a['n_t1']}, T=0: {a['n_t0']}"))
    peso_ruim = a["inesperados"]["PESO"]["fracao"] > TOLERANCIA_CATEGORIAS_INESPERADAS
    linhas.append(linha("C10_desfecho_dominio", "FALHA" if peso_ruim or not (a["n_y1"] and a["n_y0"]) else "OK",
                        f"PESO não inteiro={a['inesperados']['PESO']['n']}; Y=1: {a['n_y1']}, Y=0: {a['n_y0']}"))
    niveis_ref = {(r["variavel"], r["categoria"]) for r in ref["niveis_derivados"]}
    novos = sorted({(r["variavel"], r["categoria"]) for r in a["niveis_derivados"]} - niveis_ref)
    resultado_c11 = "FALHA" if novos else _faixa(a["n_codmunres_malformado_principal"], a["n_principal"])
    linhas.append(linha("C11_categorias_covariaveis", resultado_c11,
                        f"categorias novas={novos or 'nenhuma'}; município malformado na principal="
                        f"{a['n_codmunres_malformado_principal']}"))
    ign = {r["variavel"]: r["pct_total"] for r in a["missing_x"]}
    ign_ref = {r["variavel"]: r["pct_total"] for r in ref["missing_x"]}

    def t_desconhecido(x):
        return 100 * (1 - (x["tratamento_bruto"]["n_t1"] + x["tratamento_bruto"]["n_t0"]) / x["n_bruto"])

    difs = {**{k: ign[k] - ign_ref[k] for k in ign}, "T_desconhecido": t_desconhecido(a) - t_desconhecido(ref)}
    alertas = {k: round(v, 2) for k, v in difs.items() if abs(v) > ALERTA_DIFERENCA_IGNORADOS_PP}
    linhas.append(linha("C12_ignorados_quantificados", "ALERTA" if alertas else "OK",
                        f"diferenças > {ALERTA_DIFERENCA_IGNORADOS_PP} p.p. vs 2024: {alertas or 'nenhuma'}"))
    linhas.append(linha("C13_baseline_protegido", "OK" if baseline_intacto and caminhos_distintos else "FALHA",
                        "hashes de 2024 inalterados; caminhos próprios" if baseline_intacto else "baseline alterado"))
    f = {r["etapa"]: r["n_restante"] for r in a["fluxo"]}
    fluxo_ok = a["n_bruto"] >= f["A0"] >= f["A1"] >= f["A2"] == f["A3"] > 0
    linhas.append(linha("C14_fluxo_reconciliavel", "OK" if fluxo_ok else "FALHA",
                        f"bruto={a['n_bruto']}, A0={f['A0']}, A1={f['A1']}, A2={f['A2']}, A3={f['A3']}"))
    linhas.append(linha("C15_dado_consolidado", "FALHA" if status_oficial else "OK",
                        status_oficial or "sem qualificador preliminar"))
    return linhas


def resultado_no_contrato(linha: Mapping[str, Any], contrato: str) -> str:
    """Resultado de um critério sob v1 (sem H1) ou v1.1 (com H1). Só C08 difere."""

    if contrato not in CONTRATOS:
        raise ValueError(f"Contrato desconhecido: {contrato}")
    if (contrato == "v1" and linha["criterio"] == "C08_contador_utilizavel"
            and linha["resultado"] == "HARMONIZACAO"):
        return "FALHA"
    return linha["resultado"]


def veredito_no_contrato(criterios: Sequence[Mapping[str, Any]], contrato: str) -> str:
    return veredito_ano([{**c, "resultado": resultado_no_contrato(c, contrato)} for c in criterios])


def validar_chave_temporal(auditoria: Mapping[str, Any]) -> None:
    """Falha se a chave uniforme (ano, UF de residência, CONTADOR) não identificar o ano."""

    problemas = {k: auditoria[k] for k in ("n_chave_uf_contador_duplicada", "n_codmunres_malformado_bruto",
                                           "n_contador_ausente") if auditoria[k]}
    if problemas:
        raise ValueError(f"Chave temporal inválida em {auditoria['ano']}: {problemas}")


def veredito_ano(criterios: Sequence[Mapping[str, Any]]) -> str:
    resultados = {c["resultado"] for c in criterios}
    if "FALHA" in resultados:
        return "NAO_APROVADO"
    if "HARMONIZACAO" in resultados:
        return "APROVADO_COM_HARMONIZACAO"
    return "APROVADO"


# --- Tabelas descritivas agregadas (sem estimação causal) ---

def _pct(parte: float, total: float) -> float:
    return 100 * parte / total if total else float("nan")


def tabela_auditoria(
    auditorias: Sequence[Mapping[str, Any]], criterios: Sequence[Mapping[str, Any]],
    referencia_colunas: Sequence[str],
) -> pd.DataFrame:
    """Uma linha por ano com as colunas mínimas de auditoria pedidas para a janela."""

    linhas = []
    for a in auditorias:
        do_ano = [c for c in criterios if c["ano"] == a["ano"]]
        f = {r["etapa"]: r["n_restante"] for r in a["fluxo"]}
        comparacao = comparar_schema(a["colunas_originais"], referencia_colunas)
        inesperadas = {k: v["n"] for k, v in a["inesperados"].items() if v["n"]}
        ignorados = {r["variavel"]: r["n_missing"] for r in a["missing_x"]}
        linhas.append({
            "ano": a["ano"],
            "n_bruto": a["n_bruto"],
            "n_valido_dtnasc": a["n_valido_dtnasc"],
            "n_apos_regras_basicas": f["A3"],
            "colunas_presentes": len(a["colunas_originais"]),
            "colunas_ausentes": ";".join(comparacao["ausentes_vs_referencia"]),
            "tratamento_presente": "MESPRENAT" not in a["essenciais_ausentes"],
            "outcome_presente": "PESO" not in a["essenciais_ausentes"],
            "covariaveis_presentes": not a["essenciais_ausentes"],
            "duplicidade_contador": a["n_contador_duplicado"],
            "duplicidade_chave_uf_contador": a["n_chave_uf_contador_duplicada"],
            "chave_temporal": "(ano, UF_res, CONTADOR)",
            "chave_temporal_unica": (a["n_chave_uf_contador_duplicada"] == 0
                                     and a["n_codmunres_malformado_bruto"] == 0),
            "contador_isolado_unico_no_ano": a["n_contador_duplicado"] == 0,
            "contador_ausente": a["n_contador_ausente"],
            "dominio_mesprenat": ";".join(k for k in a["dominios_brutos"]["MESPRENAT"]),
            "dominio_peso": f"{a['peso']['percentis']['p01']:.0f}-{a['peso']['percentis']['p99']:.0f} g (p01-p99)",
            "missing_outcome": a["peso"]["n_y_p0_ausente"],
            "missing_tratamento": a["n_bruto"] - a["tratamento_bruto"]["n_t1"] - a["tratamento_bruto"]["n_t0"],
            "missing_covariaveis": json.dumps(ignorados, ensure_ascii=False),
            "categorias_inesperadas": json.dumps(inesperadas, ensure_ascii=False),
            "schema_compativel": not a["essenciais_ausentes"],
            "criterios_aprovados": sum(c["resultado"] in ("OK", "ALERTA") for c in do_ano),
            "criterios_total": len(do_ano),
            "veredito": veredito_no_contrato(do_ano, "v1.1"),
            "veredito_v1": veredito_no_contrato(do_ano, "v1"),
            "veredito_v1_1": veredito_no_contrato(do_ano, "v1.1"),
            "admitido_janela_principal": (a["ano"] in JANELAS["principal"]["anos"]
                                          and veredito_no_contrato(do_ano, "v1.1") != "NAO_APROVADO"),
            "admitido_janela_sensibilidade": (a["ano"] in JANELAS["sensibilidade"]["anos"]
                                              and veredito_no_contrato(do_ano, "v1") != "NAO_APROVADO"),
            "observacoes": "; ".join(f"{c['criterio']}={c['resultado']}" for c in do_ano
                                     if c["resultado"] != "OK") or "todos os critérios OK",
        })
    return pd.DataFrame(linhas)


def tabelas_descritivas(auditorias: Sequence[Mapping[str, Any]]) -> dict[str, pd.DataFrame]:
    """Agrega auditorias anuais em tabelas descritivas longas/largas, sem modelos."""

    descritiva, qualidade, missing, covariaveis, geografia = [], [], [], [], []
    for a in auditorias:
        n, np_ = a["n_bruto"], a["n_principal"]
        tb = a["tratamento_bruto"]
        conhecido = tb["n_t1"] + tb["n_t0"]
        meses = a["mesprenat_valido"]
        total_meses = sum(meses.values())
        descritiva.append({
            "ano": a["ano"], "n_bruto": n, "n_principal": np_, "pct_principal": _pct(np_, n),
            "prevalencia_y_pct": _pct(a["n_y1"], np_), "prevalencia_t_pct": _pct(a["n_t1"], np_),
            "prevalencia_t_bruto_conhecido_pct": _pct(tb["n_t1"], conhecido),
            "risco_y_t1_pct": 100 * a["principal"]["risco_t1"], "risco_y_t0_pct": 100 * a["principal"]["risco_t0"],
            "diferenca_bruta_pp_nao_causal": 100 * (a["principal"]["risco_t1"] - a["principal"]["risco_t0"]),
            "peso_medio_g": a["peso"]["media"], "peso_dp_g": a["peso"]["dp"],
            **{f"peso_{k}_g": v for k, v in a["peso"]["percentis"].items()},
            "mesprenat_medio": sum(int(k) * v for k, v in meses.items()) / total_meses,
            **{f"mes_{k}_pct": _pct(meses.get(str(k), 0), total_meses) for k in range(1, 10)},
            "idade_media": a["principal"]["idade_media"], "idade_dp": a["principal"]["idade_dp"],
        })
        qualidade.append({
            "ano": a["ano"], "n_bruto": n,
            "t_desconhecido_pct": _pct(n - conhecido, n), "mesprenat_99_pct": _pct(tb["n_99"], n),
            "mesprenat_vazio_pct": _pct(tb["n_vazio"], n), "mesprenat_outro_pct": _pct(tb["n_outro"], n),
            "peso_invalido_p0_pct": _pct(a["peso"]["n_y_p0_ausente"], n),
            "peso_fora_p1_pct": _pct(a["peso"]["n_y_p1_ausente"], n),
            "peso_abaixo_500": a["peso"]["n_abaixo_500"], "peso_acima_6000": a["peso"]["n_acima_6000"],
            "dtnasc_invalida": a["n_dtnasc_invalida"], "dtnasc_fora_do_ano": a["n_dtnasc_fora_do_ano"],
            "contador_ausente": a["n_contador_ausente"], "contador_duplicado": a["n_contador_duplicado"],
            "codmunres_malformado_bruto": a["n_codmunres_malformado_bruto"],
            "codmunres_malformado_principal": a["n_codmunres_malformado_principal"],
            **{f"inesperado_{k}": v["n"] for k, v in a["inesperados"].items()},
            "idade_ausente_principal_pct": _pct(a["principal"]["idade_ausente"], np_),
        })
        for r in a["missing_x"]:
            missing.append({"ano": a["ano"], "variavel": r["variavel"], "n_missing": r["n_missing"],
                            **{k: r[k] for k in ("pct_total", "pct_t1", "pct_t0", "pct_y1", "pct_y0")}})
        for r in a["niveis_derivados"]:
            covariaveis.append({**r, "pct": _pct(r["n"], np_), "pct_t1_no_nivel": _pct(r["n_t1"], r["n"]),
                                "prevalencia_y_no_nivel": _pct(r["n_y1"], r["n"])})
        for r in a["geografia"]:
            geografia.append({**r, "pct_principal": _pct(r["n_principal"], r["n_bruto"]),
                              "pct_t1": _pct(r["n_t1"], r["n_principal"]),
                              "prevalencia_y": _pct(r["n_y1"], r["n_principal"]),
                              "participacao_bruto_pct": _pct(r["n_bruto"], n)})
    return {
        "descritiva_anual": pd.DataFrame(descritiva),
        "qualidade_anos": pd.DataFrame(qualidade),
        "missing_anual": pd.DataFrame(missing),
        "covariaveis_anuais": pd.DataFrame(covariaveis),
        "geografia_anual": pd.DataFrame(geografia),
    }


def comparar_com_referencia(
    tabela: pd.DataFrame, colunas: Sequence[str], chaves: Sequence[str] = (),
    ano_referencia: int = ANO_BASELINE,
) -> pd.DataFrame:
    """Acrescenta ``<coluna>_menos_2024`` (diferença absoluta frente ao ano de referência)."""

    if ano_referencia not in set(tabela["ano"]):
        raise ValueError(f"Ano de referência {ano_referencia} ausente da tabela.")
    referencia = tabela.loc[tabela["ano"] == ano_referencia, [*chaves, *colunas]]
    saida = tabela.merge(referencia, on=list(chaves), how="left", suffixes=("", "_ref")) if chaves else \
        tabela.assign(**{f"{c}_ref": referencia[c].iloc[0] for c in colunas})
    for c in colunas:
        saida[f"{c}_menos_{ano_referencia}"] = saida[c] - saida.pop(f"{c}_ref")
    return saida
