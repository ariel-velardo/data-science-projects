# Notebooks

Todos estão salvos com as saídas e podem ser lidos sem executar nada. Para executar, use a `.venv` do projeto (ver o [README](../README.md#7-como-executar)).

## Análise atual — São Paulo (capital), ATO · [`principal/`](principal/)

Estes cinco notebooks são a fonte oficial das análises, dos gráficos e das interpretações, com 11 figuras em Plotly JSON e PNG de apoio nas saídas salvas.

Os gráficos são produzidos e armazenados nos próprios notebooks Jupyter. Para visualizá-los, utilize VS Code com suporte a Jupyter e Plotly, ou outro ambiente compatível. As representações PNG permanecem disponíveis como alternativa estática.

| Notebook | Pergunta | Natureza |
|---|---|---|
| [01 — qualidade geográfica](principal/01_qualidade_geografica.ipynb) | Qual recorte tem melhor qualidade de dados? (2014–2024) | descritivo; justifica o recorte |
| [02 — comparabilidade](principal/02_comparabilidade.ipynb) | T=1 e T=0 são comparáveis antes do ajuste? Há sobreposição? | diagnóstico sem o desfecho |
| [03 — estimação ATO 2024](principal/03_estimacao_ato.ipynb) | Qual a diferença de risco ajustada, com IC? | **estimação principal** e sensibilidade |
| [04 — série 2014–2024](principal/04_evolucao_historica.ipynb) | A direção se mantém ao longo dos anos? | estimativas pontuais anuais, descritivas |
| [05 — temporalidade](principal/05_temporalidade_prenatal.ipynb) | Quanto a duração gestacional restringe o comparador e a seleção? | descritivo, sem modelos |

A árvore ativa contém somente estes cinco notebooks. A sequência atual é 01–05; além da renomeação, foram corrigidos cinco destinos de links Markdown nos notebooks 02, 03 e 04, preservando código, metadados e saídas. As referências históricas dos pacotes acadêmicos estão no [mapeamento da Etapa 2](../README.md#correspondência-dos-notebooks-citados-na-etapa-2). Os antigos notebooks nacionais 01–05 da Entrega 1 foram retirados e permanecem no histórico Git, no commit `af30d8d`.
