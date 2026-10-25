# Alterações realizadas na reorganização

Branch `chore/reorganizacao-revisao-mike`, a partir de `f2d4f45`. Nenhuma estimativa foi recalculada e nenhum arquivo foi apagado de forma irreversível. Contexto: [estado inicial](ESTADO_INICIAL_REPOSITORIO.md). O inventário e o plano que orientaram a reorganização foram retirados em outubro de 2026 e permanecem no histórico Git (versão final em `36b1634`).

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

## 5. Dependências

Um único `requirements.txt`, com a versão validada de cada pacote:

- **acrescentados** (importados diretamente, antes implícitos): `scipy`, `joblib`, `threadpoolctl`, `psutil` e `nbformat`;
- **removidos**: `pdfplumber` e `pymupdf`, nunca importados no histórico do projeto (continuam instalados na `.venv`; nada foi desinstalado);
- **`pyspark`**: instalado na `.venv` (4.2.0, com Java 17 na máquina), mas nenhum código do projeto o importa; documentado como não dependência;
- **`requirements_before_spark.txt`**: `pip freeze` em UTF-16 do ambiente anterior ao PySpark; retirado da raiz, com o conteúdo recuperável no commit `663becf`. Nenhum script o instalava.

Nenhuma biblioteca foi instalada ou atualizada.

## 6. Correções científicas

Nenhum número mudou: a sequência de números dos textos regenerados é idêntica à original (ver [validação](VALIDACAO_FINAL.md)).

| Onde | Antes | Depois |
|---|---|---|
| 06, perfil ponderado | coluna única "População de sobreposição (ATO)" com a média de T=1; situação conjugal aparecia como 27,1% da população-alvo | colunas T=1 e T=0 ponderadas e coluna "papel no ajuste"; casadas: 27,1% em T=1 e 18,6% em T=0, sem proporção única; texto explica a diferença entre covariáveis ajustadas e variáveis de diagnóstico |
| 06 método; resumo 3.5 e 4.3–4.5 | "balanço exato", "ficam exatamente iguais", "balanço quase exato", "médias coincidem" | igualdade exata só sem penalização; com L2, balanço **aproximado** (máximo \|SMD\| 0,0031), que não demonstra ausência de confundimento |
| 06 interpretação; resumo 4.2 | "comparando gestantes com o mesmo perfil" | "grupos ponderados com distribuições aproximadamente iguais" |
| 06, 05b e resumo (seções 1 e 5) | restringir T=0 aos meses 4–6 "atenua, mas não elimina" o problema temporal | reduz a janela de início tardio considerada; não foi demonstrado quanto altera o viés nem sua direção |
| 08, seção 5 | restrição 4–6 com menor parcela de incluídos afetados | idem, explicitando que isso não demonstra redução do viés nem sua direção |
| 08, seção 2 | "as faixas são confiáveis para uma descrição grossa" | separa completude, consistência interna (`GESTACAO` × `SEMAGESTAC`) e validade da mensuração, que não foi avaliada |
| 07, resumo e interpretação | "sem evidência… de diferença estatisticamente significativa"; "Não se conclui diferença estatisticamente significativa" | "não foi feito teste formal de diferença entre anos" |
| 06, limitações | IC "considera nascimentos independentes" | bootstrap individual, possível dependência por estabelecimento, região e mães recorrentes; ausência de vinculação SINASC–SIM; item explícito sobre ausência de identificação causal |

Uma nota de revisão no topo do resumo registra essas mudanças.

## 7. Gráficos Plotly

Novo módulo `src/graficos.py`, só de apresentação: identidade T=1 (azul IPT) e T=0 (laranja), validada para daltonismo (ΔE CVD 19,6); formato pt-BR (`separators=",."`); título com subtítulo; notas de método e de fonte; nome de arquivo para a exportação PNG da barra de ferramentas; saída com Plotly interativo e PNG estático.

| Gráfico | Melhoria |
|---|---|
| 06 — escore e pesos (novo) | distribuição do escore por grupo, sem e com pesos ATO (histograma espelhado); hover com faixa, registros, % do grupo, % da soma dos pesos e peso da faixa; nota de que a ponderação não iguala variáveis fora do escore |
| 06 — balanço | hover com papel no ajuste, médias brutas e ponderadas de T=1 e T=0 e SMD com sinal; faixas sombreadas nas variáveis fora do escore; linhas 0,1/0,2 como referências |
| 06 — riscos | dois painéis: riscos por grupo e diferenças (bruta e ATO) com IC; hover com IC, nascimentos, casos e n efetivo |
| 07 — série ATO | diferença bruta como referência; hover unificado por ano com riscos, n e n efetivo; rótulos apenas em anos de destaque; nota de que não há IC anual nem teste entre anos |
| 07 — participação de T=0 | hover com contagens de T=0, T=1 e elegíveis |
| 08 — início tardio por duração | rampa sequencial dos meses 4–6; hover com n, denominador e soma |
| 08 — baixo peso pré-termo/a termo | hover com casos, n do mês e fração pré-termo |

O bootstrap não gravava réplicas; o gráfico de riscos e o texto da seção 6 do 06 usam os percentis salvos (limites dos riscos por grupo com precisão integral, extraídos do gráfico original; limites das diferenças com duas casas decimais, a precisão da tabela salva). Os traços lidos pela seção 7 ("Risco ponderado ATO", "Depois (pesos ATO)") mantêm nomes e valores, e essa seção agora localiza a parte principal pelo `id` da célula, em vez da posição fixa 22.

**Exportação:** `scripts/exportar_figuras_interativas.py` gera `outputs/figuras_interativas/` a partir das saídas salvas dos 5 notebooks principais: 11 HTML de 5–20 KB, `index.html` e um único `plotly.min.js` local. Os gráficos de 05a e 05b foram exportados sem alteração.

## 8. Notebooks, `src/`, `scripts/` e `tests/`

- **Padronização:** a função local `exibir_plotly` de 06, 07 e 08 foi substituída pela do módulo comum; imports sem uso foram removidos da configuração do 06. Os notebooks já seguiam a sequência objetivo → dados → população → método → diagnósticos → resultados → limitações; nenhuma seção foi reordenada. Não há caminhos absolutos no código.
- **Mantido de propósito:** as funções locais `fmt` (trocá-las exigiria reexecutar todas as células) e os imports repetidos na seção 7 do 06, que é executável sozinha.
- **`src/` e `scripts/`:** 16 arquivos com hash congelado não foram editados. Código novo: `src/graficos.py` e `scripts/exportar_figuras_interativas.py`.
- **Testes novos** (`tests/test_analise_sp_capital.py`, 13): estrutura de pastas; validade dos notebooks principais; valores de referência de 2024, da série e do 08; textos corrigidos; contrato da seção 7; fórmulas ATO executadas a partir do próprio notebook 07 e comparadas com implementação independente; sincronização dos HTML; links; módulo de gráficos. Nenhum precisa das bases do SINASC.

## 9. Documentação

- `README.md` reescrito para a análise atual. O bloco histórico com os spans `data-metrica` foi mantido sem alteração, porque `validar_projeto` o exige.
- `docs/GUIA_REVISAO_MIKE.md`, `notebooks/README.md`, `outputs/README.md`, `docs/README.md`, `docs/sp_capital_ato/README.md` e `docs/entrega_1_nacional_aipw/README.md`.
- Avisos em `docs/MAPA_NOTEBOOKS.md` (mapa histórico) e em `docs/REPRODUCAO.md` (o comando `python -m src.entrega` sobrescreve o README).

## 10. Commits

| Commit | Conteúdo |
|---|---|
| `663becf` | snapshot do trabalho pré-existente não rastreado, sem alteração de conteúdo |
| `0c956de` | estado inicial, inventário e plano |
| `0f05fca` | reorganização de pastas e referências |
| `d8ac83a` | dependências |
| `22dfb5c` | correções científicas e gráficos |
| `47e73ba` | README, guia, índices, exportação interativa e testes |
| último | avisos, validação final e este relatório |

Pendências e limites da validação: ver [VALIDACAO_FINAL.md](VALIDACAO_FINAL.md).
