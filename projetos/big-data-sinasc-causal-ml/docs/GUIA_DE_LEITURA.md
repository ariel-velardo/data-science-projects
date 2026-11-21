# Guia de leitura

Roteiro de leitura da análise atual do projeto sobre o início do pré-natal e o baixo peso ao nascer no município de São Paulo, com dados do SINASC. Todos os notebooks estão salvos com as saídas, e a leitura não exige executar nada nem dispor das bases.

## Em uma frase

Em 2024, entre 114.694 nascidos vivos elegíveis de mães residentes na capital paulista, o início do pré-natal nos meses 1–3 esteve associado a um risco de peso < 2.500 g **1,74 p.p. menor** que o início nos meses 4–6 (IC 95% bootstrap: −2,36 a −1,12). A estimativa vale para a população de sobreposição definida pelos pesos ATO. É uma **associação ajustada por covariáveis observadas**, não um efeito causal identificado.

## Sequência de leitura

| Ordem | Material | O que observar |
|---|---|---|
| 1 | [Relatório de análises estatísticas](relatorio_analises_comentadas/README.md) (PDF, 10 páginas) | Visão completa das análises: população, peso ao nascer (Welch), regressão logística (equação, variáveis, razões de chances, avaliação preditiva e SHAP), ATO e limitações |
| 2 | [README do projeto](../README.md), seções 1–5 | Pergunta, população, método, resultados e limitações |
| 3 | [RESUMO_PARA_REDACAO.md](sp_capital_ato/RESUMO_PARA_REDACAO.md) | Consolidação de cada decisão e de cada número, com a fonte. Ver também a nota sobre o material acadêmico, abaixo da tabela |
| 4 | [01 — qualidade geográfica](../notebooks/principal/01_qualidade_geografica.ipynb) | Por que São Paulo (capital): critério de preenchimento, sem olhar o desfecho |
| 5 | [02 — comparabilidade](../notebooks/principal/02_comparabilidade.ipynb) | Desequilíbrio antes de qualquer ajuste e escore concentrado perto de 1 (≈ 91% em T=1), o que motivou o ATO em vez de IPW |
| 6 | [03 — estimação principal](../notebooks/principal/03_estimacao_ato.ipynb) | Seções 2 (método), 3 (pesos, n efetivo e gráfico do escore), 4 (balanço e perfil da população-alvo), 5 (riscos com IC bootstrap, inclusive agrupado por estabelecimento) e 7 (sensibilidade com situação conjugal) |
| 7 | [04 — série 2014–2024](../notebooks/principal/04_evolucao_historica.ipynb) | Mesma especificação ano a ano; estimativas pontuais, sem IC anual; queda do grupo T=0 de 14,8% para 8,8% dos elegíveis |
| 8 | [05 — temporalidade e seleção](../notebooks/principal/05_temporalidade_prenatal.ipynb) | Duração gestacional por mês de início e nascimentos excluídos antes do filtro de início; leitura descritiva |
| 9 | [06 — regressão logística e peso ao nascer](../notebooks/principal/06_analise_preditiva_e_peso.ipynb) | Seções:<br>1. variáveis e equação do modelo;<br>2. razões de chances ajustadas e coeficientes;<br>3. peso em gramas por mês de início (Welch);<br>4. avaliação preditiva fora da amostra;<br>5. valores SHAP;<br>6. limitações.<br>Associação, previsão e interpretabilidade, não estimação causal; não altera o ATO |
| 10 | Diagnósticos complementares | Comparação de seis recortes de 2024 e justificativa em [`outputs/qualidade_geografica_2024/`](../outputs/qualidade_geografica_2024/RECOMENDACAO_RECORTE.md); tabelas anuais e de comparabilidade nos próprios notebooks 01 e 02 |

**Material acadêmico das Etapas 1 e 2.**
- O [PDF da Etapa 1](sp_capital_ato/PACOTE_REDACAO_ETAPA_1.pdf) é o documento acadêmico já apresentado. Restringe-se à estimação de 2024, é anterior à retirada do SIM e não representa o estado atual do estudo.
- A [fonte da Etapa 2](sp_capital_ato/PACOTE_REDACAO_ETAPA_2_OVERLEAF/) incorpora os notebooks 04 e 05. Seu PDF é compilado fora do repositório.
- O material da Etapa 2 usa a numeração anterior dos notebooks (tabela abaixo).

### Numeração dos notebooks no material da Etapa 2

O PDF e a fonte LaTeX da Etapa 2 foram produzidos antes da renumeração dos notebooks e citam os nomes antigos. A renumeração não alterou cálculos nem resultados.

| Citado no material da Etapa 2 | Notebook atual | Conteúdo |
|---|---|---|
| `05a_qualidade_geografica_sp_2014_2024.ipynb` | [01_qualidade_geografica.ipynb](../notebooks/principal/01_qualidade_geografica.ipynb) | qualidade geográfica e escolha do recorte |
| `05b_comparabilidade_sp_capital_2024.ipynb` | [02_comparabilidade.ipynb](../notebooks/principal/02_comparabilidade.ipynb) | comparabilidade e escore de propensão |
| `06_ato_sp_capital_2024.ipynb` | [03_estimacao_ato.ipynb](../notebooks/principal/03_estimacao_ato.ipynb) | estimação ATO de 2024 e sensibilidade |
| `07_evolucao_ato_sp_capital_2014_2024.ipynb` | [04_evolucao_historica.ipynb](../notebooks/principal/04_evolucao_historica.ipynb) | série 2014–2024 |
| `08_temporalidade_prenatal_sp_capital_2024.ipynb` | [05_temporalidade_prenatal.ipynb](../notebooks/principal/05_temporalidade_prenatal.ipynb) | temporalidade e seleção |

Os seis notebooks principais são a fonte oficial das análises, dos gráficos e das interpretações, com 19 figuras em Plotly JSON e PNG de apoio nas saídas salvas. O 06 é posterior ao material da Etapa 2 e não é citado nele.

Os gráficos ficam armazenados nos próprios notebooks Jupyter. Para visualizá-los, use o VS Code com suporte a Jupyter e Plotly, ou outro ambiente compatível; as representações PNG servem como alternativa estática.

As tabelas anuais de qualidade e de comparabilidade são calculadas nos notebooks 01 e 02. Para citações antigas no material acadêmico, consulte a [correspondência dos outputs](../outputs/README.md#correspondência-dos-outputs-removidos). As definições dos campos estão no [dicionário em Markdown](dados/DICIONARIO_ANALITICO_SINASC_2024.md).

## Análises realizadas

- **Recorte geográfico:** escolha por qualidade de preenchimento (2024 e série 2014–2024), sem usar a associação com o desfecho.
- **Comparabilidade:** diagnóstico de comparabilidade e de sobreposição antes da estimação, também sem o desfecho.
- **Especificação do escore:**
  - covariáveis definidas previamente, com bloqueio automático de variáveis posteriores à exposição;
  - regra de suporte fixada antes de calcular os riscos (nenhum registro excluído).
- **Estimação ATO de 2024:** bootstrap de 1.000 réplicas, com reestimação do escore em cada uma (todas convergiram), e sensibilidade com reamostragem agrupada por estabelecimento.
- **Diagnósticos de balanço e de pesos:**
  - máximo |SMD| ajustado de 0,452 para 0,0031;
  - n efetivo de Kish de 84.995 e 10.096;
  - suporte comum.
- **Sensibilidade com situação conjugal no escore:** −1,63 p.p., estimativa pontual sem IC.
- **Série 2014–2024:** a mesma especificação repetida em cada ano, de forma descritiva; a diferença ATO é negativa nos onze anos.
- **Temporalidade e seleção:** análise descritiva da relação entre duração gestacional, mês de início do pré-natal e seleção da população.
- **Notebook 06:**
  - comparação do peso ao nascer em gramas (Welch);
  - regressão logística do baixo peso, com equação, dicionário das variáveis e razões de chances com IC;
  - avaliação preditiva fora da amostra e calibração;
  - interpretabilidade por valores SHAP.

## Limitações e possíveis aprofundamentos

Os itens abaixo não foram executados.

1. **Confundimento não medido:** quantificar a robustez da associação (por exemplo, valor E) e buscar um controle negativo defensável.
2. **Dependência entre observações:**
   - a sensibilidade com reamostragem agrupada por estabelecimento existe apenas para a diferença ATO de 2024;
   - nas demais análises, os IC tratam os nascimentos como independentes;
   - a dependência por região de residência não foi avaliada.
3. **Incerteza da sensibilidade e da série:** a estimativa com situação conjugal e as estimativas anuais não têm IC, e não há teste de diferença entre anos.
4. **Conjunto de ajuste:** revisar, com diagrama causal, a situação conjugal (medida no parto) e os campos possivelmente anteriores à exposição ainda não usados (`QTDGESTANT`, `QTDFILVIVO`, `IDADEPAI`, `CODOCUPMAE`).
5. **Temporalidade da exposição:** buscar desenhos que reduzam a dependência entre duração gestacional e oportunidade de início tardio, sem condicionar em variáveis posteriores à exposição. A comparação com os meses 4–6 não demonstrou atenuar esse viés.
6. **Seleção por nascidos vivos:** vincular individualmente SINASC e SIM, incluindo óbitos fetais, se houver autorização e base adequada. O estudo atual usa somente o SINASC.
7. **Generalização:** a população de sobreposição é mais jovem e menos escolarizada que o total; extensões para o estado de São Paulo teriam outra população-alvo.
8. **Métricas preditivas e SHAP:** as métricas de desempenho e as importâncias SHAP não têm IC (bootstrap não realizado).

## Questões metodológicas em aberto

- **Estimando:** o ATO é adequado para a pergunta, dado que a população-alvo difere da população total?
- **Situação conjugal:** deveria entrar no ajuste principal, apesar de ser registrada no parto?
- **Dependência:** que estratégia de inferência com dependência entre nascimentos é mais defensável para estes dados?
- **Temporalidade da exposição:** que desenho seria mais promissor para essa questão (item 5)?

## Escopo anterior do projeto

O projeto começou com uma análise nacional de 2024 e passou depois por uma série nacional 2014–2024 estimada com AIPW (Entrega 1). Essas fases foram retiradas da árvore ativa, e os materiais versionados da Entrega 1 permanecem no histórico Git, no commit `af30d8d`.

A análise atual mudou a população, o estimando e o estimador. Os números das fases não devem ser combinados: por exemplo, −1,48 p.p. nacional (AIPW, 2024) e −1,74 p.p. na capital (ATO, 2024) respondem a perguntas diferentes.

A análise atual usa somente os seis notebooks principais. Os registros preservados por dependência de código ou por proveniência estão identificados no [índice de outputs](../outputs/README.md#proveniência-e-dependências-preservadas) e não são resultados do estudo atual.
