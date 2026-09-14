# Especificação Técnica — Painel CEMPRE Município-Ano (2007–2019)

## 1. Finalidade e escopo

Esta especificação define a implementação futura, reproduzível, do painel
municipal CEMPRE 2007–2019. Não implementa código, não extrai a série, não
produz dados, não faz merge com tratamento e não estima efeitos. A
justificativa metodológica está em
[`AUDITORIA_DISPONIBILIDADE_CEMPRE.md`](AUDITORIA_DISPONIBILIDADE_CEMPRE.md).

A unidade é município-ano. O gate vigente é `APTO_COM_RESSALVAS`: há
viabilidade técnica, não identificação causal validada nem painel analítico
pronto.

A implementação futura é faseada: nenhuma extração nacional 2007–2019
pode começar antes de um piloto técnico dirigido em pequena escala (seção
3 e seção 12). A ordem dos gates é `PILOTO_TECNICO_APROVADO` →
`PAINEL_TECNICO_CONSTRUIDO` → `PAINEL_ANALITICO_APROVADO` (seção 13).

## 2. Fonte e variáveis confirmadas

Fonte: IBGE/SIDRA/CEMPRE, Tabela 1685 (2006–2021); uso: 2007–2019; nível:
N6; chave: código municipal IBGE com sete dígitos. A API SIDRA é a via
principal. `V` é texto e deve ser preservado. Não há classificação extra
para totais municipais.

Os metadados oficiais consultados em 2026-09-14 confirmam:

| Código | Variável | Unidade | Papel |
|---:|---|---|---|
| 706 | Número de unidades locais | Unidades | secundário |
| 707 | Pessoal ocupado total | Pessoas | secundário |
| 708 | Pessoal ocupado assalariado | Pessoas | primário |
| 5944 | Pessoal assalariado médio | Pessoas | auxiliar |
| 662 | Salários e outras remunerações | Mil Reais | auxiliar/secundário |
| 1606 | Salário médio mensal | Salários mínimos | opcional/diagnóstica |
| 10143 | Salário médio mensal em reais | Reais | secundário nominal, obrigatória |

O outcome 708 é interpretado somente no universo CEMPRE; não representa
emprego informal da economia municipal, MEI ou todo emprego municipal.
O salário em reais será preservado nominal; deflator é decisão posterior.

A variável 1606 (salário médio em salários mínimos) é **opcional,
diagnóstica e alternativa**: não é requisito obrigatório do painel
técnico e sua ausência não impede `PAINEL_TECNICO_CONSTRUIDO`. A variável
salarial obrigatória para a construção básica é a 10143 (salário médio
mensal em reais). Salário em salários mínimos não substitui
deflacionamento do valor nominal em reais — são tratamentos distintos.

## 3. Fases do processo

O processo tem três gates sucessivos, cada um com critérios próprios
(detalhados na seção 13):

1. **`PILOTO_TECNICO_APROVADO`** — Fase 0, extração dirigida em pequena
   escala (seção 12), valida contrato real da API, parser, símbolos,
   reconciliação territorial e mecânica de requests/cache antes de
   qualquer extração nacional.
2. **`PAINEL_TECNICO_CONSTRUIDO`** — extração completa 2007–2019, todas
   as camadas técnicas (seções 4 a 11) executadas e validadas.
3. **`PAINEL_ANALITICO_APROVADO`** — depende de avaliação humana adicional
   (sigilo, cobertura, território, transições RAIS/eSocial, adequação do
   outcome, deflator) e não é declarado por este documento nem por
   nenhuma etapa técnica isolada.

Nenhum desses gates é aprovado por esta especificação. A extração
nacional completa (seções 4–11) só pode começar depois de
`PILOTO_TECNICO_APROVADO`.

## 4. Arquitetura

```text
API SIDRA → JSON raw
          → long normalizada da fonte
          → reconciliação / enriquecimento territorial
          → validações
          → processada/wide
          → diagnósticos → futura análise
```

| Camada | Finalidade | Saída contratada |
|---|---|---|
| API | obter dados e metadados por request | resposta bruta e log |
| JSON raw | preservar a resposta exatamente como recebida | arquivo por request |
| Long normalizada da fonte | traduzir o raw para linhas tipadas, sem enriquecimento externo | município-ano-variável, com `valor_bruto` e `status_valor_api` |
| Reconciliação/enriquecimento territorial | cruzar com calendário município-ano e derivar `status_territorial` | long enriquecida, com origem do dado preservada |
| Validações | bloquear falhas de schema/chave/cobertura | relatório de aprovação |
| Processada/wide | consumo futuro município-ano | valores e status por medida |
| Diagnósticos | quantificar cobertura, símbolos e quebras | CSVs auditáveis |
| Análise futura | decisões metodológicas posteriores | fora do escopo |

A separação entre "long normalizada da fonte" e "reconciliação/
enriquecimento territorial" é conceitual, não necessariamente física: não
é obrigatório gerar um Parquet por etapa. O que não é permitido é
apresentar informação territorial derivada (por exemplo,
`status_territorial`) como se fosse um atributo original retornado pela
API — a distinção entre o que a fonte disse e o que o projeto inferiu do
calendário deve permanecer rastreável em todo momento.

A long é canônica para recuperação. A wide é sempre derivada; não substitui
as respostas brutas nem a long. Esta etapa não realiza merge causal com o
cadastro de tratamento ou o pool de controles.

## 5. Schema raw normalizada / long

**Chave de negócio canônica**: `(codigo_municipio_ibge, ano,
codigo_variavel_sidra)`. Essa é a identidade do dado, não uma candidata.

`request_id` é somente proveniência (qual lote de extração produziu a
linha) e não integra a chave de negócio. Se a mesma chave de negócio
aparecer associada a `request_id` diferentes (reextração, sobreposição
entre lotes ano×UF×variáveis, reprocessamento), isso é tratado como
duplicidade/sobreposição do processo de extração: o pipeline deve
detectar a sobreposição, verificar consistência entre as ocorrências
(mesmo `valor_bruto` e mesmo `status_valor_api`) e resolver
deterministicamente qual registro é retido, nunca legitimar as duas
linhas como observações independentes só porque vieram de requests
diferentes.

| Campo | Tipo | Regra |
|---|---|---|
| `codigo_municipio_ibge` | string[7] | dígitos, preservar zeros; chave |
| `ano` | inteiro | 2007–2019; chave |
| `codigo_variavel_sidra` | inteiro | conjunto da seção 2; chave |
| `municipio_fonte`, `uf_fonte` | string | rótulos, não chaves |
| `nome_variavel`, `unidade` | string | conferir metadados |
| `valor_bruto` | string | `V` exatamente recebido; obrigatório; nunca descartado |
| `valor_numerico` | decimal nullable | preenchido quando `status_valor_api` estiver em `observado`, `zero_real`, `zero_arredondado` ou `zero_arredondado_negativo` (as três classes de zero recebem `valor_numerico = 0`); nulo para `sigilo`, `nao_aplicavel`, `indisponivel` e `desconhecido`; independente de `status_territorial` |
| `status_valor_api` | string controlada | leitura direta de `V`, sem cruzar calendário (seção 6) |
| `status_territorial` | string controlada | derivado do calendário território município-ano (seção 6) |
| `status_analitico` | string controlada, nullable | campo **derivado**, combina os dois status acima (seção 6) |
| `fonte_tabela` | inteiro | 1685 |
| `request_id` | string | somente proveniência do lote; não é chave |
| `data_extracao` | timestamp com fuso | resposta |
| `hash_resposta_raw` | SHA-256 | integridade |
| `versao_metadados` | string/hash | proveniência |
| `observacao_status` | string nullable | refinamento/erro |

`valor_bruto` nunca será descartado. `status_valor_api` e
`status_territorial` são preservados separadamente e nenhum dos dois
apaga ou substitui o estado original retornado pela API.

## 6. Taxonomia e parsing de valores

Três campos distintos, que não podem ser fundidos:

- **`status_valor_api`** — leitura direta de `V`, antes de qualquer
  cruzamento com o calendário territorial.
- **`status_territorial`** — resultado do cruzamento da chave
  `(codigo_municipio_ibge, ano)` com o calendário território município-ano
  (seção 7); não depende do valor de `V`.
- **`status_analitico`** — campo **derivado**, opcional para consumo,
  que combina os dois anteriores em uma leitura de conveniência para a
  wide/diagnósticos (seção 8).

### 6.1 `status_valor_api`

| Status | Regra | `valor_numerico` |
|---|---|---|
| `observado` | inteiro/decimal válido não-zero | decimal |
| `zero_real` | `-` | 0 |
| `zero_arredondado` | `0`, `0,0`, `0,00` (zero por arredondamento de valor originalmente positivo) | 0, com distinção |
| `zero_arredondado_negativo` | `-0`, `-0,0`, `-0,00` (zero por arredondamento de valor originalmente negativo) | 0, com distinção |
| `sigilo` | `x` | nulo |
| `nao_aplicavel` | `..` | nulo |
| `indisponivel` | `...` | nulo |
| `desconhecido` | símbolo/formato não previsto | nulo |

`-0`, `-0,0` e `-0,00` são estados documentados explicitamente pela fonte
(ver `AUDITORIA_DISPONIBILIDADE_CEMPRE.md`, seção 6.1) e não podem cair em
`desconhecido`: o parser deve reconhecê-los como uma terceira classe de
zero, distinta de `zero_real` e de `zero_arredondado` (positivo). As três
classes de zero (`zero_real`, `zero_arredondado`,
`zero_arredondado_negativo`) permanecem semanticamente distintas mesmo
recebendo `valor_numerico = 0`.

Algoritmo conceitual: preservar `V`; remover somente espaços externos;
classificar símbolos antes de converter; aceitar inteiros e decimais após
normalização local explícita e não ambígua; converter apenas estados
numéricos. `x`, `..` e `...` não serão imputados. Símbolo desconhecido
será preservado e classificado como `desconhecido`, o que bloqueia o gate
técnico — essa escolha impede conversão silenciosa em NA.

### 6.2 `status_territorial`

| Status | Regra |
|---|---|
| `existia_no_ano` | calendário confirma que o município existia na chave `(codigo_municipio_ibge, ano)` |
| `nao_existia_no_ano` | calendário indica que o município ainda não existia (ex.: Pescaria Brava/SC em 2007) |
| `indeterminado` | calendário territorial ainda não cruzado ou sem cobertura para a chave |

"Município ainda não existia" não é, por si só, uma anomalia: é um
estado territorial esperado e não deve ser reportado como incoerência.

### 6.3 `status_analitico` (derivado) e `incompatibilidade_territorial`

`status_analitico` é opcional e serve apenas para leitura combinada; não
é fonte primária de verdade — quem precisa da distinção completa deve
consultar `status_valor_api` e `status_territorial` separadamente.

`incompatibilidade_territorial` é reservado para uma **divergência real**
entre a API e o calendário, não para o caso esperado de município
inexistente com `V="..."`. Exemplos de incompatibilidade real:

- a API retorna valor numérico (`status_valor_api = observado` ou uma
  classe de zero) para um município que o calendário indica como
  `nao_existia_no_ano`;
- código territorial retornado pela API incompatível com o cadastro
  oficial de códigos;
- outra inconsistência lógica entre o que a API afirma e o que o
  calendário afirma.

O caso já auditado de Pescaria Brava/SC (4212650), 2007, `V="..."`,
`status_valor_api = indisponivel` e `status_territorial =
nao_existia_no_ano`, é o comportamento esperado — **não** é
`incompatibilidade_territorial`.

## 7. Calendário territorial

Será necessária tabela oficial IBGE município-ano, com fonte, versão e
hash no manifesto. Recomenda-se série histórica oficial de malhas/códigos
com vigência explícita; se indisponível, consolidar arquivos anuais
oficiais em uma tabela auditável.

Schema: `codigo_municipio_ibge` (string[7]), `ano` (inteiro),
`municipio_existia_no_ano` (boolean), `fonte_territorial`,
`versao_fonte`, `data_vigencia_inicio`, `data_vigencia_fim` e
`observacao_territorial`. Esta tabela alimenta exclusivamente
`status_territorial` (seção 6.2); não é escrita nem inferida a partir de
`valor_bruto` ou `status_valor_api`.

Criação, extinção, fusão ou alteração de código são eventos territoriais,
tratados pelo calendário, não problemas resolvidos por nome. O caso
Pescaria Brava/SC (4212650) em 2007, com `V="..."`, ilustra que o símbolo
isolado não prova sua própria causa — só o cruzamento com o calendário
permite atribuir `status_territorial`.

## 8. Processada / wide

Chave: `(codigo_municipio_ibge, ano)`. Colunas numéricas:
`qt_unidades_locais`, `pessoal_ocupado_total`,
`pessoal_ocupado_assalariado`, `pessoal_assalariado_medio`,
`salarios_remuneracoes_mil_reais_nominal` e
`salario_medio_reais_nominal`. `salario_medio_salarios_minimos` (1606) é
coluna **opcional/diagnóstica**: sua ausência não bloqueia
`PAINEL_TECNICO_CONSTRUIDO`.

Para cada medida haverá `status_valor_api_<medida>`,
`status_territorial` (única por linha, não por medida, pois depende só
de `codigo_municipio_ibge`/`ano`) e, quando útil,
`status_analitico_<medida>` derivado. Também `municipio`, `uf_codigo`,
`fonte_tabela`, `data_extracao_maxima` e `versao_metadados`. A wide nunca
terá somente números. Transformação deflacionada futura será nova coluna
analítica e não altera o nominal.

## 9. Extração, rede e cache

A segmentação de requests por **ano × UF × grupo de variáveis** é a
**estratégia inicial candidata**, ainda a validar pelo piloto técnico
(seção 12). Começar com as sete variáveis em grupo reduz chamadas;
dividir por variável apenas se o lote falhar ou ficar grande. Nenhum
limite formal de API é presumido antes da Fase 0. Se o piloto mostrar que
chamadas maiores ou menores funcionam melhor, a segmentação pode ser
ajustada, desde que preserve idempotência, auditabilidade, retomada e
cobertura verificável.

Cada request registra ID, URL/parâmetros, tentativa, início/fim, HTTP,
tamanho, hash e resultado. Timeout, retries limitados e backoff exponencial
com teto serão configuráveis e constarão no manifesto. Só HTTP 200 com JSON
no schema esperado é sucesso. Resposta vazia, JSON inesperado, schema
alterado ou falha persistente tornam o lote obrigatório falho; extração
com falha não é completa.

Persistir ambos: JSON bruto compactado por request e long normalizada
particionada por ano. Convenção:
`tabela_1685__ano_YYYY__uf_UF__vars_IDS__request_HASH.json.gz`.
Essa combinação permite reprocessar sem API e evita arquivo por célula.

Antes de qualquer extração que produza raw, cache, interim ou Parquet, a
futura implementação deve conferir as regras vigentes de `.gitignore` do
repositório para evitar inclusão acidental desses artefatos no Git. Este
documento não altera `.gitignore` e não presume que tudo deva ser
ignorado — apenas registra o requisito operacional de checagem prévia.

## 10. Proveniência, artefatos e script futuro

O manifesto `data/raw/ibge/cempre/source_manifest.json` deverá registrar
IBGE/CEMPRE, Tabela 1685, endpoint, instante, N6, anos, variáveis,
requests/sucessos/falhas, parâmetros de rede, hash/versão do script, commit
Git, metadados e hash, contagem de registros e hashes dos artefatos.

Artefatos futuros, não criados agora:

- `data/raw/ibge/cempre/fixtures/` — fixture(s) pequenas e versionadas da
  resposta real da API, congeladas na Fase 0 (seção 12);
- `data/raw/ibge/cempre/requests/`;
- `data/interim/cempre_long_2007_2019.parquet`;
- `data/processed/painel_cempre_municipio_ano_2007_2019.parquet`;
- `outputs/diagnostics/cempre_cobertura_por_ano.csv`;
- `outputs/diagnostics/cempre_status_valor.csv`;
- `outputs/diagnostics/cempre_sigilo_por_ano_uf.csv`;
- `outputs/diagnostics/cempre_transicao_2008_2009.csv`;
- `outputs/diagnostics/cempre_transicao_2018_2019.csv`.

O futuro `src/constroi_painel_cempre.py` terá funções diretas:
`fetch_metadata`, `build_requests`, `fetch_request`,
`parse_sidra_value`, `load_calendar_territorial`, `normalize_long`,
`reconcile_territorial`, `validate_long`, `build_wide`, `validate_wide`,
`build_diagnostics` e `write_manifest`. Não fará merge causal ou
estimação.

## 11. Validações e diagnósticos

Validar código com sete dígitos, ano na janela, variável prevista,
unicidade da chave de negócio `(codigo_municipio_ibge, ano,
codigo_variavel_sidra)` na long, ausência de duplicidade/sobreposição
entre `request_id` (seção 5), aderência de nomes e unidades aos
metadados, ausência de lotes esperados e reconciliação long→wide.

Por ano, reportar municípios retornados, oficialmente existentes, células
numéricas/especiais, combinações esperadas ausentes e divergências
territoriais (`incompatibilidade_territorial`, seção 6.3, distinta de
`nao_existia_no_ano`). Não exigir 5.570 municípios em todos os anos.
Produzir `ano × variável × status_valor_api × n × percentual` e, quando
disponível, UF. Medir `x` por ano/variável/UF e demais estados especiais;
não imputar sigilo.

**Validações cruzadas** (diagnósticas, aplicadas somente quando todas as
células envolvidas têm `status_valor_api = observado` ou uma classe de
zero, isto é, valor numérico observado):

- `pessoal_ocupado_assalariado <= pessoal_ocupado_total`;
- contagens de pessoas (`pessoal_ocupado_total`,
  `pessoal_ocupado_assalariado`, `pessoal_assalariado_medio`) `>= 0`;
- `qt_unidades_locais >= 0`;
- `salarios_remuneracoes_mil_reais_nominal >= 0` quando
  conceitualmente aplicável;
- `salario_medio_reais_nominal >= 0`;
- checagem aproximada de coerência entre `salarios_remuneracoes_mil_reais_nominal`,
  `pessoal_assalariado_medio` e `salario_medio_reais_nominal`, se as
  definições e unidades oficiais permitirem uma relação testável.

Essas checagens são diagnósticas: não corrigem o dado automaticamente.
Diferenças plausíveis de arredondamento são toleradas quando
justificáveis; incoerências grandes ou logicamente impossíveis (ex.:
assalariado maior que total) devem ser reportadas, não silenciadas nem
corrigidas.

Adicionar `regime_rais` e `flag_transicao_rais_2008_2009`.
Diagnosticar variações absolutas/percentuais 2008→2009 versus 2007→2008 e
2009→2010, com agregados, distribuição, outliers e, se simples, UF. O
efeito nacional aproximado de 0,32% não é correção municipal.

Adicionar `flag_transicao_esocial_2018_2019`; diagnosticar 2017→2018,
2018→2019 e, se disponível depois, 2019→2020 apenas externamente. Não
excluir 2019 automaticamente.

## 12. Fase 0 — Piloto técnico dirigido

Objetivo: validar em pequena escala, antes de qualquer extração nacional
2007–2019, os elementos que a arquitetura completa (seções 4–11)
pressupõe:

- contrato real da API SIDRA e campos efetivamente retornados;
- comportamento de `V` (incluindo os símbolos e as classes de zero da
  seção 6.1);
- parsing e schema da long normalizada da fonte;
- reconciliação territorial (seção 6.2/7), incluindo o caso
  `nao_existia_no_ano` versus `incompatibilidade_territorial`;
- mecânica de requests, retries e cache (seção 9);
- validações básicas (seção 11) sobre um subconjunto pequeno.

### 12.1 Contexto de teste

O piloto deve cobrir, no mínimo, contextos capazes de testar os riscos já
identificados na auditoria:

- os anos 2008 e 2009 (transição de apropriação RAIS);
- os anos 2018 e 2019 (transição de critério/eSocial);
- um município comum;
- um município pequeno;
- um município criado posteriormente (ex.: Pescaria Brava/SC, 4212650);
- uma UF pequena ou subconjunto territorial controlado.

Os exemplos já usados na auditoria (Serra da Saudade/MG, Pescaria
Brava/SC, os 15 municípios de Roraima) são referência direta e podem ser
reaproveitados ou ajustados pela implementação futura, desde que o
conjunto escolhido continue testando os mesmos riscos.

### 12.2 Fixture do contrato da API

A Fase 0 deve congelar uma pequena resposta real da API SIDRA como
fixture versionada (`data/raw/ibge/cempre/fixtures/`), documentando os
campos efetivamente usados pelo parser — os equivalentes a `V`, código
territorial, nome territorial, período, variável, unidade e demais campos
necessários. O schema não deve ser presumido apenas por memória.

Os testes principais de parser/schema devem rodar contra essa fixture
pequena e versionada (ou mecanismo equivalente adequado ao repositório).
A API ao vivo é usada somente em smoke/integration test controlado, não
como dependência permanente dos testes unitários.

### 12.3 Testes futuros associados

Testes unitários: inteiro, decimal, `-`, `0`, `0,0`, `0,00`, `-0`,
`-0,0`, `-0,00`, `x`, `..`, `...`, símbolo desconhecido, código inválido,
município inexistente, município existente com `...`, duplicidade de
chave de negócio entre `request_id` diferentes, variável/ano inválidos.

Testes de integração: API vazia, schema alterado, retry bem-sucedido,
falha persistente, lote duplicado e lote ausente — usando a fixture
congelada (seção 12.2) ou endpoint de teste controlado, sem baixar a
série completa.

## 13. Gates

### 13.1 `PILOTO_TECNICO_APROVADO`

Exige, no mínimo:

- contrato/schema real da API confirmado;
- fixture da Fase 0 preservada e versionada;
- parser funcionando sobre a fixture e sobre os casos da seção 12.1;
- todos os símbolos conhecidos tratados, incluindo as três classes de
  zero (seção 6.1);
- reconciliação territorial testada, incluindo distinção entre
  `nao_existia_no_ano` e `incompatibilidade_territorial`;
- mecânica de requests/retries/cache funcionando nos contextos da seção
  12.1;
- nenhuma anomalia técnica bloqueante identificada no piloto.

A extração nacional completa (seções 4–11) só pode começar depois deste
gate.

### 13.2 `PAINEL_TECNICO_CONSTRUIDO`

Exige todos os requests concluídos, raw preservada, parsing aprovado,
calendário reconciliado, chave de negócio única, cobertura contabilizada,
estados classificados (`status_valor_api`, `status_territorial` e,
quando aplicável, `status_analitico`), validações cruzadas (seção 11)
executadas e reportadas, manifesto/diagnósticos e testes aprovados. A
ausência da variável 1606 não impede este gate.

### 13.3 `PAINEL_ANALITICO_APROVADO`

Exige adicionalmente decisão humana sobre sigilo, território, transições
2008→2009 e 2018→2019, adequação substantiva do outcome e
salários/deflator. Nenhum desses gates é declarado aprovado por esta
especificação.

Permanecem abertas: fonte/política territorial, sigilo, deflator,
interpretação das quebras, população causal, comparação, antecipação e
spillover. Depois do painel técnico, a cobertura será avaliada nos 147
Fase II, 129 candidatos e 4.964 candidatos estruturais, sem alterar
retroativamente o cadastro causal. O primeiro notebook futuro sugerido é
`notebooks/XX_eda_cempre_cobertura_e_outcomes.ipynb`, restrito a
cobertura, estados especiais, distribuições e transições; sem matching,
event study, ATT ou seleção de controles.
