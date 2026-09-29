# Certificação técnica da refatoração

Estado: **EVIDENCIAS_CERTIFICACAO_PRESERVADAS; CONTRATO_FINAL_VALIDADO; REFATORACAO_HISTORICAMENTE_RECONCILIADA; CIENCIA_PRESERVADA**. As evidências executadas foram copiadas permanentemente para `C:\GitHub\_recuperacao_sinasc_5ae8e27\evidencias\`. Esse caminho é registro externo de custódia e não é dependência para reproduzir o projeto.

## Escopo e validação

- Branch `refactor/simplifica-src`; HEAD `f6e3df5380b7a008753e13ee341421082cee5799`.
- Checkpoint histórico `5ae8e272dd82016928b84dd3629decbecc1bff82`.
- `pytest --collect-only -q`: 165 testes; `pytest -q`: 165 aprovados, incluindo 13 casos novos de regressão de EOL e checkout.
- Preservação rápida/completa: 48 artefatos históricos; Fase 3: 22 linhas; Fase 4: aprovada.
- Checkouts limpos com `core.autocrlf=true` e `core.autocrlf=false`: 165 testes e guarda rápida aprovados em ambos.
- Hash portátil de `src/validacao.py`: `832357a35fa369e5431dd37aac283ffc1ce98c0765fbe20f5f8a1165fd25af33`; evolução preservada: `d732740d4955117fb72bfc636090cae556aad58cd91e15ea52825c4878237a51` → novo hash.
- Baseline e os dois CSVs têm os hashes ancorados em código. Os CSVs ainda são ignorados pelo Git e precisam de inclusão explícita no futuro commit.
- O inventário físico inicial tinha 211 arquivos. Nenhum dado, notebook, resultado ou cache científico mudou nesta rodada. Os testes atualizaram dois arquivos ignorados em `__pycache__`; não foram apagados.

## Ciência e notebooks

- N = 2.251.570; C1 = -1.340526785646844 pp; C2 = -1.2314558359825436 pp.
- Gate Fase 3: `GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR`; 22 linhas reconciliadas.
- CATE HGB médio = -1.294100493864875 pp; 84.68419813729975% negativos; gate Fase 4 = `HETEROGENEIDADE_SENSIVEL_A_MODELO`.
- Os cinco notebooks executados no isolamento têm fontes de células idênticas às cinco fontes oficiais. As execuções cobriram 7/7, 12/12, 13/13, 21/21 e 10/10 células, sem erros registrados. A reconciliação do isolamento registrou 140 hashes protegidos intactos, 26 PNG e 12 HTML.

## Arquitetura e riscos

- Comparação direta com o Git histórico: 157 definições; `CONTROLADOR_SUBSTITUIDO` 11, `IDENTICA_POR_AST` 122, `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` 13, `REMOVIDA_INTENCIONALMENTE` 11.
- Imports atuais resolvem, não há ciclo de import em nível de módulo, e as células de código dos cinco notebooks não importam módulos removidos.
- Comandos antigos permanecem em documentação metodológica histórica e no texto de alguns notebooks. A página corrente `docs/REPRODUCAO.md` aponta para as novas CLIs. Revisar editorialmente antes de citar os comandos históricos como instruções atuais.
- A custódia das evidências não depende mais de TEMP. O hash baseline histórico de `source_manifest.json` não é reproduzível; a exceção ancorada no blob Git permanece documentada e o projeto continua reprodutível sem o caminho externo de custódia.
- A guarda impede alteração acidental do JSON, do código e dos artefatos medidos, mas não oferece segurança contra alteração coordenada do validador, testes e contrato.

## Mapa função a função

Classificação por AST das definições de nível superior. Para funções adaptadas, o destino foi inspecionado manualmente; a igualdade AST não substitui validação de imports, contratos e resultados.

| Arquivo histórico | Função/classe | Destino atual | Status |
|---|---|---|---|
| `src/apresentacao_pt.py` | `traduzir` | `src/visualizacao.py:traduzir` | `IDENTICA_POR_AST` |
| `src/apresentacao_pt.py` | `rotulo` | `src/visualizacao.py:rotulo` | `IDENTICA_POR_AST` |
| `src/apresentacao_pt.py` | `tabela_pt` | `src/visualizacao.py:tabela_pt` | `IDENTICA_POR_AST` |
| `src/apresentacao_pt.py` | `exibir_pt` | `src/visualizacao.py:exibir_pt` | `IDENTICA_POR_AST` |
| `src/apresentacao_pt.py` | `imprimir_pt` | `src/visualizacao.py:imprimir_pt` | `IDENTICA_POR_AST` |
| `src/apresentacao_pt.py` | `aplicar_tema_ipt` | `src/visualizacao.py:aplicar_tema_ipt` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/apresentacao_pt.py` | `preparar_notebook` | `notebooks/ (fontes diretas)` | `REMOVIDA_INTENCIONALMENTE` |
| `src/apresentacao_pt.py` | `auditar_idioma` | `src/visualizacao.py:auditar_idioma` | `IDENTICA_POR_AST` |
| `src/audita_covariaveis.py` | `validar_colunas_propensity` | `src/diagnosticos.py:validar_colunas_propensity` | `IDENTICA_POR_AST` |
| `src/audita_covariaveis.py` | `_smd_numerico` | `src/diagnosticos.py:_smd_numerico` | `IDENTICA_POR_AST` |
| `src/audita_covariaveis.py` | `_smd_categorico` | `src/diagnosticos.py:_smd_categorico` | `IDENTICA_POR_AST` |
| `src/audita_covariaveis.py` | `calcular_smd` | `src/diagnosticos.py:calcular_smd` | `IDENTICA_POR_AST` |
| `src/audita_influencia.py` | `aipw_independente` | `src/robustez.py:aipw_independente` | `IDENTICA_POR_AST` |
| `src/audita_influencia.py` | `ess_grupos` | `src/robustez.py:ess_grupos` | `IDENTICA_POR_AST` |
| `src/audita_influencia.py` | `quantis` | `src/robustez.py:quantis` | `IDENTICA_POR_AST` |
| `src/audita_influencia.py` | `concentracao` | `src/robustez.py:concentracao` | `IDENTICA_POR_AST` |
| `src/audita_influencia.py` | `perfil_extremos` | `src/robustez.py:perfil_extremos` | `IDENTICA_POR_AST` |
| `src/audita_sinasc_2024.py` | `construir_baixo_peso_candidato` | `src/auditoria_dados.py:construir_baixo_peso_candidato` | `IDENTICA_POR_AST` |
| `src/audita_sinasc_2024.py` | `construir_tratamento_candidato` | `src/auditoria_dados.py:construir_tratamento_candidato` | `IDENTICA_POR_AST` |
| `src/audita_sinasc_2024.py` | `resumir_tratamento` | `src/auditoria_dados.py:resumir_tratamento` | `IDENTICA_POR_AST` |
| `src/audita_sinasc_2024.py` | `resumir_outcome` | `src/auditoria_dados.py:resumir_outcome` | `IDENTICA_POR_AST` |
| `src/audita_sinasc_2024.py` | `_identificador_sql` | `src/auditoria_dados.py:_identificador_sql` | `IDENTICA_POR_AST` |
| `src/audita_sinasc_2024.py` | `_percentual` | `src/auditoria_dados.py:_percentual` | `IDENTICA_POR_AST` |
| `src/audita_sinasc_2024.py` | `gerar_auditoria_parquet` | `src/auditoria_dados.py:gerar_auditoria_parquet` | `IDENTICA_POR_AST` |
| `src/audita_sinasc_2024.py` | `_markdown_auditoria` | `src/auditoria_dados.py:_markdown_auditoria` | `IDENTICA_POR_AST` |
| `src/audita_sinasc_2024.py` | `executar_auditoria_projeto` | `src/auditoria_dados.py:executar_auditoria_projeto` | `IDENTICA_POR_AST` |
| `src/baixa_dados_sinasc.py` | `calcular_sha256` | `src/sinasc.py:calcular_sha256` | `IDENTICA_POR_AST` |
| `src/baixa_dados_sinasc.py` | `verificar_arquivo_existente` | `src/sinasc.py:verificar_arquivo_existente` | `IDENTICA_POR_AST` |
| `src/baixa_dados_sinasc.py` | `baixar_arquivo_oficial` | `src/sinasc.py:baixar_arquivo_oficial` | `IDENTICA_POR_AST` |
| `src/baixa_dados_sinasc.py` | `baixar_fontes_e_gerar_manifesto` | `src/sinasc.py:baixar_fontes_e_gerar_manifesto` | `IDENTICA_POR_AST` |
| `src/carrega_sinasc.py` | `FormatoCSV` | `src/sinasc.py:FormatoCSV` | `IDENTICA_POR_AST` |
| `src/carrega_sinasc.py` | `descobrir_csv_no_zip` | `src/sinasc.py:descobrir_csv_no_zip` | `IDENTICA_POR_AST` |
| `src/carrega_sinasc.py` | `_detectar_encoding` | `src/sinasc.py:_detectar_encoding` | `IDENTICA_POR_AST` |
| `src/carrega_sinasc.py` | `detectar_formato_csv` | `src/sinasc.py:detectar_formato_csv` | `IDENTICA_POR_AST` |
| `src/carrega_sinasc.py` | `iterar_csv_em_chunks` | `src/sinasc.py:iterar_csv_em_chunks` | `IDENTICA_POR_AST` |
| `src/carrega_sinasc.py` | `validar_schema_minimo` | `src/sinasc.py:validar_schema_minimo` | `IDENTICA_POR_AST` |
| `src/constroi_amostra_analitica.py` | `construir_tratamento` | `src/amostra.py:construir_tratamento` | `IDENTICA_POR_AST` |
| `src/constroi_amostra_analitica.py` | `construir_outcome_baixo_peso` | `src/amostra.py:construir_outcome_baixo_peso` | `IDENTICA_POR_AST` |
| `src/constroi_amostra_analitica.py` | `identificar_gestacao_unica` | `src/amostra.py:identificar_gestacao_unica` | `IDENTICA_POR_AST` |
| `src/constroi_amostra_analitica.py` | `derivar_uf_residencia` | `src/amostra.py:derivar_uf_residencia` | `IDENTICA_POR_AST` |
| `src/constroi_amostra_analitica.py` | `_categoria_com_ignorado` | `src/amostra.py:_categoria_com_ignorado` | `IDENTICA_POR_AST` |
| `src/constroi_amostra_analitica.py` | `_categorizar_perdas_fetais` | `src/amostra.py:_categorizar_perdas_fetais` | `IDENTICA_POR_AST` |
| `src/constroi_amostra_analitica.py` | `preparar_covariaveis_principais` | `src/amostra.py:preparar_covariaveis_principais` | `IDENTICA_POR_AST` |
| `src/constroi_amostra_analitica.py` | `construir_cenarios_amostra` | `src/amostra.py:construir_cenarios_amostra` | `IDENTICA_POR_AST` |
| `src/cria_notebook_auditoria.py` | `criar_notebook` | `notebooks/ (fontes diretas)` | `REMOVIDA_INTENCIONALMENTE` |
| `src/cria_notebook_fase1.py` | `criar_notebook` | `notebooks/ (fontes diretas)` | `REMOVIDA_INTENCIONALMENTE` |
| `src/cria_notebook_fase2.py` | `criar_notebook` | `notebooks/ (fontes diretas)` | `REMOVIDA_INTENCIONALMENTE` |
| `src/cria_notebook_fase3.py` | `criar_notebook` | `notebooks/ (fontes diretas)` | `REMOVIDA_INTENCIONALMENTE` |
| `src/cria_notebook_fase4.py` | `criar_notebook` | `notebooks/ (fontes diretas)` | `REMOVIDA_INTENCIONALMENTE` |
| `src/diagnostica_overlap.py` | `diagnosticar_trimming` | `src/diagnosticos.py:diagnosticar_trimming` | `IDENTICA_POR_AST` |
| `src/diagnostica_overlap.py` | `resumir_overlap` | `src/diagnosticos.py:resumir_overlap` | `IDENTICA_POR_AST` |
| `src/diagnostica_overlap.py` | `construir_pipeline_propensity` | `src/diagnosticos.py:construir_pipeline_propensity` | `IDENTICA_POR_AST` |
| `src/diagnostica_overlap.py` | `estimar_propensity_oof` | `src/diagnosticos.py:estimar_propensity_oof` | `IDENTICA_POR_AST` |
| `src/dicionario_sinasc.py` | `papel_analitico` | `src/sinasc.py:papel_analitico` | `IDENTICA_POR_AST` |
| `src/dicionario_sinasc.py` | `grupo_temporal` | `src/sinasc.py:grupo_temporal` | `IDENTICA_POR_AST` |
| `src/documenta_fase4.py` | `tabela` | `docs/methodology/HETEROGENEIDADE_FASE4.md` | `REMOVIDA_INTENCIONALMENTE` |
| `src/documenta_fase4.py` | `documentar` | `docs/methodology/HETEROGENEIDADE_FASE4.md` | `REMOVIDA_INTENCIONALMENTE` |
| `src/entrega_fase5.py` | `ler` | `src/entrega.py:ler` | `IDENTICA_POR_AST` |
| `src/entrega_fase5.py` | `gravar` | `src/entrega.py:gravar` | `IDENTICA_POR_AST` |
| `src/entrega_fase5.py` | `numero` | `src/entrega.py:numero` | `IDENTICA_POR_AST` |
| `src/entrega_fase5.py` | `verificar_metricas` | `src/validacao.py:verificar_metricas` | `IDENTICA_POR_AST` |
| `src/entrega_fase5.py` | `links_quebrados` | `src/validacao.py:links_quebrados` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/entrega_fase5.py` | `validar_dicionario` | `src/validacao.py:validar_dicionario` | `IDENTICA_POR_AST` |
| `src/entrega_fase5.py` | `auditar_dicionario` | `src/entrega.py:auditar_dicionario` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/entrega_fase5.py` | `metricas` | `src/entrega.py:metricas` | `IDENTICA_POR_AST` |
| `src/entrega_fase5.py` | `marcador` | `src/entrega.py:marcador` | `IDENTICA_POR_AST` |
| `src/entrega_fase5.py` | `tabela_md` | `src/entrega.py:tabela_md` | `IDENTICA_POR_AST` |
| `src/entrega_fase5.py` | `tabela_html` | `src/entrega.py:tabela_html` | `IDENTICA_POR_AST` |
| `src/entrega_fase5.py` | `figuras` | `src/entrega.py:figuras` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/entrega_fase5.py` | `linhas_robustez` | `src/entrega.py:linhas_robustez` | `IDENTICA_POR_AST` |
| `src/entrega_fase5.py` | `gerar` | `src/entrega.py:gerar` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/entrega_fase5.py` | `validar` | `src/validacao.py:validar_entrega` | `CONTROLADOR_SUBSTITUIDO` |
| `src/estima_aipw.py` | `calcular_aipw` | `src/inferencia_causal.py:calcular_aipw` | `IDENTICA_POR_AST` |
| `src/estima_aipw.py` | `gerar_folds` | `src/inferencia_causal.py:gerar_folds` | `IDENTICA_POR_AST` |
| `src/estima_aipw.py` | `cross_fitting` | `src/inferencia_causal.py:cross_fitting` | `IDENTICA_POR_AST` |
| `src/estima_aipw.py` | `diagnosticos_influencia` | `src/inferencia_causal.py:diagnosticos_influencia` | `IDENTICA_POR_AST` |
| `src/estima_aipw.py` | `resumir_especificacoes` | `src/inferencia_causal.py:resumir_especificacoes` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_normalizar_json` | `src/sinasc.py:_normalizar_json` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_salvar_json` | `src/sinasc.py:_salvar_json` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_registros` | `src/sinasc.py:_registros` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_markdown_tabela` | `src/sinasc.py:_markdown_tabela` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_criar_views` | `src/amostra.py:_criar_views` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_auditar_base` | `src/auditoria_dados.py:_auditar_base` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_auditar_tratamento` | `src/auditoria_dados.py:_auditar_tratamento` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_auditar_peso` | `src/auditoria_dados.py:_auditar_peso` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_distribuicao_peso` | `src/auditoria_dados.py:_distribuicao_peso` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_auditar_gravidez` | `src/auditoria_dados.py:_auditar_gravidez` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_fluxo_amostra` | `src/auditoria_dados.py:_fluxo_amostra` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_auditar_missing` | `src/auditoria_dados.py:_auditar_missing` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_smd_balanceamento` | `src/auditoria_dados.py:_smd_balanceamento` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_perfil_tratamento` | `src/auditoria_dados.py:_perfil_tratamento` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_positividade` | `src/auditoria_dados.py:_positividade` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `_executar_propensity` | `src/auditoria_dados.py:_executar_propensity` | `IDENTICA_POR_AST` |
| `src/executa_fase1.py` | `executar_fase1` | `src/auditoria_dados.py:executar_auditoria_amostra` | `CONTROLADOR_SUBSTITUIDO` |
| `src/executa_fase1.py` | `main` | `scripts/executar_pipeline.py:main` | `CONTROLADOR_SUBSTITUIDO` |
| `src/executa_fase2.py` | `classificar_gate` | `src/inferencia_causal.py:classificar_gate` | `IDENTICA_POR_AST` |
| `src/executa_fase2.py` | `executar` | `src/inferencia_causal.py:executar_causal` | `CONTROLADOR_SUBSTITUIDO` |
| `src/executa_fase4.py` | `salvar` | `src/heterogeneidade.py:salvar_heterogeneidade` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/executa_fase4.py` | `patrimonio` | `src/validacao.py:patrimonio` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/executa_fase4.py` | `executar` | `src/heterogeneidade.py:executar_heterogeneidade` | `CONTROLADOR_SUBSTITUIDO` |
| `src/executa_robustez_fase3.py` | `sha256` | `src/sinasc.py:calcular_sha256` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/executa_robustez_fase3.py` | `salvar_fase3` | `src/robustez.py:salvar_fase3` | `IDENTICA_POR_AST` |
| `src/executa_robustez_fase3.py` | `historico` | `src/validacao.py:historico` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/executa_robustez_fase3.py` | `carregar_amostra` | `src/amostra.py:carregar_amostra` | `IDENTICA_POR_AST` |
| `src/executa_robustez_fase3.py` | `crossfit_auditoria` | `src/robustez.py:crossfit_auditoria` | `IDENTICA_POR_AST` |
| `src/executa_robustez_fase3.py` | `carregar_ou_ajustar` | `src/robustez.py:carregar_ou_ajustar` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/executa_robustez_fase3.py` | `resumo_predicoes` | `src/robustez.py:resumo_predicoes` | `IDENTICA_POR_AST` |
| `src/executa_robustez_fase3.py` | `auditar_original` | `src/robustez.py:auditar_original` | `IDENTICA_POR_AST` |
| `src/executa_robustez_fase3.py` | `validar_fase2_sem_escrita` | `src/validacao.py:validar_fase2_sem_escrita` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/executa_robustez_fase3.py` | `executar` | `src/robustez.py:executar_robustez` | `CONTROLADOR_SUBSTITUIDO` |
| `src/heterogeneidade_dr.py` | `pseudo_desfecho` | `src/heterogeneidade.py:pseudo_desfecho` | `IDENTICA_POR_AST` |
| `src/heterogeneidade_dr.py` | `particoes_municipais` | `src/heterogeneidade.py:particoes_municipais` | `IDENTICA_POR_AST` |
| `src/heterogeneidade_dr.py` | `rotacoes` | `src/heterogeneidade.py:rotacoes` | `IDENTICA_POR_AST` |
| `src/heterogeneidade_dr.py` | `criar_regressor` | `src/heterogeneidade.py:criar_regressor` | `IDENTICA_POR_AST` |
| `src/heterogeneidade_dr.py` | `ajustar_regressor` | `src/heterogeneidade.py:ajustar_regressor` | `IDENTICA_POR_AST` |
| `src/heterogeneidade_dr.py` | `prever_regressor` | `src/heterogeneidade.py:prever_regressor` | `IDENTICA_POR_AST` |
| `src/heterogeneidade_dr.py` | `ajuste_honesto` | `src/heterogeneidade.py:ajuste_honesto` | `IDENTICA_POR_AST` |
| `src/heterogeneidade_dr.py` | `quintis` | `src/heterogeneidade.py:quintis` | `IDENTICA_POR_AST` |
| `src/heterogeneidade_dr.py` | `resumo_distribuicao` | `src/heterogeneidade.py:resumo_distribuicao` | `IDENTICA_POR_AST` |
| `src/heterogeneidade_dr.py` | `resumir_grupos` | `src/heterogeneidade.py:resumir_grupos` | `IDENTICA_POR_AST` |
| `src/inferencia_cluster.py` | `agregar` | `src/robustez.py:agregar` | `IDENTICA_POR_AST` |
| `src/inferencia_cluster.py` | `resumo_cluster` | `src/robustez.py:resumo_cluster` | `IDENTICA_POR_AST` |
| `src/inferencia_cluster.py` | `bootstrap_cluster` | `src/robustez.py:bootstrap_cluster` | `IDENTICA_POR_AST` |
| `src/inferencia_cluster.py` | `leave_one_out` | `src/robustez.py:leave_one_out` | `IDENTICA_POR_AST` |
| `src/inferencia_cluster.py` | `folds_agrupados` | `src/robustez.py:folds_agrupados` | `IDENTICA_POR_AST` |
| `src/literatura_fase5.py` | `obter` | `src/literatura.py:obter` | `IDENTICA_POR_AST` |
| `src/literatura_fase5.py` | `documentar` | `src/literatura.py:documentar` | `IDENTICA_POR_AST` |
| `src/modelagem_preditiva.py` | `validar_x` | `src/modelagem_preditiva.py:validar_x` | `IDENTICA_POR_AST` |
| `src/modelagem_preditiva.py` | `criar_modelo` | `src/modelagem_preditiva.py:criar_modelo` | `IDENTICA_POR_AST` |
| `src/modelagem_preditiva.py` | `ajustar_modelo` | `src/modelagem_preditiva.py:ajustar_modelo` | `IDENTICA_POR_AST` |
| `src/modelagem_preditiva.py` | `predizer` | `src/modelagem_preditiva.py:predizer` | `IDENTICA_POR_AST` |
| `src/modelagem_preditiva.py` | `avaliar_probabilidades` | `src/modelagem_preditiva.py:avaliar_probabilidades` | `IDENTICA_POR_AST` |
| `src/modelagem_preditiva.py` | `_reduzir_curva` | `src/modelagem_preditiva.py:_reduzir_curva` | `IDENTICA_POR_AST` |
| `src/modelagem_preditiva.py` | `benchmark` | `src/modelagem_preditiva.py:benchmark` | `IDENTICA_POR_AST` |
| `src/prepara_sinasc_2024.py` | `ResultadoConversao` | `src/sinasc.py:ResultadoConversao` | `IDENTICA_POR_AST` |
| `src/prepara_sinasc_2024.py` | `_resultado_existente` | `src/sinasc.py:_resultado_existente` | `IDENTICA_POR_AST` |
| `src/prepara_sinasc_2024.py` | `converter_zip_para_parquet` | `src/sinasc.py:converter_zip_para_parquet` | `IDENTICA_POR_AST` |
| `src/resume_auditoria_fase3.py` | `gerar` | `docs/methodology/ROBUSTEZ_FASE3.md` | `REMOVIDA_INTENCIONALMENTE` |
| `src/resume_fase4.py` | `contraste_extremos` | `src/heterogeneidade.py:contraste_extremos` | `IDENTICA_POR_AST` |
| `src/resume_fase4.py` | `classificar` | `src/heterogeneidade.py:classificar` | `IDENTICA_POR_AST` |
| `src/resume_fase4.py` | `resumo` | `src/heterogeneidade.py:resumir_heterogeneidade` | `CONTROLADOR_SUBSTITUIDO` |
| `src/simulacao_gate_influencia.py` | `simular` | `src/robustez.py:simular` | `IDENTICA_POR_AST` |
| `src/valida_apresentacao.py` | `hash_arquivo` | `src/validacao.py:hash_arquivo` | `IDENTICA_POR_AST` |
| `src/valida_apresentacao.py` | `hash_fontes_notebook` | `src/validacao.py:hash_fontes_notebook` | `IDENTICA_POR_AST` |
| `src/valida_apresentacao.py` | `NumerosTabela` | `src/validacao.py:NumerosTabela` | `IDENTICA_POR_AST` |
| `src/valida_apresentacao.py` | `numeros_notebook` | `src/validacao.py:numeros_notebook` | `IDENTICA_POR_AST` |
| `src/valida_apresentacao.py` | `verificar_preservacao` | `src/validacao.py:verificar_preservacao` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |
| `src/valida_apresentacao.py` | `registrar_base` | `docs/architecture/BASELINE_PRE_REFATORACAO.md` | `REMOVIDA_INTENCIONALMENTE` |
| `src/valida_apresentacao.py` | `registrar_excecoes` | `docs/architecture/preservacao_refatoracao.json` | `REMOVIDA_INTENCIONALMENTE` |
| `src/valida_apresentacao.py` | `validar` | `src/validacao.py:validar_apresentacao` | `CONTROLADOR_SUBSTITUIDO` |
| `src/valida_resultados_fase2.py` | `validar` | `src/validacao.py:validar_fase2` | `CONTROLADOR_SUBSTITUIDO` |
| `src/valida_resultados_fase3.py` | `validar_folds_persistidos` | `src/validacao.py:validar_folds_persistidos` | `IDENTICA_POR_AST` |
| `src/valida_resultados_fase3.py` | `comparar_linha` | `src/validacao.py:comparar_linha` | `IDENTICA_POR_AST` |
| `src/valida_resultados_fase3.py` | `validar` | `src/validacao.py:validar_fase3` | `CONTROLADOR_SUBSTITUIDO` |
| `src/valida_resultados_fase4.py` | `validar` | `src/validacao.py:validar_fase4` | `CONTROLADOR_SUBSTITUIDO` |
| `src/visualizacao_ipt.py` | `configurar_plotly` | `src/visualizacao.py:configurar_plotly` | `IDENTICA_POR_AST` |
| `src/visualizacao_ipt.py` | `aplicar_tema_ipt` | `src/visualizacao.py:aplicar_tema_base` | `MOVIDA_COM_ADAPTACAO_NAO_CIENTIFICA` |

## Vereditos

- Evidências: `EVIDENCIAS_CERTIFICACAO_PRESERVADAS`.
- Contrato: `CONTRATO_FINAL_VALIDADO`.
- Refatoração: `REFATORACAO_HISTORICAMENTE_RECONCILIADA` para as funções científicas e artefatos verificados.
- Ciência: `CIENCIA_PRESERVADA`.
- Portabilidade: `PORTABILIDADE_EOL_RESOLVIDA`.
- Documentação: `DOCUMENTACAO_FINAL_CORRIGIDA`.
- Contrato portátil: `CONTRATO_PORTAVEL_VALIDADO`.
- Pré-staging: `PRONTO_PARA_STAGING_CONTROLADO`; esta rodada não executou staging nem commit.

## Plano exato de commit (não executado)

O `git status` apresenta 84 itens após a criação de `.gitattributes`; os dois CSVs ignorados são candidatos adicionais. Nenhum arquivo foi adicionado ao índice.

| Caminho | Classificação | Tipo | Risco | Relação com o refactor |
|---|---|---|---|---|
| `README.md` | `INCLUIR_NO_COMMIT` | modificação | baixo | Documentação e contrato da arquitetura |
| `docs/REPRODUCAO.md` | `INCLUIR_NO_COMMIT` | modificação | baixo | Documentação e contrato da arquitetura |
| `docs/RESULTADOS_PRINCIPAIS.md` | `INCLUIR_NO_COMMIT` | modificação | baixo | Documentação e contrato da arquitetura |
| `notebooks/01_auditoria_sinasc_2024.ipynb` | `INCLUIR_NO_COMMIT` | modificação | médio | Fonte migrada; células certificadas |
| `notebooks/02_amostra_desenho_e_overlap.ipynb` | `INCLUIR_NO_COMMIT` | modificação | médio | Fonte migrada; células certificadas |
| `notebooks/03_ml_preditivo_e_aipw.ipynb` | `INCLUIR_NO_COMMIT` | modificação | médio | Fonte migrada; células certificadas |
| `notebooks/04_robustez_e_auditoria_metodologica.ipynb` | `INCLUIR_NO_COMMIT` | modificação | médio | Fonte migrada; células certificadas |
| `notebooks/05_heterogeneidade_causal.ipynb` | `INCLUIR_NO_COMMIT` | modificação | médio | Fonte migrada; células certificadas |
| `outputs/diagnostics/fase3_gate.json` | `NAO_STAGEAR` | stat antigo | baixo | Conteúdo idêntico ao blob do HEAD em LF; a política fixa `eol=lf` |
| `src/apresentacao_pt.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/audita_covariaveis.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/audita_influencia.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/audita_sinasc_2024.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/baixa_dados_sinasc.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/carrega_sinasc.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/constroi_amostra_analitica.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/cria_notebook_auditoria.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/cria_notebook_fase1.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/cria_notebook_fase2.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/cria_notebook_fase3.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/cria_notebook_fase4.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/diagnostica_overlap.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/dicionario_sinasc.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/documenta_fase4.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/entrega_fase5.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/estima_aipw.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/executa_fase1.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/executa_fase2.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/executa_fase4.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/executa_robustez_fase3.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/heterogeneidade_dr.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/inferencia_cluster.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/literatura_fase5.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/modelagem_preditiva.py` | `INCLUIR_NO_COMMIT` | modificação | médio | Consolidação e guarda de preservação |
| `src/prepara_sinasc_2024.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/resume_auditoria_fase3.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/resume_fase4.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/simulacao_gate_influencia.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/valida_apresentacao.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/valida_resultados_fase2.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/valida_resultados_fase3.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/valida_resultados_fase4.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `src/visualizacao_ipt.py` | `INCLUIR_NO_COMMIT` | remoção pré-existente | médio | Módulo histórico substituído e mapeado no contrato |
| `tests/test_audita_sinasc.py` | `INCLUIR_NO_COMMIT` | modificação | baixo | Imports e ataques contratuais |
| `tests/test_baixa_dados_sinasc.py` | `INCLUIR_NO_COMMIT` | modificação | baixo | Imports e ataques contratuais |
| `tests/test_carrega_sinasc.py` | `INCLUIR_NO_COMMIT` | modificação | baixo | Imports e ataques contratuais |
| `tests/test_entrega_fase5.py` | `INCLUIR_NO_COMMIT` | modificação | baixo | Imports e ataques contratuais |
| `tests/test_fase1_amostra_e_overlap.py` | `INCLUIR_NO_COMMIT` | modificação | baixo | Imports e ataques contratuais |
| `tests/test_fase2_aipw.py` | `INCLUIR_NO_COMMIT` | modificação | baixo | Imports e ataques contratuais |
| `tests/test_fase3_robustez.py` | `INCLUIR_NO_COMMIT` | modificação | baixo | Imports e ataques contratuais |
| `tests/test_fase4.py` | `INCLUIR_NO_COMMIT` | modificação | baixo | Imports e ataques contratuais |
| `tests/test_idioma_notebooks.py` | `INCLUIR_NO_COMMIT` | modificação | baixo | Imports e ataques contratuais |
| `tests/test_prepara_sinasc.py` | `INCLUIR_NO_COMMIT` | modificação | baixo | Imports e ataques contratuais |
| `tests/test_validacao_fase3.py` | `INCLUIR_NO_COMMIT` | modificação | baixo | Imports e ataques contratuais |
| `docs/architecture/ARQUITETURA_FINAL.md` | `INCLUIR_NO_COMMIT` | novo | baixo | Documentação e contrato da arquitetura |
| `docs/architecture/CERTIFICACAO_REFATORACAO.md` | `INCLUIR_NO_COMMIT` | novo | baixo | Documentação e contrato da arquitetura |
| `docs/architecture/REFATORACAO_SRC.md` | `INCLUIR_NO_COMMIT` | novo | baixo | Documentação e contrato da arquitetura |
| `docs/architecture/preservacao_refatoracao.json` | `INCLUIR_NO_COMMIT` | novo | baixo | Documentação e contrato da arquitetura |
| `docs/literature/pdfs/chernozhukov2018.pdf` | `NAO_DEVE_ENTRAR` | novo | médio | Download local de literatura, alheio ao refactor |
| `docs/literature/pdfs/chernozhukov2018.txt` | `NAO_DEVE_ENTRAR` | novo | médio | Download local de literatura, alheio ao refactor |
| `docs/literature/pdfs/chiang2022.pdf` | `NAO_DEVE_ENTRAR` | novo | médio | Download local de literatura, alheio ao refactor |
| `docs/literature/pdfs/chiang2022.txt` | `NAO_DEVE_ENTRAR` | novo | médio | Download local de literatura, alheio ao refactor |
| `docs/literature/pdfs/falcao2020.pdf` | `NAO_DEVE_ENTRAR` | novo | médio | Download local de literatura, alheio ao refactor |
| `docs/literature/pdfs/falcao2020.txt` | `NAO_DEVE_ENTRAR` | novo | médio | Download local de literatura, alheio ao refactor |
| `docs/literature/pdfs/kennedy2023.pdf` | `NAO_DEVE_ENTRAR` | novo | médio | Download local de literatura, alheio ao refactor |
| `docs/literature/pdfs/kennedy2023.txt` | `NAO_DEVE_ENTRAR` | novo | médio | Download local de literatura, alheio ao refactor |
| `docs/literature/pdfs/ranjbar2023.pdf` | `NAO_DEVE_ENTRAR` | novo | médio | Download local de literatura, alheio ao refactor |
| `docs/literature/pdfs/ranjbar2023.txt` | `NAO_DEVE_ENTRAR` | novo | médio | Download local de literatura, alheio ao refactor |
| `scripts/baixar_dados.py` | `INCLUIR_NO_COMMIT` | novo | baixo | CLI substituta |
| `scripts/executar_pipeline.py` | `INCLUIR_NO_COMMIT` | novo | baixo | CLI substituta |
| `scripts/validar_projeto.py` | `INCLUIR_NO_COMMIT` | novo | baixo | CLI substituta |
| `src/amostra.py` | `INCLUIR_NO_COMMIT` | novo | médio | Consolidação e guarda de preservação |
| `src/auditoria_dados.py` | `INCLUIR_NO_COMMIT` | novo | médio | Consolidação e guarda de preservação |
| `src/diagnosticos.py` | `INCLUIR_NO_COMMIT` | novo | médio | Consolidação e guarda de preservação |
| `src/entrega.py` | `INCLUIR_NO_COMMIT` | novo | médio | Consolidação e guarda de preservação |
| `src/heterogeneidade.py` | `INCLUIR_NO_COMMIT` | novo | médio | Consolidação e guarda de preservação |
| `src/inferencia_causal.py` | `INCLUIR_NO_COMMIT` | novo | médio | Consolidação e guarda de preservação |
| `src/literatura.py` | `INCLUIR_NO_COMMIT` | novo | médio | Consolidação e guarda de preservação |
| `src/robustez.py` | `INCLUIR_NO_COMMIT` | novo | médio | Consolidação e guarda de preservação |
| `src/sinasc.py` | `INCLUIR_NO_COMMIT` | novo | médio | Consolidação e guarda de preservação |
| `src/validacao.py` | `INCLUIR_NO_COMMIT` | novo | médio | Consolidação e guarda de preservação |
| `src/visualizacao.py` | `INCLUIR_NO_COMMIT` | novo | médio | Consolidação e guarda de preservação |
| `tests/test_arquitetura.py` | `INCLUIR_NO_COMMIT` | novo | baixo | Imports e ataques contratuais |
| `outputs/tables/distribuicao_peso_250g.csv` | `INCLUIR_NO_COMMIT` | ignorado, promoção proposta | baixo | CSV pequeno, hash ancorado; inclusão futura exige força |
| `outputs/tables/histograma_propensity.csv` | `INCLUIR_NO_COMMIT` | ignorado, promoção proposta | baixo | CSV pequeno, hash ancorado; inclusão futura exige força |

Outros excluídos do futuro commit: `.venv/`, `__pycache__/`, `data/raw/SINASC_2024_csv.zip`, `data/processed/sinasc_2024.parquet`, os sete `outputs/tables/*.npz` e os pacotes locais de certificação. São ambiente, dados ou caches locais.

Mensagem sugerida: `refactor(sinasc): consolida src e fecha contrato de preservacao`

Corpo sugerido:

```text
Consolida modulos historicos em responsabilidades cientificas e CLIs.
Preserva as cinco fontes de notebooks, resultados, gates e caches.
Ancora evolucoes, codigo_atual, baseline e dois CSVs reconstruidos.
Adiciona testes adversariais e mapa historico de 157 definicoes.
Validacao: 165 testes; guardas rapida/completa, Fases 3/4 e dois checkouts limpos aprovados.
Evidencias executadas foram preservadas em custodia externa permanente.
```

Recomenda-se **um commit** para a consolidação e o fechamento contratual, após conferir a certificação preservada, a portabilidade e o índice. Antes desse commit: verificar branch/HEAD, hashes científicos, `git diff --check`, `pytest -q`, guardas de preservação e Fases 3/4 sem gravação de JSON; revisar `git diff --cached --stat` e `git diff --cached --name-status`. Os dois CSVs exigirão inclusão forçada, pois `.gitignore` ignora `outputs/tables/*`.
