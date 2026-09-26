# Contrato causal mínimo — Fase 1

> Contrato de trabalho observacional. Nenhum efeito causal é estimado nesta fase.

## Pergunta e decisão

Entre gestantes comparáveis nas características observadas, iniciar o pré-natal até o terceiro mês está associado a menor risco de baixo peso ao nascer? A decisão futura é avaliar se há suporte para estimar o efeito de promover início precoce do pré-natal.

## População-fonte e unidade

- População-fonte: nascidos vivos registrados no SINASC 2024.
- Unidade observada: uma DNV por nascido vivo.
- População analítica principal candidata: nascidos vivos de gestações únicas, com `MESPRENAT` entre 1 e 9 e `PESO` entre 500 e 6.000 g.
- Sensibilidades: todas as gestações válidas e todo peso numérico positivo.

## Tratamento, comparação e tempo zero

- `T=1`: primeira consulta de pré-natal no 1º, 2º ou 3º mês.
- `T=0`: primeira consulta do 4º ao 9º mês.
- `T=NA`: `MESPRENAT=99`, missing ou outro valor inválido.
- Ausência de pré-natal identificada por `CONSPRENAT=0` não entra automaticamente em `T=0`.
- Tempo zero conceitual: início da gestação, antes da decisão/oportunidade de iniciar o pré-natal precocemente.

## Outcome

- `Y=1`: peso ao nascer inferior a 2.500 g.
- `Y=0`: peso ao nascer igual ou superior a 2.500 g.
- Regra principal de qualidade: 500–6.000 g (`P1`).
- Sensibilidade: todo peso numérico positivo (`P0`).

## X principal candidato

Idade materna, escolaridade materna (`ESCMAE2010`), raça/cor materna, situação conjugal, paridade, histórico de perdas fetais e UF de residência derivada de `CODMUNRES`. Códigos ignorados permanecem explícitos; idade missing/inválida é imputada pela mediana somente dentro do pipeline, com indicador de missing.

`GRAVIDEZ` é anterior ao tratamento, mas define a elegibilidade principal (gestação única). `SEXO` é biologicamente anterior ao tratamento e preditor de Y, porém não é confundidor candidato e não entra no propensity principal.

## Estimando candidato

Ainda não se escolhe automaticamente ATE ou ATT. O alvo substantivo mais natural é o efeito médio na população elegível com suporte comum, pois a política potencial se dirige às gestantes que poderiam plausivelmente iniciar cedo ou tarde. Se o suporte for assimétrico, um alvo restrito à região de overlap pode ser mais defensável que ATE/ATT na população inteira.

## Hipóteses necessárias na próxima fase

- consistência e versões de tratamento suficientemente comparáveis;
- exchangeability condicional após X, sem confundimento não observado relevante;
- positividade nos perfis incluídos;
- temporalidade correta e ausência de ajuste por mediadores/colliders;
- mensuração suficientemente válida de T e Y.

Essas hipóteses não são provadas pelos dados. Tabagismo, álcool/drogas, IMC e nutrição pré-gestacionais, morbidades maternas, gravidez planejada, renda, acesso/distância, qualidade do serviço e preferências por cuidado são confundidores importantes ausentes ou incompletos no SINASC.

## Proibições nesta fase

Não estimar ATE, ATT, ATC, IPW de outcome, matching, AIPW, DML, meta-learners, Causal Forest, uplift ou regressão de Y interpretada causalmente. O propensity é apenas diagnóstico de assignment e overlap.
