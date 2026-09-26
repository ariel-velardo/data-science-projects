import nbformat
import pandas as pd
import pytest
from src.apresentacao_pt import traduzir, preparar_notebook, tabela_pt, auditar_idioma


def test_traduz_narrativa_preserva_tecnica():
    assert traduzir('Context & Methods') == 'Contexto e métodos'
    assert traduzir('AIPW ROC-AUC Python scikit-learn HistGradientBoosting SINASC') == 'AIPW ROC-AUC Python scikit-learn HistGradientBoosting SINASC'
    assert traduzir('outcome e propensity score') == 'desfecho e escore de propensão'


def test_tabela_so_apresentacao():
    original = pd.DataFrame({'populacao':['sem_trimming'], 'estimativa_pp':[-1.231456]})
    exibida = tabela_pt(original)
    assert exibida.iloc[0,1] == original.iloc[0,1]
    assert original.iloc[0,0] == 'sem_trimming'
    assert exibida.iloc[0,0] == 'Sem recorte de suporte'


def test_auditoria_bloqueia_ingles_narrativo():
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell('## Outcome\n\nAIPW, Python e SINASC')])
    assert auditar_idioma(nb)
    preparar_notebook(nb)
    assert not auditar_idioma(nb)


def test_chaves_codigo_nao_traduzidas():
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("a = dados['outcome']; x = 'sem_trimming'\nprint('Outcome observado:')")])
    preparar_notebook(nb)
    assert "dados['outcome']" in nb.cells[0].source
    assert "x = 'sem_trimming'" in nb.cells[0].source
    assert 'Desfecho observado:' in nb.cells[0].source


def test_guarda_historica_recusa_dados_alterados(tmp_path):
    from src.valida_apresentacao import verificar_preservacao
    with pytest.raises(ValueError):
        verificar_preservacao(tmp_path,{'dados':'novo'},{'dados':'original'})


def test_fontes_notebook_independentes_de_metadados(tmp_path):
    from src.valida_apresentacao import hash_fontes_notebook
    nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('x = 1')])
    p=tmp_path/'n.ipynb'; nbformat.write(nb,p); antes=hash_fontes_notebook(p)
    nb.cells[0].execution_count=3; nb.cells[0].id='outro-id'; nbformat.write(nb,p)
    assert hash_fontes_notebook(p)==antes
    nb.cells[0].source='x = 2'; nbformat.write(nb,p)
    assert hash_fontes_notebook(p)!=antes


def test_figura_preserva_valores():
    import plotly.graph_objects as go
    from src.apresentacao_pt import aplicar_tema_ipt
    fig=go.Figure(go.Bar(x=['sem_trimming'],y=[-1.23],name='cluster'))
    fig.update_yaxes(title='Outcome')
    aplicar_tema_ipt(fig,'Cross-fitting')
    assert list(fig.data[0].y)==[-1.23]
    assert fig.layout.title.text=='Ajuste cruzado'
    assert fig.layout.yaxis.title.text=='Desfecho'
