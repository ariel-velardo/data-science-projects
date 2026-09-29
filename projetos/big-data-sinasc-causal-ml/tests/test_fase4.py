import numpy as np
import pandas as pd
import pytest
from src.heterogeneidade import (pseudo_desfecho,particoes_municipais,rotacoes,
    criar_regressor,ajustar_regressor,prever_regressor,quintis,resumo_distribuicao,
    resumir_grupos,ajuste_honesto)
from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL


def x_sintetico(n=6000):
    rng=np.random.default_rng(4321)
    x=pd.DataFrame({'IDADEMAE_NUM':rng.uniform(18,40,n)})
    for c in COLUNAS_PROPENSITY_PRINCIPAL[1:]: x[c]=rng.choice(['1','2'],n)
    return x


def test_pseudo_desfecho_manual():
    np.testing.assert_allclose(pseudo_desfecho([1,0],[1,0],[.5,.5],[.2,.2],[.3,.3]),[1.5,.5])


def test_particoes_e_rotacoes_sem_contaminacao():
    grupos=np.repeat(np.arange(90),10); f=particoes_municipais(grupos)
    np.testing.assert_array_equal(f,particoes_municipais(grupos))
    cobertura=np.zeros(len(f))
    for a,b,c in rotacoes(f,grupos):
        assert not set(grupos[a])&set(grupos[b])
        assert not set(grupos[a])&set(grupos[c])
        assert not set(grupos[b])&set(grupos[c])
        cobertura[c]+=1
    assert np.all(cobertura==1)


def test_rejeita_particao_dividindo_municipio():
    with pytest.raises(ValueError): list(rotacoes(np.tile([1,2,3],10),np.zeros(30)))


def test_efeito_constante_sintetico():
    x=x_sintetico(); psi=np.full(len(x),-.02)
    m=ajustar_regressor(criar_regressor('hgb',min_folha=100),x.iloc[:4000],psi[:4000])
    p=prever_regressor(m,x.iloc[4000:])
    np.testing.assert_allclose(p,-.02,atol=1e-12)
    assert np.isfinite(p).all()


def test_heterogeneidade_sintetica_conhecida_e_reprodutivel():
    x=x_sintetico(); rng=np.random.default_rng(123)
    tau=np.where(x.IDADEMAE_NUM<29,-.12,.08); psi=tau+rng.normal(0,.15,len(x))
    ps=[]
    for _ in range(2):
        m=ajustar_regressor(criar_regressor('hgb',min_folha=100),x.iloc[:4000],psi[:4000])
        ps.append(prever_regressor(m,x.iloc[4000:]))
    np.testing.assert_array_equal(*ps)
    assert np.sqrt(np.mean((ps[0]-tau[4000:])**2))<.03


def test_quintis_empates_e_n():
    p=np.zeros(103); q=quintis(p)
    assert set(q)=={1,2,3,4,5}
    assert sum(np.bincount(q))==103
    assert np.ptp(np.bincount(q)[1:])<=1
    np.testing.assert_array_equal(q,quintis(p))


def test_agregacao_grupos_reconcilia():
    p=np.array([-.02,-.04,.01,.03]); grupos=np.array(['a','a','b','b'])
    r=resumir_grupos(p,grupos)
    assert sum(v['n'] for v in r)==4
    assert r[0]['media_pp']==pytest.approx(-3.)
    assert np.average([v['media_pp'] for v in r],weights=[v['n'] for v in r])==pytest.approx(100*p.mean())
    assert resumo_distribuicao(p)['proporcao_negativa']==.5


def test_guarda_x_nao_admite_desfecho():
    x=x_sintetico(30); x['PESO']=2000
    with pytest.raises(ValueError): ajustar_regressor(criar_regressor('hgb'),x,np.zeros(30))


def test_rota_real_nao_usa_y_validacao(monkeypatch):
    import src.heterogeneidade as h
    x=x_sintetico(90); t=np.tile([0,1],45); y=np.tile([0,0,1],30)
    f=np.repeat([1,2,3],30); grupos=np.arange(90)
    eventos=[]
    class Modelo:
        pass
    def ajustar(m,xx,yy):
        m.indices=set(xx.index); eventos.append(('ajuste',m.indices)); return m,{}
    def prever(m,xx):
        assert not m.indices&set(xx.index)
        return np.full(len(xx),.5)
    def cate_fit(m,xx,yy): m.indices=set(xx.index); eventos.append(('cate',m.indices)); return m
    def cate_pred(m,xx):
        assert not m.indices&set(xx.index)
        return np.full(len(xx),-.01)
    monkeypatch.setattr(h,'criar_modelo',lambda tipo:Modelo())
    monkeypatch.setattr(h,'ajustar_modelo',ajustar); monkeypatch.setattr(h,'predizer',prever)
    monkeypatch.setattr(h,'criar_regressor',lambda *a,**k:Modelo())
    monkeypatch.setattr(h,'ajustar_regressor',cate_fit); monkeypatch.setattr(h,'prever_regressor',cate_pred)
    p,logs=ajuste_honesto(x,t,y,f,grupos)
    assert np.all(p['cobertura']==1) and np.isfinite(p['cate_hgb']).all()
    assert len(logs)==3 and len(eventos)==15
    for k in range(3):
        a,b,c=list(rotacoes(f,grupos))[k]
        for _,indices in eventos[5*k:5*k+3]: assert indices<=set(a)
        for _,indices in eventos[5*k+3:5*k+5]: assert indices==set(b)


def test_dr_bernoulli_constante_com_avaliacao_externa():
    x=x_sintetico(20000); rng=np.random.default_rng(72)
    t=rng.binomial(1,.5,len(x)); y=rng.binomial(1,.3-.05*t)
    psi=pseudo_desfecho(y,t,np.full(len(x),.5),np.full(len(x),.3),np.full(len(x),.25))
    m=ajustar_regressor(criar_regressor('hgb'),x.iloc[:15000],psi[:15000])
    p=prever_regressor(m,x.iloc[15000:])
    assert np.sqrt(np.mean((p+.05)**2))<.05


def test_contraste_externo_conhecido():
    from src.heterogeneidade import contraste_extremos
    cate=np.repeat(np.arange(5),20)*.01
    r=contraste_extremos(cate,cate,np.arange(100))
    assert r['contraste_dr_q5_q1_pp']==pytest.approx(4.)
    assert r['se_municipal_pp']==pytest.approx(0.,abs=1e-12)


@pytest.mark.parametrize('rho,delta,ic,esperado',[
    (.9,1.,(-1.,2.),'HETEROGENEIDADE_NAO_EVIDENCIADA'),
    (.2,1.,(.5,1.5),'HETEROGENEIDADE_SENSIVEL_A_MODELO'),
    (.9,1.,(.5,1.5),'HETEROGENEIDADE_EXPLORATORIA_ESTAVEL'),
])
def test_gate_exige_avaliacao(rho,delta,ic,esperado):
    from src.heterogeneidade import classificar
    r=dict(contraste_dr_q5_q1_pp=delta,ic95_inferior_pp=ic[0],ic95_superior_pp=ic[1])
    assert classificar(dict(contrastes_externos=[r]*3,spearman_hgb_ridge=rho,mediana_spearman_perfis=.9))==esperado
