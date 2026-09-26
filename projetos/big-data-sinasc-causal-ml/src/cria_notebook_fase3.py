"""Notebook executável da auditoria, com tabelas e figuras IPT autocontidas."""
from pathlib import Path
import nbformat as nbf
from src.apresentacao_pt import preparar_notebook


def criar_notebook(destino):
    nb=nbf.v4.new_notebook()
    nb.metadata.kernelspec=dict(display_name='Python (SINASC .venv)',language='python',name='python3')
    cells=[]
    def md(s): cells.append(nbf.v4.new_markdown_cell(s))
    def code(s): cells.append(nbf.v4.new_code_cell(s))
    md('''# SINASC 2024 — robustez e auditoria metodológica

## 1. Por que a Fase 3 existe

Auditar o AIPW, a concentração da influência e a independência geográfica. **Não buscar um resultado mais favorável.**

Este notebook valida as predições persistidas e apresenta a execução integral. Os ajustes pesados são reproduzidos com `python -m src.executa_robustez_fase3`, na `.venv` deste projeto. Não há ajuste oculto ao abrir o notebook.

Descrição, performance preditiva dos nuisances e interpretação causal permanecem separadas. Fontes: Parquet SINASC 2024 e JSONs Fase 2/3; hashes e SQL estão nos artefatos de auditoria.
''')
    code('''from pathlib import Path
import sys, json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from IPython.display import display, Markdown, Image

raiz = next(p for p in (Path.cwd(), Path.cwd().parent) if (p/'src').exists()).resolve()
sys.path.insert(0, str(raiz))
assert Path(sys.executable).resolve() == (raiz/'.venv/Scripts/python.exe').resolve(), 'Ative a .venv do projeto'
from src.visualizacao_ipt import configurar_plotly, aplicar_tema_ipt
configurar_plotly()
pasta = raiz/'outputs/diagnostics'
ler = lambda nome: json.loads((pasta/nome).read_text(encoding='utf-8'))
historico = ler('fase2_aipw.json')
influencia = ler('fase3_influencia.json')
cluster = ler('fase3_cluster.json')
geografico = ler('fase3_crossfit_geografico.json')
monte_carlo = ler('fase3_monte_carlo.json')
sens = ler('fase3_sensibilidades.json')
gate = ler('fase3_gate.json')
pd.set_option('display.max_columns', 12)
pd.set_option('display.width', 140)

def mostrar(fig, titulo, nome, altura=600):
    aplicar_tema_ipt(fig, titulo)
    fig.update_layout(width=1100, height=altura, margin=dict(l=115,r=50,t=100,b=110))
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    arquivo = raiz/'outputs/figures'/('fase3_'+nome+'.png')
    fig.write_image(arquivo)
    display(Image(filename=str(arquivo)))

colunas = ['especificacao','populacao','n','estimativa_pp','se_iid_pp','se_cluster_pp',
           'ic95_cluster_inferior_pp','ic95_cluster_superior_pp']
def tabela(resumo):
    display(pd.DataFrame(resumo['resultados'])[colunas].round(6))
''')
    code('''display(Markdown('**Síntese:** '+gate['sintese']))
display(Markdown('**Revisão adicional:** `'+gate['gate']+'`. O gate histórico permanece `'+historico['gate']+'`.'))
''')
    md('''## 2. Resultado congelado da Fase 2

Unidade: registro de nascido vivo. População P1: gestação única, peso 500–6.000 g e MESPRENAT 1–9. T=1 meses 1–3; T=0 meses 4–9. Y=1 peso <2.500 g. Sete X congeladas; nenhuma feature municipal nova.
''')
    code("display(pd.DataFrame(historico['resultados'])[['especificacao','populacao','n','estimativa_pp','se_pp']].round(6))")
    md('''## 3. Auditoria da IF

`psi = m1−m0 + T(Y−m1)/e − (1−T)(Y−m0)/(1−e)`; `IF=psi−média(psi)`.

`SE_iid² = soma(IF²)/[N(N−1)]`. Implementação independente por grupos, tolerância absoluta 1e−12. A validação abaixo também recalcula o sandwich via DuckDB, verifica folds e compara hashes históricos.
''')
    code('''from src.valida_resultados_fase3 import validar
validacao = validar(raiz)
assert validacao['status'] == 'APROVADO'
display(pd.DataFrame(influencia['reconciliacao']))
''')
    md('''## 4. Curva de concentração

Ordem **decrescente** de |IF|; X=fração acumulada de registros, Y=fração acumulada de IF². Não é Lorenz crescente convencional. Faixas são cumulativas, com N arredondado para cima.

Contribuição `soma(psi_top)/N` compõe a estimativa; `soma(IF_top)/N` é o desvio líquido centrado. Nenhuma delas é efeito causal dos registros extremos.
''')
    code('''faixas = pd.DataFrame([dict(especificacao=s, **r) for s,d in influencia['especificacoes'].items() for r in d['faixas']])
display(faixas[['especificacao','top_pct','n','fracao_if2','fracao_abs_if','contribuicao_psi_pp','contribuicao_if_pp']].round(6))
fig = make_subplots(rows=1, cols=2, subplot_titles=['Distribuição integral','Detalhe: primeiros 10%'])
for s,d in influencia['especificacoes'].items():
    curva = d['curva']; x=100*np.array(curva['fracao_observacoes']); y=100*np.array(curva['fracao_if2'])
    for j in [1,2]:
        fig.add_scatter(x=x,y=y,mode='lines',name=s,legendgroup=s,showlegend=(j==1),
                        line=dict(color='#00598E' if s=='C1' else '#04B4E3',dash='solid' if s=='C1' else 'dash'),row=1,col=j)
fig.update_xaxes(title='Registros acumulados (%)',range=[0,100],row=1,col=1)
fig.update_xaxes(title='Registros acumulados (%)',range=[0,10],row=1,col=2)
fig.update_yaxes(title='IF² acumulada (%)',range=[0,100],row=1,col=1)
fig.update_yaxes(range=[0,100],row=1,col=2)
mostrar(fig,'Concentração da influência | P1, SINASC 2024','concentracao')
''')
    md('''Top 1% concentra aproximadamente 78,8% de IF². A maior observação responde por menos de 0,06% da soma de IF²: concentração coletiva e dominância individual são diagnósticos diferentes.

## 5. Perfil dos extremos — descrição, não mecanismo causal

O top 1% é composto por controles e quase inteiramente por Y=1. No top 0,1%, a mediana de e é aproximadamente 0,939: a baixa probabilidade relevante é **1−e**, a chance do tratamento recebido pelos controles. Não confundir com propensity baixo.
''')
    code('''display(faixas.loc[faixas.top_pct.isin([.1,1.,5.]),
    ['especificacao','top_pct','n','prop_t0','prop_t1','prop_y0','prop_y1']].round(6))
perfis = []
for s,d in influencia['especificacoes'].items():
    for pct in ['100.0','0.1','1.0','5.0']:
        r=d['perfis'][pct]
        perfis.append(dict(especificacao=s,top_pct=float(pct),n=r['n'],idade_mediana=r['idade']['0.5'],
                           e_mediano=r['propensity']['0.5'],e_p99=r['propensity']['0.99']))
display(pd.DataFrame(perfis).round(4))
''')
    code('''# Perfil categórico completo: códigos preservados, sem imputar interpretação causal.
for variavel in ['ESCOLARIDADE_MAE','RACA_COR_MAE','SITUACAO_CONJUGAL','PARIDADE_CAT','PERDAS_FETAIS_CAT']:
    linhas=[]
    for s,d in influencia['especificacoes'].items():
        for pct in ['100.0','0.1','1.0','5.0']:
            linhas += [dict(especificacao=s,top_pct=pct,categoria=k,percentual=100*v['proporcao'])
                       for k,v in d['perfis'][pct]['categorias'][variavel].items()]
    display(Markdown('**'+variavel+'**'))
    display(pd.DataFrame(linhas).pivot(index='categoria',columns=['especificacao','top_pct'],values='percentual').round(2))
''')
    code('''fig=go.Figure()
for pct in ['100.0','0.1','1.0','5.0']:
    d=influencia['especificacoes']['C1']['perfis'][pct]['categorias']['UF_RESIDENCIA']
    ufs=sorted(d)
    fig.add_scatter(x=ufs,y=[100*d[u]['proporcao'] for u in ufs],mode='lines+markers',name='Amostra' if pct=='100.0' else 'Top '+pct+'%')
fig.update_xaxes(title='UF de residência (código)')
fig.update_yaxes(title='Participação no grupo (%)',rangemode='tozero')
mostrar(fig,'Composição geográfica dos extremos C1 | descrição','perfil_uf')
''')
    md('''## 6. Dependência por município

CODMUNRES é recuperado da mesma base em ordem de contador; chave única e datas validadas. Os 5.581 agrupamentos incluem 11 códigos de município não especificado (37 registros). Não são 5.581 municípios identificados. A exclusão desses códigos aparece como sensibilidade separada.
''')
    code('''amostra=cluster['amostra']
display(pd.DataFrame([{k:v for k,v in amostra.items() if k not in ['sql','codigos_municipio_nao_especificado']}]).T)
r=cluster['resultados'][0]
display(pd.DataFrame([{'quantil':k,'N_cluster':v} for k,v in r['tamanhos'].items()]))
print('Clusters com N<10:',r['clusters_n_menor_10'],'| maior fração de N:',r['max_fracao_n'])
tabela(cluster['sensibilidade_sem_municipio_nao_especificado'])
''')
    md('''## 7. SE iid versus cluster e bootstrap

`U_g=soma(IF_i no cluster g)`; `SE_cluster²=[G/(G−1)]×soma(U_g²)/N²`. IC por t com G−1 graus de liberdade. Pressupõe independência entre clusters e regularidade; não corrige confundimento.

Bootstrap: 500 sorteios de G clusters, com reposição, denominador N* variável. Nuisances fixos; não incorpora sua incerteza completa. Na Fase 2, a correção sandwich é sensibilidade, pois os folds originais misturam municípios.
''')
    code('''tabela(cluster)
boots=pd.DataFrame([dict(especificacao=r['especificacao'],populacao=r['populacao'],
                         SE_boot_pp=r['bootstrap']['se_bootstrap_pp'],
                         IC_inferior_pp=r['bootstrap']['ic95_percentil_pp'][0],
                         IC_superior_pp=r['bootstrap']['ic95_percentil_pp'][1]) for r in cluster['resultados']])
display(boots.round(6))
fig=go.Figure()
for nome,campo in [('iid','se_iid_pp'),('cluster','se_cluster_pp'),('bootstrap','SE_boot_pp')]:
    valores=boots[campo] if nome=='bootstrap' else [r[campo] for r in cluster['resultados']]
    fig.add_bar(x=[r['especificacao']+' / '+r['populacao'] for r in cluster['resultados']],y=valores,name=nome)
fig.update_layout(barmode='group')
fig.update_yaxes(title='Erro-padrão (pp)',rangemode='tozero')
mostrar(fig,'Incerteza com predições Fase 2 fixas | SINASC 2024','erros_padrao')
''')
    md('''## 8. Cross-fitting aleatório versus agrupado

Três folds StratifiedGroupKFold por T/Y; cada código municipal pertence a apenas um fold. Mesmas X e hiperparâmetros. O early stopping HGB usa somente dados dentro do treino externo; nenhum município da validação externa participa do ajuste. Não houve tuning nem escolha por efeito.
''')
    code('''display(pd.DataFrame([{k:v for k,v in f.items() if k!='ajustes'} for f in geografico['folds']]))
comparacao=pd.DataFrame([dict(folds=k,**r) for k in ['aleatorio','agrupado'] for r in geografico[k]['resultados']])
display(comparacao[['folds']+colunas].round(6))
display(pd.DataFrame([dict(folds=k,especificacao=s,AUC=d['propensity']['roc_auc'],Brier=d['propensity']['brier'])
    for k in ['aleatorio','agrupado'] for s,d in geografico[k]['nuisance'].items()]).round(6))
fig=go.Figure()
for k in ['aleatorio','agrupado']:
    d=comparacao[comparacao.folds==k]
    fig.add_scatter(x=d.estimativa_pp,y=d.especificacao+' / '+d.populacao,mode='markers',name=k,
        error_x=dict(type='data',symmetric=False,array=d.ic95_cluster_superior_pp-d.estimativa_pp,
                     arrayminus=d.estimativa_pp-d.ic95_cluster_inferior_pp))
fig.update_xaxes(title='AIPW e IC95% cluster (pp)')
mostrar(fig,'Folds aleatórios e geográficos | IC aproximado','crossfit')
''')
    code('''diagnosticos=[]
performance=[]
for k in ['aleatorio','agrupado']:
    for r in geografico[k]['resultados']:
        diagnosticos.append(dict(folds=k,especificacao=r['especificacao'],populacao=r['populacao'],
            n=r['n'],ESS_T0=r['ess']['0']['ess'],ESS_T1=r['ess']['1']['ess'],top1_IF2=r['top1_if2']))
    for s,d in geografico[k]['nuisance'].items():
        for g,m in d['outcomes'].items():
            performance.append(dict(folds=k,especificacao=s,grupo=g,AUC=m['roc_auc'],AP=m['pr_auc_ap'],Brier=m['brier']))
display(pd.DataFrame(diagnosticos).round(4))
display(pd.DataFrame(performance).round(6))
''')
    md('''## 9. Leave-one-UF-out

Retira os registros de uma UF por vez, mantendo nuisances OOF. É diagnóstico de estabilidade da média padronizada, **não heterogeneidade causal**. Não reajusta 27 modelos.
''')
    code('''loo=pd.DataFrame(influencia['leave_one_uf_out'])
display(loo.pivot(index=['grupo','n_removido'],columns='especificacao',values=['estimativa_pp','mudanca_pp']).round(6))
fig=go.Figure()
for s in ['C1','C2']:
    d=loo[loo.especificacao==s]
    fig.add_scatter(x=d.mudanca_pp,y=d.grupo,mode='markers',name=s)
fig.add_vline(x=0,line_dash='dash')
fig.update_xaxes(title='Mudança da estimativa ao retirar a UF (pp)')
fig.update_yaxes(title='UF retirada (código)',type='category')
mostrar(fig,'Leave-one-UF-out | predições fixas','leave_uf',800)
''')
    md('''São Paulo (35) produz a maior mudança, cerca de +0,09–0,10 pp. O sinal permanece negativo em todas as exclusões. Participação geográfica não implica mecanismo causal.

## 10. Monte Carlo do gate

Quatro cenários fixos, N=50.000, 200 réplicas cada, seed 20240925+j. Efeito verdadeiro −1 pp; nuisances oráculo. S1: e=0,5 e prevalência 10%; S2: e=0,85 e prevalência 10%; S3: e entre 0,75 e 0,95 e prevalência 8%; S4: 20% da população com e=0,995, restante e=0,81375.

O oráculo isola a heurística; não reproduz incerteza do ajuste, agrupamento ou seleção SINASC. Frequência empírica 0/100% não significa probabilidade populacional exatamente 0/1.
''')
    code('''from scipy.stats import binomtest
mc=pd.DataFrame([{k:v for k,v in s.items() if k!='replicas'} for s in monte_carlo['cenarios']])
for campo in ['bias','rmse','mcse_bias']: mc[campo+'_pp']=100*mc[campo]
display(mc[['cenario','bias_pp','mcse_bias_pp','rmse_pp','cobertura','mcse_cobertura','prob_gate','ess_t0_medio']].round(6))
intervalos=[binomtest(round(s['prob_gate']*s['n_replicas']),s['n_replicas']).proportion_ci() for s in monte_carlo['cenarios']]
display(pd.DataFrame([dict(cenario=s['cenario'],prob_gate=s['prob_gate'],IC_MC_inferior=i.low,IC_MC_superior=i.high)
    for s,i in zip(monte_carlo['cenarios'],intervalos)]).round(4))
fig=make_subplots(rows=1,cols=2,subplot_titles=['Acionamento do gate','Cobertura do IC95%'])
fig.add_bar(x=mc.cenario,y=100*mc.prob_gate,name='Gate',showlegend=False,row=1,col=1)
fig.add_bar(x=mc.cenario,y=100*mc.cobertura,name='Cobertura',showlegend=False,row=1,col=2)
fig.add_hline(y=95,line_dash='dash',row=1,col=2)
fig.update_yaxes(title='Réplicas (%)',range=[0,105],row=1,col=1)
fig.update_yaxes(range=[0,105],row=1,col=2)
mostrar(fig,'Heurística e cobertura | 200 réplicas por cenário','monte_carlo')
''')
    md('''S3 aciona o gate em todas as réplicas, com cobertura de 97,5%; S4 também aciona em todas, mas com cobertura de 89,5%. A regra isolada não distingue esses casos. O bias estimado em S3 foi −0,073 pp (MCSE 0,026 pp); não se repetiu a simulação para buscar um resultado mais conveniente.

## 11. Sensibilidade CONSPRENAT=0

S1 exclui discordâncias mês válido/zero consultas. Reajusta C1/C2 na população restrita. T permanece definido por MESPRENAT; consultas não entram em X. A exclusão também é seleção posterior, não uma correção causal demonstrada.
''')
    code("display(pd.DataFrame([{k:v for k,v in sens['amostras'][s].items() if k not in ['sql','codigos_municipio_nao_especificado']} for s in ['P1','CONSPRENAT']])[['cenario','n','n_t1','n_t0','prevalencia','n_consprenat_zero']]); tabela(sens['CONSPRENAT'])")
    md('''## 12. Sensibilidade de peso P0

Todos os pesos numéricos positivos; gestação única. Mesmo Y<2.500 g, X e T. Nuisances reajustados. Valores extremos podem incluir erro de mensuração; P0 não substitui P1.
''')
    code("display(pd.DataFrame([{k:v for k,v in sens['amostras']['P0'].items() if k not in ['sql','codigos_municipio_nao_especificado']}])[['n','prevalencia','n_peso_fora_p1']]); tabela(sens['P0'])")
    md('''## 13. Sensibilidade a múltiplas

GRAVIDEZ 1/2/3, peso P1. Cada nascido vivo permanece uma linha; múltiplas podem gerar irmãos correlacionados sem identificador da gestação. Reportar estabilidade direcional/magnitude, sem equivalência com a população principal.
''')
    code("display(pd.DataFrame([{k:v for k,v in sens['amostras']['MULTIPLAS'].items() if k not in ['sql','codigos_municipio_nao_especificado']}])[['n','prevalencia','n_multipla']]); tabela(sens['MULTIPLAS'])")
    code('''resumos=pd.DataFrame([dict(cenario=k,**r) for k in ['CONSPRENAT','P0','MULTIPLAS'] for r in sens[k]['resultados'] if r['populacao']=='sem_trimming'])
display(resumos[['cenario','especificacao','n','estimativa_pp','diferenca_p1_pp','diferenca_relativa_abs_p1']].round(6))
fig=go.Figure()
for s in ['C1','C2']:
    d=resumos[resumos.especificacao==s]
    fig.add_scatter(x=d.diferenca_p1_pp,y=d.cenario,mode='markers',name=s)
fig.add_vline(x=0,line_dash='dash')
fig.update_xaxes(title='Diferença versus P1 da mesma especificação (pp)')
mostrar(fig,'Sensibilidades de elegibilidade | novos alvos condicionais','elegibilidade',500)
''')
    md('''## 14. C3: propensity não linear

HGB para e; outcomes HGB C2 históricos, com os mesmos folds aleatórios. Reutilizar esses outcomes mantém previsões OOF adequadas e isola a mudança de propensity. Hiperparâmetros congelados, sem tuning. AUC/Brier medem nuisances, não qualidade causal.
''')
    code('''tabela(sens['S0'])
display(pd.DataFrame([dict(especificacao=s,AUC=d['propensity']['roc_auc'],Brier=d['propensity']['brier'],
    suporte_min=d['overlap']['suporte_comum_observado']['inferior'],suporte_max=d['overlap']['suporte_comum_observado']['superior'])
    for s,d in sens['S0']['nuisance'].items()]).round(6))
display(pd.DataFrame([dict(especificacao=r['especificacao'],populacao=r['populacao'],top1_IF2=r['top1_if2'],
    ESS_T0=r['ess']['0']['ess'],ESS_T1=r['ess']['1']['ess'],peso_max_T0=r['ess']['0']['max']) for r in sens['S0']['resultados']]).round(6))
''')
    md('''## 15. Auditoria do estimando

O estimador descreve um contraste padronizado na distribuição selecionada de nascidos vivos. Nascimento vivo, peso disponível e mês registrado são critérios conhecidos posteriormente à decisão de iniciar pré-natal. Multiplicidade registrada ao final não prova, por si só, causalidade pós-tratamento; seleção por sobrevivência fetal também precisa ser considerada.

Não identifica automaticamente efeito em todas as concepções ou no estrato que nasceria vivo sob ambas as exposições. Estabilidade, dupla robustez e IC estreito não resolvem essas hipóteses. [Auditoria completa](../docs/methodology/AUDITORIA_ESTIMANDO_FASE3.md).

## 16. Síntese

Reconciliação independente, concentração, geografia e sensibilidades respondem perguntas diferentes. Não usar significância como critério principal; nenhuma especificação será promovida por produzir o efeito desejado.
''')
    code("display(pd.DataFrame(gate['evidencias'])); display(Markdown(gate['sintese']))")
    md('''## 17. Gate Fase 3

A revisão é adicional. O registro histórico da Fase 2 não foi editado. [Literatura e fórmulas](../docs/literature/AUDITORIA_GATE_INFLUENCIA.md); [relatório completo](../docs/methodology/ROBUSTEZ_FASE3.md).
''')
    code('''assert historico['gate']=='RESULTADO_NAO_INTERPRETAVEL'
assert gate['historico_fase2']=='RESULTADO_NAO_INTERPRETAVEL'
assert validacao['historico_intacto']
display(Markdown('**GATE_REVISAO_FASE3 = '+gate['gate']+'**'))
print('Sem CATE, Causal Forest ou uplift. Causalidade não provada.')
''')
    nb.cells=cells
    nbf.validate(nb)
    preparar_notebook(nb)
    nbf.write(nb,destino)


if __name__=='__main__':
    criar_notebook(Path(__file__).resolve().parents[1]/'notebooks/04_robustez_e_auditoria_metodologica.ipynb')
