# Início do pré-natal e baixo peso ao nascer — SINASC

Estudo observacional com microdados do Sistema de Informações sobre Nascidos Vivos (SINASC). Análise atual: **município de São Paulo, 2024**, com ponderação por sobreposição (ATO), e repetição descritiva da mesma especificação em **2014–2024**.

> **Para revisão acadêmica, comece pelo [guia de revisão](docs/GUIA_REVISAO_MIKE.md)**: ordem de leitura, o que foi feito e o que permanece em aberto.

## 1. Problema e objetivo

**Pergunta.** Entre nascidos vivos de mães residentes no município de São Paulo em 2024, o início do pré-natal no primeiro trimestre (meses 1–3) está associado a menor risco de baixo peso ao nascer, comparado ao início entre o 4º e o 6º mês, após ajuste por características maternas observadas?

**Objetivo.** Estimar essa diferença de risco de forma transparente e auditável, explicitando quais hipóteses seriam necessárias para uma leitura causal e por que elas não estão demonstradas.

**Associação, não causalidade.** O momento de início do pré-natal não foi atribuído ao acaso. O estudo estima uma **associação ajustada pelas covariáveis observadas**. Ler o resultado como efeito causal exigiria, entre outras hipóteses, ausência de confundimento não medido, positividade, consistência da exposição e ordenação temporal adequada; nenhuma delas é demonstrada pelos dados. O balanço das covariáveis após a ponderação é necessário para a comparação, mas não comprova essas hipóteses.

## 2. Dados e população

| Item | Definição |
|---|---|
| Fonte principal | SINASC, Ministério da Saúde/DATASUS, [Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc); uma linha por Declaração de Nascido Vivo |
| Recorte geográfico | mãe residente no município de São Paulo (`CODMUNRES = 355030`), escolhido por qualidade de preenchimento, **sem usar a associação com o desfecho** |
| Recorte temporal | estimação principal em 2024; mesma especificação repetida em cada ano de 2014 a 2024 (descritiva) |
| Elegibilidade (especificação B) | gestação única; peso entre 500 e 6.000 g; início do pré-natal nos meses 1–6 |
| Exposição T=1 | início do pré-natal nos meses 1–3 (`MESPRENAT` 1–3) |
| Comparação T=0 | início nos meses 4–6 |
| Desfecho Y=1 | peso ao nascer < 2.500 g |
| Covariáveis do escore | idade materna e idade², escolaridade, raça/cor, paridade e perdas fetais anteriores |
| Fora do escore | situação conjugal (temporalidade incerta; usada em diagnóstico e sensibilidade) e todas as variáveis do parto ou posteriores à exposição (idade gestacional, consultas, tipo de parto, Apgar etc.) |

Em 2024: **114.694 nascimentos elegíveis**, 104.576 em T=1 e 10.118 em T=0, nenhum excluído por suporte ou por covariável incompleta.

## 3. Método

1. **Escore de propensão** $e(X)=P(T=1\mid X)$: regressão logística com penalização L2, ajustada na amostra inteira.
2. **Pesos de sobreposição (ATO):** $1-e(X)$ para T=1 e $e(X)$ para T=0. Os pesos ficam em $[0,1]$, sem divisão por escores próximos de 0 ou 1. Isso importa aqui porque cerca de 91% dos nascimentos estão em T=1.
3. **Estimando:** diferença de riscos ponderados (T=1 − T=0) na **população de sobreposição**, que enfatiza perfis em que os dois momentos de início são frequentes. Não é a população total (ATE) nem a dos tratados (ATT).
4. **Incerteza:** bootstrap não paramétrico com **1.000 réplicas**, reestimando o escore em cada uma; intervalo de 95% por percentis. A reamostragem trata os nascimentos como independentes.
5. **Diagnósticos:** balanço por diferença média padronizada (SMD) antes e depois da ponderação, suporte do escore, tamanho amostral efetivo de Kish e sensibilidade com situação conjugal no escore.

## 4. Resultados principais

**São Paulo (capital), 2024** — [notebook 03](notebooks/principal/03_estimacao_ato.ipynb):

| | T=1 (meses 1–3) | T=0 (meses 4–6) | Diferença T=1 − T=0 |
|---|---:|---:|---:|
| Risco bruto | 8,41% | 10,41% | −2,00 p.p. (IC 95% −2,61 a −1,37) |
| Risco ponderado (ATO) | 8,68% | 10,42% | **−1,74 p.p. (IC 95% −2,36 a −1,12)** |

- Covariáveis do escore com balanço aproximado após a ponderação (máximo |SMD| de 0,452 para 0,0031). A situação conjugal, fora do escore, continua desequilibrada (SMD 0,194 em "casada").
- Sensibilidade com situação conjugal no escore: −1,63 p.p., estimativa pontual **sem IC**. Ela também muda a população-alvo.
- **Série 2014–2024** ([notebook 04](notebooks/principal/04_evolucao_historica.ipynb)): diferença ATO negativa nos onze anos, de −0,58 p.p. (2020) a −1,90 p.p. (2023), sem tendência monotônica. São estimativas pontuais, **sem IC anual e sem teste de diferença entre anos**; cada ano tem sua própria população de sobreposição.
- **Temporalidade** ([notebook 05](notebooks/principal/05_temporalidade_prenatal.ipynb)): a análise descreve a composição por duração gestacional e a seleção antes do filtro de início do pré-natal; não identifica a magnitude nem a direção do possível viés temporal.

Consolidação com a origem de cada número: [RESUMO_PARA_REDACAO.md](docs/sp_capital_ato/RESUMO_PARA_REDACAO.md).

## 5. Limitações

- **Confundimento não observado:** renda, cobertura de plano privado, planejamento da gestação, tabagismo, estado nutricional, condições clínicas e acesso a serviços não estão no SINASC.
- **Temporalidade da exposição:** `MESPRENAT` é registrado no parto. Gestações mais curtas têm menos tempo para um início tardio. Restringir o comparador aos meses 4–6 reduz a janela considerada, mas não foi demonstrado quanto isso altera o viés nem sua direção.
- **Seleção por nascidos vivos:** perdas fetais não entram na população, e este estudo não vincula o SINASC ao SIM; desfechos gestacionais fora do universo dos nascidos vivos não são observados.
- **População-alvo específica:** o ATO vale para a população de sobreposição (mais jovem e menos escolarizada que o total) e não se generaliza automaticamente para todas as gestantes, outros municípios ou outros anos.
- **Incerteza:** o bootstrap reamostra nascimentos como independentes. Agrupamento por estabelecimento ou região, e mães com mais de um parto, podem tornar o IC estreito demais.
- **Série histórica:** comparação descritiva entre estimativas pontuais, sem inferência formal.
- **Modelo:** um único escore logístico, sem modelo de desfecho; o estimador não é duplamente robusto.

## 6. Organização do repositório

```text
notebooks/
  principal/                  análise atual (SP capital, ATO) — ler na ordem 01 → 02 → 03 → 04 → 05
docs/
  GUIA_REVISAO_MIKE.md        roteiro de revisão
  sp_capital_ato/             resumo para redação, PDF da Etapa 1 e fontes LaTeX das Etapas 1 e 2
  demais pastas               literatura, fontes oficiais e dicionário analítico
outputs/
  qualidade_geografica_2024/ comparação de seis recortes de 2024 e justificativa preservadas
  temporal/manifestos/        proveniência dos ZIPs e Parquets de 2014–2023
  diagnostics/               registros preservados por dependência de código e proveniência de 2024
src/  scripts/  tests/        código reutilizado, utilitários e testes
data/                         bases locais (não versionadas)
```

Índices por pasta: [notebooks/README.md](notebooks/README.md), [outputs/README.md](outputs/README.md) e [docs/README.md](docs/README.md).

As tabelas anuais de qualidade e os resultados de comparabilidade são calculados em memória nos notebooks 01 e 02, diretamente dos Parquets; os CSVs duplicados foram removidos. O [dicionário analítico](docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md) concentra as definições dos 62 campos, sem cópia JSON. A [correspondência dos caminhos antigos](outputs/README.md#correspondência-dos-outputs-removidos-no-lote-7c) orienta a leitura das referências preservadas no pacote acadêmico.

### Correspondência dos notebooks citados na Etapa 2

Os documentos acadêmicos preservam a numeração histórica. Os cinco arquivos foram renomeados e cinco destinos de links Markdown foram corrigidos nos notebooks 02, 03 e 04. Código, metadados e saídas permanecem idênticos; somente esses três notebooks têm novos hashes de conteúdo. As fontes, o PDF e o ZIP acadêmicos não foram regenerados nesta reorganização.

| Nome histórico na Etapa 2 | Caminho atual |
|---|---|
| `05a_qualidade_geografica_sp_2014_2024.ipynb` | [`01_qualidade_geografica.ipynb`](notebooks/principal/01_qualidade_geografica.ipynb) |
| `05b_comparabilidade_sp_capital_2024.ipynb` | [`02_comparabilidade.ipynb`](notebooks/principal/02_comparabilidade.ipynb) |
| `06_ato_sp_capital_2024.ipynb` | [`03_estimacao_ato.ipynb`](notebooks/principal/03_estimacao_ato.ipynb) |
| `07_evolucao_ato_sp_capital_2014_2024.ipynb` | [`04_evolucao_historica.ipynb`](notebooks/principal/04_evolucao_historica.ipynb) |
| `08_temporalidade_prenatal_sp_capital_2024.ipynb` | [`05_temporalidade_prenatal.ipynb`](notebooks/principal/05_temporalidade_prenatal.ipynb) |

A leitura segue: 01 — qualidade geográfica e seleção da população; 02 — comparabilidade e propensity score; 03 — estimação ATO de 2024; 04 — evolução histórica de 2014 a 2024; 05 — temporalidade do pré-natal e seleção.

## 7. Como executar

Use o ambiente virtual **deste projeto** (`.venv` dentro de `projetos/big-data-sinasc-causal-ml/`). No PowerShell, a partir desta pasta:

```powershell
python -m venv .venv                      # Python 3.11 (validado com 3.11.9)
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PYTHONUTF8 = "1"
jupyter lab
```

- **Kernel:** com o Jupyter aberto a partir da `.venv`, o kernel `python3` já usa esse ambiente; no VS Code, selecione `.venv\Scripts\python.exe`.
- **Leitura sem dados:** todos os notebooks estão salvos com as saídas; não é preciso executar nada para conferir resultados e gráficos.
- **Bases locais** (não versionadas por tamanho; [fontes oficiais](docs/sources/FONTES_OFICIAIS.md) e [localização dos manifestos e hashes](outputs/README.md#proveniência-e-dependências-preservadas)):
  - 2024: `python scripts/baixar_dados.py` baixa o ZIP oficial para `data/raw/`; `python -c "from src.sinasc import converter_zip_para_parquet; converter_zip_para_parquet('data/raw/SINASC_2024_csv.zip', 'data/processed/sinasc_2024.parquet')"` gera `data/processed/sinasc_2024.parquet`;
  - 2014–2023: `python -c "from src.temporal import preparar_anos; preparar_anos('.', range(2014, 2024))"` baixa e converte um ano por vez para `data/processed/sinasc/sinasc_<ano>.parquet`.
- **Reexecução:** 01, 02 e 05 são rápidos. O 04 lê diretamente os Parquets e ajusta onze escores anuais. O 03 inclui o bootstrap de 1.000 réplicas (alguns minutos); sua seção 7 usa os objetos produzidos nas seções anteriores da mesma execução.
- **Gráficos estáticos:** o `kaleido` usa o Google Chrome instalado na máquina para gerar os PNG incorporados aos notebooks.
- **Verificações:** `python -m pytest -q tests` (não precisa das bases).
- **PySpark** não é dependência do projeto.

## 8. Como visualizar os gráficos

Os cinco [notebooks principais](notebooks/README.md) são a fonte oficial das análises, dos gráficos e das interpretações. Suas saídas salvas contêm 11 figuras em Plotly JSON com PNG de apoio.

Os gráficos são produzidos e armazenados nos próprios notebooks Jupyter. Para visualizá-los, utilize VS Code com suporte a Jupyter e Plotly, ou outro ambiente compatível. As representações PNG permanecem disponíveis como alternativa estática.

Em visualizadores compatíveis, o hover mostra valores, intervalos e tamanhos de grupo, e a barra de ferramentas permite zoom e exportação em PNG. A interatividade depende do suporte do visualizador; a leitura das saídas salvas não exige reexecutar os notebooks.

## 9. Fases anteriores do projeto

A árvore ativa contém somente os cinco notebooks da pesquisa sobre São Paulo (capital). A antiga Entrega 1 nacional AIPW e os artefatos da extensão V1/V2 foram retirados; os arquivos versionados deste lote podem ser recuperados no commit `af30d8d`. As fases removidas usam outras populações e estimadores, e seus números não devem ser combinados com os do estudo atual.

Os registros históricos ainda necessários à preparação dos dados, à proveniência ou a funções preservadas estão identificados no [índice de outputs](outputs/README.md#proveniência-e-dependências-preservadas). A limpeza dessas funções fica para outro lote.

## 10. Tecnologias

Python, DuckDB, Parquet, pandas, scikit-learn, Plotly e Jupyter.
