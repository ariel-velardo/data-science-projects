from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from src.sinasc import converter_zip_para_parquet


def test_converte_zip_para_parquet_preservando_texto(tmp_path: Path) -> None:
    caminho_zip = tmp_path / "sinasc.zip"
    caminho_parquet = tmp_path / "sinasc.parquet"
    conteudo = (
        "contador;CODMUNRES;MESPRENAT;PESO\n"
        "1;001234;03;2499\n"
        "2;000007;99;3000\n"
    )
    with zipfile.ZipFile(caminho_zip, "w", compression=zipfile.ZIP_DEFLATED) as arquivo:
        arquivo.writestr("SINASC_teste.csv", conteudo.encode("utf-8"))

    resultado = converter_zip_para_parquet(
        caminho_zip,
        caminho_parquet,
        tamanho_chunk=1,
        colunas_obrigatorias={"MESPRENAT", "PESO"},
    )
    dados = pd.read_parquet(caminho_parquet)

    assert resultado.registros == 2
    assert resultado.colunas == 4
    assert resultado.reutilizado is False
    assert dados["CODMUNRES"].tolist() == ["001234", "000007"]
    assert str(dados["PESO"].dtype).startswith("string")


def test_nao_sobrescreve_parquet_existente(tmp_path: Path) -> None:
    caminho_zip = tmp_path / "sinasc.zip"
    caminho_parquet = tmp_path / "sinasc.parquet"
    with zipfile.ZipFile(caminho_zip, "w") as arquivo:
        arquivo.writestr("SINASC.csv", b"contador;MESPRENAT;PESO\n1;03;2499\n")

    converter_zip_para_parquet(caminho_zip, caminho_parquet)
    primeira_modificacao = caminho_parquet.stat().st_mtime_ns
    resultado = converter_zip_para_parquet(caminho_zip, caminho_parquet)

    assert resultado.reutilizado is True
    assert caminho_parquet.stat().st_mtime_ns == primeira_modificacao
