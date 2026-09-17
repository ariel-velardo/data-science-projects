"""Testes do D14: contrato de especificação causal congelada."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import define_especificacao_causal as d14  # noqa: E402


def _linha(
    codigo: str, ano: int, valor_708, *,
    candidato: bool = False, coorte: float | None = None, origem: str = "proxy_censo",
    anos_excluir: str = "", elegivel_controle: bool = False,
) -> dict:
    return {
        "codigo_municipio_ibge": codigo,
        "ano": ano,
        "pessoal_ocupado_assalariado": valor_708,
        "candidato_amostra_principal": candidato,
        "ano_coorte_candidata": coorte,
        "origem_coorte": origem,
        "anos_excluir_estimacao": anos_excluir,
        "fl_elegivel_controle_candidato": elegivel_controle,
    }


def _painel_sintetico() -> pd.DataFrame:
    linhas = []
    # Tratado padrao (proxy_censo), coorte 2011
    for ano in range(2007, 2014):
        linhas.append(_linha("1100015", ano, 100.0, candidato=True, coorte=2011.0, origem="proxy_censo"))
    # Cabo Frio: origem institucional_validada, ano_transicao=2009 excluido
    for ano in range(2007, 2014):
        linhas.append(_linha(
            "3300704", ano, 200.0, candidato=True, coorte=2010.0,
            origem="institucional_validada", anos_excluir="2009",
        ))
    # Pool de controles: um deles e o municipio com sigilo em 2012
    for ano in range(2007, 2014):
        valor = None if (ano == 2012) else 50.0
        linhas.append(_linha("5003900", ano, valor, elegivel_controle=True))
    for ano in range(2007, 2014):
        linhas.append(_linha("9900000", ano, 30.0, elegivel_controle=True))
    return pd.DataFrame(linhas)


class TestUnidadesTratadasPrincipal(unittest.TestCase):
    def test_reproduz_129_via_fixture_reduzida_e_coortes(self) -> None:
        tabela = d14.unidades_tratadas_principal(_painel_sintetico())
        self.assertEqual(len(tabela), 2)
        coortes = dict(zip(tabela["codigo_municipio_ibge"], tabela["ano_coorte_candidata"]))
        self.assertEqual(coortes["1100015"], 2011.0)
        self.assertEqual(coortes["3300704"], 2010.0)


class TestUnidadesControlePrincipal(unittest.TestCase):
    def test_exclui_municipio_com_sigilo(self) -> None:
        tabela = d14.unidades_controle_principal(_painel_sintetico())
        codigos = set(tabela["codigo_municipio_ibge"])
        self.assertNotIn(d14.CODIGO_MUNICIPIO_SIGILO_EXCLUIR, codigos)
        self.assertIn("9900000", codigos)
        self.assertEqual(len(tabela), 1)

    def test_nao_imputa_nem_zera_o_sigilo(self) -> None:
        painel = _painel_sintetico()
        valor_original = painel.loc[
            (painel["codigo_municipio_ibge"] == "5003900") & (painel["ano"] == 2012),
            "pessoal_ocupado_assalariado",
        ]
        self.assertTrue(valor_original.isna().all())
        d14.unidades_controle_principal(painel)
        # A funcao nao deve alterar o painel de entrada.
        valor_apos = painel.loc[
            (painel["codigo_municipio_ibge"] == "5003900") & (painel["ano"] == 2012),
            "pessoal_ocupado_assalariado",
        ]
        self.assertTrue(valor_apos.isna().all())


class TestRegraCaboFrio(unittest.TestCase):
    def test_ano_transicao_2009_excluido_g_2010(self) -> None:
        anos_excluidos = d14.anos_excluidos_por_municipio(_painel_sintetico())
        self.assertEqual(anos_excluidos[d14.CODIGO_CABO_FRIO], [2009])
        tabela = d14.unidades_tratadas_principal(_painel_sintetico())
        coorte_cabo_frio = tabela.loc[tabela["codigo_municipio_ibge"] == d14.CODIGO_CABO_FRIO, "ano_coorte_candidata"].iloc[0]
        self.assertEqual(coorte_cabo_frio, 2010.0)

    def test_demais_candidatos_sem_anos_excluidos(self) -> None:
        anos_excluidos = d14.anos_excluidos_por_municipio(_painel_sintetico())
        self.assertEqual(anos_excluidos["1100015"], [])


class TestJanelas(unittest.TestCase):
    def test_janela_principal_e_2pre_3pos(self) -> None:
        self.assertEqual(list(d14.janela_principal_k()), [-2, -1, 0, 1, 2])

    def test_janela_sensibilidade_e_3pre_3pos(self) -> None:
        self.assertEqual(list(d14.janela_sensibilidade_k()), [-3, -2, -1, 0, 1, 2])

    def test_event_time_calculo_simples(self) -> None:
        self.assertEqual(d14.event_time(2012, 2011), 1)
        self.assertEqual(d14.event_time(2009, 2011), -2)
        self.assertEqual(d14.event_time(2011, 2011), 0)


class TestEspecificacaoSemMediadorOuPosComoCovariavel(unittest.TestCase):
    def test_covariaveis_principal_vazia_nenhum_mediador(self) -> None:
        # Nenhuma covariavel de balanceamento esta disponivel no projeto
        # ainda (ver notebook, secao de covariaveis) -- a especificacao
        # principal nao usa nenhuma, entao nao ha como incluir mediador.
        self.assertEqual(d14.ESPECIFICACAO_CAUSAL_V1.covariaveis_principal, ())

    def test_resumo_especificacao_nao_expoe_estimador_executado(self) -> None:
        resumo = d14.resumo_especificacao()
        self.assertNotIn("att", resumo)
        self.assertNotIn("efeito", resumo)
        self.assertEqual(resumo["municipio_sigilo_excluido"], "5003900")


class TestGrupoComparacaoPrincipal(unittest.TestCase):
    def test_controle_principal_e_never_treated(self) -> None:
        self.assertEqual(d14.ESPECIFICACAO_CAUSAL_V1.grupo_comparacao_principal, "never_treated_pool_estrutural_4964")

    def test_not_yet_treated_nao_entra_no_principal(self) -> None:
        self.assertFalse(d14.ESPECIFICACAO_CAUSAL_V1.not_yet_treated_no_principal)


class TestSemanticaAntecipacao(unittest.TestCase):
    """A ausencia de regra geral de antecipacao (evidencia institucional)
    nao pode ser confundida com "zero antecipacao comprovado" (suposicao
    identificadora). Sao dois campos distintos, nunca um so."""

    def test_evidencia_institucional_nao_e_suposicao(self) -> None:
        spec = d14.ESPECIFICACAO_CAUSAL_V1
        self.assertEqual(spec.evidencia_institucional_antecipacao, "INSUFICIENTE_PARA_REGRA_GERAL")
        self.assertEqual(spec.suposicao_antecipacao_principal_periodos, 0)
        # Tipos diferentes -- nunca o mesmo campo fazendo dupla funcao.
        self.assertIsInstance(spec.evidencia_institucional_antecipacao, str)
        self.assertIsInstance(spec.suposicao_antecipacao_principal_periodos, int)

    def test_resumo_expoe_as_duas_dimensoes_separadamente(self) -> None:
        resumo = d14.resumo_especificacao()
        self.assertIn("evidencia_institucional_antecipacao", resumo)
        self.assertIn("suposicao_antecipacao_principal_periodos", resumo)
        self.assertNotEqual(
            resumo["evidencia_institucional_antecipacao"], resumo["suposicao_antecipacao_principal_periodos"]
        )


if __name__ == "__main__":
    unittest.main()
