"""Contratos pequenos para o benchmark preditivo de 2024."""
import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL


def _dados(n=180, seed=19):
    rng = np.random.default_rng(seed)
    x = pd.DataFrame({"IDADEMAE_NUM": rng.normal(28, 5, n)})
    for coluna in COLUNAS_PROPENSITY_PRINCIPAL[1:]:
        x[coluna] = rng.choice(["1", "2", "3"], n)
    t = np.tile([0, 1], n // 2)
    y = np.tile([0, 0, 1, 1, 0, 1], n // 6)
    ordem = rng.permutation(n)
    return x.iloc[ordem].reset_index(drop=True), t[ordem], y[ordem]


def test_grades_congeladas_e_pipelines_historicos():
    from src.benchmark_nuisance import candidatos, criar_pipeline

    p0 = candidatos("logistica")
    hgb = candidatos("hgb")
    extra = candidatos("extra_trees")
    assert len(p0) == 1 and p0[0]["parametros"]["C"] == 1
    assert len(hgb) == 8 and sum(c["historico"] for c in hgb) == 1
    assert len(extra) == 4
    assert {c["parametros"]["max_features"] for c in extra} == {"sqrt", 0.5}
    assert {c["parametros"]["min_samples_leaf"] for c in extra} == {50, 200}
    assert criar_pipeline(p0[0])["modelo"].get_params()["max_iter"] == 500
    assert criar_pipeline(hgb[0])["modelo"].get_params()["max_iter"] == 100
    assert criar_pipeline(extra[0])["modelo"].get_params()["n_jobs"] <= 8


def test_nested_cobre_uma_vez_e_retomada_nao_repete_fits(tmp_path):
    from src.benchmark_nuisance import candidatos, executar_familia

    x, t, _ = _dados()
    spec = candidatos("logistica")
    contrato = {"dados_sha256": "a" * 64, "chave_sha256": "b" * 64}
    primeiro = executar_familia(
        x, t, "propensity", "logistica", spec, tmp_path, contrato,
        n_externos=3, n_internos=3,
    )
    assert primeiro["cobertura_min"] == primeiro["cobertura_max"] == 1
    assert primeiro["fits_realizados"] == 3
    assert len(primeiro["folds"]) == 3
    assert np.isfinite(primeiro["oof"]).all()
    segundo = executar_familia(
        x, t, "propensity", "logistica", spec, tmp_path, contrato,
        n_externos=3, n_internos=3,
    )
    assert segundo["fits_realizados"] == 0
    np.testing.assert_array_equal(primeiro["oof"], segundo["oof"])
    assert all(f["hash_validacao"] for f in segundo["folds"])


def test_execucoes_independentes_reproduzem_oof(tmp_path):
    from src.benchmark_nuisance import candidatos, executar_familia

    x, t, _ = _dados()
    spec = candidatos("logistica")
    contrato = {"dados_sha256": "a" * 64}
    a = executar_familia(x, t, "propensity", "logistica", spec,
                         tmp_path / "a", contrato, n_externos=2, n_internos=2)
    b = executar_familia(x, t, "propensity", "logistica", spec,
                         tmp_path / "b", contrato, n_externos=2, n_internos=2)
    np.testing.assert_array_equal(a["oof"], b["oof"])
    assert a["metricas_oof"] == b["metricas_oof"]


def test_feature_de_desfecho_e_rejeitada_antes_do_fit(tmp_path):
    from src.benchmark_nuisance import candidatos, executar_familia

    x, t, y = _dados()
    x["Y_BAIXO_PESO"] = y
    with pytest.raises(ValueError, match="proibidas"):
        executar_familia(x, t, "propensity", "logistica",
                         candidatos("logistica"), tmp_path,
                         {"dados_sha256": "a" * 64},
                         n_externos=2, n_internos=2)


def test_checkpoint_invalido_e_rejeitado(tmp_path):
    from src.benchmark_nuisance import candidatos, executar_familia

    x, t, _ = _dados()
    spec = candidatos("logistica")
    executar_familia(x, t, "propensity", "logistica", spec, tmp_path,
                     {"dados_sha256": "a" * 64}, n_externos=2, n_internos=2)
    with pytest.raises(ValueError, match="Checkpoint incompatível"):
        executar_familia(x, t, "propensity", "logistica", spec, tmp_path,
                         {"dados_sha256": "c" * 64}, n_externos=2, n_internos=2)


def test_checkpoint_cria_diretorio_local_ainda_ausente(tmp_path):
    from src.benchmark_nuisance import candidatos, executar_familia

    x, t, _ = _dados()
    pasta = tmp_path / "historico"
    resultado = executar_familia(x, t, "propensity", "logistica",
                                 candidatos("logistica"), pasta,
                                 {"dados_sha256": "a" * 64},
                                 n_externos=2, n_internos=2)
    assert resultado["cobertura_min"] == resultado["cobertura_max"] == 1
    assert len(list(pasta.glob("*.npz"))) == 2


def test_nested_tuning_nao_usa_validacao_externa(tmp_path):
    from src.benchmark_nuisance import executar_familia

    x, t, _ = _dados()
    spec = [
        {"id": "hgb_a", "familia": "hgb", "parametros": {"learning_rate": 0.05,
          "max_leaf_nodes": 7, "min_samples_leaf": 10, "l2_regularization": 1.0,
          "max_iter": 5}, "historico": True},
        {"id": "hgb_b", "familia": "hgb", "parametros": {"learning_rate": 0.1,
          "max_leaf_nodes": 7, "min_samples_leaf": 10, "l2_regularization": 1.0,
          "max_iter": 5}, "historico": False},
    ]
    r = executar_familia(x, t, "propensity", "hgb", spec, tmp_path,
                         {"dados_sha256": "a" * 64}, n_externos=2, n_internos=2)
    assert r["fits_realizados"] == 10
    assert len(r["candidatos_internos"]) == 4
    assert all(f["n_validacao_usado_na_selecao"] == 0 for f in r["folds"])
    assert all(f["n_validacao"] + f["n_treino"] == len(x) for f in r["folds"])
    assert all(f["hash_treino"] != f["hash_validacao"] for f in r["folds"])


def test_outcome_apenas_braco_e_media_macro(tmp_path):
    from src.benchmark_nuisance import candidatos, executar_outcome, media_macro

    x, t, y = _dados()
    r0 = executar_outcome(x, t, y, 0, "logistica", candidatos("logistica"),
                          tmp_path, {"dados_sha256": "a" * 64}, n_externos=2, n_internos=2)
    r1 = executar_outcome(x, t, y, 1, "logistica", candidatos("logistica"),
                          tmp_path, {"dados_sha256": "a" * 64}, n_externos=2, n_internos=2)
    assert r0["n"] == int((t == 0).sum())
    assert r1["n"] == int((t == 1).sum())
    assert all(f["n_treino"] + f["n_validacao"] == r0["n"] for f in r0["folds"])
    macro = media_macro(r0["metricas_oof"], r1["metricas_oof"])
    assert macro["log_loss"] == pytest.approx(
        (r0["metricas_oof"]["log_loss"] + r1["metricas_oof"]["log_loss"]) / 2)


def test_regra_um_ep_preserva_historico_e_rejeita_metrica_causal():
    from src.benchmark_nuisance import escolher_um_ep

    historico = {"id": "historico", "historico": True, "log_loss": 0.401,
                 "log_loss_se_folds": 0.003, "brier": 0.1}
    novo = {"id": "novo", "historico": False, "log_loss": 0.400,
            "log_loss_se_folds": 0.003, "brier": 0.1}
    assert escolher_um_ep([historico, novo])["id"] == "historico"
    assert escolher_um_ep([historico | {"log_loss": 0.42}, novo])["id"] == "novo"
    with pytest.raises(ValueError, match="causal"):
        escolher_um_ep([historico | {"aipw_estimativa": 0.1}, novo])


def test_api_propensity_nao_recebe_outcome_e_notebook_plotly():
    from src.benchmark_nuisance import executar_familia

    assert "y" not in inspect.signature(executar_familia).parameters
    caminho = Path(__file__).parents[1] / "notebooks/historico/08c_benchmark_modelos_nuisance.ipynb"
    nb = json.loads(caminho.read_text(encoding="utf-8"))
    markdown = "\n".join("".join(c.get("source", [])) for c in nb["cells"]
                         if c["cell_type"] == "markdown")
    codigo = "\n".join("".join(c.get("source", [])) for c in nb["cells"]
                       if c["cell_type"] == "code")
    assert all(f"## {i}." in markdown for i in range(1, 19))
    assert "plotly.graph_objects" in codigo
    assert "aplicar_tema_ipt" in codigo
    assert "calcular_aipw" not in codigo
    assert "src.inferencia_causal" not in codigo


def test_fechamento_humano_preserva_benchmark_parcial():
    raiz = Path(__file__).parents[1]
    decisao = json.loads((raiz / "outputs/temporal/modelos_nuisance/decisao_modelos_nuisance.json")
                        .read_text(encoding="utf-8"))
    notebook = json.loads((raiz / "notebooks/historico/08c_benchmark_modelos_nuisance.ipynb")
                          .read_text(encoding="utf-8"))
    fonte = "\n".join("".join(c.get("source", [])) for c in notebook["cells"]
                      if c["cell_type"] == "code")

    assert decisao["benchmark"] == "BENCHMARK_NUISANCE_2024_PARCIAL"
    assert decisao["pendencia_extratrees"] == "ACEITA_POR_ORCAMENTO"
    assert decisao["revisao_humana"] == "APROVADA"
    assert decisao["fechamento"] == "PRONTO_PARA_FECHAR_08B_08C"
    assert decisao["propensity"] == "PROPENSITY_SENSIBILIDADE_ML_RECOMENDADA"
    assert decisao["outcome"] == "OUTCOMES_HISTORICOS_MANTIDOS"
    assert '"pendencia_extratrees": "ACEITA_POR_ORCAMENTO"' in fonte
    assert '"revisao_humana": "APROVADA"' in fonte
