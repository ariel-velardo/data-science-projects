# Saídas

## Análise atual — São Paulo (capital), ATO

Os cinco [notebooks principais](../notebooks/README.md) são a fonte oficial das análises, dos gráficos e das interpretações; as pastas abaixo preservam resultados complementares.

Os gráficos são produzidos e armazenados nos próprios notebooks Jupyter. Para visualizá-los, utilize VS Code com suporte a Jupyter e Plotly, ou outro ambiente compatível. As representações PNG permanecem disponíveis como alternativa estática.

| Pasta | Conteúdo | Gerado por |
|---|---|---|
| [`qualidade_geografica_2024/`](qualidade_geografica_2024/RECOMENDACAO_RECORTE.md) | recomendação do recorte e CSVs preservados de qualidade por recorte e por ano; o 07 processa os Parquets diretamente e não depende de `qualidade_sp_por_ano.csv` | análise de qualidade geográfica (05a) |
| `comparabilidade_sp_capital_2024/` | balanço por nível e resumo do escore diagnóstico (antes da estimação) | notebook 05b |
| [`sinasc_sim_piloto_2024/`](sinasc_sim_piloto_2024/BRIEFING_APRESENTACAO.md) | piloto descritivo SINASC + SIM do Sudeste (painel municipal e resumos); as amostras de microdados ficam só na cópia local | processamento descrito em `LEIA_ME.txt` |

Os notebooks 06, 07 e 08 não gravam arquivos: seus resultados estão nas saídas salvas dos próprios notebooks.

## Proveniência e dependências preservadas

| Pasta | Conteúdo |
|---|---|
| `temporal/manifestos/` | dez manifestos SINASC 2014–2023, com fontes oficiais e hashes dos ZIPs e Parquets; lidos por `src.temporal` para preparação anual |
| `diagnostics/` | `fase1_amostra.json` e `fase1_overlap.json`, exigidos pela função histórica `src.amostra.carregar_exercicio`; `fase2_aipw.json`, preservado pelo hash completo do Parquet 2024 em `provenance.parquet_sha256` |
| `tables/` | versão JSON do [dicionário analítico](../docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md) |

O ZIP SINASC 2024 tem seu hash em `data/raw/source_manifest.json`; o hash do Parquet 2024 permanece em `diagnostics/fase2_aipw.json`. Esses arquivos e os dez manifestos anuais preservam a proveniência dos onze Parquets. O dicionário analítico cobre os 62 campos brutos e mantém sua versão [Markdown](../docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md).

**Pendência para outro lote:** `src.amostra.carregar_exercicio` ainda lê os dois JSONs da Fase 1 e é chamado por `src.modelagem_preditiva.executar_preditivo`. Essa rotina histórica não é utilizada pelos cinco notebooks principais. Os módulos e os três JSONs foram preservados sem alteração; as estimativas nacionais contidas neles não integram os resultados atuais. Separar a proveniência de 2024 desse registro histórico também fica para uma limpeza posterior.

Os resultados da Entrega 1 nacional, da extensão V1/V2 e `diagnostics/fase3_sensibilidades.json` foram retirados da árvore ativa; seus arquivos versionados permanecem recuperáveis no commit `af30d8d`.
