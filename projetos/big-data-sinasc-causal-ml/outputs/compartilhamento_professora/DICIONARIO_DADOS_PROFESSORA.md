# Dicionário de dados — SINASC Sudeste 2024

Este dicionário descreve as 41 colunas presentes, com o mesmo esquema, nos três conjuntos compartilhados:

- base regional A (`sinasc_sudeste_2024_base_regional.parquet`);
- população B (`sinasc_sudeste_2024_populacao_B.parquet`);
- amostra C (`sinasc_sudeste_2024_amostra_100k.csv` e `.parquet`).

## Convenções

- **Códigos originais** (colunas com o nome do campo SINASC, como `MESPRENAT` e `ESCMAE2010`) são mantidos como **texto**, exatamente como publicados, inclusive com zeros à esquerda (`'02'`, `'00'`).
- **Colunas analíticas** (recodificações, indicadores, T e Y) são **adicionais** e nunca substituem o original.
- **Ausentes:**
  - "nulo" é o campo vazio no arquivo oficial, que aparece como célula vazia no CSV;
  - "código de ignorado" é o código que o layout ou o projeto tratam como ignorado.
  - Nenhum valor foi imputado.
- **Contagens de ausência:** referem-se à base regional A (904.365 registros).
- **Papel sugerido:** proposta do projeto, sujeita à avaliação da professora.
  - X: candidata a covariável de ajuste.
  - T: exposição.
  - Y: desfecho.
  - Elegibilidade: critério de seleção da população B.
  - Auditoria: variável disponível para exame e discussão, **não** autorizada como covariável de ajuste.
- **Fontes das definições:**
  - layout oficial: *SINASC — Estrutura de 1996 a 2019* (Ministério da Saúde);
  - Manual DNV: *Declaração de Nascido Vivo — Manual de instruções para preenchimento*, 4ª ed., 2022;
  - regra do projeto: `src/amostra.py` e o contrato V2 em `src/v2_pre_estimacao.py`.

## 1. Identificação e geografia

| Nome original | Nome analítico | Descrição | Tipo | Codificações | Ausentes / ignorados (A) | Papel sugerido | Fonte da definição | Temporalidade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | `ID_REGISTRO` | Identificador pseudônimo do registro. É sequencial dentro do recorte, na ordem física do arquivo oficial, e liga A, B e C. **Não** é o `CONTADOR` do SINASC | inteiro | 1 a 904.365 | nenhum | chave técnica | criado para este compartilhamento | — |
| — | `ANO_NASCIMENTO` | Ano do arquivo SINASC. A data exata foi conferida (todas em 2024) e não é exportada | inteiro | 2024 | nenhum | auxiliar | arquivo SINASC 2024 | nascimento |
| `CODMUNRES` | (mantido) | Município de residência da mãe, código IBGE de 6 dígitos. É o critério do recorte regional | texto | 6 dígitos; `UF0000` = município ignorado na UF | 0 nulos; 30 códigos `UF0000` (MG 1, ES 3, RJ 22, SP 4) | filtro do recorte; agrupamento geográfico possível | layout oficial | declarado no parto; a residência pode ter mudado durante a gestação |
| — | `UF_RESIDENCIA_COD` | UF de residência: dois primeiros dígitos de `CODMUNRES` | texto | `31`, `32`, `33`, `35` | nenhum | X (X7 no projeto) | regra do projeto | idem |
| — | `UF_RESIDENCIA_SIGLA` | Sigla da UF de residência | texto | MG, ES, RJ, SP | nenhum | descritiva | derivada de `UF_RESIDENCIA_COD` | idem |

## 2. Características maternas candidatas a X

| Nome original | Nome analítico | Descrição | Tipo | Codificações | Ausentes / ignorados (A) | Papel sugerido | Fonte da definição | Temporalidade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `IDADEMAE` | `IDADEMAE_NUM` | Idade da mãe, em anos | original texto; analítico inteiro | analítico: 10 a 59 anos; fora dessa faixa, nulo | 0 nulos; 11 fora de 10–59 (7 com `99`) | X | layout oficial; regra do projeto | registrada no parto; difere da idade no início da gestação em menos de 1 ano |
| `ESCMAE2010` | `ESCOLARIDADE_MAE` | Escolaridade da mãe (classificação de 2010) | texto | 0 sem escolaridade; 1 fundamental I; 2 fundamental II; 3 médio; 4 superior incompleto; 5 superior completo; 9 ignorado. Analítico: 9 ou nulo → `IGNORADO` | 5.427 nulos (0,60%); 1.227 código 9 (0,14%) | X | layout oficial; regra do projeto | declarada no parto; em geral estável durante a gestação |
| `RACACORMAE` | `RACA_COR_MAE` | Raça/cor da mãe | texto | 1 branca; 2 preta; 3 amarela; 4 parda; 5 indígena. Analítico: 9 ou nulo → `IGNORADO` | 11.115 nulos (1,23%); 0 código 9 | X | layout oficial (não lista o código 9; tratado como ignorado por precaução) | característica fixa, autodeclarada |
| `ESTCIVMAE` | `SITUACAO_CONJUGAL` | Situação conjugal da mãe | texto | 1 solteira; 2 casada; 3 viúva; 4 separada judicialmente/divorciada; 5 união estável; 9 ignorada. Analítico: 9 ou nulo → `IGNORADO` | 2.591 nulos (0,29%); 1.778 código 9 (0,20%) | X | layout oficial; regra do projeto | registrada no parto; **pode ter mudado durante a gestação** |
| `PARIDADE` | `PARIDADE_CAT` | Primeira gestação ou não (campo derivado pelo sistema) | texto | 0 nulípara; 1 multípara. Analítico: 9, 99 ou nulo → `IGNORADO` | nenhum | X | layout oficial | história reprodutiva anterior à gestação atual |
| `QTDFILMORT` | `PERDAS_FETAIS_CAT` | Número de perdas fetais e abortos anteriores | texto (2 dígitos: `'00'`, `'01'`, …) | analítico: `0`; `1`; `2_OU_MAIS` (2 a 98); `IGNORADO` (99 ou nulo) | 7.255 nulos (0,80%); 7 código 99 | X | layout oficial; regra do projeto | anterior à gestação atual; baixa concordância relatada na validação da DNV (Bonilha et al., 2018) |

## 3. Exposição e desfecho

| Nome original | Nome analítico | Descrição | Tipo | Codificações | Ausentes / ignorados (A) | Papel sugerido | Fonte da definição | Temporalidade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `MESPRENAT` | `MESPRENAT_NUM` | Mês de gestação em que o pré-natal foi iniciado | original texto (`'01'`–`'09'`, `'99'`); analítico inteiro | 1 a 9 = mês; 99 = ignorado | 11.997 nulos (1,33%); 12.277 código 99 (1,36%) | base de T | layout oficial; Manual DNV 2022 | **registrado retrospectivamente no parto**; sujeito a erro de memória ou de registro |
| — | `CATEGORIA_MESPRENAT` | Faixa do mês de início, incluindo os casos sem T | texto | `MES_1_A_3`, `MES_4_A_6`, `MES_7_A_9`, `IGNORADO_99`, `AUSENTE`, `OUTRO_CODIGO` | nenhum (a coluna classifica os ausentes) | auxiliar de T | criado neste compartilhamento | idem |
| — | `T` | Exposição da formulação B | inteiro | 1 se `MESPRENAT` 1–3; 0 se 4–6; nulo nos demais casos | nulo em 37.783 registros de A (mês 7–9, 99 ou ausente) | **T** | contrato V2 do projeto (formulação B) | momento de início do pré-natal; T = 0 **não** significa ausência de pré-natal |
| `PESO` | `PESO_NUM` | Peso ao nascer, em gramas | original texto; analítico inteiro | gramas | 18 nulos; 1.266 abaixo de 500 g; 14 acima de 6.000 g | base de Y; elegibilidade | layout oficial | medido no nascimento |
| — | `Y` | Baixo peso ao nascer | inteiro | 1 se 500 ≤ `PESO` < 2.500 g; 0 se 2.500 ≤ `PESO` ≤ 6.000 g; nulo nos demais casos | nulo em 1.298 registros de A | **Y** | definição da OMS (< 2.500 g); faixa 500–6.000 g é regra de qualidade do projeto | desfecho, posterior à exposição |

Na base A, T e Y são calculados para todos os registros, independentemente dos demais critérios de elegibilidade. A população analítica é definida por `ELEGIVEL_B`.

## 4. Elegibilidade da população B

| Nome original | Nome analítico | Descrição | Tipo | Codificações | Ausentes / ignorados (A) | Papel sugerido | Fonte da definição | Temporalidade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GRAVIDEZ` | — | Tipo de gravidez | texto | 1 única; 2 dupla; 3 tripla ou mais; 9 ignorado | 299 nulos (0,03%); 18 código 9 | elegibilidade | layout oficial | registrado no parto |
| — | `FLAG_GESTACAO_UNICA` | Gestação única | inteiro 0/1 | 1 se `GRAVIDEZ` = 1 | nenhum | elegibilidade | regra do projeto | — |
| — | `FLAG_PESO_VALIDO` | Peso dentro da faixa aceita | inteiro 0/1 | 1 se 500 ≤ `PESO` ≤ 6.000 g | nenhum | elegibilidade | regra do projeto | — |
| — | `FLAG_MESPRENAT_CONHECIDO` | Mês de início do pré-natal conhecido | inteiro 0/1 | 1 se `MESPRENAT` ∈ {1, …, 9} | nenhum | elegibilidade (auxiliar) | regra do projeto | — |
| — | `FLAG_MESPRENAT_1_A_6` | Mês de início compatível com a formulação B | inteiro 0/1 | 1 se `MESPRENAT` ∈ {1, …, 6} | nenhum | elegibilidade | contrato V2 (B) | — |
| — | `ELEGIVEL_B` | Pertence à população analítica B | inteiro 0/1 | 1 = `FLAG_GESTACAO_UNICA` × `FLAG_PESO_VALIDO` × `FLAG_MESPRENAT_1_A_6` | nenhum | elegibilidade | contrato V2 (B) | — |
| — | `MOTIVOS_NAO_ELEGIBILIDADE_B` | Todos os motivos de exclusão do registro, separados por `;` | texto | `MESPRENAT_AUSENTE`, `MESPRENAT_IGNORADO_99`, `MESPRENAT_CODIGO_INVALIDO`, `MESPRENAT_7_A_9`, `PESO_AUSENTE_OU_NAO_NUMERICO`, `PESO_FORA_500_6000`, `GRAVIDEZ_MULTIPLA`, `GRAVIDEZ_IGNORADA_OU_AUSENTE` | nulo quando `ELEGIVEL_B` = 1 | elegibilidade (auditoria) | criado neste compartilhamento | — |
| — | `MOTIVO_PRINCIPAL_EXCLUSAO_B` | Primeiro motivo na ordem de filtros do projeto: mês desconhecido → peso → gestação única → mês 7–9 | texto | `MESPRENAT_DESCONHECIDO`, `PESO_INVALIDO`, `GESTACAO_NAO_UNICA`, `MESPRENAT_7_A_9` | nulo quando `ELEGIVEL_B` = 1 | elegibilidade (auditoria) | criado neste compartilhamento | — |

## 5. Variáveis de auditoria ou candidatas à discussão

Estas variáveis estão nos arquivos para que a professora possa examiná-las. **Sua presença não representa autorização metodológica para incluí-las em X.** Várias são medidas durante ou depois da exposição e podem atuar como mediadoras ou *colliders*, ou induzir viés de seleção se usadas para ajuste ou restrição.

| Nome original | Nome analítico | Descrição | Tipo | Codificações | Ausentes / ignorados (A) | Papel sugerido | Fonte da definição | Temporalidade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `CONSPRENAT` | — | Número de consultas de pré-natal | texto (inteiro) | número de consultas; 99 tratado como provável ignorado (não confirmado literalmente no layout) | 7.537 nulos (0,83%); 2.255 código 99 (0,25%) | auditoria (mediadora potencial) | layout oficial | **pós-exposição:** acumula-se depois do início do pré-natal |
| `CONSULTAS` | — | Faixa do número de consultas | texto | 1 nenhuma; 2 de 1 a 3; 3 de 4 a 6; 4 sete ou mais; 9 ignorado | 20 nulos; 2.311 código 9 (0,26%) | auditoria (mediadora potencial) | layout oficial | pós-exposição |
| `SEMAGESTAC` | — | Semanas de gestação ao nascer | texto (inteiro) | semanas (19 a 45 no recorte) | 3.695 nulos (0,41%) | auditoria (mediadora ou *collider*) | layout oficial | determinada no fim da gestação; limita a oportunidade de início tardio |
| `GESTACAO` | — | Faixa de idade gestacional ao nascer | texto | 1 menos de 22 semanas; 2 22–27; 3 28–31; 4 32–36; 5 37–41; 6 42 ou mais; 9 ignorado | 3.682 nulos (0,41%); 13 código 9 | auditoria | layout oficial | idem |
| `TPMETESTIM` | — | Método de estimativa da idade gestacional | texto | 1 exame físico; 2 outro método; 9 ignorado. O código **8** aparece em 350.147 registros (38,7%) e **não consta** do layout disponível; significado não confirmado | 3.695 nulos; 47.024 código 9 (5,20%) | auditoria (qualidade de `SEMAGESTAC`) | layout oficial | registro do parto |
| `PARTO` | — | Tipo de parto | texto | 1 vaginal; 2 cesáreo; 9 ignorado | 318 nulos (0,04%); 17 código 9 | auditoria | layout oficial | **pós-exposição** (no parto) |
| `KOTELCHUCK` | — | Índice de Kotelchuck de adequação do pré-natal | texto | 1 a 5 e 9. Significado dos códigos **não confirmado** no layout disponível. Convenção usual dos painéis do DATASUS: 1 não realizou pré-natal; 2 inadequado; 3 intermediário; 4 adequado; 5 mais que adequado; 9 não classificado | 0 nulos; 20.632 código 9 (2,28%) | auditoria | layout oficial (descrição sem códigos) | **combina o mês de início (T) com o número de consultas**; é parcialmente função de T |
| `QTDGESTANT` | — | Número de gestações anteriores | texto (2 dígitos) | contagem; 99 tratado como provável ignorado | 7.225 nulos (0,80%); 4 código 99 | candidata à discussão | layout oficial | anterior à gestação atual; sobrepõe-se a `PARIDADE` |
| `QTDFILVIVO` | — | Número de filhos vivos | texto (2 dígitos) | contagem; 99 tratado como provável ignorado | 4.966 nulos (0,55%); 5 código 99 | candidata à discussão | layout oficial | história reprodutiva; registrada no parto |

## 6. Campos do SINASC deliberadamente não exportados

Por privacidade ou por não serem necessários à avaliação, os arquivos **não** contêm:

- identificadores e datas: `CONTADOR`, `DTNASC`, `HORANASC`, `DTNASCMAE`, `DTULTMENST`, `DTCADASTRO`, `DTRECEBIM`, `DTRECORIGA`, `DTDECLARAC`;
- dados do lote e do sistema: `NUMEROLOTE`, `DIFDATA`, `OPORT_DN`;
- local de ocorrência e estabelecimento: `CODESTAB`, `CODMUNNASC`, `LOCNASC`;
- ocupação e naturalidade da mãe: `CODOCUPMAE`, `NATURALMAE`, `CODMUNNATU`, `CODUFNATU`;
- idade do pai: `IDADEPAI`;
- demais campos do recém-nascido e da assistência ao parto, como Apgar, anomalias, sexo e grupo de Robson.

O dicionário técnico completo das 62 colunas brutas do SINASC está no repositório do projeto (`docs/entrega/DICIONARIO_TECNICO.md`) e pode ser enviado se a professora quiser examinar outro campo.
