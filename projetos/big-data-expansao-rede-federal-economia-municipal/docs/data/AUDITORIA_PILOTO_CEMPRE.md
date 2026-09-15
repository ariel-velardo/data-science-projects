# Auditoria do Piloto Técnico — Painel CEMPRE (Fase 0)

## 1. Escopo

Esta é a implementação da **Fase 0** descrita em
[`ESPECIFICACAO_PAINEL_CEMPRE.md`](ESPECIFICACAO_PAINEL_CEMPRE.md) (seção
12). Nesta etapa:

- **não** foi extraído o painel nacional 2007–2019;
- **não** foi construída a wide nacional nem o Parquet processado final;
- **não** foi feito merge com o cadastro de tratamento (147 municípios
  Fase II, 129 candidatos causais ou pool de 4.964 candidatos a controle);
- **não** foi feita seleção de controles, matching, common support, ATT,
  event study ou qualquer estimação causal;
- **não** foi alterado nenhum cadastro causal (`CONTRATO_CAUSAL.md`,
  `PROTOCOLO_PRE_ANALISE.md`, `REVISAO_INTEGRADA_DESENHO_CAUSAL.md`);
- **não** foi alterada a especificação técnica vigente.

## 1.1 Histórico de auditoria e correções (rastreabilidade)

Este documento passou por duas rodadas. A sequência é preservada aqui
integralmente, conforme exigido pela auditabilidade acadêmica do projeto
— nenhuma reprovação é escondida.

1. **Implementação inicial** (`src/constroi_painel_cempre.py`,
   `tests/test_constroi_painel_cempre.py`, 3 fixtures, primeira versão
   deste documento): 37/37 testes passando.
2. **Autoavaliação inicial**: `PILOTO_TECNICO_APROVADO`.
3. **Auditoria independente posterior** (sessão separada) reprovou esse
   veredito, identificando três bloqueadores e dois pontos não
   bloqueantes:
   - **Bloqueador 1**: `parse_sidra_value` aceitava números não-zero com
     vírgula OU ponto, convertendo vírgula em ponto automaticamente
     (`"1,234" -> 1.234`) — uma interpretação ambígua (decimal vs.
     separador de milhar) sem evidência empírica nas fixtures reais, que
     só mostram ponto para números não-zero.
   - **Bloqueador 2**: a identificação do cabeçalho SIDRA usava uma
     heurística indireta (`D2C` não numérico) que podia, silenciosamente,
     tratar uma observação real com schema alterado como se fosse
     cabeçalho — resultando em um DataFrame vazio sem erro. Além disso,
     `[]` (lista vazia) era aceito implicitamente como resposta válida.
   - **Bloqueador 3**: não havia mecanismo de cache/reprocessamento físico
     por `request_id` — a arquitetura contratada (seção 9 da
     especificação) exige requests + retries + cache/reprocessamento
     funcionando como critério do gate.
   - **Ponto não bloqueante 4**: as exceções do `.gitignore` para
     `data/raw/ibge/cempre/` eram amplas demais — `!data/raw/ibge/cempre/`
     sem um `data/raw/ibge/cempre/*` de reingnorar em seguida deixaria
     qualquer arquivo futuro solto nesse diretório (por exemplo, em um
     futuro `requests/`) visível ao Git, não apenas as fixtures
     pretendidas.
   - **Ponto não bloqueante 5**: as validações cruzadas (seção 11/12 da
     especificação) haviam sido conferidas apenas manualmente, em um
     script ad hoc, sem função de produção nem teste automatizado —
     dívida técnica conhecida que não deveria seguir para a extração
     nacional sem ficar reproduzível.
4. **Gate reclassificado**: `PILOTO_TECNICO_NAO_APROVADO`, em razão dos
   três bloqueadores acima.
5. **Correções aplicadas nesta tarefa** (detalhadas nas seções 4, 7, 9,
   11 e 14 abaixo): parser restrito a ponto decimal para números não-zero
   (vírgula ambígua vira `desconhecido`); `validate_sidra_payload()`
   explícito, cobrindo payload não-lista, lista vazia, lista só com
   cabeçalho, itens não-dicionário e campos obrigatórios ausentes;
   `fetch_request` agora rejeita `[]`/schema inválido como sucesso e
   falha imediatamente nesses casos (sem gastar retries em uma mudança
   estrutural permanente); cache físico por `request_id`
   (`cache_path_for_request`/`load_cached_request`/`save_cached_request`,
   integrado em `fetch_request` via `cache_dir`), com verificação de hash
   e sem aceitar corrupção silenciosamente; `.gitignore` restrito a
   liberar somente as três fixtures nomeadas, reingnorando explicitamente
   cada nível intermediário; `validate_cross_measures()` reproduzível,
   com testes.
6. **Nova autoavaliação**, após as correções e nova bateria de testes
   (seção 13/17 abaixo): ver veredito na seção 18.

## 2. Chamadas reais executadas

Todas as chamadas abaixo foram feitas diretamente contra a API oficial
`apisidra.ibge.gov.br` (sem autenticação), em escala mínima, conforme
seção 12.2/17 da especificação. Nenhuma chamada baixou todos os
municípios ou todos os anos.

| # | Finalidade | URL | Resultado |
|---|---|---|---|
| 1 | Fixture — Serra da Saudade/MG, 5 anos, 6 variáveis | `t/1685/n6/3166600/v/706,707,708,5944,662,10143/p/2007,2008,2009,2018,2019` | HTTP 200, 30 linhas |
| 2 | Fixture — Pescaria Brava/SC, 3 anos, 6 variáveis | `t/1685/n6/4212650/v/706,707,708,5944,662,10143/p/2007,2013,2019` | HTTP 200, 18 linhas |
| 3 | Fixture — 15 municípios de Roraima, 1 ano, 6 variáveis | `t/1685/n6/in%20n3%2014/v/706,707,708,5944,662,10143/p/2019` | HTTP 200, 90 linhas |
| 4 | Integração controlada (rodada inicial) — pipeline completo, Serra da Saudade/MG, 2019, 7 variáveis | `t/1685/n6/3166600/v/662,706,707,708,1606,5944,10143/p/2019` | HTTP 200, 7 linhas, `validate_long` aprovado |
| 5 | Integração controlada (rodada inicial) — reconciliação territorial ao vivo, Pescaria Brava/SC, 2007 | `t/1685/n6/4212650/v/706,708/p/2007` | HTTP 200, `V="..."`, `status_valor_api=indisponivel`, `status_territorial=nao_existia_no_ano` |
| 6 | Demonstração real de cache/reprocessamento (rodada de correção) — Serra da Saudade/MG, 2018 | `t/1685/n6/3166600/v/706,708/p/2018` | HTTP 200 na 1ª chamada (cache miss, grava cache); 2ª chamada é cache hit — **zero** chamadas de rede, mesmo resultado e mesmo hash |

Nenhum teste unitário automatizado depende de rede — apenas as 6
chamadas acima, executadas manualmente para congelar fixtures e validar
a mecânica de ponta a ponta (incluindo, agora, o cache).

## 3. Fixture criada

Diretório: `data/raw/ibge/cempre/fixtures/` (versionado; exceções
estreitas no `.gitignore` — ver seção 1.1, ponto 4, e seção 11 abaixo).
As três fixtures da implementação inicial foram **preservadas sem
alteração** nesta rodada de correção, conforme instruído — não havia
necessidade objetiva de recriá-las ou ampliá-las:

- `tabela_1685_n6_3166600_serra_da_saudade_2007_2008_2009_2018_2019.json` (8.494 bytes)
- `tabela_1685_n6_4212650_pescaria_brava_2007_2013_2019.json` (5.198 bytes)
- `tabela_1685_n6_in_n3_14_roraima_2019.json` (24.288 bytes)

Total: ~38 KB. Cada arquivo é a resposta bruta da API, preservada
exatamente como recebida.

## 4. Schema real observado

O schema retornado pela API `apisidra.ibge.gov.br/values` é uma lista
JSON cujo **primeiro elemento é um dicionário de rótulos** (não uma
observação), seguido de um dicionário por observação:

```json
{
  "NC": "6", "NN": "Município",
  "MC": "45", "MN": "Pessoas",
  "V": "183",
  "D1C": "3166600", "D1N": "Serra da Saudade (MG)",
  "D2C": "708", "D2N": "Pessoal ocupado assalariado",
  "D3C": "2007", "D3N": "2007"
}
```

Campos confirmados e usados pelo parser: `V` (valor, sempre string),
`D1C`/`D1N` (código/nome do município), `D2C`/`D2N` (código/nome da
variável), `D3C`/`D3N` (ano), `MC`/`MN` (unidade de medida). O
cabeçalho tem assinatura literal própria e reconhecível:
`V == "Valor"` e `D1C == "Município (Código)"`.

**Correção aplicada nesta rodada (Bloqueador 2)**: a identificação do
cabeçalho passou a usar essa assinatura literal
(`_e_linha_de_cabecalho`), em vez da heurística anterior ("D2C não é
numérico"). A heurística anterior podia, em tese, classificar
silenciosamente uma observação real com campo corrompido/ausente como se
fosse cabeçalho, produzindo um DataFrame vazio sem erro. Agora, qualquer
item que não seja literalmente o cabeçalho é tratado como observação e
precisa ter `D1C`, `D2C`, `D3C` e `V` — sua ausência é reportada
explicitamente por `validate_sidra_payload()`, nunca silenciada.

**Achado sobre rótulo do município (não bloqueante, inalterado desde a
rodada anterior)**: `D1N` não é consistente entre municípios — Serra da
Saudade aparece como `"Serra da Saudade (MG)"` (parênteses) e os
municípios de Roraima aparecem como `"Amajari - RR"` (hífen). Como
`municipio_fonte` é apenas rótulo (não chave), isso não bloqueia o
piloto.

**Achado sobre separador decimal — parcialmente resolvido nesta rodada
(Bloqueador 1)**: a especificação (seção 6.1) descreve os literais de
zero arredondado com vírgula (`0,0`; `-0,00` etc.), refletindo a
convenção da publicação em PDF, enquanto os valores numéricos reais
observados usam **ponto** (`"188.72"`, `"512.40"`). Esta rodada de
correção resolveu a parte ambígua desse achado: **números não-zero** só
são aceitos com ponto — uma vírgula em um número não-zero (`"1,234"`,
`"12,5"`) agora é classificada como `desconhecido`, nunca mais
convertida silenciosamente (`float(v.replace(",", "."))` foi removido do
caminho de números genéricos). Os **literais de zero documentados**
continuam aceitos com vírgula OU ponto (`"0,0"`/`"0.0"` etc.) — isso é
uma decisão deliberada e permanece um comparação por igualdade de string
contra um conjunto fechado de 10 literais, não um parsing genérico; não
há, ainda, evidência empírica de qual separador a API usaria para um
zero arredondado real (nenhum foi observado ao vivo até agora), então
esse sub-ponto específico continua registrado como não bloqueante na
seção 15.

## 5. Arquitetura efetivamente implementada

Arquivo: `src/constroi_painel_cempre.py`. Implementa as funções
necessárias para o piloto, preservando a separação conceitual da
arquitetura contratada (API → JSON raw → long normalizada → reconciliação
territorial → validações → diagnósticos):

- `parse_sidra_value` — parser de `V` (seção 6.1), corrigido nesta rodada
  (Bloqueador 1: só ponto para números não-zero);
- `validate_sidra_payload` — **novo nesta rodada** (Bloqueador 2):
  validação explícita da forma do payload bruto antes de qualquer
  normalização;
- `normalize_long` — long normalizada da fonte (seção 5); agora chama
  `validate_sidra_payload` no início e levanta `ValueError` se o payload
  for estruturalmente inválido, além das validações de código municipal,
  ano e variável já existentes;
- `load_calendar_territorial` — calendário territorial mínimo do piloto
  (inalterado nesta rodada, sem evidência de bug);
- `reconcile_territorial` — deriva `status_territorial` e
  `incompatibilidade_territorial` (inalterado);
- `validate_long` — unicidade da chave canônica e duplicidade entre
  `request_id` (inalterado);
- `build_requests` — monta requisições ano × território × grupo de
  variáveis (inalterado);
- `cache_path_for_request` / `load_cached_request` / `save_cached_request`
  — **novos nesta rodada** (Bloqueador 3): cache físico por `request_id`
  em `data/raw/ibge/cempre/requests/` (não versionado), com verificação
  de hash e falha explícita em corrupção;
- `fetch_request` — agora integra `validate_sidra_payload` (payload
  inválido nunca é sucesso, e falha imediatamente sem gastar retries) e,
  opcionalmente, o cache acima (`cache_dir=...`);
- `fetch_metadata` — inalterado;
- `build_diagnostics` — inalterado;
- `validate_cross_measures` — **novo nesta rodada** (ponto não bloqueante
  5): validações cruzadas reproduzíveis sobre a long validada.

Não implementadas nesta Fase 0 (não necessárias para o piloto, conforme
autorizado pela seção 13 da especificação): `build_wide`, `validate_wide`,
`write_manifest`.

## 6. Calendário territorial do piloto

Inalterado nesta rodada — sem evidência de bug, conforme instruído.
`load_calendar_territorial()` retorna uma fixture mínima cobrindo Serra
da Saudade/MG, os 15 municípios de Roraima e Pescaria Brava/SC, com
Pescaria Brava marcada como não existente antes de 2013. Município fora
dessa cobertura resulta em `status_territorial = indeterminado`.

## 7. Resultado do parser

`parse_sidra_value` cobre todos os símbolos exigidos pela seção 6.1,
incluindo as três classes de zero. **Após a correção do Bloqueador 1**,
o algoritmo é: remover espaços externos; comparar contra os literais
exatos documentados (`-`, os 5 literais de zero arredondado positivo, os
5 de zero arredondado negativo, `x`, `..`, `...`) antes de qualquer
tentativa de conversão numérica; só então tentar casar um número
genérico contra `^-?\d+(\.\d+)?$` (ponto apenas); qualquer vírgula fora
dos literais de zero, ou qualquer formato fora desse regex, é
`desconhecido`. `valor_bruto` é preservado em 100% dos casos, inclusive
quando `desconhecido`.

## 8. `status_valor_api` encontrados

- Fixture Serra da Saudade (30 valores): todos `observado`.
- Fixture Pescaria Brava (18 valores): `observado` para 2013/2019 (12
  valores), `indisponivel` para 2007 (6 valores, `V="..."`).
- Fixture Roraima 2019 (90 valores): todos `observado`.
- Chamadas de integração ao vivo (seção 2, itens 4-6): todos `observado`.

Não foram observados `x`, `-`, nem os literais de zero arredondado em
nenhuma chamada real. Todos os 8 literais de zero, `x`/`..`/`...`, o
símbolo desconhecido e — novo nesta rodada — os casos de vírgula
ambígua em número não-zero (`"1,234"`, `"12,5"`) foram testados via
casos sintéticos, sem depender de rede.

## 9. Reconciliação territorial

Inalterada e revalidada nesta rodada (suíte completa, seção 13). Os
quatro cenários da seção 12.1/13.1 continuam cobertos: existia no ano;
não existia + `"..."` (esperado, não incompatibilidade — caso Pescaria
Brava/2007, preservado exatamente como antes); incompatibilidade real
(caso sintético); cobertura ausente no calendário (`indeterminado`).

## 10. Estratégia de requests testada

Inalterada. A segmentação candidata (ano × território × grupo de
variáveis) foi testada com município único e UF pequena (`in n3`).
Adicionalmente, agora toda resposta passa por `validate_sidra_payload`
antes de ser aceita como sucesso — testado com o payload real das
fixtures e com casos sintéticos de schema quebrado (seção 12 abaixo).

## 11. Comportamento de cache/retry (Bloqueador 3 — corrigido nesta rodada)

Anteriormente (rodada inicial): cache físico não estava implementado —
apontado pela auditoria independente como um dos três bloqueadores, já
que o gate exige requests + retries + **cache/reprocessamento**
funcionando (seção 9/13.1 da especificação).

**Implementado nesta rodada**: `cache_path_for_request(request_id,
cache_dir)` calcula um caminho determinístico
(`data/raw/ibge/cempre/requests/<request_id>.json`, não versionado).
`save_cached_request` grava um envelope `{request_id, hash_resposta_raw,
texto_resposta_raw}` — o **texto exato** da resposta, não apenas o JSON
já parseado, para permitir reverificação de integridade byte a byte.
`load_cached_request` recalcula o hash SHA-256 do texto e compara com o
hash salvo; qualquer divergência, JSON malformado no envelope ou no
texto da resposta levanta `ValueError` — nunca cai silenciosamente de
volta para a rede. `fetch_request(..., cache_dir=...)` integra os três:
cache hit retorna sem nenhuma chamada de rede (inclusive validando o
payload em cache com `validate_sidra_payload` antes de aceitar); cache
miss chama a rede normalmente e, em caso de sucesso, grava o cache;
cache corrompido ou com schema inválido falha explicitamente, sem
tentar a rede automaticamente.

**Demonstrado com chamada real** (seção 2, item 6): uma primeira chamada
a `apisidra.ibge.gov.br` (Serra da Saudade/MG, 2018) foi cacheada; uma
segunda chamada, usando uma sessão que lança `AssertionError` caso
`.get()` seja invocado, retornou o mesmo resultado e o mesmo hash **sem
nenhuma chamada de rede** — prova de que o reprocessamento funciona sem
depender da API.

Retry/backoff (inalterado desta rodada, já testado antes): sucesso HTTP
200 na primeira tentativa; falha HTTP 500 seguida de sucesso no retry
seguinte; falha persistente após o limite. **Refinamento desta rodada**:
uma falha de **schema** (payload bem formado mas com forma errada, ex.
`[]` ou campo obrigatório ausente) agora falha imediatamente, sem gastar
as tentativas restantes — retry não conserta uma mudança estrutural
permanente. Já um erro de **decodificação JSON** (resposta
truncada/corrompida em trânsito) continua sendo tentado novamente, por
ser potencialmente transitório; se persistir até o limite, falha com
`resultado=None`.

## 12. Testes criados

`tests/test_constroi_painel_cempre.py`, **71 testes** via `unittest`
(nenhum depende de rede) — 34 testes a mais que a rodada inicial (37):

- `TestParseSidraValue` (21 testes, +5 desta rodada): os 16 anteriores
  mais `"1,234" -> desconhecido`, `"12,5" -> desconhecido`, `"1.234" ->
  observado`, `"-12.5" -> observado` (explícito) e preservação de
  `valor_bruto` no caso de vírgula ambígua.
- `TestNormalizeLong` (5 testes, inalterados).
- `TestReconcileTerritorial` (5 testes, inalterados).
- `TestValidateLongDuplicidade` (3 testes, inalterados).
- `TestBuildRequests` (3 testes, inalterados).
- `TestFetchRequestRede` (5 testes): os 3 anteriores de
  retry/sucesso/falha (payload de sucesso corrigido de `[]` para um
  payload real válido, já que `[]` deixou de ser sucesso) mais um teste
  explícito de payload real válido.
- `TestValidateSidraPayload` (9 testes, **novo**): payload real válido,
  payload não-lista, lista vazia, lista só com cabeçalho, item não-dict,
  observação sem `D1C`/`D2C`/`D3C`/`V`.
- `TestFetchRequestSchemaInvalido` (9 testes, **novo**): lista vazia,
  lista só com cabeçalho, campos `D1C`/`D2C`/`D3C`/`V` ausentes, payload
  não-lista — todos falhando com exatamente 1 chamada de rede (sem
  gastar retries); JSON inválido com retry (falha persistente e
  sucesso-no-retry).
- `TestCacheReprocessamento` (6 testes, **novo**): 1ª execução (cache
  miss → cria cache), 2ª execução (cache hit → zero chamadas de rede),
  cache com JSON inválido (falha explícita, zero chamadas de rede), cache
  com schema inválido (não aceito, zero chamadas de rede), `request_id`
  diferente não reutiliza cache de outro, `load_cached_request` retorna
  `None` em cache miss.
- `TestValidateCrossMeasures` (4 testes, **novo**): caso coerente (zero
  violações), assalariado > total (1 violação), valor negativo (1
  violação), sigilo não gera falsa violação.

## 13. Testes executados e resultados

```
.venv\Scripts\python.exe -m unittest tests.test_constroi_painel_cempre -v
...
Ran 71 tests in 0.25s
OK
```

Executados apenas os testes da Fase 0 diretamente relacionados às
correções, conforme instruído — a suíte completa do projeto não foi
executada (nenhum outro módulo depende de `constroi_painel_cempre.py`).

## 14. Validações cruzadas implementadas (ponto não bloqueante 5 — corrigido nesta rodada)

Anteriormente: verificação manual, ad hoc, não reproduzível.

**Implementado nesta rodada**: `validate_cross_measures(df_long)` pivota
a long (já validada por `validate_long`) para `(codigo_municipio_ibge,
ano)` × medida, **somente** quando `status_valor_api` indica valor
numérico observado (`observado` ou uma classe de zero) — células em
sigilo/indisponível/etc. são excluídas da comparação, nunca tratadas como
zero ou ausência. Verifica: `pessoal_ocupado_assalariado <=
pessoal_ocupado_total`; não-negatividade de `pessoal_ocupado_total`,
`pessoal_ocupado_assalariado`, `pessoal_assalariado_medio`,
`qt_unidades_locais`, `salarios_remuneracoes_mil_reais_nominal` e
`salario_medio_reais_nominal`. Retorna um DataFrame de violações (vazio
se não houver nenhuma) — puramente diagnóstico, sem corrigir nada.

A relação aproximada entre salários e outras remunerações, pessoal
assalariado médio e salário médio mensal **não** foi implementada como
regra de validação — documentado explicitamente no código como decisão
deliberada: as unidades disponíveis permitiriam uma fórmula aproximada,
mas transformar uma aproximação incerta em regra de validação arriscaria
sinalizar diferenças de arredondamento legítimas como violação. Fica
para uma etapa posterior, com decisão humana explícita sobre tolerância.

Testado com 4 casos (`TestValidateCrossMeasures`, seção 12): caso
coerente, assalariado > total, valor negativo (`salário médio` sintético
negativo), e um caso com sigilo (`x`) que não deve gerar falsa violação
por comparação com dado ausente.

## 15. Anomalias encontradas

Nenhuma anomalia técnica bloqueante. Um achado não bloqueante
permanece em aberto (já registrado na rodada anterior, sem mudança):

1. Formato de rótulo do município (`D1N`) inconsistente entre municípios
   (parênteses vs. hífen) — não afeta a chave, apenas o rótulo textual.
2. Separador decimal dos literais de zero arredondado documentados na
   especificação (vírgula) diverge do separador observado nos valores
   numéricos reais não-zero (ponto). A parte ambígua deste achado — como
   tratar vírgula em números **não-zero** — foi **resolvida** nesta
   rodada (Bloqueador 1: agora `desconhecido`). A parte que permanece
   aberta é estritamente sobre os **literais de zero**: nenhum valor real
   arredondado a zero foi observado ao vivo até agora para confirmar
   empiricamente se a API usaria vírgula ou ponto nesse caso específico
   — o parser aceita ambos os formatos apenas para esse conjunto fechado
   de 10 literais, não como parsing genérico.

## 16. Artefatos produzidos/modificados nesta rodada

- `src/constroi_painel_cempre.py` (modificado — 5 correções)
- `tests/test_constroi_painel_cempre.py` (modificado — 34 testes novos)
- `.gitignore` (modificado — exceções de `data/raw/ibge/cempre/`
  reescritas de forma estreita)
- `docs/data/AUDITORIA_PILOTO_CEMPRE.md` (este documento, reescrito com
  rastreabilidade completa)
- `data/raw/ibge/cempre/fixtures/*.json` (preservadas sem alteração)
- `data/raw/ibge/cempre/requests/*.json` (cache operacional real, criado
  pela demonstração da seção 2/11 — **não versionado**, ignorado pelo
  Git, conforme confirmado por `git check-ignore`/`git add --dry-run` na
  seção 20)

Nenhum Parquet, nenhum manifesto de proveniência nacional e nenhum
diagnóstico de cobertura nacional foram criados.

## 17. Avaliação do gate `PILOTO_TECNICO_APROVADO` (reavaliação)

| # | Critério (seção 13.1 da especificação) | Avaliação |
|---|---|---|
| 1 | Contrato/schema real da API confirmado | **Sim** — inalterado; cabeçalho agora identificado por assinatura literal, mais robusto que a heurística anterior. |
| 2 | Fixture real preservada e versionada | **Sim** — as 3 fixtures preservadas sem alteração; `.gitignore` agora restringe a exceção estritamente a elas (ver seção 20). |
| 3 | Parser funciona sobre a fixture e os casos da seção 12.1 | **Sim** — e agora é seguro: vírgula ambígua em número não-zero não é mais convertida silenciosamente (Bloqueador 1 corrigido). |
| 4 | Todos os símbolos conhecidos tratados, incl. as três classes de zero | **Sim** — inalterado; ver achado não bloqueante 2 (seção 15) sobre separador de zero não confirmado empiricamente. |
| 5 | `status_valor_api` e `status_territorial` permanecem separados | **Sim** — inalterado, testado explicitamente. |
| 6 | Reconciliação territorial testada, incl. `nao_existia_no_ano` vs. `incompatibilidade_territorial` | **Sim** — inalterado. |
| 7 | Requests funcionam nos contextos da seção 12.1 | **Sim** — e agora com validação explícita de schema (`validate_sidra_payload`), corrigindo o Bloqueador 2. |
| 8 | Retry/cache funcionam | **Sim** — cache físico por `request_id` implementado e demonstrado com chamada real (Bloqueador 3 corrigido); retry distingue falha transitória (JSON inválido) de falha permanente (schema inválido). |
| 9 | Chave canônica preservada | **Sim** — inalterado. |
| 10 | Nenhuma anomalia técnica bloqueante | **Sim** — apenas os dois achados não bloqueantes da seção 15 (um deles parcialmente resolvido nesta rodada). |

Critérios adicionais verificados nesta rodada, cobrindo os pontos não
bloqueantes 4 e 5 da auditoria independente:

| # | Critério adicional | Avaliação |
|---|---|---|
| 11 | `.gitignore` restrito somente às fixtures pequenas necessárias | **Sim** — reescrito com reingnorar explícito em cada nível (`data/raw/ibge/cempre/*`, `data/raw/ibge/cempre/fixtures/*`), confirmado com `git check-ignore -v` e `git add --dry-run` (seção 20). |
| 12 | Validações cruzadas reproduzíveis, não apenas manuais | **Sim** — `validate_cross_measures()`, com 4 testes automatizados. |

## 18. Veredito

## PILOTO_TECNICO_APROVADO

**Motivo**: os três bloqueadores identificados pela auditoria
independente (parser ambíguo, validação de schema/resposta vazia
insuficiente, ausência de cache/reprocessamento) foram corrigidos nesta
rodada e cobertos por 34 novos testes automatizados (total 71/71
passando). Os dois pontos não bloqueantes (`.gitignore` amplo,
validações cruzadas não reproduzíveis) também foram corrigidos. Os dez
critérios originais do gate mais os dois critérios adicionais desta
rodada foram avaliados individualmente (seção 17) e todos atendidos. O
único ponto que permanece parcialmente em aberto — qual separador a API
usaria para um literal de zero arredondado real, nunca observado ao vivo
— é não bloqueante por natureza (afeta um conjunto fechado de 10
literais defensivamente aceitos em ambos os formatos, não a
classificação de números genéricos, que agora é estrita).

Este veredito cobre exclusivamente a viabilidade técnica da mecânica do
piloto — não implica `PAINEL_TECNICO_CONSTRUIDO` nem qualquer decisão
analítica ou causal.

## 19. Próximos passos recomendados

1. Antes da extração nacional 2007–2019, decidir a fonte definitiva do
   calendário territorial histórico (seção 7 da especificação) — a
   fixture mínima usada aqui cobre apenas os municípios do piloto.
2. Ao extrair os primeiros lotes nacionais, verificar empiricamente se
   algum literal de zero arredondado aparece com vírgula ou ponto,
   resolvendo o último sub-ponto aberto do achado da seção 15.
3. Implementar `build_wide`, `validate_wide` e `write_manifest` apenas
   quando a extração nacional for autorizada — nesse momento, decidir
   também se/como a relação aproximada entre salários, pessoal
   assalariado médio e salário médio mensal deve virar uma validação
   cruzada adicional (deliberadamente não implementada nesta Fase 0,
   seção 14).
4. Ao escalar o volume de requests, monitorar o tamanho do diretório de
   cache (`data/raw/ibge/cempre/requests/`, não versionado) e decidir uma
   política de retenção/limpeza antes da extração nacional.

## 20. Verificação final

```
.venv\Scripts\python.exe -m unittest tests.test_constroi_painel_cempre -v
Ran 71 tests in 0.25s
OK
```

`git diff --check`: sem problemas de espaço em branco (apenas aviso de
conversão LF/CRLF do Git no Windows, não um problema de conteúdo).

`git check-ignore -v` / `git add --dry-run` (ponto não bloqueante 4,
corrigido):

- fixture pretendida (`data/raw/ibge/cempre/fixtures/tabela_1685_n6_3166600_...json`) → **versionável** (`git add --dry-run` aceita).
- arquivo simulado em `data/raw/ibge/cempre/requests/` (cache futuro) → **ignorado** (`git add --dry-run` recusa).
- arquivo simulado solto em `data/raw/ibge/cempre/` fora de `fixtures/` → **ignorado**.
- arquivo simulado não previsto dentro de `data/raw/ibge/cempre/fixtures/` → **ignorado** (só os 3 nomes explícitos são liberados).

`git status --short -- .`: apenas os artefatos listados na seção 16.
Nenhum `git add`, `git commit` ou `git push` foi executado nesta tarefa.

Confirmações explícitas:

- **não** houve extração nacional 2007–2019;
- **não** foi construído painel completo (wide nacional ou Parquet
  processado);
- **não** houve merge causal com o cadastro de tratamento ou pool de
  controles;
- **não** houve estimação, matching, common support, ATT ou event study;
- **não** houve `git add`, `commit` ou `push`.
