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

`a6a1a41e146dca6a9d6ef6113ddf05ea032d3a89`

Commits recentes:

- `1ee321c` — `feat: constroi calendario territorial IBGE 2007-2019`
- `a6a1a41` — `feat: implementa piloto tecnico do CEMPRE`

Os dois commits foram enviados para `origin/main`.

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

Spot-check tecnico provisorio do Codex:

`SPOT_CHECK_TERRITORIAL_PROVISORIO = OK`

Estado do gate:

`COMMITADO_AGUARDANDO_CONFIRMACAO_INDEPENDENTE_FINAL`

Ainda falta a confirmacao independente final por outro agente antes de
considerar definitivamente fechado:

`CALENDARIO_TERRITORIAL_APTO_CONFIRMADO`

Essa verificacao deve ser focalizada. Nao reabrir auditoria territorial ampla
sem novo problema concreto.

---

## 4. Camada operacional

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

## 5. Proximos passos

1. concluir confirmacao independente final do calendario territorial;
2. integrar o calendario territorial nacional ao pipeline CEMPRE;
3. validar tecnicamente essa integracao;
4. somente depois avaliar liberacao da extracao nacional CEMPRE.

Nao reabrir Fase 0 ou calendario territorial sem anomalia concreta.

---

## 6. Extracao nacional CEMPRE

Status:

**PROIBIDA NESTE MOMENTO.**

Os commits territorial e Fase 0, por si so, nao autorizam a extracao.

Antes de qualquer extracao nacional ainda e necessario:

- confirmacao independente final do calendario territorial;
- integracao do calendario ao pipeline CEMPRE;
- validacao da integracao;
- verificacao dos gates tecnicos correspondentes.

---

## 7. Regra para agentes

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
