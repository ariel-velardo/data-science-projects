# Estado Atual

STATUS = FASE_3_AUDITADA_COM_RESSALVAS
FASE_ATUAL = FASE_3_ROBUSTEZ_METODOLOGICA
DATA_INICIO = 2026-09-25
DATA_ATUALIZACAO = 2026-09-26
GATE_FASE_0 = VIAVEL_COM_RESSALVAS
GATE_FASE_1 = PRONTO_COM_RESSALVAS
EFEITO_CAUSAL_ESTIMADO = SIM
MODELO_CAUSAL_EXECUTADO = SIM
CAUSALIDADE_PROVADA = NAO
GATE_FASE_2 = RESULTADO_NAO_INTERPRETAVEL
GATE_FASE_3 = GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR

## Auditoria metodológica da Fase 3

- A fórmula AIPW, as seis linhas históricas e os 18 arquivos protegidos foram reconciliados sem erro material e sem reescrever a Fase 2. O gate histórico acima permanece registrado.
- O limiar de 50% de IF² no 1% mais extremo é uma heurística, não um teste universal de invalidade. A revisão de 13 referências, o contraexemplo analítico e 800 replicações Monte Carlo sustentam a revisão de seu uso como veto automático. Isso não comprova identificação causal.
- C1: −1,340527 pp; C2: −1,231456 pp. Erros-padrão agrupados por município: 0,068287 e 0,067997 pp, respectivamente. A dependência geográfica aumenta a incerteza em aproximadamente 10%.
- O ajuste cruzado agrupado por município altera as estimativas em menos de 0,005 pp. Nenhuma exclusão de UF inverte o sinal. O modelo C3 de propensão HGB resulta em −1,232469 pp.
- Excluir discordância de consultas ou ampliar a regra de peso tem pouca influência; incluir gestações múltiplas altera a magnitude em aproximadamente 0,20 pp e muda a população-alvo.
- Confundimento residual, seleção de nascidos vivos e temporalidade de covariáveis continuam limitantes. O estimando observável é uma associação padronizada na população selecionada; sua interpretação causal exige hipóteses não verificadas.
- Validação: 22 linhas da Fase 3 reconciliadas, 65 testes aprovados e `pip check` sem inconsistências. Notebook 04 executado integralmente; registros em `outputs/diagnostics/fase3_validacao.json`.
- Evidências e limitações: [relatório completo](../methodology/ROBUSTEZ_FASE3.md), [literatura](../literature/AUDITORIA_GATE_INFLUENCIA.md) e [estimando](../methodology/AUDITORIA_ESTIMANDO_FASE3.md).
- Próxima sequência autorizada: concluir commit/push desta fase; padronizar e reexecutar notebooks 01–04 em português; depois executar a Fase 4 exclusivamente como exercício didático exploratório. Não há autorização para Fase 5 ou artigo completo.

## Objetivo

Comparar predição de baixo peso e estimação AIPW cross-fitted sob as hipóteses e população congeladas da Fase 1. Fase 1 publicada no checkpoint `caf1446`.

## Pergunta candidata

Entre gestantes comparáveis em características observáveis, iniciar o pré-natal até o terceiro mês de gestação está associado a uma redução no risco de baixo peso ao nascer?

## Fonte de dados

- Portal de Dados Abertos do SUS / Ministério da Saúde.
- Recurso candidato: `Nascidos Vivos - 2024`.
- URL do ZIP informada: `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINASC/csv/SINASC_2024_csv.zip`.
- Dicionário oficial localizado: `SINASC: Estrutura de 1996 a 2019`.
- Manual oficial mais recente utilizado: `Declaração de Nascido Vivo: manual de instruções para preenchimento`, 4ª edição, Ministério da Saúde, 2022.

## Definições candidatas

- Tratamento: `MESPRENAT` 1-3 versus 4-9; código 99 e missing excluídos da definição candidata.
- Outcome: `PESO` inferior a 2.500 g, com regra principal de qualidade entre 500 e 6.000 g; peso numérico positivo permanece como sensibilidade.
- Unidade de análise: um registro de nascido vivo; `contador` é único nesta extração, sem garantia de estabilidade longitudinal.
- Controle/comparação: início após o terceiro mês; ausência de pré-natal não será incluída automaticamente.
- População principal: nascidos vivos com T conhecido, peso principal válido e gestação única.
- Amostra candidata: 2.251.570 registros; T=1: 1.942.045 (86,253%); T=0: 309.525 (13,747%).

## Decisões herdadas da Fase 1

- Escopo restrito ao ano de 2024 e ao desenho da Fase 1, sem estimação de efeito.
- Fonte principal exclusivamente institucional oficial.
- Dados brutos serão preservados byte a byte e não versionados.
- Dúvidas não bloqueantes serão registradas como `QUESTAO_ABERTA` e tratadas conservadoramente.
- O bruto oficial foi preservado e seu hash SHA-256 registrado no manifesto.
- `MESPRENAT=99` foi confirmado no manual oficial como ignorado e permanece inelegível.
- Gestação única foi escolhida como principal; gestações múltiplas ficam como sensibilidade.
- X principal: idade materna, escolaridade materna, raça/cor materna, situação conjugal, paridade, perdas fetais e UF de residência.
- Missing categórico recebe categoria explícita; idade usa mediana e indicador no pipeline.
- O balanceamento bruto apresenta desequilíbrio material, especialmente em situação conjugal e escolaridade.
- Nenhum perfil marginal pré-especificado apresentou T praticamente determinístico; isso não substitui o overlap multivariado.
- Propensity logístico L2 em 5 folds OOF: AUC 0,662873; todos convergiram (49–58 iterações, L-BFGS).
- Suporte comum observado: 0,306807–0,973928. Não há scores fora de 0,01–0,99.
- Sensibilidade 0,05–0,95 excluiria 147.550 registros (140.879 tratados e 6.671 controles).
- Gate `PRONTO_COM_RESSALVAS`: suporte permite o exercício exploratório; confundimento não observado, seleção de nascidos vivos e mensuração continuam limitantes.

## Decisões abertas

- Registros com `CONSPRENAT=0` e mês válido são discordantes (684 precoces e 414 tardios na base). A classificação segue MESPRENAT; zero consultas não é usado para criar controles nem para excluir retroativamente registros.
- Estabilidade e significado operacional de `contador` entre extrações.
- Plausibilidade de exchangeability condicional diante de confundidores socioeconômicos e de acesso não observados.

## Riscos metodológicos iniciais

- Confundimento residual em dados observacionais.
- Temporalidade ambígua de variáveis coletadas ao longo da gestação.
- Missing e códigos especiais na variável de início do pré-natal.
- Possível viés de seleção ao excluir registros sem informação válida.
- Risco de leakage ao usar consultas, idade gestacional, parto ou características neonatais como X.

## Próxima etapa

1. Revisar substantivamente o gate de concentração de influência com orientação acadêmica, sem reinterpretá-lo como teste universal de invalidade.
2. Avaliar seleção, confundimento não observado e incerteza por dependência geográfica antes de promover conclusões causais.
3. Usar os notebooks como material do trabalho, mantendo resultados condicionais e limitações explícitas.

## Resultado da Fase 2

- População integral preservada: 2.251.570. Sem trimming oculto. Três folds estratificados T/Y, seed 20240925.
- Predição (teste N=450.314): logística ROC-AUC 0,574248, AP 0,100220, Brier 0,072350; HGB 0,583494, 0,104537 e 0,072239. Discriminação limitada, calibração por decis razoável. Precision/recall/F1 ao limiar 0,5 são zero.
- Associação bruta NÃO CAUSAL: −1,423859 pp.
- C1 AIPW: −1,340527 pp (SE 0,061994; IC95% −1,462034 a −1,219019).
- C2 AIPW: −1,231456 pp (SE 0,061981; IC95% −1,352938 a −1,109973).
- 0,01–0,99 não altera N; 0,05–0,95 mantém 2.103.319, C1 −1,382662 pp e C2 −1,273369 pp.
- Todos os ajustes logísticos convergiram. HGB usa early stopping interno ao treino.
- Gate `RESULTADO_NAO_INTERPRETAVEL` segundo regra conservadora pré-especificada: top 1% de |IF| concentra 78,8% de IF² (limite do plano 50%). Estimativas são estáveis entre modelos e trimming; o gate decorre desse diagnóstico, não de falha de execução.
- Este limiar não é um critério universal de identificação ou validade assintótica. Contribuição máxima individual é ~0,0015 pp; ESS dos controles ~232.772. Os resultados e esse contraponto são preservados para revisão.
- Sem placebo defensável; heterogeneidade omitida; nenhum Causal Forest ou artigo final produzido.
