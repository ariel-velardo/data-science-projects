# Guia de revisão

Roteiro para revisar a análise atual do projeto: início do pré-natal e baixo peso ao nascer, município de São Paulo, SINASC. Todos os notebooks estão salvos com as saídas; a revisão não exige executar nada nem dispor das bases.

## Em uma frase

Em 2024, entre 114.694 nascidos vivos elegíveis de mães residentes na capital paulista, o início do pré-natal nos meses 1–3 esteve associado a um risco de peso < 2.500 g **1,74 p.p. menor** (IC 95% bootstrap: −2,36 a −1,12) que o início nos meses 4–6, na população de sobreposição definida pelos pesos ATO. É uma **associação ajustada por covariáveis observadas**, não um efeito causal identificado.

## Sequência de leitura

| Ordem | Material | O que observar |
|---|---|---|
| 1 | [README do projeto](../README.md), seções 1–5 | pergunta, população, método, resultados e limitações em duas páginas |
| 2 | [RESUMO_PARA_REDACAO.md](sp_capital_ato/RESUMO_PARA_REDACAO.md) | consolidação de cada decisão e de cada número, com a fonte. O [PDF da Etapa 1](sp_capital_ato/PACOTE_REDACAO_ETAPA_1.pdf) é a versão já entregue, restrita à estimação de 2024 e anterior à retirada do SIM; não representa o estado atual do estudo. A [fonte da Etapa 2](sp_capital_ato/PACOTE_REDACAO_ETAPA_2_OVERLEAF/) incorpora os notebooks 04 e 05 |
| 3 | [01 — qualidade geográfica](../notebooks/principal/01_qualidade_geografica.ipynb) | por que São Paulo (capital): critério de preenchimento, sem olhar o desfecho |
| 4 | [02 — comparabilidade](../notebooks/principal/02_comparabilidade.ipynb) | desequilíbrio antes de qualquer ajuste e escore concentrado perto de 1 (≈ 91% em T=1), o que motivou o ATO em vez de IPW |
| 5 | [03 — estimação principal](../notebooks/principal/03_estimacao_ato.ipynb) | seção 2 (método); seção 3 (pesos, n efetivo e gráfico do escore); seção 4 (balanço e perfil da população-alvo); seção 5 (riscos com IC bootstrap); seção 7 (sensibilidade com situação conjugal) |
| 6 | [04 — série 2014–2024](../notebooks/principal/04_evolucao_historica.ipynb) | mesma especificação ano a ano; estimativas pontuais, sem IC anual; queda do grupo T=0 de 14,8% para 8,8% dos elegíveis |
| 7 | [05 — temporalidade e seleção](../notebooks/principal/05_temporalidade_prenatal.ipynb) | duração gestacional por mês de início e nascimentos excluídos antes do filtro de início; leitura descritiva |
| 8 | Diagnósticos complementares | Comparação de seis recortes de 2024 e justificativa em [`outputs/qualidade_geografica_2024/`](../outputs/qualidade_geografica_2024/RECOMENDACAO_RECORTE.md); tabelas anuais e de comparabilidade nos próprios notebooks 01 e 02 |
| 9 | Limitações | seção 5 do resumo e seções finais dos notebooks 03, 04 e 05 |

Os cinco notebooks principais são a fonte oficial das análises, dos gráficos e das interpretações, com 11 figuras em Plotly JSON e PNG de apoio nas saídas salvas.

Os CSVs duplicados de qualidade anual e comparabilidade foram removidos; nenhum deles é necessário à execução dos notebooks. Para referências antigas no material acadêmico preservado, consulte a [correspondência dos outputs](../outputs/README.md#correspondência-dos-outputs-removidos-no-lote-7c). As definições dos campos permanecem no [dicionário em Markdown](dados/DICIONARIO_ANALITICO_SINASC_2024.md).

Os gráficos são produzidos e armazenados nos próprios notebooks Jupyter. Para visualizá-los, utilize VS Code com suporte a Jupyter e Plotly, ou outro ambiente compatível. As representações PNG permanecem disponíveis como alternativa estática.

## O que foi realizado até o momento

- Escolha do recorte geográfico por qualidade de preenchimento (2024 e série 2014–2024), sem usar a associação com o desfecho.
- Diagnóstico de comparabilidade e de sobreposição antes da estimação, também sem o desfecho.
- Definição prévia das covariáveis do escore, com bloqueio automático de variáveis posteriores à exposição, e regra de suporte fixada antes de calcular riscos (nenhum registro excluído).
- Estimação ATO de 2024 com bootstrap de 1.000 réplicas, reestimando o escore em cada uma (todas convergiram).
- Diagnósticos de balanço (máximo |SMD| ajustado de 0,452 para 0,0031), de pesos (n efetivo de Kish 84.995 e 10.096) e de suporte.
- Sensibilidade com situação conjugal no escore: −1,63 p.p., estimativa pontual sem IC.
- Repetição da especificação em cada ano de 2014 a 2024 (diferença ATO negativa nos onze anos), de forma descritiva.
- Análise descritiva da relação entre duração gestacional, mês de início do pré-natal e seleção da população.

## O que permanece como limitação ou possível aprofundamento

Nenhum dos itens abaixo foi iniciado.

1. **Confundimento não medido:** quantificar a robustez da associação (por exemplo, valor E) e buscar um controle negativo defensável.
2. **Dependência entre observações:** bootstrap ou variância agrupada por estabelecimento de nascimento ou por região de residência; o IC atual trata os nascimentos como independentes.
3. **Incerteza da sensibilidade e da série:** a estimativa com situação conjugal e as estimativas anuais não têm IC, e não há teste de diferença entre anos.
4. **Conjunto de ajuste:** revisar com diagrama causal a situação conjugal (medida no parto) e campos possivelmente anteriores à exposição ainda não usados (`QTDGESTANT`, `QTDFILVIVO`, `IDADEPAI`, `CODOCUPMAE`).
5. **Temporalidade da exposição:** desenhos que reduzam a dependência entre duração gestacional e oportunidade de início tardio, sem condicionar em variáveis posteriores à exposição. A comparação com os meses 4–6 não demonstrou atenuar esse viés.
6. **Seleção por nascidos vivos:** se houver autorização e base adequada, vinculação individual SINASC–SIM, incluindo óbitos fetais; o estudo atual usa somente o SINASC.
7. **Generalização:** a população de sobreposição é mais jovem e menos escolarizada que o total; extensões para o estado de São Paulo teriam outra população-alvo.

## Onde a opinião do revisor seria mais útil

- Se o ATO é o estimando adequado para a pergunta, dado que a população-alvo difere da população total.
- Se a situação conjugal deveria entrar no ajuste principal, apesar de ser registrada no parto.
- Que estratégia de inferência com dependência é mais defensável para estes dados.
- Que desenho seria mais promissor para a questão da temporalidade da exposição (item 5).

## Fases anteriores, para contexto

O projeto começou com uma análise nacional de 2024 e evoluiu para a Entrega 1, uma série nacional 2014–2024 estimada com AIPW. Essas fases foram retiradas da árvore ativa; os materiais versionados da Entrega 1 permanecem no histórico Git, no commit `af30d8d`. A análise atual mudou população, estimando e estimador. Os números das fases não devem ser combinados; por exemplo, −1,48 p.p. nacional (AIPW, 2024) e −1,74 p.p. na capital (ATO, 2024) respondem a perguntas diferentes.

A revisão atual usa somente os cinco notebooks principais. Os registros preservados por dependência de código ou proveniência estão identificados no [índice de outputs](../outputs/README.md#proveniência-e-dependências-preservadas); não são resultados do estudo atual.

A reorganização de outubro de 2026 está documentada em [manutencao/ALTERACOES_REALIZADAS.md](manutencao/ALTERACOES_REALIZADAS.md).
