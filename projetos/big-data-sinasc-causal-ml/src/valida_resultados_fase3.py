"""Reconciliação independente dos resumos Fase 3, sem refazer nuisances."""
import json
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from src.valida_apresentacao import verificar_preservacao
from src.audita_influencia import aipw_independente
from src.executa_robustez_fase3 import (carregar_amostra,historico,salvar_fase3,
                                       validar_fase2_sem_escrita,sha256)


def validar_folds_persistidos(fold,cobertura,grupos=None):
    if not np.all(np.asarray(cobertura)==1) or set(np.unique(fold))!={1,2,3}:
        raise ValueError('Falha de cobertura OOF.')
    if grupos is not None:
        tabela=pd.DataFrame(dict(grupo=grupos,fold=fold))
        if (tabela.groupby('grupo').fold.nunique()!=1).any():
            raise ValueError('Um cluster aparece em mais de um fold.')


def comparar_linha(row,psi,grupos):
    """Sandwich independente por SQL; não chama resumo_cluster."""
    theta=float(np.mean(psi)); n=len(psi)
    scores=pd.DataFrame(dict(grupo=grupos,score=psi-theta))
    with duckdb.connect() as c:
        c.register('scores',scores)
        G,soma=c.execute('SELECT count(*),sum(u*u) FROM (SELECT grupo,sum(score) u FROM scores GROUP BY grupo)').fetchone()
    se_cl=np.sqrt(G/(G-1)*soma/n**2)
    assert row['n']==n
    np.testing.assert_allclose(row['estimativa'],theta,rtol=0,atol=1e-12)
    np.testing.assert_allclose(row['se_iid'],np.std(psi,ddof=1)/np.sqrt(n),rtol=0,atol=1e-12)
    np.testing.assert_allclose(row['se_cluster'],se_cl,rtol=0,atol=1e-12)


def validar(raiz=None):
    raiz=Path(raiz or Path(__file__).resolve().parents[1]); p=raiz/'outputs/diagnostics'
    ler=lambda nome:json.loads((p/nome).read_text(encoding='utf-8'))
    esperado=ler('fase3_preservacao.json')['historico_sha256']
    verificar_preservacao(raiz,historico(raiz),esperado)
    fase2=validar_fase2_sem_escrita(raiz)
    sens=ler('fase3_sensibilidades.json'); geo=ler('fase3_crossfit_geografico.json')
    n_linhas=0; populacoes={}
    for nome,cenario,arquivo,resumo in (
        ('aleatorio','P1','fase2_predicoes_oof.npz',geo['aleatorio']),
        ('geografico','P1','fase3_geografico_oof.npz',geo['agrupado']),
        ('consprenat','CONSPRENAT','fase3_consprenat_oof.npz',sens['CONSPRENAT']),
        ('p0','P0','fase3_p0_oof.npz',sens['P0']),
        ('multiplas','MULTIPLAS','fase3_multiplas_oof.npz',sens['MULTIPLAS'])):
        dados,info=carregar_amostra(raiz/'data/processed/sinasc_2024.parquet',cenario)
        with np.load(raiz/'outputs/tables'/arquivo) as a:
            pred={k:a[k] for k in a.files}
        assert all(len(v)==len(dados) for v in pred.values())
        validar_folds_persistidos(pred['fold_id'],pred['cobertura'],dados.CODMUNRES.to_numpy() if nome=='geografico' else None)
        if nome!='aleatorio':
            log=ler(f'fase3_{nome}_ajustes.json')
            assert log['cache_sha256']==sha256(raiz/'outputs/tables'/arquivo)
            assert log['contrato']['chaves']==info['sha256_ordem_contador']
            assert log['contrato']['dados']==sha256(raiz/'data/processed/sinasc_2024.parquet')
            assert log['contrato']['x']==list(dados.columns[3:10])
            for f,h in log['contrato']['codigo'].items():
                assert sha256(raiz/'src'/f)==h,'Código do ajuste alterado após execução.'
        t=dados.tratamento.to_numpy(); y=dados.Y_BAIXO_PESO.to_numpy()
        rows=list(resumo['resultados'])
        if nome=='aleatorio':
            with np.load(raiz/'outputs/tables/fase3_c3_propensity_oof.npz') as a:
                np.testing.assert_array_equal(a['contador'],dados.contador.to_numpy(dtype=str))
                pred['e_C3']=a['e_C3']
            rows += [r for r in sens['S0']['resultados'] if r['especificacao']=='C3']
        for row in rows:
            s=row['especificacao']; e=pred['e_C3' if s=='C3' else 'e']; outcome='C2' if s=='C3' else s
            mask=np.ones(len(t),bool) if row['populacao']=='sem_trimming' else (e>=.05)&(e<=.95)
            _,psi=aipw_independente(y[mask],t[mask],e[mask],pred['m0_'+outcome][mask],pred['m1_'+outcome][mask])
            comparar_linha(row,psi,dados.CODMUNRES.to_numpy()[mask]); n_linhas+=1
        populacoes[nome]=dict(n=len(dados),n_t1=int(t.sum()),n_t0=int((t==0).sum()))
    principal=populacoes['aleatorio']['n']
    assert principal-populacoes['consprenat']['n']==sens['amostras']['P1']['n_consprenat_zero']
    assert populacoes['p0']['n']-principal==sens['amostras']['P0']['n_peso_fora_p1']
    assert populacoes['multiplas']['n']-principal==sens['amostras']['MULTIPLAS']['n_multipla']
    verificar_preservacao(raiz,historico(raiz),esperado)
    resultado=dict(status='APROVADO',linhas_reconciliadas=n_linhas,tolerancia_absoluta=1e-12,
                   sandwich_independente='DuckDB GROUP BY; score centrado por registro',
                   fase2=fase2,populacoes=populacoes,historico_intacto=True,
                   clusters_exclusivos_nos_folds=True)
    salvar_fase3(p/'fase3_validacao.json',resultado)
    print(json.dumps(resultado,ensure_ascii=False,indent=2))
    return resultado


if __name__=='__main__':
    validar()
