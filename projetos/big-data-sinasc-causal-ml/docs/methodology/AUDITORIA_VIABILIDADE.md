# Auditoria de Viabilidade - SINASC 2024

> Esta auditoria é descritiva. Nenhum efeito causal foi estimado.

## Dimensões e granularidade

- Registros: 2,389,325.
- Colunas: 62.
- Granularidade candidata: um registro de nascido vivo.
- `contador` único: True.

## Tratamento candidato

- Campo: `MESPRENAT` - Mês de gestação em que iniciou o pré-natal.
- Utilizável para meses 1-9: 2,308,388 (96.613%).
- Início até o 3º mês: 1,992,408.
- Início após o 3º mês: 315,980.
- Código 99: 37,569; missing: 43,368.
- QUESTAO_ABERTA: O PDF 1996-2019 não documenta o código 99 para MESPRENAT; sua interpretação como ignorado é operacional e deve ser confirmada.

## Outcome candidato

- Campo: `PESO` em gramas.
- Pesos válidos: 2,389,104 (99.991%).
- Baixo peso (<2.500 g): 226,375 (9.475%).
- Faixa observada: 100 a 7000 g.
- Alertas: 3,727 abaixo de 500 g e 59 acima de 6.000 g.
- QUESTAO_ABERTA: Pesos extremos são mantidos no diagnóstico bruto e sinalizados; uma regra de exclusão biológica exige decisão metodológica posterior.

## Covariáveis por temporalidade

### A provavelmente pre tratamento

`CODMUNNATU`, `CODMUNRES`, `CODPAISRES`, `CODUFNATU`, `DTNASCMAE`, `ESCMAE`, `ESCMAE2010`, `ESCMAEAGR1`, `ESTCIVMAE`, `IDADEMAE`, `IDADEPAI`, `NATURALMAE`, `PARIDADE`, `QTDFILMORT`, `QTDFILVIVO`, `QTDGESTANT`, `QTDPARTCES`, `QTDPARTNOR`, `RACACORMAE`, `SERIESCMAE`

### B provavelmente pos tratamento mediadora

`APGAR1`, `APGAR5`, `CODANOMAL`, `CONSPRENAT`, `CONSULTAS`, `DTNASC`, `GESTACAO`, `HORANASC`, `IDANOMAL`, `KOTELCHUCK`, `PARTO`, `RACACOR`, `SEMAGESTAC`, `SEXO`, `STCESPARTO`, `STTRABPART`, `TPAPRESENT`, `TPNASCASSI`, `TPROBSON`

### C temporalidade ou papel duvidoso

`CODESTAB`, `CODOCUPMAE`, `DTULTMENST`, `GRAVIDEZ`, `LOCNASC`, `TPMETESTIM`

## Gate de viabilidade

**VIÁVEL_COM_RESSALVAS**

T e Y são construíveis para a grande maioria dos registros e há volume e covariáveis pré-tratamento candidatas. As ressalvas materiais são o dicionário oficial limitado a 2019, o código 99 de `MESPRENAT` não documentado nesse PDF, missing de T, extremos de peso e a ausência, nesta fase, de uma estratégia causal final capaz de resolver confundimento residual.

Este gate avalia dados e desenho candidato; não valida causalidade.
