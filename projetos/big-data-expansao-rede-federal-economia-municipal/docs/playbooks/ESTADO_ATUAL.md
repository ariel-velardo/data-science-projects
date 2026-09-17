# Estado Atual do Projeto

> Documento operacional mutável.
>
> Atualizar quando uma etapa for fechada, um gate mudar ou uma nova unidade
> de trabalho for aberta.
>
> Snapshot: 2026-09-16.

---

## 1. Checkpoint atual

Branch:

`main`

HEAD/origin conhecido:

`5b716907f9c02aa4b7ebb5a4c949d4147a0e7521`

Commits recentes:

- `5b71690` — `feat: integra fonte agregados ao pipeline CEMPRE`
- `d4ace33` — `docs: registra adaptador CEMPRE de agregados`
- `4a4355e` — `feat: adiciona adaptador CEMPRE para API de agregados`
- `dc995e7` — `docs: registra fechamento do D5 CEMPRE`
- `7218c56` — `feat: implementa executor controlado CEMPRE`
- `7277798` — `docs: fecha auditoria pre-extracao CEMPRE`
- `1b59058` — `fix: vincula cache ao request CEMPRE`
- `bffd766` — `docs: registra fechamento do D4 CEMPRE`
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
recente: `5b716907f9c02aa4b7ebb5a4c949d4147a0e7521` (D7 — integração
explícita e selecionável de `agregados_v3` ao pipeline nacional — ver
seção 12).

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

## 9. Auditoria integrada D1-D4 — binding cache/request (bloqueador fechado)

Status técnico:

`AUDITORIA_INTEGRADA_D1_D4 = APROVADA_APOS_CORRECAO`

`BINDING_CACHE_REQUEST = APROVADO`

`BINDING_VARIAVEIS_OBRIGATORIAS = APROVADO`

`PLANO_COMPLETUDE_INTEGRADOS = APROVADO`

`CACHE_RETOMABILIDADE_PRECONDICAO = APROVADA`

`LONG_NAO_PODE_SER_CONSTRUIDA_INCOMPLETA = CONFIRMADO`

`MANIFESTO_NAO_MASCARA_INCOMPLETUDE = CONFIRMADO`

`GUARDA_AUTORIZACAO = APROVADA`

`DRY_RUN_ZERO_EFEITOS_COLATERAIS = CONFIRMADO`

`PIPELINE_PRE_EXECUCAO_CEMPRE = APROVADO`

`PODE_PROSSEGUIR_PARA_GATE_DE_EXECUCAO_REAL = SIM`

`EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = NÃO`

Commit substantivo da correção:

`1b590587168112778011583ca49d2fbc86aa66af` — `fix: vincula cache ao
request CEMPRE`

Push: **CONCLUIDO**

### Causa raiz

A auditoria integrada final do pipeline nacional CEMPRE (D1-D4) reproduziu
offline um único bloqueador pré-extração: um cache/resultado
estruturalmente válido (hash íntegro, schema SIDRA correto) NÃO estava
vinculado semanticamente ao request esperado. Foram reproduzidos dois
sub-cenários do mesmo bloqueador:

1. um único cache válido copiado para os nomes de vários `request_id`
   esperados era aceito em todos eles (integridade/hash e schema não
   bastam para provar pertencimento);
2. um payload estruturalmente válido contendo SOMENTE a variável 708 (de
   um grupo de 7 solicitado) também era aceito como resultado completo do
   lote — falsa completude por variáveis parciais.

### Correção aplicada

Centralizada em um único helper, `_validar_resultado_corresponde_request`,
reutilizado em todos os pontos de entrada de um resultado no pipeline
(sem duplicar a regra):

- **`envelope.request_id`** validado dentro de `load_cached_request` —
  divergência entre o `request_id` do envelope e o `request_id` esperado
  invalida o cache explicitamente (nunca corrigido/inferido pelo nome do
  arquivo);
- **ano** validado semanticamente: todo ano presente no payload precisa
  ser exatamente o ano do request esperado;
- **território** validado semanticamente: UF/município presentes no
  payload precisam corresponder ao território do request esperado (UF
  derivada dos 2 primeiros dígitos do código municipal — convenção já
  usada e validada em `constroi_calendario_territorial_ibge.py`, não uma
  heurística nova);
- **variáveis** validadas em duas pontas:
  `obrigatorias_solicitadas ⊆ variaveis_payload ⊆ variaveis_esperadas`,
  onde `obrigatorias_solicitadas = variaveis_esperadas ∩
  VARIAVEIS_OBRIGATORIAS`. As **seis variáveis básicas obrigatórias**
  são:
  - `706` — número de unidades locais;
  - `707` — pessoal ocupado total;
  - `708` — pessoal ocupado assalariado;
  - `5944` — pessoal assalariado médio;
  - `662` — salários e outras remunerações;
  - `10143` — salário médio mensal em reais.

  A variável `1606` permanece opcional/diagnóstica — presente ou ausente,
  não afeta a validade do resultado. Qualquer variável fora do grupo
  solicitado continua proibida (rejeição preservada, não relaxada).

A mesma barreira semântica foi aplicada em três pontos, sem três
implementações paralelas:

- **cache existente**: `_resultado_a_partir_do_cache` (usada por
  `fetch_request` em cache hit e por `load_results_from_cache`/D2) —
  cache semanticamente incompatível vira resultado com erro explícito,
  nunca sucesso;
- **resposta NOVA de rede**: `fetch_request`, imediatamente após
  `validate_sidra_payload` e ANTES de `save_cached_request`/retorno de
  sucesso — uma resposta HTTP 200 com schema válido mas semanticamente
  incompleta (ex.: só 708) nunca chega a ser persistida como cache
  válido; tratada como falha permanente (sem gastar retries, já que
  incompatibilidade semântica não se resolve por retry);
- **bypass de `build_long_from_results`**: `_sanitizar_resultados_contra_request`,
  aplicada antes de `avalia_completude_plano` dentro de
  `build_long_from_results` — protege mesmo contra uma lista de
  resultados construída manualmente (sem passar pelo cache), reescrevendo
  como falha qualquer resultado marcado como sucesso mas semanticamente
  incompatível com o request esperado do plano.

### Impacto verificado

- payload parcial (ex.: só 708) e cache trocado (A copiado para B) NUNCA
  contam como sucesso na completude (`avalia_completude_plano`);
- `build_long_from_results` nunca produz uma long "completa" a partir de
  um resultado semanticamente incompatível — falha explicitamente
  (`ValueError`, "incompleto") antes de normalizar/concatenar;
- `validate_manifest` não foi alterado (nem deveria: não é o lugar da
  correção) — como a barreira atua antes da aceitação do resultado, não
  existe caminho normal para um manifesto registrar `completo=True` sobre
  um resultado semanticamente incompatível;
- `dry_run_national_pipeline` classifica cache semanticamente
  incompatível como `invalido` (nunca como ausente), produz bloqueador
  explícito e `pronto_para_execucao_real=False` — reproduzido tanto para
  um único request trocado quanto em escala (todos os requests de um
  plano sintético de 27 recebendo o mesmo payload parcial/trocado:
  resultado NUNCA é "todos válidos, pronto=True").

### Testes

- 234/234 testes CEMPRE passando (`tests.test_constroi_painel_cempre`),
  incluindo os testes adversariais dos dois recheck focais: envelope
  `request_id` divergente, ano/território/variáveis errados, cache A
  copiado para B, envelope correto + payload de outro lote, plano
  sintético A/B/C com payload de A em todos, bypass manual de
  `build_long_from_results`, payload contendo apenas 708, ausência
  individual de cada uma das seis variáveis obrigatórias, payload válido
  sem 1606, payload válido com 1606, variável extra fora do grupo,
  resposta nova de rede semanticamente incompatível não persistida em
  cache, dry run com cache semanticamente incompatível (isolado e em
  escala);
- 44/44 testes territoriais passando (`tests.test_constroi_calendario_territorial_ibge`),
  inalterado;
- `AUDITORIA_ZERO_REDE = SIM` — todo teste novo usa sessão/`fetch_request`
  mockados; nenhuma chamada real à API SIDRA/IBGE.

### O que a auditoria AINDA NÃO validou

A aprovação acima cobre exclusivamente a integridade PRÉ-EXECUÇÃO
(binding cache/request, completude offline, guardas, dry run). Ainda NÃO
foram validados, e pertencem às próximas etapas:

- executor real nacional;
- rede real em 351 chamadas;
- retries reais em escala nacional;
- backoff real;
- rate limiting;
- paralelismo;
- comportamento do SIDRA sob carga;
- interrupção durante HTTP;
- retomada do executor real;
- performance real;
- cobertura real retornada pelo SIDRA;
- completude real da primeira coleta.

`PODE_PROSSEGUIR_PARA_GATE_DE_EXECUCAO_REAL = SIM` significa apenas que a
infraestrutura pré-execução está suficientemente íntegra para começar a
projetar/habilitar o ramo real — **NÃO** significa
`EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = SIM`. Não declara
`PAINEL_TECNICO_CONSTRUIDO`.

---

## 10. D5 — Executor controlado nacional

Status técnico:

`D5_EXECUTOR_CONTROLADO_IMPLEMENTADO = SIM`

`D5_SPOT_CHECK = APROVADO`

`GUARDA_EXECUCAO_REAL = APROVADA`

`CACHE_PRE_SCAN = APROVADO`

`CACHE_VALIDO_NAO_REEXECUTA = CONFIRMADO`

`CACHE_INVALIDO_BLOQUEIA_ANTES_REDE = CONFIRMADO`

`PERSISTENCIA_REQUEST_A_REQUEST = CONFIRMADA`

`FAIL_FAST = CONFIRMADO`

`RETOMABILIDADE_EXECUTOR_SIMULADA = APROVADA`

`RELOAD_CACHE_COMO_FONTE_FINAL = CONFIRMADO`

`COMPLETUDE_POS_COLETA = APROVADA`

`LONG_APENAS_SE_COMPLETO = CONFIRMADO`

`MANIFESTO_APENAS_APOS_LONG = CONFIRMADO`

`EXECUTOR_D5 = APROVADO`

`PODE_PROSSEGUIR_PARA_GATE_DA_PRIMEIRA_EXECUCAO = SIM`

`EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = NÃO`

Commit substantivo:

`7218c56b36f0ef665d6e1a4daf55ce0dfa12b86f` — `feat: implementa executor
controlado CEMPRE`

Push: **CONCLUIDO**

O D5 implementou o executor real do pipeline nacional CEMPRE (até então
bloqueado por `NotImplementedError` no D4) e passou por spot-check
independente no Codex, aprovado sem bloqueadores.

### Arquitetura

Três funções, sem duplicação de contrato:

- `execute_missing_requests(plano, cache_dir, session, timeout,
  max_retries, backoff_base)` — coleta pura, sequencial, request a
  request; testável com plano sintético pequeno (não exige simular os
  351 requests nacionais);
- `execute_national_pipeline(config, autorizacao_extracao, session)` —
  orquestração completa: guarda de autorização, plano, conflito de
  artefatos, coleta, recarga, completude, long, manifesto;
- `run_national_pipeline(config, modo, autorizacao_extracao, session)` —
  ponto de entrada único por modo (`dry_run` inalterado;
  `execute` + `autorizacao_extracao=True` agora delega para
  `execute_national_pipeline` em vez de levantar `NotImplementedError`).

### Ordem operacional aprovada

1. validar autorização (`_garantir_autorizacao_execucao_real`, mesma
   guarda do D4 — `PermissionError` antes de qualquer plano/rede);
2. construir/validar plano nacional (D1, `build_national_request_plan`);
3. verificar conflitos dos outputs finais (long/manifesto existentes com
   `overwrite=False`) — bloqueia ANTES de qualquer coleta;
4. pre-scan de TODOS os caches do plano (reaproveita
   `load_results_from_cache`/D2, incluindo a vinculação semântica da
   seção 9: `envelope.request_id`, ano, território, variáveis
   obrigatórias);
5. bloquear a execução inteira se QUALQUER cache esperado for inválido
   — zero chamada de rede, mesmo para outros itens ausentes do mesmo
   plano;
6. executar sequencialmente (sem paralelismo/async) SOMENTE os requests
   com cache ausente;
7. persistir cada cache válido imediatamente via `fetch_request`
   (nenhuma segunda escrita de cache no executor);
8. fail-fast na primeira falha — requests restantes do plano não são
   buscados;
9. recarregar TODOS os resultados a partir do cache em disco
   (`load_results_from_cache` de novo — nunca os objetos retidos em
   memória durante a coleta: a fonte de verdade final é sempre o que
   ficou persistido);
10. avaliar completude (`avalia_completude_plano`) sobre essa recarga;
11. somente se `completo=True` E a coleta teve sucesso, construir a long
    (`build_long_from_results`, sem lógica paralela);
12. persistir a long em Parquet (`write_long_parquet`, `overwrite`
    repassado do config — nunca sobrescreve silenciosamente);
13. somente após a long persistida com sucesso, construir o manifesto
    (`build_manifest`, reaproveitando a proveniência real da coleta);
14. persistir o manifesto (`write_manifest`);
15. retornar o relatório final (contagens, `request_id_falha` se houver,
    `completo`, caminhos, `git_commit`, `sucesso_execucao` — nunca trata
    `autorizacao_extracao=True` como sinônimo de sucesso).

### Cache

- **cache válido**: reaproveitado; sem nova chamada de rede; sem
  regravação; bytes/`mtime` preservados (testado explicitamente);
- **cache ausente**: único estado elegível para fetch;
- **cache inválido** (corrompido, schema inválido, `request_id`
  trocado, payload de outro lote, variável obrigatória ausente):
  bloqueia ANTES da rede; nunca é apagado; nunca é sobrescrito; nunca
  vira cache miss — permanece em disco para diagnóstico.

`overwrite=True` se aplica exclusivamente aos ARTEFATOS FINAIS (long e
manifesto) — nunca relaxa a política de cache inválido, que é sempre
bloqueante independentemente de `overwrite`.

### Retomabilidade (SIMULADA)

Propriedade validada com sessões HTTP fake (mock), reproduzindo o
cenário de interrupção lógica:

- **Run 1**: A → sucesso, cache persistido; B → falha; C → não
  executado (fail-fast);
- **Run 2** (mesmo `cache_dir`): A → reaproveitado do cache (zero nova
  chamada); B → executado; C → executado.

`RETOMABILIDADE_EXECUTOR_SIMULADA = APROVADA`. Isso é retomabilidade
SIMULADA com sessões fake — a interrupção FÍSICA real de um processo
(kill, queda de energia, perda de conexão a meio de uma resposta HTTP em
andamento) ainda NÃO foi validada.

### Falhas parciais (comportamento conhecido, NÃO bloqueante)

Se a long for persistida com sucesso e a persistência do manifesto
falhar (ex.: `FileExistsError` por conflito com `overwrite=False`,
ou qualquer outra falha após `write_long_parquet`):

- a execução falha explicitamente (`sucesso_execucao=False`);
- o manifesto final não existe;
- a long permanece em disco como artefato parcial detectável (não é
  removida — o pipeline nunca desfaz uma escrita já concluída);
- uma nova execução com `overwrite=False` bloqueia antes da rede ao
  detectar o conflito de artefato existente (mesma guarda do dry run);
- requer intervenção explícita (decidir `overwrite=True` conscientemente
  ou mover/remover o artefato parcial manualmente).

Não há rollback transacional entre long e manifesto — isso é
deliberado e conhecido, não um bug.

### Testes

- 253/253 testes CEMPRE passando (`tests.test_constroi_painel_cempre`),
  incluindo os testes obrigatórios do D5: guarda de autorização, cache
  válido/ausente/inválido (corrompido, `request_id` trocado, variável
  obrigatória ausente), persistência request a request, fail-fast,
  retomada simulada, recarga do cache como fonte final, completude
  pós-coleta, long somente se completo, manifesto somente após long
  persistida, proteção `overwrite=False` para long e manifesto,
  manifesto final recarregável via `load_manifest`/`validate_manifest`,
  dry run inalterado e sem efeitos colaterais após o D5;
- 44/44 testes territoriais passando, inalterado;
- `AUDITORIA_D5_ZERO_REDE = SIM` — todo teste novo usa sessão/`fetch_request`
  mockados; `cempre.requests.get` real é explicitamente bloqueado nos
  testes de alto nível; nenhuma chamada real à API SIDRA/IBGE.

### Dry run nacional real (diagnóstico, não autorização)

Estado atual do cache nacional real (`CACHE_DIR`), verificado via dry
run somente leitura:

- `n_requests_esperados = 351`;
- `n_cache_validos = 0`;
- `n_cache_ausentes = 351`;
- `n_cache_invalidos = 0`;
- `n_requests_que_exigiriam_rede = 351`;
- `pronto_para_execucao_real = True`.

`pronto_para_execucao_real=True` é SOMENTE diagnóstico técnico — não
significa `EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = SIM`. Nenhuma extração
real foi realizada nesta etapa.

### O que o D5 ainda NÃO validou

- comportamento real da API SIDRA;
- 351 chamadas reais;
- necessidade real de rate limiting;
- retries em condições reais;
- adequação do timeout real;
- backoff sob falhas reais;
- performance total da coleta;
- duração real da coleta;
- interrupção FÍSICA de processo/energia;
- retomada após interrupção física real (só a simulada, com mocks, foi
  validada);
- cobertura efetivamente retornada pela API;
- qualidade efetiva dos dados coletados.

O D5 fecha o executor controlado nacional. Não declara
`PAINEL_TECNICO_CONSTRUIDO` e não autoriza a extração nacional CEMPRE.

---

## 11. D6 — Adaptador CEMPRE para a API de Dados Agregados do IBGE

Status técnico:

`D6_ADAPTADOR_AGREGADOS = IMPLEMENTADO`

`VALIDACAO_PAYLOAD_AGREGADOS = APROVADA`

`NORMALIZACAO_AGREGADOS = APROVADA`

`EQUIVALENCIA_LONG_CANONICA = APROVADA`

`PROVENIENCIA_FONTE_API = APROVADA`

`CACHE_ENTRE_FONTES_NAO_COLIDE = CONFIRMADO`

`BINDING_AGREGADOS = APROVADO`

`COLETA_NACIONAL = PAUSADA`

`EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = NÃO`

Commit substantivo:

`4a4355eb94305a5bb7055fa99e23f078f319f814` — `feat: adiciona adaptador
CEMPRE para API de agregados`

Push: **CONCLUIDO**

### Motivação

A coleta nacional real via `apisidra.ibge.gov.br` foi pausada porque o
primeiro request em produção recebeu `HTTP 403` com
`Server: cloudflare` / `Cf-Mitigated: challenge` — bloqueio operacional
neste ambiente, causa raiz inconclusiva. Uma auditoria focal de
equivalência (probes reais, zero coleta nacional) comparou a apisidra
legada com a API oficial de Dados Agregados do IBGE
(`servicodados.ibge.gov.br/api/v3/agregados`) para o agregado 1685 e
concluiu `API_AGREGADOS_EQUIVALENCIA = APROVADA_PARA_IMPLEMENTAR_ADAPTADOR`
— equivalência semântica confirmada para município, ano, variável, valor
(incluindo o caso especial real `"..."` de Pescaria Brava/SC, 2007,
preservado literalmente), unidade e cobertura territorial (Amajari/RR e
Roraima completa, 2019).

### Arquitetura implementada

Fonte **paralela e explicitamente distinta** da apisidra legada — nada do
legado foi reescrito (`validate_sidra_payload`, `normalize_long`,
`parse_sidra_value`, fixtures apisidra e contratos D1-D5 permanecem
intactos):

- `build_requests_agregados` — mesma granularidade lógica nacional (ano ×
  UF × grupo de variáveis) já aprovada em D1, URL/schema da API de Dados
  Agregados; `request_id` derivado de um texto canônico DIFERENTE do de
  `build_requests` (prefixado por `FONTE_API_AGREGADOS`), garantindo que
  o mesmo lote lógico nunca colida no mesmo arquivo de cache que a
  apisidra;
- `validate_agregados_payload` — validação estrutural do schema real
  observado (`bloco.id/variavel/unidade/resultados[].series[].localidade/serie`),
  falha explícita para forma inesperada;
- `normalize_long_agregados` — mapeia o schema novo DIRETAMENTE para a
  mesma long canônica (`_COLUNAS_LONG`) de `normalize_long`, sem fabricar
  campos apisidra artificiais; reutiliza `parse_sidra_value` sem duplicar
  parser de símbolos/valores;
- `fetch_request_agregados` — espelha `fetch_request` (mesmo
  retry/timeout/backoff/SHA-256/contrato de resultado), valida com
  `validate_agregados_payload` e aplica a MESMA vinculação semântica
  (`_validar_resultado_corresponde_request`, via despacho por
  `fonte_api`) antes de `save_cached_request`;
- `FONTE_API_SIDRA`/`FONTE_API_AGREGADOS` — identidade explícita da fonte,
  gravada no envelope de cache (`save_cached_request`) e verificada no
  carregamento (`load_cached_request(..., fonte_api_esperada=...)`).

### Proveniência entre fontes (requisito crítico)

Duas barreiras independentes, nenhuma delas dependendo só da URL ser
diferente:

1. **`request_id` fisicamente distinto** — o mesmo lote lógico
   (ano/UF/variáveis) produz `request_id`/caminho de cache diferentes
   para `apisidra` e `agregados_v3`, então as duas fontes nunca escrevem
   no mesmo arquivo;
2. **`fonte_api` no envelope** — cache de uma fonte é rejeitado
   explicitamente (erro citando `fonte_api`) se apresentado para um
   request da outra fonte, mesmo com hash/schema internamente
   consistentes. Cache legado gravado antes do D6 (sem o campo
   `fonte_api`) continua sendo tratado como `apisidra` — retrocompatível,
   nunca destruído.

### Verificação focal pré-commit

Confirmado por teste e/ou inspeção de código, sem necessidade de
refatoração adicional:

- apisidra legado continua retrocompatível (fixtures/testes antigos
  passam sem alteração);
- cache legado sem `fonte_api` continua entendido como `apisidra`;
- cache `apisidra` não é aceito como `agregados_v3`, e vice-versa;
- `request_id` das duas fontes não colide para o mesmo lote lógico;
- `normalize_long_agregados` produz exatamente `_COLUNAS_LONG`;
- `parse_sidra_value` é reutilizado sem duplicação;
- Pescaria Brava/SC, 2007, `"..."` continua `indisponivel` também via
  `agregados_v3`;
- nenhuma função `agregados_v3` está referenciada em
  `dry_run_national_pipeline`, `execute_national_pipeline`,
  `execute_missing_requests`, `run_national_pipeline` ou
  `NationalRunConfig` — confirmado por busca textual, resultado vazio;
  a fonte padrão nacional continua sendo exclusivamente `apisidra`.

### Fixtures reais versionadas

Três respostas REAIS da API de Dados Agregados (mesmos probes da
auditoria de equivalência, zero chamada HTTP nova nesta etapa),
adicionadas explicitamente ao Git com `git add -f` (o diretório
`data/raw/ibge/cempre/fixtures/` é ignorado por padrão; estas fixtures
são exceções pequenas e deliberadas, mesma política já aplicada às
fixtures apisidra existentes):

- `agregados_v3_1685_n6_1400027_amajari_rr_2019.json` — Amajari/RR, 2019,
  6 variáveis obrigatórias;
- `agregados_v3_1685_n6_4212650_pescaria_brava_2007.json` — Pescaria
  Brava/SC, 2007, 6 obrigatórias com `"..."`;
- `agregados_v3_1685_n6_3166600_serra_da_saudade_2018_var708.json` —
  Serra da Saudade/MG, 2018, variável 708.

Necessárias para reprodutibilidade: os testes do D6 dependem delas
diretamente (`_carrega_fixture`) e falhariam em um clone limpo sem essas
fixtures versionadas.

### Testes

- 289/289 testes CEMPRE passando (`tests.test_constroi_painel_cempre`),
  incluindo os 36 novos do D6: schema válido/inválido do payload
  Agregados, normalização numérica, `"..."` → `indisponivel`,
  equivalência linha a linha com as fixtures apisidra reais (Amajari via
  Roraima, Pescaria Brava), unidade e labels, binding completo (1606
  opcional, variável obrigatória ausente/extra rejeitadas, UF/ano
  errados rejeitados), identidade de fonte (cache cruzado rejeitado nos
  dois sentidos, cache legado retrocompatível, `request_id` distinto),
  `fetch_request_agregados` com sessão mockada (payload parcial não cria
  cache, schema inválido não é sucesso, zero rede real);
- 44/44 testes territoriais passando, inalterado;
- zero chamada HTTP real em toda a implementação e nos testes do D6 —
  todas as fixtures reaproveitam respostas já obtidas na auditoria de
  equivalência.

### Próximo passo

`agregados_v3` ainda NÃO está integrado ao executor nacional (D5) — a
fonte padrão nacional continua exclusivamente `apisidra`. O próximo
passo é **integrar D6 ao D5 de forma explícita e selecionável** (ex.:
campo de configuração explícito em `NationalRunConfig` para escolher a
fonte, nunca uma troca silenciosa de padrão), preservando a guarda de
autorização e a política de não misturar cache entre fontes também no
nível do orquestrador nacional.

O D6 fecha o adaptador isolado da API de Dados Agregados. Não declara
`PAINEL_TECNICO_CONSTRUIDO`, não integra `agregados_v3` ao D5 e não
autoriza a extração nacional CEMPRE.

---

## 12. D7 — Integração da API agregados_v3 ao pipeline nacional

Status técnico:

`D7_INTEGRACAO_D6_D5 = IMPLEMENTADA`

`FONTE_API_SELECIONAVEL = SIM`

`DEFAULT_APISIDRA_RETROCOMPATIVEL = SIM`

`DRY_RUN_AGREGADOS = APROVADO`

`EXECUTOR_AGREGADOS = APROVADO_EM_SIMULACAO`

`CACHE_SOURCE_AWARE = APROVADO`

`NORMALIZADOR_POR_FONTE = APROVADO`

`MANIFESTO_FONTE_EXPLICITA = APROVADO`

`RETOMABILIDADE_AGREGADOS_SIMULADA = APROVADA`

`D7_ZERO_REDE_REAL = SIM`

`COLETA_NACIONAL = PAUSADA`

`EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = NÃO`

Commit substantivo:

`5b716907f9c02aa4b7ebb5a4c949d4147a0e7521` — `feat: integra fonte
agregados ao pipeline CEMPRE`

Push: **CONCLUIDO**

### O que mudou

O D6 (seção 11) implementou `agregados_v3` de forma isolada, sem ligação
ao executor nacional. O D7 conecta as duas frentes de forma **explícita e
selecionável**, sem trocar silenciosamente o padrão:

- `NationalRunConfig` ganhou o campo `fonte_api`, com **default
  `FONTE_API_SIDRA`** — todo código/configuração anterior ao D7 continua
  se comportando exatamente como antes. Fontes válidas:
  `apisidra`/`agregados_v3`; qualquer outro valor falha explicitamente
  (`ValueError`) na construção do config, antes de qualquer plano/rede;
- plano nacional permanece **351 requests** (13 anos × 27 UFs × 1 grupo)
  para as duas fontes — `build_national_request_plan_agregados` (novo)
  espelha `build_national_request_plan` (D1), trocando só o builder de
  requests; a validação (`validate_national_request_plan`) é a mesma
  para as duas, sem duplicação;
- `dry_run_national_pipeline` funciona para as duas fontes e agora inclui
  `fonte_api` no relatório;
- a leitura de cache já era source-aware desde o D6
  (`_resultado_a_partir_do_cache`/`load_cached_request` despacham
  validação/binding por `fonte_api`) — o D7 não precisou alterar essa
  camada, só confirmá-la por teste no nível do orquestrador nacional;
- `execute_missing_requests` despacha o fetch por fonte via
  `fetch_request_by_source` (novo dispatcher pequeno, sem duplicar o
  loop sequencial único);
- `build_long_from_results` despacha a normalização por fonte via
  `_normalize_long_por_fonte` (novo dispatcher pequeno: `apisidra` →
  `normalize_long`, `agregados_v3` → `normalize_long_agregados`; resto
  da função — completude, `validate_long`, `reconcile_territorial`,
  ordenação — inalterado);
- `build_manifest` registra `fonte["fonte_api"]` explicitamente (via novo
  `_fonte_api_do_plano`, que falha se o plano misturar fontes) e
  `build_request_provenance` registra `fonte_api` por request — nenhum
  manifesto produzido é ambíguo quanto a qual API gerou os caches/long;
- `request_id`/`hash_plano_canonico` já distinguiam as duas fontes desde
  o D6 (URLs e `request_id` diferentes) — confirmado por teste explícito
  no nível do plano nacional completo, nenhuma mudança de código
  necessária.

### Verificado

- executor `agregados_v3` aprovado **em simulação** (sessão HTTP fake):
  execução sequencial, persistência request a request, fail-fast (A
  sucesso, B falha, C não executado) e retomada (reaproveita A, busca só
  B/C) — mesmas propriedades já aprovadas para `apisidra` no D5;
- teste end-to-end sintético com `agregados_v3`: plano de 27 requests
  (calendário sintético), caches ausentes → fetch fake → persistência →
  reload do disco → completude → `normalize_long_agregados` → long →
  manifesto, com `sucesso_execucao=True`, manifesto recarregável e
  validado (`load_manifest`/`validate_manifest`);
- cache de uma fonte apresentado a um request da outra continua rejeitado
  explicitamente (mesma barreira do D6, agora exercida também no fluxo
  nacional completo).

### Testes

- 317/317 testes CEMPRE passando (289 anteriores + 28 novos do D7:
  seleção de fonte, plano por fonte, dry run por fonte, cache
  cross-fonte rejeitado, dispatch de fetch, dispatch de normalização,
  manifesto por fonte, fail-fast/retomada `agregados_v3`, end-to-end
  sintético);
- 44/44 testes territoriais passando, inalterado;
- zero chamada HTTP real — todo teste de alto nível bloqueia
  explicitamente `requests.get` real e usa sessão/fetch mockados.

### Próximo passo

1. executar dry run nacional usando explicitamente
   `fonte_api=agregados_v3` (real, sobre o `CACHE_DIR` de produção,
   somente leitura) e confirmar: 351 requests; zero caches `agregados_v3`
   válidos inicialmente (ainda não há coleta real); zero caches
   inválidos; nenhuma colisão com cache `apisidra` residual (arquivos
   antigos são ignorados, nunca reaproveitados sob a fonte errada); zero
   conflito de output (long/manifesto ainda não existem);
2. definir um gate operacional curto para a primeira coleta real via
   `agregados_v3` (critérios de entrada/saída, parâmetros conservadores
   de timeout/retries/backoff);
3. somente depois solicitar autorização humana explícita
   (`EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = SIM`);
4. realizar a primeira coleta nacional via `agregados_v3`;
5. após a coleta, auditar cobertura e qualidade dos dados antes de
   declarar qualquer `PAINEL_TECNICO_CONSTRUIDO`.

O D7 fecha a integração explícita e selecionável entre D6 e D5. Não
declara `PAINEL_TECNICO_CONSTRUIDO` e não autoriza a extração nacional
CEMPRE.

---

## 13. Camada operacional

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

## 14. Proximos passos

1. executar dry run nacional usando explicitamente `fonte_api=agregados_v3`
   (real, sobre o `CACHE_DIR` de produção, somente leitura) e confirmar:
   351 requests; zero caches `agregados_v3` válidos inicialmente (ainda
   não há coleta real por essa fonte); zero caches inválidos; nenhuma
   colisão com cache `apisidra` residual (arquivos antigos são ignorados,
   nunca reaproveitados sob a fonte errada); zero conflito de output
   (long/manifesto ainda não existem);
2. definir o gate operacional da PRIMEIRA execução real via
   `agregados_v3` (critérios explícitos de entrada/saída — distinto do
   gate de infraestrutura já aprovado nos D5/D7);
3. decidir explicitamente os parâmetros iniciais conservadores da
   primeira coleta: `timeout`; `max_retries`; `backoff_base`; execução
   sequencial (sem paralelismo); critérios de interrupção manual;
4. somente após decisão humana explícita:
   `EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = SIM`;
5. executar a primeira coleta nacional via `agregados_v3`
   (`execute_national_pipeline`, `fonte_api=agregados_v3`,
   `modo=MODO_EXECUCAO_REAL`, `autorizacao_extracao=True`);
6. acompanhar progresso e falhas durante a coleta real;
7. ao final, verificar: 351 requests; caches válidos; zero caches
   inválidos; completude;
8. construir/validar long e manifesto (já automático em
   `execute_national_pipeline` quando `completo=True`);
9. auditar cobertura e qualidade dos dados efetivamente coletados antes
   de declarar qualquer `PAINEL_TECNICO_CONSTRUIDO`.

Nao reabrir Fase 0, calendario territorial, D2, D3, D4, D5, D6 ou D7 sem
anomalia concreta. `PODE_PROSSEGUIR_PARA_GATE_DA_PRIMEIRA_EXECUCAO = SIM`
e `D7_INTEGRACAO_D6_D5 = IMPLEMENTADA` (seção 12) autorizam prosseguir
para o DESENHO do gate da primeira execução — NÃO equivalem a
`EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = SIM` e não autorizam, por si só,
executar a primeira coleta.

---

## 15. Extracao nacional CEMPRE

Status:

**EXTRAÇÃO NACIONAL CEMPRE = NÃO AUTORIZADA**

Os commits territorial, Fase 0, D1, D2, D3, D4, a correção do binding
cache/request (seção 9), o executor controlado D5 (seção 10), o
adaptador CEMPRE para Dados Agregados D6 (seção 11) e a integração D6-D5
D7 (seção 12), por si só, não autorizam a extração — inclusive com
`PIPELINE_PRE_EXECUCAO_CEMPRE = APROVADO`,
`PODE_PROSSEGUIR_PARA_GATE_DE_EXECUCAO_REAL = SIM`,
`PODE_PROSSEGUIR_PARA_GATE_DA_PRIMEIRA_EXECUCAO = SIM` e
`D7_INTEGRACAO_D6_D5 = IMPLEMENTADA`.

O ramo real do orquestrador (`execute_national_pipeline`) já está
implementado, aprovado em spot-check (D5) e agora aceita explicitamente
`fonte_api=apisidra` ou `fonte_api=agregados_v3` (D7, aprovado em
simulação com sessão HTTP fake) — a lacuna que falta não é mais de
implementação, é de validação sob condições reais e de decisão humana
explícita. A fonte candidata operacional para a próxima primeira coleta
é `agregados_v3`, devido ao Cloudflare Challenge observado na `apisidra`
neste ambiente — mas `agregados_v3` ainda NÃO foi usada em nenhuma
coleta real, e essa escolha ainda não foi formalizada como decisão
executada.

Antes de qualquer extração nacional ainda é necessário:

- dry run nacional real explícito com `fonte_api=agregados_v3` (seção
  14, item 1);
- definição do gate operacional da primeira execução (seção 14, item 2);
- decisão explícita dos parâmetros conservadores iniciais (timeout,
  max_retries, backoff, critérios de interrupção);
- validação do executor real sob rede real (retries, backoff, rate
  limiting, paralelismo, interrupção física/retomada real — ver seção
  10, "O que o D5 ainda não validou"; a integração D7 só foi validada em
  simulação, nunca contra a API real);
- autorização explícita para a extração nacional.

---

## 16. D8 — Primeira coleta nacional real via `agregados_v3` (concluída; painel técnico ainda NÃO declarado)

Status técnico:

`COLETA_NACIONAL_AGREGADOS_351 = CONCLUIDA`

`CACHE_AGREGADOS_351 = PERSISTIDO`

`CONSTRUCAO_LONG_AGREGADOS_TENTATIVA_1 = REPROVADA` (bloqueio real,
símbolo `"X"` maiúsculo, 18 linhas, ano 2012, municípios de SC e MT)

`SIMBOLO_X_MAIUSCULO = SIGILO_CONFIRMADO` (documentação oficial do
SIDRA: `X` = valor inibido para não identificar o informante)

`PARSER_SIGILO_X_x = CORRIGIDO`

`LONG_CEMPRE_AGREGADOS = CONSTRUIDA` (reconstrução cache-only, zero rede
nova)

`MANIFESTO_CEMPRE_AGREGADOS = CONSTRUIDO_E_VALIDADO`

`STATUS_DESCONHECIDO = ZERO`

`PAINEL_TECNICO_CONSTRUIDO = NÃO`

`PRONTO_PARA_AUDITORIA_QUALIDADE_COBERTURA = SIM`

`COLETA_NACIONAL = CONCLUIDA` (para a fonte `agregados_v3` — não reabre
automaticamente coleta nacional via `apisidra` nem autoriza nova coleta
nacional sem decisão explícita futura)

`EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = NÃO` (a autorização concedida
cobriu exclusivamente o evento pontual já executado — os 351 requests
`agregados_v3` desta coleta — e não abre automaticamente autorização
para coletas futuras)

Commit substantivo da correção do parser:

`798f54a57ea05cca026571dee1bcde1bca4616a7` — `fix: reconhece sigilo
maiusculo no CEMPRE`

Push: **CONCLUIDO**

### Linha do tempo factual

Preservada integralmente, incluindo o bloqueio real — não reescrita
como se a primeira execução tivesse sido perfeita:

1. Dry run nacional real `agregados_v3` aprovado (seção 14, item 1):
   351 esperados, 0 caches válidos, 351 ausentes, 0 inválidos, sem
   conflito de outputs, `pronto_para_execucao_real=True`.
2. Canário real único aprovado: exatamente 1 chamada HTTP real (UF=RO,
   ano=2007), HTTP 200, `validate_agregados_payload` e binding semântico
   aprovados, normalização em memória aprovada, zero efeito colateral.
3. Autorização humana explícita concedida para a primeira coleta
   nacional real via `agregados_v3`, com os parâmetros conservadores
   default já implementados (`timeout=15.0`, `max_retries=3`,
   `backoff_base=1.0`, execução sequencial, fail-fast).
4. Execução real completou 351/351 requests HTTP com sucesso (1 timeout
   transitório em `request_id=0886246915adfdc3`, recuperado
   automaticamente pelo retry). 351 caches `agregados_v3` persistidos em
   disco, sem nenhuma corrupção.
5. A construção da long foi **corretamente bloqueada** por
   `validate_long`: 18 linhas (ano 2012, municípios de Santa Catarina e
   Mato Grosso) vieram com `valor_bruto="X"` (maiúsculo) — símbolo não
   reconhecido pelo parser vigente (`parse_sidra_value` só aceitava
   `"x"` minúsculo como sigilo). Nenhuma long nem manifesto foram
   criados nesse momento; a guarda de `desconhecido` funcionou como
   projetado (seção 7 deste playbook).
6. Investigação offline (100% a partir dos 351 caches já em disco, zero
   nova chamada de rede) confirmou que essas 18 linhas eram o único
   símbolo não reconhecido em toda a coleta, e que a documentação
   oficial do SIDRA define `X` como "valor inibido para não identificar
   o informante" — equivalente semântico de `x` minúsculo (`sigilo`).
7. Correção focal aplicada em `parse_sidra_value`
   (`src/constroi_painel_cempre.py`): `"x"` e `"X"` agora retornam
   `("sigilo", None)`; nenhum outro símbolo foi tornado permissivo;
   `desconhecido` continua bloqueante para qualquer outro caso;
   `valor_bruto` continua preservado exatamente como recebido (`"x"` ou
   `"X"`, nunca normalizado fisicamente de um para o outro). Testes
   adicionados em `tests/test_constroi_painel_cempre.py`: `"x"` →
   sigilo; `"X"` → sigilo; `valor_bruto` preservado como `"X"` após
   `normalize_long_agregados`; símbolo desconhecido novo (`"Y"`)
   continua bloqueante em `parse_sidra_value` e em `validate_long`.
8. Regressão completa pós-correção: 320/320 testes CEMPRE passando (317
   anteriores + 3 novos); 44/44 testes territoriais passando,
   inalterado. Zero rede nos testes.
9. Reconstrução da long/manifesto feita **inteiramente a partir dos 351
   caches já persistidos** — zero nova chamada HTTP (rede bloqueada
   explicitamente no script de execução; nenhuma tentativa de rede
   ocorreu). `run_national_pipeline` em `modo=execute` reaproveitou
   351/351 caches, executou 0 requests novos, `completo=True`,
   `sucesso_execucao=True`.
10. Long e manifesto validados: `validate_long` aprovado (zero
    duplicatas, zero bloqueios); `load_manifest`/`validate_manifest`
    aprovados sem exceção; `fonte.fonte_api="agregados_v3"`;
    `execucao.n_sucessos=351`, `n_falhas=0`, `completo=True`;
    `codigo.git_commit` do manifesto = `798f54a5...` (commit da
    correção do parser, confirmando a proveniência pós-correção).

### Resultado da long (`data/interim/cempre_long_2007_2019.parquet`)

- 506.870 linhas; 5.570 municípios distintos; anos 2007–2019 (13);
  variáveis: 662, 706, 707, 708, 1606, 5944, 10143 (7 — grupo completo
  contratado);
- distribuição de `status_valor_api`: `observado` = 506.629;
  `indisponivel` = 210; `sigilo` = 18 (todas com `valor_bruto="X"`);
  `zero_real` = 11; `zero_arredondado` = 2; `desconhecido` = 0.

### O que esta seção NÃO declara

- `PAINEL_TECNICO_CONSTRUIDO` — ainda pendente auditoria de cobertura e
  qualidade dos dados efetivamente coletados frente ao esperado;
- adequação analítica de sigilo, comparabilidade RAIS/eSocial ou
  deflator — decisões humanas da seção 19 do `PLAYBOOK_CEMPRE.md`
  (`PAINEL_ANALITICO_APROVADO`);
- autorização para qualquer nova coleta nacional futura (via
  `agregados_v3` ou `apisidra`).

Não reabrir esta coleta nacional sem anomalia concreta. Próximo passo:
auditoria de cobertura/qualidade dos dados efetivamente coletados, antes
de qualquer declaração de `PAINEL_TECNICO_CONSTRUIDO`.

---

## 17. D9 — Auditoria de cobertura e qualidade do painel técnico nacional CEMPRE (aprovada)

Status técnico:

`AUDITORIA_COBERTURA_CEMPRE = APROVADA`

`AUDITORIA_QUALIDADE_CEMPRE = APROVADA`

`COBERTURA_FASE_II = APROVADA`

`COBERTURA_129_CANDIDATOS = APROVADA`

`MANIFESTO_FINAL_CEMPRE = APROVADO`

`PAINEL_TECNICO_CONSTRUIDO = SIM`

`PRONTO_PARA_CONSTRUCAO_ANALITICA = SIM`

`DESENHO_CAUSAL_APROVADO = NÃO` (não inferido a partir da qualidade do
painel técnico — decisão separada, fora do escopo desta auditoria)

Artefatos auditados (inalterados por esta auditoria — tarefa somente
diagnóstica, zero rede, zero escrita):

- `data/interim/cempre_long_2007_2019.parquet`
- `data/raw/ibge/cempre/source_manifest.json`

### Integridade estrutural

- 506.870 linhas; 5.570 municípios distintos; 13 anos (2007–2019); 7
  variáveis (662, 706, 707, 708, 1606, 5944, 10143);
- grid: `5.570 × 13 × 7 = 506.870`, exato;
- zero duplicatas na chave `(codigo_municipio_ibge, ano,
  codigo_variavel_sidra)`;
- cobertura por ano: exatamente 38.990 linhas/ano, todos os 13 anos, sem
  exceção;
- cobertura por variável: exatamente 72.410 linhas/variável, todas as 7,
  sem exceção.

### Distribuição de `status_valor_api`

`observado` = 506.629; `indisponivel` = 210; `sigilo` = 18; `zero_real`
= 11; `zero_arredondado` = 2; `zero_arredondado_negativo` = 0;
`nao_aplicavel` = 0; `desconhecido` = 0.

### Território

`status_territorial`: `existia_no_ano` = 506.646 linhas;
`nao_existia_no_ano` = 224 linhas (32 combinações município-ano × 7
variáveis: 210 `indisponivel`, 11 `sigilo`, 2 `observado`, 1
`zero_real`).

Ressalva territorial registrada (decisão futura da construção
analítica — **não corrigida nem alterada no painel técnico**): dois
municípios com valor observado um ano antes da criação formal segundo o
calendário territorial (DTB), ambos já marcados
`incompatibilidade_territorial=True` pelo próprio pipeline (D2):

- Balneário Rincão/SC, código `4220000`, ano 2012, variável 706
  (número de unidades locais), valor = 1;
- Paraíso das Águas/MS, código `5006275`, ano 2012, variável 706, valor
  = 2.

Mesmo padrão institucional já documentado para Pescaria Brava/2007
(seção 14 do `PLAYBOOK_CEMPRE.md`) — município com atividade econômica
registrada antes da existência político-territorial oficial. Não é
tratado como bloqueador técnico: é isolado (2 municípios, 1 ano), já
sinalizado pelo contrato existente, e a decisão sobre incluir/excluir
esses pontos pertence à fase analítica, não à técnica.

### Sigilo (18 linhas)

100% no ano 2012; 4 municípios (São Miguel da Boa Vista/SC, Figueirão/MS,
Balneário Rincão/SC, Paraíso das Águas/MS); 100% `valor_bruto="X"`,
`status_valor_api="sigilo"`, `valor_numerico=None`. Nenhuma
inconsistência técnica.

### Indisponível (210 linhas)

100% em município-ano que ainda não existia segundo o calendário
territorial; 0 indisponíveis em município já existente — mesmo padrão
institucional documentado (Pescaria Brava).

### Zeros

`zero_real` = 11; `zero_arredondado` = 2. Classificação coerente com o
contrato vigente (seção 7 do `PLAYBOOK_CEMPRE.md`).

### Variável 1606

72.410 linhas; 5.570 municípios; 13 anos — cobertura completa,
estatisticamente equivalente às 6 variáveis obrigatórias. **Permanece
OPCIONAL no contrato de aquisição** — não promovida a obrigatória sem
decisão metodológica explícita.

### Plausibilidade

`validate_cross_measures` (reutilizada, sem lógica paralela): aprovado,
0 violações — 0 casos de `pessoal_ocupado_assalariado (708) >
pessoal_ocupado_total (707)`, 0 valores negativos nas medidas
auditadas.

### Unidades e labels

Todas as 7 variáveis com exatamente 1 combinação nome/unidade — nenhuma
inconsistência.

### Cobertura Fase II e candidatos principais

- 147/147 municípios Fase II presentes na long; 147/147 com 13 anos × 7
  variáveis completos; 0 ausentes; 0 status especiais no subconjunto
  Fase II;
- candidatos principais (`candidato_amostra_principal=True` no cadastro
  causal já existente): 129/129 presentes; 129/129 completos.

### Manifesto

`fonte_api=agregados_v3`; `n_sucessos=351`; `n_falhas=0`;
`completo=True`; SHA-256 do parquet da long consistente com o
registrado no manifesto; `n_linhas=506.870`; `git_commit` da geração =
`798f54a57ea05cca026571dee1bcde1bca4616a7` (commit da correção do
parser — seção 16).

### O que esta seção NÃO declara

- `DESENHO_CAUSAL_APROVADO` — decisão separada, não decorre da
  qualidade/cobertura do painel técnico;
- qualquer regra de transformação long → wide, tratamento de
  incompatibilidade territorial na análise, ou decisão sobre a
  variável 1606 na análise — pertencem à construção do painel
  analítico (ver seção 18, "Próximos passos").

Não reabrir esta auditoria sem anomalia concreta.

---

## 18. Próximos passos (pós-auditoria de cobertura/qualidade)

1. construir o painel analítico município-ano a partir da long técnica;
2. definir regras explícitas para:
   - existência territorial;
   - incompatibilidade territorial;
   - valores especiais;
   - variável 1606;
   - transformação long → wide;
3. integrar o painel CEMPRE ao cadastro causal nacional;
4. auditar a população analítica resultante;
5. somente depois avançar para diagnósticos de identificação causal.

Não iniciar construção analítica ou análise causal antes das decisões
explícitas do item 2. `PAINEL_TECNICO_CONSTRUIDO = SIM` autoriza avançar
para a construção do painel analítico — não autoriza, por si só,
nenhuma decisão de desenho causal.

---

## 19. D10 — Painel analítico CEMPRE município-ano

Status técnico:

`PAINEL_ANALITICO_CEMPRE = CONSTRUIDO`

`CHAVE_MUNICIPIO_ANO = APROVADA`

`REGRA_EXISTENCIA_TERRITORIAL = APLICADA`

`MUNICIPIO_ANO_PRE_CRIACAO_EXCLUIDO = CONFIRMADO`

`STATUS_ESPECIAIS_PRESERVADOS = SIM`

`VARIAVEL_1606_PRESERVADA_COMO_OPCIONAL = SIM`

`COBERTURA_FASE_II_ANALITICA = APROVADA`

`COBERTURA_129_ANALITICA = APROVADA`

`PAINEL_ANALITICO_CEMPRE_APROVADO = SIM`

`PRONTO_PARA_INTEGRAR_CADASTRO_CAUSAL = SIM`

`DESENHO_CAUSAL_APROVADO = NÃO`

Commit substantivo:

`f04991a3f5bf5dfcd98765d95c2d60922a45ccb3` — `feat: constroi painel
analitico CEMPRE`

Push: **CONCLUIDO**

### O que foi construído

Entrada: `data/interim/cempre_long_2007_2019.parquet` (long técnica
nacional, imutável, aprovada em D8/D9 — não alterada nesta etapa).

Novo script `src/constroi_painel_analitico_cempre.py`
(`build_painel_analitico`, `auditar_populacao`,
`build_diagnostico_exclusao_territorial`,
`relatorio_missing_por_variavel`, `validate_painel_analitico`).

Regra territorial analítica (única regra de inclusão/exclusão):
somente `status_territorial == "existia_no_ano"` entra no painel
principal — nunca decidido pelo valor retornado pela API. A long
técnica tem 72.410 município-ano estruturais (5.570 municípios × 13
anos); 32 município-ano são pré-criação territorial e foram excluídos
do painel principal (preservados em diagnóstico, não apagados nem
corrigidos na long). Painel final: **72.378 linhas**, uma por
`(codigo_municipio_ibge, ano)`, chave única — bate exatamente com a
soma dos municípios existentes por ano (5.564×2 + 5.565×4 + 5.570×7).

7 variáveis contratadas viram colunas numéricas (`valor_numerico`
reaproveitado, sem reparsear `valor_bruto`) mais 7 colunas de status
espelhadas (nomenclatura reaproveitada de
`constroi_painel_cempre._VARIAVEL_PARA_COLUNA`, estendida para 1606).
Variável 1606 incluída e preservada como **opcional** no contrato — sua
ausência/status especial nunca exclui município-ano.
`status_valor_api == "desconhecido"` bloqueia a construção
(`ValueError`) — não ocorreu (zero desconhecidos na execução real).

Casos reais confirmados excluídos do painel principal (ano 2012,
apesar de valor `observado`/`zero_real` na long técnica, já
sinalizados com `incompatibilidade_territorial=True` desde D8/D9):
Balneário Rincão/SC (`4220000`) e Paraíso das Águas/MS (`5006275`) —
ambos voltam a aparecer normalmente a partir de 2013, ano de sua
criação oficial.

### Distribuição de NAs por status (painel final, revisão pós-D10)

7 NAs no total, distribuídos em 4 variáveis, **100% originados de
`sigilo`**, **zero originados de `indisponivel`** (esperado: os casos
`indisponivel` da long técnica estavam concentrados em município-ano
pré-criação, removidos pela regra territorial) e **zero de qualquer
outro status**. `zero_real`/`zero_arredondado` continuam valores
numéricos 0 — nunca contados como `n_na`. Nenhuma incompatibilidade
entre NA e status encontrada.

### Correção de isolamento de testes (sem mudança de lógica produtiva)

Ao rodar a suíte técnica completa como regressão, 2 testes de
`TestDryRunPorFonte` (`tests/test_constroi_painel_cempre.py`) falhavam
porque seu `_config()` não isolava `caminho_long`/`caminho_manifesto`
em diretório temporário — o default de `NationalRunConfig` apontava
para os artefatos reais do projeto, que agora existem legitimamente
(D8/D9), gerando um falso conflito de artefato no cenário sintético do
teste. Corrigido **somente no teste** (`_config()` agora passa
`caminho_long`/`caminho_manifesto` dentro do `TemporaryDirectory` já
usado pelo `setUp`) — nenhuma linha de código produtivo
(`constroi_painel_cempre.py`) foi alterada.

### Testes e regressão

- 24/24 testes novos de `tests/test_constroi_painel_analitico_cempre.py`
  passando (pivot long→wide, chave única, exclusão/preservação
  territorial, Balneário Rincão e Paraíso das Águas excluídos, sigilo/
  indisponível/zero/desconhecido tratados corretamente, 1606 não
  determina exclusão, 708/707 preservadas, cobertura Fase II/129
  candidatos);
- 320/320 testes de `tests/test_constroi_painel_cempre.py` passando
  (317 anteriores + 3 do D9 + a correção de isolamento acima, sem
  regressão);
- 44/44 testes territoriais passando, inalterado;
- zero chamada de rede em todas as suítes.

### Artefatos gerados (não versionados — política de `.gitignore`
inalterada)

- `data/processed/cempre_painel_analitico_2007_2019.parquet`
  (72.378 linhas × 19 colunas);
- `outputs/diagnostics/cempre_municipio_ano_excluidos_territorio.csv`
  (224 linhas — rastreabilidade das 32 exclusões território, NÃO usado
  como input causal).

### O que esta seção NÃO declara

- integração ao cadastro causal nacional (próxima etapa, ainda não
  iniciada);
- `DESENHO_CAUSAL_APROVADO` — decisão separada, não decorre da
  construção do painel analítico;
- `PAINEL_TECNICO_CONSTRUIDO` permanece como já estava (D9) — esta
  seção não o reabre nem o altera.

Não reabrir o D10 sem anomalia concreta.

---

## 20. Regra para agentes

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
