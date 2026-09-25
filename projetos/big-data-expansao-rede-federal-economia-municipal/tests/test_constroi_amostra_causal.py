"""Testes sintéticos da construção da amostra causal congelada D15."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import constroi_amostra_causal as amostra_mod  # noqa: E402


def _painel_sintetico() -> pd.DataFrame:
    linhas: list[dict] = []
    unidades = [
        ("3300704", True, False, 2010),  # Cabo Frio
        ("1100015", True, False, 2009),
        ("1100023", False, True, None),
        ("5003900", False, True, None),  # sigilo estrutural D15
    ]
    for codigo, candidato, elegivel, coorte in unidades:
        for ano in range(2007, 2020):
            linhas.append(
                {
                    "codigo_municipio_ibge": codigo,
                    "ano": ano,
                    "candidato_amostra_principal": candidato,
                    "fl_elegivel_controle_candidato": elegivel,
                    "ano_coorte_candidata": coorte,
                    "ano_transicao": 2009 if codigo == "3300704" else pd.NA,
                    "primeiro_ano_completo": 2010 if codigo == "3300704" else pd.NA,
                    "pessoal_ocupado_assalariado": 10,
                    "status_pessoal_ocupado_assalariado": "observado",
                }
            )
    return pd.DataFrame(linhas)


class TestConstroiAmostraCausal(unittest.TestCase):
    def test_constroi_painel_base_e_mascara_cabo(self) -> None:
        amostra, exclusoes = amostra_mod.construir_amostra_causal(_painel_sintetico())

        self.assertEqual(amostra.codigo_municipio_ibge.nunique(), 3)
        self.assertEqual(len(amostra), 39)
        self.assertNotIn("5003900", set(amostra.codigo_municipio_ibge))
        self.assertEqual(int(amostra.elegivel_estimacao_principal.sum()), 38)
        cabo_2009 = amostra.loc[
            (amostra.codigo_municipio_ibge == "3300704") & (amostra.ano == 2009)
        ].iloc[0]
        self.assertFalse(cabo_2009.elegivel_estimacao_principal)
        self.assertEqual(cabo_2009.motivo_nao_elegibilidade_estimacao, "ANO_TRANSICAO_INSTITUCIONAL_CABO_FRIO_2009")
        self.assertEqual(exclusoes["tipo_exclusao"].tolist(), ["UNIDADE", "OBSERVACAO"])
        self.assertEqual(exclusoes["codigo_municipio_ibge"].tolist(), ["5003900", "3300704"])

    def test_recortes_de_janela_respeitam_coorte_e_elegibilidade(self) -> None:
        amostra, _ = amostra_mod.construir_amostra_causal(_painel_sintetico())
        principal = amostra_mod.selecionar_janela_principal(amostra)
        sensibilidade = amostra_mod.selecionar_janela_sensibilidade(amostra)

        self.assertEqual(principal.codigo_municipio_ibge.nunique(), 2)
        self.assertEqual(sensibilidade.codigo_municipio_ibge.nunique(), 1)
        self.assertEqual(set(sensibilidade.codigo_municipio_ibge), {"3300704"})

    def test_rejeita_unidade_selecionada_sem_13_anos(self) -> None:
        painel = _painel_sintetico()
        painel = painel.loc[~((painel.codigo_municipio_ibge == "1100015") & (painel.ano == 2019))]
        with self.assertRaisesRegex(ValueError, "13 anos"):
            amostra_mod.construir_amostra_causal(painel)


if __name__ == "__main__":
    unittest.main()
