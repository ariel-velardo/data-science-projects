"""Notebook didático com resultados persistidos da execução integral."""
from pathlib import Path
import nbformat as nbf


def criar_notebook(destino):
    nb = nbf.v4.new_notebook()
    nb.metadata.kernelspec = {'display_name': 'Python (SINASC Fase 2)', 'language': 'python', 'name': 'sinasc-fase1'}
    nb.metadata.language_info = {'name': 'python', 'version': '3.11'}
    cells = []
    def md(texto):
        cells.append(nbf.v4.new_markdown_cell(texto))
    def code(texto):
        cells.append(nbf.v4.new_code_cell(texto))
    md('''# SINASC 2024 — ML preditivo e AIPW

## 1. Perguntas da Fase 2

**Predição:** quem apresenta maior risco de baixo peso?

**Causal:** qual a diferença média de risco sob início precoce versus tardio, sob as hipóteses observacionais?

Este exercício compara duas perguntas distintas. Os resultados causais são condicionais a hipóteses fortes e não provam causalidade.
''')
    code('''from pathlib import Path
import json
import sys
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
from IPython.display import display, Markdown, Image

raiz = next(p for p in (Path.cwd(), Path.cwd().parent) if (p/'src').exists()).resolve()
sys.path.insert(0, str(raiz))
from src.visualizacao_ipt import aplicar_tema_ipt, configurar_plotly
configurar_plotly()
pio.renderers.default = 'png'
pasta = raiz/'outputs/diagnostics'
pred = json.loads((pasta/'fase2_modelagem_preditiva.json').read_text(encoding='utf-8'))
causal = json.loads((pasta/'fase2_aipw.json').read_text(encoding='utf-8'))
sens = json.loads((pasta/'fase2_sensibilidades.json').read_text(encoding='utf-8'))
assert causal['provenance']['n'] == pred['n'] == 2251570
assert causal['efeito_causal_estimado'] and not causal['causalidade_provada']
assert sum(f['n_validacao'] for f in causal['folds']) == pred['n']
assert all(f['intersecao'] == 0 for f in causal['folds'])

def mostrar(fig, titulo, arquivo):
    aplicar_tema_ipt(fig, titulo)
    fig.update_layout(width=1100, height=650, margin=dict(l=100, r=50, t=90, b=100))
    fig.update_yaxes(automargin=True)
    fig.write_html(raiz/'outputs/figures'/arquivo, include_plotlyjs=True)
    png = (raiz/'outputs/figures'/arquivo).with_suffix('.png')
    fig.write_image(png)
    display(Image(filename=str(png)))

print('Resultados da amostra integral; recalcular na .venv com: python -m src.executa_fase2')
print('Gate:', causal['gate'])
''')
    md('''## Síntese dos resultados executados

A discriminação preditiva foi limitada (ROC-AUC 0,574 logística; 0,583 HGB), com calibração por decis próxima da diagonal. AIPW: C1 −1,341 pp e C2 −1,231 pp; as sensibilidades de suporte mudaram pouco os valores.

O gate conservador é **RESULTADO_NAO_INTERPRETAVEL**: os 1% maiores |IF| concentram 78,8% de IF², acima do limite pré-especificado de 50%. Esse limiar do exercício não é um teste universal de invalidade. A contribuição individual máxima é ~0,0015 pp e o ESS dos controles ~232.772; estes contrapontos e a estabilidade numérica também devem ser considerados na revisão. Não afirmar causalidade provada.
''')
    md('''## 2. População congelada

SINASC 2024: gestações únicas, peso 500–6.000 g, mês de início do pré-natal válido. O checkpoint da Fase 1 está documentado no plano. Sem exclusão complete-case e sem trimming oculto.

## 3. X, T e Y

T=1: meses 1–3; T=0: meses 4–9. Y=1: peso <2.500 g.

X: idade, escolaridade, raça/cor, situação conjugal, paridade, perdas fetais e UF maternas. Números de consultas, idade gestacional, parto, Apgar e estabelecimento ficam fora do ajuste.
''')
    code("display(pd.DataFrame([causal['provenance']]).T)")
    md('''## 4. ASSOCIAÇÃO BRUTA — NÃO CAUSAL

A diferença entre os grupos observados mistura tratamento, composição e confundimento. Ela é apresentada antes do ajuste apenas como descrição.
''')
    code("display(pd.DataFrame([causal['associacao_bruta']]))")
    md('''## 5. Benchmark preditivo

Split 80/20 estratificado por Y; seed fixa. Mesmas sete X, sem T. PR-AUC aqui é average precision. Precision, recall e F1 usam limiar 0,5, não otimizado no teste. Calibração usa decis de probabilidade; não houve recalibração no teste.
''')
    code('''metricas = ['modelo', 'roc_auc', 'pr_auc_ap', 'brier', 'precision_05', 'recall_05', 'f1_05', 'prevalencia', 'media_predita']
display(pd.DataFrame(pred['modelos'])[metricas].round(6))
print('N treino:', pred['n_treino'], '| N teste:', pred['n_teste'])
print('Brier baseline:', pred['brier_baseline_prevalencia_treino'])
''')
    code('''fig = go.Figure()
for modelo in pred['modelos']:
    fig.add_scatter(x=modelo['roc']['x'], y=modelo['roc']['y'], mode='lines', name=modelo['modelo'])
fig.add_scatter(x=[0,1], y=[0,1], mode='lines', line=dict(dash='dash'), name='Referência')
fig.update_xaxes(title='Taxa de falsos positivos', range=[0,1])
fig.update_yaxes(title='Sensibilidade', range=[0,1])
mostrar(fig, 'ROC no teste | baixo peso — SINASC 2024', 'fase2_roc.html')
''')
    code('''fig = go.Figure()
for modelo in pred['modelos']:
    fig.add_scatter(x=modelo['pr']['x'], y=modelo['pr']['y'], mode='lines', name=modelo['modelo'])
fig.add_hline(y=pred['modelos'][0]['prevalencia'], line_dash='dash')
fig.update_xaxes(title='Recall', range=[0,1])
fig.update_yaxes(title='Precision', range=[0,1])
mostrar(fig, 'Precision–Recall no teste | linha = prevalência', 'fase2_pr.html')
''')
    code('''fig = go.Figure()
for modelo in pred['modelos']:
    c = modelo['calibracao']
    fig.add_scatter(x=c['previsto'], y=c['observado'], mode='lines+markers', name=modelo['modelo'])
lim = max(max(m['calibracao']['previsto'] + m['calibracao']['observado']) for m in pred['modelos'])*1.1
fig.add_scatter(x=[0,lim], y=[0,lim], mode='lines', line=dict(dash='dash'), name='Calibração perfeita')
fig.update_xaxes(title='Risco previsto médio', range=[0,lim])
fig.update_yaxes(title='Frequência observada', range=[0,lim])
mostrar(fig, 'Calibração no teste | decis de probabilidade', 'fase2_calibracao.html')
''')
    md('''## 6. Por que predição não é efeito causal

Um modelo de risco aprende quem apresenta Y. Um efeito compara outcomes potenciais sob ações diferentes. Boa AUC não elimina confundimento; baixa AUC de Y não invalida por si só um estimador de efeito.

## 7. AIPW em linguagem simples

O estimador combina previsões de risco sob cada tratamento e correções dos resíduos ponderadas pela probabilidade do tratamento recebido.

`psi = m1 − m0 + T(Y−m1)/e − (1−T)(Y−m0)/(1−e)`

A média de psi é a diferença estimada de risco. SE = desvio-padrão de (psi−média) / √N; IC95% = estimativa ±1,96 SE. A dupla robustez não garante resultado correto quando ambos os modelos são inadequados ou há confundimento não observado.

## 8. Cross-fitting

Três folds estratificados por T/Y, sem sobreposição. Codificadores e imputação ajustados dentro de cada treino. Cada registro recebe exatamente uma previsão OOF de cada nuisance. C1 e C2 compartilham o propensity logístico.
''')
    code('''display(pd.DataFrame([{k:v for k,v in f.items() if k != 'ajustes'} for f in causal['folds']]))
ajustes = [dict(fold=f['fold'], modelo=nome, n_iter=v['n_iter'], convergence_warning=v['convergence_warning'])
           for f in causal['folds'] for nome,v in f['ajustes'].items()]
display(pd.DataFrame(ajustes))
print('AUC propensity OOF, descritiva:', causal['auc_propensity_oof'])
''')
    md('''## 9. C1: baseline paramétrico

Propensity e outcomes logísticos L2. Resultado em pontos percentuais; IC aproximado por função de influência.
''')
    code('''resultados = pd.DataFrame(causal['resultados'])
colunas = ['especificacao', 'populacao', 'n', 'estimativa_pp', 'se_pp', 'ic95_inferior_pp', 'ic95_superior_pp']
display(resultados.loc[(resultados.especificacao == 'C1') & (resultados.populacao == 'sem_trimming'), colunas])
''')
    md('''## 10. C2: outcomes não lineares

Propensity logístico compartilhado; m0/m1 por HistGradientBoosting. Nenhuma especificação foi selecionada por produzir efeito maior ou menor.
''')
    code("display(resultados.loc[(resultados.especificacao == 'C2') & (resultados.populacao == 'sem_trimming'), colunas])")
    md('''## 11. Sensibilidade ao suporte

Trimming muda a população-alvo. Os intervalos 0,01–0,99 e 0,05–0,95 são sensibilidades. Os ICs tratam a seleção pelo propensity aprendido como fixa; não incluem essa incerteza adicional.
''')
    code('''display(resultados[colunas].round(6))
fig = go.Figure()
for spec in ['C1','C2']:
    d = resultados[resultados.especificacao == spec]
    fig.add_scatter(x=d.estimativa_pp, y=d.populacao, mode='markers', name=spec,
                    error_x=dict(type='data', array=1.96*d.se_pp, visible=True))
fig.add_vline(x=0, line_dash='dash')
fig.update_xaxes(title='Diferença estimada de risco (pontos percentuais)')
fig.update_yaxes(title='População analítica')
mostrar(fig, 'AIPW cross-fitted | estimativa e IC95% aproximado', 'fase2_aipw.html')
''')
    md('''## 12. Diagnósticos do estimador

ESS descreve a concentração dos pesos, não o número real de pessoas. A concentração de IF² nos extremos é verificada pelo gate pré-especificado. Percentis de psi e IF estão no JSON integral.
''')
    code('''linhas = []
for chave, d in causal['diagnosticos'].items():
    linhas.append(dict(cenario=chave, fracao_variancia_top1pct=d['frac_variancia_top1pct'],
                       max_abs_IF=d['max_abs_influencia'], max_contribuicao_pp=d['max_contribuicao_individual_pp'],
                       ESS_T0=d['pesos_por_grupo']['0']['ess'], ESS_T1=d['pesos_por_grupo']['1']['ess'],
                       peso_max_T0=d['pesos_por_grupo']['0']['max']))
display(pd.DataFrame(linhas).round(6))
display(pd.DataFrame(causal['overlap']['trimming_diagnostico']))
display(pd.DataFrame([dict(especificacao=s, nuisance=k, **v)
                      for s, modelos in causal['nuisance_oof'].items() for k,v in modelos.items()]).round(6))
''')
    md('''## 13. Limitações

Dados observacionais: faltam renda, tabagismo, nutrição, morbidades prévias, planejamento da gravidez e medidas de acesso/qualidade. X no nascimento é proxy de estado prévio. Timing retrospectivo e discordâncias de consultas podem causar erro de classificação.

Seleção por nascido vivo, informação e limites de peso pode induzir viés. Não extrapolar para todas as concepções. SE iid não considera dependência geográfica/familiar nem incerteza de identificação. Significância estatística não demonstra causalidade. Nenhum placebo/negative control adequado foi identificado; heterogeneidade foi omitida.

## 14. Gate analítico

O gate usa as regras declaradas no plano anterior à estimação. Não é certificação de causalidade verdadeira.
''')
    code("display(Markdown('**'+causal['gate']+'**')); print('EFEITO_CAUSAL_ESTIMADO = SIM; CAUSALIDADE_PROVADA = NAO')")
    nb.cells = cells
    nbf.validate(nb)
    nbf.write(nb, destino)


if __name__ == '__main__':
    criar_notebook(Path(__file__).resolve().parents[1]/'notebooks/03_ml_preditivo_e_aipw.ipynb')
