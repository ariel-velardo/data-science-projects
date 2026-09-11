"""Testes pequenos e focados para auditoria_correspondencia_unidades_fase_ii.py.

Usa apenas `unittest` (stdlib) -- pytest não está instalado no `.venv` do
projeto (ver requirements.txt) e nenhuma dependência nova foi adicionada
para este script. Execução:

    python -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import auditoria_correspondencia_unidades_fase_ii as auditoria  # noqa: E402


class TestNormaliza(unittest.TestCase):
    def test_remove_acentos_caixa_e_espacos(self) -> None:
        self.assertEqual(auditoria.normaliza("  São   Paulo  "), "SAO PAULO")
        self.assertEqual(auditoria.normaliza("Piracicaba"), "PIRACICABA")

    def test_nao_remove_pontuacao(self) -> None:
        # normaliza() cuida só de acento/caixa/espaço -- pontuação é
        # tratada em normaliza_municipio()/normaliza_nome_unidade().
        self.assertEqual(auditoria.normaliza("Sto. Amaro"), "STO. AMARO")


class TestNormalizaMunicipio(unittest.TestCase):
    def test_neutraliza_pontuacao_e_expande_abreviacao_simples(self) -> None:
        oficial = auditoria.normaliza_municipio("Santo Amaro das Pedras")
        abreviado = auditoria.normaliza_municipio("Sto. Amaro das Pedras")
        self.assertEqual(oficial, "SANTO AMARO DAS PEDRAS")
        self.assertEqual(abreviado, oficial)

    def test_nao_expande_abreviacao_ambigua(self) -> None:
        # "S." não é expandido (ambíguo entre São/Santo/Santa) -- a
        # normalização deve continuar transparente, nunca adivinhar.
        self.assertNotIn("SAO", auditoria.normaliza_municipio("S. Amaro"))
        self.assertNotIn("SANTO", auditoria.normaliza_municipio("S. Amaro"))


class TestNormalizaNomeUnidade(unittest.TestCase):
    def test_neutraliza_caixa_acentuacao_espaco_e_pontuacao_simples(self) -> None:
        a = auditoria.normaliza_nome_unidade("Instituto Federal Fluminense - Campus Cabo Frio")
        b = auditoria.normaliza_nome_unidade("INSTITUTO  FEDERAL FLUMINENSE   -   CAMPUS CABO FRIO")
        self.assertEqual(a, b)

    def test_nao_funde_descricoes_semanticamente_diferentes(self) -> None:
        # Não deve deduzir que "CEFET-MG UNED Contagem" e o nome
        # institucional por extenso são a mesma unidade -- apenas
        # neutraliza caixa/acento/espaço/pontuação, nada além disso.
        a = auditoria.normaliza_nome_unidade("CEFET-MG UNED Contagem")
        b = auditoria.normaliza_nome_unidade(
            "Centro Federal de Educacao Tecnologica de Minas Gerais - Uned Contagem"
        )
        self.assertNotEqual(a, b)

    def test_nao_expande_abreviacao_municipal(self) -> None:
        # Diferente de normaliza_municipio(): não usa ABREVIACOES_MUNICIPAIS
        # (é um dicionário de topônimo, não de nome de instituição).
        self.assertIn("STO", auditoria.normaliza_nome_unidade("Campus Sto. Amaro"))


class TestSistecTemDuplicataAmbigua(unittest.TestCase):
    def test_detecta_duplicata_so_com_diferenca_de_caixa(self) -> None:
        # Caso real encontrado na revisão adversarial: Cabo Frio/RJ tinha
        # duas linhas SISTEC para o mesmo nome, diferindo só em caixa, não
        # detectadas pela versão anterior (case-sensitive).
        candidatos = pd.DataFrame({
            "nome_unidade_sistec": [
                "Instituto Federal Fluminense - Campus Cabo Frio",
                "INSTITUTO FEDERAL FLUMINENSE - CAMPUS CABO FRIO",
            ],
            "dt_autorizacao_sistec": ["17/04/2009 00:00:00", "07/06/2011 00:00:00"],
        })
        self.assertTrue(auditoria.sistec_tem_duplicata_ambigua(candidatos))

    def test_nomes_realmente_diferentes_nao_sao_duplicata(self) -> None:
        candidatos = pd.DataFrame({
            "nome_unidade_sistec": ["Campus A", "Campus B"],
            "dt_autorizacao_sistec": ["01/01/2010 00:00:00", "01/01/2011 00:00:00"],
        })
        self.assertFalse(auditoria.sistec_tem_duplicata_ambigua(candidatos))

    def test_mesmo_nome_e_mesma_data_nao_e_ambiguo(self) -> None:
        candidatos = pd.DataFrame({
            "nome_unidade_sistec": ["Campus A", "CAMPUS A"],
            "dt_autorizacao_sistec": ["01/01/2010 00:00:00", "01/01/2010 00:00:00"],
        })
        self.assertFalse(auditoria.sistec_tem_duplicata_ambigua(candidatos))

    def test_vazio_retorna_false(self) -> None:
        vazio = pd.DataFrame(columns=["nome_unidade_sistec", "dt_autorizacao_sistec"])
        self.assertFalse(auditoria.sistec_tem_duplicata_ambigua(vazio))


class TestMatchSistecCandidates(unittest.TestCase):
    def test_preserva_valores_originais_e_classifica_qualidade(self) -> None:
        fase_ii = pd.DataFrame({
            "codigo_municipio_ibge": ["1111111"],
            "municipio": ["Santo Amaro das Pedras"],
            "uf": ["XX"],
        })
        sistec = pd.DataFrame({
            "sigla_unidade_ensino": ["IFTESTE"],
            "nome_unidade_ensino": ["Instituto Federal Teste - Campus Sto. Amaro"],
            "dt_autorizacao": ["01/01/2020 00:00:00"],
            "sigla_uf_unidade_ensino": ["xx"],  # caixa baixa proposital
            "nome_municipio_unidade_ensino": ["Sto. Amaro das Pedras"],
        })
        sistec_idx = auditoria.index_sistec(sistec)
        candidatos = auditoria.match_sistec_candidates(fase_ii, sistec_idx)

        self.assertEqual(len(candidatos), 1)
        linha = candidatos.iloc[0]
        self.assertEqual(linha["nome_unidade_sistec"], "Instituto Federal Teste - Campus Sto. Amaro")
        self.assertEqual(linha["municipio_unidade_sistec"], "Sto. Amaro das Pedras")
        self.assertEqual(linha["dt_autorizacao_sistec"], "01/01/2020 00:00:00")
        self.assertEqual(linha["correspondencia_municipio"], "normalizada")

    def test_correspondencia_exata_quando_strings_batem_apos_normaliza(self) -> None:
        fase_ii = pd.DataFrame({
            "codigo_municipio_ibge": ["2222222"],
            "municipio": ["Piracicaba"],
            "uf": ["SP"],
        })
        sistec = pd.DataFrame({
            "sigla_unidade_ensino": ["IFSP"],
            "nome_unidade_ensino": ["IFSP - Campus Piracicaba"],
            "dt_autorizacao": ["02/02/2011 10:00:00"],
            "sigla_uf_unidade_ensino": ["SP"],
            "nome_municipio_unidade_ensino": ["Piracicaba"],
        })
        candidatos = auditoria.match_sistec_candidates(fase_ii, auditoria.index_sistec(sistec))
        self.assertEqual(candidatos.iloc[0]["correspondencia_municipio"], "exata")

    def test_municipio_sem_nenhum_candidato(self) -> None:
        fase_ii = pd.DataFrame({
            "codigo_municipio_ibge": ["3333333"],
            "municipio": ["Vila Sem Candidato"],
            "uf": ["ZZ"],
        })
        sistec = pd.DataFrame({
            "sigla_unidade_ensino": ["IFOUTRO"],
            "nome_unidade_ensino": ["Campus de Outro Lugar"],
            "dt_autorizacao": ["03/03/2012 00:00:00"],
            "sigla_uf_unidade_ensino": ["WW"],
            "nome_municipio_unidade_ensino": ["Outro Municipio"],
        })
        candidatos = auditoria.match_sistec_candidates(fase_ii, auditoria.index_sistec(sistec))
        self.assertTrue(candidatos.empty)


class TestBuildCensoCandidates(unittest.TestCase):
    def test_municipio_com_varias_entidades(self) -> None:
        escolas = pd.DataFrame({
            "CO_MUNICIPIO": ["1111111", "1111111", "2222222"],
            "NU_ANO_CENSO": ["2007", "2011", "2010"],
            "CO_ENTIDADE": ["E_ANTIGA", "E_NOVA", "E_UNICA"],
            "NO_ENTIDADE": ["Escola Antiga", "Campus Novo", "Campus Unico"],
            "fl_em_atividade": [True, True, True],
            "fl_presenca_federal_ept_ativa": [True, True, True],
        })
        candidatos = auditoria.build_censo_candidates({"1111111", "2222222"}, escolas)
        n_por_municipio = candidatos.groupby("codigo_municipio_ibge").size()
        self.assertEqual(n_por_municipio["1111111"], 2)
        self.assertEqual(n_por_municipio["2222222"], 1)

    def test_ignora_municipios_fora_da_fase_ii(self) -> None:
        escolas = pd.DataFrame({
            "CO_MUNICIPIO": ["9999999"],
            "NU_ANO_CENSO": ["2010"],
            "CO_ENTIDADE": ["E_FORA"],
            "NO_ENTIDADE": ["Escola Fora Da Lista"],
            "fl_em_atividade": [True],
            "fl_presenca_federal_ept_ativa": [True],
        })
        candidatos = auditoria.build_censo_candidates({"1111111"}, escolas)
        self.assertTrue(candidatos.empty)

    def test_distingue_entidade_nunca_ativa_de_entidade_com_ept_ativa(self) -> None:
        # Caso real: Campinas/SP tem entidades federais (ex.: escola
        # militar) que nunca estiveram ativas nem tiveram EPT ativa --
        # não podem ficar indistinguíveis da entidade EPT real.
        escolas = pd.DataFrame({
            "CO_MUNICIPIO": ["1111111", "1111111"],
            "NU_ANO_CENSO": ["2010", "2010"],
            "CO_ENTIDADE": ["MILITAR", "IF_REAL"],
            "NO_ENTIDADE": ["Escola Militar", "Campus Real"],
            "fl_em_atividade": [True, True],
            "fl_presenca_federal_ept_ativa": [False, True],
        })
        candidatos = auditoria.build_censo_candidates({"1111111"}, escolas)
        militar = candidatos[candidatos["co_entidade"] == "MILITAR"].iloc[0]
        real = candidatos[candidatos["co_entidade"] == "IF_REAL"].iloc[0]
        self.assertTrue(pd.isna(militar["primeiro_ano_ept_ativa_censo"]))
        self.assertFalse(pd.isna(real["primeiro_ano_ept_ativa_censo"]))


class TestOrdemDasLinhas(unittest.TestCase):
    def test_build_censo_candidates_independente_da_ordem_de_entrada(self) -> None:
        escolas = pd.DataFrame({
            "CO_MUNICIPIO": ["1111111", "1111111", "1111111"],
            "NU_ANO_CENSO": ["2009", "2007", "2008"],
            "CO_ENTIDADE": ["E1", "E1", "E1"],
            "NO_ENTIDADE": ["Nome C", "Nome A", "Nome B"],
            "fl_em_atividade": [True, True, True],
            "fl_presenca_federal_ept_ativa": [True, False, True],
        })
        embaralhada = escolas.iloc[[2, 0, 1]].reset_index(drop=True)
        r1 = auditoria.build_censo_candidates({"1111111"}, escolas).sort_values("co_entidade").reset_index(drop=True)
        r2 = auditoria.build_censo_candidates({"1111111"}, embaralhada).sort_values("co_entidade").reset_index(drop=True)
        pd.testing.assert_frame_equal(r1, r2)

    def test_tem_lacuna_interna_independente_da_ordem(self) -> None:
        anos_embaralhados = [2010, 2007, 2011, 2009, 2008]
        ativa_correspondente = [False, True, True, False, False]
        # equivalente, em ordem cronológica, a True, False, False, False, True
        self.assertTrue(auditoria.tem_lacuna_interna(anos_embaralhados, ativa_correspondente))


class TestTemLacunaInterna(unittest.TestCase):
    def test_detecta_lacuna_entre_dois_periodos_verdadeiros(self) -> None:
        anos = [2007, 2008, 2009, 2010, 2011]
        ativa = [True, False, False, False, True]
        self.assertTrue(auditoria.tem_lacuna_interna(anos, ativa))

    def test_sem_lacuna_quando_monotonico(self) -> None:
        anos = [2007, 2008, 2009, 2010, 2011]
        ativa = [False, False, True, True, True]
        self.assertFalse(auditoria.tem_lacuna_interna(anos, ativa))


class TestBuildPainelDiagnostics(unittest.TestCase):
    def test_separa_presenca_geral_de_presenca_ept_ativa_antes_de_2009(self) -> None:
        # Réplica minimalista do padrão real de Campinas/SP: presença
        # federal geral antes de 2009 (ex.: escola militar), mas nenhuma
        # EPT ativa nesse período.
        painel = pd.DataFrame({
            "CO_MUNICIPIO": ["1111111", "1111111"],
            "NU_ANO_CENSO": ["2007", "2008"],
            "fl_presenca_federal": [True, True],
            "fl_presenca_federal_ept_ativa": [False, False],
        })
        diag = auditoria.build_painel_diagnostics({"1111111"}, painel).iloc[0]
        self.assertTrue(diag["presenca_federal_geral_antes_2009"])
        self.assertFalse(diag["presenca_federal_ept_ativa_antes_2009"])

    def test_ept_ativa_antes_de_2009_quando_realmente_ha(self) -> None:
        painel = pd.DataFrame({
            "CO_MUNICIPIO": ["1111111"],
            "NU_ANO_CENSO": ["2007"],
            "fl_presenca_federal": [True],
            "fl_presenca_federal_ept_ativa": [True],
        })
        diag = auditoria.build_painel_diagnostics({"1111111"}, painel).iloc[0]
        self.assertTrue(diag["presenca_federal_geral_antes_2009"])
        self.assertTrue(diag["presenca_federal_ept_ativa_antes_2009"])

    def test_2009_nao_conta_como_antes_de_2009(self) -> None:
        painel = pd.DataFrame({
            "CO_MUNICIPIO": ["1111111"],
            "NU_ANO_CENSO": ["2009"],
            "fl_presenca_federal": [True],
            "fl_presenca_federal_ept_ativa": [True],
        })
        diag = auditoria.build_painel_diagnostics({"1111111"}, painel).iloc[0]
        self.assertFalse(diag["presenca_federal_geral_antes_2009"])
        self.assertFalse(diag["presenca_federal_ept_ativa_antes_2009"])


class TestClassifyMunicipio(unittest.TestCase):
    BASE = dict(
        n_entidades_censo_com_ept_ativa=1,
        n_nomes_unidade_sistec_distintos=1,
        n_registros_sistec=1,
        presenca_federal_ept_ativa_antes_2009=False,
        trajetoria_intermitente_ept_ativa=False,
        correspondencia_municipio="exata",
        duplicata_ambigua_sistec=False,
    )

    def test_caso_sem_nenhum_alerta(self) -> None:
        categorias = auditoria.classify_municipio(**self.BASE)
        self.assertEqual(categorias, ["A_SEM_ALERTA_MECANICO"])

    def test_somente_intermitente_nao_gera_sem_alerta_mecanico(self) -> None:
        # Reproduz o caso real encontrado na revisão adversarial: Jequié/BA
        # e Piracicaba/SP eram rotulados A_LIMPO mesmo com D_INTERMITENTE
        # presente, porque a condição antiga não excluía intermitência.
        kwargs = {**self.BASE, "trajetoria_intermitente_ept_ativa": True}
        categorias = auditoria.classify_municipio(**kwargs)
        self.assertEqual(categorias, ["D_INTERMITENTE"])
        self.assertNotIn("A_SEM_ALERTA_MECANICO", categorias)

    def test_somente_multiplas_entidades_censo(self) -> None:
        kwargs = {**self.BASE, "n_entidades_censo_com_ept_ativa": 2}
        categorias = auditoria.classify_municipio(**kwargs)
        self.assertEqual(categorias, ["C_MULTIPLAS_ENTIDADES"])

    def test_somente_multiplos_nomes_sistec(self) -> None:
        kwargs = {**self.BASE, "n_nomes_unidade_sistec_distintos": 2, "n_registros_sistec": 2}
        categorias = auditoria.classify_municipio(**kwargs)
        self.assertEqual(categorias, ["C_MULTIPLAS_ENTIDADES"])

    def test_f_ambiguo_isolado_por_duplicata(self) -> None:
        kwargs = {**self.BASE, "duplicata_ambigua_sistec": True}
        categorias = auditoria.classify_municipio(**kwargs)
        self.assertEqual(categorias, ["F_AMBIGUO"])

    def test_f_ambiguo_por_multiplicidade_nos_dois_lados(self) -> None:
        kwargs = {
            **self.BASE,
            "n_entidades_censo_com_ept_ativa": 2,
            "n_nomes_unidade_sistec_distintos": 2,
            "n_registros_sistec": 2,
        }
        categorias = auditoria.classify_municipio(**kwargs)
        self.assertIn("F_AMBIGUO", categorias)
        self.assertIn("C_MULTIPLAS_ENTIDADES", categorias)

    def test_sem_candidato_mec(self) -> None:
        kwargs = {
            **self.BASE,
            "n_registros_sistec": 0,
            "n_nomes_unidade_sistec_distintos": 0,
            "correspondencia_municipio": "sem_candidato",
        }
        categorias = auditoria.classify_municipio(**kwargs)
        self.assertEqual(categorias, ["E_SEM_CANDIDATO_MEC"])

    def test_ept_ativa_antes_de_2009(self) -> None:
        kwargs = {**self.BASE, "presenca_federal_ept_ativa_antes_2009": True}
        categorias = auditoria.classify_municipio(**kwargs)
        self.assertEqual(categorias, ["B_EPT_ATIVA_ANTES_2009"])

    def test_categorias_multiplas_nao_mutuamente_exclusivas(self) -> None:
        kwargs = {
            **self.BASE,
            "presenca_federal_ept_ativa_antes_2009": True,
            "trajetoria_intermitente_ept_ativa": True,
        }
        categorias = auditoria.classify_municipio(**kwargs)
        self.assertIn("B_EPT_ATIVA_ANTES_2009", categorias)
        self.assertIn("D_INTERMITENTE", categorias)
        self.assertNotIn("A_SEM_ALERTA_MECANICO", categorias)

    def test_a_sem_alerta_mecanico_nunca_coexiste_com_outra_categoria(self) -> None:
        # Propriedade geral (não um caso isolado): para qualquer alerta
        # individual ligado, A_SEM_ALERTA_MECANICO nunca pode aparecer
        # junto -- é exatamente a garantia que faltava antes da correção.
        variacoes = [
            {"presenca_federal_ept_ativa_antes_2009": True},
            {"n_entidades_censo_com_ept_ativa": 2},
            {"trajetoria_intermitente_ept_ativa": True},
            {"n_registros_sistec": 0, "n_nomes_unidade_sistec_distintos": 0, "correspondencia_municipio": "sem_candidato"},
            {"duplicata_ambigua_sistec": True},
        ]
        for extra in variacoes:
            categorias = auditoria.classify_municipio(**{**self.BASE, **extra})
            self.assertNotIn("A_SEM_ALERTA_MECANICO", categorias, msg=f"falhou para {extra}: {categorias}")


class TestPrioridadeRevisao(unittest.TestCase):
    def test_municipio_forcado_e_sempre_alta(self) -> None:
        codigo = next(iter(auditoria.MUNICIPIOS_PRIORIDADE_FORCADA))
        prioridade = auditoria.prioridade_revisao(codigo, [], False, False)
        self.assertEqual(prioridade, "alta")

    def test_f_ambiguo_e_alta(self) -> None:
        prioridade = auditoria.prioridade_revisao("0000000", ["F_AMBIGUO"], False, False)
        self.assertEqual(prioridade, "alta")

    def test_ept_antes_2009_com_multiplas_entidades_e_alta(self) -> None:
        prioridade = auditoria.prioridade_revisao(
            "0000000", ["B_EPT_ATIVA_ANTES_2009", "C_MULTIPLAS_ENTIDADES"], True, True
        )
        self.assertEqual(prioridade, "alta")

    def test_um_unico_sinal_e_media(self) -> None:
        prioridade = auditoria.prioridade_revisao("0000000", ["D_INTERMITENTE"], False, False)
        self.assertEqual(prioridade, "media")

    def test_sem_alerta_e_baixa(self) -> None:
        prioridade = auditoria.prioridade_revisao("0000000", ["A_SEM_ALERTA_MECANICO"], False, False)
        self.assertEqual(prioridade, "baixa")


class TestBuildLongTable(unittest.TestCase):
    def test_duas_fontes_simultaneas_sem_produto_cartesiano(self) -> None:
        fase_ii = pd.DataFrame({"codigo_municipio_ibge": ["1111111"], "municipio": ["Cidade Teste"], "uf": ["XX"]})
        censo_candidatos = pd.DataFrame({
            "codigo_municipio_ibge": ["1111111", "1111111"],
            "co_entidade": ["E1", "E2"],
            "nomes_historicos_censo": ["Campus 1", "Campus 2"],
            "primeiro_ano_registro_censo": [2010, 2011],
            "ultimo_ano_registro_censo": [2019, 2019],
            "primeiro_ano_ativa_censo": [2010, 2011],
            "ultimo_ano_ativa_censo": [2019, 2019],
            "primeiro_ano_ept_ativa_censo": [2010, 2011],
            "ultimo_ano_ept_ativa_censo": [2019, 2019],
        })
        sistec_candidatos = pd.DataFrame({
            "codigo_municipio_ibge": ["1111111"] * 3,
            "sigla_unidade_sistec": ["IF1", "IF2", "IF3"],
            "nome_unidade_sistec": ["Unidade 1", "Unidade 2", "Unidade 3"],
            "dt_autorizacao_sistec": ["01/01/2010 00:00:00"] * 3,
            "uf_unidade_sistec": ["XX"] * 3,
            "municipio_unidade_sistec": ["Cidade Teste"] * 3,
            "correspondencia_municipio": ["exata"] * 3,
        })
        longo = auditoria.build_long_table(fase_ii, censo_candidatos, sistec_candidatos)
        # uniao (2 Censo + 3 SISTEC = 5), nunca produto cartesiano (2*3=6)
        self.assertEqual(len(longo), 5)
        self.assertEqual(int((longo["tipo_candidato"] == "CENSO_ESCOLAR").sum()), 2)
        self.assertEqual(int((longo["tipo_candidato"] == "MEC_SISTEC").sum()), 3)


class TestValidateSummaryTable(unittest.TestCase):
    @staticmethod
    def _tabela_valida() -> tuple[pd.DataFrame, set[str]]:
        codigos = [f"{i:07d}" for i in range(147)]
        linhas = [
            {"codigo_municipio_ibge": c, "categorias": "A_SEM_ALERTA_MECANICO", "prioridade_revisao": "baixa"}
            for c in codigos
        ]
        forcados = set(auditoria.MUNICIPIOS_PRIORIDADE_FORCADA)
        intermitentes = {"2918001", "2804508", "3538709", "3143302"}
        for i, codigo in enumerate(sorted(forcados | intermitentes)):
            codigos[i] = codigo
            linhas[i]["codigo_municipio_ibge"] = codigo
            if codigo in intermitentes:
                linhas[i]["categorias"] = "D_INTERMITENTE"
            linhas[i]["prioridade_revisao"] = "alta" if codigo in forcados else "media"
        return pd.DataFrame(linhas), set(codigos)

    def test_aceita_tabela_valida(self) -> None:
        resumo, codigos = self._tabela_valida()
        auditoria.validate_summary_table(resumo, codigos)  # não deve levantar

    def test_rejeita_coluna_ano_tratamento(self) -> None:
        resumo, codigos = self._tabela_valida()
        resumo["ano_tratamento"] = 2010
        with self.assertRaises(ValueError):
            auditoria.validate_summary_table(resumo, codigos)

    def test_rejeita_menos_de_147_municipios(self) -> None:
        resumo, codigos = self._tabela_valida()
        resumo = resumo.iloc[:10].copy()
        with self.assertRaises(ValueError):
            auditoria.validate_summary_table(resumo, codigos)

    def test_rejeita_codigo_duplicado(self) -> None:
        resumo, codigos = self._tabela_valida()
        resumo.loc[1, "codigo_municipio_ibge"] = resumo.loc[0, "codigo_municipio_ibge"]
        with self.assertRaises(ValueError):
            auditoria.validate_summary_table(resumo, codigos)

    def test_rejeita_sem_alerta_coexistindo_com_outra_categoria(self) -> None:
        resumo, codigos = self._tabela_valida()
        resumo.loc[0, "categorias"] = "A_SEM_ALERTA_MECANICO; D_INTERMITENTE"
        with self.assertRaises(ValueError):
            auditoria.validate_summary_table(resumo, codigos)

    def test_rejeita_municipio_forcado_sem_prioridade_alta(self) -> None:
        resumo, codigos = self._tabela_valida()
        codigo_forcado = next(iter(auditoria.MUNICIPIOS_PRIORIDADE_FORCADA))
        resumo.loc[resumo["codigo_municipio_ibge"] == codigo_forcado, "prioridade_revisao"] = "baixa"
        with self.assertRaises(ValueError):
            auditoria.validate_summary_table(resumo, codigos)


class TestReadSistecCsv(unittest.TestCase):
    def test_arquivo_ausente_leva_a_filenotfounderror(self) -> None:
        with self.assertRaises(FileNotFoundError):
            auditoria.read_sistec_csv(Path("caminho/que/nao/existe.csv"))

    def test_valida_hash_e_tamanho_no_fluxo_de_producao(self) -> None:
        # Exercita o mesmo caminho que main() usa: caminho real do
        # repositório, hash e tamanho conferidos antes de ler.
        sistec = auditoria.read_sistec_csv(auditoria.SISTEC_PATH)
        self.assertGreater(len(sistec), 0)

    def test_preserva_string_literal_null(self) -> None:
        sistec = auditoria.read_sistec_csv(auditoria.SISTEC_PATH)
        self.assertEqual(int((sistec["sigla_unidade_ensino"] == "null").sum()), 183)
        self.assertEqual(int(sistec["sigla_unidade_ensino"].isna().sum()), 0)

    def test_valores_originais_nao_sao_modificados(self) -> None:
        sistec = auditoria.read_sistec_csv(auditoria.SISTEC_PATH)
        # nomes de unidade continuam com acentuação/caixa mista original,
        # não normalizados
        tem_minuscula = sistec["nome_unidade_ensino"].str.contains(r"[a-z]", regex=True).any()
        self.assertTrue(bool(tem_minuscula))


class TestSaidasSemColunaAnoTratamento(unittest.TestCase):
    def test_build_summary_table_nao_gera_coluna_ano_tratamento(self) -> None:
        fase_ii = pd.DataFrame({
            "codigo_municipio_ibge": ["1111111"],
            "municipio": ["Cidade Teste"],
            "uf": ["XX"],
        })
        censo_candidatos = pd.DataFrame({
            "codigo_municipio_ibge": ["1111111"],
            "co_entidade": ["E1"],
            "nomes_historicos_censo": ["Campus Teste"],
            "primeiro_ano_registro_censo": [2010],
            "ultimo_ano_registro_censo": [2019],
            "primeiro_ano_ativa_censo": [2010],
            "ultimo_ano_ativa_censo": [2019],
            "primeiro_ano_ept_ativa_censo": [2010],
            "ultimo_ano_ept_ativa_censo": [2019],
        })
        sistec_candidatos = pd.DataFrame(columns=[
            "codigo_municipio_ibge", "sigla_unidade_sistec", "nome_unidade_sistec",
            "dt_autorizacao_sistec", "uf_unidade_sistec", "municipio_unidade_sistec",
            "correspondencia_municipio",
        ])
        painel_diag = pd.DataFrame({
            "codigo_municipio_ibge": ["1111111"],
            "presenca_federal_geral_antes_2009": [False],
            "presenca_federal_ept_ativa_antes_2009": [False],
            "trajetoria_intermitente_ept_ativa": [False],
        })
        resumo = auditoria.build_summary_table(fase_ii, censo_candidatos, sistec_candidatos, painel_diag)
        longo = auditoria.build_long_table(fase_ii, censo_candidatos, sistec_candidatos)
        self.assertNotIn("ano_tratamento", resumo.columns)
        self.assertNotIn("ano_tratamento", longo.columns)
        self.assertIn("E_SEM_CANDIDATO_MEC", resumo.iloc[0]["categorias"])


if __name__ == "__main__":
    unittest.main()
