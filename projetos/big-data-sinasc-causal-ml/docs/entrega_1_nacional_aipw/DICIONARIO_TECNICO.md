# Dicionário técnico — SINASC 2014–2024

Material de apoio para a aula. A **Parte A** descreve as variáveis que o projeto usa, ou deliberadamente não usa, e como cada uma foi codificada. A **Parte B** lista todas as 62 colunas brutas encontradas nos arquivos de 2014 a 2024.

- **Fontes:**
  - layout oficial *SINASC: Estrutura de 1996 a 2019* (MS/SVS/CGIAE), arquivo `data/raw/SINASC_Estrutura.pdf`;
  - [dicionário analítico 2024](../dados/DICIONARIO_ANALITICO_SINASC_2024.md);
  - código de construção da amostra (`src/amostra.py`);
  - [contrato V2](../temporal/CONTRATO_V2_PRE_ESTIMACAO.md).
- **Percentuais de ausência:** salvo indicação, referem-se à base bruta de 2024 (N = 2.389.325). "Analítico" refere-se à população analítica histórica (A) de 2024 (N = 2.251.570).
- **Versão em CSV da Parte B:** [outputs/entrega_1_nacional_aipw/dicionario_raw_2014_2024.csv](../../outputs/entrega_1_nacional_aipw/dicionario_raw_2014_2024.csv).

---

## Parte A — Dicionário analítico

### A.1 Variáveis do modelo (Y, T e X)

| Campo original | Variável analítica | Papel | Tipo | Descrição | Codificação / regra | Missing / ignorado | Uso no modelo | Observação |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `PESO` | `Y_BAIXO_PESO` | **Y** (desfecho) e elegibilidade | binária (0/1), derivada de inteiro em gramas | Peso ao nascer em gramas | Y = 1 se `PESO` < 2.500 g; Y = 0 se ≥ 2.500 g. Elegível só com 500 ≤ `PESO` ≤ 6.000 g | Ausente 0,009% (bruto 2024). Fora de 500–6.000 g: 3.471 registros em 2024, excluídos | Alvo dos modelos m₀ e m₁ | Definição de BPN da OMS. A faixa 500–6.000 g é regra de qualidade do projeto, não da OMS |
| `MESPRENAT` | `tratamento` (T) | **T** (exposição) | binária (0/1), derivada de mês 1–9 | Mês de gestação em que iniciou o pré-natal | T = 1 se 1–3. T = 0 se 4–6 (B, principal), 4–5 (C) ou 4–9 (A, histórica). Meses 7–9 saem de B; 6–9 saem de C | Vazio 1,82% e código 99 1,57% (bruto 2024); 7,57% combinados em 2014. Ficam **fora de T**, sem imputação | Alvo do modelo de propensão e(X) | 99 = codificação operacional observada de "ignorado", sem confirmação literal no Manual DNV 2022. Não significa "sem pré-natal". Registro retrospectivo |
| `IDADEMAE` | `IDADEMAE_NUM` (**X1**) | X | numérica contínua (anos) | Idade da mãe | Aceita entre 10 e 59 anos; fora disso, ausente | Ausente no analítico: 32 registros (2024). No modelo: imputação pela mediana do treino com indicador de ausência | Propensão e desfechos | Medida no parto. Proxy de condição pré-gestacional |
| `ESCMAE2010` | `ESCOLARIDADE_MAE` (**X2**) | X | categórica | Escolaridade da mãe (categorias de 2010) | 0 sem escolaridade; 1 fundamental I; 2 fundamental II; 3 médio; 4 superior incompleto; 5 superior completo; 9 ou vazio → `IGNORADO` | Analítico 2024: 0,48% `IGNORADO` (bruto: ausente 0,87% e ignorado 0,24%) | *One-hot* (logística) ou categórica nativa (HGB) | `ESCMAE` (antiga, em anos de estudo) não é usada |
| `RACACORMAE` | `RACA_COR_MAE` (**X3**) | X | categórica | Raça/cor da mãe | 1 branca; 2 preta; 3 amarela; 4 parda; 5 indígena; 9 ou vazio → `IGNORADO` | Analítico 2024: 1,25% (2014: 3,45%) | Idem | O layout não lista código 9 para este campo; por precaução, a regra trata 9 e vazio como `IGNORADO` |
| `ESTCIVMAE` | `SITUACAO_CONJUGAL` (**X4**) | X | categórica | Situação conjugal da mãe | 1 solteira; 2 casada; 3 viúva; 4 separada/divorciada; 5 união estável; 9 ou vazio → `IGNORADO` | Analítico 2024: 0,61% (bruto: ausente 0,39% e ignorado 0,28%) | Idem | Proxy de apoio social |
| `PARIDADE` | `PARIDADE_CAT` (**X5**) | X | categórica binária | Primeira gestação ou não | 0 nulípara; 1 multípara; 9/99 ou vazio → `IGNORADO` | 0% nos onze anos | Idem | Campo derivado pelo sistema |
| `QTDFILMORT` | `PERDAS_FETAIS_CAT` (**X6**) | X | categórica ordinal | Número de perdas fetais e abortos anteriores | 0 → `0`; 1 → `1`; 2 a 98 → `2_OU_MAIS`; demais → `IGNORADO` | Analítico 2024: 1,88% (2014: 8,37%) | Idem | Baixa concordância em validação local do modelo antigo da DNV (Bonilha et al., 2018). Sensibilidade sem esta variável ainda não executada |
| `CODMUNRES` | `UF_RESIDENCIA` (**X7**) e cluster | X e auxiliar | categórica (27 UFs); código IBGE de 6 dígitos | Município de residência da mãe | X7 = 2 primeiros dígitos (UF). Malformado → `IGNORADO` (0 casos em todos os anos) | 0% | X7 na propensão e nos desfechos; o município inteiro define os clusters do erro-padrão | Cerca de 5.580 municípios por ano. O município **não** entra em X |

### A.2 Variáveis auxiliares e de elegibilidade

| Campo original | Variável analítica | Papel | Tipo | Descrição | Codificação / regra | Missing / ignorado | Uso no modelo | Observação |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GRAVIDEZ` | `gravidez_num` | Elegibilidade | categórica | Tipo de gravidez | 1 única; 2 dupla; 3 tripla ou mais; 9 ignorado. População principal: só `GRAVIDEZ` = 1 | Ausente 0,05% e ignorado 0,003%; excluídos | Filtro; não entra em X | Múltiplos excluídos (53.205 em 2024, após as demais regras). Incluí-los muda a população-alvo |
| `DTNASC` | ano de nascimento | Elegibilidade | data (ddmmaaaa, texto) | Data de nascimento | Data válida e pertencente ao ano do arquivo | 0 datas inválidas ou fora do ano, em todos os anos | Define o corte anual | Não entra em X |
| `CONTADOR` | chave | Auxiliar | texto | Número identificador do registro | Chave = (ano, UF de residência, `CONTADOR`), única em todos os anos | 0% | Ordenação e reprodutibilidade das partições | Em 2014–2017, `CONTADOR` sozinho não é único; a chave composta é. Não é identificador longitudinal |

### A.3 Variáveis deliberadamente fora de X

| Campo original | Variável analítica | Papel | Tipo | Descrição | Codificação / regra | Missing / ignorado | Uso no modelo | Observação |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `CONSPRENAT` | — | Auditoria (mediadora potencial) | inteiro | Número de consultas de pré-natal | Não usado em X nem em T. `CONSPRENAT` = 0 **não** é convertido em controle | Ausente 1,28% | **Não usado** | Consultas acumulam após o início: estão no caminho T → Y |
| `CONSULTAS` | — | Auditoria (mediadora potencial) | categórica | Faixa de consultas (1 nenhuma; 2 de 1–3; 3 de 4–6; 4 7+; 9 ignorado) | Não usado | Ausente 0,13% e ignorado 0,29% | **Não usado** | Mesmo motivo de `CONSPRENAT` |
| `SEMAGESTAC` / `GESTACAO` | — | Auditoria (mediadora/*collider*) | inteiro (semanas) / categórica (faixas 1–6, 9) | Idade gestacional ao nascer | Usada só na auditoria temporal 09c (gestação × mês de início) | Ausente 0,75% / 0,74% | **Não usado** | Ajustar por idade gestacional enviesa o contraste (Wilcox et al., 2011). Não se restringe a análise a nascimentos a termo |
| `PARTO` | — | Auditoria (pós-tratamento) | categórica | Tipo de parto (1 vaginal; 2 cesáreo; 9 ignorado) | Não usado | Ausente 0,05% | **Não usado** | Ocorre depois da exposição |
| `APGAR1` / `APGAR5` | — | Não utilizado (pós-tratamento) | inteiro 0–10 | Apgar no 1º e no 5º minuto | Não usado | Ausente 0,99% / 0,99% | **Não usado** | Desfecho neonatal, medido após o nascimento |
| `KOTELCHUCK` | — | Auditoria | categórica | Índice de Kotelchuck de adequação do pré-natal | Não usado em X nem em T | Ausente 0%. Significado dos códigos não confirmado documentalmente | **Não usado** | Combina início **e** número de consultas, o que mistura T com a mediadora |

**Por que essas variáveis ficam de fora?** As covariáveis X devem descrever a gestante **antes** da exposição. Variáveis medidas depois do início do pré-natal (consultas), no parto (tipo de parto, Apgar) ou que resultam da duração da gestação (idade gestacional) não confundem a relação T → Y. Elas fazem parte dela ou selecionam a amostra; ajustar por elas introduziria viés em vez de removê-lo.

---

## Parte B — Dicionário raw (todas as colunas, 2014–2024)

Construída automaticamente a partir do cabeçalho do CSV de cada ZIP anual e do schema dos Parquets convertidos, sem varrer os 30,5 milhões de registros. As descrições vêm do layout oficial *SINASC: Estrutura de 1996 a 2019*.

- **Colunas por ano:** 61 de 2014 a 2022; 62 em 2023–2024, com o acréscimo de `OPORT_DN`. União: **62 campos distintos**.
- **Tipo físico:** todos os campos são texto no CSV (separador `;`, UTF-8) e foram preservados como texto (`BYTE_ARRAY/UTF8`) no Parquet. O layout oficial declara todos como caractere (C).
- **Grafia:** em 2016, todas as colunas vêm em minúsculas. Em 2023–2024, apenas `contador` vem em minúsculas. O projeto normaliza os nomes para maiúsculas.
- **Campos sem descrição oficial confirmada:** `OPORT_DN` (`DESCRICAO_NAO_CONFIRMADA`). Os códigos de `KOTELCHUCK` também não estão documentados no layout.
- **Campos que constam do layout, mas não dos arquivos 2014–2024:** `CODCART`, `CODMUNCART`, `DTRECORIG`, `DTREGCART`, `NUMREGCART`, `RACACORN`, `RACACOR_RN`, `UFINFORM`.
- **Papéis:** Y, T, X, elegibilidade, auxiliar, auditoria e não utilizado. Um campo pode ter dois papéis (por exemplo, `PESO` é Y e também critério de elegibilidade).
- **Descrições longas:** foram encurtadas aqui; o texto integral está no CSV.

<!-- PARTE_B_INICIO -->
| # | Campo | Anos presentes | Layout oficial (tipo, tamanho; desde) | Papel no projeto | Uso / regra | Descrição oficial resumida |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | `CONTADOR` | 2014–2024 (11) | C, 8; 1996 | **auxiliar** | Compõe a chave (ano, UF de residência, CONTADOR) | Número identificador do registro |
| 2 | `ORIGEM` | 2014–2024 (11) | C, 6; 2010 | não utilizado | — | Banco de dados de Origem 1- Oracle, 2- FTP, 3- SEAD |
| 3 | `CODESTAB` | 2014–2024 (11) | C, 8; 2000 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Código do estabelecimento de saúde onde ocorreu o nascimento |
| 4 | `CODMUNNASC` | 2014–2024 (11) | C, 10; 1996 | não utilizado | — | Código IBGE do município de nascimento |
| 5 | `LOCNASC` | 2014–2024 (11) | C, 7; 1996 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Local de nascimento: 1 – Hospital; 2 – Outros estabelecimentos de saúde; 3 – Domicílio; 4 – Outros; 5- Aldeia Indígena. |
| 6 | `IDADEMAE` | 2014–2024 (11) | C, 8; 1996 | **X** | X1 IDADEMAE_NUM (10–59 anos; fora disso = ausente) | Idade da mãe |
| 7 | `ESTCIVMAE` | 2014–2024 (11) | C, 9; 1996 | **X** | X4 SITUACAO_CONJUGAL (9/vazio = IGNORADO) | Situação conjugal da mãe: 1– Solteira; 2– Casada; 3– Viúva; 4– Separada judicialmente/divorciada; 5– União estável; 9– Ignorada. |
| 8 | `ESCMAE` | 2014–2024 (11) | C, 6; 1996 | **auditoria** | Escolaridade antiga; não usada em X (usa-se ESCMAE2010) | Escolaridade, em anos de estudo concluídos: 1 – Nenhuma; 2 – 1 a 3 anos; 3 – 4 a 7 anos; 4 – 8 a 11 anos; 5 – 12 e mais; 9 – Ignorado. |
| 9 | `CODOCUPMAE` | 2014–2024 (11) | C, 10; 1996 | não utilizado | — | Código de ocupação da mãe conforme tabela do CBO (Código Brasileiro de Ocupações). |
| 10 | `QTDFILVIVO` | 2014–2024 (11) | C, 10; 1996 | **auditoria** | Inventário de qualidade; não entra em X | Número de filhos vivos |
| 11 | `QTDFILMORT` | 2014–2024 (11) | C, 10; 1996 | **X** | X6 PERDAS_FETAIS_CAT (0, 1, 2_OU_MAIS, IGNORADO) | Número de perdas fetais e abortos |
| 12 | `CODMUNRES` | 2014–2024 (11) | C, 9; 1996 | **X; auxiliar** | X7 UF_RESIDENCIA (2 primeiros dígitos); município = cluster da inferência | Código IBGE do município de residência |
| 13 | `GESTACAO` | 2014–2024 (11) | C, 8; 1996 | **auditoria** | Faixa de idade gestacional: mediadora/collider; só auditoria | Semanas de gestação: 1– Menos de 22 semanas; 2– 22 a 27 semanas; 3– 28 a 31 semanas; 4– 32 a 36 semanas; 5– 37 a 41 semanas; 6– 42 semanas e mais; 9– … |
| 14 | `GRAVIDEZ` | 2014–2024 (11) | C, 8; 1996 | **elegibilidade** | População principal: gestação única (GRAVIDEZ = 1) | Tipo de gravidez: 1– Única; 2– Dupla; 3– Tripla ou mais; 9– Ignorado. |
| 15 | `PARTO` | 2014–2024 (11) | C, 5; 1996 | **auditoria** | Pós-tratamento; só diagnóstico | Tipo de parto: 1– Vaginal; 2– Cesário; 9– Ignorado |
| 16 | `CONSULTAS` | 2014–2024 (11) | C, 9; 1996 | **auditoria** | Faixa de consultas: mediadora potencial; não entra em X | Número de consultas de pré‐natal. Valores: 1– Nenhuma; 2– de 1 a 3; 3– de 4 a 6; 4– 7 e mais; 9– Ignorado. |
| 17 | `DTNASC` | 2014–2024 (11) | C, 8; 1996 | **elegibilidade** | Data válida e ano de nascimento do arquivo | Data de nascimento: dd mm aaaa |
| 18 | `HORANASC` | 2014–2024 (11) | C, 8; 1997 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Horário de nascimento |
| 19 | `SEXO` | 2014–2024 (11) | C, 4; 1996 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Sexo: 1- M – Masculino; 2- F – Feminino; 0- I – ignorado |
| 20 | `APGAR1` | 2014–2024 (11) | C, 6; 1996 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Apgar no 1º minuto 00 a a10 |
| 21 | `APGAR5` | 2014–2024 (11) | C, 6; 1996 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Apgar no 5º minuto 00 a 10 |
| 22 | `RACACOR` | 2014–2024 (11) | C, 7; 1996 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Tipo de raça e cor do nascido: 1– Branca; 2– Preta; 3– Amarela; 4– Parda; 5– Indígena. |
| 23 | `PESO` | 2014–2024 (11) | C, 4; 1996 | **Y; elegibilidade** | Y = 1 se PESO < 2.500 g; elegível se 500 ≤ PESO ≤ 6.000 g | Peso ao nascer em gramas. |
| 24 | `IDANOMAL` | 2014–2024 (11) | C, 8; 1997 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Anomalia identificada: 1– Sim; 2– Não; 9– Ignorado |
| 25 | `DTCADASTRO` | 2014–2024 (11) | C, 10; 2006 | não utilizado | — | Data do cadastro da DN no sistema |
| 26 | `CODANOMAL` | 2014–2024 (11) | C, 20; 1996 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Código da anomalia (CID-10) |
| 27 | `NUMEROLOTE` | 2014–2024 (11) | C, 10; 2010 | não utilizado | — | Número do lote |
| 28 | `VERSAOSIST` | 2014–2024 (11) | C, 10; 2010 | não utilizado | — | Versão do sistema |
| 29 | `DTRECEBIM` | 2014–2024 (11) | C, 9; 2006 | não utilizado | — | Data do último recebimento do lote, dada pelo Sisnet. |
| 30 | `DIFDATA` | 2014–2024 (11) | C, 8; 2010 | não utilizado | — | Diferença entre a data de Nascimento e data do recebimento original da DN ([DTNASC] – [DTRECORIGA]) |
| 31 | `DTRECORIGA` | 2014–2024 (11) | C, 10; 2014 | não utilizado | — | Cria-se campo DTRECORIGA e copia os valores de DTRECORIG para esse campo. Se DTRECORIGA = Nulo, copia os valores de DTRECEBIM. Se DTRECEBIM = Nulo, … |
| 32 | `NATURALMAE` | 2014–2024 (11) | C, 10; 2010 | não utilizado | — | Se a mãe for estrangeira, constará o código do país de nascimento. |
| 33 | `CODMUNNATU` | 2014–2024 (11) | C, 10; 2010 | não utilizado | — | Código do município de naturalidade da mãe |
| 34 | `CODUFNATU` | 2014–2024 (11) | C, 9; 2013 | não utilizado | — | Código UF de naturalidade |
| 35 | `ESCMAE2010` | 2014–2024 (11) | C, 10; 2012 | **X** | X2 ESCOLARIDADE_MAE (9/vazio = IGNORADO) | Escolaridade 2010. Valores: 0 – Sem escolaridade; 1 – Fundamental I (1ª a 4ª série); 2 – Fundamental II (5ª a 8ª série); 3 – Médio (antigo 2º Grau); … |
| 36 | `SERIESCMAE` | 2014–2024 (11) | C, 10; 2010 | não utilizado | — | Série escolar da mãe. Valores de 1 a 8. |
| 37 | `DTNASCMAE` | 2014–2024 (11) | C, 9; 2010 | não utilizado | — | Data de nascimento da mãe: dd mm aaaa |
| 38 | `RACACORMAE` | 2014–2024 (11) | C, 10; 2010 | **X** | X3 RACA_COR_MAE (9/vazio = IGNORADO) | Tipo de raça e cor da mãe: 1– Branca; 2– Preta; 3– Amarela; 4– Parda; 5– Indígena. |
| 39 | `QTDGESTANT` | 2014–2024 (11) | C, 10; 2010 | **auditoria** | Inventário de qualidade; não entra em X | Número de gestações anteriores |
| 40 | `QTDPARTNOR` | 2014–2024 (11) | C, 10; 2010 | não utilizado | — | Número de partos vaginais |
| 41 | `QTDPARTCES` | 2014–2024 (11) | C, 10; 2010 | não utilizado | — | Número de partos cesáreos |
| 42 | `IDADEPAI` | 2014–2024 (11) | C, 8; 2010 | não utilizado | — | Idade do pai |
| 43 | `DTULTMENST` | 2014–2024 (11) | C, 10; 2010 | **auditoria** | Data da última menstruação; só auditoria temporal | Data da última menstruação (DUM): dd mm aaaa |
| 44 | `SEMAGESTAC` | 2014–2024 (11) | C, 10; 2010 | **auditoria** | Idade gestacional: mediadora/collider; usada só na auditoria temporal | Número de semanas de gestação. |
| 45 | `TPMETESTIM` | 2014–2024 (11) | C, 10; 2010 | **auditoria** | Método de estimativa da IG; só auditoria temporal | Método utilizado. Valores: 1– Exame físico; 2– Outro método; 9– Ignorado. |
| 46 | `CONSPRENAT` | 2014–2024 (11) | C, 10; 2010 | **auditoria** | Consultas acumuladas: mediadora potencial; não entra em X | Número de consultas pré‐natal |
| 47 | `MESPRENAT` | 2014–2024 (11) | C, 9; 2010 | **T** | T = 1 se 1–3; T = 0 se 4–6 (B), 4–5 (C) ou 4–9 (A); 99/vazio fora de T | Mês de gestação em que iniciou o pré‐natal |
| 48 | `TPAPRESENT` | 2014–2024 (11) | C, 10; 2010 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Tipo de apresentação do RN. Valores: 1– Cefálico; 2– Pélvica ou podálica; 3– Transversa; 9– Ignorado. |
| 49 | `STTRABPART` | 2014–2024 (11) | C, 10; 2010 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Trabalho de parto induzido? Valores: 1– Sim; 2– Não; 3– Não se aplica; 9– Ignorado. |
| 50 | `STCESPARTO` | 2014–2024 (11) | C, 10; 2010 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Cesárea ocorreu antes do trabalho de parto iniciar? Valores: 1– Sim; 2– Não; 3– Não se aplica; 9– Ignorado. |
| 51 | `TPNASCASSI` | 2014–2024 (11) | C, 10; 2013 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Nascimento foi assistido por? Valores: 1– Médico; 2– Enfermagem ou Obstetriz; 3– Parteira; 4– Outros; 9– Ignorado |
| 52 | `TPFUNCRESP` | 2014–2024 (11) | C, 10; 2014 | não utilizado | — | Tipo de função do responsável pelo preenchimento. Valores: 1– Médico; 2– Enfermeiro; 3– Parteira; 4– Funcionário do cartório; 5– Outros. |
| 53 | `TPDOCRESP` | 2014–2024 (11) | C, 9; 2014 | não utilizado | — | Tipo do documento do responsável. Valores: 1‐CNES; 2‐CRM; 3‐ COREN; 4‐RG; 5‐ CPF. |
| 54 | `DTDECLARAC` | 2014–2024 (11) | C, 10; 2014 | não utilizado | — | Data da declaração: dd mm aaaa |
| 55 | `ESCMAEAGR1` | 2014–2024 (11) | C, 10; 2013 | não utilizado | — | Escolaridade 2010 agregada. Valores: 00 – Sem Escolaridade; 01 – Fundamental I Incompleto; 02 – Fundamental I Completo; 03 – Fundamental II … |
| 56 | `STDNEPIDEM` | 2014–2024 (11) | C, 10; 2010 | não utilizado | — | Status de DO Epidemiológica. Valores: 1 – SIM; 0 – NÃO. |
| 57 | `STDNNOVA` | 2014–2024 (11) | C, 8; 2010 | não utilizado | — | Status de DO Nova. Valores: 1 – SIM; 0 – NÃO. |
| 58 | `CODPAISRES` | 2014–2024 (11) | C, 10; 2010 | não utilizado | — | Código do país de residência |
| 59 | `TPROBSON` | 2014–2024 (11) | C, 8; 2010 | não utilizado | Pós-nascimento/assistência ao parto: excluído de X | Código do Grupo de Robson, gerado pelo sistema |
| 60 | `PARIDADE` | 2014–2024 (11) | C, 10; 2014 | **X** | X5 PARIDADE_CAT (9/99/vazio = IGNORADO) | Define se é a primeira gravidez ou se teve mais de uma. 1 – Multípara; 0- Nulípara. |
| 61 | `KOTELCHUCK` | 2014–2024 (11) | C, 10; 2014 | **auditoria** | Índice que combina início e consultas; não entra em X nem em T | índice de Kotelchuck - Avaliação da assistência pré-natal |
| 62 | `OPORT_DN` | 2023–2024 (2) | não consta | não utilizado | — | DESCRICAO_NAO_CONFIRMADA |
<!-- PARTE_B_FIM -->
