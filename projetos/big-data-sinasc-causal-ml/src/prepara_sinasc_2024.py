"""Conversão reproduzível do CSV oficial em ZIP para Parquet textual."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from src.carrega_sinasc import (
    detectar_formato_csv,
    iterar_csv_em_chunks,
    validar_schema_minimo,
)


@dataclass(frozen=True)
class ResultadoConversao:
    caminho: Path
    registros: int
    colunas: int
    reutilizado: bool


def _resultado_existente(caminho: Path) -> ResultadoConversao:
    metadados = pq.ParquetFile(caminho).metadata
    return ResultadoConversao(
        caminho=caminho,
        registros=metadados.num_rows,
        colunas=metadados.num_columns,
        reutilizado=True,
    )


def converter_zip_para_parquet(
    caminho_zip: str | Path,
    caminho_parquet: str | Path,
    tamanho_chunk: int = 250_000,
    colunas_obrigatorias: set[str] | None = None,
) -> ResultadoConversao:
    """Converte em fluxo e não sobrescreve um Parquet já existente."""

    origem = Path(caminho_zip)
    destino = Path(caminho_parquet)
    if destino.exists():
        return _resultado_existente(destino)

    formato = detectar_formato_csv(origem)
    validar_schema_minimo(
        formato.colunas,
        colunas_obrigatorias or {"contador", "MESPRENAT", "PESO"},
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(destino.suffix + ".tmp")
    if temporario.exists():
        raise FileExistsError(
            f"Parquet temporário encontrado em {temporario}; revise antes de continuar."
        )

    escritor: pq.ParquetWriter | None = None
    registros = 0
    try:
        for chunk in iterar_csv_em_chunks(origem, tamanho_chunk=tamanho_chunk):
            tabela = pa.Table.from_pandas(chunk, preserve_index=False)
            if escritor is None:
                escritor = pq.ParquetWriter(
                    temporario,
                    tabela.schema,
                    compression="zstd",
                    use_dictionary=True,
                )
            escritor.write_table(tabela)
            registros += len(chunk)
    finally:
        if escritor is not None:
            escritor.close()

    if registros == 0:
        raise ValueError("O CSV não contém registros de dados.")
    temporario.replace(destino)
    return ResultadoConversao(destino, registros, len(formato.colunas), False)


if __name__ == "__main__":
    projeto = Path(__file__).resolve().parents[1]
    resultado = converter_zip_para_parquet(
        projeto / "data" / "raw" / "SINASC_2024_csv.zip",
        projeto / "data" / "processed" / "sinasc_2024.parquet",
    )
    print(resultado)
