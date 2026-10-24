# Entrega 1 — série nacional 2014–2024 (AIPW)

Documentos da primeira entrega da disciplina: Brasil, 2014–2024, início do pré-natal nos meses 1–3 versus 4–6 (formulação B), estimador AIPW com *cross-fitting* ajustado separadamente em cada ano e erro-padrão agrupado por município. Esta fase está concluída e preservada sem alteração de conteúdo; apenas os caminhos foram atualizados na reorganização de 24/10/2026 (antes ficavam em `docs/entrega/`).

| Documento | Conteúdo |
|---|---|
| [RELATORIO_FINAL_DISCIPLINA.md](RELATORIO_FINAL_DISCIPLINA.md) | Relatório completo: contexto, métodos, resultados, limitações e referências |
| [TABELAS_RESULTADOS.md](TABELAS_RESULTADOS.md) | Tabelas finais, sensibilidades e comparação entre formulações |
| [DICIONARIO_TECNICO.md](DICIONARIO_TECNICO.md) | Variáveis analíticas e dicionário raw de 2014–2024 |
| [METADADOS_BASE.md](METADADOS_BASE.md) | Fonte, volumes por ano, filtros, qualidade e proveniência |
| [MATRIZ_XTY.md](MATRIZ_XTY.md) | Definição e codificação de X, T e Y |
| [RESUMO_UMA_PAGINA.md](RESUMO_UMA_PAGINA.md), [ROTEIRO_APRESENTACAO.md](ROTEIRO_APRESENTACAO.md), [MATERIAL_PROXIMA_AULA.md](MATERIAL_PROXIMA_AULA.md) | Material de apresentação em aula |

- Notebooks: [`notebooks/entrega_1_nacional_aipw/`](../../notebooks/entrega_1_nacional_aipw/) (01–05), salvos com as saídas.
- Figuras e tabelas: [`outputs/entrega_1_nacional_aipw/`](../../outputs/entrega_1_nacional_aipw/); estimação completa em [`outputs/temporal/estimacao_v2/`](../../outputs/temporal/estimacao_v2/).
- Contrato metodológico V2 (formulações A, B e C, populações e suporte): [`docs/temporal/CONTRATO_V2_PRE_ESTIMACAO.md`](../temporal/CONTRATO_V2_PRE_ESTIMACAO.md); versão congelada em `outputs/temporal/v2_pre_estimacao/contrato_v2_congelado.json`.
- **Registro para leitura, não reexecutável na árvore atual.** Os notebooks de desenvolvimento da V1 → V2 (06–10, incluindo `10_estimacao_v2.ipynb`, citado no relatório), sua documentação de trabalho e os resultados intermediários de `outputs/temporal/` foram retirados em outubro de 2026. Estão no histórico Git (último commit com os arquivos: `e11bee6`) e precisam ser recuperados de lá para reexecutar esta entrega.

**Não confundir com a análise atual** ([`docs/sp_capital_ato/`](../sp_capital_ato/)): município de São Paulo, ponderação por sobreposição (ATO). Os números das duas fases (por exemplo, −1,48 p.p. nacional em 2024 e −1,74 p.p. na capital em 2024) têm populações, estimandos e estimadores diferentes e não devem ser combinados.
