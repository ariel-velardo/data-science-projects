"""Reconciliação das saídas DR-Learner com predições externas e população fixa."""
import json
import numpy as np
from src.executa_fase4 import ROOT,salvar,patrimonio
from src.executa_robustez_fase3 import carregar_amostra,sha256
from src.heterogeneidade_dr import particoes_municipais,rotacoes,quintis
from src.resume_fase4 import classificar


def validar():
    ler=lambda nome:json.loads((ROOT/'outputs/diagnostics'/nome).read_text(encoding='utf-8'))
    assert patrimonio()==ler('fase4_preservacao.json')['sha256']
    log=ler('fase4_ajustes.json'); r=ler('fase4_resultados.json')
    dados,auditoria=carregar_amostra(ROOT/'data/processed/sinasc_2024.parquet')
    assert sha256(ROOT/'data/processed/sinasc_2024.parquet')==log['contrato']['dados_sha256']
    assert auditoria['sha256_ordem_contador']==log['contrato']['chaves_sha256']
    for f,h in log['contrato']['codigo'].items(): assert sha256(ROOT/'src'/f)==h
    arquivo=ROOT/'outputs/tables/fase4_predicoes_oof.npz'
    assert sha256(arquivo)==log['cache_sha256']
    with np.load(arquivo) as a: p={k:a[k] for k in a.files}
    assert all(len(v)==len(dados) for v in p.values())
    np.testing.assert_array_equal(p['contador'],dados.contador.to_numpy(dtype=str))
    assert np.all(p['cobertura']==1)
    assert all(np.isfinite(v).all() for k,v in p.items() if k!='contador')
    t,y=dados.tratamento.to_numpy(),dados.Y_BAIXO_PESO.to_numpy()
    assert np.all((p['e']>0)&(p['e']<1))
    assert all(np.all((p[m]>=0)&(p[m]<=1)) for m in ('m0','m1'))
    # Reconstrução separada por grupo, sem chamar a função de pseudo-desfecho.
    esperado=p['m1']-p['m0']
    esperado[t==1]+=(y[t==1]-p['m1'][t==1])/p['e'][t==1]
    esperado[t==0]-=(y[t==0]-p['m0'][t==0])/(1-p['e'][t==0])
    np.testing.assert_allclose(p['psi'],esperado,rtol=0,atol=1e-12)
    grupos=dados.CODMUNRES.to_numpy(); fold=particoes_municipais(grupos)
    np.testing.assert_array_equal(fold,p['fold_id'])
    import hashlib
    for (a,b,c),l in zip(rotacoes(fold,grupos),log['rotacoes']):
        assert (len(a),len(b),len(c))==(l['n_auxiliares'],l['n_cate'],l['n_avaliacao'])
        for nome,i in zip(('A','B','C'),(a,b,c)): assert hashlib.sha256(i.tobytes()).hexdigest()==l['indices_sha256'][nome]
    cate=p['cate_hgb']; q=quintis(cate)
    assert len(cate)==2251570 and r['principal']['n']==len(cate)
    np.testing.assert_allclose(r['principal']['media_pp'],100*cate.mean(),rtol=0,atol=1e-12)
    for campo,percentil in (('p05_pp',.05),('p25_pp',.25),('mediana_pp',.5),('p75_pp',.75),('p95_pp',.95)):
        np.testing.assert_allclose(r['principal'][campo],100*np.quantile(cate,percentil),rtol=0,atol=1e-12)
    assert sum(r['histograma']['contagens'])==len(cate)
    assert sum(s['n'] for s in r['quintis'])==len(cate)
    for s in r['quintis']:
        mask=q==s['quintil']; assert mask.sum()==s['n']
        np.testing.assert_allclose(s['cate_medio_pp'],100*cate[mask].mean(),rtol=0,atol=1e-10)
        np.testing.assert_allclose(s['prevalencia_observada_pct'],100*y[mask].mean(),rtol=0,atol=1e-10)
    for dim in {s['dimensao'] for s in r['perfis']}:
        rs=[s for s in r['perfis'] if s['dimensao']==dim]
        assert sum(s['n'] for s in rs)==len(cate)
        np.testing.assert_allclose(np.average([s['media_pp'] for s in rs],weights=[s['n'] for s in rs]),100*cate.mean(),rtol=0,atol=1e-10)
    for col in log['contrato']['x'][1:]:
        for k in range(1,6):
            rs=[s for s in r['quintis_composicao_x'] if s['variavel']==col and s['quintil']==k]
            assert sum(s['n'] for s in rs)==int((q==k).sum())
            np.testing.assert_allclose(sum(s['percentual'] for s in rs),100.,atol=1e-10)
    # ICs externos: recomputar variância da diferença diretamente por somas municipais.
    for s in r['estabilidade']['contrastes_externos']:
        mask=fold==s['particao']; z=esperado[mask]; cs=cate[mask]; g=grupos[mask]; qs=quintis(cs)
        baixo,alto=qs==1,qs==5; delta=z[alto].mean()-z[baixo].mean()
        u=np.where(alto,(z-z[alto].mean())/alto.sum(),0)-np.where(baixo,(z-z[baixo].mean())/baixo.sum(),0)
        import pandas as pd
        somas=pd.DataFrame(dict(g=g,u=u)).groupby('g').u.sum().to_numpy(); G=len(somas)
        se=np.sqrt(G/(G-1)*np.sum(somas**2))
        np.testing.assert_allclose([s['contraste_dr_q5_q1_pp'],s['se_municipal_pp']],[100*delta,100*se],rtol=0,atol=1e-10)
    assert r['gate']==classificar(r['estabilidade'])==ler('fase4_gate.json')['gate']
    resultado=dict(status='APROVADO',n=len(dados),n_t1=int(t.sum()),n_t0=int((t==0).sum()),
        cobertura_unica=True,papeis_municipais_disjuntos=True,pseudo_desfecho_reconciliado=True,
        quintis_e_perfis_reconciliados=True,historico_fases_0_3_preservado=True,
        tolerancia_absoluta_score=1e-12,tolerancia_resumos=1e-10,gate=r['gate'])
    salvar('fase4_validacao.json',resultado)
    print(json.dumps(resultado,ensure_ascii=False,indent=2)); return resultado


if __name__=='__main__': validar()
