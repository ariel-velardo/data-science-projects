"""Reconcilia artefatos persistidos com dados e predições, sem reajustar modelos."""
import json
import hashlib
from pathlib import Path
import duckdb
import numpy as np
from src.executa_fase1 import _criar_views, _salvar_json
from src.estima_aipw import resumir_especificacoes


def validar(raiz):
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
    _salvar_json(pasta/'fase2_validacao.json', r)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    validar(Path(__file__).resolve().parents[1])
