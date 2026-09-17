"""Testes do D11 — integração do painel analítico CEMPRE ao cadastro
causal nacional.

Cobre exclusivamente a integração (merge many-to-one, preservação da
população/outcome, validações A-H). Usa painel/cadastros sintéticos em
memória para a mecânica do merge, e o cadastro causal Fase II REAL
(`outputs/diagnostics/cadastro_causal_tratamento_fase_ii.csv`, leitura
local, zero rede) para os casos institucionais nomeados no D11 (Sobral,
Brasília, Duque de Caxias, Campinas, Contagem).

Execução:
    .venv\\Scripts\\python.exe -m unittest tests.test_constroi_painel_cempre_cadastro_causal -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import constroi_painel_analitico_cempre as analitico  # noqa: E402
import constroi_painel_cempre_cadastro_causal as integra  # noqa: E402

COLUNAS_VALOR = list(analitico.MAPA_VARIAVEL_COLUNA.values())
COLUNAS_STATUS = [f"status_{c}" for c in COLUNAS_VALOR]


def _linha_painel(codigo: str, ano: int, *, uf_codigo: str = "11", municipio_fonte: str = "Município Teste") -> dict:
    linha = {
        "codigo_municipio_ibge": codigo, "ano": ano, "uf_codigo": uf_codigo,
        "municipio_fonte": municipio_fonte, "status_territorial": "existia_no_ano",
    }
    for i, coluna in enumerate(COLUNAS_VALOR):
        linha[coluna] = 100.0 + i
        linha[f"status_{coluna}"] = "observado"
    return linha


def _painel_sintetico(codigos: list[str], anos: list[int]) -> pd.DataFrame:
    linhas = [_linha_painel(codigo, ano) for codigo in codigos for ano in anos]
    return pd.DataFrame(linhas)


def _linha_cadastro_nacional(
    codigo: str, *, fase_ii: bool = False, exposto: bool = False, elegivel_controle: bool | None = None,
) -> dict:
    if elegivel_controle is None:
        elegivel_controle = (not fase_ii) and (not exposto)
    return {
        "codigo_municipio_ibge": codigo, "municipio": "X", "uf": "XX", "co_uf": "00",
        "primeiro_ano_exposicao_observada": 2010 if exposto else pd.NA,
        "n_anos_no_universo": 13, "anos_ausentes_do_universo": "",
        "sem_exposicao_observada_2007_2019": not exposto,
        "presente_nos_13_anos_do_universo": True,
        "fl_municipio_fase_ii": fase_ii,
        "fl_excluir_exposicao_observada": exposto,
        "fl_excluir_universo_incompleto": False,
        "fl_excluir_fase_ii": fase_ii,
        "fl_elegivel_controle_candidato": elegivel_controle,
        "motivos_exclusao": "",
    }


def _cadastro_nacional_sintetico(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _linha_cadastro_causal(
    codigo: str, *, status_populacao_causal: str = "candidato_principal",
    ano_coorte_candidata: float | None = 2011.0, candidato_amostra_principal: bool = True,
    pode_ser_controle: bool = False, ever_treated: bool = True,
) -> dict:
    return {
        "codigo_municipio_ibge": codigo, "municipio": "X", "uf": "XX",
        "fase_ii": True,
        "ano_inicio_observado_censo": ano_coorte_candidata,
        "intermitencia_observada_no_painel": False,
        "ano_evento_institucional": pd.NA, "ano_transicao": pd.NA,
        "primeiro_ano_completo": ano_coorte_candidata,
        "ano_coorte_candidata": ano_coorte_candidata,
        "origem_coorte": "proxy_censo",
        "anos_sensibilidade": "", "anos_excluir_estimacao": "",
        "tratamento_absorvente": True, "tratamento_preexistente_painel": False,
        "ever_treated": ever_treated, "pode_ser_controle": pode_ser_controle,
        "n_pre_limpo": 3.0, "n_pos_disponivel": 5.0,
        "elegivel_temporal_2pre_3pos": True, "elegivel_temporal_3pre_3pos": True,
        "candidato_amostra_principal": candidato_amostra_principal,
        "motivo_exclusao_principal": pd.NA,
        "validacao_institucional_individual": False, "revisao_prioritaria": False,
        "nivel_evidencia": "nenhuma", "status_institucional": "proxy_censo_sem_validacao_individual",
        "status_timing": "proxy_primeiro_ept_federal_ativa",
        "status_populacao_causal": status_populacao_causal,
        "motivo_decisao": "teste", "fonte_decisao": "teste",
    }


def _cadastro_causal_sintetico(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["codigo_municipio_ibge"] + integra.COLUNAS_CADASTRO_CAUSAL)
    return pd.DataFrame(rows)


class TestBuildPainelIntegrado(unittest.TestCase):
    # A. merge many-to-one
    def test_merge_many_to_one_preserva_linhas(self) -> None:
        painel = _painel_sintetico(["1100015", "3166600"], [2018, 2019])
        cadastro_nacional = _cadastro_nacional_sintetico([
            _linha_cadastro_nacional("1100015", fase_ii=False),
            _linha_cadastro_nacional("3166600", fase_ii=True, elegivel_controle=False),
        ])
        cadastro_causal = _cadastro_causal_sintetico([_linha_cadastro_causal("3166600")])

        integrado = integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal)
        self.assertEqual(len(integrado), 4)

    # B. 72.378-equivalente: n linhas preservado (versão sintética controlada)
    def test_numero_de_linhas_preservado(self) -> None:
        painel = _painel_sintetico(["1100015"], [2007, 2008, 2009])
        cadastro_nacional = _cadastro_nacional_sintetico([_linha_cadastro_nacional("1100015")])
        cadastro_causal = _cadastro_causal_sintetico([])
        integrado = integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal)
        self.assertEqual(len(integrado), len(painel))

    # C. chave única
    def test_chave_municipio_ano_unica_apos_merge(self) -> None:
        painel = _painel_sintetico(["1100015", "3166600"], [2019])
        cadastro_nacional = _cadastro_nacional_sintetico([
            _linha_cadastro_nacional("1100015"), _linha_cadastro_nacional("3166600", fase_ii=True, elegivel_controle=False),
        ])
        cadastro_causal = _cadastro_causal_sintetico([_linha_cadastro_causal("3166600")])
        integrado = integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal)
        self.assertFalse(integrado.duplicated(subset=["codigo_municipio_ibge", "ano"]).any())

    # D. município do painel sem correspondência no cadastro nacional bloqueia
    def test_municipio_sem_correspondencia_no_cadastro_nacional_bloqueia(self) -> None:
        painel = _painel_sintetico(["9999999"], [2019])
        cadastro_nacional = _cadastro_nacional_sintetico([_linha_cadastro_nacional("1100015")])
        cadastro_causal = _cadastro_causal_sintetico([])
        with self.assertRaisesRegex(ValueError, "sem correspondência"):
            integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal)

    def test_cadastro_nacional_duplicado_bloqueia(self) -> None:
        painel = _painel_sintetico(["1100015"], [2019])
        cadastro_nacional = _cadastro_nacional_sintetico([
            _linha_cadastro_nacional("1100015"), _linha_cadastro_nacional("1100015"),
        ])
        cadastro_causal = _cadastro_causal_sintetico([])
        with self.assertRaisesRegex(ValueError, "duplicado"):
            integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal)

    # O. outcome 708/demais variáveis byte-idênticas antes/depois
    def test_outcome_cempre_identico_apos_merge(self) -> None:
        painel = _painel_sintetico(["1100015"], [2019])
        cadastro_nacional = _cadastro_nacional_sintetico([_linha_cadastro_nacional("1100015")])
        cadastro_causal = _cadastro_causal_sintetico([])
        integrado = integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal)
        for coluna in COLUNAS_VALOR + COLUNAS_STATUS:
            self.assertEqual(integrado.iloc[0][coluna], painel.iloc[0][coluna])

    # município fora do cadastro causal recebe NaN, não valor inventado
    def test_municipio_nao_fase_ii_recebe_nan_nas_colunas_causais(self) -> None:
        painel = _painel_sintetico(["1100015"], [2019])
        cadastro_nacional = _cadastro_nacional_sintetico([_linha_cadastro_nacional("1100015")])
        cadastro_causal = _cadastro_causal_sintetico([_linha_cadastro_causal("3166600")])
        integrado = integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal)
        self.assertTrue(pd.isna(integrado.iloc[0]["status_populacao_causal"]))
        self.assertTrue(pd.isna(integrado.iloc[0]["candidato_amostra_principal"]) or integrado.iloc[0]["candidato_amostra_principal"] is None)


class TestValidatePainelIntegrado(unittest.TestCase):
    def _cenario_basico(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        painel = _painel_sintetico(["1100015", "3166600"], [2018, 2019])
        cadastro_nacional = _cadastro_nacional_sintetico([
            _linha_cadastro_nacional("1100015"),
            _linha_cadastro_nacional("3166600", fase_ii=True, elegivel_controle=False),
        ])
        cadastro_causal = _cadastro_causal_sintetico([_linha_cadastro_causal("3166600", ano_coorte_candidata=2011.0)])
        return painel, cadastro_nacional, cadastro_causal

    # E. Fase II identificados corretamente
    def test_validate_confirma_fase_ii(self) -> None:
        painel, cad_nac, cad_causal = self._cenario_basico()
        integrado = integra.build_painel_integrado(painel, cad_nac, cad_causal)
        resultado = integra.validate_painel_integrado(
            painel, integrado, cad_causal, n_linhas_esperado=4, n_fase_ii_esperado=1, n_candidatos_esperado=1,
        )
        self.assertEqual(resultado["n_fase_ii"], 1)

    def test_validate_fase_ii_ausente_levanta_erro(self) -> None:
        painel, cad_nac, cad_causal = self._cenario_basico()
        integrado = integra.build_painel_integrado(painel, cad_nac, cad_causal)
        with self.assertRaisesRegex(ValueError, "E:"):
            integra.validate_painel_integrado(
                painel, integrado, cad_causal, n_linhas_esperado=4, n_fase_ii_esperado=2, n_candidatos_esperado=1,
            )

    # F. candidatos principais identificados
    def test_validate_confirma_candidatos_principais(self) -> None:
        painel, cad_nac, cad_causal = self._cenario_basico()
        integrado = integra.build_painel_integrado(painel, cad_nac, cad_causal)
        resultado = integra.validate_painel_integrado(
            painel, integrado, cad_causal, n_linhas_esperado=4, n_fase_ii_esperado=1, n_candidatos_esperado=1,
        )
        self.assertEqual(resultado["n_candidatos_principais"], 1)

    def test_validate_numero_de_linhas_errado_levanta_erro(self) -> None:
        painel, cad_nac, cad_causal = self._cenario_basico()
        integrado = integra.build_painel_integrado(painel, cad_nac, cad_causal)
        with self.assertRaisesRegex(ValueError, "A:"):
            integra.validate_painel_integrado(
                painel, integrado, cad_causal, n_linhas_esperado=999, n_fase_ii_esperado=1, n_candidatos_esperado=1,
            )


class TestExposicaoEControles(unittest.TestCase):
    # H. controles não incluem municípios Fase II
    def test_elegivel_a_controle_nunca_e_fase_ii(self) -> None:
        cadastro_nacional = _cadastro_nacional_sintetico([
            _linha_cadastro_nacional("1100015", fase_ii=False, exposto=False),
            _linha_cadastro_nacional("3166600", fase_ii=True, elegivel_controle=False),
        ])
        elegiveis = cadastro_nacional[cadastro_nacional["fl_elegivel_controle_candidato"] == True]  # noqa: E712
        self.assertFalse((elegiveis["fl_municipio_fase_ii"] == True).any())  # noqa: E712

    # I. pode_ser_controle preservado após o merge
    def test_pode_ser_controle_preservado(self) -> None:
        painel = _painel_sintetico(["3166600"], [2019])
        cadastro_nacional = _cadastro_nacional_sintetico([_linha_cadastro_nacional("3166600", fase_ii=True, elegivel_controle=False)])
        cadastro_causal = _cadastro_causal_sintetico([_linha_cadastro_causal("3166600", pode_ser_controle=False)])
        integrado = integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal)
        self.assertEqual(integrado.iloc[0]["pode_ser_controle"], False)

    # J. exposição nacional preservada
    def test_exposicao_nacional_preservada(self) -> None:
        painel = _painel_sintetico(["1100015"], [2019])
        cadastro_nacional = _cadastro_nacional_sintetico([_linha_cadastro_nacional("1100015", exposto=True, elegivel_controle=False)])
        cadastro_causal = _cadastro_causal_sintetico([])
        integrado = integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal)
        self.assertEqual(integrado.iloc[0]["sem_exposicao_observada_2007_2019"], False)


class TestCoortesCandidatas(unittest.TestCase):
    # G. coortes reproduzidas (mecanismo, com contagem sintética controlada)
    def test_diagnostico_populacional_soma_coortes_corretamente(self) -> None:
        codigos = [f"110{i:04d}" for i in range(5)]
        anos_coorte = [2009.0, 2010.0, 2010.0, 2011.0, 2011.0]
        painel = _painel_sintetico(codigos, [2019])
        cadastro_nacional = _cadastro_nacional_sintetico([
            _linha_cadastro_nacional(c, fase_ii=True, elegivel_controle=False) for c in codigos
        ])
        cadastro_causal = _cadastro_causal_sintetico([
            _linha_cadastro_causal(c, ano_coorte_candidata=a) for c, a in zip(codigos, anos_coorte)
        ])
        integrado = integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal)
        diagnostico = integra.build_diagnostico_populacional(integrado)
        coorte_2010 = diagnostico[diagnostico["metrica"] == "coorte_candidata_2010"]["valor"].iloc[0]
        coorte_2011 = diagnostico[diagnostico["metrica"] == "coorte_candidata_2011"]["valor"].iloc[0]
        self.assertEqual(coorte_2010, 2)
        self.assertEqual(coorte_2011, 2)


class TestCasosEspeciaisReais(unittest.TestCase):
    """K, L, M, N: usa o cadastro causal Fase II REAL (leitura local,
    zero rede) para confirmar que os casos institucionais nomeados no
    D11 permanecem com o status já auditado, sem reinterpretação."""

    CODIGOS_ESPERADOS = {
        "5300108": ("Brasília/DF", "excluido_principal"),
        "3301702": ("Duque de Caxias/RJ", "excluido_principal"),
        "3509502": ("Campinas/SP", "sob_revisao"),
        "3118601": ("Contagem/MG", "sob_revisao"),
        "2312908": ("Sobral/CE", "candidato_com_ressalva"),
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.cadastro_causal_real = integra.carrega_cadastro_causal_fase_ii()

    # M. Brasília e Duque de Caxias preservam suas exclusões
    def test_brasilia_e_duque_de_caxias_excluidos_principal(self) -> None:
        for codigo in ("5300108", "3301702"):
            linha = self.cadastro_causal_real[self.cadastro_causal_real["codigo_municipio_ibge"] == codigo].iloc[0]
            self.assertEqual(linha["status_populacao_causal"], "excluido_principal")
            self.assertFalse(bool(linha["candidato_amostra_principal"]))

    # N. Campinas/Contagem preservam ausência de coorte candidata (sob_revisao)
    def test_campinas_e_contagem_sob_revisao_sem_coorte(self) -> None:
        for codigo in ("3509502", "3118601"):
            linha = self.cadastro_causal_real[self.cadastro_causal_real["codigo_municipio_ibge"] == codigo].iloc[0]
            self.assertEqual(linha["status_populacao_causal"], "sob_revisao")
            self.assertTrue(pd.isna(linha["ano_coorte_candidata"]))

    # K. Sobral preservado — candidato com ressalva, coorte 2010, distinto
    # de criação/inauguração institucional (não recalculado aqui)
    def test_sobral_candidato_com_ressalva_coorte_2010(self) -> None:
        linha = self.cadastro_causal_real[self.cadastro_causal_real["codigo_municipio_ibge"] == "2312908"].iloc[0]
        self.assertEqual(linha["status_populacao_causal"], "candidato_com_ressalva")
        self.assertEqual(linha["ano_coorte_candidata"], 2010.0)
        self.assertEqual(linha["primeiro_ano_completo"], 2010.0)
        self.assertFalse(bool(linha["candidato_amostra_principal"]))

    # L. casos sob revisão preservados (contagem = 5, conforme contrato)
    def test_total_sob_revisao_bate_com_contrato(self) -> None:
        n_sob_revisao = (self.cadastro_causal_real["status_populacao_causal"] == "sob_revisao").sum()
        self.assertEqual(n_sob_revisao, 5)

    def test_integracao_preserva_casos_reais_via_merge(self) -> None:
        """Ponta a ponta pequena: pega os 5 códigos reais acima, monta um
        painel sintético de 1 ano e confirma que o merge devolve
        exatamente os status já auditados — sem reinterpretação."""
        codigos = list(self.CODIGOS_ESPERADOS)
        painel = _painel_sintetico(codigos, [2019])
        cadastro_nacional = _cadastro_nacional_sintetico([
            _linha_cadastro_nacional(c, fase_ii=True, elegivel_controle=False) for c in codigos
        ])
        cadastro_causal_subset = self.cadastro_causal_real[
            self.cadastro_causal_real["codigo_municipio_ibge"].isin(codigos)
        ].reset_index(drop=True)

        integrado = integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal_subset)
        for codigo, (nome, status_esperado) in self.CODIGOS_ESPERADOS.items():
            status_obtido = integrado.loc[integrado["codigo_municipio_ibge"] == codigo, "status_populacao_causal"].iloc[0]
            self.assertEqual(status_obtido, status_esperado, msg=f"{nome} ({codigo})")


class TestNaoCriaTransformacaoCausal(unittest.TestCase):
    # Q/R: nenhuma coluna post/event_time/tratado_ano é criada; nenhum
    # filtro por outcome; nenhuma função de estimação existe no módulo.
    def test_nenhuma_coluna_post_ou_event_time_criada(self) -> None:
        painel = _painel_sintetico(["3166600"], [2019])
        cadastro_nacional = _cadastro_nacional_sintetico([_linha_cadastro_nacional("3166600", fase_ii=True, elegivel_controle=False)])
        cadastro_causal = _cadastro_causal_sintetico([_linha_cadastro_causal("3166600")])
        integrado = integra.build_painel_integrado(painel, cadastro_nacional, cadastro_causal)
        proibidas = {"post", "tratado_ano", "event_time", "att", "did"}
        self.assertFalse(proibidas & set(c.lower() for c in integrado.columns))

    def test_modulo_nao_expoe_funcao_de_estimacao(self) -> None:
        nomes_proibidos = ("estima", "matching", "att", "callaway", "sant_anna")
        for nome in dir(integra):
            nome_lower = nome.lower()
            self.assertFalse(
                any(p in nome_lower for p in nomes_proibidos),
                msg=f"função/símbolo suspeito de estimação causal encontrado: {nome}",
            )


if __name__ == "__main__":
    unittest.main()
