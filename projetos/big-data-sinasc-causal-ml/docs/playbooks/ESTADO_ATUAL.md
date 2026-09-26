# Estado Atual

STATUS = FASE_0_CONCLUIDA_GATE_VIABILIDADE
DATA_INICIO = 2026-09-25
DATA_CONCLUSAO = 2026-09-25
GATE_FASE_0 = VIAVEL_COM_RESSALVAS
EFEITO_CAUSAL_ESTIMADO = NAO
MODELO_CAUSAL_EXECUTADO = NAO

## Objetivo

Verificar se os dados oficiais do SINASC 2024 sustentam, com qualidade e documentação suficientes, o desenho candidato sobre início precoce do pré-natal e baixo peso ao nascer.

## Pergunta candidata

Entre gestantes comparáveis em características observáveis, iniciar o pré-natal até o terceiro mês de gestação está associado a uma redução no risco de baixo peso ao nascer?

## Fonte de dados

- Portal de Dados Abertos do SUS / Ministério da Saúde.
- Recurso candidato: `Nascidos Vivos - 2024`.
- URL do ZIP informada: `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINASC/csv/SINASC_2024_csv.zip`.
- Dicionário oficial localizado: `SINASC: Estrutura de 1996 a 2019`, publicado pelo Ministério da Saúde; a defasagem em relação a 2024 permanece como limitação.

## Definições candidatas

- Tratamento: `MESPRENAT` 1-3 versus 4-9; código 99 e missing excluídos da definição candidata.
- Outcome: `PESO` numérico positivo inferior a 2.500 g, medido em gramas.
- Unidade de análise: um registro de nascido vivo; `contador` é único nesta extração, sem garantia de estabilidade longitudinal.
- Controle/comparação: início após o terceiro mês; ausência de pré-natal não será incluída automaticamente.

## Decisões tomadas

- Escopo restrito à Fase 0 e ao ano de 2024.
- Fonte principal exclusivamente institucional oficial.
- Dados brutos serão preservados byte a byte e não versionados.
- Dúvidas não bloqueantes serão registradas como `QUESTAO_ABERTA` e tratadas conservadoramente.
- O bruto oficial foi preservado e seu hash SHA-256 registrado no manifesto.
- A classificação temporal de covariáveis é provisória; nenhuma seleção causal final de X foi realizada.
- O gate da Fase 0 foi classificado como `VIAVEL_COM_RESSALVAS`.

## Decisões abertas

- Semântica oficial do código 99 de `MESPRENAT` na versão 2024.
- Regras finais de elegibilidade e tratamento de pesos biologicamente implausíveis.
- Estabilidade e significado operacional de `contador` entre extrações.
- Conjunto causal final de covariáveis e estratégia de identificação.

## Riscos metodológicos iniciais

- Confundimento residual em dados observacionais.
- Temporalidade ambígua de variáveis coletadas ao longo da gestação.
- Missing e códigos especiais na variável de início do pré-natal.
- Possível viés de seleção ao excluir registros sem informação válida.
- Risco de leakage ao usar consultas, idade gestacional, parto ou características neonatais como X.

## Próximo gate

**GATE_FASE_1_DESENHO_CAUSAL**: requer validação manual das questões abertas, definição de elegibilidade, DAG/estimando, assumptions e estratégia de identificação. Não avançado automaticamente.
