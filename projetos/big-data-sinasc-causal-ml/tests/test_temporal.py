"""Extensão temporal: ano como parâmetro sem tocar no baseline certificado de 2024."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from src import temporal as tp

RAIZ_REAL = Path(__file__).resolve().parents[1]

CABECALHO_2024 = ['contador', 'ORIGEM', 'IDADEMAE', 'ESTCIVMAE', 'QTDFILMORT', 'CODMUNRES',
                  'GRAVIDEZ', 'DTNASC', 'PESO', 'RACACORMAE', 'ESCMAE2010', 'MESPRENAT',
                  'CONSPRENAT', 'PARIDADE']


def _csv(colunas, linhas, sep=';'):
    return (sep.join(colunas) + '\n' + ''.join(sep.join(l) + '\n' for l in linhas)).encode('utf-8')


def _zip(caminho, nome_csv, conteudo):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(caminho, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(nome_csv, conteudo)
    return caminho


def _linha(contador='1', ano='2023'):
    return [contador, '1', '29', '1', '00', '355030', '1', f'0101{ano}', '3100', '1', '4', '02', '07', '1']


# --- validação do ano e resolução de caminhos ---

def test_validar_ano_aceita_somente_inteiro_publicado():
    assert tp.validar_ano(2024) == 2024
    assert tp.validar_ano(1996) == 1996
    for invalido in (True, '2024', 2024.0, None):
        with pytest.raises(TypeError):
            tp.validar_ano(invalido)
    for fora in (1995, 3000):
        with pytest.raises(ValueError):
            tp.validar_ano(fora, ano_maximo=2026)


def test_ano_2024_resolve_exatamente_os_caminhos_legados(tmp_path):
    c = tp.caminhos_ano(tmp_path, 2024)
    assert c.baseline and c.manifesto is None
    assert c.zip_bruto == tmp_path / 'data/raw/SINASC_2024_csv.zip'
    assert c.parquet == tmp_path / 'data/processed/sinasc_2024.parquet'
    assert not any(tmp_path.iterdir()), 'Resolver caminhos não pode criar arquivos.'


def test_url_2024_coincide_com_fonte_oficial_certificada():
    from src.sinasc import FONTES_OFICIAIS
    assert tp.url_sinasc(2024) == FONTES_OFICIAIS[0]['url']
    assert tp.caminhos_ano(RAIZ_REAL, 2024).zip_bruto.name == FONTES_OFICIAIS[0]['arquivo']


def test_anos_diferentes_nunca_compartilham_arquivos(tmp_path):
    todos = [tp.caminhos_ano(tmp_path, ano) for ano in range(2010, 2027)]
    arquivos = [p for c in todos for p in (c.zip_bruto, c.parquet, c.manifesto) if p is not None]
    assert len(arquivos) == len(set(arquivos))
    legado = tp.caminhos_ano(tmp_path, 2024)
    for c in todos:
        if c.ano != 2024:
            assert not c.baseline
            assert str(c.ano) in c.zip_bruto.as_posix() and str(c.ano) in c.parquet.name
            assert c.zip_bruto.parent != legado.zip_bruto.parent
            assert c.parquet.parent != legado.parquet.parent


# --- schema entre anos ---

def test_schema_compara_sem_diferenciar_caixa_e_posicao():
    minusculo = [c.lower() for c in CABECALHO_2024[1:]] + ['contador']
    r = tp.comparar_schema(minusculo, CABECALHO_2024)
    assert r['ausentes_vs_referencia'] == [] and r['extras_vs_referencia'] == []
    assert not r['identico'] and 'MESPRENAT' in r['diferenca_de_caixa']
    tp.validar_schema_temporal(minusculo, tp.VARIAVEIS_ESSENCIAIS)


def test_schema_incompativel_e_detectado():
    sem_paridade = [c for c in CABECALHO_2024 if c != 'PARIDADE']
    with pytest.raises(ValueError, match='PARIDADE'):
        tp.validar_schema_temporal(sem_paridade, tp.VARIAVEIS_ESSENCIAIS)
    with pytest.raises(ValueError, match='ambíguas'):
        tp.normalizar_colunas(['PESO', 'peso'])


def test_classificacao_de_anos_segue_criterios_em_ordem():
    base = dict(tratamento_MESPRENAT=True, outcome_PESO=True, essenciais_ausentes=[])
    assert tp.classificar_ano(base) == 'JANELA_PRINCIPAL'
    assert tp.classificar_ano(base, 'preliminar') == 'EXCLUIDO_DADO_NAO_CONSOLIDADO'
    assert tp.classificar_ano({**base, 'essenciais_ausentes': ['PARIDADE']}, 'preliminar') == \
        'SENSIBILIDADE_PENDENTE_COVARIAVEIS_AUSENTES'
    assert tp.classificar_ano({**base, 'tratamento_MESPRENAT': False}) == 'INCOMPATIVEL_SEM_T_OU_Y'


# --- download e cache: 2024 só é verificado; outros anos têm pasta e manifesto próprios ---

def _raiz_com_baseline(tmp_path):
    zip_2024 = _zip(tmp_path / 'data/raw/SINASC_2024_csv.zip', 'SINASC_2024.csv',
                    _csv(CABECALHO_2024, [_linha(ano='2024')]))
    h = hashlib.sha256(zip_2024.read_bytes()).hexdigest()
    manifesto = tmp_path / 'data/raw/source_manifest.json'
    manifesto.write_text(json.dumps({'fontes': [{'arquivo': 'SINASC_2024_csv.zip', 'sha256': h}]}),
                         encoding='utf-8')
    return zip_2024, manifesto


def _instantaneo(raiz):
    return {p.relative_to(raiz).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in raiz.rglob('*') if p.is_file()}


def test_download_2024_apenas_verifica_sem_rede_nem_escrita(tmp_path, monkeypatch):
    _raiz_com_baseline(tmp_path)
    monkeypatch.setattr(tp, 'baixar_arquivo_oficial', lambda *a, **k: pytest.fail('rede usada'))
    antes = _instantaneo(tmp_path)
    r = tp.baixar_sinasc_ano(tmp_path, 2024)
    assert r['baseline'] and r['reutilizado']
    assert _instantaneo(tmp_path) == antes


def test_download_2024_falha_se_zip_certificado_divergir(tmp_path):
    zip_2024, _ = _raiz_com_baseline(tmp_path)
    zip_2024.write_bytes(zip_2024.read_bytes() + b'x')
    with pytest.raises(ValueError, match='SHA-256 divergente'):
        tp.baixar_sinasc_ano(tmp_path, 2024)


def test_download_de_outro_ano_nao_toca_baseline(tmp_path, monkeypatch):
    _raiz_com_baseline(tmp_path)
    antes = _instantaneo(tmp_path)
    destinos = []

    def falso_download(url, destino, sha256_esperado=None):
        destinos.append((url, Path(destino)))
        _zip(Path(destino), 'SINASC_2023.csv', _csv(CABECALHO_2024, [_linha()]))
        return {'arquivo': str(destino), 'bytes': Path(destino).stat().st_size,
                'sha256': hashlib.sha256(Path(destino).read_bytes()).hexdigest(), 'reutilizado': False}

    monkeypatch.setattr(tp, 'baixar_arquivo_oficial', falso_download)
    r = tp.baixar_sinasc_ano(tmp_path, 2023)
    assert destinos == [(tp.url_sinasc(2023), tmp_path / 'data/raw/sinasc/2023/SINASC_2023_csv.zip')]
    assert r['manifesto']['arquivo_local'] == 'data/raw/sinasc/2023/SINASC_2023_csv.zip'
    depois = _instantaneo(tmp_path)
    assert {k: depois[k] for k in antes} == antes, 'Arquivos de 2024 ou source_manifest alterados.'
    assert set(depois) - set(antes) == {'data/raw/sinasc/2023/SINASC_2023_csv.zip',
                                        'outputs/temporal/manifestos/sinasc_2023.json'}


def test_manifesto_de_ano_recusa_zip_diferente_do_registrado(tmp_path, monkeypatch):
    registro = tp.caminhos_ano(tmp_path, 2023).manifesto
    registro.parent.mkdir(parents=True)
    registro.write_text(json.dumps({'sha256': '0' * 64}), encoding='utf-8')
    monkeypatch.setattr(tp, 'baixar_arquivo_oficial', lambda *a, **k: {
        'arquivo': 'x', 'bytes': 1, 'sha256': '1' * 64, 'reutilizado': True})
    with pytest.raises(ValueError, match='diverge do manifesto'):
        tp.baixar_sinasc_ano(tmp_path, 2023)


def test_conversao_de_outro_ano_usa_cache_proprio_e_preserva_2024(tmp_path):
    _raiz_com_baseline(tmp_path)
    parquet_2024 = tmp_path / 'data/processed/sinasc_2024.parquet'
    parquet_2024.parent.mkdir(parents=True)
    parquet_2024.write_bytes(b'parquet certificado')
    # Layout observado em 2016: nomes minúsculos e contador na última coluna.
    colunas = [c.lower() for c in CABECALHO_2024[1:]] + ['contador']
    linhas = [l[1:] + [l[0]] for l in (_linha('1', '2016'), _linha('2', '2016'))]
    _zip(tp.caminhos_ano(tmp_path, 2016).zip_bruto, 'SINASC_2016.csv', _csv(colunas, linhas))
    r = tp.converter_sinasc_ano(tmp_path, 2016)
    assert r.caminho == tmp_path / 'data/processed/sinasc/sinasc_2016.parquet'
    assert r.registros == 2 and not r.reutilizado
    assert pq.ParquetFile(r.caminho).schema_arrow.names == colunas
    assert parquet_2024.read_bytes() == b'parquet certificado'
    assert tp.converter_sinasc_ano(tmp_path, 2016).reutilizado


def test_conversao_rejeita_ano_com_schema_incompativel(tmp_path):
    colunas = [c for c in CABECALHO_2024 if c != 'PARIDADE']
    _zip(tp.caminhos_ano(tmp_path, 2012).zip_bruto, 'SINASC_2012.csv',
         _csv(colunas, [_linha('1', '2012')[:-1]]))
    with pytest.raises(ValueError, match='PARIDADE'):
        tp.converter_sinasc_ano(tmp_path, 2012)
    assert not tp.caminhos_ano(tmp_path, 2012).parquet.exists()


def test_conversao_2024_nunca_reconverte(tmp_path):
    with pytest.raises(FileNotFoundError, match='certificado'):
        tp.converter_sinasc_ano(tmp_path, 2024)


# --- inspeção remota por HTTP Range, sem rede ---

class _Resposta:
    def __init__(self, status, content=b'', headers=None):
        self.status_code, self.content, self.headers = status, content, headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class _SessaoRange:
    """Serve um ZIP em memória respeitando cabeçalhos Range, como o S3 oficial."""

    def __init__(self, dados):
        self.dados, self.bytes_servidos = dados, 0

    def head(self, url, timeout=None):
        return _Resposta(200, headers={'Content-Length': str(len(self.dados))})

    def get(self, url, headers=None, timeout=None):
        inicio, fim = map(int, headers['Range'].removeprefix('bytes=').split('-'))
        trecho = self.dados[inicio:fim + 1]
        self.bytes_servidos += len(trecho)
        return _Resposta(206, trecho)


def test_inspecao_remota_le_cabecalho_e_dominios_sem_baixar_tudo():
    linhas = [_linha(str(i), '2019') for i in range(1, 3001)]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('SINASC_2019.csv', _csv(CABECALHO_2024, linhas))
    sessao = _SessaoRange(buffer.getvalue())
    r = tp.inspecionar_zip_remoto('https://exemplo/SINASC_2019_csv.zip', bytes_amostra=2_000,
                                  campos_dominio=['MESPRENAT', 'KOTELCHUCK'], sessao=sessao)
    assert r['colunas'] == CABECALHO_2024 and r['separador'] == ';'
    assert r['csv_interno'] == 'SINASC_2019.csv' and r['n_linhas_malformadas_amostra'] == 0
    assert 0 < r['n_linhas_amostra'] < len(linhas)
    assert r['dominios_amostra'] == {'MESPRENAT': {'02': r['n_linhas_amostra']}, 'KOTELCHUCK': None}


# --- baseline certificado continua intacto ---

def test_codigo_ancorado_do_baseline_nao_foi_alterado():
    from src.validacao import _validar_codigo_atual_ancorado, sha256
    m = json.loads((RAIZ_REAL / 'docs/architecture/preservacao_refatoracao.json').read_text(encoding='utf-8'))
    _validar_codigo_atual_ancorado(m)
    for nome, esperado in m['codigo_atual'].items():
        assert sha256(RAIZ_REAL / nome) == esperado, nome
    assert 'src/temporal.py' not in m['codigo_atual']


def test_numeros_certificados_2024_inalterados():
    ler = lambda n: json.loads((RAIZ_REAL / 'outputs/diagnostics' / n).read_text(encoding='utf-8'))
    aipw = {r['especificacao']: r['estimativa_pp'] for r in ler('fase2_aipw.json')['resultados']
            if r['populacao'] == 'sem_trimming'}
    assert aipw == {'C1': -1.340526785646844, 'C2': -1.2314558359825436}
    assert ler('fase1_amostra.json')['fluxo_amostra'][-1]['n_restante'] == 2251570
    assert ler('fase3_gate.json')['gate'] == 'GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR'
    r4 = ler('fase4_resultados.json')
    assert r4['principal']['media_pp'] == -1.294100493864875
    assert r4['principal']['proporcao_negativa'] * 100 == pytest.approx(84.68419813729975, abs=1e-12)
    assert r4['gate'] == 'HETEROGENEIDADE_SENSIVEL_A_MODELO'


def test_notebook_06_em_portugues_executado_e_sem_erros():
    import nbformat
    from src.visualizacao import auditar_idioma
    p = RAIZ_REAL / 'notebooks/06_auditoria_historica_sinasc.ipynb'
    nb = nbformat.read(p, as_version=4)
    nbformat.validate(nb)
    assert not auditar_idioma(nb)
    codigo = [c for c in nb.cells if c.cell_type == 'code']
    assert codigo and all(c.execution_count is not None for c in codigo)
    assert not any(o.output_type == 'error' for c in codigo for o in c.outputs)
    for c in codigo:
        compile(c.source, str(p), 'exec')
