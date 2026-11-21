"""Testes da equação do M3 e da interpretabilidade por SHAP (notebook 06).

Os unitários usam dados sintéticos; o último bloco lê as saídas salvas do notebook executado. Os testes conferem
cálculo, aditividade, reprodutibilidade e agregação: nenhum exige ordem de importância nem significância.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

from src.interpretabilidade import (ROTULOS_GRUPOS, TAMANHO_AMOSTRA_SHAP, agrupar_contribuicoes, amostra_reprodutivel,
                                    contribuicao_por_nivel, contribuicoes_lineares, contribuicoes_shap,
                                    erro_reconstrucao, grupos_de_termos, importancia_global)
from src.logistica_desfecho import (CATEGORIAS, DICIONARIO_M3, MODELOS, NUMERICAS, PREDITORES_M3, SEMENTE, X1,
                                    ajustar_modelo, coeficientes_modelo, construir_modelo, nome_do_termo,
                                    preditor_linear_escala_original, razoes_de_chances, resumo_descritivo_m3)

RAIZ = Path(__file__).resolve().parents[1]
NB06 = RAIZ / "notebooks" / "principal" / "06_analise_preditiva_e_peso.ipynb"


def _sinteticos(n, semente):
    """Covariáveis com os níveis declarados do M3 e Y de um modelo logístico conhecido."""
    rng = np.random.default_rng(semente)
    x = pd.DataFrame({X1: rng.binomial(1, 0.85, n), "IDADEMAE_NUM": rng.integers(14, 46, n).astype(float)})
    for coluna, (niveis, _) in CATEGORIAS.items():
        x[coluna] = rng.choice(list(niveis), n)
    x["IDADEMAE_QUAD"] = x.IDADEMAE_NUM ** 2
    logito = (-2.2 - 0.3 * x[X1] + 0.5 * (x.PERDAS_FETAIS_CAT == "2_OU_MAIS") - 0.3 * (x.PARIDADE_CAT == "1")
              + 0.003 * (x.IDADEMAE_NUM - 27) ** 2)
    return x[list(PREDITORES_M3)], rng.binomial(1, expit(logito))


@pytest.fixture(scope="module")
def ajustado():
    x, y = _sinteticos(8000, 11)
    return x, y, ajustar_modelo(construir_modelo(MODELOS["M3"]), x, y)


# ------------------------------------------------------------------ equação do M3

def test_coeficientes_sao_os_estimados_e_nao_reconstruidos(ajustado):
    x, y, modelo = ajustado
    tabela = coeficientes_modelo(modelo)
    nomes = list(modelo[:-1].get_feature_names_out())
    assert list(tabela.index) == ["Intercepto", *nomes]
    assert tabela.loc["Intercepto", "coef_desenho"] == modelo[-1].intercept_[0]
    assert np.array_equal(tabela.loc[nomes, "coef_desenho"].to_numpy(), modelo[-1].coef_.ravel())
    # As OR publicadas são exp do mesmo coeficiente.
    ors, _ = razoes_de_chances(modelo, x, y)
    assert np.allclose(np.log(ors["or"]), tabela.loc[ors.index, "coef_desenho"], rtol=0, atol=1e-12)


def test_escala_original_desfaz_a_padronizacao(ajustado):
    x, _, modelo = ajustado
    tabela = coeficientes_modelo(modelo)
    escala = modelo[:-1][-1].named_transformers_["numericas"]
    for termo, media, dp in zip(escala.feature_names_in_, escala.mean_, escala.scale_):
        assert tabela.loc[termo, "coef_original"] == pytest.approx(tabela.loc[termo, "coef_desenho"] / dp)
        assert tabela.loc[termo, ["media_padronizacao", "dp_padronizacao"]].tolist() == pytest.approx([media, dp])
    # Indicadores e X1 não são padronizados: o coeficiente é o mesmo nas duas escalas.
    binarios = [t for t in tabela.index if t not in ("Intercepto", *NUMERICAS)]
    assert np.array_equal(tabela.loc[binarios, "coef_original"], tabela.loc[binarios, "coef_desenho"])
    eta = preditor_linear_escala_original(tabela, x)
    assert np.max(np.abs(eta - modelo.decision_function(x))) < 1e-9
    assert np.max(np.abs(expit(eta) - modelo.predict_proba(x)[:, 1])) < 1e-12


def test_rotulos_e_dicionario_cobrem_o_modelo(ajustado):
    _, _, modelo = ajustado
    rotulos = [nome_do_termo(t) for t in ["Intercepto", *modelo[:-1].get_feature_names_out()]]
    assert len(set(rotulos)) == len(rotulos)
    with pytest.raises(KeyError):
        nome_do_termo("SITUACAO_CONJUGAL_2")
    no_dicionario = " ".join(d["modelo"] for d in DICIONARIO_M3)
    assert all(p in no_dicionario for p in PREDITORES_M3) and "Y_2500" in no_dicionario
    assert all(d["referencia"] and d["ignorados"] for d in DICIONARIO_M3)


def test_resumo_descritivo_soma_a_populacao(ajustado):
    x, y, _ = ajustado
    resumo = resumo_descritivo_m3(x, y, y)
    assert (resumo.groupby("variavel").n.sum() == len(x)).all()
    assert resumo.groupby("variavel").pct.sum().to_numpy() == pytest.approx(100)


# ------------------------------------------------------------------ SHAP

def test_amostra_reprodutivel():
    a, b = amostra_reprodutivel(5000, 300, 7), amostra_reprodutivel(5000, 300, 7)
    assert np.array_equal(a, b) and len(np.unique(a)) == 300 and np.all(np.diff(a) > 0) and a.max() < 5000
    assert not np.array_equal(a, amostra_reprodutivel(5000, 300, 8))
    assert len(amostra_reprodutivel(20_000)) == TAMANHO_AMOSTRA_SHAP
    for tamanho in (0, 5001):
        with pytest.raises(ValueError):
            amostra_reprodutivel(5000, tamanho)


def test_decomposicao_linear_reconstroi_o_logit(ajustado):
    x, _, modelo = ajustado
    explicar = x.iloc[amostra_reprodutivel(len(x), 500, SEMENTE)]
    phi, base = contribuicoes_lineares(modelo, explicar, x)
    assert erro_reconstrucao(phi, base, modelo.decision_function(explicar)) < 1e-10
    # Com o fundo igual ao universo, o valor-base é o logit médio e a média de cada φ no universo é zero.
    phi_todos, base_todos = contribuicoes_lineares(modelo, x, x)
    assert base_todos == pytest.approx(modelo.decision_function(x).mean(), abs=1e-12) and base == base_todos
    assert np.abs(phi_todos.mean()).max() < 1e-12
    # Invariância à padronização: φ da idade = (β/σ)·(idade − média), em anos.
    tabela = coeficientes_modelo(modelo)
    esperado = tabela.loc["IDADEMAE_NUM", "coef_original"] * (explicar.IDADEMAE_NUM - x.IDADEMAE_NUM.mean())
    assert np.allclose(phi["IDADEMAE_NUM"], esperado, rtol=0, atol=1e-10)


def test_shap_linear_explainer_igual_a_decomposicao_exata(ajustado):
    pytest.importorskip("shap")
    x, _, modelo = ajustado
    explicar = x.iloc[amostra_reprodutivel(len(x), 400, 3)]
    phi_shap, base_shap = contribuicoes_shap(modelo, explicar, x)
    phi_exato, base_exato = contribuicoes_lineares(modelo, explicar, x)
    assert list(phi_shap.columns) == list(phi_exato.columns)
    assert np.max(np.abs((phi_shap - phi_exato).to_numpy())) < 1e-10 and base_shap == pytest.approx(base_exato)
    assert erro_reconstrucao(phi_shap, base_shap, modelo.decision_function(explicar)) < 1e-10


def test_agrupamento_soma_linha_a_linha_antes_do_valor_absoluto(ajustado):
    x, _, modelo = ajustado
    phi, _ = contribuicoes_lineares(modelo, x.iloc[:300], x)
    grupos = grupos_de_termos(phi.columns)
    assert list(grupos) == ["IDADE", X1, *CATEGORIAS]
    assert grupos["IDADE"] == ["IDADEMAE_NUM", "IDADEMAE_QUAD"] and set(grupos) <= set(ROTULOS_GRUPOS)
    agrupado = agrupar_contribuicoes(phi, grupos)
    assert np.allclose(agrupado.sum(axis=1), phi.sum(axis=1), rtol=0, atol=1e-12)
    # Idade e idade² se compensam: a importância conjunta não é a soma das importâncias separadas.
    separadas = phi[grupos["IDADE"]].abs().mean().sum()
    assert importancia_global(agrupado)["IDADE"] < separadas
    with pytest.raises(ValueError):
        agrupar_contribuicoes(phi, {k: v for k, v in grupos.items() if k != "IDADE"})
    with pytest.raises(ValueError):
        grupos_de_termos([*phi.columns, "SITUACAO_CONJUGAL_2"])


def test_importancia_ordenada_e_contribuicao_constante_por_nivel(ajustado):
    x, _, modelo = ajustado
    phi, _ = contribuicoes_lineares(modelo, x.iloc[:2000], x)
    agrupado = agrupar_contribuicoes(phi, grupos_de_termos(phi.columns))
    imp = importancia_global(agrupado)
    assert imp.is_monotonic_decreasing and (imp >= 0).all()
    niveis = contribuicao_por_nivel(agrupado, x)
    assert (niveis.groupby("grupo").n.sum() == 2000).all()
    assert np.allclose(niveis.phi_min, niveis.phi_max, rtol=0, atol=1e-12)


# ------------------------------------------------------------------ saídas salvas do notebook 06

def _nb06():
    if not NB06.is_file():
        pytest.skip("notebook 06 ainda não gerado")
    return json.loads(NB06.read_text(encoding="utf-8"))


def _texto(celula):
    partes = []
    for o in celula.get("outputs", []):
        partes.append("".join(o.get("text", [])))
        for chave in ("text/plain", "text/markdown"):
            valor = o.get("data", {}).get(chave, "")
            partes.append("".join(valor) if isinstance(valor, list) else valor)
    return "\n".join(partes)


def test_notebook_06_secoes_de_equacao_e_shap_executadas():
    celulas = {c["id"]: c for c in _nb06()["cells"]}
    for ident in ("nb06-equacao", "nb06-coeficientes", "nb06-dicionario", "nb06-secao-shap", "nb06-shap"):
        assert ident in celulas, ident
    coeficientes, shap_txt = _texto(celulas["nb06-coeficientes"]), _texto(celulas["nb06-shap"])
    assert "Equação conferida" in coeficientes
    assert "SHAP conferido" in shap_txt and f"amostra de {TAMANHO_AMOSTRA_SHAP:,}".replace(",", ".") in shap_txt
    assert "log-odds" in shap_txt and "Verificações do notebook 06 concluídas" in _texto(celulas["nb06-verificacoes"])
    proibidos = ("causou", "impactou")
    assert not any(p in _texto(celulas[i]).lower() for i in ("nb06-shap", "nb06-coeficientes") for p in proibidos)
