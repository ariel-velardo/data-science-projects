import numpy as np
import pandas as pd
import pytest

from src.estima_aipw import calcular_aipw, gerar_folds, cross_fitting


def test_aipw_efeito_zero_e_ic():
    rng = np.random.default_rng(42)
    n = 20000
    t = rng.binomial(1, .5, n)
    y = rng.binomial(1, .2, n)
    r, psi = calcular_aipw(y, t, np.full(n, .5), np.full(n, .2), np.full(n, .2))
    assert abs(r['estimativa']) < .02
    assert r['ic95_inferior'] < r['estimativa'] < r['ic95_superior']
    assert r['se'] == pytest.approx(np.std(psi, ddof=1) / np.sqrt(n))


def test_aipw_sinal_e_dupla_robustez_com_propensity_correto():
    rng = np.random.default_rng(43)
    n = 30000
    t = rng.binomial(1, .5, n)
    y = rng.binomial(1, .3 - .1 * t)
    r, _ = calcular_aipw(y, t, np.full(n, .5), np.full(n, .5), np.full(n, .5))
    assert -.12 < r['estimativa'] < -.08


def test_dupla_robustez_outcome_correto_propensity_errado():
    rng = np.random.default_rng(15)
    n = 50000
    x = rng.binomial(1, .5, n)
    t = rng.binomial(1, .2 + .6*x)
    m0 = .1 + .2*x
    m1 = m0 - .05
    y = rng.binomial(1, np.where(t == 1, m1, m0))
    r, _ = calcular_aipw(y, t, np.full(n, .5), m0, m1)
    assert abs(r['estimativa'] + .05) < .015


def test_pesos_ess_e_influencia_simples():
    from src.estima_aipw import diagnosticos_influencia
    d = diagnosticos_influencia(np.tile([-1., 1.], 50), np.tile([0, 1], 50), np.full(100, .5))
    assert d['pesos_por_grupo']['0']['ess'] == pytest.approx(50)
    assert d['frac_variancia_top1pct'] == pytest.approx(.01)


def test_gate_respeita_criterios_pre_especificados():
    from src.executa_fase2 import classificar_gate
    linhas = [dict(especificacao=s, populacao='sem_trimming', estimativa_pp=v) for s,v in [('C1',-1.3),('C2',-1.2)]]
    assert classificar_gate(linhas, {'d': {'frac_variancia_top1pct': .8}}) == 'RESULTADO_NAO_INTERPRETAVEL'
    assert classificar_gate(linhas, {'d': {'frac_variancia_top1pct': .2}}) == 'RESULTADO_EXPLORATORIO_ESTAVEL'
    linhas[1]['estimativa_pp'] = -.5
    assert classificar_gate(linhas, {'d': {'frac_variancia_top1pct': .2}}) == 'RESULTADO_SENSIVEL_A_ESPECIFICACAO'


@pytest.mark.parametrize('campo,valor', [('e', 0), ('e', 1), ('e', np.nan), ('m0', -1), ('m1', 2)])
def test_aipw_rejeita_predicoes_invalidas(campo, valor):
    a = dict(y=np.array([0, 1, 0, 1]), t=np.array([0, 1, 0, 1]), e=np.full(4, .5), m0=np.full(4, .2), m1=np.full(4, .3))
    a[campo][0] = valor
    with pytest.raises(ValueError):
        calcular_aipw(**a)


def test_aipw_rejeita_grupo_unico_e_tamanho_errado():
    with pytest.raises(ValueError):
        calcular_aipw([0, 1], [1, 1], [.5, .5], [.2, .2], [.3, .3])
    with pytest.raises(ValueError):
        calcular_aipw([0, 1], [0, 1], [.5], [.2, .2], [.3, .3])


def test_folds_reproduziveis_sem_sobreposicao():
    t = np.tile([0, 1, 0, 1], 30)
    y = np.tile([0, 0, 1, 1], 30)
    a = gerar_folds(t, y, 3, 42)
    b = gerar_folds(t, y, 3, 42)
    cobertura = np.zeros(len(t))
    for (tr, va), (tr2, va2) in zip(a, b):
        assert not np.intersect1d(tr, va).size
        np.testing.assert_array_equal(va, va2)
        cobertura[va] += 1
    assert np.all(cobertura == 1)


def test_cross_fitting_guarda_de_leakage():
    with pytest.raises(ValueError, match='proibidas'):
        cross_fitting(pd.DataFrame({'PESO': [2000]*20}), np.tile([0, 1], 10), np.tile([1, 0], 10), 2)


def test_folds_nao_truncam_tratamento_fracionario():
    with pytest.raises(ValueError):
        gerar_folds(np.tile([.5, 1], 20), np.tile([0, 1], 20), 2)


def test_cross_fitting_rejeita_tratamento_fracionario_antes_de_converter():
    from src.audita_covariaveis import COLUNAS_PROPENSITY_PRINCIPAL
    x = pd.DataFrame({c: [1]*40 for c in COLUNAS_PROPENSITY_PRINCIPAL})
    with pytest.raises(ValueError, match='T/Y'):
        cross_fitting(x, np.tile([.5, 1], 20), np.tile([0, 1], 20), 2)


def test_cross_fitting_pequeno_reconcilia_e_sem_nan():
    rng = np.random.default_rng(40)
    n = 400
    x = pd.DataFrame({'IDADEMAE_NUM': rng.normal(28, 5, n)})
    for nome in ['ESCOLARIDADE_MAE', 'RACA_COR_MAE', 'SITUACAO_CONJUGAL', 'PARIDADE_CAT', 'PERDAS_FETAIS_CAT', 'UF_RESIDENCIA']:
        x[nome] = rng.choice(['1', '2'], n)
    t = rng.binomial(1, .5, n)
    y = rng.binomial(1, .3 - .1*t)
    r = cross_fitting(x, t, y, 2)
    assert len(r['e']) == n
    assert np.isfinite(r['m0_C1']).all() and np.isfinite(r['m1_C2']).all()
    assert np.all(r['cobertura'] == 1)
    assert sum(f['n_validacao'] for f in r['folds']) == n
