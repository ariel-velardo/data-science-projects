# Dados SINASC Sudeste 2024 para avaliação de viabilidade causal

**Projeto:** Início precoce do pré-natal e baixo peso ao nascer no Brasil (SINASC 2014–2024)
**Disciplina:** Big Data & Analytics

Este pacote reúne uma amostra real dos microdados do SINASC, preparada para uma avaliação metodológica independente. O objetivo não é apresentar resultados do projeto, e sim fornecer dados completos, documentados e auditáveis para examinar se existe um desenho de inferência causal defensável para a pergunta abaixo. Nenhum estimador causal foi aplicado aos arquivos, e nenhuma seleção de registros foi orientada por resultados.

## 1. Pergunta investigada

Entre gestantes comparáveis nas características observadas, iniciar o pré-natal no 1º–3º mês de gestação está associado a menor risco de baixo peso ao nascer (< 2.500 g) do que iniciar no 4º–6º mês?

A questão de fundo é saber se essa associação pode receber interpretação causal com os dados disponíveis. Se a resposta for negativa, queremos saber qual estimando, população ou desenho seria mais adequado.

## 2. Origem dos dados

- **Fonte:** Sistema de Informações sobre Nascidos Vivos (SINASC), Ministério da Saúde, Portal de Dados Abertos do SUS: <https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc>.
- **Arquivo:** `SINASC_2024_csv.zip`, acessado em 25/09/2026 (SHA-256 `27e55de6359e1b1914301dc1d752d78e9535a7a52cc0640931dd94876aca6027`).
- **Unidade de observação:** 1 linha = 1 nascido vivo = 1 Declaração de Nascido Vivo (DNV). Gêmeos geram uma linha por recém-nascido.
- **Momento do registro:** todos os campos são preenchidos no nascimento. Não há acompanhamento longitudinal da gestante nem identificador que ligue partos da mesma mulher.
- **Layout oficial dos campos:** *SINASC — Estrutura de 1996 a 2019* e *Manual de preenchimento da DNV* (4ª ed., 2022).

## 3. Por que o Sudeste

O recorte inclui os nascimentos de **mães residentes** em Minas Gerais (31), Espírito Santo (32), Rio de Janeiro (33) e São Paulo (35), definidos pelo município de residência da mãe (`CODMUNRES`), e não pelo local do parto.

A escolha é operacional:

- reduz o volume de 2,39 milhões para 0,90 milhão de registros;
- mantém heterogeneidade geográfica e socioeconômica entre e dentro dos estados;
- não decorre de nenhum resultado do projeto.

Conclusões obtidas com este recorte não se generalizam automaticamente para outras regiões ou outros anos.

## 4. Os três conjuntos exportados

| Arquivo | Conteúdo | Registros | Tamanho |
| --- | --- | ---: | ---: |
| `sinasc_sudeste_2024_base_regional.parquet` (A) | Todos os nascimentos de 2024 do recorte regional, **antes** de qualquer filtro de elegibilidade, inclusive os registros com exposição ou desfecho incompletos | 904.365 | 10,4 MB |
| `sinasc_sudeste_2024_populacao_B.parquet` (B) | Todos os registros de A que atendem aos critérios da população analítica principal B do projeto, **sem amostragem**, sem *matching* e sem exclusão por escore de propensão | 842.998 | 9,2 MB |
| `sinasc_sudeste_2024_amostra_100k.csv` (C) | 100.000 registros sorteados aleatoriamente de A, **antes** dos filtros de elegibilidade | 100.000 | 11,4 MB |
| `sinasc_sudeste_2024_amostra_100k.parquet` (C) | A mesma amostra, em Parquet, com registros e valores idênticos aos do CSV | 100.000 | 1,2 MB |

Distribuição de A por estado: MG 219.819; ES 49.937; RJ 163.722; SP 470.887.

Na população B: 758.924 registros com T = 1, 84.074 com T = 0 e 70.725 com Y = 1.

Na amostra C, 93.208 dos 100.000 registros são elegíveis para B (`ELEGIVEL_B = 1`).

**Detalhes da amostra C:**

- amostragem aleatória simples, sem reposição, com semente 42 (`numpy.random.default_rng(42)`);
- sorteio feito sobre a lista de identificadores, sem uso de T, Y ou elegibilidade;
- as proporções por UF, elegibilidade, T e Y ficam dentro da variação esperada da amostragem.

Como a amostra é retirada de A, ela traz os indicadores de elegibilidade e permite reproduzir integralmente a seleção da população B.

**Esquema comum.** Os três conjuntos têm as mesmas 41 colunas, e um registro pode ser comparado entre eles pelo `ID_REGISTRO`. O arquivo `DICIONARIO_DADOS_PROFESSORA.md` descreve cada coluna: códigos, ausentes, papel sugerido, fonte e temporalidade.

## 5. O que representam T, Y e X

- **T (exposição):** mês de início do pré-natal registrado na DNV (`MESPRENAT`). T = 1 para início no 1º–3º mês; T = 0 para início no 4º–6º mês. T = 0 **não** significa ausência de pré-natal.
- **Y (desfecho):** baixo peso ao nascer. Y = 1 se 500 ≤ `PESO` < 2.500 g; Y = 0 se 2.500 ≤ `PESO` ≤ 6.000 g.
- **X (covariáveis candidatas):** características maternas registradas na DNV e plausivelmente anteriores ao início do pré-natal:
  - idade (`IDADEMAE`);
  - escolaridade (`ESCMAE2010`);
  - raça/cor (`RACACORMAE`);
  - situação conjugal (`ESTCIVMAE`);
  - paridade (`PARIDADE`);
  - perdas fetais anteriores (`QTDFILMORT`);
  - UF de residência (derivada de `CODMUNRES`).

  O conjunto é uma proposta do projeto, e não uma especificação fechada.
- **Variáveis de auditoria:**
  - consultas (`CONSPRENAT`, `CONSULTAS`);
  - idade gestacional (`SEMAGESTAC`, `GESTACAO`, `TPMETESTIM`);
  - tipo de parto (`PARTO`);
  - índice de Kotelchuck (`KOTELCHUCK`);
  - gestações anteriores e filhos vivos (`QTDGESTANT`, `QTDFILVIVO`).

  Estão disponíveis para exame, mas **não** são propostas como covariáveis de ajuste. Várias são medidas durante ou depois da exposição; o índice de Kotelchuck, por exemplo, é construído em parte a partir do próprio mês de início.

Os códigos originais do SINASC são preservados como texto. As recodificações do projeto (por exemplo, `ESCOLARIDADE_MAE`, em que o código 9 ou vazio vira `IGNORADO`) aparecem como colunas adicionais.

## 6. Filtros utilizados

| Etapa | Critério | Registros restantes |
| --- | --- | ---: |
| Base regional A | mãe residente em MG, ES, RJ ou SP (`CODMUNRES`), nascimento em 2024 | 904.365 |
| 1 | `MESPRENAT` conhecido (1–9); exclui vazio e 99 | 880.091 |
| 2 | 500 ≤ `PESO` ≤ 6.000 g | 878.902 |
| 3 | gestação única (`GRAVIDEZ` = 1) | 856.282 |
| 4 = população B | `MESPRENAT` entre 1 e 6 | 842.998 |

**Ordem dos filtros.** A ordem é apenas expositiva: o resultado final não depende dela. Cada registro de A traz os indicadores `FLAG_*`, `ELEGIVEL_B` e a lista completa de motivos de exclusão, o que permite refazer ou alterar qualquer filtro.

**Ausência em X.** Valores ausentes nas covariáveis X não excluem registros. No projeto, as categorias ausentes formam o nível `IGNORADO`.

**Conferência com o projeto.** A população B destes arquivos foi conferida registro a registro com a função original do projeto. A mesma regra, aplicada ao Brasil inteiro, reproduz o N nacional documentado (2.207.214).

## 7. Hipóteses de identificação que ainda precisam de avaliação

Os pontos abaixo estão em aberto. Não foram resolvidos pelo projeto e são justamente o objeto da avaliação.

1. **Confundimento não observado.** O SINASC não registra:
   - renda;
   - tabagismo, álcool e outras substâncias;
   - estado nutricional e IMC pré-gestacional;
   - morbidades prévias;
   - intenção da gravidez;
   - violência;
   - apoio social;
   - barreiras de acesso aos serviços de saúde.

   Esses fatores podem afetar tanto o momento de início do pré-natal quanto o peso ao nascer.
2. **Suporte comum.** Os grupos são muito desiguais em tamanho, e algumas combinações de características (por exemplo, categorias raras de escolaridade, raça/cor ou situação conjugal em estados menores) têm poucos registros com T = 0. Resta avaliar se há gestantes comparáveis nos dois grupos em todo o espaço de X.
3. **Temporalidade das covariáveis.** Todas as variáveis são registradas no nascimento. Situação conjugal e município de residência podem ter mudado durante a gestação.
4. **Ausência de acompanhamento longitudinal.** O tempo zero da gestação e o momento da decisão de procurar o pré-natal não são observados.
5. **Seleção por nascido vivo e pelos critérios de elegibilidade.** Perdas gestacionais e natimortos não aparecem no SINASC. A exclusão de mês desconhecido, de gestações múltiplas e de início no 7º–9º mês também altera a população-alvo, e a ausência de `MESPRENAT` pode não ser aleatória.
6. **Duração da gestação e oportunidade de início tardio.** Gestações mais curtas, que concentram o baixo peso, têm menos tempo para registrar um início tardio. Restringir o comparador ao 4º–6º mês reduz esse problema, mas não o elimina.
7. **Mediadores e variáveis pós-exposição.** Ajustar por consultas, idade gestacional, tipo de parto ou pelo índice de Kotelchuck pode bloquear parte do efeito ou induzir viés de *collider*.
8. **Intervenção hipotética versus exposição registrada.** O mês de início é informado retrospectivamente e pode ter erro de registro ou de memória. A associação com o início registrado não equivale automaticamente ao efeito de uma intervenção bem definida, como garantir o início no 1º trimestre.
9. **Generalização.** A avaliação está restrita ao Sudeste e a 2024.

Fica a critério da professora escolher os métodos de avaliação e, se for o caso, propor outro estimando ou desenho.

## 8. Como abrir os arquivos

**Python (pandas):**

```python
import pandas as pd

# Parquet preserva os tipos (códigos originais como texto, indicadores como inteiros)
base = pd.read_parquet("sinasc_sudeste_2024_base_regional.parquet")

# CSV: separador ';', UTF-8; ler códigos como texto para preservar zeros à esquerda
inteiros = ["ID_REGISTRO", "ANO_NASCIMENTO", "IDADEMAE_NUM", "MESPRENAT_NUM", "T", "PESO_NUM", "Y",
            "FLAG_GESTACAO_UNICA", "FLAG_PESO_VALIDO", "FLAG_MESPRENAT_CONHECIDO",
            "FLAG_MESPRENAT_1_A_6", "ELEGIVEL_B"]
amostra = pd.read_csv("sinasc_sudeste_2024_amostra_100k.csv", sep=";", dtype=str)
amostra[inteiros] = amostra[inteiros].astype("Int64")

populacao_b_na_amostra = amostra[amostra["ELEGIVEL_B"] == 1]
```

**Python (DuckDB):**

```python
import duckdb
duckdb.sql("SELECT UF_RESIDENCIA_SIGLA, T, count(*) FROM 'sinasc_sudeste_2024_populacao_B.parquet' GROUP BY ALL ORDER BY ALL")
```

**R:**

```r
library(arrow)
base <- read_parquet("sinasc_sudeste_2024_base_regional.parquet")
amostra <- read.csv2("sinasc_sudeste_2024_amostra_100k.csv", colClasses = "character", encoding = "UTF-8")
```

**Excel:** o CSV usa `;` como separador (o mesmo padrão do arquivo oficial do SINASC). Ao abri-lo diretamente, o Excel remove os zeros à esquerda dos códigos (`'02'` vira `2`). Para preservá-los, use *Dados → De Texto/CSV* e defina as colunas de código como Texto.

**Células vazias** correspondem a valores ausentes (nulos). Nenhum valor foi imputado.

## 9. Como executar o notebook

O notebook `notebooks/apoio_aula/01_amostra_sinasc_sudeste_avaliacao_causal.ipynb`, no repositório do projeto, reconstrói os três conjuntos a partir do arquivo oficial. Ele também documenta as decisões e executa as verificações de validação. Usa DuckDB para o processamento e Plotly para os gráficos, e não executa nenhum estimador causal.

1. Clone o repositório e entre em `projetos/big-data-sinasc-causal-ml/`.
2. Crie e ative o ambiente virtual do projeto e instale as dependências:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   $env:PYTHONUTF8 = "1"
   ```

3. Baixe o arquivo oficial de 2024 e converta-o para Parquet. Os dados não são versionados por causa do tamanho:

   ```powershell
   python scripts/baixar_dados.py
   python -c "from pathlib import Path; from src.sinasc import converter_zip_para_parquet as c; c(Path('data/raw/SINASC_2024_csv.zip'), Path('data/processed/sinasc_2024.parquet'))"
   ```

4. Abra o notebook no Jupyter (`jupyter lab`) e execute todas as células. A execução completa leva poucos minutos.

O notebook confere se o Parquet de origem é idêntico ao usado no projeto (SHA-256 `a7a1618e555d…`). Em seguida, regrava os arquivos em `outputs/compartilhamento_professora/` e encerra com um quadro de verificações:

- contagens e correspondência dos quatro estados;
- unicidade dos registros;
- reprodução da regra B pela função original do projeto;
- coerência de T e Y;
- identidade entre CSV e Parquet;
- ausência de identificadores;
- reprodutibilidade do sorteio.

O resultado fica registrado em `manifesto_validacao.json`.

## Privacidade e uso

Os arquivos não contêm `CONTADOR`, datas (de nascimento, da última menstruação, de cadastro), hora do nascimento, códigos de estabelecimento de saúde, município de ocorrência do parto, ocupação ou naturalidade da mãe. O `ID_REGISTRO` é um identificador pseudônimo criado para este compartilhamento.

O código do município de residência foi mantido para permitir a avaliação geográfica e o agrupamento estatístico. Em municípios pequenos, a combinação desse código com idade, raça/cor, paridade e outros atributos pode, em tese, tornar um registro único (risco de reidentificação por combinação de atributos). Embora os microdados de origem sejam públicos, pedimos que os arquivos sejam usados apenas para esta avaliação acadêmica e não sejam republicados.
