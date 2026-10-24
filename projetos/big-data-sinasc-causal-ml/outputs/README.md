# Saídas

## Análise atual — São Paulo (capital), ATO

| Pasta | Conteúdo | Gerado por |
|---|---|---|
| [`figuras_interativas/`](figuras_interativas/index.html) | HTML interativo de todos os gráficos de `notebooks/principal/`, com `plotly.min.js` local compartilhado | `scripts/exportar_figuras_interativas.py` (a partir das saídas salvas) |
| [`qualidade_geografica_2024/`](qualidade_geografica_2024/RECOMENDACAO_RECORTE.md) | recomendação do recorte e CSVs de qualidade por recorte e por ano (o 07 lê `qualidade_sp_por_ano.csv`) | notebook 05a |
| `comparabilidade_sp_capital_2024/` | balanço por nível e resumo do escore diagnóstico (antes da estimação) | notebook 05b |
| [`sinasc_sim_piloto_2024/`](sinasc_sim_piloto_2024/BRIEFING_APRESENTACAO.md) | piloto descritivo SINASC + SIM do Sudeste (painel municipal e resumos); as amostras de microdados ficam só na cópia local | processamento descrito em `LEIA_ME.txt` |

Os notebooks 06, 07 e 08 não gravam arquivos: seus resultados estão nas saídas salvas dos próprios notebooks.

## Fases anteriores

| Pasta | Conteúdo |
|---|---|
| [`entrega_1_nacional_aipw/`](entrega_1_nacional_aipw/) | figuras e tabelas da Entrega 1 (Brasil 2014–2024, AIPW) e dicionário raw |
| `temporal/` | extensão temporal nacional: manifestos, descritiva, suporte, modelos auxiliares, contrato V2 congelado e estimação V2; lido por `src/` e pelos testes |
| `diagnostics/` | resultados e validações da fase inicial 2024, conferidos por hash (`scripts/validar_projeto.py`) |
| `tables/`, `figures/` | arquivos locais e regeneráveis das fases anteriores (fora do Git) |

Não mova nem renomeie `temporal/`, `diagnostics/` e `tables/`: caminhos e hashes são conferidos por código, testes e contratos congelados.
