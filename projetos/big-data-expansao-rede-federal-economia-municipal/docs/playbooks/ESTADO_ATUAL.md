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

`214c660412d43312125eb5fd69dcbb4e88dce166`

Commits recentes:

- `214c660` — `feat: implementa persistencia offline da long CEMPRE`
- `7db9950` — `docs: registra fechamento do D1 CEMPRE`
- `d9ba6ce` — `feat: implementa plano nacional e completude CEMPRE`
- `acd3d8a` — `feat: integra calendario territorial ao pipeline CEMPRE`
- `d17e621` — `docs: atualiza estado apos fechamento territorial`
- `dd6bbac` — `docs: adiciona playbooks operacionais do projeto`

Os commits foram enviados para `origin/main`. Checkpoint substantivo mais
recente: `214c660412d43312125eb5fd69dcbb4e88dce166` (D2).

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

## 7. Camada operacional

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

## 8. Proximos passos

1. D3 — implementar manifesto e proveniência da extração/reconstrução;
2. D4 — implementar orquestrador nacional e dry-run;
3. auditar o pipeline nacional completo;
4. somente então decidir sobre autorização da extração nacional;
5. após autorização explícita, realizar a primeira execução real.

Nao reabrir Fase 0, calendario territorial ou D2 sem anomalia concreta.

---

## 9. Extracao nacional CEMPRE

Status:

**EXTRAÇÃO NACIONAL CEMPRE = NÃO AUTORIZADA**

Os commits territorial, Fase 0, D1 e D2, por si so, nao autorizam a
extracao.

Antes de qualquer extracao nacional ainda e necessario:

- gate independente pre-extracao nacional CEMPRE aprovado;
- autorizacao explicita para a extracao nacional.

---

## 10. Regra para agentes

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
