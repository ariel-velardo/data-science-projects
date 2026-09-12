# Pool Candidato a Controles sem Exposição Observada (2007–2019)

## 1. Objetivo

Construir, documentar e testar um cadastro reproduzível de elegibilidade
para o **pool inicial de municípios candidatos a controle** da Expansão
Fase II.

Rotina: [`src/constroi_pool_candidato_controles.py`](../../src/constroi_pool_candidato_controles.py).

Esta etapa **não**:

- faz matching;
- usa outcomes econômicos (CEMPRE ou qualquer outro);
- estima efeito causal (ATT, event study, DiD, TWFE);
- avalia suporte comum ou balanceamento;
- define controles causais finais;
- trata spillovers geográficos ou distância.

Ela apenas identifica, de forma puramente lógica sobre cadastros já
aprovados, quais municípios são **candidatos a comparação** com base em:

1. ausência de exposição federal observada durante 2007–2019;
2. presença no universo municipal durante os 13 anos;
3. não pertencimento à lista oficial de municípios da Expansão Fase II.

## 2. Por que esse pool está sendo criado

O `CONTRATO_CAUSAL.md` registra que **não existe hoje um pool nacional de
controles reproduzível**: as antigas populações exploratórias (53
municípios em common support, 47 pares) não são atualmente reprodutíveis
e estão suspensas como populações operacionais. Antes de qualquer
matching, é preciso primeiro delimitar, de forma auditável e
determinística, **quem sequer pode entrar na disputa** por ser controle —
ou seja, quem não tem exposição observada durante a janela e está
presente no universo o tempo todo. Esta rotina resolve exatamente essa
etapa preliminar, sem tocar em nenhuma variável causal.

## 3. Por que essa etapa vem antes do matching

Matching, suporte comum e balanceamento exigem covariáveis e (no caso do
outcome) o painel econômico do CEMPRE — nenhum dos dois existe ainda
nesta fase do projeto. Definir primeiro o pool de elegibilidade estrutural
(exposição + universo + Fase II) permite:

- auditar o funil de exclusão antes de introduzir qualquer variável
  economicamente carregada;
- não confundir "não pode ser controle por desenho" (exposto, Fase II,
  fora do universo) com "não é bom controle por falta de suporte comum"
  (uma decisão estatística que só pode ser tomada depois, com
  covariáveis);
- garantir que a etapa causal (matching) parta de uma população candidata
  já validada estruturalmente, e não de um recorte ad-hoc.

## 4. Ausência de exposição observada × "never-treated" causal

Um município com `sem_exposicao_observada_2007_2019=True` **não é** um
"never-treated" comprovado em sentido causal forte. Essa nomenclatura é
deliberadamente evitada em todo o projeto (ver
`CADASTRO_NACIONAL_EXPOSICAO_REDE_FEDERAL.md`, seção 2, e
`CONTRATO_CAUSAL.md`). As diferenças relevantes:

- a proxy de exposição (`fl_presenca_federal_ept_ativa`, Censo Escolar)
  é observacional e mecânica — não confirma criação administrativa,
  autorização, inauguração ou início das aulas de um campus;
- a ausência de exposição **dentro da janela 2007–2019** não garante
  ausência de exposição fora dela (antes de 2007 ou depois de 2019);
- nenhuma validação institucional individual (ato de criação, fonte
  primária) foi feita para os municípios "sem exposição observada" — ao
  contrário do que já foi feito para os 147 da Fase II em
  `CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`;
- suporte comum, balanceamento em covariáveis e ausência de spillover
  geográfico — três condições adicionais exigidas de um controle causal
  válido — não foram avaliados aqui.

Por isso, todo município elegível por esta rotina é chamado, em toda a
documentação e no código, de **"candidato a controle sem exposição
observada em 2007–2019"** — nunca de "controle", "never-treated" ou
"controle causal validado".

## 5. Regra operacional exata

Um município é candidato elegível somente quando todas as condições são
verdadeiras:

```
elegivel =
    sem_exposicao_observada_2007_2019
    AND presente_nos_13_anos_do_universo
    AND NOT fl_municipio_fase_ii
```

Nenhuma dessas três condições é recalculada ou redefinida por esta
rotina — as duas primeiras são lidas diretamente do cadastro nacional de
exposição já aprovado; a terceira é obtida por pertencimento ao cadastro
oficial da Fase II.

## 6. Fontes utilizadas

| Fonte | Caminho | Papel |
|---|---|---|
| Resumo nacional de exposição observada | `data/processed/resumo_exposicao_rede_federal_municipio_2007_2019.parquet` | Fornece `sem_exposicao_observada_2007_2019` e `presente_nos_13_anos_do_universo`, já aprovados e não recalculados |
| Cadastro oficial Fase II | `data/processed/fase_ii_municipios.parquet` | Fornece o conjunto dos 147 códigos municipais oficiais da Expansão Fase II |

Nenhum outro arquivo é lido. Em particular, **nenhum outcome econômico
(CEMPRE), covariável, dado geográfico ou resultado de estimação causal é
utilizado.**

## 7. Definição de exposição observada herdada

Herdada exatamente do cadastro nacional
(`CADASTRO_NACIONAL_EXPOSICAO_REDE_FEDERAL.md`, seções 2 e 4):
`sem_exposicao_observada_2007_2019=True` significa que o município nunca
apresentou, em nenhum dos anos em que foi observado no universo do Censo
Escolar entre 2007 e 2019, a proxy `fl_presenca_federal_ept_ativa`
(escola federal, ativa, com oferta de EPT — `TP_DEPENDENCIA==1` ∧
`TP_SITUACAO_FUNCIONAMENTO==1` ∧ `IN_PROF==1`). Esta rotina não altera
essa definição.

## 8. Funil quantitativo obtido

Execução de referência (dados locais desta sessão; para os valores
correntes, execute o script ou leia
`outputs/diagnostics/resumo_pool_candidato_controles.csv` diretamente —
nenhum número abaixo é mantido manualmente independente do artefato):

| Métrica | Valor |
|---|---|
| Total de municípios (resumo nacional) | 5.570 |
| Sem exposição observada 2007–2019 | 4.970 |
| Com exposição observada 2007–2019 | 600 |
| Presentes nos 13 anos do universo | 5.564 |
| Universo incompleto (< 13 anos) | 6 |
| Pertencentes à Fase II | 147 |
| Não pertencentes à Fase II | 5.423 |
| **Elegíveis (candidatos a controle)** | **4.964** |
| Inelegíveis | 606 |

Verificação aritmética: 4.970 (sem exposição) − 6 (universo incompleto,
integralmente contido no conjunto sem exposição, ver seção 9) = 4.964
elegíveis — confere exatamente com o valor obtido.

## 9. Motivos de exclusão e sobreposições

`motivos_exclusao` registra, sem hierarquia, **todos** os motivos
aplicáveis a cada município inelegível (`;`-separado); um município
elegível tem `motivos_exclusao=""` (string vazia — mesma convenção já
usada em `anos_expostos` no cadastro nacional para "nenhum aplicável").

| Motivo excluído por | Contagem |
|---|---|
| Exposição observada (`fl_excluir_exposicao_observada`) | 600 |
| Universo incompleto (`fl_excluir_universo_incompleto`) | 6 |
| Fase II (`fl_excluir_fase_ii`) | 147 |

Sobreposições entre motivos (execução de referência):

| Sobreposição | Contagem |
|---|---|
| Exposição observada ∩ universo incompleto | 0 |
| Exposição observada ∩ Fase II | 147 |
| Universo incompleto ∩ Fase II | 0 |
| Os três motivos simultaneamente | 0 |

A sobreposição **exposição ∩ Fase II = 147** confirma que **todos** os
147 municípios oficiais da Fase II apresentaram ao menos um ano, entre
2007 e 2019, com presença federal de EPT ativa observada no Censo
Escolar (`fl_presenca_federal_ept_ativa=true`). Essa sobreposição **não**
identifica qual unidade gerou o registro, **não** demonstra que o
registro foi produzido pelo campus da própria Fase II, **não** identifica
criação administrativa, autorização, inauguração ou início das aulas, e
**não** valida o timing institucional do tratamento — nenhuma dessas
questões é respondida por uma contagem de sobreposição. Presença federal
preexistente no município (anterior à Fase II) ou unidades de outras
ondas de expansão da Rede Federal podem, isoladamente ou em conjunto,
contribuir para a exposição observada, exatamente como já alertado em
`CADASTRO_NACIONAL_EXPOSICAO_REDE_FEDERAL.md` (seção 2) para o cadastro
nacional do qual esta rotina herda a proxy. Esta seção mantém, portanto,
quatro conceitos distintos: exposição observada (o que o Censo Escolar
mede), pertencimento à lista Fase II (um cadastro administrativo),
tratamento causal (uma decisão documentada em `CONTRATO_CAUSAL.md`) e
timing institucional (auditado, para os 147 da Fase II, em
`CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md` e `AUDITORIA_TIMING_TRATAMENTO.md`).
Nenhum município Fase II é excluído *apenas* pelo motivo Fase II sem
também carregar o motivo de exposição observada. A sobreposição zero
entre universo incompleto e Fase II é coerente com os 147 municípios da
Fase II serem sedes historicamente consolidadas, observadas nos 13 anos
do Censo.

## 10. Limitações observacionais

- A ausência de exposição observada depende inteiramente da cobertura e
  qualidade do Censo Escolar em cada ano — as mesmas limitações já
  documentadas em `CADASTRO_NACIONAL_EXPOSICAO_REDE_FEDERAL.md`, seção
  13, se aplicam integralmente aqui (nenhuma validação institucional
  individual, sem distinção de outras fases de expansão federal, sem
  harmonização territorial histórica).
- Um município "sem exposição observada" pode, ainda assim, ter recebido
  um campus federal fora da janela 2007–2019, ou ter sido alvo de outra
  fase de expansão não capturada por esta proxy.
- Nenhuma variável de distância geográfica foi usada; um município
  espacialmente próximo de um polo Fase II pode estar contaminado por
  spillover e ainda assim aparecer como elegível aqui — a política de
  spillover permanece uma decisão aberta em `CONTRATO_CAUSAL.md`.
- `presente_nos_13_anos_do_universo` reflete apenas presença no universo
  do Censo Escolar, não qualidade ou completude de outras fontes (por
  exemplo, do CEMPRE, que ainda não foi incorporado ao projeto).

## 11. Por que estes municípios ainda não são controles finais

Um município `fl_elegivel_controle_candidato=True` é apenas um candidato
estrutural — ele ainda não passou por:

1. avaliação de spillover geográfico (critério ainda em aberto no
   `CONTRATO_CAUSAL.md`);
2. construção do painel econômico do CEMPRE (outcome primário futuro,
   ainda não construído);
3. incorporação de covariáveis pré-tratamento justificadas pelo DAG do
   `CONTRATO_CAUSAL.md`;
4. avaliação de suporte comum e balanceamento com os tratados;
5. matching propriamente dito.

Nenhuma dessas cinco etapas foi executada por esta rotina. Portanto, os
4.964 municípios do pool filtrado formam apenas o **ponto de partida**
para a construção do pool de controles causais — não o resultado final.

## 12. Etapas pendentes

Na ordem em que devem ser abordadas (ver `ROADMAP_ACADEMICO.md`):

- exclusão de municípios contaminados por spillover geográfico;
- construção do painel econômico municipal do CEMPRE;
- incorporação de covariáveis pré-tratamento;
- avaliação de suporte comum e balanceamento;
- matching e definição final do(s) grupo(s) de comparação.

## 13. Confirmação: nenhum outcome econômico foi utilizado

Esta rotina lê exclusivamente `resumo_exposicao_rede_federal_municipio_2007_2019.parquet`
e `fase_ii_municipios.parquet` — nenhum dos dois contém outcomes
econômicos, dados do CEMPRE, resultados pós-tratamento, covariáveis
econômicas, distância geográfica, escores de propensão, resultados de
suporte comum ou estimativas de efeito causal. A regra de elegibilidade
(seção 5) é uma expressão puramente lógica sobre três flags booleanas.

## 14. Schema dos artefatos

### Cadastro completo

`data/processed/cadastro_elegibilidade_controles_2007_2019.parquet` —
5.570 linhas, uma por município do resumo nacional (nenhum município
inelegível é apagado).

| Coluna | Tipo | Descrição |
|---|---|---|
| `codigo_municipio_ibge` | string (7 dígitos) | chave |
| `municipio`, `uf`, `co_uf` | string | herdados do resumo nacional |
| `primeiro_ano_exposicao_observada`, `n_anos_no_universo`, `anos_ausentes_do_universo` | Int64 / string | preservados do resumo nacional como contexto diagnóstico |
| `sem_exposicao_observada_2007_2019` | bool | herdado do resumo nacional, não recalculado |
| `presente_nos_13_anos_do_universo` | bool | herdado do resumo nacional, não recalculado |
| `fl_municipio_fase_ii` | bool | pertencimento ao cadastro oficial da Fase II |
| `fl_excluir_exposicao_observada` | bool | inverso lógico de `sem_exposicao_observada_2007_2019` |
| `fl_excluir_universo_incompleto` | bool | inverso lógico de `presente_nos_13_anos_do_universo` |
| `fl_excluir_fase_ii` | bool | idêntica a `fl_municipio_fase_ii` |
| `fl_elegivel_controle_candidato` | bool | conjunção lógica da seção 5 |
| `motivos_exclusao` | string, `;`-separado | todos os motivos aplicáveis; `""` se elegível |

### Pool filtrado

`data/processed/pool_candidato_controles_sem_exposicao_2007_2019.parquet`
— seleção exata das linhas do cadastro completo com
`fl_elegivel_controle_candidato=True`, mesmas colunas, sem transformação
adicional.

### Diagnóstico resumido

`outputs/diagnostics/resumo_pool_candidato_controles.csv` — pares
`metrica,valor` com o funil completo da seção 8 e as sobreposições da
seção 9.

## 15. Validações executadas

Ver `validate_resumo_nacional`, `validate_fase_ii_municipios`,
`validate_fase_ii_subset_universo`, `validate_cadastro_elegibilidade` e
`validate_pool_filtrado` em
[`src/constroi_pool_candidato_controles.py`](../../src/constroi_pool_candidato_controles.py).
Toda violação levanta `ValueError` com exemplos concretos — nenhuma
correção é feita silenciosamente.
