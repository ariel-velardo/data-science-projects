from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.diagnosticos import (
    COLUNAS_PROPENSITY_PRINCIPAL,
    VARIAVEIS_PROIBIDAS_PROPENSITY,
    calcular_smd,
    validar_colunas_propensity,
)
from src.amostra import (
    construir_cenarios_amostra,
    construir_outcome_baixo_peso,
    construir_tratamento,
    derivar_uf_residencia,
    identificar_gestacao_unica,
)
from src.diagnosticos import diagnosticar_trimming


def test_pipeline_rejeita_outcome_e_oof_cobre_todos():
    from src.diagnosticos import construir_pipeline_propensity, estimar_propensity_oof
    with pytest.raises(ValueError, match="proibidas"):
        construir_pipeline_propensity(["PESO"], [])
    x = pd.DataFrame({"idade": np.tile([20., 30., 40., 50.], 10)})
    t = pd.Series(np.tile([0, 1, 0, 1, 1, 0, 1, 0], 5))
    p, diagnostico = estimar_propensity_oof(x, t, ["idade"], [], 2)
    assert len(p) == len(t)
    assert np.all((p > 0) & (p < 1))
    assert all(f["convergiu"] for f in diagnostico["convergencia"])
    with pytest.raises(ValueError, match="proibidas"):
        estimar_propensity_oof(x.assign(PESO=3000), t, ["idade"], [], 2)


def test_mesprenat_define_tratamento_e_preserva_ignorado_como_ausente() -> None:
    meses = pd.Series(["01", "03", "04", "09", "99", None], dtype="string")

    tratamento = construir_tratamento(meses)

    assert tratamento.tolist()[:4] == [1, 1, 0, 0]
    assert tratamento.iloc[4:].isna().all()


def test_outcome_aplica_regra_de_qualidade_sem_mudar_limiar_de_baixo_peso() -> None:
    pesos = pd.Series(["499", "500", "2499", "2500", "6000", "6001", None])

    p0 = construir_outcome_baixo_peso(pesos, regra_peso="P0")
    p1 = construir_outcome_baixo_peso(pesos, regra_peso="P1")

    assert p0.tolist()[:6] == [1, 1, 1, 0, 0, 0]
    assert p1.iloc[0] is pd.NA or pd.isna(p1.iloc[0])
    assert p1.tolist()[1:5] == [1, 1, 0, 0]
    assert pd.isna(p1.iloc[5])
    assert pd.isna(p1.iloc[6])


def test_gestacao_unica_reconhece_apenas_codigo_um() -> None:
    gravidez = pd.Series(["1", "2", "3", "9", None], dtype="string")

    unica = identificar_gestacao_unica(gravidez)

    assert unica.tolist()[:4] == [True, False, False, False]
    assert unica.iloc[4] is False or not bool(unica.iloc[4])


def test_uf_residencia_e_derivada_sem_alterar_codigo_municipal() -> None:
    municipios = pd.Series(["355030", "330455", "530010", None], dtype="string")
    original = municipios.copy()

    uf = derivar_uf_residencia(municipios)

    assert uf.tolist()[:3] == ["35", "33", "53"]
    assert pd.isna(uf.iloc[3])
    pd.testing.assert_series_equal(municipios, original)


def test_fluxo_da_amostra_reconcilia_exclusoes_e_cenario_final() -> None:
    dados = pd.DataFrame(
        {
            "MESPRENAT": ["01", "04", "99", "02", "05", "03"],
            "PESO": ["3200", "2499", "3000", "499", "6100", "2800"],
            "GRAVIDEZ": ["1", "1", "1", "1", "1", "2"],
            "IDADEMAE": ["25", "30", "22", "28", "31", "27"],
            "ESCMAE2010": ["3", "2", "3", "3", "9", "4"],
            "RACACORMAE": ["4", "1", "4", "2", "4", "1"],
            "ESTCIVMAE": ["1", "2", "1", "5", "1", "2"],
            "PARIDADE": ["0", "1", "0", "1", "1", "0"],
            "QTDFILMORT": ["00", "01", "00", "00", "99", "00"],
            "CODMUNRES": ["355030", "330455", "355030", "230440", "530010", "330455"],
        }
    )

    amostra, fluxo = construir_cenarios_amostra(dados)

    assert fluxo["n_excluido"].sum() == len(dados) - len(amostra)
    assert fluxo.iloc[-1]["etapa"] == "A3"
    assert len(amostra) == 2
    assert set(amostra["tratamento"].astype(int)) == {0, 1}


def test_guarda_de_leakage_rejeita_pos_tratamento_e_outcome() -> None:
    assert "PESO" in VARIAVEIS_PROIBIDAS_PROPENSITY
    assert "CONSPRENAT" in VARIAVEIS_PROIBIDAS_PROPENSITY
    assert "GESTACAO" in VARIAVEIS_PROIBIDAS_PROPENSITY
    assert "Y_BAIXO_PESO" not in COLUNAS_PROPENSITY_PRINCIPAL

    with pytest.raises(ValueError, match="proibidas"):
        validar_colunas_propensity([*COLUNAS_PROPENSITY_PRINCIPAL, "PESO"])


def test_smd_numerico_e_categorico_em_casos_sinteticos() -> None:
    dados = pd.DataFrame(
        {
            "tratamento": [0, 0, 1, 1],
            "idade": [20.0, 20.0, 22.0, 22.0],
            "grupo": ["A", "A", "B", "B"],
        }
    )

    tabela = calcular_smd(
        dados,
        tratamento="tratamento",
        numericas=["idade"],
        categoricas=["grupo"],
    )

    assert set(tabela["variavel"]) == {"idade", "grupo"}
    assert np.isinf(tabela.loc[tabela["variavel"].eq("idade"), "smd_abs"]).item()
    assert tabela.loc[tabela["variavel"].eq("grupo"), "smd_abs"].item() > 0


def test_trimming_e_apenas_diagnostico_e_reconcilia_perdas() -> None:
    propensity = np.array([0.001, 0.02, 0.50, 0.97, 0.999])
    tratamento = np.array([0, 0, 1, 1, 1])

    diagnostico = diagnosticar_trimming(propensity, tratamento)

    sem_trimming = diagnostico.loc[diagnostico["regra"].eq("sem_trimming")].iloc[0]
    moderado = diagnostico.loc[diagnostico["regra"].eq("0.05_0.95")].iloc[0]
    assert sem_trimming["n_mantido"] == 5
    assert moderado["n_mantido"] == 1
    assert moderado["n_excluido"] == 4
