# Estado Atual do Projeto

> Documento operacional mutável.
>
> Atualizar quando uma etapa for fechada, um gate mudar ou uma nova unidade
> de trabalho for aberta.
>
> Snapshot: 2026-09-15.

---

## 1. Checkpoint atual

Branch:

`main`

HEAD/origin conhecido:

`5dd529240162dc169b27c532abb99f552735bc62`

Commits recentes:

- `5dd5292` — `feat: implementa dry run nacional CEMPRE`
- `a605530` — `docs: registra fechamento do D3 CEMPRE`
- `cb853ec` — `feat: implementa manifesto e proveniencia CEMPRE`
- `a228c6a` — `docs: registra fechamento do D2 CEMPRE`
- `214c660` — `feat: implementa persistencia offline da long CEMPRE`
- `7db9950` — `docs: registra fechamento do D1 CEMPRE`
- `d9ba6ce` — `feat: implementa plano nacional e completude CEMPRE`
- `acd3d8a` — `feat: integra calendario territorial ao pipeline CEMPRE`
- `d17e621` — `docs: atualiza estado apos fechamento territorial`
- `dd6bbac` — `docs: adiciona playbooks operacionais do projeto`

Os commits foram enviados para `origin/main`. Checkpoint substantivo mais
recente: `5dd529240162dc169b27c532abb99f552735bc62` (D4).

---

## 2. Fase 0 CEMPRE

Status técnico:

`PILOTO_TECNICO_APROVADO_CONFIRMADO`

Gate:

`PODE_COMMITAR_FASE_0 = SIM`

Commit:

`a6a1a41`

Push:

**CONCLUIDO**

O spot-check independente final confirmou:

- parser seguro para valores não-zero;
- payload/schema SIDRA;
- cache e reprocessamento;
- `.gitignore`;
- validacoes cruzadas;
- fixtures;
- 71/71 testes passando.

A frente esta tecnicamente fechada e commitada.

Isso NAO autoriza, isoladamente, extracao nacional CEMPRE.

---

## 3. Calendario Territorial IBGE

Fonte:

**IBGE — Divisao Territorial Brasileira (DTB), edicoes anuais 2007-2019.**

Resultado principal:

- 2007-2008: 5.564 municipios;
- 2009-2012: 5.565 municipios;
- 2013-2019: 5.570 municipios;
- 5.570 codigos;
- 72.410 linhas;
- 44/44 testes passando.

Dependencia de reproducibilidade:

`xlrd==2.0.2`

Commit:

`1ee321c`

Push:

**CONCLUIDO**

Estado do gate:

`CALENDARIO_TERRITORIAL_APTO_CONFIRMADO`

Revisao final pos-commit:

`REVISAO_FINAL_TERRITORIAL_POS_COMMIT = OK`

Governanca da revisao final:

`INDEPENDENCIA_ENTRE_SESSOES = SIM`

`INDEPENDENCIA_ENTRE_AGENTES = NAO`

Essa e uma limitacao de governanca nao bloqueante para o calendario
territorial. A revisao foi focalizada; nao reabrir auditoria territorial ampla
sem novo problema concreto.

## 4. Integracao Territorial CEMPRE

Status tecnico:

**CONCLUIDA**

Commit da integracao:

`acd3d8a646d94a01bb6fb3275ef536d6b8bead24` — `feat: integra calendario territorial ao pipeline CEMPRE`

Push:

**CONCLUIDO**

Validacoes de fechamento:

- 80/80 testes CEMPRE passando;
- 44/44 testes territoriais passando;
- smoke-check do calendario territorial real: 72.410 linhas, 5.570 codigos,
  anos 2007–2019 e chave municipio-ano unica;
- testes unitarios independentes do Parquet territorial real passando;
- integracao entre calendario territorial e CEMPRE fechada tecnicamente.

Gates operacionais:

`INTEGRACAO_TERRITORIAL_CEMPRE_APROVADA = SIM`

`PODE_COMMITAR_INTEGRACAO = SIM`

Os gates ja fechados permanecem inalterados:

`PILOTO_TECNICO_APROVADO_CONFIRMADO`

`CALENDARIO_TERRITORIAL_APTO_CONFIRMADO`

## 5. D1 — Plano nacional e completude CEMPRE

Status tecnico:

`D1_PLANO_NACIONAL_REQUESTS = CONCLUIDO`

`D1_SPOT_CHECK = APROVADO`

`PLANO_NACIONAL_REQUESTS_APROVADO = SIM`

`CONTRATO_COMPLETUDE_APROVADO = SIM`

Commit:

`d9ba6ce296762ba39189d1856ba1bf0b122296c1` — `feat: implementa plano nacional e completude CEMPRE`

Fechamento registrado:

- plano padrão nacional: 27 UFs × 13 anos × 1 grupo de variáveis;
- 351 requests esperados derivados, não hardcoded;
- referência externa de 27 UFs;
- cobertura do produto cartesiano validada;
- completude offline implementada;
- 104/104 testes CEMPRE passando;
- 44/44 testes territoriais passando;
- zero rede no desenvolvimento/auditoria D1.

O D1 fecha o plano e o contrato de completude. Não declara
`PAINEL_TECNICO_CONSTRUIDO` e não autoriza a extração nacional CEMPRE.

---

## 6. D2 — Persistência e reconstrução offline da long CEMPRE

Status técnico:

`D2_PERSISTENCIA_LONG = CONCLUIDO`

`D2_RECONSTRUCAO_OFFLINE = CONCLUIDO`

`D2_SPOT_CHECK = APROVADO`

`PERSISTENCIA_LONG_APROVADA = SIM`

`RECONSTRUCAO_OFFLINE_APROVADA = SIM`

`ROUNDTRIP_PARQUET_APROVADO = SIM`

`PODE_COMMITAR_D2 = SIM` (já commitado)

Commit substantivo:

`214c660412d43312125eb5fd69dcbb4e88dce166` — `feat: implementa persistencia offline da long CEMPRE`

Push:

**CONCLUIDO**

O D2 passou por spot-check independente no Codex, que apontou dois
bloqueadores focais (validação estrutural fraca em `write_long_parquet` e
`load_long_parquet` aceitando `incompatibilidade_territorial` não
booleana). Ambos foram corrigidos centralizando a validação em
`_validar_schema_long_persistida()`, reutilizada nos dois sentidos
(escrita e leitura), e o recheck independente final aprovou o fechamento.

Fechamento registrado:

- reconstrução da long CEMPRE inteiramente offline, a partir do cache já
  existente em disco — nenhuma função do D2 chama `fetch_request` ou rede;
- cache válido, ausente e corrompido tratados explicitamente (nunca cai
  para rede, nunca converte silenciosamente em sucesso);
- completude do plano (`avalia_completude_plano`) obrigatória e verificada
  antes de qualquer construção da long — plano incompleto falha
  explicitamente e não produz long considerada completa;
- `normalize_long` reutilizado sem duplicar lógica de parsing;
- `validate_long` reutilizado — long reprovada (ex.: símbolo
  `desconhecido`) bloqueia a persistência;
- reconciliação territorial (`reconcile_territorial`) aplicada antes da
  persistência;
- ordem determinística da long persistida por `codigo_municipio_ibge`,
  `ano`, `codigo_variavel_sidra`, `request_id` — independente da ordem do
  plano/resultados de entrada;
- persistência em Parquet com `overwrite=False` como padrão — nunca
  sobrescreve silenciosamente;
- `write_long_parquet` e `load_long_parquet` usam o MESMO contrato
  estrutural (`_validar_schema_long_persistida`): o que não pode ser
  recarregado como long válida também não pode ser gravado como long
  válida;
- ano fora da janela 2007–2019 é rejeitado tanto na escrita quanto no
  reload, sem criar/aceitar arquivo;
- `incompatibilidade_territorial` não booleana é rejeitada tanto na
  escrita quanto no reload — sem conversão silenciosa de string
  (`"True"`/`"False"`/`"sim"`/`"nao"`);
- equivalência lógica de round-trip Parquet validada
  (`validate_round_trip_equivalencia`) — chave canônica, valores brutos e
  numéricos (inclusive NA), status API, request_id, hash e os dois status
  territoriais comparados após normalizar a ordem;
- 135/135 testes CEMPRE passando (104 anteriores ao D2 + 27 do D2 + 4 da
  correção focal);
- 44/44 testes territoriais passando;
- zero rede no desenvolvimento/auditoria/correção do D2.

O D2 fecha a persistência e a reconstrução offline da long. Não declara
`PAINEL_TECNICO_CONSTRUIDO` e não autoriza a extração nacional CEMPRE.

---

## 7. D3 — Manifesto e proveniência do pipeline CEMPRE

Status técnico:

`D3_MANIFESTO = CONCLUIDO`

`D3_PROVENIENCIA = CONCLUIDA`

`D3_SPOT_CHECK = APROVADO`

`MANIFESTO_APROVADO = SIM`

`PROVENIENCIA_APROVADA = SIM`

`MANIFESTO_COMPLETO_VALIDO = SIM`

`MANIFESTO_INCOMPLETO_VALIDO = SIM`

`PODE_COMMITAR_D3 = SIM` (já commitado)

Commit substantivo:

`cb853ecbd5390892d16b63d6746e2363bd3185fb` — `feat: implementa manifesto e proveniencia CEMPRE`

Push:

**CONCLUIDO**

O D3 passou por spot-check independente no Codex, que apontou dois
bloqueadores focais: (1) `validate_manifest()` aceitava contradições
entre `execucao` e a proveniência por request (ex.: `n_sucessos`
divergente, request marcado ausente/duplicado na execução mas com status
diferente na proveniência); (2) `validate_manifest()` aceitava
adulteração de `hash_plano`, `anos` e `variaveis` na seção `plano`. Ambos
foram corrigidos com dois helpers focais —
`_validar_consistencia_execucao_requests()` e
`_validar_consistencia_plano_requests()` —, reutilizados por
`validate_manifest()` sem duplicar a lógica de `avalia_completude_plano()`,
e o recheck independente final aprovou o fechamento.

Fechamento registrado:

- SHA-256 de artefatos implementado (`sha256_file`), leitura em chunks,
  falha explícita para arquivo ausente, zero rede;
- hash canônico do plano implementado (`hash_plano_canonico`) —
  independente de ordem de lista e de chaves de dicionário, sensível a
  qualquer mudança real de conteúdo;
- proveniência por request implementada (`build_request_provenance`) —
  uma entrada por request esperado, nunca o payload bruto nem a long
  inteira;
- commit Git completo registrado (`get_git_head`, via `subprocess`,
  somente leitura, hash de 40 hex nunca abreviado, falha explícita se
  indeterminável);
- timestamp UTC ISO-8601 (`timestamp_utc_iso`), injetável para testes
  determinísticos;
- completude reutiliza `avalia_completude_plano()` — nenhuma lógica
  paralela de contagem;
- execução completa e incompleta ambas suportadas — `write_manifest`
  rejeita apenas inconsistência lógica, nunca a incompletude em si;
- consistência execução × proveniência validada
  (`_validar_consistencia_execucao_requests`): `n_sucessos`/`n_falhas`
  e os conjuntos de ausentes/duplicados da seção `execucao` precisam
  bater exatamente com os `status_execucao` registrados em `requests`;
  `completo=True` exige que todo request esperado esteja como "sucesso";
- `hash_plano` validado como SHA-256 hex completo (64 caracteres), nunca
  recomputado no reload;
- anos, variáveis e UFs do manifesto validados
  (`_validar_consistencia_plano_requests`) — anos dentro de 2007–2019 e
  coerentes com a proveniência (plano parcial deliberado continua
  válido); variáveis exatamente iguais a `VARIAVEIS_ESPERADAS` (ordem
  irrelevante); UFs do plano coerentes com as UFs presentes na
  proveniência;
- persistência/reload em JSON (`write_manifest`/`load_manifest`) com
  `overwrite=False` por padrão — nunca sobrescreve silenciosamente;
- round-trip JSON validado — manifesto escrito e recarregado preserva
  conteúdo lógico integral;
- 180/180 testes CEMPRE passando (169 anteriores ao D3 + 34 do D3 + 11
  da correção focal, com 3 testes pré-existentes ajustados apenas no
  texto do `assertRaisesRegex` devido à checagem unificada);
- 44/44 testes territoriais passando;
- zero rede no desenvolvimento/auditoria/correção do D3.

O D3 fecha o manifesto e a proveniência do pipeline. Não declara
`PAINEL_TECNICO_CONSTRUIDO` e não autoriza a extração nacional CEMPRE.

---

## 8. D4 — Orquestração nacional (dry run offline)

Status técnico:

`D4_ORQUESTRADOR_DRY_RUN = CONCLUIDO`

`D4_GUARDA_AUTORIZACAO = CONCLUIDA`

`D4_SPOT_CHECK = APROVADO`

`ORQUESTRADOR_DRY_RUN_APROVADO = SIM`

`GUARDA_AUTORIZACAO_APROVADA = SIM`

`CLASSIFICACAO_CACHE_APROVADA = SIM`

`DRY_RUN_ZERO_EFEITOS_COLATERAIS = SIM`

`SMOKE_CHECK_NACIONAL_OFFLINE = APROVADO`

`PODE_COMMITAR_D4 = SIM` (já commitado)

Commit substantivo:

`5dd529240162dc169b27c532abb99f552735bc62` — `feat: implementa dry run nacional CEMPRE`

Push:

**CONCLUIDO**

O D4 passou por spot-check independente no Codex, aprovado sem
bloqueadores. Achado não bloqueante registrado: `NationalRunConfig.modo`
é redundante em relação ao parâmetro `modo` de `run_national_pipeline()`
— sem impacto de segurança ou de comportamento, sem necessidade de
correção antes da auditoria integrada.

Fechamento registrado:

- `dry_run_national_pipeline()` compõe D1 (`build_national_request_plan`,
  já validado internamente), D2 (`load_results_from_cache`) e D3
  (`hash_plano_canonico`, `get_git_head`) sem duplicar nenhum desses
  contratos;
- `dry_run` é o modo padrão de `NationalRunConfig`/`run_national_pipeline`
  — nunca chama rede por padrão;
- execução real (`modo="execute"`) sem `autorizacao_extracao=True`
  explícito falha imediatamente com `PermissionError`, antes de qualquer
  request; a autorização é sempre parâmetro explícito, nunca variável
  global;
- mesmo com `autorizacao_extracao=True`, a execução real ainda não está
  implementada nesta etapa — protegida por `NotImplementedError`
  explícito, deixando claro que o branch real só será habilitado após
  gate explícito de autorização de extração nacional;
- classificação de cache reaproveita o contrato de `load_results_from_cache`
  (D2): cache válido não exige rede; cache ausente exigiria rede e NÃO é
  bloqueador (é exatamente o que uma execução real futura preencheria);
  cache inválido/corrompido É bloqueador operacional, nunca convertido
  automaticamente em cache miss, nunca apagado;
- arquivo(s) residual(is) de cache fora do plano nacional avaliado são
  ignorados pela classificação (não pertencem a nenhum `request_id`
  esperado);
- conflito de artefato existente com `overwrite=False` (long ou
  manifesto) vira bloqueador explícito; `overwrite=True` remove apenas o
  conflito LÓGICO do relatório do dry run — nenhum arquivo é escrito,
  sobrescrito ou apagado em nenhum dos dois casos;
- dry run não cria cache, não cria long, não escreve manifesto — é
  simulação pura;
- `pronto_para_execucao_real` é diagnóstico técnico do relatório —
  explicitamente NÃO equivale a `EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA`;
- 204/204 testes CEMPRE passando (180 anteriores ao D4 + 24 do D4);
- 44/44 testes territoriais passando;
- zero rede no desenvolvimento/auditoria do D4.

Smoke-check nacional offline (calendário territorial real + `CACHE_DIR`
real em modo somente leitura, nenhum arquivo criado):

- `n_requests_esperados = 351`;
- `n_cache_validos = 0`;
- `n_cache_ausentes = 351`;
- `n_cache_invalidos = 0`;
- `n_requests_que_exigiriam_rede = 351`;
- `bloqueadores = 0`;
- `pronto_para_execucao_real = True` (diagnóstico técnico apenas — não
  autoriza extração).

O D4 fecha a orquestração nacional em modo dry run. Não declara
`PAINEL_TECNICO_CONSTRUIDO` e não autoriza a extração nacional CEMPRE.

---

## 9. Camada operacional

Arquivos operacionais:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/playbooks/PLAYBOOK_PROJETO.md`
- `docs/playbooks/PLAYBOOK_CEMPRE.md`
- `docs/playbooks/PLAYBOOK_TERRITORIO.md`
- `docs/playbooks/PLAYBOOK_AUDITORIA.md`
- `docs/playbooks/ESTADO_ATUAL.md`
- `scripts/agent_preflight.ps1`

Esta camada e operacional e deve permanecer separada dos commits cientificos.

---

## 10. Proximos passos

1. realizar auditoria integrada final do pipeline nacional CEMPRE
   (D1 + D2 + D3 + D4);
2. verificar sistemicamente: plano; cache; completude; persistência;
   manifesto; dry run; guardas; retomabilidade; riscos de artefatos
   parciais ou inconsistentes;
3. somente se essa auditoria for aprovada, decidir explicitamente sobre a
   autorização da primeira extração nacional real;
4. após autorização explícita, implementar/habilitar o ramo de execução
   real de forma controlada;
5. realizar a primeira extração nacional;
6. validar cobertura/completude do material coletado antes de qualquer
   construção analítica ou causal.

Nao reabrir Fase 0, calendario territorial, D2, D3 ou D4 sem anomalia
concreta.

---

## 11. Extracao nacional CEMPRE

Status:

**EXTRAÇÃO NACIONAL CEMPRE = NÃO AUTORIZADA**

Os commits territorial, Fase 0, D1, D2, D3 e D4, por si so, nao autorizam
a extracao.

Antes de qualquer extracao nacional ainda e necessario:

- gate independente pre-extracao nacional CEMPRE aprovado;
- autorizacao explicita para a extracao nacional.

---

## 12. Regra para agentes

Antes de trabalhar:

1. ler `PLAYBOOK_PROJETO.md`;
2. ler o playbook especifico;
3. ler este arquivo;
4. executar `scripts/agent_preflight.ps1`;
5. confirmar a unidade de trabalho autorizada.

Nao iniciar automaticamente:

- nova frente;
- extracao nacional;
- merge causal;
- estimacao causal;
- commit ou push nao autorizado.

Se o Git observado divergir materialmente deste snapshot, parar e reportar.
