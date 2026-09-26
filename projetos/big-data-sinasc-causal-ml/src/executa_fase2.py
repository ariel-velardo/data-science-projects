"""Executa os dois exercícios congelados sobre a população integral."""
import hashlib
import json
import platform
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import roc_auc_score

from src.executa_fase1 import _criar_views, _salvar_json, _markdown_tabela
from src.audita_covariaveis import COLUNAS_PROPENSITY_PRINCIPAL
from src.modelagem_preditiva import benchmark, avaliar_probabilidades, SEED
from src.estima_aipw import cross_fitting, resumir_especificacoes
from src.diagnostica_overlap import resumir_overlap


def classificar_gate(linhas, diagnosticos):
    if any(d['frac_variancia_top1pct'] > .5 for d in diagnosticos.values()):
        return 'RESULTADO_NAO_INTERPRETAVEL'
    principal = {r['especificacao']: r['estimativa_pp'] for r in linhas if r['populacao'] == 'sem_trimming'}
    if principal['C1']*principal['C2'] < 0 or abs(principal['C1']-principal['C2']) > .25:
        return 'RESULTADO_SENSIVEL_A_ESPECIFICACAO'
    if any(abs(r['estimativa_pp']-principal[r['especificacao']]) > .5 for r in linhas):
        return 'RESULTADO_SENSIVEL_A_ESPECIFICACAO'
    return 'RESULTADO_EXPLORATORIO_ESTAVEL'


def executar(raiz):
    inicio = time.time()
    pasta = raiz / 'outputs/diagnostics'
    parquet = raiz / 'data/processed/sinasc_2024.parquet'
    fase1 = json.loads((pasta/'fase1_amostra.json').read_text(encoding='utf-8'))
    overlap1 = json.loads((pasta/'fase1_overlap.json').read_text(encoding='utf-8'))
    if overlap1['status'] != 'CONCLUIDO':
        raise ValueError('Fase 1 sem overlap concluído.')
    with duckdb.connect() as c:
        _criar_views(c, parquet)
        # ORDER BY garante identidade dos índices OOF entre execuções.
        dados = c.execute('SELECT * FROM amostra_principal ORDER BY contador').df()
        datas = c.execute("""
            WITH d AS (SELECT try_strptime(DTNASC, '%d%m%Y') AS data FROM sinasc)
            SELECT CAST(min(data) AS VARCHAR) AS minimo, CAST(max(data) AS VARCHAR) AS maximo,
                   count(*) FILTER (WHERE data IS NULL) AS n_missing,
                   count(*) FILTER (WHERE year(data) <> 2024) AS n_fora_2024 FROM d
        """).df().to_dict('records')[0]
        if datas['n_missing'] or datas['n_fora_2024']:
            raise ValueError('Datas inválidas ou fora do ano congelado.')
    if len(dados) != fase1['fluxo_amostra'][-1]['n_restante']:
        raise ValueError('N divergiu do contrato Fase 1.')
    if dados.contador.isna().any() or dados.contador.duplicated().any():
        raise ValueError('Chave inválida.')
    x = dados.loc[:, list(COLUNAS_PROPENSITY_PRINCIPAL)]
    t = dados.tratamento.to_numpy(dtype=int)
    y = dados.Y_BAIXO_PESO.to_numpy(dtype=int)
    provenance = {'python': platform.python_version(), 'sklearn': sklearn.__version__,
                  'seed': SEED, 'n': len(dados), 'chave': 'contador', 'ordem': 'contador',
                  'parquet_sha256': hashlib.sha256(parquet.read_bytes()).hexdigest(),
                  'datas_nascimento': datas,
                  'x': list(x.columns), 't': 'MESPRENAT 1-3 versus 4-9', 'y': 'PESO <2500',
                  'populacao': 'SINASC 2024, gravidez única, peso 500-6000g, mês válido'}
    bruto = {'rotulo': 'ASSOCIAÇÃO BRUTA — NÃO CAUSAL',
             'risco_t1': float(y[t==1].mean()), 'risco_t0': float(y[t==0].mean()),
             'diferenca_pp': float(100*(y[t==1].mean()-y[t==0].mean()))}
    preditivo = benchmark(x, y)
    preditivo['provenance'] = provenance
    _salvar_json(pasta/'fase2_modelagem_preditiva.json', preditivo)
    pred = cross_fitting(x, t, y, n_folds=3)
    # Arquivo grande apenas local, sob política de ignore existente.
    np.savez_compressed(raiz/'outputs/tables/fase2_predicoes_oof.npz',
                        **{k:v for k,v in pred.items() if isinstance(v, np.ndarray)})
    linhas, diagnosticos = resumir_especificacoes(y, t, pred)
    nuisance = {}
    for spec in ('C1', 'C2'):
        nuisance[spec] = {f'm{g}_grupo_observado': avaliar_probabilidades(y[t==g], pred[f'm{g}_{spec}'][t==g]) for g in (0, 1)}
    gate = classificar_gate(linhas, diagnosticos)
    resultado = {'provenance': provenance, 'associacao_bruta': bruto,
                 'efeito_causal_estimado': True, 'causalidade_provada': False,
                 'n_folds': 3, 'folds': pred['folds'], 'nuisance_oof': nuisance,
                 'auc_propensity_oof': float(roc_auc_score(t, pred['e'])),
                 'overlap': resumir_overlap(pred['e'], t),
                 'resultados': linhas, 'diagnosticos': diagnosticos, 'gate': gate,
                 'segundos_execucao': time.time()-inicio,
                 'negative_control': 'não identificado placebo/negative control adequado',
                 'incerteza': 'IF iid; IC aproximado condicional ao suporte aprendido; não inclui confundimento ou seleção',
                 'heterogeneidade': 'omitida para manter escopo parcimonioso'}
    _salvar_json(pasta/'fase2_aipw.json', resultado)
    _salvar_json(pasta/'fase2_sensibilidades.json', {'resultados': linhas, 'gate': gate,
        'mesmo_propensity_C1_C2': True, 'clipping': False,
        'nota': 'Trimming define populações diferentes; N pode variar frente à Fase 1 de 5 folds.'})
    tabela = pd.DataFrame(linhas)[['especificacao', 'populacao', 'n', 'n_t1', 'n_t0', 'estimativa_pp', 'se_pp', 'ic95_inferior_pp', 'ic95_superior_pp']]
    (pasta/'RESULTADOS_FASE2.md').write_text(
        '# Resultados exploratórios da Fase 2\n\n'+_markdown_tabela(tabela)+
        '\nUnidade: pontos percentuais. Hipóteses observacionais não provadas.\n\nGate: '+gate+'\n', encoding='utf-8')
    print(tabela.to_string(index=False), flush=True)
    print('Gate:', gate, flush=True)
    return resultado


if __name__ == '__main__':
    executar(Path(__file__).resolve().parents[1])
