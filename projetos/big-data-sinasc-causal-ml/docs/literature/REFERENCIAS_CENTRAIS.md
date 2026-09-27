# Referências centrais

Seleção dirigida de 12 referências, não revisão sistemática. O mapa inicial e a auditoria do gate permanecem preservados. Priorizados pré-natal/SINASC, predição, AIPW, ajuste cruzado, heterogeneidade, clusters e seleção. Títulos e citações mantêm o idioma original; a análise está em PT-BR. DOIs de versões públicas estão identificados quando distintos do publicado.

## vale2021

Vale CCR, Almeida NKO, Almeida RMVR. Association between Prenatal Care Adequacy Indexes and Low Birth Weight Outcome. Rev Bras Ginecol Obstet. 2021;43:256–263.

DOI: [10.1055/s-0041-1728779](https://doi.org/10.1055/s-0041-1728779). [Fonte](https://pmc.ncbi.nlm.nih.gov/articles/PMC10208735/).

| Dimensão | Síntese |
| --- | --- |
| Problema | Adequação do pré-natal e baixo peso. |
| Populacao | 368.093 nascidos vivos únicos a termo; Rio de Janeiro, 2015–2016. |
| Dados | SINASC. |
| Metodo | Sete índices; regressão logística ajustada. |
| Resultado | Inadequação associada a maiores odds de baixo peso; magnitude varia conforme índice. |
| Limitacoes | Índices combinam início e consultas; confundidores ausentes e qualidade do cuidado não medida. |
| Uso | Contexto brasileiro; não equivale ao T isolado deste projeto. |

## falcao2020

Falcão IR et al. Factors associated with low birth weight at term: a population-based linkage study of the 100 million Brazilian cohort. BMC Pregnancy Childbirth. 2020;20:536.

DOI: [10.1186/s12884-020-03226-x](https://doi.org/10.1186/s12884-020-03226-x). [Fonte](https://pmc.ncbi.nlm.nih.gov/articles/PMC7491100/).

| Dimensão | Síntese |
| --- | --- |
| Problema | Determinantes sociais de baixo peso a termo. |
| Populacao | 8.768.930 nascidos vivos a termo, Brasil, 2001–2015. |
| Dados | Coorte de 100 Milhões vinculada ao SINASC. |
| Metodo | Regressão logística com estrutura hierárquica. |
| Resultado | Escolaridade, raça/cor, idade, paridade e assistência associam-se ao desfecho. |
| Limitacoes | Associações observacionais; população socialmente selecionada e a termo. |
| Uso | Fundamentar X e discutir confundimento socioeconômico residual. |

## bonilha2018

Bonilha EA et al. Coverage, completeness and reliability of the data in the Information System on Live Births in public maternity wards in the municipality in São Paulo, Brazil, 2011. Epidemiol Serv Saude. 2018;27:e201712811.

DOI: [10.5123/S1679-49742018000100011](https://doi.org/10.5123/S1679-49742018000100011). [Fonte](https://www.scielo.br/j/ress/a/Vqsdk5khwLbWBNDc9RZvqPb/).

| Dimensão | Síntese |
| --- | --- |
| Problema | Confiabilidade dos campos do SINASC. |
| Populacao | 5.785 registros de quatro maternidades públicas; São Paulo, 2011. |
| Dados | SINASC comparado a estudo de campo. |
| Metodo | Cobertura, completude e concordância kappa. |
| Resultado | Boa concordância de peso e gravidez; concordância menor para consultas e perdas fetais. |
| Limitacoes | Quatro hospitais e período local; não valida nacionalmente os dados de 2024. |
| Uso | Justificar auditoria e cautela com história reprodutiva e assistência. |

## ranjbar2023

Ranjbar A, Montazeri F, Vahidi Farashah M, Mehrnoush V, Darsareh F, Roozbeh N. Machine learning-based approach for predicting low birth weight. BMC Pregnancy Childbirth. 2023;23:803.

DOI: [10.1186/s12884-023-06128-w](https://doi.org/10.1186/s12884-023-06128-w). [Fonte](https://pmc.ncbi.nlm.nih.gov/articles/PMC10662167/).

| Dimensão | Síntese |
| --- | --- |
| Problema | Predição de baixo peso com ML. |
| Populacao | 8.853 partos; Irã, 2020–2022. |
| Dados | Rede materno-neonatal iraniana. |
| Metodo | Comparação de oito modelos preditivos. |
| Resultado | XGBoost foi destacado pelo conjunto de m?tricas; deep learning teve maior AUROC. Os autores pedem novas avalia??es. |
| Limitacoes | Preditores obstétricos tardios e contexto distinto; métricas não transportáveis ao SINASC. |
| Uso | Separar benchmark de risco, temporalidade dos preditores e estimação causal. |

## funk2011

Funk MJ, Westreich D, Wiesen C, Stürmer T, Brookhart MA, Davidian M. Doubly robust estimation of causal effects. Am J Epidemiol. 2011;173:761–767.

DOI: [10.1093/aje/kwq439](https://doi.org/10.1093/aje/kwq439). [Fonte](https://pmc.ncbi.nlm.nih.gov/articles/PMC3070495/).

| Dimensão | Síntese |
| --- | --- |
| Problema | Combinar regressão do desfecho e propensity. |
| Populacao | Exemplos e populações simuladas. |
| Dados | Estudo metodológico; não SINASC. |
| Metodo | Estimador duplamente robusto e simulações. |
| Resultado | Consistência sob especificação adequada de um dos componentes e hipóteses de identificação. |
| Limitacoes | Dupla robustez não elimina confundimento nem garante inferência com quaisquer modelos ML. |
| Uso | Explicar a lógica do AIPW e seus limites. |

## petersen2012

Petersen ML, Porter KE, Gruber S, Wang Y, van der Laan MJ. Diagnosing and responding to violations in the positivity assumption. Stat Methods Med Res. 2012;21:31–54.

DOI: [10.1177/0962280210386207](https://doi.org/10.1177/0962280210386207). [Fonte](https://pmc.ncbi.nlm.nih.gov/articles/PMC4107929/).

| Dimensão | Síntese |
| --- | --- |
| Problema | Suporte insuficiente para identificar contrastes. |
| Populacao | Cenários metodológicos e exemplos aplicados. |
| Dados | Simulações e dados ilustrativos. |
| Metodo | Diagnóstico de positividade, bootstrap e redefinição de alvos. |
| Resultado | Escassez de suporte pode aumentar viés sem aumento evidente de variância. |
| Limitacoes | Diagnósticos dependem de modelo e parâmetro. |
| Uso | Interpretar overlap e reconhecer que trimming muda o alvo. |

## austin2015

Austin PC, Stuart EA. Moving towards best practice when using inverse probability of treatment weighting (IPTW) using the propensity score to estimate causal treatment effects in observational studies. Stat Med. 2015;34:3661–3679.

DOI: [10.1002/sim.6607](https://doi.org/10.1002/sim.6607). [Fonte](https://pmc.ncbi.nlm.nih.gov/articles/PMC4626409/).

| Dimensão | Síntese |
| --- | --- |
| Problema | Uso e diagnóstico de pesos por propensity. |
| Populacao | Estudos observacionais; discussão metodológica. |
| Dados | Exemplos ilustrativos de ponderação. |
| Metodo | Revisão prática de IPTW, pesos e balanceamento. |
| Resultado | Recomenda examinar distribuição dos pesos e equilíbrio das covariáveis. |
| Limitacoes | Balanceamento observado não assegura ausência de confundimento não medido. |
| Uso | Fundamentar SMD e diagnóstico de suporte, sem usar AUC como validação causal. |

## chernozhukov2018

Chernozhukov V, Chetverikov D, Demirer M, Duflo E, Hansen C, Newey W, Robins J. Double/debiased machine learning for treatment and structural parameters. Econom J. 2018;21:C1–C68.

DOI: [10.1111/ectj.12097](https://doi.org/10.1111/ectj.12097). [Fonte](https://www.nber.org/papers/w23564).

| Dimensão | Síntese |
| --- | --- |
| Problema | Viés de regularização ao inserir ML em estimação causal. |
| Populacao | Modelos semiparamétricos e aplicações econômicas. |
| Dados | Teoria e exemplos empíricos; versão pública NBER de 2017. |
| Metodo | Scores ortogonais e cross-fitting. |
| Resultado | Sob condições de regularidade e taxas dos auxiliares, permite inferência assintótica. |
| Limitacoes | Não prova as hipóteses substantivas de identificação nem cobre automaticamente dependência geográfica. |
| Uso | Fundamentar ajuste cruzado e separar robustez estatística de identificação. |

## kennedy2023

Kennedy EH. Towards optimal doubly robust estimation of heterogeneous causal effects. arXiv:2004.14497, versão 5, 2023 (submissão inicial 2020).

DOI: [10.48550/arXiv.2004.14497](https://doi.org/10.48550/arXiv.2004.14497). [Fonte](https://arxiv.org/abs/2004.14497v5).

| Dimensão | Síntese |
| --- | --- |
| Problema | Estimar CATE com modelos auxiliares aprendidos. |
| Populacao | Classes de modelos não paramétricos; sem população clínica-alvo. |
| Dados | Teoria e simulações. |
| Metodo | Regressão em duas etapas sobre pseudo-desfecho duplamente robusto. |
| Resultado | Estabelece limites de erro e condições para eficiência oráculo. |
| Limitacoes | Condições teóricas não certificam o HGB específico nem o SINASC agrupado. |
| Uso | Base do DR-Learner; avaliação externa e interpretação exploratória. |

## chiang2022

Chiang HD, Kato K, Ma Y, Sasaki Y. Multiway Cluster Robust Double/Debiased Machine Learning. J Bus Econ Stat. 2022;40:1046–1056.

DOI: [10.48550/arXiv.1909.03489](https://doi.org/10.48550/arXiv.1909.03489). [Fonte](https://arxiv.org/abs/1909.03489).

| Dimensão | Síntese |
| --- | --- |
| Problema | ML causal sob amostragem agrupada. |
| Populacao | Ambientes com múltiplas dimensões de agrupamento. |
| Dados | Simulações e aplicação de demanda. |
| Metodo | Cross-fitting e inferência robusta a múltiplos clusters. |
| Resultado | Propõe divisão compatível com dependência e erros-padrão agrupados. |
| Limitacoes | A implementação municipal do projeto não é o estimador multiway do artigo. |
| Uso | Motivar separação geográfica; DOI listado é da versão pública arXiv. |

## cameron2015

Cameron AC, Miller DL. A Practitioner's Guide to Cluster-Robust Inference. J Hum Resour. 2015;50:317–372.

DOI: [10.3368/jhr.50.2.317](https://doi.org/10.3368/jhr.50.2.317). [Fonte](https://escholarship.org/uc/item/1jq5d0pq).

| Dimensão | Síntese |
| --- | --- |
| Problema | Incerteza com observações dependentes dentro de grupos. |
| Populacao | Dados agrupados em aplicações econométricas. |
| Dados | Exemplos, teoria e simulações. |
| Metodo | Inferência robusta a clusters e bootstrap. |
| Resultado | Ignorar dependência pode subestimar a incerteza; número e tamanhos dos grupos importam. |
| Limitacoes | Requer hipóteses sobre independência entre grupos e regularidade. |
| Uso | Explicar EP municipal e limites da sensibilidade geográfica. |

## snowden2018

Snowden JM, Bovbjerg ML, Dissanayake M, Basso O. The curse of the perinatal epidemiologist: inferring causation amidst selection. Curr Epidemiol Rep. 2018;5:379–387.

DOI: [10.1007/s40471-018-0172-x](https://doi.org/10.1007/s40471-018-0172-x). [Fonte](https://pmc.ncbi.nlm.nih.gov/articles/PMC6510491/).

| Dimensão | Síntese |
| --- | --- |
| Problema | Seleção nas transições da gestação ao nascimento. |
| Populacao | Populações reprodutivas e perinatais. |
| Dados | Revisão conceitual e exemplos causais. |
| Metodo | Diagramas causais e discussão de populações sob risco. |
| Resultado | Condicionar sobrevivência e marcos gestacionais pode comprometer contrastes causais. |
| Limitacoes | Não fornece uma correção identificada para esta extração do SINASC. |
| Uso | Delimitar o estimando aos registros selecionados e impedir extrapolação a concepções. |

[Manifesto de PDFs](MANIFESTO_ARTIGOS.md) · [Fichas](fichas/).
