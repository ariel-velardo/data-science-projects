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

`7218c56b36f0ef665d6e1a4daf55ce0dfa12b86f`

Commits recentes:

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
recente: `7218c56b36f0ef665d6e1a4daf55ce0dfa12b86f` (D5 — executor
controlado nacional CEMPRE — ver seção 10).

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

## 11. Camada operacional

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

## 12. Proximos passos

1. definir o gate operacional da PRIMEIRA execução real (critérios
   explícitos de entrada/saída — distinto do gate de infraestrutura já
   aprovado no D5);
2. decidir explicitamente os parâmetros iniciais conservadores da
   primeira coleta: `timeout`; `max_retries`; `backoff_base`; execução
   sequencial (sem paralelismo); critérios de interrupção manual;
3. realizar um dry run final imediatamente antes da coleta (estado do
   cache pode mudar entre esta atualização e a execução);
4. somente após decisão humana explícita:
   `EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = SIM`;
5. executar a primeira coleta nacional (`execute_national_pipeline`,
   `modo=MODO_EXECUCAO_REAL`, `autorizacao_extracao=True`);
6. acompanhar progresso e falhas durante a coleta real;
7. ao final, verificar: 351 requests; caches válidos; zero caches
   inválidos; completude;
8. construir/validar long e manifesto (já automático em
   `execute_national_pipeline` quando `completo=True`);
9. auditar cobertura e qualidade dos dados efetivamente coletados;
10. somente depois decidir explicitamente sobre eventual
    `PAINEL_TECNICO_CONSTRUIDO`.

Nao reabrir Fase 0, calendario territorial, D2, D3, D4 ou D5 sem anomalia
concreta. `PODE_PROSSEGUIR_PARA_GATE_DA_PRIMEIRA_EXECUCAO = SIM` (seção
10) autoriza prosseguir para o DESENHO do gate da primeira execução —
NÃO equivale a `EXTRACAO_NACIONAL_CEMPRE_AUTORIZADA = SIM` e não
autoriza, por si só, executar a primeira coleta.

---

## 13. Extracao nacional CEMPRE

Status:

**EXTRAÇÃO NACIONAL CEMPRE = NÃO AUTORIZADA**

Os commits territorial, Fase 0, D1, D2, D3, D4, a correção do binding
cache/request (seção 9) e o executor controlado D5 (seção 10), por si
só, não autorizam a extração — inclusive com
`PIPELINE_PRE_EXECUCAO_CEMPRE = APROVADO`,
`PODE_PROSSEGUIR_PARA_GATE_DE_EXECUCAO_REAL = SIM` e
`PODE_PROSSEGUIR_PARA_GATE_DA_PRIMEIRA_EXECUCAO = SIM`.

O ramo real do orquestrador (`execute_national_pipeline`) já está
implementado e aprovado em spot-check (D5) — a lacuna que falta não é
mais de implementação, é de validação sob condições reais e de decisão
humana explícita.

Antes de qualquer extração nacional ainda é necessário:

- definição do gate operacional da primeira execução (seção 12);
- decisão explícita dos parâmetros conservadores iniciais (timeout,
  max_retries, backoff, critérios de interrupção);
- validação do executor real sob rede real (retries, backoff, rate
  limiting, paralelismo, interrupção física/retomada real — ver seção
  10, "O que o D5 ainda não validou");
- autorização explícita para a extração nacional.

---

## 14. Regra para agentes

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
