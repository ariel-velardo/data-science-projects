# Gráficos finais

Dez gráficos selecionados entre os temas dos notebooks e redesenhados dos mesmos agregados para leitura offline. Tema IPT do projeto; fontes históricas preservadas.

| ID | Gráfico | Fonte | Leitura |
| --- | --- | --- | --- |
| fluxo | Da base à população analítica | fase1_amostra.json | Filtros sequenciais; as sete X não excluem novos registros. |
| tratamento | Início precoce e tardio | fase1_amostra.json | Distribuição na população analítica; T=0 não significa ausência de pré-natal. |
| prevalencia | Baixo peso observado por grupo | fase1_amostra.json | Descrição bruta; diferenças de composição impedem interpretar as barras como efeitos. |
| smd | Desequilíbrio antes do ajuste | fase1_amostra.json | Para categóricas, nível de maior SMD absoluto. Linha 0,1 é referência diagnóstica. |
| overlap | Suporte comum entre os grupos | fase1_overlap.json; histograma_propensity.csv | Diagnóstico OOF de cinco partições da Fase 1; suporte observado não prova intercambialidade. |
| roc | Discriminação preditiva no teste | fase2_modelagem_preditiva.json | Mesmas sete X, sem T. AP e Brier complementam a ROC na tabela de resultados. |
| aipw | AIPW e sensibilidade ao suporte | fase2_aipw.json | Recorte muda a população-alvo. ICs não incorporam viés de seleção ou confundimento. |
| geografia | Robustez à separação municipal | fase3_crossfit_geografico.json | ICs supõem independência entre municípios. Estabilidade numérica não elimina confundimento. |
| cate | Distribuição integral do CATE previsto | fase4_resultados.json | Distribuição de previsões, não de efeitos individuais conhecidos. p5–p95 não é IC. |
| perfis | Perfis de idade: exercício exploratório | fase4_resultados.json | 32 idades ausentes ficam fora deste gráfico, mas permanecem no N integral. Não indica prioridade clínica. |

O HTML embute uma única cópia do Plotly. Não embute observações individuais. Os gráficos históricos permanecem em `outputs/figures/` e nos notebooks.
