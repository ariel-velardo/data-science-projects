import nbformat
import pandas as pd
import pytest
from src.visualizacao import traduzir, tabela_pt, auditar_idioma


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
    nb.cells[0].source = traduzir(nb.cells[0].source)
    assert not auditar_idioma(nb)


def test_notebooks_fonte_preservam_codigo_e_idioma():
    from pathlib import Path
    for p in Path('notebooks').glob('0[1-5]*.ipynb'):
        nb = nbformat.read(p, as_version=4)
        assert not auditar_idioma(nb)
        assert any(c.cell_type == 'code' for c in nb.cells)
        for c in nb.cells:
            if c.cell_type == 'code':
                compile(c.source, str(p), 'exec')


def test_guarda_historica_recusa_dados_alterados(tmp_path):
    from src.validacao import verificar_preservacao
    with pytest.raises(ValueError):
        verificar_preservacao(tmp_path,{'dados':'novo'},{'dados':'original'})


def test_fontes_notebook_independentes_de_metadados(tmp_path):
    from src.validacao import hash_fontes_notebook
    nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('x = 1')])
    p=tmp_path/'n.ipynb'; nbformat.write(nb,p); antes=hash_fontes_notebook(p)
    nb.cells[0].execution_count=3; nb.cells[0].id='outro-id'; nbformat.write(nb,p)
    assert hash_fontes_notebook(p)==antes
    nb.cells[0].source='x = 2'; nbformat.write(nb,p)
    assert hash_fontes_notebook(p)!=antes


def test_figura_preserva_valores():
    import plotly.graph_objects as go
    from src.visualizacao import aplicar_tema_ipt
    fig=go.Figure(go.Bar(x=['sem_trimming'],y=[-1.23],name='cluster'))
    fig.update_yaxes(title='Outcome')
    aplicar_tema_ipt(fig,'Cross-fitting')
    assert list(fig.data[0].y)==[-1.23]
    assert fig.layout.title.text=='Ajuste cruzado'
    assert fig.layout.yaxis.title.text=='Desfecho'
