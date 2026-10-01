# Plano técnico do notebook 09 — AIPW anual SINASC 2014–2024

**Estado:** `PLANO_NOTEBOOK_09_CONCLUIDO`. Documento para revisão humana; nenhum notebook 09 ou efeito temporal foi produzido. A sequência 06–08C e a PoC Spark independente estão em [EXPANSAO_TEMPORAL.md](EXPANSAO_TEMPORAL.md).

## 1. Objetivo

Estimar, separadamente em cada ano, como varia o contraste AIPW entre início do pré-natal até o terceiro mês (`T=1`) e início posterior (`T=0`) no risco de baixo peso ao nascer (`Y=1`). Descrever estabilidade de sinal e magnitude em 2014–2024 sob especificações congeladas. O notebook começa pelos anos independentes; não faz pooled nem escolhe janela, modelo ou recorte pelo efeito observado.

## 2. Estimando

Para cada ano, diferença média de risco em pontos percentuais entre os desfechos potenciais sob `T=1` e `T=0` na população principal elegível daquele ano (nascidos vivos SINASC que passam pelo fluxo A0–A3). Unidade: registro de nascido vivo; chave de controle `(ano, UF_RESIDENCIA, CONTADOR)`; momento conceitual da decisão: início da gestação; Y é aferido ao nascimento. O estimando é anual e sua população pode mudar entre anos. Interpretação causal depende de consistência, ausência de confundimento não medido, positividade, mensuração e seleção defensáveis; a dupla robustez não resolve essas ameaças. Consultas acumuladas, idade gestacional, parto, Apgar e qualquer variável após a decisão não entram nas sete X pré-tratamento certificadas (`src.diagnosticos.COLUNAS_PROPENSITY_PRINCIPAL`).

## 3. Janelas

Principal: **2014–2024**, contrato v1.1 com harmonização H1 da chave. Sensibilidade obrigatória: **2018–2024**, contrato v1 estrito. Ambas usam os mesmos resultados anuais de 2018–2024, mas são apresentadas integralmente e com seus contratos de admissão. Não selecionar a janela pelo resultado. Ler `outputs/temporal/contrato_temporal.json` e conferir os vereditos anuais antes do primeiro fit.

## 4. Especificações

| Código histórico | Propensity | Outcomes `m0`, `m1` | Papel |
|---|---|---|---|
| C1 | logística L2, `C=1` | logística histórica por braço | principal |
| C2 | mesma logística L2, `C=1` | HGB histórico por braço | principal alternativa de outcome |
| C3 | HGB histórico | mesmos HGB históricos de C2 | sensibilidade de propensity |

Nomes confirmados em `src/inferencia_causal.py` e `src/robustez.py`: C3 troca somente `e`, sem alterar folds ou outcomes C2. O benchmark 08C é preditivo; `BENCHMARK_NUISANCE_2024_PARCIAL` e a aprovação humana da pendência ExtraTrees não transformam melhora preditiva em melhora causal. Não usar ExtraTrees como outcome, não criar outcome tunado e não renomear C1/C2/C3.

## 5. Propensity principal

Usar `src.modelagem_preditiva.criar_modelo('logistica')`, com `C=1`, sete X e pré-processamento ajustado dentro de cada treino. Ajustar do zero em cada ano e fold; nunca transferir coeficientes de 2024 nem fazer tuning anual. Verificar em OOF log-loss, Brier, calibração, AUC, SMD, ESS, quantis, extremos e caudas, mantendo métricas preditivas separadas da estimativa AIPW.

## 6. Sensibilidade HGB do propensity

Usar a configuração histórica de `criar_modelo('hgb')` de 2024, sem busca anual. Antes do AIPW C3 de cada ano de 2014–2023, auditar OOF da mesma configuração com log-loss, Brier, calibração, AUC, maior `|SMD|` ponderado, ESS por braço e fração fora de `[0,05; 0,95]`; reportar também extremos de `e`. Registrar qualquer falha grave de suporte com ano e evidência, sem alterar hiperparâmetros nem suprimir o ano. C1/C2 não dependem de aprovação preditiva do HGB.

## 7. Outcomes

Em cada ano e fold, ajustar `m0` e `m1` separadamente nos registros dos respectivos braços, para a logística histórica e o HGB histórico. Predizer ambas as funções em toda a validação OOF. Reusar as mesmas predições HGB em C2 e C3. Reportar métricas preditivas por braço, inclusive prevalência, calibração e convergência. Não escolher outcome com base no efeito estimado.

## 8. Cross-fitting

Preservar OOF: cada registro recebe uma única predição de cada nuisance, gerada por fit sem esse registro. Para o AIPW histórico, `src.inferencia_causal.gerar_folds` usa estratos conjuntos `2*T+Y`; o preprocessing é ajustado dentro do treino. Conferir ausência de interseção treino/validação, cobertura exatamente 1, probabilidades finitas, chaves/ordem e hash dos índices por fold. Não misturar anos nos folds. Os cinco folds do notebook 08 pertencem ao **diagnóstico de overlap** e não substituem os três folds do AIPW.

## 9. Folds

Três folds estratificados por `T,Y` para C1/C2/C3, como na Fase 2 e no C3 da Fase 3 de 2024. Fixar a partição uma vez por ano e compartilhar entre especificações; confirmar que cada estrato `T,Y` suporta os três folds e que ambos os braços e classes de Y estão presentes no treino. O benchmark aninhado 08B/08C tem folds internos adicionais apenas para seleção preditiva de 2024; eles não entram no 09.

## 10. Seeds

Seed histórica `20240925` (`src.inferencia_causal.SEED`, `src.robustez.SEED`, `src.modelagem_preditiva.SEED`). Registrar versões de NumPy, scikit-learn, DuckDB e código. Repetição determinística de folds e hashes é teste de retomada. Não mudar seed por ano para melhorar métricas; qualquer alteração futura exige novo contrato antes dos efeitos.

## 11. Ordenação

Em 2024, conferir a ordem usada nos caches AIPW certificados da Fase 2 (`ORDER BY contador` em `src.amostra.carregar_amostra`) e a identidade por `contador`/`fold_id` antes de reutilizá-los. A ordem física certificada do notebook 08 é um contrato diagnóstico distinto. Em 2014–2023, usar a ordem determinística da camada temporal por `(ano, UF_RESIDENCIA, CONTADOR)`, respeitando sua ordenação SQL de `CONTADOR` como texto (`src.temporal.carregar_amostra_temporal`). A chave identifica registros; a ordem fixa a atribuição de folds. Guardar hash da sequência de chaves e dos índices OOF.

## 12. Trimming

Estimativa principal **sem trimming**, como as linhas principais C1/C2 da Fase 2. Sensibilidade fixa `[0,05; 0,95]` para C1/C2/C3, já usada em `src.robustez.resumo_predicoes`; `[0,01; 0,99]` pode ser exibida como diagnóstico de suporte do notebook 08 e como comparação histórica C1/C2, sem virar uma regra escolhida por efeito. Para cada recorte, publicar N excluído e nova população alvo: o recorte altera o estimando. Sem clipping silencioso. Congelar qualquer ampliação dessas regras antes de calcular efeitos anuais.

## 13. Inferência

A Fase 2 calculou erro-padrão pela dispersão da influência AIPW sob hipótese iid (`src.inferencia_causal.calcular_aipw`), com ressalva explícita de que o IC é aproximado e condicional ao suporte aprendido. A Fase 3 calculou também erro-padrão agrupado por `CODMUNRES` e IC com quantil t de `G-1` graus de liberdade (`src.robustez.resumo_cluster`). Planejar o IC municipal como leitura principal prudente do 09, exibindo o iid histórico como referência e sem afirmar independência perfeita de milhões de linhas. Conferir disponibilidade e validade de `CODMUNRES` em cada ano, número e tamanhos de clusters e concentração da variância. Bootstrap municipal de nuisances fixos existe na Fase 3, mas não é exigido nem acionado automaticamente; não refaz o ajuste ML e não capta toda a incerteza. Uma mudança de método de inferência exige revisão antes da implementação.

## 14. IC

Reportar estimativa e SE em pontos percentuais e IC95% municipal via t (`G-1`) quando os clusters forem válidos, mais IC95% iid para reconciliação histórica. Em 2024, comparar C1/C2 sem trimming com `outputs/diagnostics/fase2_aipw.json` e comparar a inferência municipal com a Fase 3, usando tolerâncias certificadas. ICs anuais sobrepostos não constituem teste de igualdade entre anos; eventual teste de tendência ou contraste 2021–2022 precisa de hipótese e método pré-especificados.

## 15. Outputs

Tabela agregada, uma linha por `(ano, especificacao, trimming)`: ano, janela/contrato, N, n tratado, n controle, N excluído, estimativa AIPW, SE iid e municipal, IC95% respectivos, clusters, fração em caudas, ESS tratado e controle (absoluto e relativo), propensity mínimo/máximo, diagnóstico de overlap, modelos de propensity/outcome, regra de trimming, hashes e status de execução/convergência. Acrescentar tabela anual de auditoria dos nuisances e manifesto de execução com limitação conhecida e próximo passo. Não versionar OOF individuais, pseudo-outcomes, checkpoints pesados ou Parquets.

## 16. Plotly

Aplicar `src.visualizacao.aplicar_tema_ipt` a todos os gráficos. Prever até cinco figuras: AIPW anual com IC; C1 versus C2; C3 versus C2; N/ESS por ano se necessário; estimativa versus suporte somente se trouxer contexto interpretável. Diferenciar janelas e trimming por legenda/aba, com eixo em pontos percentuais e nota de que os ICs não testam diferenças temporais. Não reconstruir gráficos aprovados do 08C.

## 17. Caches

Propor caches locais reiniciáveis por `(ano, especificacao, fold, modelo)`, em diretório novo exclusivo do 09. O contrato de cada cache deve incluir SHA-256 do Parquet anual, sequência de chaves e ordem, N/T/Y, sete features e schema, seed, índices de treino/validação, preprocessing, parâmetros do modelo, versão de bibliotecas e hash do código. Validar hash e cobertura antes de ler; falha de contrato interrompe o ano sem sobrescrever o cache. Os caches 2024 históricos de Fases 2/3 e 08B/08C ficam intactos. Materializar somente arrays e metadados necessários, fora do Git.

## 18. Custo inicial

Por ano sem cache: **18 fits OOF** = 3 folds × [1 propensity logístico + 2 outcomes logísticos + 2 outcomes HGB + 1 propensity HGB]. Em 11 anos: **198 fits**; se 2024 puder reutilizar caches certificados após conciliação exata de hashes, ordem, folds e modelos, restam **180 novos fits**. A janela 2018–2024 reutiliza esses resultados e não adiciona fits.

Como âncora, `outputs/temporal/modelos_nuisance/benchmark_runtime.csv` mostra em 2024 ~74 s para três fits de propensity HGB histórico, ~66 s para seis fits de outcome HGB histórico e ~54 s para seis fits de outcomes logísticos; `custo_projetado.csv` estimou ~64 s para os três fits do propensity logístico. Isso sugere **~4,3 min de fit por ano, ~47 min de fit para 11 anos** em condições semelhantes. É extrapolação, não medição do 09: leitura, preparo, SMD/ESS, I/O e anos maiores podem elevar o tempo total. Reservar inicialmente **2–4 horas de parede**, revisar após um ano piloto completo e interromper se a projeção superar o orçamento aprovado antes de seguir. O piloto do 08C registrou RSS perto de 0,8 GB em amostras; o pico em 2–2,7 milhões de linhas é desconhecido. Planejar máquina com **ao menos 8 GB livres** e medir RSS real no primeiro ano. Cinco vetores `float64` para C1/C2 ocupam ~90 MB em 2024; `e_C3` acrescenta ~18 MB, fora DataFrames e temporários. Reservar **~2–3 GB locais** para caches e metadados dos 11 anos, sujeito a compressão e medição. Não pré-alocar nem versionar esses caches nesta rodada.

## 19. Checkpoints

Executar um ano por vez e salvar checkpoint após cada fold e um resumo atômico ao concluir o ano. O primeiro ano de execução deve ser **2024 como reconciliação positiva** dos efeitos e hashes certificados, sem substituir os artefatos históricos; só depois iniciar 2014 e seguir em ordem cronológica. Revalidar contrato em cada retomada. Publicar status `CONCLUIDO`, `SINALIZADO` ou `BLOQUEADO` por ano/especificação, com motivo e último checkpoint íntegro.

## 20. Critérios de bloqueio

**Continuar** se admissão anual, chaves, datas, T/Y, X pré-tratamento, folds, OOF e probabilidades cumprirem o contrato. **Sinalizar e manter o ano visível** se houver piora de calibração, `|SMD|` ponderado acima de 0,10, mais de 10% fora de `[0,05; 0,95]`, ESS relativo abaixo de 0,50 em algum braço, concentração elevada da influência ou discrepância relevante de inferência iid/municipal. Esses números são gatilhos operacionais **propostos para revisão humana antes de implementar**; não excluem anos nem redefinem estimando. **Bloquear o cálculo daquela especificação/ano** se hash de dados/cache divergir, chave ou ordem não for reproduzível, faltar braço/classe/fold, ocorrer leakage, modelo não convergir, houver `e` fora de `(0,1)`, outcome fora de `[0,1]`, OOF incompleto, ESS inválido/colapsado ou não existir suporte comum compatível. Registrar NA e evidência; não retunar, recortar ou omitir o ano após ver o efeito. Falha apenas do HGB bloqueia C3, sem apagar C1/C2 válidos.

## 21. Leitura de 2021–2022

Comparar visualmente as estimativas e diagnósticos desses anos ao restante da série. O notebook 07 viu mudança descritiva em Y, enquanto 08 não viu deterioração conjunta de suporte que a explicasse sozinha. Se o AIPW também mudar, reportar como heterogeneidade temporal aparente, condicionada a populações e pressupostos anuais. Não atribuir automaticamente à COVID-19, Zika ou outro evento. Um teste formal de mudança de nível/tendência requer hipótese, contraste, correlação entre anos e plano inferencial definidos antes de executá-lo.

## 22. Sensibilidade 2018–2024

Mostrar todas as linhas e figuras desse subconjunto sob v1 estrito, lado a lado com a janela principal v1.1. Os anos comuns devem ter estimativas idênticas, pois nenhum ajuste depende de anos vizinhos. Divergência para o mesmo `(ano, especificacao, trimming)` é erro de implementação. Discutir se a leitura qualitativa muda sem declarar uma das janelas vencedora.

## 23. Limitações

Confundimento residual, erro de mensuração, seleção de nascidos vivos e mudanças de composição/codificação entre anos podem alterar estimativas sem alteração do efeito causal. H1 resolve somente a chave de 2014–2017. Cross-fitting reduz viés de ajuste dos nuisances, mas não prova identificação. O recorte de suporte muda a população. Inferência municipal não cobre automaticamente dependência entre anos nem incerteza completa do ajuste ML. Ganhos preditivos de HGB e aumento do N não garantem validade causal.

## 24. Sequência de execução futura

1. Revisar este plano, os gatilhos propostos e o orçamento; congelar contrato do 09 antes de efeitos.
2. Verificar 33 hashes históricos, manifestos anuais, granularidade, chave, datas, T/Y, X e leakage; validar janelas.
3. Reconciliação 2024 de ordem/folds/OOF, C1/C2/C3 e inferência, somente com artefatos certificados ou fits em caminhos novos quando indispensáveis.
4. Medir um ano completo para tempo, RSS e disco; atualizar projeção e aprovar continuação computacional.
5. Para cada 2014–2023: preparar um ano, auditar propensity logístico/HGB e outcomes OOF, aplicar gates, calcular AIPW apenas nas especificações válidas, salvar checkpoint e tabela agregada.
6. Montar as duas janelas sem novos fits; produzir figuras Plotly e interpretação descritiva, preditiva e causal em seções separadas.
7. Revisar limites, 2021–2022 e critérios de conclusão antes de publicar qualquer inferência temporal.

## 25. Testes previstos

Testes leves para chave/ordem, admissões v1/v1.1, estratos e cobertura OOF, ausência de interseção, exclusão de variáveis pós-tratamento, hashes de cache, retomada sem refit, partições por ano, fórmula AIPW em amostra sintética e reconciliação 2024 com tolerâncias históricas. Testar que C1/C2 compartilham `e`, C2/C3 compartilham `m0/m1`, que as janelas comuns produzem linhas idênticas e que falhas produzem status explícito sem descarte silencioso. Rodar os testes do projeto na `.venv` local; não usar treinamento nacional como teste unitário.

## 26. Critérios de conclusão do notebook 09

Contrato congelado antes de efeitos; 11 anos da janela principal e sete da sensibilidade presentes com status e razões de bloqueio; C1/C2 e C3 quando suporte válido; C1/C2/C3 de 2024 reconciliados com histórico; estimativas, SE/IC, N, caudas, ESS e overlap por ano completos; caches verificáveis; figuras Plotly legíveis; nenhuma mistura pooled; nenhuma escolha pós-hoc de janela/modelo/trimming; testes aprovados; limitações e hipóteses explícitas; revisão humana das estimativas. Só então considerar o notebook implementado e concluído.
