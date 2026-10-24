# Estado inicial do repositório (antes da reorganização)

Registro feito em 24/10/2026, antes de qualquer alteração de conteúdo.

## Git

| Item | Valor |
|---|---|
| Raiz do repositório Git | `C:/GitHub/data-science-projects` (workspace com vários projetos; este projeto é a subpasta `projetos/big-data-sinasc-causal-ml/`) |
| Branch inicial | `feature/expansao-temporal-sinasc` |
| Commit inicial (HEAD) | `f2d4f45 feat(entrega): consolida fluxo acadêmico SINASC 2014-2024` |
| Stash | vazio |
| Arquivos rastreados no projeto | 303 (20 notebooks) |
| Entradas em `git status` | 37 (1 modificada, 36 não rastreadas) |

**Arquivo marcado como modificado:** `outputs/diagnostics/fase3_gate.json`. O conteúdo é idêntico ao do HEAD (`git diff --exit-code` sem diferença; mesmo MD5 do blob). A marcação vem da combinação `core.autocrlf=true` com o atributo `eol=lf` desse arquivo em `.gitattributes`. Não é alteração real e não foi tocado.

**Trabalho científico não versionado no início:**

- `notebooks/principal/06_ato_sp_capital_2024.ipynb`, `07_evolucao_ato_sp_capital_2014_2024.ipynb` e `08_temporalidade_prenatal_sp_capital_2024.ipynb`: os três notebooks da análise atual (SP capital, ATO);
- `docs/entrega/RESUMO_PARA_REDACAO.md`, `PACOTE_REDACAO_ETAPA_1.pdf`, pasta e ZIP do projeto Overleaf, pasta e ZIP dos anexos técnicos e cópias de artigos;
- `outputs/qualidade_geografica_2024/`, `outputs/comparabilidade_sp_capital_2024/` e `outputs/sinasc_sim_piloto_2024/`;
- `outputs/compartilhamento_professora/` e `notebooks/apoio_aula/`;
- artefatos de `outputs/temporal/` (figuras e resumos JSON da fase nacional);
- `requirements_before_spark.txt`.

## Linha de base de validação (antes de qualquer mudança)

| Verificação | Resultado |
|---|---|
| `python -m pytest -q tests` (`.venv` do projeto) | 322 aprovados em 85 s |
| `python scripts/validar_projeto.py --rapida` | aprovada (preservação por hash, gates, notebooks 01–05 da raiz, links de `docs/` e do README, métricas `data-metrica`) |

## Riscos identificados

| Risco | Severidade | Tratamento |
|---|---|---|
| Notebooks principais 06–08 e o resumo acadêmico fora do Git: uma limpeza poderia perdê-los sem retorno | crítico | commit de snapshot antes de qualquer movimentação, mais backup local verificado |
| Arquivos com hash congelado (`docs/architecture/BASELINE_PRE_REFATORACAO.md`, `preservacao_refatoracao.json`): `outputs/diagnostics/`, `outputs/tables/`, `apresentacao/`, 16 arquivos de `src/` e `scripts/` | alto | não mover nem editar; código novo apenas em módulos novos |
| `validar_entrega` confere links de todos os `.md` de `docs/` e do README, além dos spans `data-metrica` do README | alto | atualizar links em cada movimentação; preservar o bloco de métricas históricas do README |
| A seção 7 do notebook 06 lê as **saídas salvas** das primeiras 22 células (nomes de traços Plotly e tabelas HTML) | alto | preservar nomes, dados e tabelas; tornar o recorte robusto à inserção de células |
| O PDF já entregue da Etapa 1 cita caminhos (`docs/entrega/RESUMO_PARA_REDACAO.md`, notebooks em `outputs/`) | médio | registrar a correspondência entre caminhos antigos e novos; não alterar o PDF nem sua fonte LaTeX |
| `.gitignore` da raiz do workspace ignora `*.csv` e `*.parquet`; CSVs de resultados da fase SP capital estavam ignorados | médio | negar apenas os CSVs agregados de resultados no `.gitignore` do projeto; microdados continuam ignorados |
| Bootstrap e estimações anuais não gravam resultados em disco: os valores existem só nas saídas salvas dos notebooks | médio | não reexecutar; regenerar gráficos a partir dos valores salvos, com verificação numérica |
| Execução de código pode criar `__pycache__` ou reescrever saídas | baixo | `sys.dont_write_bytecode`, `-B` e `-p no:cacheprovider` nos comandos de validação |

## Proteção criada

1. Branch dedicada: `chore/reorganizacao-revisao-mike`, criada a partir de `f2d4f45`. A branch original não foi alterada.
2. Commit `663becf chore(snapshot): versiona trabalho pré-existente ainda não rastreado`: 71 arquivos produzidos antes desta tarefa, versionados **sem alteração de conteúdo** e identificados como trabalho anterior. Não incluiu microdados, ZIPs redundantes nem PDFs de artigos.
3. Backup local `_arquivo_local/backup_estado_inicial_20261024.zip` (56 MB): 149 arquivos não rastreados ou ignorados de `docs/`, `notebooks/`, `outputs/` e da raiz, com manifesto SHA-256 interno; os hashes foram conferidos na releitura do ZIP. Ficaram de fora `data/`, `.venv/`, `outputs/tables/`, `outputs/figures/` e `docs/literature/pdfs/`, que não são movidos nem editados nesta tarefa, além de `DO24OPEN_csv.zip` (98 MB, download oficial que é apenas movido, nunca apagado).

Comandos destrutivos (`git reset --hard`, `git clean`, `git stash` automático, exclusões recursivas) não foram usados.
