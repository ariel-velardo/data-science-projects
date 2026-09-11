# Auditoria de Correspondência: Unidades da Fase II

## Status e escopo

Auditoria preliminar e reproduzível, executada por
`src/auditoria_correspondencia_unidades_fase_ii.py`. Ela cruza três
fontes já existentes no projeto para os 147 municípios oficiais da Fase
II e produz **candidatos, diagnósticos e uma fila priorizada para
validação institucional**. Ela não define ano de tratamento, não
escolhe automaticamente "a" unidade da Fase II de nenhum município, e
não executa matching, common support, ATT, event study ou regressão
causal. O `CONTRATO_CAUSAL.md` não foi alterado por esta etapa.

Esta versão incorpora correções de uma revisão adversarial (contexto
limpo, sem a justificativa de quem escreveu o código) que encontrou um
bug real de classificação e gaps de cobertura de teste — ver seção
"Correções desta versão" abaixo.

## Finalidade

As investigações institucionais anteriores (Montes Claros, Porto
Alegre, Brasília — ver histórico de commits e `git log` deste
repositório) mostraram que a regra "primeiro ano com qualquer EPT
federal ativa no município" pode capturar uma entidade federal
preexistente e institucionalmente distinta do polo real da Expansão
Fase II. Antes de investigar manualmente os 147 municípios um a um,
esta auditoria automatiza duas coisas:

1. o **inventário** de todas as entidades federais observadas no Censo
   Escolar por município (não apenas a primeira);
2. o **cruzamento** desse inventário com uma segunda fonte
   independente — a base MEC/SISTEC "Unidades da Rede Federal de
   EPCT" — para levantar candidatos adicionais e sinalizar
   inconsistências.

O resultado é uma **triagem**, não uma conclusão. Ela prioriza onde a
validação institucional manual (atos de criação, notícias de
inauguração, páginas de memória institucional dos Institutos Federais)
deve começar.

## Fontes e proveniência

| Fonte | Caminho | Papel |
|---|---|---|
| Cadastro oficial Fase II | `data/processed/fase_ii_municipios.parquet` | 147 códigos IBGE, município, UF |
| Censo Escolar, escola-ano | `data/interim/censo_escolas_federais_2007_2019.parquet` | entidades federais observadas, por CO_ENTIDADE |
| Painel município-ano | `data/processed/painel_presenca_federal_ept_fase_ii_2007_2019.parquet` | presença federal antes de 2009 (geral e EPT ativa, separadas); lacunas internas em EPT ativa |
| Base MEC/SISTEC | `data/raw/institutional/mec_sistec/Unidades_da_Rede_Federal_de_EPCT.csv` | candidatos adicionais por nome de unidade + `dt_autorizacao` |

### Proveniência da base MEC/SISTEC

- **Título**: "2008 a 2019 - Unidades da Rede Federal de EPCT"
- **Órgão**: Portal de Dados Abertos do Ministério da Educação (seção PRONATEC)
- **URL original**: `https://dadosabertos.mec.gov.br/images/conteudo/pronatec/Unidades_da_Rede_Federal_de_EPCT.csv`
- **Status da URL original nesta auditoria**: bloqueada por desafio
  Cloudflare (HTTP 403, `Cf-Mitigated: challenge`); o `robots.txt` do
  domínio proíbe explicitamente `ClaudeBot`. Nenhuma tentativa de
  contornar essa proteção foi feita.
- **URL efetivamente usada** (cópia pública arquivada, independente do
  servidor do MEC): `https://web.archive.org/web/20250424052536id_/https://dadosabertos.mec.gov.br/images/conteudo/pronatec/Unidades_da_Rede_Federal_de_EPCT.csv`
  — captura de 2025-04-24 05:25:36 UTC. O dígest do arquivo é idêntico
  em todas as capturas do Internet Archive entre 2020-01-29 e
  2025-04-24, indicando conteúdo estável por mais de cinco anos.
- **SHA-256 esperado**: `ff48f76f4fed741514032edd6b67373b80e0791345a9dba593c6d93396015dc3`
- **Tamanho esperado**: 105.709 bytes
- O script **valida hash e tamanho em tempo de execução** antes de ler
  o arquivo; diverge → falha, não segue com um arquivo não verificado.

## Limitações da base MEC/SISTEC

A base tem 977 linhas e 5 colunas (`sigla_unidade_ensino`,
`nome_unidade_ensino`, `dt_autorizacao`, `sigla_uf_unidade_ensino`,
`nome_municipio_unidade_ensino`). Limitações confirmadas por inspeção
direta, nesta e em sessões anteriores desta auditoria:

- **Sem chave estruturada**: não há código IBGE nem CO_ENTIDADE/INEP.
  A única correspondência possível com os 147 municípios é
  UF + nome do município, normalizado — um método necessariamente mais
  frágil que uma chave numérica.
- **183 das 977 linhas (18,7%) têm `sigla_unidade_ensino` igual à
  string literal `"null"`** — mantenedora não identificável sem
  inferência por nome. O script lê com `keep_default_na=False`
  precisamente para preservar essa string literal (o `na_values`
  padrão do pandas trataria `"null"` como ausente e a converteria
  silenciosamente em `NaN`).
- **Mistura, sem filtro, unidades da Rede Federal com entidades fora
  de escopo**: a base contém, por exemplo, `INSTITUTO MATHEUS`,
  `INSTITUTO PRISCILLA CASTILHO`, `INSTITUTO TAULUS` (aparentam ser
  privadas), `Ministério da Edução` [sic] e — de forma decisiva —
  **`Escola teste - manual sistec`**, um registro de teste do próprio
  sistema, com `dt_autorizacao` no mesmo formato de todas as outras
  linhas.
- **Duplicatas da mesma unidade física com nomes ligeiramente
  diferentes e datas diferentes**: por exemplo, em Cabo Frio/RJ,
  "Instituto Federal Fluminense - Campus Cabo Frio" (17/04/2009) e
  "INSTITUTO FEDERAL FLUMINENSE - CAMPUS CABO FRIO" (07/06/2011)
  diferem só em caixa. O detector de duplicata (`sistec_tem_duplicata_ambigua`)
  normaliza caixa/acento/espaço/pontuação antes de comparar — mas
  **nunca** funde descrições semanticamente diferentes (ex.: "CEFET-MG
  UNED Contagem" vs. o nome institucional por extenso): isso fica só
  sinalizado (`F_AMBIGUO`) para revisão humana, nunca decidido
  automaticamente.
- **Erros de município na própria fonte**: o "Instituto Federal do Rio
  Grande do Norte - Campus Santa Cruz" aparece na base com
  `nome_municipio_unidade_ensino = "Natal"` — por isso Santa Cruz/RN
  aparece nesta auditoria como `E_SEM_CANDIDATO_MEC`, mesmo existindo
  uma linha na base cujo *nome da unidade* menciona Santa Cruz. Esta
  auditoria **não corrige esse tipo de erro por inferência de texto**
  — fazer isso seria criar uma correspondência automática exatamente
  do tipo que a tarefa proíbe.

## Por que `dt_autorizacao` não é tratamento

`dt_autorizacao` tem resolução de **hora, minuto e segundo**
(ex.: `28/09/2010 11:28:58`), incompatível com uma data de portaria
publicada no Diário Oficial (que tem resolução de dia). A distribuição
anual do campo tem dois picos artificiais — 2009 (297 linhas) e 2014
(323 linhas), 63% do total em só dois anos — mais compatível com lotes
de importação/cadastro no SISTEC do que com uma distribuição orgânica
de atos de autorização ao longo do tempo. A presença do registro
`Escola teste - manual sistec` com uma data no mesmo formato confirma:
este campo é, com grande probabilidade, **um carimbo de sistema (data
de criação/edição do registro no SISTEC)**, não a data legal de
autorização de funcionamento.

Por isso: **`dt_autorizacao` é preservado nas saídas apenas como
referência descritiva.** Ele nunca é convertido em ano, nunca decide
categoria, nunca decide prioridade, e todas as ocorrências de um
mesmo município são mantidas lado a lado — nenhuma é escolhida como
"a" data.

## Dicionário das colunas de ano do Censo (tabela longa)

As seis colunas de ano abaixo, presentes nas linhas `CENSO_ESCOLAR` da
tabela longa, descrevem **somente o histórico observado de cada
entidade no Censo Escolar** — nenhuma delas é, ou substitui, um ano de
tratamento.

| Coluna | Significado |
|---|---|
| `primeiro_ano_registro_censo` | primeiro ano em que a entidade aparece no Censo Escolar, em qualquer situação |
| `ultimo_ano_registro_censo` | último ano em que a entidade aparece no Censo Escolar, em qualquer situação |
| `primeiro_ano_ativa_censo` | primeiro ano com `fl_em_atividade = verdadeiro`; nulo se a entidade nunca esteve ativa |
| `ultimo_ano_ativa_censo` | último ano com `fl_em_atividade = verdadeiro`; nulo se nunca esteve ativa |
| `primeiro_ano_ept_ativa_censo` | primeiro ano com `fl_presenca_federal_ept_ativa = verdadeiro`; nulo se a entidade nunca teve EPT ativa |
| `ultimo_ano_ept_ativa_censo` | último ano com `fl_presenca_federal_ept_ativa = verdadeiro`; nulo se nunca teve EPT ativa |

`primeiro_ano_ept_ativa_censo` é, em particular, a mesma métrica cujo
uso ingênuo ("primeiro ano com qualquer EPT federal ativa no
município") motivou toda esta linha de investigação — ver "Finalidade"
acima. Ela continua exposta aqui, por entidade, como dado descritivo;
usá-la para atribuir um ano de tratamento sem validação institucional
repete exatamente o problema que esta auditoria existe para evitar.

## Significado das categorias

Categorias **não são mutuamente exclusivas entre B e F** — um município
pode acumular várias delas simultaneamente. `A_SEM_ALERTA_MECANICO` é a
única exceção: por construção (só é atribuída depois de checar que
nenhuma outra categoria disparou), ela nunca coexiste com nenhuma das
outras cinco. Isso é garantido tanto em `classify_municipio` quanto por
uma checagem redundante em `validate_summary_table` (falha alto se a
garantia for quebrada no futuro).

| Categoria | Critério exato implementado |
|---|---|
| `A_SEM_ALERTA_MECANICO` | nenhuma das categorias B–F foi disparada — significa apenas "esta auditoria não encontrou alerta mecânico", nunca "unidade da Fase II validada institucionalmente" |
| `B_EPT_ATIVA_ANTES_2009` | há EPT federal ativa (`fl_presenca_federal_ept_ativa`) em 2007 ou 2008 no painel processado — sinal mecânico de timing antecipado que exige validação institucional; **não é prova de preexistência**, pode representar implantação precoce da própria Fase II |
| `C_MULTIPLAS_ENTIDADES` | mais de 1 entidade do Censo com EPT ativa em algum ano (`n_entidades_censo_com_ept_ativa`) **ou** mais de 1 nome distinto de unidade no MEC/SISTEC (`n_nomes_unidade_sistec_distintos`) |
| `D_INTERMITENTE` | existe ao menos um ano com EPT federal ativa = falso entre o primeiro e o último ano com EPT federal ativa = verdadeiro, no painel |
| `E_SEM_CANDIDATO_MEC` | nenhuma linha da base MEC/SISTEC corresponde por UF + nome do município (nem exata, nem normalizada) |
| `F_AMBIGUO` | candidatos MEC/SISTEC com o mesmo nome normalizado e `dt_autorizacao` divergente **ou** múltiplas entidades relevantes no Censo *e* no MEC/SISTEC simultaneamente **ou** múltiplos nomes MEC/SISTEC cuja melhor correspondência de município não é exata |

`prioridade_revisao` (`alta`/`media`/`baixa`) é derivada dessas
categorias: **alta** se o município está na lista de prioridade forçada
(ver abaixo), se `F_AMBIGUO`, ou se `B_EPT_ATIVA_ANTES_2009` e
`C_MULTIPLAS_ENTIDADES` ocorrem juntos; **media** se qualquer outra
categoria de sinal (B, C, D ou E) está presente sozinha; **baixa**
caso contrário.

### Contagens do Censo Escolar: total, ativa, EPT ativa

Uma entidade federal sem qualquer relação com EPT (ex.: uma escola
militar) não pode inflar silenciosamente o alerta de múltiplas
entidades. Por isso a tabela-resumo separa três contagens — todas as
entidades continuam preservadas na tabela longa, só a contagem que
alimenta `C_MULTIPLAS_ENTIDADES` é filtrada:

| Coluna | O que conta |
|---|---|
| `n_entidades_censo_total` | toda entidade (CO_ENTIDADE) observada no Censo, sem filtro |
| `n_entidades_censo_com_alguma_atividade` | entidades com `fl_em_atividade = verdadeiro` em algum ano |
| `n_entidades_censo_com_ept_ativa` | entidades com `fl_presenca_federal_ept_ativa = verdadeiro` em algum ano — **esta é a usada em `C_MULTIPLAS_ENTIDADES`** |

### Contagens MEC/SISTEC: registros brutos vs. nomes distintos

Pelo mesmo motivo, linhas brutas da base MEC/SISTEC **não são chamadas
de "unidades físicas"** — podem ser a mesma unidade registrada mais de
uma vez (ver "Limitações" acima):

| Coluna | O que conta |
|---|---|
| `n_registros_sistec` | linhas brutas da base MEC/SISTEC que correspondem ao município por UF + nome |
| `n_nomes_unidade_sistec_distintos` | nomes de unidade distintos após normalização de caixa/acento/espaço/pontuação — **esta é a usada em `C_MULTIPLAS_ENTIDADES`/`F_AMBIGUO`** |

### Presença federal antes de 2009: geral vs. EPT ativa

| Coluna | O que mede | Usada em categoria? |
|---|---|---|
| `presenca_federal_geral_antes_2009` | qualquer escola federal (inclusive sem relação com EPT) presente em 2007/2008 — só diagnóstico | não |
| `presenca_federal_ept_ativa_antes_2009` | EPT federal ativa especificamente em 2007/2008 | sim — alimenta `B_EPT_ATIVA_ANTES_2009` |

**Nenhuma das duas prova preexistência institucional de um campus da
Fase II.** A separação existe para impedir que uma instituição federal
sem relação com EPT (ex.: a Escola Preparatória de Cadetes do Exército,
presente em Campinas/SP desde antes de 2009) seja lida como evidência
de campus preexistente — ver "Efeito da correção em Campinas" abaixo.

## Diferença entre candidato automático e validação institucional

Um "candidato" nesta auditoria é qualquer linha que **passou por uma
regra mecânica de correspondência** (mesmo código IBGE, para o Censo;
UF + nome normalizado, para o MEC/SISTEC). Isso não é o mesmo que
"confirmado". A auditoria institucional já realizada para Montes
Claros, Porto Alegre e Brasília mostrou que duas entidades podem
corresponder à mesma cidade e ainda assim serem institucionalmente
distintas (mantenedoras diferentes, datas de origem diferentes,
nenhuma relação de sucessão entre elas). **Nenhuma linha desta
auditoria deve ser lida como "a unidade correta da Fase II"** sem
confronto com ato de criação, autorização de funcionamento, notícia de
inauguração ou fonte institucional equivalente.

## Correções desta versão (revisão adversarial)

Uma revisão adversarial (subagente em contexto limpo, sem a
justificativa de design de quem escreveu o código) encontrou um bug de
classificação confirmado e gaps de cobertura de teste. Resumo das
mudanças de comportamento (não só de nome):

- **`A_LIMPO` → `A_SEM_ALERTA_MECANICO`, agora mutuamente exclusiva de
  B–F por construção.** Antes, a condição que definia "limpo" não
  excluía `D_INTERMITENTE` — **Jequié/BA e Piracicaba/SP apareciam
  simultaneamente como "sem alerta" e "intermitente"**, contradizendo
  o próprio propósito da categoria. Corrigido ao reestruturar
  `classify_municipio`: a categoria só é adicionada depois de avaliar
  todas as outras, se a lista ainda estiver vazia — não é mais
  possível reintroduzir esse tipo de bug sem que
  `validate_summary_table` falhe.
- **`B_PREEXISTENTE` → `B_EPT_ATIVA_ANTES_2009`**, e passou a usar
  apenas `fl_presenca_federal_ept_ativa` (nunca a presença federal
  genérica). Isso mudou o resultado real: **Campinas/SP e Angra dos
  Reis/RJ saíram da categoria B** porque a única presença federal
  anterior a 2009 identificada era de entidades sem relação com EPT
  (uma escola militar e um colégio naval, respectivamente) — ver
  próxima seção.
- **Contagens do Censo e do MEC/SISTEC separadas** em três e duas
  colunas, respectivamente (ver tabelas acima), para que entidades sem
  EPT ativa e registros duplicados no MEC/SISTEC não inflem
  `C_MULTIPLAS_ENTIDADES`/`F_AMBIGUO` silenciosamente.
- **`sistec_tem_duplicata_ambigua` agora normaliza o nome antes de
  comparar** (caixa/acento/espaço/pontuação). Antes, comparava strings
  brutas e não detectava duplicatas como a de Cabo Frio/RJ (mesma
  unidade, nomes diferindo só em caixa) — agora detecta.
- **`read_sistec_csv` agora usa `keep_default_na=False`.** Antes, o
  `na_values` padrão do pandas convertia a string literal `"null"` (183
  ocorrências) em `NaN`, contradizendo o que esta documentação já
  afirmava sobre os dados preservados.

## Efeito da correção em Campinas e Angra dos Reis

**Campinas/SP** tem 4 entidades no Censo: uma é a "ESCOLA PREPARATORIA
DE CADETES DO EXERCITO" (nunca teve EPT ativa — é uma escola militar),
duas nunca estiveram ativas em nenhum sentido, e só 1
(`IFSP - CAMPUS CAMPINAS`) teve EPT ativa (a partir de 2016). Antes da
correção: `n_entidades_censo=4` e a presença federal genérica da escola
militar em 2007/2008 gerava `B_PREEXISTENTE` — Campinas aparecia como
prioridade alta. Depois da correção: `n_entidades_censo_com_ept_ativa=1`,
`presenca_federal_ept_ativa_antes_2009=False` (a escola militar nunca
teve EPT ativa) → **`A_SEM_ALERTA_MECANICO`, prioridade baixa.**
**Angra dos Reis/RJ** segue exatamente o mesmo padrão (a entidade
preexistente ali é o Colégio Naval).

Isso é o resultado pretendido pela correção, não um efeito colateral:
uma instituição federal sem relação com EPT não deve, por si só, gerar
alerta de preexistência de campus da Fase II.

## Contagens reproduzidas (execução de referência, pós-correção)

Total de municípios: **147**. Categorias B–F não são mutuamente
exclusivas entre si (não somam 147); `A_SEM_ALERTA_MECANICO` é
exclusiva de todas as outras:

| Categoria | Municípios |
|---|---:|
| `A_SEM_ALERTA_MECANICO` | 124 |
| `B_EPT_ATIVA_ANTES_2009` | 5 |
| `C_MULTIPLAS_ENTIDADES` | 19 |
| `D_INTERMITENTE` | 4 |
| `E_SEM_CANDIDATO_MEC` | 1 |
| `F_AMBIGUO` | 7 |

Prioridade de revisão: **alta**: 7 · **media**: 16 · **baixa**: 124.

Correspondência com a base MEC/SISTEC: **exata**: 146 ·
**normalizada**: 0 · **sem_candidato**: 1.

Casos intermitentes preservados (idênticos aos já confirmados por
inspeção direta dos dados em etapa anterior desta auditoria, agora sem
o rótulo "sem alerta" incorreto): Jequié/BA (2918001) e Piracicaba/SP
(3538709) aparecem só com `D_INTERMITENTE`; Nossa Senhora da Glória/SE
(2804508) com `D_INTERMITENTE; C_MULTIPLAS_ENTIDADES`; Montes Claros/MG
(3143302) — prioridade forçada — com as quatro categorias
`B_EPT_ATIVA_ANTES_2009; C_MULTIPLAS_ENTIDADES; D_INTERMITENTE; F_AMBIGUO`.

## Casos prioritários

### Prioridade forçada (independente das regras automáticas)

- **Montes Claros/MG** (3143302) — Colégio Agrícola Antônio Versiani
  Athayde (UFMG, EPT ativa 2007–2008) x Campus Montes Claros do IFNMG
  (2011–). `B_EPT_ATIVA_ANTES_2009; C_MULTIPLAS_ENTIDADES; D_INTERMITENTE; F_AMBIGUO`.
- **Porto Alegre/RS** (4314902) — Campus Porto Alegre do IFRS, ex-Escola
  Técnica da UFRGS (EPT ativa desde 2007) x Campus Restinga, polo real
  da Fase II (2011–). `B_EPT_ATIVA_ANTES_2009; C_MULTIPLAS_ENTIDADES; F_AMBIGUO`.
- **Brasília/DF** (5300108) — Campus Planaltina preexistente (absorvido
  em 2008) agregado, sob o mesmo código IBGE, a múltiplas ondas de
  implantação (13 entidades no Censo, 20 registros no MEC/SISTEC).
  `B_EPT_ATIVA_ANTES_2009; C_MULTIPLAS_ENTIDADES; F_AMBIGUO`.

### Demais casos de prioridade alta (7 no total)

Contagem/MG, Cabedelo/PB, Cabo Frio/RJ e Duque de Caxias/RJ — todos
`C_MULTIPLAS_ENTIDADES; F_AMBIGUO`. Ver
`outputs/diagnostics/resumo_correspondencia_unidades_fase_ii.csv` para
o diagnóstico completo de cada um.

### Caso sem candidato MEC/SISTEC

**Santa Cruz/RN** (2411205): existe uma entidade no Censo (IFRN Campus
Santa Cruz) e uma linha correspondente na base MEC/SISTEC pelo nome da
unidade, mas essa linha da base tem `nome_municipio_unidade_ensino =
"Natal"` — um erro na fonte, não corrigido automaticamente.

## Próximos passos

1. Validação institucional individual dos 7 municípios de prioridade
   alta, começando pelos três casos já confirmados por pesquisa direta.
2. Revisão dos 16 municípios de prioridade média.
3. Verificação manual do caso Santa Cruz/RN diretamente com o IFRN.
4. Só depois de validação institucional: reconstrução de uma população
   causal candidata — fora do escopo desta etapa.

## Proibição de uso direto em estimação causal

Os arquivos gerados por esta auditoria
(`outputs/diagnostics/auditoria_correspondencia_unidades_fase_ii.csv`
e `outputs/diagnostics/resumo_correspondencia_unidades_fase_ii.csv`)
**não devem ser usados diretamente** como insumo de matching, common
support, ATT, event study ou qualquer estimador causal. Nenhuma coluna
neste resultado define "ano de tratamento" — inclusive as colunas de
ano do Censo (ver dicionário acima) são histórico observado, não
tratamento. `CONTRATO_CAUSAL.md` permanece a fonte de verdade sobre
decisões causais do projeto e não foi alterado por esta etapa.
