"""Testes do notebook 06 (logística do desfecho e peso contínuo).

Os testes unitários usam dados sintéticos e não precisam das bases do SINASC; o último bloco lê as saídas salvas
do notebook executado. Nenhum teste exige significância estatística: conferem cálculo, ausência de vazamento,
reprodutibilidade e coerência dos intervalos.
"""
import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats
from sklearn.base import BaseEstimator, ClassifierMixin

from src.logistica_desfecho import (CATEGORIAS, MODELOS, PREDITORES_M3, X1, ajustar_modelo, codificar_preditores,
                                    construir_modelo, curva_calibracao, definir_desfechos, metricas_probabilisticas,
                                    prever_fora_da_amostra, razoes_de_chances, validar_preditores)
from src.peso_continuo import anova_welch, comparar_medias_welch, resumir_peso

RAIZ = Path(__file__).resolve().parents[1]
NB06 = RAIZ / "notebooks" / "principal" / "06_analise_preditiva_e_peso.ipynb"


# ------------------------------------------------------------------ peso contínuo

def test_resumir_peso_confere_numpy():
    rng = np.random.default_rng(1)
    peso = pd.Series(np.r_[rng.normal(3200, 500, 400), rng.normal(3000, 600, 300)].round())
    grupo = pd.Series(["a"] * 400 + ["b"] * 300)
    tabela = resumir_peso(peso, grupo)
    b = peso[grupo == "b"].to_numpy()
    linha = tabela.loc["b"]
    assert linha["n"] == 300
    assert linha["media"] == pytest.approx(b.mean())
    assert linha["dp"] == pytest.approx(b.std(ddof=1))
    assert [linha[c] for c in ("p10", "p25", "mediana", "p75", "p90")] == pytest.approx(
        np.percentile(b, [10, 25, 50, 75, 90]))
    assert linha["pct_menor_2500"] == pytest.approx(100 * (b < 2500).mean())
    assert linha["pct_menor_2600"] == pytest.approx(100 * (b < 2600).mean())
    assert linha["ic95_inf"] < linha["media"] < linha["ic95_sup"]


def test_resumir_peso_rejeita_nulos():
    with pytest.raises(ValueError):
        resumir_peso(pd.Series([3000.0, np.nan]), pd.Series(["a", "a"]))


def test_welch_confere_scipy_e_ic_contem_diferenca():
    rng = np.random.default_rng(2)
    a, b = rng.normal(3250, 450, 5000), rng.normal(3150, 600, 800)
    r = comparar_medias_welch(a, b)
    ref = stats.ttest_ind(a, b, equal_var=False)
    assert r["diferenca"] == pytest.approx(a.mean() - b.mean())
    assert (r["t"], r["gl"], r["p"]) == pytest.approx((ref.statistic, ref.df, ref.pvalue))
    assert (r["ic95_inf"], r["ic95_sup"]) == pytest.approx(tuple(ref.confidence_interval(0.95)))
    assert r["ic95_inf"] < r["diferenca"] < r["ic95_sup"]


def test_anova_welch_confere_formula_e_scipy():
    rng = np.random.default_rng(3)
    amostras = {"m1": rng.normal(3200, 400, 300), "m2": rng.normal(3180, 500, 120), "m3": rng.normal(3100, 650, 60)}
    r = anova_welch(amostras)
    assert r["gl1"] == 2 and r["gl2"] > 0 and 0 <= r["p"] <= 1
    if "equal_var" in inspect.signature(stats.f_oneway).parameters:  # Welch no scipy a partir da 1.16
        ref = stats.f_oneway(*amostras.values(), equal_var=False)
        assert (r["F"], r["p"]) == pytest.approx((ref.statistic, ref.pvalue))
    iguais = anova_welch({"a": np.array([1.0, 2, 3, 4]), "b": np.array([2.5, 2.5, 1.5, 3.5])})
    assert iguais["F"] == pytest.approx(0.0) and iguais["p"] == pytest.approx(1.0)


# ------------------------------------------------------------------ logística do desfecho

def test_desfechos_nos_limites():
    y = definir_desfechos(pd.Series([2499, 2500, 2599, 2600, 500, 6000]))
    assert y["Y_2500"].tolist() == [1, 0, 0, 0, 1, 0]
    assert y["Y_2600"].tolist() == [1, 1, 1, 0, 1, 0]


@pytest.mark.parametrize("peso", [[499, 3000], [3000, 6001], [3000, np.nan]])
def test_desfechos_rejeitam_peso_fora_da_elegibilidade(peso):
    with pytest.raises(ValueError):
        definir_desfechos(pd.Series(peso, dtype=float))


@pytest.mark.parametrize("proibida", ["PESO", "peso_num", "SEMAGESTAC", "CONSULTAS", "KOTELCHUCK", "CODESTAB",
                                      "SITUACAO_CONJUGAL", "Y_2600"])
def test_preditores_fora_da_lista_sao_rejeitados(proibida):
    validar_preditores(PREDITORES_M3)
    with pytest.raises(ValueError):
        validar_preditores([*PREDITORES_M3, proibida])


def _sinteticos(n, semente, coef_x1=-0.4):
    """Covariáveis com os níveis declarados e Y de um modelo logístico conhecido."""
    rng = np.random.default_rng(semente)
    x = pd.DataFrame({X1: rng.binomial(1, 0.85, n), "IDADEMAE_NUM": rng.integers(14, 46, n).astype(float)})
    for coluna, (niveis, _) in CATEGORIAS.items():
        x[coluna] = rng.choice(list(niveis), n)
    x["IDADEMAE_QUAD"] = x.IDADEMAE_NUM ** 2
    logito = -2.0 + coef_x1 * x[X1] + 0.4 * (x.ESCOLARIDADE_MAE == "0-1") + 0.002 * (x.IDADEMAE_NUM - 28) ** 2
    y = rng.binomial(1, 1 / (1 + np.exp(-logito)))
    return x[list(PREDITORES_M3)], y


def test_codificacao_agrega_niveis_raros_na_referencia_declarada():
    bruto = pd.DataFrame({X1: [1, 0, 1, 0], "IDADEMAE_NUM": [20.0, 30, 40, 25],
                          "ESCOLARIDADE_MAE": ["0", "1", "IGNORADO", "5"], "RACA_COR_MAE": ["IGNORADO", "4", "1", "2"],
                          "PARIDADE_CAT": ["0", "1", "1", "0"], "PERDAS_FETAIS_CAT": ["IGNORADO", "1", "2_OU_MAIS", "0"]})
    x = codificar_preditores(bruto)
    assert list(x.columns) == list(PREDITORES_M3)
    assert x.ESCOLARIDADE_MAE.tolist() == ["0-1", "0-1", "3", "5"]
    assert x.RACA_COR_MAE.tolist() == ["1", "4", "1", "2"]
    assert x.PERDAS_FETAIS_CAT.tolist() == ["0", "1", "2_OU_MAIS", "0"]
    assert x.IDADEMAE_QUAD.tolist() == [400.0, 900.0, 1600.0, 625.0]
    with pytest.raises(ValueError):
        codificar_preditores(bruto.assign(PARIDADE_CAT=["0", "1", "1", "IGNORADO"]))


def test_categoria_nao_declarada_gera_erro():
    x, y = _sinteticos(2000, 4)
    x.loc[0, "RACA_COR_MAE"] = "9"
    with pytest.raises(ValueError):
        ajustar_modelo(construir_modelo(MODELOS["M3"]), x, y)


def test_or_de_preditor_binario_igual_a_tabela_2x2():
    a, b, c, d = 130, 870, 45, 205  # X1=1: casos, não casos; X1=0: casos, não casos
    x = pd.DataFrame({X1: [1] * (a + b) + [0] * (c + d)})
    y = np.array([1] * a + [0] * b + [1] * c + [0] * d)
    modelo = ajustar_modelo(construir_modelo(MODELOS["M1"]), x, y)
    tabela, diagnostico = razoes_de_chances(modelo, x, y)
    linha = tabela.loc[X1]
    assert linha["or"] == pytest.approx(a * d / (b * c), rel=1e-8)
    assert linha["ep"] == pytest.approx(np.sqrt(1 / a + 1 / b + 1 / c + 1 / d), rel=1e-8)
    assert linha["ic95_inf"] < linha["or"] < linha["ic95_sup"]
    assert diagnostico["gradiente_max"] < 1e-8


def test_recupera_coeficiente_simulado():
    x, y = _sinteticos(60_000, 5, coef_x1=-0.4)
    modelo = ajustar_modelo(construir_modelo(MODELOS["M3"]), x, y)
    tabela, diagnostico = razoes_de_chances(modelo, x, y)
    linha = tabela.loc[X1]
    assert abs(np.log(linha["or"]) - (-0.4)) < 4 * linha["ep"]
    assert diagnostico["gradiente_max"] < 1e-8 and np.isfinite(diagnostico["condicao"])
    assert not {"IDADEMAE_NUM", "IDADEMAE_QUAD"} & set(tabela.index)


class _Espiao(ClassifierMixin, BaseEstimator):
    """Registra as linhas usadas no ajuste e falha se prever alguma delas."""
    registro = []

    def fit(self, x, y):
        self.vistas_ = set(x.index)
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, x):
        assert not self.vistas_ & set(x.index), "linha de treino prevista pelo próprio modelo"
        _Espiao.registro.append(list(x.index))
        return np.tile([0.9, 0.1], (len(x), 1))

    def predict(self, x):
        return np.zeros(len(x), dtype=int)


def test_previsao_fora_da_amostra_sem_vazamento_e_reprodutivel():
    x, y = _sinteticos(1000, 6)
    _Espiao.registro.clear()
    p, dobra = prever_fora_da_amostra(_Espiao(), x, y)
    previstas = [i for bloco in _Espiao.registro for i in bloco]
    assert sorted(previstas) == list(x.index) and len(p) == len(x)
    assert sorted(np.unique(dobra)) == [0, 1, 2, 3, 4]
    p1, dobra1 = prever_fora_da_amostra(construir_modelo(MODELOS["M3"]), x, y)
    p2, dobra2 = prever_fora_da_amostra(construir_modelo(MODELOS["M3"]), x, y)
    assert np.array_equal(p1, p2) and np.array_equal(dobra1, dobra2)
    assert np.isfinite(p1).all() and ((p1 > 0) & (p1 < 1)).all()


def test_metricas_casos_limite():
    y = np.array([0] * 80 + [1] * 20)
    perfeita = metricas_probabilisticas(y, np.where(y == 1, 0.999, 0.001))
    assert perfeita["roc_auc"] == 1 and perfeita["average_precision"] == 1 and perfeita["brier"] < 1e-5
    constante = metricas_probabilisticas(y, np.full(100, 0.2))
    assert constante["roc_auc"] == 0.5 and constante["average_precision"] == pytest.approx(0.2)
    assert constante["brier"] == pytest.approx(0.16) and np.isnan(constante["inclinacao_calibracao"])
    # Prevalências de dobras de treino diferem na 5ª casa: a inclinação continua indefinida.
    quase = metricas_probabilisticas(y, 0.2 + np.tile([0, 1e-5, -1e-5, 2e-5, -2e-5], 20))
    assert np.isnan(quase["inclinacao_calibracao"]) and quase["roc_auc"] == pytest.approx(0.5, abs=0.1)
    rng = np.random.default_rng(7)
    p = rng.uniform(0.02, 0.4, 200_000)
    calibrada = metricas_probabilisticas(rng.binomial(1, p), p)
    assert calibrada["inclinacao_calibracao"] == pytest.approx(1, abs=0.05)
    assert calibrada["dif_media_prevista_observada"] == pytest.approx(0, abs=0.005)


def test_curva_calibracao_por_decis():
    rng = np.random.default_rng(8)
    p = rng.uniform(0.01, 0.5, 5000)
    y = rng.binomial(1, p)
    curva = curva_calibracao(y, p)
    assert len(curva) == 10 and curva.n.sum() == 5000
    assert curva.previsto.is_monotonic_increasing
    assert ((curva.ic95_inf <= curva.observado) & (curva.observado <= curva.ic95_sup)).all()


# ------------------------------------------------------------------ saídas salvas do notebook 06

def _nb06():
    if not NB06.is_file():
        pytest.skip("notebook 06 ainda não gerado")
    return json.loads(NB06.read_text(encoding="utf-8"))


def _textos(celula):
    partes = []
    for o in celula.get("outputs", []):
        partes.append("".join(o.get("text", [])))
        for chave in ("text/plain", "text/html", "text/markdown"):
            valor = o.get("data", {}).get(chave, "")
            partes.append("".join(valor) if isinstance(valor, list) else valor)
    return "\n".join(partes)


def test_notebook_06_executado_sem_erros_e_com_tres_figuras():
    nb = _nb06()
    codigo = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert [c["execution_count"] for c in codigo] == list(range(1, len(codigo) + 1))
    assert not any(o["output_type"] == "error" for c in codigo for o in c.get("outputs", []))
    figuras = [o for c in codigo for o in c.get("outputs", []) if "application/vnd.plotly.v1+json" in o.get("data", {})]
    assert len(figuras) == 3 and all("image/png" in o["data"] for o in figuras)


def test_notebook_06_reproduz_populacoes_do_03_e_conclui_verificacoes():
    nb = _nb06()
    textos = {c["id"]: _textos(c) for c in nb["cells"] if c["cell_type"] == "code"}
    tudo = "\n".join(textos.values())
    assert "P6: 114.694 nascimentos | X1=1 104.576 | X1=0 10.118 | < 2.500 g 9.850 | < 2.600 g 12.962" in tudo
    assert "P9: 116.429 nascimentos" in tudo
    assert "sem mês válido: 993 (889 sem código e 104 com o código 99" in tudo
    assert "Preditores do M3: " + ", ".join(PREDITORES_M3) in tudo
    assert "Verificações do notebook 06 concluídas" in textos["nb06-verificacoes"]
    # Sensibilidade por casos completos ao lado da especificação principal, que não muda.
    associacao = textos["nb06-associacao"]
    assert "OR ajustada (M3, P6, casos completos)" in associacao and "Sem os 94 registros" in associacao
    assert "0,83 (0,78 a 0,88)" in associacao and "0,81 (0,76 a 0,87)" in associacao
    desempenho = textos["nb06-desempenho"]
    assert all(m in desempenho for m in MODELOS) and desempenho.count("< 2.600 g") >= 4
