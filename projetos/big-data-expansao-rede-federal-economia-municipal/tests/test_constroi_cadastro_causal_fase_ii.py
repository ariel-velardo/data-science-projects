"""Testes do cadastro causal de tratamento da Expansão Fase II.

Execução:
    .venv\\Scripts\\python.exe -m pytest tests/test_constroi_cadastro_causal_fase_ii.py -v
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import auditoria_timing_tratamento as auditoria  # noqa: E402
import constroi_cadastro_causal_fase_ii as cadastro  # noqa: E402


def _valid_exception(**overrides):
    """Exceção mínima válida (candidata principal simples), para testes de
    schema — evita repetir todos os campos obrigatórios em cada teste."""
    base = {
        "ano_evento_institucional": 2010,
        "ano_transicao": 2010,
        "primeiro_ano_completo": 2011,
        "ano_coorte_candidata": 2011,
        "origem_coorte": "institucional_validada",
        "anos_sensibilidade": [],
        "anos_excluir_estimacao": [2010],
        "tratamento_absorvente": True,
        "tratamento_preexistente_painel": False,
        "status_institucional": "teste",
        "status_timing": "teste",
        "status_populacao_causal": "candidato_principal",
        "validacao_institucional_individual": True,
        "revisao_prioritaria": False,
        "nivel_evidencia": "fonte_institucional_oficial",
        "motivo_decisao": "motivo de teste",
        "fonte_decisao": "fonte_teste",
        "fontes": [{
            "url_ou_caminho": "https://exemplo.gov.br",
            "titulo": "Título de teste",
            "orgao": "Órgão de teste",
            "data_evidencia_ou_acesso": "2026-01-01",
            "nivel_evidencia": "fonte_institucional_oficial",
            "descricao_factual": "descrição de teste",
            "campo_sustentado": "ano_evento_institucional",
        }],
    }
    base.update(overrides)
    return base


class TestFonteReproduzivelDoTiming(unittest.TestCase):
    """Correção 1: o cálculo do timing não pode depender do CSV ignorado
    pelo Git; precisa vir diretamente do painel."""

    def test_calculo_direto_nao_le_o_csv_de_auditoria(self) -> None:
        fase_ii = auditoria.read_processed_parquet(cadastro.FASE_II_PATH)
        painel = auditoria.read_processed_parquet(cadastro.PAINEL_PATH)
        # Chamado sem que o CSV precise existir: se compute_timing_observado_censo
        # dependesse dele, um caminho inexistente causaria falha aqui.
        caminho_falso = Path("caminho/que/nao/existe.csv")
        self.assertFalse(caminho_falso.exists())
        timing = cadastro.compute_timing_observado_censo(fase_ii, painel)
        cadastro.cross_check_timing_csv(timing, csv_path=caminho_falso)  # não deve levantar
        self.assertEqual(len(timing), 147)

    def test_cross_check_falha_com_mensagem_clara_se_csv_divergir(self, tmp_path=Path(".")) -> None:
        import tempfile
        computed = pd.DataFrame({
            "codigo_municipio_ibge": ["1111111", "2222222"],
            "ano_inicio_observado_censo": [2010, 2011],
        })
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "auditoria_timing_tratamento.csv"
            pd.DataFrame({
                "codigo_municipio_ibge": ["1111111", "2222222"],
                "primeiro_ano_presenca_federal_ept_ativa": [2010, 9999],  # diverge
            }).to_csv(csv_path, index=False)
            with self.assertRaises(ValueError) as ctx:
                cadastro.cross_check_timing_csv(computed, csv_path=csv_path)
            self.assertIn("2222222", str(ctx.exception))

    def test_painel_tem_exatamente_147_vezes_13_linhas(self) -> None:
        painel = auditoria.read_processed_parquet(cadastro.PAINEL_PATH)
        self.assertEqual(len(painel), 147 * 13)

    def test_cross_check_falha_com_codigo_municipal_excedente_no_csv(self) -> None:
        import tempfile
        computed = pd.DataFrame({
            "codigo_municipio_ibge": ["1111111", "2222222"],
            "ano_inicio_observado_censo": [2010, 2011],
        })
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "auditoria_timing_tratamento.csv"
            pd.DataFrame({
                # "3333333" não existe no cálculo direto do painel: um merge
                # left silenciosamente ignoraria essa linha excedente.
                "codigo_municipio_ibge": ["1111111", "2222222", "3333333"],
                "primeiro_ano_presenca_federal_ept_ativa": [2010, 2011, 2012],
            }).to_csv(csv_path, index=False)
            with self.assertRaises(ValueError) as ctx:
                cadastro.cross_check_timing_csv(computed, csv_path=csv_path)
            self.assertIn("3333333", str(ctx.exception))


class TestValidacaoDoPainel(unittest.TestCase):
    """Correção 2: validação por município, não apenas conjuntos globais."""

    def test_falha_se_um_municipio_tiver_contagem_diferente_de_13(self) -> None:
        fase_ii = auditoria.read_processed_parquet(cadastro.FASE_II_PATH)
        painel = auditoria.read_processed_parquet(cadastro.PAINEL_PATH)
        anos = pd.to_numeric(painel["NU_ANO_CENSO"], errors="raise")
        primeiro_codigo = painel["CO_MUNICIPIO"].iloc[0]
        # Remove uma única observação de um único município: os conjuntos
        # globais de anos e códigos continuam intactos, mas a contagem por
        # município já não é 13 — isso não pode passar despercebido.
        painel_quebrado = painel[~((painel["CO_MUNICIPIO"] == primeiro_codigo) & (anos == 2007))]
        self.assertEqual(len(painel_quebrado), len(painel) - 1)
        with self.assertRaises(ValueError) as ctx:
            cadastro.compute_timing_observado_censo(fase_ii, painel_quebrado)
        self.assertIn("13", str(ctx.exception))

    def test_falha_se_um_municipio_tiver_cobertura_de_anos_incorreta_mas_total_de_linhas_preservado(self) -> None:
        fase_ii = auditoria.read_processed_parquet(cadastro.FASE_II_PATH)
        painel = auditoria.read_processed_parquet(cadastro.PAINEL_PATH)
        anos = pd.to_numeric(painel["NU_ANO_CENSO"], errors="raise")
        primeiro_codigo = painel["CO_MUNICIPIO"].iloc[0]
        # Duplica 2007 e remove 2019 do mesmo município: total de linhas do
        # painel inteiro permanece 1.911 e o conjunto GLOBAL de anos
        # continua sendo {2007..2019}, mas esse município específico não
        # cobre mais 2007-2019. Uma checagem só-global não pegaria isso.
        idx_2007 = painel[(painel["CO_MUNICIPIO"] == primeiro_codigo) & (anos == 2007)].index
        idx_2019 = painel[(painel["CO_MUNICIPIO"] == primeiro_codigo) & (anos == 2019)].index
        duplicata_de_2007 = painel.loc[idx_2007].copy()  # ano permanece 2007, não 2019
        painel_quebrado = pd.concat([painel.drop(index=idx_2019), duplicata_de_2007], ignore_index=True)
        self.assertEqual(len(painel_quebrado), 1911)
        with self.assertRaises(ValueError):
            cadastro.compute_timing_observado_censo(fase_ii, painel_quebrado)


class TestSemanticaDaProxyDoCenso(unittest.TestCase):
    """Correção 3: proxy do Censo nunca vira data institucional confirmada."""

    def test_municipio_padrao_nao_preenche_primeiro_ano_completo(self) -> None:
        decision = cadastro.build_default_decision("1111111", 2012)
        self.assertIsNone(decision["primeiro_ano_completo"])
        self.assertIsNone(decision["ano_evento_institucional"])
        self.assertIsNone(decision["ano_transicao"])
        self.assertEqual(decision["ano_coorte_candidata"], 2012)
        self.assertEqual(decision["origem_coorte"], "proxy_censo")
        self.assertFalse(decision["validacao_institucional_individual"])

    def test_validacao_individual_nao_implica_revisao_prioritaria_automatica(self) -> None:
        # Um município pode não ter validação individual (proxy padrão) e,
        # ainda assim, não entrar na fila prioritária de revisão.
        decision = cadastro.build_default_decision("1111111", 2012)
        self.assertFalse(decision["validacao_institucional_individual"])
        self.assertFalse(decision["revisao_prioritaria"])

    def test_nenhum_municipio_do_cadastro_real_tem_primeiro_ano_completo_sem_validacao(self) -> None:
        fase_ii = auditoria.read_processed_parquet(cadastro.FASE_II_PATH)
        painel = auditoria.read_processed_parquet(cadastro.PAINEL_PATH)
        exceptions = cadastro.load_exceptions(cadastro.EXCEPTIONS_PATH)
        registry = cadastro.build_causal_registry(fase_ii, painel, exceptions)
        sem_validacao = registry[~registry["validacao_institucional_individual"]]
        self.assertTrue(sem_validacao["primeiro_ano_completo"].isna().all())


class TestFlagsPopulacionais(unittest.TestCase):
    """Correção 4: flags fixas para toda a população institucional."""

    @classmethod
    def setUpClass(cls) -> None:
        fase_ii = auditoria.read_processed_parquet(cadastro.FASE_II_PATH)
        painel = auditoria.read_processed_parquet(cadastro.PAINEL_PATH)
        exceptions = cadastro.load_exceptions(cadastro.EXCEPTIONS_PATH)
        cls.registry = cadastro.build_causal_registry(fase_ii, painel, exceptions)

    def test_147_codigos_unicos(self) -> None:
        self.assertEqual(len(self.registry), 147)
        self.assertEqual(self.registry["codigo_municipio_ibge"].nunique(), 147)

    def test_nenhum_municipio_pode_ser_controle(self) -> None:
        self.assertFalse(self.registry["pode_ser_controle"].any())

    def test_todos_ever_treated(self) -> None:
        self.assertTrue(self.registry["ever_treated"].all())

    def test_exclusao_nao_e_ausencia_de_tratamento(self) -> None:
        excluidos = self.registry[self.registry["status_populacao_causal"] == "excluido_principal"]
        self.assertGreater(len(excluidos), 0)
        self.assertTrue((excluidos["ever_treated"]).all())
        self.assertFalse((excluidos["pode_ser_controle"]).any())

    def test_elegibilidade_temporal_bruta_nao_vira_candidatura_automatica(self) -> None:
        # Existe pelo menos um município temporalmente elegível que NÃO é
        # candidato à amostra principal por motivo institucional (não apenas
        # temporal) — prova de que os dois campos não são a mesma coisa.
        elegivel_mas_fora = self.registry[
            self.registry["elegivel_temporal_2pre_3pos"] & ~self.registry["candidato_amostra_principal"]
        ]
        self.assertGreater(len(elegivel_mas_fora), 0)

    def test_nenhum_excluido_especial_ou_sob_revisao_entra_na_amostra_principal(self) -> None:
        bloqueado = self.registry["status_populacao_causal"].isin(
            {"excluido_principal", "especial_estimando", "sob_revisao", "candidato_com_ressalva",
             "institucional_inelegivel_janelas"}
        )
        self.assertFalse(self.registry.loc[bloqueado, "candidato_amostra_principal"].any())

    def test_crosstab_soma_147(self) -> None:
        table = cadastro.build_status_crosstab(self.registry)
        self.assertEqual(int(table["n_municipios"].sum()), 147)


class TestAnosParciais(unittest.TestCase):
    def test_ano_parcial_aparece_em_anos_excluir_estimacao(self) -> None:
        exceptions = cadastro.load_exceptions(cadastro.EXCEPTIONS_PATH)
        alcantara = exceptions["2100204"]
        self.assertEqual(alcantara["ano_transicao"], 2008)
        self.assertIn(2008, alcantara["anos_excluir_estimacao"])

    def test_ano_parcial_nao_e_contado_como_pre_limpo(self) -> None:
        decision = cadastro.apply_exception(
            cadastro.build_default_decision("2100204", 2008),
            {"ano_evento_institucional": 2008, "ano_transicao": 2008, "primeiro_ano_completo": 2009,
             "ano_coorte_candidata": 2009, "origem_coorte": "institucional_validada"},
        )
        self.assertEqual(cadastro.calculate_n_pre_limpo(decision), 1)
        self.assertFalse(cadastro.eligible(decision, pre=2, post=3, end_year=2019))

    def test_regra_nao_se_aplica_quando_mes_e_desconhecido(self) -> None:
        # Cabedelo: identidade validada, mas mês/natureza do início desconhecidos
        # -> ano_transicao deve permanecer nulo, não ser inventado.
        exceptions = cadastro.load_exceptions(cadastro.EXCEPTIONS_PATH)
        cabedelo = exceptions["2503209"]
        self.assertIsNone(cabedelo["ano_transicao"])
        self.assertIsNone(cabedelo["primeiro_ano_completo"])


class TestCasosEspeciais(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fase_ii = auditoria.read_processed_parquet(cadastro.FASE_II_PATH)
        painel = auditoria.read_processed_parquet(cadastro.PAINEL_PATH)
        cls.exceptions = cadastro.load_exceptions(cadastro.EXCEPTIONS_PATH)
        cls.registry = cadastro.build_causal_registry(fase_ii, painel, cls.exceptions)

    def _row(self, code: str) -> pd.Series:
        codes = self.registry["codigo_municipio_ibge"].astype("string").str.zfill(7)
        matches = self.registry[codes == str(code).zfill(7)]
        self.assertEqual(len(matches), 1, f"esperava exatamente 1 linha para {code}, achei {len(matches)}")
        return matches.iloc[0]

    def test_brasilia_excluida_e_nunca_controle(self) -> None:
        row = self._row("5300108")
        self.assertEqual(row["status_populacao_causal"], "excluido_principal")
        self.assertFalse(row["pode_ser_controle"])
        self.assertTrue(row["ever_treated"])
        self.assertFalse(row["candidato_amostra_principal"])

    def test_duque_de_caxias_nao_recebe_g_2007(self) -> None:
        row = self._row("3301702")
        self.assertTrue(pd.isna(row["ano_coorte_candidata"]))
        self.assertNotEqual(row["ano_coorte_candidata"], 2007)

    def test_duque_de_caxias_e_exposicao_anterior_ao_painel(self) -> None:
        row = self._row("3301702")
        self.assertTrue(row["tratamento_preexistente_painel"])
        self.assertEqual(row["status_populacao_causal"], "excluido_principal")
        self.assertFalse(row["candidato_amostra_principal"])
        self.assertFalse(row["pode_ser_controle"])

    def test_porto_alegre_e_estimando_especial_nao_candidato_principal(self) -> None:
        row = self._row("4314902")
        self.assertEqual(row["status_populacao_causal"], "especial_estimando")
        self.assertFalse(row["candidato_amostra_principal"])
        self.assertFalse(row["pode_ser_controle"])
        # não mistura "primeira exposição" com "chegada de campus adicional":
        # a coorte registrada é a do Restinga (2011), não uma primeira
        # exposição municipal em 2007.
        self.assertEqual(int(row["ano_coorte_candidata"]), 2011)

    def test_montes_claros_nao_e_classificado_como_reversao_pela_serie_agregada(self) -> None:
        row = self._row("3143302")
        self.assertTrue(row["intermitencia_observada_no_painel"])
        self.assertTrue(row["tratamento_absorvente"])
        # só pode ser absorvente apesar da intermitência com validação
        # institucional individual documentada — nunca por padrão.
        self.assertTrue(row["validacao_institucional_individual"])
        self.assertIn("duas_entidades", row["status_institucional"])

    def test_jequie_nsg_piracicaba_permanecem_sob_revisao_fora_da_principal(self) -> None:
        for codigo in ("2918001", "2804508", "3538709"):
            row = self._row(codigo)
            self.assertEqual(row["status_populacao_causal"], "sob_revisao", codigo)
            self.assertFalse(row["candidato_amostra_principal"], codigo)
            self.assertFalse(row["tratamento_absorvente"], codigo)
            self.assertFalse(row["pode_ser_controle"], codigo)

    def test_alcantara_e_abaetetuba_permanecem_institucionais_mas_inelegiveis(self) -> None:
        for codigo in ("2100204", "1500107"):
            row = self._row(codigo)
            self.assertTrue(row["ever_treated"], codigo)
            self.assertFalse(row["pode_ser_controle"], codigo)
            self.assertFalse(row["elegivel_temporal_2pre_3pos"], codigo)
            self.assertFalse(row["candidato_amostra_principal"], codigo)


class TestValidacaoDeSchemaDoJson(unittest.TestCase):
    """Correção 8: combinações inválidas devem ser rejeitadas com clareza."""

    def test_rejeita_codigo_inexistente_em_excecoes(self) -> None:
        fase = pd.DataFrame({"codigo_municipio_ibge": ["1111111"], "municipio": ["Teste"], "uf": ["TS"]})
        with self.assertRaises(ValueError):
            cadastro.validate_exception_codes(fase, {"9999999": {}})

    def test_rejeita_json_com_campo_obrigatorio_faltando(self) -> None:
        incompleta = _valid_exception()
        del incompleta["motivo_decisao"]
        with self.assertRaises(ValueError) as ctx:
            cadastro.validate_exception_schema("1111111", incompleta)
        self.assertIn("motivo_decisao", str(ctx.exception))

    def test_rejeita_ano_fora_da_janela_admitida(self) -> None:
        invalida = _valid_exception(ano_evento_institucional=1990)
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_rejeita_status_populacao_causal_invalido(self) -> None:
        invalida = _valid_exception(status_populacao_causal="status_inventado")
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_rejeita_origem_coorte_invalida(self) -> None:
        invalida = _valid_exception(origem_coorte="fonte_misteriosa")
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_rejeita_transicao_diferente_do_evento(self) -> None:
        invalida = _valid_exception(ano_evento_institucional=2010, ano_transicao=2011)
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_rejeita_primeiro_ano_completo_antes_da_transicao(self) -> None:
        invalida = _valid_exception(ano_transicao=2011, primeiro_ano_completo=2010, ano_evento_institucional=2011)
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_rejeita_transicao_ausente_de_anos_excluir_estimacao(self) -> None:
        invalida = _valid_exception(anos_excluir_estimacao=[])
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_rejeita_preexistente_com_coorte_definida(self) -> None:
        invalida = _valid_exception(
            tratamento_preexistente_painel=True, status_populacao_causal="excluido_principal"
        )
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_rejeita_proxy_censo_com_coorte_explicita(self) -> None:
        invalida = _valid_exception(origem_coorte="proxy_censo")  # coorte=2011 ainda presente
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_rejeita_validacao_true_sem_nivel_institucional(self) -> None:
        invalida = _valid_exception(nivel_evidencia="auditoria_local_dados")
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_rejeita_validacao_true_sem_fontes(self) -> None:
        invalida = _valid_exception(fontes=[])
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_rejeita_fonte_com_campo_obrigatorio_faltando(self) -> None:
        invalida = _valid_exception()
        del invalida["fontes"][0]["orgao"]
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_rejeita_campo_populacional_fixo_sobrescrito(self) -> None:
        invalida = _valid_exception()
        invalida["pode_ser_controle"] = True
        with self.assertRaises(ValueError):
            cadastro.validate_exception_schema("1111111", invalida)

    def test_json_real_carrega_sem_erro(self) -> None:
        exceptions = cadastro.load_exceptions(cadastro.EXCEPTIONS_PATH)
        self.assertGreaterEqual(len(exceptions), 15)

    def test_rejeita_campo_desconhecido_no_nivel_da_excecao(self) -> None:
        invalida = _valid_exception(campo_desconhecido="valor_inesperado")
        with self.assertRaises(ValueError) as ctx:
            cadastro.validate_exception_schema("1111111", invalida)
        self.assertIn("campo_desconhecido", str(ctx.exception))

    def test_rejeita_campo_desconhecido_em_fontes(self) -> None:
        invalida = _valid_exception()
        invalida["fontes"][0]["campo_desconhecido"] = "valor_inesperado"
        with self.assertRaises(ValueError) as ctx:
            cadastro.validate_exception_schema("1111111", invalida)
        self.assertIn("campo_desconhecido", str(ctx.exception))


class TestDeterminismoEIntegridade(unittest.TestCase):
    def test_execucao_e_deterministica(self) -> None:
        fase_ii = auditoria.read_processed_parquet(cadastro.FASE_II_PATH)
        painel = auditoria.read_processed_parquet(cadastro.PAINEL_PATH)
        exceptions = cadastro.load_exceptions(cadastro.EXCEPTIONS_PATH)
        r1 = cadastro.build_causal_registry(fase_ii, painel, exceptions)
        r2 = cadastro.build_causal_registry(fase_ii, painel, copy.deepcopy(exceptions))
        pd.testing.assert_frame_equal(r1, r2)

    def test_absorvente_e_monotonico(self) -> None:
        self.assertEqual(cadastro.absorbing_treatment_series(2012, 2007, 2019), [False] * 5 + [True] * 8)

    def test_ausencia_de_coorte_nao_tenta_converter_nan_em_inteiro(self) -> None:
        decision = cadastro.build_default_decision("1111111", 2012)
        decision["ano_coorte_candidata"] = float("nan")
        self.assertIsNone(cadastro.calculate_n_pre_limpo(decision))
        self.assertFalse(cadastro.eligible(decision, pre=2, post=3, end_year=2019))


if __name__ == "__main__":
    unittest.main()
