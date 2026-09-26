"""Casos analíticos independentes e contratos da auditoria Fase 3."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.audita_influencia import aipw_independente, concentracao, ess_grupos
from src.inferencia_cluster import resumo_cluster, bootstrap_cluster, leave_one_out, folds_agrupados
from src.simulacao_gate_influencia import simular
from src.executa_robustez_fase3 import carregar_amostra, salvar_fase3, crossfit_auditoria


def test_aipw_analitico_sinal_media_e_normalizacao():
    # T=0: .2-(Y-.2)/.5; T=1: .2+(Y-.4)/.5.
    r, psi = aipw_independente([0, 1, 0, 1], [0, 0, 1, 1], [.5]*4, [.2]*4, [.4]*4)
    np.testing.assert_allclose(psi, [.6, -1.4, -.6, 1.4], atol=1e-15)
    assert r['estimativa'] == pytest.approx(0, abs=1e-15)
    assert r['se'] == pytest.approx(np.sqrt(4.64/12))


@pytest.mark.parametrize('bad', [0., 1., np.nan])
def test_auditoria_rejeita_propensity_invalido(bad):
    with pytest.raises(ValueError):
        aipw_independente([0, 1], [0, 1], [bad, .5], [.1]*2, [.2]*2)


def test_concentracao_uniforme_e_arredondamento():
    r = concentracao(np.tile([-1., 1.], 50))
    assert r['faixas'][0]['n'] == 1
    assert next(d for d in r['faixas'] if d['top_pct'] == 1)['fracao_if2'] == pytest.approx(.01)
    assert np.all(np.diff(r['curva']['fracao_if2']) >= 0)
    assert r['curva']['fracao_if2'][-1] == pytest.approx(1)


def test_concentracao_evento_unico_e_contribuicao_liquida():
    psi = np.zeros(1000); psi[0] = 10
    r = concentracao(psi)
    top = next(d for d in r['faixas'] if d['top_pct'] == .1)
    assert top['fracao_if2'] == pytest.approx(.999)
    assert top['contribuicao_psi_pp'] == pytest.approx(1.)
    assert top['contribuicao_if_pp'] == pytest.approx(.999)


def test_variancia_nula_explicita():
    assert concentracao(np.ones(100))['variancia_nula']


def test_ess_pesos_desiguais():
    d = ess_grupos([0, 0, 1, 1], [.5, .75, .5, .25])
    assert d['0']['ess'] == pytest.approx(36/20)
    assert d['1']['ess'] == pytest.approx(36/20)


def test_cluster_se_analitico_e_singletons_equivalem_iid():
    psi = np.array([1., 3., 5., 7.])
    # theta=4; U=(-4,4); G/(G-1)*sum(U²)/N²=4.
    r = resumo_cluster(psi, ['a','a','b','b'])
    assert r['se_cluster'] == pytest.approx(2.)
    assert r['se_iid'] == pytest.approx(np.sqrt(20/12))
    s = resumo_cluster(psi, np.arange(4))
    assert s['se_cluster'] == pytest.approx(s['se_iid'])


def test_cluster_centrado_por_registro_nao_por_media_de_cluster():
    psi = np.array([0.,0.,0.,4.])
    r = resumo_cluster(psi, ['a','a','a','b'])
    assert r['estimativa'] == 1.
    assert r['se_cluster'] == pytest.approx(1.5)


@pytest.mark.parametrize('g', [['a']*4, ['a',None,'b','b']])
def test_cluster_invalido(g):
    with pytest.raises(ValueError):
        resumo_cluster([1,2,3,4], g)


def test_bootstrap_reproduzivel_e_denominador_variavel():
    psi = np.array([0.,0.,0.,4.]); g=['a','a','a','b']
    a = bootstrap_cluster(psi,g,200,42)
    b = bootstrap_cluster(psi,g,200,42)
    assert a == b
    assert set(a['replicas']).issubset({0.,1.,4.})
    assert a['n_bootstrap_min'] == 2 and a['n_bootstrap_max'] == 6


def test_leave_one_cluster_out_reconcilia():
    psi=np.arange(7.)
    g=np.array(['a']*3+['b']*2+['c']*2)
    for row in leave_one_out(psi,g):
        assert row['estimativa_pp'] == pytest.approx(100*psi[g!=row['grupo']].mean())
        assert row['n_removido'] == (g==row['grupo']).sum()


def test_folds_sem_municipios_compartilhados_reproduziveis():
    g=np.repeat(np.arange(30),8); t=np.tile([0,0,1,1],60); y=np.tile([0,1,0,1],60)
    a=folds_agrupados(t,y,g); b=folds_agrupados(t,y,g)
    cobertura=np.zeros(len(t),int)
    for (tr,va),(tr2,va2) in zip(a,b):
        assert not set(g[tr]) & set(g[va])
        np.testing.assert_array_equal(va,va2)
        cobertura[va]+=1
    assert np.all(cobertura==1)


def test_simulacao_oraculo_recupera_efeito_sem_teste_de_cobertura_rigido():
    a=simular(n=5000,replicas=40,seed=91)
    b=simular(n=5000,replicas=40,seed=91)
    assert a==b
    for s in a['cenarios']:
        assert abs(s['bias']) < 4*s['mcse_bias']
        assert s['rmse'] > 0
        assert len(s['replicas']) == 40


def test_escrita_nunca_aceita_nome_historico(tmp_path):
    p=tmp_path/'fase2_aipw.json'; p.write_text('historico')
    with pytest.raises(ValueError):
        salvar_fase3(p,{'novo': True})
    assert p.read_text()=='historico'


def test_c3_rejeita_municipio_em_x_e_outcome():
    with pytest.raises(ValueError):
        crossfit_auditoria(pd.DataFrame({'CODMUNRES':['123456']*40}), np.tile([0,1],20),np.tile([1,0],20),c3=True)


def test_resumo_integra_estimativa_cluster_e_nuisances():
    from src.executa_robustez_fase3 import resumo_predicoes
    dados=pd.DataFrame({'tratamento':np.tile([0,0,1,1],30),
                        'Y_BAIXO_PESO':np.tile([0,1,0,1],30),
                        'CODMUNRES':np.repeat(np.arange(30),4)})
    pred={k:np.full(120,.5) for k in ('e','m0_C1','m1_C1','m0_C2','m1_C2')}
    r=resumo_predicoes(dados,pred)
    assert len(r['resultados'])==4
    assert all(a['n']==120 and a['estimativa']==0 for a in r['resultados'])


def test_c3_fit_real_prediz_somente_registros_fora_do_treino(monkeypatch):
    import src.executa_robustez_fase3 as modulo
    rng=np.random.default_rng(110)
    n=600
    x=pd.DataFrame({'IDADEMAE_NUM':rng.normal(28,5,n)})
    for col in ['ESCOLARIDADE_MAE','RACA_COR_MAE','SITUACAO_CONJUGAL','PARIDADE_CAT','PERDAS_FETAIS_CAT','UF_RESIDENCIA']:
        x[col]=rng.choice(['1','2'],n)
    t=np.tile([0,0,1,1],150); y=np.tile([0,1,0,1],150)
    ajuste_original=modulo.ajustar_modelo
    predicao_original=modulo.predizer
    contagem=[]
    def ajustar(modelo,treino,target):
        modelo,log=ajuste_original(modelo,treino,target)
        modelo.indices_auditoria=set(treino.index)
        return modelo,log
    def predizer_sem_leakage(modelo,validacao):
        assert not modelo.indices_auditoria & set(validacao.index)
        contagem.append(len(validacao))
        return predicao_original(modelo,validacao)
    monkeypatch.setattr(modulo,'ajustar_modelo',ajustar)
    monkeypatch.setattr(modulo,'predizer',predizer_sem_leakage)
    p,logs=modulo.crossfit_auditoria(x,t,y,c3=True)
    assert len(contagem)==18  # 6 nuisances em cada um dos três folds.
    assert np.all(p['cobertura']==1) and np.isfinite(p['e_C3']).all()


def test_contraexemplo_aipw_gate_superior_50_com_overlap_oraculo():
    # Frequências exatas: P(T=0,Y=1)=.012; P(T=1,Y=1)=.0595.
    t=np.repeat([0,0,1,1],[120,1380,595,7905])
    y=np.repeat([1,0,1,0],[120,1380,595,7905])
    r,psi=aipw_independente(y,t,np.full(10000,.85),np.full(10000,.08),np.full(10000,.07))
    assert r['estimativa']==pytest.approx(-.01)
    top=next(f for f in concentracao(psi)['faixas'] if f['top_pct']==1)
    assert top['fracao_if2']==pytest.approx(.01*(.92/.15)**2/(.07*.93/.85+.08*.92/.15))
    assert top['fracao_if2']>.5


def test_populacoes_sensibilidade_preservam_x_e_reconciliam(tmp_path):
    import duckdb
    raw=pd.DataFrame(dict(contador=list('abcdefg'), MESPRENAT=['1','4','1','4','1','4','99'],
        PESO=['3000','2000','499','6100','2000','3000','3000'], GRAVIDEZ=['1','1','1','1','2','3','1'],
        CONSPRENAT=['1','0','1','1','1','1','1'], IDADEMAE=['25']*7, ESCMAE2010=['3']*7,
        RACACORMAE=['4']*7,ESTCIVMAE=['1']*7,PARIDADE=['0']*7,QTDFILMORT=['00']*7,
        CODMUNRES=['355030']*7,DTNASC=['01012024']*7))
    p=tmp_path/'raw.parquet'
    with duckdb.connect() as c:
        c.register('raw',raw); c.execute('COPY raw TO ? (FORMAT PARQUET)',[str(p)])
    principal,_=carregar_amostra(p,'P1')
    p0,_=carregar_amostra(p,'P0')
    mult,_=carregar_amostra(p,'MULTIPLAS')
    s1,_=carregar_amostra(p,'CONSPRENAT')
    assert principal.contador.tolist()==['a','b']
    assert p0.contador.tolist()==['a','b','c','d']
    assert mult.contador.tolist()==['a','b','e','f']
    assert s1.contador.tolist()==['a']
    pd.testing.assert_frame_equal(principal,p0.iloc[:2].reset_index(drop=True))
