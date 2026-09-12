"""Testes do pool candidato a controles sem exposição observada (2007-2019).

Execução:
    .venv\\Scripts\\python.exe -m unittest \
        tests.test_constroi_pool_candidato_controles -v

Todos os testes usam dados sintéticos pequenos — nenhum lê os Parquets
reais do cadastro nacional ou da lista Fase II.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import constroi_pool_candidato_controles as pool_mod  # noqa: E402


def _linha_resumo(
    codigo: str,
    sem_exposicao: bool = True,
    presente_13: bool = True,
    municipio: str = "Município Teste",
    uf: str = "RO",
    co_uf: str | None = None,
) -> dict:
    return {
        "codigo_municipio_ibge": codigo,
        "municipio": municipio,
        "uf": uf,
        "co_uf": co_uf if co_uf is not None else codigo[:2],
        "sem_exposicao_observada_2007_2019": sem_exposicao,
        "presente_nos_13_anos_do_universo": presente_13,
    }


def _resumo_df(rows: list[dict]) -> pd.DataFrame:
    """Constrói o DataFrame exatamente com os valores fornecidos, sem
    nenhuma coerção de tipo — uma coerção automática (`.astype(str)`,
    `.astype(bool)`) mascararia entradas adversariais (código nulo virando
    a string "None", flag não booleana virando True/False) antes de
    chegarem ao validador. Dados válidos devem ser passados já como
    valores Python válidos (códigos como string, flags como True/False)."""
    return pd.DataFrame(rows)


class TestBuildCadastroElegibilidade(unittest.TestCase):
    """Cobre os cenários de elegibilidade pedidos na especificação."""

    def test_nao_fase_ii_completo_sem_exposicao_e_elegivel(self) -> None:
        resumo = _resumo_df([_linha_resumo("1100015", sem_exposicao=True, presente_13=True)])
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes=set())
        row = cadastro.iloc[0]
        self.assertTrue(row["fl_elegivel_controle_candidato"])
        self.assertEqual(row["motivos_exclusao"], "")

    def test_fase_ii_mesmo_sem_exposicao_e_inelegivel(self) -> None:
        resumo = _resumo_df([_linha_resumo("1100015", sem_exposicao=True, presente_13=True)])
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes={"1100015"})
        row = cadastro.iloc[0]
        self.assertFalse(row["fl_elegivel_controle_candidato"])
        self.assertIn("fase_ii", row["motivos_exclusao"])

    def test_exposto_mesmo_nao_fase_ii_e_inelegivel(self) -> None:
        resumo = _resumo_df([_linha_resumo("1100015", sem_exposicao=False, presente_13=True)])
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes=set())
        row = cadastro.iloc[0]
        self.assertFalse(row["fl_elegivel_controle_candidato"])
        self.assertIn("exposicao_observada", row["motivos_exclusao"])

    def test_universo_incompleto_e_sem_exposicao_e_inelegivel(self) -> None:
        resumo = _resumo_df([_linha_resumo("1100015", sem_exposicao=True, presente_13=False)])
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes=set())
        row = cadastro.iloc[0]
        self.assertFalse(row["fl_elegivel_controle_candidato"])
        self.assertIn("universo_incompleto", row["motivos_exclusao"])

    def test_municipio_com_mais_de_um_motivo_registra_todos(self) -> None:
        resumo = _resumo_df([_linha_resumo("1100015", sem_exposicao=False, presente_13=False)])
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes={"1100015"})
        row = cadastro.iloc[0]
        motivos = set(row["motivos_exclusao"].split(";"))
        self.assertEqual(motivos, {"exposicao_observada", "universo_incompleto", "fase_ii"})

    def test_flags_de_exclusao_sao_inverso_logico_esperado(self) -> None:
        resumo = _resumo_df([
            _linha_resumo("1100015", sem_exposicao=True, presente_13=True),
            _linha_resumo("1100023", sem_exposicao=False, presente_13=False),
        ])
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes={"1100023"})
        indexado = cadastro.set_index("codigo_municipio_ibge")
        self.assertFalse(indexado.loc["1100015", "fl_excluir_exposicao_observada"])
        self.assertFalse(indexado.loc["1100015", "fl_excluir_universo_incompleto"])
        self.assertFalse(indexado.loc["1100015", "fl_excluir_fase_ii"])
        self.assertTrue(indexado.loc["1100023", "fl_excluir_exposicao_observada"])
        self.assertTrue(indexado.loc["1100023", "fl_excluir_universo_incompleto"])
        self.assertTrue(indexado.loc["1100023", "fl_excluir_fase_ii"])


class TestValidateResumoNacionalNegativos(unittest.TestCase):
    def test_rejeita_duplicidade_de_codigo(self) -> None:
        resumo = _resumo_df([_linha_resumo("1100015"), _linha_resumo("1100015")])
        with self.assertRaises(ValueError) as ctx:
            pool_mod.validate_resumo_nacional(resumo)
        self.assertIn("duplicad", str(ctx.exception))

    def test_rejeita_codigo_invalido(self) -> None:
        # Fixture pequena (1 linha) de propósito: se a validação de formato
        # for desativada, a única forma de este teste continuar a levantar
        # ValueError seria pela checagem de cardinalidade (!= 5.570) — por
        # isso a mensagem exigida é específica da validação de formato, não
        # apenas "algum ValueError".
        resumo = _resumo_df([_linha_resumo("110001")])  # 6 dígitos
        with self.assertRaisesRegex(
            ValueError, r"resumo nacional de exposição: codigo_municipio_ibge inválido"
        ):
            pool_mod.validate_resumo_nacional(resumo)

    def test_rejeita_codigo_nulo(self) -> None:
        resumo = _resumo_df([_linha_resumo("1100015")])
        resumo.loc[0, "codigo_municipio_ibge"] = None
        with self.assertRaisesRegex(
            ValueError, r"resumo nacional de exposição: codigo_municipio_ibge contém valor nulo"
        ):
            pool_mod.validate_resumo_nacional(resumo)

    def test_rejeita_flag_invalida(self) -> None:
        resumo = _resumo_df([_linha_resumo("1100015"), _linha_resumo("1100023")])
        resumo["sem_exposicao_observada_2007_2019"] = ["sim", "nao"]  # não booleano
        with self.assertRaisesRegex(
            ValueError,
            r"resumo nacional de exposição: sem_exposicao_observada_2007_2019 deve ser booleana",
        ):
            pool_mod.validate_resumo_nacional(resumo)

    def test_rejeita_flag_nula(self) -> None:
        resumo = _resumo_df([_linha_resumo("1100015"), _linha_resumo("1100023")])
        resumo["presente_nos_13_anos_do_universo"] = pd.array([True, pd.NA], dtype="boolean")
        with self.assertRaisesRegex(
            ValueError,
            r"resumo nacional de exposição: presente_nos_13_anos_do_universo contém valor nulo",
        ):
            pool_mod.validate_resumo_nacional(resumo)


class TestValidateFaseIIMunicipiosNegativos(unittest.TestCase):
    def test_rejeita_duplicidade(self) -> None:
        fase_ii = pd.DataFrame({"codigo_municipio_ibge": ["1100015", "1100015"]})
        with self.assertRaises(ValueError) as ctx:
            pool_mod.validate_fase_ii_municipios(fase_ii)
        self.assertIn("duplicad", str(ctx.exception))

    def test_rejeita_codigo_invalido(self) -> None:
        # Fixture de 1 linha: sem mensagem específica, uma checagem de
        # cardinalidade (!= 147) desativada-por-engano na validação de
        # formato ainda deixaria este teste passar pelo motivo errado.
        fase_ii = pd.DataFrame({"codigo_municipio_ibge": ["ABC1234"]})
        with self.assertRaisesRegex(ValueError, r"lista Fase II: codigo_municipio_ibge inválido"):
            pool_mod.validate_fase_ii_municipios(fase_ii)

    def test_rejeita_codigo_nulo(self) -> None:
        fase_ii = pd.DataFrame({"codigo_municipio_ibge": [None]})
        with self.assertRaisesRegex(
            ValueError, r"lista Fase II: codigo_municipio_ibge contém valor nulo"
        ):
            pool_mod.validate_fase_ii_municipios(fase_ii)


class TestValidateFaseIISubsetUniverso(unittest.TestCase):
    def test_rejeita_codigo_fase_ii_fora_do_universo(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            pool_mod.validate_fase_ii_subset_universo({"1100015", "9999999"}, {"1100015"})
        self.assertIn("9999999", str(ctx.exception))

    def test_aceita_quando_fase_ii_subset_do_universo(self) -> None:
        pool_mod.validate_fase_ii_subset_universo({"1100015"}, {"1100015", "1100023"})  # não deve levantar


class TestValidateCadastroElegibilidadeNegativos(unittest.TestCase):
    def _cadastro_valido(self) -> tuple[pd.DataFrame, pd.DataFrame, set[str]]:
        resumo = _resumo_df([
            _linha_resumo("1100015", sem_exposicao=True, presente_13=True),
            _linha_resumo("1100023", sem_exposicao=False, presente_13=True),
            _linha_resumo("1100031", sem_exposicao=True, presente_13=False),
        ])
        fase_ii_codes = {"1100023"}
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes)
        return cadastro, resumo, fase_ii_codes

    def test_cadastro_valido_nao_levanta(self) -> None:
        cadastro, resumo, fase_ii_codes = self._cadastro_valido()
        pool_mod.validate_cadastro_elegibilidade(cadastro, resumo, fase_ii_codes)  # não deve levantar

    def test_rejeita_marcacao_fase_ii_incoerente(self) -> None:
        cadastro, resumo, fase_ii_codes = self._cadastro_valido()
        cadastro.loc[cadastro["codigo_municipio_ibge"] == "1100015", "fl_municipio_fase_ii"] = True
        with self.assertRaises(ValueError):
            pool_mod.validate_cadastro_elegibilidade(cadastro, resumo, fase_ii_codes)

    def test_rejeita_elegibilidade_incoerente_com_regra_logica(self) -> None:
        cadastro, resumo, fase_ii_codes = self._cadastro_valido()
        cadastro.loc[cadastro["codigo_municipio_ibge"] == "1100023", "fl_elegivel_controle_candidato"] = True
        with self.assertRaises(ValueError):
            pool_mod.validate_cadastro_elegibilidade(cadastro, resumo, fase_ii_codes)

    def test_rejeita_fase_ii_elegivel(self) -> None:
        cadastro, resumo, fase_ii_codes = self._cadastro_valido()
        idx = cadastro["codigo_municipio_ibge"] == "1100023"
        cadastro.loc[idx, "fl_elegivel_controle_candidato"] = True
        cadastro.loc[idx, "motivos_exclusao"] = ""
        with self.assertRaises(ValueError):
            pool_mod.validate_cadastro_elegibilidade(cadastro, resumo, fase_ii_codes)

    def test_rejeita_motivos_exclusao_incoerente(self) -> None:
        cadastro, resumo, fase_ii_codes = self._cadastro_valido()
        idx = cadastro["codigo_municipio_ibge"] == "1100023"
        cadastro.loc[idx, "motivos_exclusao"] = "universo_incompleto"  # motivo errado
        with self.assertRaises(ValueError):
            pool_mod.validate_cadastro_elegibilidade(cadastro, resumo, fase_ii_codes)

    def test_rejeita_conjunto_municipios_diferente_do_resumo(self) -> None:
        cadastro, resumo, fase_ii_codes = self._cadastro_valido()
        cadastro_reduzido = cadastro.iloc[:-1].copy()
        with self.assertRaises(ValueError):
            pool_mod.validate_cadastro_elegibilidade(cadastro_reduzido, resumo, fase_ii_codes)


class TestBuildPoolFiltrado(unittest.TestCase):
    def test_pool_contem_apenas_elegiveis(self) -> None:
        resumo = _resumo_df([
            _linha_resumo("1100015", sem_exposicao=True, presente_13=True),
            _linha_resumo("1100023", sem_exposicao=False, presente_13=True),
        ])
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes=set())
        pool = pool_mod.build_pool_filtrado(cadastro)
        self.assertEqual(len(pool), 1)
        self.assertEqual(pool.iloc[0]["codigo_municipio_ibge"], "1100015")

    def test_pool_e_selecao_exata_do_cadastro(self) -> None:
        resumo = _resumo_df([
            _linha_resumo("1100015", sem_exposicao=True, presente_13=True),
            _linha_resumo("1100023", sem_exposicao=False, presente_13=True),
        ])
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes=set())
        pool = pool_mod.build_pool_filtrado(cadastro)
        esperado = cadastro.loc[cadastro["fl_elegivel_controle_candidato"]].reset_index(drop=True)
        pd.testing.assert_frame_equal(pool.reset_index(drop=True), esperado)


class TestValidatePoolFiltradoNegativos(unittest.TestCase):
    def _cadastro_e_pool(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        resumo = _resumo_df([
            _linha_resumo("1100015", sem_exposicao=True, presente_13=True),
            _linha_resumo("1100023", sem_exposicao=False, presente_13=True),
        ])
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes=set())
        pool = pool_mod.build_pool_filtrado(cadastro)
        return cadastro, pool

    def test_pool_valido_nao_levanta(self) -> None:
        cadastro, pool = self._cadastro_e_pool()
        pool_mod.validate_pool_filtrado(pool, cadastro)  # não deve levantar

    def test_rejeita_pool_com_municipio_nao_elegivel(self) -> None:
        cadastro, pool = self._cadastro_e_pool()
        linha_inelegivel = cadastro.loc[~cadastro["fl_elegivel_controle_candidato"]]
        pool_contaminado = pd.concat([pool, linha_inelegivel], ignore_index=True)
        with self.assertRaises(ValueError):
            pool_mod.validate_pool_filtrado(pool_contaminado, cadastro)

    def test_rejeita_pool_com_duplicidade(self) -> None:
        cadastro, pool = self._cadastro_e_pool()
        pool_duplicado = pd.concat([pool, pool], ignore_index=True)
        with self.assertRaises(ValueError):
            pool_mod.validate_pool_filtrado(pool_duplicado, cadastro)

    def test_rejeita_pool_divergente_do_cadastro(self) -> None:
        cadastro, pool = self._cadastro_e_pool()
        pool_alterado = pool.copy()
        pool_alterado.loc[0, "municipio"] = "Nome Alterado"
        with self.assertRaises(ValueError):
            pool_mod.validate_pool_filtrado(pool_alterado, cadastro)


class TestBuildResumoDiagnostico(unittest.TestCase):
    def test_contagens_batem_com_cadastro(self) -> None:
        resumo = _resumo_df([
            _linha_resumo("1100015", sem_exposicao=True, presente_13=True),
            _linha_resumo("1100023", sem_exposicao=False, presente_13=True),
            _linha_resumo("1100031", sem_exposicao=True, presente_13=False),
        ])
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes={"1100023"})
        diagnostico = pool_mod.build_resumo_diagnostico(cadastro)
        valores = dict(zip(diagnostico["metrica"], diagnostico["valor"]))
        self.assertEqual(valores["total_municipios"], 3)
        self.assertEqual(valores["elegivel_controle_candidato"], 1)
        self.assertEqual(valores["pertence_fase_ii"], 1)
        self.assertEqual(valores["excluido_por_universo_incompleto"], 1)

    def test_sobreposicao_entre_motivos_contabilizada(self) -> None:
        resumo = _resumo_df([
            _linha_resumo("1100015", sem_exposicao=False, presente_13=False),
        ])
        cadastro = pool_mod.build_cadastro_elegibilidade(resumo, fase_ii_codes={"1100015"})
        diagnostico = pool_mod.build_resumo_diagnostico(cadastro)
        valores = dict(zip(diagnostico["metrica"], diagnostico["valor"]))
        self.assertEqual(valores["sobreposicao_tres_motivos"], 1)


class TestNomesDeArquivos(unittest.TestCase):
    def test_nomes_exatos_dos_artefatos(self) -> None:
        self.assertEqual(pool_mod.OUT_CADASTRO.name, "cadastro_elegibilidade_controles_2007_2019.parquet")
        self.assertEqual(
            pool_mod.OUT_POOL.name, "pool_candidato_controles_sem_exposicao_2007_2019.parquet"
        )
        self.assertEqual(pool_mod.OUT_DIAGNOSTICO.name, "resumo_pool_candidato_controles.csv")


if __name__ == "__main__":
    unittest.main()
