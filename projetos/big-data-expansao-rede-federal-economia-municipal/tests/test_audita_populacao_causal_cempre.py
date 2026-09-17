"""Testes do D12: auditoria diagnóstica de população causal e suporte temporal."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import audita_populacao_causal_cempre as d12  # noqa: E402


def _painel(
    *,
    coorte: int = 2009,
    anos: list[int] | None = None,
    missing_708: set[int] | None = None,
    candidato: bool = True,
    status: str = "candidato_principal",
    elegivel_controle: bool = False,
    nunca_exposto: bool = False,
) -> pd.DataFrame:
    anos = anos or list(range(2007, 2020))
    missing_708 = missing_708 or set()
    return pd.DataFrame([
        {
            "codigo_municipio_ibge": "1100015",
            "ano": ano,
            "pessoal_ocupado_assalariado": None if ano in missing_708 else 100.0,
            "status_pessoal_ocupado_assalariado": "sigilo" if ano in missing_708 else "observado",
            "fase_ii": True,
            "status_populacao_causal": status,
            "candidato_amostra_principal": candidato,
            "ano_coorte_candidata": float(coorte),
            "fl_elegivel_controle_candidato": elegivel_controle,
            "sem_exposicao_observada_2007_2019": nunca_exposto,
        }
        for ano in anos
    ])


class TestSuporteTemporal(unittest.TestCase):
    def test_coorte_2009_tem_dois_pre_calendario_e_nao_tres(self) -> None:
        diagnostico = d12.auditar_fase_ii(_painel())
        linha = diagnostico.iloc[0]
        self.assertEqual(linha["n_pre_calendario"], 2)
        self.assertEqual(linha["n_pos_calendario"], 11)
        self.assertTrue(linha["elegivel_diag_2pre_3pos"])
        self.assertFalse(linha["elegivel_diag_3pre_3pos"])
        self.assertIn("calendario_ausente:2006", linha["motivo_nao_elegibilidade_diagnostica"])

    def test_missing_dentro_da_janela_adjacente_reprova_os_dois_criterios(self) -> None:
        diagnostico = d12.auditar_fase_ii(_painel(coorte=2010, missing_708={2012}))
        linha = diagnostico.iloc[0]
        self.assertFalse(linha["elegivel_diag_2pre_3pos"])
        self.assertFalse(linha["elegivel_diag_3pre_3pos"])
        self.assertIn("outcome_708_inutil:2012", linha["motivo_nao_elegibilidade_diagnostica"])

    def test_missing_fora_da_janela_adjacente_nao_reprova(self) -> None:
        diagnostico = d12.auditar_fase_ii(_painel(coorte=2011, missing_708={2019}))
        linha = diagnostico.iloc[0]
        self.assertTrue(linha["elegivel_diag_2pre_3pos"])
        self.assertTrue(linha["elegivel_diag_3pre_3pos"])

    def test_limites_de_calendario_e_outcome_sao_distintos(self) -> None:
        limite_calendario = d12.auditar_fase_ii(_painel(coorte=2009)).iloc[0]
        limite_outcome = d12.auditar_fase_ii(_painel(coorte=2010, missing_708={2012})).iloc[0]
        self.assertIn("calendario_ausente", limite_calendario["motivo_nao_elegibilidade_diagnostica"])
        self.assertNotIn("outcome_708_inutil", limite_calendario["motivo_nao_elegibilidade_diagnostica"])
        self.assertIn("outcome_708_inutil", limite_outcome["motivo_nao_elegibilidade_diagnostica"])
        self.assertNotIn("calendario_ausente", limite_outcome["motivo_nao_elegibilidade_diagnostica"])

    def test_708_missing_na_janela_adjacente_reprova_apesar_de_haver_contagem_suficiente(self) -> None:
        diagnostico = d12.auditar_fase_ii(_painel(coorte=2011, missing_708={2009, 2011}))
        linha = diagnostico.iloc[0]
        self.assertEqual(linha["ano_coorte_candidata"], 2011.0)
        self.assertEqual(linha["n_pre_calendario"], 4)
        self.assertEqual(linha["n_pre_708_util"], 3)
        self.assertEqual(linha["n_pos_708_util"], 8)
        self.assertFalse(linha["elegivel_diag_3pre_3pos"])
        self.assertIn("outcome_708_inutil:2009", linha["motivo_nao_elegibilidade_diagnostica"])

    def test_criterio_2pre3pos_falha_por_outcome(self) -> None:
        diagnostico = d12.auditar_fase_ii(_painel(coorte=2011, missing_708={2007, 2008, 2009, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019}))
        linha = diagnostico.iloc[0]
        self.assertFalse(linha["elegivel_diag_2pre_3pos"])
        self.assertEqual(linha["classificacao_diagnostica"], "LIMITACAO_DE_OUTCOME")
        self.assertIn("outcome_708_inutil:2008", linha["motivo_nao_elegibilidade_diagnostica"])

    def test_caso_fora_dos_129_nao_e_promovido(self) -> None:
        diagnostico = d12.auditar_fase_ii(_painel(candidato=False, status="candidato_com_ressalva"))
        linha = diagnostico.iloc[0]
        self.assertFalse(linha["candidato_amostra_principal"])
        self.assertIsNone(linha["elegivel_diag_2pre_3pos"])
        self.assertEqual(linha["classificacao_diagnostica"], "CASO_INSTITUCIONAL_FORA_DOS_129")

    def test_caso_sem_coorte_mantem_suporte_temporal_indefinido(self) -> None:
        painel = _painel(candidato=False, status="sob_revisao").assign(ano_coorte_candidata=None)
        linha = d12.auditar_fase_ii(painel).iloc[0]
        self.assertTrue(pd.isna(linha["n_pre_calendario"]))
        self.assertTrue(pd.isna(linha["n_pos_708_util"]))


class TestControlesEstruturais(unittest.TestCase):
    def test_controles_por_coorte_usam_pool_elegivel_nao_nunca_exposto(self) -> None:
        controle = _painel(candidato=False, status="nao_fase_ii", elegivel_controle=True, nunca_exposto=True)
        nao_elegivel = _painel(candidato=False, status="nao_fase_ii", elegivel_controle=False, nunca_exposto=True).assign(codigo_municipio_ibge="1100023")
        painel = pd.concat([controle, nao_elegivel], ignore_index=True)
        resumo = d12.auditar_controles_por_coorte(painel, coortes=[2009])
        linha = resumo.iloc[0]
        self.assertEqual(linha["n_controles_estruturais"], 1)
        self.assertEqual(linha["n_nunca_expostos"], 2)
        self.assertEqual(linha["controles_2pre_3pos"], 1)
        self.assertEqual(linha["controles_3pre_3pos"], 0)

    def test_controle_com_missing_708_nao_tem_painel_completo(self) -> None:
        controle = _painel(candidato=False, status="nao_fase_ii", elegivel_controle=True, nunca_exposto=True, missing_708={2010})
        resumo = d12.auditar_controles_por_coorte(controle, coortes=[2011])
        self.assertEqual(resumo.iloc[0]["controles_708_completo_2007_2019"], 0)
        self.assertEqual(resumo.iloc[0]["controles_2pre_3pos"], 0)

    def test_controle_com_missing_na_janela_adjacente_reprova(self) -> None:
        controle = _painel(candidato=False, status="nao_fase_ii", elegivel_controle=True, nunca_exposto=True, missing_708={2012})
        resumo = d12.auditar_controles_por_coorte(controle, coortes=[2010])
        self.assertEqual(resumo.iloc[0]["controles_2pre_3pos"], 0)
        self.assertEqual(resumo.iloc[0]["controles_3pre_3pos"], 0)


class TestContratosD12(unittest.TestCase):
    def test_resumo_reproduz_coortes_pelos_dados(self) -> None:
        painel = pd.concat([_painel(coorte=2009), _painel(coorte=2010).assign(codigo_municipio_ibge="1100023")], ignore_index=True)
        resumo = d12.resumo_por_coorte(painel)
        self.assertEqual(resumo.set_index("ano_coorte_candidata").loc[2009, "n_candidatos"], 1)
        self.assertEqual(resumo.set_index("ano_coorte_candidata").loc[2010, "n_candidatos"], 1)

    def test_nao_cria_post_ou_event_time_persistente(self) -> None:
        diagnostico = d12.auditar_fase_ii(_painel())
        proibidas = {"post", "event_time", "tratado_ano", "amostra_causal_final"}
        self.assertFalse(proibidas & set(diagnostico.columns))

    def test_modulo_nao_expoe_estimador(self) -> None:
        proibidos = ("att", "callaway", "matching", "estima")
        self.assertFalse(any(any(p in nome.lower() for p in proibidos) for nome in dir(d12)))


class TestPainelRealD12(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.painel = d12.carrega_painel_integrado()
        cls.diagnostico = d12.auditar_fase_ii(cls.painel)

    def test_reproduz_129_candidatos_e_coortes_reais(self) -> None:
        candidatos = self.diagnostico[self.diagnostico["candidato_amostra_principal"] == True]  # noqa: E712
        self.assertEqual(len(self.diagnostico), 147)
        self.assertEqual(len(candidatos), 129)
        self.assertEqual(
            candidatos["ano_coorte_candidata"].value_counts().sort_index().to_dict(),
            {2009.0: 21, 2010.0: 27, 2011.0: 66, 2012.0: 13, 2013.0: 2},
        )

    def test_reproduz_pool_estrutural_sem_substituir_por_nunca_expostos(self) -> None:
        controles = d12.auditar_controles_por_coorte(self.painel)
        self.assertTrue((controles["n_controles_estruturais"] == 4964).all())
        self.assertTrue((controles["n_nunca_expostos"] == 4970).all())

    def test_sobral_revisao_e_exclusao_nao_sao_promovidos(self) -> None:
        por_codigo = self.diagnostico.set_index("codigo_municipio_ibge")
        sobral = por_codigo.loc["2312908"]
        self.assertEqual(sobral["status_populacao_causal"], "candidato_com_ressalva")
        self.assertEqual(sobral["ano_coorte_candidata"], 2010.0)
        self.assertFalse(sobral["candidato_amostra_principal"])
        for codigo in ("5300108", "3509502"):
            self.assertFalse(por_codigo.loc[codigo, "candidato_amostra_principal"])


if __name__ == "__main__":
    unittest.main()
