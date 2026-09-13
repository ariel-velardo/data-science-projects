# Diagnóstico de Integração Funcional — Arranjos Populacionais x Fase II

## 1. Objetivo

Construir um diagnóstico **exclusivamente descritivo** de integração
funcional entre os 4.964 municípios candidatos a controle e os 147
municípios da Expansão Fase II, usando os **Arranjos Populacionais** do
IBGE (Censo Demográfico 2010) — agrupamentos de municípios definidos por
deslocamento pendular para trabalho/estudo ou por contiguidade de manchas
urbanizadas — e cruzando esse resultado com as distâncias e flags de
25/50/100 km já calculadas em
`docs/methodology/DIAGNOSTICO_SPILLOVER_FASE_II.md`.

Rotina: [`src/constroi_diagnostico_arranjos_populacionais_fase_ii.py`](../../src/constroi_diagnostico_arranjos_populacionais_fase_ii.py).

Esta etapa **não**:

- escolhe definitivamente a regra causal de spillover;
- exclui nenhum município do pool candidato já aprovado;
- modifica os artefatos do pool candidato ou do diagnóstico de distâncias;
- usa CEMPRE, RAIS, PIB ou qualquer outcome econômico;
- faz matching;
- estima propensity score ou qualquer efeito causal.

## 2. Metodologia oficial dos Arranjos Populacionais

Fonte: IBGE, **Arranjos Populacionais e Concentrações Urbanas do Brasil**
(2ª edição), Coordenação de Geografia. Definição oficial (LEIA_ME do
produto):

> "Um arranjo populacional é o agrupamento de dois ou mais municípios
> onde há uma forte integração populacional devido aos movimentos
> pendulares para trabalho ou estudo, ou devido à contiguidade entre as
> manchas urbanizadas principais."

Os dados de deslocamento pendular vêm da **amostra do Censo Demográfico
2010** — o IBGE recomenda observar os limites de uso da expansão dessa
amostra (mesma ressalva do próprio produto).

**Ano de referência**: 2010 — o mesmo ano da fonte de sedes municipais já
usada em `DIAGNOSTICO_SPILLOVER_FASE_II.md`, evitando qualquer mistura de
malhas territoriais diferentes entre os dois diagnósticos.

## 3. Fonte, proveniência e hash

- **Origem institucional**: IBGE, Coordenação de Geografia — publicação
  direta, sem distribuidor intermediário.
- **Página do produto**: `https://www.ibge.gov.br/geociencias/organizacao-do-territorio/divisao-regional/15782-arranjos-populacionais-e-concentracoes-urbanas-do-brasil.html`
- **Diretório oficial**: `https://geoftp.ibge.gov.br/organizacao_do_territorio/divisao_regional/arranjos_populacionais/`
- **Arquivo usado — Tabela 1.1** ("Municípios brasileiros que participam
  de arranjos populacionais — 2010"):
  - URL exata: `https://geoftp.ibge.gov.br/organizacao_do_territorio/divisao_regional/arranjos_populacionais/tabelas_xls_2ed/tab01.xlsx`
  - Data de acesso: 2026-09-12T21:35:40Z
  - Tamanho: 111.497 bytes
  - SHA-256: `fcb65d94220814643536e00bc775e3fea69d9da9bbb56acd576f4abfb058da77`
  - Caminho local: `data/raw/ibge/arranjos_populacionais_2010/tab01_municipios_arranjos_populacionais_2010.xlsx`
  - Manifesto completo: `data/raw/ibge/arranjos_populacionais_2010/source_manifest.json`
- **Rodapé original da tabela**: "Fonte: IBGE, Censo Demográfico 2010.
  Nota: Arranjos populacionais identificados segundo metodologia
  desenvolvida pela Coordenação de Geografia do IBGE."
- **Totais confirmados na leitura**: 294 arranjos populacionais, 953
  municípios participantes, 953 códigos únicos (nenhum duplicado — cada
  município pertence, no máximo, a um arranjo nesta tabela).
- **Reconciliação de códigos**: o código do município na planilha bruta é
  numérico (ex.: `3500105`); é convertido para string de 7 dígitos —
  **nenhuma geocodificação por nome de município**, nenhuma composição
  inferida manualmente.
- **Cobertura confirmada no acesso**: 722 dos 4.964 candidatos e 46 dos
  147 municípios Fase II participam de algum arranjo (os demais
  simplesmente não têm nenhum arranjo associado — ver seção 6 sobre por
  que isso não é ausência de spillover).

### 3.1 Arquivos do mesmo produto deliberadamente não utilizados

- **Tabelas 2 a 8 do mesmo produto** (`tab02.xlsx` a `tab08.xls`) trazem
  Produto Interno Bruto (PIB) municipal e número de empresas/unidades
  locais para 2010–2011 — variáveis de natureza CEMPRE. Foram
  **deliberadamente não baixadas nem usadas**, por serem outcomes
  econômicos fora do escopo desta rotina.
- **Geodatabase Access (`ArranjosPopulacionais_mbd_2ed.zip`)**: contém a
  feição `ComposicaoRecortes_01_PorMunicipio`, com o código numérico
  interno oficial do arranjo (`CodArranjo`) além do nome. **Não foi
  extraída nesta rotina** por indisponibilidade de ferramenta de leitura
  de arquivos Access (`.mdb`) no ambiente de execução (nem `mdbtools`,
  nem `pyodbc`/driver Access). Ver limitação na seção 9.

## 4. Identificador do arranjo usado nesta rotina

Como o código numérico oficial (`CodArranjo`) só existe na geodatabase
Access não extraída (seção 3.1), esta rotina deriva um identificador
determinístico (`codigo_arranjo_populacional`) a partir do **nome
oficialmente publicado** do arranjo na própria Tabela 1.1 (ex.:
"Adamantina - Lucília/SP" → `ADAMANTINA_LUCILIA_SP`). Este identificador:

- **não é** o `CodArranjo` interno do IBGE;
- é estável e reprodutível a partir do nome oficialmente publicado;
- serve apenas para agrupar municípios do mesmo arranjo dentro desta
  rotina, sem ambiguidade.

O nome completo (`nome_arranjo_populacional`) é sempre preservado junto
ao identificador derivado, para rastreabilidade direta com a publicação
oficial.

## 5. Diferença entre arranjo populacional e distância sede-a-sede

| | Distância sede-a-sede (`DIAGNOSTICO_SPILLOVER_FASE_II.md`) | Arranjo populacional (esta rotina) |
|---|---|---|
| O que mede | Distância geodésica em linha reta entre sedes municipais | Integração funcional por deslocamento pendular (trabalho/estudo) ou contiguidade de manchas urbanizadas |
| Fonte | Coordenadas de sedes municipais (IBGE via geobr) | Amostra do Censo Demográfico 2010 (deslocamento) + malha urbana (IBGE) |
| Direcionalidade | Sempre existe (todo par de municípios tem uma distância) | Só existe para os 953 municípios que efetivamente compõem algum dos 294 arranjos |
| Relação com spillover | Aproximação geográfica pura, sem qualquer dado de comportamento | Aproximação de integração comportamental observada (mas ainda uma aproximação, não uma medida direta de spillover econômico da Fase II) |

As duas medidas são complementares e não substitutas: um candidato pode
estar geodesicamente próximo de um Fase II sem compartilhar arranjo (ligação
funcional fraca ou não desenvolvida em 2010), e pode compartilhar arranjo
mesmo estando a uma distância geodésica maior que 25 ou 50 km (ligação
funcional documentada apesar da distância em linha reta).

## 5.1 Advertência: direção temporal e risco de informação pós-tratamento

Há também um problema de direção temporal. Os Arranjos Populacionais
foram construídos com informações observadas em 2010, enquanto 21 dos
129 municípios candidatos à amostra principal possuem coorte candidata
em 2009 e 48 possuem coorte candidata em 2010 ou antes (`ano_coorte_candidata`
em `outputs/diagnostics/cadastro_causal_tratamento_fase_ii.csv`). Para
esses casos, a integração territorial registrada pelo Censo de 2010 pode,
em princípio, já incorporar deslocamentos ou transformações contemporâneos
ou posteriores à implantação da Rede Federal. Este diagnóstico não
demonstra que isso efetivamente ocorreu, mas identifica risco de
condicionamento em informação contemporânea ou posterior ao tratamento
caso o pertencimento ao arranjo seja usado para selecionar ou excluir
controles das coortes de 2009 e 2010. Essa seleção poderia introduzir
risco de endogeneidade e viés de seleção justamente por utilizar
informação potencialmente afetada pelo tratamento.

Essa limitação tem duas direções, não apenas uma:

- **Coortes com `ano_coorte_candidata <= 2010`** (48 dos 129 candidatos à
  amostra principal: 21 em 2009, 27 em 2010) — para a coorte de 2009, a
  informação do arranjo de 2010 é posterior ao início do tratamento; para
  a coorte de 2010, é contemporânea a ele. Em ambos os casos, a
  classificação pode já refletir deslocamentos ou integração
  contemporâneos ou posteriores ao início do tratamento, configurando
  risco de informação pós-tratamento.
- **Coortes com `ano_coorte_candidata > 2010`** — a classificação do
  arranjo é anterior ao início do tratamento, mas pode estar desatualizada
  e não capturar mudanças de integração territorial ocorridas depois de
  2010 (ver seção 9).

Pertencer ao mesmo arranjo que um Fase II não prova ocorrência de
spillover, e estar fora de qualquer arranjo não prova ausência de
spillover ou de integração econômica — em ambos os casos o arranjo é, no
melhor cenário, uma aproximação parcial e datada de 2010.

Por essa razão, sem uma medida funcional inequivocamente pré-tratamento,
a classificação dos Arranjos Populacionais de 2010 deve permanecer como
diagnóstico ou análise de sensibilidade. Ela não deve ser adotada
automaticamente como regra causal principal e não transforma os
municípios restantes em controles causalmente válidos. A preservação de
4.819 candidatos e da cobertura por UF (nenhuma UF zerada; 93 tratados
candidatos das coortes 2010–2011 mantendo controles na própria UF)
demonstra apenas viabilidade amostral, não validade causal.

## 6. O que esta rotina não demonstra

- **Pertencer ao mesmo arranjo populacional de um Fase II não demonstra
  contaminação efetiva por spillover.** O arranjo mede integração
  funcional em 2010 (antes ou durante o início de parte das coortes de
  tratamento); não mede se algum mecanismo de spillover (deslocamento de
  estudantes/trabalhadores do campus, mercado de trabalho compartilhado)
  efetivamente operou entre os dois municípios específicos.
- **Não pertencer a nenhum arranjo não demonstra ausência de spillover
  nem de integração territorial.** A metodologia do IBGE só reconhece
  arranjo quando a integração observada em 2010 ultrapassa os limiares
  metodológicos do próprio estudo — um candidato pode ter deslocamento
  pendular relevante com um Fase II sem que a dupla tenha sido
  classificada como arranjo (limiares não divulgados nesta rotina), ou
  pode ter desenvolvido integração após 2010, fora da janela da fonte.
- **Município sem arranjo não é automaticamente um controle causal
  válido.** A ausência de arranjo é apenas a ausência de um tipo
  específico de evidência de integração funcional — as demais condições
  de validade causal (suporte comum, balanceamento, ausência de outras
  formas de contaminação) permanecem inteiramente em aberto.
- **Nenhuma política de spillover definitiva foi escolhida por esta
  rotina.** O cruzamento com as flags de 25/50/100 km é apresentado como
  insumo diagnóstico adicional, não como critério de exclusão.
- **Nenhum outcome econômico foi usado.** Nenhuma variável do CEMPRE,
  RAIS, PIB ou de qualquer outcome pós-tratamento entra nesta rotina,
  direta ou indiretamente (ver também seção 3.1).

## 7. Schema dos artefatos

### Composição de arranjos (interino)

`data/interim/arranjos_populacionais_municipios_2010.parquet` — 953
linhas (uma por município participante de algum arranjo):

| Coluna | Tipo | Descrição |
|---|---|---|
| `codigo_municipio_ibge` | string (7 dígitos) | reconciliado da planilha bruta |
| `codigo_arranjo_populacional` | string | identificador derivado do nome oficial (seção 4) |
| `nome_arranjo_populacional` | string | nome exatamente como publicado na Tabela 1.1 |

### Diagnóstico de integração funcional

`data/processed/diagnostico_arranjos_populacionais_fase_ii.parquet` —
uma linha por candidato do pool (exatamente 4.964 linhas):

| Coluna | Tipo | Descrição |
|---|---|---|
| `codigo_municipio_ibge`, `municipio`, `uf` | string | candidato, herdados do pool candidato aprovado |
| `fl_pertence_arranjo_populacional` | bool | participa de algum dos 294 arranjos |
| `codigo_arranjo_populacional`, `nome_arranjo_populacional` | string (nulos se `fl_pertence_arranjo_populacional=False`) | identificador e nome do arranjo |
| `quantidade_fase_ii_no_arranjo` | int | quantos dos 147 Fase II compartilham o mesmo arranjo (0 se nenhum ou se o candidato não tem arranjo) |
| `codigos_fase_ii_no_arranjo` | string, `;`-separado, ordenado pelo menor código | lista determinística; `""` se `quantidade_fase_ii_no_arranjo=0` |
| `fl_mesmo_arranjo_populacional_fase_ii` | bool | `quantidade_fase_ii_no_arranjo > 0` |
| `distancia_sedes_km`, `fl_ate_25_km`, `fl_ate_50_km`, `fl_ate_100_km` | float / bool | **preservados sem nenhuma alteração** de `diagnostico_distancias_spillover_fase_ii.parquet` |

### Resumo diagnóstico

`outputs/diagnostics/resumo_arranjos_populacionais_fase_ii.csv` — três
seções identificadas pela coluna `secao`: `geral` (contagens nacionais e
cruzamentos com as flags de distância), `por_uf` e `por_macrorregiao`
(mesmas contagens de pertencimento e integração, desagregadas).

## 8. Validações executadas

Ver `validate_pool_candidato`, `validate_fase_ii_municipios`,
`validate_diagnostico_distancias_bruto`, `validate_arranjos_populacionais`
e `validate_diagnostico` em
[`src/constroi_diagnostico_arranjos_populacionais_fase_ii.py`](../../src/constroi_diagnostico_arranjos_populacionais_fase_ii.py).
Toda violação levanta `ValueError` com exemplos concretos. Entre outras:
cardinalidade exata dos insumos (4.964 e 147), unicidade de código nas
três fontes (inclusive "cada município pertence a no máximo um
arranjo"), `merge` com `validate` apropriado (`one_to_one` para o
cruzamento com distâncias já calculadas, `many_to_one` para o
cruzamento com a composição de arranjos), preservação exata do conjunto
de candidatos, tratamento explícito dos candidatos sem arranjo
(identificador nulo, quantidade zero, flag falsa), coerência entre a
lista de códigos Fase II do arranjo e a contagem, ordenação
determinística da lista, todo código listado pertencente ao conjunto
oficial dos 147, e **verificação byte-a-byte de que `distancia_sedes_km`
e as três flags de limiar não foram alteradas** em relação ao
diagnóstico de distâncias original.

## 9. Limitações metodológicas

- **Geodatabase Access não extraída.** O código numérico oficial
  (`CodArranjo`) do IBGE não foi obtido — o identificador desta rotina é
  derivado do nome publicado (seção 4), não da chave interna oficial.
- **Cobertura parcial por desenho do próprio produto IBGE.** Apenas 953
  dos ~5.570 municípios brasileiros participam de algum arranjo — a
  imensa maioria dos candidatos (4.242 de 4.964) simplesmente não tem
  esse tipo de dado, o que é uma característica do produto do IBGE, não
  uma falha desta rotina.
- **Direção temporal dos Arranjos de 2010 em relação ao tratamento (ver
  seção 5.1).** A limitação tem duas direções, não apenas uma:
  - para os 48 dos 129 candidatos à amostra principal com
    `ano_coorte_candidata <= 2010` (21 em 2009, 27 em 2010), a
    classificação do arranjo de 2010 é posterior ao início do tratamento
    para a coorte de 2009 e contemporânea a ele para a coorte de 2010 —
    em ambos os casos há risco de que ela já incorpore deslocamentos ou
    mudanças territoriais contemporâneos ou posteriores à implantação da
    Rede Federal, o que configuraria condicionamento em informação
    pós-tratamento caso essa classificação seja usada para selecionar ou
    excluir controles, com risco de endogeneidade e de viés de seleção;
  - para coortes de tratamento posteriores a 2010, a integração funcional
    pode ter mudado desde então (novas rodovias, novos polos econômicos)
    sem que a fonte de 2010 capture essa mudança, configurando risco de
    classificação desatualizada.
  Nenhuma das duas direções é demonstrada por este diagnóstico como
  tendo efetivamente ocorrido; ambas são riscos de identificação, não
  constatações de efeito.
- **Nenhuma validação dos limiares metodológicos internos do IBGE.** Este
  projeto não teve acesso aos limiares exatos (ex.: percentual mínimo de
  deslocamento) usados pelo IBGE para classificar um município como
  parte de um arranjo — a rotina apenas herda o resultado já classificado
  pelo IBGE, sem recalculá-lo.
- **Nenhum município foi removido do pool.** O pool candidato permanece
  intacto — as flags produzidas aqui são exclusivamente diagnósticas.
- **Nenhum resultado econômico foi consultado** (seção 3.1).

## 10. Próximos passos (fora do escopo desta rotina)

Assim como o diagnóstico de distâncias, este diagnóstico de integração
funcional é apenas mais um insumo quantitativo para a decisão futura,
fundamentada e documentada, sobre a regra de spillover a adotar —
conforme `CONTRATO_CAUSAL.md` e `PROTOCOLO_PRE_ANALISE.md`. Nenhuma
combinação entre distância e arranjo populacional é escolhida aqui como
filtro definitivo.
