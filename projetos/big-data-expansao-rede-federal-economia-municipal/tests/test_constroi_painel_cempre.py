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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import constroi_painel_cempre as cempre  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "ibge" / "cempre" / "fixtures"


def _carrega_fixture(nome: str) -> list[dict]:
    with open(FIXTURES_DIR / nome, encoding="utf-8") as f:
        return json.load(f)


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


class TestReconcileTerritorial(unittest.TestCase):
    def setUp(self) -> None:
        self.calendario = cempre.load_calendar_territorial()

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
        df = cempre.reconcile_territorial(df, self.calendario)
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


if __name__ == "__main__":
    unittest.main()
