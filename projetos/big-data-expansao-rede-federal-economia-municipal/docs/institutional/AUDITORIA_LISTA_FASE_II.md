# Auditoria: Lista de Cidades-Pólo da Expansão Fase II

## 1. Status e escopo

Primeira reconstrução real de dados do projeto, com fonte primária
verificada. Nenhum ano de tratamento foi atribuído, nenhum matching foi
refeito, nenhum ATT foi estimado. Esta etapa apenas reconstrói **a lista
de cidades-pólo** da Expansão Fase II e a associa a códigos IBGE.

## 2. Fonte primária localizada

Em sessão anterior, a tentativa de acessar o "Plano de Expansão Fase II"
via ferramenta de fetch automatizada retornou HTTP 403. Nesta sessão,
acessando via `curl` direto em shell, o mesmo domínio respondeu HTTP 200
— e, ao seguir o link do edital a partir da página de índice do IFRS,
localizou-se o **Anexo I** da **Chamada Pública MEC/SETEC nº
001/2007**: a "Relação Nominal das Cidades Pólo" — a lista nacional
completa e oficial, com exatamente **150 municípios**, organizada por
UF, assinada por Fernando Haddad (Ministro da Educação) e Eliezer
Moreira Pacheco (Secretário/SETEC), Brasília, 24/04/2007.

Esse documento é a fonte primária da lista. Foi obtido via **espelho
institucional** do IFRS (domínio `memoria.ifrs.edu.br`), não do domínio
original do MEC/SETEC (que não hospeda mais o arquivo em local
verificado nesta sessão).

## 3. Fontes acessadas

| Fonte | Classificação | URL | Status | SHA-256 (8 primeiros) |
|---|---|---|---|---|
| Edital 001/2007 + Anexo I (PDF) | primária, via espelho IFRS | `.../tainacan-items/5012/14702/ADREI_00011.pdf` | HTTP 200 | `6075c1ad` |
| Página de índice do edital (HTML) | espelho institucional (apenas navegação) | `.../documentos/edital-chamada-publica-mec-setec-n-o-001-2007/` | HTTP 200 | `9a27d027` |
| Plano de Expansão Fase II (apresentação) | primária, via espelho IFRS | `.../tainacan-items/5012/167488/ADMEC_00087B.pdf` | HTTP 200 | `11afeebc` |
| Localidades IBGE (municípios) | primária, API oficial | `servicodados.ibge.gov.br/api/v1/localidades/municipios` | HTTP 200 | `86ecdccd` |

Checksums completos, tamanhos, datas de acesso e método (`curl` direto,
`GET`) em
[`data/raw/institutional/fase_ii/source_manifest.json`](../../data/raw/institutional/fase_ii/source_manifest.json).

## 4. Fonte que falhou

| Fonte | URL tentada | Método | Status | Data |
|---|---|---|---|---|
| MEC — "Institutos Federais: concepção e diretrizes" | `.../principios-concepcoes.pdf` | `curl` direto, `GET`, com e sem `--location`, `User-Agent Mozilla/5.0` | **HTTP 404** (corpo JSON de erro do gov.br) | 2026-09-09 |

A página-pai (`institutos-federais-de-educacao-ciencia-e-tecnologia`)
responde HTTP 200, mas não contém mais link para este PDF (verificado
buscando `href="*.pdf"` no HTML retornado). O arquivo parece ter sido
removido ou reorganizado no domínio `gov.br` desde um acesso bem-sucedido
em sessão anterior (via ferramenta de fetch distinta, fora desta
execução). Esta fonte **não era necessária** para reconstruir o Anexo I
e não bloqueou a tarefa.

## 5. O que o "Plano de Expansão Fase II" (apresentação) revelou

Esse documento é uma apresentação de slides (23 páginas). O texto
extraível cobre em detalhe **apenas Ceará e Rio Grande do Norte**; os
mapas de outros estados são imagem, sem camada de texto (nenhuma
ferramenta de OCR está instalada neste ambiente — não foi usada,
conforme a regra "OCR somente se já instalada"). Portanto **este
documento sozinho não permitiria reconstruir a lista nacional** — a
lista completa veio do Anexo I do edital (seção 6).

Achados úteis, com página exata:
- Confirma **Sobral/CE** como cidade-pólo proposta na Fase II (slide
  "Ceará - Distribuição Proposta no Plano de Expansão - Fase II").
- A legenda **"Raio de Abrangência: 50 Km"** aparece especificamente no
  mapa do Ceará — não há evidência, nesta fonte, de que seja regra
  nacional.
- Critérios de seleção (distribuição territorial equilibrada, cobertura
  de mesorregiões, sintonia com APLs, aproveitamento de infraestrutura
  existente, identificação de parcerias) — idênticos aos já registrados
  em `docs/institutional/EXPANSAO_FASE_II.md`, agora reconfirmados nesta
  fonte.
- Não há qualquer menção a Campinas/SP neste documento.

## 6. Extração do Anexo I

Texto extraído via `pdftotext -layout` (poppler/xpdf 4.06, já instalado
no sistema — nenhuma biblioteca Python de PDF foi adicionada). O layer
de texto do PDF está em **cp1252** (confirmado byte a byte: `0xC9` →
"É", consistente com "MINISTÉRIO"). O Anexo I ocupa as **páginas 9–10**
de 11, em duas colunas com quebra fixa na coluna 27 (confirmado
empiricamente antes de escrever o parser).

**A própria página final do Anexo I declara "TOTAL: 150 CIDADES"** — o
script extraiu exatamente 150 registros, batendo com essa contagem
interna do documento.

## 7. Padronização territorial e associação de código IBGE

Correspondência por nome normalizado (maiúsculas, sem acento) dentro da
mesma UF — nunca por nome isolado. Resultado:

- **145 correspondências exatas** (nome da fonte bate exatamente com o
  nome oficial IBGE, dentro da mesma UF).
- **1 correção manual revisada individualmente**: São Miguel D'Oeste/SC
  (grafia do edital) → **São Miguel do Oeste** (grafia oficial IBGE,
  código `4217204`). Único candidato na UF; documentada, não é
  correspondência fuzzy automática.
- **4 casos administrativos**: Gama, Planaltina, Samambaia e Taguatinga
  (DF) não são municípios — são Regiões Administrativas do Distrito
  Federal, que **não é dividido em municípios** (fato estrutural: há
  exatamente 1 registro de UF=DF na base do IBGE). As 4 unidades foram
  associadas ao único município-equivalente do DF (**Brasília**, código
  `5300108`), com status `corrigida_administrativa` e observação
  explícita — nenhum nome foi "casado" por aproximação.
- **0 correspondências ambíguas sem resolução.**

Nenhum município ausente da fonte foi inventado. Nenhuma correção foi
aplicada sem revisão individual e documentada.

## 8. Casos especiais sinalizados

| Caso | Presente no Anexo I? | UF | Código IBGE | Status |
|---|---|---|---|---|
| **Sobral** | Sim | CE | `2312908` | exata |
| **Campinas** | Sim | SP | `3509502` | exata |

Ambos aparecem exatamente uma vez, sem ambiguidade. Isso confirma, com
fonte primária, o que o `PROTOCOLO_PRE_ANALISE.md` já registrava sobre
esses dois municípios pertencerem à Fase II — mas **nenhum ano de
tratamento foi atribuído aqui**, conforme escopo.

## 9. Reconciliação do funil documental

| Item | Valor obtido | Valor documental prévio | Bate? |
|---|---|---|---|
| Unidades/cidades-pólo no Anexo I | **150** | "150 unidades" (README, PROTOCOLO) | Sim — e o próprio documento se autodeclara "TOTAL: 150 CIDADES" |
| Municípios distintos (código IBGE) | **147** | "144 municípios" (RECUPERACAO_CONTEXTO_FREEZE, PROTOCOLO) | **Não — diferença de 3** |

Explicação **parcial**, sem forçar o número: das 150 linhas do Anexo I,
**apenas 3 municípios "somem" ao agregar por código IBGE** — as 4 linhas
do DF colapsam em 1 código (Brasília), uma redução líquida de 3 (150 −
3 = 147). As outras 146 linhas já eram 146 municípios distintos (145
exatos + 1 corrigido), sem nenhuma duplicata de nome dentro da mesma UF
(verificado: 0 duplicados).

**Os 3 municípios de diferença entre 147 (nesta reconstrução) e 144
(protocolo congelado) permanecem NÃO EXPLICADOS por esta fonte.**
Hipóteses possíveis, nenhuma comprovada aqui:
- o número "144" no protocolo pode refletir uma etapa **posterior** ao
  Anexo I (ex.: resultado da avaliação de mérito do item 7 do edital,
  que podia excluir municípios sem proposta válida ou sem contrapartida
  aprovada — o edital previa exatamente esse funil de seleção);
  NÃO COMPROVADO NESTA EXECUÇÃO.
- pode refletir uma contagem que já tratava o DF de forma diferente da
  usada aqui, ou excluía/agregava outros casos administrativos ainda não
  identificados; NÃO COMPROVADO NESTA EXECUÇÃO.

Esta divergência deve ser tratada como aberta na reconstrução
institucional, não resolvida por ajuste numérico.

## 10. Contagem por UF (municípios distintos)

AC 2 · AL 4 · AM 5 · AP 1 · BA 8 · CE 6 · DF 1 · ES 5 · GO 6 · MA 8 ·
MG 12 · MS 5 · MT 6 · PA 5 · PB 5 · PE 5 · PI 6 · PR 6 · RJ 7 · RN 6 ·
RO 2 · RR 1 · RS 10 · SC 7 · SE 3 · SP 12 · TO 3 — soma = 147.

## 11. Artefatos produzidos

| Artefato | Caminho |
|---|---|
| Fontes brutas preservadas | `data/raw/institutional/fase_ii/*.pdf`, `*.html`, `*.json` |
| Manifesto de fontes | `data/raw/institutional/fase_ii/source_manifest.json` |
| Código reprodutível | `src/constroi_lista_fase_ii.py` |
| Tabela intermediária (1 linha por cidade-pólo) | `data/interim/fase_ii_unidades.parquet` (150 linhas) |
| Tabela final (1 linha por município IBGE) | `data/processed/fase_ii_municipios.parquet` (147 linhas) |

`data/raw`, `data/interim` e `data/processed` não são versionados neste
repositório (`.gitignore` do projeto) — reprodutibilidade garantida pelo
script + manifesto com checksums, não pelo Git.

## 12. Validações executadas

- Reexecução do script duas vezes seguidas; hash SHA-256 dos dois
  Parquets de saída **idêntico** entre as duas execuções — determinismo
  confirmado.
- Schema de `fase_ii_unidades.parquet`: 12 colunas, incluindo todas as
  pedidas (`nome_unidade_fonte`, `municipio_fonte`, `uf_fonte`, `fase`,
  `pagina_fonte`, `documento_fonte`, `metodo_extracao`, `observacao`) +
  colunas de resolução IBGE.
- Schema de `fase_ii_municipios.parquet`: 9 colunas, incluindo todas as
  pedidas (`codigo_municipio_ibge`, `municipio`, `uf`,
  `quantidade_unidades_fase_ii`, `nomes_unidades`, `fonte_primaria`,
  `paginas_fonte`, `status_validacao`, `observacao`).
- `codigo_municipio_ibge` único em `fase_ii_municipios.parquet`: **sim**
  (147 valores únicos, 147 linhas).
- Nenhum `codigo_municipio_ibge` nulo na tabela final: **confirmado**
  (0 nulos) — a tabela é declarada completa para as 150 unidades de
  origem.
- Nomes duplicados (mesma UF, mesmo `municipio_fonte`) na tabela
  intermediária: **0**.
- Município com mais de 1 unidade: **1** (Brasília/DF, 4 unidades —
  caso administrativo documentado, não ambiguidade de dado).
- Caracteres acentuados (ex.: "Brasília", "Ilhéus") gravados corretamente
  em UTF-8 nos Parquets — confirmado por inspeção de bytes
  (`b'Bras\xc3\xadlia'`); as exibições com "�" vistas durante a auditoria
  eram limitação de renderização do terminal, não erro de dado.

## 13. O que não foi realizado

- Não foi determinado por que o protocolo congelado registra 144
  municípios em vez dos 147 encontrados aqui (seção 9) — requer fonte
  adicional (ex.: resultado da avaliação de mérito da Chamada Pública,
  ou lista pós-seleção), fora do escopo desta etapa.
- Não foi baixado o Censo Escolar nem o CEMPRE (fora do escopo).
- Não foi atribuído ano de tratamento a nenhum município (fora do
  escopo).
- Não foi reconstruído o matching nem o common support (fora do
  escopo).
- O documento MEC "Institutos Federais: concepção e diretrizes" não foi
  reacessado (ver seção 4) — não era necessário para esta etapa.

## 14. Problemas fora do escopo (não corrigidos)

- O `Plano de Expansão Fase II` (apresentação, 23 páginas) tem a maior
  parte do seu conteúdo geográfico em mapas-imagem, sem camada de texto.
  Reconstruir os critérios de pontuação por município exigiria OCR
  (ferramenta não instalada neste ambiente) ou uma fonte alternativa —
  não resolvido aqui, apenas registrado.
- O domínio `gov.br` parece ter reorganizado ou removido o PDF
  "principios-concepcoes.pdf" desde a última sessão — não investigado a
  fundo (fora do escopo desta tarefa; não bloqueou o resultado).
