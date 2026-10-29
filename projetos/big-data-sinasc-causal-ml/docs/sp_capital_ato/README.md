# Análise atual — São Paulo (capital), ponderação por sobreposição (ATO)

Documentos da fase atual do projeto: SINASC 2024, mães residentes no município de São Paulo, início do pré-natal nos meses 1–3 (T=1) versus 4–6 (T=0), desfecho peso ao nascer < 2.500 g, escore de propensão logístico e pesos de sobreposição (ATO). A série 2014–2024 da mesma especificação é descritiva.

| Arquivo | Conteúdo |
|---|---|
| [RESUMO_PARA_REDACAO.md](RESUMO_PARA_REDACAO.md) | Consolidação de problema, dados, método, resultados, limitações, referências e questões abertas, com a fonte de cada número |
| [PACOTE_REDACAO_ETAPA_1.pdf](PACOTE_REDACAO_ETAPA_1.pdf) | Documento acadêmico **tal como entregue** no repasse da Etapa 1: estimação de 2024 (notebook 06). Registro histórico, não atualizado: ainda contém a subseção "Papel complementar do SIM", cita caminhos anteriores à reorganização e não inclui a série anual de estimativas ATO (notebook 07) nem a análise de temporalidade (notebook 08). Não representa o estado atual do estudo |
| [PACOTE_REDACAO_ETAPA_1_OVERLEAF/](PACOTE_REDACAO_ETAPA_1_OVERLEAF/) | Fonte LaTeX da Etapa 1, alterada em 26/10/2026 com a retirada do SIM; não corresponde exatamente ao PDF entregue. Preservada sem novas alterações; a versão de trabalho passou a ser a da Etapa 2 |
| [PACOTE_REDACAO_ETAPA_2_OVERLEAF/](PACOTE_REDACAO_ETAPA_2_OVERLEAF/) | Fonte LaTeX **atual** (Etapa 2, 27/10/2026): estimação de 2024 (notebook 06), série anual 2014–2024 (notebook 07), temporalidade e seleção (notebook 08), sem material do piloto SIM e com a origem de tabelas e figuras apontando para os nomes históricos dos notebooks. Compilar com XeLaTeX; instruções em `LEIA_ME.txt`. Situação do PDF e do ZIP abaixo |
| [artigos/LEIA_ME.md](artigos/LEIA_ME.md) | Índice das referências citadas; os PDFs de acesso aberto ficam só na cópia local (fora do Git) |

Os notebooks desta fase estão em [`notebooks/principal/`](../../notebooks/principal/) (01 a 05). Os números antigos nas descrições dos pacotes são históricos; consulte o [mapeamento da Etapa 2](../../README.md#correspondência-dos-notebooks-citados-na-etapa-2) para os caminhos atuais.

**Não confundir com a Entrega 1:** série nacional 2014–2024 estimada com AIPW, retirada da árvore ativa e recuperável no commit `af30d8d`, em `docs/entrega_1_nacional_aipw/`. População, estimando e estimador são diferentes, e os números das duas fases não devem ser combinados. As menções à entrega nacional no resumo para redação e no pacote acadêmico preservado referem-se a esse material histórico.

## Caminhos citados no PDF da Etapa 1

O PDF é o entregável já enviado e **não foi alterado**. A fonte LaTeX foi alterada uma única vez depois da entrega, em 26/10/2026: a subseção "Papel complementar do SIM" foi retirada, e as menções ao SIM em limitações e trabalhos futuros foram reescritas como referência contextual, porque o piloto SINASC + SIM saiu do projeto. A fonte anterior a essa alteração, versionada pela primeira vez em 24/10/2026 (commit `663becf`) e sem mudanças até o commit `2c9b16f`, é a que corresponde ao PDF entregue. A reorganização de 24/10/2026 mudou alguns caminhos que o PDF cita:

| Caminho citado no PDF | Caminho atual |
|---|---|
| `docs/entrega/RESUMO_PARA_REDACAO.md` | `docs/sp_capital_ato/RESUMO_PARA_REDACAO.md` |
| `docs/entrega/` (demais documentos, fase nacional) | histórico Git: `af30d8d`, pasta `docs/entrega_1_nacional_aipw/` |
| `outputs/qualidade_geografica_2024/qualidade_sp_2014_2024.ipynb` | `notebooks/principal/01_qualidade_geografica.ipynb` |
| `outputs/comparabilidade_sp_capital_2024/comparabilidade_sp_capital_2024.ipynb` | `notebooks/principal/02_comparabilidade.ipynb` |
| `outputs/qualidade_geografica_2024/qualidade_sp_por_ano.csv` | removido no lote 7C; indicadores calculados em memória no [notebook 01](../../notebooks/principal/01_qualidade_geografica.ipynb), objeto `dados` |
| `outputs/qualidade_geografica_2024/RECOMENDACAO_RECORTE.md` | [preservado](../../outputs/qualidade_geografica_2024/RECOMENDACAO_RECORTE.md), com a comparação de seis recortes de 2024 |
| `outputs/comparabilidade_sp_capital_2024/balanco_covariaveis_2024.csv` e `resumo_propensity_2024.csv` | removidos no lote 7C; tabelas `saida_balanco` e `resumo_ps` calculadas no [notebook 02](../../notebooks/principal/02_comparabilidade.ipynb) |
| `notebooks/principal/06_ato_sp_capital_2024.ipynb` | `notebooks/principal/03_estimacao_ato.ipynb` |
| `docs/methodology/DAG_INICIAL.md` | inalterado |

## Situação dos pacotes da Etapa 1

| Item | Situação |
|---|---|
| PDF entregue | `PACOTE_REDACAO_ETAPA_1.pdf`, nesta pasta, sem alteração desde o primeiro versionamento (`663becf`, 24/10/2026) |
| Fonte LaTeX atual | `PACOTE_REDACAO_ETAPA_1_OVERLEAF/`, alterada em 26/10/2026 (retirada do SIM) |
| `PACOTE_REDACAO_ETAPA_1_OVERLEAF.zip` entregue | não há cópia local nem versão no Git. O conteúdo da pasta correspondente pode ser recuperado no commit `2c9b16f`; um ZIP gerado a partir dele não é o arquivo original |
| `ANEXOS_TECNICOS_ETAPA_1.zip` entregue | cópia local em `_arquivo_local/entrega_sp_capital_etapa_1/`, fora do Git; contém o notebook 06 da entrega, a base analítica em CSV, um dicionário resumido e os artigos de acesso aberto |

Para gerar um ZIP do Overleaf a partir da versão **atual** da pasta (não equivalente ao entregue), no PowerShell:

```powershell
Compress-Archive -Path docs\sp_capital_ato\PACOTE_REDACAO_ETAPA_1_OVERLEAF\* -DestinationPath PACOTE_REDACAO_ETAPA_1_OVERLEAF.zip
```

O notebook 06 recebeu correções de redação e gráficos depois da entrega (registro em `docs/manutencao/ALTERACOES_REALIZADAS.md`, no histórico Git, commit `3dd446f`); as estimativas citadas no PDF não mudaram.

## Situação do pacote da Etapa 2

| Item | Situação |
|---|---|
| Fonte LaTeX | `PACOTE_REDACAO_ETAPA_2_OVERLEAF/`, criada em 27/10/2026 a partir da fonte da Etapa 1 e atualizada com os notebooks 05a a 08, sem reexecução nem alteração de resultados. Duas seções novas (série 2014–2024; temporalidade e seleção), quatro tabelas novas e duas figuras novas (`fig5_serie_ato_2014_2024.tex`, `fig6_temporalidade_2024.tex`) |
| Verificação estática | referências cruzadas, citações, arquivos de figura, balanço de chaves e ambientes, contagem de colunas das 15 tabelas, ausência de caminhos removidos e de material do piloto SIM; números das tabelas e figuras novas conferidos com as saídas salvas dos notebooks 07 e 08 |
| Correções após a compilação | em 27/10/2026: `headheight` de 15pt para 22pt em `main.tex`; no painel (b) da Figura 5 (`fig6_temporalidade_2024.tex`), a faixa sombreada que encobria as barras dos meses 4–6 foi substituída por uma linha divisória tracejada, com a nota da figura ajustada. Nenhum dado ou resultado foi alterado |
| Revisão editorial | em 29/10/2026: capa passa a identificar o documento como relatório técnico-científico; Apresentação reescrita de forma impessoal (pergunta, dados, população, método, resultados, série, temporalidade e limitações); seção "Orientação para a redação" removida, com a ressalva sobre a fase nacional AIPW incorporada à Discussão e as questões em aberto mantidas como subseção da Discussão. Números, tabelas, figuras, bibliografia e conclusões inalterados |
| PDF | a versão de 27/10/2026 (26 páginas, compilada em ambiente externo com XeLaTeX e BibTeXU) é anterior à revisão editorial e não corresponde à fonte atual. A fonte revisada ainda precisa ser compilada fora do repositório; o PDF não é armazenado aqui |
| Conferência da fonte | SHA-256 após normalização para LF: `main.tex` `0e482b7ee26c57d612aa2d71cd6c0b8cbbf46fda7b1858a3cecc8ed0e28576f5`; `figuras/fig6_temporalidade_2024.tex` `29b16858d6416f9225ac2b0a9e1ab9671ecc08b6d2659afdd3c62bc7110f8b60` |
| ZIP para o Overleaf | `PACOTE_REDACAO_ETAPA_2_OVERLEAF.zip`, regerado em 29/10/2026 a partir da fonte revisada, com os nove arquivos necessários à compilação (sem `LEIA_ME.txt`); cópia local em `_arquivo_local/entrega_sp_capital_etapa_2/`, fora do Git. Se a fonte mudar, o ZIP deve ser gerado de novo |
