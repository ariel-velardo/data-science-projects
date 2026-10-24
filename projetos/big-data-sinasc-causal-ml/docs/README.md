# Documentação do projeto

Para revisar a análise atual, comece pelo [guia de revisão](GUIA_REVISAO_MIKE.md).

## Análise atual — São Paulo (capital), ATO

| Documento | Finalidade |
| --- | --- |
| [GUIA_REVISAO_MIKE.md](GUIA_REVISAO_MIKE.md) | Ordem de leitura, o que foi realizado e o que permanece em aberto |
| [sp_capital_ato/RESUMO_PARA_REDACAO.md](sp_capital_ato/RESUMO_PARA_REDACAO.md) | Problema, dados, método, resultados, limitações e referências, com a fonte de cada número |
| [sp_capital_ato/PACOTE_REDACAO_ETAPA_1.pdf](sp_capital_ato/PACOTE_REDACAO_ETAPA_1.pdf) | Documento acadêmico da Etapa 1 (estimação de 2024) e sua [fonte LaTeX](sp_capital_ato/PACOTE_REDACAO_ETAPA_1_OVERLEAF/) |
| [sp_capital_ato/README.md](sp_capital_ato/README.md) | Índice da pasta e correspondência entre os caminhos citados no PDF e os atuais |
| [dados/DICIONARIO_ANALITICO_SINASC_2024.md](dados/DICIONARIO_ANALITICO_SINASC_2024.md) | Definições de campos e códigos usados nos notebooks |
| [literature/](literature/) e [sources/](sources/) | Referências centrais, fichas de leitura e fontes oficiais |

## Entrega 1 — série nacional 2014–2024 (AIPW)

[entrega_1_nacional_aipw/](entrega_1_nacional_aipw/README.md): relatório final da disciplina, tabelas de resultados, dicionário técnico, metadados da base, matriz X–T–Y e material de apresentação. População, estimando e estimador diferem da análise atual.

## Manutenção

[manutencao/](manutencao/ALTERACOES_REALIZADAS.md): estado inicial, inventário, plano, alterações e validação da reorganização de outubro de 2026.

## Histórico de desenvolvimento

Registros preservados para rastreabilidade. Não são necessários para a leitura da análise atual.

| Pasta | Conteúdo |
| --- | --- |
| [temporal/](temporal/) e [MAPA_NOTEBOOKS.md](MAPA_NOTEBOOKS.md) | Expansão 2014–2024 e transição V1 → V2 (Entrega 1) |
| [playbooks/](playbooks/) | Registros de estado e planejamento interno |
| [methodology/DAG_INICIAL.md](methodology/DAG_INICIAL.md) | DAG de trabalho citado como fonte da Figura 4 do PDF da Etapa 1 |

A documentação da fase inicial (Brasil 2024) foi retirada da árvore em outubro de 2026 e permanece no histórico Git.

> **Preservação.** Parte da documentação histórica é referenciada por código, testes ou artefatos congelados da extensão temporal. Por isso, arquivos históricos não devem ser movidos, renomeados ou reescritos sem verificar essas dependências.
