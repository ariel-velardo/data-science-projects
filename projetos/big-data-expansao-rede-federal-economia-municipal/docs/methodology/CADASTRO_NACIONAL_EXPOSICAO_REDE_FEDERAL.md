# Cadastro Nacional de Exposição à Rede Federal (2007–2019)

## 1. Objetivo

Construir a primeira versão reproduzível do cadastro nacional de
exposição observada à Rede Federal, município-ano, 2007–2019. Este
cadastro é insumo da etapa 1 do `ROADMAP_ACADEMICO.md` ("construir
cadastro nacional de exposição") e servirá, em etapa **posterior e fora
do escopo desta rotina**, para montar o pool de municípios de comparação
da Expansão Fase II.

Rotina: [`src/constroi_cadastro_nacional_exposicao_rede_federal.py`](../../src/constroi_cadastro_nacional_exposicao_rede_federal.py).

Esta etapa **não**:

- seleciona controles causais finais;
- executa matching;
- avalia suporte comum;
- estima event study, ATT, DiD ou qualquer efeito causal;
- monta o painel CEMPRE;
- altera decisões do `CONTRATO_CAUSAL.md`;
- baixa dados novos da internet.

## 2. Diferença entre exposição nacional observada e tratamento Fase II

O tratamento causal da pesquisa permanece, sem alteração:

> presença operacional de campus da Rede Federal associado à Expansão
> Fase II no município.

O Censo Escolar fornece uma **proxy observacional anual** dessa presença,
baseada na regra `TP_DEPENDENCIA==1` ∧ `TP_SITUACAO_FUNCIONAMENTO==1` ∧
`IN_PROF==1` — presença federal de EPT ativa. Esta é a **mesma regra**
já usada em `constroi_painel_censo_escolar.py` e
`constroi_cadastro_causal_fase_ii.py`, aplicada agora a **todos os
municípios do Brasil**, não apenas aos 147 da Fase II.

Essa regra identifica presença federal de EPT ativa observada — ela **não
identifica, isoladamente**:

- fase de expansão (Fase I, Fase II, expansões posteriores);
- criação administrativa;
- inauguração;
- início institucional exato;
- pertencimento à Expansão Fase II.

Portanto, **nenhuma linha deste cadastro deve ser lida como tratamento
Fase II.** Um município fora dos 147 oficiais que apresente
`fl_presenca_federal_ept_ativa=true` neste cadastro pode ser: (a) sede de
uma escola técnica federal de outra fase de expansão, anterior ou
posterior à Fase II; (b) sede de uma entidade federal historicamente
distinta (ver, por exemplo, os casos de Porto Alegre/RS e Montes
Claros/MG documentados em `CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`, que
mostram que a mesma regra mecânica pode capturar entidades federais sem
relação de sucessão com o polo real da Fase II); ou (c) efetivamente um
município da Fase II ainda não incluído na lista oficial dos 147 — mas
essa hipótese exige confronto individual com o cadastro
`fase_ii_municipios.parquet`, nunca inferência automática por esta
rotina. A separação entre "exposição observada" (o que este cadastro
mede) e "tratamento Fase II" (uma decisão causal, documentada em
`CONTRATO_CAUSAL.md` e `CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`) é o
motivo de toda a nomenclatura deste documento evitar termos como
"tratado" ou "never-treated" (ver seção 6).

## 3. Fontes e proveniência

Todos os insumos são locais; **nada foi baixado nesta etapa**.

| Fonte | Caminho | Papel |
|---|---|---|
| Microdados do Censo Escolar 2007–2019 (13 ZIPs) | `data/raw/inep/censo_escolar/microdados_censo_escolar_{ano}.zip` | Único insumo bruto: usado apenas para reconstruir o **universo municipal anual** (todas as dependências administrativas) |
| Manifesto de origem | `data/raw/inep/censo_escolar/source_manifest.json` | Mesma proveniência já auditada em `AUDITORIA_CONSTRUCAO_CENSO_ESCOLAR.md` |
| Contagens federais município-ano | `data/interim/censo_federal_municipio_ano_2007_2019.parquet` | **Reutilizado, não recalculado** — já construído e auditado por `constroi_painel_censo_escolar.py` |
| Painel Fase II aprovado | `data/processed/painel_presenca_federal_ept_fase_ii_2007_2019.parquet` | Usado apenas para reconciliação (seção 9) |
| Cadastro oficial Fase II | `data/processed/fase_ii_municipios.parquet` | Usado apenas para identificar o subconjunto dos 147 municípios na reconciliação |

Este cadastro **não relê nem refiltra** as escolas federais dos ZIPs —
essa contagem já existe, foi validada e é reutilizada tal como está. O
único processamento novo sobre os microdados brutos é a leitura do
**universo municipal** (seção 5), porque o agregado federal existente só
contém municípios com ao menos um registro federal naquele ano — não
representa exposição zero.

## 4. Regra operacional (reaproveitada, não redefinida)

| Flag | Definição | Contagem que a sustenta |
|---|---|---|
| `fl_presenca_federal` | qualquer escola federal (`TP_DEPENDENCIA==1`) observada no município-ano | `qt_escolas_federais > 0` |
| `fl_presenca_federal_ativa` | escola federal em atividade (`TP_SITUACAO_FUNCIONAMENTO==1`), independente de EPT | `qt_escolas_em_atividade > 0` |
| `fl_presenca_federal_ept` | escola federal com oferta de EPT (`IN_PROF==1`), independente de estar ativa (ver `AUDITORIA_CONSTRUCAO_CENSO_ESCOLAR.md`, seção 6.1) | `qt_escolas_com_ept > 0` |
| `fl_presenca_federal_ept_ativa` | escola federal, ativa, com EPT — **proxy principal de exposição** | `qt_escolas_federal_ept_ativa > 0` |

Contenções logicamente exigidas e validadas: `ept_ativa ⇒ presença_federal`
(validação 8, seção 8). As demais contenções (`ept_ativa ⊆ ept`,
`ept_ativa ⊆ ativa`, `ept ⊆ federais`, `ativa ⊆ federais`) já foram
auditadas em `AUDITORIA_CONSTRUCAO_CENSO_ESCOLAR.md` para o agregado
federal reutilizado aqui e não são recalculadas.

## 5. Granularidade

**Produto A** — `CO_MUNICIPIO × NU_ANO_CENSO`, uma linha por município
observado no universo do Censo naquele ano (todo o Brasil, 2007–2019).

**Produto B** — uma linha por `codigo_municipio_ibge` observado em
qualquer ano de 2007–2019 (resumo da trajetória).

## 6. Método de construção do universo municipal anual

O agregado federal (`censo_federal_municipio_ano_2007_2019.parquet`)
contém **apenas** município-ano com ao menos um registro federal — não
serve para representar exposição zero, porque um município sem escola
federal simplesmente não aparece nele.

Para representar exposição zero, o universo municipal de cada ano é
construído **diretamente dos microdados brutos** (todas as dependências
administrativas, não apenas federais): para cada um dos 13 ZIPs, lê-se
em chunks (`chunksize=50.000`, sem nunca extrair o CSV para disco,
reaproveitando `csv_path_in_zip` de `constroi_painel_censo_escolar.py`)
apenas 5 colunas de identificação (`NU_ANO_CENSO`, `CO_MUNICIPIO`,
`NO_MUNICIPIO`, `SG_UF`, `CO_UF`), sem filtro de dependência, e
deduplica-se por `CO_MUNICIPIO` dentro de cada ano.

**Não se presume uma grade fixa de 5.570 municípios × 13 anos.** O
número de municípios por ano é preservado exatamente como observado no
Censo daquele ano — o Brasil teve 5.564 municípios até 2012 e 5.570 a
partir de 2013 (criação de Balneário Rincão/SC, Pescaria Brava/SC,
Paraíso das Águas/MS e outros casos), e o próprio Censo Escolar pode não
cobrir 100% do universo IBGE em todo ano. O painel nacional (Produto A)
tem, portanto, um número de linhas por ano potencialmente diferente ano
a ano — ver seção 10 para os números efetivamente obtidos nesta
execução.

O ano de cada linha do universo é atribuído pelo arquivo de origem (um
ZIP = um ano do Censo), não recopiado ingenuamente da coluna
`NU_ANO_CENSO` linha a linha — a mesma convenção de robustez já usada em
`constroi_painel_censo_escolar.py` para o agregado federal (a rotina
avisa em `stderr`, mas não falha, se algum registro tiver
`NU_ANO_CENSO` divergente do ano do arquivo).

## 7. Tratamento dos zeros

O painel nacional (Produto A) é o resultado de um `left join` do
universo municipal anual com o agregado federal, com `validate="one_to_one"`
(ambas as tabelas já são únicas por município-ano) e preenchimento de
zero nas 11 colunas de contagem (`qt_*`) para todo município-ano sem
registro correspondente no agregado federal. As 4 flags são recalculadas
a partir das contagens já preenchidas — nunca herdadas diretamente do
agregado federal.

## 8. Mudanças de códigos e cobertura municipal

O universo de cada ano é preservado como observado (seção 6): se um
município não aparece no Censo de um determinado ano (por não existir
ainda, por ter sido extinto/fundido, ou por lacuna do próprio Censo),
ele simplesmente **não gera linha** para aquele ano no painel nacional —
não é imputado como "exposição zero" nesse ano, porque exposição zero
pressupõe que o município existia e podia ser observado.

O resumo municipal (Produto B) expõe essa situação explicitamente:

- `n_anos_no_universo`: quantos dos 13 anos o município foi observado no
  Censo (pode ser < 13);
- `anos_ausentes_do_universo`: lista (formato `;`-separado, ex.:
  `"2007;2008;2009;2010;2011;2012"`) dos anos em que o município não
  apareceu no universo — nunca confundidos com anos observados e sem
  exposição;
- `presente_nos_13_anos_do_universo`: `true` somente se
  `anos_ausentes_do_universo` for vazio.

Nenhuma harmonização territorial histórica (por exemplo, mapear um
código antigo para um código novo após um desmembramento) é feita
silenciosamente por esta rotina — a ausência fica registrada como está,
para decisão explícita em etapa posterior.

## 9. Validações executadas

**Sobre o painel nacional** (`validate_painel_nacional`):

1. anos exatamente 2007–2019;
2. unicidade de município-ano;
3. ausência de `CO_MUNICIPIO` nulo;
4. `CO_MUNICIPIO` com 7 dígitos;
5. `CO_UF` coerente com os 2 primeiros dígitos de `CO_MUNICIPIO`;
6. nenhuma contagem `qt_*` negativa;
7. cada flag coerente com sua contagem correspondente
   (`fl_X == (qt_X > 0)`);
8. `fl_presenca_federal_ept_ativa=true` implica `fl_presenca_federal=true`.

**Reconciliações** (`validate_reconciliacao_federal`,
`validate_reconciliacao_fase_ii`):

9. todo município-ano SEM registro no agregado federal tem as 11
   contagens exatamente zero; nenhum registro federal positivo é
   perdido pelo `left join`; as contagens batem exatamente para as
   chaves em comum com `censo_federal_municipio_ano_2007_2019.parquet`;
10. reconciliação byte-a-byte (mesmas 11 contagens + as 3 flags que já
    existiam) do subconjunto dos 147 municípios da Fase II contra
    `painel_presenca_federal_ept_fase_ii_2007_2019.parquet` já aprovado.

**Sobre o resumo municipal** (`validate_resumo_municipal`), recomputando
cada agregado diretamente do painel nacional — nunca chamando de volta a
própria função que construiu o resumo, para não validar uma tautologia:

11. `n_anos_no_universo` e `n_anos_com_exposicao_observada` batem com a
    recontagem independente a partir do painel;
12. `primeiro_ano_exposicao_observada` / `ultimo_ano_exposicao_observada`
    coerentes com `anos_expostos`;
13. `padrao_intermitente_exposicao_observada` recomputado diretamente do
    painel (existência de ao menos um ano observado, dentro da janela
    `[primeiro, último]`, sem exposição);
14. `n_anos_no_universo + len(anos_ausentes_do_universo) == 13` e
    `presente_nos_13_anos_do_universo` coerente com
    `anos_ausentes_do_universo`.

Qualquer violação levanta `ValueError` com exemplos concretos das
divergências — nenhuma correção é feita silenciosamente.

## 10. Schema efetivo

### Produto A — painel nacional município-ano

`data/processed/cadastro_nacional_exposicao_rede_federal_municipio_ano_2007_2019.parquet`

| Coluna | Tipo | Descrição |
|---|---|---|
| `CO_MUNICIPIO` | string (7 dígitos) | chave |
| `NU_ANO_CENSO` | string (4 dígitos) | chave |
| `NO_MUNICIPIO` | string | nome, conforme o Censo daquele ano |
| `SG_UF` | string | UF |
| `CO_UF` | string (2 dígitos) | código IBGE da UF |
| `qt_escolas_federais` … `qt_doc_prof_tec` (11 colunas) | Int64 | reaproveitadas de `censo_federal_municipio_ano_2007_2019.parquet`, preenchidas com 0 |
| `fl_presenca_federal` | bool | `qt_escolas_federais > 0` |
| `fl_presenca_federal_ativa` | bool | `qt_escolas_em_atividade > 0` |
| `fl_presenca_federal_ept` | bool | `qt_escolas_com_ept > 0` |
| `fl_presenca_federal_ept_ativa` | bool | `qt_escolas_federal_ept_ativa > 0` — proxy principal |

### Produto B — resumo municipal da exposição observada

`data/processed/resumo_exposicao_rede_federal_municipio_2007_2019.parquet`

| Coluna | Tipo | Descrição |
|---|---|---|
| `codigo_municipio_ibge` | string (7 dígitos) | chave |
| `municipio`, `uf`, `co_uf` | string | do último ano observado no universo |
| `primeiro_ano_exposicao_observada` | Int64 (nulo se nunca exposto) | primeiro ano com `fl_presenca_federal_ept_ativa=true` |
| `ultimo_ano_exposicao_observada` | Int64 (nulo se nunca exposto) | último ano com a flag |
| `n_anos_no_universo` | Int64 | quantos dos 13 anos o município foi observado no Censo |
| `n_anos_com_exposicao_observada` | Int64 | quantos anos com a flag verdadeira |
| `exposicao_observada_em_2007` | bool | flag verdadeira especificamente em 2007 |
| `exposicao_observada_2007_2019` | bool | `n_anos_com_exposicao_observada > 0` |
| `sem_exposicao_observada_2007_2019` | bool | nenhuma exposição observada — **não** "never-treated" |
| `presente_nos_13_anos_do_universo` | bool | observado no Censo em todos os 13 anos |
| `padrao_intermitente_exposicao_observada` | bool | há ano observado, dentro de `[primeiro, último]`, sem exposição |
| `anos_expostos` | string, `;`-separado | ex.: `"2011;2012;2013"`; `""` se nunca exposto |
| `anos_ausentes_do_universo` | string, `;`-separado | anos em que o município não apareceu no universo do Censo |

## 11. Dimensões e contagens obtidas

Execução de referência (dados locais desta sessão). Para os valores
correntes, execute o script (`main()` imprime o resumo) ou leia os dois
Parquets diretamente — nenhum número abaixo é mantido manualmente
independente do Parquet.

Universo municipal por ano (não é uma grade fixa — reflete a expansão
territorial real do Brasil no período):

| Ano | 2007 | 2008 | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Municípios no universo | 5.564 | 5.564 | 5.565 | 5.565 | 5.565 | 5.565 | 5.570 | 5.570 | 5.570 | 5.570 | 5.570 | 5.570 | 5.570 |

- **Painel nacional (Produto A):** 72.378 linhas — soma exata dos 13
  universos anuais acima (não 5.570 × 13 = 72.410; a diferença de 32
  linhas é exatamente a diferença acumulada de municípios entre os anos
  com universo menor e 5.570).
- **Resumo municipal (Produto B):** 5.570 linhas — 1 por município
  distinto observado em algum ano de 2007–2019 (a união de todos os
  universos anuais).
- **Sem exposição observada 2007–2019** (`sem_exposicao_observada_2007_2019`): 4.970.
- **Exposição já observada em 2007** (`exposicao_observada_em_2007`): 146.
- **Primeira exposição observada entre 2008 e 2019**: 454.
- **Padrão intermitente de exposição observada**: 17.
- **Presentes nos 13 anos do universo**: 5.564 / 5.570 (6 municípios têm
  cobertura incompleta — consistente com a expansão territorial de 5.564
  para 5.570 municípios ocorrida dentro da própria janela 2007–2019).
- **Reconciliação exata do subconjunto Fase II** (147 municípios × 13
  anos, todas as colunas comparáveis contra
  `painel_presenca_federal_ept_fase_ii_2007_2019.parquet`): **OK**, sem
  nenhuma divergência.

Consistência aritmética: 4.970 (sem exposição) + 146 (exposição desde
2007) + 454 (primeira exposição 2008–2019) = 5.570 (total de municípios
distintos) — confere exatamente.

## 12. Padrões temporais

A trajetória de exposição de cada município é preservada exatamente
como observada — incluindo lacunas e intermitências — sem qualquer
suavização ou preenchimento de "buraco" por interpolação. A proxy
principal (`fl_presenca_federal_ept_ativa`) **não é tratada como
absorvente por padrão**: um município pode ter exposição observada,
depois lacuna, depois exposição novamente, e isso fica registrado em
`padrao_intermitente_exposicao_observada=true`, exatamente como já
acontece na Fase II para os casos de Jequié/BA, Nossa Senhora da
Glória/SE e Piracicaba/SP (ver `CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`).

## 13. Limitações

- **Nenhuma validação institucional individual.** Diferente do cadastro
  causal da Fase II, este cadastro nacional não confronta nenhuma linha
  com ato de criação, autorização, inauguração ou fonte institucional —
  é puramente derivado da regra mecânica do Censo Escolar, para os
  ~5.570 municípios do Brasil.
- **Sem correspondência com outras fases de expansão.** Este cadastro
  não identifica se um município fora dos 147 pertence à Fase I, a uma
  fase posterior, ou a nenhuma expansão federal — essa correspondência
  ainda não foi construída (é parte do trabalho de "cadastro nacional de
  exposição" propriamente dito, mas na acepção causal completa,
  distinta da leitura puramente observacional aqui produzida).
- **Universo dependente da cobertura do próprio Censo Escolar.** Um
  município que não é observado em um ano do Censo (por qualquer razão,
  inclusive falha de resposta ao Censo, não apenas inexistência
  territorial) fica marcado como ausente do universo naquele ano — a
  rotina não distingue "município não existia" de "município existia
  mas não foi coberto pelo Censo naquele ano"; ambos os casos aparecem
  igualmente em `anos_ausentes_do_universo`.
- **Nomes municipais podem variar entre anos.** `municipio`, `uf` e
  `co_uf` no resumo (Produto B) vêm do último ano observado no
  universo; pequenas diferenças de grafia entre anos (mesma limitação já
  documentada em `AUDITORIA_CONSTRUCAO_CENSO_ESCOLAR.md` para o painel
  Fase II) não são harmonizadas.
- **Sem informação de spillover geográfico.** Este cadastro não traz
  nenhuma variável de distância ou vizinhança — a política de
  spillovers permanece uma decisão aberta em `CONTRATO_CAUSAL.md`.

## 14. Por que este cadastro ainda não define controles causais

Este cadastro responde apenas "que municípios têm, ano a ano,
observação de presença federal com EPT ativa no Censo Escolar" — uma
pergunta puramente observacional e nacional. Para se tornar um pool de
controles causais válido para a Expansão Fase II, ainda faltam, nesta
ordem (ver `ROADMAP_ACADEMICO.md`, seção "Próxima etapa técnica"):

1. excluir os municípios já cobertos por outras fases de expansão da
   Rede Federal (este cadastro não os distingue da Fase II sem
   comparação adicional);
2. excluir municípios potencialmente contaminados por spillover
   geográfico de um município tratado (critério ainda em aberto);
3. construir o painel econômico municipal do CEMPRE (ainda não
   construído);
4. incorporar covariáveis pré-tratamento justificadas pelo DAG de
   `CONTRATO_CAUSAL.md` (ainda não incorporadas);
5. avaliar suporte comum e balanceamento entre tratados e candidatos a
   controle (nada disso foi feito aqui).

Um município `sem_exposicao_observada_2007_2019=true` neste cadastro
**não é**, por si só, um controle causal validado — é apenas um
município sem presença federal de EPT ativa observada no período,
segundo a mesma proxy mecânica usada para o tratamento candidato. Nem a
exclusão do resumo, nem `n_anos_no_universo`, nem qualquer outra coluna
deste cadastro autorizam estimação causal.
