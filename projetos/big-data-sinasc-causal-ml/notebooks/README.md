# Notebooks

Todos estão salvos com as saídas e podem ser lidos sem executar nada. Para executar, use a `.venv` do projeto (ver o [README](../README.md#7-como-executar)).

## Análise atual — São Paulo (capital), ATO · [`principal/`](principal/)

Estes cinco notebooks são a fonte oficial das análises, dos gráficos e das interpretações, com 11 figuras em Plotly JSON e PNG de apoio nas saídas salvas.

Os gráficos são produzidos e armazenados nos próprios notebooks Jupyter. Para visualizá-los, utilize VS Code com suporte a Jupyter e Plotly, ou outro ambiente compatível. As representações PNG permanecem disponíveis como alternativa estática.

| Notebook | Pergunta | Natureza |
|---|---|---|
| [05a — qualidade geográfica](principal/05a_qualidade_geografica_sp_2014_2024.ipynb) | Qual recorte tem melhor qualidade de dados? (2014–2024) | descritivo; justifica o recorte |
| [05b — comparabilidade](principal/05b_comparabilidade_sp_capital_2024.ipynb) | T=1 e T=0 são comparáveis antes do ajuste? Há sobreposição? | diagnóstico sem o desfecho |
| [06 — estimação ATO 2024](principal/06_ato_sp_capital_2024.ipynb) | Qual a diferença de risco ajustada, com IC? | **estimação principal** e sensibilidade |
| [07 — série 2014–2024](principal/07_evolucao_ato_sp_capital_2014_2024.ipynb) | A direção se mantém ao longo dos anos? | estimativas pontuais anuais, descritivas |
| [08 — temporalidade](principal/08_temporalidade_prenatal_sp_capital_2024.ipynb) | Quanto a duração gestacional restringe o comparador e a seleção? | descritivo, sem modelos |

A árvore ativa contém somente estes cinco notebooks. A numeração histórica foi mantida para preservar nomes, hashes e referências acadêmicas. Os antigos notebooks nacionais 01–05 da Entrega 1 foram retirados e permanecem no histórico Git, no commit `af30d8d`.
