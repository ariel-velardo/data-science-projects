"""Testes do D10 — painel analítico CEMPRE município-ano.

Cobre exclusivamente a transformação long técnica -> painel analítico
wide (regra territorial de inclusão/exclusão, pivot, preservação de
status, bloqueio de `desconhecido`, validações estruturais). Usa
long técnica sintética em memória — nenhum teste depende de rede, do
parquet real ou do manifesto real.

Execução:
    .venv\\Scripts\\python.exe -m unittest tests.test_constroi_painel_analitico_cempre -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import constroi_painel_analitico_cempre as analitico  # noqa: E402
import constroi_painel_cempre as cempre  # noqa: E402


def _linha_long(
    codigo: str,
    ano: int,
    variavel: int,
    *,
    valor_bruto: str = "100",
    valor_numerico: float | None = 100.0,
    status_valor_api: str = "observado",
    status_territorial: str = "existia_no_ano",
    incompatibilidade_territorial: bool = False,
    municipio_fonte: str = "Município Teste - XX",
) -> dict:
    """Constrói uma linha sintética da long técnica com apenas as
    colunas que o módulo analítico realmente usa — evita passar pelo
    pipeline apisidra/agregados completo (parser, normalize_long,
    reconcile_territorial) para manter os testes focais e rápidos."""
    return {
        "codigo_municipio_ibge": codigo,
        "ano": ano,
        "codigo_variavel_sidra": variavel,
        "municipio_fonte": municipio_fonte,
        "nome_variavel": f"Variável {variavel}",
        "unidade": "Unidade Teste",
        "valor_bruto": valor_bruto,
        "valor_numerico": valor_numerico,
        "status_valor_api": status_valor_api,
        "status_territorial": status_territorial,
        "incompatibilidade_territorial": incompatibilidade_territorial,
    }


def _municipio_completo(codigo: str, ano: int, *, status_territorial: str = "existia_no_ano",
                         municipio_fonte: str = "Município Teste - XX") -> list[dict]:
    """Um município-ano com as 7 variáveis contratadas, todas observadas
    com valores plausíveis (708 <= 707, tudo não-negativo)."""
    valores = {706: 10.0, 707: 100.0, 708: 90.0, 662: 500.0, 1606: 2.5, 5944: 85.0, 10143: 1800.0}
    return [
        _linha_long(
            codigo, ano, variavel,
            valor_bruto=str(valor), valor_numerico=valor,
            status_valor_api="observado", status_territorial=status_territorial,
            municipio_fonte=municipio_fonte,
        )
        for variavel, valor in valores.items()
    ]


class TestBuildPainelAnalitico(unittest.TestCase):
    # A. pivot long -> wide
    def test_pivot_produz_uma_linha_por_municipio_ano_com_7_colunas_de_valor(self) -> None:
        df_long = pd.DataFrame(_municipio_completo("1100015", 2019))
        painel = analitico.build_painel_analitico(df_long)

        self.assertEqual(len(painel), 1)
        linha = painel.iloc[0]
        self.assertEqual(linha["codigo_municipio_ibge"], "1100015")
        self.assertEqual(linha["ano"], 2019)
        self.assertEqual(linha["pessoal_ocupado_total"], 100.0)
        self.assertEqual(linha["pessoal_ocupado_assalariado"], 90.0)
        self.assertEqual(linha["qt_unidades_locais"], 10.0)
        self.assertEqual(linha["salario_medio_salarios_minimos_nominal"], 2.5)

    # B. chave município-ano única
    def test_chave_municipio_ano_unica_para_dois_municipios(self) -> None:
        linhas = _municipio_completo("1100015", 2019) + _municipio_completo("3166600", 2019)
        painel = analitico.build_painel_analitico(pd.DataFrame(linhas))
        self.assertEqual(len(painel), 2)
        self.assertFalse(painel.duplicated(subset=["codigo_municipio_ibge", "ano"]).any())

    # C. município não existente excluído
    def test_municipio_nao_existente_excluido_do_painel(self) -> None:
        linhas = _municipio_completo("4212650", 2007, status_territorial="nao_existia_no_ano")
        painel = analitico.build_painel_analitico(pd.DataFrame(linhas))
        self.assertEqual(len(painel), 0)

    # D. município existente preservado
    def test_municipio_existente_preservado(self) -> None:
        linhas = _municipio_completo("1100015", 2019, status_territorial="existia_no_ano")
        painel = analitico.build_painel_analitico(pd.DataFrame(linhas))
        self.assertEqual(len(painel), 1)

    # E/F. Balneário Rincão e Paraíso das Águas 2012 excluídos (caso real)
    def test_balneario_rincao_2012_excluido_apesar_de_valor_observado(self) -> None:
        linhas = _municipio_completo(
            "4220000", 2012, status_territorial="nao_existia_no_ano", municipio_fonte="Balneário Rincão - SC",
        )
        df_long = pd.DataFrame(linhas)
        painel = analitico.build_painel_analitico(df_long)
        self.assertEqual(len(painel), 0)

        diagnostico = analitico.build_diagnostico_exclusao_territorial(df_long)
        self.assertEqual(len(diagnostico), 7)
        self.assertTrue((diagnostico["codigo_municipio_ibge"] == "4220000").all())

    def test_paraiso_das_aguas_2012_excluido_apesar_de_valor_observado(self) -> None:
        linhas = _municipio_completo(
            "5006275", 2012, status_territorial="nao_existia_no_ano", municipio_fonte="Paraíso das Águas - MS",
        )
        df_long = pd.DataFrame(linhas)
        painel = analitico.build_painel_analitico(df_long)
        self.assertEqual(len(painel), 0)

        diagnostico = analitico.build_diagnostico_exclusao_territorial(df_long)
        self.assertEqual(len(diagnostico), 7)
        self.assertTrue((diagnostico["codigo_municipio_ibge"] == "5006275").all())

    # G. sigilo vira NA numérico e status sigilo permanece
    def test_sigilo_vira_na_numerico_status_preservado(self) -> None:
        linhas = _municipio_completo("1100015", 2019)
        # substitui a linha da variável 662 por sigilo
        linhas = [l for l in linhas if l["codigo_variavel_sidra"] != 662]
        linhas.append(_linha_long(
            "1100015", 2019, 662, valor_bruto="X", valor_numerico=None, status_valor_api="sigilo",
        ))
        painel = analitico.build_painel_analitico(pd.DataFrame(linhas))
        linha = painel.iloc[0]
        self.assertTrue(pd.isna(linha["salarios_remuneracoes_mil_reais_nominal"]))
        self.assertEqual(linha["status_salarios_remuneracoes_mil_reais_nominal"], "sigilo")

    # H. indisponível vira NA e status permanece
    def test_indisponivel_vira_na_status_preservado(self) -> None:
        linhas = _municipio_completo("1100015", 2019)
        linhas = [l for l in linhas if l["codigo_variavel_sidra"] != 707]
        linhas.append(_linha_long(
            "1100015", 2019, 707, valor_bruto="...", valor_numerico=None, status_valor_api="indisponivel",
        ))
        painel = analitico.build_painel_analitico(pd.DataFrame(linhas))
        linha = painel.iloc[0]
        self.assertTrue(pd.isna(linha["pessoal_ocupado_total"]))
        self.assertEqual(linha["status_pessoal_ocupado_total"], "indisponivel")

    # I. zero permanece zero
    def test_zero_real_permanece_zero_numerico(self) -> None:
        linhas = _municipio_completo("1100015", 2019)
        linhas = [l for l in linhas if l["codigo_variavel_sidra"] != 708]
        linhas.append(_linha_long(
            "1100015", 2019, 708, valor_bruto="-", valor_numerico=0.0, status_valor_api="zero_real",
        ))
        painel = analitico.build_painel_analitico(pd.DataFrame(linhas))
        linha = painel.iloc[0]
        self.assertEqual(linha["pessoal_ocupado_assalariado"], 0.0)
        self.assertFalse(pd.isna(linha["pessoal_ocupado_assalariado"]))
        self.assertEqual(linha["status_pessoal_ocupado_assalariado"], "zero_real")

    # J. desconhecido bloqueia
    def test_desconhecido_bloqueia_construcao(self) -> None:
        linhas = _municipio_completo("1100015", 2019)
        linhas = [l for l in linhas if l["codigo_variavel_sidra"] != 708]
        linhas.append(_linha_long(
            "1100015", 2019, 708, valor_bruto="N/D", valor_numerico=None, status_valor_api="desconhecido",
        ))
        with self.assertRaisesRegex(ValueError, "desconhecido"):
            analitico.build_painel_analitico(pd.DataFrame(linhas))

    # K. 1606 não determina exclusão
    def test_1606_sigilo_nao_exclui_municipio_ano(self) -> None:
        linhas = _municipio_completo("1100015", 2019)
        linhas = [l for l in linhas if l["codigo_variavel_sidra"] != 1606]
        linhas.append(_linha_long(
            "1100015", 2019, 1606, valor_bruto="X", valor_numerico=None, status_valor_api="sigilo",
        ))
        painel = analitico.build_painel_analitico(pd.DataFrame(linhas))
        self.assertEqual(len(painel), 1)
        linha = painel.iloc[0]
        self.assertTrue(pd.isna(linha["salario_medio_salarios_minimos_nominal"]))
        self.assertEqual(linha["status_salario_medio_salarios_minimos_nominal"], "sigilo")
        # demais variáveis continuam observadas normalmente
        self.assertEqual(linha["pessoal_ocupado_total"], 100.0)

    # L. 708/707 preservadas
    def test_708_e_707_preservadas_e_relacao_consistente(self) -> None:
        linhas = _municipio_completo("1100015", 2019)
        painel = analitico.build_painel_analitico(pd.DataFrame(linhas))
        linha = painel.iloc[0]
        self.assertIn("pessoal_ocupado_total", painel.columns)
        self.assertIn("pessoal_ocupado_assalariado", painel.columns)
        self.assertLessEqual(linha["pessoal_ocupado_assalariado"], linha["pessoal_ocupado_total"])


class TestAuditarPopulacao(unittest.TestCase):
    def test_separa_existente_e_nao_existente(self) -> None:
        linhas = (
            _municipio_completo("1100015", 2019, status_territorial="existia_no_ano")
            + _municipio_completo("4220000", 2012, status_territorial="nao_existia_no_ano")
        )
        auditoria = analitico.auditar_populacao(pd.DataFrame(linhas))
        self.assertEqual(auditoria["n_municipio_ano_existente"], 1)
        self.assertEqual(auditoria["n_municipio_ano_nao_existente"], 1)
        self.assertEqual(
            auditoria["municipio_ano_nao_existente"].iloc[0]["codigo_municipio_ibge"], "4220000",
        )


class TestValidatePainelAnalitico(unittest.TestCase):
    # M. 147 Fase II permanecem cobertos (versão sintética: 1 município Fase II)
    def test_fase_ii_coberto_nao_levanta_erro(self) -> None:
        linhas = _municipio_completo("1100015", 2019)
        df_long = pd.DataFrame(linhas)
        painel = analitico.build_painel_analitico(df_long)
        resultado = analitico.validate_painel_analitico(
            painel, df_long, fase_ii_codigos={"1100015"}, candidatos_codigos=set(),
        )
        self.assertEqual(resultado["fase_ii_municipios_cobertos"], 1)
        self.assertEqual(resultado["fase_ii_municipio_ano_cobertos"], 1)

    def test_fase_ii_ausente_levanta_erro(self) -> None:
        linhas = _municipio_completo("1100015", 2019, status_territorial="existia_no_ano")
        df_long = pd.DataFrame(linhas)
        painel = analitico.build_painel_analitico(df_long)
        with self.assertRaisesRegex(ValueError, "I:"):
            analitico.validate_painel_analitico(
                painel, df_long, fase_ii_codigos={"1100015", "3166600"}, candidatos_codigos=set(),
            )

    # N. 129 candidatos principais permanecem cobertos
    def test_candidatos_principais_cobertos_nao_levanta_erro(self) -> None:
        linhas = _municipio_completo("1100015", 2019)
        df_long = pd.DataFrame(linhas)
        painel = analitico.build_painel_analitico(df_long)
        resultado = analitico.validate_painel_analitico(
            painel, df_long, fase_ii_codigos=set(), candidatos_codigos={"1100015"},
        )
        self.assertEqual(resultado["candidatos_municipios_cobertos"], 1)

    def test_candidato_ausente_levanta_erro(self) -> None:
        linhas = _municipio_completo("1100015", 2019, status_territorial="existia_no_ano")
        df_long = pd.DataFrame(linhas)
        painel = analitico.build_painel_analitico(df_long)
        with self.assertRaisesRegex(ValueError, "J:"):
            analitico.validate_painel_analitico(
                painel, df_long, fase_ii_codigos=set(), candidatos_codigos={"1100015", "3166600"},
            )

    def test_708_maior_que_707_levanta_erro(self) -> None:
        linhas = _municipio_completo("1100015", 2019)
        linhas = [l for l in linhas if l["codigo_variavel_sidra"] not in (707, 708)]
        linhas.append(_linha_long("1100015", 2019, 707, valor_bruto="50", valor_numerico=50.0))
        linhas.append(_linha_long("1100015", 2019, 708, valor_bruto="80", valor_numerico=80.0))
        df_long = pd.DataFrame(linhas)
        painel = analitico.build_painel_analitico(df_long)
        with self.assertRaisesRegex(ValueError, "H:"):
            analitico.validate_painel_analitico(painel, df_long)

    def test_valor_negativo_levanta_erro(self) -> None:
        linhas = _municipio_completo("1100015", 2019)
        linhas = [l for l in linhas if l["codigo_variavel_sidra"] != 706]
        linhas.append(_linha_long("1100015", 2019, 706, valor_bruto="-5", valor_numerico=-5.0))
        df_long = pd.DataFrame(linhas)
        painel = analitico.build_painel_analitico(df_long)
        with self.assertRaisesRegex(ValueError, "G:"):
            analitico.validate_painel_analitico(painel, df_long)

    def test_anos_fora_da_janela_levanta_erro(self) -> None:
        linhas = _municipio_completo("1100015", 2050)
        df_long = pd.DataFrame(linhas)
        painel = analitico.build_painel_analitico(df_long)
        with self.assertRaisesRegex(ValueError, "F:"):
            analitico.validate_painel_analitico(painel, df_long)


class TestRelatorioMissing(unittest.TestCase):
    def test_missing_report_contabiliza_sigilo_e_indisponivel(self) -> None:
        linhas = _municipio_completo("1100015", 2019)
        linhas = [l for l in linhas if l["codigo_variavel_sidra"] != 662]
        linhas.append(_linha_long(
            "1100015", 2019, 662, valor_bruto="X", valor_numerico=None, status_valor_api="sigilo",
        ))
        painel = analitico.build_painel_analitico(pd.DataFrame(linhas))
        missing = analitico.relatorio_missing_por_variavel(painel)
        linha_662 = missing[missing["coluna"] == "salarios_remuneracoes_mil_reais_nominal"].iloc[0]
        self.assertEqual(linha_662["n_na"], 1)
        self.assertEqual(linha_662["n_sigilo"], 1)
        self.assertEqual(linha_662["n_total"], 1)


class TestBuildDiagnosticoExclusaoTerritorial(unittest.TestCase):
    def test_diagnostico_contem_apenas_nao_existentes(self) -> None:
        linhas = (
            _municipio_completo("1100015", 2019, status_territorial="existia_no_ano")
            + _municipio_completo("4220000", 2012, status_territorial="nao_existia_no_ano")
        )
        diagnostico = analitico.build_diagnostico_exclusao_territorial(pd.DataFrame(linhas))
        self.assertEqual(len(diagnostico), 7)
        self.assertTrue((diagnostico["codigo_municipio_ibge"] == "4220000").all())
        self.assertTrue((diagnostico["status_territorial"] == "nao_existia_no_ano").all())


class TestMapaVariavelColuna(unittest.TestCase):
    def test_mapa_cobre_exatamente_as_7_variaveis_esperadas(self) -> None:
        self.assertEqual(set(analitico.MAPA_VARIAVEL_COLUNA), cempre.VARIAVEIS_ESPERADAS)

    def test_1606_presente_e_marcada_opcional_no_contrato_original(self) -> None:
        self.assertIn(1606, analitico.MAPA_VARIAVEL_COLUNA)
        self.assertNotIn(1606, cempre.VARIAVEIS_OBRIGATORIAS)


if __name__ == "__main__":
    unittest.main()
