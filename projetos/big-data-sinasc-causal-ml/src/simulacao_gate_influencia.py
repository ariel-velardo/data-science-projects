"""Experimento de falsificação da heurística, com nuisances oráculo conhecidos."""
import numpy as np
from src.audita_influencia import aipw_independente, ess_grupos


def simular(n=50000, replicas=200, seed=20240925):
    """DGPs fixados antes de executar; efeito de risco constante -0,01."""
    if n<100 or replicas<2:
        raise ValueError('Experimento insuficiente.')
    cenarios=[]
    for j,nome in enumerate(('S1','S2','S3','S4')):
        rng=np.random.default_rng(seed+j)
        linhas=[]
        for rep in range(replicas):
            x=rng.uniform(-1,1,n)
            if nome=='S1':
                e=np.full(n,.5); m0=np.full(n,.105)
            elif nome=='S2':
                e=np.full(n,.85); m0=np.full(n,.1085)
            elif nome=='S3':
                e=.85+.10*x; m0=.0885+.02*x
            else:
                # 20% com e=.995; demais .81375: E[e]=.85.
                e=np.where(x>.6,.995,.81375); m0=.0885+.02*x
            m1=m0-.01
            t=rng.binomial(1,e); y=rng.binomial(1,np.where(t==1,m1,m0))
            r,psi=aipw_independente(y,t,e,m0,m1)
            q=(psi-psi.mean())**2; k=max(1,int(np.ceil(.01*n)))
            top=float(np.partition(q,-k)[-k:].sum()/q.sum())
            ess=ess_grupos(t,e)
            linhas.append(dict(replica=rep,estimativa=r['estimativa'],erro=r['estimativa']+.01,
                erro_quadratico=(r['estimativa']+.01)**2,se=r['se'],
                cobertura=bool(abs(r['estimativa']+.01)<=1.96*r['se']),top1_if2=top,gate=bool(top>.5),
                ess_t0=ess['0']['ess'],ess_t1=ess['1']['ess'],prop_t1=float(t.mean()),prev_y=float(y.mean())))
        erros=np.array([r['erro'] for r in linhas]); gate=np.mean([r['gate'] for r in linhas])
        cobertura=np.mean([r['cobertura'] for r in linhas])
        cenarios.append(dict(cenario=nome,n=n,n_replicas=replicas,efeito_verdadeiro=-.01,
            bias=float(erros.mean()),rmse=float(np.sqrt(np.mean(erros**2))),
            mcse_bias=float(erros.std(ddof=1)/np.sqrt(replicas)),cobertura=float(cobertura),
            mcse_cobertura=float(np.sqrt(cobertura*(1-cobertura)/replicas)),
            prob_gate=float(gate),mcse_prob_gate=float(np.sqrt(gate*(1-gate)/replicas)),
            top1_if2_medio=float(np.mean([r['top1_if2'] for r in linhas])),
            ess_t0_medio=float(np.mean([r['ess_t0'] for r in linhas])),
            ess_t1_medio=float(np.mean([r['ess_t1'] for r in linhas])),replicas=linhas))
    return dict(seed=seed,metodo='AIPW com e,m0,m1 verdadeiros (oráculo), observações iid',
        dgp={'X':'Uniforme(-1,1)','S1':'e=.5; m0=.105',
             'S2':'e=.85; m0=.1085','S3':'e=.85+.10X; m0=.0885+.02X',
             'S4':'e=.995 se X>.6; .81375 caso contrário; m0=.0885+.02X',
             'todos':'m1=m0-.01; T~Bernoulli(e); Y~Bernoulli(mT); E[Y]=.10 S1/S2 e .08 S3/S4'},
        limitacao='Oráculo isola a heurística; não simula ajuste ML, clusters ou seleção SINASC. Não valida o estudo.',
        cenarios=cenarios)
