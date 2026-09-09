"""Auditoria de timing do tratamento (primeira presenca federal EPT no Censo Escolar).

Criado porque nenhuma rotina existente no projeto pode ser reutilizada: `src/`
so continha um `.gitkeep` no momento desta auditoria (ver
docs/methodology/AUDITORIA_TIMING_TRATAMENTO.md, secao "O que nao foi
realizado").

O script:
1. Varre data/raw, data/interim, data/processed por qualquer fonte tabular
   (csv/parquet/xlsx/json/duckdb) cujo nome sugira tratamento, municipio,
   matching ou Censo Escolar.
2. Se nenhuma fonte for encontrada, gera a tabela de auditoria apenas com o
   cabecalho especificado (0 linhas) -- nao inventa codigos de municipio.
3. Grava outputs/diagnostics/auditoria_timing_tratamento.csv.

Nao baixa dados, nao altera dados brutos, nao estima efeitos.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIRS = [
    PROJECT_ROOT / "data" / "raw",
    PROJECT_ROOT / "data" / "interim",
    PROJECT_ROOT / "data" / "processed",
]
OUTPUT_CSV = PROJECT_ROOT / "outputs" / "diagnostics" / "auditoria_timing_tratamento.csv"

TABULAR_EXTENSIONS = {".csv", ".parquet", ".xlsx", ".xls", ".json", ".duckdb"}
KEYWORDS = re.compile(
    r"tratamento|municip|matching|censo.?escolar|coorte|common.?support|fase.?ii",
    re.IGNORECASE,
)

AUDIT_COLUMNS = [
    "codigo_municipio",
    "municipio",
    "uf",
    "fase_ii",
    "primeiro_ano_presenca",
    "coorte_tratamento",
    "common_support",
    "amostra_core",
    "controle_utilizado",
    "controle_repetido",
    "flag_presenca_anterior",
    "flag_reversao_tratamento",
    "flag_lacuna_timing",
    "flag_caso_especial",
    "status_timing",
    "observacao",
]


def find_candidate_sources() -> list[Path]:
    """Procura arquivos tabulares candidatos nas pastas de dados do projeto."""
    candidates: list[Path] = []
    for base in DATA_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.name == ".gitkeep":
                continue
            if path.suffix.lower() in TABULAR_EXTENSIONS:
                candidates.append(path)
    return candidates


def build_audit_table(candidate_sources: list[Path]) -> pd.DataFrame:
    """Constroi a tabela de auditoria.

    Sem fonte tabular municipal candidata, retorna a tabela vazia (apenas
    cabecalho) -- nenhum valor e inventado.
    """
    if not candidate_sources:
        return pd.DataFrame(columns=AUDIT_COLUMNS)

    # Reservado para uma futura execucao em que exista de fato uma fonte
    # tabular de tratamento/municipio: aqui apenas listamos o que foi
    # encontrado, sem tentar inferir o schema de um arquivo desconhecido
    # (evita inventar mapeamento de colunas).
    raise NotImplementedError(
        "Fontes tabulares candidatas foram encontradas: "
        f"{[str(p) for p in candidate_sources]}. "
        "Este script nao infere schema de fontes desconhecidas; "
        "mapear as colunas manualmente antes de reexecutar."
    )


def main() -> None:
    candidates = find_candidate_sources()
    table = build_audit_table(candidates)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUTPUT_CSV, index=False)
    print(f"Fontes candidatas encontradas: {len(candidates)}")
    for c in candidates:
        print(f"  - {c}")
    print(f"Linhas na tabela de auditoria: {len(table)}")
    print(f"CSV gravado em: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
