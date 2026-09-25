"""Testes da D18: reavaliação do gate pré-estimação sem estimar efeitos."""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import reavalia_gate_pre_estimacao as d18  # noqa: E402


def _amostra_sintetica() -> pd.DataFrame:
    linhas: list[dict] = []
    unidades = [
        ("3300704", "Cabo Frio", "TRATADO_PRINCIPAL", 2010.0, "33", 100.0, 10.0),
        ("1100015", "Tratado A", "TRATADO_PRINCIPAL", 2012.0, "11", 60.0, 4.0),
        ("1100023", "Tratado B", "TRATADO_PRINCIPAL", 2013.0, "11", 40.0, 3.0),
        ("1100031", "Controle A", "CONTROLE_NEVER_TREATED", None, "11", 20.0, 2.0),
        ("3300100", "Controle B", "CONTROLE_NEVER_TREATED", None, "33", 30.0, 2.5),
    ]
    for codigo, municipio, papel, coorte, uf, base, crescimento in unidades:
        for ano in range(2007, 2020):
            cabo_2009 = codigo == "3300704" and ano == 2009
            valor = base + crescimento * (ano - 2007)
            linhas.append(
                {
                    "codigo_municipio_ibge": codigo,
                    "ano": ano,
                    "uf_codigo": uf,
                    "municipio_fonte": municipio,
                    "papel_causal": papel,
                    "coorte_g": coorte,
                    "tempo_relativo": ano - coorte if coorte is not None else None,
                    "elegivel_estimacao_principal": not cabo_2009,
                    "motivo_nao_elegibilidade_estimacao": (
                        "ANO_TRANSICAO_INSTITUCIONAL_CABO_FRIO_2009" if cabo_2009 else None
                    ),
                    "pessoal_ocupado_assalariado": valor,
                    "pessoal_ocupado_total": valor * 1.2,
                    "qt_unidades_locais": valor / 5,
                    "salario_medio_reais_nominal": 1000.0 + 20 * (ano - 2007),
                    "status_pessoal_ocupado_assalariado": "observado",
                }
            )
    return pd.DataFrame(linhas)


class TestRestricaoPreTratamento(unittest.TestCase):
    def test_selecao_nunca_inclui_ano_g_ou_posterior(self) -> None:
        resultado = d18.selecionar_painel_pre_coorte(_amostra_sintetica(), 2012)
        self.assertTrue(resultado["ano"].lt(2012).all())
        self.assertTrue(resultado["tempo_relativo_pre"].lt(0).all())
        self.assertEqual(set(resultado["grupo"]), {"TRATADOS_COORTE", "CONTROLES_NEVER_TREATED"})

    def test_log1p_permanece_rotulado_como_diagnostico(self) -> None:
        resultado = d18.resumir_tendencias_escala(_amostra_sintetica(), coortes=(2012,))
        self.assertEqual(set(resultado["uso_log1p"]), {"APENAS_DIAGNOSTICO_NAO_ALTERA_OUTCOME_PRINCIPAL"})


class TestOverlapATT(unittest.TestCase):
    def test_distingue_falta_de_suporte_do_tratado_de_cauda_irrelevante_de_controles(self) -> None:
        scores = pd.DataFrame(
            {
                "codigo_municipio_ibge": ["t1", "t2", "t3", "c1", "c2", "c3"],
                "tratado": [True, True, True, False, False, False],
                "propensity_score": [0.20, 0.60, 0.90, 0.05, 0.30, 0.80],
            }
        )
        classificado, resumo = d18.classificar_suporte_att(scores)

        self.assertEqual(resumo["n_tratados_acima_max_controles"], 1)
        self.assertEqual(resumo["n_tratados_abaixo_min_controles"], 0)
        self.assertEqual(resumo["n_controles_abaixo_min_tratados"], 1)
        self.assertEqual(resumo["n_controles_acima_max_tratados"], 0)
        self.assertEqual(
            classificado.loc[classificado["codigo_municipio_ibge"].eq("c1"), "implicacao_att"].iloc[0],
            "CAUDA_DE_CONTROLES_NAO_E_FALTA_DE_SUPORTE_DO_TRATADO",
        )


class TestTransformacoesPre(unittest.TestCase):
    def test_normalizacao_g_menos_1_usa_base_100(self) -> None:
        painel = d18.selecionar_painel_pre_coorte(_amostra_sintetica(), 2012)
        normalizado = d18.normalizar_indice_g_menos_1(painel, coorte=2012)
        base = normalizado.loc[normalizado["ano"].eq(2011)]
        self.assertTrue((base["indice_g_menos_1"] == 100.0).all())
        self.assertTrue(normalizado["ano"].lt(2012).all())

    def test_primeira_diferenca_e_calculada_dentro_da_unidade(self) -> None:
        painel = d18.selecionar_painel_pre_coorte(_amostra_sintetica(), 2012)
        diferencas = d18.calcular_primeiras_diferencas(painel)
        tratado = diferencas.loc[diferencas["codigo_municipio_ibge"].eq("1100015")]
        self.assertTrue((tratado["delta_outcome"] == 4.0).all())
        self.assertTrue(diferencas["ano"].lt(2012).all())
        self.assertTrue((diferencas["intervalo_anos"] == 1).all())

    def test_incerteza_de_primeiras_diferencas_usa_unidades(self) -> None:
        resumo = d18.resumir_primeiras_diferencas(_amostra_sintetica(), coortes=(2012,))

        self.assertEqual(int(resumo.loc[0, "n_unidades_tratados"]), 1)
        self.assertEqual(int(resumo.loc[0, "n_unidades_controles"]), 2)
        self.assertGreater(int(resumo.loc[0, "n_deltas_controles"]), 2)
        self.assertIn("erro_padrao_descritivo_por_unidade", resumo.columns)


class TestNaoMutacao(unittest.TestCase):
    def test_leave_top_n_nao_altera_amostra_original(self) -> None:
        amostra = _amostra_sintetica()
        original = amostra.copy(deep=True)
        resultado = d18.diagnostico_influencia_pre(amostra, coortes=(2012,))

        pd.testing.assert_frame_equal(amostra, original)
        self.assertEqual(
            set(resultado["rotulo_uso"]),
            {"ANALISE_DE_INFLUENCIA_PRE_TRATAMENTO__NAO_REGRA_DE_EXCLUSAO"},
        )
        self.assertIn("SEM_OMISSAO", set(resultado["cenario"]))
        self.assertIn("OMITE_TOP_10", set(resultado["cenario"]))

    def test_cenarios_spillover_nao_alteram_papel_causal(self) -> None:
        amostra = _amostra_sintetica()
        original = amostra[["codigo_municipio_ibge", "ano", "papel_causal"]].copy()
        distancias = pd.DataFrame(
            {
                "codigo_municipio_ibge": ["1100031", "3300100"],
                "fl_ate_25_km": [True, False],
                "fl_ate_50_km": [True, True],
                "fl_ate_100_km": [True, True],
            }
        )
        arranjos = pd.DataFrame(
            {
                "codigo_municipio_ibge": ["1100031", "3300100"],
                "fl_mesmo_arranjo_populacional_fase_ii": [False, True],
            }
        )
        resultado = d18.cenarios_spillover_hipoteticos(amostra, distancias, arranjos)

        pd.testing.assert_frame_equal(
            amostra[["codigo_municipio_ibge", "ano", "papel_causal"]], original
        )
        self.assertEqual(set(resultado["rotulo_uso"]), {"CENARIO_HIPOTETICO_DE_SENSIBILIDADE__NAO_AMOSTRA_PRINCIPAL"})
        self.assertEqual(set(resultado["cenario"]), {"ATE_25_KM", "ATE_50_KM", "ATE_100_KM", "MESMO_ARRANJO_POPULACIONAL"})


class TestContratosCongelados(unittest.TestCase):
    def test_parquet_d15_permanece_byte_identical(self) -> None:
        caminho = ROOT / "data" / "processed" / "amostra_causal_cempre_2007_2019.parquet"
        hash_antes = hashlib.sha256(caminho.read_bytes()).hexdigest()
        amostra = pd.read_parquet(caminho)
        d18.resumir_tendencias_escala(amostra)
        hash_depois = hashlib.sha256(caminho.read_bytes()).hexdigest()
        self.assertEqual(hash_antes, hash_depois)

    def test_todas_as_coortes_sao_preservadas(self) -> None:
        amostra = _amostra_sintetica()
        resultado = d18.resumir_tendencias_escala(amostra, coortes=(2010, 2012, 2013))
        self.assertEqual(set(resultado["coorte_g"]), {2010, 2012, 2013})

    def test_cabo_frio_permanece_inelegivel_apenas_em_2009(self) -> None:
        amostra = _amostra_sintetica()
        antes = amostra.loc[amostra["codigo_municipio_ibge"].eq("3300704"), ["ano", "elegivel_estimacao_principal"]].copy()
        d18.resumir_tendencias_escala(amostra, coortes=(2010,))
        depois = amostra.loc[amostra["codigo_municipio_ibge"].eq("3300704"), ["ano", "elegivel_estimacao_principal"]]
        pd.testing.assert_frame_equal(antes, depois)
        self.assertEqual(antes.loc[~antes["elegivel_estimacao_principal"], "ano"].tolist(), [2009])


if __name__ == "__main__":
    unittest.main()
