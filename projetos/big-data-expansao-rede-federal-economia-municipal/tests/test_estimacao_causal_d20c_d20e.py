"""Contratos e artefatos da estimação causal D20C–D20E.

Os testes separam validações puras de população/configuração das verificações
dos artefatos congelados produzidos pela execução real autorizada.
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import estima_efeito_causal_rede_federal as d20  # noqa: E402


D15 = ROOT / "data" / "processed" / "amostra_causal_cempre_2007_2019.parquet"
VIEW = ROOT / "data" / "processed" / "amostra_principal_estimavel_d20b_2007_2019.parquet"
OVERLAP = ROOT / "outputs" / "diagnostics" / "D18_overlap_att.csv"
DISTANCIAS = ROOT / "data" / "processed" / "diagnostico_distancias_spillover_fase_ii.parquet"
ARRANJOS = ROOT / "data" / "processed" / "diagnostico_arranjos_populacionais_fase_ii.parquet"
OUT = ROOT / "outputs" / "causal"


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


class TestInputsCongelados(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.view, cls.auditoria = d20.carregar_validar_view_principal(VIEW)

    def test_hashes_d15_e_view_d20b(self) -> None:
        self.assertEqual(sha256(D15), d20.HASH_D15_ESPERADO)
        self.assertEqual(sha256(VIEW), d20.HASH_VIEW_D20B_ESPERADO)

    def test_dimensoes_chave_periodo_e_outcome(self) -> None:
        self.assertEqual(self.auditoria["n_linhas"], 66183)
        self.assertEqual(self.auditoria["n_municipios"], 5091)
        self.assertEqual(self.auditoria["anos"], list(range(2007, 2020)))
        self.assertTrue(self.auditoria["painel_balanceado"])
        self.assertTrue(self.auditoria["chave_unica"])
        self.assertEqual(self.auditoria["outcome_nulos"], 0)

    def test_populacao_coortes_e_exclusoes(self) -> None:
        self.assertEqual(self.auditoria["n_tratados"], 128)
        self.assertEqual(self.auditoria["n_controles"], 4963)
        self.assertEqual(
            self.auditoria["coortes"],
            {2009: 21, 2010: 26, 2011: 66, 2012: 13, 2013: 2},
        )
        self.assertTrue(self.auditoria["cabo_frio_ausente"])
        self.assertTrue(self.auditoria["codigo_5003900_ausente"])


class TestEspecificacaoCongelada(unittest.TestCase):
    def test_parametros_principais_e_inferencia(self) -> None:
        cfg = d20.CONFIGURACAO_PRINCIPAL
        self.assertEqual(cfg.backend, "differences==0.3.0")
        self.assertEqual(cfg.outcome, "pessoal_ocupado_assalariado")
        self.assertEqual(cfg.base_period, "universal")
        self.assertEqual(cfg.control_group, "never_treated")
        self.assertEqual(cfg.est_method, "dr")
        self.assertEqual(cfg.anticipation, 0)
        self.assertFalse(cfg.as_repeated_cross_section)
        self.assertEqual(cfg.boot_iterations, 1999)
        self.assertEqual(cfg.random_state, 20260924)
        self.assertEqual(cfg.n_jobs, 1)
        self.assertEqual(cfg.alpha, 0.05)
        self.assertEqual(cfg.k_referencia, -1)
        self.assertEqual(cfg.janela_principal, (-2, -1, 0, 1, 2))

    def test_api_real_preparada_com_coorte_nula_para_controles(self) -> None:
        view, _ = d20.carregar_validar_view_principal(VIEW)
        dados = d20.preparar_dados_api(view, outcome_modelo="nivel")
        self.assertEqual(dados.index.names, ["codigo_municipio_ibge", "ano"])
        self.assertTrue(
            dados.loc[dados["papel_causal"].eq(d20.PAPEL_CONTROLE), "coorte_api"]
            .isna()
            .all()
        )
        self.assertFalse(dados["outcome_modelo"].isna().any())


class TestPopulacoesRobustez(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.view, _ = d20.carregar_validar_view_principal(VIEW)
        cls.overlap = pd.read_csv(OVERLAP, dtype={"codigo_municipio_ibge": "string"})
        cls.distancias = pd.read_parquet(DISTANCIAS)
        cls.arranjos = pd.read_parquet(ARRANJOS)

    def _resumo(self, nome: str) -> dict[str, object]:
        dados, auditoria = d20.construir_populacao_especificacao(
            self.view,
            nome,
            overlap=self.overlap,
            distancias=self.distancias,
            arranjos=self.arranjos,
        )
        self.assertTrue(dados.groupby("codigo_municipio_ibge")["ano"].nunique().eq(13).all())
        return auditoria

    def test_log1p_preserva_populacao_e_muda_somente_escala(self) -> None:
        auditoria = self._resumo("log1p")
        self.assertEqual((auditoria["n_tratados"], auditoria["n_controles"]), (128, 4963))
        self.assertEqual(auditoria["escala_outcome"], "log1p")
        dados, _ = d20.construir_populacao_especificacao(
            self.view, "log1p", overlap=self.overlap,
            distancias=self.distancias, arranjos=self.arranjos,
        )
        esperado = np.log1p(dados[d20.OUTCOME_PRIMARIO].to_numpy(dtype=float))
        np.testing.assert_allclose(dados["outcome_modelo"], esperado)

    def test_janela_tres_pre_restringe_coortes_sem_truncar_calendario(self) -> None:
        auditoria = self._resumo("janela_3pre")
        self.assertEqual(auditoria["n_tratados"], 107)
        self.assertEqual(auditoria["n_controles"], 4963)
        self.assertEqual(auditoria["coortes"], {2010: 26, 2011: 66, 2012: 13, 2013: 2})
        self.assertEqual(auditoria["anos"], list(range(2007, 2020)))

    def test_suporte_remove_exatamente_cinco_tratados_pre_especificados(self) -> None:
        auditoria = self._resumo("suporte")
        self.assertEqual(auditoria["n_tratados"], 123)
        self.assertEqual(auditoria["n_controles"], 4963)
        self.assertEqual(len(auditoria["codigos_excluidos"]), 5)
        self.assertEqual(
            set(auditoria["codigos_excluidos"]),
            {"1506807", "2604106", "2910800", "4305108", "5201108"},
        )

    def test_spillover_remove_apenas_controles_nas_contagens_congeladas(self) -> None:
        esperados = {"spillover_25km": 4589, "spillover_50km": 3488, "spillover_100km": 1323}
        for nome, n_controles in esperados.items():
            with self.subTest(nome=nome):
                auditoria = self._resumo(nome)
                self.assertEqual(auditoria["n_tratados"], 128)
                self.assertEqual(auditoria["n_controles"], n_controles)

    def test_arranjo_preserva_tratados_e_remove_controles_pre_classificados(self) -> None:
        auditoria = self._resumo("arranjo_populacional")
        self.assertEqual(auditoria["n_tratados"], 128)
        self.assertEqual(auditoria["n_controles"], 4818)
        self.assertEqual(auditoria["rotulo"], "SENSIBILIDADE_ARRANJO_POPULACIONAL")


class TestArtefatosCongelados(unittest.TestCase):
    def test_outputs_principais_tem_schemas_e_referencia_corretos(self) -> None:
        att_gt = pd.read_csv(OUT / "D20C_att_gt_principal.csv")
        simples = pd.read_csv(OUT / "D20C_agregacao_simples.csv")
        coorte = pd.read_csv(OUT / "D20C_agregacao_coorte.csv")
        evento = pd.read_csv(OUT / "D20C_event_study_completo.csv")
        principal = pd.read_csv(OUT / "D20C_event_study_principal.csv")

        self.assertTrue({"coorte_g", "ano", "event_time", "att", "status_celula"}.issubset(att_gt))
        self.assertFalse(att_gt.loc[att_gt["ano"].ge(att_gt["coorte_g"]), "att"].isna().any())
        self.assertEqual(len(simples), 1)
        self.assertEqual(set(coorte["coorte_g"]), {2009, 2010, 2011, 2012, 2013})
        self.assertEqual(set(principal["event_time"]), {-2, -1, 0, 1, 2})
        referencia = evento.loc[evento["event_time"].eq(-1)]
        self.assertEqual(len(referencia), 1)
        self.assertEqual(referencia["att"].item(), 0.0)
        self.assertTrue(referencia[["std_error", "ci_lower", "ci_upper"]].isna().all().all())

    def test_manifesto_congela_inputs_parametros_e_outputs(self) -> None:
        manifesto = json.loads((OUT / "D20C_manifesto_resultado.json").read_text(encoding="utf-8"))
        self.assertEqual(manifesto["inputs"]["d15"]["sha256"], d20.HASH_D15_ESPERADO)
        self.assertEqual(manifesto["inputs"]["view_d20b"]["sha256"], d20.HASH_VIEW_D20B_ESPERADO)
        self.assertEqual(manifesto["configuracao"]["boot_iterations"], 1999)
        self.assertEqual(manifesto["configuracao"]["random_state"], 20260924)
        self.assertEqual(manifesto["populacao"]["n_tratados"], 128)
        self.assertTrue(manifesto["outputs"])
        for item in manifesto["outputs"]:
            caminho = ROOT / item["path"]
            self.assertTrue(caminho.exists())
            self.assertEqual(sha256(caminho), item["sha256"])

    def test_robustezes_sao_independentes_e_tabela_comparativa_existe(self) -> None:
        principal_hash = sha256(OUT / "D20C_att_gt_principal.csv")
        comparativa = pd.read_csv(OUT / "D20D_tabela_comparativa.csv")
        self.assertEqual(set(comparativa["especificacao"]), set(d20.ORDEM_ESPECIFICACOES))
        self.assertEqual(sha256(OUT / "D20C_att_gt_principal.csv"), principal_hash)
        for nome in d20.ORDEM_ESPECIFICACOES[1:]:
            self.assertTrue((OUT / f"D20D_{nome}_manifesto.json").exists())
            self.assertTrue((OUT / f"D20D_{nome}_event_study.csv").exists())

        gates = json.loads((OUT / "D20D_gates.json").read_text(encoding="utf-8"))
        self.assertEqual(gates["D20D_ROBUSTEZES_PRE_ESPECIFICADAS_CONCLUIDAS"], "SIM")
        self.assertEqual(gates["DESENHO_CAUSAL_APROVADO"], "NAO")
        esperados = {
            "D20D_LOG1P_EXECUTADO",
            "D20D_JANELA_3PRE_EXECUTADA",
            "D20D_SUPORTE_EXECUTADO",
            "D20D_SPILLOVER_25_EXECUTADO",
            "D20D_SPILLOVER_50_EXECUTADO",
            "D20D_SPILLOVER_100_EXECUTADO",
            "D20D_ARRANJO_EXECUTADO",
        }
        self.assertEqual({chave for chave in gates if chave.startswith("D20D_") and chave.endswith(("_EXECUTADO", "_EXECUTADA"))}, esperados)
        self.assertTrue(all(gates[chave] == "SIM" for chave in esperados))

    def test_auditoria_pos_estimacao_e_matriz_evidencia(self) -> None:
        auditoria = json.loads((OUT / "D20E_auditoria_pos_estimacao.json").read_text(encoding="utf-8"))
        matriz = pd.read_csv(OUT / "D20E_matriz_evidencia.csv")
        self.assertEqual(auditoria["gates"]["D20E_AUDITORIA_POS_ESTIMACAO_CONCLUIDA"], "SIM")
        self.assertEqual(auditoria["gates"]["DESENHO_CAUSAL_APROVADO"], "NAO")
        self.assertTrue(auditoria["reprodutibilidade_seed"]["reproduzivel"])
        self.assertLessEqual(d20.TOLERANCIA_REPRODUTIBILIDADE, 1e-10)
        self.assertLessEqual(
            auditoria["reprodutibilidade_seed"]["max_abs_diff"],
            d20.TOLERANCIA_REPRODUTIBILIDADE,
        )
        self.assertFalse(auditoria["pesos_agregacao"]["expostos_saida_publica"])
        self.assertEqual(
            auditoria["pesos_agregacao"]["status"],
            "NAO_EXPOSTOS_PELA_SAIDA_PUBLICA_DIFFERENCES_0_3_0",
        )
        self.assertEqual(
            set(matriz["dimensao"]),
            {"pre_tendencias", "overlap", "escala", "spillover", "timing_proxy", "coorte_pequena", "influencia_municipios_grandes", "inferencia", "validade_externa"},
        )


if __name__ == "__main__":
    unittest.main()
