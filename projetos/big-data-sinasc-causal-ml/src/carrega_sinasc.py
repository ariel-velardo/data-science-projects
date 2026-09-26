"""Leitura segura e reproduzível de arquivos CSV do SINASC em ZIP."""

from __future__ import annotations

import csv
import zipfile
from collections.abc import Iterator, Sequence, Set
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class FormatoCSV:
    """Formato observado no CSV interno do arquivo oficial."""

    arquivo_interno: str
    encoding: str
    separador: str
    colunas: tuple[str, ...]


def descobrir_csv_no_zip(caminho_zip: str | Path) -> str:
    """Retorna o único CSV interno e rejeita ZIPs ausentes ou ambíguos."""

    caminho = Path(caminho_zip)
    if not caminho.exists():
        raise FileNotFoundError(f"ZIP não encontrado: {caminho}")

    with zipfile.ZipFile(caminho) as arquivo_zip:
        candidatos = [
            nome
            for nome in arquivo_zip.namelist()
            if not nome.endswith("/") and nome.lower().endswith(".csv")
        ]

    if len(candidatos) != 1:
        raise ValueError(
            f"Esperado exatamente um CSV no ZIP; encontrados {len(candidatos)}: {candidatos}"
        )
    return candidatos[0]


def _detectar_encoding(amostra: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            amostra.decode(encoding)
        except UnicodeDecodeError:
            continue
        return "utf-8" if encoding == "utf-8-sig" else encoding
    raise UnicodeError("Não foi possível detectar um encoding compatível.")


def detectar_formato_csv(caminho_zip: str | Path, bytes_amostra: int = 131_072) -> FormatoCSV:
    """Detecta encoding, separador e cabeçalho a partir de uma amostra limitada."""

    arquivo_interno = descobrir_csv_no_zip(caminho_zip)
    with zipfile.ZipFile(caminho_zip) as arquivo_zip:
        with arquivo_zip.open(arquivo_interno) as fluxo:
            amostra = fluxo.read(bytes_amostra)

    encoding = _detectar_encoding(amostra)
    texto = amostra.decode(encoding)
    dialect = csv.Sniffer().sniff(texto[:65_536], delimiters=";,|\t,")
    cabecalho = next(csv.reader(texto.splitlines(), dialect))
    colunas = tuple(coluna.lstrip("\ufeff").strip() for coluna in cabecalho)
    return FormatoCSV(arquivo_interno, encoding, dialect.delimiter, colunas)


def iterar_csv_em_chunks(
    caminho_zip: str | Path,
    tamanho_chunk: int = 250_000,
    colunas: Sequence[str] | None = None,
) -> Iterator[pd.DataFrame]:
    """Lê o CSV interno em chunks, mantendo todos os campos originais como texto."""

    formato = detectar_formato_csv(caminho_zip)
    with zipfile.ZipFile(caminho_zip) as arquivo_zip:
        with arquivo_zip.open(formato.arquivo_interno) as fluxo:
            yield from pd.read_csv(
                fluxo,
                sep=formato.separador,
                encoding=formato.encoding,
                dtype="string",
                usecols=colunas,
                chunksize=tamanho_chunk,
                keep_default_na=True,
                low_memory=False,
            )


def validar_schema_minimo(colunas: Sequence[str], obrigatorias: Set[str]) -> None:
    """Falha explicitamente quando o schema mínimo necessário não está presente."""

    ausentes = sorted(set(obrigatorias) - set(colunas))
    if ausentes:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(ausentes)}")
