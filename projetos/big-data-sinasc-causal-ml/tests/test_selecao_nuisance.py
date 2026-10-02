"""Contrato pré-especificado para seleção de nuisance models sem usar efeito causal."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import json
import inspect
from pathlib import Path


def _x_sintetico(n: int = 600, seed: int = 20240925) -> pd.DataFrame:
    from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL

    rng = np.random.default_rng(seed)
    x = pd.DataFrame({"IDADEMAE_NUM": rng.normal(28, 6, n)})
    for coluna in COLUNAS_PROPENSITY_PRINCIPAL[1:]:
        x[coluna] = rng.choice(["1", "2", "3"], n)
    return x.loc[:, list(COLUNAS_PROPENSITY_PRINCIPAL)]


def _xt_balanceado(n_pares: int = 600, seed: int = 20240925):
    base = _x_sintetico(n=n_pares, seed=seed)
    x = pd.concat([base, base], ignore_index=True)
    t = np.r_[np.zeros(n_pares, dtype=int), np.ones(n_pares, dtype=int)]
    ordem = np.random.default_rng(seed).permutation(len(x))
    return x.iloc[ordem].reset_index(drop=True), t[ordem]


def test_grade_pequena_preserva_baseline_certificado():
    from src.selecao_nuisance import BASELINE_C, GRADE_C_PROPENSITY

    assert GRADE_C_PROPENSITY == (0.01, 0.1, 1.0, 10.0, 100.0)
    assert BASELINE_C == 1.0


def test_metricas_probabilidade_reconciliam_prevalencia_e_scores():
    from src.selecao_nuisance import metricas_probabilidade

    y = np.array([0, 0, 1, 1])
    p = np.array([0.1, 0.2, 0.8, 0.9])
    resultado = metricas_probabilidade(y, p, n_bins=2)
    assert resultado["prevalencia"] == pytest.approx(0.5)
    assert resultado["media_predita"] == pytest.approx(0.5)
    assert 0 < resultado["log_loss"] < 0.3
    assert 0 < resultado["brier"] < 0.1
    assert resultado["auc"] == pytest.approx(1.0)
    assert resultado["erro_calibracao_medio"] >= 0


def test_balanceamento_iptw_reduz_desequilibrio_conhecido():
    from src.selecao_nuisance import diagnosticos_propensity

    x = pd.DataFrame({
        "idade": np.r_[np.repeat(20.0, 100), np.repeat(40.0, 100)],
        "perfil": np.r_[np.repeat("A", 100), np.repeat("B", 100)],
    })
    t = np.r_[np.repeat(0, 80), np.repeat(1, 20), np.repeat(0, 20), np.repeat(1, 80)]
    e = np.r_[np.repeat(0.2, 100), np.repeat(0.8, 100)]
    resultado = diagnosticos_propensity(x, t, e, numericas=("idade",), categoricas=("perfil",))
    assert resultado["max_abs_smd_bruto"] > 1
    assert resultado["max_abs_smd_ponderado"] == pytest.approx(0.0, abs=1e-12)
    assert resultado["ess_t0_sobre_n"] == pytest.approx(resultado["ess_t1_sobre_n"])
    assert resultado["fora_005_095_fracao"] == 0


def _resultado(C, log_loss, se, brier=0.1, smd=0.05, ess=0.7, cauda=0.05):
    return {
        "C": C,
        "log_loss": log_loss,
        "log_loss_se_folds": se,
        "brier": brier,
        "erro_calibracao_medio": 0.01,
        "auc": 0.65,
        "max_abs_smd_ponderado": smd,
        "ess_t0_sobre_n": ess,
        "ess_t1_sobre_n": 0.95,
        "fora_005_095_fracao": cauda,
    }


def test_selecao_preserva_c1_quando_baseline_esta_na_regra_de_um_erro_padrao():
    from src.selecao_nuisance import selecionar_candidato_propensity

    candidatos = [_resultado(0.1, 0.399, 0.002), _resultado(1.0, 0.400, 0.002)]
    escolha = selecionar_candidato_propensity(candidatos)
    assert escolha["C_escolhido"] == 1.0
    assert escolha["baseline_preservado"]
    assert escolha["criterio"] == "baseline-first dentro de 1 EP e guardrails"


def test_selecao_troca_baseline_somente_quando_ele_falha_regra_pre_especificada():
    from src.selecao_nuisance import selecionar_candidato_propensity

    candidatos = [_resultado(0.1, 0.390, 0.001), _resultado(1.0, 0.410, 0.001)]
    escolha = selecionar_candidato_propensity(candidatos)
    assert escolha["C_escolhido"] == 0.1
    assert not escolha["baseline_preservado"]


def test_selecao_rejeita_qualquer_metrica_causal():
    from src.selecao_nuisance import selecionar_candidato_propensity

    candidatos = [_resultado(1.0, 0.4, 0.01) | {"aipw_estimativa": -0.01}]
    with pytest.raises(ValueError, match="causal"):
        selecionar_candidato_propensity(candidatos)


def test_piloto_oof_e_deterministico_e_cobre_cada_observacao_uma_vez():
    from src.selecao_nuisance import avaliar_grade_propensity

    x = _x_sintetico()
    rng = np.random.default_rng(8)
    logits = -0.5 + 0.04 * (x.IDADEMAE_NUM.to_numpy() - 28)
    t = rng.binomial(1, 1 / (1 + np.exp(-logits)))
    a = avaliar_grade_propensity(x, t, candidatos=(0.1, 1.0), n_folds=3)
    b = avaliar_grade_propensity(x, t, candidatos=(0.1, 1.0), n_folds=3)
    assert a["resultados"] == b["resultados"]
    assert a["auditoria"]["cobertura_min"] == a["auditoria"]["cobertura_max"] == 1
    assert a["auditoria"]["usa_outcome"] is False
    assert len(a["auditoria"]["folds"]) == 3
    assert {r["C"] for r in a["resultados"]} == {0.1, 1.0}


def test_nested_propensity_separa_tuning_interno_da_validacao_externa():
    from src.selecao_nuisance import executar_selecao_nested_propensity

    x, t = _xt_balanceado(n_pares=600, seed=19)

    resultado = executar_selecao_nested_propensity(
        x,
        t,
        candidatos=(0.1, 1.0),
        n_folds_externos=3,
        n_folds_internos=2,
    )

    assert resultado["auditoria"]["cobertura_min"] == 1
    assert resultado["auditoria"]["cobertura_max"] == 1
    assert resultado["auditoria"]["total_fits_previstos"] == 15
    assert resultado["auditoria"]["total_fits_realizados"] == 15
    assert resultado["auditoria"]["usa_outcome"] is False
    assert len(resultado["folds"]) == 3
    assert len(resultado["candidatos"]) == 6
    assert np.isfinite(resultado["oof_externo"]).all()
    assert set(resultado["fold_externo_id"]) == {1, 2, 3}
    assert all(fold["n_treino"] + fold["n_validacao"] == len(x) for fold in resultado["folds"])
    assert all(fold["n_validacao_usado_na_selecao"] == 0 for fold in resultado["folds"])


def test_nested_propensity_e_deterministico_e_nao_recebe_outcome():
    from src.selecao_nuisance import executar_selecao_nested_propensity

    parametros = inspect.signature(executar_selecao_nested_propensity).parameters
    assert not {"y", "outcome", "Y_BAIXO_PESO"}.intersection(parametros)

    x, t = _xt_balanceado(n_pares=500, seed=23)
    a = executar_selecao_nested_propensity(
        x, t, candidatos=(0.1, 1.0), n_folds_externos=2, n_folds_internos=2
    )
    b = executar_selecao_nested_propensity(
        x, t, candidatos=(0.1, 1.0), n_folds_externos=2, n_folds_internos=2
    )

    assert np.array_equal(a["oof_externo"], b["oof_externo"])
    colunas_deterministicas = (
        "outer_fold", "n_treino", "n_validacao", "hash_treino", "hash_validacao",
        "C_menor_log_loss_interno", "C_escolhido", "baseline_preservado",
        "limite_um_ep", "n_validacao_usado_na_selecao",
    )
    assert [
        {chave: fold[chave] for chave in colunas_deterministicas} for fold in a["folds"]
    ] == [
        {chave: fold[chave] for chave in colunas_deterministicas} for fold in b["folds"]
    ]
    assert a["candidatos"] == b["candidatos"]
    assert a["metricas_oof"] == b["metricas_oof"]


def test_outputs_nested_sao_pequenos_e_cache_oof_fica_separado(tmp_path):
    from src.selecao_nuisance import (
        executar_selecao_nested_propensity,
        salvar_resultado_nested_propensity,
    )

    x, t = _xt_balanceado(n_pares=600, seed=31)
    resultado = executar_selecao_nested_propensity(
        x, t, candidatos=(0.1, 1.0), n_folds_externos=2, n_folds_internos=2
    )
    pasta_outputs = tmp_path / "outputs"
    caminho_cache = tmp_path / "cache" / "nested_oof.npz"
    arquivos = salvar_resultado_nested_propensity(
        resultado,
        pasta_outputs=pasta_outputs,
        caminho_cache=caminho_cache,
        contexto={"ano": 2024, "n": len(x), "n_t0": int((t == 0).sum()), "n_t1": int((t == 1).sum())},
        baseline_metricas=resultado["metricas_oof"],
    )

    assert set(arquivos) == {"resumo", "folds", "candidatos", "cache_oof"}
    assert caminho_cache.exists()
    assert not any(p.suffix == ".npz" for p in pasta_outputs.iterdir())
    assert all(Path(arquivos[chave]).stat().st_size < 1_000_000 for chave in ("resumo", "folds", "candidatos"))
    resumo = json.loads(Path(arquivos["resumo"]).read_text(encoding="utf-8"))
    assert resumo["auditoria"]["total_fits_realizados"] == 10
    assert resumo["cache_oof"]["versionado"] is False


def test_notebook_08b_tem_as_doze_secoes_e_nao_executa_estimacao_causal():
    caminho = Path(__file__).parents[1] / "notebooks/historico/08b_selecao_modelos_nuisance.ipynb"
    notebook = json.loads(caminho.read_text(encoding="utf-8"))
    markdown = "\n".join(
        "".join(celula.get("source", ""))
        for celula in notebook["cells"]
        if celula["cell_type"] == "markdown"
    )
    codigo = "\n".join(
        "".join(celula.get("source", ""))
        for celula in notebook["cells"]
        if celula["cell_type"] == "code"
    )
    for numero in range(1, 13):
        assert f"## {numero}." in markdown
    assert "src.inferencia_causal" not in codigo
    assert "calcular_aipw" not in codigo
    assert "Y_BAIXO_PESO" not in codigo.replace("'Y_BAIXO_PESO'}.intersection(x.columns)", "")
    assert "notebook_09_criado': False" in codigo
