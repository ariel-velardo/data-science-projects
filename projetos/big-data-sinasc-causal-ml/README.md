# Início precoce do pré-natal e baixo peso ao nascer no Brasil

## SINASC 2014–2024

Análise observacional com inferência causal, AIPW e *cross-fitting* em aproximadamente 30,5 milhões de registros do SINASC.

## 1. Visão geral

O Sistema de Informações sobre Nascidos Vivos (SINASC), mantido pelo Ministério da Saúde, registra cada nascimento ocorrido no Brasil a partir da Declaração de Nascido Vivo (DNV). Este projeto usa os microdados públicos de 2014 a 2024: 30.468.409 registros brutos, em que cada linha corresponde a um nascido vivo (uma DNV).

**Pergunta de pesquisa.** Entre gestantes comparáveis nas características observadas, iniciar o pré-natal no 1º–3º mês está associado a menor risco de baixo peso ao nascer do que iniciar no 4º–6º mês?

Trata-se de um estudo observacional: o momento de início do pré-natal não foi atribuído aleatoriamente. Para comparar grupos com perfis observados semelhantes, o contraste é estimado com o estimador duplamente robusto AIPW (*Augmented Inverse Probability Weighting*), com *cross-fitting*, separadamente para cada ano.

**Resultado principal.** Na formulação principal (B), o início do pré-natal no 1º trimestre está associado a um risco de baixo peso ao nascer aproximadamente 0,9 a 1,5 ponto percentual (p.p.) menor do que o início entre o 4º e o 6º mês, em todos os onze anos.

Essa é uma estimativa obtida **sob hipóteses de identificação** (ausência de confundimento não medido, suporte comum e ordenação temporal adequada das variáveis). Ela não constitui prova de causalidade.

## 2. Dados

| Item | Descrição |
| --- | --- |
| Fonte | Ministério da Saúde, [SINASC — Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc) |
| Período | 2014–2024 (11 anos, analisados separadamente) |
| Cobertura | Brasil: 27 UFs e cerca de 5.580 municípios de residência por ano |
| Registros brutos | 30.468.409 |
| População principal B | 27.533.362 (gestação única, peso entre 500 e 6.000 g, início do pré-natal no 1º–6º mês) |
| Granularidade | 1 linha = 1 nascido vivo = 1 DNV |
| Target (Y) | Baixo peso ao nascer: `PESO` < 2.500 g |
| Tratamento (T) | `MESPRENAT` 1–3 (T = 1) versus 4–6 (T = 0) |
| Features (X) | 7 covariáveis: idade, escolaridade, raça/cor, situação conjugal, paridade, perdas fetais e UF de residência |
| Formato analítico | CSV oficial (ZIP) convertido para Parquet; consultas e transformações em DuckDB |

A prevalência de baixo peso na população analítica variou de 6,93% (2014) a 7,89% (2023 e 2024).

## 3. Fluxo principal

Os cinco notebooks de `notebooks/principal/` formam o **fluxo acadêmico principal** do projeto e devem ser lidos nesta ordem:

| Notebook | Conteúdo |
| --- | --- |
| [01 — EDA](notebooks/entrega_1_nacional_aipw/01_eda_sinasc_2014_2024.ipynb) | Descrição da base 2014–2024: volume, qualidade, ausências, perfil das gestantes e evolução do desfecho e da exposição. |
| [02 — Preparação e desenho](notebooks/entrega_1_nacional_aipw/02_preparacao_e_desenho.ipynb) | Da base bruta à população analítica: filtros, definição de Y, T e X e escolha do comparador. |
| [03 — Propensity e suporte](notebooks/entrega_1_nacional_aipw/03_propensity_e_overlap.ipynb) | Escore de propensão, sobreposição entre grupos, balanceamento das covariáveis e tamanho efetivo de amostra. |
| [04 — Estimação AIPW](notebooks/entrega_1_nacional_aipw/04_estimacao_aipw.ipynb) | Modelos auxiliares, estimador AIPW, *cross-fitting* e cálculo da incerteza. |
| [05 — Resultados e sensibilidades](notebooks/entrega_1_nacional_aipw/05_resultados_e_sensibilidades.ipynb) | Contrastes de 2014 a 2024, formulação C, especificações de modelo, recorte de suporte, inferência municipal e limitações. |

Os demais notebooks registram o histórico do desenvolvimento e são preservados para rastreabilidade, mas não são necessários para acompanhar o trabalho:

- `notebooks/historico/`: extensão temporal e execução científica original ([10_estimacao_v2.ipynb](notebooks/historico/10_estimacao_v2.ipynb));
- `notebooks/01–05` (raiz da pasta): análise inicial restrita a 2024, mantida no lugar original por compatibilidade com os registros históricos do projeto.

## 4. Metodologia resumida

- **X:** 7 covariáveis maternas e geográficas, medidas na DNV. Valores categóricos ausentes formam a categoria `IGNORADO`.
- **T:** início do pré-natal no 1º–3º mês (T = 1) versus 4º–6º mês (T = 0), na formulação principal B.
- **Y:** `PESO` < 2.500 g.
- **Método:** AIPW, que combina um modelo de propensão P(T | X) e modelos de desfecho P(Y | T, X). O contraste é a diferença entre os riscos padronizados de baixo peso nos dois grupos, em p.p.
- **Cross-fitting:** 3 partições; cada observação recebe predições de modelos ajustados sem ela.
- **Inferência:** erro-padrão agrupado por município de residência e IC95% correspondente.
- **Especificações de modelo:** C1 (propensão e desfechos logísticos), C2 (propensão logística e desfechos HGB) e C3 (propensão e desfechos HGB).
- **Sensibilidades:**
  - formulação C, com comparador restrito ao 4º–5º mês;
  - especificações C1, C2 e C3;
  - recorte de suporte (*trimming*) mantendo apenas escores de propensão em [0,05; 0,95].

## 5. Resultados principais

Contraste AIPW = risco de baixo peso com início no 1º–3º mês **menos** o risco com início no 4º–6º mês. Valores negativos indicam menor risco estimado no início precoce.

| Ano | B / C1 (p.p.) | IC95% municipal |
| --- | ---: | :---: |
| 2014 | −0,936 | −1,046 a −0,827 |
| 2022 | −1,524 | −1,671 a −1,377 |
| 2024 | −1,480 | −1,626 a −1,335 |

- O contraste é negativo em **todos os 11 anos**, de −0,936 p.p. (2014) a −1,524 p.p. (2022).
- A formulação C (comparador 4º–5º mês) segue o mesmo padrão, com valores entre −0,851 e −1,487 p.p.
- As especificações C2 e C3 ficam muito próximas entre si e entre 0,07 e 0,12 p.p. menos negativas que C1, sem mudar a direção nem a ordem de grandeza.
- O recorte de suporte [0,05; 0,95] altera pouco as estimativas: a maior mudança é de 0,067 p.p. em B e 0,096 p.p. em C.
- Nenhum IC95% municipal inclui zero, com ou sem recorte.
- Em B, o ano de 2024 tem caudas de propensão sinalizadas (10,56% dos registros fora de [0,05; 0,95]). Em C, os anos de 2017 a 2024 recebem a mesma sinalização. Nenhum registro fica fora de [0,01; 0,99].

As tabelas completas, ano a ano, estão em [TABELAS_RESULTADOS.md](docs/entrega_1_nacional_aipw/TABELAS_RESULTADOS.md).

<details>
<summary>Referência histórica de reprodução — análise de 2024</summary>

Métricas da primeira versão do projeto, restrita a 2024, com comparador 4º–9º mês. São mantidas para rastreabilidade e para a validação automática do histórico. **Não substituem os resultados finais de 2014–2024.**

| Indicador (2024, versão inicial) | Valor |
| --- | --- |
| Registros brutos | <span data-metrica="bruto">2.389.325</span> |
| Colunas originais | <span data-metrica="colunas">62</span> |
| Registros analíticos | <span data-metrica="n">2.251.570</span> |
| T = 1: início até o 3º mês | <span data-metrica="n_t1">1.942.045</span> |
| T = 0: início após o 3º mês | <span data-metrica="n_t0">309.525</span> |
| Baixo peso na população analítica (%) | <span data-metrica="prevalencia">7,894891</span> |
| UFs de residência | <span data-metrica="ufs">27</span> |
| C1 AIPW: estimativa (p.p.) | <span data-metrica="C1_estimativa_pp">-1,340527</span> |
| C2 AIPW: estimativa (p.p.) | <span data-metrica="C2_estimativa_pp">-1,231456</span> |
| CATE HGB: média (p.p.) | <span data-metrica="cate_media_pp">-1,294100</span> |
| Classificação da análise de heterogeneidade | <span data-metrica="gate4">HETEROGENEIDADE_SENSIVEL_A_MODELO</span> |

</details>

## 6. Estrutura do repositório

```text
notebooks/
  principal/    fluxo acadêmico da entrega (01–05)
  historico/    desenvolvimento temporal e execução científica original
  01–05 antigos análise inicial de 2024, preservada por rastreabilidade histórica
src/            módulos Python reutilizados pelos notebooks (caminhos, estimação, figuras)
data/           dados brutos (ZIP), Parquet anual e caches intermediários; mantidos apenas localmente
outputs/        tabelas, figuras, diagnósticos e resultados da estimação usados pelos notebooks
docs/           relatório final, dicionário, metadados, metodologia e referências
apresentacao/   relatório interativo em HTML da análise inicial de 2024
```

## 7. Como executar

Use o ambiente virtual do próprio projeto (`.venv` dentro desta pasta). No PowerShell, a partir de `projetos/big-data-sinasc-causal-ml/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONUTF8 = "1"
jupyter lab
```

Execute os notebooks de `notebooks/principal/` na ordem **01 → 02 → 03 → 04 → 05**.

- Os notebooks **03, 04 e 05** leem resultados já calculados em `outputs/` e executam em poucos instantes; nenhum modelo é ajustado neles.
- Os notebooks **01 e 02** combinam tabelas consolidadas em `outputs/` com algumas consultas DuckDB aos arquivos Parquet anuais: 2014–2023 em `data/processed/sinasc/` e 2024 em `data/processed/sinasc_2024.parquet`. Esses arquivos não são versionados no Git por causa do tamanho. Os ZIPs anuais vêm da fonte oficial, e o endereço de cada ano e os hashes de verificação estão em [METADADOS_BASE.md](docs/entrega_1_nacional_aipw/METADADOS_BASE.md).
- O notebook científico original ([10_estimacao_v2.ipynb](notebooks/historico/10_estimacao_v2.ipynb)), que ajusta os modelos sobre todos os registros, é versionado. Os caches de ajuste ficam em `data/interim/`, são apenas locais e não são versionados; por isso, um clone do repositório não reexecuta de imediato a estimação pesada. Ele é computacionalmente pesado e não é necessário para a leitura acadêmica dos resultados.

## 8. Documentação

| Documento | Conteúdo |
| --- | --- |
| [RELATORIO_FINAL_DISCIPLINA.md](docs/entrega_1_nacional_aipw/RELATORIO_FINAL_DISCIPLINA.md) | Relatório completo: contexto, métodos, resultados, limitações e referências |
| [DICIONARIO_TECNICO.md](docs/entrega_1_nacional_aipw/DICIONARIO_TECNICO.md) | Dicionário das variáveis usadas na análise |
| [METADADOS_BASE.md](docs/entrega_1_nacional_aipw/METADADOS_BASE.md) | Ficha da base, volumes por ano, filtros, qualidade e proveniência |
| [MATRIZ_XTY.md](docs/entrega_1_nacional_aipw/MATRIZ_XTY.md) | Definição e codificação de X, T e Y |
| [TABELAS_RESULTADOS.md](docs/entrega_1_nacional_aipw/TABELAS_RESULTADOS.md) | Tabelas finais de resultados, sensibilidades e comparação entre formulações |

Um mapa completo da documentação principal, complementar e histórica está disponível em [docs/README.md](docs/README.md).

## 9. Limitações

- **Confundimento residual:** apenas sete covariáveis registradas na DNV estão disponíveis; fatores como renda, tabagismo, estado nutricional, morbidades prévias e acesso efetivo a serviços estão ausentes ou incompletos no SINASC.
- **Seleção por nascido vivo:** o SINASC inclui apenas nascidos vivos; perdas gestacionais e natimortos não entram na análise.
- **`MESPRENAT` retrospectivo:** o mês de início do pré-natal é informado no momento do parto e pode conter erro de registro ou de memória.
- **Problema temporal residual:** gestações que terminam mais cedo têm menos tempo para iniciar o pré-natal tardiamente. Restringir o comparador ao 4º–6º mês reduz esse problema, mas não o elimina.
- **Dependência entre anos não modelada:** cada ano é estimado separadamente. O IC municipal não considera a dependência temporal, e as diferenças entre anos não são testes formais de mudança.
- **Caudas de propensão sinalizadas:** 2024 em B e 2017–2024 em C apresentam mais de 10% dos registros fora de [0,05; 0,95], ainda que sem violação de positividade em [0,01; 0,99].

## 10. Tecnologias

Python, DuckDB, Parquet, pandas, scikit-learn, Plotly e Jupyter.
