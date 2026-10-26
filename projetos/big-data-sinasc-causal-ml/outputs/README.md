# Saídas

## Análise atual — São Paulo (capital), ATO

Os cinco [notebooks principais](../notebooks/README.md) são a fonte oficial das análises, dos gráficos e das interpretações; as pastas abaixo preservam resultados complementares.

Os gráficos são produzidos e armazenados nos próprios notebooks Jupyter. Para visualizá-los, utilize VS Code com suporte a Jupyter e Plotly, ou outro ambiente compatível. As representações PNG permanecem disponíveis como alternativa estática.

| Pasta | Conteúdo | Gerado por |
|---|---|---|
| [`qualidade_geografica_2024/`](qualidade_geografica_2024/RECOMENDACAO_RECORTE.md) | recomendação e dois CSVs da comparação de seis recortes em 2024, com conteúdo não coberto pela série paulista do 05a | comparação geográfica de 2024 documentada na recomendação |

Os cinco notebooks não dependem dos CSVs removidos: calculam suas tabelas diretamente dos Parquets e mantêm os resultados nas saídas salvas. O 05a produz os indicadores anuais em `dados`; o 05b produz o balanço em `saida_balanco` e os diagnósticos do escore em `resumo_ps`. Os notebooks 06, 07 e 08 também não gravam arquivos de resultados externos.

### Comparação geográfica preservada

`comparacao_recortes_2024.csv` (seis linhas, chave `recorte_id`) e `qualidade_variaveis_2024.csv` (54 linhas, chave `recorte_id`, `variavel`) cobrem Sudeste, SP estado, SP capital, MG, RJ e ES. O 05a cobre somente capital, estado e restante de SP em 2014–2024. Portanto, os dois CSVs não são duplicações completas do notebook: preservam qualidade, exclusões e contagens dos demais recortes; o primeiro também contém baixo peso descritivo por grupo, que o 05a não calcula.

`RECOMENDACAO_RECORTE.md` preserva a justificativa da comparação de 2024: a alternativa estadual frente à amostra menor de ES, as limitações de preenchimento de MG/RJ e os códigos 99 sem classificação documental no Sudeste. É citado no 05a, no resumo e no pacote acadêmico. Seu “próximo passo” registra o estágio histórico daquela comparação; o estado atual da análise está nos notebooks e no guia de revisão. Os dois CSVs permanecem inalterados; na recomendação, apenas a referência às regras de recorte foi reescrita em 26/10/2026, quando o piloto SINASC + SIM foi retirado do projeto (resultados e contagens não mudaram).

### Correspondência dos outputs removidos no lote 7C

| Arquivo antigo | Fonte atual e verificação |
|---|---|
| `qualidade_geografica_2024/qualidade_sp_por_ano.csv` | [05a](../notebooks/principal/05a_qualidade_geografica_sp_2014_2024.ipynb), seções 3–6: regras e construção de `dados` (33 linhas, chave ano/recorte); os 33 percentuais anuais de MESPRENAT válido coincidem com o gráfico salvo na precisão do CSV |
| `comparabilidade_sp_capital_2024/balanco_covariaveis_2024.csv` | [05b](../notebooks/principal/05b_comparabilidade_sp_capital_2024.ipynb), seções 4–5 e 8: construção e validação das 29 linhas de `saida_balanco`, chave variável/tipo/nível |
| `comparabilidade_sp_capital_2024/resumo_propensity_2024.csv` | [05b](../notebooks/principal/05b_comparabilidade_sp_capital_2024.ipynb), seções 6–8: construção e validação das 66 linhas de `resumo_ps`, chave modelo/bloco/item |
| `tables/dicionario_analitico_sinasc_2024.json` | [Dicionário em Markdown](../docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md): 62 campos, definições, domínios, códigos de ignorado, exemplos, papéis e observações conferidos; percentuais iguais na precisão publicada de seis casas |

A inspeção do código atual não identificou consumidores desses quatro arquivos; o teste de estrutura foi ajustado para exigir as fontes preservadas. As tabelas completas são reconstruídas em memória, enquanto as saídas salvas mostram as apresentações selecionadas pelos notebooks. Não houve reexecução de notebooks ou alteração de métodos neste lote. O resumo, PDF e fonte Overleaf permanecem com suas citações históricas; use a correspondência acima para localizar os resultados. Os arquivos removidos também podem ser consultados no commit anterior ao lote, `a5358a3`.

## Proveniência e dependências preservadas

| Pasta | Conteúdo |
|---|---|
| `temporal/manifestos/` | dez manifestos SINASC 2014–2023, com fontes oficiais e hashes dos ZIPs e Parquets; lidos por `src.temporal` para preparação anual |
| `diagnostics/` | `fase1_amostra.json` e `fase1_overlap.json`, exigidos pela função histórica `src.amostra.carregar_exercicio`; `fase2_aipw.json`, preservado pelo hash completo do Parquet 2024 em `provenance.parquet_sha256` |

O ZIP SINASC 2024 tem seu hash em `data/raw/source_manifest.json`; esse manifesto não contém o hash do Parquet. O hash do Parquet 2024 permanece em `diagnostics/fase2_aipw.json`, campo `provenance.parquet_sha256`: `a7a1618e555d1417f692b5334b2a0fd01cfee911b3d45c0e0623346f3b8a12b5`. Esses arquivos e os dez manifestos anuais preservam a proveniência dos onze Parquets. O dicionário analítico cobre os 62 campos brutos na versão [Markdown](../docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md).

**Pendência para outro lote:** `src.amostra.carregar_exercicio` ainda lê os dois JSONs da Fase 1 e é chamado por `src.modelagem_preditiva.executar_preditivo`. Essa rotina histórica não é utilizada pelos cinco notebooks principais. Os módulos e os três JSONs foram preservados sem alteração; as estimativas nacionais contidas neles não integram os resultados atuais. Separar a proveniência de 2024 desse registro histórico também fica para uma limpeza posterior.

Os resultados da Entrega 1 nacional, da extensão V1/V2 e `diagnostics/fase3_sensibilidades.json` foram retirados da árvore ativa; seus arquivos versionados permanecem recuperáveis no commit `af30d8d`.
