"""Gera o notebook 05 em português, com avaliação externa e limites explícitos."""
from pathlib import Path
import nbformat as nbf
from src.apresentacao_pt import preparar_notebook


def criar_notebook(destino):
    nb=nbf.v4.new_notebook(); cells=[]
    def md(s): cells.append(nbf.v4.new_markdown_cell(s))
    def code(s): cells.append(nbf.v4.new_code_cell(s))
    md('''# SINASC 2024 — heterogeneidade causal exploratória

## 1. Objetivo

Verificar se o contraste ajustado entre início precoce e tardio do pré-natal varia com perfis maternos observáveis. **Exercício didático e exploratório; não identifica automaticamente quem se beneficia de uma intervenção.**

A Fase 3 foi publicada antes desta análise, seguida da padronização em português. A população, T, Y, sete covariáveis e regras de qualidade permanecem congelados. Fonte: SINASC 2024, Parquet e diagnósticos locais com hashes. Unidade: um registro de nascido vivo; chave `contador`.
''')
    code('''from pathlib import Path
import sys, json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from IPython.display import display, Markdown, Image
raiz=next(p for p in (Path.cwd(),Path.cwd().parent) if (p/'src').exists()).resolve()
sys.path.insert(0,str(raiz))
assert Path(sys.executable).resolve()==(raiz/'.venv/Scripts/python.exe').resolve(), 'Use a .venv do projeto'
from src.visualizacao_ipt import configurar_plotly,aplicar_tema_ipt
configurar_plotly()
ler=lambda nome:json.loads((raiz/'outputs/diagnostics'/nome).read_text(encoding='utf-8'))
r=ler('fase4_resultados.json'); ajustes=ler('fase4_ajustes.json')
pd.set_option('display.max_columns',12)

def mostrar(fig,titulo,nome,altura=570):
    aplicar_tema_ipt(fig,titulo)
    fig.update_layout(width=1100,height=altura,margin=dict(l=115,r=55,t=100,b=105))
    fig.update_xaxes(automargin=True); fig.update_yaxes(automargin=True)
    p=raiz/'outputs/figures'/('fase4_'+nome+'.png')
    fig.write_image(p); display(Image(filename=str(p)))

print('Reproduzir ajustes: python -m src.executa_fase4')
print('Resumir: python -m src.resume_fase4')
print('Validar: python -m src.valida_resultados_fase4')
''')
    code('''display(pd.DataFrame([{k:r['populacao'][k] for k in ['n','n_t1','n_t0','prevalencia']}]))
print('Covariáveis congeladas:',ajustes['contrato']['x'])
''')
    md('''## 2. O que significa CATE

O CATE candidato é a diferença média entre Y(1) e Y(0) condicional às covariáveis X, na população selecionada. Aqui Y indica baixo peso: valor negativo corresponde a menor risco estimado sob início precoce **apenas sob as hipóteses causais**.

Não observamos os dois desfechos potenciais de uma pessoa. A variação das previsões pode representar estrutura do contraste, erro amostral, especificação do modelo ou confundimento residual. Não é uma medida verificada de benefício individual.

## 3. Limitações

Dados observacionais e selecionados entre nascidos vivos. Renda, tabagismo, nutrição, morbidades e acesso/qualidade permanecem incompletamente medidos. Temporalidade de X e mensuração do mês são limitantes. A estabilidade não resolve a identificação causal.

Os intervalos apresentados são de **contrastes DR de avaliação**, com funções aprendidas tratadas como fixas. Não são intervalos individuais de CATE. A dispersão das previsões não é o erro-padrão do modelo aprendido. Rotação das amostras também cria dependência entre resultados combinados.

## 4. DR-Learner

Primeiro estimar e(X), m0(X), m1(X). Depois construir:

`psi = m1 − m0 + T(Y−m1)/e − (1−T)(Y−m0)/(1−e)`

Finalmente, aprender E[psi|X] por HistGradientBoostingRegressor: 100 iterações, até 7 folhas, mínimo de 2.000 registros por folha, regularização L2=1 e semente 20240925. Sem busca de hiperparâmetros. Comparação simples: Ridge com alpha=10. Modelos auxiliares compatíveis com C2 da Fase 2: propensão logística e desfechos HGB.

[Fundamentação do DR-Learner](https://arxiv.org/html/2004.14497v3). A teoria não certifica automaticamente o desempenho deste estimador específico no SINASC agrupado.

## 5. Ajuste cruzado e honestidade

Três partições de municípios, sorteadas sem usar T/Y. Em cada rotação: **A** ajusta os auxiliares; **B** recebe previsões externas, constrói psi e ajusta o CATE; **C** recebe CATE e fornece avaliação externa. Cada nascimento é avaliado uma vez. Nenhum município de C aparece em A/B; codificação e imputação são ajustadas dentro do treino correspondente.

Essa separação evita vazamento indireto de Y de C através dos modelos auxiliares. Não foram reutilizados os pseudo-desfechos da Fase 2 em uma segunda divisão ingênua. Há perda de eficiência, pois cada etapa usa aproximadamente um terço da população.
''')
    code('''display(pd.DataFrame(ajustes['contrato']['particoes']))
display(pd.DataFrame([{k:v for k,v in x.items() if k not in ['ajustes','indices_sha256']} for x in ajustes['rotacoes']]))
print('UF 53 aparece somente em uma partição municipal; na sua avaliação, é categoria nova nos dois treinos. Isso limita a generalização para o DF.')
''')
    md('''## 6. Distribuição de CATE

Valores em pontos percentuais. O intervalo p5–p95 resume a distribuição prevista; não é intervalo de confiança. Nenhuma previsão foi recortada ou limitada artificialmente.
''')
    code('''display(pd.DataFrame([dict(modelo='HGB principal',**r['principal']),dict(modelo='Ridge',**r['alternativo'])]).T)
h=r['histograma']; limites=np.array(h['limites_pp'])
fig=make_subplots(rows=1,cols=2,subplot_titles=['Amplitude integral','Detalhe: p5 a p95 (90% das previsões)'])
for j in [1,2]:
    fig.add_bar(x=(limites[1:]+limites[:-1])/2,y=h['contagens'],width=np.diff(limites),name='Nascimentos',showlegend=False,row=1,col=j)
    fig.add_vline(x=0,line_dash='dash',row=1,col=j)
fig.update_xaxes(title='CATE previsto (pp)')
fig.update_xaxes(range=[r['principal']['p05_pp'],r['principal']['p95_pp']],row=1,col=2)
fig.update_yaxes(title='Registros',row=1,col=1)
mostrar(fig,'Distribuição das previsões externas | não é benefício individual','distribuicao')
''')
    md('''## 7. Perfis maternos pré-especificados

Idade, escolaridade, raça/cor e paridade. Códigos categóricos originais permanecem explícitos; não constituem ordenação de prioridade. As médias de CATE descrevem o que o modelo aprendeu; o contraste DR usa o pseudo-desfecho de avaliação. Seus intervalos municipais aproximados não incluem toda a incerteza dos modelos nem ajuste para múltiplas comparações.
''')
    code('''perfis=pd.DataFrame(r['perfis'])
for dim in ['Faixa etária','Escolaridade','Raça/cor','Paridade']:
    display(Markdown('### '+dim))
    display(perfis.loc[perfis.dimensao==dim,['grupo','n','media_pp','p05_pp','mediana_pp','p95_pp','contraste_dr_pp','ic95_dr_inferior_pp','ic95_dr_superior_pp']].round(4))
d=perfis[perfis.dimensao=='Faixa etária']
d=d.assign(ordem=d.grupo.map({'<20':0,'20–29':1,'30–34':2,'≥35':3,'Ausente':4})).sort_values('ordem',ascending=False)
rotulos=[g+' (N='+format(int(n),',').replace(',','.')+')' for g,n in zip(d.grupo,d.n)]
fig=go.Figure(go.Scatter(x=d.media_pp,y=rotulos,mode='markers',name='Média prevista',
    error_x=dict(type='data',symmetric=False,array=d.p95_pp-d.media_pp,arrayminus=d.media_pp-d.p05_pp)))
fig.add_vline(x=0,line_dash='dash'); fig.update_xaxes(title='CATE previsto (pp); barras = p5–p95, não IC')
fig.update_yaxes(title='Faixa etária materna')
mostrar(fig,'Perfis de idade | distribuição prevista dentro de cada grupo','idade')
''')
    md('''## 8. Quintis de CATE

Quintis globais crescentes, com N aproximadamente igual. Empates repartidos aleatoriamente com semente fixa, independentemente de Y; pessoas empatadas não têm efeitos previstos diferentes por estarem em quintis distintos.

Idade média e proporções das seis covariáveis categóricas caracterizam a composição. A prevalência de Y é **somente descritiva**. Quintis não significam melhores pacientes para tratar e os contrastes brutos de Y não validam o CATE.
''')
    code('''qs=pd.DataFrame(r['quintis']); display(qs.round(5))
fig=go.Figure()
for coluna,nome in [('cate_medio_pp','HGB principal'),('ridge_medio_pp','Ridge nos mesmos quintis')]:
    fig.add_scatter(x=qs.quintil,y=qs[coluna],mode='lines+markers',name=nome)
fig.update_xaxes(title='Quintil crescente do CATE HGB',dtick=1)
fig.update_yaxes(title='Média prevista (pp)'); fig.add_hline(y=0,line_dash='dash')
mostrar(fig,'Comparação de modelos nos quintis globais | descrição','quintis')
''')
    code('''composicao=pd.DataFrame(r['quintis_composicao_x'])
for variavel in ajustes['contrato']['x'][1:]:
    display(Markdown('**'+variavel+' — composição (%)**'))
    display(composicao[composicao.variavel==variavel].pivot(index='categoria',columns='quintil',values='percentual').fillna(0).round(2))
''')
    md('''## 9. Diagnósticos de estabilidade

**Modelo:** correlação HGB/Ridge, discrepância absoluta e concordância de sinal nas previsões externas.

**Partições:** distribuição e médias de perfis comparadas entre conjuntos geográficos distintos. Para as correlações, usar categorias com N≥1.000 em cada conjunto comparado. Diferenças também podem refletir composição geográfica.

**Separação externa:** em cada conjunto C, recalcular quintis localmente e comparar a média de psi em Q5 e Q1. Como a ordem é crescente, uma diferença positiva é compatível com a ordenação prevista. O IC é municipal, condicional às funções fixas. As três rotações compartilham dados em papéis diferentes; não são três estudos independentes.
''')
    code('''e=r['estabilidade']
display(pd.DataFrame([{k:e[k] for k in ['spearman_hgb_ridge','diferenca_absoluta_media_pp','concordancia_sinal','mediana_spearman_perfis']}]).T)
display(pd.DataFrame(e['distribuicao_particao']).round(5))
display(pd.DataFrame(e['correlacoes_perfis']).round(5))
externo=pd.DataFrame(e['contrastes_externos'])
display(externo.drop(columns='metodo').round(5))
fig=go.Figure(go.Scatter(x=externo.contraste_dr_q5_q1_pp,y=externo.particao.astype(str),mode='markers',name='Contraste DR externo',
    error_x=dict(type='data',symmetric=False,array=externo.ic95_superior_pp-externo.contraste_dr_q5_q1_pp,
    arrayminus=externo.contraste_dr_q5_q1_pp-externo.ic95_inferior_pp)))
fig.add_vline(x=0,line_dash='dash')
fig.update_xaxes(title='Diferença Q5−Q1 no pseudo-desfecho externo (pp), IC95% municipal')
fig.update_yaxes(title='Partição de avaliação',type='category')
mostrar(fig,'Validação externa da ordenação | contraste entre extremos','validacao')
''')
    md('''## 10. Relação entre ATE e CATE

Na população-alvo, o ATE é a média do CATE verdadeiro, sob as mesmas hipóteses. A média de previsões regularizadas não precisa coincidir exatamente com a média dos pseudo-desfechos, nem com C2 histórico: há separação diferente e menos dados por ajuste. Nenhuma previsão foi recentrada para forçar concordância.
''')
    code("display(pd.DataFrame([{k:r[k] for k in ['media_psi_pp','diferenca_media_cate_psi_pp','ate_fase2_c2_pp']}]).T); print('Média CATE HGB (pp):',r['principal']['media_pp'])")
    md('''## 11. Exercício de decisão — somente conceito

Se houvesse capacidade limitada para promover início precoce, seria necessário definir a intervenção, seus custos e elegibilidade, avaliar valor esperado em dados independentes e realizar validação prospectiva com critérios de equidade. A intervenção de promoção não é equivalente a observar início precoce. Sem efeito identificado dessa ação e sem custos, não há ROI defensável.

O modelo atual **não recomenda tratamento, retirada de cuidado, alocação clínica ou política pública**. Um sinal previsto não determina a verdade individual. Causal Forest foi omitido para manter a fase parcimoniosa e sem novas dependências.

## 12. Critério de decisão

As regras operacionais foram registradas antes do ajuste. A classificação considera avaliação externa, comparação de modelos e estabilidade entre partições; não usa apenas a dispersão das previsões. Os limiares são critérios exploratórios deste exercício, não testes universais.

[Protocolo, resultados e limitações](../docs/methodology/HETEROGENEIDADE_FASE4.md). Os critérios históricos das Fases 1–3 permanecem registrados. Nenhuma Fase 5 foi iniciada.
''')
    code('''from src.valida_resultados_fase4 import validar
validacao=validar()
assert validacao['status']=='APROVADO'
display(Markdown('**'+r['gate']+'**'))
print('Causalidade provada: NÃO. Recomendação clínica: NÃO.')
''')
    nb.cells=cells; preparar_notebook(nb); nbf.validate(nb); nbf.write(nb,destino)


if __name__=='__main__': criar_notebook(Path(__file__).resolve().parents[1]/'notebooks/05_heterogeneidade_causal.ipynb')
