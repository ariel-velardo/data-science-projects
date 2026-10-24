# Inventário do repositório

Levantamento feito em 24/10/2026, antes da reorganização, sobre todos os arquivos do projeto, exceto `.venv/` e o conteúdo de `data/`, que só foi dimensionado. As dependências vieram de buscas por caminhos em `.py`, `.ipynb`, `.md`, `.json`, `.tex` e `.txt`, e da leitura dos validadores em `src/validacao.py` e `tests/`.

**Classes:** A = essencial para reprodução; B = resultado científico consolidado; C = complemento relevante; D = legado ou auxiliar; E = redundância ou resíduo.

## 1. Três fases científicas convivem no repositório

| Fase | Pergunta e método | Onde está | Situação |
|---|---|---|---|
| **Fase inicial 2024 (Brasil)** | AIPW em 2024, comparador 4º–9º mês (formulação A) | `notebooks/01–05` (raiz), `docs/*.md` da raiz, `docs/methodology/`, `docs/architecture/`, `outputs/diagnostics/`, `outputs/tables/`, `apresentacao/` | legado congelado por hash; validado por `scripts/validar_projeto.py` |
| **Entrega 1 — série nacional 2014–2024** | AIPW anual com *cross-fitting*, B = 1º–3º vs 4º–6º mês, IC agrupado por município | `notebooks/principal/01–05`, `notebooks/historico/`, `docs/entrega/` (relatório final da disciplina e anexos), `docs/temporal/`, `outputs/entrega/`, `outputs/temporal/` | concluída e entregue (commit `f2d4f45`) |
| **Análise atual — SP capital, ATO** | ponderação por sobreposição (ATO) em 2024, bootstrap de 1.000 réplicas; série 2014–2024 descritiva; temporalidade | `notebooks/principal/06–08`, notebooks em `outputs/qualidade_geografica_2024/` e `outputs/comparabilidade_sp_capital_2024/`, `docs/entrega/RESUMO_PARA_REDACAO.md` e pacote `*_ETAPA_1` | resultados consolidados; pacote acadêmico da Etapa 1 entregue; estava fora do Git |

As duas pastas `docs/entrega/` e `notebooks/principal/` misturavam a Entrega 1 nacional com a análise atual. O pacote da análise atual se chama "Etapa 1 do repasse acadêmico", o que convive mal com o rótulo "Entrega 1" da fase nacional.

## 2. Diretórios

### Raiz do projeto

| Item | Classe | Finalidade e dependências | Decisão |
|---|---|---|---|
| `README.md` | A | Documentava só a fase nacional AIPW. `validar_entrega` exige os spans `data-metrica` do bloco histórico e confere os links | reescrever, preservando o bloco de métricas |
| `requirements.txt` | A | 14 dependências; faltavam `scipy`, `psutil`, `joblib`, `nbformat` e `threadpoolctl`, importados diretamente; `pdfplumber` e `pymupdf` não são importados em nenhum lugar | consolidar |
| `requirements_before_spark.txt` | E | `pip freeze` (UTF-16) do ambiente antes da instalação do PySpark; citado apenas em listagens de `git status` e listas de hashes dos notebooks históricos 09c/09d | retirar da raiz depois da consolidação; preservar o conteúdo |
| `.gitignore`, `.gitattributes` | A | O `.gitignore` da raiz do workspace ignora `*.csv` e `*.parquet` | negar CSVs agregados de resultados; ignorar `_arquivo_local/` |
| `apresentacao/relatorio_interativo_sinasc_2024.html` | D | Relatório interativo da fase inicial 2024; hash no baseline; gerado por `src/entrega.py` | manter (congelado) |

### `notebooks/`

| Pasta | Classe | Conteúdo | Dependências | Decisão |
|---|---|---|---|---|
| `principal/06–08` | A/B | Análise atual: ATO 2024, série 2014–2024, temporalidade | 06 é citado oito vezes no PDF da Etapa 1; 07 lê `outputs/qualidade_geografica_2024/qualidade_sp_por_ano.csv` e calcula hashes do 06; a seção 7 do 06 lê o próprio arquivo pelo caminho `notebooks/principal/06_...` | manter no lugar |
| `principal/01–05` | B | Fluxo acadêmico da Entrega 1 nacional | README, `docs/README.md` e documentos da entrega; links relativos `../../` | mover para pasta própria da Entrega 1 (mesma profundidade, links relativos continuam válidos) |
| `historico/` (10 notebooks) | C | Desenvolvimento da extensão temporal nacional (V1 → V2) | `docs/MAPA_NOTEBOOKS.md`, `docs/temporal/`, testes (`test_temporal.py`, `test_estimacao_v2.py`…) | manter |
| `01–05` na raiz | D | Fase inicial 2024 | `validar_notebooks` exige exatamente esses cinco arquivos em `notebooks/0[1-5]*.ipynb` | manter (congelado) |
| `apoio_aula/` (1 notebook) | D | Prepara amostras do SINASC 2023 Sudeste para a avaliação independente da professora; grava em `outputs/compartilhamento_professora/`; não estima nada | referenciado apenas pelo pacote de compartilhamento | retirar da estrutura ativa |

### `outputs/`

| Pasta | Classe | Conteúdo | Dependências | Decisão |
|---|---|---|---|---|
| `diagnostics/` (37 arquivos) | B (fase 2024) | JSONs de amostra, AIPW, robustez, heterogeneidade e validação | 33 com hash no baseline; lidos por `src/` e `tests/` | manter (congelado) |
| `tables/` (12) | B/E | `.npz` de predições fora da partição (303 MB) e agregados; ignorado pelo Git | hashes no baseline; `src/` | manter |
| `figures/` (16 PNG) | E | Figuras da extensão temporal gravadas pelos notebooks históricos 07 e 08; ignorado | notebooks históricos | manter (local, regenerável) |
| `temporal/` (≈230 arquivos) | B/C | Resultados da extensão temporal **nacional**: manifestos, descritiva, suporte, modelos auxiliares, auditoria pré-V2, contrato V2 congelado, estimação V2 | `src/temporal.py`, `src/estimacao_v2.py`, testes, contrato congelado, notebooks `principal/01–05` e `historico/` | manter. **Exceção:** `temporal/figuras/` são 7 PNGs idênticos byte a byte a `figures/temporal_*.png` (E) |
| `entrega/` | B | Figuras (PNG e HTML) e tabelas da Entrega 1 nacional; dicionário raw | links de `docs/entrega/*.md` e do notebook `principal/02` | renomear para `entrega_1/` |
| `qualidade_geografica_2024/` | B | Notebook e CSVs que justificam o recorte SP capital | lido pelo notebook 07; citado no PDF da Etapa 1 e no resumo | manter os CSVs e a recomendação; reavaliar a posição do notebook |
| `comparabilidade_sp_capital_2024/` | B | Notebook de diagnóstico pré-estimação (balanço e sobreposição) e dois CSVs | citado pelo notebook 06, pelo PDF e pelo resumo | idem |
| `sinasc_sim_piloto_2024/` | C | Piloto descritivo SINASC + SIM; contém o ZIP bruto oficial do SIM (98 MB) e amostras de microdados | citado pelo resumo e pela recomendação de recorte | manter os agregados; o ZIP bruto pertence a `data/raw/` |
| `compartilhamento_professora/` | D/E | Amostras de microdados (Parquet e CSV, 49 MB) e documentação de um compartilhamento anterior; o ZIP repete três arquivos da pasta | nenhuma dependência fora do próprio pacote e do notebook de apoio | retirar da estrutura ativa |

### `docs/`

| Item | Classe | Observação | Decisão |
|---|---|---|---|
| `entrega/` — relatório final, dicionário técnico, matriz X–T–Y, metadados, tabelas, resumo de uma página, roteiro, material de aula | B | Entrega 1 nacional (rastreados) | separar em pasta da Entrega 1 |
| `entrega/RESUMO_PARA_REDACAO.md`, `PACOTE_REDACAO_ETAPA_1.pdf`, `PACOTE_REDACAO_ETAPA_1_OVERLEAF/` | B | Análise atual, SP capital ATO | separar em pasta da análise atual |
| `entrega/*.zip` (2) | E | Idênticos byte a byte às pastas expandidas (conferido arquivo por arquivo) | retirar da estrutura ativa |
| `entrega/ANEXOS_TECNICOS_ETAPA_1/` | E/C | Cópia do notebook 06 (idêntica ao original), artigos (idênticos a `entrega/artigos/`), CSV analítico derivado (2,9 MB) e dicionário resumido | retirar da estrutura ativa; o ZIP é o pacote entregue |
| `entrega/artigos/` | C | PDFs de acesso aberto citados e índice | manter o índice; PDFs fora do Git, como em `docs/literature/pdfs/` |
| `architecture/`, `methodology/`, `temporal/`, `playbooks/`, `dados/`, `artigo/`, `literature/`, `sources/` | C/D | Registros das fases anteriores; `BASELINE_PRE_REFATORACAO.md` e `preservacao_refatoracao.json` são âncoras de validação | manter |
| `*.md` na raiz de `docs/` | D | Documentação da fase inicial 2024; `SINTESE_EXECUTIVA.md` e `RESULTADOS_PRINCIPAIS.md` têm caminho fixo em `validar_entrega` | manter |

### `src/`, `scripts/`, `tests/`

- `src/` (19 módulos): 12 módulos e `__init__.py` têm hash registrado em `preservacao_refatoracao.json` (`codigo_atual`); qualquer edição reprova `validar_projeto`. Os notebooks 06–08 usam `src.amostra._criar_views`, `src.diagnosticos.construir_pipeline_propensity`/`validar_colunas_propensity` e `src.visualizacao` (`CORES_IPT`, `aplicar_tema_base`). **Decisão:** não editar módulos congelados; código novo só em módulos novos.
- `scripts/` (3): todos congelados. Nenhum referencia `requirements_before_spark.txt`.
- `tests/` (19 arquivos, 322 testes aprovados): nenhum cobre os notebooks 06–08, a fase SP capital nem a estrutura de pastas da análise atual.

### Caches e temporários

`__pycache__/` em `src/`, `scripts/` e `tests/`, além de `.pytest_cache/`: todos já ignorados. Nenhum `.ipynb_checkpoints`.

## 3. Credenciais e dados sensíveis

Busca por padrões de segredo (`api_key`, `token`, `password`, `secret`, chaves privadas e `.env`) em arquivos de texto do projeto: **nenhuma ocorrência de credencial**. Os microdados são públicos e desidentificados (SINASC/SIM, Portal de Dados Abertos do SUS). As amostras exportadas não têm identificadores individuais, segundo seus próprios manifestos, e continuam fora do Git.

## 4. Pontos de atenção para a revisão científica

| Notebook / documento | Achado | Severidade |
|---|---|---|
| 06, célula do perfil da população de sobreposição | A coluna única "População de sobreposição (ATO)" usa a média ponderada de T=1; para situação conjugal, que não está no ajuste e segue desequilibrada, mostra 27,1% (T=1), quando T=0 ponderado é 18,6% | médio |
| 06, método (item 5) e perfil | "balanço exato", "ficam exatamente iguais" e "médias coincidem", embora o máximo \|SMD\| ajustado seja 0,0031 e haja penalização L2 | médio |
| 06 e resumo | "Restringir T=0 aos meses 4–6 atenua, mas não elimina" o problema temporal: atenuação não demonstrada | médio |
| 08, seção 2 | "as faixas são confiáveis": concordância entre campos não é validação de acurácia | médio |
| 07, resumo e interpretação | "sem evidência… de diferença estatisticamente significativa" e "não se conclui diferença estatisticamente significativa" sugerem um teste que não foi feito | baixo |
