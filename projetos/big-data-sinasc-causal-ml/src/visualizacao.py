"""Tema IPT e apresentação PT-BR."""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import builtins
import re
from pathlib import Path
import pandas as pd
from IPython.display import display as _display, Markdown

CORES_IPT = {
    "AZUL_PRINCIPAL": "#00598E",
    "AZUL_ESCURO": "#133C5A",
    "CIANO": "#04B4E3",
    "AZUL_MEDIO": "#226986",
    "AZUL_CLARO": "#82B0C6",
    "BRANCO": "#FFFFFF",
    "CINZA_FUNDO": "#F5F7F9",
    "CINZA_GRADE": "#D9E7EE",
}

PALETA_IPT = [
    CORES_IPT["AZUL_PRINCIPAL"],
    CORES_IPT["CIANO"],
    CORES_IPT["AZUL_MEDIO"],
    CORES_IPT["AZUL_CLARO"],
    CORES_IPT["AZUL_ESCURO"],
]

TEMPLATE_PLOTLY_IPT = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor=CORES_IPT["BRANCO"],
        plot_bgcolor=CORES_IPT["BRANCO"],
        font={"family": "Arial", "color": CORES_IPT["AZUL_ESCURO"], "size": 13},
        colorway=PALETA_IPT,
        title={"font": {"color": CORES_IPT["AZUL_ESCURO"], "size": 20}, "x": 0.02},
        margin={"l": 65, "r": 35, "t": 75, "b": 60},
        legend={"orientation": "h", "y": -0.2, "x": 0},
        xaxis={"showline": True, "linecolor": CORES_IPT["CINZA_GRADE"], "gridcolor": CORES_IPT["CINZA_GRADE"], "zeroline": False},
        yaxis={"showline": True, "linecolor": CORES_IPT["CINZA_GRADE"], "gridcolor": CORES_IPT["CINZA_GRADE"], "zeroline": False},
    )
)

def configurar_plotly() -> None:
    """Registra e ativa o tema comum do projeto."""

    pio.templates["ipt_academico"] = TEMPLATE_PLOTLY_IPT
    pio.templates.default = "ipt_academico"
    pio.renderers.default = "png"

def aplicar_tema_base(figura: go.Figure, titulo: str | None = None) -> go.Figure:
    """Aplica o tema e um título opcional a uma figura Plotly."""

    figura.update_layout(template=TEMPLATE_PLOTLY_IPT)
    if titulo:
        figura.update_layout(title=titulo)
    return figura


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
    aplicar_tema_base(fig,traduzir(titulo))
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

def auditar_idioma(nb):
    erros=[]
    for i,c in enumerate(nb.cells):
        if c.cell_type!='markdown': continue
        texto=re.sub(r'`[^`]+`|https?://\S+','',c.source)
        for termo in TERMOS:
            if re.search(r'(?<!\w)'+re.escape(termo)+r'(?!\w)',texto,re.I): erros.append((i,termo))
    return erros
