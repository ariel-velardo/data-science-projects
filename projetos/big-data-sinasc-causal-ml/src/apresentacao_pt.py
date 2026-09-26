"""Camada de apresentação PT-BR; não altera dados ou chaves analíticas."""
import ast
import builtins
import io
import re
import tokenize
from pathlib import Path

import nbformat
import pandas as pd
from IPython.display import display as _display, Markdown
from src.visualizacao_ipt import aplicar_tema_ipt as _tema

TERMOS = {
    'tl;dr':'Resumo executivo', 'Context & Methods':'Contexto e métodos',
    'Key Assumptions':'Hipóteses principais', 'Data':'Dados',
    'Results':'Resultados', 'Takeaways':'Principais conclusões',
    'propensity score':'escore de propensão', 'propensity':'escore de propensão',
    'outcomes':'desfechos', 'outcome':'desfecho', 'treatment':'tratamento',
    'benchmark':'modelo de referência', 'overlap':'suporte comum',
    'trimming':'recorte de suporte', 'cross-fitting':'ajuste cruzado',
    'cross-fitted':'com ajuste cruzado', 'out-of-fold':'fora da partição de treino',
    'missing':'dados ausentes', 'leakage':'vazamento de informação',
    'complete-case':'somente casos completos', 'nuisances':'modelos auxiliares',
    'nuisance':'modelo auxiliar', 'baseline':'referência',
    'folds':'partições', 'fold':'partição', 'clusters':'agrupamentos', 'cluster':'agrupamento',
    'leave-one-UF-out':'exclusão de uma UF por vez', 'features':'covariáveis', 'feature':'covariável',
    'early stopping':'parada antecipada', 'tuning':'busca de hiperparâmetros',
    'negative control':'controle negativo', 'timing':'momento de ocorrência',
    'performance':'desempenho', 'schema':'estrutura de campos', 'seed':'semente',
    'split':'divisão', 'bias':'viés', 'top':'extremos', 'gate':'critério de decisão',
    'pipeline':'sequência de processamento', 'ranking':'ordenação',
    'one-hot sparse':'codificação indicadora esparsa', 'sandwich':'sanduíche',
    'proxy':'aproximação', 'provenance':'procedência',
}
TECNICOS = ('AIPW','ROC-AUC','PR-AUC','Python','scikit-learn','HistGradientBoosting',
            'SINASC','DR-Learner','CATE','ATE','bootstrap','Monte Carlo','OOF','DAG','ESS')
ROTULOS = {'sem_trimming':'Sem recorte de suporte','0.01_0.99':'Suporte 0,01–0,99',
           '0.05_0.95':'Suporte 0,05–0,95','<MISSING>':'Ausente',
           'aleatorio':'Aleatório','agrupado':'Agrupado', 'iid':'Independência individual',
           'cluster':'Agrupamento municipal','SE_boot_pp':'EP bootstrap (pp)',
           'roc_auc':'ROC-AUC','pr_auc_ap':'PR-AUC (AP)','brier':'Brier',
           'se_pp':'EP (pp)','se_iid_pp':'EP individual (pp)','se_cluster_pp':'EP municipal (pp)',
           'estimativa_pp':'Estimativa (pp)', 'n':'N','n_t1':'N tratado','n_t0':'N controle',
           'convergence_warning':'Alerta de convergência','n_iter':'Iterações'}


def traduzir(texto):
    """Traduz prosa; trechos entre crases e URLs preservam identificadores reais."""
    partes = re.split(r'(`[^`]+`|https?://\S+)', str(texto))
    for i in range(0,len(partes),2):
        for termo,pt in sorted(TERMOS.items(),key=lambda x:-len(x[0])):
            def substituir(m):
                return pt[0].upper()+pt[1:] if m[0][0].isupper() else pt
            partes[i]=re.sub(r'(?<!\w)'+re.escape(termo)+r'(?!\w)',substituir,partes[i],flags=re.I)
    return ''.join(partes)


def rotulo(valor):
    if not isinstance(valor,str): return valor
    if valor in ROTULOS: return ROTULOS[valor]
    # Colunas SINASC e identificadores de decisões históricas ficam literais.
    if valor.isupper() or '/' in valor or '\\' in valor: return traduzir(valor)
    return traduzir(valor.replace('_',' '))


def tabela_pt(tabela):
    resultado=tabela.copy()
    if isinstance(resultado.columns,pd.MultiIndex):
        resultado.columns=pd.MultiIndex.from_tuples([tuple(rotulo(v) for v in k) for k in resultado.columns],names=[rotulo(n) for n in resultado.columns.names])
    else: resultado.columns=[rotulo(c) for c in resultado.columns]
    if isinstance(resultado.index,pd.MultiIndex):
        resultado.index=pd.MultiIndex.from_tuples([tuple(rotulo(v) for v in k) for k in resultado.index],names=[rotulo(n) for n in resultado.index.names])
    else:
        resultado.index=resultado.index.map(rotulo)
        resultado.index.name=rotulo(resultado.index.name)
    for c in resultado.columns:
        if resultado[c].dtype==object or isinstance(resultado[c].dtype,pd.StringDtype):
            resultado[c]=resultado[c].map(rotulo)
    return resultado


def exibir_pt(*objetos,**kwargs):
    objetos=[tabela_pt(o) if isinstance(o,pd.DataFrame) else
             Markdown(traduzir(o.data)) if isinstance(o,Markdown) else o for o in objetos]
    return _display(*objetos,**kwargs)


def imprimir_pt(*objetos,**kwargs):
    return builtins.print(*[traduzir(o) if isinstance(o,str) else o for o in objetos],**kwargs)


def aplicar_tema_ipt(fig,titulo):
    _tema(fig,traduzir(titulo))
    for eixo in list(fig.select_xaxes())+list(fig.select_yaxes()):
        if eixo.title.text: eixo.title.text=traduzir(eixo.title.text)
        if eixo.ticktext is not None: eixo.ticktext=[rotulo(v) for v in eixo.ticktext]
    for a in fig.layout.annotations or []: a.text=traduzir(a.text)
    for tr in fig.data:
        if tr.name: tr.name=rotulo(tr.name)
        for eixo in ('x','y','text'):
            vals=getattr(tr,eixo,None)
            if vals is not None and not isinstance(vals,str) and len(vals) and isinstance(vals[0],str):
                setattr(tr,eixo,[traduzir(v.replace('sem_trimming','Sem recorte de suporte')) for v in vals])
    return fig


def preparar_notebook(nb):
    """Aplicada pelo gerador antes de gravar. Traduz só literais de prosa em código."""
    nb.metadata.kernelspec={'display_name':'Python (SINASC .venv)','language':'python','name':'python3'}
    primeira=True
    for cell in nb.cells:
        if cell.cell_type=='markdown': cell.source=traduzir(cell.source)
        elif cell.cell_type=='code':
            tokens=[]
            for tok in tokenize.generate_tokens(io.StringIO(cell.source).readline):
                if tok.type==tokenize.COMMENT:
                    tok=tok._replace(string=traduzir(tok.string))
                elif tok.type==tokenize.STRING and '\n' not in tok.string:
                    try: valor=ast.literal_eval(tok.string)
                    except (ValueError,SyntaxError): valor=None
                    # Chaves, caminhos, expressões SQL e f-strings não são reescritos.
                    if isinstance(valor,str) and ' ' in valor and not any(s in valor for s in ('SELECT ','FROM ','/','\\','<','>')):
                        tok=tok._replace(string=repr(traduzir(valor)))
                tokens.append(tok)
            cell.source=tokenize.untokenize(tokens)
            if primeira:
                # Inserção depois dos imports do tema original, antes de qualquer exibição.
                marcador='configurar_plotly()'
                acrescimo='from src.apresentacao_pt import exibir_pt as display, imprimir_pt as print, aplicar_tema_ipt\n'
                if marcador in cell.source:
                    cell.source=cell.source.replace(marcador,acrescimo+marcador,1)
                primeira=False
    return nb


def auditar_idioma(nb):
    erros=[]
    for i,c in enumerate(nb.cells):
        if c.cell_type!='markdown': continue
        texto=re.sub(r'`[^`]+`|https?://\S+','',c.source)
        for termo in TERMOS:
            if re.search(r'(?<!\w)'+re.escape(termo)+r'(?!\w)',texto,re.I): erros.append((i,termo))
    return erros


if __name__=='__main__':
    for p in sorted((Path(__file__).resolve().parents[1]/'notebooks').glob('*.ipynb')):
        erros=auditar_idioma(nbformat.read(p,as_version=4))
        if erros: raise ValueError(f'{p.name}: {erros}')
        builtins.print(p.name, 'PT-BR aprovado')
