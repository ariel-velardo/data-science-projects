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
    monkeypatch.setattr(tp, 'baixar_zip_retomavel', lambda *a, **k: pytest.fail('rede usada'))
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

    def falso_download(url, destino, sessao=None):
        destinos.append((url, Path(destino)))
        _zip(Path(destino), 'SINASC_2023.csv', _csv(CABECALHO_2024, [_linha()]))
        return {'bytes': Path(destino).stat().st_size,
                'sha256': hashlib.sha256(Path(destino).read_bytes()).hexdigest(),
                'conteudo': tp.verificar_zip_sinasc(destino), 'falhas': [], 'ultima_modificacao': 'x'}

    monkeypatch.setattr(tp, 'baixar_zip_retomavel', falso_download)
    r = tp.baixar_sinasc_ano(tmp_path, 2023)
    assert destinos == [(tp.url_sinasc(2023), tmp_path / 'data/raw/sinasc/2023/SINASC_2023_csv.zip')]
    assert r['manifesto']['arquivo_local'] == 'data/raw/sinasc/2023/SINASC_2023_csv.zip'
    assert r['manifesto']['crc_verificado'] and r['manifesto']['csv_interno'] == 'SINASC_2023.csv'
    # Segunda chamada: reutiliza o ZIP íntegro sem baixar de novo.
    monkeypatch.setattr(tp, 'baixar_zip_retomavel', lambda *a, **k: pytest.fail('baixou de novo'))
    assert tp.baixar_sinasc_ano(tmp_path, 2023)['reutilizado']
    depois = _instantaneo(tmp_path)
    assert {k: depois[k] for k in antes} == antes, 'Arquivos de 2024 ou source_manifest alterados.'
    assert set(depois) - set(antes) == {'data/raw/sinasc/2023/SINASC_2023_csv.zip',
                                        'outputs/temporal/manifestos/sinasc_2023.json'}


def test_manifesto_de_ano_recusa_zip_diferente_do_registrado(tmp_path):
    c = tp.caminhos_ano(tmp_path, 2023)
    _zip(c.zip_bruto, 'SINASC_2023.csv', _csv(CABECALHO_2024, [_linha()]))
    tp.gravar_manifesto_ano(tmp_path, 2023, {'sha256': '0' * 64, 'tamanho_bytes': c.zip_bruto.stat().st_size})
    with pytest.raises(ValueError, match='diverge do manifesto'):
        tp.baixar_sinasc_ano(tmp_path, 2023)


def test_zip_existente_corrompido_nao_e_reutilizado(tmp_path):
    c = tp.caminhos_ano(tmp_path, 2023)
    _zip(c.zip_bruto, 'SINASC_2023.csv', _csv(CABECALHO_2024, [_linha(str(i)) for i in range(200)]))
    dados = bytearray(c.zip_bruto.read_bytes())
    dados[60] ^= 0xFF  # corrompe o conteúdo comprimido
    c.zip_bruto.write_bytes(bytes(dados))
    with pytest.raises(Exception):
        tp.baixar_sinasc_ano(tmp_path, 2023)
    assert not c.manifesto.exists()


def test_manifesto_temporal_proibido_para_2024(tmp_path):
    with pytest.raises(ValueError, match='baseline'):
        tp.gravar_manifesto_ano(tmp_path, 2024, {'x': 1})
    with pytest.raises(ValueError, match='source_manifest'):
        tp.ler_manifesto_ano(tmp_path, 2024)


def test_verificacao_zip_exige_um_unico_csv(tmp_path):
    p = tmp_path / 'dois.zip'
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr('a.csv', 'x')
        z.writestr('b.csv', 'y')
    with pytest.raises(ValueError, match='um CSV'):
        tp.verificar_zip_sinasc(p)


# --- download retomável (servidor falso, sem rede) ---

class _Fluxo:
    def __init__(self, status, dados, falhar_apos=None):
        self.status_code, self.dados, self.falhar_apos = status, dados, falhar_apos

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        import requests
        for i in range(0, len(self.dados), 7):
            if self.falhar_apos is not None and i >= self.falhar_apos:
                raise requests.ConnectionError('queda simulada')
            yield self.dados[i:i + 7]


class _ServidorArquivo:
    def __init__(self, dados, falhas=0, ignora_range=False):
        self.dados, self.falhas, self.ignora_range, self.ranges = dados, falhas, ignora_range, []

    def head(self, url, timeout=None):
        return _Resposta(200, headers={'Content-Length': str(len(self.dados)), 'Last-Modified': 'hoje'})

    def get(self, url, headers=None, stream=False, timeout=None):
        inicio = int(headers['Range'].split('=')[1].rstrip('-')) if headers else 0
        self.ranges.append(inicio)
        if self.ignora_range:
            return _Fluxo(200, self.dados)
        falhar = len(self.dados) // 2 - inicio if self.falhas else None
        self.falhas = max(0, self.falhas - 1)
        return _Fluxo(206 if inicio else 200, self.dados[inicio:], falhar)


def _zip_em_memoria(n=300):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('SINASC_2019.csv', _csv(CABECALHO_2024, [_linha(str(i), '2019') for i in range(n)]))
    return buffer.getvalue()


def test_download_retomavel_continua_de_onde_parou(tmp_path):
    dados = _zip_em_memoria()
    servidor = _ServidorArquivo(dados, falhas=1)
    destino = tmp_path / 'SINASC_2019_csv.zip'
    r = tp.baixar_zip_retomavel('u', destino, sessao=servidor, espera_segundos=0)
    assert destino.read_bytes() == dados and not destino.with_suffix('.zip.part').exists()
    assert r['sha256'] == hashlib.sha256(dados).hexdigest() and len(r['falhas']) == 1
    assert servidor.ranges[0] == 0 and 0 < servidor.ranges[1] < len(dados)


def test_download_esgotado_preserva_parcial_e_nao_cria_destino(tmp_path):
    servidor = _ServidorArquivo(_zip_em_memoria(), falhas=99)
    destino = tmp_path / 'SINASC_2019_csv.zip'
    with pytest.raises(RuntimeError, match='incompleto'):
        tp.baixar_zip_retomavel('u', destino, sessao=servidor, tentativas=1, espera_segundos=0)
    assert not destino.exists() and destino.with_suffix('.zip.part').exists()


def test_download_recusa_servidor_que_ignora_range(tmp_path):
    dados = _zip_em_memoria()
    destino = tmp_path / 'SINASC_2019_csv.zip'
    destino.with_suffix('.zip.part').write_bytes(dados[:10])
    with pytest.raises(ValueError, match='Range'):
        tp.baixar_zip_retomavel('u', destino, sessao=_ServidorArquivo(dados, ignora_range=True),
                                tentativas=1, espera_segundos=0)
    assert destino.with_suffix('.zip.part').read_bytes() == dados[:10]


def test_download_com_crc_invalido_nao_promove_arquivo(tmp_path):
    dados = bytearray(_zip_em_memoria())
    dados[60] ^= 0xFF
    destino = tmp_path / 'SINASC_2019_csv.zip'
    with pytest.raises(Exception):
        tp.baixar_zip_retomavel('u', destino, sessao=_ServidorArquivo(bytes(dados)), espera_segundos=0)
    assert not destino.exists()


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


# --- conversão registrada e orquestração sequencial ---

def _falso_download_zip(linhas_por_ano):
    def baixar(url, destino, sessao=None):
        ano = int(Path(destino).parent.name)
        _zip(Path(destino), f'SINASC_{ano}.csv', _csv(CABECALHO_2024, linhas_por_ano[ano]))
        return {'bytes': Path(destino).stat().st_size, 'sha256': hashlib.sha256(Path(destino).read_bytes()).hexdigest(),
                'conteudo': tp.verificar_zip_sinasc(destino), 'falhas': [], 'ultima_modificacao': 'x'}
    return baixar


def _raiz_completa(tmp_path):
    _raiz_com_baseline(tmp_path)
    p = tmp_path / 'data/processed/sinasc_2024.parquet'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b'parquet certificado')


def test_preparar_anos_registra_download_e_conversao_por_ano(tmp_path, monkeypatch):
    _raiz_completa(tmp_path)
    linhas = {2022: [_linha('1', '2022'), _linha('2', '2022')], 2023: [_linha('1', '2023')]}
    monkeypatch.setattr(tp, 'baixar_zip_retomavel', _falso_download_zip(linhas))
    antes = tp.impressao_baseline(tmp_path)
    r = tp.preparar_anos(tmp_path, [2022, 2023])
    assert [x['ano'] for x in r] == [2022, 2023] and [x['n_registros'] for x in r] == [2, 1]
    m = tp.ler_manifesto_ano(tmp_path, 2022)
    assert m['conversao']['parquet_sha256'] == hashlib.sha256(tp.caminhos_ano(tmp_path, 2022).parquet.read_bytes()).hexdigest()
    assert m['conversao']['colunas_originais'] == CABECALHO_2024 and m['conversao']['separador'] == ';'
    assert tp.impressao_baseline(tmp_path) == antes
    # Reexecução: nada é baixado nem reconvertido; o manifesto permanece idêntico.
    monkeypatch.setattr(tp, 'baixar_zip_retomavel', lambda *a, **k: pytest.fail('baixou de novo'))
    texto = tp.caminhos_ano(tmp_path, 2022).manifesto.read_text(encoding='utf-8')
    tp.preparar_anos(tmp_path, [2022])
    assert tp.caminhos_ano(tmp_path, 2022).manifesto.read_text(encoding='utf-8') == texto
    log = (tmp_path / 'data/interim/temporal_registro_execucao.jsonl').read_text(encoding='utf-8').splitlines()
    assert all(json.loads(l)['status'] == 'ok' for l in log)


def test_preparar_anos_recusa_2024_e_para_no_primeiro_erro(tmp_path, monkeypatch):
    _raiz_completa(tmp_path)
    with pytest.raises(ValueError, match='baseline'):
        tp.preparar_anos(tmp_path, [2024])

    def falha(*a, **k):
        raise RuntimeError('rede indisponível')

    monkeypatch.setattr(tp, 'baixar_zip_retomavel', falha)
    with pytest.raises(RuntimeError, match='rede'):
        tp.preparar_anos(tmp_path, [2021, 2022])
    eventos = [json.loads(l) for l in (tmp_path / 'data/interim/temporal_registro_execucao.jsonl')
               .read_text(encoding='utf-8').splitlines()]
    assert [(e['ano'], e['status']) for e in eventos] == [(2021, 'falha')]
    assert not tp.caminhos_ano(tmp_path, 2022).zip_bruto.exists()


def test_conversao_registrada_detecta_parquet_adulterado(tmp_path, monkeypatch):
    _raiz_completa(tmp_path)
    monkeypatch.setattr(tp, 'baixar_zip_retomavel', _falso_download_zip({2020: [_linha('1', '2020')]}))
    tp.preparar_anos(tmp_path, [2020])
    parquet = tp.caminhos_ano(tmp_path, 2020).parquet
    import pandas as pd
    pd.DataFrame({'contador': ['9']}).to_parquet(parquet)
    with pytest.raises(ValueError, match='diverge da conversão'):
        tp.registrar_conversao(tmp_path, 2020)


def test_manifestos_temporais_nao_incluem_2024():
    pasta = RAIZ_REAL / 'outputs/temporal/manifestos'
    nomes = sorted(p.name for p in pasta.glob('*.json'))
    assert 'sinasc_2024.json' not in nomes
    for p in pasta.glob('*.json'):
        m = json.loads(p.read_text(encoding='utf-8'))
        assert m['url'] == tp.url_sinasc(m['ano']) and m['crc_verificado']
        assert m['arquivo_local'] == f"data/raw/sinasc/{m['ano']}/SINASC_{m['ano']}_csv.zip"
        assert len(m['sha256']) == 64 and len(m['conversao']['parquet_sha256']) == 64
