"""Testes do diagnóstico de integração funcional via Arranjos Populacionais
(pool candidato x Fase II).

Execução:
    .venv\\Scripts\\python.exe -m unittest \
        tests.test_constroi_diagnostico_arranjos_populacionais_fase_ii -v

Todos os testes usam dados sintéticos pequenos — nenhum lê os Parquets ou
a planilha XLSX reais, e nenhum acessa a internet.
"""
from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import constroi_diagnostico_arranjos_populacionais_fase_ii as diag  # noqa: E402

N_POOL = diag.N_POOL_ESPERADO
N_FASE_II = diag.N_FASE_II_ESPERADO


# ---------------------------------------------------------------------------
# Helpers de construção de dados sintéticos
# ---------------------------------------------------------------------------


def _pool_row(codigo: str, municipio: str = "Candidato Teste", uf: str = "RO") -> dict:
    return {"codigo_municipio_ibge": codigo, "municipio": municipio, "uf": uf}


def _fase_ii_row(codigo: str, municipio: str = "Tratado Teste", uf: str = "RO") -> dict:
    return {"codigo_municipio_ibge": codigo, "municipio": municipio, "uf": uf}


def _dist_row(codigo: str, distancia: float, ate_25: bool, ate_50: bool, ate_100: bool) -> dict:
    return {
        "codigo_municipio_ibge": codigo,
        "distancia_sedes_km": distancia,
        "fl_ate_25_km": ate_25, "fl_ate_50_km": ate_50, "fl_ate_100_km": ate_100,
    }


def _pool_completo(sobrescreve: dict[int, dict] | None = None) -> pd.DataFrame:
    """Pool sintético de tamanho real (4.964), para que testes de código
    inválido/nulo/duplicado não sejam mascarados por um erro de
    cardinalidade anterior na cadeia de validação."""
    sobrescreve = sobrescreve or {}
    linhas = []
    for i in range(N_POOL):
        linha = _pool_row(str(1100015 + i))
        linha.update(sobrescreve.get(i, {}))
        linhas.append(linha)
    return pd.DataFrame(linhas)


def _fase_ii_completo(sobrescreve: dict[int, dict] | None = None) -> pd.DataFrame:
    sobrescreve = sobrescreve or {}
    linhas = []
    for i in range(N_FASE_II):
        linha = _fase_ii_row(str(1200203 + i))
        linha.update(sobrescreve.get(i, {}))
        linhas.append(linha)
    return pd.DataFrame(linhas)


def _dist_completo(pool: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [_dist_row(c, 500.0, False, False, False) for c in pool["codigo_municipio_ibge"]]
    )


def _pares(*grupos: tuple[str, list[str]]) -> list[tuple[str, int]]:
    """Constrói a lista (nome_arranjo, codigo) no mesmo formato devolvido
    por `load_arranjos_bruto`."""
    pares = []
    for nome, codigos in grupos:
        for c in codigos:
            pares.append((nome, int(c)))
    return pares


# ---------------------------------------------------------------------------
# Validações dos insumos autorizados
# ---------------------------------------------------------------------------


class TestValidatePoolCandidato(unittest.TestCase):
    def test_rejeita_cardinalidade_errada(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015")])
        with self.assertRaisesRegex(ValueError, rf"pool candidato a controles: esperado exatamente {N_POOL}"):
            diag.validate_pool_candidato(pool)

    def test_rejeita_codigo_invalido(self) -> None:
        pool = _pool_completo({0: {"codigo_municipio_ibge": "110001"}})  # 6 dígitos
        with self.assertRaisesRegex(ValueError, r"pool candidato a controles: codigo_municipio_ibge inválido"):
            diag.validate_pool_candidato(pool)

    def test_rejeita_codigo_nulo(self) -> None:
        pool = _pool_completo({0: {"codigo_municipio_ibge": None}})
        with self.assertRaisesRegex(ValueError, r"pool candidato a controles: codigo_municipio_ibge contém valor nulo"):
            diag.validate_pool_candidato(pool)

    def test_rejeita_codigo_duplicado(self) -> None:
        pool = _pool_completo().iloc[:-1].copy()
        pool = pd.concat([pool, pool.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, r"pool candidato a controles: codigo_municipio_ibge duplicado"):
            diag.validate_pool_candidato(pool)


class TestValidateFaseIIMunicipios(unittest.TestCase):
    def test_rejeita_cardinalidade_errada(self) -> None:
        fase_ii = pd.DataFrame([_fase_ii_row("1200203")])
        with self.assertRaisesRegex(ValueError, rf"lista Fase II: esperado exatamente {N_FASE_II}"):
            diag.validate_fase_ii_municipios(fase_ii)


# ---------------------------------------------------------------------------
# Composição de arranjos populacionais
# ---------------------------------------------------------------------------


class TestBuildArranjosPopulacionais(unittest.TestCase):
    def test_reconcilia_codigo_e_gera_slug_do_nome(self) -> None:
        pares = _pares(("Adamantina - Lucília/SP", ["3500105", "3527405"]))
        arranjos = diag.build_arranjos_populacionais(pares)
        self.assertEqual(set(arranjos["codigo_municipio_ibge"]), {"3500105", "3527405"})
        self.assertEqual(arranjos["nome_arranjo_populacional"].unique().tolist(), ["Adamantina - Lucília/SP"])
        self.assertTrue((arranjos["codigo_arranjo_populacional"] == "ADAMANTINA_LUCILIA_SP").all())

    def test_rejeita_codigo_nulo_na_composicao_bruta(self) -> None:
        pares = [("Arranjo Teste", None)]
        with self.assertRaisesRegex(ValueError, r"arranjos populacionais IBGE 2010: código de município contém valor nulo"):
            diag.build_arranjos_populacionais(pares)


class TestValidateArranjosPopulacionais(unittest.TestCase):
    def test_aceita_composicao_valida(self) -> None:
        arranjos = diag.build_arranjos_populacionais(_pares(("Arranjo A", ["1100015", "1100023"])))
        diag.validate_arranjos_populacionais(arranjos)  # não deve levantar

    def test_rejeita_municipio_em_mais_de_um_arranjo(self) -> None:
        arranjos = diag.build_arranjos_populacionais(
            _pares(("Arranjo A", ["1100015"]), ("Arranjo B", ["1100015"]))
        )
        with self.assertRaisesRegex(
            ValueError, r"arranjos populacionais IBGE 2010: codigo_municipio_ibge duplicado"
        ):
            diag.validate_arranjos_populacionais(arranjos)


# ---------------------------------------------------------------------------
# build_diagnostico
# ---------------------------------------------------------------------------


class TestBuildDiagnostico(unittest.TestCase):
    def test_candidato_sem_arranjo(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015")])
        fase_ii = pd.DataFrame([_fase_ii_row("1200203")])
        dist = _dist_completo(pool)
        arranjos = diag.build_arranjos_populacionais(_pares(("Outro Arranjo", ["9999999"])))
        resultado = diag.build_diagnostico(pool, fase_ii, dist, arranjos)
        row = resultado.iloc[0]
        self.assertFalse(row["fl_pertence_arranjo_populacional"])
        self.assertTrue(pd.isna(row["codigo_arranjo_populacional"]))
        self.assertTrue(pd.isna(row["nome_arranjo_populacional"]))
        self.assertEqual(row["quantidade_fase_ii_no_arranjo"], 0)
        self.assertEqual(row["codigos_fase_ii_no_arranjo"], "")
        self.assertFalse(row["fl_mesmo_arranjo_populacional_fase_ii"])

    def test_arranjo_sem_fase_ii(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015")])
        fase_ii = pd.DataFrame([_fase_ii_row("1200203")])
        dist = _dist_completo(pool)
        arranjos = diag.build_arranjos_populacionais(
            _pares(("Arranjo A", ["1100015"]), ("Arranjo B", ["1200203"]))
        )
        resultado = diag.build_diagnostico(pool, fase_ii, dist, arranjos)
        row = resultado.iloc[0]
        self.assertTrue(row["fl_pertence_arranjo_populacional"])
        self.assertEqual(row["quantidade_fase_ii_no_arranjo"], 0)
        self.assertFalse(row["fl_mesmo_arranjo_populacional_fase_ii"])

    def test_arranjo_com_um_fase_ii(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015")])
        fase_ii = pd.DataFrame([_fase_ii_row("1200203")])
        dist = _dist_completo(pool)
        arranjos = diag.build_arranjos_populacionais(
            _pares(("Arranjo A", ["1100015", "1200203"]))
        )
        resultado = diag.build_diagnostico(pool, fase_ii, dist, arranjos)
        row = resultado.iloc[0]
        self.assertTrue(row["fl_mesmo_arranjo_populacional_fase_ii"])
        self.assertEqual(row["quantidade_fase_ii_no_arranjo"], 1)
        self.assertEqual(row["codigos_fase_ii_no_arranjo"], "1200203")

    def test_arranjo_com_varios_fase_ii_lista_deterministica_ordenada(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015")])
        fase_ii = pd.DataFrame([_fase_ii_row("1200400"), _fase_ii_row("1200203")])
        dist = _dist_completo(pool)
        arranjos = diag.build_arranjos_populacionais(
            _pares(("Arranjo A", ["1100015", "1200400", "1200203"]))
        )
        resultado = diag.build_diagnostico(pool, fase_ii, dist, arranjos)
        row = resultado.iloc[0]
        self.assertEqual(row["quantidade_fase_ii_no_arranjo"], 2)
        # ordenado pelo menor código primeiro, independentemente da ordem
        # de entrada em `fase_ii` (1200400 foi passado antes de 1200203).
        self.assertEqual(row["codigos_fase_ii_no_arranjo"], "1200203;1200400")

    def test_preserva_distancias_sem_alteracao(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015")])
        fase_ii = pd.DataFrame([_fase_ii_row("1200203")])
        dist = pd.DataFrame([_dist_row("1100015", 37.5, False, True, True)])
        arranjos = diag.build_arranjos_populacionais(_pares(("Arranjo A", ["9999999"])))
        resultado = diag.build_diagnostico(pool, fase_ii, dist, arranjos)
        row = resultado.iloc[0]
        self.assertEqual(row["distancia_sedes_km"], 37.5)
        self.assertFalse(row["fl_ate_25_km"])
        self.assertTrue(row["fl_ate_50_km"])
        self.assertTrue(row["fl_ate_100_km"])

    def test_merge_nao_usa_nome_do_municipio(self) -> None:
        """O nome do candidato em `pool` e o nome/UF completamente distintos
        na fonte de arranjos (que nem carrega nome de município) não devem
        influenciar o resultado — o pertencimento é decidido só pelo código."""
        pool = pd.DataFrame([_pool_row("1100015", municipio="Nome Qualquer", uf="ZZ")])
        fase_ii = pd.DataFrame([_fase_ii_row("1200203", municipio="Outro Nome", uf="ZZ")])
        dist = _dist_completo(pool)
        arranjos = diag.build_arranjos_populacionais(_pares(("Arranjo A", ["1100015", "1200203"])))
        resultado = diag.build_diagnostico(pool, fase_ii, dist, arranjos)
        self.assertTrue(resultado.iloc[0]["fl_mesmo_arranjo_populacional_fase_ii"])
        self.assertEqual(resultado.iloc[0]["municipio"], "Nome Qualquer")  # herdado do pool, não do arranjo

    def test_rejeita_candidato_sem_distancia_precalculada(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015"), _pool_row("1100023")])
        fase_ii = pd.DataFrame([_fase_ii_row("1200203")])
        dist = pd.DataFrame([_dist_row("1100015", 10.0, True, True, True)])  # falta 1100023
        arranjos = diag.build_arranjos_populacionais(_pares(("Arranjo A", ["9999999"])))
        with self.assertRaisesRegex(ValueError, r"diagnóstico: candidato\(s\) sem distância pré-calculada"):
            diag.build_diagnostico(pool, fase_ii, dist, arranjos)


# ---------------------------------------------------------------------------
# validate_diagnostico
# ---------------------------------------------------------------------------


class TestValidateDiagnosticoNegativos(unittest.TestCase):
    def _diagnostico_valido(self):
        pool = pd.DataFrame([_pool_row("1100015"), _pool_row("1100031")])
        fase_ii = pd.DataFrame([_fase_ii_row("1200203")])
        dist = _dist_completo(pool)
        arranjos = diag.build_arranjos_populacionais(
            _pares(("Arranjo A", ["1100015", "1200203"]))
        )
        resultado = diag.build_diagnostico(pool, fase_ii, dist, arranjos)
        return resultado, pool, {"1200203"}, dist

    def test_diagnostico_valido_nao_levanta(self) -> None:
        resultado, pool, fase_ii_codes, dist = self._diagnostico_valido()
        diag.validate_diagnostico(resultado, pool, fase_ii_codes, dist)  # não deve levantar

    def test_rejeita_cardinalidade_diferente_do_pool(self) -> None:
        resultado, pool, fase_ii_codes, dist = self._diagnostico_valido()
        reduzido = resultado.iloc[:1].copy()
        with self.assertRaisesRegex(ValueError, r"diagnóstico de arranjos populacionais: esperado exatamente"):
            diag.validate_diagnostico(reduzido, pool, fase_ii_codes, dist)

    def test_rejeita_conjunto_de_candidatos_alterado(self) -> None:
        resultado, pool, fase_ii_codes, dist = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado.loc[0, "codigo_municipio_ibge"] = "9999999"
        with self.assertRaisesRegex(ValueError, r"diagnóstico de arranjos populacionais: conjunto de candidatos"):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes, dist)

    def test_rejeita_flag_pertence_nula(self) -> None:
        resultado, pool, fase_ii_codes, dist = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado["fl_pertence_arranjo_populacional"] = alterado["fl_pertence_arranjo_populacional"].astype(object)
        alterado.loc[0, "fl_pertence_arranjo_populacional"] = None
        with self.assertRaisesRegex(
            ValueError, r"diagnóstico de arranjos populacionais: fl_pertence_arranjo_populacional contém valor nulo"
        ):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes, dist)

    def test_rejeita_flag_com_dtype_invalido(self) -> None:
        resultado, pool, fase_ii_codes, dist = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado["fl_mesmo_arranjo_populacional_fase_ii"] = alterado["fl_mesmo_arranjo_populacional_fase_ii"].astype(int)
        with self.assertRaisesRegex(
            ValueError, r"diagnóstico de arranjos populacionais: fl_mesmo_arranjo_populacional_fase_ii deve ser booleana"
        ):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes, dist)

    def test_rejeita_candidato_sem_arranjo_com_codigo_preenchido(self) -> None:
        resultado, pool, fase_ii_codes, dist = self._diagnostico_valido()
        alterado = resultado.copy()
        idx = alterado["codigo_municipio_ibge"] == "1100031"  # candidato sem arranjo nesta fixture
        alterado.loc[idx, "codigo_arranjo_populacional"] = "ALGUM_ARRANJO"
        with self.assertRaisesRegex(
            ValueError, r"diagnóstico de arranjos populacionais: candidato\(s\) sem arranjo com codigo_arranjo_populacional não nulo"
        ):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes, dist)

    def test_rejeita_quantidade_incoerente_com_lista(self) -> None:
        resultado, pool, fase_ii_codes, dist = self._diagnostico_valido()
        alterado = resultado.copy()
        idx = alterado["codigo_municipio_ibge"] == "1100015"
        alterado.loc[idx, "quantidade_fase_ii_no_arranjo"] = 5
        with self.assertRaisesRegex(
            ValueError, r"diagnóstico de arranjos populacionais: quantidade_fase_ii_no_arranjo não bate com a lista"
        ):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes, dist)

    def test_rejeita_flag_incoerente_com_quantidade(self) -> None:
        resultado, pool, fase_ii_codes, dist = self._diagnostico_valido()
        alterado = resultado.copy()
        idx = alterado["codigo_municipio_ibge"] == "1100015"
        alterado.loc[idx, "fl_mesmo_arranjo_populacional_fase_ii"] = False
        with self.assertRaisesRegex(
            ValueError, r"diagnóstico de arranjos populacionais: fl_mesmo_arranjo_populacional_fase_ii não é coerente"
        ):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes, dist)

    def test_rejeita_lista_nao_ordenada(self) -> None:
        resultado, pool, fase_ii_codes, dist = self._diagnostico_valido()
        alterado = resultado.copy()
        # Fixture com 2 tratados no mesmo arranjo, fora de ordem.
        idx = alterado["codigo_municipio_ibge"] == "1100015"
        alterado.loc[idx, "codigos_fase_ii_no_arranjo"] = "1200400;1200203"
        alterado.loc[idx, "quantidade_fase_ii_no_arranjo"] = 2
        with self.assertRaisesRegex(
            ValueError, r"diagnóstico de arranjos populacionais: lista codigos_fase_ii_no_arranjo não está ordenada"
        ):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes, dist)

    def test_rejeita_codigo_fora_da_fase_ii_na_lista(self) -> None:
        resultado, pool, fase_ii_codes, dist = self._diagnostico_valido()
        alterado = resultado.copy()
        idx = alterado["codigo_municipio_ibge"] == "1100015"
        alterado.loc[idx, "codigos_fase_ii_no_arranjo"] = "8888888"
        with self.assertRaisesRegex(
            ValueError, r"diagnóstico de arranjos populacionais: código\(s\) em codigos_fase_ii_no_arranjo fora do conjunto oficial"
        ):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes, dist)

    def test_rejeita_distancia_alterada_em_relacao_ao_original(self) -> None:
        resultado, pool, fase_ii_codes, dist = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado.loc[0, "distancia_sedes_km"] = alterado.loc[0, "distancia_sedes_km"] + 1.0
        with self.assertRaisesRegex(
            ValueError, r"diagnóstico de arranjos populacionais: coluna distancia_sedes_km foi alterada"
        ):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes, dist)


# ---------------------------------------------------------------------------
# build_resumo_diagnostico — reconciliação
# ---------------------------------------------------------------------------


class TestBuildResumoDiagnostico(unittest.TestCase):
    def test_reconciliacao_contagens_com_diagnostico(self) -> None:
        pool = pd.DataFrame([
            _pool_row("1100015", uf="RO"), _pool_row("1100031", uf="RO"), _pool_row("1200800", uf="AC"),
        ])
        fase_ii = pd.DataFrame([_fase_ii_row("1200203")])
        dist = _dist_completo(pool)
        arranjos = diag.build_arranjos_populacionais(
            _pares(("Arranjo A", ["1100015", "1200203"]), ("Arranjo B", ["1100031"]))
        )
        diagnostico = diag.build_diagnostico(pool, fase_ii, dist, arranjos)
        resumo_geral, resumo_uf, resumo_regiao = diag.build_resumo_diagnostico(diagnostico)
        valores = dict(zip(resumo_geral["metrica"], resumo_geral["valor"]))

        self.assertEqual(valores["total_candidatos"], 3)
        self.assertEqual(valores["candidatos_em_algum_arranjo"], int(diagnostico["fl_pertence_arranjo_populacional"].sum()))
        self.assertEqual(valores["candidatos_mesmo_arranjo_fase_ii"], int(diagnostico["fl_mesmo_arranjo_populacional_fase_ii"].sum()))
        self.assertEqual(
            valores["candidatos_em_arranjo_sem_fase_ii"],
            int((diagnostico["fl_pertence_arranjo_populacional"] & ~diagnostico["fl_mesmo_arranjo_populacional_fase_ii"]).sum()),
        )
        self.assertEqual(resumo_uf["total_candidatos"].sum(), len(diagnostico))
        self.assertEqual(resumo_regiao["total_candidatos"].sum(), len(diagnostico))


# ---------------------------------------------------------------------------
# Garantia de ausência de outcomes econômicos
# ---------------------------------------------------------------------------


class TestNaoUsaOutcomesEconomicos(unittest.TestCase):
    def test_fontes_lidas_nao_referenciam_outcomes(self) -> None:
        caminhos = [
            str(diag.POOL_CANDIDATO_PATH), str(diag.FASE_II_MUNICIPIOS_PATH),
            str(diag.DIAGNOSTICO_DISTANCIAS_PATH), str(diag.ARRANJOS_BRUTO_PATH),
        ]
        proibidos = ["cempre", "rais", "pib"]
        for caminho in caminhos:
            for p in proibidos:
                self.assertNotIn(p, caminho.lower(), f"caminho de fonte lida referencia outcome proibido: {caminho}")

    def test_codigo_fonte_nao_realiza_matching_ou_propensity(self) -> None:
        codigo_fonte = inspect.getsource(diag)
        proibidos = ["propensity_score", "psm", "nearest_neighbor", "att(", "did("]
        encontrados = [p for p in proibidos if p in codigo_fonte.lower()]
        self.assertEqual(encontrados, [], f"referências proibidas encontradas no código-fonte: {encontrados}")


class TestNomesDeArquivos(unittest.TestCase):
    def test_nomes_exatos_dos_artefatos(self) -> None:
        self.assertEqual(diag.OUT_ARRANJOS_INTERIM.name, "arranjos_populacionais_municipios_2010.parquet")
        self.assertEqual(diag.OUT_DIAGNOSTICO.name, "diagnostico_arranjos_populacionais_fase_ii.parquet")
        self.assertEqual(diag.OUT_RESUMO.name, "resumo_arranjos_populacionais_fase_ii.csv")


if __name__ == "__main__":
    unittest.main()
