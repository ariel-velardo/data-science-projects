# Auditoria da Construção do Painel do Censo Escolar (2007–2019)

## 1. Status e escopo

Fechamento documental da etapa que construiu o painel de presença federal
de Educação Profissional e Tecnológica (EPT) a partir dos microdados do
Censo Escolar da Educação Básica.

- Rotina: [`src/constroi_painel_censo_escolar.py`](../../src/constroi_painel_censo_escolar.py).
- Nenhum ano de tratamento foi atribuído. Nenhum efeito causal foi
  estimado. Nenhum matching ou coorte foi definido nesta etapa
  (ver seção 11).
- Esta auditoria **não reprocessou a base**: validou os três Parquets já
  produzidos e conferiu apenas os bytes iniciais e uma pequena amostra
  acentuada dos CSVs de origem (seção 10).

## 2. Fontes locais utilizadas

Todos os insumos são locais; nada foi baixado nesta etapa.

| Insumo | Caminho | Observação |
|---|---|---|
| Microdados do Censo Escolar 2007–2019 (13 ZIPs) | `data/raw/inep/censo_escolar/microdados_censo_escolar_{ano}.zip` | Um CSV de escola por ZIP: `microdados_ed_basica_{ano}/dados/microdados_ed_basica_{ano}.csv` |
| Manifesto de origem | `data/raw/inep/censo_escolar/source_manifest.json` | Fonte: INEP — Microdados do Censo Escolar da Educação Básica. URL de índice e SHA-256 de cada ZIP registrados no manifesto. Período declarado: 2007–2019. |
| Lista de municípios da Fase II | `data/processed/fase_ii_municipios.parquet` | 147 municípios, `codigo_municipio_ibge` único; produzida e auditada em [`docs/institutional/AUDITORIA_LISTA_FASE_II.md`](../institutional/AUDITORIA_LISTA_FASE_II.md) |

O manifesto (`source_manifest.json`) foi gravado com BOM UTF-8; os CSVs do
Censo, não (contraste discutido na seção 10).

## 3. Período

2007 a 2019, inclusive — 13 anos. Confirmado nas três tabelas: o conjunto
de valores de `NU_ANO_CENSO` é exatamente `{2007, …, 2019}`.

## 4. Leitura direta dos ZIPs

Os CSVs **não são extraídos para disco**. Para cada ano:

1. Abre-se o ZIP com `zipfile`, localiza-se o único `.csv` interno
   (asserção `len(csvs) == 1`).
2. Lêem-se os bytes do CSV em memória (`z.read`) e passa-se um
   `io.BytesIO` diretamente ao `pandas.read_csv`.
3. Leitura em blocos (`chunksize=50_000`), mantendo em memória apenas as
   linhas federais de cada bloco.
4. `sep=";"`, `encoding="latin-1"` (ver seção 10),
   `encoding_errors="replace"` como rede de segurança,
   `low_memory=False`.

Apenas `pandas` + `pyarrow` + biblioteca padrão. Sem DuckDB, sem Polars.

## 5. Colunas selecionadas (`usecols`)

19 colunas lidas de cada CSV (layout harmonizado do INEP, 370 colunas em
todos os anos — as 19 estão presentes em 2007, 2013 e 2019):

| Grupo | Colunas |
|---|---|
| Identificação | `NU_ANO_CENSO`, `CO_ENTIDADE`, `NO_ENTIDADE`, `CO_MUNICIPIO`, `NO_MUNICIPIO`, `SG_UF`, `CO_UF` |
| Classificação | `TP_DEPENDENCIA`, `TP_SITUACAO_FUNCIONAMENTO`, `TP_LOCALIZACAO`, `TP_LOCALIZACAO_DIFERENCIADA` |
| Oferta EPT (flags) | `IN_PROF`, `IN_PROF_TEC` |
| Volumes EPT | `QT_MAT_PROF`, `QT_MAT_PROF_TEC`, `QT_TUR_PROF`, `QT_TUR_PROF_TEC`, `QT_DOC_PROF`, `QT_DOC_PROF_TEC` |

Códigos (`CO_ENTIDADE`, `CO_MUNICIPIO`, `CO_UF`, `NU_ANO_CENSO`) lidos como
texto e normalizados por `zfill` (8 / 7 / 2 dígitos) para preservar zeros
à esquerda. Demais colunas convertidas com `pd.to_numeric(errors="coerce")`.

## 6. Critérios (definições operacionais)

Aplicados no nível escola-ano; as contagens município-ano e o painel são
agregações dessas flags.

| Flag | Definição | Comentário |
|---|---|---|
| escola federal | `TP_DEPENDENCIA == 1` | Filtro aplicado na leitura; a tabela escola-ano contém **apenas** federais |
| `fl_em_atividade` | `TP_SITUACAO_FUNCIONAMENTO == 1` | Escola em funcionamento no ano |
| `fl_oferta_ept` | `IN_PROF == 1` | Oferta de educação profissional. **Independente da situação de funcionamento** |
| `fl_oferta_ept_tecnica` | `IN_PROF_TEC == 1` | Oferta de curso técnico |
| `fl_presenca_federal_ept_ativa` | `TP_DEPENDENCIA == 1` **e** `TP_SITUACAO_FUNCIONAMENTO == 1` **e** `IN_PROF == 1` | Presença federal EPT efetivamente em atividade no ano |

### 6.1 Relações de contenção — correção conceitual desta etapa

As relações de contenção **corretas** entre os conjuntos são:

- `ept_ativa ⊆ ept`
- `ept_ativa ⊆ em_atividade`
- `ept ⊆ escolas_federais`
- `em_atividade ⊆ escolas_federais`

A relação **`ept ⊆ em_atividade` NÃO é obrigatória** e não deve ser
tratada como invariante. Uma escola federal pode ter registro de oferta
de EPT (`IN_PROF == 1`) num ano em que **não** está em atividade
(`TP_SITUACAO_FUNCIONAMENTO ≠ 1`) — p. ex. unidade paralisada ou extinta
com cadastro de oferta ainda preenchido. Por construção, `ept_ativa` já
exige atividade; `ept` sozinho não.

Situação nesta base:

- **No código:** a rotina **não contém** validação nem comentário que
  suponha `ept ⊆ em_atividade`. `fl_oferta_ept` é definido apenas por
  `IN_PROF == 1`, sem referência a `TP_SITUACAO_FUNCIONAMENTO`. Nenhuma
  função `validate_*` compara `qt_escolas_com_ept` com
  `qt_escolas_em_atividade`. **Nenhuma correção de código foi necessária.**
- **No relatório de revisão anterior:** o resumo descreveu a coerência de
  aninhamento como a cadeia `ept_ativa ⊆ ept ⊆ em_atividade`, cujo elo
  intermediário (`ept ⊆ em_atividade`) está conceitualmente incorreto
  como invariante. Essa afirmação **fica retificada por este documento**.
  A verificação efetivamente executada na bateria consolidada testou
  `ept_ativa ⊆ ept`, `ept_ativa ⊆ em_atividade`, `ept ⊆ federais` e
  `em_atividade ⊆ federais` — todas sem violação — e **não** testou
  `ept ⊆ em_atividade`; portanto nenhum resultado numérico da bateria
  depende da relação incorreta.

Observação adicional: `ept_tecnica ⊆ ept` também não é imposta pelo
código, mas se sustenta empiricamente (0 violações em 6.781 linhas),
coerente com a hierarquia do INEP (`IN_PROF_TEC == 1 ⇒ IN_PROF == 1`).

## 7. Parquets produzidos e dimensões

| Parquet | Caminho | Linhas | Colunas | Chave |
|---|---|---|---|---|
| escola-ano | `data/interim/censo_escolas_federais_2007_2019.parquet` | 6.781 | 23 | `(NU_ANO_CENSO, CO_ENTIDADE)` |
| município-ano | `data/interim/censo_federal_municipio_ano_2007_2019.parquet` | 5.192 | 16 | `(NU_ANO_CENSO, CO_MUNICIPIO)` |
| painel Fase II | `data/processed/painel_presenca_federal_ept_fase_ii_2007_2019.parquet` | 1.911 | 19 | `(CO_MUNICIPIO, NU_ANO_CENSO)` |

- A tabela escola-ano acrescenta às 19 colunas-fonte as 4 flags derivadas
  (`fl_em_atividade`, `fl_oferta_ept`, `fl_oferta_ept_tecnica`,
  `fl_presenca_federal_ept_ativa`).
- A tabela município-ano tem 5 identificadores + 11 colunas `qt_*`
  (5 contagens de escolas + 6 somas de matrículas/turmas/docentes EPT).
- O painel é a grade completa **147 municípios × 13 anos = 1.911 linhas**,
  com `left join` sobre a município-ano; anos sem escola federal ficam
  com contagens 0 e flags `False`. Traz 5 identificadores + 11 `qt_*` +
  3 flags de presença (`fl_presenca_federal`, `fl_presenca_federal_ept`,
  `fl_presenca_federal_ept_ativa`).

Cobertura por ano (escolas federais na tabela escola-ano):

| Ano | 2007 | 2008 | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Escolas | 235 | 271 | 302 | 354 | 470 | 518 | 523 | 561 | 647 | 703 | 728 | 752 | 717 |

## 8. Validações executadas

Funções `validate_escola_ano`, `validate_municipio_ano`,
`validate_panel_fase_ii` e `audit_contradictions` da própria rotina, mais
a bateria consolidada da revisão. Resultado: **0 erros**.

| Validação | Resultado |
|---|---|
| `NU_ANO_CENSO` == {2007…2019} nas 3 tabelas | OK (13 anos) |
| Unicidade `(NU_ANO_CENSO, CO_ENTIDADE)` — escola-ano | 0 duplicatas |
| Unicidade `(NU_ANO_CENSO, CO_MUNICIPIO)` — município-ano | 0 duplicatas |
| Unicidade `(CO_MUNICIPIO, NU_ANO_CENSO)` — painel | 0 duplicatas |
| Comprimento de códigos (`CO_ENTIDADE`=8, `CO_MUNICIPIO`=7, `CO_UF`=2) | 0 violações |
| `TP_DEPENDENCIA` na escola-ano | exclusivamente `{1}`; 0 não-federais |
| Nulos em identificadores (`CO_ENTIDADE`, `CO_MUNICIPIO`, `NU_ANO_CENSO`; painel: + `NO_MUNICIPIO`, `SG_UF`, `CO_UF`) | 0 nulos |
| Contagens `qt_*` negativas (município-ano e painel) | 0 |
| Reconciliação: Σ `qt_escolas_federais` (município-ano) vs. nº linhas escola-ano | 6.781 = 6.781; batimento por ano em ativas / EPT / EPT-ativa |
| Aninhamento `em_atividade ⊆ federais`, `ept ⊆ federais`, `ept_ativa ⊆ ept`, `ept_ativa ⊆ em_atividade`, `ept_tecnica ⊆ ept` | 0 violações (ver 6.1 — `ept ⊆ em_atividade` **não** é exigida nem testada) |
| Coerência flag ↔ contagem no painel (`fl_* == (qt_* > 0)`) | OK nas 3 flags |
| Implicações no painel: `ept_ativa ⇒ ept ⇒ presença_federal` | OK |
| Linhas do painel sem escola federal (497) com todas as flags `False` | OK |
| `CO_UF == CO_MUNICIPIO[:2]` no painel | sempre |
| Contradições `IN_PROF` × quantidades EPT (`audit_contradictions`) | 0 |
| Mojibake (U+FFFD) em `NO_MUNICIPIO` / `NO_ENTIDADE` nas 3 tabelas | 0 (após correção de encoding — seção 10) |
| Colunas de `usecols` presentes nos headers 2007 / 2013 / 2019 | 19/19 |

## 9. Municípios da Fase II e combinações município-ano

- **147 municípios** distintos no painel — conjunto **idêntico** ao de
  `fase_ii_municipios.parquet` (0 faltando, 0 sobrando).
- Todos os 147 presentes em **todos os 13 anos**.
- **1.911 combinações município-ano** = 147 × 13 (grade completa, sem
  buracos e sem duplicatas).
- Origem do número 147: das 150 cidades-polo do Anexo I da Chamada Pública
  MEC/SETEC nº 001/2007, as 4 linhas do Distrito Federal colapsam em 1
  código IBGE (Brasília), reduzindo o total líquido para 147. A divergência
  entre 147 e o "144" de documentos congelados permanece aberta, conforme
  [`AUDITORIA_LISTA_FASE_II.md`](../institutional/AUDITORIA_LISTA_FASE_II.md)
  (seção 9) — não é objeto desta etapa.

## 10. Correção de encoding e reconciliação BOM / UTF-8 / Latin-1

### 10.1 O problema

A rotina lia os CSVs com `encoding="utf-8-sig"` — valor que estava
**escrito no código como suposição, nunca verificado contra os bytes**.
Com `encoding_errors="replace"`, todo byte de acento virava o caractere
de substituição `�` (U+FFFD). Impacto medido nos Parquets anteriores:

| Tabela | Coluna | Linhas com `�` (antes) |
|---|---|---|
| escola-ano | `NO_MUNICIPIO` | 2.532 / 6.781 |
| escola-ano | `NO_ENTIDADE` | 165 |
| município-ano | `NO_MUNICIPIO` | 2.010 / 5.192 |
| painel Fase II | `NO_MUNICIPIO` | 512 / 1.911 |

### 10.2 A correção

Uma linha em [`constroi_painel_censo_escolar.py`](../../src/constroi_painel_censo_escolar.py):
`encoding="utf-8-sig"` → `encoding="latin-1"`. `encoding_errors="replace"`
mantido (inócuo em latin-1, pois todo byte 0x00–0xFF tem mapeamento).
Os três Parquets foram regenerados a partir dos ZIPs locais; após a
correção, **0 ocorrências de `�`** em qualquer coluna de nome, com
acentuação correta (`São Gabriel da Cachoeira`, `Belém`,
`CENTRO FEDERAL DE EDUC. TECNOLÓGICA DO AMAZONAS`).

### 10.3 Por que `utf-8-sig` "parecia" plausível e por que Latin-1 é o certo

Verificação feita **apenas sobre os bytes iniciais e uma amostra
acentuada** (sem reprocessar a base):

1. **Sem BOM.** Os primeiros 16 bytes de cada CSV (2007, 2013, 2019) são
   `4e 55 5f 41 4e 4f 5f 43 45 4e 53 4f 3b 4e 4f 5f` — o texto ASCII
   `"NU_ANO_CENSO;NO_"`. Não há BOM UTF-8 (`EF BB BF`) nem BOM UTF-16
   (`FF FE` / `FE FF`). Logo o sufixo `-sig` de `utf-8-sig` **não tinha
   nenhum BOM para remover** e o codec se comportava exatamente como
   `utf-8` puro.

2. **O cabeçalho engana.** A linha de cabeçalho e o começo da primeira
   linha de dados são inteiramente ASCII. Uma amostra pequena (≈4 KB)
   **decodifica como UTF-8 sem erro** — foi o que sustentou a suposição
   incorreta.

3. **A primeira falha real.** Lendo além do cabeçalho, o primeiro byte
   não-ASCII aparece na **posição 6923**, na primeira linha de dados:
   a sequência bruta `... 3b 4e 6f 72 74 65 3b 31 3b 52 6f 6e 64 f4 6e 69 61 3b`
   (`;Norte;1;Rond<f4>nia;`), ou seja o **"ô" de "Rondônia"** codificado
   como o byte único `0xF4`. Em UTF-8, `0xF4` inicia uma sequência de 4
   bytes e exige que o próximo byte seja continuação (`0x80`–`0xBF`); o
   byte seguinte é `0x6E` (`'n'`), que quebra a sequência. Portanto a
   **decodificação estrita como UTF-8 falha** — confirmado nos 13 anos.

4. **Latin-1 preserva.** O byte `0xF4` corresponde a `U+00F4` ("ô") tanto
   em **ISO-8859-1 (latin-1)** quanto em **CP1252**. Todos os caracteres
   acentuados do português ocupam a faixa `0xC0`–`0xFF`, **idêntica** nas
   duas codificações (ISO-8859-1 e CP1252 só divergem em `0x80`–`0x9F`,
   faixa não usada por letras acentuadas do português). ISO-8859-1 é a
   codificação histórica dos microdados do INEP e a escolha padrão e
   segura aqui.

5. **Contraste com o manifesto.** O `source_manifest.json` do próprio
   projeto **tem** BOM UTF-8 no primeiro byte — evidência de que a
   ausência de BOM nos CSVs do Censo é característica da fonte (INEP), e
   não um acidente de gravação local.

**Conclusão:** não há divergência real. A auditoria anterior apenas
repetiu o `encoding` que estava escrito no código; a leitura estrita como
UTF-8 falha porque os arquivos **não são** UTF-8 (nem têm BOM); os
arquivos são ISO-8859-1, e `encoding="latin-1"` reproduz os nomes
corretamente.

## 11. Ausência de atribuição causal ou definição de tratamento

- Nenhuma das três tabelas contém coluna de tratamento, coorte, grupo,
  *common support*, *event-time* ou "primeiro ano de tratamento".
- O painel expõe **apenas presença observada** (flags) e **volumes**
  (contagens) por município-ano.
- A função `audit_entradas_saidas` registra entradas, saídas e lacunas de
  presença federal EPT ativa **apenas no log de console** (dicionário de
  retorno da `main`); **não grava nada nos Parquets** e não decide
  tratamento.
- Coerente com [`CONTRATO_CAUSAL.md`](../methodology/CONTRATO_CAUSAL.md)
  ("primeira presença federal EPT observada no Censo Escolar" é o
  tratamento operacional candidato, ainda a confrontar com criação /
  inauguração / início efetivo — item aberto) e com
  [`AUDITORIA_LISTA_FASE_II.md`](../institutional/AUDITORIA_LISTA_FASE_II.md)
  ("nenhum ano de tratamento foi atribuído nesta etapa").

## 12. Hashes finais (SHA-256)

Parquets regenerados após a correção de encoding:

| Parquet | Bytes | SHA-256 |
|---|---|---|
| `data/interim/censo_escolas_federais_2007_2019.parquet` | 152.637 | `a6ae8a3882b120ecba11b9cdef66507ded5113d46bf1d74de8a744be9630da73` |
| `data/interim/censo_federal_municipio_ano_2007_2019.parquet` | 90.233 | `86d8e80d46da47ab6cf73d9ea3c92eb216dc61a89ce6afa67588d60aa43d94d3` |
| `data/processed/painel_presenca_federal_ept_fase_ii_2007_2019.parquet` | 36.726 | `46d3b7f255e2b372116c2aee80743f1d2d5434f9fcce5e640c05dfbeb7cc8dfd` |

SHA-256 de cada ZIP de origem: em
`data/raw/inep/censo_escolar/source_manifest.json`.

## 13. Limitações e observações

- **`data/` não é versionada** (`.gitignore` do monorepo). A
  reprodutibilidade é garantida pelo script + manifesto de origem com
  checksums, não pelo Git.
- **Sem suíte de testes** (`tests/` só contém `.gitkeep`). A validação
  desta etapa vem das funções `validate_*` embutidas na rotina e da
  bateria consolidada da revisão.
- **Rótulos de nome no painel:** `NO_MUNICIPIO`, `SG_UF` e `CO_UF` vêm do
  Censo nos anos em que há escola federal no município e do cadastro
  Fase II (nomes oficiais do IBGE) nos anos sem escola. Pequenas
  diferenças de grafia entre INEP e IBGE são possíveis; ambas são
  rótulos válidos e a chave de junção é sempre `CO_MUNICIPIO`.
- **`ept` sem exigência de atividade:** ver seção 6.1 — a métrica de
  oferta EPT (`IN_PROF == 1`) é independente da situação de funcionamento;
  para uso causal, a métrica com semântica de "campus operante" é
  `fl_presenca_federal_ept_ativa`.
- **Layout do INEP:** cada `microdados_censo_escolar_{ano}.zip` contém
  `microdados_ed_basica_{ano}.csv` com 370 colunas em todos os anos
  (re-release harmonizada) — não foi necessário mapeamento de colunas por
  ano.
- **`TP_LOCALIZACAO_DIFERENCIADA`** é lida e convertida, mas não é usada
  em nenhuma flag ou agregação desta etapa — mantida para uso futuro.
- **Determinismo:** ordenação explícita por `(NU_ANO_CENSO, CO_ENTIDADE)`
  e `(CO_MUNICIPIO, NU_ANO_CENSO)`; execuções repetidas produzem os
  mesmos hashes.
- **Divergência 147 vs. 144:** herdada da etapa da lista Fase II, não
  reconciliada aqui (fora do escopo).
