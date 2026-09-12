"""Testes do cadastro nacional de exposição à Rede Federal.

Execução:
    .venv\\Scripts\\python.exe -m unittest \
        tests.test_constroi_cadastro_nacional_exposicao_rede_federal -v

Todos os testes usam dados sintéticos pequenos — nenhum lê os ZIPs
brutos do Censo Escolar (isso só acontece na execução real de `main()`).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import constroi_cadastro_nacional_exposicao_rede_federal as cadastro  # noqa: E402

ANOS = cadastro.ANOS
COUNT_COLS = cadastro.COUNT_COLS
FLAG_COLS = list(cadastro.FLAG_DEFINITIONS)


def _painel_row(
    codigo: str = "1100015",
    ano: int = 2007,
    nome: str = "Município Teste",
    uf: str = "RO",
    co_uf: str | None = None,
    qt_federal: int = 0,
    qt_ativa: int = 0,
    qt_ept: int = 0,
    qt_ept_tec: int = 0,
    qt_ept_ativa: int = 0,
) -> dict:
    """Constrói uma linha do painel nacional já no schema final (inclusive
    flags), replicando manualmente a mesma regra de `build_painel_nacional`
    para poder testar `validate_painel_nacional` de forma isolada, e
    permitindo introduzir incoerências propositais nos testes negativos."""
    co_uf = co_uf if co_uf is not None else codigo[:2]
    return {
        "CO_MUNICIPIO": codigo,
        "NU_ANO_CENSO": str(ano),
        "NO_MUNICIPIO": nome,
        "SG_UF": uf,
        "CO_UF": co_uf,
        "qt_escolas_federais": qt_federal,
        "qt_escolas_em_atividade": qt_ativa,
        "qt_escolas_com_ept": qt_ept,
        "qt_escolas_com_ept_tecnica": qt_ept_tec,
        "qt_escolas_federal_ept_ativa": qt_ept_ativa,
        "qt_mat_prof": 0,
        "qt_mat_prof_tec": 0,
        "qt_tur_prof": 0,
        "qt_tur_prof_tec": 0,
        "qt_doc_prof": 0,
        "qt_doc_prof_tec": 0,
        "fl_presenca_federal": qt_federal > 0,
        "fl_presenca_federal_ativa": qt_ativa > 0,
        "fl_presenca_federal_ept": qt_ept > 0,
        "fl_presenca_federal_ept_ativa": qt_ept_ativa > 0,
    }


def _painel_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in COUNT_COLS:
        df[col] = df[col].astype("Int64")
    for col in FLAG_COLS:
        df[col] = df[col].astype(bool)
    return df


def _municipio_exposto_em(codigo: str, anos_expostos: set[int], anos_no_universo: list[int] | None = None,
                           uf: str = "RO") -> list[dict]:
    """Gera 1 linha por ano em `anos_no_universo` (default: todos os 13),
    com EPT federal ativa exatamente nos anos de `anos_expostos`."""
    anos_no_universo = anos_no_universo if anos_no_universo is not None else list(ANOS)
    rows = []
    for ano in anos_no_universo:
        exposto = ano in anos_expostos
        rows.append(_painel_row(
            codigo=codigo, ano=ano, uf=uf,
            qt_federal=1, qt_ativa=1 if exposto else 1, qt_ept=1 if exposto else 0,
            qt_ept_ativa=1 if exposto else 0,
        ))
    return rows


class TestBuildPainelNacional(unittest.TestCase):
    """Junção universo + contagens federais, preenchimento de zero."""

    def test_municipio_sem_registro_federal_recebe_contagem_zero(self) -> None:
        universo = pd.DataFrame([
            {"CO_MUNICIPIO": "1100015", "NU_ANO_CENSO": "2007", "NO_MUNICIPIO": "Alta Floresta D'Oeste",
             "SG_UF": "RO", "CO_UF": "11"},
        ])
        federal_vazio = pd.DataFrame(columns=["CO_MUNICIPIO", "NU_ANO_CENSO", *COUNT_COLS])
        painel = cadastro.build_painel_nacional(universo, federal_vazio)
        self.assertEqual(len(painel), 1)
        row = painel.iloc[0]
        for col in COUNT_COLS:
            self.assertEqual(row[col], 0)
        for flag in FLAG_COLS:
            self.assertFalse(row[flag])

    def test_municipio_com_registro_federal_preserva_contagem(self) -> None:
        universo = pd.DataFrame([
            {"CO_MUNICIPIO": "1100023", "NU_ANO_CENSO": "2011", "NO_MUNICIPIO": "Ariquemes",
             "SG_UF": "RO", "CO_UF": "11"},
        ])
        federal = pd.DataFrame([{
            "CO_MUNICIPIO": "1100023", "NU_ANO_CENSO": "2011",
            "qt_escolas_federais": 1, "qt_escolas_em_atividade": 1, "qt_escolas_com_ept": 1,
            "qt_escolas_com_ept_tecnica": 1, "qt_escolas_federal_ept_ativa": 1,
            "qt_mat_prof": 50, "qt_mat_prof_tec": 50, "qt_tur_prof": 2, "qt_tur_prof_tec": 2,
            "qt_doc_prof": 5, "qt_doc_prof_tec": 5,
        }])
        painel = cadastro.build_painel_nacional(universo, federal)
        row = painel.iloc[0]
        self.assertEqual(row["qt_escolas_federais"], 1)
        self.assertTrue(row["fl_presenca_federal_ept_ativa"])

    def test_universo_com_municipios_diferentes_por_ano_nao_forca_grade_fixa(self) -> None:
        # Município "9999999" só existe no universo a partir de 2013 —
        # simula criação territorial durante a janela.
        universo = pd.DataFrame([
            {"CO_MUNICIPIO": "1100015", "NU_ANO_CENSO": "2007", "NO_MUNICIPIO": "A", "SG_UF": "RO", "CO_UF": "11"},
            {"CO_MUNICIPIO": "1100015", "NU_ANO_CENSO": "2013", "NO_MUNICIPIO": "A", "SG_UF": "RO", "CO_UF": "11"},
            {"CO_MUNICIPIO": "9999999", "NU_ANO_CENSO": "2013", "NO_MUNICIPIO": "B", "SG_UF": "RO", "CO_UF": "99"},
        ])
        federal_vazio = pd.DataFrame(columns=["CO_MUNICIPIO", "NU_ANO_CENSO", *COUNT_COLS])
        painel = cadastro.build_painel_nacional(universo, federal_vazio)
        # Exatamente 3 linhas — nenhuma linha "9999999"/"2007" foi inventada.
        self.assertEqual(len(painel), 3)
        self.assertNotIn(
            ("9999999", "2007"),
            set(zip(painel["CO_MUNICIPIO"], painel["NU_ANO_CENSO"])),
        )


class TestValidatePainelNacionalNegativos(unittest.TestCase):
    """Casos que devem ser rejeitados por `validate_painel_nacional`."""

    def test_rejeita_anos_fora_de_2007_2019(self) -> None:
        painel = _painel_df([_painel_row(ano=2020)])
        with self.assertRaises(ValueError):
            cadastro.validate_painel_nacional(painel)

    def test_rejeita_duplicidade_municipio_ano(self) -> None:
        rows = _municipio_exposto_em("1100015", set())
        rows.append(_painel_row(codigo="1100015", ano=2010))  # duplica 2010
        painel = _painel_df(rows)
        with self.assertRaises(ValueError) as ctx:
            cadastro.validate_painel_nacional(painel)
        self.assertIn("duplicada", str(ctx.exception))

    def test_rejeita_codigo_municipal_com_comprimento_invalido(self) -> None:
        rows = _municipio_exposto_em("11000155", set())  # 8 dígitos
        painel = _painel_df(rows)
        with self.assertRaises(ValueError):
            cadastro.validate_painel_nacional(painel)

    def test_rejeita_codigo_municipal_nulo(self) -> None:
        rows = _municipio_exposto_em("1100015", set())
        painel = _painel_df(rows)
        painel.loc[0, "CO_MUNICIPIO"] = None
        with self.assertRaises(ValueError):
            cadastro.validate_painel_nacional(painel)

    def test_rejeita_uf_incoerente_com_codigo_municipal(self) -> None:
        rows = _municipio_exposto_em("1100015", set())
        painel = _painel_df(rows)
        painel.loc[0, "CO_UF"] = "99"  # diverge do prefixo "11" de 1100015
        with self.assertRaises(ValueError) as ctx:
            cadastro.validate_painel_nacional(painel)
        self.assertIn("CO_UF", str(ctx.exception))

    def test_rejeita_contagem_negativa(self) -> None:
        rows = _municipio_exposto_em("1100015", set())
        painel = _painel_df(rows)
        painel.loc[0, "qt_escolas_federais"] = -1
        with self.assertRaises(ValueError):
            cadastro.validate_painel_nacional(painel)

    def test_rejeita_flag_incoerente_com_contagem(self) -> None:
        rows = _municipio_exposto_em("1100015", set())
        painel = _painel_df(rows)
        painel.loc[0, "fl_presenca_federal"] = False  # contagem=1 mas flag=False
        with self.assertRaises(ValueError) as ctx:
            cadastro.validate_painel_nacional(painel)
        self.assertIn("incoerente", str(ctx.exception))

    def test_rejeita_ept_ativa_sem_presenca_federal(self) -> None:
        rows = _municipio_exposto_em("1100015", set())
        painel = _painel_df(rows)
        # Linha internamente coerente coluna a coluna (cada flag bate com
        # sua própria contagem), mas que viola o contentamento lógico
        # fl_presenca_federal_ept_ativa ⇒ fl_presenca_federal.
        painel.loc[0, "qt_escolas_federais"] = 0
        painel.loc[0, "fl_presenca_federal"] = False
        painel.loc[0, "qt_escolas_federal_ept_ativa"] = 1
        painel.loc[0, "fl_presenca_federal_ept_ativa"] = True
        with self.assertRaises(ValueError) as ctx:
            cadastro.validate_painel_nacional(painel)
        self.assertIn("presença federal", str(ctx.exception))


class TestReconciliacaoFederal(unittest.TestCase):
    def test_falha_se_registro_federal_positivo_for_perdido_pelo_merge(self) -> None:
        # O painel nacional (universo) não contém o município do registro
        # federal — simula um bug de universo incompleto.
        painel = _painel_df([_painel_row(codigo="1100015", ano=2010)])
        federal = pd.DataFrame([{
            "CO_MUNICIPIO": "2200000", "NU_ANO_CENSO": "2010",
            **{c: 1 for c in COUNT_COLS},
        }])
        with self.assertRaises(ValueError) as ctx:
            cadastro.validate_reconciliacao_federal(painel, federal)
        self.assertIn("perdido pelo merge", str(ctx.exception))

    def test_falha_se_contagem_divergir_entre_painel_e_federal(self) -> None:
        painel = _painel_df([_painel_row(codigo="1100015", ano=2010, qt_federal=1)])
        federal = pd.DataFrame([{
            "CO_MUNICIPIO": "1100015", "NU_ANO_CENSO": "2010",
            "qt_escolas_federais": 2,  # diverge do painel (1)
            **{c: 0 for c in COUNT_COLS if c != "qt_escolas_federais"},
        }])
        with self.assertRaises(ValueError) as ctx:
            cadastro.validate_reconciliacao_federal(painel, federal)
        self.assertIn("Divergência", str(ctx.exception))

    def test_falha_se_municipio_sem_registro_federal_tiver_contagem_diferente_de_zero(self) -> None:
        # Município tem contagem > 0 no painel, mas não existe nenhum
        # registro correspondente na fonte federal — inconsistência.
        painel = _painel_df([_painel_row(codigo="1100015", ano=2010, qt_federal=1)])
        federal_vazio = pd.DataFrame(columns=["CO_MUNICIPIO", "NU_ANO_CENSO", *COUNT_COLS])
        with self.assertRaises(ValueError):
            cadastro.validate_reconciliacao_federal(painel, federal_vazio)

    def test_passa_quando_painel_e_federal_estao_reconciliados(self) -> None:
        painel = _painel_df([
            _painel_row(codigo="1100015", ano=2010, qt_federal=0),
            _painel_row(codigo="1100023", ano=2010, qt_federal=1, qt_ativa=1, qt_ept=1, qt_ept_ativa=1),
        ])
        federal = pd.DataFrame([{
            "CO_MUNICIPIO": "1100023", "NU_ANO_CENSO": "2010",
            "qt_escolas_federais": 1, "qt_escolas_em_atividade": 1, "qt_escolas_com_ept": 1,
            "qt_escolas_com_ept_tecnica": 0, "qt_escolas_federal_ept_ativa": 1,
            "qt_mat_prof": 0, "qt_mat_prof_tec": 0, "qt_tur_prof": 0, "qt_tur_prof_tec": 0,
            "qt_doc_prof": 0, "qt_doc_prof_tec": 0,
        }])
        cadastro.validate_reconciliacao_federal(painel, federal)  # não deve levantar


class TestReconciliacaoFaseII(unittest.TestCase):
    def test_falha_se_subconjunto_fase_ii_nao_tiver_147_vezes_13(self) -> None:
        painel = _painel_df(_municipio_exposto_em("1100015", set()))  # só 1 município, 13 anos
        fase_ii_painel = pd.DataFrame(columns=["CO_MUNICIPIO", "NU_ANO_CENSO", *COUNT_COLS, *FLAG_COLS])
        with self.assertRaises(ValueError):
            cadastro.validate_reconciliacao_fase_ii(painel, fase_ii_painel, fase_ii_codes={"1100015", "2200000"})

    def test_falha_se_coluna_comparavel_divergir_do_painel_fase_ii_aprovado(self) -> None:
        rows = _municipio_exposto_em("1100015", {2011, 2012, 2013})
        painel = _painel_df(rows)
        fase_ii_painel = _painel_df(rows).copy()
        # Introduz divergência isolada em uma linha do painel Fase II "aprovado".
        fase_ii_painel.loc[fase_ii_painel["NU_ANO_CENSO"] == "2011", "qt_escolas_federais"] = 99
        with self.assertRaises(ValueError) as ctx:
            cadastro.validate_reconciliacao_fase_ii(painel, fase_ii_painel, fase_ii_codes={"1100015"})
        self.assertIn("Divergência", str(ctx.exception))

    def test_passa_quando_subconjunto_fase_ii_bate_exatamente(self) -> None:
        rows = _municipio_exposto_em("1100015", {2011, 2012, 2013})
        painel = _painel_df(rows)
        fase_ii_painel = _painel_df(rows)
        cadastro.validate_reconciliacao_fase_ii(painel, fase_ii_painel, fase_ii_codes={"1100015"})  # não deve levantar

    def test_falha_se_painel_fase_ii_tiver_chave_excedente(self) -> None:
        # Adversarial: o painel Fase II de referência ganha uma chave
        # município-ano válida e NÃO duplicada (município diferente, ano já
        # existente para outro município) que não pertence ao conjunto
        # esperado de fase_ii_codes × ANOS. Um merge interno sozinho
        # descartaria essa linha silenciosamente sem erro — por isso a
        # validação de conjuntos de chaves precisa detectá-la antes do merge.
        rows = _municipio_exposto_em("1100015", {2011, 2012, 2013})
        painel = _painel_df(rows)
        chave_excedente = ("9999999", "2015")
        self.assertNotIn(chave_excedente, {(r["CO_MUNICIPIO"], r["NU_ANO_CENSO"]) for r in rows})
        linha_excedente = _painel_row(codigo=chave_excedente[0], ano=int(chave_excedente[1]), uf="MA")
        fase_ii_painel = _painel_df(rows + [linha_excedente])
        with self.assertRaises(ValueError) as ctx:
            cadastro.validate_reconciliacao_fase_ii(painel, fase_ii_painel, fase_ii_codes={"1100015"})
        mensagem = str(ctx.exception)
        self.assertIn("Excedentes", mensagem)
        self.assertIn("9999999", mensagem)


class TestBuildResumoMunicipal(unittest.TestCase):
    """Cobre os cenários pedidos: sem exposição, exposto desde 2007,
    primeira exposição durante a janela, intermitência, mudança de
    universo entre anos."""

    def _resumo_de(self, codigo: str, anos_expostos: set[int], anos_no_universo: list[int] | None = None) -> pd.Series:
        rows = _municipio_exposto_em(codigo, anos_expostos, anos_no_universo)
        painel = _painel_df(rows)
        resumo = cadastro.build_resumo_municipal(painel)
        cadastro.validate_resumo_municipal(resumo, painel)  # não deve levantar
        self.assertEqual(len(resumo), 1)
        return resumo.iloc[0]

    def test_municipio_sem_exposicao_na_janela(self) -> None:
        row = self._resumo_de("1100015", anos_expostos=set())
        self.assertTrue(row["sem_exposicao_observada_2007_2019"])
        self.assertFalse(row["exposicao_observada_2007_2019"])
        self.assertFalse(row["exposicao_observada_em_2007"])
        self.assertTrue(pd.isna(row["primeiro_ano_exposicao_observada"]))
        self.assertTrue(pd.isna(row["ultimo_ano_exposicao_observada"]))
        self.assertEqual(row["anos_expostos"], "")
        self.assertFalse(row["padrao_intermitente_exposicao_observada"])

    def test_municipio_exposto_desde_2007(self) -> None:
        row = self._resumo_de("1100015", anos_expostos=set(ANOS))
        self.assertTrue(row["exposicao_observada_em_2007"])
        self.assertEqual(int(row["primeiro_ano_exposicao_observada"]), 2007)
        self.assertEqual(int(row["ultimo_ano_exposicao_observada"]), 2019)
        self.assertEqual(int(row["n_anos_com_exposicao_observada"]), 13)
        self.assertFalse(row["padrao_intermitente_exposicao_observada"])

    def test_primeira_exposicao_durante_a_janela(self) -> None:
        anos_expostos = set(range(2011, 2020))  # exposto só a partir de 2011
        row = self._resumo_de("1100015", anos_expostos=anos_expostos)
        self.assertFalse(row["exposicao_observada_em_2007"])
        self.assertEqual(int(row["primeiro_ano_exposicao_observada"]), 2011)
        self.assertFalse(row["padrao_intermitente_exposicao_observada"])

    def test_exposicao_intermitente(self) -> None:
        # Exposto em 2010-2011, lacuna em 2012, exposto novamente em 2013+.
        anos_expostos = {2010, 2011, 2013, 2014, 2015, 2016, 2017, 2018, 2019}
        row = self._resumo_de("1100015", anos_expostos=anos_expostos)
        self.assertEqual(int(row["primeiro_ano_exposicao_observada"]), 2010)
        self.assertEqual(int(row["ultimo_ano_exposicao_observada"]), 2019)
        self.assertTrue(row["padrao_intermitente_exposicao_observada"])

    def test_primeiro_e_ultimo_ano_coerentes_com_anos_expostos(self) -> None:
        row = self._resumo_de("1100015", anos_expostos={2009, 2012, 2015})
        anos = [int(a) for a in row["anos_expostos"].split(";")]
        self.assertEqual(int(row["primeiro_ano_exposicao_observada"]), min(anos))
        self.assertEqual(int(row["ultimo_ano_exposicao_observada"]), max(anos))

    def test_mudanca_do_universo_municipal_entre_anos(self) -> None:
        # Município só aparece no universo a partir de 2013 (ex.: criação
        # territorial) — não deve ser tratado como "sem exposição" nos
        # anos em que nem existia no universo.
        anos_no_universo = list(range(2013, 2020))
        row = self._resumo_de("9999999", anos_expostos={2014, 2015}, anos_no_universo=anos_no_universo)
        self.assertEqual(int(row["n_anos_no_universo"]), 7)
        self.assertFalse(row["presente_nos_13_anos_do_universo"])
        anos_ausentes = [int(a) for a in row["anos_ausentes_do_universo"].split(";")]
        self.assertEqual(anos_ausentes, list(range(2007, 2013)))
        self.assertEqual(int(row["primeiro_ano_exposicao_observada"]), 2014)

    def test_resumo_municipal_tem_o_schema_documentado(self) -> None:
        rows = _municipio_exposto_em("1100015", {2011}) + _municipio_exposto_em("1100023", set())
        painel = _painel_df(rows)
        resumo = cadastro.build_resumo_municipal(painel)
        colunas_esperadas = {
            "codigo_municipio_ibge", "municipio", "uf", "co_uf",
            "primeiro_ano_exposicao_observada", "ultimo_ano_exposicao_observada",
            "n_anos_no_universo", "n_anos_com_exposicao_observada",
            "exposicao_observada_em_2007", "exposicao_observada_2007_2019",
            "sem_exposicao_observada_2007_2019", "presente_nos_13_anos_do_universo",
            "padrao_intermitente_exposicao_observada", "anos_expostos", "anos_ausentes_do_universo",
        }
        self.assertEqual(set(resumo.columns), colunas_esperadas)
        self.assertEqual(len(resumo), 2)
        self.assertEqual(resumo["codigo_municipio_ibge"].nunique(), 2)


class TestValidateResumoMunicipalNegativos(unittest.TestCase):
    def test_falha_se_primeiro_ano_incoerente_com_anos_expostos(self) -> None:
        rows = _municipio_exposto_em("1100015", {2011, 2012})
        painel = _painel_df(rows)
        resumo = cadastro.build_resumo_municipal(painel)
        resumo.loc[0, "primeiro_ano_exposicao_observada"] = 2005  # incoerente com anos_expostos
        with self.assertRaises(ValueError):
            cadastro.validate_resumo_municipal(resumo, painel)

    def test_falha_se_intermitencia_declarada_nao_bater_com_o_painel(self) -> None:
        rows = _municipio_exposto_em("1100015", set(ANOS))  # sem lacuna real
        painel = _painel_df(rows)
        resumo = cadastro.build_resumo_municipal(painel)
        resumo.loc[0, "padrao_intermitente_exposicao_observada"] = True  # falso positivo
        with self.assertRaises(ValueError):
            cadastro.validate_resumo_municipal(resumo, painel)

    def test_falha_se_codigo_municipal_duplicado_no_resumo(self) -> None:
        rows = _municipio_exposto_em("1100015", {2011})
        painel = _painel_df(rows)
        resumo = cadastro.build_resumo_municipal(painel)
        resumo_duplicado = pd.concat([resumo, resumo], ignore_index=True)
        with self.assertRaises(ValueError):
            cadastro.validate_resumo_municipal(resumo_duplicado, painel)


class TestSummarizeObservedExposure(unittest.TestCase):
    def test_sem_exposicao_retorna_campos_nulos(self) -> None:
        resultado = cadastro.summarize_observed_exposure([2007, 2008, 2009], [False, False, False])
        self.assertIsNone(resultado["primeiro_ano_exposicao_observada"])
        self.assertIsNone(resultado["ultimo_ano_exposicao_observada"])
        self.assertEqual(resultado["anos_expostos"], "")
        self.assertFalse(resultado["padrao_intermitente_exposicao_observada"])

    def test_aceita_lista_de_anos_menor_que_13(self) -> None:
        # Ao contrário de summarize_presence_trajectory, não exige 2007-2019 completo.
        resultado = cadastro.summarize_observed_exposure([2015, 2016, 2017], [True, False, True])
        self.assertEqual(resultado["primeiro_ano_exposicao_observada"], 2015)
        self.assertEqual(resultado["ultimo_ano_exposicao_observada"], 2017)
        self.assertTrue(resultado["padrao_intermitente_exposicao_observada"])


if __name__ == "__main__":
    unittest.main()
