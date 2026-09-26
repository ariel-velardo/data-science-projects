from __future__ import annotations

import pandas as pd
from pathlib import Path

from src.audita_sinasc_2024 import (
    construir_baixo_peso_candidato,
    construir_tratamento_candidato,
    gerar_auditoria_parquet,
    resumir_outcome,
    resumir_tratamento,
)


def test_baixo_peso_candidato_respeita_limite_de_2500_gramas() -> None:
    pesos = pd.Series(["2499", "2500", "3000", None, "invalido"], dtype="string")

    resultado = construir_baixo_peso_candidato(pesos)

    assert resultado.tolist()[:3] == [1, 0, 0]
    assert pd.isna(resultado.iloc[3])
    assert pd.isna(resultado.iloc[4])


def test_tratamento_candidato_exclui_ignorado_e_missing() -> None:
    meses = pd.Series(["01", "03", "04", "09", "99", None, "invalido"], dtype="string")

    resultado = construir_tratamento_candidato(meses)

    assert resultado.tolist()[:4] == [1, 1, 0, 0]
    assert resultado.iloc[4:].isna().all()


def test_tratamento_nao_classifica_ausencia_de_prenatal_como_controle() -> None:
    meses = pd.Series(["00", "10"], dtype="string")

    resultado = construir_tratamento_candidato(meses)

    assert resultado.isna().all()


def test_resumo_tratamento_separa_validos_ignorado_e_missing() -> None:
    meses = pd.Series(["01", "03", "04", "09", "99", None], dtype="string")

    resumo = resumir_tratamento(meses)

    assert resumo["n_total"] == 6
    assert resumo["n_utilizavel"] == 4
    assert resumo["n_inicio_ate_terceiro_mes"] == 2
    assert resumo["n_inicio_apos_terceiro_mes"] == 2
    assert resumo["n_codigo_99"] == 1
    assert resumo["n_missing"] == 1


def test_resumo_outcome_mantem_pesos_extremos_como_alerta() -> None:
    pesos = pd.Series(["100", "499", "2499", "2500", "7000", None], dtype="string")

    resumo = resumir_outcome(pesos)

    assert resumo["n_valido"] == 5
    assert resumo["n_baixo_peso"] == 3
    assert resumo["n_abaixo_500g"] == 2
    assert resumo["n_acima_6000g"] == 1
    assert resumo["n_missing_invalido"] == 1


def test_auditoria_parquet_reconcilia_schema_chave_t_e_y(tmp_path: Path) -> None:
    caminho = tmp_path / "sinasc.parquet"
    pd.DataFrame(
        {
            "contador": pd.Series(["1", "2", "3"], dtype="string"),
            "MESPRENAT": pd.Series(["03", "04", "99"], dtype="string"),
            "PESO": pd.Series(["2499", "2500", None], dtype="string"),
            "IDADEMAE": pd.Series(["20", "30", "40"], dtype="string"),
        }
    ).to_parquet(caminho, index=False)

    auditoria = gerar_auditoria_parquet(caminho)

    assert auditoria["dimensoes"] == {"registros": 3, "colunas": 4}
    assert auditoria["identificador"]["contador_unico"] is True
    assert auditoria["tratamento_candidato"]["n_utilizavel"] == 2
    assert auditoria["outcome_candidato"]["n_valido"] == 2
    assert auditoria["outcome_candidato"]["n_baixo_peso"] == 1
    assert len(auditoria["schema_auditado"]) == 4
