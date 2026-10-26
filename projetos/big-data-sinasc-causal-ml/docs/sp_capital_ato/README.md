# Análise atual — São Paulo (capital), ponderação por sobreposição (ATO)

Documentos da fase atual do projeto: SINASC 2024, mães residentes no município de São Paulo, início do pré-natal nos meses 1–3 (T=1) versus 4–6 (T=0), desfecho peso ao nascer < 2.500 g, escore de propensão logístico e pesos de sobreposição (ATO). A série 2014–2024 da mesma especificação é descritiva.

| Arquivo | Conteúdo |
|---|---|
| [RESUMO_PARA_REDACAO.md](RESUMO_PARA_REDACAO.md) | Consolidação de problema, dados, método, resultados, limitações, referências e questões abertas, com a fonte de cada número |
| [PACOTE_REDACAO_ETAPA_1.pdf](PACOTE_REDACAO_ETAPA_1.pdf) | Documento acadêmico entregue no repasse da Etapa 1: estimação de 2024 (notebook 06). Não inclui a série anual de estimativas ATO (notebook 07) nem a análise de temporalidade (notebook 08) |
| [PACOTE_REDACAO_ETAPA_1_OVERLEAF/](PACOTE_REDACAO_ETAPA_1_OVERLEAF/) | Fonte LaTeX do PDF (compilar com XeLaTeX; instruções em `LEIA_ME.txt`) |
| [artigos/LEIA_ME.md](artigos/LEIA_ME.md) | Índice das referências citadas; os PDFs de acesso aberto ficam só na cópia local (fora do Git) |

Os notebooks desta fase estão em [`notebooks/principal/`](../../notebooks/principal/) (05a, 05b, 06, 07 e 08).

**Não confundir com a Entrega 1:** série nacional 2014–2024 estimada com AIPW, retirada da árvore ativa e recuperável no commit `af30d8d`, em `docs/entrega_1_nacional_aipw/`. População, estimando e estimador são diferentes, e os números das duas fases não devem ser combinados. As menções à entrega nacional no resumo para redação e no pacote acadêmico preservado referem-se a esse material histórico.

## Caminhos citados no PDF da Etapa 1

O PDF e sua fonte LaTeX são entregáveis já enviados e **não foram alterados**. A reorganização de 24/10/2026 mudou alguns caminhos que eles citam:

| Caminho citado no PDF | Caminho atual |
|---|---|
| `docs/entrega/RESUMO_PARA_REDACAO.md` | `docs/sp_capital_ato/RESUMO_PARA_REDACAO.md` |
| `docs/entrega/` (demais documentos, fase nacional) | histórico Git: `af30d8d`, pasta `docs/entrega_1_nacional_aipw/` |
| `outputs/qualidade_geografica_2024/qualidade_sp_2014_2024.ipynb` | `notebooks/principal/05a_qualidade_geografica_sp_2014_2024.ipynb` |
| `outputs/comparabilidade_sp_capital_2024/comparabilidade_sp_capital_2024.ipynb` | `notebooks/principal/05b_comparabilidade_sp_capital_2024.ipynb` |
| `outputs/qualidade_geografica_2024/qualidade_sp_por_ano.csv` | removido no lote 7C; indicadores calculados em memória no [notebook 05a](../../notebooks/principal/05a_qualidade_geografica_sp_2014_2024.ipynb), objeto `dados` |
| `outputs/qualidade_geografica_2024/RECOMENDACAO_RECORTE.md` | [preservado](../../outputs/qualidade_geografica_2024/RECOMENDACAO_RECORTE.md), com a comparação de seis recortes de 2024 |
| `outputs/comparabilidade_sp_capital_2024/balanco_covariaveis_2024.csv` e `resumo_propensity_2024.csv` | removidos no lote 7C; tabelas `saida_balanco` e `resumo_ps` calculadas no [notebook 05b](../../notebooks/principal/05b_comparabilidade_sp_capital_2024.ipynb) |
| `notebooks/principal/06_ato_sp_capital_2024.ipynb` | inalterado |
| `docs/methodology/DAG_INICIAL.md` | inalterado |

Os ZIPs entregues (`PACOTE_REDACAO_ETAPA_1_OVERLEAF.zip` e `ANEXOS_TECNICOS_ETAPA_1.zip`) eram cópias byte a byte das pastas expandidas e ficam na cópia local `_arquivo_local/entrega_sp_capital_etapa_1/`, fora do Git. Para recriar o ZIP do Overleaf a partir desta pasta, no PowerShell:

```powershell
Compress-Archive -Path docs\sp_capital_ato\PACOTE_REDACAO_ETAPA_1_OVERLEAF\* -DestinationPath PACOTE_REDACAO_ETAPA_1_OVERLEAF.zip
```

O notebook 06 recebeu correções de redação e gráficos depois da entrega (ver [ALTERACOES_REALIZADAS.md](../manutencao/ALTERACOES_REALIZADAS.md)); as estimativas citadas no PDF não mudaram.
