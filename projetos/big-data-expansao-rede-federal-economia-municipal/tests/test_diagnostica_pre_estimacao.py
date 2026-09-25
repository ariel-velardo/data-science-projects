"""Testes sintéticos e de integração da auditoria pré-estimação D17."""
from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import diagnostica_pre_estimacao as d17  # noqa: E402


def _amostra_sintetica() -> pd.DataFrame:
    linhas: list[dict] = []
    unidades = [
        ("3300704", "TRATADO_PRINCIPAL", 2010.0, "33", 100.0),
        ("1100015", "TRATADO_PRINCIPAL", 2012.0, "11", 60.0),
        ("1100023", "TRATADO_PRINCIPAL", 2013.0, "11", 40.0),
        ("1100031", "CONTROLE_NEVER_TREATED", None, "11", 20.0),
        ("3300100", "CONTROLE_NEVER_TREATED", None, "33", 30.0),
    ]
    for codigo, papel, coorte, uf, base in unidades:
        for ano in range(2007, 2020):
            cabo_2009 = codigo == "3300704" and ano == 2009
            linhas.append(
                {
                    "codigo_municipio_ibge": codigo,
                    "ano": ano,
                    "uf_codigo": uf,
                    "municipio_fonte": f"M{codigo}",
                    "papel_causal": papel,
                    "coorte_g": coorte,
                    "tempo_relativo": ano - coorte if coorte is not None else None,
                    "elegivel_estimacao_principal": not cabo_2009,
                    "motivo_nao_elegibilidade_estimacao": (
                        "ANO_TRANSICAO_INSTITUCIONAL_CABO_FRIO_2009" if cabo_2009 else None
                    ),
                    "pessoal_ocupado_assalariado": base + 2 * (ano - 2007),
                    "pessoal_ocupado_total": base * 1.2 + 2 * (ano - 2007),
                    "qt_unidades_locais": base / 5 + (ano - 2007),
                    "salarios_remuneracoes_mil_reais_nominal": base * 10 + ano,
                    "pessoal_assalariado_medio": base * 0.9 + (ano - 2007),
                    "salario_medio_salarios_minimos_nominal": 2.0 + 0.1 * (ano - 2007),
                    "salario_medio_reais_nominal": 1000.0 + 20 * (ano - 2007),
                    "status_pessoal_ocupado_assalariado": "observado",
                }
            )
    return pd.DataFrame(linhas)


class TestPreTratamento(unittest.TestCase):
    def test_filtra_exclusivamente_periodos_pre_tratamento(self) -> None:
        resultado = d17.selecionar_periodos_pre(_amostra_sintetica(), coorte=2012)

        tratados = resultado.loc[resultado["grupo"].eq("TRATADOS_COORTE")]
        controles = resultado.loc[resultado["grupo"].eq("CONTROLES_NEVER_TREATED")]
        self.assertTrue(tratados["ano"].lt(2012).all())
        self.assertTrue(controles["ano"].lt(2012).all())
        self.assertTrue(resultado["tempo_relativo_pre"].lt(0).all())

    def test_calcula_event_time_pre_corretamente(self) -> None:
        resultado = d17.selecionar_periodos_pre(_amostra_sintetica(), coorte=2012)
        linha = resultado.loc[resultado["ano"].eq(2010)].iloc[0]
        self.assertEqual(int(linha["tempo_relativo_pre"]), -2)

    def test_compara_coorte_apenas_com_never_treated(self) -> None:
        resumo = d17.comparar_coorte_never_pre(_amostra_sintetica(), coorte=2012)

        self.assertEqual(set(resumo["grupo"]), {"TRATADOS_COORTE", "CONTROLES_NEVER_TREATED"})
        self.assertEqual(set(resumo.loc[resumo["grupo"].eq("TRATADOS_COORTE"), "n_unidades"]), {1})
        self.assertEqual(set(resumo.loc[resumo["grupo"].eq("CONTROLES_NEVER_TREATED"), "n_unidades"]), {2})
        self.assertTrue(resumo["tempo_relativo_pre"].lt(0).all())

    def test_trata_coorte_pequena_sem_excluir(self) -> None:
        resumo = d17.comparar_coorte_never_pre(_amostra_sintetica(), coorte=2013)
        tratados = resumo.loc[resumo["grupo"].eq("TRATADOS_COORTE")]

        self.assertEqual(set(tratados["n_unidades"]), {1})
        self.assertEqual(set(tratados["alerta_tamanho_coorte"]), {"COORTE_PEQUENA_PRECISAO_LIMITADA"})


class TestCovariaveisEBalanco(unittest.TestCase):
    def test_rejeita_covariavel_pos_tratamento_no_baseline(self) -> None:
        with self.assertRaisesRegex(ValueError, "pós-tratamento|pos-tratamento"):
            d17.construir_baseline_comum(
                _amostra_sintetica(),
                covariaveis=["periodo_pos_coorte"],
                ano_base=2007,
            )

    def test_standardized_mean_difference(self) -> None:
        tratados = pd.Series([2.0, 4.0])
        controles = pd.Series([0.0, 2.0])
        esperado = 2.0 / (((2.0 + 2.0) / 2.0) ** 0.5)

        self.assertAlmostEqual(d17.standardized_mean_difference(tratados, controles), esperado)

    def test_baseline_comum_usa_2007_e_preserva_unidades(self) -> None:
        resultado = d17.construir_baseline_comum(
            _amostra_sintetica(),
            covariaveis=["pessoal_ocupado_assalariado", "qt_unidades_locais"],
            ano_base=2007,
        )

        self.assertEqual(len(resultado), 5)
        self.assertEqual(set(resultado["ano_baseline"]), {2007})
        self.assertEqual(resultado["codigo_municipio_ibge"].nunique(), 5)


class TestOverlap(unittest.TestCase):
    def test_identifica_intervalo_de_suporte_e_caudas(self) -> None:
        scores = pd.DataFrame(
            {
                "codigo_municipio_ibge": ["1", "2", "3", "4", "5"],
                "tratado": [True, True, False, False, False],
                "propensity_score": [0.40, 0.80, 0.10, 0.50, 0.70],
            }
        )
        resultado, resumo = d17.identificar_suporte_empirico(scores)

        self.assertAlmostEqual(resumo["limite_inferior"], 0.40)
        self.assertAlmostEqual(resumo["limite_superior"], 0.70)
        self.assertEqual(int(resultado["fora_suporte_empirico"].sum()), 2)
        self.assertFalse(bool(resultado.loc[resultado["codigo_municipio_ibge"].eq("2"), "em_suporte_empirico"].iloc[0]))


class TestCaboFrioEPreservacao(unittest.TestCase):
    def test_cabo_frio_explica_perda_de_uma_janela(self) -> None:
        diagnostico = d17.diagnosticar_cobertura_cabo_frio(_amostra_sintetica())
        principal = diagnostico.loc[diagnostico["janela"].eq("principal_k_-2_2")].iloc[0]

        self.assertEqual(int(principal["n_populacao_calendario"]), 3)
        self.assertEqual(int(principal["n_janela_completa_elegivel"]), 2)
        self.assertEqual(int(principal["perda_cabo_frio"]), 1)

    def test_classificacao_spillover_nao_altera_papel_causal(self) -> None:
        amostra = _amostra_sintetica()
        original = amostra[["codigo_municipio_ibge", "ano", "papel_causal"]].copy()
        distancias = pd.DataFrame(
            {
                "codigo_municipio_ibge": ["1100031", "3300100"],
                "distancia_sedes_km": [20.0, 120.0],
                "fl_ate_25_km": [True, False],
                "fl_ate_50_km": [True, False],
                "fl_ate_100_km": [True, False],
            }
        )

        resultado = d17.classificar_spillover_controles(amostra, distancias)

        pd.testing.assert_frame_equal(
            resultado[["codigo_municipio_ibge", "ano", "papel_causal"]], original
        )
        self.assertIn("classificacao_spillover_diagnostica", resultado.columns)

    def test_funcao_diagnostica_nao_altera_parquet_d15(self) -> None:
        origem = ROOT / "data" / "processed" / "amostra_causal_cempre_2007_2019.parquet"
        hash_antes = hashlib.sha256(origem.read_bytes()).hexdigest()
        amostra = pd.read_parquet(origem)

        d17.construir_baseline_comum(
            amostra,
            covariaveis=["pessoal_ocupado_assalariado"],
            ano_base=2007,
        )

        hash_depois = hashlib.sha256(origem.read_bytes()).hexdigest()
        self.assertEqual(hash_antes, hash_depois)

    def test_hash_de_arquivo_e_deterministico(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "fixture.bin"
            caminho.write_bytes(b"D17")
            self.assertEqual(d17.sha256_arquivo(caminho), hashlib.sha256(b"D17").hexdigest())


if __name__ == "__main__":
    unittest.main()
