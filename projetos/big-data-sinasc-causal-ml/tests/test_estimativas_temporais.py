"""Contratos leves do AIPW anual; sem treinar modelos nacionais."""
import json

import numpy as np
import pandas as pd
import pytest

from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL


def _dados(n=120):
    dados = pd.DataFrame({
        "contador": [f"{i:03d}" for i in range(n)],
        "tratamento": np.tile([0, 0, 1, 1], n // 4),
        "Y_BAIXO_PESO": np.tile([0, 1, 0, 1], n // 4),
        "IDADEMAE_NUM": np.full(n, 27.0),
        "ESCOLARIDADE_MAE": ["2"] * n,
        "RACA_COR_MAE": ["1"] * n,
        "SITUACAO_CONJUGAL": ["1"] * n,
        "PARIDADE_CAT": ["0"] * n,
        "PERDAS_FETAIS_CAT": ["0"] * n,
        "UF_RESIDENCIA": ["35"] * n,
        "CODMUNRES": ["355030", "350950", "351880", "354340"] * (n // 4),
    })
    return dados


def test_entrada_exige_chave_unica_e_features_pre_tratamento():
    from src.estimativas_temporais import validar_registros

    dados = _dados()
    contrato = validar_registros(dados, 2018)
    assert contrato["n"] == 120
    assert contrato["features"] == list(COLUNAS_PROPENSITY_PRINCIPAL)
    assert len(contrato["chave_sha256"]) == 64
    with pytest.raises(ValueError, match="ordem"):
        validar_registros(dados.iloc[::-1].reset_index(drop=True), 2018)
    with pytest.raises(ValueError, match="chave"):
        validar_registros(pd.concat([dados, dados.iloc[:1]]), 2018)
    with pytest.raises(ValueError, match="pós-tratamento"):
        validar_registros(dados.assign(APGAR1=9), 2018)


def test_bloqueio_c3_nao_apaga_c1_c2():
    from src.estimativas_temporais import resumir_aipw

    dados = _dados()
    n = len(dados)
    pred = {"e": np.full(n, .5), "e_C3": np.full(n, np.nan),
            "m0_C1": np.full(n, .1), "m1_C1": np.full(n, .08),
            "m0_C2": np.full(n, .11), "m1_C2": np.full(n, .07)}
    linhas = resumir_aipw(dados, pred, 2018)
    assert all(r["status"] == "CONCLUIDO" for r in linhas if r["especificacao"] != "C3")
    assert all(r["status"] == "BLOQUEADO" for r in linhas if r["especificacao"] == "C3")


def test_chave_contador_maiuscula_do_sql_antigo_e_normalizada():
    from src.estimativas_temporais import normalizar_colunas_identificacao

    dados = _dados().rename(columns={"contador": "CONTADOR", "CODMUNRES": "codmunres"})
    normalizado = normalizar_colunas_identificacao(dados)
    assert "contador" in normalizado and "CONTADOR" not in normalizado
    assert "CODMUNRES" in normalizado and "codmunres" not in normalizado
    assert normalizado.contador.iloc[0] == "000"
    with pytest.raises(ValueError, match="ambígua"):
        normalizar_colunas_identificacao(dados.assign(contador="outro"))


def test_folds_congelados_estratificam_ty_e_cobrem_uma_vez():
    from src.estimativas_temporais import particoes

    dados = _dados()
    folds, auditoria = particoes(dados.tratamento.to_numpy(),
                               dados.Y_BAIXO_PESO.to_numpy())
    cobertura = np.zeros(len(dados), dtype=int)
    for treino, validacao in folds:
        assert not np.intersect1d(treino, validacao).size
        assert set((2 * dados.tratamento.to_numpy()[validacao]
                    + dados.Y_BAIXO_PESO.to_numpy()[validacao])) == {0, 1, 2, 3}
        cobertura[validacao] += 1
    assert np.all(cobertura == 1)
    assert auditoria["seed"] == 20240925 and auditoria["n_folds"] == 3


def test_checkpoint_retomada_rejeita_contrato_incompativel(tmp_path):
    from src.estimativas_temporais import guardar_checkpoint, ler_checkpoint

    caminho = tmp_path / "e_fold1"
    contrato = {"ano": 2018, "fold": 1, "modelo": "e", "parquet_sha256": "a" * 64}
    vetor = np.array([0.2, 0.8])
    guardar_checkpoint(caminho, contrato, vetor, {"segundos": 1.0})
    np.testing.assert_array_equal(ler_checkpoint(caminho, contrato)[0], vetor)
    with pytest.raises(ValueError, match="incompatível"):
        ler_checkpoint(caminho, contrato | {"fold": 2})
    with pytest.raises(FileExistsError):
        guardar_checkpoint(caminho, contrato, vetor, {})


def test_aipw_sintetico_preserva_compartilhamento_e_inferencia():
    from src.estimativas_temporais import resumir_aipw
    from src.inferencia_causal import calcular_aipw

    dados = _dados()
    n = len(dados)
    pred = {"e": np.full(n, 0.5), "e_C3": np.full(n, 0.6),
            "m0_C1": np.full(n, 0.1), "m1_C1": np.full(n, 0.08),
            "m0_C2": np.full(n, 0.11), "m1_C2": np.full(n, 0.07)}
    linhas = resumir_aipw(dados, pred, 2018)
    assert len(linhas) == 6
    c1 = next(r for r in linhas if r["especificacao"] == "C1"
              and r["trimming"] == "sem_trimming")
    historico, _ = calcular_aipw(dados.Y_BAIXO_PESO, dados.tratamento,
                                  pred["e"], pred["m0_C1"], pred["m1_C1"])
    assert c1["estimativa_pp"] == pytest.approx(historico["estimativa_pp"])
    assert c1["se_iid_pp"] == pytest.approx(historico["se_pp"])
    assert c1["n_clusters"] == 4 and c1["se_cluster_pp"] >= 0
    assert {r["propensity_modelo"] for r in linhas if r["especificacao"] in ("C1", "C2")} == {"logistica_C1"}
    assert {r["outcome_modelo"] for r in linhas if r["especificacao"] in ("C2", "C3")} == {"hgb_historico"}


def test_janelas_comuns_identicas_sem_novos_fits():
    from src.estimativas_temporais import montar_janelas

    linhas = [{"ano": ano, "especificacao": "C1", "trimming": "sem_trimming",
               "estimativa_pp": float(ano)} for ano in range(2014, 2025)]
    principal, sensibilidade = montar_janelas(linhas)
    assert len(principal) == 11 and len(sensibilidade) == 7
    assert sensibilidade == [r for r in principal if r["ano"] >= 2018]


def test_reexecucao_anual_nao_substitui_estimativa_divergente(tmp_path):
    from src.estimativas_temporais import _conferir_reexecucao_anual

    caminho = tmp_path / "ano_2014.json"
    linha = {"especificacao": "C1", "trimming": "sem_trimming", "n": 100,
             "n_t0": 40, "n_t1": 60, "n_excluido": 0,
             "estimativa_pp": -1.0, "se_iid_pp": .1, "se_cluster_pp": .2}
    caminho.write_text(json.dumps({"efeitos": [linha]}), encoding="utf-8")
    _conferir_reexecucao_anual(caminho, [linha.copy()])
    with pytest.raises(ValueError, match="divergiu"):
        _conferir_reexecucao_anual(caminho, [linha | {"estimativa_pp": -1.1}])
