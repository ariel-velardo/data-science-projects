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


if __name__ == "__main__":
    unittest.main()
