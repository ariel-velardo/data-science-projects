"""Testes do D13: diagnósticos offline do gate de identificação causal."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import diagnostica_identificacao_causal as d13  # noqa: E402


def _linha(
    codigo: str, ano: int, valor_708: float | None, *,
    candidato: bool = False, coorte: float | None = None,
    elegivel_controle: bool = False, nunca_exposto: bool = False,
    fase_ii: bool | None = None, motivos_exclusao: str = "",
) -> dict:
    return {
        "codigo_municipio_ibge": codigo,
        "ano": ano,
        "pessoal_ocupado_assalariado": valor_708,
        "status_pessoal_ocupado_assalariado": "observado" if valor_708 is not None else "sigilo",
        "candidato_amostra_principal": candidato,
        "ano_coorte_candidata": coorte,
        "fl_elegivel_controle_candidato": elegivel_controle,
        "sem_exposicao_observada_2007_2019": nunca_exposto,
        "fase_ii": fase_ii,
        "motivos_exclusao": motivos_exclusao,
    }


def _painel_sintetico() -> pd.DataFrame:
    """1 tratado (coorte 2010) + 2 controles elegíveis, 2007-2013.

    Valores do tratado crescem 100/coorte a cada ano (100, 200, ..., 400) só
    para tornar a mudança pré e o índice fáceis de conferir manualmente.
    Os controles ficam estáveis em 50 (controle A) e 30 (controle B) —
    mediana do pool = 40 em cada ano.
    """
    linhas = []
    for i, ano in enumerate(range(2007, 2014)):
        linhas.append(_linha("1100015", ano, 100.0 * (i + 1), candidato=True, coorte=2010.0))
    for ano in range(2007, 2014):
        linhas.append(_linha("2200000", ano, 50.0, elegivel_controle=True, nunca_exposto=True))
        linhas.append(_linha("3300000", ano, 30.0, elegivel_controle=True, nunca_exposto=True))
    # Município nunca exposto fora do pool (universo incompleto) — não deve
    # contaminar as métricas do pool elegível.
    for ano in range(2010, 2014):
        linhas.append(_linha("4400000", ano, 10.0, nunca_exposto=True, motivos_exclusao="universo_incompleto"))
    return pd.DataFrame(linhas)


class TestAuditaPoolControles(unittest.TestCase):
    def test_pool_e_subconjunto_de_nunca_expostos_e_sem_fase_ii(self) -> None:
        resultado = d13.auditar_pool_controles(_painel_sintetico())
        self.assertEqual(resultado["n_pool_elegivel"], 2)
        self.assertEqual(resultado["n_nunca_expostos"], 3)
        self.assertTrue(resultado["pool_e_subconjunto_de_nunca_expostos"])
        self.assertTrue(resultado["pool_sem_fase_ii"])
        self.assertEqual(resultado["n_nunca_exposto_fora_do_pool"], 1)
        self.assertEqual(resultado["motivos_nunca_exposto_fora_do_pool"], {"universo_incompleto": 1})


class TestBaselinePreTratamento(unittest.TestCase):
    def test_baseline_usa_apenas_g_menos_1_e_pool_inteiro(self) -> None:
        tabela = d13.baseline_pre_tratamento_por_coorte(_painel_sintetico(), coortes=[2010])
        linha = tabela.iloc[0]
        self.assertEqual(linha["ano_baseline_g_menos_1"], 2009)
        self.assertEqual(linha["n_tratados"], 1)
        self.assertEqual(linha["n_controles"], 2)
        # ano-índice 2009 é o 3º ano (2007,2008,2009) -> valor = 300.0
        self.assertAlmostEqual(linha["mediana_tratados"], 300.0)
        self.assertAlmostEqual(linha["mediana_controles"], 40.0)

    def test_nenhum_controle_filtrado_por_outcome(self) -> None:
        painel = _painel_sintetico()
        tabela = d13.baseline_pre_tratamento_por_coorte(painel, coortes=[2010])
        self.assertEqual(tabela.iloc[0]["n_controles"], 2)


class TestSeriePreTendencia(unittest.TestCase):
    def test_serie_usa_somente_anos_anteriores_a_coorte(self) -> None:
        serie = d13.serie_pre_tendencia_niveis(_painel_sintetico(), coorte=2010)
        self.assertTrue((serie["ano"] < 2010).all())
        anos_presentes = sorted(serie["ano"].unique())
        self.assertEqual(anos_presentes, [2007, 2008, 2009])

    def test_coorte_2009_so_tem_dois_anos_pre(self) -> None:
        painel = _painel_sintetico().copy()
        painel.loc[painel["candidato_amostra_principal"], "ano_coorte_candidata"] = 2009.0
        serie = d13.serie_pre_tendencia_niveis(painel, coorte=2009)
        anos_presentes = sorted(serie["ano"].unique())
        self.assertEqual(anos_presentes, [2007, 2008])


class TestIndiceNormalizado(unittest.TestCase):
    def test_g_menos_1_igual_a_100(self) -> None:
        serie = d13.serie_pre_tendencia_niveis(_painel_sintetico(), coorte=2010)
        indice = d13.indice_pre_tendencia_normalizado(serie, coorte=2010)
        base_tratados = indice.loc[(indice["grupo"] == "tratados") & (indice["ano"] == 2009), "indice_708"]
        self.assertAlmostEqual(float(base_tratados.iloc[0]), 100.0)
        base_controles = indice.loc[(indice["grupo"] == "controles") & (indice["ano"] == 2009), "indice_708"]
        self.assertAlmostEqual(float(base_controles.iloc[0]), 100.0)

    def test_indice_proporcional_ao_baseline(self) -> None:
        serie = d13.serie_pre_tendencia_niveis(_painel_sintetico(), coorte=2010)
        indice = d13.indice_pre_tendencia_normalizado(serie, coorte=2010)
        # tratado 2007 = 100.0, baseline (2009) = 300.0 -> indice = 33.33
        valor_2007 = indice.loc[(indice["grupo"] == "tratados") & (indice["ano"] == 2007), "indice_708"]
        self.assertAlmostEqual(float(valor_2007.iloc[0]), 100.0 / 300.0 * 100.0, places=4)


class TestMudancaG2G1(unittest.TestCase):
    def test_variacao_absoluta_e_percentual(self) -> None:
        tabela = d13.mudanca_pre_g2_g1(_painel_sintetico(), coortes=[2010])
        tratados = tabela.loc[tabela["grupo"] == "tratados"].iloc[0]
        self.assertEqual(tratados["ano_g2"], 2008)
        self.assertEqual(tratados["ano_g1"], 2009)
        self.assertAlmostEqual(tratados["mediana_g2"], 200.0)
        self.assertAlmostEqual(tratados["mediana_g1"], 300.0)
        self.assertAlmostEqual(tratados["variacao_absoluta"], 100.0)
        self.assertAlmostEqual(tratados["variacao_percentual"], 50.0)

    def test_coorte_2009_usa_2007_2008_como_unica_mudanca_pre(self) -> None:
        painel = _painel_sintetico().copy()
        painel.loc[painel["candidato_amostra_principal"], "ano_coorte_candidata"] = 2009.0
        tabela = d13.mudanca_pre_g2_g1(painel, coortes=[2009])
        tratados = tabela.loc[tabela["grupo"] == "tratados"].iloc[0]
        self.assertEqual(tratados["ano_g2"], 2007)
        self.assertEqual(tratados["ano_g1"], 2008)


class TestNenhumaContaminacaoPos(unittest.TestCase):
    def test_serie_pre_tendencia_nunca_inclui_ano_pos(self) -> None:
        painel = _painel_sintetico()
        for coorte in (2009, 2010, 2011, 2012, 2013):
            serie = d13.serie_pre_tendencia_niveis(painel, coorte=coorte)
            if not serie.empty:
                self.assertTrue((serie["ano"] < coorte).all())


if __name__ == "__main__":
    unittest.main()
