# Metadados da base — SINASC 2014–2024

## 1. Ficha da base

| Item | Valor |
| --- | --- |
| **Dataset** | SINASC — Sistema de Informações sobre Nascidos Vivos |
| **Instituição** | Ministério da Saúde — Secretaria de Vigilância em Saúde e Ambiente / DATASUS |
| **Fonte** | Portal de Dados Abertos do SUS: <https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc> |
| **Padrão do arquivo** | `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINASC/csv/SINASC_{ano}_csv.zip` |
| **Período** | 2014–2024 |
| **Anos** | 11 (análise separada por ano de nascimento, sem *pooling*) |
| **Cobertura geográfica** | Brasil: 27 UFs e cerca de 5.580 municípios de residência por ano (5.580 a 5.587) |
| **Granularidade** | 1 linha = 1 nascido vivo = 1 Declaração de Nascido Vivo (DNV) |
| **Unidade de análise** | nascido vivo de gestação única |
| **Chave** | (ano, UF de residência, `CONTADOR`), única em todos os anos; não é identificador longitudinal |
| **Formato original** | ZIP contendo um CSV por ano (separador `;`, UTF-8) |
| **Formato analítico** | Parquet, todas as colunas como texto; consultas e transformações em DuckDB |
| **Colunas por ano** | 61 (2014–2022); 62 (2023–2024, com `OPORT_DN`); 62 campos distintos no total |
| **Volume bruto total** | **30.468.409 registros**; 9,93 GB de CSV descomprimido e 1,24 GB em ZIP |
| **População analítica histórica (A)** | 28.194.211 |
| **População principal (B)** | 27.533.362 |
| **População de sensibilidade (C)** | 26.860.501 |
| **Target** | Y = 1 se `PESO` < 2.500 g (baixo peso ao nascer); Y = 0 se ≥ 2.500 g |
| **Prevalência do target** | 6,93%–7,19% (2014–2020); 7,37% (2021); 7,85%–7,89% (2022–2024). Em 2024: 7,894891% |
| **Tratamento** | `MESPRENAT` 1–3 (T = 1) versus 4–6 (T = 0) na formulação principal B |
| **Número de features (X)** | 7: idade, escolaridade, raça/cor, situação conjugal, paridade, perdas fetais e UF |
| **Filtros** | `MESPRENAT` conhecido; 500 ≤ `PESO` ≤ 6.000 g; `GRAVIDEZ` = 1 (única); comparador restrito a 4–6 (B) ou 4–5 (C) |
| **Missing principais** | `MESPRENAT` desconhecido (99 ou vazio): 7,57% (2014) → 3,39% (2024) da base bruta. Perdas fetais `IGNORADO` no analítico: 8,37% → 1,88%. Raça/cor: 3,45% → 1,25% |
| **Software** | Python 3.11.9; DuckDB 1.5.5; pandas 3.0.6; NumPy 2.4.6; scikit-learn 1.8.0; Plotly 6.9.0 (figuras) |
| **Data de extração** | 2024: 25/09/2026. 2014–2023: 29/09/2026. Última modificação remota dos arquivos entre 21/10/2025 e 08/05/2026 |
| **Proveniência** | SHA-256 do ZIP e do Parquet registrados por ano (Apêndice A); manifestos em `outputs/temporal/manifestos/` e `data/raw/source_manifest.json` |
| **Documentação oficial** | *SINASC: Estrutura de 1996 a 2019 — Dicionário de Dados* (SHA-256 `0ffc4599…cdee4`); *Manual de preenchimento da DNV*, 4ª ed., 2022 |

## 2. Registros e colunas por ano

<!-- TABELA_ANUAL_INICIO -->
| Ano | N bruto | Colunas | N analítico (A) | % do bruto | N B | N C | Y = 1 (%) | ZIP (MB) | CSV (MB) | Última modificação remota | Acesso |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 2014 | 2.979.259 | 61 | 2.691.119 | 90,33 | 2.615.773 | 2.538.604 | 6,93 | 126,8 | 1017,0 | 21/10/2025 | 29/09/2026 |
| 2015 | 3.017.668 | 61 | 2.745.846 | 90,99 | 2.673.272 | 2.599.919 | 6,98 | 127,2 | 1031,9 | 21/10/2025 | 29/09/2026 |
| 2016 | 2.857.800 | 61 | 2.626.594 | 91,91 | 2.560.827 | 2.492.767 | 7,04 | 107,4 | 634,5 | 08/05/2026 | 29/09/2026 |
| 2017 | 2.923.535 | 61 | 2.695.676 | 92,21 | 2.630.828 | 2.562.927 | 7,03 | 119,2 | 1002,0 | 08/05/2026 | 29/09/2026 |
| 2018 | 2.944.932 | 61 | 2.734.473 | 92,85 | 2.672.423 | 2.606.245 | 7,02 | 119,6 | 1017,5 | 08/05/2026 | 29/09/2026 |
| 2019 | 2.849.146 | 61 | 2.645.383 | 92,85 | 2.586.743 | 2.524.898 | 7,19 | 115,5 | 984,1 | 08/05/2026 | 29/09/2026 |
| 2020 | 2.730.145 | 61 | 2.535.311 | 92,86 | 2.476.058 | 2.415.861 | 7,09 | 111,0 | 942,7 | 08/05/2026 | 29/09/2026 |
| 2021 | 2.677.101 | 61 | 2.481.267 | 92,68 | 2.425.844 | 2.371.495 | 7,37 | 108,6 | 923,7 | 08/05/2026 | 29/09/2026 |
| 2022 | 2.561.922 | 61 | 2.397.626 | 93,59 | 2.344.255 | 2.291.516 | 7,85 | 105,1 | 905,4 | 08/05/2026 | 29/09/2026 |
| 2023 | 2.537.576 | 62 | 2.389.346 | 94,16 | 2.340.125 | 2.291.075 | 7,89 | 106,4 | 909,2 | 08/05/2026 | 29/09/2026 |
| 2024 | 2.389.325 | 62 | 2.251.570 | 94,23 | 2.207.214 | 2.165.194 | 7,89 | 92,3 | 561,8 | 08/05/2026 | 25/09/2026 |
| **Total** | **30.468.409** | — | **28.194.211** | 92,54 | **27.533.362** | **26.860.501** | — | 1239,1 | 9930,0 | — | — |
<!-- TABELA_ANUAL_FIM -->

- **N analítico (A):** gestação única, `MESPRENAT` 1–9 conhecido e peso 500–6.000 g.
- **B e C** são subconjuntos de A (comparador 4–6 e 4–5, respectivamente). O grupo T = 1 é o mesmo nas três formulações.

## 3. Fluxo de filtros — exemplo de 2024

| Etapa | Regra | Excluídos | Restantes | % da base bruta |
| --- | --- | ---: | ---: | ---: |
| Base bruta | — | — | 2.389.325 | 100,00 |
| A0 | T conhecido (`MESPRENAT` 1–9) e `PESO` numérico positivo | 81.079 | 2.308.246 | 96,61 |
| A1 | 500 g ≤ `PESO` ≤ 6.000 g | 3.471 | 2.304.775 | 96,46 |
| A2 | Gestação única (`GRAVIDEZ` = 1) | 53.205 | 2.251.570 | 94,23 |
| B | Comparador restrito a 4–6 (exclui `MESPRENAT` 7–9) | 44.356 | 2.207.214 | 92,38 |
| C | Comparador restrito a 4–5 (exclui também `MESPRENAT` 6) | 42.020 | 2.165.194 | 90,62 |

As sete covariáveis não removem registros: missing categórico vira a categoria `IGNORADO`, e a idade ausente é imputada dentro do pipeline de modelagem.

## 4. Qualidade por ano (base bruta)

<!-- TABELA_QUALIDADE_INICIO -->
| Ano | `MESPRENAT` 99 (%) | `MESPRENAT` vazio (%) | T desconhecido (%) | Peso inválido ≤ 0 (%) | Datas inválidas | `CODMUNRES` malformado |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2014 | 3,65 | 3,83 | 7,57 | 0,054 | 0 | 0 |
| 2015 | 3,00 | 3,86 | 6,86 | 0,039 | 0 | 0 |
| 2016 | 2,73 | 3,22 | 5,95 | 0,036 | 0 | 0 |
| 2017 | 2,53 | 3,09 | 5,62 | 0,034 | 0 | 0 |
| 2018 | 2,41 | 2,50 | 4,91 | 0,032 | 0 | 0 |
| 2019 | 2,34 | 2,55 | 4,90 | 0,026 | 0 | 0 |
| 2020 | 2,48 | 2,42 | 4,90 | 0,023 | 0 | 0 |
| 2021 | 2,40 | 2,66 | 5,07 | 0,021 | 0 | 0 |
| 2022 | 2,06 | 2,00 | 4,06 | 0,015 | 0 | 0 |
| 2023 | 1,65 | 1,81 | 3,47 | 0,011 | 0 | 0 |
| 2024 | 1,57 | 1,82 | 3,39 | 0,009 | 0 | 0 |
<!-- TABELA_QUALIDADE_FIM -->

## Apêndice A — Proveniência e hashes

O SHA-256 completo de cada ZIP e de cada Parquet está nos manifestos. Aqui são mostrados os 12 primeiros caracteres.

<!-- TABELA_HASH_INICIO -->
| Ano | SHA-256 ZIP (início) | SHA-256 Parquet (início) | Arquivo local |
| --- | --- | --- | --- |
| 2014 | `892ab530ea21` | `b201bf9ecda6` | `data/raw/sinasc/2014/SINASC_2014_csv.zip` |
| 2015 | `0e35031cccc7` | `d6f1384db37c` | `data/raw/sinasc/2015/SINASC_2015_csv.zip` |
| 2016 | `a25e4d65e0eb` | `483b1036809e` | `data/raw/sinasc/2016/SINASC_2016_csv.zip` |
| 2017 | `6a526a0245e6` | `7e28ea30b56d` | `data/raw/sinasc/2017/SINASC_2017_csv.zip` |
| 2018 | `1367ac0d8350` | `cfff334ad6ec` | `data/raw/sinasc/2018/SINASC_2018_csv.zip` |
| 2019 | `4d528a8b6338` | `c0ada054bbff` | `data/raw/sinasc/2019/SINASC_2019_csv.zip` |
| 2020 | `d06af4961ab0` | `cb271925a648` | `data/raw/sinasc/2020/SINASC_2020_csv.zip` |
| 2021 | `240eb1f03aa9` | `fc349f75802c` | `data/raw/sinasc/2021/SINASC_2021_csv.zip` |
| 2022 | `89e6f791a247` | `a357f6785672` | `data/raw/sinasc/2022/SINASC_2022_csv.zip` |
| 2023 | `c4ce57f7aa53` | `66ad723138fc` | `data/raw/sinasc/2023/SINASC_2023_csv.zip` |
| 2024 | `27e55de6359e` | `a7a1618e555d` | `data/raw/SINASC_2024_csv.zip` |
<!-- TABELA_HASH_FIM -->

- **Contrato V2 congelado:** `outputs/temporal/v2_pre_estimacao/contrato_v2_congelado.json` (SHA-256 do conteúdo científico `2174989c33b3…7d0b`).
- **Código da estimação V2:** `src/estimacao_v2.py` (SHA-256 `bb3d74ec9182…24a6`, conforme `manifesto_estimacao_v2.json`).
- **Commit de referência:** `eccc1a9750b068910f5b2c4e474f26ccab14bb57`, branch `feature/expansao-temporal-sinasc`. Os arquivos da V2 ainda não estão versionados.
