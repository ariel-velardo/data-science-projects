"""Testes da Fase 0 (piloto técnico) do painel CEMPRE município-ano.

Cobre exclusivamente os componentes do piloto descritos em
`docs/data/ESPECIFICACAO_PAINEL_CEMPRE.md` (seção 12): parser de `V`,
normalização da long, reconciliação territorial e validação da chave
canônica. NÃO testa extração nacional nem faz merge causal.

Execução:
    .venv\\Scripts\\python.exe -m unittest tests.test_constroi_painel_cempre -v

Os testes de parser/normalização/reconciliação/validação usam dados
sintéticos ou a fixture real congelada em
`data/raw/ibge/cempre/fixtures/` — nenhum depende de chamada de rede.
Os testes de rede (marcados na classe `TestFetchRequestRede`) usam
mocks; nenhum teste automatizado desta suíte chama a API ao vivo.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import constroi_painel_cempre as cempre  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "ibge" / "cempre" / "fixtures"


def _carrega_fixture(nome: str) -> list[dict]:
    with open(FIXTURES_DIR / nome, encoding="utf-8") as f:
        return json.load(f)


def _escreve_calendario_sintetico(caminho: Path, linhas: list[dict]) -> None:
    pd.DataFrame(linhas).to_parquet(caminho, index=False)


# ---------------------------------------------------------------------------
# parse_sidra_value
# ---------------------------------------------------------------------------


class TestParseSidraValue(unittest.TestCase):
    def test_inteiro(self) -> None:
        status, valor = cempre.parse_sidra_value("183")
        self.assertEqual(status, "observado")
        self.assertEqual(valor, 183.0)

    def test_decimal_ponto(self) -> None:
        status, valor = cempre.parse_sidra_value("188.72")
        self.assertEqual(status, "observado")
        self.assertEqual(valor, 188.72)

    def test_decimal_negativo(self) -> None:
        status, valor = cempre.parse_sidra_value("-12.5")
        self.assertEqual(status, "observado")
        self.assertEqual(valor, -12.5)

    def test_zero_real(self) -> None:
        status, valor = cempre.parse_sidra_value("-")
        self.assertEqual(status, "zero_real")
        self.assertEqual(valor, 0.0)

    def test_zero_arredondado_inteiro(self) -> None:
        status, valor = cempre.parse_sidra_value("0")
        self.assertEqual(status, "zero_arredondado")
        self.assertEqual(valor, 0.0)

    def test_zero_arredondado_vírgula_uma_casa(self) -> None:
        status, valor = cempre.parse_sidra_value("0,0")
        self.assertEqual(status, "zero_arredondado")
        self.assertEqual(valor, 0.0)

    def test_zero_arredondado_vírgula_duas_casas(self) -> None:
        status, valor = cempre.parse_sidra_value("0,00")
        self.assertEqual(status, "zero_arredondado")
        self.assertEqual(valor, 0.0)

    def test_zero_arredondado_ponto_uma_casa(self) -> None:
        status, valor = cempre.parse_sidra_value("0.0")
        self.assertEqual(status, "zero_arredondado")
        self.assertEqual(valor, 0.0)

    def test_zero_arredondado_ponto_duas_casas(self) -> None:
        status, valor = cempre.parse_sidra_value("0.00")
        self.assertEqual(status, "zero_arredondado")
        self.assertEqual(valor, 0.0)

    def test_zero_arredondado_negativo_inteiro(self) -> None:
        status, valor = cempre.parse_sidra_value("-0")
        self.assertEqual(status, "zero_arredondado_negativo")
        self.assertEqual(valor, 0.0)

    def test_zero_arredondado_negativo_vírgula_uma_casa(self) -> None:
        status, valor = cempre.parse_sidra_value("-0,0")
        self.assertEqual(status, "zero_arredondado_negativo")
        self.assertEqual(valor, 0.0)

    def test_zero_arredondado_negativo_vírgula_duas_casas(self) -> None:
        status, valor = cempre.parse_sidra_value("-0,00")
        self.assertEqual(status, "zero_arredondado_negativo")
        self.assertEqual(valor, 0.0)

    def test_sigilo(self) -> None:
        status, valor = cempre.parse_sidra_value("x")
        self.assertEqual(status, "sigilo")
        self.assertIsNone(valor)

    def test_nao_aplicavel(self) -> None:
        status, valor = cempre.parse_sidra_value("..")
        self.assertEqual(status, "nao_aplicavel")
        self.assertIsNone(valor)

    def test_indisponivel(self) -> None:
        status, valor = cempre.parse_sidra_value("...")
        self.assertEqual(status, "indisponivel")
        self.assertIsNone(valor)

    def test_simbolo_desconhecido(self) -> None:
        status, valor = cempre.parse_sidra_value("N/D")
        self.assertEqual(status, "desconhecido")
        self.assertIsNone(valor)

    def test_formato_zero_nao_documentado_e_desconhecido(self) -> None:
        # "0.000" não é um dos literais documentados (0, 0,0, 0,00) — não
        # deve ser silenciosamente aceito como zero.
        status, valor = cempre.parse_sidra_value("0.000")
        self.assertEqual(status, "desconhecido")
        self.assertIsNone(valor)

    def test_preserva_espacos_externos(self) -> None:
        status, valor = cempre.parse_sidra_value("  183  ")
        self.assertEqual(status, "observado")
        self.assertEqual(valor, 183.0)

    # -- Bloqueador 1 (auditoria independente): vírgula em número
    # não-zero é ambígua (decimal vs. separador de milhar) e não é
    # comprovada pelas fixtures reais, que usam ponto. --

    def test_virgula_tres_digitos_e_desconhecida_nao_decimal(self) -> None:
        status, valor = cempre.parse_sidra_value("1,234")
        self.assertEqual(status, "desconhecido")
        self.assertIsNone(valor)

    def test_virgula_uma_casa_no_numero_nao_zero_e_desconhecida(self) -> None:
        status, valor = cempre.parse_sidra_value("12,5")
        self.assertEqual(status, "desconhecido")
        self.assertIsNone(valor)

    def test_ponto_decimal_nao_zero_continua_observado(self) -> None:
        status, valor = cempre.parse_sidra_value("1.234")
        self.assertEqual(status, "observado")
        self.assertEqual(valor, 1.234)

    def test_ponto_decimal_negativo_continua_observado(self) -> None:
        status, valor = cempre.parse_sidra_value("-12.5")
        self.assertEqual(status, "observado")
        self.assertEqual(valor, -12.5)

    def test_valor_bruto_preservado_mesmo_quando_desconhecido(self) -> None:
        # valor_bruto nunca é descartado, mesmo para o caso ambíguo de vírgula.
        linhas = [
            {
                "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "12,5",
                "D1C": "3166600", "D1N": "Serra da Saudade (MG)", "D2C": "708",
                "D2N": "Pessoal ocupado assalariado", "D3C": "2010", "D3N": "2010",
            }
        ]
        df = cempre.normalize_long(linhas, request_id="req_teste_virgula")
        self.assertEqual(df.iloc[0]["valor_bruto"], "12,5")
        self.assertEqual(df.iloc[0]["status_valor_api"], "desconhecido")
        self.assertTrue(cempre.pd.isna(df.iloc[0]["valor_numerico"]))


# ---------------------------------------------------------------------------
# validate_sidra_payload — Bloqueador 2: contrato explícito do payload
# ---------------------------------------------------------------------------


class TestValidateSidraPayload(unittest.TestCase):
    def setUp(self) -> None:
        self.payload_real = _carrega_fixture(
            "tabela_1685_n6_3166600_serra_da_saudade_2007_2008_2009_2018_2019.json"
        )

    def test_payload_real_e_valido(self) -> None:
        valido, motivo = cempre.validate_sidra_payload(self.payload_real)
        self.assertTrue(valido)
        self.assertIsNone(motivo)

    def test_payload_nao_e_lista(self) -> None:
        valido, motivo = cempre.validate_sidra_payload({"erro": "não é lista"})
        self.assertFalse(valido)
        self.assertIsNotNone(motivo)

    def test_lista_vazia(self) -> None:
        valido, motivo = cempre.validate_sidra_payload([])
        self.assertFalse(valido)
        self.assertIn("vazia", motivo)

    def test_lista_apenas_com_cabecalho(self) -> None:
        cabecalho = self.payload_real[0]
        valido, motivo = cempre.validate_sidra_payload([cabecalho])
        self.assertFalse(valido)
        self.assertIn("observação", motivo)

    def test_item_que_nao_e_dicionario(self) -> None:
        valido, motivo = cempre.validate_sidra_payload([self.payload_real[0], "não é um dict"])
        self.assertFalse(valido)
        self.assertIsNotNone(motivo)

    def test_observacao_sem_d1c(self) -> None:
        obs = dict(self.payload_real[1])
        del obs["D1C"]
        valido, motivo = cempre.validate_sidra_payload([self.payload_real[0], obs])
        self.assertFalse(valido)
        self.assertIn("D1C", motivo)

    def test_observacao_sem_d2c(self) -> None:
        obs = dict(self.payload_real[1])
        del obs["D2C"]
        valido, motivo = cempre.validate_sidra_payload([self.payload_real[0], obs])
        self.assertFalse(valido)
        self.assertIn("D2C", motivo)

    def test_observacao_sem_d3c(self) -> None:
        obs = dict(self.payload_real[1])
        del obs["D3C"]
        valido, motivo = cempre.validate_sidra_payload([self.payload_real[0], obs])
        self.assertFalse(valido)
        self.assertIn("D3C", motivo)

    def test_observacao_sem_v(self) -> None:
        obs = dict(self.payload_real[1])
        del obs["V"]
        valido, motivo = cempre.validate_sidra_payload([self.payload_real[0], obs])
        self.assertFalse(valido)
        self.assertIn("V", motivo)


# ---------------------------------------------------------------------------
# normalize_long
# ---------------------------------------------------------------------------


class TestNormalizeLong(unittest.TestCase):
    def setUp(self) -> None:
        self.linhas_serra_saudade = _carrega_fixture(
            "tabela_1685_n6_3166600_serra_da_saudade_2007_2008_2009_2018_2019.json"
        )

    def test_normaliza_fixture_real_preserva_valor_bruto_e_chave(self) -> None:
        df = cempre.normalize_long(self.linhas_serra_saudade, request_id="req_teste_001")
        self.assertGreater(len(df), 0)
        # nenhuma linha de cabeçalho (D1C == "Município (Código)") deve sobrar
        self.assertTrue((df["codigo_municipio_ibge"] == "3166600").all())
        self.assertTrue(df["ano"].between(2007, 2019).all())
        linha_708_2007 = df[(df["ano"] == 2007) & (df["codigo_variavel_sidra"] == 708)].iloc[0]
        self.assertEqual(linha_708_2007["valor_bruto"], "183")
        self.assertEqual(linha_708_2007["valor_numerico"], 183.0)
        self.assertEqual(linha_708_2007["status_valor_api"], "observado")
        self.assertEqual(linha_708_2007["request_id"], "req_teste_001")

    def test_codigo_municipio_invalido_levanta_erro(self) -> None:
        linhas = [
            {
                "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "10",
                "D1C": "31666", "D1N": "Município Inválido", "D2C": "708",
                "D2N": "Pessoal ocupado assalariado", "D3C": "2010", "D3N": "2010",
            }
        ]
        with self.assertRaises(ValueError):
            cempre.normalize_long(linhas, request_id="req_teste_002")

    def test_ano_invalido_levanta_erro(self) -> None:
        linhas = [
            {
                "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "10",
                "D1C": "3166600", "D1N": "Serra da Saudade (MG)", "D2C": "708",
                "D2N": "Pessoal ocupado assalariado", "D3C": "2030", "D3N": "2030",
            }
        ]
        with self.assertRaises(ValueError):
            cempre.normalize_long(linhas, request_id="req_teste_003")

    def test_variavel_invalida_levanta_erro(self) -> None:
        linhas = [
            {
                "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "10",
                "D1C": "3166600", "D1N": "Serra da Saudade (MG)", "D2C": "999999",
                "D2N": "Variável inexistente", "D3C": "2010", "D3N": "2010",
            }
        ]
        with self.assertRaises(ValueError):
            cempre.normalize_long(linhas, request_id="req_teste_004")

    def test_municipio_inexistente_com_reticencias(self) -> None:
        linhas_pescaria = _carrega_fixture(
            "tabela_1685_n6_4212650_pescaria_brava_2007_2013_2019.json"
        )
        df = cempre.normalize_long(linhas_pescaria, request_id="req_teste_005")
        linha_2007 = df[(df["ano"] == 2007) & (df["codigo_variavel_sidra"] == 706)].iloc[0]
        self.assertEqual(linha_2007["valor_bruto"], "...")
        self.assertEqual(linha_2007["status_valor_api"], "indisponivel")
        self.assertTrue(cempre.pd.isna(linha_2007["valor_numerico"]))


# ---------------------------------------------------------------------------
# load_calendar_territorial / reconcile_territorial
# ---------------------------------------------------------------------------


class TestLoadCalendarTerritorial(unittest.TestCase):
    def _linhas_validas(self) -> list[dict]:
        return [
            {
                "codigo_municipio_ibge": "3166600",
                "ano": 2007,
                "municipio_existia_no_ano": True,
                "fonte_territorial": "DTB sintÃ©tica",
            },
            {
                "codigo_municipio_ibge": "4212650",
                "ano": 2007,
                "municipio_existia_no_ano": False,
                "fonte_territorial": "DTB sintÃ©tica",
            },
        ]

    def test_carrega_calendario_parquet_sintetico_valido(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "calendario.parquet"
            _escreve_calendario_sintetico(caminho, self._linhas_validas())

            calendario = cempre.load_calendar_territorial(caminho)

        self.assertEqual(list(calendario["codigo_municipio_ibge"]), ["3166600", "4212650"])
        self.assertTrue(pd.api.types.is_string_dtype(calendario["codigo_municipio_ibge"]))
        self.assertTrue(pd.api.types.is_integer_dtype(calendario["ano"]))
        self.assertTrue(pd.api.types.is_bool_dtype(calendario["municipio_existia_no_ano"]))

    def test_arquivo_ausente_falha_explicitamente(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "inexistente.parquet"
            with self.assertRaisesRegex(FileNotFoundError, "encontrado"):
                cempre.load_calendar_territorial(caminho)

    def test_formato_nao_suportado_falha_explicitamente(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "calendario.csv"
            caminho.write_text("codigo_municipio_ibge,ano,municipio_existia_no_ano\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "formato"):
                cempre.load_calendar_territorial(caminho)

    def test_coluna_estrutural_ausente_falha_explicitamente(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "calendario.parquet"
            linhas = self._linhas_validas()
            for linha in linhas:
                del linha["municipio_existia_no_ano"]
            _escreve_calendario_sintetico(caminho, linhas)
            with self.assertRaisesRegex(ValueError, "coluna"):
                cempre.load_calendar_territorial(caminho)

    def test_codigo_municipal_invalido_falha_explicitamente(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "calendario.parquet"
            linhas = self._linhas_validas()
            linhas[0]["codigo_municipio_ibge"] = "316660"
            _escreve_calendario_sintetico(caminho, linhas)
            with self.assertRaisesRegex(ValueError, "municipal"):
                cempre.load_calendar_territorial(caminho)

    def test_ano_fora_da_janela_falha_explicitamente(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "calendario.parquet"
            linhas = self._linhas_validas()
            linhas[0]["ano"] = 2006
            _escreve_calendario_sintetico(caminho, linhas)
            with self.assertRaisesRegex(ValueError, "ano"):
                cempre.load_calendar_territorial(caminho)

    def test_booleano_territorial_invalido_falha_explicitamente(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "calendario.parquet"
            linhas = self._linhas_validas()
            linhas[0]["municipio_existia_no_ano"] = "sim"
            linhas[1]["municipio_existia_no_ano"] = "nao"
            _escreve_calendario_sintetico(caminho, linhas)
            with self.assertRaisesRegex(ValueError, "booleano"):
                cempre.load_calendar_territorial(caminho)

    def test_chave_duplicada_falha_explicitamente(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "calendario.parquet"
            linhas = self._linhas_validas()
            linhas.append(linhas[0].copy())
            _escreve_calendario_sintetico(caminho, linhas)
            with self.assertRaisesRegex(ValueError, "chave duplicada"):
                cempre.load_calendar_territorial(caminho)

    def test_nulo_estrutural_falha_explicitamente(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "calendario.parquet"
            linhas = self._linhas_validas()
            linhas[0]["municipio_existia_no_ano"] = None
            _escreve_calendario_sintetico(caminho, linhas)
            with self.assertRaisesRegex(ValueError, "nulo"):
                cempre.load_calendar_territorial(caminho)


class TestReconcileTerritorial(unittest.TestCase):
    def setUp(self) -> None:
        self._diretorio_temporario = tempfile.TemporaryDirectory()
        self.addCleanup(self._diretorio_temporario.cleanup)
        caminho = Path(self._diretorio_temporario.name) / "calendario_reconciliacao.parquet"
        _escreve_calendario_sintetico(caminho, [
            {"codigo_municipio_ibge": "3166600", "ano": 2007, "municipio_existia_no_ano": True},
            {"codigo_municipio_ibge": "4212650", "ano": 2007, "municipio_existia_no_ano": False},
            {"codigo_municipio_ibge": "4212650", "ano": 2013, "municipio_existia_no_ano": True},
            {"codigo_municipio_ibge": "3550308", "ano": 2007, "municipio_existia_no_ano": True},
        ])
        self.calendario = cempre.load_calendar_territorial(caminho)

    def test_municipio_existia_no_ano(self) -> None:
        linhas = [
            {
                "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "183",
                "D1C": "3166600", "D1N": "Serra da Saudade (MG)", "D2C": "708",
                "D2N": "Pessoal ocupado assalariado", "D3C": "2007", "D3N": "2007",
            }
        ]
        df = cempre.normalize_long(linhas, request_id="req_teste_010")
        df = cempre.reconcile_territorial(df, self.calendario)
        self.assertEqual(df.iloc[0]["status_territorial"], "existia_no_ano")
        # status_valor_api não deve ser alterado pela reconciliação
        self.assertEqual(df.iloc[0]["status_valor_api"], "observado")

    def test_pescaria_brava_2007_nao_existia_nao_e_incompatibilidade(self) -> None:
        linhas_pescaria = _carrega_fixture(
            "tabela_1685_n6_4212650_pescaria_brava_2007_2013_2019.json"
        )
        df = cempre.normalize_long(linhas_pescaria, request_id="req_teste_011")
        df = cempre.reconcile_territorial(df, self.calendario)
        linha_2007 = df[(df["ano"] == 2007) & (df["codigo_variavel_sidra"] == 706)].iloc[0]
        self.assertEqual(linha_2007["status_valor_api"], "indisponivel")
        self.assertEqual(linha_2007["status_territorial"], "nao_existia_no_ano")
        self.assertFalse(linha_2007["incompatibilidade_territorial"])

    def test_pescaria_brava_2013_existia(self) -> None:
        linhas_pescaria = _carrega_fixture(
            "tabela_1685_n6_4212650_pescaria_brava_2007_2013_2019.json"
        )
        df = cempre.normalize_long(linhas_pescaria, request_id="req_teste_012")
        df = cempre.reconcile_territorial(df, self.calendario)
        linha_2013 = df[(df["ano"] == 2013) & (df["codigo_variavel_sidra"] == 706)].iloc[0]
        self.assertEqual(linha_2013["status_territorial"], "existia_no_ano")

    def test_incompatibilidade_territorial_valor_numerico_para_municipio_inexistente(self) -> None:
        # Caso sintético e adversarial: valor numérico observado para uma
        # chave que o calendário afirma não existir — divergência real,
        # distinta do caso esperado de Pescaria Brava/2007 com "...".
        linhas = [
            {
                "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "50",
                "D1C": "4212650", "D1N": "Pescaria Brava (SC)", "D2C": "708",
                "D2N": "Pessoal ocupado assalariado", "D3C": "2007", "D3N": "2007",
            }
        ]
        df = cempre.normalize_long(linhas, request_id="req_teste_013")
        df = cempre.reconcile_territorial(df, self.calendario)
        linha = df.iloc[0]
        self.assertEqual(linha["status_valor_api"], "observado")
        self.assertEqual(linha["status_territorial"], "nao_existia_no_ano")
        self.assertTrue(linha["incompatibilidade_territorial"])

    def test_codigo_sem_cobertura_no_calendario_e_indeterminado(self) -> None:
        linhas = [
            {
                "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "50",
                "D1C": "3550308", "D1N": "São Paulo (SP)", "D2C": "708",
                "D2N": "Pessoal ocupado assalariado", "D3C": "2007", "D3N": "2007",
            }
        ]
        df = cempre.normalize_long(linhas, request_id="req_teste_014")
        calendario_sem_cobertura = self.calendario[
            self.calendario["codigo_municipio_ibge"] != "3550308"
        ]
        df = cempre.reconcile_territorial(df, calendario_sem_cobertura)
        self.assertEqual(df.iloc[0]["status_territorial"], "indeterminado")


# ---------------------------------------------------------------------------
# validate_long — chave canônica e duplicidade entre request_id
# ---------------------------------------------------------------------------


class TestValidateLongDuplicidade(unittest.TestCase):
    def test_duplicidade_consistente_e_resolvida(self) -> None:
        linhas_a = [
            {
                "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "183",
                "D1C": "3166600", "D1N": "Serra da Saudade (MG)", "D2C": "708",
                "D2N": "Pessoal ocupado assalariado", "D3C": "2007", "D3N": "2007",
            }
        ]
        df_a = cempre.normalize_long(linhas_a, request_id="req_lote_A")
        df_b = cempre.normalize_long(linhas_a, request_id="req_lote_B")
        combinado = cempre.pd.concat([df_a, df_b], ignore_index=True)
        df_validado, relatorio = cempre.validate_long(combinado)
        self.assertEqual(len(df_validado), 1)
        self.assertTrue(relatorio["aprovado"])
        self.assertEqual(len(relatorio["duplicatas_resolvidas"]), 1)

    def test_duplicidade_inconsistente_levanta_erro(self) -> None:
        linhas_a = [
            {
                "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "183",
                "D1C": "3166600", "D1N": "Serra da Saudade (MG)", "D2C": "708",
                "D2N": "Pessoal ocupado assalariado", "D3C": "2007", "D3N": "2007",
            }
        ]
        linhas_b = [
            {
                "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "999",
                "D1C": "3166600", "D1N": "Serra da Saudade (MG)", "D2C": "708",
                "D2N": "Pessoal ocupado assalariado", "D3C": "2007", "D3N": "2007",
            }
        ]
        df_a = cempre.normalize_long(linhas_a, request_id="req_lote_A")
        df_b = cempre.normalize_long(linhas_b, request_id="req_lote_B")
        combinado = cempre.pd.concat([df_a, df_b], ignore_index=True)
        with self.assertRaises(ValueError):
            cempre.validate_long(combinado)

    def test_simbolo_desconhecido_bloqueia_validacao(self) -> None:
        linhas = [
            {
                "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "N/D",
                "D1C": "3166600", "D1N": "Serra da Saudade (MG)", "D2C": "708",
                "D2N": "Pessoal ocupado assalariado", "D3C": "2007", "D3N": "2007",
            }
        ]
        df = cempre.normalize_long(linhas, request_id="req_lote_C")
        df_validado, relatorio = cempre.validate_long(df)
        self.assertFalse(relatorio["aprovado"])
        self.assertIn("desconhecido", relatorio["motivos_bloqueio"][0])


# ---------------------------------------------------------------------------
# build_requests / request_id determinístico
# ---------------------------------------------------------------------------


class TestBuildRequests(unittest.TestCase):
    def test_request_id_determinístico_e_estavel(self) -> None:
        r1 = cempre.build_requests(
            anos=[2007], territorios=[{"tipo": "municipio", "codigo": "3166600"}], variaveis=[706, 708]
        )
        r2 = cempre.build_requests(
            anos=[2007], territorios=[{"tipo": "municipio", "codigo": "3166600"}], variaveis=[706, 708]
        )
        self.assertEqual(r1[0]["request_id"], r2[0]["request_id"])

    def test_request_id_muda_com_parametros(self) -> None:
        r1 = cempre.build_requests(
            anos=[2007], territorios=[{"tipo": "municipio", "codigo": "3166600"}], variaveis=[706]
        )
        r2 = cempre.build_requests(
            anos=[2008], territorios=[{"tipo": "municipio", "codigo": "3166600"}], variaveis=[706]
        )
        self.assertNotEqual(r1[0]["request_id"], r2[0]["request_id"])

    def test_url_uf_usa_sintaxe_in_n3(self) -> None:
        r = cempre.build_requests(anos=[2019], territorios=[{"tipo": "uf", "codigo": "14"}], variaveis=[706])
        self.assertIn("in%20n3%2014", r[0]["url"])


# ---------------------------------------------------------------------------
# fetch_request — mecânica de retry/backoff, sem rede real
# ---------------------------------------------------------------------------


def _payload_valido_minimo() -> list[dict]:
    # [] não é mais um sucesso válido (Bloqueador 2) — os testes de rede
    # que exercitam o caminho de sucesso precisam de um payload real e
    # estruturalmente válido (cabeçalho + 1 observação real).
    return [
        {
            "NC": "Nível Territorial (Código)", "NN": "Nível Territorial",
            "MC": "Unidade de Medida (Código)", "MN": "Unidade de Medida", "V": "Valor",
            "D1C": "Município (Código)", "D1N": "Município",
            "D2C": "Variável (Código)", "D2N": "Variável",
            "D3C": "Ano (Código)", "D3N": "Ano",
        },
        {
            "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": "183",
            "D1C": "3166600", "D1N": "Serra da Saudade (MG)", "D2C": "708",
            "D2N": "Pessoal ocupado assalariado", "D3C": "2007", "D3N": "2007",
        },
    ]


class TestFetchRequestRede(unittest.TestCase):
    def test_sucesso_http_200(self) -> None:
        payload = _payload_valido_minimo()
        spec = {"request_id": "req_x", "url": "https://apisidra.ibge.gov.br/values/fake", "params": {}}
        resposta_mock = mock.Mock()
        resposta_mock.status_code = 200
        resposta_mock.text = json.dumps(payload)
        resposta_mock.json.return_value = payload
        sessao_mock = mock.Mock()
        sessao_mock.get.return_value = resposta_mock
        resultado = cempre.fetch_request(spec, session=sessao_mock, max_retries=3, backoff_base=0.0)
        self.assertEqual(resultado["status_http"], 200)
        self.assertEqual(resultado["resultado"], payload)
        self.assertIsNotNone(resultado["hash_resposta_raw"])

    def test_retry_apos_falha_e_depois_sucesso(self) -> None:
        payload = _payload_valido_minimo()
        spec = {"request_id": "req_y", "url": "https://apisidra.ibge.gov.br/values/fake", "params": {}}
        resposta_falha = mock.Mock()
        resposta_falha.status_code = 500
        resposta_falha.text = "erro"
        resposta_ok = mock.Mock()
        resposta_ok.status_code = 200
        resposta_ok.text = json.dumps(payload)
        resposta_ok.json.return_value = payload
        sessao_mock = mock.Mock()
        sessao_mock.get.side_effect = [resposta_falha, resposta_ok]
        resultado = cempre.fetch_request(spec, session=sessao_mock, max_retries=3, backoff_base=0.0)
        self.assertEqual(resultado["status_http"], 200)
        self.assertIsNotNone(resultado["resultado"])
        self.assertEqual(sessao_mock.get.call_count, 2)

    def test_falha_persistente_apos_limite_de_tentativas(self) -> None:
        spec = {"request_id": "req_z", "url": "https://apisidra.ibge.gov.br/values/fake", "params": {}}
        resposta_falha = mock.Mock()
        resposta_falha.status_code = 500
        resposta_falha.text = "erro"
        sessao_mock = mock.Mock()
        sessao_mock.get.return_value = resposta_falha
        resultado = cempre.fetch_request(spec, session=sessao_mock, max_retries=2, backoff_base=0.0)
        self.assertIsNone(resultado["resultado"])
        self.assertEqual(resultado["status_http"], 500)
        self.assertEqual(sessao_mock.get.call_count, 2)

    def test_payload_real_valido_e_sucesso(self) -> None:
        payload_real = _carrega_fixture(
            "tabela_1685_n6_3166600_serra_da_saudade_2007_2008_2009_2018_2019.json"
        )
        spec = {"request_id": "req_payload_real", "url": "https://apisidra.ibge.gov.br/values/fake", "params": {}}
        resposta_ok = mock.Mock()
        resposta_ok.status_code = 200
        resposta_ok.text = json.dumps(payload_real)
        resposta_ok.json.return_value = payload_real
        sessao_mock = mock.Mock()
        sessao_mock.get.return_value = resposta_ok
        resultado = cempre.fetch_request(spec, session=sessao_mock, max_retries=3, backoff_base=0.0)
        self.assertEqual(resultado["status_http"], 200)
        self.assertIsNotNone(resultado["resultado"])
        self.assertIsNone(resultado["erro"])


class TestFetchRequestSchemaInvalido(unittest.TestCase):
    """Bloqueador 2/8: HTTP 200 com payload estruturalmente inválido nunca
    é sucesso, e uma mudança estrutural permanente não desperdiça retries."""

    def _spec(self) -> dict:
        return {"request_id": "req_schema", "url": "https://apisidra.ibge.gov.br/values/fake", "params": {}}

    def _mock_sessao(self, corpo_json: object) -> mock.Mock:
        resposta = mock.Mock()
        resposta.status_code = 200
        resposta.text = json.dumps(corpo_json)
        resposta.json.return_value = corpo_json
        sessao_mock = mock.Mock()
        sessao_mock.get.return_value = resposta
        return sessao_mock

    def test_lista_vazia_nao_e_sucesso_e_nao_gasta_retries(self) -> None:
        sessao_mock = self._mock_sessao([])
        resultado = cempre.fetch_request(self._spec(), session=sessao_mock, max_retries=3, backoff_base=0.0)
        self.assertIsNone(resultado["resultado"])
        self.assertIsNotNone(resultado["erro"])
        self.assertEqual(sessao_mock.get.call_count, 1)

    def test_lista_so_com_cabecalho_nao_e_sucesso(self) -> None:
        cabecalho = _carrega_fixture(
            "tabela_1685_n6_3166600_serra_da_saudade_2007_2008_2009_2018_2019.json"
        )[0]
        sessao_mock = self._mock_sessao([cabecalho])
        resultado = cempre.fetch_request(self._spec(), session=sessao_mock, max_retries=3, backoff_base=0.0)
        self.assertIsNone(resultado["resultado"])
        self.assertEqual(sessao_mock.get.call_count, 1)

    def test_campo_d1c_ausente_nao_e_sucesso(self) -> None:
        obs = dict(_carrega_fixture(
            "tabela_1685_n6_3166600_serra_da_saudade_2007_2008_2009_2018_2019.json"
        )[1])
        del obs["D1C"]
        sessao_mock = self._mock_sessao([obs])
        resultado = cempre.fetch_request(self._spec(), session=sessao_mock, max_retries=3, backoff_base=0.0)
        self.assertIsNone(resultado["resultado"])
        self.assertEqual(sessao_mock.get.call_count, 1)

    def test_campo_d2c_ausente_nao_e_sucesso(self) -> None:
        obs = dict(_carrega_fixture(
            "tabela_1685_n6_3166600_serra_da_saudade_2007_2008_2009_2018_2019.json"
        )[1])
        del obs["D2C"]
        sessao_mock = self._mock_sessao([obs])
        resultado = cempre.fetch_request(self._spec(), session=sessao_mock, max_retries=3, backoff_base=0.0)
        self.assertIsNone(resultado["resultado"])
        self.assertEqual(sessao_mock.get.call_count, 1)

    def test_campo_d3c_ausente_nao_e_sucesso(self) -> None:
        obs = dict(_carrega_fixture(
            "tabela_1685_n6_3166600_serra_da_saudade_2007_2008_2009_2018_2019.json"
        )[1])
        del obs["D3C"]
        sessao_mock = self._mock_sessao([obs])
        resultado = cempre.fetch_request(self._spec(), session=sessao_mock, max_retries=3, backoff_base=0.0)
        self.assertIsNone(resultado["resultado"])
        self.assertEqual(sessao_mock.get.call_count, 1)

    def test_campo_v_ausente_nao_e_sucesso(self) -> None:
        obs = dict(_carrega_fixture(
            "tabela_1685_n6_3166600_serra_da_saudade_2007_2008_2009_2018_2019.json"
        )[1])
        del obs["V"]
        sessao_mock = self._mock_sessao([obs])
        resultado = cempre.fetch_request(self._spec(), session=sessao_mock, max_retries=3, backoff_base=0.0)
        self.assertIsNone(resultado["resultado"])
        self.assertEqual(sessao_mock.get.call_count, 1)

    def test_payload_nao_e_lista_nao_e_sucesso(self) -> None:
        sessao_mock = self._mock_sessao({"erro": "isso não é uma lista"})
        resultado = cempre.fetch_request(self._spec(), session=sessao_mock, max_retries=3, backoff_base=0.0)
        self.assertIsNone(resultado["resultado"])
        self.assertEqual(sessao_mock.get.call_count, 1)

    def test_json_invalido_tenta_novamente_e_pode_falhar(self) -> None:
        resposta_invalida = mock.Mock()
        resposta_invalida.status_code = 200
        resposta_invalida.text = "{não é json"
        resposta_invalida.json.side_effect = ValueError("Expecting value")
        sessao_mock = mock.Mock()
        sessao_mock.get.return_value = resposta_invalida
        resultado = cempre.fetch_request(self._spec(), session=sessao_mock, max_retries=2, backoff_base=0.0)
        self.assertIsNone(resultado["resultado"])
        self.assertIsNotNone(resultado["erro"])
        self.assertEqual(sessao_mock.get.call_count, 2)

    def test_json_invalido_depois_sucesso_no_retry(self) -> None:
        resposta_invalida = mock.Mock()
        resposta_invalida.status_code = 200
        resposta_invalida.text = "{não é json"
        resposta_invalida.json.side_effect = ValueError("Expecting value")
        payload_real = _carrega_fixture(
            "tabela_1685_n6_3166600_serra_da_saudade_2007_2008_2009_2018_2019.json"
        )
        resposta_ok = mock.Mock()
        resposta_ok.status_code = 200
        resposta_ok.text = json.dumps(payload_real)
        resposta_ok.json.return_value = payload_real
        sessao_mock = mock.Mock()
        sessao_mock.get.side_effect = [resposta_invalida, resposta_ok]
        resultado = cempre.fetch_request(self._spec(), session=sessao_mock, max_retries=3, backoff_base=0.0)
        self.assertIsNotNone(resultado["resultado"])
        self.assertEqual(sessao_mock.get.call_count, 2)


# ---------------------------------------------------------------------------
# Correção focal pós-recheck do binding: variáveis básicas obrigatórias.
#
# A vinculação semântica anterior exigia só `variaveis_payload ⊆
# variaveis_esperadas` — um payload contendo SOMENTE 708 de um grupo de 7
# passava. Estes testes cobrem a regra corrigida (item 6 do pedido): a
# MESMA barreira semântica também precisa ser aplicada em `fetch_request`,
# sobre uma resposta NOVA de rede, ANTES de `save_cached_request`.
# ---------------------------------------------------------------------------


def _linha_payload_binding(codigo: str, ano: int, variavel: int, valor: str = "100") -> dict:
    return {
        "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": valor,
        "D1C": codigo, "D1N": "Município Teste", "D2C": variavel,
        "D2N": "Variável Teste", "D3C": ano, "D3N": str(ano),
    }


class TestFetchRequestVinculacaoSemanticaVariaveis(unittest.TestCase):
    def _spec_nacional(self, variaveis: set[int] | list[int] | None = None) -> dict:
        variaveis_ordenadas = sorted(cempre.VARIAVEIS_ESPERADAS if variaveis is None else variaveis)
        return {
            "request_id": "req_binding_var",
            "url": "https://apisidra.ibge.gov.br/values/fake",
            "params": {},
            "ano": 2010,
            "territorio": {"tipo": "municipio", "codigo": "3166600"},
            "variaveis": variaveis_ordenadas,
            "fonte_tabela": cempre.FONTE_TABELA,
        }

    def _mock_sessao(self, payload: list[dict]) -> mock.Mock:
        resposta = mock.Mock()
        resposta.status_code = 200
        resposta.text = json.dumps(payload)
        resposta.json.return_value = payload
        sessao_mock = mock.Mock()
        sessao_mock.get.return_value = resposta
        return sessao_mock

    def test_resposta_nova_com_payload_parcial_nao_e_sucesso_e_nao_cria_cache(self) -> None:
        spec = self._spec_nacional()
        payload_parcial = [_linha_payload_binding("3166600", 2010, 708, "100")]
        sessao_mock = self._mock_sessao(payload_parcial)
        with tempfile.TemporaryDirectory() as diretorio:
            cache_dir = Path(diretorio)
            resultado = cempre.fetch_request(
                spec, session=sessao_mock, cache_dir=cache_dir, max_retries=3, backoff_base=0.0,
            )
            self.assertIsNone(resultado["resultado"])
            self.assertIsNotNone(resultado["erro"])
            self.assertIn("obrigat", resultado["erro"])
            self.assertFalse(cempre.cache_path_for_request(spec["request_id"], cache_dir).exists())
        self.assertEqual(sessao_mock.get.call_count, 1)

    def test_resposta_nova_valida_sem_1606_e_sucesso_e_pode_persistir_cache(self) -> None:
        spec = self._spec_nacional()
        payload_sem_1606 = [
            _linha_payload_binding("3166600", 2010, variavel, "100")
            for variavel in sorted(cempre.VARIAVEIS_OBRIGATORIAS)
        ]
        sessao_mock = self._mock_sessao(payload_sem_1606)
        with tempfile.TemporaryDirectory() as diretorio:
            cache_dir = Path(diretorio)
            resultado = cempre.fetch_request(
                spec, session=sessao_mock, cache_dir=cache_dir, max_retries=3, backoff_base=0.0,
            )
            self.assertIsNone(resultado["erro"])
            self.assertIsNotNone(resultado["resultado"])
            self.assertTrue(cempre.cache_path_for_request(spec["request_id"], cache_dir).exists())
        self.assertEqual(sessao_mock.get.call_count, 1)


# ---------------------------------------------------------------------------
# Cache/reprocessamento — Bloqueador 3
# ---------------------------------------------------------------------------


class TestCacheReprocessamento(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self._tmpdir.name)
        self.payload_real = _carrega_fixture(
            "tabela_1685_n6_3166600_serra_da_saudade_2007_2008_2009_2018_2019.json"
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _mock_sessao_sucesso(self) -> mock.Mock:
        resposta_ok = mock.Mock()
        resposta_ok.status_code = 200
        resposta_ok.text = json.dumps(self.payload_real)
        resposta_ok.json.return_value = self.payload_real
        sessao_mock = mock.Mock()
        sessao_mock.get.return_value = resposta_ok
        return sessao_mock

    def test_primeira_execucao_cache_miss_cria_cache(self) -> None:
        spec = {"request_id": "req_cache_001", "url": "https://apisidra.ibge.gov.br/values/fake", "params": {}}
        sessao_mock = self._mock_sessao_sucesso()
        resultado = cempre.fetch_request(spec, session=sessao_mock, cache_dir=self.cache_dir, backoff_base=0.0)
        self.assertEqual(sessao_mock.get.call_count, 1)
        self.assertIsNotNone(resultado["resultado"])
        self.assertTrue(cempre.cache_path_for_request("req_cache_001", self.cache_dir).exists())

    def test_segunda_execucao_cache_hit_zero_chamadas_de_rede(self) -> None:
        spec = {"request_id": "req_cache_002", "url": "https://apisidra.ibge.gov.br/values/fake", "params": {}}
        sessao_mock_1 = self._mock_sessao_sucesso()
        resultado_1 = cempre.fetch_request(spec, session=sessao_mock_1, cache_dir=self.cache_dir, backoff_base=0.0)

        sessao_mock_2 = mock.Mock()
        sessao_mock_2.get.side_effect = AssertionError("rede não deveria ser chamada em cache hit")
        resultado_2 = cempre.fetch_request(spec, session=sessao_mock_2, cache_dir=self.cache_dir, backoff_base=0.0)

        self.assertEqual(sessao_mock_2.get.call_count, 0)
        self.assertTrue(resultado_2.get("de_cache"))
        self.assertEqual(resultado_2["resultado"], resultado_1["resultado"])

    def test_cache_com_json_invalido_falha_explicitamente(self) -> None:
        request_id = "req_cache_corrompido"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cempre.cache_path_for_request(request_id, self.cache_dir).write_text("{ isso não é json", encoding="utf-8")
        spec = {"request_id": request_id, "url": "https://apisidra.ibge.gov.br/values/fake", "params": {}}
        sessao_mock = mock.Mock()
        sessao_mock.get.side_effect = AssertionError("cache corrompido não deve cair para rede silenciosamente")
        resultado = cempre.fetch_request(spec, session=sessao_mock, cache_dir=self.cache_dir, backoff_base=0.0)
        self.assertIsNone(resultado["resultado"])
        self.assertIsNotNone(resultado["erro"])
        self.assertEqual(sessao_mock.get.call_count, 0)

    def test_cache_com_schema_invalido_nao_e_aceito(self) -> None:
        request_id = "req_cache_schema_invalido"
        texto_lista_vazia = json.dumps([])
        cempre.save_cached_request(
            request_id,
            texto_resposta_raw=texto_lista_vazia,
            hash_resposta_raw=cempre.hashlib.sha256(texto_lista_vazia.encode("utf-8")).hexdigest(),
            cache_dir=self.cache_dir,
        )
        spec = {"request_id": request_id, "url": "https://apisidra.ibge.gov.br/values/fake", "params": {}}
        sessao_mock = mock.Mock()
        sessao_mock.get.side_effect = AssertionError("payload em cache com schema inválido não deve chamar rede")
        resultado = cempre.fetch_request(spec, session=sessao_mock, cache_dir=self.cache_dir, backoff_base=0.0)
        self.assertIsNone(resultado["resultado"])
        self.assertIsNotNone(resultado["erro"])
        self.assertEqual(sessao_mock.get.call_count, 0)

    def test_request_id_diferente_nao_reutiliza_cache(self) -> None:
        spec_a = {"request_id": "req_cache_A", "url": "https://apisidra.ibge.gov.br/values/fake", "params": {}}
        sessao_mock_a = self._mock_sessao_sucesso()
        cempre.fetch_request(spec_a, session=sessao_mock_a, cache_dir=self.cache_dir, backoff_base=0.0)

        spec_b = {"request_id": "req_cache_B", "url": "https://apisidra.ibge.gov.br/values/fake", "params": {}}
        sessao_mock_b = self._mock_sessao_sucesso()
        resultado_b = cempre.fetch_request(spec_b, session=sessao_mock_b, cache_dir=self.cache_dir, backoff_base=0.0)

        self.assertEqual(sessao_mock_b.get.call_count, 1)
        self.assertFalse(resultado_b.get("de_cache", False))

    def test_load_cached_request_retorna_none_em_cache_miss(self) -> None:
        self.assertIsNone(cempre.load_cached_request("request_inexistente", self.cache_dir))


# ---------------------------------------------------------------------------
# validate_cross_measures — validações cruzadas reproduzíveis
# ---------------------------------------------------------------------------


class TestValidateCrossMeasures(unittest.TestCase):
    def _linha(self, codigo: str, ano: int, variavel: int, valor: str, request_id: str = "req_cross") -> dict:
        return {
            "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": valor,
            "D1C": codigo, "D1N": "Município Teste", "D2C": variavel,
            "D2N": "Variável Teste", "D3C": ano, "D3N": str(ano),
        }

    def test_caso_coerente_sem_violacoes(self) -> None:
        linhas = [
            self._linha("3166600", 2019, 707, "226"),
            self._linha("3166600", 2019, 708, "210"),
            self._linha("3166600", 2019, 706, "16"),
        ]
        df = cempre.normalize_long(linhas, request_id="req_cross_ok")
        violacoes = cempre.validate_cross_measures(df)
        self.assertEqual(len(violacoes), 0)

    def test_assalariado_maior_que_total_e_violacao(self) -> None:
        linhas = [
            self._linha("3166600", 2019, 707, "100"),
            self._linha("3166600", 2019, 708, "150"),
        ]
        df = cempre.normalize_long(linhas, request_id="req_cross_bad")
        violacoes = cempre.validate_cross_measures(df)
        self.assertEqual(len(violacoes), 1)
        self.assertIn("pessoal_ocupado_assalariado", violacoes.iloc[0]["regra_violada"])

    def test_valor_negativo_e_violacao(self) -> None:
        linhas = [self._linha("3166600", 2019, 10143, "-12.5")]
        df = cempre.normalize_long(linhas, request_id="req_cross_negativo")
        violacoes = cempre.validate_cross_measures(df)
        self.assertEqual(len(violacoes), 1)
        self.assertIn("salario_medio_reais_nominal", violacoes.iloc[0]["regra_violada"])

    def test_sigilo_nao_gera_falsa_violacao(self) -> None:
        linhas = [
            self._linha("3166600", 2019, 707, "x"),
            self._linha("3166600", 2019, 708, "150"),
        ]
        df = cempre.normalize_long(linhas, request_id="req_cross_sigilo")
        violacoes = cempre.validate_cross_measures(df)
        self.assertEqual(len(violacoes), 0)


# ---------------------------------------------------------------------------
# D1 — plano nacional de requests e contrato de completude (offline)
# ---------------------------------------------------------------------------


_UFS_CONTRATADAS_SINTETICAS = [
    ("11", "RO"), ("12", "AC"), ("13", "AM"), ("14", "RR"),
    ("15", "PA"), ("16", "AP"), ("17", "TO"), ("21", "MA"),
    ("22", "PI"), ("23", "CE"), ("24", "RN"), ("25", "PB"),
    ("26", "PE"), ("27", "AL"), ("28", "SE"), ("29", "BA"),
    ("31", "MG"), ("32", "ES"), ("33", "RJ"), ("35", "SP"),
    ("41", "PR"), ("42", "SC"), ("43", "RS"), ("50", "MS"),
    ("51", "MT"), ("52", "GO"), ("53", "DF"),
]


class TestPlanoNacionalRequests(unittest.TestCase):
    def setUp(self) -> None:
        self.calendario_sintetico = pd.DataFrame(
            [{"uf_codigo": codigo, "uf_sigla": sigla} for codigo, sigla in _UFS_CONTRATADAS_SINTETICAS]
        )
        self.ufs_esperadas = cempre.uf_list_from_calendario(self.calendario_sintetico)
        self.plano = cempre.build_national_request_plan(calendario=self.calendario_sintetico)

    def _validar(self, plano: list[dict] | None = None) -> dict:
        return cempre.validate_national_request_plan(
            self.plano if plano is None else plano,
            ufs_esperadas=self.ufs_esperadas,
        )

    def test_plano_nacional_e_deterministico(self) -> None:
        segundo_plano = cempre.build_national_request_plan(calendario=self.calendario_sintetico.sample(frac=1))
        self.assertEqual(self.plano, segundo_plano)

    def test_duas_construcoes_equivalentes_tem_mesmos_request_ids(self) -> None:
        segundo_plano = cempre.build_national_request_plan(calendario=self.calendario_sintetico.copy())
        self.assertEqual(
            [item["request_id"] for item in self.plano],
            [item["request_id"] for item in segundo_plano],
        )

    def test_request_ids_sao_unicos(self) -> None:
        request_ids = [item["request_id"] for item in self.plano]
        self.assertEqual(len(request_ids), len(set(request_ids)))

    def test_plano_contem_todos_os_anos_contratados(self) -> None:
        self.assertEqual({item["ano"] for item in self.plano}, set(range(2007, 2020)))

    def test_plano_cobre_exatamente_as_ufs_da_referencia_externa(self) -> None:
        self._validar()
        self.assertEqual(
            {item["territorio"]["codigo"] for item in self.plano},
            {item["codigo"] for item in self.ufs_esperadas},
        )

    def test_plano_usa_grupo_de_variaveis_contratado(self) -> None:
        self.assertEqual({tuple(item["variaveis"]) for item in self.plano}, {tuple(sorted(cempre.VARIAVEIS_ESPERADAS))})

    def test_total_esperado_e_derivado_do_contrato_atual(self) -> None:
        relatorio = self._validar()
        self.assertEqual(relatorio["total_requests_esperados"], 13 * 27 * 1)
        self.assertEqual(len(self.plano), relatorio["total_requests_esperados"])

    def test_referencia_externa_precisa_ter_27_ufs(self) -> None:
        with self.assertRaisesRegex(ValueError, "27 UFs"):
            cempre.validate_national_request_plan(self.plano, ufs_esperadas=self.ufs_esperadas[:-1])

    def test_referencia_externa_com_codigo_duplicado_falha(self) -> None:
        referencia_duplicada = [dict(uf) for uf in self.ufs_esperadas]
        referencia_duplicada[-1]["codigo"] = referencia_duplicada[0]["codigo"]
        with self.assertRaisesRegex(ValueError, "duplicado"):
            cempre.validate_national_request_plan(self.plano, ufs_esperadas=referencia_duplicada)

    def test_combinacao_uf_ano_ausente_falha(self) -> None:
        plano_incompleto = self.plano[1:]
        with self.assertRaisesRegex(ValueError, "ausente"):
            self._validar(plano_incompleto)

    def test_uf_inteira_ausente_falha(self) -> None:
        plano_sem_uf = [item for item in self.plano if item["territorio"]["codigo"] != "11"]
        with self.assertRaisesRegex(ValueError, "ausente"):
            self._validar(plano_sem_uf)

    def test_uf_inesperada_falha(self) -> None:
        request_inesperado = dict(self.plano[0])
        request_inesperado["request_id"] = "request_uf_inesperada"
        request_inesperado["territorio"] = {"tipo": "uf", "codigo": "99", "sigla": "ZZ"}
        with self.assertRaisesRegex(ValueError, "fora do contrato"):
            self._validar(self.plano + [request_inesperado])

    def test_grupo_de_variaveis_divergente_falha(self) -> None:
        request_divergente = dict(self.plano[0])
        request_divergente["variaveis"] = [706, 707]
        with self.assertRaisesRegex(ValueError, "grupo de variáveis"):
            self._validar([request_divergente] + self.plano[1:])

    def test_combinacao_duplicada_falha(self) -> None:
        duplicado = dict(self.plano[0])
        duplicado["request_id"] = "request_combinacao_duplicada"
        with self.assertRaisesRegex(ValueError, "combinação.*duplicada"):
            self._validar(self.plano + [duplicado])

    def test_request_id_duplicado_falha(self) -> None:
        with self.assertRaisesRegex(ValueError, "request_id duplicado"):
            self._validar(self.plano + [dict(self.plano[0])])

    def test_ano_fora_do_contrato_falha(self) -> None:
        request_fora_do_ano = dict(self.plano[0])
        request_fora_do_ano["request_id"] = "request_ano_fora"
        request_fora_do_ano["ano"] = 2006
        with self.assertRaisesRegex(ValueError, "ano fora"):
            self._validar(self.plano + [request_fora_do_ano])


class TestCompletudePlanoNacional(unittest.TestCase):
    def setUp(self) -> None:
        calendario_sintetico = pd.DataFrame(
            [{"uf_codigo": codigo, "uf_sigla": sigla} for codigo, sigla in _UFS_CONTRATADAS_SINTETICAS]
        )
        self.plano = cempre.build_national_request_plan(calendario=calendario_sintetico)

    def _resultados_validos(self) -> list[dict]:
        return [
            {"request_id": item["request_id"], "erro": None, "resultado": {"valido": True}, "de_cache": False}
            for item in self.plano
        ]

    def test_todos_os_resultados_validos_completam_o_plano(self) -> None:
        relatorio = cempre.avalia_completude_plano(self.plano, self._resultados_validos())
        self.assertTrue(relatorio["completo"])
        self.assertEqual(relatorio["n_requests_esperados"], len(self.plano))
        self.assertEqual(relatorio["n_sucessos"], len(self.plano))
        self.assertEqual(relatorio["n_falhas"], 0)

    def test_request_esperado_ausente_impede_completude(self) -> None:
        relatorio = cempre.avalia_completude_plano(self.plano, self._resultados_validos()[1:])
        self.assertFalse(relatorio["completo"])
        self.assertEqual(len(relatorio["request_ids_ausentes"]), 1)
        self.assertEqual(relatorio["n_sucessos"], len(self.plano) - 1)

    def test_resultado_com_erro_impede_completude(self) -> None:
        resultados = self._resultados_validos()
        resultados[0]["erro"] = "HTTP 500"
        resultados[0]["resultado"] = None
        relatorio = cempre.avalia_completude_plano(self.plano, resultados)
        self.assertFalse(relatorio["completo"])
        self.assertEqual(relatorio["n_falhas"], 1)

    def test_resultado_nulo_impede_completude(self) -> None:
        resultados = self._resultados_validos()
        resultados[0]["resultado"] = None
        relatorio = cempre.avalia_completude_plano(self.plano, resultados)
        self.assertFalse(relatorio["completo"])
        self.assertEqual(relatorio["n_falhas"], 1)

    def test_resultado_inesperado_e_sinalizado(self) -> None:
        resultados = self._resultados_validos() + [
            {"request_id": "request_inesperado", "erro": None, "resultado": {"valido": True}}
        ]
        relatorio = cempre.avalia_completude_plano(self.plano, resultados)
        self.assertFalse(relatorio["completo"])
        self.assertEqual(relatorio["request_ids_inesperados"], ["request_inesperado"])

    def test_resultado_duplicado_e_sinalizado(self) -> None:
        resultados = self._resultados_validos() + [dict(self._resultados_validos()[0])]
        relatorio = cempre.avalia_completude_plano(self.plano, resultados)
        self.assertFalse(relatorio["completo"])
        self.assertEqual(relatorio["request_ids_duplicados"], [self.plano[0]["request_id"]])
        self.assertEqual(relatorio["n_sucessos"], len(self.plano) - 1)
        self.assertEqual(relatorio["n_falhas"], 1)

    def test_cache_hit_valido_conta_como_sucesso(self) -> None:
        resultados = self._resultados_validos()
        resultados[0]["de_cache"] = True
        relatorio = cempre.avalia_completude_plano(self.plano, resultados)
        self.assertTrue(relatorio["completo"])
        self.assertEqual(relatorio["n_sucessos"], len(self.plano))

    def test_resultado_sem_request_id_e_malformado_controladamente(self) -> None:
        resultados = self._resultados_validos() + [{"erro": None, "resultado": {"valido": True}}]
        relatorio = cempre.avalia_completude_plano(self.plano, resultados)
        self.assertFalse(relatorio["completo"])
        self.assertEqual(len(relatorio["resultados_malformados"]), 1)


# ---------------------------------------------------------------------------
# D2 — persistência e reconstrução offline da long CEMPRE
#
# Deliberadamente NÃO usa o plano nacional de 351 requests: planos
# pequenos e sintéticos são suficientes para exercitar o contrato de
# `load_results_from_cache`/`build_long_from_results`/`rebuild_long_from_cache`,
# que dependem apenas do plano recebido (seção 11 do pedido). Nenhum teste
# desta seção chama rede.
# ---------------------------------------------------------------------------


def _linha_payload_d2(codigo: str, ano: int, variavel: int, valor: str) -> dict:
    return {
        "NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas", "V": valor,
        "D1C": codigo, "D1N": "Município Teste", "D2C": variavel,
        "D2N": "Variável Teste", "D3C": ano, "D3N": str(ano),
    }


def _plano_pequeno_d2() -> list[dict]:
    return [
        {
            "request_id": "req_d2_zzz", "url": "https://apisidra.ibge.gov.br/values/fake_zzz",
            "params": {}, "ano": 2010, "territorio": {"tipo": "municipio", "codigo": "3166600"},
            "variaveis": [708], "fonte_tabela": cempre.FONTE_TABELA,
        },
        {
            "request_id": "req_d2_aaa", "url": "https://apisidra.ibge.gov.br/values/fake_aaa",
            "params": {}, "ano": 2007, "territorio": {"tipo": "municipio", "codigo": "1100015"},
            "variaveis": [708], "fonte_tabela": cempre.FONTE_TABELA,
        },
    ]


def _calendario_d2() -> pd.DataFrame:
    linhas = [
        {"codigo_municipio_ibge": codigo, "ano": ano, "municipio_existia_no_ano": True}
        for codigo in ("3166600", "1100015")
        for ano in range(2007, 2020)
    ]
    return pd.DataFrame(linhas)


def _salva_cache_valido_d2(cache_dir: Path, request_id: str, payload: list[dict]) -> None:
    texto = json.dumps(payload)
    hash_resposta = cempre.hashlib.sha256(texto.encode("utf-8")).hexdigest()
    cempre.save_cached_request(request_id, texto_resposta_raw=texto, hash_resposta_raw=hash_resposta, cache_dir=cache_dir)


class TestLoadResultsFromCache(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.cache_dir = Path(self._tmpdir.name)
        self.plano = _plano_pequeno_d2()

    def test_cache_valido_e_carregado_offline(self) -> None:
        payload = [_linha_payload_d2("3166600", 2010, 708, "100")]
        _salva_cache_valido_d2(self.cache_dir, "req_d2_zzz", payload)
        resultados = cempre.load_results_from_cache([self.plano[0]], self.cache_dir)
        self.assertEqual(len(resultados), 1)
        resultado = resultados[0]
        self.assertIsNone(resultado["erro"])
        self.assertTrue(resultado["de_cache"])
        self.assertEqual(resultado["resultado"], payload)
        self.assertIsNotNone(resultado["hash_resposta_raw"])

    def test_cache_ausente_e_falha_explicita_no_resultado(self) -> None:
        resultados = cempre.load_results_from_cache([self.plano[0]], self.cache_dir)
        resultado = resultados[0]
        self.assertIsNone(resultado["resultado"])
        self.assertIsNotNone(resultado["erro"])
        self.assertTrue(resultado["de_cache"])

    def test_cache_corrompido_e_falha_explicita(self) -> None:
        cempre.cache_path_for_request("req_d2_zzz", self.cache_dir).parent.mkdir(parents=True, exist_ok=True)
        cempre.cache_path_for_request("req_d2_zzz", self.cache_dir).write_text("{ isso não é json", encoding="utf-8")
        resultados = cempre.load_results_from_cache([self.plano[0]], self.cache_dir)
        resultado = resultados[0]
        self.assertIsNone(resultado["resultado"])
        self.assertIsNotNone(resultado["erro"])

    def test_payload_em_cache_com_schema_invalido_nao_passa(self) -> None:
        texto_lista_vazia = json.dumps([])
        cempre.save_cached_request(
            "req_d2_zzz",
            texto_resposta_raw=texto_lista_vazia,
            hash_resposta_raw=cempre.hashlib.sha256(texto_lista_vazia.encode("utf-8")).hexdigest(),
            cache_dir=self.cache_dir,
        )
        resultados = cempre.load_results_from_cache([self.plano[0]], self.cache_dir)
        resultado = resultados[0]
        self.assertIsNone(resultado["resultado"])
        self.assertIsNotNone(resultado["erro"])

    def test_load_results_from_cache_nunca_chama_fetch_request(self) -> None:
        with mock.patch.object(cempre, "fetch_request", side_effect=AssertionError("não deve ser chamado")):
            cempre.load_results_from_cache(self.plano, self.cache_dir)


class TestBuildLongFromResults(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.cache_dir = Path(self._tmpdir.name)
        self.plano = _plano_pequeno_d2()
        self.calendario = _calendario_d2()
        _salva_cache_valido_d2(self.cache_dir, "req_d2_zzz", [_linha_payload_d2("3166600", 2010, 708, "100")])
        _salva_cache_valido_d2(self.cache_dir, "req_d2_aaa", [_linha_payload_d2("1100015", 2007, 708, "150")])

    def test_plano_completo_mais_caches_validos_constroi_long(self) -> None:
        resultados = cempre.load_results_from_cache(self.plano, self.cache_dir)
        long_construida = cempre.build_long_from_results(self.plano, resultados, self.calendario)
        self.assertEqual(len(long_construida), 2)
        self.assertTrue({"status_territorial", "incompatibilidade_territorial"} <= set(long_construida.columns))

    def test_plano_incompleto_falha_ao_construir_long_completa(self) -> None:
        resultados = cempre.load_results_from_cache([self.plano[0]], self.cache_dir)
        with self.assertRaisesRegex(ValueError, "incompleto"):
            cempre.build_long_from_results(self.plano, resultados, self.calendario)

    def test_resultado_com_erro_falha_ao_construir_long_completa(self) -> None:
        resultados = cempre.load_results_from_cache(self.plano, self.cache_dir)
        resultados[0]["erro"] = "HTTP 500"
        resultados[0]["resultado"] = None
        with self.assertRaisesRegex(ValueError, "incompleto"):
            cempre.build_long_from_results(self.plano, resultados, self.calendario)

    def test_normalize_long_recebe_request_id_e_hash_corretos(self) -> None:
        resultados = cempre.load_results_from_cache(self.plano, self.cache_dir)
        long_construida = cempre.build_long_from_results(self.plano, resultados, self.calendario)
        resultados_por_id = {r["request_id"]: r for r in resultados}
        for _, linha in long_construida.iterrows():
            resultado_esperado = resultados_por_id[linha["request_id"]]
            self.assertEqual(linha["hash_resposta_raw"], resultado_esperado["hash_resposta_raw"])

    def test_validate_long_continua_sendo_aplicado(self) -> None:
        _salva_cache_valido_d2(self.cache_dir, "req_d2_zzz", [_linha_payload_d2("3166600", 2010, 708, "N/D")])
        resultados = cempre.load_results_from_cache(self.plano, self.cache_dir)
        with self.assertRaisesRegex(ValueError, "validate_long"):
            cempre.build_long_from_results(self.plano, resultados, self.calendario)

    def test_reconciliacao_territorial_esta_presente(self) -> None:
        resultados = cempre.load_results_from_cache(self.plano, self.cache_dir)
        long_construida = cempre.build_long_from_results(self.plano, resultados, self.calendario)
        self.assertTrue((long_construida["status_territorial"] == "existia_no_ano").all())
        self.assertFalse(long_construida["incompatibilidade_territorial"].any())

    def test_ordem_da_long_e_deterministica(self) -> None:
        resultados = cempre.load_results_from_cache(self.plano, self.cache_dir)
        long_a = cempre.build_long_from_results(self.plano, resultados, self.calendario)
        long_b = cempre.build_long_from_results(list(reversed(self.plano)), list(reversed(resultados)), self.calendario)
        pd.testing.assert_frame_equal(
            long_a.reset_index(drop=True), long_b.reset_index(drop=True), check_dtype=False,
        )
        self.assertEqual(long_a.iloc[0]["codigo_municipio_ibge"], "1100015")
        self.assertEqual(long_a.iloc[1]["codigo_municipio_ibge"], "3166600")

    def test_build_long_from_results_nunca_chama_fetch_request(self) -> None:
        resultados = cempre.load_results_from_cache(self.plano, self.cache_dir)
        with mock.patch.object(cempre, "fetch_request", side_effect=AssertionError("não deve ser chamado")):
            cempre.build_long_from_results(self.plano, resultados, self.calendario)


class TestPersistenciaLongParquet(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.diretorio = Path(self._tmpdir.name)
        cache_dir = self.diretorio / "cache"
        self.plano = _plano_pequeno_d2()
        self.calendario = _calendario_d2()
        _salva_cache_valido_d2(cache_dir, "req_d2_zzz", [_linha_payload_d2("3166600", 2010, 708, "100")])
        _salva_cache_valido_d2(cache_dir, "req_d2_aaa", [_linha_payload_d2("1100015", 2007, 708, "150")])
        resultados = cempre.load_results_from_cache(self.plano, cache_dir)
        self.long_valida = cempre.build_long_from_results(self.plano, resultados, self.calendario)

    def test_persistencia_cria_parquet(self) -> None:
        caminho = self.diretorio / "long_teste.parquet"
        caminho_retornado = cempre.write_long_parquet(self.long_valida, caminho)
        self.assertTrue(caminho.exists())
        self.assertEqual(caminho_retornado, caminho)

    def test_persistencia_nao_sobrescreve_por_padrao(self) -> None:
        caminho = self.diretorio / "long_teste_overwrite.parquet"
        cempre.write_long_parquet(self.long_valida, caminho)
        with self.assertRaises(FileExistsError):
            cempre.write_long_parquet(self.long_valida, caminho)
        # com overwrite=True explícito, deve funcionar
        cempre.write_long_parquet(self.long_valida, caminho, overwrite=True)

    # -- Correção focal do spot-check: write_long_parquet valida
    # estruturalmente ANTES de escrever (não só presença de colunas) —
    # simetria com load_long_parquet via _validar_schema_long_persistida.

    def test_write_rejeita_ano_fora_da_janela_e_nao_cria_arquivo(self) -> None:
        caminho = self.diretorio / "long_write_ano_invalido.parquet"
        long_ano_invalido = self.long_valida.copy()
        long_ano_invalido.loc[0, "ano"] = 2050
        with self.assertRaisesRegex(ValueError, "ano"):
            cempre.write_long_parquet(long_ano_invalido, caminho)
        self.assertFalse(caminho.exists())

    def test_write_rejeita_incompatibilidade_territorial_nao_booleana_e_nao_cria_arquivo(self) -> None:
        caminho = self.diretorio / "long_write_bool_invalido.parquet"
        long_bool_invalida = self.long_valida.copy()
        long_bool_invalida["incompatibilidade_territorial"] = long_bool_invalida["incompatibilidade_territorial"].astype(str)
        long_bool_invalida.loc[0, "incompatibilidade_territorial"] = "nao_booleano"
        with self.assertRaisesRegex(ValueError, "incompatibilidade_territorial"):
            cempre.write_long_parquet(long_bool_invalida, caminho)
        self.assertFalse(caminho.exists())

    def test_load_rejeita_parquet_com_incompatibilidade_territorial_nao_booleana(self) -> None:
        caminho = self.diretorio / "long_load_bool_invalido.parquet"
        long_bool_invalida = self.long_valida.copy()
        long_bool_invalida["incompatibilidade_territorial"] = long_bool_invalida["incompatibilidade_territorial"].astype(str)
        long_bool_invalida.loc[0, "incompatibilidade_territorial"] = "nao_booleano"
        # Escreve diretamente (contornando write_long_parquet) para simular
        # um artefato Parquet já existente/corrompido por fora do pipeline.
        long_bool_invalida.to_parquet(caminho, index=False)
        with self.assertRaisesRegex(ValueError, "incompatibilidade_territorial"):
            cempre.load_long_parquet(caminho)

    def test_long_valida_continua_sendo_persistida_e_recarregada_normalmente(self) -> None:
        caminho = self.diretorio / "long_valida_ok.parquet"
        cempre.write_long_parquet(self.long_valida, caminho)
        long_recarregada = cempre.load_long_parquet(caminho)
        self.assertEqual(len(long_recarregada), len(self.long_valida))
        self.assertTrue(pd.api.types.is_bool_dtype(long_recarregada["incompatibilidade_territorial"]))

    def test_reload_preserva_schema_contratado(self) -> None:
        caminho = self.diretorio / "long_reload.parquet"
        cempre.write_long_parquet(self.long_valida, caminho)
        long_recarregada = cempre.load_long_parquet(caminho)
        for coluna in [
            "valor_bruto", "valor_numerico", "status_valor_api", "request_id",
            "hash_resposta_raw", "fonte_tabela", "ano", "codigo_municipio_ibge",
            "codigo_variavel_sidra", "status_territorial", "incompatibilidade_territorial",
        ]:
            self.assertIn(coluna, long_recarregada.columns)

    def test_roundtrip_parquet_preserva_conteudo_logico(self) -> None:
        caminho = self.diretorio / "long_roundtrip.parquet"
        cempre.write_long_parquet(self.long_valida, caminho)
        long_recarregada = cempre.load_long_parquet(caminho)
        relatorio = cempre.validate_round_trip_equivalencia(self.long_valida, long_recarregada)
        self.assertTrue(relatorio["equivalente"])
        self.assertEqual(relatorio["n_linhas"], len(self.long_valida))

    def test_arquivo_parquet_com_coluna_estrutural_ausente_e_rejeitado(self) -> None:
        caminho = self.diretorio / "long_sem_coluna.parquet"
        long_sem_coluna = self.long_valida.drop(columns=["status_territorial"])
        long_sem_coluna.to_parquet(caminho, index=False)
        with self.assertRaisesRegex(ValueError, "coluna"):
            cempre.load_long_parquet(caminho)

    def test_chave_canonica_duplicada_no_parquet_e_rejeitada(self) -> None:
        caminho = self.diretorio / "long_duplicada.parquet"
        long_duplicada = pd.concat([self.long_valida, self.long_valida.iloc[[0]]], ignore_index=True)
        long_duplicada.to_parquet(caminho, index=False)
        with self.assertRaisesRegex(ValueError, "duplicada"):
            cempre.load_long_parquet(caminho)

    def test_ano_invalido_no_parquet_e_rejeitado(self) -> None:
        caminho = self.diretorio / "long_ano_invalido.parquet"
        long_ano_invalido = self.long_valida.copy()
        long_ano_invalido.loc[0, "ano"] = 2050
        long_ano_invalido.to_parquet(caminho, index=False)
        with self.assertRaisesRegex(ValueError, "ano"):
            cempre.load_long_parquet(caminho)

    def test_variavel_invalida_no_parquet_e_rejeitada(self) -> None:
        caminho = self.diretorio / "long_variavel_invalida.parquet"
        long_variavel_invalida = self.long_valida.copy()
        long_variavel_invalida.loc[0, "codigo_variavel_sidra"] = 999999
        long_variavel_invalida.to_parquet(caminho, index=False)
        with self.assertRaisesRegex(ValueError, "variável"):
            cempre.load_long_parquet(caminho)

    def test_arquivo_ausente_falha_explicitamente(self) -> None:
        with self.assertRaises(FileNotFoundError):
            cempre.load_long_parquet(self.diretorio / "inexistente.parquet")

    def test_formato_nao_parquet_falha_explicitamente(self) -> None:
        caminho = self.diretorio / "long.csv"
        caminho.write_text("codigo_municipio_ibge,ano\n3166600,2010\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "formato"):
            cempre.load_long_parquet(caminho)


class TestRebuildLongFromCache(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.diretorio = Path(self._tmpdir.name)
        self.cache_dir = self.diretorio / "cache"
        self.plano = _plano_pequeno_d2()
        self.calendario = _calendario_d2()
        _salva_cache_valido_d2(self.cache_dir, "req_d2_zzz", [_linha_payload_d2("3166600", 2010, 708, "100")])
        _salva_cache_valido_d2(self.cache_dir, "req_d2_aaa", [_linha_payload_d2("1100015", 2007, 708, "150")])

    def test_rebuild_offline_a_partir_de_cache_funciona_sem_rede(self) -> None:
        long_reconstruida = cempre.rebuild_long_from_cache(self.plano, self.cache_dir, self.calendario)
        self.assertEqual(len(long_reconstruida), 2)
        self.assertTrue({"status_territorial", "incompatibilidade_territorial"} <= set(long_reconstruida.columns))

    def test_rebuild_offline_pode_persistir_diretamente(self) -> None:
        caminho = self.diretorio / "long_rebuild.parquet"
        long_reconstruida = cempre.rebuild_long_from_cache(
            self.plano, self.cache_dir, self.calendario, caminho_persistencia=caminho,
        )
        self.assertTrue(caminho.exists())
        long_recarregada = cempre.load_long_parquet(caminho)
        cempre.validate_round_trip_equivalencia(long_reconstruida, long_recarregada)

    def test_rebuild_offline_nunca_chama_fetch_request(self) -> None:
        with mock.patch.object(cempre, "fetch_request", side_effect=AssertionError("não deve ser chamado")):
            cempre.rebuild_long_from_cache(self.plano, self.cache_dir, self.calendario)

    def test_rebuild_offline_nunca_chama_requests_get(self) -> None:
        with mock.patch.object(cempre.requests, "get", side_effect=AssertionError("não deve ser chamado")):
            cempre.rebuild_long_from_cache(self.plano, self.cache_dir, self.calendario)


# ---------------------------------------------------------------------------
# Correção focal pós-auditoria integrada D1-D4 (bloqueador pré-extração
# nacional): vinculação semântica RESULTADO/CACHE ↔ REQUEST ESPERADO.
#
# A auditoria reproduziu offline que um único cache válido, copiado para os
# nomes de vários request_ids esperados, era classificado como válido em
# todos eles (integridade/hash e schema não bastam). Estes testes cobrem as
# duas barreiras da correção: (1) envelope.request_id divergente do
# request_id esperado; (2) payload estruturalmente válido mas semanticamente
# de outro lote (ano, UF/território ou grupo de variáveis diferentes).
# ---------------------------------------------------------------------------


class TestVinculacaoSemanticaCacheRequest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.cache_dir = Path(self._tmpdir.name)
        self.plano = _plano_pequeno_d2()
        self.calendario = _calendario_d2()

    def _payload_correto(self, item: dict, valor: str = "100") -> list[dict]:
        return [_linha_payload_d2(item["territorio"]["codigo"], item["ano"], item["variaveis"][0], valor)]

    def _plano_abc(self) -> list[dict]:
        base = _plano_pequeno_d2()[0]
        return [
            {**base, "request_id": "req_abc_a", "territorio": {"tipo": "municipio", "codigo": "3166600"}, "ano": 2010},
            {**base, "request_id": "req_abc_b", "territorio": {"tipo": "municipio", "codigo": "1100015"}, "ano": 2010},
            {**base, "request_id": "req_abc_c", "territorio": {"tipo": "municipio", "codigo": "4212650"}, "ano": 2010},
        ]

    # -- A: envelope.request_id diferente do request_id esperado --

    def test_envelope_request_id_diferente_do_esperado_e_rejeitado(self) -> None:
        item_a, item_b = self.plano
        _salva_cache_valido_d2(self.cache_dir, item_a["request_id"], self._payload_correto(item_a))
        bytes_a = cempre.cache_path_for_request(item_a["request_id"], self.cache_dir).read_bytes()
        cempre.cache_path_for_request(item_b["request_id"], self.cache_dir).write_bytes(bytes_a)

        with self.assertRaisesRegex(ValueError, "request_id do envelope"):
            cempre.load_cached_request(item_b["request_id"], self.cache_dir)

    # -- F: cache copiado A->B vira inválido no fluxo de reconstrução offline --

    def test_cache_copiado_de_outro_request_e_invalido_no_load_results_from_cache(self) -> None:
        item_a, item_b = self.plano
        _salva_cache_valido_d2(self.cache_dir, item_a["request_id"], self._payload_correto(item_a))
        bytes_a = cempre.cache_path_for_request(item_a["request_id"], self.cache_dir).read_bytes()
        cempre.cache_path_for_request(item_b["request_id"], self.cache_dir).write_bytes(bytes_a)

        resultados = cempre.load_results_from_cache(self.plano, self.cache_dir)
        resultados_por_id = {r["request_id"]: r for r in resultados}
        self.assertIsNone(resultados_por_id[item_a["request_id"]]["erro"])
        self.assertIsNotNone(resultados_por_id[item_b["request_id"]]["erro"])
        self.assertIsNone(resultados_por_id[item_b["request_id"]]["resultado"])

    # -- B: envelope correto + payload de ano errado --

    def test_payload_ano_errado_e_rejeitado(self) -> None:
        item = self.plano[0]
        payload_ano_errado = [
            _linha_payload_d2(item["territorio"]["codigo"], item["ano"] + 1, item["variaveis"][0], "100")
        ]
        _salva_cache_valido_d2(self.cache_dir, item["request_id"], payload_ano_errado)
        resultados = cempre.load_results_from_cache([item], self.cache_dir)
        self.assertIsNone(resultados[0]["resultado"])
        self.assertIn("ano", resultados[0]["erro"])

    # -- C: envelope correto + payload de UF/município errado --

    def test_payload_territorio_errado_e_rejeitado(self) -> None:
        item = self.plano[0]  # município 3166600
        outro_municipio = self.plano[1]["territorio"]["codigo"]  # 1100015
        payload_territorio_errado = [
            _linha_payload_d2(outro_municipio, item["ano"], item["variaveis"][0], "100")
        ]
        _salva_cache_valido_d2(self.cache_dir, item["request_id"], payload_territorio_errado)
        resultados = cempre.load_results_from_cache([item], self.cache_dir)
        self.assertIsNone(resultados[0]["resultado"])
        self.assertIn("município", resultados[0]["erro"])

    def test_payload_uf_errada_e_rejeitado_para_request_de_uf(self) -> None:
        item_uf = {
            "request_id": "req_uf_11", "url": "https://apisidra.ibge.gov.br/values/fake_uf_11",
            "params": {}, "ano": 2010, "territorio": {"tipo": "uf", "codigo": "11", "sigla": "RO"},
            "variaveis": [708], "fonte_tabela": cempre.FONTE_TABELA,
        }
        # Município real de outra UF (31 = MG), não da UF 11 esperada.
        payload_uf_errada = [_linha_payload_d2("3166600", 2010, 708, "100")]
        _salva_cache_valido_d2(self.cache_dir, item_uf["request_id"], payload_uf_errada)
        resultados = cempre.load_results_from_cache([item_uf], self.cache_dir)
        self.assertIsNone(resultados[0]["resultado"])
        self.assertIn("UF", resultados[0]["erro"])

    # -- D: envelope correto + payload de variáveis erradas --

    def test_payload_variaveis_erradas_e_rejeitado(self) -> None:
        item = dict(self.plano[0])
        item["variaveis"] = [708]
        payload_variavel_errada = [_linha_payload_d2(item["territorio"]["codigo"], item["ano"], 707, "100")]
        _salva_cache_valido_d2(self.cache_dir, item["request_id"], payload_variavel_errada)
        resultados = cempre.load_results_from_cache([item], self.cache_dir)
        self.assertIsNone(resultados[0]["resultado"])
        self.assertIn("variável", resultados[0]["erro"])

    # -- E: cache genuinamente correto continua sendo aceito --

    def test_cache_genuino_correto_continua_aceito(self) -> None:
        item = self.plano[0]
        _salva_cache_valido_d2(self.cache_dir, item["request_id"], self._payload_correto(item))
        resultados = cempre.load_results_from_cache([item], self.cache_dir)
        self.assertIsNone(resultados[0]["erro"])
        self.assertIsNotNone(resultados[0]["resultado"])

    # -- G: plano sintético A/B/C com payload de A copiado para todos --

    def test_plano_sintetico_abc_payload_de_a_copiado_para_todos(self) -> None:
        plano_abc = self._plano_abc()
        payload_a = self._payload_correto(plano_abc[0])
        for item in plano_abc:
            _salva_cache_valido_d2(self.cache_dir, item["request_id"], payload_a)

        resultados = cempre.load_results_from_cache(plano_abc, self.cache_dir)
        resultados_por_id = {r["request_id"]: r for r in resultados}
        self.assertIsNotNone(resultados_por_id["req_abc_a"]["resultado"])
        self.assertIsNone(resultados_por_id["req_abc_a"]["erro"])
        for request_id in ("req_abc_b", "req_abc_c"):
            self.assertIsNone(resultados_por_id[request_id]["resultado"])
            self.assertIsNotNone(resultados_por_id[request_id]["erro"])

    # -- H: resultado semanticamente inválido não conta como sucesso na completude --

    def test_resultado_semanticamente_invalido_nao_conta_como_sucesso_na_completude(self) -> None:
        plano_abc = self._plano_abc()
        payload_a = self._payload_correto(plano_abc[0])
        for item in plano_abc:
            _salva_cache_valido_d2(self.cache_dir, item["request_id"], payload_a)
        resultados = cempre.load_results_from_cache(plano_abc, self.cache_dir)
        relatorio = cempre.avalia_completude_plano(plano_abc, resultados)
        self.assertFalse(relatorio["completo"])
        self.assertEqual(relatorio["n_sucessos"], 1)
        self.assertEqual(relatorio["n_falhas"], 2)

    # -- I: long não é construída como completa com resultado trocado --

    def test_long_nao_e_construida_como_completa_com_resultado_trocado(self) -> None:
        plano_abc = self._plano_abc()
        payload_a = self._payload_correto(plano_abc[0])
        for item in plano_abc:
            _salva_cache_valido_d2(self.cache_dir, item["request_id"], payload_a)
        resultados = cempre.load_results_from_cache(plano_abc, self.cache_dir)
        calendario_abc = pd.DataFrame([
            {"codigo_municipio_ibge": codigo, "ano": 2010, "municipio_existia_no_ano": True}
            for codigo in ("3166600", "1100015", "4212650")
        ])
        with self.assertRaisesRegex(ValueError, "incompleto"):
            cempre.build_long_from_results(plano_abc, resultados, calendario_abc)

    # -- Defesa contra bypass de load_results_from_cache (seção 8 do pedido) --

    def test_build_long_from_results_bloqueia_resultado_construido_manualmente(self) -> None:
        item_a, item_b = self.plano
        payload_a = self._payload_correto(item_a)
        resultados_manuais = [
            {"request_id": item_a["request_id"], "erro": None, "resultado": payload_a, "de_cache": False, "hash_resposta_raw": "x"},
            # Bypass deliberado de load_results_from_cache: usa o payload de A
            # também para B, sem nunca passar pelo cache.
            {"request_id": item_b["request_id"], "erro": None, "resultado": payload_a, "de_cache": False, "hash_resposta_raw": "y"},
        ]
        with self.assertRaisesRegex(ValueError, "incompleto"):
            cempre.build_long_from_results(self.plano, resultados_manuais, self.calendario)

    # -- N: nenhuma chamada de rede durante a vinculação semântica --

    def test_validacao_semantica_nunca_chama_rede(self) -> None:
        item_a, item_b = self.plano
        payload_a = self._payload_correto(item_a)
        for item in self.plano:
            _salva_cache_valido_d2(self.cache_dir, item["request_id"], payload_a)
        with mock.patch.object(cempre, "fetch_request", side_effect=AssertionError("não deve ser chamado")), \
             mock.patch.object(cempre.requests, "get", side_effect=AssertionError("não deve ser chamado")):
            resultados = cempre.load_results_from_cache(self.plano, self.cache_dir)
        self.assertIsNotNone(resultados[0]["resultado"])
        self.assertIsNone(resultados[1]["resultado"])


class TestBindingVariaveisObrigatorias(unittest.TestCase):
    """Correção focal pós-recheck: `variaveis_payload ⊆ variaveis_esperadas`
    sozinho aceitava payload parcial (ex.: só 708 de um grupo de 7). A
    regra corrigida exige também `obrigatorias_solicitadas ⊆
    variaveis_payload`, onde `obrigatorias_solicitadas = variaveis_esperadas
    ∩ VARIAVEIS_OBRIGATORIAS` — preservando 1606 como sempre opcional."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.cache_dir = Path(self._tmpdir.name)
        self.item = {
            "request_id": "req_nacional_binding",
            "url": "https://apisidra.ibge.gov.br/values/fake_nacional",
            "params": {}, "ano": 2010, "territorio": {"tipo": "municipio", "codigo": "3166600"},
            "variaveis": sorted(cempre.VARIAVEIS_ESPERADAS), "fonte_tabela": cempre.FONTE_TABELA,
        }

    def _payload(self, variaveis: list[int], valor: str = "100") -> list[dict]:
        return [_linha_payload_d2("3166600", 2010, variavel, valor) for variavel in variaveis]

    def _resultado_para(self, payload: list[dict]) -> dict:
        _salva_cache_valido_d2(self.cache_dir, self.item["request_id"], payload)
        resultados = cempre.load_results_from_cache([self.item], self.cache_dir)
        return resultados[0]

    # -- A: apenas uma obrigatória (708) --

    def test_apenas_708_e_rejeitado(self) -> None:
        resultado = self._resultado_para(self._payload([708]))
        self.assertIsNone(resultado["resultado"])
        self.assertIn("obrigat", resultado["erro"])

    # -- B: cinco das seis obrigatórias (falta 662) --

    def test_cinco_das_seis_obrigatorias_e_rejeitado(self) -> None:
        variaveis_presentes = sorted(cempre.VARIAVEIS_OBRIGATORIAS - {662})
        resultado = self._resultado_para(self._payload(variaveis_presentes))
        self.assertIsNone(resultado["resultado"])
        self.assertIn("obrigat", resultado["erro"])
        self.assertIn("662", resultado["erro"])

    # -- C: as seis obrigatórias, sem 1606 --

    def test_seis_obrigatorias_sem_1606_e_aceito(self) -> None:
        resultado = self._resultado_para(self._payload(sorted(cempre.VARIAVEIS_OBRIGATORIAS)))
        self.assertIsNone(resultado["erro"])
        self.assertIsNotNone(resultado["resultado"])

    # -- D: as seis obrigatórias + 1606 --

    def test_seis_obrigatorias_mais_1606_e_aceito(self) -> None:
        variaveis_presentes = sorted(cempre.VARIAVEIS_OBRIGATORIAS | {1606})
        resultado = self._resultado_para(self._payload(variaveis_presentes))
        self.assertIsNone(resultado["erro"])
        self.assertIsNotNone(resultado["resultado"])

    # -- E: seis obrigatórias + variável fora do grupo --

    def test_seis_obrigatorias_mais_variavel_fora_do_grupo_e_rejeitado(self) -> None:
        variaveis_presentes = sorted(cempre.VARIAVEIS_OBRIGATORIAS) + [999999]
        resultado = self._resultado_para(self._payload(variaveis_presentes))
        self.assertIsNone(resultado["resultado"])
        self.assertIn("fora do grupo", resultado["erro"])

    # -- remoção individual de cada obrigatória faz o binding falhar --

    def test_remocao_individual_de_cada_obrigatoria_falha(self) -> None:
        for variavel_removida in sorted(cempre.VARIAVEIS_OBRIGATORIAS):
            with self.subTest(variavel_removida=variavel_removida):
                cache_dir = Path(tempfile.mkdtemp(dir=self.cache_dir))
                variaveis_presentes = sorted(cempre.VARIAVEIS_OBRIGATORIAS - {variavel_removida})
                payload = self._payload(variaveis_presentes)
                _salva_cache_valido_d2(cache_dir, self.item["request_id"], payload)
                resultado = cempre.load_results_from_cache([self.item], cache_dir)[0]
                self.assertIsNone(resultado["resultado"])
                self.assertIn("obrigat", resultado["erro"])
                self.assertIn(str(variavel_removida), resultado["erro"])

    # -- impacto na completude: N-1 completos + 1 payload parcial --

    def test_payload_parcial_nao_conta_como_sucesso_na_completude(self) -> None:
        item_completo = dict(self.item, request_id="req_binding_completo")
        item_parcial = dict(self.item, request_id="req_binding_parcial")
        plano = [item_completo, item_parcial]
        _salva_cache_valido_d2(
            self.cache_dir, item_completo["request_id"], self._payload(sorted(cempre.VARIAVEIS_OBRIGATORIAS)),
        )
        _salva_cache_valido_d2(self.cache_dir, item_parcial["request_id"], self._payload([708]))

        resultados = cempre.load_results_from_cache(plano, self.cache_dir)
        relatorio = cempre.avalia_completude_plano(plano, resultados)
        self.assertFalse(relatorio["completo"])
        self.assertEqual(relatorio["n_sucessos"], 1)
        self.assertEqual(relatorio["n_falhas"], 1)

    # -- impacto na long: resultado com payload parcial nunca produz long completa --

    def test_long_nao_e_construida_como_completa_com_payload_parcial(self) -> None:
        item_completo = dict(self.item, request_id="req_binding_completo_long")
        item_parcial = dict(self.item, request_id="req_binding_parcial_long")
        plano = [item_completo, item_parcial]
        _salva_cache_valido_d2(
            self.cache_dir, item_completo["request_id"], self._payload(sorted(cempre.VARIAVEIS_OBRIGATORIAS)),
        )
        _salva_cache_valido_d2(self.cache_dir, item_parcial["request_id"], self._payload([708]))
        resultados = cempre.load_results_from_cache(plano, self.cache_dir)
        calendario = pd.DataFrame([
            {"codigo_municipio_ibge": "3166600", "ano": 2010, "municipio_existia_no_ano": True},
        ])
        with self.assertRaisesRegex(ValueError, "incompleto"):
            cempre.build_long_from_results(plano, resultados, calendario)

    # -- zero rede --

    def test_binding_variaveis_nunca_chama_rede(self) -> None:
        with mock.patch.object(cempre, "fetch_request", side_effect=AssertionError("não deve ser chamado")), \
             mock.patch.object(cempre.requests, "get", side_effect=AssertionError("não deve ser chamado")):
            self._resultado_para(self._payload([708]))


# ---------------------------------------------------------------------------
# D3 — manifesto e proveniência do pipeline CEMPRE
#
# Usa um plano pequeno (1 ano × 27 UFs, via build_national_request_plan
# com `anos` explícito) — o contrato de UFs exige exatamente 27, mas não
# há necessidade de gerar o plano nacional completo (351 requests) só
# para testar o manifesto. Nenhum teste desta seção chama rede.
# ---------------------------------------------------------------------------


def _plano_e_ufs_d3() -> tuple[list[dict], list[dict]]:
    calendario_sintetico = pd.DataFrame(
        [{"uf_codigo": codigo, "uf_sigla": sigla} for codigo, sigla in _UFS_CONTRATADAS_SINTETICAS]
    )
    ufs_esperadas = cempre.uf_list_from_calendario(calendario_sintetico)
    plano = cempre.build_national_request_plan(calendario=calendario_sintetico, anos=[2010])
    return plano, ufs_esperadas


def _resultados_sucesso_d3(plano: list[dict]) -> list[dict]:
    return [
        {
            "request_id": item["request_id"],
            "erro": None,
            "resultado": {"valido": True},
            "de_cache": True,
            "hash_resposta_raw": cempre.hashlib.sha256(item["request_id"].encode("utf-8")).hexdigest(),
        }
        for item in plano
    ]


class TestSha256File(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.caminho = Path(self._tmpdir.name) / "artefato.bin"
        self.caminho.write_bytes(b"conteudo original")

    def test_hash_de_arquivo_e_deterministico(self) -> None:
        hash_1 = cempre.sha256_file(self.caminho)
        hash_2 = cempre.sha256_file(self.caminho)
        self.assertEqual(hash_1, hash_2)
        self.assertRegex(hash_1, r"^[0-9a-f]{64}$")

    def test_alteracao_no_arquivo_muda_hash(self) -> None:
        hash_antes = cempre.sha256_file(self.caminho)
        self.caminho.write_bytes(b"conteudo alterado")
        hash_depois = cempre.sha256_file(self.caminho)
        self.assertNotEqual(hash_antes, hash_depois)

    def test_arquivo_ausente_falha_explicitamente(self) -> None:
        with self.assertRaises(FileNotFoundError):
            cempre.sha256_file(Path(self._tmpdir.name) / "inexistente.bin")


class TestHashPlanoCanonico(unittest.TestCase):
    def setUp(self) -> None:
        self.plano, _ = _plano_e_ufs_d3()

    def test_hash_logico_do_plano_independe_da_ordem(self) -> None:
        hash_original = cempre.hash_plano_canonico(self.plano)
        hash_invertido = cempre.hash_plano_canonico(list(reversed(self.plano)))
        self.assertEqual(hash_original, hash_invertido)

    def test_hash_independe_da_ordem_de_chaves_do_dicionario(self) -> None:
        item = self.plano[0]
        item_reordenado = {chave: item[chave] for chave in reversed(list(item.keys()))}
        plano_reordenado = [item_reordenado] + self.plano[1:]
        self.assertEqual(cempre.hash_plano_canonico(self.plano), cempre.hash_plano_canonico(plano_reordenado))

    def test_alteracao_real_no_plano_muda_hash(self) -> None:
        hash_antes = cempre.hash_plano_canonico(self.plano)
        plano_alterado = [dict(item) for item in self.plano]
        plano_alterado[0]["ano"] = 2011
        hash_depois = cempre.hash_plano_canonico(plano_alterado)
        self.assertNotEqual(hash_antes, hash_depois)


class TestBuildRequestProvenance(unittest.TestCase):
    def setUp(self) -> None:
        self.plano, _ = _plano_e_ufs_d3()

    def test_proveniencia_preserva_hash_raw(self) -> None:
        resultados = _resultados_sucesso_d3(self.plano)
        provenance = cempre.build_request_provenance(self.plano, resultados)
        resultados_por_id = {r["request_id"]: r for r in resultados}
        for entrada in provenance:
            self.assertEqual(entrada["hash_resposta_raw"], resultados_por_id[entrada["request_id"]]["hash_resposta_raw"])
            self.assertEqual(entrada["status_execucao"], "sucesso")

    def test_proveniencia_preserva_erro(self) -> None:
        resultados = _resultados_sucesso_d3(self.plano)
        resultados[0]["erro"] = "HTTP 500"
        resultados[0]["resultado"] = None
        provenance = cempre.build_request_provenance(self.plano, resultados)
        entrada = next(e for e in provenance if e["request_id"] == self.plano[0]["request_id"])
        self.assertEqual(entrada["erro"], "HTTP 500")
        self.assertEqual(entrada["status_execucao"], "falha")

    def test_proveniencia_marca_ausente(self) -> None:
        resultados = _resultados_sucesso_d3(self.plano)[1:]
        provenance = cempre.build_request_provenance(self.plano, resultados)
        entrada = next(e for e in provenance if e["request_id"] == self.plano[0]["request_id"])
        self.assertEqual(entrada["status_execucao"], "ausente")

    def test_payload_bruto_nao_e_incluido_na_proveniencia(self) -> None:
        resultados = _resultados_sucesso_d3(self.plano)
        provenance = cempre.build_request_provenance(self.plano, resultados)
        for entrada in provenance:
            self.assertNotIn("resultado", entrada)


class TestBuildManifest(unittest.TestCase):
    def setUp(self) -> None:
        self.plano, self.ufs_esperadas = _plano_e_ufs_d3()

    def _build(self, resultados: list[dict], **kwargs) -> dict:
        return cempre.build_manifest(
            self.plano,
            resultados,
            ufs_esperadas=self.ufs_esperadas,
            anos_esperados=[2010],
            git_commit="a" * 40,
            timestamp_geracao="2026-01-01T00:00:00+00:00",
            **kwargs,
        )

    def test_manifesto_valido_completo(self) -> None:
        manifesto = self._build(_resultados_sucesso_d3(self.plano))
        self.assertTrue(manifesto["execucao"]["completo"])
        self.assertEqual(manifesto["plano"]["n_requests_esperados"], len(self.plano))
        self.assertEqual(len(manifesto["requests"]), len(self.plano))
        cempre.validate_manifest(manifesto)  # não deve levantar

    def test_manifesto_valido_incompleto(self) -> None:
        resultados = _resultados_sucesso_d3(self.plano)[1:]
        manifesto = self._build(resultados)
        self.assertFalse(manifesto["execucao"]["completo"])
        self.assertEqual(len(manifesto["execucao"]["request_ids_ausentes"]), 1)
        cempre.validate_manifest(manifesto)  # incompleto não é inconsistente

    def test_payload_bruto_nao_e_incluido_no_manifesto(self) -> None:
        manifesto = self._build(_resultados_sucesso_d3(self.plano))
        for entrada in manifesto["requests"]:
            self.assertNotIn("resultado", entrada)
        texto = json.dumps(manifesto)
        self.assertNotIn('"valido": true', texto.replace(" ", ""))

    def test_timestamp_injetado_e_usado_literalmente(self) -> None:
        manifesto = self._build(_resultados_sucesso_d3(self.plano))
        self.assertEqual(manifesto["geracao"]["timestamp_utc"], "2026-01-01T00:00:00+00:00")

    def test_completo_true_com_ausente_e_rejeitado(self) -> None:
        manifesto = self._build(_resultados_sucesso_d3(self.plano)[1:])
        manifesto["execucao"]["completo"] = True  # inconsistência forçada
        with self.assertRaisesRegex(ValueError, "completo=True"):
            cempre.validate_manifest(manifesto)

    def test_completo_true_com_falha_e_rejeitado(self) -> None:
        resultados = _resultados_sucesso_d3(self.plano)
        resultados[0]["erro"] = "HTTP 500"
        resultados[0]["resultado"] = None
        manifesto = self._build(resultados)
        manifesto["execucao"]["completo"] = True
        with self.assertRaisesRegex(ValueError, "completo=True"):
            cempre.validate_manifest(manifesto)

    def test_completo_true_com_duplicado_e_rejeitado(self) -> None:
        resultados = _resultados_sucesso_d3(self.plano) + [dict(_resultados_sucesso_d3(self.plano)[0])]
        manifesto = self._build(resultados)
        self.assertFalse(manifesto["execucao"]["completo"])
        manifesto["execucao"]["completo"] = True
        with self.assertRaisesRegex(ValueError, "completo=True"):
            cempre.validate_manifest(manifesto)

    def test_commit_git_malformado_e_rejeitado(self) -> None:
        manifesto = self._build(_resultados_sucesso_d3(self.plano))
        manifesto["codigo"]["git_commit"] = "commit_invalido"
        with self.assertRaisesRegex(ValueError, "git_commit"):
            cempre.validate_manifest(manifesto)

    def test_sha256_de_artefato_malformado_e_rejeitado(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho_artefato = Path(diretorio) / "calendario.parquet"
            caminho_artefato.write_bytes(b"conteudo qualquer")
            manifesto = self._build(
                _resultados_sucesso_d3(self.plano),
                artefatos={"calendario_territorial": {"caminho": str(caminho_artefato)}},
            )
            manifesto["artefatos"]["calendario_territorial"]["sha256"] = "hash_nao_hexadecimal"
            with self.assertRaisesRegex(ValueError, "sha256"):
                cempre.validate_manifest(manifesto)

    def test_artefato_long_parquet_registra_n_linhas_e_colunas(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho_artefato = Path(diretorio) / "long.parquet"
            caminho_artefato.write_bytes(b"conteudo qualquer")
            manifesto = self._build(
                _resultados_sucesso_d3(self.plano),
                artefatos={"long_parquet": {"caminho": str(caminho_artefato), "n_linhas": 42, "colunas": ["a", "b"]}},
            )
            entrada = manifesto["artefatos"]["long_parquet"]
            self.assertEqual(entrada["n_linhas"], 42)
            self.assertEqual(entrada["colunas"], ["a", "b"])
            self.assertRegex(entrada["sha256"], r"^[0-9a-f]{64}$")

    def test_manifesto_nao_declara_gates_de_autorizacao(self) -> None:
        manifesto = self._build(_resultados_sucesso_d3(self.plano))
        texto = json.dumps(manifesto)
        self.assertNotIn("EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA", texto)
        self.assertNotIn("PAINEL_TECNICO_CONSTRUIDO", texto)

    def test_build_manifest_nunca_chama_fetch_request(self) -> None:
        with mock.patch.object(cempre, "fetch_request", side_effect=AssertionError("não deve ser chamado")):
            self._build(_resultados_sucesso_d3(self.plano))

    def test_build_manifest_nunca_chama_requests_get(self) -> None:
        with mock.patch.object(cempre.requests, "get", side_effect=AssertionError("não deve ser chamado")):
            self._build(_resultados_sucesso_d3(self.plano))


# ---------------------------------------------------------------------------
# D3 — correção focal do spot-check (Bloqueadores 1 e 2): consistência
# execução×proveniência e contrato da seção plano×proveniência.
#
# Os casos "completo=True + falha" (item B) e "manifesto completo/incompleto
# coerente continua válido" (itens F/G) já são cobertos por
# `TestBuildManifest.test_completo_true_com_falha_e_rejeitado` e
# `test_manifesto_valido_completo`/`test_manifesto_valido_incompleto` acima
# — não duplicados aqui.
# ---------------------------------------------------------------------------


class TestConsistenciaExecucaoRequests(unittest.TestCase):
    def setUp(self) -> None:
        self.plano, self.ufs_esperadas = _plano_e_ufs_d3()

    def _manifesto_completo_valido(self) -> dict:
        return cempre.build_manifest(
            self.plano,
            _resultados_sucesso_d3(self.plano),
            ufs_esperadas=self.ufs_esperadas,
            anos_esperados=[2010],
            git_commit="a" * 40,
            timestamp_geracao="2026-01-01T00:00:00+00:00",
        )

    def test_n_sucessos_divergente_da_proveniencia_e_rejeitado(self) -> None:
        manifesto = self._manifesto_completo_valido()
        manifesto["execucao"]["n_sucessos"] -= 1
        with self.assertRaisesRegex(ValueError, "n_sucessos"):
            cempre.validate_manifest(manifesto)

    def test_falha_agregada_mas_proveniencia_toda_sucesso_e_rejeitado(self) -> None:
        manifesto = self._manifesto_completo_valido()
        manifesto["execucao"]["n_falhas"] = 1
        with self.assertRaisesRegex(ValueError, "n_falhas"):
            cempre.validate_manifest(manifesto)

    def test_ausente_na_execucao_mas_sucesso_na_proveniencia_e_rejeitado(self) -> None:
        manifesto = self._manifesto_completo_valido()
        manifesto["execucao"]["request_ids_ausentes"] = [self.plano[0]["request_id"]]
        with self.assertRaisesRegex(ValueError, "request_ids_ausentes"):
            cempre.validate_manifest(manifesto)

    def test_duplicado_na_execucao_mas_proveniencia_diferente_e_rejeitado(self) -> None:
        manifesto = self._manifesto_completo_valido()
        manifesto["execucao"]["request_ids_duplicados"] = [self.plano[0]["request_id"]]
        with self.assertRaisesRegex(ValueError, "request_ids_duplicados"):
            cempre.validate_manifest(manifesto)


class TestContratoPlanoManifesto(unittest.TestCase):
    def setUp(self) -> None:
        self.plano, self.ufs_esperadas = _plano_e_ufs_d3()

    def _manifesto_valido(self) -> dict:
        return cempre.build_manifest(
            self.plano,
            _resultados_sucesso_d3(self.plano),
            ufs_esperadas=self.ufs_esperadas,
            anos_esperados=[2010],
            git_commit="a" * 40,
            timestamp_geracao="2026-01-01T00:00:00+00:00",
        )

    def test_hash_plano_com_formato_invalido_e_rejeitado(self) -> None:
        manifesto = self._manifesto_valido()
        manifesto["plano"]["hash_plano"] = "hash_nao_hexadecimal"
        with self.assertRaisesRegex(ValueError, "hash_plano"):
            cempre.validate_manifest(manifesto)

    def test_ano_fora_da_janela_no_plano_e_rejeitado(self) -> None:
        manifesto = self._manifesto_valido()
        manifesto["plano"]["anos"] = [2050]
        with self.assertRaisesRegex(ValueError, "janela"):
            cempre.validate_manifest(manifesto)

    def test_ano_do_plano_divergente_da_proveniencia_e_rejeitado(self) -> None:
        manifesto = self._manifesto_valido()
        manifesto["plano"]["anos"] = [2011]  # dentro da janela, mas não é o ano real dos requests
        with self.assertRaisesRegex(ValueError, "divergente dos anos"):
            cempre.validate_manifest(manifesto)

    def test_variavel_fora_do_contrato_no_plano_e_rejeitada(self) -> None:
        manifesto = self._manifesto_valido()
        manifesto["plano"]["variaveis"] = manifesto["plano"]["variaveis"] + [999999]
        with self.assertRaisesRegex(ValueError, "variaveis fora do contrato"):
            cempre.validate_manifest(manifesto)

    def test_variavel_contratada_ausente_no_plano_e_rejeitada(self) -> None:
        manifesto = self._manifesto_valido()
        manifesto["plano"]["variaveis"] = manifesto["plano"]["variaveis"][:-1]
        with self.assertRaisesRegex(ValueError, "variaveis fora do contrato"):
            cempre.validate_manifest(manifesto)

    def test_variaveis_em_ordem_diferente_mesmo_conjunto_continua_valido(self) -> None:
        manifesto = self._manifesto_valido()
        manifesto["plano"]["variaveis"] = list(reversed(manifesto["plano"]["variaveis"]))
        cempre.validate_manifest(manifesto)  # não deve levantar

    def test_ufs_do_plano_divergentes_da_proveniencia_e_rejeitado(self) -> None:
        manifesto = self._manifesto_valido()
        ufs_adulteradas = list(manifesto["plano"]["ufs"])
        ufs_adulteradas[0] = "99"
        manifesto["plano"]["ufs"] = ufs_adulteradas
        with self.assertRaisesRegex(ValueError, "plano.ufs"):
            cempre.validate_manifest(manifesto)


class TestPersistenciaManifesto(unittest.TestCase):
    def setUp(self) -> None:
        self.plano, self.ufs_esperadas = _plano_e_ufs_d3()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.diretorio = Path(self._tmpdir.name)
        self.manifesto = cempre.build_manifest(
            self.plano,
            _resultados_sucesso_d3(self.plano),
            ufs_esperadas=self.ufs_esperadas,
            anos_esperados=[2010],
            git_commit="a" * 40,
            timestamp_geracao="2026-01-01T00:00:00+00:00",
        )

    def test_write_manifest_cria_json(self) -> None:
        caminho = self.diretorio / "manifesto.json"
        caminho_retornado = cempre.write_manifest(self.manifesto, caminho)
        self.assertTrue(caminho.exists())
        self.assertEqual(caminho_retornado, caminho)
        with open(caminho, encoding="utf-8") as f:
            conteudo = json.load(f)
        self.assertEqual(conteudo["schema_manifesto"], self.manifesto["schema_manifesto"])

    def test_overwrite_padrao_rejeita_arquivo_existente(self) -> None:
        caminho = self.diretorio / "manifesto_overwrite.json"
        cempre.write_manifest(self.manifesto, caminho)
        with self.assertRaises(FileExistsError):
            cempre.write_manifest(self.manifesto, caminho)
        cempre.write_manifest(self.manifesto, caminho, overwrite=True)

    def test_load_manifest_rejeita_json_invalido(self) -> None:
        caminho = self.diretorio / "manifesto_invalido.json"
        caminho.write_text("{ isso não é json", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "JSON"):
            cempre.load_manifest(caminho)

    def test_load_manifest_rejeita_contrato_inconsistente(self) -> None:
        caminho = self.diretorio / "manifesto_inconsistente.json"
        caminho.write_text(json.dumps({"schema_manifesto": "x"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "seção"):
            cempre.load_manifest(caminho)

    def test_roundtrip_json_preserva_conteudo(self) -> None:
        caminho = self.diretorio / "manifesto_roundtrip.json"
        cempre.write_manifest(self.manifesto, caminho)
        manifesto_recarregado = cempre.load_manifest(caminho)
        self.assertEqual(manifesto_recarregado, self.manifesto)

    def test_write_manifest_nao_rejeita_execucao_incompleta(self) -> None:
        manifesto_incompleto = cempre.build_manifest(
            self.plano,
            _resultados_sucesso_d3(self.plano)[1:],
            ufs_esperadas=self.ufs_esperadas,
            anos_esperados=[2010],
            git_commit="a" * 40,
            timestamp_geracao="2026-01-01T00:00:00+00:00",
        )
        caminho = self.diretorio / "manifesto_incompleto.json"
        cempre.write_manifest(manifesto_incompleto, caminho)
        manifesto_recarregado = cempre.load_manifest(caminho)
        self.assertFalse(manifesto_recarregado["execucao"]["completo"])
        self.assertEqual(len(manifesto_recarregado["execucao"]["request_ids_ausentes"]), 1)

    def test_write_manifest_nunca_chama_fetch_request(self) -> None:
        caminho = self.diretorio / "manifesto_sem_rede.json"
        with mock.patch.object(cempre, "fetch_request", side_effect=AssertionError("não deve ser chamado")):
            cempre.write_manifest(self.manifesto, caminho)
            cempre.load_manifest(caminho)


class TestGetGitHead(unittest.TestCase):
    def test_mock_confirma_uso_do_hash_completo(self) -> None:
        hash_completo = "f" * 40
        resultado_mock = mock.Mock(returncode=0, stdout=hash_completo + "\n", stderr="")
        with mock.patch.object(cempre.subprocess, "run", return_value=resultado_mock) as run_mock:
            commit = cempre.get_git_head()
        self.assertEqual(commit, hash_completo)
        self.assertEqual(len(commit), 40)
        run_mock.assert_called_once()

    def test_falha_do_comando_git_e_explicita(self) -> None:
        resultado_mock = mock.Mock(returncode=128, stdout="", stderr="fatal: not a git repository")
        with mock.patch.object(cempre.subprocess, "run", return_value=resultado_mock):
            with self.assertRaises(RuntimeError):
                cempre.get_git_head()

    def test_comando_git_ausente_e_explicito(self) -> None:
        with mock.patch.object(cempre.subprocess, "run", side_effect=OSError("git não encontrado")):
            with self.assertRaises(RuntimeError):
                cempre.get_git_head()

    def test_saida_em_formato_inesperado_e_explicita(self) -> None:
        resultado_mock = mock.Mock(returncode=0, stdout="abreviado123\n", stderr="")
        with mock.patch.object(cempre.subprocess, "run", return_value=resultado_mock):
            with self.assertRaises(RuntimeError):
                cempre.get_git_head()


# ---------------------------------------------------------------------------
# D4 — orquestração nacional (dry run offline)
#
# Usa um calendário sintético com 1 linha por UF (27 UFs, ano fixo) e
# `anos=[2010]` no plano — 27 requests, o suficiente para testar
# classificação de cache, conflitos e o contrato do relatório, sem gerar
# o plano nacional completo (351) nos testes unitários. Nenhum teste
# desta seção chama rede.
# ---------------------------------------------------------------------------


def _payload_valido_para_item(item: dict, valor: str = "100") -> list[dict]:
    """Payload sintético genuinamente compatível com `item` (mesma UF/
    município e ano do request, TODAS as variáveis básicas obrigatórias do
    grupo solicitado presentes) — para distinguir de um payload copiado de
    outro request (mesmo conteúdo, request_id diferente) ou de um payload
    parcial (faltando variável obrigatória), que a vinculação semântica
    deve rejeitar em ambos os casos.
    """
    territorio = item["territorio"]
    if territorio["tipo"] == "uf":
        codigo_municipio = f"{territorio['codigo']}00001"
    else:
        codigo_municipio = territorio["codigo"]
    variaveis_obrigatorias_do_item = sorted(set(item["variaveis"]) & cempre.VARIAVEIS_OBRIGATORIAS)
    variaveis_a_incluir = variaveis_obrigatorias_do_item or sorted(item["variaveis"])[:1]
    return [
        _linha_payload_d2(codigo_municipio, item["ano"], variavel, valor)
        for variavel in variaveis_a_incluir
    ]


def _escreve_calendario_nacional_sintetico(caminho: Path) -> None:
    linhas = [
        {
            "codigo_municipio_ibge": f"{codigo_uf}00001",
            "ano": 2010,
            "municipio_existia_no_ano": True,
            "uf_codigo": codigo_uf,
            "uf_sigla": sigla,
        }
        for codigo_uf, sigla in _UFS_CONTRATADAS_SINTETICAS
    ]
    pd.DataFrame(linhas).to_parquet(caminho, index=False)


class TestDryRunNationalPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.diretorio = Path(self._tmpdir.name)
        self.calendario_path = self.diretorio / "calendario.parquet"
        _escreve_calendario_nacional_sintetico(self.calendario_path)
        self.cache_dir = self.diretorio / "cache"
        self.caminho_long = self.diretorio / "interim" / "long.parquet"
        self.caminho_manifesto = self.diretorio / "raw" / "manifesto.json"

        calendario = cempre.load_calendar_territorial(self.calendario_path)
        self.plano = cempre.build_national_request_plan(calendario=calendario, anos=[2010])

    def _config(self, **overrides: Any) -> "cempre.NationalRunConfig":
        base = dict(
            cache_dir=self.cache_dir,
            calendario_path=self.calendario_path,
            caminho_long=self.caminho_long,
            caminho_manifesto=self.caminho_manifesto,
            anos=[2010],
        )
        base.update(overrides)
        return cempre.NationalRunConfig(**base)

    # -- A/G: todos ausentes --

    def test_dry_run_todos_caches_ausentes(self) -> None:
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["n_requests_esperados"], 27)
        self.assertEqual(relatorio["n_cache_ausentes"], 27)
        self.assertEqual(relatorio["n_cache_validos"], 0)
        self.assertEqual(relatorio["n_cache_invalidos"], 0)
        self.assertEqual(relatorio["n_requests_que_exigiriam_rede"], 27)
        self.assertEqual(relatorio["bloqueadores"], [])
        self.assertTrue(relatorio["pronto_para_execucao_real"])

    # -- B: alguns válidos --

    def test_dry_run_alguns_caches_validos(self) -> None:
        for item in self.plano[:5]:
            _salva_cache_valido_d2(self.cache_dir, item["request_id"], _payload_valido_para_item(item))
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["n_cache_validos"], 5)
        self.assertEqual(relatorio["n_cache_ausentes"], 22)
        self.assertEqual(relatorio["n_requests_que_exigiriam_rede"], 22)

    # -- C: todos válidos --

    def test_dry_run_todos_caches_validos(self) -> None:
        for item in self.plano:
            _salva_cache_valido_d2(self.cache_dir, item["request_id"], _payload_valido_para_item(item))
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["n_cache_validos"], 27)
        self.assertEqual(relatorio["n_requests_que_exigiriam_rede"], 0)
        self.assertTrue(relatorio["pronto_para_execucao_real"])

    # -- D: cache corrompido --

    def test_cache_corrompido_e_classificado_invalido(self) -> None:
        request_id = self.plano[0]["request_id"]
        caminho_cache = cempre.cache_path_for_request(request_id, self.cache_dir)
        caminho_cache.parent.mkdir(parents=True, exist_ok=True)
        caminho_cache.write_text("{ isso não é json", encoding="utf-8")
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["n_cache_invalidos"], 1)
        self.assertIn(request_id, relatorio["request_ids_cache_invalidos"])

    # -- E: schema inválido --

    def test_cache_schema_invalido_e_classificado_invalido(self) -> None:
        request_id = self.plano[0]["request_id"]
        texto_lista_vazia = json.dumps([])
        cempre.save_cached_request(
            request_id,
            texto_resposta_raw=texto_lista_vazia,
            hash_resposta_raw=cempre.hashlib.sha256(texto_lista_vazia.encode("utf-8")).hexdigest(),
            cache_dir=self.cache_dir,
        )
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["n_cache_invalidos"], 1)
        self.assertIn(request_id, relatorio["request_ids_cache_invalidos"])

    # -- F: cache inválido vira bloqueador --

    def test_cache_invalido_vira_bloqueador(self) -> None:
        request_id = self.plano[0]["request_id"]
        caminho_cache = cempre.cache_path_for_request(request_id, self.cache_dir)
        caminho_cache.parent.mkdir(parents=True, exist_ok=True)
        caminho_cache.write_text("{ nao e json", encoding="utf-8")
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertFalse(relatorio["pronto_para_execucao_real"])
        self.assertTrue(any("inválido" in bloqueador for bloqueador in relatorio["bloqueadores"]))

    # -- G/H: ausente exige rede; válido não exige --

    def test_cache_ausente_conta_como_exigiria_rede(self) -> None:
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(set(relatorio["request_ids_que_exigiriam_rede"]), set(relatorio["request_ids_cache_ausentes"]))

    def test_cache_valido_nao_conta_como_exigiria_rede(self) -> None:
        item = self.plano[0]
        _salva_cache_valido_d2(self.cache_dir, item["request_id"], _payload_valido_para_item(item))
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertNotIn(item["request_id"], relatorio["request_ids_que_exigiriam_rede"])

    # -- I/J/K: n_requests_esperados/hash_plano/git_commit --

    def test_n_requests_esperados_vem_do_plano(self) -> None:
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["n_requests_esperados"], len(self.plano))

    def test_hash_plano_vem_do_d3(self) -> None:
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["hash_plano"], cempre.hash_plano_canonico(self.plano))

    def test_git_commit_completo_presente(self) -> None:
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertRegex(relatorio["git_commit"], r"^[0-9a-f]{40}$")

    # -- L/M: conflitos de artefatos --

    def test_conflito_long_existente_vira_bloqueador(self) -> None:
        self.caminho_long.parent.mkdir(parents=True, exist_ok=True)
        self.caminho_long.write_bytes(b"conteudo qualquer")
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertTrue(relatorio["conflito_long_existente"])
        self.assertFalse(relatorio["pronto_para_execucao_real"])

    def test_conflito_manifesto_existente_vira_bloqueador(self) -> None:
        self.caminho_manifesto.parent.mkdir(parents=True, exist_ok=True)
        self.caminho_manifesto.write_text("{}", encoding="utf-8")
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertTrue(relatorio["conflito_manifesto_existente"])
        self.assertFalse(relatorio["pronto_para_execucao_real"])

    # -- N: overwrite=True remove conflito lógico, mas não sobrescreve nada --

    def test_overwrite_true_remove_conflito_mas_nao_sobrescreve_arquivo(self) -> None:
        self.caminho_long.parent.mkdir(parents=True, exist_ok=True)
        self.caminho_long.write_bytes(b"conteudo original")
        conteudo_antes = self.caminho_long.read_bytes()
        mtime_antes = self.caminho_long.stat().st_mtime

        relatorio = cempre.dry_run_national_pipeline(self._config(overwrite=True))

        self.assertFalse(relatorio["conflito_long_existente"])
        self.assertEqual(self.caminho_long.read_bytes(), conteudo_antes)
        self.assertEqual(self.caminho_long.stat().st_mtime, mtime_antes)

    # -- O/P/Q: dry run não cria nada --

    def test_dry_run_nao_cria_long_nem_manifesto_nem_cache(self) -> None:
        self.assertFalse(self.caminho_long.exists())
        self.assertFalse(self.caminho_manifesto.exists())
        cempre.dry_run_national_pipeline(self._config())
        self.assertFalse(self.caminho_long.exists())
        self.assertFalse(self.caminho_manifesto.exists())
        self.assertFalse(self.cache_dir.exists() and any(self.cache_dir.iterdir()))

    # -- R/S: zero rede --

    def test_dry_run_nunca_chama_fetch_request(self) -> None:
        with mock.patch.object(cempre, "fetch_request", side_effect=AssertionError("não deve ser chamado")):
            cempre.dry_run_national_pipeline(self._config())

    def test_dry_run_nunca_chama_requests_get(self) -> None:
        with mock.patch.object(cempre.requests, "get", side_effect=AssertionError("não deve ser chamado")):
            cempre.dry_run_national_pipeline(self._config())

    # -- T: execução real sem autorização falha antes da rede --

    def test_execucao_real_sem_autorizacao_falha_antes_da_rede(self) -> None:
        with mock.patch.object(cempre, "fetch_request", side_effect=AssertionError("não deve ser chamado")), \
             mock.patch.object(cempre.requests, "get", side_effect=AssertionError("não deve ser chamado")):
            with self.assertRaises(PermissionError):
                cempre.run_national_pipeline(
                    self._config(), modo=cempre.MODO_EXECUCAO_REAL, autorizacao_extracao=False,
                )

    def test_execucao_real_autorizada_ainda_nao_implementada(self) -> None:
        with mock.patch.object(cempre, "fetch_request", side_effect=AssertionError("não deve ser chamado")), \
             mock.patch.object(cempre.requests, "get", side_effect=AssertionError("não deve ser chamado")):
            with self.assertRaises(NotImplementedError):
                cempre.run_national_pipeline(
                    self._config(), modo=cempre.MODO_EXECUCAO_REAL, autorizacao_extracao=True,
                )

    def test_modo_desconhecido_falha_explicitamente(self) -> None:
        with self.assertRaises(ValueError):
            cempre.run_national_pipeline(self._config(), modo="modo_invalido", autorizacao_extracao=False)

    # -- U: dry_run é o modo padrão --

    def test_dry_run_e_modo_padrao(self) -> None:
        config = self._config()
        self.assertEqual(config.modo, cempre.MODO_DRY_RUN)
        relatorio = cempre.run_national_pipeline(config)
        self.assertEqual(relatorio["modo"], "dry_run")

    # -- V: relatório determinístico --

    def test_relatorio_e_deterministico(self) -> None:
        relatorio_1 = cempre.dry_run_national_pipeline(self._config())
        relatorio_2 = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio_1, relatorio_2)

    # -- W: resumo humano reflete as contagens reais --

    def test_resumo_humano_reflete_contagens(self) -> None:
        for item in self.plano[:3]:
            _salva_cache_valido_d2(self.cache_dir, item["request_id"], _payload_valido_para_item(item))
        relatorio = cempre.dry_run_national_pipeline(self._config())
        resumo = cempre.format_dry_run_summary(relatorio)
        self.assertIn(f"Requests esperados: {relatorio['n_requests_esperados']}", resumo)
        self.assertIn(f"Caches válidos: {relatorio['n_cache_validos']}", resumo)
        self.assertIn(f"Caches ausentes: {relatorio['n_cache_ausentes']}", resumo)
        self.assertIn(f"Requests que exigiriam rede: {relatorio['n_requests_que_exigiriam_rede']}", resumo)
        self.assertIn("Pronto tecnicamente para execução: SIM", resumo)

    # -- Correção focal pós-auditoria integrada D1-D4: cache semanticamente
    # incompatível (payload de outro request) precisa ser classificado como
    # inválido/bloqueador no dry run, nunca tratado como cache ausente. --

    def test_dry_run_cache_semanticamente_incompativel_e_classificado_invalido(self) -> None:
        item_alvo, item_outro = self.plano[0], self.plano[1]
        payload_de_outro = _payload_valido_para_item(item_outro)
        _salva_cache_valido_d2(self.cache_dir, item_alvo["request_id"], payload_de_outro)
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["n_cache_invalidos"], 1)
        self.assertIn(item_alvo["request_id"], relatorio["request_ids_cache_invalidos"])

    def test_dry_run_cache_semanticamente_incompativel_vira_bloqueador(self) -> None:
        item_alvo, item_outro = self.plano[0], self.plano[1]
        payload_de_outro = _payload_valido_para_item(item_outro)
        _salva_cache_valido_d2(self.cache_dir, item_alvo["request_id"], payload_de_outro)
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertTrue(any("inválido" in bloqueador for bloqueador in relatorio["bloqueadores"]))

    def test_dry_run_nao_fica_pronto_com_cache_semanticamente_trocado(self) -> None:
        item_alvo, item_outro = self.plano[0], self.plano[1]
        payload_de_outro = _payload_valido_para_item(item_outro)
        _salva_cache_valido_d2(self.cache_dir, item_alvo["request_id"], payload_de_outro)
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertFalse(relatorio["pronto_para_execucao_real"])

    def test_dry_run_arquivo_residual_fora_do_plano_continua_ignorado(self) -> None:
        request_id_residual = "request_fora_do_plano_nacional"
        _salva_cache_valido_d2(
            self.cache_dir, request_id_residual, [_linha_payload_d2("9999999", 2010, 708, "100")],
        )
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["n_requests_esperados"], 27)
        self.assertEqual(relatorio["n_cache_validos"], 0)
        self.assertEqual(relatorio["n_cache_invalidos"], 0)
        self.assertEqual(relatorio["n_cache_ausentes"], 27)
        self.assertTrue(relatorio["pronto_para_execucao_real"])

    def test_dry_run_reproducao_ataque_cache_unico_copiado_para_todos_os_requests(self) -> None:
        # Reproduz o cenário crítico da auditoria (um único cache válido
        # copiado para muitos request_ids esperados) na escala dos 27
        # requests sintéticos desta classe de teste — suficiente para
        # demonstrar a propriedade sem gerar o plano nacional de 351.
        item_a = self.plano[0]
        payload_a = _payload_valido_para_item(item_a)
        for item in self.plano:
            _salva_cache_valido_d2(self.cache_dir, item["request_id"], payload_a)
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["n_cache_validos"], 1)
        self.assertEqual(relatorio["n_cache_invalidos"], len(self.plano) - 1)
        self.assertIn(item_a["request_id"], relatorio["request_ids_cache_validos"])
        self.assertFalse(relatorio["pronto_para_execucao_real"])

    # -- Correção focal pós-recheck: payload parcial (só 708) em escala --

    def test_dry_run_payload_parcial_apenas_708_em_um_request_e_invalido_e_bloqueador(self) -> None:
        item_alvo = self.plano[0]
        codigo_municipio = f"{item_alvo['territorio']['codigo']}00001"
        payload_parcial = [_linha_payload_d2(codigo_municipio, item_alvo["ano"], 708, "100")]
        _salva_cache_valido_d2(self.cache_dir, item_alvo["request_id"], payload_parcial)
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["n_cache_invalidos"], 1)
        self.assertIn(item_alvo["request_id"], relatorio["request_ids_cache_invalidos"])
        self.assertFalse(relatorio["pronto_para_execucao_real"])

    def test_dry_run_payload_parcial_apenas_708_em_todos_os_requests_e_completamente_invalido(self) -> None:
        # Reproduz o ataque descrito no recheck (351 payloads contendo
        # somente 708) na escala dos 27 requests sintéticos desta classe —
        # NUNCA deve resultar em "todos válidos, pronto=True".
        for item in self.plano:
            codigo_municipio = f"{item['territorio']['codigo']}00001"
            payload_parcial = [_linha_payload_d2(codigo_municipio, item["ano"], 708, "100")]
            _salva_cache_valido_d2(self.cache_dir, item["request_id"], payload_parcial)
        relatorio = cempre.dry_run_national_pipeline(self._config())
        self.assertEqual(relatorio["n_cache_validos"], 0)
        self.assertEqual(relatorio["n_cache_invalidos"], len(self.plano))
        self.assertFalse(relatorio["pronto_para_execucao_real"])


class TestDryRunNacionalSmokeCheckOffline(unittest.TestCase):
    """Seção 13: smoke-check OFFLINE com calendário territorial real e
    plano nacional padrão (351 requests), usando `CACHE_DIR` real em modo
    somente leitura. Não cria nenhum arquivo; não autoriza extração."""

    def test_smoke_check_offline_plano_nacional_real(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            config = cempre.NationalRunConfig(
                cache_dir=cempre.CACHE_DIR,
                calendario_path=None,
                caminho_long=Path(diretorio) / "long_inexistente.parquet",
                caminho_manifesto=Path(diretorio) / "manifesto_inexistente.json",
            )
            with mock.patch.object(cempre, "fetch_request", side_effect=AssertionError("não deve ser chamado")), \
                 mock.patch.object(cempre.requests, "get", side_effect=AssertionError("não deve ser chamado")):
                relatorio = cempre.dry_run_national_pipeline(config)

        self.assertEqual(relatorio["n_requests_esperados"], 351)
        self.assertEqual(
            relatorio["n_cache_validos"] + relatorio["n_cache_ausentes"] + relatorio["n_cache_invalidos"],
            351,
        )
        self.assertFalse(relatorio["conflito_long_existente"])
        self.assertFalse(relatorio["conflito_manifesto_existente"])


if __name__ == "__main__":
    unittest.main()
