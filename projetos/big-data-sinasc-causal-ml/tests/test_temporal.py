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


def test_notebook_06_em_portugues_executado_e_sem_erros():
    import nbformat
    from src.visualizacao import auditar_idioma
    p = RAIZ_REAL / 'notebooks/historico/06_auditoria_historica_sinasc.ipynb'
    nb = nbformat.read(p, as_version=4)
    nbformat.validate(nb)
    assert not auditar_idioma(nb)
    codigo = [c for c in nb.cells if c.cell_type == 'code']
    assert codigo and all(c.execution_count is not None for c in codigo)
    assert not any(o.output_type == 'error' for c in codigo for o in c.outputs)
    for c in codigo:
        compile(c.source, str(p), 'exec')


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


# --- auditoria anual com as views congeladas, critérios e chave (ano, CONTADOR) ---

def _linhas_ano(ano, n=10, troca=None):
    """n registros elegíveis alternando T e Y; ``troca`` = {indice: {campo: valor}}."""
    base = []
    for i in range(n):
        r = dict(zip(CABECALHO_2024, _linha(str(i + 1), str(ano))))
        r['MESPRENAT'] = '02' if i % 2 == 0 else '05'
        r['PESO'] = '3100' if i % 3 else '2000'
        r.update((troca or {}).get(i, {}))
        base.append(r)
    return base


def _parquet_ano(tmp_path, ano, registros, minusculo=False):
    import pandas as pd
    tabela = pd.DataFrame(registros, dtype='string')
    if minusculo:
        tabela = tabela[[*CABECALHO_2024[1:], 'contador']].rename(columns=str.lower)
    p = tmp_path / f'sinasc_{ano}.parquet'
    tabela.to_parquet(p, index=False)
    return p


def _auditoria(tmp_path, ano, **kw):
    minusculo = kw.pop('minusculo', False)
    return tp.auditar_ano(_parquet_ano(tmp_path, ano, _linhas_ano(ano, **kw), minusculo), ano)


def _criterios(a, ref, status=None):
    return tp.avaliar_criterios(a, ref, integridade_ok=True, baseline_intacto=True,
                                caminhos_distintos=True, status_oficial=status)


def test_auditoria_ano_limpo_e_aprovada_e_independe_de_caixa_e_posicao(tmp_path):
    ref = _auditoria(tmp_path, 2024)
    a = _auditoria(tmp_path, 2016, minusculo=True)
    assert a['n_bruto'] == a['n_principal'] == 10 and a['n_t1'] == 5 and a['n_y1'] == 4
    assert {r['etapa']: r['n_restante'] for r in a['fluxo']}['A3'] == 10
    assert tp.veredito_ano(_criterios(a, ref)) == 'APROVADO'
    assert a['niveis_derivados'][0]['ano'] == 2016


def test_chave_temporal_e_ano_contador(tmp_path):
    ref = _auditoria(tmp_path, 2024)
    # Mesmo CONTADOR em anos diferentes é permitido: a chave é (ano, CONTADOR).
    a2023 = _auditoria(tmp_path, 2023)
    assert a2023['n_contador_duplicado'] == 0 and tp.veredito_ano(_criterios(a2023, ref)) == 'APROVADO'
    duplicado = _auditoria(tmp_path, 2022, troca={1: {'contador': '1'}})
    c08 = next(c for c in _criterios(duplicado, ref) if c['criterio'] == 'C08_contador_utilizavel')
    assert duplicado['n_contador_duplicado'] == 1 and c08['resultado'] == 'FALHA'


def test_datas_fora_do_ano_seguem_faixas_fixadas():
    assert tp._faixa(0, 10_000) == 'OK'
    assert tp._faixa(1, 10_000) == 'HARMONIZACAO'
    assert tp._faixa(2, 10_000) == 'FALHA'


def test_data_fora_do_ano_reprova_acima_da_tolerancia(tmp_path):
    ref = _auditoria(tmp_path, 2024)
    a = _auditoria(tmp_path, 2021, troca={0: {'DTNASC': '01012020'}, 1: {'DTNASC': '3102'}})
    assert (a['n_dtnasc_fora_do_ano'], a['n_dtnasc_invalida']) == (1, 1)
    criterios = _criterios(a, ref)
    assert next(c for c in criterios if c['criterio'] == 'C07_datas_do_ano')['resultado'] == 'FALHA'
    assert tp.veredito_ano(criterios) == 'NAO_APROVADO'


def test_codigo_novo_em_covariavel_e_detectado(tmp_path):
    ref = _auditoria(tmp_path, 2024)
    a = _auditoria(tmp_path, 2019, troca={3: {'ESCMAE2010': '7'}})
    assert a['inesperados']['ESCMAE2010'] == {'n': 1, 'fracao': 0.1, 'valores': {'7': 1}}
    r = {c['criterio']: c['resultado'] for c in _criterios(a, ref)}
    assert r['C06_codificacao_compativel'] == 'FALHA' and r['C11_categorias_covariaveis'] == 'FALHA'


def test_dado_preliminar_nao_entra_na_janela(tmp_path):
    ref = _auditoria(tmp_path, 2024)
    a = _auditoria(tmp_path, 2025)
    assert tp.veredito_ano(_criterios(a, ref, status='preliminar')) == 'NAO_APROVADO'


def test_ano_sem_covariavel_essencial_para_nos_criterios_de_presenca(tmp_path):
    ref = _auditoria(tmp_path, 2024)
    registros = [{k: v for k, v in r.items() if k != 'PARIDADE'} for r in _linhas_ano(2012)]
    a = tp.auditar_ano(_parquet_ano(tmp_path, 2012, registros), 2012)
    assert a['essenciais_ausentes'] == ['PARIDADE'] and 'n_bruto' not in a
    criterios = _criterios(a, ref)
    assert criterios[-1]['criterio'] == 'C05_covariaveis_presentes' and criterios[-1]['resultado'] == 'FALHA'


# --- agregações descritivas ---

def test_tabelas_descritivas_e_comparacao_com_2024(tmp_path):
    ref = _auditoria(tmp_path, 2024)
    a = _auditoria(tmp_path, 2020, troca={0: {'MESPRENAT': '99'}, 1: {'PESO': ''}})
    tabelas = tp.tabelas_descritivas([a, ref])
    d = tabelas['descritiva_anual'].set_index('ano')
    assert d.loc[2020, 'n_bruto'] == 10 and d.loc[2020, 'n_principal'] == 8
    assert d.loc[2020, 'pct_principal'] == pytest.approx(80.0)
    assert d.loc[2024, 'prevalencia_t_pct'] == pytest.approx(50.0)
    q = tabelas['qualidade_anos'].set_index('ano')
    assert q.loc[2020, 'mesprenat_99_pct'] == pytest.approx(10.0) and q.loc[2020, 'peso_invalido_p0_pct'] == pytest.approx(10.0)
    cov = tabelas['covariaveis_anuais']
    assert cov.groupby(['ano', 'variavel']).pct.sum().round(10).eq(100).all()
    geo = tabelas['geografia_anual']
    assert geo.groupby('ano').participacao_bruto_pct.sum().round(10).eq(100).all()
    comp = tp.comparar_com_referencia(tabelas['descritiva_anual'], ['pct_principal'])
    assert comp.set_index('ano').loc[2024, 'pct_principal_menos_2024'] == 0
    assert comp.set_index('ano').loc[2020, 'pct_principal_menos_2024'] == pytest.approx(-20.0)
    longa = tp.comparar_com_referencia(cov, ['pct'], chaves=['variavel', 'categoria'])
    assert longa.loc[longa.ano == 2024, 'pct_menos_2024'].eq(0).all()
    aud = tp.tabela_auditoria([a, ref], _criterios(a, ref) + _criterios(ref, ref), CABECALHO_2024)
    assert list(aud.veredito) == ['APROVADO', 'APROVADO'] and aud.n_apos_regras_basicas.tolist() == [8, 10]
    assert aud.missing_tratamento.tolist() == [1, 0]


def test_comparacao_exige_ano_de_referencia():
    import pandas as pd
    with pytest.raises(ValueError, match='referência'):
        tp.comparar_com_referencia(pd.DataFrame({'ano': [2020], 'x': [1.0]}), ['x'])


def _contador_por_uf(ano):
    """Duas UFs de residência, contador reiniciando em 1 em cada uma (padrão de 2014-2017)."""
    troca = {i: {'contador': str(i % 5 + 1), 'CODMUNRES': '355030' if i < 5 else '330455'} for i in range(10)}
    return troca


def test_h1_harmoniza_contador_por_uf_somente_em_ano_documentado(tmp_path):
    ref = _auditoria(tmp_path, 2024, troca={i: {'CODMUNRES': '355030' if i < 5 else '330455'} for i in range(10)})
    a2015 = _auditoria(tmp_path, 2015, troca=_contador_por_uf(2015))
    assert a2015['n_contador_duplicado'] == 5 and a2015['n_chave_uf_contador_duplicada'] == 0
    assert a2015['n_contador_igual_1'] == 2
    c08 = next(c for c in _criterios(a2015, ref) if c['criterio'] == 'C08_contador_utilizavel')
    assert c08['resultado'] == 'HARMONIZACAO' and 'H1' in c08['evidencia']
    assert tp.veredito_ano(_criterios(a2015, ref)) == 'APROVADO_COM_HARMONIZACAO'
    # Mesmo padrão fora dos anos documentados continua sendo falha.
    a2021 = _auditoria(tmp_path, 2021, troca=_contador_por_uf(2021))
    assert tp.veredito_ano(_criterios(a2021, ref)) == 'NAO_APROVADO'


def test_h1_nao_se_aplica_se_chave_composta_repetir(tmp_path):
    ref = _auditoria(tmp_path, 2024)
    a = _auditoria(tmp_path, 2016, troca={1: {'contador': '1'}})  # mesma UF, contador repetido
    assert a['n_chave_uf_contador_duplicada'] == 1
    c08 = next(c for c in _criterios(a, ref) if c['criterio'] == 'C08_contador_utilizavel')
    assert c08['resultado'] == 'FALHA'


def test_registro_de_harmonizacoes_documentado():
    for h in tp.HARMONIZACOES:
        assert {'id', 'variavel', 'anos', 'valor_original', 'valor_harmonizado', 'justificativa'} <= set(h)
        assert tp.ANO_BASELINE not in h['anos']


def test_notebook_07_em_portugues_executado_sem_inferencia():
    import nbformat
    from src.visualizacao import auditar_idioma
    p = RAIZ_REAL / 'notebooks/historico/07_descritiva_temporal_sinasc.ipynb'
    nb = nbformat.read(p, as_version=4)
    nbformat.validate(nb)
    assert not auditar_idioma(nb)
    codigo = [c for c in nb.cells if c.cell_type == 'code']
    assert all(c.execution_count is not None for c in codigo)
    assert not any(o.output_type == 'error' for c in codigo for o in c.outputs)
    fonte = '\n'.join(c.source for c in codigo)
    for proibido in ('calcular_aipw', 'cross_fitting', 'estimar_propensity_oof', 'ajuste_honesto', 'ajustar_modelo'):
        assert proibido not in fonte, proibido
    assert 'Interpretação pendente' not in '\n'.join(c.source for c in nb.cells)


def test_tabelas_temporais_versionaveis_sao_coerentes():
    import pandas as pd
    pasta = RAIZ_REAL / 'outputs/temporal/tabelas'
    aud = pd.read_csv(pasta / 'auditoria_anos.csv')
    assert aud.ano.tolist() == list(range(2014, 2025))
    assert aud.set_index('ano').loc[2024, 'n_apos_regras_basicas'] == 2251570
    assert set(aud.veredito) <= {'APROVADO', 'APROVADO_COM_HARMONIZACAO', 'NAO_APROVADO'}
    crit = pd.read_csv(pasta / 'criterios_admissao.csv')
    assert crit.groupby('ano').criterio.nunique().eq(len(tp.CRITERIOS_ADMISSAO)).all()
    harm = pd.read_csv(pasta / 'harmonizacoes.csv')
    assert harm.verificada_no_ano.all()
    comuns = set(harm.ano)
    assert comuns == set(aud.loc[aud.veredito == 'APROVADO_COM_HARMONIZACAO', 'ano'])
    desc = pd.read_csv(pasta / 'descritiva_anual.csv').set_index('ano')
    assert (desc.n_principal <= desc.n_bruto).all() and desc.loc[2024, 'pct_principal_menos_2024'] == 0
    cov = pd.read_csv(pasta / 'covariaveis_anuais.csv')
    somas = cov.groupby(['ano', 'variavel']).n.sum().unstack()
    assert somas.eq(desc.n_principal, axis=0).all().all()
    for nome in ('qualidade_anos', 'missing_anual', 'geografia_anual'):
        assert set(pd.read_csv(pasta / f'{nome}.csv').ano) == set(desc.index)


def test_manifestos_temporais_nao_incluem_2024():
    pasta = RAIZ_REAL / 'outputs/temporal/manifestos'
    nomes = sorted(p.name for p in pasta.glob('*.json'))
    assert 'sinasc_2024.json' not in nomes
    for p in pasta.glob('*.json'):
        m = json.loads(p.read_text(encoding='utf-8'))
        assert m['url'] == tp.url_sinasc(m['ano']) and m['crc_verificado']
        assert m['arquivo_local'] == f"data/raw/sinasc/{m['ano']}/SINASC_{m['ano']}_csv.zip"
        assert len(m['sha256']) == 64 and len(m['conversao']['parquet_sha256']) == 64


# --- contratos v1 / v1.1, janelas congeladas e chave uniforme ---

def test_janelas_congeladas_e_contratos_lado_a_lado():
    assert tp.JANELAS['principal'] == {'anos': tuple(range(2014, 2025)), 'contrato': 'v1.1'}
    assert tp.JANELAS['sensibilidade']['anos'] == tuple(range(2018, 2025))
    assert tp.JANELAS['sensibilidade']['contrato'] == 'v1'
    assert tp.JANELAS['sensibilidade']['obrigatoria_em'] == ('08', '09')
    assert tp.CONTRATOS['v1']['harmonizacoes'] == () and tp.CONTRATOS['v1.1']['harmonizacoes'] == ('H1',)
    assert 'antes da leitura' in tp.VERSAO_CRITERIOS_V1
    assert 'após a leitura' in tp.VERSAO_CRITERIOS_V1_1 and 'antes de qualquer estimação' in tp.VERSAO_CRITERIOS_V1_1


def test_h1_e_harmonizacao_de_identificador_com_cronologia():
    h1 = next(h for h in tp.HARMONIZACOES if h['id'] == 'H1')
    assert h1['tipo'] == 'harmonização de identificador' and h1['anos'] == (2014, 2015, 2016, 2017)
    assert set(h1['nao_altera']) >= {'tratamento', 'desfecho', 'covariáveis', 'regras de inclusão', 'frequências'}
    assert 'após a leitura' in h1['identificada_em'] and 'antes de qualquer estimação' in h1['aprovada_em']


def test_resultado_por_contrato_so_difere_em_c08_harmonizado():
    c08 = {'criterio': 'C08_contador_utilizavel', 'resultado': 'HARMONIZACAO'}
    outro = {'criterio': 'C07_datas_do_ano', 'resultado': 'HARMONIZACAO'}
    assert tp.resultado_no_contrato(c08, 'v1') == 'FALHA' and tp.resultado_no_contrato(c08, 'v1.1') == 'HARMONIZACAO'
    assert tp.resultado_no_contrato(outro, 'v1') == 'HARMONIZACAO'
    assert tp.veredito_no_contrato([c08], 'v1') == 'NAO_APROVADO'
    assert tp.veredito_no_contrato([c08], 'v1.1') == 'APROVADO_COM_HARMONIZACAO'
    with pytest.raises(ValueError, match='Contrato'):
        tp.resultado_no_contrato(c08, 'v2')


def test_chave_uniforme_valida_em_ano_com_e_sem_h1(tmp_path):
    tp.validar_chave_temporal(_auditoria(tmp_path, 2020))
    tp.validar_chave_temporal(_auditoria(tmp_path, 2015, troca=_contador_por_uf(2015)))
    with pytest.raises(ValueError, match='Chave temporal inválida'):
        tp.validar_chave_temporal(_auditoria(tmp_path, 2016, troca={1: {'contador': '1'}}))
    with pytest.raises(ValueError, match='Chave temporal inválida'):
        tp.validar_chave_temporal(_auditoria(tmp_path, 2019, troca={2: {'CODMUNRES': '35'}}))


def test_tabelas_versionadas_registram_os_dois_contratos():
    import pandas as pd
    aud = pd.read_csv(RAIZ_REAL / 'outputs/temporal/tabelas/auditoria_anos.csv').set_index('ano')
    anos_h1 = [2014, 2015, 2016, 2017]
    assert aud.loc[anos_h1, 'veredito_v1'].eq('NAO_APROVADO').all()
    assert aud.loc[anos_h1, 'veredito_v1_1'].eq('APROVADO_COM_HARMONIZACAO').all()
    assert aud.loc[2018:2024, 'veredito_v1'].eq('APROVADO').all() and aud.loc[2018:2024, 'veredito_v1_1'].eq('APROVADO').all()
    assert aud.index[aud.admitido_janela_principal].tolist() == list(tp.JANELAS['principal']['anos'])
    assert aud.index[aud.admitido_janela_sensibilidade].tolist() == list(tp.JANELAS['sensibilidade']['anos'])
    assert aud.chave_temporal_unica.all()
    contrato = json.loads((RAIZ_REAL / 'outputs/temporal/contrato_temporal.json').read_text(encoding='utf-8'))
    assert contrato['janelas']['principal']['anos'] == list(range(2014, 2025))
    assert contrato['vereditos']['2015'] == {'v1': 'NAO_APROVADO', 'v1.1': 'APROVADO_COM_HARMONIZACAO'}
    assert contrato['vereditos']['2024'] == {'v1': 'APROVADO', 'v1.1': 'APROVADO'}


# --- notebook 08: comparabilidade, suporte e positividade temporal ---

def _dados_diagnostico_temporal():
    import pandas as pd

    return pd.DataFrame({
        'contador': ['4', '1', '3', '2', '8', '5', '7', '6'],
        'tratamento': [0, 0, 1, 1, 0, 1, 0, 1],
        'Y_BAIXO_PESO': [0, 1, 0, 1, 0, 0, 1, 0],
        'IDADEMAE_NUM': [18., 24., 31., 42., 19., 28., 36., 45.],
        'ESCOLARIDADE_MAE': ['1', '2', '2', '3', '1', '2', '3', '3'],
        'RACA_COR_MAE': ['1', '1', '2', '2', '1', '2', '2', '1'],
        'SITUACAO_CONJUGAL': ['1', '2', '1', '2', '1', '2', '1', '2'],
        'PARIDADE_CAT': ['0', '1', '1', '2', '0', '1', '2', '2'],
        'PERDAS_FETAIS_CAT': ['0', '0', '1', '1', '0', '1', '0', '1'],
        'UF_RESIDENCIA': ['35', '33', '35', '33', '35', '33', '35', '33'],
    })


def test_limites_do_notebook_08_estao_congelados_antes_dos_resultados():
    assert tp.LIMITES_DIAGNOSTICO_TEMPORAL == {
        'smd_abs': 0.10,
        'celula_minima_por_grupo': 100,
        'tratamento_extremo_inferior': 0.01,
        'tratamento_extremo_superior': 0.99,
        'faixas_propensity': ((0.01, 0.99), (0.05, 0.95)),
    }
    assert tp.SEMENTE_PROPENSITY_TEMPORAL == 20240925
    assert tp.N_FOLDS_PROPENSITY_TEMPORAL == 5


def test_ordem_certificada_2024_e_preservada_e_novos_anos_usam_chave_temporal(tmp_path):
    registros = _linhas_ano(2024, n=4)
    for registro, contador, municipio in zip(registros, ['20', '3', '11', '2'],
                                             ['355030', '330455', '355030', '330455']):
        registro['contador'] = contador
        registro['CODMUNRES'] = municipio
    parquet_2024 = _parquet_ano(tmp_path, 2024, registros)
    dados_2024, contrato_2024 = tp.carregar_amostra_temporal(parquet_2024, 2024)
    assert dados_2024.contador.astype(str).tolist() == ['20', '3', '11', '2']
    assert contrato_2024['regra_ordenacao'] == tp.ORDEM_2024_CERTIFICADA

    parquet_2023 = _parquet_ano(tmp_path, 2023, [dict(r, DTNASC='01012023') for r in registros])
    dados_2023, contrato_2023 = tp.carregar_amostra_temporal(parquet_2023, 2023)
    assert list(zip(dados_2023.UF_RESIDENCIA, dados_2023.contador.astype(str))) == [
        ('33', '2'), ('33', '3'), ('35', '11'), ('35', '20')]
    assert contrato_2023['regra_ordenacao'] == tp.ORDEM_CHAVE_TEMPORAL
    assert contrato_2023['sha256_sequencia_chave'] != contrato_2024['sha256_sequencia_chave']


def test_carregador_temporal_normaliza_nome_fisico_contador_em_caixa_alta(tmp_path):
    import pandas as pd

    registros = _linhas_ano(2014, n=4)
    tabela = pd.DataFrame(registros, dtype='string').rename(columns={'contador': 'CONTADOR'})
    parquet = tmp_path / 'sinasc_2014_contador_maiusculo.parquet'
    tabela.to_parquet(parquet, index=False)
    dados, contrato = tp.carregar_amostra_temporal(parquet, 2014)
    assert 'contador' in dados.columns and 'CONTADOR' not in dados.columns
    assert dados.contador.astype(str).tolist() == ['1', '2', '3', '4']
    assert contrato['n'] == 4


def test_smd_intra_ano_retorna_niveis_sinal_e_flag_sem_misturar_composicao():
    dados = _dados_diagnostico_temporal()
    smd = tp.smd_intra_ano(dados, 2020, numericas=['IDADEMAE_NUM'],
                           categoricas=['ESCOLARIDADE_MAE'])
    assert list(smd.columns) == ['ano', 'variavel', 'nivel', 'smd', 'abs_smd', 'sinalizado_010']
    assert set(smd.loc[smd.variavel == 'ESCOLARIDADE_MAE', 'nivel']) == {'1', '2', '3'}
    assert (smd.abs_smd == smd.smd.abs()).all()
    assert (smd.sinalizado_010 == smd.abs_smd.gt(0.10)).all()


def test_smd_temporal_compara_populacoes_com_2024_em_funcao_separada():
    atual = _dados_diagnostico_temporal().iloc[:6].copy()
    referencia = _dados_diagnostico_temporal().copy()
    comp = tp.smd_composicao_vs_referencia(
        atual, referencia, 2019, numericas=['IDADEMAE_NUM'], categoricas=['RACA_COR_MAE'])
    assert list(comp.columns) == [
        'ano', 'ano_referencia', 'variavel', 'nivel', 'smd_temporal', 'abs_smd_temporal',
        'sinalizado_010']
    assert comp.ano.eq(2019).all() and comp.ano_referencia.eq(2024).all()
    assert 'tratamento' not in comp.columns


def test_smd_temporal_por_resumos_reproduz_calculo_em_memoria():
    atual = _dados_diagnostico_temporal().iloc[:6].copy()
    referencia = _dados_diagnostico_temporal().copy()
    direto = tp.smd_composicao_vs_referencia(
        atual, referencia, 2019, numericas=['IDADEMAE_NUM'], categoricas=['RACA_COR_MAE'])
    compacto = tp.smd_composicao_resumida_vs_referencia(
        tp.resumir_composicao(atual, ['IDADEMAE_NUM'], ['RACA_COR_MAE']),
        tp.resumir_composicao(referencia, ['IDADEMAE_NUM'], ['RACA_COR_MAE']),
        2019)
    cols = ['variavel', 'nivel', 'smd_temporal', 'abs_smd_temporal', 'sinalizado_010']
    pd = pytest.importorskip('pandas')
    pd.testing.assert_frame_equal(
        direto[cols].sort_values(['variavel', 'nivel'], na_position='first').reset_index(drop=True),
        compacto[cols].sort_values(['variavel', 'nivel'], na_position='first').reset_index(drop=True),
        check_dtype=False)


def test_distribuicao_tratamento_e_positividade_aplicam_limites_pre_especificados():
    dados = _dados_diagnostico_temporal()
    tratamento = tp.distribuicao_tratamento(dados, 2022)
    assert set(tratamento.granularidade) == {'ano', 'ano_uf'}
    assert tratamento.loc[tratamento.granularidade == 'ano', 'n'].item() == len(dados)
    assert tratamento.n_t0.add(tratamento.n_t1).eq(tratamento.n).all()

    positividade = tp.positividade_perfis(dados, 2022)
    assert set(positividade.perfil) == {
        'UF_RESIDENCIA', 'FAIXA_IDADE_MAE', 'ESCOLARIDADE_MAE', 'RACA_COR_MAE', 'PARIDADE_CAT'}
    assert positividade.flag_celula_pequena.all()
    assert (positividade.flag_tratamento_extremo ==
            (positividade.proporcao_t1.le(0.01) | positividade.proporcao_t1.ge(0.99))).all()


def test_propensity_temporal_em_fixture_e_deterministico_e_estratificado():
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(20240925)
    n = 100
    dados = pd.DataFrame({
        'IDADEMAE_NUM': rng.integers(15, 46, n).astype(float),
        'ESCOLARIDADE_MAE': rng.choice(['1', '2', '3'], n),
        'RACA_COR_MAE': rng.choice(['1', '2'], n),
        'SITUACAO_CONJUGAL': rng.choice(['1', '2'], n),
        'PARIDADE_CAT': rng.choice(['0', '1', '2'], n),
        'PERDAS_FETAIS_CAT': rng.choice(['0', '1'], n),
        'UF_RESIDENCIA': rng.choice(['33', '35'], n),
    })
    tratamento = pd.Series(np.tile([0, 1], n // 2), name='tratamento')
    p1, m1 = tp.ajustar_propensity_temporal(dados, tratamento, n_folds=5)
    p2, m2 = tp.ajustar_propensity_temporal(dados, tratamento, n_folds=5)
    assert np.array_equal(p1, p2)
    assert np.isfinite(p1).all() and ((p1 > 0) & (p1 < 1)).all()
    assert m1['n_folds'] == m2['n_folds'] == 5 and len(m1['tempo_por_fold_segundos']) == 5
    assert all(f['n_validacao'] == 20 for f in m1['folds'])


def test_metricas_propensity_overlap_ess_e_fracoes_fora_de_suporte():
    import numpy as np

    propensity = np.array([0.02, 0.70, 0.30, 0.98])
    tratamento = np.array([0, 0, 1, 1])
    resumo = tp.resumir_propensity_ano(propensity, tratamento, 2021, auc_oof=0.75)
    assert resumo['ano'] == 2021 and resumo['auc_oof'] == 0.75
    assert resumo['suporte_comum_inferior'] == pytest.approx(0.30)
    assert resumo['suporte_comum_superior'] == pytest.approx(0.70)
    assert resumo['fora_005_095_n'] == 2 and resumo['fora_005_095_fracao'] == pytest.approx(0.5)
    assert resumo['fora_005_095_t0_fracao'] == pytest.approx(0.5)
    assert resumo['fora_005_095_t1_fracao'] == pytest.approx(0.5)
    assert 0 < resumo['ess_t0'] <= 2 and 0 < resumo['ess_t1'] <= 2


def test_controle_positivo_compara_todos_os_componentes_e_detecta_divergencia():
    import numpy as np

    propensity = np.array([0.02, 0.70, 0.30, 0.98])
    tratamento = np.array([0, 0, 1, 1])
    resumo = tp.resumir_propensity_ano(propensity, tratamento, 2024, auc_oof=0.75)
    certificado = {
        'grupos': {
            'controle': {'n': 2, 'min': 0.02, 'max': 0.70,
                         'percentis': {f'p{int(p * 100):02d}': float(np.quantile(propensity[tratamento == 0], p))
                                        for p in [0, .01, .05, .25, .5, .75, .95, .99, 1]}},
            'tratado': {'n': 2, 'min': 0.30, 'max': 0.98,
                        'percentis': {f'p{int(p * 100):02d}': float(np.quantile(propensity[tratamento == 1], p))
                                       for p in [0, .01, .05, .25, .5, .75, .95, .99, 1]}},
        },
        'suporte_comum_observado': {'inferior': 0.30, 'superior': 0.70},
        'trimming_diagnostico': [{'regra': '0.05_0.95', 'n_excluido': 2}],
        'metodo': {'auc_oof': 0.75},
    }
    controle = tp.comparar_controle_positivo_2024(resumo, certificado)
    assert controle['aprovado'] and all(controle['checks'].values())
    divergente = tp.comparar_controle_positivo_2024({**resumo, 'auc_oof': 0.70}, certificado)
    assert not divergente['aprovado'] and not divergente['checks']['auc_oof']


def test_cache_temporal_e_deterministico_validado_e_invalidado_por_contrato(tmp_path):
    import numpy as np

    base = tp.criar_contrato_cache(
        ano=2020, parquet_sha256='a' * 64, codigo_sha256='b' * 64,
        chave_sha256='c' * 64, regra_ordenacao=tp.ORDEM_CHAVE_TEMPORAL,
        n=4, n_t0=2, n_t1=2)
    caminhos = tp.salvar_cache_propensity(tmp_path, base, np.array([0.1, 0.2, 0.8, 0.9]))
    assert caminhos['metadados'].exists() and caminhos['predicoes'].exists()
    carregado = tp.carregar_cache_propensity(tmp_path, base)
    assert np.array_equal(carregado, np.array([0.1, 0.2, 0.8, 0.9]))
    assert 'timestamp' not in json.loads(caminhos['metadados'].read_text(encoding='utf-8'))

    alterado = {**base, 'parquet_sha256': 'd' * 64}
    with pytest.raises(ValueError, match='contrato'):
        tp.validar_contrato_cache(base, alterado)
    assert tp.carregar_cache_propensity(tmp_path, alterado) is None


def test_perfis_fora_de_suporte_sao_agregados_sem_registros_individuais():
    import numpy as np

    dados = _dados_diagnostico_temporal()
    propensity = np.array([0.001, 0.02, 0.50, 0.97, 0.999, 0.60, 0.40, 0.80])
    perfis = tp.perfis_fora_suporte(dados, propensity, 2018)
    assert set(perfis.faixa) == {'fora_001_099', 'fora_005_095'}
    assert set(perfis.perfil) == {
        'UF_RESIDENCIA', 'FAIXA_IDADE_MAE', 'ESCOLARIDADE_MAE', 'RACA_COR_MAE', 'PARIDADE_CAT'}
    assert {'ano', 'faixa', 'perfil', 'categoria', 'n', 'n_t0', 'n_t1', 'proporcao_no_perfil'} <= set(perfis)
    assert 'contador' not in perfis.columns


def test_recortes_principal_e_sensibilidade_reutilizam_os_mesmos_resultados_anuais():
    import pandas as pd

    tabela = pd.DataFrame({'ano': range(2014, 2025), 'auc_oof': range(11)})
    recortes = tp.recortar_janelas(tabela)
    assert recortes['principal'].ano.tolist() == list(range(2014, 2025))
    assert recortes['sensibilidade'].ano.tolist() == list(range(2018, 2025))
    assert recortes['sensibilidade'].set_index('ano').auc_oof.equals(
        tabela[tabela.ano >= 2018].set_index('ano').auc_oof)


def test_notebook_08_tem_contrato_diagnostico_e_nao_estima_efeitos_causais():
    import nbformat
    import re

    caminho = RAIZ_REAL / 'notebooks/historico/08_estabilidade_temporal_overlap.ipynb'
    assert caminho.exists()
    nb = nbformat.read(caminho, as_version=4)
    nbformat.validate(nb)
    fonte = '\n'.join(c.source for c in nb.cells)
    for secao in ('controle positivo 2024', 'SMD intra-ano', 'composiÃ§Ã£o versus 2024',
                  'sensibilidade 2018â€“2024', '2021â€“2022', 'critÃ©rios para o notebook 09'):
        for _ in range(3):
            try:
                reparada = secao.encode('cp1252').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                break
            if reparada == secao:
                break
            secao = reparada
        assert secao.casefold() in fonte.casefold()
    codigo = '\n'.join(c.source for c in nb.cells if c.cell_type == 'code')
    for proibido in ('calcular_aipw', 'aipw_independente', 'ajuste_honesto', 'CATE', 'pooled'):
        assert re.search(rf'\b{re.escape(proibido)}\b', codigo, flags=re.IGNORECASE) is None
