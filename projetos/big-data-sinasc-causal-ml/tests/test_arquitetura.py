"""Contratos da migração: CLIs separadas e preservação sem reajuste."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ_REAL = Path(__file__).resolve().parents[1]
MANIFESTO = 'docs/architecture/preservacao_refatoracao.json'
SOURCE_MANIFEST = 'data/raw/source_manifest.json'


def _atributo_git(caminho, atributo):
    resultado = subprocess.run(
        ['git', 'check-attr', atributo, '--', caminho],
        cwd=RAIZ_REAL,
        check=True,
        capture_output=True,
        text=True,
    )
    return resultado.stdout.rstrip().rsplit(': ', 1)[-1]


@pytest.mark.parametrize('caminho', [
    'src/validacao.py',
    'docs/architecture/CERTIFICACAO_REFATORACAO.md',
    'outputs/diagnostics/fase4_resultados.json',
    'notebooks/05_heterogeneidade_causal.ipynb',
    'outputs/tables/distribuicao_peso_250g.csv',
    'outputs/tables/histograma_propensity.csv',
    SOURCE_MANIFEST,
])
def test_politica_eol_fixa_crlf_para_artefatos_ancorados(caminho):
    assert _atributo_git(caminho, 'text') == 'set'
    assert _atributo_git(caminho, 'eol') == 'crlf'


@pytest.mark.parametrize('caminho', [
    'data/raw/.gitkeep',
    'docs/methodology/PLANO_ESTIMACAO_FASE2.md',
    'docs/methodology/RESULTADOS_E_LIMITACOES_FASE2.md',
    'outputs/diagnostics/VALIDACAO_FASE2.md',
    'outputs/diagnostics/fase3_gate.json',
])
def test_politica_eol_preserva_excecoes_lf(caminho):
    assert _atributo_git(caminho, 'text') == 'set'
    assert _atributo_git(caminho, 'eol') == 'lf'


def test_validacao_nao_tem_eol_misto():
    dados = (RAIZ_REAL / 'src/validacao.py').read_bytes()
    sem_crlf = dados.replace(b'\r\n', b'')
    assert b'\n' not in sem_crlf
    assert b'\r' not in sem_crlf


@pytest.mark.parametrize('etapa', ['dados', 'amostra', 'preditivo', 'causal', 'robustez', 'heterogeneidade'])
def test_pipeline_despacha_somente_etapa_solicitada(etapa):
    from scripts.executar_pipeline import executar_etapa
    chamadas = []
    acoes = {nome: lambda nome=nome: chamadas.append(nome) for nome in
             ['dados', 'amostra', 'preditivo', 'causal', 'robustez', 'heterogeneidade']}
    executar_etapa(etapa, acoes)
    assert chamadas == [etapa]


def test_pipeline_rejeita_etapa_desconhecida():
    from scripts.executar_pipeline import executar_etapa
    with pytest.raises(ValueError):
        executar_etapa('temporal', {})


def test_contrato_cache_rejeita_dados_alterados():
    from src.validacao import conferir_contrato
    with pytest.raises(ValueError, match='contrato'):
        conferir_contrato(Path('.'), {'n': 10, 'codigo': {}}, {'n': 11, 'codigo': {}})


def test_hash_codigo_sem_manifesto_nao_aceita_mudanca(tmp_path):
    from src.validacao import verificar_codigo
    (tmp_path / 'src').mkdir()
    p = tmp_path / 'src/modelo.py'
    p.write_text('modelo original', encoding='utf-8')
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    verificar_codigo(tmp_path, {'modelo.py': h})
    p.write_text('modelo alterado', encoding='utf-8')
    with pytest.raises(ValueError):
        verificar_codigo(tmp_path, {'modelo.py': h})


def test_validacao_notebooks_exige_cinco_fontes(tmp_path):
    from src.validacao import validar_notebooks
    (tmp_path / 'notebooks').mkdir()
    with pytest.raises(ValueError, match='cinco'):
        validar_notebooks(tmp_path)


def test_validacao_rapida_nao_chama_modelagem(monkeypatch):
    import src.validacao as v
    chamadas = []
    for nome in ['validar_entrega', 'validar_apresentacao', 'validar_notebooks',
                 'validar_imports', 'validar_preservacao_refatoracao', 'validar_gates']:
        monkeypatch.setattr(v, nome, lambda *a, nome=nome, **k: chamadas.append(nome))
    v.validar_projeto(completa=False)
    assert chamadas == ['validar_imports', 'validar_preservacao_refatoracao',
                        'validar_gates', 'validar_notebooks', 'validar_apresentacao', 'validar_entrega']


# --- Allowlist de normalização EOL (path-scoped, não por extensão) ---

CAMINHOS_EOL = [
    'data/raw/.gitkeep',
    'docs/methodology/PLANO_ESTIMACAO_FASE2.md',
    'docs/methodology/RESULTADOS_E_LIMITACOES_FASE2.md',
    'outputs/diagnostics/VALIDACAO_FASE2.md',
]


def test_allowlist_eol_e_exatamente_os_quatro_caminhos():
    """TESTE I: a allowlist não foi ampliada."""
    from src.validacao import CAMINHOS_NORMALIZAR_EOL
    assert CAMINHOS_NORMALIZAR_EOL == frozenset(CAMINHOS_EOL)


@pytest.mark.parametrize('caminho', CAMINHOS_EOL)
def test_sha256_preservacao_normaliza_apenas_allowlist_eol(tmp_path, caminho):
    """TESTE I: um caminho autorizado com CRLF bate no hash calculado sobre LF."""
    from src.validacao import sha256_preservacao
    p = tmp_path / caminho
    p.parent.mkdir(parents=True, exist_ok=True)
    conteudo_lf = b'linha 1\nlinha 2\n'
    hash_lf = hashlib.sha256(conteudo_lf).hexdigest()
    p.write_bytes(conteudo_lf.replace(b'\n', b'\r\n'))
    assert sha256_preservacao(tmp_path, caminho) == hash_lf


@pytest.mark.parametrize('caminho', CAMINHOS_EOL)
def test_sha256_preservacao_detecta_alteracao_real_em_caminho_eol(tmp_path, caminho):
    """TESTE I: alterar um caractere real (não EOL) muda o hash normalizado."""
    from src.validacao import sha256_preservacao
    p = tmp_path / caminho
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b'linha 1\r\nlinha 2\r\n')
    hash_original = sha256_preservacao(tmp_path, caminho)
    p.write_bytes(b'linha 1\r\nlinha 2 alterada\r\n')
    assert sha256_preservacao(tmp_path, caminho) != hash_original


def test_sha256_preservacao_nao_normaliza_arquivo_fora_da_allowlist(tmp_path):
    """TESTE J: outro .md (mesma pasta) continua byte-a-byte."""
    from src.validacao import sha256_preservacao
    caminho = 'docs/methodology/OUTRO_DOCUMENTO.md'
    p = tmp_path / caminho
    p.parent.mkdir(parents=True, exist_ok=True)
    conteudo_lf = b'linha 1\nlinha 2\n'
    hash_lf = hashlib.sha256(conteudo_lf).hexdigest()
    hash_crlf_bruto = hashlib.sha256(conteudo_lf.replace(b'\n', b'\r\n')).hexdigest()
    p.write_bytes(conteudo_lf.replace(b'\n', b'\r\n'))
    atual = sha256_preservacao(tmp_path, caminho)
    assert atual == hash_crlf_bruto
    assert atual != hash_lf


def test_sha256_preservacao_binario_continua_estrito(tmp_path):
    """TESTE K: binário com \\r\\n incidental continua byte-a-byte."""
    from src.validacao import sha256_preservacao
    caminho = 'data/processed/exemplo.parquet'
    p = tmp_path / caminho
    p.parent.mkdir(parents=True, exist_ok=True)
    dados_binarios = b'\x00\x01\r\n\x02\xff\r\n\x03'
    p.write_bytes(dados_binarios)
    assert sha256_preservacao(tmp_path, caminho) == hashlib.sha256(dados_binarios).hexdigest()


# --- Exceção histórica do source_manifest: âncora em código + blob Git ---

def _copiar(raiz, *caminhos):
    for rel in caminhos:
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RAIZ_REAL / rel, raiz / rel)


def _editar_json(raiz, alterar):
    p = raiz / MANIFESTO
    m = json.loads(p.read_text(encoding='utf-8'))
    alterar(m)
    p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')


def _aceita(raiz, nome=SOURCE_MANIFEST, esperado=None):
    from src.validacao import EXCECAO_SOURCE_MANIFEST, _excecao_historica
    return _excecao_historica(raiz, nome, esperado or EXCECAO_SOURCE_MANIFEST['hash_baseline_nao_reproduzido'])


@pytest.fixture
def repo_sm(tmp_path, monkeypatch):
    """Cópia do source_manifest e do JSON reais; o Git é lido do repositório real,
    de modo que qualquer falha nos testes decorre só da mutação aplicada."""
    import src.validacao as v
    _copiar(tmp_path, SOURCE_MANIFEST, MANIFESTO)
    original = v._ler_referencia_git
    monkeypatch.setattr(v, '_ler_referencia_git', lambda raiz, commit, caminho: original(RAIZ_REAL, commit, caminho))
    assert _aceita(tmp_path) is True  # controle positivo
    return tmp_path


def test_excecao_historica_real_ancorada_no_blob_git():
    """Repositório real: âncora em código, commit fixo ancestral e blob coincidem."""
    from src.validacao import EXCECAO_SOURCE_MANIFEST, _ler_referencia_git
    a = EXCECAO_SOURCE_MANIFEST
    ref = _ler_referencia_git(RAIZ_REAL, a['commit_git'], SOURCE_MANIFEST)
    assert ref['ancestral'] and ref['oid'] == a['blob_git']
    assert hashlib.sha256(ref['dados']).hexdigest() == a['hash_git_acessivel']
    assert _aceita(RAIZ_REAL) is True


def test_a_alterar_so_source_manifest_falha(repo_sm):
    with open(repo_sm / SOURCE_MANIFEST, 'ab') as f:
        f.write(b' ')
    assert _aceita(repo_sm) is False


def test_b_alterar_so_registro_da_excecao_falha(repo_sm):
    _editar_json(repo_sm, lambda m: m['excecoes_historicas'][SOURCE_MANIFEST].update(
        hash_atual_aprovado='0' * 64))
    assert _aceita(repo_sm) is False


def test_c_alterar_source_manifest_e_registro_juntos_falha(repo_sm):
    """ATAQUE 1: bytes novos + hashes do JSON reescritos para os bytes novos."""
    alvo = repo_sm / SOURCE_MANIFEST
    novo = alvo.read_bytes().replace(b'SINASC', b'SINASX', 1)
    alvo.write_bytes(novo)
    _editar_json(repo_sm, lambda m: m['excecoes_historicas'][SOURCE_MANIFEST].update(
        hash_atual_aprovado=hashlib.sha256(novo).hexdigest(),
        hash_git_acessivel=hashlib.sha256(novo.replace(b'\r\n', b'\n')).hexdigest()))
    assert _aceita(repo_sm) is False


def test_d_mover_registro_e_arquivo_para_outro_caminho_falha(repo_sm):
    outro = 'data/raw/outro_manifest.json'
    shutil.copyfile(repo_sm / SOURCE_MANIFEST, repo_sm / outro)
    _editar_json(repo_sm, lambda m: m['excecoes_historicas'].update(
        {outro: m['excecoes_historicas'].pop(SOURCE_MANIFEST)}))
    assert _aceita(repo_sm, nome=outro) is False


def test_e_alterar_baseline_esperado_falha(repo_sm):
    _editar_json(repo_sm, lambda m: m['excecoes_historicas'][SOURCE_MANIFEST].update(
        hash_baseline_nao_reproduzido='1' * 64))
    assert _aceita(repo_sm) is False
    assert _aceita(repo_sm, esperado='1' * 64) is False


@pytest.mark.parametrize('campo', ['hash_git_acessivel', 'blob_git', 'commit_git'])
def test_f_alterar_referencia_git_declarada_no_json_falha(repo_sm, campo):
    _editar_json(repo_sm, lambda m: m['excecoes_historicas'][SOURCE_MANIFEST].update({campo: 'f' * 40}))
    assert _aceita(repo_sm) is False


@pytest.mark.parametrize('referencia', [
    None,
    {'ancestral': False},
    {'oid': '0' * 40},
    {'dados': b'{"outro": "conteudo"}\n'},
])
def test_g_referencia_git_divergente_da_ancora_falha(repo_sm, monkeypatch, referencia):
    import src.validacao as v
    real = v._ler_referencia_git(repo_sm, v.EXCECAO_SOURCE_MANIFEST['commit_git'], SOURCE_MANIFEST)
    falsa = None if referencia is None else {**real, **referencia}
    monkeypatch.setattr(v, '_ler_referencia_git', lambda *a: falsa)
    assert _aceita(repo_sm) is False


def test_h_excecao_so_vale_para_source_manifest(repo_sm):
    shutil.copyfile(repo_sm / SOURCE_MANIFEST, repo_sm / 'data/raw/.gitkeep')
    _editar_json(repo_sm, lambda m: m['excecoes_historicas'].update(
        {'data/raw/.gitkeep': m['excecoes_historicas'][SOURCE_MANIFEST]}))
    assert _aceita(repo_sm, nome='data/raw/.gitkeep') is False
    baseline = json.loads((RAIZ_REAL / 'docs/architecture/BASELINE_PRE_REFATORACAO.md').read_text(
        encoding='utf-8').split('```json\n', 1)[1].split('\n```', 1)[0])['hashes']
    outros = [h for n, h in baseline.items() if n != SOURCE_MANIFEST]
    assert not any(_aceita(repo_sm, esperado=h) for h in outros)


def test_git_indisponivel_falha_fechado(tmp_path):
    """Sem repositório Git a exceção não é aceita (falha fechada)."""
    _copiar(tmp_path, SOURCE_MANIFEST, MANIFESTO)
    assert _aceita(tmp_path) is False


# --- Histórico de migração + cadeia de evoluções autorizadas ---

REGISTRO_VALIDACAO = 'src/valida_apresentacao.py'
HASH_DESTINO_HISTORICO = 'c00d1d79dd9d20f225e40c9c8ba27e18ee204b2644ccf3f30c9cdcf28afacd78'


def _migracao(raiz):
    from src.validacao import _excecao_refatoracao, _manifesto_refatoracao
    registro = _manifesto_refatoracao(raiz)['migracoes'][REGISTRO_VALIDACAO]
    return _excecao_refatoracao(raiz, REGISTRO_VALIDACAO, registro['hashes_anteriores'][0])


@pytest.fixture
def repo_mig(tmp_path):
    _copiar(tmp_path, MANIFESTO, 'src/validacao.py')
    assert _migracao(tmp_path) is True  # controle positivo
    return tmp_path


def _alterar_validacao(raiz):
    p = raiz / 'src/validacao.py'
    p.write_bytes(p.read_bytes() + b'# alteracao nao autorizada\r\n')
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_destinos_historicos_de_validacao_preservados():
    from src.validacao import _manifesto_refatoracao
    m = _manifesto_refatoracao(RAIZ_REAL)
    destinos = [r['destinos']['src/validacao.py'] for r in m['migracoes'].values()
                if 'src/validacao.py' in r['destinos']]
    assert destinos == [HASH_DESTINO_HISTORICO] * 6


def test_cadeia_real_de_validacao_termina_nos_bytes_atuais():
    from src.validacao import _manifesto_refatoracao, cadeia_evolucao_valida, sha256
    m = _manifesto_refatoracao(RAIZ_REAL)
    atual = sha256(RAIZ_REAL / 'src/validacao.py')
    assert m['codigo_atual']['src/validacao.py'] == atual
    assert cadeia_evolucao_valida(m['evolucoes_autorizadas'], 'src/validacao.py', HASH_DESTINO_HISTORICO, atual)


def test_l_alterar_validacao_sem_evolucao_falha(repo_mig):
    _alterar_validacao(repo_mig)
    with pytest.raises(ValueError, match='Destino da migração alterado'):
        _migracao(repo_mig)


def test_m_alterar_validacao_e_codigo_atual_falha(repo_mig):
    novo = _alterar_validacao(repo_mig)
    _editar_json(repo_mig, lambda m: m['codigo_atual'].update({'src/validacao.py': novo}))
    with pytest.raises(ValueError, match='Destino da migração alterado'):
        _migracao(repo_mig)


def test_n_reescrever_destinos_historicos_falha(repo_mig):
    """ATAQUE 2: arquivo + codigo_atual + destinos históricos reescritos juntos."""
    novo = _alterar_validacao(repo_mig)

    def reescrever(m):
        m['codigo_atual']['src/validacao.py'] = novo
        for r in m['migracoes'].values():
            if 'src/validacao.py' in r['destinos']:
                r['destinos']['src/validacao.py'] = novo
    _editar_json(repo_mig, reescrever)
    with pytest.raises(ValueError, match='Histórico de migrações alterado'):
        _migracao(repo_mig)


def test_cadeia_que_omite_prefixo_ancorado_falha(repo_mig):
    """Reescrever a cadeia pulando os estados já ancorados em código falha."""
    atual = hashlib.sha256((repo_mig / 'src/validacao.py').read_bytes()).hexdigest()
    _editar_json(repo_mig, lambda m: m['evolucoes_autorizadas'].update(
        {'src/validacao.py': [{'hash_anterior': HASH_DESTINO_HISTORICO, 'hash_novo': atual}]}))
    with pytest.raises(ValueError, match='Destino da migração alterado'):
        _migracao(repo_mig)


def _passos(*pares):
    return {'src/x.py': [{'hash_anterior': a, 'hash_novo': b} for a, b in pares]}


def test_o_evolucao_sem_ancora_falha():
    from src.validacao import cadeia_evolucao_valida
    assert not cadeia_evolucao_valida(_passos(('A', 'B')), 'src/x.py', 'A', 'B')
    assert not cadeia_evolucao_valida(_passos(('A', 'B'), ('B', 'C')), 'src/x.py', 'A', 'C')


def test_p_cadeia_quebrada_falha():
    from src.validacao import EVOLUCOES_ANCORADAS, cadeia_evolucao_valida
    assert not cadeia_evolucao_valida(_passos(('A', 'B'), ('C', 'D')), 'src/x.py', 'A', 'D')
    assert not cadeia_evolucao_valida(_passos(('X', 'B')), 'src/x.py', 'A', 'B')
    a, b, c, d = EVOLUCOES_ANCORADAS['src/validacao.py']
    passos = {'src/validacao.py': [
        {'hash_anterior': a, 'hash_novo': b},
        {'hash_anterior': 'quebra', 'hash_novo': c},
        {'hash_anterior': c, 'hash_novo': d},
        {'hash_anterior': d, 'hash_novo': 'final'},
    ]}
    assert not cadeia_evolucao_valida(passos, 'src/validacao.py', a, 'final')


def test_q_evolucao_que_nao_termina_nos_bytes_reais_falha():
    from src.validacao import EVOLUCOES_ANCORADAS, cadeia_evolucao_valida
    assert not cadeia_evolucao_valida(_passos(('A', 'B')), 'src/x.py', 'A', 'Z')
    assert not cadeia_evolucao_valida(_passos(), 'src/x.py', 'A', 'A')
    assert not cadeia_evolucao_valida(_passos(('A', 'B'), ('B', 'A'), ('A', 'C')), 'src/x.py', 'A', 'C')
    a, b, c, d = EVOLUCOES_ANCORADAS['src/validacao.py']
    passos = {'src/validacao.py': [
        {'hash_anterior': a, 'hash_novo': b},
        {'hash_anterior': b, 'hash_novo': c},
        {'hash_anterior': c, 'hash_novo': d},
        {'hash_anterior': d, 'hash_novo': 'hash_documentado'},
    ]}
    assert not cadeia_evolucao_valida(passos, 'src/validacao.py', a, 'hash_real_diferente')
    passos['src/validacao.py'][-1]['hash_novo'] = a
    assert not cadeia_evolucao_valida(passos, 'src/validacao.py', a, a)


@pytest.mark.parametrize('destino', [
    'src/robustez.py', 'src/heterogeneidade.py', 'src/inferencia_causal.py',
])
@pytest.mark.parametrize('com_evolucao', [False, True])
def test_modulo_cientifico_e_codigo_atual_nao_criam_autoridade(tmp_path, destino, com_evolucao):
    from src.validacao import _excecao_refatoracao
    _copiar(tmp_path, MANIFESTO, destino)
    m = json.loads((tmp_path / MANIFESTO).read_text(encoding='utf-8'))
    origem = next(k for k, r in m['migracoes'].items()
                  if list(r['destinos']) == [destino])
    historico = m['migracoes'][origem]['hashes_anteriores'][0]
    alvo = tmp_path / destino
    alvo.write_bytes(alvo.read_bytes() + b'\n# ataque\n')
    novo = hashlib.sha256(alvo.read_bytes()).hexdigest()

    def alterar(registro):
        registro['codigo_atual'][destino] = novo
        if com_evolucao:
            registro['evolucoes_autorizadas'][destino] = [{
                'hash_anterior': registro['migracoes'][origem]['destinos'][destino],
                'hash_novo': novo,
            }]

    _editar_json(tmp_path, alterar)
    mensagem = 'sem âncora' if com_evolucao else 'Destino da migração alterado'
    with pytest.raises(ValueError, match=mensagem):
        _excecao_refatoracao(tmp_path, origem, historico)


def test_novo_caminho_na_lista_de_evolucoes_falha(tmp_path):
    from src.validacao import _validar_evolucoes_documentadas
    _copiar(tmp_path, MANIFESTO)
    _editar_json(tmp_path, lambda m: m['evolucoes_autorizadas'].update({
        'src/novo.py': [{'hash_anterior': 'A', 'hash_novo': 'B'}]}))
    m = json.loads((tmp_path / MANIFESTO).read_text(encoding='utf-8'))
    with pytest.raises(ValueError, match='sem âncora'):
        _validar_evolucoes_documentadas(m)


def test_codigo_atual_inteiro_adulterado_no_json_falha():
    from src.validacao import _validar_codigo_atual_ancorado
    m = json.loads((RAIZ_REAL / MANIFESTO).read_text(encoding='utf-8'))
    _validar_codigo_atual_ancorado(m)
    m['codigo_atual'] = {k: '0' * 64 for k in m['codigo_atual']}
    with pytest.raises(ValueError, match='codigo_atual'):
        _validar_codigo_atual_ancorado(m)


def test_codigo_atual_exige_entrada_do_validador():
    from src.validacao import _validar_codigo_atual_ancorado
    m = json.loads((RAIZ_REAL / MANIFESTO).read_text(encoding='utf-8'))
    m['codigo_atual'].pop('src/validacao.py')
    with pytest.raises(ValueError, match='codigo_atual'):
        _validar_codigo_atual_ancorado(m)


def test_baseline_e_json_alterados_juntos_falham(tmp_path):
    from src.validacao import _validar_baseline_ancorado
    _copiar(tmp_path, MANIFESTO, 'docs/architecture/BASELINE_PRE_REFATORACAO.md')
    alvo = tmp_path / 'docs/architecture/BASELINE_PRE_REFATORACAO.md'
    alvo.write_bytes(alvo.read_bytes() + b'\n')
    _editar_json(tmp_path, lambda m: m.update(
        baseline_sha256=hashlib.sha256(alvo.read_bytes()).hexdigest()))
    m = json.loads((tmp_path / MANIFESTO).read_text(encoding='utf-8'))
    with pytest.raises(ValueError, match='Baseline'):
        _validar_baseline_ancorado(tmp_path, m)


@pytest.mark.parametrize('destino', [
    'outputs/tables/distribuicao_peso_250g.csv',
    'outputs/tables/histograma_propensity.csv',
])
def test_csv_e_json_alterados_juntos_falham(tmp_path, destino):
    from src.validacao import _validar_csvs_promovidos
    _copiar(tmp_path, MANIFESTO, destino)
    alvo = tmp_path / destino
    alvo.write_bytes(alvo.read_bytes() + b'\n')
    _editar_json(tmp_path, lambda m: m['artefatos_reconstruidos_promovidos'][destino].update(
        sha256=hashlib.sha256(alvo.read_bytes()).hexdigest()))
    m = json.loads((tmp_path / MANIFESTO).read_text(encoding='utf-8'))
    with pytest.raises(ValueError, match='CSV promovido'):
        _validar_csvs_promovidos(tmp_path, m)
