"""Testes da D16: descrição e auditoria da amostra causal materializada."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import analisa_amostra_causal as analise  # noqa: E402


def _amostra_sintetica() -> pd.DataFrame:
    linhas: list[dict] = []
    unidades = [
        ("1100015", "TRATADO_PRINCIPAL", 2009.0, True, False),
        ("3300704", "TRATADO_PRINCIPAL", 2010.0, True, False),
        ("1100023", "TRATADO_PRINCIPAL", 2011.0, True, False),
        ("1100031", "CONTROLE_NEVER_TREATED", None, False, True),
    ]
    for codigo, papel, coorte, candidato, controle in unidades:
        for ano in range(2007, 2020):
            cabo_2009 = codigo == "3300704" and ano == 2009
            linhas.append(
                {
                    "codigo_municipio_ibge": codigo,
                    "ano": ano,
                    "papel_causal": papel,
                    "candidato_amostra_principal": candidato if candidato else None,
                    "fl_elegivel_controle_candidato": controle,
                    "ano_coorte_candidata": coorte,
                    "coorte_g": coorte,
                    "tempo_relativo": ano - coorte if coorte is not None else None,
                    "elegivel_estimacao_principal": not cabo_2009,
                    "motivo_nao_elegibilidade_estimacao": (
                        "ANO_TRANSICAO_INSTITUCIONAL_CABO_FRIO_2009" if cabo_2009 else None
                    ),
                    "pessoal_ocupado_assalariado": float(ano - 2000),
                    "status_pessoal_ocupado_assalariado": "observado",
                }
            )
    return pd.DataFrame(linhas)


class TestValidacaoAmostra(unittest.TestCase):
    def test_valida_contagens_balanceamento_e_sobreposicao(self) -> None:
        resultado = analise.validar_amostra_causal(_amostra_sintetica())

        self.assertEqual(resultado["n_tratados"], 3)
        self.assertEqual(resultado["n_controles"], 1)
        self.assertEqual(resultado["n_unidades"], 4)
        self.assertEqual(resultado["n_linhas"], 52)
        self.assertEqual(resultado["sobreposicao_tratado_controle"], 0)
        self.assertEqual(resultado["unidades_painel_desbalanceado"], 0)

    def test_rejeita_codigo_excluido_por_sigilo(self) -> None:
        amostra = _amostra_sintetica()
        extra = amostra.loc[amostra.codigo_municipio_ibge.eq("1100031")].copy()
        extra["codigo_municipio_ibge"] = "5003900"

        with self.assertRaisesRegex(ValueError, "5003900"):
            analise.validar_amostra_causal(pd.concat([amostra, extra], ignore_index=True))

    def test_rejeita_sobreposicao_tratado_controle(self) -> None:
        amostra = _amostra_sintetica()
        amostra.loc[amostra.codigo_municipio_ibge.eq("1100015"), "fl_elegivel_controle_candidato"] = True

        with self.assertRaisesRegex(ValueError, "tratado.*controle"):
            analise.validar_amostra_causal(amostra)


class TestCoberturaEventTime(unittest.TestCase):
    def test_cobertura_event_time_respeita_mascara_cabo_frio(self) -> None:
        cobertura = analise.cobertura_event_time(_amostra_sintetica())
        linha_menos_um = cobertura.loc[cobertura.tempo_relativo.eq(-1)].iloc[0]

        self.assertEqual(int(linha_menos_um.n_tratados_no_painel), 3)
        self.assertEqual(int(linha_menos_um.n_tratados_elegiveis), 2)

    def test_janela_principal_distingue_populacao_de_cobertura_completa(self) -> None:
        diagnostico = analise.diagnostico_janelas(_amostra_sintetica())
        principal = diagnostico.loc[diagnostico.janela.eq("principal_k_-2_2")].iloc[0]

        self.assertEqual(int(principal.n_tratados_populacao), 3)
        self.assertEqual(int(principal.n_tratados_janela_completa_elegivel), 2)
        self.assertEqual(int(principal.perda_por_cobertura), 1)

    def test_sensibilidade_exclui_coorte_2009_e_exige_janela_completa(self) -> None:
        diagnostico = analise.diagnostico_janelas(_amostra_sintetica())
        sensibilidade = diagnostico.loc[diagnostico.janela.eq("sensibilidade_k_-3_2")].iloc[0]

        self.assertEqual(int(sensibilidade.n_tratados_populacao), 2)
        self.assertEqual(int(sensibilidade.n_tratados_janela_completa_elegivel), 1)
        self.assertEqual(int(sensibilidade.perda_por_cobertura), 1)


class TestArtefatoRealD16(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        caminho = Path(__file__).resolve().parents[1] / "data" / "processed" / "amostra_causal_cempre_2007_2019.parquet"
        cls.amostra = pd.read_parquet(caminho)

    def test_reproduz_dimensoes_d15(self) -> None:
        resultado = analise.validar_amostra_causal(self.amostra)

        self.assertEqual(resultado["n_tratados"], 129)
        self.assertEqual(resultado["n_controles"], 4963)
        self.assertEqual(resultado["n_unidades"], 5092)
        self.assertEqual(resultado["n_linhas"], 66196)
        self.assertEqual(resultado["n_linhas_elegiveis"], 66195)

    def test_reproduz_coortes_e_cobertura_completa_real(self) -> None:
        coortes = dict(
            zip(
                analise.distribuicao_coortes(self.amostra)["coorte_g"],
                analise.distribuicao_coortes(self.amostra)["n_tratados"],
            )
        )
        janelas = analise.diagnostico_janelas(self.amostra).set_index("janela")

        self.assertEqual(coortes, {2009: 21, 2010: 27, 2011: 66, 2012: 13, 2013: 2})
        self.assertEqual(int(janelas.loc["principal_k_-2_2", "n_tratados_populacao"]), 129)
        self.assertEqual(int(janelas.loc["principal_k_-2_2", "n_tratados_janela_completa_elegivel"]), 128)
        self.assertEqual(int(janelas.loc["sensibilidade_k_-3_2", "n_tratados_populacao"]), 108)
        self.assertEqual(int(janelas.loc["sensibilidade_k_-3_2", "n_tratados_janela_completa_elegivel"]), 107)


if __name__ == "__main__":
    unittest.main()
