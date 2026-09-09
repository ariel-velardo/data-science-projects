# Auditoria de Timing do Tratamento

## 1. Status e escopo

Auditoria empírica do timing do tratamento ("primeira presença federal
EPT observada no Censo Escolar"), conforme
[CONTRATO_CAUSAL.md](CONTRATO_CAUSAL.md). Nenhum ATT foi estimado, nenhum
estimador staggered foi executado, o matching não foi alterado e o
contrato causal não foi tocado.

**Resultado principal desta execução: a auditoria não pôde ser realizada
sobre dados observados, porque nenhuma fonte tabular de tratamento,
município, matching ou Censo Escolar existe neste repositório.**

Confirmado por varredura completa do projeto (excluindo `.venv/` e
`.git/`): `data/raw`, `data/interim` e `data/processed` contêm apenas
`.gitkeep`; `src/` e `tests/` também continham apenas `.gitkeep` antes
desta execução. Isso é consistente com o próprio
[RECUPERACAO_CONTEXTO_FREEZE.md](../freeze/RECUPERACAO_CONTEXTO_FREEZE.md),
que registra que a pasta do projeto exploratório original não estava
versionada no Git e foi removida em uma reorganização do repositório —
ou seja, os números do funil (144 → 119 → 53 → 47) e os resultados de
matching/pré-tendências existem **apenas como texto** nos documentos
congelados, sem tabela subjacente reproduzível neste repositório.

## 2. O que foi reutilizado / criado

- Reutilizado: nada — não havia rotina, dataset ou schema no projeto.
- Criado: `src/auditoria_timing_tratamento.py` (varre `data/raw|interim|
  processed` por fontes tabulares candidatas relacionadas a tratamento/
  município/matching/Censo Escolar; se nenhuma existir, gera a tabela de
  auditoria apenas com o cabeçalho especificado, sem inventar linhas).
- Criado: `outputs/diagnostics/auditoria_timing_tratamento.csv` (saída do
  script; 0 linhas de dado).
- Criado: este relatório.

## 3. Auditoria mínima obrigatória — item a item

### 3.1 Identificação da fonte tabular

| Campo exigido | Fonte tabular localizada |
|---|---|
| código IBGE do município | **NENHUMA** |
| ano | **NENHUMA** |
| presença federal EPT | **NENHUMA** |
| primeiro ano observado | **NENHUMA** |
| coorte de tratamento | **NENHUMA** |
| pertencimento à Fase II | **NENHUMA** |
| common support | **NENHUMA** |
| amostra core | **NENHUMA** |

Fonte ausente, especificamente: não há em `data/raw`, `data/interim` nem
`data/processed` nenhum arquivo `.csv`, `.parquet`, `.xlsx`, `.json` ou
`.duckdb` com dados do Censo Escolar, do CEMPRE, de códigos municipais
IBGE, de resultado de matching ou de classificação de coortes. Os únicos
registros existentes são as afirmações em prosa no
PROTOCOLO_PRE_ANALISE.md e no RECUPERACAO_CONTEXTO_FREEZE.md.

### 3.2 Validações (unicidade, cobertura, códigos, estabilidade, etc.)

Todas as validações abaixo são **DADOS_INSUFICIENTES** — não executáveis
sem a fonte tabular da seção 3.1:

- Unicidade de município-ano.
- Cobertura temporal 2007–2019.
- Códigos municipais ausentes, inválidos ou duplicados.
- Estabilidade do primeiro ano de tratamento.
- Municípios que aparecem tratados e depois deixam de aparecer
  (flag_reversao_tratamento).
- Presença federal anterior ao ano atribuído como tratamento
  (flag_presenca_anterior).
- Lacunas de observação próximas ao primeiro ano (flag_lacuna_timing).
- Coerência das coortes 2010, 2011, 2012 e 2013.
- Casos especiais de Sobral/CE e Campinas/SP — os únicos dados
  disponíveis sobre esses dois casos são as observações qualitativas já
  registradas em PROTOCOLO_PRE_ANALISE.md (seção 7), sem data municipal
  verificável em fonte tabular.

### 3.3 Reconciliação do funil 144 → 119 → 53 → 47

**Não reconciliável nesta execução.** Os quatro números existem somente
como texto nos documentos congelados:

- 144 municípios Fase II (RECUPERACAO_CONTEXTO_FREEZE.md, "População Fase
  II").
- 119 tratados 2010–2013 = 37+65+14+3 (mesma seção — a soma aritmética
  bate, mas não há lista de códigos municipais para conferir contra os
  144).
- 53 tratados em common support (mesmo documento, seção "Common
  support").
- 47 pares nas coortes 2010–2011 = 17+30 (seção "Amostra causal core
  candidata").

Sem uma tabela município-ano subjacente, não é possível confirmar que
os 119 são de fato um subconjunto dos 144, que os 53 são de fato um
subconjunto dos 119, ou que os 47 são de fato um subconjunto dos 53.
A aritmética interna de cada etapa (37+65+14+3=119; 17+30=47) está
correta, mas isso comprova apenas consistência textual, não consistência
observacional.

**Atenção sobre "47 pares"**: o protocolo (RECUPERACAO_CONTEXTO_FREEZE.md,
"Matching exploratório") registra 53 tratados matched, **51 controles
únicos** e ESS dos controles ≈ 49,3 — ou seja, o próprio documento já
indica que o matching foi feito com reposição e que pode haver controle
repetido entre pares (ESS < número de tratados). Para a amostra core de
47, não existe fonte que informe se os controles associados aos 47
tratados são distintos entre si. As colunas `controle_utilizado` e
`controle_repetido` da tabela de auditoria não puderam ser preenchidas
por essa mesma razão. **Não deve ser assumido que existem 47 controles
distintos.**

## 4. Regra de classificação (definida para uso futuro, não aplicada a nenhum município)

Regra explícita a ser aplicada quando a fonte tabular existir:

- `timing_consistente`: primeiro ano de presença estável entre
  reprocessamentos, sem presença federal observada em ano anterior ao
  atribuído, sem lacuna de observação nos 2 anos anteriores ao primeiro
  ano, e sem reversão do tratamento (ano de presença não pode "desaparecer"
  em anos posteriores).
- `timing_com_alerta`: um dos itens acima falha de forma limitada (ex.:
  uma lacuna isolada de 1 ano na série, ou pequena instabilidade entre
  bases) mas o primeiro ano permanece o candidato mais plausível.
- `timing_inconsistente`: presença federal observada antes do ano
  atribuído como tratamento, reversão de tratamento sem explicação
  documentada, ou múltiplos primeiros anos conflitantes entre fontes.
- `dados_insuficientes`: não há série de Censo Escolar (ou equivalente)
  para o município permitindo qualquer uma das checagens acima.

Nesta execução, **os 144/119/53/47 municípios candidatos não puderam ser
classificados** — todos cairiam em `dados_insuficientes` caso uma lista
de códigos municipais existisse, mas nem essa lista está presente no
repositório para gerar as linhas da tabela.

## 5. Tabela de auditoria

Caminho: `outputs/diagnostics/auditoria_timing_tratamento.csv`.

Colunas gravadas (conforme especificação): `codigo_municipio`,
`municipio`, `uf`, `fase_ii`, `primeiro_ano_presenca`,
`coorte_tratamento`, `common_support`, `amostra_core`,
`controle_utilizado`, `controle_repetido`, `flag_presenca_anterior`,
`flag_reversao_tratamento`, `flag_lacuna_timing`, `flag_caso_especial`,
`status_timing`, `observacao`.

Linhas de dado: **0** — nenhum código municipal foi inventado. O CSV
existe apenas como definição de schema, pronto para ser populado quando
a fonte de tratamento/Censo Escolar for reconstruída ou revalidada.

## 6. Gate consolidado

### NAO_APTO

Justificativa: o gate avalia exclusivamente a consistência observacional
do timing, conforme escopo desta tarefa. Não existe, neste repositório,
nenhuma tabela município-ano, nenhum código IBGE, nenhuma série de Censo
Escolar e nenhum resultado de matching reproduzível. Toda a evidência
disponível é textual (documentos congelados), não auditável no nível
município-ano exigido. Sem essa base observável, não é possível emitir
`APTO` nem `PROMISSOR_COM_ALERTAS` — ambos pressupõem ter checado, ainda
que parcialmente, dados reais. Este gate **não** se pronuncia sobre
identificação causal válida, apenas sobre a impossibilidade de auditar o
timing com os artefatos hoje disponíveis.

## 7. O que não foi realizado e por quê

- Nenhuma das 9 validações da seção "Auditoria mínima obrigatória" (item
  2 do pedido original) foi executada sobre dados reais — não há fonte.
- A tabela de auditoria não pôde ser populada linha a linha — não há
  lista de códigos municipais no repositório.
- Testes existentes relacionados: não executados porque `tests/` contém
  apenas `.gitkeep` — não há suíte de testes no projeto.
- Reconciliação numérica do funil 144→119→53→47 contra dados: não
  realizada — apenas a consistência aritmética textual foi conferida
  (seção 3.3).

## 8. Problemas fora do escopo (não corrigidos)

- O `.gitignore` do monorepo (`C:/GitHub/data-science-projects/.gitignore`,
  regra `*.csv`) ignora silenciosamente qualquer `.csv` deste projeto,
  incluindo `outputs/diagnostics/auditoria_timing_tratamento.csv` — o
  arquivo existe em disco mas não aparece em `git status`. Isso é uma
  configuração do repositório pai, fora do escopo desta tarefa.
- `src/` e `tests/` estavam vazios antes desta execução, apesar de o
  README descrever `src` como "pipeline reproduzível" — não há pipeline
  implementado ainda.
- Não há, no repositório, nenhum arquivo com a lista dos 144 municípios
  Fase II nem dos códigos IBGE citados no funil — esse é o bloqueio
  central para qualquer auditoria futura de timing.
