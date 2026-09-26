# Auditoria dirigida do gate de influência — Fase 3

Data: 26/09/2026. Escopo: revisão metodológica dirigida, não sistemática. O gate histórico `RESULTADO_NAO_INTERPRETAVEL` permanece intacto. Esta revisão avalia o fundamento do critério, sem selecionar uma conclusão pelo sinal ou pela significância do AIPW.

## Resposta à questão central

**Não foi localizada, nas referências examinadas, recomendação formal para declarar um AIPW inválido porque o top 1% de |IF| concentra mais de 50% de IF².** Isso é uma conclusão limitada à busca dirigida, não prova de inexistência em toda a literatura. O número 50% do projeto é uma heurística de alerta. Não é teste de identificação causal, de positividade, de normalidade assintótica ou de cobertura.

Buscas incluíram AIPW/influence function/variance concentration/rare outcomes, positivity/near positivity/effective sample size, cluster robust asymptotically linear estimators e clustered cross-fitting. As consultas literais `"influence function" "top 1%" "50%" AIPW` e `"influence function" "50%" "concentration"` não localizaram uma justificativa metodológica específica para esse gate. Fontes de ensino informal não foram usadas como autoridade para o limiar. Alguns acessos diretos ao PMC retornaram bloqueio de navegador; foram consultados os trechos indexados dos artigos e registros dos autores/periódicos. Isso limita alegações de leitura integral de todas as fontes.

## Recomendações formais, heurísticas e aplicação própria

| Tema | Base formal ou recomendação publicada | Uso nesta auditoria |
|---|---|---|
| AIPW | Score ortogonal e expansão assintoticamente linear; condições de identificação, momentos e taxas dos nuisances [1–3] | Recalcular score, centralização e SE; dupla robustez de consistência não basta para inferência Wald |
| Positividade | Probabilidades muito próximas de 0/1 podem gerar instabilidade e viés; suporte é dependente do alvo/modelo [4,5,11] | Examinar e, pesos observados, ESS, trimming e C3; não certificar suporte por AUC |
| Concentração | Influência descreve sensibilidade local; a distribuição individual da IF não precisa ser normal [2,3] | Curva completa, máximo individual e agregados; o corte 50% é do projeto |
| Outcome pouco frequente | Informação depende também da variância da IF e da raridade; N isoladamente pode ser enganoso [7] | Examinar combinação Y=1 e grupo minoritário; não chamar todo registro influente de erro |
| Clusters | Dependência intracluster exige agregar os scores; muitos clusters e condições sobre tamanhos/importância são relevantes [8,9] | Sandwich por CODMUNRES, diagnóstico de cluster dominante e bootstrap |
| Cross-fitting | As divisões devem respeitar a estrutura de dependência [10] | Três folds sem CODMUNRES compartilhado; não implementar multiway DML neste projeto |
| ESS | `(sum w)^2 / sum(w^2)` é diagnóstico de dispersão de pesos [6] | Reportar por tratamento; não tratá-lo como tamanho efetivo completo do AIPW agrupado |
| Seleção perinatal | Condicionar nascimento/sobrevivência ou intermediários pode abrir caminhos de seleção [12,13] | Auditoria separada do estimando; estabilidade estatística não resolve seleção |

## Derivação própria: por que um percentual fixo não testa o CLT

Para a média de um Bernoulli de probabilidade 0,01, a IF verdadeira é `Y−0,01`. Os eventos representam 1% da população e respondem por 99% da variância. Ainda assim, a IF é limitada, a variância é finita e o CLT iid se aplica quando N cresce. A distribuição da IF individual é discreta, não normal; o limite normal relevante é o da média normalizada. Um Q-Q plot de IF não testa a validade desse limite.

Um contraexemplo diretamente AIPW usa tratamento aleatório com `e=0,85`, `m0=0,08`, `m1=0,07`, efeito verdadeiro `−0,01`. Com nuisances oráculo, a IF é a correção residual e:

`Var(IF) = 0,07×0,93/0,85 + 0,08×0,92/0,15 ≈ 0,567255`.

Controles com Y=1 correspondem a 1,2% da população e têm `|IF|=0,92/0,15`. Logo o 1% mais extremo responde, no limite, por aproximadamente

`0,01×(0,92/0,15)² / Var(IF) ≈ 66,3%`.

Há overlap, efeito conhecido e IF limitada. Esse cálculo é uma **derivação do projeto**, não um limiar alternativo retirado de um artigo. Refuta a interpretação universal do gate; não prova que o SINASC satisfaz as hipóteses. A simulação S1–S4 complementa a derivação com cobertura e erro Monte Carlo.

Para uma sequência iid com momentos adequados, ausência de dominância de uma única contribuição e condições de Lindeberg são conceitos diferentes da participação de uma fração fixa de 1%. Máximo `IF²/sum(IF²)` pequeno é evidência descritiva útil, não um teste suficiente de todas as condições. Sob dependência, a unidade relevante passa a ser o score agregado do cluster.

## Fórmulas adotadas na Fase 3

`psi_i = m1_i−m0_i + T_i(Y_i−m1_i)/e_i − (1−T_i)(Y_i−m0_i)/(1−e_i)`.

`theta = sum(psi_i)/N`, `IF_i=psi_i−theta`, `SE_iid²=sum(IF_i²)/[N(N−1)]`.

Com `G` códigos de residência e `U_g=sum_{i em g} IF_i`, a sensibilidade sandwich é:

`SE_cluster² = [G/(G−1)] × sum_g(U_g²)/N²`.

A derivada do momento `psi−theta` em theta é −1. A correção finita é exatamente `G/(G−1)`, sem fator adicional por número de features. O intervalo usa `t_(G−1,0,975)`. A média continua ponderada por nascido vivo; não é a média não ponderada das médias municipais. Se cada cluster contém um registro, a fórmula recupera o SE iid amostral. Isso é testado analiticamente.

O bootstrap sorteia G clusters com reposição e igual probabilidade. A estimativa de cada réplica é a razão entre soma dos pseudo-outcomes sorteados e soma de seus tamanhos, com N* variável. São 500 réplicas e seed fixa. Mantém nuisances e regra de trimming fixos: não incorpora sua incerteza completa. Sandwich aplicado aos folds aleatórios é uma sensibilidade condicional; não corrige retrospectivamente a separação treino/validação inadequada à dependência. O cross-fitting geográfico é outra análise, com novos ajustes.

Independência entre municípios continua sendo hipótese. Dependência espacial entre municípios, mães não identificadas e erro de mensuração permanecem. Bootstrap e correção finita não resolvem esses problemas.

## Referências selecionadas e contribuição específica

1. Funk MJ, Westreich D, Wiesen C, Stürmer T, Brookhart MA, Davidian M (2011). *Doubly robust estimation of causal effects*. American Journal of Epidemiology 173:761–767. [Registro dos autores e DOI](https://scholars.duke.edu/publication/805658). Fundamenta a combinação de outcome e propensity e a propriedade de dupla robustez; não estabelece o corte top1/50.
2. Kennedy EH (2016). *Semiparametric theory and empirical processes in causal inference*. Capítulo em Statistical Causal Inferences and Their Applications in Public Health Research. [Versão do autor](https://arxiv.org/abs/1510.04740). Fundamenta IF, variância assintótica e condições para nuisances flexíveis.
3. Chernozhukov V et al. (2018). *Double/debiased machine learning for treatment and structural parameters*. The Econometrics Journal 21:C1–C68. [NBER e versão publicada](https://www.nber.org/papers/w23564). Ortogonalidade e cross-fitting reduzem viés de regularização; os resultados requerem condições, não apenas N elevado.
4. Petersen ML, Porter KE, Gruber S, Wang Y, van der Laan MJ (2012). *Diagnosing and responding to violations in the positivity assumption*. Statistical Methods in Medical Research 21:31–54. [Artigo](https://pmc.ncbi.nlm.nih.gov/articles/PMC4107929/). Positividade prática, diagnóstico e mudanças de alvo; sparsidade pode gerar viés sem aumento proporcional de variância.
5. Austin PC, Stuart EA (2015). *Moving towards best practice when using inverse probability of treatment weighting (IPTW) using the propensity score to estimate causal treatment effects in observational studies*. Statistics in Medicine 34:3661–3679. [Artigo](https://pmc.ncbi.nlm.nih.gov/articles/PMC4626409/). Diagnósticos de pesos e equilíbrio; resultados observacionais exigem mais que uma AUC de propensity.
6. WeightIt. *Compute effective sample size of weighted sample*. [Documentação oficial CRAN](https://search.r-project.org/CRAN/refmans/WeightIt/html/ESS.html). Documenta a fórmula de ESS; referência técnica, não artigo demonstrando validade do AIPW.
7. Balzer L, Ahern J, Galea S, van der Laan M (2016). *Estimating Effects with Rare Outcomes and High Dimensional Covariates: Knowledge is Power*. Epidemiologic Methods 5:1–18. [Artigo](https://pmc.ncbi.nlm.nih.gov/articles/PMC5436729/). Informação e variância da IF com eventos raros; discute TMLE, não prescreve nossa heurística nem autoriza transferir garantias para qualquer AIPW.
8. Cameron AC, Miller DL (2015). *A Practitioner's Guide to Cluster-Robust Inference*. Journal of Human Resources 50:317–372. [Versão institucional](https://escholarship.org/uc/item/1jq5d0pq). Dependência dentro dos clusters, aproximação com muitos clusters e limites de correções/bootstraps.
9. MacKinnon JG, Nielsen MØ, Webb MD (2023). *Cluster-robust inference: A guide to empirical practice*. Journal of Econometrics 232:272–299. [Artigo](https://doi.org/10.1016/j.jeconom.2022.04.001). Heterogeneidade de tamanhos/importância e bootstrap; a seção de pairs bootstrap explicita o N* variável.
10. Chiang HD, Kato K, Ma Y, Sasaki Y (2022). *Multiway Cluster Robust Double/Debiased Machine Learning*. Journal of Business & Economic Statistics 40:1046–1056. [Manuscrito dos autores](https://arxiv.org/abs/1909.03489). Cross-fitting e inferência compatíveis com clusters; usado como fundamento, sem alegar equivalência exata ao algoritmo multiway.
11. Crump RK, Hotz VJ, Imbens GW, Mitnik OA (2009). *Dealing with limited overlap in estimation of average treatment effects*. Biometrika 96:187–199. [Repositório do autor](https://dash.harvard.edu/entities/publication/73120378-86bc-6bd4-e053-0100007fdf3b). Trimming troca a população estimada por precisão/suporte; sua regra aproximada depende de condições e não é regra universal.
12. Snowden JM, Bovbjerg ML, Dissanayake M, Basso O (2018). *The curse of the perinatal epidemiologist: inferring causation amidst selection*. Current Epidemiology Reports 5:379–387. [Registro institucional dos autores](https://pdxscholar.library.pdx.edu/sph_facpub/253/). Seleção e sobrevivência ao longo do processo reprodutivo podem comprometer interpretações de contrastes entre nascidos vivos.
13. Chiu YH, Stensrud MJ, Dahabreh IJ, Rinaudo P, Diamond MP, Hsu J, Hernández-Díaz S, Hernán MA (2020). *The Effect of Prenatal treatments on offspring events in the presence of competing events: an application to a randomized trial of fertility therapies*. Epidemiology 31:636–643. [Artigo](https://pmc.ncbi.nlm.nih.gov/articles/PMC7755108/). Distingue associações condicionais em nascidos vivos de efeitos em estratos principais; esses alvos não são identificados automaticamente nesta base.

## Implicação para o projeto

O gate de 50% deve ser preservado como decisão histórica de governança. A revisão adicional deve usar reconciliação, perfil dos extremos, estabilidade geográfica, dependência e sensibilidades. Nenhuma alteração de gate elimina confundimento não observado, seleção ou ambiguidade temporal. Não se escolhe uma especificação por produzir um efeito desejado.
