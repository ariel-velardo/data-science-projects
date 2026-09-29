"""Contratos da entrega: detectar divergência, links quebrados e exposição indevida."""
import pytest

from src.validacao import verificar_metricas, links_quebrados, validar_dicionario


def test_detecta_numero_publicado_divergente():
    with pytest.raises(ValueError, match='n'):
        verificar_metricas('<span data-metrica="n">123</span>', {'n': '124'})


def test_exige_metrica_ausente():
    with pytest.raises(ValueError, match='ausente'):
        verificar_metricas('Sem número', {'n': '124'})


def test_aceita_numero_correto():
    verificar_metricas('<span data-metrica="n">2.251.570</span>', {'n': '2.251.570'})


def test_links_relativos_e_ancoras(tmp_path):
    p = tmp_path / 'pagina.md'
    p.write_text('[ok](alvo.md#secao) [erro](ausente.md) [web](https://example.org)', encoding='utf-8')
    (tmp_path / 'alvo.md').write_text('# Seção\n', encoding='utf-8')
    assert links_quebrados(p) == ['ausente.md']


def test_dicionario_rejeita_duplicata_e_omissao():
    with pytest.raises(ValueError):
        validar_dicionario([{'nome': 'A'}, {'nome': 'A'}], ['A', 'B'])


def test_dicionario_preserva_ordem_e_cobertura():
    validar_dicionario([{'nome': 'A'}, {'nome': 'B'}], ['A', 'B'])


def test_detecta_ancora_inexistente(tmp_path):
    p = tmp_path / 'pagina.md'
    p.write_text('[ruim](alvo.md#nao-existe)', encoding='utf-8')
    (tmp_path / 'alvo.md').write_text('# Seção\n', encoding='utf-8')
    assert links_quebrados(p) == ['alvo.md#nao-existe']


def test_links_em_bloco_codigo_sao_dados_mas_links_renderizados_sao_validados(tmp_path):
    p = tmp_path / 'baseline.md'
    p.write_text('```json\n{"fonte": "[histórico](ausente.md)"}\n```\n'
                 '[navegável](tambem-ausente.md)\n', encoding='utf-8')
    assert links_quebrados(p) == ['tambem-ausente.md']
