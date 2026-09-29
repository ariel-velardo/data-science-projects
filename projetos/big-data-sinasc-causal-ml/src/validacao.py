"""Preservação e validação de artefatos científicos."""
from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
import duckdb
import numpy as np
from src.amostra import _criar_views
from src.sinasc import _salvar_json
from src.inferencia_causal import resumir_especificacoes
import pandas as pd
from src.robustez import aipw_independente
from src.amostra import carregar_amostra
from src.robustez import salvar_fase3
from src.sinasc import calcular_sha256 as sha256
from src.heterogeneidade import ROOT
from src.heterogeneidade import salvar_heterogeneidade as salvar
from src.heterogeneidade import particoes_municipais
from src.heterogeneidade import rotacoes
from src.heterogeneidade import quintis
from src.heterogeneidade import classificar
import argparse
import csv
import html
import unicodedata
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]

AUTORIZADOS={'src/cria_notebook_fase2.py','notebooks/03_ml_preditivo_e_aipw.ipynb'}

# Allowlist EXATA: só estes 4 caminhos têm divergência comprovada de EOL
# (core.autocrlf=true grava CRLF no checkout; os blobs Git e os hashes
# históricos foram calculados sobre LF). Nenhum outro caminho é normalizado.
CAMINHOS_NORMALIZAR_EOL = frozenset({
    'data/raw/.gitkeep',
    'docs/methodology/PLANO_ESTIMACAO_FASE2.md',
    'docs/methodology/RESULTADOS_E_LIMITACOES_FASE2.md',
    'outputs/diagnostics/VALIDACAO_FASE2.md',
})

def hash_arquivo(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def sha256_preservacao(raiz, nome):
    """Hash binário estrito, exceto nos 4 caminhos da allowlist de EOL."""
    caminho = raiz / nome
    if nome in CAMINHOS_NORMALIZAR_EOL:
        return hashlib.sha256(caminho.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    return sha256(caminho)

def hash_fontes_notebook(p):
    nb=json.loads(Path(p).read_text(encoding='utf-8'))
    fontes=[(c['cell_type'],''.join(c['source'])) for c in nb['cells']]
    return hashlib.sha256(json.dumps(fontes,ensure_ascii=False).encode()).hexdigest()


def _baseline(raiz):
    texto = (raiz/'docs/architecture/BASELINE_PRE_REFATORACAO.md').read_text(encoding='utf-8')
    return json.loads(texto.split('```json\n', 1)[1].split('\n```', 1)[0])


def _manifesto_refatoracao(raiz):
    p = raiz/'docs/architecture/preservacao_refatoracao.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


# Hash canônico do bloco `migracoes` (destinos como produzidos pela refatoração
# original). Fixado em código: reescrever o histórico só no JSON falha.
SHA256_MIGRACOES_HISTORICAS = '6a5c1fb2a2c615518a3abd23e23d93cb00256382ac71aa84de72b8385ba240ae'
SHA256_BASELINE_PRE_REFATORACAO = '7dbcd5919af84278355359f7fd66e69fc4922d63f23755ee623d87e624a16d0f'

# Todas as entradas de codigo_atual exceto este validador. O validador tem
# cadeia propria porque conter o hash dos seus proprios bytes seria circular.
SHA256_CODIGO_ATUAL_SEM_VALIDACAO = '5011f8c4ad5c371a20bf5ce9898b31e5a8f2e23abde20be7eb7f609360553d9e'
CSVS_RECONSTRUIDOS_PROMOVIDOS = {
    'outputs/tables/distribuicao_peso_250g.csv': '0e36635c74dc5a1b044b9dc594d57c2a3b93c5b35e4b83c62e7e5de05aaf19af',
    'outputs/tables/histograma_propensity.csv': '5032b1050978973f874b6ca92881ca296307c0504e4338eb528844a63be1c418',
}

# Prefixo já fechado de cada cadeia de evoluções (estados anteriores, em ordem).
# O estado final fica no JSON, pois um arquivo não pode conter o próprio hash.
EVOLUCOES_ANCORADAS = {
    'src/validacao.py': (
        'c00d1d79dd9d20f225e40c9c8ba27e18ee204b2644ccf3f30c9cdcf28afacd78',
        '370a8b8e71d367c9bdd0e3d82d22824496a050277665ab2994024536aeb4c183',
        'a9191a94298aa90a35c837a3d213bbfb22b5ef07f695652ed3e3a0d86648ebce',
        'd732740d4955117fb72bfc636090cae556aad58cd91e15ea52825c4878237a51',
    ),
}


def _hash_canonico(obj):
    texto = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(texto.encode('utf-8')).hexdigest()


def _validar_evolucoes_documentadas(manifesto):
    evolucoes = manifesto.get('evolucoes_autorizadas') or {}
    if set(evolucoes) != set(EVOLUCOES_ANCORADAS):
        raise ValueError('Evolucao sem âncora independente no codigo.')
    destinos = {destino for r in manifesto['migracoes'].values() for destino in r['destinos']}
    if not set(evolucoes) <= destinos:
        raise ValueError('Evolucao sem destino no historico de migracao.')


def _validar_codigo_atual_ancorado(manifesto):
    codigo = manifesto['codigo_atual']
    if 'src/validacao.py' not in codigo:
        raise ValueError('codigo_atual sem entrada para o validador.')
    sem_validacao = {nome: h for nome, h in codigo.items() if nome != 'src/validacao.py'}
    if _hash_canonico(sem_validacao) != SHA256_CODIGO_ATUAL_SEM_VALIDACAO:
        raise ValueError('codigo_atual diverge da ancora independente.')


def _validar_baseline_ancorado(raiz, manifesto):
    if (manifesto['baseline_sha256'] != SHA256_BASELINE_PRE_REFATORACAO or
            sha256(raiz/'docs/architecture/BASELINE_PRE_REFATORACAO.md') != SHA256_BASELINE_PRE_REFATORACAO):
        raise ValueError('Baseline imutavel alterado.')


def _validar_csvs_promovidos(raiz, manifesto):
    registros = manifesto.get('artefatos_reconstruidos_promovidos') or {}
    if set(registros) != set(CSVS_RECONSTRUIDOS_PROMOVIDOS):
        raise ValueError('CSV promovido ausente ou inesperado no contrato.')
    for nome, esperado in CSVS_RECONSTRUIDOS_PROMOVIDOS.items():
        registro = registros[nome]
        if (registro.get('sha256') != esperado or
                registro.get('status') != 'RECONSTRUCAO_VALIDADA_PROMOVIDA' or
                not (raiz/nome).is_file() or sha256(raiz/nome) != esperado):
            raise ValueError('CSV promovido alterado: '+nome)


def cadeia_evolucao_valida(evolucoes, destino, historico, atual):
    """Cadeia íntegra: começa no hash histórico, cada passo parte do anterior,
    termina nos bytes atuais, sem ciclos, e respeita o prefixo ancorado."""
    hashes = [historico]
    for passo in evolucoes.get(destino) or []:
        if passo.get('hash_anterior') != hashes[-1]:
            return False
        hashes.append(passo.get('hash_novo'))
    ancora = EVOLUCOES_ANCORADAS.get(destino)
    return bool(ancora and len(hashes) == len(ancora) + 1 and hashes[-1] == atual
                and len(set(hashes)) == len(hashes)
                and tuple(hashes[:len(ancora)]) == ancora)


def _excecao_refatoracao(raiz, nome, original):
    """Exceção fechada: hash anterior conhecido E todos os destinos preservados
    (ou evoluídos por cadeia autorizada a partir do destino histórico)."""
    manifesto = _manifesto_refatoracao(raiz)
    if not manifesto:
        return False
    if _hash_canonico(manifesto['migracoes']) != SHA256_MIGRACOES_HISTORICAS:
        raise ValueError('Histórico de migrações alterado.')
    _validar_evolucoes_documentadas(manifesto)
    registro = manifesto['migracoes'].get(nome)
    if not registro or original not in registro['hashes_anteriores']:
        return False
    evolucoes = manifesto.get('evolucoes_autorizadas') or {}
    for destino, esperado in registro['destinos'].items():
        p = raiz/destino
        if not p.is_file():
            raise ValueError('Destino da migração ausente: '+destino)
        atual = hash_fontes_notebook(p) if p.suffix == '.ipynb' else sha256(p)
        if atual != esperado and not cadeia_evolucao_valida(evolucoes, destino, esperado, atual):
            raise ValueError('Destino da migração alterado: '+destino)
    if registro.get('removido') and (raiz/nome).exists():
        raise ValueError('Módulo histórico reapareceu: '+nome)
    return True


# Âncora da única exceção histórica. A autoridade está aqui e no objeto Git
# imutável do commit fixo, não no JSON de preservação (que só documenta e
# precisa concordar). Os bytes do baseline 6e63e6ab... NÃO foram recuperados.
# Objetivo: detectar mudanças acidentais ou não reconciliadas; não resiste a
# quem reescreve simultaneamente este código, os testes e os contratos.
EXCECAO_SOURCE_MANIFEST = {
    'arquivo': 'data/raw/source_manifest.json',
    'hash_baseline_nao_reproduzido': '6e63e6ab0022edc5860672dc9d52a07123e6a3680ad080fd996ce5431f9674ea',
    'hash_atual_aprovado': 'c1fdc4277225e1a604c1277d0267100dd9d12957e4f2b71ac25461eb9f470eca',
    'commit_git': 'caf14463e85021db4128fd0bf197b6c0e5e74c3c',
    'blob_git': 'f443b468d4997501a103f3671c3913dd48e3765d',
    'hash_git_acessivel': 'c1ee5347021950cb66c82aac4e674de0325557061edf82d7af8b52b887cfc67b',
}


def _ler_referencia_git(raiz, commit, caminho):
    """Leitura somente-leitura do blob versionado, sem filtros de EOL.
    Retorna None se o Git ou o objeto não estiverem disponíveis (falha fechada)."""
    import subprocess
    git = ['git', '-C', str(raiz)]
    try:
        ancestral = subprocess.run(git + ['merge-base', '--is-ancestor', commit, 'HEAD'],
                                   capture_output=True).returncode == 0
        oid = subprocess.run(git + ['rev-parse', '--verify', f'{commit}:./{caminho}'],
                             capture_output=True, text=True, check=True).stdout.strip()
        dados = subprocess.run(git + ['cat-file', 'blob', oid], capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return {'ancestral': ancestral, 'oid': oid, 'dados': dados}


def _excecao_historica(raiz, nome, esperado):
    """Aceita a divergência do hash de baseline apenas para o arquivo fixo, se
    o baseline, os bytes atuais e o blob Git do commit fixo baterem com a
    âncora em código, e o registro documental no JSON concordar com ela."""
    a = EXCECAO_SOURCE_MANIFEST
    if nome != a['arquivo'] or esperado != a['hash_baseline_nao_reproduzido']:
        return False
    manifesto = _manifesto_refatoracao(raiz) or {}
    registro = (manifesto.get('excecoes_historicas') or {}).get(nome)
    if not registro or any(registro.get(k) != v for k, v in a.items() if k != 'arquivo'):
        return False
    caminho = raiz / nome
    if not caminho.is_file():
        return False
    dados = caminho.read_bytes()
    normalizado = hashlib.sha256(dados.replace(b'\r\n', b'\n')).hexdigest()
    if hashlib.sha256(dados).hexdigest() != a['hash_atual_aprovado'] or normalizado != a['hash_git_acessivel']:
        return False
    ref = _ler_referencia_git(raiz, a['commit_git'], nome)
    return bool(ref and ref['ancestral'] and ref['oid'] == a['blob_git']
                and hashlib.sha256(ref['dados']).hexdigest() == a['hash_git_acessivel'] == normalizado)


def verificar_codigo(raiz, codigo):
    for nome, esperado in codigo.items():
        caminho = 'src/'+nome
        p = raiz/caminho
        if p.is_file() and sha256(p) == esperado:
            continue
        if not _excecao_refatoracao(raiz, caminho, esperado):
            raise ValueError('Código do ajuste alterado após execução: '+nome)


def conferir_contrato(raiz, salvo, atual):
    """Permite só a migração documentada do código, nunca dados ou parâmetros."""
    if {k: v for k, v in salvo.items() if k != 'codigo'} != {
        k: v for k, v in atual.items() if k != 'codigo'
    }:
        raise ValueError('Cache não corresponde ao contrato; preservar e investigar.')
    verificar_codigo(raiz, salvo['codigo'])
    verificar_codigo(raiz, atual['codigo'])

class NumerosTabela(HTMLParser):
    def __init__(self):
        super().__init__(); self.dentro=False; self.numeros=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('td','th'): self.dentro=True
    def handle_endtag(self,tag):
        if tag in ('td','th'): self.dentro=False
    def handle_data(self,data):
        if self.dentro and re.fullmatch(r'[-+]?\d[\d,.eE+%-]*',data.strip()):
            self.numeros.append(data.strip())

def numeros_notebook(p):
    nb=json.loads(p.read_text(encoding='utf-8')); numeros=[]
    for c in nb['cells']:
        for o in c.get('outputs',[]):
            html=o.get('data',{}).get('text/html')
            if html:
                parser=NumerosTabela(); parser.feed(''.join(html)); numeros.append(parser.numeros)
    return numeros

def verificar_preservacao(raiz, atual, original):
    """Valida hashes originais e exceções explícitas, sem reescrever manifestos."""
    if set(atual) != set(original):
        raise ValueError('Inventário histórico alterado.')
    p = raiz/'outputs/diagnostics/apresentacao_preservacao.json'
    registro = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'excecoes': {}}
    for nome, h in original.items():
        if atual[nome] == h:
            continue
        r = registro['excecoes'].get(nome)
        valido = nome in AUTORIZADOS and r and r['antes'] == h and r['depois'] == atual[nome]
        if nome.endswith('.ipynb') and r and r.get('fontes_sha256'):
            valido = (nome in AUTORIZADOS and r['antes'] == h and
                      hash_fontes_notebook(raiz/nome) == r['fontes_sha256'])
        if not valido and not _excecao_refatoracao(raiz, nome, h):
            raise ValueError(f'Alteração não autorizada ou não reconciliada: {nome}')

def validar_apresentacao():
    base=json.loads((ROOT/'outputs/diagnostics/apresentacao_base.json').read_text(encoding='utf-8'))
    for nome,numeros in base['notebooks'].items():
        novo=numeros_notebook(ROOT/'notebooks'/nome)
        assert novo==numeros, f'Números exibidos mudaram: {nome}'
    for nome,h in base['diagnosticos'].items():
        assert hash_arquivo(ROOT/'outputs/diagnostics'/nome)==h,f'Diagnóstico histórico modificado: {nome}'
    print('Quatro notebooks: números das tabelas e diagnósticos históricos preservados.')


def validar_fase2(raiz, persistir=True):
    pasta = raiz/'outputs/diagnostics'
    resultado = json.loads((pasta/'fase2_aipw.json').read_text(encoding='utf-8'))
    parquet = raiz/'data/processed/sinasc_2024.parquet'
    assert hashlib.sha256(parquet.read_bytes()).hexdigest() == resultado['provenance']['parquet_sha256']
    with duckdb.connect() as c:
        _criar_views(c, raiz/'data/processed/sinasc_2024.parquet')
        datas = c.execute("""
            WITH d AS (SELECT try_strptime(DTNASC, '%d%m%Y') AS data FROM sinasc)
            SELECT count(*) FILTER (WHERE data IS NULL) AS datas_invalidas,
                   count(*) FILTER (WHERE year(data) <> 2024) AS fora_2024,
                   CAST(min(data) AS VARCHAR) AS minima,
                   CAST(max(data) AS VARCHAR) AS maxima FROM d
        """).df().to_dict('records')[0]
        dados = c.execute('SELECT tratamento, Y_BAIXO_PESO FROM amostra_principal ORDER BY contador').df()
    assert datas['datas_invalidas'] == 0 and datas['fora_2024'] == 0, datas
    cache = np.load(raiz/'outputs/tables/fase2_predicoes_oof.npz')
    assert all(len(cache[k]) == len(dados) for k in cache.files)
    assert np.all(cache['cobertura'] == 1)
    assert set(np.unique(cache['fold_id'])) == {1, 2, 3}
    t, y = dados.tratamento.to_numpy(), dados.Y_BAIXO_PESO.to_numpy()
    linhas, _ = resumir_especificacoes(y, t, cache)
    for atual, salvo in zip(linhas, resultado['resultados']):
        assert atual['n'] == salvo['n'] == atual['n_t0'] + atual['n_t1']
        for campo in ('estimativa', 'se', 'ic95_inferior', 'ic95_superior'):
            assert np.isclose(atual[campo], salvo[campo], rtol=0, atol=1e-12)
    # A concentração de IF² é de grupo; máximo individual ajuda a contextualizá-la.
    r = {'status': 'APROVADO', 'n': len(dados), 'datas': datas,
         'cobertura_oof': 'exatamente uma previsão por observação',
         'resultados_reconciliados': len(linhas), 'tolerancia_absoluta': 1e-12,
         'n_nan_predicoes': sum(int(np.isnan(cache[k]).sum()) for k in cache.files)}
    assert r['n_nan_predicoes'] == 0
    if persistir:
        _salvar_json(pasta/'fase2_validacao.json', r)
    print(json.dumps(r, ensure_ascii=False, indent=2))

    return r


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

def validar_fase3(raiz=None):
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
            verificar_codigo(raiz, log['contrato']['codigo'])
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


def validar_fase4():
    ler=lambda nome:json.loads((ROOT/'outputs/diagnostics'/nome).read_text(encoding='utf-8'))
    verificar_preservacao(ROOT, patrimonio(), ler('fase4_preservacao.json')['sha256'])
    log=ler('fase4_ajustes.json'); r=ler('fase4_resultados.json')
    dados,auditoria=carregar_amostra(ROOT/'data/processed/sinasc_2024.parquet')
    assert sha256(ROOT/'data/processed/sinasc_2024.parquet')==log['contrato']['dados_sha256']
    assert auditoria['sha256_ordem_contador']==log['contrato']['chaves_sha256']
    verificar_codigo(ROOT, log['contrato']['codigo'])
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


def verificar_metricas(texto, esperadas):
    encontradas = re.findall(r'<span data-metrica="([^"]+)">([^<]+)</span>', texto)
    for chave, valor in encontradas:
        if chave not in esperadas or html.unescape(valor) != esperadas[chave]:
            raise ValueError(f'Métrica divergente: {chave} = {valor}')
    ausentes = set(esperadas) - {c for c, _ in encontradas}
    if ausentes:
        raise ValueError(f'Métrica ausente: {sorted(ausentes)}')

def links_quebrados(arquivo):
    texto = arquivo.read_text(encoding='utf-8')
    if arquivo.suffix == '.md':
        linhas, cerca = [], None
        for linha in texto.splitlines():
            marcador = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', linha)
            if cerca is None:
                if marcador:
                    cerca = marcador.group(1)
                else:
                    linhas.append(linha)
            elif (marcador and marcador.group(1)[0] == cerca[0]
                  and len(marcador.group(1)) >= len(cerca)
                  and not marcador.group(2).strip()):
                cerca = None
        texto = '\n'.join(linhas)
    destinos = re.findall(r'\]\(([^)]+)\)', texto)
    destinos += re.findall(r'(?:href|src)="([^"]+)"', texto) if arquivo.suffix == '.html' else []
    erros = []
    for destino in destinos:
        u = urlsplit(destino.strip('<>'))
        if u.scheme:
            continue
        alvo = arquivo.parent / unquote(u.path) if u.path else arquivo
        if not alvo.exists():
            erros.append(destino)
        elif u.fragment and alvo.suffix in {'.md', '.html'}:
            conteudo = alvo.read_text(encoding='utf-8')
            ids = set(re.findall(r'id="([^"]+)"', conteudo))
            for titulo in re.findall(r'^#+\s+(.+)$', conteudo, re.M):
                slug = re.sub(r'[^\w -]', '', titulo.lower()).replace(' ', '-')
                ids.add(slug)
                ids.add(''.join(c for c in unicodedata.normalize('NFD', slug) if not unicodedata.combining(c)))
            if unquote(u.fragment) not in ids:
                erros.append(destino)
    return sorted(set(erros))

def validar_dicionario(linhas, colunas):
    nomes = [r['nome'] for r in linhas]
    if nomes != colunas or len(nomes) != len(set(nomes)):
        raise ValueError('Cobertura, ordem ou unicidade do dicionário inválida')

def validar_entrega():
    from src.entrega import metricas
    from src.entrega import linhas_robustez
    from src.entrega import numero
    from src.entrega import ler
    from src.entrega import figuras
    from src.entrega import gravar
    valores,_=metricas(); essenciais=['bruto','colunas','n','n_t1','n_t0','prevalencia','ufs','C1_estimativa_pp','C2_estimativa_pp','cate_media_pp','gate4']
    for nome in ['README.md','docs/SINTESE_EXECUTIVA.md','docs/RESULTADOS_PRINCIPAIS.md','apresentacao/relatorio_interativo_sinasc_2024.html']:
        texto=(ROOT/nome).read_text(encoding='utf-8')
        verificar_metricas(texto,valores if 'RESULTADOS' in nome or nome.endswith('.html') else {k:valores[k] for k in essenciais})
        if '\ufffd' in texto or 'Ã§' in texto or 'Ã£' in texto: raise ValueError('Codificação inválida: '+nome)
    erros={}
    for p in [ROOT/'README.md', *ROOT.joinpath('docs').rglob('*.md')]:
        problemas=links_quebrados(p)
        if problemas: erros[str(p.relative_to(ROOT))]=problemas
    if erros: raise ValueError(f'Links locais quebrados: {erros}')
    notebooks=[]
    for p in sorted(ROOT.joinpath('notebooks').glob('0[1-5]*.ipynb')):
        n=json.loads(p.read_text(encoding='utf-8')); cells=[c for c in n['cells'] if c['cell_type']=='code']
        assert all(c.get('execution_count') is not None for c in cells)
        assert not any(o.get('output_type')=='error' for c in cells for o in c.get('outputs',[]))
        notebooks.append(dict(nome=p.name,celulas_executadas=len(cells)))
    d=json.loads((ROOT/'outputs/tables/dicionario_analitico_sinasc_2024.json').read_text(encoding='utf-8'))
    validar_dicionario(d,[s['coluna'] for s in ler('auditoria_schema_sinasc_2024.json')])
    pagina=ROOT/'apresentacao/relatorio_interativo_sinasc_2024.html'; texto=pagina.read_text(encoding='utf-8')
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)="https?://',texto)
    assert texto.count('<section id=')==14 and texto.count('<figure>')==10
    assert pagina.stat().st_size<15_000_000
    assert not re.search(r'"(?:contador|m0_C1|m1_C1|fold_id)"\s*:\s*\[',texto)
    resultado_md=(ROOT/'docs/RESULTADOS_PRINCIPAIS.md').read_text(encoding='utf-8')
    for row in linhas_robustez():
        assert '| '+' | '.join(row)+' |' in resultado_md, 'Tabela de robustez divergente'
        assert '<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' in texto, 'Robustez HTML divergente'
    for x in d:
        pct=lambda v:'Não confirmado' if v is None else numero(v)
        row=[x['nome'],x['descricao'],x['tipo'],x['dominio'],pct(x['missing_pct']),pct(x['ignorado_pct']),pct(x['missing_ignorado_pct']),x['exemplos'],x['papel'],x['fases'],x['observacao']]
        assert '<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' in texto, 'Dicionário HTML divergente: '+x['nome']
    # Reconciliar séries e layouts incorporados com as figuras dos agregados atuais.
    decoder=json.JSONDecoder()
    for f in figuras():
        padrao=r'Plotly\.newPlot\(\s*"fig-'+re.escape(f['id'])+r'",\s*'
        inicio=re.search(padrao,texto)
        assert inicio, f['id']
        trecho=texto[inicio.end():]
        dados,fim=decoder.raw_decode(trecho)
        layout,_=decoder.raw_decode(trecho[fim:].lstrip(' ,\n\r\t'))
        esperado=json.loads(f['fig'].to_json())
        assert dados==esperado['data'] and layout==esperado['layout'], 'Gráfico divergente: '+f['id']
    resultado=dict(status='APROVADO_COM_RESSALVA_VISUAL',colunas=len(d),notebooks=notebooks,links_internos='APROVADO',metricas='APROVADO',series_graficos='APROVADO',dicionario_html='APROVADO',html_bytes=pagina.stat().st_size,html_sha256=hashlib.sha256(pagina.read_bytes()).hexdigest(),modelagem_nova=False,inspecao_html='Bloqueada pela política de URL local do navegador; abertura e controles exigem conferência manual.')
    gravar('outputs/diagnostics/fase5_validacao.json',json.dumps(resultado,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(resultado,ensure_ascii=False,indent=2))

def historico(raiz):
    """Inventário histórico completo, inclusive fontes movidas (valor None)."""
    original = json.loads((raiz/'outputs/diagnostics/fase3_preservacao.json').read_text(encoding='utf-8'))['historico_sha256']
    return {nome: sha256_preservacao(raiz, nome) if (raiz/nome).is_file() else None for nome in original}

def patrimonio():
    original = json.loads((ROOT/'outputs/diagnostics/fase4_preservacao.json').read_text(encoding='utf-8'))['sha256']
    return {nome: sha256_preservacao(ROOT, nome) if (ROOT/nome).is_file() else None for nome in original}

def validar_fase2_sem_escrita(raiz):
    r = validar_fase2(raiz, persistir=False)
    salvo = json.loads((raiz/'outputs/diagnostics/fase2_validacao.json').read_text(encoding='utf-8'))
    if r != salvo:
        raise ValueError('Validação histórica não reproduziu o JSON salvo.')
    return r


def validar_notebooks(raiz=ROOT):
    import nbformat
    from src.visualizacao import auditar_idioma
    arquivos = sorted((raiz/'notebooks').glob('0[1-5]*.ipynb'))
    if len(arquivos) != 5:
        raise ValueError('São necessários os cinco notebooks fonte.')
    base = _baseline(raiz)
    manifesto = _manifesto_refatoracao(raiz)
    for p in arquivos:
        nb = nbformat.read(p, as_version=4)
        nbformat.validate(nb)
        codigo = [c for c in nb.cells if c.cell_type == 'code']
        esperado = base['notebooks'][p.relative_to(raiz).as_posix()]
        if len(codigo) != esperado['celulas_codigo']:
            raise ValueError('Quantidade de células mudou: '+p.name)
        if any(c.execution_count is None for c in codigo):
            raise ValueError('Notebook não executado: '+p.name)
        if any(o.output_type == 'error' for c in codigo for o in c.outputs):
            raise ValueError('Notebook contém erro: '+p.name)
        if auditar_idioma(nb):
            raise ValueError('Narrativa fora de PT-BR: '+p.name)
        if numeros_notebook(p) != esperado['numeros']:
            raise ValueError('Números exibidos mudaram: '+p.name)
        if manifesto:
            fontes = manifesto['notebooks'][p.relative_to(raiz).as_posix()]
            if hash_fontes_notebook(p) != fontes:
                raise ValueError('Fonte analítica alterada: '+p.name)
        for c in codigo:
            compile(c.source, str(p), 'exec')
    return {'notebooks': 5, 'erros': 0, 'numeros_preservados': True}


def validar_imports():
    import ast
    import importlib
    for p in (ROOT/'src').glob('*.py'):
        importlib.import_module('src.'+p.stem)
    fontes = [(str(p), p.read_text(encoding='utf-8')) for pasta in ('src', 'scripts', 'tests')
              for p in (ROOT/pasta).glob('*.py')]
    for p in (ROOT/'notebooks').glob('*.ipynb'):
        nb = json.loads(p.read_text(encoding='utf-8'))
        fontes += [(str(p), ''.join(c['source'])) for c in nb['cells'] if c['cell_type'] == 'code']
    for nome, texto in fontes:
        for n in ast.walk(ast.parse(texto, filename=nome)):
            if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith(('src.', 'scripts.')):
                modulo = importlib.import_module(n.module)
                for alias in n.names:
                    if alias.name != '*' and not hasattr(modulo, alias.name):
                        raise ImportError(f'{nome}: {n.module}.{alias.name}')
            elif isinstance(n, ast.Import):
                for alias in n.names:
                    if alias.name.startswith(('src.', 'scripts.')):
                        importlib.import_module(alias.name)


def validar_gates():
    from src.inferencia_causal import classificar_gate
    from src.entrega import ler, metricas
    base = _baseline(ROOT)
    if metricas()[0] != base['metricas']:
        raise ValueError('Métricas centrais ou gates mudaram.')
    causal = ler('fase2_aipw.json')
    if classificar_gate(causal['resultados'], causal['diagnosticos']) != causal['gate']:
        raise ValueError('Gate AIPW divergente.')
    r = ler('fase4_resultados.json')
    if classificar(r['estabilidade']) != r['gate'] or r['gate'] != ler('fase4_gate.json')['gate']:
        raise ValueError('Gate de heterogeneidade divergente.')
    if ler('fase3_gate.json')['historico_fase2'] != causal['gate']:
        raise ValueError('Gate histórico inconsistente.')


def validar_preservacao_refatoracao(completa=False):
    base = _baseline(ROOT)
    manifesto = _manifesto_refatoracao(ROOT)
    if not manifesto:
        raise ValueError('Manifesto da refatoração ausente.')
    _validar_baseline_ancorado(ROOT, manifesto)
    _validar_codigo_atual_ancorado(manifesto)
    _validar_evolucoes_documentadas(manifesto)
    _validar_csvs_promovidos(ROOT, manifesto)
    for nome, esperado in manifesto['codigo_atual'].items():
        if not (ROOT/nome).is_file() or sha256(ROOT/nome) != esperado:
            raise ValueError('Código posterior à refatoração alterado: '+nome)
    for nome, esperado in base['hashes'].items():
        # A rápida confere agregados; a completa lê também os dados e caches grandes.
        if not completa and (nome.startswith('data/') or nome.endswith('.npz')):
            continue
        if sha256_preservacao(ROOT, nome) != esperado and not _excecao_historica(ROOT, nome, esperado):
            raise ValueError('Artefato científico alterado: '+nome)
    for nome, registro in manifesto['migracoes'].items():
        if not _excecao_refatoracao(ROOT, nome, registro['hashes_anteriores'][0]):
            raise ValueError('Migração não reconciliada: '+nome)
    return {'artefatos_preservados': len(base['hashes'])}


def executar_notebooks():
    """Executa diretamente as fontes no kernel da .venv, sem geradores."""
    import subprocess
    import sys
    for p in sorted((ROOT/'notebooks').glob('0[1-5]*.ipynb')):
        subprocess.run([sys.executable, '-m', 'nbconvert', '--execute', '--to', 'notebook',
                        '--inplace', '--ExecutePreprocessor.kernel_name=python3',
                        '--ExecutePreprocessor.timeout=600', str(p)], cwd=ROOT, check=True)
    validar_notebooks()


def validar_projeto(completa=False):
    validar_imports()
    validar_preservacao_refatoracao(completa=completa)
    validar_gates()
    validar_notebooks()
    validar_apresentacao()
    validar_entrega()
    if completa:
        import subprocess
        import sys
        validar_fase3(ROOT)  # Inclui a reconciliação da Fase 2 sem escrita.
        validar_fase4()
        subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests'], cwd=ROOT, check=True)
        executar_notebooks()
        validar_preservacao_refatoracao(completa=True)
    print('Validação '+('completa' if completa else 'rápida')+' aprovada.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--completa', action='store_true')
    parser.add_argument('--notebooks', action='store_true', help='Executar diretamente os cinco notebooks')
    args = parser.parse_args()
    if args.notebooks:
        executar_notebooks()
    else:
        validar_projeto(completa=args.completa)
