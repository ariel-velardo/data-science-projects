# Estado Atual do Projeto

> Documento operacional mutável.
>
> Atualizar quando uma etapa for fechada, um gate mudar ou uma nova unidade
> de trabalho for aberta.
>
> Snapshot: 2026-09-25 (projeto pausado — ver seção 33).

---

## 1. Checkpoint atual

Branch:

`main`

HEAD/origin conhecido após o registro documental do D14:

`c59022fc15e081411ff09bdf8765bc6347d15b00`

Commits recentes:

- `c59022f` — `docs: registra especificacao causal congelada`
- `9f01bd4` — `feat: congela especificacao causal`
- `9871046` — `docs: registra gate de identificacao causal`
- `78d006b` — `feat: implementa gate de identificacao causal`
- `e4c1ef7` — `fix: amplia fallback Plotly sem Kaleido`
- `90293f7` — `docs: registra D12 e protocolo visual academico`
- `b52fff8` — `feat: adiciona notebook academico e identidade visual IPT`
- `11b690e` — `feat: audita suporte temporal da populacao causal`
- `4bfa02a` — `docs: registra painel CEMPRE integrado ao cadastro causal`
- `e906b2b` — `feat: integra painel CEMPRE ao cadastro causal`
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
recente antes deste registro documental: `b52fff82a0f5aa15d7cd9c879265c3356f0e5552`
(notebook acadêmico principal e identidade visual IPT), precedido por
`11b690e` (D12) e `4bfa02a` (registro documental do D11). O D11 — integração do
painel analítico CEMPRE ao cadastro causal — ver seção 20).

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

## 20. D11 — Painel CEMPRE integrado ao cadastro causal

Status técnico:

`PAINEL_CEMPRE_CADASTRO_CAUSAL = CONSTRUIDO`

`MERGE_CADASTRAL = APROVADO`

`POPULACAO_FASE_II_147 = PRESERVADA`

`CANDIDATOS_PRINCIPAIS_129 = PRESERVADOS`

`COORTES_CANDIDATAS = PRESERVADAS`

`POOL_CONTROLES = PRESERVADO`

`OUTCOME_CEMPRE = PRESERVADO`

`PAINEL_INTEGRADO_APROVADO = SIM`

`PRONTO_PARA_AUDITORIA_POPULACAO_CAUSAL = SIM`

`DESENHO_CAUSAL_APROVADO = NÃO`

Commit substantivo:

`e906b2b107f408f55cda7dd46149956b58f9dc12` — `feat: integra painel
CEMPRE ao cadastro causal`

Artefatos canônicos não versionados, usados sem recalcular: painel
analítico CEMPRE D10; cadastro nacional de exposição/elegibilidade; e
cadastro causal Fase II. O painel integrado preserva 72.378 linhas e a
chave única `(codigo_municipio_ibge, ano)`, cobrindo 5.570 municípios.
Os dois merges foram `many_to_one`; zero município do painel ficou sem
correspondência no cadastro nacional.

Foram preservados: 147 Fase II; 129 candidatos principais; coortes
2009–2013 de 21/27/66/13/2; 600 expostos e 4.970 nunca expostos; 4.964
elegíveis e 606 não elegíveis a controle. Nenhum Fase II tem
`pode_ser_controle=True`. Os casos especiais institucionais foram
mantidos sem reinterpretação, inclusive Sobral/CE como
`candidato_com_ressalva`, `primeiro_ano_completo=2010` e
`ano_coorte_candidata=2010`.

Outcome e status CEMPRE foram preservados sem transformação. Não foram
criados `post`, `tratado_ano`, `event_time`, matching, pesos causais ou
estimação. O schema final tem **58 colunas**: 19 do D10 (5 identidade/
território + 7 valores + 7 status), 11 do cadastro nacional e **28** do
cadastro causal. A divergência textual 57×58 foi resolvida: a coluna não
contabilizada era `revisao_prioritaria`, metadata legítima já existente no
cadastro causal; não há colunas duplicadas, sufixos de merge ou colisões.

Validação focal: 22/22 testes D11 passaram, zero rede.

---

## 21. D12 — Auditoria da população causal e suporte temporal CEMPRE

Status técnico:

`AUDITORIA_POPULACAO_CAUSAL = CONCLUIDA`

`CANDIDATOS_129_AUDITADOS = SIM`

`SUPORTE_ADJACENTE_2PRE_3POS = DIAGNOSTICADO`

`SUPORTE_ADJACENTE_3PRE_3POS = DIAGNOSTICADO`

`POOL_CONTROLES_4964 = AUDITADO`

`DISPONIBILIDADE_708 = AUDITADA`

`NOTEBOOK_ACADEMICO_PRINCIPAL = CRIADO`

`IDENTIDADE_VISUAL_IPT = PADRONIZADA`

`AMOSTRA_CAUSAL_FINAL = NÃO DEFINIDA`

`DESENHO_CAUSAL_APROVADO = NÃO`

`PRONTO_PARA_GATE_DE_IDENTIFICACAO = SIM`

Commit substantivo:

`11b690e` — `feat: audita suporte temporal da populacao causal`

O D12 audita, sem selecionar nem persistir uma amostra causal final, a
disponibilidade de calendário e do outcome CEMPRE 708 por município/coorte.
As elegibilidades diagnósticas usam janelas **adjacentes completas**: 2 pré +
3 pós requer `g-2` a `g+2`; 3 pré + 3 pós requer `g-3` a `g+2`. Cada ano
requerido deve existir no painel e possuir outcome numérico utilizável.

Foram auditados 129 candidatos principais, distribuídos nas coortes 2009–2013
em 21/27/66/13/2. Todos passam 2 pré + 3 pós (129/129); 108 passam 3 pré + 3
pós (108/129). Os 21 restantes pertencem à coorte 2009: a janela 3 pré + 3
pós exigiria 2006, fora do período 2007–2019. Essa é uma limitação de
calendário, não de disponibilidade do outcome.

Para os 1.677 município-ano dos 129 candidatos, o CEMPRE 708 está completo:
observado em todas as células, sem missing, sigilo, indisponível ou zero. O
pool canônico contém 4.964 controles estruturais, distinto dos 4.970
municípios nunca expostos. Há uma única célula de 708 sigilosa no pool:
município `5003900`, ano 2012. Ela não afeta a coorte 2009 (4.964/0 em
2 pré + 3 pós / 3 pré + 3 pós), mas reduz as coortes 2010–2013 para
4.963/4.963, pois 2012 integra ambas as janelas adjacentes.

Validação focal: 17/17 testes D12 passaram, offline. Nenhum efeito causal,
pré-tendência, matching, `post`, `event_time`, ATT ou estimador foi criado.

### Protocolo acadêmico e visual

O notebook `notebooks/01_analise_expansao_rede_federal_economia_municipal.ipynb`
é a camada narrativa e acadêmica do projeto; `src/` e `tests/` permanecem a
camada reproduzível e testável. Decisões metodológicas e gráficos relevantes
devem aparecer no notebook principal. Plotly é a biblioteca visual preferencial
e a identidade inspirada no IPT está centralizada em `src/visualizacao_ipt.py`.

O notebook foi salvo com outputs, tabelas estilizadas e cinco figuras Plotly.
Kaleido não está disponível no ambiente; por isso, a exportação estática usa o
fallback HTML local, sem instalar dependências e sem rede.

---

## 22. D13 — Gate de Identificação Causal

Status técnico:

`D13_GATE_IDENTIFICACAO = CONCLUIDO`

`GATE_IDENTIFICACAO = APTO_PARA_ESPECIFICACAO`

`PRE_TENDENCIAS_DESCRITIVAS = CONCLUIDAS`

`POOL_CONTROLES_4964 = CONFIRMADO`

`JANELA_2PRE_3POS = CANDIDATA_PRINCIPAL`

`JANELA_3PRE_3POS = CANDIDATA_SENSIBILIDADE`

`JANELA_ANTECIPACAO_DEFINIDA = NÃO`

`AMOSTRA_CAUSAL_FINAL = NÃO DEFINIDA`

`DESENHO_CAUSAL_APROVADO = NÃO`

`PRONTO_PARA_D14_ESPECIFICACAO = SIM`

Commit substantivo:

`78d006bdaa11e9b351e62b61f428e9602930c86a` — `feat: implementa gate de
identificacao causal`

Commit de correção visual (pré-requisito técnico, sem alterar análise):

`e4c1ef75987c9f06e22f06f0a3f358133949a036` — `fix: amplia fallback Plotly
sem Kaleido`

Push: **CONCLUIDO** (ambos).

### O que o D13 audita e diagnostica (sem estimar nenhum efeito)

O D13 responde dez perguntas de identificação causal exigidas antes de
qualquer estimação — tratamento, comparação, janela, timing, suporte e
pré-tendências —, reaproveitando integralmente os artefatos já aprovados
(D10/D11/D12), sem recalculá-los. Confirmado, reproduzindo exatamente os
números do D12:

- **129 candidatos principais**, coortes 2009=21, 2010=27, 2011=66,
  2012=13, 2013=2;
- suporte temporal: **2 pré + 3 pós = 129/129**; **3 pré + 3 pós =
  108/129**; a coorte 2009 vai de 21/21 (2pré+3pós) para 0/21 (3pré+3pós)
  porque a janela exigiria 2006, fora do painel 2007–2019 — limitação de
  calendário, não de qualidade do outcome;
- pool estrutural de **4.964 controles**, distinto dos **4.970** municípios
  nunca expostos em 2007–2019 — auditado empiricamente (não presumido): os
  4.964 são subconjunto estrito dos 4.970 (0 exceções), nenhum é Fase II
  (0 exceções); os 6 nunca expostos fora do pool ficam de fora por
  `universo_incompleto` (municípios criados após 2007), não por falha de
  exposição.

### Timing e antecipação

`JANELA_ANTECIPACAO_DEFINIDA = NÃO` — o `CONTRATO_CAUSAL.md` e o
`PROTOCOLO_PRE_ANALISE.md` não têm, e o D13 não inventou, uma regra geral
de antecipação. Achado específico preservado, não reinterpretado: dos 129
candidatos, **128 estão sob `origem_coorte='proxy_censo'`** (sem
`ano_transicao`/`primeiro_ano_completo` documentados individualmente) e
**1 — Cabo Frio/RJ, código `3300704`** — está sob
`origem_coorte='institucional_validada'`, com `ano_transicao=2009`
(excluído da estimação no cadastro causal) e `primeiro_ano_completo=2010`
(igual à `ano_coorte_candidata`). Este é o único caso em que o contrato já
tem regra de timing inequívoca; não foi generalizado para os demais 128.

### Pré-tendências descritivas

Baseline (`g-1`), níveis pré-tratamento (por coorte, usando toda a história
pré disponível — 2 a 6 anos, não travado em 2) e índice normalizado
(`g-1=100`) foram diagnosticados usando **exclusivamente anos
pré-tratamento**; nenhuma observação pós-tratamento foi usada para
escolher o desenho. A diferença de nível entre tratados (muito mais altos)
e o pool de controles no baseline **não foi tratada como reprovação
automática de DiD** — é um diagnóstico esperado, dado que a seleção dos
municípios Fase II pelo MEC não é aleatória (DAG do `CONTRATO_CAUSAL.md`).
O índice `g-1=100` foi usado somente para visualização de trajetória
relativa; nenhum outcome transformado foi persistido em nenhum artefato.
Spillover e arranjos populacionais permanecem diagnósticos já produzidos em
etapas anteriores, não reabertos nem usados como critério de exclusão
automática.

### Gráficos adicionados

`06_distribuicao_baseline_tratados_controles`,
`07_pre_tendencias_niveis`, `08_pre_tendencias_indice`,
`09_mudanca_pre_g2_g1` — Plotly, identidade IPT, salvos via
`src/visualizacao_ipt.py` (fallback HTML local, Kaleido segue indisponível
e não foi instalado).

### Correção técnica no fallback visual

`Plotly` instalado no ambiente é `7.0.0`, que passou a levantar
`RuntimeError` (em vez de `ImportError`) quando o Kaleido está ausente. O
fallback de `salvar_figura_ipt` (já documentado desde o D12) não capturava
esse tipo e travava a execução do notebook — corrigido ampliando o
`except` para incluir `RuntimeError`, sem alterar nenhuma outra lógica
visual nem a paleta/identidade IPT. Teste focal adicionado em
`tests/test_visualizacao_ipt.py` simulando `write_image` levantando
`RuntimeError` e confirmando o fallback para HTML sem exceção (3/3 testes
passando).

### Testes

- `tests/test_diagnostica_identificacao_causal.py`: **10/10 passando**,
  offline — cobrem cálculo de baseline, uso exclusivo de períodos pré,
  normalização `g-1=100`, tratamento da coorte 2009, ausência de
  contaminação por dados pós-tratamento e preservação do pool canônico
  (nenhum controle filtrado por outcome);
- `tests/test_visualizacao_ipt.py`: **3/3 passando**, incluindo o novo
  teste focal do fallback `RuntimeError`;
- `tests/test_audita_populacao_causal_cempre.py` (D12): **17/17 passando**,
  sem regressão — os resultados do D12 permanecem inalterados.

### Notebook

`notebooks/01_analise_expansao_rede_federal_economia_municipal.ipynb`
cresceu de 28 para **63 células**, executado integralmente offline e salvo
com outputs, **zero traceback**, **9 figuras Plotly** renderizadas, com
seções didáticas sobre Diferenças-em-Diferenças, tratamento escalonado,
hipótese de tendências paralelas, baseline, pré-tendências, limitação da
coorte 2009 e classificação do gate de identificação. Nenhum ATT, nenhum
matching, nenhum TWFE causal e nenhum Callaway–Sant'Anna foi executado.

### Propostas candidatas (registradas, não congeladas)

- `GRUPO_COMPARACAO_CANDIDATO` = pool estrutural dos 4.964 controles;
- `JANELA_PRINCIPAL_CANDIDATA` = 2 pré + 3 pós;
- `JANELA_SENSIBILIDADE_CANDIDATA` = 3 pré + 3 pós, restrita às coortes com
  suporte (2010–2013);
- `OUTCOME_PRINCIPAL_CANDIDATO` = CEMPRE 708 em nível, sem transformação;
- `ESTIMADOR_CANDIDATO_FUTURO` = DiD para tratamento escalonado /
  Callaway–Sant'Anna.

Essas decisões ainda precisam ser congeladas no D14 — não são um contrato
final.

### Próximo passo

**D14 — Congelamento da Especificação Causal**, que deverá decidir
explicitamente: (1) definição operacional do tratamento; (2) regra de
timing; (3) tratamento da antecipação/transição; (4) grupo de comparação
final (never-treated e eventual papel de not-yet-treated); (5) janela
principal; (6) janela de sensibilidade; (7) tratamento da coorte 2009;
(8) outcome principal e eventuais transformações de sensibilidade; (9)
tratamento do sigilo do município `5003900`/2012; (10) política de
spillover para robustez; (11) configuração futura do estimador. Nenhum
efeito causal foi estimado no fechamento do D13.

Não reabrir D13 sem anomalia concreta.

---

## 23. D14 — Congelamento da Especificação Causal

Status técnico:

`ESPECIFICACAO_CAUSAL_CONGELADA = SIM`

`PRONTO_PARA_CONSTRUIR_AMOSTRA_CAUSAL = SIM`

`DESENHO_CAUSAL_APROVADO = NÃO`

`EVIDENCIA_INSTITUCIONAL_ANTECIPACAO = INSUFICIENTE_PARA_REGRA_GERAL`

`SUPOSICAO_ANTECIPACAO_PRINCIPAL = 0_PERIODOS`

`GRUPO_COMPARACAO_PRINCIPAL = NEVER_TREATED`

`NOT_YET_TREATED = NÃO UTILIZADO`

Commit substantivo:

`9f01bd4e95559a10f975ffc3cfcd6c042ef44d48` — `feat: congela especificacao
causal`

Push: **CONCLUIDO**.

### O que o D14 fez

Transformou as propostas diagnósticas do D13 em uma especificação causal
explícita e reproduzível, sem estimar nenhum efeito, sem executar
Callaway–Sant'Anna, sem matching e sem rede. Preservou integralmente os
resultados de D12/D13: 129 candidatos principais (coortes 2009=21,
2010=27, 2011=66, 2012=13, 2013=2), pool estrutural de 4.964 controles,
2 pré + 3 pós = 129/129, 3 pré + 3 pós = 108/129, coorte 2009 incluída na
janela principal e excluída por construção da sensibilidade.

### Ajuste conceitual 1 — antecipação: evidência vs. suposição

O fechamento inicial do D14 registrava apenas
`JANELA_ANTECIPACAO_DEFINIDA = NÃO`, o que misturava duas ideias
distintas. Corrigido para separar explicitamente:

- **Evidência institucional** (`EVIDENCIA_INSTITUCIONAL_ANTECIPACAO =
  INSUFICIENTE_PARA_REGRA_GERAL`) — os documentos aprovados não permitem
  afirmar empiricamente ausência de antecipação para os 128/129 candidatos
  sob `origem_coorte='proxy_censo'`. Isso é uma **limitação**, registrada
  como tal (status `LIMITACAO` na tabela do contrato), não como pendência
  que bloqueia o congelamento.
- **Suposição da especificação** (`SUPOSICAO_ANTECIPACAO_PRINCIPAL =
  0_PERIODOS`) — a especificação principal adota zero períodos de
  antecipação como **hipótese identificadora**, não como fato observado;
  é o parâmetro padrão de Callaway–Sant'Anna e a opção mais conservadora
  sem inventar uma janela sem evidência.

Cabo Frio/RJ (código `3300704`) permanece tratado pela regra institucional
específica já existente no cadastro causal (D11), distinta desta suposição
geral: 2009 = `ano_transicao`, excluído da estimação; 2010 =
`primeiro_ano_completo` = coorte `g` = `k=0`.

### Ajuste conceitual 2 — not-yet-treated: escolha deliberada, não proibição técnica

A justificativa inicial (`pode_ser_controle=False` "proibiria"
not-yet-treated) foi corrigida. `pode_ser_controle=False` significa apenas
que os 147 municípios Fase II não pertencem ao pool estrutural de
controles permanentes — conceito distinto de usar unidades ainda não
tratadas como grupo de comparação econométrico (not-yet-treated), que
Callaway–Sant'Anna suporta tecnicamente.

A decisão de usar exclusivamente never-treated é **metodológica e
deliberada**, fundamentada em cinco razões (detalhadas no notebook, seção
41): (1) suficiência operacional dos 4.963 never-treated; (2) simplicidade
de interpretação do contrafactual; (3) incerteza de timing dos futuros
tratados (mesma limitação de proxy do Censo); (4) antecipação geral não
empiricamente conhecida (ajuste conceitual 1); (5) risco de contaminação
se o comportamento pré-tratamento mudar antes do ano registrado.
Adicionalmente, not-yet-treated é pequeno e decrescente entre os 129 (81
em 2010, 15 em 2011, 2 em 2012, 0 a partir de 2013), agregando pouca
informação frente aos 4.963 never-treated já disponíveis.

### Contrato final da especificação (22 itens, notebook seção 60)

Todos os itens essenciais (tratamento, coorte g, ano zero, suposição de
antecipação principal, controle principal, período total, outcome,
sigilo, covariáveis, estimando) estão `CONGELADO`. Sensibilidades
registradas (não bloqueiam): janela 3 pré + 3 pós, transformação log1p,
covariáveis condicionais (dependentes de fonte de dados ainda não
aprovada), filtros espaciais de spillover (limiares já documentados:
25/50/100 km, arranjo populacional). Limitação registrada (não bloqueia):
evidência institucional de antecipação insuficiente para regra geral.
Único item `PENDENTE` não essencial: outcome per capita, indisponível por
ausência de fonte populacional municipal aprovada no projeto — nenhuma
nova coleta foi aberta.

### Decisões congeladas — resumo

- Tratamento: presença operacional de campus Fase II (cadastro causal
  D11, não redefinido);
- Coorte g = `ano_coorte_candidata`;
- Controle principal: never-treated, pool estrutural 4.964 menos o
  município com sigilo (`5003900`, 708/2012) = **4.963**;
- Outcome principal: CEMPRE 708, em nível; log1p como sensibilidade (há
  zeros reais no pool de controles);
- Período total da estimação: 2007–2019 inteiro (distinto da janela de
  event-study);
- Janela principal de event-study: `k = -2,-1,0,+1,+2`, com `k=-1` como
  referência;
- Janela de sensibilidade: `k = -3,...,+2`, restrita às coortes
  2010–2013 (108/129);
- Sigilo do município `5003900` em 2012: excluído do painel causal
  principal inteiro (nunca imputado, nunca zerado);
- Painel balanceado exigido na especificação principal;
- Covariáveis: nenhuma no principal (gate D — sensibilidade futura,
  dependente de fonte de dados);
- Spillover: nenhum filtro no principal (gate A — thresholds já
  documentados como sensibilidade futura).

### Módulo e testes

`src/define_especificacao_causal.py` — contrato de especificação
(`EspecificacaoCausal`, `ESPECIFICACAO_CAUSAL_V1`) e funções puras
(`unidades_tratadas_principal`, `unidades_controle_principal`,
`anos_excluidos_por_municipio`, `event_time`, `janela_principal_k`,
`janela_sensibilidade_k`, `resumo_especificacao`). Nenhuma amostra causal
é persistida por este módulo — apenas definição lógica das unidades.

`tests/test_define_especificacao_causal.py`: **14/14 passando**, offline
— cobrem controle principal never-treated, not-yet-treated fora do
principal, separação entre evidência institucional e suposição de
antecipação (dois campos distintos, nunca confundidos), regra específica
de Cabo Frio, exclusão do sigilo sem imputação/zeragem, 129 tratados e
4.963 controles reproduzidos.

Regressão focal (D12+D13+D14+visual): **44/44 passando**, offline.

### Notebook

`notebooks/01_analise_expansao_rede_federal_economia_municipal.ipynb`
cresceu de 63 para **107 células**, executado integralmente offline e
salvo com outputs, **zero traceback**, 32/32 células de código com
output, **10 figuras Plotly** (9 do D13 + 1 nova de auditoria de
transformação do outcome). Nenhum ATT, nenhum matching, nenhum TWFE
causal e nenhum Callaway–Sant'Anna foi executado.

### Próximo passo

**D15 — Construção da Amostra Causal Congelada**, que deverá materializar,
sem estimar nenhum efeito: os 129 tratados conforme o contrato; os 4.963
controles never-treated; painel balanceado; período 2007–2019; exclusão
do município `5003900`; aplicação da exclusão institucional de 2009 para
Cabo Frio; metadados necessários para a futura estimação; validações da
população resultante.

Não reabrir D12/D13/D14 sem anomalia concreta.

---

## 24. D15 — Construção da Amostra Causal Congelada

Status técnico:

`AMOSTRA_CONSTRUIDA = SIM`

`PRONTA_PARA_ESTIMACAO = SIM`

`DESENHO_CAUSAL_APROVADO = NAO`

Artefatos:

- `notebooks/02_construcao_amostra_causal.ipynb`;
- `data/processed/amostra_causal_cempre_2007_2019.parquet`;
- `outputs/diagnostics/exclusoes_amostra_causal.csv`;
- `src/constroi_amostra_causal.py`;
- `tests/test_constroi_amostra_causal.py`.

Dimensões reproduzidas: 129 tratados, 4.963 controles never-treated,
5.092 municípios, 66.196 município-anos no painel-base e 66.195
observações elegíveis. O código `5003900` foi excluído integralmente
por sigilo do outcome em 2012. Cabo Frio/RJ permanece no painel-base e
2009 é a única observação mascarada para estimação.

A auditoria pós-D15 confirmou chave única, painel-base balanceado,
ausência de sobreposição tratado/controle, coortes 2009=21, 2010=27,
2011=66, 2012=13 e 2013=2, e outcome final sem missing ou sigilo.

---

## 25. D16 — Análise Descritiva da Amostra Causal

Status técnico:

`D16_AMOSTRA_DESCRITA = SIM`

`D16_INCONSISTENCIA_BLOQUEADORA = NAO`

`D16_PRONTA_PARA_DIAGNOSTICOS_PRE_ESTIMACAO = SIM`

`DESENHO_CAUSAL_APROVADO = NAO`

O notebook `notebooks/03_analise_descritiva_amostra_causal.ipynb`
documenta composição, coortes, distribuição territorial, cobertura
temporal e do outcome, escala, assimetria, evolução anual e cobertura
descritiva de event-time. Nenhum ATT, event-study causal, matching, TWFE
causal ou Callaway–Sant'Anna foi executado.

O outcome final possui 66.193 observações com status `observado` e 3
`zero_real`, sem NaNs. A população com suporte de calendário é 129 na
janela principal e 108 na sensibilidade. Depois da máscara Cabo
Frio/2009, 128 e 107, respectivamente, possuem todos os valores de `k`
elegíveis. Essa distinção é observacional e não altera as populações
congeladas.

Artefatos diagnósticos:

- `outputs/diagnostics/resumo_amostra_causal.csv`;
- `outputs/diagnostics/distribuicao_coortes.csv`;
- `outputs/diagnostics/cobertura_event_time.csv`;
- figuras Plotly em HTML interativo sob `outputs/figures/interactive/`.

PNG permanece indisponível porque `kaleido>=1` não está instalado no
ambiente. Nenhuma dependência foi instalada.

---

## 26. D17 — Diagnósticos pré-estimação

Status técnico:

`D17_DIAGNOSTICOS_PRE_ESTIMACAO_CONCLUIDOS = SIM`

`D17_SUPORTE_EMPIRICO_DOCUMENTADO = SIM`

`D17_AMOSTRA_PRONTA_TECNICAMENTE_PARA_IMPLEMENTACAO_DO_ESTIMADOR = NAO`

`D17_ALERTA_IDENTIFICACAO_IMPORTANTE = SIM`

`DESENHO_CAUSAL_APROVADO = NAO`

O notebook `notebooks/04_diagnosticos_pre_estimacao.ipynb` executa uma
auditoria exclusivamente pré-estimação da amostra congelada D15. Nenhum
ATT, Callaway–Sant'Anna, event-study causal, TWFE causal, matching,
trimming, peso causal ou seleção automática de unidades foi executado.

### Inputs e preservação

Foram reproduzidos: 129 tratados; 4.963 controles never-treated; 5.092
municípios; 66.196 município-anos; 66.195 observações elegíveis; coortes
2009=21, 2010=27, 2011=66, 2012=13 e 2013=2; painel-base balanceado;
zero sobreposição tratado/controle; zero missing ou sigilo no outcome;
`5003900` ausente; Cabo Frio/2009 como única máscara observacional.

Hashes SHA-256 calculados no início e no fim do notebook confirmaram que
o parquet D15, os quatro CSVs D15/D16 e os notebooks 02/03 permaneceram
inalterados durante a D17.

### Covariáveis e comparabilidade

Os dados processados atuais não contêm população municipal, urbanização,
PIB/renda, escolaridade ou infraestrutura. Não houve download nem criação
de proxy artificial. As medidas CEMPRE variantes no tempo foram usadas
somente no baseline comum de 2007, anterior a todas as coortes; em anos
contemporâneos/pós-tratamento permanecem outcomes ou possíveis mediadores.

No baseline de 2007, tratados já apresentam escala econômica muito maior.
Os SMDs foram: unidades locais = 0,936; pessoal ocupado total = 0,870;
pessoal ocupado assalariado = 0,869; salário médio nominal em reais =
0,436. Esses valores são diagnósticos, não regra de exclusão.

### Pré-trajetórias e overlap

Trajetórias prévias foram comparadas por coorte contra never-treated usando
somente `k<0`, em nível e `log1p` (esta última apenas como diagnóstico de
escala). Slopes em nível são heterogêneas; 2011 e 2012 apresentam diferenças
particularmente relevantes frente aos controles. Os intervalos e slopes são
rotulados como diagnósticos de poder limitado; ausência de rejeição não é
tratada como prova de tendências paralelas, em linha com Roth (2022).

Uma regressão logística L2 simples, com covariáveis CEMPRE de 2007 e
macrorregião, foi usada apenas para diagnosticar overlap. O intervalo
empírico comum do score foi aproximadamente [0,000834; 0,848672]: cinco
tratados e 1.361 controles ficaram nas caudas fora desse intervalo. Nenhuma
unidade foi removida e nenhum matching/peso foi derivado —
`PROPENSITY_SCORE_DIAGNOSTICO != MATCHING`.

### Geografia, spillover, coortes pequenas e influência

Entre os 4.963 controles D15, 374/1.475/3.640 ficam a até 25/50/100 km da
sede de um município Fase II. Cento e quarenta e cinco compartilham um
Arranjo Populacional IBGE 2010 com Fase II. As classificações são
temporárias e diagnósticas; `papel_causal` não foi alterado. A limitação
temporal dos arranjos de 2010 foi preservada.

O parquet de arranjos disponível cobre municípios candidatos a controle,
não os 129 tratados. Por isso, a quantidade de tratados no mesmo arranjo e
a decomposição dessa exposição por coorte não são identificáveis nesse
artefato; nenhuma linha ou coorte foi imputada para preencher essa lacuna.

As coortes 2012 (13 tratados) e 2013 (2) foram mantidas, com alerta de
precisão. Cabo Frio explica integralmente a passagem 129→128 na janela
principal e 108→107 na sensibilidade. No baseline, os dez maiores tratados
concentram aproximadamente 34,35% do outcome do grupo; nenhum outlier foi
excluído.

### Artefatos D17

- `notebooks/04_diagnosticos_pre_estimacao.ipynb`;
- `src/diagnostica_pre_estimacao.py`;
- `tests/test_diagnostica_pre_estimacao.py`;
- `outputs/diagnostics/covariaveis_pre_tratamento.csv`;
- `outputs/diagnostics/balanco_descritivo_pre_tratamento.csv`;
- `outputs/diagnostics/diagnostico_overlap.csv`;
- `outputs/diagnostics/diagnostico_pre_tendencias.csv`;
- `outputs/diagnostics/diagnostico_spillover_controles.csv`;
- `outputs/diagnostics/riscos_identificacao_D17.csv`;
- nove figuras Plotly D17 em HTML interativo sob
  `outputs/figures/interactive/`.

O notebook D17 foi executado integralmente offline: 44 células, 21 células
de código com output e zero traceback. O notebook acadêmico principal foi
atualizado apenas com uma síntese curta e também executado integralmente,
sem traceback. PNG continuou indisponível por ausência de Kaleido; nenhuma
dependência foi instalada.

Validação automatizada executada offline:

- testes sintéticos específicos da D17: 12/12 aprovados;
- suíte focal relevante D14–D17: 115/115 aprovados;
- suíte completa do projeto: 711/711 aprovados.

O gate técnico permanece conservador: os diagnósticos e o suporte estão
documentados, mas diferenças de escala, caudas de overlap, pré-trajetórias,
covariáveis municipais ausentes, risco de spillover/antecipação e coortes
pequenas impedem declarar a amostra pronta para implementar o estimador.
Isso não equivale a rejeição causal definitiva e não modifica decisões
congeladas.

---

## 27. D18 — Reavaliação do gate pré-estimação

Status técnico:

`D18_REAVALIACAO_PRE_ESTIMACAO_CONCLUIDA = SIM`

`D18_OVERLAP_ATT_DOCUMENTADO = SIM`

`D18_PRE_TENDENCIAS_ESCALA_AUDITADAS = SIM`

`D18_INFLUENCIA_PRE_TRATAMENTO_AUDITADA = SIM`

`D18_PLANO_ROBUSTEZ_PRE_ESPECIFICADO = SIM`

`D18_PRONTO_TECNICAMENTE_PARA_IMPLEMENTAR_ESTIMADOR = SIM`

`D18_IDENTIFICACAO_SUFICIENTE_PARA_INTERPRETACAO_CAUSAL = COM_RESSALVAS`

`DESENHO_CAUSAL_APROVADO = NAO`

O notebook `notebooks/05_reavaliacao_gate_pre_estimacao.ipynb` reavaliou
exclusivamente com informação pré-tratamento, características estruturais e
metadados congelados os alertas da D17. Nenhum ATT, Callaway–Sant'Anna real,
event-study causal, TWFE causal, matching, trimming, peso ou seleção por
resultado pós-tratamento foi executado.

### Refinamento rastreável da D17

A D17 encontrou diferenças grandes de nível, cinco tratados e 1.361 controles
fora da interseção completa dos intervalos do score, slopes em nível
heterogêneas, proximidade espacial, concentração do outcome e coortes pequenas.
A D18 não reescreve esses fatos; refinou sua interpretação:

- diferenças de nível/porte não equivalem a violação automática de tendências
  paralelas;
- os cinco tratados estão todos acima do máximo dos controles, enquanto os
  1.361 controles estão todos abaixo do mínimo dos tratados — apenas o primeiro
  caso é falta de suporte diretamente relevante para ATT;
- slopes em nível são fortemente sensíveis à escala do outcome;
- precisão limitada, especialmente em 2013, não é falha de identificação por
  si só;
- proximidade espacial documenta exposição potencial, não contaminação
  comprovada;
- ausência de covariáveis externas não impede tecnicamente o DiD incondicional
  congelado no D14, embora limite especificações condicionais e mantenha
  confundimento como ressalva substantiva.

### Overlap orientado ao ATT

O score diagnóstico D17 foi preservado sem novo ajuste. Os limites observados
foram:

- tratados: `[0,0008337554; 0,9623589047]`;
- controles: `[0,0000126253; 0,8486715311]`;
- tratados abaixo do mínimo dos controles: 0;
- tratados acima do máximo dos controles: 5;
- controles abaixo do mínimo dos tratados: 1.361;
- controles acima do máximo dos tratados: 0;
- tratados dentro da faixa dos controles: 124;
- controles dentro da faixa dos tratados: 3.602.

Os cinco tratados na cauda superior são Feira de Santana/BA (2012),
Caruaru/PE (2011), Anápolis/GO (2011), Caxias do Sul/RS (2011) e
Santarém/PA (2010). O nearest-support foi calculado no espaço padronizado
das quatro covariáveis CEMPRE de 2007 e macrorregião, apenas como descrição;
nenhuma unidade foi removida e nenhuma distância foi convertida em matching.

### Escala, primeiras diferenças e influência

Diferenças de slopes em nível (tratados menos controles) por coorte foram
aproximadamente 303,2; 107,6; 878,2; 1.501,9 e 1.981,3 para 2009–2013. Em
`log1p`, apenas para diagnóstico de escala, as diferenças foram -0,0082;
-0,0271; 0,0174; 0,0003 e 0,0425. Em 2009–2010 o sinal muda e em 2012 a
diferença praticamente desaparece na escala logarítmica; isso mostra forte
componente mecânico de escala, sem provar tendências paralelas.

As primeiras diferenças pré em nível apresentaram SMDs aproximados de 0,237;
0,180; 0,590; 0,802 e 0,516 por coorte. A incerteza foi apresentada
descritivamente, com o erro-padrão calculado sobre médias por município para
evitar tratar linhas anuais como réplicas independentes e sem p-valor
decisório. O diagnóstico de influência omitiu do
cálculo pré, nunca da amostra, o maior tratado e os top 5/10: as divergências
foram atenuadas, mas persistiram em 2011–2012. O padrão combina influência de
grandes municípios com heterogeneidade difusa.

### Coorte 2013, spillover e antecipação

Os dois tratados de 2013 são Angra dos Reis/RJ e Registro/SP. Ambos estão
dentro da faixa de score dos controles e no Sudeste. Registro apresenta
trajetória pré crescente mais regular; Angra dos Reis apresenta volatilidade
maior. A classificação é `PRECISAO` como problema principal e `TRAJETORIA`
como risco adicional; `SUPORTE` não é o problema observado nessa coorte.

Nos cenários hipotéticos, sem mudar `papel_causal`, restariam:

- 4.589 controles após sinalizar até 25 km;
- 3.488 após até 50 km;
- 1.323 após até 100 km;
- 4.818 após compartilhamento de arranjo populacional.

Há, portanto, volume substancial de controles para sensibilidades espaciais
futuras, inclusive no cenário mais severo. A limitação temporal dos Arranjos
Populacionais de 2010 permanece.

Para antecipação, foi preservada a separação entre fato, hipótese e risco:
128/129 timings são `proxy_censo`; `anticipation=0` continua hipótese
congelada; e mudança comportamental anterior ao registro segue plausível. Os
padrões em `k=-2` e `k=-3` não são uniformes e não autorizam redefinir `g` ou
criar nova janela nesta etapa.

### Dois gates e plano futuro

O gate D17 misturava prontidão técnica com suficiência de identificação. A D18
separa os conceitos. A amostra D15 possui contrato, chave, outcome, coortes,
papéis, período e máscaras tecnicamente implementáveis; logo, a implementação
futura do estimador pode começar em etapa própria. A interpretação causal não
fica irrestritamente aprovada: suporte dos cinco tratados extremos,
heterogeneidade pré, influência de porte, timing proxy, spillover plausível e
ausência de covariáveis externas permanecem ressalvas.

O plano futuro de robustez foi pré-especificado, sem execução: principal em
nível; `log1p`; janela `k=-3...+2`; agregações por coorte; diagnóstico separado
de 2013; spillover 25/50/100 km; arranjo populacional; ajustes com covariáveis
baseline existentes, se metodologicamente definidos; e eventual restrição de
suporte apenas como sensibilidade formalizada. Nenhuma especificação foi
escolhida usando resultados pós-tratamento.

### Artefatos D18

- `notebooks/05_reavaliacao_gate_pre_estimacao.ipynb`;
- `src/reavalia_gate_pre_estimacao.py`;
- `tests/test_reavalia_gate_pre_estimacao.py`;
- `outputs/diagnostics/D18_overlap_att.csv`;
- `outputs/diagnostics/D18_pre_tendencias_escala.csv`;
- `outputs/diagnostics/D18_primeiras_diferencas.csv`;
- `outputs/diagnostics/D18_influencia_pre.csv`;
- `outputs/diagnostics/D18_spillover_cenarios.csv`;
- `outputs/diagnostics/D18_matriz_riscos.csv`;
- `outputs/diagnostics/D18_plano_robustez.csv`;
- sete figuras Plotly D18 em HTML interativo sob
  `outputs/figures/interactive/`.

O parquet D15 permaneceu byte-identical, com SHA-256
`7c24c01b569ed6d10f773d00599b5010e1607696f46d716827182a078e4d733b`.
Cabo Frio/2009 permaneceu como única máscara e nenhuma coorte foi excluída.

Validação executada offline:

- testes específicos D18: **11/11 aprovados**;
- suíte focal D14–D18 + identidade visual: **51/51 aprovados**;
- suíte completa do projeto: **722/722 aprovados**;
- notebook D18: 37 células, 14 células de código executadas, zero traceback;
- notebook acadêmico principal: 115 células, 36 células de código
  executadas, zero traceback;
- sete outputs Plotly preservados também como HTML interativo;
- `git diff --check` sem erro.

A inspeção visual automática em navegador não pôde abrir a URL local por
política do ambiente. A validação programática confirmou títulos/eixos das sete
figuras, presença dos HTMLs Plotly e ausência de erro nos notebooks. PNG não foi
gerado por ausência de Kaleido, já documentada; nenhuma dependência foi
instalada.

### Próximo passo

A D18 autoriza apenas iniciar, em tarefa posterior específica, a implementação
técnica do estimador candidato e do plano de robustez. Não aprova o desenho
causal, não autoriza estimar automaticamente nesta mesma unidade de trabalho e
não fecha as ressalvas de interpretação.

---

## 28. D19 — infraestrutura e validação do estimador DiD escalonado

### Estado do gate

**D19_BACKEND_CALLAWAY_SANTANNA_VALIDADO = BLOQUEADO_DEPENDENCIA**

**D19_DGP_SINTETICO_VALIDADO = SIM**

**D19_ATT_GT_SINTETICO_VALIDADO = NAO**

**D19_HETEROGENEIDADE_SINTETICA_VALIDADA = SIM**

**D19_EVENT_STUDY_SINTETICO_VALIDADO = NAO**

**D19_INFERENCIA_CONFIGURADA = NAO**

**D19_DRY_RUN_AMOSTRA_REAL_VALIDADO = SIM**

**D19_INFRAESTRUTURA_PRONTA_PARA_ESTIMACAO_REAL = NAO**

**D19_EFEITO_CAUSAL_REAL_ESTIMADO = NAO**

**DESENHO_CAUSAL_APROVADO = NAO**

O notebook notebooks/06_infraestrutura_estimador_did_escalonado.ipynb
construiu e validou a infraestrutura anterior à estimação real. Não havia
backend confiável de Callaway–Sant'Anna instalado: R/Rscript e o pacote did
estavam ausentes; o pacote Python differences também estava ausente. O
statsmodels 0.14.6 disponível não implementa ATT grupo-tempo e foi usado
somente para uma demonstração TWFE em painel sintético explicitamente marcado.
Nenhum pacote foi instalado e nenhuma aproximação caseira de
Callaway–Sant'Anna foi criada.

### Contrato e plano operacional

O contrato técnico separa o painel integral de estimação (2007–2019) da janela
principal de reporte (k=-2...+2). O mapeamento futuro para R did usa município
como idname, ano como tname, primeira coorte como gname, zero para
never-treated, outcome em nível, control_group=nevertreated, anticipation=0,
base_period=universal e fórmula principal incondicional. O plano D20 recomenda
att_gt, agregações dynamic, group e simple, cluster por município, multiplier
bootstrap e bandas simultâneas. A execução exige autorização de dependência e
nova validação sintética do backend.

### DGP e cenários sintéticos

O módulo src/simula_did_escalonado.py gera painéis determinísticos com efeitos
fixos de unidade e tempo, coortes escalonadas, never-treated, dinâmica,
heterogeneidade por coorte, antecipação opcional, violação controlada de
tendências paralelas, overlap fraco e coorte pequena. Foram executados cinco
cenários:

1. desenho limpo;
2. heterogeneidade forte;
3. violação de tendências paralelas;
4. overlap fraco;
5. coorte 2013 com n=2.

A verdade conhecida ATT(g,t) e suas agregações foram mantidas sob o rótulo
VERDADE_DGP_NAO_ESTIMATIVA. Elas comprovam o DGP, não o estimador moderno, que
permanece ausente. No cenário heterogêneo, a média global verdadeira foi
11,3564 e o TWFE sintético convencional foi 10,4065, ilustrando por que TWFE
não substitui o estimador grupo-tempo.

### Dry-run estrutural na D15

A base real foi apenas lida, validada e convertida ao contrato futuro. O
dry-run confirmou:

- 66.196 linhas, 5.092 municípios e chave município-ano única;
- 129 tratados e 4.963 never-treated;
- coortes 2009–2013 com contagens 21, 27, 66, 13 e 2;
- 66.195 linhas elegíveis;
- Cabo Frio/2009 como única máscara;
- código histórico 5003900 ausente;
- os cinco tratados extremos de suporte preservados;
- coorte 2013 preservada e marcada com alerta de precisão;
- estimacao_executada=False.

O parquet D15 permaneceu byte-identical, com SHA-256
7c24c01b569ed6d10f773d00599b5010e1607696f46d716827182a078e4d733b.

### Artefatos D19

- notebooks/06_infraestrutura_estimador_did_escalonado.ipynb;
- src/simula_did_escalonado.py;
- src/estima_did_escalonado.py;
- tests/test_infraestrutura_did_escalonado.py;
- outputs/diagnostics/D19_backends.csv;
- outputs/diagnostics/D19_contrato_estimador.csv;
- outputs/diagnostics/D19_mapeamento_backend.csv;
- outputs/diagnostics/D19_cenarios_sinteticos.csv;
- outputs/diagnostics/D19_att_gt_verdade.csv;
- outputs/diagnostics/D19_event_study_verdade.csv;
- outputs/diagnostics/D19_twfe_sintetico.csv;
- outputs/diagnostics/D19_dry_run_amostra_real.csv;
- outputs/diagnostics/D19_coortes_reporte.csv;
- outputs/diagnostics/D19_plano_operacional_D20.csv;
- seis figuras Plotly D19 em HTML interativo sob
  outputs/figures/interactive/.

O notebook acadêmico principal recebeu somente uma síntese curta dos gates e
dos artefatos D19.

### Validação executada offline

- testes específicos D19: **19/19 aprovados**;
- suíte focal D14–D19 + identidade visual: **70/70 aprovados**;
- suíte completa do projeto: **741/741 aprovados**;
- notebook D19: 50 células, 17 células de código executadas, zero traceback;
- notebook acadêmico principal: 117 células, 37 células de código
  executadas, zero traceback;
- seis outputs Plotly D19 preservados como HTML interativo;
- hash da D15 confirmado antes e depois do dry-run;
- git diff --check sem erro.

### Limitações e próximo passo

Não foram validados ATT(g,t) estimados, agregações estimadas, event-study
estimado, erros-padrão, bootstrap ou bandas simultâneas. A D20 só poderá
começar após autorização explícita para disponibilizar o backend recomendado e
repetir os testes sintéticos antes de qualquer uso da D15. A D19 não aprova o
desenho causal nem autoriza estimação real automática.

---

## 29. D20A — validação do backend Python `differences==0.3.0`

### Estado do gate

**D20A_PYTHON_DIFERENCES_0_3_0_DISPONIVEL = SIM**

**D20A_BACKEND_CALLAWAY_SANTANNA_PYTHON_VALIDADO = SIM**

**D20A_CONVENCAO_COORTE_VALIDADA = SIM**

**D20A_BASE_PERIOD_VALIDADO = SIM**

**D20A_NEVER_TREATED_VALIDADO = SIM**

**D20A_ATT_GT_SINTETICO_VALIDADO = SIM**

**D20A_MONTE_CARLO_VALIDADO = SIM**

**D20A_EVENT_STUDY_SINTETICO_VALIDADO = SIM**

**D20A_INFERENCIA_VALIDADA = PARCIAL**

**D20A_PAINEL_DESBALANCEADO_VALIDADO = SIM**

**D20A_CABO_FRIO_IMPLEMENTACAO_DEFINIDA = BLOQUEADO_DECISAO**

**D20A_DRY_RUN_REAL_BACKEND_VALIDADO = SIM**

**D20A_PRONTO_PARA_PRIMEIRA_ESTIMACAO_REAL = NAO**

**D20A_EFEITO_REAL_ESTIMADO = NAO**

**DESENHO_CAUSAL_APROVADO = NAO**

### Ambiente e instalação

Não foi instalado R, Rscript, `did` ou `DRDID`. O dry-run do pip confirmou
que `differences==0.3.0` seria o único pacote novo. A instalação ocorreu
somente na `.venv` do projeto; Python 3.11.9, numpy 2.4.6, pandas 3.0.5,
scikit-learn 1.9.0, statsmodels 0.15.0 e scipy 1.17.1 permaneceram
inalterados. `pip check` estava limpo antes e permaneceu limpo depois.

### Auditoria estrutural da API

O backend exige DataFrame com MultiIndex entidade-tempo e representa
*never-treated* com coorte nula, não zero. Coorte é o primeiro período
tratado e o tempo relativo é `t-g`; para `g=2011`, 2010 corresponde a `k=-1`,
2011 a `k=0` e 2012 a `k=+1`.

Com `anticipation=0`, `base_period='universal'` usa `g-1` como base comum e
normaliza `k=-1` em zero. `base_period='varying'` usa comparações sequenciais
nos leads e não produz a mesma referência normalizada. O grupo de controle
principal validado foi exclusivamente `never_treated`. `est_method='dr'`
resolve para o estimador duplamente robusto em painel com propensity score
logístico MLE; não equivale a `dr-ipt`.

No modo painel, `cluster_var=None` já agrupa por entidade. Para painel
desbalanceado foi necessário fixar `as_repeated_cross_section=False`; o
backend então forma pares completos por célula ATT(g,t).

### Validação sintética e Monte Carlo

Foram reutilizados, sem criar DGP paralelo, os cinco cenários da D19: LIMPO,
HETEROGENEIDADE_FORTE, VIOLACAO_PARALLEL_TRENDS, OVERLAP_FRACO e
COORTE_2013_N2. ATT(g,t), agregações `simple`, `cohort` e `event` foram
comparadas com a verdade conhecida.

As sementes foram congeladas antes dos resultados: 23001–23030 para ponto e
24001–24010 para cobertura, com n=240 e 99 repetições de bootstrap. No cenário
limpo, sobre 750 células, o bias médio foi 0,0473, MAE 0,2207, RMSE 0,2762 e
correlação 0,9949, sem falhas de convergência. A cobertura simultânea observada
foi 1,00 sobre 250 células em dez sementes; o volume limitado de sementes e
bootstrap recomenda interpretar esse valor apenas como smoke test empírico,
não como calibração definitiva.

A violação deliberada de tendências paralelas gerou bias médio 3,7132 e
cobertura analítica pontual zero, como esperado. Overlap fraco e coorte 2013
com n=2 permaneceram executáveis, mas com alertas de suporte e precisão.

### Inferência e Cabo Frio

A versão 0.3.0 inclui multiplier bootstrap e bandas simultâneas. Porém, com
`base_period='universal'`, a presença da célula determinística `k=-1` de
variância zero causa divisão por zero e bandas simultâneas `NaN`. A D20A usa a
API pública `filter_gt` para excluir `k=-1` apenas do bootstrap e reinsere a
referência zero somente na apresentação. Por depender desse workaround, o
gate de inferência é PARCIAL.

No teste desbalanceado equivalente a Cabo Frio, remover apenas 2009 preserva
2010 e todos os demais anos no objeto e mantém a coorte. Entretanto, sob base
universal, o município deixa de participar de toda célula pós-tratamento da
coorte 2010 que requer o par com 2009. O backend ainda pondera a agregação pela
contagem integral da coorte, embora a célula seja estimada nos pares completos.
Essa diferença é material e exige decisão metodológica humana; a D20A não
escolheu entre manter a regra atual, excluir a unidade da população principal
ou alterar a estratégia.

### Dry-run real e artefatos

O dry-run leu a D15, aplicou somente a elegibilidade já congelada, converteu
controles para coorte nula e instanciou `ATTgt`. Um guard explícito impede
`.fit()` em dados não sintéticos. O parquet D15 permaneceu byte-identical, com
SHA-256 `7c24c01b569ed6d10f773d00599b5010e1607696f46d716827182a078e4d733b`.

Principais artefatos:

- `notebooks/07_validacao_backend_differences.ipynb`;
- `src/valida_backend_differences.py`;
- `tests/test_backend_differences_d20a.py`;
- `outputs/diagnostics/D20A_api_differences.csv`;
- `outputs/diagnostics/D20A_base_period.csv`;
- `outputs/diagnostics/D20A_cenarios_resumo.csv`;
- `outputs/diagnostics/D20A_monte_carlo_resumo.csv`;
- `outputs/diagnostics/D20A_monte_carlo_configuracao.json`;
- `outputs/diagnostics/D20A_cabo_frio_sintetico.csv`;
- `outputs/diagnostics/D20A_dry_run_real.csv`;
- `outputs/diagnostics/D20A_gates.csv`;
- `outputs/diagnostics/D20A_ambiente.csv`;
- `outputs/diagnostics/D20A_dependencias_novas.csv`;
- dois gráficos Plotly D20A em HTML interativo sob
  `outputs/figures/interactive/`.

O notebook acadêmico principal recebeu a síntese, os gates, o resumo do Monte
Carlo e o gráfico decisório de ATT dinâmico versus verdade conhecida.

### Validação executada

- testes específicos D20A: **13/13 aprovados**;
- suíte completa do projeto: **754/754 aprovados**;
- notebook D20A: 20 células, 10 células de código executadas, zero traceback;
- notebook acadêmico principal: 121 células, 39 células de código executadas,
  zero traceback;
- inspeção visual em navegador local dos dois HTMLs Plotly concluída;
- nenhuma alteração no stack científico além de `differences==0.3.0`;
- nenhum fit, ATT, event-study ou p-valor foi calculado na amostra real;
- nenhum commit, push ou staging foi executado.

### Limitações e próximo gate

A D20A valida o backend para desenvolvimento técnico, não para execução real.
Antes da primeira estimação na D15 são necessárias duas decisões humanas:
tratamento metodológico de Cabo Frio e aceitação ou substituição do workaround
de inferência da versão 0.3.0. Nenhuma dessas decisões deve ser tomada com base
em resultados reais, que continuam inexistentes.

---

## 30. D20B — fechamento pré-estimação: Cabo Frio + inferência

### Estado do gate

**D20B_CABO_FRIO_DECISAO_FECHADA = SIM**

**D20B_POPULACAO_ESTIMAVEL_128_VALIDADA = SIM**

**D20B_VIEW_BALANCEADA_VALIDADA = SIM**

**D20B_WORKAROUND_K_MENOS_1_VALIDADO = SIM**

**D20B_INFERENCIA_CONFIGURADA = SIM**

**D20B_BOOTSTRAP_FINAL_PRE_ESPECIFICADO = SIM**

**D20B_PRONTO_PARA_ESTIMACAO_REAL = SIM**

**D20B_EFEITO_REAL_ESTIMADO = NAO**

**DESENHO_CAUSAL_APROVADO = NAO**

### Decisão metodológica sobre Cabo Frio

A D20B preserva duas populações distintas:

```text
POPULACAO_D15_TRATADOS = 129
POPULACAO_PRINCIPAL_ESTIMAVEL = 128
```

Cabo Frio/RJ (`3300704`) continua documentado na D15 com `g=2010` e 13
linhas. Seu `k=-1` principal é 2009, ano de transição institucional já
inelegível. Assim, o município não possui base válida para
`base_period='universal'`. Não houve imputação, uso de 2009, mudança de `g`,
repeated cross-section ou exclusão implícita por célula.

A view/cópia principal exclui Cabo Frio integralmente apenas da estimação. Ela
contém 128 tratados, 4.963 controles, 5.091 municípios e 66.183 linhas em
painel balanceado 2007–2019. As coortes são 2009=21, 2010=26, 2011=66,
2012=13 e 2013=2; `5003900` permanece ausente.

Como a decisão altera a população tratada do estimando principal, ela foi
registrada no addendum
`docs/methodology/ADDENDUM_D20B_CABO_FRIO_INFERENCIA.md`. O D14 original não
foi reescrito. A motivação é exclusivamente a incompatibilidade pré-resultado
`Cabo Frio/2009 × g-1`.

### Workaround e inferência

Em dados sintéticos D19, foram comparados: A) `base_period='universal'` sem
bootstrap/filtro; e B) remoção de `k=-1` antes do multiplier bootstrap. A
diferença máxima foi zero para ATT(g,t) pós-tratamento, agregações `cohort` e
`simple` e event-study em todos os `k != -1`. `k=-1` não participa da banda e
é recolocado como zero, sem erro-padrão ou limites, somente na apresentação.

A configuração final foi congelada antes de efeitos reais:

- `boot_iterations=1999`;
- `random_state=20260924`;
- `n_jobs=1`;
- `alpha=0.05`;
- bandas simultâneas de 95%;
- cluster automático por entidade.

Embora o ambiente tenha 16 CPUs, `differences==0.3.0` falhou com `n_jobs=4`
no multiplier bootstrap por incompatibilidade Joblib/tqdm. `n_jobs=1` foi
congelado como configuração estável. Os 1.999 draws não foram executados na
base real.

### Artefatos e validação

- `docs/methodology/ADDENDUM_D20B_CABO_FRIO_INFERENCIA.md`;
- `data/processed/amostra_principal_estimavel_d20b_2007_2019.parquet`;
- `outputs/diagnostics/D20B_view_principal_estimavel.csv`;
- `outputs/diagnostics/D20B_workaround_k_menos_1.csv`;
- `outputs/diagnostics/D20B_invariancia_*.csv`;
- `outputs/diagnostics/D20B_configuracao_inferencia.json`;
- `outputs/diagnostics/D20B_gates.csv`;
- seções D20B nos notebooks 07 e acadêmico principal.

Validação executada:

- testes específicos D20A/D20B: **19/19 aprovados**;
- suíte completa: **760/760 aprovados**;
- notebook 07: 28 células, 13 células de código executadas, zero traceback;
- notebook acadêmico principal: 125 células, 40 células de código executadas,
  zero traceback;
- D15 byte-identical, SHA-256
  `7c24c01b569ed6d10f773d00599b5010e1607696f46d716827182a078e4d733b`;
- nenhum fit, ATT, event-study ou p-valor real executado;
- nenhum commit, push ou staging executado.

`D20B_PRONTO_PARA_ESTIMACAO_REAL = SIM` fecha apenas os dois bloqueios
técnicos autorizados nesta unidade. Não inicia automaticamente a estimação e
não aprova o desenho causal.

---

## 31. D20C–D20E — primeira estimação real, robustezes e auditoria

### Escopo e estado do gate

A primeira estimação no outcome real foi executada na view D20B congelada,
sem redefinir tratamento, coortes, outcome, controles, antecipação, população,
modelo ou robustezes após observar os resultados. A D21 não foi executada.

**D20C_AMOSTRA_PRINCIPAL_VALIDADA = SIM**

**D20C_ATT_GT_REAL_ESTIMADO = SIM**

**D20C_AGREGACAO_SIMPLE_ESTIMADA = SIM**

**D20C_AGREGACAO_COORTE_ESTIMADA = SIM**

**D20C_EVENT_STUDY_REAL_ESTIMADO = SIM**

**D20C_BOOTSTRAP_1999_CONCLUIDO = SIM**

**D20C_BANDAS_SIMULTANEAS_VALIDAS = SIM**

**D20C_RESULTADO_PRINCIPAL_CONGELADO = SIM**

**D20D_LOG1P_EXECUTADO = SIM**

**D20D_JANELA_3PRE_EXECUTADA = SIM**

**D20D_SUPORTE_EXECUTADO = SIM**

**D20D_SPILLOVER_25_EXECUTADO = SIM**

**D20D_SPILLOVER_50_EXECUTADO = SIM**

**D20D_SPILLOVER_100_EXECUTADO = SIM**

**D20D_ARRANJO_EXECUTADO = SIM**

**D20D_ROBUSTEZES_PRE_ESPECIFICADAS_CONCLUIDAS = SIM**

**D20E_AUDITORIA_POS_ESTIMACAO_CONCLUIDA = SIM**

**D20E_PRE_TENDENCIAS_REAVALIADAS = SIM**

**D20E_OVERLAP_REAVALIADO = SIM**

**D20E_SPILLOVER_REAVALIADO = SIM**

**D20E_COORTE_2013_REAVALIADA = SIM**

**D20E_MATRIZ_EVIDENCIA_PRODUZIDA = SIM**

**D20E_INTERPRETACAO_CAUSAL_PENDENTE_REVISAO = SIM**

**DESENHO_CAUSAL_APROVADO = NAO**

### Especificação e população

O principal usa `differences==0.3.0`, ATT grupo-tempo DR sem covariáveis,
`base_period='universal'`, `control_group='never_treated'`, painel verdadeiro,
`anticipation=0`, referência `k=-1`, 1.999 draws, seed `20260924`,
`n_jobs=1`, `alpha=0.05` e bandas simultâneas.

A view permanece com 128 tratados, 4.963 controles, 5.091 municípios,
66.183 linhas e painel balanceado 2007–2019. As coortes são 2009=21,
2010=26, 2011=66, 2012=13 e 2013=2. Cabo Frio e `5003900` estão ausentes.

### Resultados congelados

O ATT simples principal é **2.050,9903**, erro-padrão **296,5924** e banda
simultânea de 95% **[1.481,3245; 2.620,6561]**. Foram produzidas 65 células
ATT(g,t), sendo 45 pós-tratamento; não houve falha nem warning de célula
pós-tratamento.

Por coorte: 2009 = 4.048,5987; 2010 = 1.694,9899; 2011 = 1.478,5356;
2012 = 2.345,8441; e 2013 = -2.200,0178. A coorte 2013 tem somente dois
tratados e banda ampla [-5.885,5416; 1.485,5061]; imprecisão não foi tratada
como efeito zero nem motivou exclusão.

No event-study, `k=0`, `k=1` e `k=2` são, respectivamente, 818,2776,
1.641,5888 e 2.188,8119. Há cinco leads disponíveis; as bandas de `k=-4`,
`k=-3` e `k=-2` não incluem zero. Esse padrão é um diagnóstico material de
identificação, não prova ou refutação mecânica de tendências paralelas.

As robustezes produziram ATT simples: log1p = 0,003965, com banda
[-0,025647; 0,033577] em escala não comparável a empregos; janela com três
pré-períodos = 1.576,2500; suporte = 1.818,3355; spillover 25 km =
2.069,8677; 50 km = 2.070,0738; 100 km = 2.096,0032; e arranjo populacional
= 2.080,0024. Todas as sensibilidades em nível mantiveram o sinal e tiveram
bandas descritivamente sobrepostas ao principal. Isso não prova ausência de
spillover nem corrige o estimando principal.

A contextualização descritiva usa somente a média pré-tratamento dos tratados
(17.190,5770): ATT simples / média pré = 0,119309, ou 11,93%. Essa razão não é
um novo estimando causal.

### Auditoria e reprodutibilidade

Uma repetição integral com a configuração congelada foi realizada em memória,
sem sobrescrever os outputs principais. A maior diferença absoluta foi
`1,8189894035458565e-12`, abaixo da tolerância numérica `1e-10`. A saída
pública do backend não expõe os pesos de agregação; nenhuma ponderação ad hoc
foi inferida.

Hashes de entrada preservados:

- D15: `7c24c01b569ed6d10f773d00599b5010e1607696f46d716827182a078e4d733b`;
- view D20B: `91b0a14b38740a56c1b6b3912e1ad3252632037b9044c992ec5331a932a10969`.

### Artefatos e validação

Os artefatos principais, manifests, tabelas de robustez, gates e matriz de
evidência estão em `outputs/causal/`; os três gráficos Plotly IPT estão em
`outputs/figures/interactive/`. O notebook didático é
`notebooks/08_estimacao_causal_principal_robustez.ipynb`; o notebook acadêmico
principal contém apenas a síntese D20C–D20E. O plano futuro, sem execução de
ML causal, está em `docs/methodology/PLANO_D21_CAUSAL_ML.md`.

Validação executada:

- testes focais D20C–D20E: **14/14 aprovados**;
- regressão D14–D20E: **103/103 aprovados**;
- suíte completa: **774/774 aprovados**;
- notebook 08: 34 células, 12/12 células de código executadas, dois outputs
  Plotly e zero erro/traceback;
- notebook acadêmico principal: 129 células, 42/42 células de código
  executadas, 12 outputs Plotly e zero erro/traceback;
- `pip check` sem dependências quebradas e `git diff --check` sem erro;
- nenhum pacote instalado, dado bruto alterado, commit, push ou staging.

### Limitações e próximo gate

O resultado continua condicionado a tendências paralelas não observáveis,
timing majoritariamente proxy, cinco tratados extremos, influência de porte,
spillovers plausíveis, pequena coorte 2013 e validade externa limitada ao
estimando e à população analisados. A significância estatística não remove
essas ressalvas. A interpretação causal aguarda revisão humana; nenhuma etapa
D21 está autorizada automaticamente.

---

## 32. Regra para agentes

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

---

## 33. PAUSA DO PROJETO

**STATUS_PROJETO = PAUSADO**

**DATA_PAUSA = 2026-09-25**

### Motivo

Projeto academicamente válido, porém pausado porque a disciplina Big Data &
Analytics seguirá com um novo projeto mais centrado em Machine Learning /
Causal Machine Learning.

**Pausado não significa descartado. Todo o trabalho realizado permanece
preservado** no histórico Git e nos documentos desta pasta.

### Última etapa efetivamente concluída

D20C–D20E (seção 31): primeira estimação causal real (ATT grupo-tempo via
Callaway–Sant'Anna, `differences==0.3.0`), robustezes pré-especificadas
(D20D) e auditoria pós-estimação com matriz de evidência (D20E).
`DESENHO_CAUSAL_APROVADO = NAO` — a interpretação causal continua pendente
de revisão humana; nenhuma etapa D21 foi executada.

### Análises já realizadas (resumo)

- D20A: validação do backend `differences==0.3.0` em dados sintéticos;
- D20B: decisão metodológica sobre Cabo Frio/RJ (excluído apenas da view de
  estimação, preservado na D15) e congelamento da configuração de
  inferência (bootstrap 1.999 draws, `random_state=20260924`, `n_jobs=1`);
- D20C: ATT simples principal = 2.050,9903 (erro-padrão 296,5924, banda
  simultânea 95% [1.481,3245; 2.620,6561]), agregações por coorte e
  event-study;
- D20D: sete robustezes (log1p, janela de 3 pré-períodos, suporte,
  spillover 25/50/100 km, arranjo populacional) — sinal preservado em
  todas;
- D20E: reavaliação de pré-tendências, overlap, spillover e coorte 2013;
  matriz de evidência produzida; interpretação causal explicitamente
  pendente.

### Estado dos dados

- artefatos científicos (`outputs/causal/*.csv`, `data/processed/*.parquet`)
  seguem a política vigente do projeto e permanecem fora do Git (regra
  `*.csv`/`data/processed/*` do `.gitignore`), reproduzíveis a partir dos
  scripts em `src/` e dos notebooks;
- manifestos e configurações em JSON (`outputs/causal/*_manifesto.json`,
  `outputs/causal/D20D_gates.json`, `outputs/causal/D20E_auditoria_pos_estimacao.json`,
  `outputs/diagnostics/D20A_monte_carlo_configuracao.json`,
  `outputs/diagnostics/D20B_configuracao_inferencia.json`) são pequenos e
  foram versionados como exceção deliberada, junto com este fechamento;
- a D15 (base de tratamento) permanece byte-identical, SHA-256
  `7c24c01b569ed6d10f773d00599b5010e1607696f46d716827182a078e4d733b`.

### Notebooks principais

- `notebooks/01_analise_expansao_rede_federal_economia_municipal.ipynb` —
  notebook acadêmico principal, com a síntese de todas as etapas D1–D20E;
- `notebooks/02` a `notebooks/08` — notebooks técnicos de suporte
  (construção da amostra causal, diagnósticos pré-estimação, infraestrutura
  do estimador escalonado, validação de backend, estimação principal e
  robustez).

### Testes e validações existentes

- suíte completa do projeto: **774/774 aprovados** (`python -m unittest
  discover -s tests -p "test_*.py"`), executada nesta sessão de pausa sem
  nenhuma alteração metodológica;
- `pip check`: sem dependências quebradas;
- `git diff --check`: sem marcadores de conflito.

### Limitações e pendências congeladas

Caso o projeto seja retomado no futuro:

1. decidir a interpretação causal do resultado principal (D20E deixou a
   matriz de evidência pronta, mas a leitura humana final não foi feita);
2. avaliar `docs/methodology/PLANO_D21_CAUSAL_ML.md` — plano de Machine
   Learning causal ainda não executado, sem nenhuma estimação realizada;
3. o resultado principal continua condicionado a tendências paralelas não
   observáveis, timing majoritariamente proxy, cinco tratados extremos,
   influência de porte, spillovers plausíveis, pequena coorte 2013 (n=2) e
   validade externa limitada à população e ao estimando analisados;
4. a seção "Status" do `README.md` (`EFEITO_CAUSAL_ESTIMADO = NAO`) ficou
   desatualizada frente ao D20C, que já produziu uma estimativa real; a
   correção desse status é uma decisão de interpretação causal (pendência
   1) e não foi alterada nesta pausa para não antecipar essa decisão.

### Ponto exato de retomada

Ler esta seção, a seção 31 (D20C–D20E) e
`docs/methodology/PLANO_D21_CAUSAL_ML.md`; decidir a interpretação causal
pendente antes de iniciar qualquer nova estimação; só então avaliar se o
D21 (Causal ML) deve ser iniciado.
