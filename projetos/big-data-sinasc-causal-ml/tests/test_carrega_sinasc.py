from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd
import pytest

from src.sinasc import (
    descobrir_csv_no_zip,
    detectar_formato_csv,
    iterar_csv_em_chunks,
    validar_schema_minimo,
)


def criar_zip_sintetico(caminho: Path) -> None:
    conteudo = (
        "contador;CODMUNRES;MESPRENAT;PESO\n"
        "1;001234;03;2499\n"
        "2;000007;;3000\n"
    )
    with zipfile.ZipFile(caminho, "w", compression=zipfile.ZIP_DEFLATED) as arquivo:
        arquivo.writestr("dados/SINASC_teste.csv", conteudo.encode("utf-8"))


def test_descobre_unico_csv_em_zip(tmp_path: Path) -> None:
    caminho_zip = tmp_path / "sinasc.zip"
    criar_zip_sintetico(caminho_zip)

    assert descobrir_csv_no_zip(caminho_zip) == "dados/SINASC_teste.csv"


def test_rejeita_zip_sem_csv(tmp_path: Path) -> None:
    caminho_zip = tmp_path / "sem_csv.zip"
    with zipfile.ZipFile(caminho_zip, "w") as arquivo:
        arquivo.writestr("leia-me.txt", "sem dados")

    with pytest.raises(ValueError, match="CSV"):
        descobrir_csv_no_zip(caminho_zip)


def test_detecta_utf8_separador_e_cabecalho(tmp_path: Path) -> None:
    caminho_zip = tmp_path / "sinasc.zip"
    criar_zip_sintetico(caminho_zip)

    formato = detectar_formato_csv(caminho_zip)

    assert formato.encoding == "utf-8"
    assert formato.separador == ";"
    assert formato.colunas == ("contador", "CODMUNRES", "MESPRENAT", "PESO")


def test_leitura_preserva_codigos_com_zeros_a_esquerda(tmp_path: Path) -> None:
    caminho_zip = tmp_path / "sinasc.zip"
    criar_zip_sintetico(caminho_zip)

    chunks = list(iterar_csv_em_chunks(caminho_zip, tamanho_chunk=1))
    dados = pd.concat(chunks, ignore_index=True)

    assert dados["CODMUNRES"].tolist() == ["001234", "000007"]
    assert dados["MESPRENAT"].tolist()[0] == "03"
    assert pd.isna(dados["MESPRENAT"].tolist()[1])


def test_valida_schema_minimo() -> None:
    validar_schema_minimo(["MESPRENAT", "PESO", "IDADEMAE"], {"MESPRENAT", "PESO"})

    with pytest.raises(ValueError, match="PESO"):
        validar_schema_minimo(["MESPRENAT"], {"MESPRENAT", "PESO"})
