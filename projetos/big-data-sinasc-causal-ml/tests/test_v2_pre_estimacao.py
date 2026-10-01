"""Testes leves do contrato V2 pré-estimação (fixtures sintéticas; nenhum Parquet real)."""
import ast
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from src import v2_pre_estimacao as v2
from src.amostra import _criar_views

RAIZ = Path(__file__).resolve().parents[1]
ANO = 2020


def _fixture(n: int = 900, seed: int = 7) -> pd.DataFrame:
    """Registros sintéticos com todos os códigos relevantes de MESPRENAT."""

    rng = np.random.default_rng(seed)
    escolaridade = rng.choice(["1", "2", "3", "4", "5", "9"], n)
    # Mês de início associado à escolaridade, para um propensity não trivial.
    base = np.where(np.isin(escolaridade, ["4", "5"]), 0.85, 0.6)
    precoce = rng.random(n) < base
    mes = np.where(precoce, rng.choice(["01", "02", "03"], n), rng.choice(["04", "05", "06", "07", "08", "09"], n))
    dados = pd.DataFrame({
        "contador": [str(i + 1) for i in range(n)],
        "MESPRENAT": mes,
        "PESO": rng.integers(1500, 4200, n).astype(str),
        "GRAVIDEZ": "1",
        "IDADEMAE": rng.integers(15, 45, n).astype(str),
        "ESCMAE2010": escolaridade,
        "RACACORMAE": rng.choice(["1", "2", "4", "9"], n),
        "ESTCIVMAE": rng.choice(["1", "2", "5"], n),
        "PARIDADE": rng.choice(["0", "1"], n),
        "QTDFILMORT": rng.choice(["00", "01", "02", "99"], n),
        "CODMUNRES": rng.choice(["350000", "330000", "310000"], n),
        "DTNASC": "15062020",
    })
    especiais = {0: "99", 1: None, 2: "", 3: "10", 4: "abc", 5: "99", 6: None}
    for i, valor in especiais.items():
        dados.loc[i, "MESPRENAT"] = valor
    dados.loc[7, "GRAVIDEZ"] = "2"            # gemelar: inelegível
    dados.loc[8, "PESO"] = "8000"             # fora de P1: inelegível
    dados.loc[9, "PESO"] = "450"              # fora de P1: inelegível
    dados.loc[10, "IDADEMAE"] = "99"          # idade ausente no X
    return dados.astype("string")


@pytest.fixture()
def parquet(tmp_path):
    caminho = tmp_path / "sinasc_v2.parquet"
    _fixture().to_parquet(caminho, index=False)
    return caminho


def _v1(parquet):
    with duckdb.connect() as con:
        _criar_views(con, Path(parquet))
        v1 = con.execute("SELECT * FROM amostra_principal").df()
        bruto = con.execute("SELECT contador, MESPRENAT FROM sinasc").df()
    return v1.merge(bruto, on="contador", how="left")


# --- Populações -------------------------------------------------------------

def test_populacao_b_contem_somente_meses_1_a_6(parquet):
    dados, meta = v2.carregar_populacao(parquet, ANO, "B")
    assert set(dados.mesprenat_num) <= {1, 2, 3, 4, 5, 6}
    assert not dados.mesprenat_num.isin([7, 8, 9]).any()
    assert (dados.tratamento == dados.mesprenat_num.le(3).astype(int)).all()
    assert meta["n"] == meta["n_t0"] + meta["n_t1"] and meta["chave_unica"]


def test_ordem_deterministica_ano_base_segue_linha_fisica(parquet):
    """No ano-base a ordem é a física do arquivo (contrato do 08), explícita e reprodutível."""
    a, ma = v2.carregar_populacao(parquet, v2.ANO_BASELINE, "B")
    b, mb = v2.carregar_populacao(parquet, v2.ANO_BASELINE, "B")
    assert ma["sha256_sequencia_chave"] == mb["sha256_sequencia_chave"]
    bruto = _fixture()
    posicao = {c: i for i, c in enumerate(bruto.contador)}
    assert a.contador.map(posicao).is_monotonic_increasing
    outro, _ = v2.carregar_populacao(parquet, ANO, "B")
    assert list(outro.contador) == sorted(outro.contador, key=lambda c: (
        outro.set_index("contador").loc[c, "UF_RESIDENCIA"], str(c)))


def test_populacao_c_exclui_6_a_9(parquet):
    dados, _ = v2.carregar_populacao(parquet, ANO, "C")
    assert set(dados.mesprenat_num) <= {1, 2, 3, 4, 5}
    assert not dados.mesprenat_num.isin([6, 7, 8, 9]).any()


def test_b_e_c_sao_subconjuntos_exatos_da_v1(parquet):
    v1 = _v1(parquet)
    for formulacao, maximo in (("A_V1", 9), ("B", 6), ("C", 5)):
        dados, _ = v2.carregar_populacao(parquet, ANO, formulacao)
        esperado = v1.loc[pd.to_numeric(v1.MESPRENAT, errors="coerce").le(maximo), "contador"]
        assert sorted(dados.contador) == sorted(esperado)
        # T coincide com a V1 nos meses mantidos
        junto = dados.merge(v1[["contador", "tratamento"]], on="contador", suffixes=("", "_v1"))
        assert (junto.tratamento == junto.tratamento_v1).all()


@pytest.mark.parametrize("codigo", ["99", None, "", "10", "abc"])
def test_codigos_desconhecidos_permanecem_na(codigo):
    serie = pd.Series([codigo, "02", "05"], dtype="string")
    for formulacao in ("A_V1", "B", "C"):
        t = v2.classificar_tratamento(serie, formulacao)
        assert pd.isna(t.iloc[0])
        assert t.iloc[1] == 1 and t.iloc[2] == 0


def test_codigos_desconhecidos_nao_entram_na_populacao(parquet):
    bruto = _fixture()
    for formulacao in ("A_V1", "B", "C"):
        dados, _ = v2.carregar_populacao(parquet, ANO, formulacao)
        excluidos = bruto.loc[[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], "contador"]
        assert not dados.contador.isin(excluidos).any()


def test_meses_fora_da_formulacao_ficam_na():
    serie = pd.Series(["06", "07", "09"], dtype="string")
    assert v2.classificar_tratamento(serie, "B").tolist()[0] == 0
    assert v2.classificar_tratamento(serie, "B").isna().tolist()[1:] == [True, True]
    assert v2.classificar_tratamento(serie, "C").isna().all()
    assert (v2.classificar_tratamento(serie, "A_V1") == 0).all()


def test_landmark_d_nao_implementada():
    with pytest.raises(ValueError):
        v2.classificar_tratamento(pd.Series(["01"]), "D_LANDMARK")
    assert v2.FORMULACOES["D_LANDMARK"]["implementada"] is False


def test_mesma_definicao_de_y_e_desfecho_nao_materializado(parquet):
    """A elegibilidade usa y_p1 válido (peso 500-6000 g) como na V1, mas Y não é carregado."""
    dados, _ = v2.carregar_populacao(parquet, ANO, "B")
    assert not ({"Y_BAIXO_PESO", "PESO", "y_p1"} & set(dados.columns))
    bruto = _fixture().set_index("contador")
    peso = pd.to_numeric(bruto.loc[dados.contador, "PESO"])
    assert peso.between(500, 6000).all()
    with pytest.raises(ValueError):
        v2.verificar_ausencia_desfecho(["IDADEMAE_NUM", "Y_BAIXO_PESO"])


def test_mesmas_sete_x_que_a_v1(parquet):
    dados, _ = v2.carregar_populacao(parquet, ANO, "B")
    assert list(v2.FEATURES) == ["IDADEMAE_NUM", "ESCOLARIDADE_MAE", "RACA_COR_MAE", "SITUACAO_CONJUGAL",
                                 "PARIDADE_CAT", "PERDAS_FETAIS_CAT", "UF_RESIDENCIA"]
    v1 = _v1(parquet).set_index("contador")
    x = dados.set_index("contador")[list(v2.FEATURES)]
    pd.testing.assert_frame_equal(x, v1.loc[x.index, list(v2.FEATURES)], check_dtype=False)


@pytest.mark.parametrize("proibida", ["SEMAGESTAC", "KOTELCHUCK", "CONSPRENAT", "Y_BAIXO_PESO", "GESTACAO"])
def test_x_recusa_variaveis_pos_tratamento(proibida):
    x = pd.DataFrame({c: ["1"] for c in v2.FEATURES})
    x[proibida] = ["1"]
    with pytest.raises(ValueError):
        v2.validar_x(x)


# --- Partições, OOF e cache -----------------------------------------------------

def test_particoes_identicas_ao_notebook08_e_cobertura_exata(parquet):
    from sklearn.model_selection import StratifiedKFold
    dados, _ = v2.carregar_populacao(parquet, ANO, "B")
    t = dados.tratamento.to_numpy()
    folds = v2.particoes_diagnostico(t)
    referencia = StratifiedKFold(5, shuffle=True, random_state=20240925).split(dados[list(v2.FEATURES)], t)
    for (a, b), (c, d) in zip(folds, referencia, strict=True):
        assert np.array_equal(a, c) and np.array_equal(b, d)
    cobertura = np.zeros(len(t), int)
    for _, validacao in folds:
        cobertura[validacao] += 1
    assert (cobertura == 1).all()


def test_particao_invalida_e_recusada():
    t = np.array([0, 1] * 10)
    idx = np.arange(20)
    with pytest.raises(ValueError):
        v2.validar_particoes([(idx[:15], idx[10:])], t)
    so_tratados = np.where(t == 1)[0]
    with pytest.raises(ValueError):
        v2.validar_particoes([(np.setdiff1d(idx, so_tratados), so_tratados)], t)


def test_oof_reproduz_pipeline_do_notebook08_sem_vazamento(parquet, tmp_path):
    from sklearn.base import clone
    from src import temporal as tp
    dados, meta = v2.carregar_populacao(parquet, ANO, "B")
    meta["parquet_sha256"] = v2.sha256_arquivo(parquet)
    e, ajuste = v2.ajustar_propensity_oof(dados, meta, "B", tmp_path / "cache", "c" * 64)
    x = dados[list(v2.FEATURES)]
    t = dados.tratamento.to_numpy()
    referencia, _ = tp.ajustar_propensity_temporal(x, t)
    np.testing.assert_allclose(e, referencia, rtol=0, atol=1e-12)
    # Sem vazamento: a predição de cada partição vem de um ajuste que não viu a validação.
    treino, validacao = v2.particoes_diagnostico(t)[0]
    modelo = clone(v2.construir_pipeline()).fit(x.iloc[treino], t[treino])
    np.testing.assert_allclose(modelo.predict_proba(x.iloc[validacao])[:, 1], e[validacao], atol=1e-12)
    assert all(l["n_treino"] + l["n_validacao"] == len(t) for l in ajuste["folds"])
    assert ajuste["todos_convergiram"] and ajuste["particoes_validas"]


def test_checkpoint_reutilizado_e_incompativel_rejeitado(parquet, tmp_path):
    dados, meta = v2.carregar_populacao(parquet, ANO, "C")
    meta["parquet_sha256"] = "a" * 64
    pasta = tmp_path / "cache"
    e1, a1 = v2.ajustar_propensity_oof(dados, meta, "C", pasta, "c" * 64)
    e2, a2 = v2.ajustar_propensity_oof(dados, meta, "C", pasta, "c" * 64)
    assert np.array_equal(e1, e2)
    assert {l["origem"] for l in a1["folds"]} == {"ajuste"} and {l["origem"] for l in a2["folds"]} == {"cache"}
    alterado = dict(meta, parquet_sha256="b" * 64)
    with pytest.raises(ValueError, match="incompatível"):
        v2.ajustar_propensity_oof(dados, alterado, "C", pasta, "c" * 64)
    alterado = dict(meta, sha256_sequencia_chave="0" * 64)
    with pytest.raises(ValueError, match="incompatível"):
        v2.ajustar_propensity_oof(dados, alterado, "C", pasta, "c" * 64)


def test_checkpoint_adulterado_rejeitado(parquet, tmp_path):
    dados, meta = v2.carregar_populacao(parquet, ANO, "B")
    meta["parquet_sha256"] = "a" * 64
    pasta = tmp_path / "cache"
    v2.ajustar_propensity_oof(dados, meta, "B", pasta, "c" * 64)
    arquivo = next((pasta).rglob("fold1.npz"))
    with np.load(arquivo) as z:
        e = z["e"].copy()
    e[0] = 0.5 if e[0] != 0.5 else 0.4
    np.savez_compressed(arquivo, e=e)
    with pytest.raises(ValueError):
        v2.ajustar_propensity_oof(dados, meta, "B", pasta, "c" * 64)


def test_contrato_do_cache_contem_campos_exigidos():
    meta = {"parquet_sha256": "p", "regra_ordenacao": "o", "sha256_sequencia_chave": "k", "n": 10, "n_t0": 4, "n_t1": 6}
    c = v2.contrato_fold(formulacao="B", ano=2014, fold=1, meta=meta, indices_validacao=np.arange(2),
                         codigo_sha256="h")
    for campo in ("formulacao", "ano", "features", "seed", "fold", "parquet_sha256", "regra_ordenacao",
                  "sha256_sequencia_chave", "pipeline", "versoes", "codigo_sha256", "fingerprint"):
        assert campo in c
    assert c["pipeline"]["modelo"]["parametros"]["C"] == "1.0"
    assert c["seed"] == 20240925 and c["n_folds"] == 5


# --- Diagnósticos ---------------------------------------------------------------

def test_ess_definicao():
    assert v2.ess(np.ones(10)) == pytest.approx(10)
    assert v2.ess(np.array([1.0, 1.0, 2.0])) == pytest.approx(16 / 6)
    t = np.array([0, 0, 1, 1])
    e = np.array([0.5, 0.5, 0.5, 0.5])
    w = v2.pesos_ate(t, e)
    assert np.allclose(w, 2.0)
    with pytest.raises(ValueError):
        v2.pesos_ate(t, np.array([0.0, 0.5, 0.5, 1.0]))


def test_smd_coincide_com_definicao_historica(parquet):
    from src.selecao_nuisance import diagnosticos_propensity
    dados, _ = v2.carregar_populacao(parquet, ANO, "A_V1")
    t = dados.tratamento.to_numpy()
    rng = np.random.default_rng(1)
    e = np.clip(rng.uniform(0.2, 0.9, len(t)), 0.01, 0.99)
    linha, balanco = v2.resumir_suporte(dados[list(v2.FEATURES)], t, e)
    historico = diagnosticos_propensity(dados[list(v2.FEATURES)], t, e)
    assert linha["max_abs_smd_bruto"] == pytest.approx(historico["max_abs_smd_bruto"], abs=1e-12)
    assert linha["max_abs_smd_ponderado"] == pytest.approx(historico["max_abs_smd_ponderado"], abs=1e-12)
    assert linha["ess_t0"] == pytest.approx(historico["ess_t0"]) and linha["ess_t1"] == pytest.approx(historico["ess_t1"])
    assert linha["fora_005_095_fracao"] == pytest.approx(historico["fora_005_095_fracao"])
    assert set(balanco.variavel) == set(v2.FEATURES)


def test_smd_ponderado_balanceia_quando_e_e_verdadeiro():
    rng = np.random.default_rng(3)
    x = rng.integers(0, 2, 200_000).astype(float)
    e = np.where(x == 1, 0.8, 0.4)
    t = (rng.random(len(x)) < e).astype(int)
    assert abs(v2.smd(x, t, np.ones(len(t)))) > 0.5
    assert abs(v2.smd(x, t, v2.pesos_ate(t, e))) < 0.02


def test_suporte_comum_e_caudas():
    x = pd.DataFrame({c: ["1"] * 6 for c in v2.FEATURES})
    x["IDADEMAE_NUM"] = [20, 21, 22, 23, 24, 25]
    t = np.array([0, 0, 0, 1, 1, 1])
    e = np.array([0.02, 0.3, 0.6, 0.4, 0.7, 0.97])
    linha, _ = v2.resumir_suporte(x, t, e)
    assert linha["suporte_comum_inferior"] == pytest.approx(0.4)
    assert linha["suporte_comum_superior"] == pytest.approx(0.6)
    assert linha["fora_suporte_comum_n"] == 4
    assert linha["fora_005_095_n"] == 2 and linha["fora_001_099_n"] == 0
    assert linha["e_min"] == pytest.approx(0.02) and linha["e_max"] == pytest.approx(0.97)
    assert "e_p0_1" in linha and "e_p99_9" in linha and "peso_t0_p99_9" in linha


# --- Gates ----------------------------------------------------------------------

_OK = {"bracos": True, "particoes": True, "propensity_valido": True, "sem_vazamento": True,
       "convergencia": True, "contrato_dados": True}


def _linha(**kw):
    base = {"ess_t0_sobre_n": 0.8, "ess_t1_sobre_n": 0.9, "max_abs_smd_ponderado": 0.02, "fora_005_095_fracao": 0.04}
    base.update(kw)
    return base


def test_gate_aprovado_sinalizado_bloqueado():
    assert v2.avaliar_gate(_linha(), _OK)["status"] == "APROVADO"
    assert v2.avaliar_gate(_linha(max_abs_smd_ponderado=0.10), _OK)["status"] == "APROVADO"
    assert v2.avaliar_gate(_linha(max_abs_smd_ponderado=0.1001), _OK)["sinais"] == ["S1_smd_ponderado"]
    assert v2.avaliar_gate(_linha(fora_005_095_fracao=0.11), _OK)["sinais"] == ["S2_caudas"]
    assert v2.avaliar_gate(_linha(ess_t0_sobre_n=0.45), _OK)["sinais"] == ["S3_ess_baixo"]
    bloqueado = v2.avaliar_gate(_linha(ess_t0_sobre_n=0.19), _OK)
    assert bloqueado["status"] == "BLOQUEADO" and "B6_ess_minimo" in bloqueado["bloqueios"]
    for chave in _OK:
        r = v2.avaliar_gate(_linha(), {**_OK, chave: False})
        assert r["status"] == "BLOQUEADO"
    with pytest.raises(ValueError):
        v2.avaliar_gate(_linha(), {"bracos": True})


def test_consolidacao_usa_pior_status_e_b_decide_suporte():
    tabela = pd.DataFrame([
        {"formulacao": "B", "ano": 2014, "status": "APROVADO"},
        {"formulacao": "B", "ano": 2020, "status": "SINALIZADO"},
        {"formulacao": "C", "ano": 2014, "status": "BLOQUEADO"},
        {"formulacao": "C", "ano": 2020, "status": "APROVADO"},
    ])
    r = v2.consolidar_gates(tabela, {"principal": (2014, 2020), "sensibilidade": (2020,)})
    assert r["SUPORTE_V2"] == "SUPORTE_V2_SINALIZADO"
    assert r["SUPORTE_SENSIBILIDADE_C"] == "SUPORTE_SENSIBILIDADE_C_BLOQUEADO"
    assert r["PRONTIDAO"] == "PRONTO_PARA_REVISAO_HUMANA_ANTES_DOS_EFEITOS"
    assert r["por_formulacao"]["C"]["sensibilidade"]["status"] == "APROVADO"
    assert r["por_formulacao"]["B"]["principal"]["anos_sinalizados"] == [2020]
    tabela.loc[0, "status"] = "BLOQUEADO"
    assert v2.consolidar_gates(tabela, {"principal": (2014, 2020)})["PRONTIDAO"] == "NAO_PRONTO_PARA_ESTIMAR_V2"


def test_reconciliacao_de_n():
    meta = {"n_t1": 10, "n_t0": 5}
    assert v2.reconciliar_n(meta, 10, 5)["aprovado"]
    assert not v2.reconciliar_n(meta, 10, 6)["aprovado"]


# --- Contrato congelado ---------------------------------------------------------

def test_contrato_registrado_uma_unica_vez(tmp_path):
    caminho = tmp_path / "contrato.json"
    contrato = {"status": "X", "registrado_em": "t1", "decisao": {"B": "principal"}}
    primeiro = v2.registrar_contrato(caminho, contrato)
    segundo = v2.registrar_contrato(caminho, {**contrato, "registrado_em": "t2"})
    assert segundo["registrado_em"] == "t1" and primeiro["hash_contrato"] == segundo["hash_contrato"]
    with pytest.raises(ValueError):
        v2.registrar_contrato(caminho, {**contrato, "decisao": {"B": "sensibilidade"}})


# --- Ausência de efeito e preservação da V1 --------------------------------------

def test_nenhum_aipw_nem_outcome_no_fluxo(parquet, tmp_path, monkeypatch):
    import sklearn.ensemble
    from src import inferencia_causal, modelagem_preditiva, robustez

    def proibido(*a, **k):
        raise AssertionError("Função de efeito/desfecho chamada no diagnóstico pré-V2")

    monkeypatch.setattr(inferencia_causal, "cross_fitting", proibido)
    monkeypatch.setattr(robustez, "aipw_independente", proibido)
    monkeypatch.setattr(modelagem_preditiva, "ajustar_modelo", proibido)
    monkeypatch.setattr(sklearn.ensemble.HistGradientBoostingClassifier, "fit", proibido)
    for nome in dir(inferencia_causal):
        if "aipw" in nome.lower() and callable(getattr(inferencia_causal, nome)):
            monkeypatch.setattr(inferencia_causal, nome, proibido)
    dados, meta = v2.carregar_populacao(parquet, ANO, "B")
    meta["parquet_sha256"] = "a" * 64
    e, _ = v2.ajustar_propensity_oof(dados, meta, "B", tmp_path, "c" * 64)
    linha, _ = v2.resumir_suporte(dados[list(v2.FEATURES)], dados.tratamento.to_numpy(), e)
    assert not any(t in k.lower() for k in linha for t in ("aipw", "efeito", "ate_", "cate", "ic95"))


def test_modulo_nao_importa_nem_chama_estimadores_de_efeito():
    fonte = (RAIZ / "src/v2_pre_estimacao.py").read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    importados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module)
        elif isinstance(no, ast.Import):
            importados.update(a.name for a in no.names)
    proibidos = {"src.inferencia_causal", "src.robustez", "src.estimativas_temporais", "src.benchmark_nuisance",
                 "src.heterogeneidade", "src.auditoria_pre_v2"}
    assert not (importados & proibidos)
    chamadas = {no.func.attr if isinstance(no.func, ast.Attribute) else getattr(no.func, "id", "")
                for no in ast.walk(arvore) if isinstance(no, ast.Call)}
    tokens = {tok for c in chamadas for tok in c.lower().split("_")}
    assert not (tokens & {"aipw", "cate", "outcome", "outcomes", "hgb", "efeito", "m0", "m1"})
    assert not {c for c in chamadas if "histgradient" in c.lower()}
    assert "HistGradientBoosting" not in fonte


def test_v1_intocada():
    from src import temporal as tp
    from src.amostra import construir_tratamento
    serie = pd.Series(["01", "03", "04", "09", "99", None, "10"])
    assert construir_tratamento(serie).tolist()[:4] == [1, 1, 0, 0]
    assert construir_tratamento(serie).isna().tolist()[4:] == [True, True, True]
    assert tp.DEFINICAO_TRATAMENTO_TEMPORAL == "MESPRENAT entre 1-3 (T=1) versus 4-9 (T=0)"
    assert v2.FORMULACOES["A_V1"]["controles"] == (4, 5, 6, 7, 8, 9)
    fonte = (RAIZ / "src/v2_pre_estimacao.py").read_text(encoding="utf-8")
    for destino in ("outputs/temporal/estimativas", "outputs/temporal/pre_v2",
                    "data/interim/estimativas_temporais"):
        assert destino not in fonte
    # Única referência a diagnósticos históricos: leitura do hash certificado do Parquet 2024.
    assert fonte.count("outputs/diagnostics") == 1
    assert 'outputs/diagnostics/fase2_aipw.json").read_text' in fonte
    # O cache do notebook 08 é lido somente via carregar_cache_propensity (nunca salvo).
    assert "salvar_cache_propensity" not in fonte


def test_contrato_futuro_preserva_janelas_e_especificacoes():
    from src import temporal as tp
    assert tp.JANELAS["principal"]["anos"] == v2.ANOS
    assert tp.JANELAS["sensibilidade"]["anos"] == tuple(range(2018, 2025))
    assert v2.N_FOLDS_DIAGNOSTICO == tp.N_FOLDS_PROPENSITY_TEMPORAL == 5
    assert v2.SEED == tp.SEMENTE_PROPENSITY_TEMPORAL
