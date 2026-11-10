# Matriz de rastreabilidade do painel

Arquivo gerado por `dashboard/construir.py`. NB 01 a NB 05 são os notebooks principais.

| Indicador | Fonte | Regra | Unidade | Denominador | Visualização |
|---|---|---|---|---|---|
| Nascimentos por recorte, 2024 | comparacao_recortes_2024.csv | Contagem por residência materna; recortes sobrepostos | registros | não se aplica | B: tabela e indicador por recorte |
| Variáveis essenciais válidas | comparacao_recortes_2024.csv | Mês 1–9, gravidez 1–3 e peso 500–6.000 g simultaneamente | % | Nascimentos do recorte | B: indicador por recorte |
| Mês de início válido | comparacao_recortes_2024.csv | Mês de início entre 1 e 9 | % | Nascimentos do recorte | B: indicador por recorte |
| Peso válido e gravidez válida | comparacao_recortes_2024.csv | Peso na faixa operacional; gravidez 1–3 | % | Nascimentos do recorte | B: indicador por recorte |
| Retenção na especificação B | comparacao_recortes_2024.csv | Elegíveis divididos pelos nascimentos | % | Nascimentos do recorte | B: indicador por recorte |
| Proporção de T=0 por recorte | comparacao_recortes_2024.csv | T=0 dividido pelos elegíveis | % | Elegíveis do recorte | B: indicador por recorte |
| Exclusões sequenciais por recorte | comparacao_recortes_2024.csv | Quatro etapas, mutuamente exclusivas | % e registros | Nascimentos do recorte | B: barras empilhadas |
| T=1 e T=0 por recorte | comparacao_recortes_2024.csv | Início nos meses 1–3 e 4–6 | registros | não se aplica | B: barras por grupo |
| Qualidade por variável e recorte | qualidade_variaveis_2024.csv | Válido quando há regra; preenchido quando a validade não é confirmada | % | Nascimentos do recorte | B: mapa de calor |
| Mês válido por ano | NB 01, célula 18 | Mês 1–9, capital, estado e restante | % | Nascimentos do recorte e do ano | B: linhas |
| Grupos por ano e recorte | NB 01, célula 21 | Especificação B em cada ano | registros | não se aplica | B: linhas |
| Retenção anual da capital | NB 01, célula 16 | Elegíveis divididos pelos nascimentos | % | Nascimentos da capital no ano | B: tabela anual |
| Consistência por campo | NB 01, célula 24 | Mínimo, máximo e vantagem sobre o restante do estado | % e p.p. | Nascimentos do recorte e do ano | B: tabela |
| Funil da população | comparacao_recortes_2024.csv, linha da capital | Subtrações sequenciais conferidas contra os elegíveis | registros | Nascimentos da capital (120.789) | C: funil e barras |
| Mês de início entre elegíveis | NB 05, célula 11 | Mês dividido pelo total | % | Elegíveis da capital em 2024 (114.694) | A: faixa da gestação; C: barras |
| Perfil materno por grupo | NB 02, célula 12 | Percentual em uma casa; contagens por categoria não exibidas | % | Grupo; total recalculado com os dois grupos | C: barras e tabela |
| Idade materna média e DP | NB 02, célula 12 | Valores salvos | anos | Grupo | C: indicador |
| População-alvo do ATO | NB 03, célula 20 | Médias e proporções brutas e ponderadas | % e anos | Grupo com pesos normalizados | D: tabela |
| SMD antes e depois do ATO | NB 03, célula 18 | SMD assinado com denominador não ponderado; exibido em módulo | adimensional | Grupos T=1 e T=0 | D: gráfico de balanço |
| SMD assinado pré-estimação | NB 02, célula 15 | Diagnóstico com situação conjugal, sem desfecho | adimensional | Grupos T=1 e T=0 | D: barras divergentes |
| Distribuição do escore, diagnóstico | NB 02, célula 22 | Fora da partição; caixas agrupadas até 0 ou pelo menos 10 registros | % do grupo | Grupo | D: histograma espelhado |
| Distribuição do escore e dos pesos, modelo final | NB 03, célula 15 | Mesma regra de agrupamento | % do grupo e % da soma dos pesos | Grupo; soma dos pesos do grupo | D: histograma espelhado |
| Percentis do escore | NB 02, célula 20; NB 03, célula 11 | Valores salvos | escore | Grupo | D: tabela |
| Regiões extremas do escore | NB 02, célula 20 | Limites fixos | registros e % | Grupo | D: tabela |
| Pesos e n efetivo | NB 03, célula 13 | Kish; pesos 1−e em T=1 e e em T=0 | peso, registros e % | Grupo | D: barras e tabela |
| Situação conjugal, diagnóstico | NB 03, célula 18 | Fora do modelo principal | adimensional | Grupos T=1 e T=0 | D: balanço por nível |
| Riscos brutos | NB 03, célula 22 | Casos divididos pelos nascimentos; IC bootstrap por percentis | % | Grupo | A e E: riscos |
| Riscos ponderados ATO | NB 03, célula 22 | Pesos normalizados no grupo; IC bootstrap por percentis | % | Soma dos pesos do grupo | A e E: riscos |
| Diferença bruta | NB 03, célula 22 | T=1 − T=0; IC bootstrap por percentis | p.p. | Grupos T=1 e T=0 | E: intervalos |
| Diferença ATO e IC 95% | NB 03, célula 22 | T=1 − T=0; 1.000 réplicas com reestimação do escore | p.p. | Grupos ponderados | A e E: intervalos |
| Conferência do bootstrap | NB 03, célula 22 | Erro-padrão, média das réplicas e intervalo normal | p.p. | 1.000 réplicas | E: comparação de intervalos |
| Sensibilidade com situação conjugal | NB 03, células 31 e 33 | Estimativa pontual, sem bootstrap e sem IC | p.p. e % | Grupos ponderados | E: gráfico e tabela |
| Diferença ATO anual | NB 04, células 19 e 27 | Modelo separado em cada ano; sem IC anual e sem teste entre anos | p.p. | Grupos ponderados do ano | F: linhas |
| Diferença bruta anual | NB 04, células 17 e 27 | T=1 − T=0 | p.p. | Grupos do ano | F: linhas |
| Riscos anuais brutos e ATO | NB 04, células 17 e 19 | Valores salvos | % | Grupo do ano | F: linhas |
| Elegíveis, T=1 e T=0 por ano | NB 04, célula 17 | Especificação B | registros | não se aplica | F: barras empilhadas |
| Início tardio (T=0) por ano | NB 04, células 17 e 29 | T=0 dividido pelos elegíveis | % | Elegíveis do ano | F: linha |
| Totais do período selecionado | NB 04, célula 17 | Soma de anos disjuntos; percentual recalculado sobre a soma de elegíveis | registros e % | Elegíveis do período | F: indicadores |
| Diagnósticos anuais | NB 04, células 19, 21, 23 e 24 | Balanço, suporte, pesos e n efetivo do modelo anual | vários | Grupo do ano | F: gráfico e tabela |
| Início nos meses 4–6 por duração | NB 05, célula 11 | Faixas agrupadas: < 28, 28–31, 32–36 e ≥ 37 semanas | % | Nascimentos da faixa | G: barras empilhadas |
| Baixo peso por duração | NB 05, célula 18 | Mesmas faixas agrupadas | % | Nascimentos da faixa | G: barras |
| Baixo peso por mês de início | NB 05, célula 20 | Parcelas pré-termo e a termo | % | Nascimentos do mês com duração conhecida | G: barras empilhadas |
| Incluídos e excluídos pelo início | NB 05, célula 28 | Antes do filtro de início; células de 1 a 9 exibidas como < 10; linhas 7–9 e ausente com contagens em múltiplos de 10 e percentuais inteiros | registros e % | Linha da tabela | G: barras e tabela |
| Início ausente ou ignorado | RESUMO_PARA_REDACAO.md, seção 10 | Campo ausente e código 99 | registros | Antes do filtro (117.422) | G: texto |
| DAG conceitual | fig4_dag.tex; DAG_INICIAL.md | Hipótese de trabalho, sem estimação | não se aplica | não se aplica | G: diagrama |
