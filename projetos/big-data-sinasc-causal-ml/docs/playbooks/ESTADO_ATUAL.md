# Estado Atual

STATUS = FASE_1_CONCLUIDA
FASE_ATUAL = FASE_1_DESENHO_E_OVERLAP
DATA_INICIO = 2026-09-25
DATA_ATUALIZACAO = 2026-09-26
GATE_FASE_0 = VIAVEL_COM_RESSALVAS
GATE_FASE_1 = PRONTO_COM_RESSALVAS
EFEITO_CAUSAL_ESTIMADO = NAO
MODELO_CAUSAL_EXECUTADO = NAO

## Objetivo

Definir a amostra analítica, o contrato causal mínimo e as covariáveis pré-tratamento; auditar balanceamento, positividade e overlap antes de qualquer estimação causal.

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

## Decisões tomadas

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

1. Congelar o desenho e a população no plano da Fase 2.
2. Executar benchmark preditivo e AIPW cross-fitted autorizados, após checkpoint da Fase 1.
3. Interpretar estabilidade e limitações, sem certificação de causalidade.
