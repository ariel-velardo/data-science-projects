# Fluxo dos dados

SINASC bruto → Parquet textual → filtros → população principal → X/T/Y → propensity → AIPW → robustez → DR-Learner.

Bruto: 2.389.325 registros.

| Etapa | Regra | Excluídos | Restantes |
| --- | --- | --- | --- |
| A0 | T conhecido e PESO numerico positivo | 81.079 | 2.308.246 |
| A1 | A0 + 500 g <= PESO <= 6.000 g | 3.471 | 2.304.775 |
| A2 | A1 + gestacao unica (GRAVIDEZ=1) | 53.205 | 2.251.570 |
| A3 | A2 + X principal preparado; missing tratado no pipeline | 0 | 2.251.570 |

Unidade: nascido vivo; chave `contador`, única nesta extração. Não há identificador longitudinal de mãe. T: meses 1–3 versus 4–9; Y: peso <2.500 g. X: idade, escolaridade, raça/cor, situação conjugal, paridade, perdas fetais e UF maternas.

O tempo zero é conceitual (início da gestação); o mês é retrospectivo. Outcome medido ao nascer em 2024. Consultas acumuladas, idade gestacional, parto e Apgar não entram em X. A amostra é selecionada por informação, sobrevivência e peso.

Propensity de cinco partições diagnostica suporte (Fase 1). AIPW usa três partições (Fase 2). Auditoria e partições municipais compõem a Fase 3. DR-Learner usa três papéis municipais disjuntos por rodada (Fase 4). Nada foi reestimado na Fase 5.

Fonte: `fase1_amostra.json`, campo `fluxo_amostra`. [Contrato e limitações](../METODOLOGIA_DO_PROJETO.md).
