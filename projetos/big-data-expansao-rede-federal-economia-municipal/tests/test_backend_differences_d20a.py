"""Integração D20A com ``differences==0.3.0``.

Todos os ajustes são sintéticos. A amostra D15 entra apenas em dry-run
estrutural e o teste de proteção exige que qualquer fit real seja recusado.
"""
from __future__ import annotations

import hashlib
import inspect
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import simula_did_escalonado as simulador  # noqa: E402
import valida_backend_differences as d20a  # noqa: E402


class TestAPIRealDifferences(unittest.TestCase):
    def test_versao_e_assinaturas_sao_as_instaladas(self) -> None:
        auditoria = d20a.auditar_api_differences()

        self.assertEqual(auditoria["versao"], "0.3.0")
        self.assertIn("base_period", inspect.signature(d20a.ATTgt).parameters)
        self.assertIn("control_group", inspect.signature(d20a.ATTgt.fit).parameters)
        self.assertIn("boot_iterations", inspect.signature(d20a.ATTgt.fit).parameters)
        self.assertEqual(auditoria["never_treated_api"], "coorte_nula")
        self.assertEqual(auditoria["cluster_entidade_api"], "cluster_var=None")

    def test_coorte_e_primeiro_ano_de_tratamento(self) -> None:
        resultado = simulador.criar_cenario_limpo(seed=2011, n_unidades=80)
        modelo = d20a.construir_modelo_sintetico(resultado.painel, base_period="universal")
        celulas = pd.DataFrame(modelo.group_time)
        coorte = celulas.loc[celulas["cohort"].eq(2010)].copy()
        coorte["k"] = coorte["time"] - coorte["cohort"]

        self.assertEqual(coorte.loc[coorte["time"].eq(2009), "k"].item(), -1)
        self.assertEqual(coorte.loc[coorte["time"].eq(2010), "k"].item(), 0)
        self.assertEqual(coorte.loc[coorte["time"].eq(2011), "k"].item(), 1)

    def test_base_period_universal_normaliza_k_menos_um(self) -> None:
        resultado = simulador.criar_cenario_limpo(seed=2012, n_unidades=80)
        universal = d20a.estimar_sintetico(resultado.painel, base_period="universal")
        varying = d20a.estimar_sintetico(resultado.painel, base_period="varying")

        u_ref = universal["event"].loc[universal["event"]["event_time"].eq(-1), "att"].item()
        v_ref = varying["event"].loc[varying["event"]["event_time"].eq(-1), "att"].item()
        self.assertEqual(u_ref, 0.0)
        self.assertNotEqual(v_ref, 0.0)

    def test_never_treated_exclui_coortes_futuras_dos_controles(self) -> None:
        resultado = simulador.criar_cenario_limpo(seed=2013, n_unidades=80)
        with tempfile.TemporaryDirectory() as pasta:
            d20a.estimar_sintetico(
                resultado.painel,
                base_period="universal",
                files_path=pasta,
            )
            celula = pd.read_parquet(
                Path(pasta) / "cohort-2010_base_period-2009_time-2011.parquet"
            )

        controles = celula.loc[celula["_control"].eq(1), "coorte_api"]
        self.assertTrue(controles.isna().all())
        self.assertFalse(celula["coorte_api"].isin([2012, 2013]).any())


class TestEstimacaoSintetica(unittest.TestCase):
    def test_cenario_limpo_recupera_att_gt(self) -> None:
        resultado = simulador.criar_cenario_limpo(seed=2020, n_unidades=160)
        estimacao = d20a.estimar_sintetico(resultado.painel)
        comparacao, metricas = d20a.comparar_att_gt(
            estimacao["att_gt"], resultado.verdade_att_gt
        )

        self.assertFalse(comparacao.empty)
        self.assertLess(metricas["mae"], 1.0)
        self.assertLess(metricas["rmse"], 1.25)
        self.assertGreater(metricas["correlacao"], 0.90)

    def test_agregacoes_cohort_event_e_simple_existem(self) -> None:
        resultado = simulador.criar_cenario_heterogeneo(seed=2021, n_unidades=120)
        estimacao = d20a.estimar_sintetico(resultado.painel)

        self.assertEqual(set(estimacao["cohort"]["coorte"]), {2010, 2012, 2013})
        self.assertIn(0, set(estimacao["event"]["event_time"]))
        self.assertEqual(len(estimacao["simple"]), 1)

    def test_overlap_fraco_e_coorte_n2_sao_executaveis_e_sinalizados(self) -> None:
        overlap = d20a.estimar_sintetico(
            simulador.criar_cenario_overlap_fraco(seed=2022, n_unidades=120).painel
        )
        pequena = d20a.estimar_sintetico(
            simulador.criar_cenario_coorte_pequena(seed=2023, n_unidades=120).painel
        )

        self.assertEqual(overlap["metadados"]["cenario"], "OVERLAP_FRACO")
        self.assertGreaterEqual(overlap["metadados"]["n_celulas_falhas"], 0)
        self.assertEqual(pequena["metadados"]["n_coorte_2013"], 2)
        self.assertTrue(np.isfinite(pequena["cohort"].loc[
            pequena["cohort"]["coorte"].eq(2013), "att"
        ]).all())

    def test_bootstrap_reprodutivel_produz_banda_simultanea(self) -> None:
        painel = simulador.criar_cenario_limpo(seed=2024, n_unidades=100).painel
        primeira = d20a.estimar_sintetico(
            painel, boot_iterations=19, random_state=77
        )["event"]
        segunda = d20a.estimar_sintetico(
            painel, boot_iterations=19, random_state=77
        )["event"]

        pd.testing.assert_frame_equal(primeira, segunda)
        self.assertTrue({"ci_lower", "ci_upper", "inferencia"}.issubset(primeira))
        self.assertEqual(set(primeira["inferencia"]), {"bootstrap_simultanea"})

    def test_cinco_cenarios_d19_sao_executados_sem_dgp_paralelo(self) -> None:
        validacao = d20a.executar_cenarios_d19(n_unidades=80)

        self.assertEqual(
            set(validacao["resumo"]["cenario"]),
            {
                "LIMPO",
                "HETEROGENEIDADE_FORTE",
                "VIOLACAO_PARALLEL_TRENDS",
                "OVERLAP_FRACO",
                "COORTE_2013_N2",
            },
        )
        self.assertEqual(validacao["resumo"]["n_celulas_falhas"].min(), 0)

    def test_monte_carlo_registra_seeds_e_cobertura(self) -> None:
        validacao = d20a.executar_monte_carlo(
            seeds_ponto=[2101, 2102],
            seeds_bootstrap=[2201],
            n_unidades=80,
            boot_iterations=19,
        )

        self.assertEqual(validacao["configuracao"]["seeds_ponto"], [2101, 2102])
        self.assertEqual(validacao["configuracao"]["seeds_bootstrap"], [2201])
        self.assertEqual(validacao["configuracao"]["boot_iterations"], 19)
        self.assertEqual(len(validacao["por_seed_ponto"]), 2)
        self.assertTrue(0.0 <= validacao["resumo"]["cobertura"] <= 1.0)


class TestPainelDesbalanceado(unittest.TestCase):
    def test_cabo_frio_sintetico_e_preservado_mas_nao_entra_em_celula_com_base_ausente(self) -> None:
        resultado = simulador.criar_cenario_limpo(seed=2030, n_unidades=80)
        painel = resultado.painel.copy()
        unidade = painel.loc[painel["coorte_g"].eq(2010), "id"].iloc[0]
        desbalanceado = painel.loc[~(painel["id"].eq(unidade) & painel["ano"].eq(2009))]

        with tempfile.TemporaryDirectory() as pasta:
            estimacao = d20a.estimar_sintetico(
                desbalanceado,
                as_repeated_cross_section=False,
                files_path=pasta,
            )
            celula = pd.read_parquet(
                Path(pasta) / "cohort-2010_base_period-2009_time-2011.parquet"
            )

        codigo_interno = sorted(painel["id"].unique()).index(unidade)
        self.assertFalse(estimacao["metadados"]["painel_balanceado"])
        self.assertFalse(estimacao["metadados"]["como_repeated_cross_section"])
        self.assertEqual(estimacao["metadados"]["linhas_unidade_desbalanceada"], 12)
        self.assertNotIn(codigo_interno, set(celula["id"]))


class TestDryRunRealSemFit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.caminho = ROOT / "data" / "processed" / "amostra_causal_cempre_2007_2019.parquet"

    def test_dry_run_remove_so_cabo_frio_2009_e_nao_estima(self) -> None:
        antes = hashlib.sha256(self.caminho.read_bytes()).hexdigest()
        preparados, auditoria = d20a.executar_dry_run_real_sem_fit(self.caminho)
        depois = hashlib.sha256(self.caminho.read_bytes()).hexdigest()

        self.assertEqual(len(preparados), 66195)
        self.assertEqual(auditoria["n_unidades"], 5092)
        self.assertEqual(auditoria["n_linhas_cabo_frio"], 12)
        self.assertEqual(auditoria["coorte_cabo_frio"], 2010)
        self.assertFalse(auditoria["painel_balanceado_backend"])
        self.assertFalse(auditoria["estimacao_executada"])
        self.assertTrue(auditoria["fit_real_bloqueado"])
        self.assertEqual(antes, depois)

    def test_fit_real_e_explicitamente_proibido(self) -> None:
        preparados, _ = d20a.executar_dry_run_real_sem_fit(self.caminho)
        with self.assertRaisesRegex(PermissionError, "fit real proibido"):
            d20a.estimar_sintetico(preparados)


class TestFechamentoPreEstimacaoD20B(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.caminho = ROOT / "data" / "processed" / "amostra_causal_cempre_2007_2019.parquet"

    def test_view_exclui_apenas_cabo_frio_e_preserva_d15(self) -> None:
        hash_antes = hashlib.sha256(self.caminho.read_bytes()).hexdigest()
        d15 = pd.read_parquet(self.caminho)
        d15_antes = d15.copy(deep=True)

        view, auditoria = d20a.preparar_amostra_principal_estimavel(d15)

        pd.testing.assert_frame_equal(d15, d15_antes)
        self.assertEqual(hash_antes, hashlib.sha256(self.caminho.read_bytes()).hexdigest())
        self.assertEqual(len(d15.loc[d15["codigo_municipio_ibge"].astype(str).eq("3300704")]), 13)
        self.assertFalse(view["codigo_municipio_ibge"].astype(str).eq("3300704").any())
        self.assertEqual(auditoria["POPULACAO_D15_TRATADOS"], 129)
        self.assertEqual(auditoria["POPULACAO_PRINCIPAL_ESTIMAVEL"], 128)
        self.assertEqual(auditoria["n_controles"], 4963)
        self.assertEqual(auditoria["n_municipios"], 5091)
        self.assertEqual(auditoria["n_linhas"], 66183)
        self.assertTrue(auditoria["painel_balanceado_2007_2019"])
        self.assertTrue(auditoria["codigo_5003900_ausente"])

    def test_view_preserva_demais_coortes(self) -> None:
        d15 = pd.read_parquet(self.caminho)
        _, auditoria = d20a.preparar_amostra_principal_estimavel(d15)

        self.assertEqual(
            auditoria["contagem_coortes"],
            {2009: 21, 2010: 26, 2011: 66, 2012: 13, 2013: 2},
        )
        self.assertEqual(auditoria["motivo_exclusao"], "CABO_FRIO_2009_INCOMPATIVEL_COM_REFERENCIA_G_MENOS_1")
        self.assertFalse(auditoria["efeito_real_estimado"])

    def test_copia_materializada_nao_sobrescreve_d15(self) -> None:
        hash_antes = hashlib.sha256(self.caminho.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta) / "view_d20b.parquet"
            view, auditoria = d20a.materializar_view_principal_estimavel(
                self.caminho, destino
            )
            recarregada = pd.read_parquet(destino)

        pd.testing.assert_frame_equal(view, recarregada)
        self.assertTrue(auditoria["d15_byte_identical"])
        self.assertEqual(hash_antes, hashlib.sha256(self.caminho.read_bytes()).hexdigest())

    def test_workaround_preserva_todas_estimativas_nao_referencia(self) -> None:
        painel = simulador.criar_cenario_limpo(seed=25001, n_unidades=80).painel

        validacao = d20a.validar_workaround_k_menos_1(
            painel,
            boot_iterations=19,
            random_state=25002,
            n_jobs=1,
        )

        self.assertTrue(validacao["invariantes"]["att_gt_pos_tratamento"])
        self.assertTrue(validacao["invariantes"]["cohort"])
        self.assertTrue(validacao["invariantes"]["simple"])
        self.assertTrue(validacao["invariantes"]["event_k_diferente_menos_1"])
        self.assertTrue(validacao["invariantes"]["k_menos_1_retirado_da_banda"])
        self.assertTrue(validacao["invariantes"]["k_menos_1_reposto_zero_apresentacao"])
        self.assertEqual(validacao["max_abs_diff"]["att_gt_pos_tratamento"], 0.0)
        self.assertEqual(validacao["max_abs_diff"]["cohort"], 0.0)
        self.assertEqual(validacao["max_abs_diff"]["simple"], 0.0)
        self.assertEqual(validacao["max_abs_diff"]["event_k_diferente_menos_1"], 0.0)

    def test_bootstrap_final_esta_pre_especificado_sem_execucao_real(self) -> None:
        configuracao = d20a.configuracao_inferencia_final_d20b()

        self.assertEqual(configuracao["base_period"], "universal")
        self.assertEqual(configuracao["boot_iterations"], 1999)
        self.assertEqual(configuracao["random_state"], 20260924)
        self.assertEqual(configuracao["n_jobs"], 1)
        self.assertGreaterEqual(configuracao["n_jobs_cpu_disponiveis"], 1)
        self.assertIn("differences 0.3.0 falha", configuracao["n_jobs_justificativa"])
        self.assertEqual(configuracao["alpha"], 0.05)
        self.assertTrue(configuracao["bandas_simultaneas"])
        self.assertFalse(configuracao["executado_na_base_real"])

    def test_gates_d20b_nao_autorizam_estimacao_real(self) -> None:
        gates = d20a.gates_d20b(
            view_validada=True,
            workaround_validado=True,
            inferencia_configurada=True,
        )

        self.assertEqual(gates["D20B_CABO_FRIO_DECISAO_FECHADA"], "SIM")
        self.assertEqual(gates["D20B_POPULACAO_ESTIMAVEL_128_VALIDADA"], "SIM")
        self.assertEqual(gates["D20B_VIEW_BALANCEADA_VALIDADA"], "SIM")
        self.assertEqual(gates["D20B_WORKAROUND_K_MENOS_1_VALIDADO"], "SIM")
        self.assertEqual(gates["D20B_INFERENCIA_CONFIGURADA"], "SIM")
        self.assertEqual(gates["D20B_BOOTSTRAP_FINAL_PRE_ESPECIFICADO"], "SIM")
        self.assertEqual(gates["D20B_PRONTO_PARA_ESTIMACAO_REAL"], "SIM")
        self.assertEqual(gates["D20B_EFEITO_REAL_ESTIMADO"], "NAO")
        self.assertEqual(gates["DESENHO_CAUSAL_APROVADO"], "NAO")


if __name__ == "__main__":
    unittest.main()
