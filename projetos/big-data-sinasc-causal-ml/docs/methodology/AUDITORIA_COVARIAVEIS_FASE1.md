# Auditoria conceitual de covariáveis — Fase 1

> A classificação é causal/conceitual: pergunta-se se T poderia causar ou alterar a variável, não apenas quando ela foi registrada.

| Variável | Definição e momento | T pode alterar? | Pode afetar T? | Pode afetar Y? | Papel candidato | Decisão principal |
|---|---|---:|---:|---:|---|---|
| `IDADEMAE` | idade na gestação, preexistente | não | sim | sim | confundidor | incluir |
| `ESCMAE2010` | escolaridade materna; majoritariamente prévia | improvável | sim | sim | confundidor socioeconômico | incluir; `9`/missing explícito |
| `RACACORMAE` | autodeclaração materna | não | sim, via desigualdades estruturais | sim | confundidor/proxy estrutural | incluir com interpretação não biológica |
| `ESTCIVMAE` | situação conjugal | pouco provável | sim | sim | confundidor social | incluir; ignorado explícito |
| `PARIDADE` | histórico reprodutivo anterior | não | sim | sim | confundidor | incluir |
| `QTDFILMORT` | perdas fetais/abortos anteriores | não | sim | sim | confundidor/histórico | incluir categorizada em 0, 1, 2+ e ignorado |
| `CODMUNRES` | município de residência no parto | T não altera diretamente, mas mudança residencial é possível | sim, via acesso | sim, via contexto | contextual/confundidor | derivar UF no principal; município só descritivo |
| `GRAVIDEZ` | número de conceptos da gestação atual, definido na concepção | não | sim, após diagnóstico | sim, fortemente | elegibilidade/confundidor | restringir a única; todas como sensibilidade |
| `SEXO` | sexo do concepto, biologicamente definido antes de T | não | não de forma plausível no tempo zero | sim | preditor de Y apenas | excluir do propensity principal |
| `CODOCUPMAE` | ocupação informada no parto; pode mudar na gestação | possivelmente | sim | sim | duvidoso | excluir do principal; 6,5% missing e alta cardinalidade |
| `DTULTMENST` | data anterior a T, usada para datar gestação | não | não substantivamente | não diretamente | variável de mensuração/contextual | excluir; 53,2% missing |
| `TPMETESTIM` | método usado quando DUM ignorada | possivelmente, via contato/registro do cuidado | não antes de T | não diretamente | pós-tratamento/processo de mensuração | proibir |
| `LOCNASC` | local onde ocorreu o nascimento | sim, via encaminhamento/assistência | não antes de T | associado por risco/assistência | pós-tratamento/collider potencial | proibir |
| `CODESTAB` | estabelecimento do parto | sim, via trajetória assistencial | não antes de T | associado por risco/qualidade | pós-tratamento/collider potencial | proibir |
| `CONSPRENAT`/`CONSULTAS` | quantidade de consultas acumulada | sim | não no tempo zero | sim, como mediação/qualidade | mediador | proibir |
| `GESTACAO`/`SEMAGESTAC` | duração da gestação | sim, potencialmente | não | sim | mediador/outcome intermediário | proibir |
| `PARTO`, Apgar, `KOTELCHUCK` | eventos/índices ao fim da gestação | sim | não | associados a Y | pós-tratamento/mediador/collider | proibir |

`IDADEPAI` (67,1% missing) e `SERIESCMAE` (34,3% missing) não entram no conjunto principal. A seleção de confundidores não usa importância de variável nem seleção automática de features.
