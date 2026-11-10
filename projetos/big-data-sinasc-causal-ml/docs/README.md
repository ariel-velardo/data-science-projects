# Documentação do projeto

Para revisar a análise atual, comece pelo [guia de revisão](GUIA_REVISAO_MIKE.md).

Os cinco [notebooks principais](../notebooks/README.md) são a fonte oficial das análises, dos gráficos e das interpretações. Os gráficos são produzidos e armazenados nos próprios notebooks Jupyter. Para visualizá-los, utilize VS Code com suporte a Jupyter e Plotly, ou outro ambiente compatível. As representações PNG permanecem disponíveis como alternativa estática.

## Análise atual — São Paulo (capital), ATO

| Documento | Finalidade |
| --- | --- |
| [GUIA_REVISAO_MIKE.md](GUIA_REVISAO_MIKE.md) | Ordem de leitura, o que foi realizado e o que permanece em aberto |
| [sp_capital_ato/RESUMO_PARA_REDACAO.md](sp_capital_ato/RESUMO_PARA_REDACAO.md) | Problema, dados, método, resultados, limitações e referências, com a fonte de cada número |
| [sp_capital_ato/PACOTE_REDACAO_ETAPA_1.pdf](sp_capital_ato/PACOTE_REDACAO_ETAPA_1.pdf) | Documento acadêmico da Etapa 1 tal como entregue (estimação de 2024), registro histórico não atualizado; a [fonte LaTeX da Etapa 1](sp_capital_ato/PACOTE_REDACAO_ETAPA_1_OVERLEAF/) foi alterada na retirada do SIM e não corresponde exatamente ao PDF |
| [sp_capital_ato/PACOTE_REDACAO_ETAPA_2_OVERLEAF/](sp_capital_ato/PACOTE_REDACAO_ETAPA_2_OVERLEAF/) | Fonte LaTeX atual do documento acadêmico (Etapa 2): estimação de 2024, série 2014–2024 e temporalidade e seleção; compilada e revisada em ambiente externo, PDF não armazenado no repositório (ver [situação](sp_capital_ato/README.md#situação-do-pacote-da-etapa-2)) |
| [sp_capital_ato/README.md](sp_capital_ato/README.md) | Índice da pasta e correspondência entre os caminhos citados no PDF e os atuais |
| [dados/DICIONARIO_ANALITICO_SINASC_2024.md](dados/DICIONARIO_ANALITICO_SINASC_2024.md) | Definições dos 62 campos e códigos; versão consolidada em Markdown, sem duplicação JSON |
| [literature/REFERENCIAS_CENTRAIS.md](literature/REFERENCIAS_CENTRAIS.md) e [sources/FONTES_OFICIAIS.md](sources/FONTES_OFICIAIS.md) | Sínteses bibliográficas consolidadas e fontes oficiais; os manifestos de artigos permanecem em `literature/` |

## Referências históricas de arquivos

Os CSVs anuais de qualidade e de comparabilidade foram retirados no lote 7C: os notebooks 01 e 02 calculam essas tabelas diretamente dos Parquets. Consulte a [correspondência dos outputs removidos](../outputs/README.md#correspondência-dos-outputs-removidos-no-lote-7c) ao ler citações antigas no PDF ou na fonte Overleaf, cujo conteúdo científico foi preservado; o resumo para redação já aponta para os notebooks. A comparação dos seis recortes de 2024 continua em `outputs/qualidade_geografica_2024/`, pois sua abrangência excede a do 01.

Os registros administrativos anteriores da reorganização estão no histórico Git, no commit `3dd446f`, em `docs/manutencao/`. Não são necessários para executar ou revisar a análise atual.

## Histórico de desenvolvimento

Registros preservados para rastreabilidade. Não são necessários para a leitura da análise atual.

| Pasta | Conteúdo |
| --- | --- |
| [methodology/DAG_INICIAL.md](methodology/DAG_INICIAL.md) | DAG de trabalho citado como fonte da Figura 4 do PDF da Etapa 1 |

A Entrega 1 nacional AIPW e seu contrato V2 foram retirados da árvore ativa e permanecem no histórico Git, no commit `af30d8d`. A documentação de desenvolvimento das fases anteriores também está no histórico. O resumo para redação e o pacote acadêmico da análise atual permanecem preservados; referências textuais à entrega nacional nesses materiais devem ser consultadas no histórico, conforme o [índice da análise atual](sp_capital_ato/README.md).

Os manifestos anuais e os registros históricos mantidos por dependência estão identificados no [índice de outputs](../outputs/README.md#proveniência-e-dependências-preservadas).
