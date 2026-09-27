"""Execução integral do DR-Learner; preserva resultados das Fases 0–3."""
import json
from pathlib import Path
import numpy as np
from src.audita_covariaveis import COLUNAS_PROPENSITY_PRINCIPAL
from src.executa_robustez_fase3 import carregar_amostra,sha256,historico
from src.heterogeneidade_dr import particoes_municipais,ajuste_honesto,rotacoes
from src.valida_apresentacao import verificar_preservacao

ROOT=Path(__file__).resolve().parents[1]


def salvar(nome,objeto):
    if not nome.startswith('fase4_'): raise ValueError('Saída fora da Fase 4.')
    (ROOT/'outputs/diagnostics'/nome).write_text(json.dumps(objeto,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def patrimonio():
    arquivos=historico(ROOT)
    for padrao in ('fase1_*.json','fase3_*.json','apresentacao_*.json'):
        for p in (ROOT/'outputs/diagnostics').glob(padrao): arquivos[p.relative_to(ROOT).as_posix()]=sha256(p)
    for p in (ROOT/'notebooks').glob('0[1-4]*.ipynb'): arquivos[p.relative_to(ROOT).as_posix()]=sha256(p)
    return arquivos


def executar():
    ler=lambda p:json.loads(p.read_text(encoding='utf-8'))
    gate=ler(ROOT/'outputs/diagnostics/fase3_gate.json')
    if not gate['permite_exercicio_didatico_fase4'] or gate['gate']=='NOVO_PROBLEMA_METODOLOGICO_IDENTIFICADO':
        raise ValueError('Fase 3 não autoriza o exercício de heterogeneidade.')
    verificar_preservacao(ROOT,historico(ROOT),ler(ROOT/'outputs/diagnostics/fase3_preservacao.json')['historico_sha256'])
    antes=patrimonio(); preservacao=ROOT/'outputs/diagnostics/fase4_preservacao.json'
    if preservacao.exists(): assert ler(preservacao)['sha256']==antes,'Histórico alterado após início da Fase 4.'
    else: salvar('fase4_preservacao.json',dict(checkpoint='1d27ab4e40b5f49ecd53ef0b73134f9e66c28325',sha256=antes))
    dados,auditoria=carregar_amostra(ROOT/'data/processed/sinasc_2024.parquet')
    x=dados.loc[:,list(COLUNAS_PROPENSITY_PRINCIPAL)]
    t=dados.tratamento.to_numpy(); y=dados.Y_BAIXO_PESO.to_numpy(); grupos=dados.CODMUNRES.to_numpy()
    assert len(dados)==2251570 and t.sum()==1942045 and (t==0).sum()==309525
    f=particoes_municipais(grupos)
    particoes=[]
    for k in (1,2,3):
        m=f==k
        assert set(np.unique(t[m]))=={0,1} and set(np.unique(y[m]))=={0,1}
        particoes.append(dict(particao=k,n=int(m.sum()),n_t1=int(t[m].sum()),n_t0=int((t[m]==0).sum()),
            n_y1=int(y[m].sum()),n_municipios=len(np.unique(grupos[m]))))
    list(rotacoes(f,grupos))
    contrato=dict(dados_sha256=sha256(ROOT/'data/processed/sinasc_2024.parquet'),
        chaves_sha256=auditoria['sha256_ordem_contador'],x=list(x.columns),n=len(dados),semente=20240925,
        particoes=particoes,codigo={p:sha256(ROOT/'src'/p) for p in ('heterogeneidade_dr.py',
        'modelagem_preditiva.py','estima_aipw.py','diagnostica_overlap.py','audita_covariaveis.py')})
    salvar('fase4_preflight.json',dict(status='APROVADO',amostra=auditoria,contrato=contrato,
        sem_novas_features=True,municipio_somente_separacao=True,particoes_independentes_de_t_y=True))
    cache=ROOT/'outputs/tables/fase4_predicoes_oof.npz'; logp=ROOT/'outputs/diagnostics/fase4_ajustes.json'
    if cache.exists():
        log=ler(logp)
        if log['contrato']!=contrato or log['cache_sha256']!=sha256(cache):
            raise ValueError('Cache incompatível; preservar e investigar.')
        print('Predições da Fase 4 já existem e correspondem ao contrato.',flush=True)
    else:
        pred,logs=ajuste_honesto(x,t,y,f,grupos)
        pred['contador']=dados.contador.to_numpy(dtype=str)
        np.savez_compressed(cache,**pred)
        salvar('fase4_ajustes.json',dict(contrato=contrato,rotacoes=logs,cache_sha256=sha256(cache)))
    assert patrimonio()==antes,'Um artefato histórico foi alterado.'
    print('Fase 4: ajuste integral concluído; histórico preservado.',flush=True)


if __name__=='__main__': executar()
