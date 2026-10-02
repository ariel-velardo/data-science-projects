"""Contratos essenciais da estimação V2 em dados sintéticos pequenos."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL


def _dados(n=800, seed=0):
    rng = np.random.default_rng(seed)
    mes = rng.integers(1, 10, n)
    municipios = np.array(["355030", "350950", "351880", "354340", "330455", "330170"])
    codmun = municipios[rng.integers(0, len(municipios), n)]
    dados = pd.DataFrame({
        "contador": [f"{i:04d}" for i in range(n)],
        "tratamento": (mes <= 3).astype(int),
        "Y_BAIXO_PESO": (rng.random(n) < .2).astype(int),
        "IDADEMAE_NUM": rng.integers(15, 45, n).astype(float),
        "ESCOLARIDADE_MAE": rng.choice(["1", "2", "3"], n),
        "RACA_COR_MAE": rng.choice(["1", "4"], n),
        "SITUACAO_CONJUGAL": rng.choice(["1", "2"], n),
        "PARIDADE_CAT": rng.choice(["0", "1"], n),
        "PERDAS_FETAIS_CAT": rng.choice(["0", "1"], n),
        "UF_RESIDENCIA": [c[:2] for c in codmun],
        "CODMUNRES": codmun,
    })
    ordem = np.lexsort((dados.contador.to_numpy(), dados.UF_RESIDENCIA.to_numpy()))
    return dados.iloc[ordem].reset_index(drop=True), mes[ordem]


def _entrada(sub, formulacao):
    from src.estimativas_temporais import validar_registros

    entrada = validar_registros(sub, 2018)
    entrada.update(parquet_sha256="0" * 64, ordem="sintetica", formulacao=formulacao,
                   status_suporte_09d="APROVADO")
    return entrada


def test_populacoes_b_c_restringem_controles_sem_reclassificar():
    from src.estimacao_v2 import populacao

    dados, mes = _dados()
    b, comp_b = populacao(dados, mes, "B")
    c, comp_c = populacao(dados, mes, "C")
    assert set(comp_b["n_por_mesprenat"]) == {str(m) for m in range(1, 7)}
    assert set(comp_c["n_por_mesprenat"]) == {str(m) for m in range(1, 6)}
    assert len(b) == np.isin(mes, range(1, 7)).sum() and len(c) == np.isin(mes, range(1, 6)).sum()
    assert b.tratamento.sum() == c.tratamento.sum() == dados.tratamento.sum()
    pd.testing.assert_frame_equal(b, dados.loc[np.isin(mes, range(1, 7))].reset_index(drop=True))
    with pytest.raises(ValueError, match="T diverge"):
        populacao(dados.assign(tratamento=1 - dados.tratamento), mes, "B")


def test_ajuste_cobertura_oof_cache_e_rejeicao(tmp_path):
    from src.estimacao_v2 import ajustar, populacao

    dados, mes = _dados()
    sub, _ = populacao(dados, mes, "B")
    entrada = _entrada(sub, "B")
    pred, log = ajustar(sub, entrada, tmp_path)
    assert all(np.isfinite(v).all() and len(v) == len(sub) for v in pred.values())
    assert log["folds"]["cobertura_min"] == log["folds"]["cobertura_max"] == 1
    assert sum(not a["reutilizado"] for a in log["ajustes"]) == 18
    for fold in log["folds"]["folds"]:
        assert fold["n_treino"] + fold["n_validacao"] == len(sub)

    pred2, log2 = ajustar(sub, entrada, tmp_path)
    assert all(a["reutilizado"] for a in log2["ajustes"])
    assert all(np.array_equal(pred[k], pred2[k]) for k in pred)

    # Mesma pasta, contrato divergente (formulação gravada como C): cache rejeitado, nunca reutilizado.
    metadados = next(tmp_path.rglob("e_fold1.json"))
    conteudo = json.loads(metadados.read_text(encoding="utf-8"))
    conteudo["contrato"]["formulacao"] = "C"
    metadados.write_text(json.dumps(conteudo), encoding="utf-8")
    with pytest.raises(ValueError, match="incompatível"):
        ajustar(sub, entrada, tmp_path)


def test_checkpoint_incompativel_lista_campos_divergentes(tmp_path):
    import sklearn

    from src.estimacao_v2 import ajustar_com_diagnostico, contrato_atual, populacao

    dados, mes = _dados()
    sub, _ = populacao(dados, mes, "B")
    entrada = _entrada(sub, "B")
    ajustar_com_diagnostico(sub, entrada, tmp_path)
    # A reconstrução usada no diagnóstico coincide com o contrato gravado por ``ajustar``.
    metadados = sorted(tmp_path.rglob("*_fold*.json"))
    assert len(metadados) == 18
    for arquivo in metadados:
        nome, numero = arquivo.stem.rsplit("_fold", 1)
        salvo = json.loads(arquivo.read_text(encoding="utf-8"))["contrato"]
        assert contrato_atual(sub, entrada, nome, int(numero)) == salvo

    alvo = next(a for a in metadados if a.stem == "m1_C2_fold2")
    conteudo = json.loads(alvo.read_text(encoding="utf-8"))
    conteudo["contrato"]["sklearn"] = "0.0.0"
    alvo.write_text(json.dumps(conteudo), encoding="utf-8")
    antes = alvo.read_bytes()
    with pytest.raises(ValueError) as erro:
        ajustar_com_diagnostico(sub, entrada, tmp_path)
    mensagem = str(erro.value)
    assert mensagem.startswith("Checkpoint incompatível: B/2018/m1_C2/fold2")
    assert [linha for linha in mensagem.splitlines() if linha.startswith("- ")] == [
        f"- sklearn: salvo=0.0.0 atual={sklearn.__version__}"]
    assert ".venv" in mensagem
    assert alvo.read_bytes() == antes


def test_notebook_10_localiza_raiz_a_partir_de_notebooks():
    raiz = Path(__file__).resolve().parents[1]
    notebook = json.loads((raiz / "notebooks/historico/10_estimacao_v2.ipynb").read_text(encoding="utf-8"))
    bootstrap = next(c for c in notebook["cells"] if c["cell_type"] == "code")
    ambiente = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    saida = subprocess.run([sys.executable, "-c", "".join(bootstrap["source"])], cwd=raiz / "notebooks/historico",
                           env={**ambiente, "PYTHONIOENCODING": "utf-8"}, capture_output=True,
                           text=True, encoding="utf-8", check=True)
    assert f"Raiz localizada: {raiz}" in saida.stdout
    assert f"Python do kernel: {sys.executable}" in saida.stdout


def test_formulacao_entra_no_contrato_do_cache():
    from src.estimacao_v2 import contrato_ajuste, populacao, sha256_codigo_v2
    from src.estimativas_temporais import particoes
    from src.modelagem_preditiva import criar_modelo

    dados, mes = _dados()
    sub, _ = populacao(dados, mes, "C")
    _, auditoria = particoes(sub.tratamento.to_numpy(), sub.Y_BAIXO_PESO.to_numpy())
    alvo = sub.tratamento.to_numpy()
    contratos = [contrato_ajuste({**_entrada(sub, f)}, auditoria["folds"][0], "e", "logistica", alvo,
                                 criar_modelo("logistica"), sha256_codigo_v2()) for f in ("B", "C")]
    assert contratos[0] != contratos[1]
    assert contratos[1]["formulacao"] == "C" and contratos[1]["meses"] == [1, 2, 3, 4, 5]
    assert contratos[1]["features"] == list(COLUNAS_PROPENSITY_PRINCIPAL)


def test_resumo_consistente_com_aipw_e_cluster_historicos(tmp_path):
    from src.estimacao_v2 import ajustar, populacao, resumir
    from src.inferencia_causal import calcular_aipw
    from src.robustez import resumo_cluster

    dados, mes = _dados()
    sub, _ = populacao(dados, mes, "B")
    entrada = _entrada(sub, "B")
    pred, _ = ajustar(sub, entrada, tmp_path)
    linhas = resumir(sub, pred, entrada)
    assert len(linhas) == 6
    t, y = sub.tratamento.to_numpy(), sub.Y_BAIXO_PESO.to_numpy()
    iid, psi = calcular_aipw(y, t, pred["e"], pred["m0_C2"], pred["m1_C2"])
    cluster = resumo_cluster(psi, sub.CODMUNRES.to_numpy(dtype=str))
    linha = next(r for r in linhas if r["especificacao"] == "C2" and r["trimming"] == "sem_trimming")
    assert linha["estimativa_pp"] == pytest.approx(iid["estimativa_pp"], abs=1e-12)
    assert linha["se_cluster_pp"] == pytest.approx(cluster["se_cluster_pp"], abs=1e-12)
    assert linha["razao_se_cluster_iid"] == pytest.approx(linha["se_cluster_pp"] / linha["se_iid_pp"])
    assert linha["n_excluido"] == 0 and linha["pct_excluido"] == 0
