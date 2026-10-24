# Alterações realizadas na reorganização

Branch `chore/reorganizacao-revisao-mike`, a partir de `f2d4f45`. Nenhuma estimativa foi recalculada e nenhum arquivo foi apagado de forma irreversível. Contexto: [estado inicial](ESTADO_INICIAL_REPOSITORIO.md), [inventário](INVENTARIO_REPOSITORIO.md) e [plano](PLANO_REORGANIZACAO.md).

## 1. Movimentações

Feitas com `git mv`, que preserva o histórico, exceto quando indicado.

| Origem | Destino | Motivo |
|---|---|---|
| `notebooks/principal/01–05_*.ipynb` | `notebooks/entrega_1_nacional_aipw/` | separar a Entrega 1 nacional da análise atual |
| `outputs/qualidade_geografica_2024/qualidade_sp_2014_2024.ipynb` | `notebooks/principal/05a_qualidade_geografica_sp_2014_2024.ipynb` | etapa da análise principal que estava escondida entre resultados |
| `outputs/comparabilidade_sp_capital_2024/comparabilidade_sp_capital_2024.ipynb` | `notebooks/principal/05b_comparabilidade_sp_capital_2024.ipynb` | idem |
| `docs/entrega/` (8 documentos nacionais) | `docs/entrega_1_nacional_aipw/` | Entrega 1 identificada pela fase |
| `docs/entrega/RESUMO_PARA_REDACAO.md`, `PACOTE_REDACAO_ETAPA_1.pdf`, `PACOTE_REDACAO_ETAPA_1_OVERLEAF/`, `artigos/` | `docs/sp_capital_ato/` | documentos da análise atual reunidos |
| `outputs/entrega/` | `outputs/entrega_1_nacional_aipw/` | figuras e tabelas da Entrega 1 |
| `outputs/sinasc_sim_piloto_2024/DO24OPEN_csv.zip` (98 MB, não rastreado) | `data/raw/sim/DO24OPEN_csv.zip` (`mv`) | dado bruto oficial não pertence a `outputs/` |

Os notebooks 05a e 05b gravam em `raiz/outputs/<pasta>/` por caminho calculado a partir da raiz do projeto; a mudança de pasta não altera onde gravam.

## 2. Retirado da estrutura ativa

Nada foi apagado. O material foi movido para `_arquivo_local/` (ignorado pelo Git) e, quando era texto, também está no commit `663becf`.

| Item | Situação | Onde ficou |
|---|---|---|
| `notebooks/apoio_aula/` | preparação de amostras do SINASC 2023 para a avaliação independente da professora; sem resultado científico exclusivo | `_arquivo_local/notebooks_apoio_aula/`; histórico Git |
| `outputs/compartilhamento_professora/` | amostras de microdados (49 MB) e documentação do compartilhamento anterior; o ZIP repetia três arquivos da pasta | `_arquivo_local/compartilhamento_professora/`; documentação também no histórico Git |
| `docs/entrega/ANEXOS_TECNICOS_ETAPA_1/` e `.zip` | pasta idêntica ao ZIP; notebook idêntico ao 06 da época; artigos idênticos a `artigos/`; CSV analítico derivado | `_arquivo_local/entrega_sp_capital_etapa_1/` |
| `docs/entrega/PACOTE_REDACAO_ETAPA_1_OVERLEAF.zip` | idêntico à pasta expandida, que continua versionada | `_arquivo_local/entrega_sp_capital_etapa_1/` |
| `outputs/temporal/figuras/` (7 PNG) | cópias byte a byte de `outputs/figures/temporal_*.png`, gravadas pelo notebook histórico 07 | `git rm`; recuperável do commit `663becf` |

## 3. Referências atualizadas

- Links e caminhos em `README.md`, `docs/README.md`, nos 8 documentos da Entrega 1 e em `RESUMO_PARA_REDACAO.md`.
- Notebooks: links em markdown nos nacionais 01 e 05, no 05a, no 05b, no 06 e no 07; caminho de leitura da tabela 1 no nacional 02 (célula 3) e lista de arquivos com hash conferido no 07 (célula 5). Nessas duas células de código a saída não depende do caminho alterado, por isso as saídas salvas continuam válidas sem reexecução.
- Dois links quebrados **anteriores à reorganização** corrigidos nos notebooks históricos 09 e 10 (`../docs/` → `../../docs/`).
- `outputs/sinasc_sim_piloto_2024/LEIA_ME.txt`: nova localização do ZIP do SIM.
- O PDF da Etapa 1 e sua fonte LaTeX não foram alterados; a correspondência de caminhos está em [`docs/sp_capital_ato/README.md`](../sp_capital_ato/README.md).
- Os notebooks 05b e 06 tinham células acrescentadas com formatação JSON diferente do restante do arquivo; ao gravar as edições, a formatação foi uniformizada (sem alteração de conteúdo).

## 4. `.gitignore` do projeto

Passam a ser ignorados `_arquivo_local/`, `.pytest_cache/` e os PDFs de `docs/sp_capital_ato/artigos/` (mesma política de direitos autorais de `docs/literature/pdfs/`). Os CSVs agregados de resultados da análise atual foram versionados explicitamente (`git add -f`), porque o `.gitignore` da raiz do workspace ignora `*.csv`; as amostras de microdados continuam fora do Git.
