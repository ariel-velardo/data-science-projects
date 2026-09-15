"""Testes do calendário territorial município-ano (IBGE/DTB 2007–2019).

Execução:
    .venv\\Scripts\\python.exe -m unittest \
        tests.test_constroi_calendario_territorial_ibge -v

Todos os testes usam dados sintéticos pequenos — nenhum lê os arquivos DTB
reais nem os Parquets do projeto, e nenhum acessa a internet.
"""
from __future__ import annotations

import hashlib
import inspect
import re
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import constroi_calendario_territorial_ibge as cal  # noqa: E402

COD = cal.COD
EXISTIA = cal.EXISTIA
ANOS = list(cal.ANOS_JANELA)

# Esquemas sintéticos equivalentes aos dois formatos reais observados.
ESQ_MUNICIPIO_COMPLETO7 = {
    "nivel": "municipio", "coluna_uf": "UF", "coluna_nome_uf": "Nome_UF",
    "coluna_codigo": "Código Município Completo", "formato_codigo": "completo7",
    "coluna_codigo_parcial": "Município", "coluna_nome_municipio": "Nome_Município",
}
ESQ_DISTRITO_UF5 = {
    "nivel": "distrito", "coluna_uf": "UF", "coluna_nome_uf": "Nome_UF",
    "coluna_codigo": "Município", "formato_codigo": "uf+5",
    "coluna_codigo_parcial": None, "coluna_nome_municipio": "Nome_Município",
}


# ---------------------------------------------------------------------------
# Helpers de dados sintéticos
# ---------------------------------------------------------------------------


def _nome_uf(codigo: str) -> str:
    return cal.UF_CODIGO_PARA_SIGLA_NOME[codigo[:2]][1]


def _raw_municipio(linhas: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"UF": c[:2], "Nome_UF": _nome_uf(c), "Município": c[2:], "Código Município Completo": c,
          "Nome_Município": n} for c, n in linhas],
        dtype=object,
    )


def _raw_distrito(linhas: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"UF": c[:2], "Nome_UF": _nome_uf(c), "Município": c[2:], "Nome_Município": n,
          "Distrito": d, "Nome_Distrito": f"Distrito {d}"} for c, n, d in linhas],
        dtype=object,
    )


def _lista(ano: int, linhas: list[tuple[str, str]]) -> pd.DataFrame:
    return cal.normaliza_lista_anual(_raw_municipio(linhas), ano, ESQ_MUNICIPIO_COMPLETO7)


def _listas(por_ano: dict[int, list[tuple[str, str]]]) -> dict[int, pd.DataFrame]:
    return {ano: _lista(ano, linhas) for ano, linhas in por_ano.items()}


def _proveniencia(anos) -> dict[int, dict[str, str]]:
    return {a: {"versao_fonte": f"DTB {a} sintética", "fonte_ano": f"sintetico://{a}"} for a in anos}


BASE = [("1100015", "Alta Floresta D'Oeste"), ("3515004", "Embu")]


def _cenario_padrao() -> dict[int, pd.DataFrame]:
    """1100015 em todos os anos; 3515004 muda de nome em 2012 (mesmo código);
    4212650 só entra a partir de 2013."""
    por_ano = {}
    for ano in ANOS:
        linhas = [("1100015", "Alta Floresta D'Oeste"),
                  ("3515004", "Embu" if ano < 2012 else "Embu das Artes")]
        if ano >= 2013:
            linhas.append(("4212650", "Pescaria Brava"))
        por_ano[ano] = linhas
    return _listas(por_ano)


# ---------------------------------------------------------------------------
# Código municipal e ano
# ---------------------------------------------------------------------------


class TestCodigoMunicipal(unittest.TestCase):
    def test_codigo_valido(self):
        self.assertEqual(cal.valida_codigo_municipal("4212650"), "4212650")
        self.assertEqual(cal.valida_codigo_municipal("1100015"), "1100015")

    def test_codigo_invalido(self):
        for invalido in ("421265", "42126500", "42126a0", " 4212650", "", None, 4212650, 4212650.0):
            with self.subTest(invalido=invalido):
                with self.assertRaisesRegex(ValueError, "7 dígitos"):
                    cal.valida_codigo_municipal(invalido)

    def test_codigo_invalido_na_planilha_interrompe(self):
        raw = _raw_municipio([("1100015", "A")])
        raw.loc[0, "Código Município Completo"] = "110001"
        with self.assertRaisesRegex(ValueError, "7 dígitos"):
            cal.normaliza_lista_anual(raw, 2014, ESQ_MUNICIPIO_COMPLETO7)

    def test_codigo_5_digitos_invalido_no_formato_uf5(self):
        raw = _raw_distrito([("1100015", "A", "05")])
        raw.loc[0, "Município"] = "0015"
        with self.assertRaisesRegex(ValueError, "5 dígitos"):
            cal.normaliza_lista_anual(raw, 2007, ESQ_DISTRITO_UF5)

    def test_celula_numerica_nao_e_convertida_em_silencio(self):
        raw = _raw_municipio([("1100015", "A")])
        raw.loc[0, "Código Município Completo"] = 1100015.0
        with self.assertRaisesRegex(ValueError, "não textual"):
            cal.normaliza_lista_anual(raw, 2014, ESQ_MUNICIPIO_COMPLETO7)

    def test_prefixo_do_codigo_diverge_da_uf(self):
        raw = _raw_municipio([("4212650", "Pescaria Brava")])
        raw.loc[0, "UF"] = "35"
        raw.loc[0, "Nome_UF"] = "São Paulo"
        with self.assertRaisesRegex(ValueError, "prefixo"):
            cal.normaliza_lista_anual(raw, 2014, ESQ_MUNICIPIO_COMPLETO7)

    def test_codigo_completo_diverge_do_codigo_parcial(self):
        raw = _raw_municipio([("4212650", "Pescaria Brava")])
        raw.loc[0, "Município"] = "12651"
        with self.assertRaisesRegex(ValueError, "diverge de UF"):
            cal.normaliza_lista_anual(raw, 2014, ESQ_MUNICIPIO_COMPLETO7)

    def test_nome_uf_incompativel(self):
        raw = _raw_municipio([("4212650", "Pescaria Brava")])
        raw.loc[0, "Nome_UF"] = "Paraná"
        with self.assertRaisesRegex(ValueError, "Nome_UF"):
            cal.normaliza_lista_anual(raw, 2014, ESQ_MUNICIPIO_COMPLETO7)


class TestAno(unittest.TestCase):
    def test_anos_limite_validos(self):
        self.assertEqual(cal.valida_ano(2007), 2007)
        self.assertEqual(cal.valida_ano(2019), 2019)

    def test_ano_invalido(self):
        for invalido in (2006, 2020, "2013", 2013.0, True, None):
            with self.subTest(invalido=invalido):
                with self.assertRaises(ValueError):
                    cal.valida_ano(invalido)

    def test_ano_invalido_na_normalizacao(self):
        with self.assertRaisesRegex(ValueError, "fora da janela"):
            cal.normaliza_lista_anual(_raw_municipio(BASE), 2020, ESQ_MUNICIPIO_COMPLETO7)

    def test_esquemas_cobrem_exatamente_a_janela(self):
        self.assertEqual(set(cal.ESQUEMAS_DTB), set(cal.ANOS_JANELA))
        self.assertEqual(len(cal.ANOS_JANELA), 13)
        for ano, esquema in cal.ESQUEMAS_DTB.items():
            with self.subTest(ano=ano):
                self.assertRegex(esquema["sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(esquema["tamanho_bytes"], 0)
                self.assertTrue(cal.url_dtb(esquema).startswith(cal.DTB_FTP_BASE + "/"))


# ---------------------------------------------------------------------------
# Schema anual e duplicidade
# ---------------------------------------------------------------------------


class TestSchemaEDuplicidade(unittest.TestCase):
    def test_schema_anual_inesperado(self):
        raw = _raw_municipio(BASE).drop(columns=["Nome_Município"])
        with self.assertRaisesRegex(ValueError, "schema anual inesperado"):
            cal.normaliza_lista_anual(raw, 2015, ESQ_MUNICIPIO_COMPLETO7)

    def test_schema_renomeado_tambem_e_inesperado(self):
        raw = _raw_municipio(BASE).rename(columns={"Código Município Completo": "Cod_Mun"})
        with self.assertRaisesRegex(ValueError, "schema anual inesperado"):
            cal.normaliza_lista_anual(raw, 2015, ESQ_MUNICIPIO_COMPLETO7)

    def test_planilha_vazia(self):
        raw = _raw_municipio(BASE).iloc[0:0]
        with self.assertRaisesRegex(ValueError, "sem linhas"):
            cal.normaliza_lista_anual(raw, 2015, ESQ_MUNICIPIO_COMPLETO7)

    def test_duplicidade_em_lista_municipal(self):
        raw = _raw_municipio([("1100015", "A"), ("1100015", "A")])
        with self.assertRaisesRegex(ValueError, "duplicado"):
            cal.normaliza_lista_anual(raw, 2015, ESQ_MUNICIPIO_COMPLETO7)

    def test_distrito_colapsa_linhas_do_mesmo_municipio(self):
        raw = _raw_distrito([("1100015", "Alta Floresta D'Oeste", "05"),
                             ("1100015", "Alta Floresta D'Oeste", "20"),
                             ("3515004", "Embu", "05")])
        lista = cal.normaliza_lista_anual(raw, 2007, ESQ_DISTRITO_UF5)
        self.assertEqual(lista[COD].tolist(), ["1100015", "3515004"])
        cal.valida_lista_anual(lista, 2007)

    def test_distrito_com_nomes_divergentes_para_o_mesmo_codigo(self):
        raw = _raw_distrito([("1100015", "Alta Floresta D'Oeste", "05"),
                             ("1100015", "Outro Nome", "20")])
        with self.assertRaisesRegex(ValueError, "divergentes para o mesmo código"):
            cal.normaliza_lista_anual(raw, 2007, ESQ_DISTRITO_UF5)

    def test_valida_lista_anual_detecta_duplicidade_codigo_ano(self):
        lista = _lista(2010, BASE)
        duplicada = pd.concat([lista, lista.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicidade de código-ano"):
            cal.valida_lista_anual(duplicada, 2010)

    def test_valida_lista_anual_detecta_ano_errado(self):
        lista = _lista(2010, BASE)
        with self.assertRaisesRegex(ValueError, "diferente de 2011"):
            cal.valida_lista_anual(lista, 2011)

    def test_normalizacao_formato_uf5_monta_codigo_de_7_digitos(self):
        raw = _raw_distrito([("4212650", "Pescaria Brava", "05")])
        lista = cal.normaliza_lista_anual(raw, 2013, ESQ_DISTRITO_UF5)
        self.assertEqual(lista.loc[0, COD], "4212650")
        self.assertEqual(lista.loc[0, "uf_sigla"], "SC")
        self.assertEqual(lista.loc[0, "nome_municipio"], "Pescaria Brava")


# ---------------------------------------------------------------------------
# União, grade e derivação do booleano
# ---------------------------------------------------------------------------


class TestUniaoEGrade(unittest.TestCase):
    def test_uniao_dos_codigos(self):
        listas = {2007: _lista(2007, [("1100015", "A"), ("3515004", "B")]),
                  2008: _lista(2008, [("3515004", "B"), ("4212650", "C")])}
        self.assertEqual(cal.constroi_uniao_codigos(listas), ["1100015", "3515004", "4212650"])

    def test_uniao_sem_listas(self):
        with self.assertRaises(ValueError):
            cal.constroi_uniao_codigos({})

    def test_grade_tem_13_linhas_por_codigo_e_valida(self):
        listas = _cenario_padrao()
        calendario = cal.constroi_calendario(listas, _proveniencia(ANOS))
        cal.valida_calendario(calendario, listas)
        self.assertEqual(len(calendario), 3 * 13)
        self.assertTrue((calendario.groupby(COD).size() == 13).all())
        self.assertEqual(calendario[EXISTIA].dtype, bool)
        self.assertEqual(list(calendario.columns), cal.COLUNAS_CALENDARIO)

    def test_municipio_presente_true_e_ausente_false(self):
        calendario = cal.constroi_calendario(_cenario_padrao(), _proveniencia(ANOS))
        pb = calendario.loc[calendario[COD] == "4212650"].set_index("ano")
        for ano in range(2007, 2013):
            self.assertFalse(pb.at[ano, EXISTIA])
            self.assertTrue(pd.isna(pb.at[ano, "nome_municipio_ano"]))
            self.assertIn("primeira presença na janela: DTB 2013", pb.at[ano, "observacao_territorial"])
        for ano in range(2013, 2020):
            self.assertTrue(pb.at[ano, EXISTIA])
            self.assertEqual(pb.at[ano, "nome_municipio_ano"], "Pescaria Brava")
        self.assertIn("entrada no calendário", pb.at[2013, "observacao_territorial"])

    def test_resultado_vem_da_fonte_e_nao_do_codigo(self):
        """Mesmo código 4212650, fonte sintética diferente -> resultado diferente:
        o calendário não embute a história de Pescaria Brava."""
        por_ano = {ano: BASE + [("4212650", "Pescaria Brava")] for ano in ANOS}
        listas = _listas(por_ano)
        calendario = cal.constroi_calendario(listas, _proveniencia(ANOS))
        cal.valida_calendario(calendario, listas)
        self.assertTrue(calendario.loc[calendario[COD] == "4212650", EXISTIA].all())

    def test_alteracao_de_nome_sem_alteracao_de_codigo(self):
        listas = _cenario_padrao()
        calendario = cal.constroi_calendario(listas, _proveniencia(ANOS))
        cal.valida_calendario(calendario, listas)  # não é erro
        embu = calendario.loc[calendario[COD] == "3515004"].set_index("ano")
        self.assertTrue(embu[EXISTIA].all())
        self.assertEqual(embu.at[2011, "nome_municipio_ano"], "Embu")
        self.assertEqual(embu.at[2012, "nome_municipio_ano"], "Embu das Artes")
        self.assertIn("nome difere da DTB 2011: 'Embu'", embu.at[2012, "observacao_territorial"])
        self.assertTrue(pd.isna(embu.at[2013, "observacao_territorial"]))

        transicoes = cal.constroi_transicoes(listas)
        eventos = transicoes.loc[transicoes["tipo_registro"] == "evento"]
        do_codigo = eventos.loc[eventos[COD] == "3515004"]
        self.assertEqual(do_codigo["tipo_evento"].tolist(), ["mudanca_nome"])
        self.assertEqual(int(do_codigo["ano_evento"].iloc[0]), 2012)
        self.assertFalse(bool(do_codigo["nome_igual_apos_normalizacao"].iloc[0]))

    def test_proveniencia_ausente(self):
        with self.assertRaisesRegex(ValueError, "proveniência ausente"):
            cal.constroi_calendario(_cenario_padrao(), _proveniencia(ANOS[:-1]))


class TestValidaCalendario(unittest.TestCase):
    def setUp(self):
        self.listas = _cenario_padrao()
        self.calendario = cal.constroi_calendario(self.listas, _proveniencia(ANOS))

    def _indice(self, codigo: str, ano: int) -> int:
        return self.calendario.index[(self.calendario[COD] == codigo) & (self.calendario["ano"] == ano)][0]

    def test_true_sem_constar_da_fonte(self):
        listas = dict(self.listas)
        listas[2015] = listas[2015].loc[listas[2015][COD] != "4212650"].reset_index(drop=True)
        with self.assertRaisesRegex(ValueError, "marcado True sem constar da lista oficial DTB 2015"):
            cal.valida_calendario(self.calendario, listas)

    def test_presente_na_fonte_marcado_false(self):
        adulterado = self.calendario.copy()
        i = self._indice("4212650", 2016)
        adulterado.loc[i, EXISTIA] = False
        adulterado.loc[i, "nome_municipio_ano"] = None
        with self.assertRaisesRegex(ValueError, "consta da lista oficial DTB 2016 mas está marcado False"):
            cal.valida_calendario(adulterado, self.listas)

    def test_duplicidade_no_calendario(self):
        duplicado = pd.concat([self.calendario, self.calendario.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicidade"):
            cal.valida_calendario(duplicado, self.listas)

    def test_booleano_nulo(self):
        adulterado = self.calendario.copy()
        adulterado[EXISTIA] = adulterado[EXISTIA].astype(object)
        adulterado.loc[0, EXISTIA] = None
        with self.assertRaisesRegex(ValueError, "contém nulo"):
            cal.valida_calendario(adulterado, self.listas)

    def test_codigo_sem_13_linhas(self):
        incompleto = self.calendario.drop(index=self._indice("1100015", 2019))
        with self.assertRaises(ValueError):
            cal.valida_calendario(incompleto, self.listas)

    def test_codigo_sem_13_linhas_mensagem(self):
        # remove um ano de um código mas mantém o ano coberto por outros códigos
        incompleto = self.calendario.drop(index=self._indice("1100015", 2010))
        with self.assertRaisesRegex(ValueError, "não tem exatamente 13 linhas"):
            cal.valida_calendario(incompleto, self.listas)

    def test_nome_preenchido_para_inexistente(self):
        adulterado = self.calendario.copy()
        adulterado.loc[self._indice("4212650", 2007), "nome_municipio_ano"] = "Pescaria Brava"
        with self.assertRaisesRegex(ValueError, "se e somente se"):
            cal.valida_calendario(adulterado, self.listas)

    def test_calendario_sem_todos_os_anos(self):
        parcial = self.calendario.loc[self.calendario["ano"] != 2019]
        with self.assertRaisesRegex(ValueError, "não cobrem exatamente"):
            cal.valida_calendario(parcial, self.listas)


# ---------------------------------------------------------------------------
# Transições
# ---------------------------------------------------------------------------


class TestTransicoes(unittest.TestCase):
    def test_classes_sem_casos_registram_zero(self):
        transicoes = cal.constroi_transicoes(_cenario_padrao())
        resumo = transicoes.loc[transicoes["tipo_registro"] == "resumo_classe"].set_index("tipo_evento")
        self.assertEqual(set(resumo.index), set(cal.CLASSES_EVENTO))
        self.assertEqual(int(resumo.at["entrada", "n_casos"]), 1)
        self.assertEqual(int(resumo.at["mudanca_nome", "n_casos"]), 1)
        for classe in ("saida", "mudanca_uf", "possivel_mudanca_codigo", "lacuna_intermediaria"):
            self.assertEqual(int(resumo.at[classe, "n_casos"]), 0)
            self.assertIn("zero casos", resumo.at[classe, "observacao"])

    def test_entrada_saida_lacuna_e_possivel_mudanca_de_codigo(self):
        por_ano = {}
        for ano in ANOS:
            linhas = list(BASE)
            if ano <= 2010:
                linhas.append(("4300001", "Velho Codigo"))   # sai em 2011
            else:
                linhas.append(("4300002", "Velho Código"))   # entra em 2011, mesmo nome normalizado
            if ano not in (2014, 2015):
                linhas.append(("2206720", "Nazária"))        # lacuna em 2014–2015
            por_ano[ano] = linhas
        transicoes = cal.constroi_transicoes(_listas(por_ano))
        eventos = transicoes.loc[transicoes["tipo_registro"] == "evento"]
        tipos = eventos.groupby("tipo_evento")[COD].apply(list).to_dict()
        self.assertEqual(sorted(tipos["saida"]), ["2206720", "4300001"])
        self.assertEqual(sorted(tipos["entrada"]), ["2206720", "4300002"])
        self.assertEqual(tipos["possivel_mudanca_codigo"], ["4300001"])
        self.assertEqual(tipos["lacuna_intermediaria"], ["2206720"])

    def test_nome_igual_apos_normalizacao_e_apenas_diagnostico(self):
        por_ano = {ano: [("2917334", "Iuiú" if ano < 2016 else "Iuiu")] for ano in ANOS}
        transicoes = cal.constroi_transicoes(_listas(por_ano))
        evento = transicoes.loc[transicoes["tipo_evento"].eq("mudanca_nome") & transicoes["tipo_registro"].eq("evento")]
        self.assertEqual(len(evento), 1)
        self.assertTrue(bool(evento["nome_igual_apos_normalizacao"].iloc[0]))


# ---------------------------------------------------------------------------
# Reconciliação estrutural (somente diagnóstica)
# ---------------------------------------------------------------------------


class TestReconciliacao(unittest.TestCase):
    def test_reporta_sem_excluir(self):
        calendario = cal.constroi_calendario(_cenario_padrao(), _proveniencia(ANOS))
        grupos = {"g": {"1100015", "4212650", "9999999", "123"}}
        inep = {"1100015": set(), "3515004": set(), "4212650": set(range(2007, 2013))}
        rec = cal.reconcilia_codigos_projeto(calendario, grupos, inep)
        valores = {(r.grupo, r.metrica): r.valor for r in rec.itertuples()}
        self.assertEqual(valores[("g", "n_codigos_unicos")], 4)
        self.assertEqual(valores[("g", "n_codigos_formato_invalido")], 1)
        self.assertEqual(valores[("g", "n_codigos_fora_da_uniao_do_calendario")], 1)
        self.assertEqual(valores[("g", "n_codigos_existentes_nos_13_anos")], 1)
        self.assertEqual(valores[("g", "n_codigos_inexistentes_em_algum_ano")], 1)
        grupo_inep = "cadastro_elegibilidade_controles_anos_ausentes_universo_inep"
        self.assertEqual(valores[(grupo_inep, "n_codigos_anos_ausentes_inep_iguais_anos_inexistentes_calendario")], 3)
        self.assertEqual(valores[(grupo_inep, "n_codigos_divergentes")], 0)
        # a entrada não é modificada
        self.assertEqual(grupos, {"g": {"1100015", "4212650", "9999999", "123"}})


# ---------------------------------------------------------------------------
# Integridade de arquivos (sem rede)
# ---------------------------------------------------------------------------


class _RespostaFalsa:
    def __init__(self, conteudo: bytes):
        self.content = conteudo

    def raise_for_status(self):
        return None


class _SessaoFalsa:
    def __init__(self, conteudo: bytes):
        self.conteudo = conteudo
        self.chamadas = 0

    def get(self, url, timeout=None):
        self.chamadas += 1
        return _RespostaFalsa(self.conteudo)


class TestIntegridadeArquivo(unittest.TestCase):
    def test_sha_correto_e_incorreto(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "x.zip"
            caminho.write_bytes(b"abc")
            sha = hashlib.sha256(b"abc").hexdigest()
            self.assertEqual(cal.verifica_integridade_arquivo(caminho, sha, 3)["sha256"], sha)
            with self.assertRaisesRegex(ValueError, "difere do registrado"):
                cal.verifica_integridade_arquivo(caminho, "0" * 64, 3)

    def test_download_desabilitado_sem_arquivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                cal.garante_arquivo_dtb(2013, destino=Path(tmp), permitir_download=False)

    def test_download_com_conteudo_diferente_nao_grava(self):
        with tempfile.TemporaryDirectory() as tmp:
            sessao = _SessaoFalsa(b"conteudo que nao e a DTB")
            with self.assertRaisesRegex(ValueError, "NÃO gravado"):
                cal.garante_arquivo_dtb(2013, destino=Path(tmp), sessao=sessao)
            self.assertEqual(sessao.chamadas, 1)
            self.assertFalse((Path(tmp) / cal.ESQUEMAS_DTB[2013]["arquivo"]).exists())


class TestSemHistoriaEmbutida(unittest.TestCase):
    def test_construcao_nao_referencia_codigos_ou_contagens_historicas(self):
        """O único código municipal literal do módulo é o do caso de auditoria,
        que não aparece em nenhuma função de construção/validação; contagens
        históricas não aparecem no módulo."""
        fonte = Path(cal.__file__).read_text(encoding="utf-8")
        codigos_literais = set(re.findall(r"\"([0-9]{7})\"", fonte))
        self.assertEqual(codigos_literais, {cal.CASO_AUDITORIA_PESCARIA_BRAVA})
        for funcao in (cal.normaliza_lista_anual, cal.valida_lista_anual, cal.constroi_uniao_codigos,
                       cal.constroi_calendario, cal._observacoes_territoriais, cal.valida_calendario,
                       cal.constroi_transicoes):
            with self.subTest(funcao=funcao.__name__):
                self.assertNotIn("CASO_AUDITORIA_PESCARIA_BRAVA", inspect.getsource(funcao))
                self.assertNotIn(cal.CASO_AUDITORIA_PESCARIA_BRAVA, inspect.getsource(funcao))
        for contagem in ("5564", "5565", "5570", "5.564", "5.565", "5.570"):
            self.assertNotIn(contagem, fonte)


if __name__ == "__main__":
    unittest.main()
