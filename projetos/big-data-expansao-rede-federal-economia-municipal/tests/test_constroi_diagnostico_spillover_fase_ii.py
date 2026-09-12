"""Testes do diagnóstico de proximidade espacial (pool candidato x Fase II).

Execução:
    .venv\\Scripts\\python.exe -m unittest \
        tests.test_constroi_diagnostico_spillover_fase_ii -v

Todos os testes usam dados sintéticos pequenos — nenhum lê os Parquets
reais do pool, da Fase II ou da fonte espacial bruta, e nenhum acessa a
internet.
"""
from __future__ import annotations

import inspect
import math
import struct
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import constroi_diagnostico_spillover_fase_ii as diag  # noqa: E402

RAIO_TERRA_KM = diag.RAIO_TERRA_KM


# ---------------------------------------------------------------------------
# Helpers de construção de dados sintéticos
# ---------------------------------------------------------------------------


def _wkb_point(lon: float, lat: float) -> bytes:
    return b"\x01" + struct.pack("<I", 1) + struct.pack("<dd", lon, lat)


def _sede_bruta_row(codigo_float: float, lon: float, lat: float, uf: str = "RO") -> dict:
    return {
        "code_muni": codigo_float,
        "name_muni": "Sede Teste",
        "code_state": 11.0,
        "abbrev_state": uf,
        "name_state": "Rondônia",
        "code_region": 1.0,
        "name_region": "Norte",
        "year": 2010.0,
        "geometry": _wkb_point(lon, lat),
    }


def _pool_row(codigo: str, municipio: str = "Candidato Teste", uf: str = "RO") -> dict:
    return {"codigo_municipio_ibge": codigo, "municipio": municipio, "uf": uf}


def _fase_ii_row(codigo: str, municipio: str = "Tratado Teste", uf: str = "RO") -> dict:
    return {"codigo_municipio_ibge": codigo, "municipio": municipio, "uf": uf}


def _sedes_df(rows: list[tuple[str, float, float]]) -> pd.DataFrame:
    """Constrói o DataFrame reconciliado de sedes diretamente (sem passar
    pelo WKB bruto) — usado pelos testes de `build_diagnostico` /
    `validate_diagnostico`, que operam sobre a fonte já processada."""
    return pd.DataFrame(
        [{"codigo_municipio_ibge": c, "latitude_sede": lat, "longitude_sede": lon} for c, lat, lon in rows]
    )


def _ponto_ao_norte(lat0: float, lon0: float, distancia_km: float) -> tuple[float, float]:
    """Desloca um ponto puramente para o norte por uma distância geodésica
    de referência (mesma longitude ⇒ a fórmula de Haversine se reduz
    analiticamente a `distancia = R * delta_lat_em_radianos`). O ajuste por
    `nextafter` compensa o arredondamento de ponto flutuante do próprio
    round-trip grau/radiano (não da fórmula), garantindo que a distância
    recalculada por `haversine_km` fique exatamente `<= distancia_km` —
    necessário para os testes de fronteira, que comparam com `<=`."""
    delta_lat_rad = distancia_km / RAIO_TERRA_KM
    lat1 = lat0 + math.degrees(delta_lat_rad)
    for _ in range(100):
        dist = diag.haversine_km(np.array([lat0]), np.array([lon0]), np.array([lat1]), np.array([lon0]))[0]
        if dist <= distancia_km:
            break
        lat1 = np.nextafter(lat1, lat0)
    return lat1, lon0


# ---------------------------------------------------------------------------
# Haversine
# ---------------------------------------------------------------------------


class TestHaversineKm(unittest.TestCase):
    def test_distancia_zero_entre_coordenadas_identicas(self) -> None:
        d = diag.haversine_km(np.array([-10.0]), np.array([-50.0]), np.array([-10.0]), np.array([-50.0]))
        self.assertAlmostEqual(d[0], 0.0, places=9)

    def test_exemplo_conhecido_um_grau_no_equador(self) -> None:
        # Um grau de latitude no equador equivale a R * (pi/180) km — valor
        # de referência amplamente documentado (~111.19 km para R=6371 km).
        d = diag.haversine_km(np.array([0.0]), np.array([0.0]), np.array([1.0]), np.array([0.0]))
        esperado = RAIO_TERRA_KM * math.radians(1.0)
        self.assertAlmostEqual(d[0], esperado, places=6)
        self.assertAlmostEqual(d[0], 111.19, places=1)


# ---------------------------------------------------------------------------
# Parsing WKB e construção da fonte espacial
# ---------------------------------------------------------------------------


class TestParseWkbPoint(unittest.TestCase):
    def test_extrai_lon_lat_corretamente(self) -> None:
        lon, lat = diag._parse_wkb_point(_wkb_point(-61.999, -11.935))
        self.assertAlmostEqual(lon, -61.999, places=6)
        self.assertAlmostEqual(lat, -11.935, places=6)


class TestBuildSedesMunicipais(unittest.TestCase):
    def test_reconcilia_codigo_para_sete_digitos(self) -> None:
        bruto = pd.DataFrame([_sede_bruta_row(1100015.0, -61.999, -11.935)])
        sedes = diag.build_sedes_municipais(bruto)
        self.assertEqual(sedes.iloc[0]["codigo_municipio_ibge"], "1100015")
        self.assertAlmostEqual(sedes.iloc[0]["latitude_sede"], -11.935, places=6)
        self.assertAlmostEqual(sedes.iloc[0]["longitude_sede"], -61.999, places=6)

    def test_rejeita_code_muni_nulo(self) -> None:
        bruto = pd.DataFrame([_sede_bruta_row(1100015.0, -61.999, -11.935)])
        bruto.loc[0, "code_muni"] = None
        with self.assertRaisesRegex(ValueError, r"sedes municipais IBGE 2010: code_muni contém valor nulo"):
            diag.build_sedes_municipais(bruto)

    def test_rejeita_geometry_nula(self) -> None:
        bruto = pd.DataFrame([_sede_bruta_row(1100015.0, -61.999, -11.935)])
        bruto.loc[0, "geometry"] = None
        with self.assertRaisesRegex(ValueError, r"sedes municipais IBGE 2010: geometry contém valor nulo"):
            diag.build_sedes_municipais(bruto)


class TestValidateSedesMunicipais(unittest.TestCase):
    def test_aceita_sedes_validas(self) -> None:
        sedes = _sedes_df([("1100015", -11.9, -62.0), ("1100023", -10.0, -61.0)])
        diag.validate_sedes_municipais(sedes)  # não deve levantar

    def test_rejeita_codigo_duplicado(self) -> None:
        sedes = _sedes_df([("1100015", -11.9, -62.0), ("1100015", -10.0, -61.0)])
        with self.assertRaisesRegex(ValueError, r"sedes municipais IBGE 2010: codigo_municipio_ibge duplicado"):
            diag.validate_sedes_municipais(sedes)

    def test_rejeita_codigo_invalido(self) -> None:
        sedes = _sedes_df([("11000155", -11.9, -62.0)])  # 8 dígitos
        with self.assertRaisesRegex(ValueError, r"sedes municipais IBGE 2010: codigo_municipio_ibge inválido"):
            diag.validate_sedes_municipais(sedes)

    def test_rejeita_latitude_fora_do_intervalo(self) -> None:
        sedes = _sedes_df([("1100015", 45.0, -62.0)])  # latitude fora do Brasil
        with self.assertRaisesRegex(
            ValueError, r"sedes municipais IBGE 2010: latitude_sede fora do intervalo geográfico válido"
        ):
            diag.validate_sedes_municipais(sedes)

    def test_rejeita_longitude_fora_do_intervalo(self) -> None:
        sedes = _sedes_df([("1100015", -11.9, 100.0)])  # longitude fora do Brasil
        with self.assertRaisesRegex(
            ValueError, r"sedes municipais IBGE 2010: longitude_sede fora do intervalo geográfico válido"
        ):
            diag.validate_sedes_municipais(sedes)


# ---------------------------------------------------------------------------
# Validações dos insumos autorizados (pool e Fase II)
# ---------------------------------------------------------------------------


class TestValidatePoolCandidato(unittest.TestCase):
    def test_rejeita_cardinalidade_errada(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015")])
        with self.assertRaisesRegex(
            ValueError, rf"pool candidato a controles: esperado exatamente {diag.N_POOL_ESPERADO}"
        ):
            diag.validate_pool_candidato(pool)

    def test_rejeita_codigo_duplicado(self) -> None:
        pool = pd.DataFrame([_pool_row(str(1100015 + i)) for i in range(diag.N_POOL_ESPERADO - 1)])
        pool = pd.concat([pool, pool.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, r"pool candidato a controles: codigo_municipio_ibge duplicado"):
            diag.validate_pool_candidato(pool)

    def test_rejeita_codigo_nulo(self) -> None:
        pool = pd.DataFrame([_pool_row(str(1100015 + i)) for i in range(diag.N_POOL_ESPERADO)])
        pool.loc[0, "codigo_municipio_ibge"] = None
        with self.assertRaisesRegex(
            ValueError, r"pool candidato a controles: codigo_municipio_ibge contém valor nulo"
        ):
            diag.validate_pool_candidato(pool)

    def test_rejeita_codigo_invalido(self) -> None:
        pool = pd.DataFrame([_pool_row(str(1100015 + i)) for i in range(diag.N_POOL_ESPERADO)])
        pool.loc[0, "codigo_municipio_ibge"] = "110001"  # 6 dígitos
        with self.assertRaisesRegex(ValueError, r"pool candidato a controles: codigo_municipio_ibge inválido"):
            diag.validate_pool_candidato(pool)


class TestValidateFaseIIMunicipios(unittest.TestCase):
    def test_rejeita_cardinalidade_errada(self) -> None:
        fase_ii = pd.DataFrame([_fase_ii_row("1200203")])
        with self.assertRaisesRegex(ValueError, rf"lista Fase II: esperado exatamente {diag.N_FASE_II_ESPERADO}"):
            diag.validate_fase_ii_municipios(fase_ii)


class TestValidateFaseIINotInPool(unittest.TestCase):
    def test_rejeita_sobreposicao(self) -> None:
        with self.assertRaisesRegex(ValueError, r"pool candidato a controles: .* Fase II presente"):
            diag.validate_fase_ii_not_in_pool({"1100015", "1100023"}, {"1100023"})

    def test_aceita_conjuntos_disjuntos(self) -> None:
        diag.validate_fase_ii_not_in_pool({"1100015"}, {"1100023"})  # não deve levantar


class TestValidateCoberturaEspacial(unittest.TestCase):
    def test_rejeita_candidato_sem_cobertura(self) -> None:
        with self.assertRaisesRegex(ValueError, r"cobertura espacial: .* candidato\(s\) sem sede"):
            diag.validate_cobertura_espacial({"1100015", "9999999"}, {"1100023"}, {"1100015", "1100023"})

    def test_rejeita_fase_ii_sem_cobertura(self) -> None:
        with self.assertRaisesRegex(ValueError, r"cobertura espacial: .* Fase II sem sede"):
            diag.validate_cobertura_espacial({"1100015"}, {"9999999"}, {"1100015"})


# ---------------------------------------------------------------------------
# build_diagnostico
# ---------------------------------------------------------------------------


class TestBuildDiagnostico(unittest.TestCase):
    def test_escolhe_o_tratado_mais_proximo(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015")])
        fase_ii = pd.DataFrame([_fase_ii_row("1100023"), _fase_ii_row("1100031")])
        lat0, lon0 = -11.0, -62.0
        lat_perto, lon_perto = _ponto_ao_norte(lat0, lon0, 10.0)
        lat_longe, lon_longe = _ponto_ao_norte(lat0, lon0, 90.0)
        sedes = _sedes_df([("1100015", lat0, lon0), ("1100023", lat_perto, lon_perto), ("1100031", lat_longe, lon_longe)])
        resultado = diag.build_diagnostico(pool, fase_ii, sedes)
        self.assertEqual(resultado.iloc[0]["codigo_municipio_fase_ii_mais_proximo"], "1100023")
        self.assertAlmostEqual(resultado.iloc[0]["distancia_sedes_km"], 10.0, places=4)

    def test_desempate_pelo_menor_codigo_ibge(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015")])
        fase_ii = pd.DataFrame([_fase_ii_row("1100099"), _fase_ii_row("1100023")])
        lat0, lon0 = -11.0, -62.0
        lat_norte, lon_norte = _ponto_ao_norte(lat0, lon0, 30.0)
        # Ambos os tratados exatamente à mesma distância (mesma latitude) —
        # o desempate deve escolher o menor código IBGE (1100023), não a
        # ordem de aparição na lista de entrada (1100099 vem primeiro).
        sedes = _sedes_df([("1100015", lat0, lon0), ("1100099", lat_norte, lon_norte), ("1100023", lat_norte, lon_norte)])
        resultado = diag.build_diagnostico(pool, fase_ii, sedes)
        self.assertEqual(resultado.iloc[0]["codigo_municipio_fase_ii_mais_proximo"], "1100023")

    def _cenario_fronteira(self, distancia_km: float) -> pd.DataFrame:
        pool = pd.DataFrame([_pool_row("1100015")])
        fase_ii = pd.DataFrame([_fase_ii_row("1100023")])
        lat0, lon0 = -11.0, -62.0
        lat1, lon1 = _ponto_ao_norte(lat0, lon0, distancia_km)
        sedes = _sedes_df([("1100015", lat0, lon0), ("1100023", lat1, lon1)])
        return diag.build_diagnostico(pool, fase_ii, sedes)

    def test_fronteira_exatamente_25km(self) -> None:
        resultado = self._cenario_fronteira(25.0)
        self.assertTrue(bool(resultado.iloc[0]["fl_ate_25_km"]))

    def test_fronteira_exatamente_50km(self) -> None:
        resultado = self._cenario_fronteira(50.0)
        self.assertTrue(bool(resultado.iloc[0]["fl_ate_50_km"]))

    def test_fronteira_exatamente_100km(self) -> None:
        resultado = self._cenario_fronteira(100.0)
        self.assertTrue(bool(resultado.iloc[0]["fl_ate_100_km"]))

    def test_imediatamente_acima_de_25km(self) -> None:
        resultado = self._cenario_fronteira(25.001)
        self.assertFalse(bool(resultado.iloc[0]["fl_ate_25_km"]))
        self.assertTrue(bool(resultado.iloc[0]["fl_ate_50_km"]))

    def test_imediatamente_acima_de_50km(self) -> None:
        resultado = self._cenario_fronteira(50.001)
        self.assertFalse(bool(resultado.iloc[0]["fl_ate_50_km"]))
        self.assertTrue(bool(resultado.iloc[0]["fl_ate_100_km"]))

    def test_imediatamente_acima_de_100km(self) -> None:
        resultado = self._cenario_fronteira(100.001)
        self.assertFalse(bool(resultado.iloc[0]["fl_ate_100_km"]))

    def test_rejeita_candidato_sem_sede_apos_merge(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015"), _pool_row("9999999")])
        fase_ii = pd.DataFrame([_fase_ii_row("1100023")])
        sedes = _sedes_df([("1100015", -11.0, -62.0), ("1100023", -11.2, -62.0)])
        with self.assertRaisesRegex(ValueError, r"diagnóstico: candidato\(s\) sem sede municipal"):
            diag.build_diagnostico(pool, fase_ii, sedes)


# ---------------------------------------------------------------------------
# validate_diagnostico
# ---------------------------------------------------------------------------


class TestValidateDiagnosticoNegativos(unittest.TestCase):
    def _diagnostico_valido(self) -> tuple[pd.DataFrame, pd.DataFrame, set[str]]:
        pool = pd.DataFrame([_pool_row("1100015"), _pool_row("1100031")])
        fase_ii = pd.DataFrame([_fase_ii_row("1100023")])
        sedes = _sedes_df([("1100015", -11.0, -62.0), ("1100031", -12.0, -63.0), ("1100023", -11.2, -62.0)])
        resultado = diag.build_diagnostico(pool, fase_ii, sedes)
        return resultado, pool, {"1100023"}

    def test_diagnostico_valido_nao_levanta(self) -> None:
        resultado, pool, fase_ii_codes = self._diagnostico_valido()
        diag.validate_diagnostico(resultado, pool, fase_ii_codes)  # não deve levantar

    def test_rejeita_cardinalidade_diferente_do_pool(self) -> None:
        resultado, pool, fase_ii_codes = self._diagnostico_valido()
        reduzido = resultado.iloc[:1].copy()
        with self.assertRaisesRegex(ValueError, r"diagnóstico de distâncias: esperado exatamente"):
            diag.validate_diagnostico(reduzido, pool, fase_ii_codes)

    def test_rejeita_codigo_candidato_duplicado(self) -> None:
        resultado, pool, fase_ii_codes = self._diagnostico_valido()
        duplicado = pd.concat([resultado, resultado.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, r"diagnóstico de distâncias: codigo_municipio_ibge duplicado"):
            diag.validate_diagnostico(duplicado, pool, fase_ii_codes)

    def test_rejeita_conjunto_de_candidatos_alterado(self) -> None:
        resultado, pool, fase_ii_codes = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado.loc[0, "codigo_municipio_ibge"] = "9999999"
        with self.assertRaisesRegex(ValueError, r"diagnóstico de distâncias: conjunto de candidatos"):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes)

    def test_rejeita_tratado_fora_do_conjunto_fase_ii(self) -> None:
        resultado, pool, fase_ii_codes = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado.loc[0, "codigo_municipio_fase_ii_mais_proximo"] = "8888888"
        with self.assertRaisesRegex(ValueError, r"diagnóstico de distâncias: município\(s\) mais próximo\(s\) fora"):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes)

    def test_rejeita_distancia_negativa(self) -> None:
        resultado, pool, fase_ii_codes = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado.loc[0, "distancia_sedes_km"] = -1.0
        with self.assertRaisesRegex(ValueError, r"diagnóstico de distâncias: distancia_sedes_km contém valor negativo"):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes)

    def test_rejeita_distancia_nao_finita(self) -> None:
        resultado, pool, fase_ii_codes = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado.loc[0, "distancia_sedes_km"] = float("inf")
        with self.assertRaisesRegex(
            ValueError, r"diagnóstico de distâncias: distancia_sedes_km contém valor não finito"
        ):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes)

    def test_rejeita_flag_nula(self) -> None:
        resultado, pool, fase_ii_codes = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado["fl_ate_25_km"] = alterado["fl_ate_25_km"].astype(object)
        alterado.loc[0, "fl_ate_25_km"] = None
        with self.assertRaisesRegex(ValueError, r"diagnóstico de distâncias: fl_ate_25_km contém valor nulo"):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes)

    def test_rejeita_flag_com_dtype_invalido(self) -> None:
        resultado, pool, fase_ii_codes = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado["fl_ate_25_km"] = alterado["fl_ate_25_km"].astype(int)
        with self.assertRaisesRegex(ValueError, r"diagnóstico de distâncias: fl_ate_25_km deve ser booleana"):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes)

    def test_rejeita_inconsistencia_entre_flag_e_distancia(self) -> None:
        resultado, pool, fase_ii_codes = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado.loc[0, "fl_ate_25_km"] = not bool(alterado.loc[0, "fl_ate_25_km"])
        with self.assertRaisesRegex(
            ValueError, r"diagnóstico de distâncias: fl_ate_25_km não é exatamente equivalente"
        ):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes)

    def test_rejeita_monotonicidade_violada(self) -> None:
        resultado, pool, fase_ii_codes = self._diagnostico_valido()
        alterado = resultado.copy()
        alterado.loc[0, "fl_ate_50_km"] = False
        alterado.loc[0, "fl_ate_25_km"] = True
        with self.assertRaisesRegex(ValueError, r"diagnóstico de distâncias: monotonicidade violada"):
            diag.validate_diagnostico(alterado, pool, fase_ii_codes)


# ---------------------------------------------------------------------------
# build_resumo_diagnostico — reconciliação
# ---------------------------------------------------------------------------


class TestBuildResumoDiagnostico(unittest.TestCase):
    def test_reconciliacao_contagens_com_diagnostico(self) -> None:
        pool = pd.DataFrame([_pool_row("1100015", uf="RO"), _pool_row("1100031", uf="RO"), _pool_row("1200203", uf="AC")])
        fase_ii = pd.DataFrame([_fase_ii_row("1100023")])
        lat0, lon0 = -11.0, -62.0
        lat_20, lon_20 = _ponto_ao_norte(lat0, lon0, 20.0)
        lat_60, lon_60 = _ponto_ao_norte(lat0, lon0, 60.0)
        sedes = _sedes_df(
            [
                ("1100023", lat0, lon0),
                ("1100015", lat_20, lon_20),
                ("1100031", lat_60, lon_60),
                ("1200203", *_ponto_ao_norte(lat0, lon0, 150.0)),
            ]
        )
        diagnostico = diag.build_diagnostico(pool, fase_ii, sedes)
        resumo_geral, resumo_uf = diag.build_resumo_diagnostico(diagnostico)
        valores = dict(zip(resumo_geral["metrica"], resumo_geral["valor"]))

        self.assertEqual(valores["total_candidatos"], 3)
        self.assertEqual(valores["quantidade_ate_25_km"], int(diagnostico["fl_ate_25_km"].sum()))
        self.assertEqual(valores["quantidade_ate_50_km"], int(diagnostico["fl_ate_50_km"].sum()))
        self.assertEqual(valores["quantidade_ate_100_km"], int(diagnostico["fl_ate_100_km"].sum()))
        self.assertEqual(valores["quantidade_acima_100_km"], int((~diagnostico["fl_ate_100_km"]).sum()))
        self.assertAlmostEqual(valores["proporcao_ate_25_km"], diagnostico["fl_ate_25_km"].mean())

        soma_uf_ate_100 = resumo_uf["quantidade_ate_100_km"].sum()
        self.assertEqual(soma_uf_ate_100, int(diagnostico["fl_ate_100_km"].sum()))
        self.assertEqual(resumo_uf["total_candidatos"].sum(), len(diagnostico))


# ---------------------------------------------------------------------------
# Garantia de ausência de outcomes econômicos
# ---------------------------------------------------------------------------


class TestNaoUsaOutcomesEconomicos(unittest.TestCase):
    def test_fontes_lidas_nao_referenciam_outcomes(self) -> None:
        """As três únicas fontes efetivamente lidas pela rotina (as
        constantes *_PATH usadas por load_*) não podem apontar para nenhum
        arquivo de outcome econômico — checagem sobre os caminhos
        realmente utilizados, não sobre o texto da documentação (que
        precisa mencionar CEMPRE/RAIS/PIB para explicar a restrição)."""
        caminhos = [str(diag.POOL_CANDIDATO_PATH), str(diag.FASE_II_MUNICIPIOS_PATH), str(diag.SEDES_BRUTO_PATH)]
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
        self.assertEqual(diag.OUT_SEDES_INTERIM.name, "sedes_municipais_ibge_2010.parquet")
        self.assertEqual(diag.OUT_DIAGNOSTICO.name, "diagnostico_distancias_spillover_fase_ii.parquet")
        self.assertEqual(diag.OUT_RESUMO.name, "resumo_distancias_spillover_fase_ii.csv")


if __name__ == "__main__":
    unittest.main()
