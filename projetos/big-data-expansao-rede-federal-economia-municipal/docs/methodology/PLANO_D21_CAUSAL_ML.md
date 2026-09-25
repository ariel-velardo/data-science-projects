# Plano D21 — extensão causal com Machine Learning

## Status

`D21_CAUSAL_ML_EXECUTADA = NAO`

Este plano registra somente uma frente futura. A escolha das famílias de
modelos não usa sinal, magnitude, intervalo ou significância observados na
D20C/D20D, e nenhum hiperparâmetro é selecionado a partir desses resultados.

## Objetivo futuro

Investigar extensões causais com Machine Learning que preservem o tratamento
escalonado, a temporalidade e o estimando causal explicitamente definido. A
frente deverá avaliar se modelos flexíveis para funções auxiliares (*nuisance
models*) melhoram robustez ou permitem estudar heterogeneidade de efeitos sem
converter desempenho preditivo em evidência causal.

## Requisitos metodológicos mínimos

- usar *cross-fitting* para reduzir sobreajuste nas funções auxiliares;
- separar modelos de outcome e de propensão/tratamento quando o estimador os
  exigir;
- distinguir estimadores *doubly robust* de Double Machine Learning: possuir
  uma propriedade duplamente robusta não torna automaticamente um método DML;
- respeitar adoção escalonada, coortes, calendário, grupo de comparação e
  event-time, sem reduzir o problema a um tratamento binário estático;
- usar somente covariáveis disponíveis antes do momento de decisão/tratamento;
- excluir mediadores e qualquer informação pós-tratamento das features;
- preservar validação de overlap, suporte, inferência, estabilidade e valor
  substantivo, além de métricas preditivas auxiliares;
- não usar Random Forest, XGBoost ou outro ML preditivo comum como prova de
  efeito causal.

## Famílias candidatas a investigar

- estimadores ortogonais/DML adaptados a painel e tratamento escalonado;
- learners flexíveis para componentes de outcome e propensão dentro de um
  estimador causal formal;
- métodos de CATE/uplift compatíveis com o desenho temporal, se o estimando e
  a unidade de decisão futura forem previamente definidos;
- árvores ou florestas causais somente após verificar compatibilidade com
  coortes, dependência longitudinal, inferência e tamanho efetivo de amostra.

## Gate

A D21 depende de revisão humana dos resultados e limitações D20C–D20E. Este
arquivo não escolhe algoritmo, hiperparâmetros, features finais, população ou
critério decisório e não autoriza iniciar a modelagem.
