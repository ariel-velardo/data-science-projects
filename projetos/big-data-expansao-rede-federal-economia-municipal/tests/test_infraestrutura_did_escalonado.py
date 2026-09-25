"""Testes D19 para DGP, contrato e dry-run do DiD escalonado.

Nenhum teste deste arquivo estima efeito causal na amostra real. A única
regressão permitida usa painel explicitamente marcado como sintético.
"""
from __future__ import annotations

import hashlib
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import estima_did_escalonado as infraestrutura  # noqa: E402
import simula_did_escalonado as simulador  # noqa: E402
import visualizacao_ipt as visual  # noqa: E402


class TestIntegracaoVisualNotebook(unittest.TestCase):
    def test_notebook_referencia_apenas_cores_existentes_no_tema_ipt(self) -> None:
        conteudo = (ROOT / "notebooks" / "06_infraestrutura_estimador_did_escalonado.ipynb").read_text(
            encoding="utf-8"
        )
        chaves_usadas = set(re.findall(r"CORES_IPT\['([^']+)'\]", conteudo))

        self.assertTrue(chaves_usadas)
        self.assertTrue(chaves_usadas.issubset(visual.CORES_IPT))


class TestDGPEscalonado(unittest.TestCase):
    def test_seed_fixa_reproduz_painel_e_verdade(self) -> None:
        config = simulador.ConfiguracaoDGP(seed=1901, n_unidades=90)

        primeira = simulador.simular_painel_did_escalonado(config)
        segunda = simulador.simular_painel_did_escalonado(config)

        pd.testing.assert_frame_equal(primeira.painel, segunda.painel)
        pd.testing.assert_frame_equal(primeira.verdade_att_gt, segunda.verdade_att_gt)

    def test_painel_tem_adocao_escalonada_e_never_treated_corretos(self) -> None:
        resultado = simulador.simular_painel_did_escalonado(
            simulador.ConfiguracaoDGP(n_unidades=100, proporcao_never_treated=0.40)
        )
        painel = resultado.painel

        self.assertEqual(painel["id"].nunique(), 100)
        self.assertEqual(painel.loc[painel["coorte_g"].eq(0), "id"].nunique(), 40)
        self.assertTrue(
            painel.loc[painel["coorte_g"].eq(0), "tratado_no_periodo"].eq(0).all()
        )
        tratados = painel.loc[painel["coorte_g"].gt(0)]
        esperado = tratados["ano"].ge(tratados["coorte_g"]).astype(int)
        pd.testing.assert_series_equal(
            tratados["tratado_no_periodo"].reset_index(drop=True),
            esperado.reset_index(drop=True),
            check_names=False,
        )

    def test_att_gt_verdadeiro_e_conhecido_por_construcao(self) -> None:
        config = simulador.ConfiguracaoDGP(
            n_unidades=120,
            coortes=(2010, 2012),
            efeitos_coorte=(2.0, 5.0),
            efeito_dinamico=1.5,
            desvio_efeito_individual=0.0,
        )
        verdade = simulador.simular_painel_did_escalonado(config).verdade_att_gt
        celula = verdade.loc[verdade["coorte_g"].eq(2010) & verdade["ano"].eq(2012)].iloc[0]

        self.assertAlmostEqual(float(celula["att_gt_verdadeiro"]), 5.0)
        self.assertEqual(int(celula["event_time"]), 2)

    def test_antecipacao_controlavel_aparece_apenas_na_janela_configurada(self) -> None:
        config = simulador.ConfiguracaoDGP(
            n_unidades=90,
            antecipacao_periodos=1,
            efeito_antecipacao=-2.0,
            desvio_efeito_individual=0.0,
        )
        painel = simulador.simular_painel_did_escalonado(config).painel
        tratados = painel.loc[painel["coorte_g"].gt(0)]

        self.assertTrue(tratados.loc[tratados["event_time"].eq(-1), "efeito_verdadeiro"].eq(-2.0).all())
        self.assertTrue(tratados.loc[tratados["event_time"].lt(-1), "efeito_verdadeiro"].eq(0.0).all())

    def test_cenario_heterogeneo_tem_efeitos_distintos_por_coorte_e_tempo(self) -> None:
        resultado = simulador.criar_cenario_heterogeneo(seed=1902, n_unidades=120)
        verdade = resultado.verdade_att_gt

        self.assertGreater(verdade.groupby("coorte_g")["att_gt_verdadeiro"].mean().nunique(), 1)
        self.assertGreater(verdade.groupby("event_time")["att_gt_verdadeiro"].mean().nunique(), 1)

    def test_violacao_parallel_trends_esta_no_outcome_sem_tratamento(self) -> None:
        resultado = simulador.criar_cenario_violacao_tendencias(seed=1903, n_unidades=150)
        diagnostico = simulador.diagnosticar_tendencias_nao_tratadas(resultado.painel)

        self.assertGreater(abs(float(diagnostico["diferenca_slope_pre"])), 0.25)
        self.assertTrue(bool(diagnostico["violacao_detectavel_no_dgp"]))

    def test_overlap_fraco_cria_tratados_acima_do_maximo_dos_controles(self) -> None:
        resultado = simulador.criar_cenario_overlap_fraco(seed=1904, n_unidades=180)
        diagnostico = simulador.diagnosticar_overlap_dgp(resultado.painel)

        self.assertGreater(int(diagnostico["n_tratados_acima_max_controles"]), 0)
        self.assertLess(float(diagnostico["fracao_tratados_no_suporte"]), 1.0)

    def test_coorte_pequena_preserva_exatamente_duas_unidades(self) -> None:
        resultado = simulador.criar_cenario_coorte_pequena(seed=1905, n_unidades=100)
        contagens = resultado.painel.drop_duplicates("id").groupby("coorte_g").size()

        self.assertEqual(int(contagens.loc[2013]), 2)

    def test_agregacoes_da_verdade_sao_rotuladas_como_nao_estimativas(self) -> None:
        resultado = simulador.criar_cenario_limpo(seed=1906, n_unidades=120)

        for tipo in ("grupo", "dinamica", "global"):
            agregado = simulador.agregar_verdade_att(resultado.verdade_att_gt, tipo)
            self.assertEqual(set(agregado["natureza"]), {"VERDADE_DGP_NAO_ESTIMATIVA"})


class TestInfraestruturaBackend(unittest.TestCase):
    def test_backend_ausente_bloqueia_sem_fallback_caseiro(self) -> None:
        auditoria = pd.DataFrame(
            [
                {"backend": "did", "disponivel_no_ambiente": False, "suporta_group_time_ATT": True},
                {"backend": "differences", "disponivel_no_ambiente": False, "suporta_group_time_ATT": True},
                {"backend": "statsmodels", "disponivel_no_ambiente": True, "suporta_group_time_ATT": False},
            ]
        )

        decisao = infraestrutura.selecionar_backend(auditoria)

        self.assertEqual(decisao["gate"], "BLOQUEADO_DEPENDENCIA")
        self.assertIsNone(decisao["backend_selecionado"])
        self.assertFalse(decisao["usar_aproximacao_caseira"])

    def test_contrato_distingue_periodo_de_estimacao_da_janela_de_reporte(self) -> None:
        contrato = infraestrutura.contrato_estimador_d19().set_index("campo")["valor"]

        self.assertEqual(contrato["periodo_estimacao"], "2007-2019_INTEGRAL")
        self.assertEqual(contrato["janela_reporte_principal"], "k=-2,-1,0,+1,+2")
        self.assertEqual(contrato["referencia_dinamica"], "k=-1")

    def test_twfe_recusa_dados_que_nao_sao_sinteticos(self) -> None:
        dados_reais_falsos = pd.DataFrame(
            {"id": ["a", "a"], "ano": [2007, 2008], "y": [1.0, 2.0], "tratado_no_periodo": [0, 1]}
        )

        with self.assertRaisesRegex(ValueError, "somente dados sintéticos"):
            infraestrutura.estimar_twfe_sintetico(dados_reais_falsos)

    def test_twfe_sintetico_retorna_coeficiente_sem_se_apresentar_como_cs(self) -> None:
        painel = simulador.criar_cenario_heterogeneo(seed=1907, n_unidades=80).painel
        resultado = infraestrutura.estimar_twfe_sintetico(painel)

        self.assertTrue(np.isfinite(resultado["coeficiente_twfe"]))
        self.assertEqual(resultado["rotulo"], "TWFE_CONVENCIONAL_APENAS_DADOS_SINTETICOS")
        self.assertNotIn("att_gt", resultado)


class TestDryRunAmostraReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.caminho = ROOT / "data" / "processed" / "amostra_causal_cempre_2007_2019.parquet"
        cls.amostra = pd.read_parquet(cls.caminho)

    def test_preparacao_real_preserva_populacoes_e_nao_estima(self) -> None:
        preparados = infraestrutura.preparar_dados_estimador(self.amostra)
        validacao = infraestrutura.validar_dados_estimador(preparados)

        self.assertEqual(validacao["n_unidades"], 5092)
        self.assertEqual(validacao["n_tratados"], 129)
        self.assertEqual(validacao["n_controles"], 4963)
        self.assertEqual(validacao["n_linhas"], 66196)
        self.assertEqual(validacao["n_elegiveis"], 66195)
        self.assertFalse(validacao["estimacao_executada"])

    def test_cabo_frio_sigilo_coortes_e_extremos_sao_preservados(self) -> None:
        preparados = infraestrutura.preparar_dados_estimador(self.amostra)
        validacao = infraestrutura.validar_dados_estimador(preparados)
        extremos = {"2910800", "2604106", "5201108", "4305108", "1506807"}

        self.assertEqual(validacao["anos_inelegiveis_cabo_frio"], [2009])
        self.assertFalse(preparados["id_backend"].eq("5003900").any())
        self.assertEqual(validacao["contagem_coortes"], {2009: 21, 2010: 27, 2011: 66, 2012: 13, 2013: 2})
        self.assertTrue(extremos.issubset(set(preparados["id_backend"])))

    def test_coorte_2013_recebe_warning_de_precisao_sem_exclusao(self) -> None:
        preparados = infraestrutura.preparar_dados_estimador(self.amostra)
        reporte = infraestrutura.resumo_coortes_para_reporte(preparados).set_index("coorte_g")

        self.assertEqual(int(reporte.loc[2013, "n_tratados"]), 2)
        self.assertEqual(reporte.loc[2013, "warning_precisao"], "COORTE_N2_PRECISAO_CRITICA")

    def test_dry_run_rejeita_qualquer_tentativa_de_twfe_na_amostra_real(self) -> None:
        preparados = infraestrutura.preparar_dados_estimador(self.amostra)
        with patch("statsmodels.formula.api.ols", side_effect=AssertionError("fit proibido")):
            with self.assertRaisesRegex(ValueError, "somente dados sintéticos"):
                infraestrutura.estimar_twfe_sintetico(preparados)

    def test_parquet_d15_permanece_byte_identical(self) -> None:
        antes = hashlib.sha256(self.caminho.read_bytes()).hexdigest()
        preparados = infraestrutura.preparar_dados_estimador(self.amostra)
        infraestrutura.validar_dados_estimador(preparados)
        depois = hashlib.sha256(self.caminho.read_bytes()).hexdigest()

        self.assertEqual(antes, depois)


if __name__ == "__main__":
    unittest.main()
