# Playbook Operacional — CEMPRE

## 0. Escopo

Este documento consolida regras operacionais estáveis do painel CEMPRE
município-ano 2007–2019.

Contratos primários:

- `docs/data/AUDITORIA_DISPONIBILIDADE_CEMPRE.md`
- `docs/data/ESPECIFICACAO_PAINEL_CEMPRE.md`
- `docs/data/AUDITORIA_PILOTO_CEMPRE.md`

Se houver conflito, os contratos específicos prevalecem e a divergência deve
ser reportada.

---

## 1. Fonte

Fonte:

**IBGE / SIDRA / CEMPRE**

Tabela:

**1685**

Nível:

**N6 — município**

Janela:

**2007–2019**

O campo `V`/valor bruto deve ser preservado como texto, qualquer que seja
a interface.

### 1.1 Interfaces conhecidas

Duas interfaces de acesso a essa mesma fonte estatística (CEMPRE/IBGE,
agregado 1685), com contratos de schema distintos:

**`apisidra`** (`apisidra.ibge.gov.br`)
- contrato legado, via principal histórica do projeto;
- fixtures históricas já congeladas (D0/Fase 0);
- bloqueada operacionalmente neste ambiente por Cloudflare Challenge
  (`HTTP 403` / `Cf-Mitigated: challenge`) — ver `ESTADO_ATUAL.md`.

**`agregados_v3`** (`servicodados.ibge.gov.br/api/v3/agregados`)
- API oficial de Dados Agregados do IBGE;
- adaptador dedicado (D6), schema próprio, normaliza diretamente para a
  long canônica (não finge ser payload apisidra);
- `fonte_api` explícita na proveniência do cache;
- cache nunca compartilhado entre as duas fontes, mesmo para o mesmo
  lote lógico (ano/UF/variáveis) — ver `ESTADO_ATUAL.md` para o estado
  de implementação e os gates do D6.

Regra arquitetural válida para qualquer interface futura: **nunca
converter silenciosamente o payload de uma fonte em payload de outra**
(ex.: tratar resposta de `agregados_v3` como se fosse `apisidra`). Cada
fonte tem seu próprio normalizador; ambas convergem para a MESMA long
canônica (seção 5). `agregados_v3` ainda não é a fonte nacional ativa —
consultar `ESTADO_ATUAL.md` antes de presumir qual interface está em uso.

---

## 2. Variáveis

### Outcome primário

`708` — Pessoal ocupado assalariado

### Construção básica obrigatória

- `706` — Número de unidades locais
- `707` — Pessoal ocupado total
- `708` — Pessoal ocupado assalariado
- `5944` — Pessoal assalariado médio
- `662` — Salários e outras remunerações
- `10143` — Salário médio mensal em reais

### Opcional/diagnóstica

- `1606` — Salário médio mensal em salários mínimos

A ausência da 1606 NÃO bloqueia o painel técnico.

---

## 3. Interpretação do outcome

A variável 708 representa emprego assalariado no universo CEMPRE.

Não representa automaticamente:

- emprego informal;
- MEI;
- todo emprego municipal.

---

## 4. Arquitetura

```text
API SIDRA
→ JSON raw
→ long normalizada da fonte
→ reconciliação/enriquecimento territorial
→ validações
→ wide/processada
→ diagnósticos
→ futura análise
```

Informação territorial derivada nunca deve ser apresentada como atributo
original da API.

---

## 5. Chave canônica

Na long:

```text
(codigo_municipio_ibge, ano, codigo_variavel_sidra)
```

`request_id` é somente proveniência.

Duplicatas entre requests:

- detectar;
- comparar;
- resolver deterministicamente se consistentes;
- falhar se inconsistentes.

---

## 6. Campos fundamentais

Preservar separadamente:

- `valor_bruto`
- `valor_numerico`
- `status_valor_api`
- `status_territorial`

`status_analitico` pode existir como derivado.

Reconciliação territorial nunca sobrescreve o dado original da API.

---

## 7. Taxonomia de `status_valor_api`

Estados:

- `observado`
- `zero_real`
- `zero_arredondado`
- `zero_arredondado_negativo`
- `sigilo`
- `nao_aplicavel`
- `indisponivel`
- `desconhecido`

Símbolos:

`-`
→ `zero_real`
→ `0`

`0`, `0,0`, `0,00`, `0.0`, `0.00`
→ `zero_arredondado`
→ `0`

`-0`, `-0,0`, `-0,00`, `-0.0`, `-0.00`
→ `zero_arredondado_negativo`
→ `0`

`x`
→ `sigilo`
→ nulo

`..`
→ `nao_aplicavel`
→ nulo

`...`
→ `indisponivel`
→ nulo

desconhecido
→ preservar bruto
→ nulo
→ bloqueia aprovação técnica até investigação.

---

## 8. Parsing de números não-zero

A API observada no piloto usa ponto decimal para números não-zero.

Regra vigente:

- `1.234` → observado;
- `-12.5` → observado;
- `1,234` → desconhecido;
- `12,5` → desconhecido.

Não converter vírgula silenciosamente.

Os literais explícitos de zero são tratados separadamente.

---

## 9. Contrato observado da API

Fixtures reais confirmaram campos equivalentes a:

- `V`
- `D1C` / `D1N`
- `D2C` / `D2N`
- `D3C` / `D3N`
- `MC` / `MN`

Payload inválido não pode produzir sucesso silencioso.

Devem falhar:

- payload não-lista;
- lista vazia;
- lista apenas com cabeçalho;
- item não-dicionário;
- ausência de campos essenciais;
- schema incompatível.

---

## 10. Fixtures

Fixtures pequenas reais podem ser versionadas para:

- congelar contrato;
- testar parser;
- testar normalização;
- permitir testes offline.

Fixture NÃO é cache operacional.

---

## 11. Requests

`request_id` deve ser determinístico.

Estratégia inicial candidata:

`ano × UF/território × grupo de variáveis`

Cada request deve permitir registrar:

- URL/parâmetros;
- request_id;
- tentativas;
- HTTP;
- tamanho;
- hash;
- erro;
- resultado.

---

## 12. Retry

Falhas transitórias:

- timeout;
- retries limitados;
- backoff.

Falha persistente deve ser explícita.

Schema estruturalmente inválido não é sucesso.

---

## 13. Cache

Cache operacional é requisito da Fase 0.

Deve permitir:

1. salvar resposta válida;
2. carregar por `request_id`;
3. reprocessar sem rede;
4. cache hit com zero chamada à API;
5. verificar integridade;
6. rejeitar cache corrompido/inválido.

Diretório esperado:

`data/raw/ibge/cempre/requests/`

Esse conteúdo não pertence ao Git.

---

## 14. Território

`status_territorial` vem de fonte independente do CEMPRE.

Fonte adotada:

**IBGE — Divisão Territorial Brasileira (DTB), 2007–2019.**

Artefato:

`data/processed/calendario_territorial_municipios_2007_2019.parquet`

Join:

```text
(codigo_municipio_ibge, ano)
```

Regra:

- presente → `existia_no_ano`
- ausente → `nao_existia_no_ano`
- sem cobertura → `indeterminado`

Pescaria Brava/2007:

- CEMPRE: `...`
- API: `indisponivel`
- DTB: não existia
- território: `nao_existia_no_ano`

Isso NÃO é incompatibilidade territorial.

---

## 15. Validações cruzadas

Quando valores forem observáveis, diagnosticar:

- `pessoal_ocupado_assalariado <= pessoal_ocupado_total`
- contagens `>= 0`
- unidades locais `>= 0`
- salários/remunerações `>= 0`, quando aplicável
- salário médio em reais `>= 0`

Essas validações não corrigem dados.

---

## 16. Transição 2008→2009

Mudança RAIS:

- registros agregados até 2008;
- individualizados a partir de 2009.

O efeito nacional aproximado de 0,32% NÃO é correção municipal.

Diagnosticar; não corrigir automaticamente.

---

## 17. Transição 2018→2019

Mudança de critério de unidade ativa e incorporação gradual do eSocial.

Não excluir 2019 automaticamente.

---

## 18. Salários

A variável 10143 é nominal.

Deflator é decisão posterior.

A variável 1606 é diagnóstica e não substitui deflacionamento.

---

## 19. Gates

### `PILOTO_TECNICO_APROVADO`

Exige:

- contrato real da API;
- fixture;
- parser seguro;
- símbolos;
- schema;
- API e território separados;
- reconciliação territorial;
- requests;
- retries;
- cache;
- chave canônica;
- nenhuma anomalia bloqueante.

A aprovação final deve ser independente.

### `PAINEL_TECNICO_CONSTRUIDO`

Exige:

- extração completa;
- raw;
- requests;
- parsing;
- território;
- chave;
- cobertura;
- validações;
- diagnósticos;
- manifesto;
- testes.

### `PAINEL_ANALITICO_APROVADO`

Exige decisão humana sobre:

- sigilo;
- cobertura;
- território;
- RAIS;
- eSocial;
- adequação substantiva;
- salários/deflator;
- comparabilidade.

---

## 20. Extração nacional

Não iniciar apenas porque o código permite.

Pré-requisitos:

1. Fase 0 aprovada independentemente;
2. `.gitignore` seguro;
3. cache funcional;
4. calendário territorial apto;
5. dependências reproduzíveis;
6. nenhuma anomalia bloqueante.

Consultar:

`docs/playbooks/ESTADO_ATUAL.md`

---

## 21. Separação causal

O pipeline CEMPRE NÃO deve:

- selecionar controles;
- alterar tratamento;
- fazer matching;
- ATT;
- event study;
- escolher especificação causal.

---

## 22. Auditoria

Usar:

`docs/playbooks/PLAYBOOK_AUDITORIA.md`

Após auditoria ampla e correção delimitada, preferir spot-check focalizado.
