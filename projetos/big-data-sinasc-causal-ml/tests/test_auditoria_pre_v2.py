"""Testes leves da auditoria pré-V2 (fixtures sintéticas; nenhuma leitura dos Parquets reais)."""
import ast
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from src import auditoria_pre_v2 as ap

RAIZ = Path(__file__).resolve().parents[1]

# Cada linha: MESPRENAT, SEMAGESTAC, CONSPRENAT, UF (código município), GRAVIDEZ, PESO
LINHAS = [
    ("01", "39", "08", "350000", "1", "3200"),
    ("1", "38", "07", "350000", "1", "3100"),
    ("02", "21", "02", "350000", "1", "600"),
    ("03", "40", "10", "330000", "1", "2400"),
    ("04", "37", "06", "330000", "1", "2900"),
    ("05", "22", "03", "330000", "1", "700"),
    ("06", "26", "04", "350000", "1", "1500"),
    ("07", "23", "02", "350000", "1", "900"),
    ("08", "36", "03", "330000", "1", "2600"),
    ("09", "39", "01", "330000", "1", "3300"),
    ("99", "40", "00", "350000", "1", "3000"),
    (None, "41", "00", "350000", "1", "3400"),
    ("", None, "99", "330000", "1", "3500"),
    ("10", "42", "05", "330000", "1", "3600"),
    ("04", "38", "07", "350000", "2", "2400"),    # gemelar: não elegível
    ("05", "39", "07", "ABC", "1", "8000"),       # peso fora de P1 e município inválido
]


def _fixture() -> pd.DataFrame:
    dados = pd.DataFrame(LINHAS, columns=["MESPRENAT", "SEMAGESTAC", "CONSPRENAT", "CODMUNRES", "GRAVIDEZ", "PESO"])
    n = len(dados)
    extras = {"GESTACAO": "5", "KOTELCHUCK": "4", "TPMETESTIM": "8", "DTULTMENST": "01012020",
              "IDADEMAE": "25", "ESCMAE2010": "3", "RACACORMAE": "4", "ESTCIVMAE": "1",
              "PARIDADE": "1", "QTDFILMORT": "00"}
    for coluna, valor in extras.items():
        dados[coluna] = [valor] * n
    dados.loc[2, "DTULTMENST"] = None
    dados.loc[3, "IDADEMAE"] = "99"
    return dados.astype("string")


@pytest.fixture()
def parquet(tmp_path):
    caminho = tmp_path / "sinasc_teste.parquet"
    _fixture().to_parquet(caminho, index=False)
    return caminho


@pytest.fixture()
def cubos(parquet):
    resultado, _ = ap.agregar_ano(parquet, 2020, threads=1)
    return resultado


def _base(parquet):
    import duckdb
    with duckdb.connect() as con:
        return con.execute(ap.sql_base_derivada(ap.fonte_parquet(parquet), 2020)).df()


def test_derivacao_preserva_linhas_e_categoriza_mesprenat(parquet):
    base = _base(parquet)
    assert len(base) == len(LINHAS)
    assert base["mes"].tolist()[:14] == ["01", "01", "02", "03", "04", "05", "06", "07", "08", "09",
                                         "99", "VAZIO", "VAZIO", "OUTRO_INVALIDO"]
    assert set(base["mes"]) <= set(ap.CATEGORIAS_MESPRENAT)


def test_separa_99_vazio_e_invalido():
    mes = pd.Series(["01", "09", "99", "VAZIO", "OUTRO_INVALIDO"])
    assert ap.status_mesprenat(mes).tolist() == ["CONHECIDO", "CONHECIDO", "99", "VAZIO", "OUTRO_INVALIDO"]
    assert ap.grupo_d3(pd.Series(["03", "05", "06", "07", "99", "VAZIO"])).tolist() == \
        ["1-3", "4-5", "6", "7-9", "99", "VAZIO"]


def test_99_vazio_e_invalido_nunca_entram_em_t():
    t = ap.tratamento_v1(pd.Series(["01", "03", "04", "09", "99", "VAZIO", "OUTRO_INVALIDO"]))
    assert t.tolist()[:4] == [1, 1, 0, 0]
    assert t.iloc[4:].isna().all()


def test_faixas_gestacionais(parquet):
    base = _base(parquet)
    faixa = dict(zip(base["semanas"].astype("Int64").astype(str), base["faixa_ig"]))
    assert faixa["21"] == "<22" and faixa["22"] == "22-26" and faixa["26"] == "22-26"
    assert faixa["23"] == "22-26" and faixa["36"] == "32-36" and faixa["37"] == "37-41"
    assert faixa["41"] == "37-41" and faixa["42"] == ">=42"
    assert base.loc[base["semanas"].isna(), "faixa_ig"].eq("AUSENTE_OU_INVALIDA").all()


def test_elegibilidade_e_outcome(parquet):
    base = _base(parquet)
    assert base["elegivel"].sum() == 14
    assert base.loc[2, "y"] == 1 and base.loc[0, "y"] == 0
    assert pd.isna(base.loc[15, "y"])
    assert base.loc[15, "uf"] == "IGNORADO"


def test_denominadores_e_brasil_igual_soma_uf(cubos):
    d5 = ap.d5_tabelas(cubos["ig_uf"])
    props = d5[["prop_99", "prop_VAZIO", "prop_OUTRO_INVALIDO"]].sum(axis=1) + d5["n_CONHECIDO"] / d5["denominador"]
    assert props.round(12).eq(1).all()
    for pop, bloco in d5.groupby("populacao"):
        brasil = bloco[bloco["uf"] == "BRASIL"]["denominador"].sum()
        assert brasil == bloco[bloco["uf"] != "BRASIL"]["denominador"].sum()
    bruta = d5[(d5["populacao"] == "BRUTA") & (d5["uf"] == "BRASIL")].iloc[0]
    assert bruta["denominador"] == len(LINHAS)
    assert (bruta["n_99"], bruta["n_VAZIO"], bruta["n_OUTRO_INVALIDO"]) == (1, 2, 1)


def test_d3_consprenat_zero_e_denominadores(cubos):
    d3 = ap.d3_tabelas(cubos["consprenat"])
    zero = d3["consprenat_zero"]
    br = zero[(zero["populacao"] == "BRUTA") & (zero["uf"] == "BRASIL")]
    assert br["n"].sum() == 2
    assert set(br["grupo_mesprenat"]) == {"99", "VAZIO"}
    assert br["denominador_consprenat"].eq(2).all()
    assert br["prop_dentro_consprenat"].sum() == pytest.approx(1)


def test_d1_proporcoes_somam_um(cubos):
    d1 = ap.d1_tabelas(cubos["ig_uf"], cubos["gestacao"])["brasil"]
    soma = d1.groupby(["ano", "faixa_ig"])["prop_no_estrato_ig"].sum()
    assert soma.round(12).eq(1).all()
    assert set(d1["ano"]) == {"2020", "2014-2024"}


def test_status_consistencia_leituras():
    assert ap.status_consistencia(23, 7) == "POTENCIALMENTE_INCOMPATIVEL_L1"
    assert ap.status_consistencia(19, 7) == "POTENCIALMENTE_INCOMPATIVEL_MESMO_COM_TOLERANCIA"
    assert ap.status_consistencia(25, 7) == "POTENCIALMENTE_INCOMPATIVEL_SOMENTE_L2"
    assert ap.status_consistencia(26, 7) == "SEM_INCOMPATIBILIDADE_DETECTADA"
    assert ap.status_consistencia(15, 1) == "SEM_INCOMPATIBILIDADE_DETECTADA"
    assert ap.status_consistencia(None, 7) == "NAO_AVALIAVEL"
    assert "IMPOSSIVEL" not in " ".join(ap.STATUS_CONSISTENCIA)


def test_limiares_estruturais():
    assert ap.limiar_semanas_afetadas(9, "L1") == 31
    assert ap.limiar_semanas_afetadas(9, "L2") == 33
    assert ap.limiar_semanas_afetadas(6, "L1") == 19
    assert ap.limiar_semanas_afetadas(6, "L2") == 20
    assert ap.limiar_semanas_afetadas(5, "L1") == 15
    assert ap.limiar_semanas_afetadas(5, "L2") == 16


def test_populacoes_abc(cubos):
    d7 = ap.d7_tabelas(cubos["ig_uf"], cubos["semanas"], cubos["perfil_categorico"], cubos["perfil_numerico"])
    resumo = d7["resumo"][d7["resumo"]["ano"] == "2020"].set_index("alternativa")
    assert resumo["n_controle_v1"].eq(6).all()
    assert resumo.loc["A_V1_4_9", "n_controles_mantidos"] == 6
    assert resumo.loc["B_4_6", "n_controles_mantidos"] == 3
    assert resumo.loc["C_4_5", "n_controles_mantidos"] == 2
    assert (resumo["n_controles_mantidos"] + resumo["n_controles_excluidos"]).eq(6).all()
    assert resumo.loc["A_V1_4_9", "fracao_controle_7_9"] == pytest.approx(0.5)
    assert set(d7["mesprenat"]["mes"]) <= {"04", "05", "06", "07", "08", "09"}
    assert resumo.loc["A_V1_4_9", "M1_L1"] >= resumo.loc["B_4_6", "M1_L1"] >= resumo.loc["C_4_5", "M1_L1"]


def test_d4_smd_rotulado_como_missingness(cubos):
    d4 = ap.d4_tabelas(cubos["perfil_categorico"], cubos["perfil_numerico"])
    assert d4["smd"].empty or d4["smd"]["rotulo"].str.contains("NÃO É BALANCEAMENTO CAUSAL").all()
    assert d4["perfil"]["rotulo"].eq("DESCRITIVO / NÃO CAUSAL").all()


def test_heaping_indicadores():
    ind = ap.indicadores_heaping({"01": 10, "02": 30, "03": 60, "04": 20})
    assert ind["razao_3_4"] == 3
    assert ind["vizinhanca_3"] == pytest.approx(60 / 25)
    assert ind["salto_3_4_pp"] == pytest.approx(100 * (60 - 20) / 120)


def test_sem_mutacao_dos_dados(parquet, tmp_path):
    antes = hashlib.sha256(parquet.read_bytes()).hexdigest()
    ap.agregar_ano(parquet, 2020, threads=1)
    assert hashlib.sha256(parquet.read_bytes()).hexdigest() == antes
    mes = pd.Series(["01", "99", "VAZIO"])
    copia = mes.copy()
    ap.status_mesprenat(mes)
    ap.tratamento_v1(mes)
    pd.testing.assert_series_equal(mes, copia)


def test_determinismo(parquet):
    a, _ = ap.agregar_ano(parquet, 2020, threads=1)
    b, _ = ap.agregar_ano(parquet, 2020, threads=2)
    for nome in a:
        chaves = [c for c in a[nome].columns if c != "n"]
        x = a[nome].sort_values(chaves).reset_index(drop=True)
        y = b[nome].sort_values(chaves).reset_index(drop=True)
        pd.testing.assert_frame_equal(x, y, check_dtype=False)


def test_schema_dos_cubos(cubos):
    esperado = {
        "ig_uf": ["ano", "uf", "elegivel", "mes", "faixa_ig", "n"],
        "semanas": ["ano", "elegivel", "mes", "semanas_status", "semanas", "n"],
        "consprenat": ["ano", "uf", "elegivel", "consprenat", "mes", "n"],
        "kotelchuck": ["ano", "elegivel", "kotelchuck", "consprenat", "mes", "n"],
        "perfil_categorico": ["ano", "mes", "variavel", "nivel", "n"],
    }
    for nome, colunas in esperado.items():
        assert list(cubos[nome].columns) == colunas
    assert cubos["n_base"]["n"].iloc[0] == len(LINHAS)


def test_inventario_schema_sem_diferenciar_caixa(tmp_path):
    caminho = tmp_path / "minusculo.parquet"
    _fixture().rename(columns=str.lower).to_parquet(caminho, index=False)
    inv = ap.inventario_schema(caminho, 2016).set_index("campo")
    assert inv.loc["MESPRENAT", "presente"] and inv.loc["MESPRENAT", "caixa_diferente"]
    assert not inv.loc["CONTADOR", "presente"]
    resultado, _ = ap.agregar_ano(caminho, 2016, threads=1)
    assert resultado["n_base"]["n"].iloc[0] == len(LINHAS)


def test_modulo_nao_calcula_aipw_nem_propensity():
    fonte = (RAIZ / "src" / "auditoria_pre_v2.py").read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    importados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados |= {a.name for a in no.names}
        elif isinstance(no, ast.ImportFrom):
            importados.add(no.module or "")
    proibidos = ("sklearn", "src.inferencia_causal", "src.estimativas_temporais", "src.robustez",
                 "src.modelagem_preditiva", "src.heterogeneidade", "src.diagnosticos")
    assert not any(i.startswith(p) for i in importados for p in proibidos)
    funcoes = [n.name.lower() for n in ast.walk(arvore) if isinstance(n, ast.FunctionDef)]
    assert not any("aipw" in f or "propensity" in f or "ajustar" in f for f in funcoes)


def test_gates_regras_mecanicas():
    assert ap.pior_status("APROVADO", "SINALIZADO") == "SINALIZADO"
    assert ap.melhor_status("BLOQUEADO", "PENDENTE", "SINALIZADO") == "SINALIZADO"
    matriz = pd.DataFrame({"ano": ["2020"] * 2, "mes": ["07", "07"], "n": [600, 400],
                           "status_diagnostico": ["POTENCIALMENTE_INCOMPATIVEL_L1", "SEM_INCOMPATIBILIDADE_DETECTADA"]})
    assert ap.avaliar_g2(matriz, {})["status"] == "BLOQUEADO"
    matriz["n"] = [6, 4]                               # célula < 100 não decide bloqueio
    assert ap.avaliar_g2(matriz, {})["status"] == "SINALIZADO"
    matriz["n"] = [100, 900]
    assert ap.avaliar_g2(matriz, {})["status"] == "SINALIZADO"
    matriz["status_diagnostico"] = "SEM_INCOMPATIBILIDADE_DETECTADA"
    assert ap.avaliar_g2(matriz, {})["status"] == "APROVADO"
    assert ap.avaliar_g2(matriz, {"2014": 3})["status"] == "SINALIZADO"
    g = {"G1": {"status": "SINALIZADO"}, "G2": {"status": "SINALIZADO"}, "G3": {"status": "SINALIZADO"},
         "G5": {"status": "APROVADO"}, "G6": {"status": "BLOQUEADO"}}
    g7 = ap.avaliar_g7(g)
    assert g7["formulacoes"] == {"B_4_6": "SINALIZADO", "C_4_5": "BLOQUEADO", "D_landmark": "PENDENTE"}
    assert g7["status"] == "SINALIZADO" and g7["V2_escolhida"] is False


def test_smd_missingness_com_grupos_suficientes():
    cat = pd.DataFrame({"ano": [2020] * 4, "mes": ["01", "01", "99", "99"], "variavel": ["Y_BAIXO_PESO"] * 4,
                        "nivel": ["0", "1", "0", "1"], "n": [180, 20, 120, 30]})
    num = pd.DataFrame({"ano": [2020, 2020], "mes": ["01", "99"], "n": [200, 150], "n_idade": [200, 150],
                        "soma_idade": [5000.0, 3600.0], "soma2_idade": [130000.0, 90000.0],
                        "n_y": [200, 150], "soma_y": [20, 30]})
    smd = ap.d4_tabelas(cat, num)["smd"]
    y = smd[(smd["ano"] == "2020") & (smd["variavel"] == "Y_BAIXO_PESO")].iloc[0]
    assert y["smd"] == pytest.approx(ap.smd_binario(0.2, 0.1))
    assert set(smd["grupo"]) == {"99"}


def test_pipeline_completo_na_fixture(cubos):
    d1 = ap.d1_tabelas(cubos["ig_uf"], cubos["gestacao"])
    d2 = ap.d2_tabelas(cubos["semanas"])
    d3 = ap.d3_tabelas(cubos["consprenat"])
    d4 = ap.d4_tabelas(cubos["perfil_categorico"], cubos["perfil_numerico"])
    d6 = ap.d6_tabelas(cubos["ig_uf"], cubos["processo"])
    d7 = ap.d7_tabelas(cubos["ig_uf"], cubos["semanas"], cubos["perfil_categorico"], cubos["perfil_numerico"])
    d8 = ap.d8_tabelas(cubos["kotelchuck"])
    assert not d6["indicadores"].empty and not d8["x_consprenat"].empty
    g = {"G1": ap.avaliar_g1(d3["consprenat_zero"], d3["longa"], semantica_oficial=True),
         "G2": ap.avaliar_g2(d2["matriz"], ap.codigos_fora_dominio_mesprenat(cubos["ig_uf"])),
         "G3": ap.avaliar_g3(d4["smd"]),
         "G4": ap.avaliar_g4(d7["resumo"], d1["padrao_truncamento"]),
         "G5": ap.avaliar_g5(d7["resumo"]), "G6": ap.avaliar_g6(d7["resumo"])}
    g["G7"] = ap.avaliar_g7(g)
    assert all(v["status"] in ap.ORDEM_GRAVIDADE for v in g.values())
    assert g["G2"]["status"] == "SINALIZADO"          # 07 com 23 semanas e código 10
    assert g["G3"]["status"] == "PENDENTE"            # grupos desconhecidos < 100
    assert g["G4"]["status"] == "SINALIZADO"


def test_criterios_congelados_tem_hash_estavel():
    assert ap.hash_criterios() == ap.hash_criterios()
    assert set(ap.CRITERIOS_GATES) == {f"G{i}" for i in range(1, 8)}
    assert ap.ROTULO_99_MESPRENAT == "CODIFICACAO_OPERACIONAL_OBSERVADA"
