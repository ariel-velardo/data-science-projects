# Auditoria de src antes das alterações

Todos os arquivos de src, tests e notebooks foram lidos. As dependências abaixo incluem imports em funções e células; não foram inferidas apenas pelos nomes.

| Arquivo atual | Responsabilidade | Consumidores | Destino | Ação | Justificativa |
|---|---|---|---|---|---|
| apresentacao_pt.py | Camada de apresentação PT-BR; não altera dados ou chaves analíticas. | src/cria_notebook_auditoria.py, src/cria_notebook_fase1.py, src/cria_notebook_fase2.py, src/cria_notebook_fase3.py, src/cria_notebook_fase4.py, src/documenta_fase4.py, tests/test_idioma_notebooks.py, notebooks/01_auditoria_sinasc_2024.ipynb, notebooks/02_amostra_desenho_e_overlap.ipynb, notebooks/03_ml_preditivo_e_aipw.ipynb, notebooks/04_robustez_e_auditoria_metodologica.ipynb, notebooks/05_heterogeneidade_causal.ipynb, docs/REPRODUCAO.md | visualizacao | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| audita_covariaveis.py | Contrato de covariáveis, guarda de leakage e balanceamento bruto. | src/diagnostica_overlap.py, src/executa_fase1.py, src/executa_fase2.py, src/executa_fase4.py, src/executa_robustez_fase3.py, src/modelagem_preditiva.py, tests/test_fase1_amostra_e_overlap.py, tests/test_fase2_aipw.py, tests/test_fase4.py | diagnosticos | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| audita_influencia.py | AUDITORIA FASE 3: implementação independente, concentração e perfis. | src/executa_robustez_fase3.py, src/simulacao_gate_influencia.py, src/valida_resultados_fase3.py, tests/test_fase3_robustez.py | robustez | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| audita_sinasc_2024.py | Regras diagnósticas, não causais, para a auditoria do SINASC 2024. | src/cria_notebook_auditoria.py, tests/test_audita_sinasc.py, notebooks/01_auditoria_sinasc_2024.ipynb, docs/REPRODUCAO.md | auditoria_dados | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| baixa_dados_sinasc.py | Aquisição idempotente e verificação de integridade das fontes oficiais. | src/audita_sinasc_2024.py, tests/test_baixa_dados_sinasc.py, docs/REPRODUCAO.md | sinasc + scripts/baixar_dados.py | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| carrega_sinasc.py | Leitura segura e reproduzível de arquivos CSV do SINASC em ZIP. | src/audita_sinasc_2024.py, src/prepara_sinasc_2024.py, tests/test_carrega_sinasc.py | sinasc | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| constroi_amostra_analitica.py | Regras reproduzíveis da amostra analítica candidata da Fase 1. | tests/test_fase1_amostra_e_overlap.py | amostra | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| cria_notebook_auditoria.py | Gera o notebook acadêmico da Fase 0 com nbformat. | docs/REPRODUCAO.md | notebooks versionados (remover gerador) | Remover | Notebook versionado é a fonte; geração duplicada eliminada. |
| cria_notebook_fase1.py | Gera o notebook didatico e reproduzivel da Fase 1. | docs/REPRODUCAO.md | notebooks versionados (remover gerador) | Remover | Notebook versionado é a fonte; geração duplicada eliminada. |
| cria_notebook_fase2.py | Notebook didático com resultados persistidos da execução integral. | src/valida_apresentacao.py, docs/REPRODUCAO.md | notebooks versionados (remover gerador) | Remover | Notebook versionado é a fonte; geração duplicada eliminada. |
| cria_notebook_fase3.py | Notebook executável da auditoria, com tabelas e figuras IPT autocontidas. | src/resume_auditoria_fase3.py, docs/REPRODUCAO.md | notebooks versionados (remover gerador) | Remover | Notebook versionado é a fonte; geração duplicada eliminada. |
| cria_notebook_fase4.py | Gera o notebook 05 em português, com avaliação externa e limites explícitos. | src/documenta_fase4.py, docs/REPRODUCAO.md | notebooks versionados (remover gerador) | Remover | Notebook versionado é a fonte; geração duplicada eliminada. |
| diagnostica_overlap.py | Propensity score usado exclusivamente para diagnóstico de overlap. | src/executa_fase1.py, src/executa_fase2.py, src/executa_robustez_fase3.py, src/modelagem_preditiva.py, tests/test_fase1_amostra_e_overlap.py | diagnosticos | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| dicionario_sinasc.py | Metadados transcritos do dicionário oficial SINASC: Estrutura 1996 a 2019. | src/audita_sinasc_2024.py, src/entrega_fase5.py | sinasc | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| documenta_fase4.py | Acrescenta resultados validados ao protocolo da Fase 4, sem refazer modelos. | CLI/import direto | documentação versionada + entrega | Remover | Narrativa histórica versionada e entrega consolidada absorvem a responsabilidade. |
| entrega_fase5.py | Entrega acadêmica offline. Consome agregados históricos; nunca ajusta modelos. | src/literatura_fase5.py, tests/test_entrega_fase5.py, README.md, docs/REPRODUCAO.md | entrega + validacao | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| estima_aipw.py | AIPW transparente com predições OOF e SE por função de influência. | src/executa_fase2.py, src/executa_robustez_fase3.py, src/heterogeneidade_dr.py, src/valida_resultados_fase2.py, tests/test_fase2_aipw.py | inferencia_causal | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| executa_fase1.py | Executa a auditoria descritiva e o diagnostico de overlap da Fase 1. | src/cria_notebook_fase1.py, src/executa_fase2.py, src/executa_robustez_fase3.py, src/resume_auditoria_fase3.py, src/valida_resultados_fase2.py, notebooks/02_amostra_desenho_e_overlap.ipynb, docs/REPRODUCAO.md | amostra + auditoria_dados | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| executa_fase2.py | Executa os dois exercícios congelados sobre a população integral. | src/cria_notebook_fase2.py, tests/test_fase2_aipw.py, notebooks/03_ml_preditivo_e_aipw.ipynb, docs/REPRODUCAO.md | amostra + modelagem_preditiva + inferencia_causal | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| executa_fase4.py | Execução integral do DR-Learner; preserva resultados das Fases 0–3. | src/cria_notebook_fase4.py, src/documenta_fase4.py, src/resume_fase4.py, src/valida_resultados_fase4.py, notebooks/05_heterogeneidade_causal.ipynb, docs/REPRODUCAO.md | heterogeneidade + validacao | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| executa_robustez_fase3.py | AUDITORIA / SENSIBILIDADE FASE 3. Nunca escreve no histórico da Fase 2. | src/cria_notebook_fase3.py, src/executa_fase4.py, src/resume_auditoria_fase3.py, src/resume_fase4.py, src/valida_resultados_fase3.py, src/valida_resultados_fase4.py, tests/test_fase3_robustez.py, notebooks/04_robustez_e_auditoria_metodologica.ipynb, docs/REPRODUCAO.md | amostra + robustez + validacao | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| heterogeneidade_dr.py | DR-Learner com três papéis disjuntos: auxiliares, regressão e avaliação. | src/executa_fase4.py, src/resume_fase4.py, src/valida_resultados_fase4.py, tests/test_fase4.py | heterogeneidade | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| inferencia_cluster.py | Sandwich e bootstrap de clusters para a média de pseudo-outcomes fixos. | src/executa_robustez_fase3.py, src/resume_fase4.py, tests/test_fase3_robustez.py | robustez | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| literatura_fase5.py | Organiza referências revisadas e tenta obter PDFs públicos, sem contornar bloqueios. | docs/REPRODUCAO.md | literatura | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| modelagem_preditiva.py | Modelos congelados e benchmark de risco; não estima efeitos causais. | src/estima_aipw.py, src/executa_fase2.py, src/executa_robustez_fase3.py, src/heterogeneidade_dr.py | modelagem_preditiva | Preservar | Preservar cálculos e contratos em módulo conceitual. |
| prepara_sinasc_2024.py | Conversão reproduzível do CSV oficial em ZIP para Parquet textual. | tests/test_prepara_sinasc.py, docs/REPRODUCAO.md | sinasc | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| resume_auditoria_fase3.py | Tabelas do relatório Fase 3 derivadas dos artefatos validados. | docs/REPRODUCAO.md | documentação versionada + entrega | Remover | Narrativa histórica versionada e entrega consolidada absorvem a responsabilidade. |
| resume_fase4.py | Resumos descritivos e avaliação externa de heterogeneidade; nenhum reajuste. | src/cria_notebook_fase4.py, src/documenta_fase4.py, src/valida_resultados_fase4.py, tests/test_fase4.py, notebooks/05_heterogeneidade_causal.ipynb, docs/REPRODUCAO.md | heterogeneidade | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| simulacao_gate_influencia.py | Experimento de falsificação da heurística, com nuisances oráculo conhecidos. | src/executa_robustez_fase3.py, tests/test_fase3_robustez.py | robustez | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| valida_apresentacao.py | Rastreia números exibidos e exceções explícitas de apresentação autorizadas. | src/documenta_fase4.py, src/executa_fase4.py, src/executa_robustez_fase3.py, src/valida_resultados_fase3.py, tests/test_idioma_notebooks.py, docs/REPRODUCAO.md | validacao | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| valida_resultados_fase2.py | Reconcilia artefatos persistidos com dados e predições, sem reajustar modelos. | src/executa_robustez_fase3.py, docs/REPRODUCAO.md | validacao | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| valida_resultados_fase3.py | Reconciliação independente dos resumos Fase 3, sem refazer nuisances. | src/cria_notebook_fase3.py, src/documenta_fase4.py, src/resume_auditoria_fase3.py, tests/test_validacao_fase3.py, notebooks/04_robustez_e_auditoria_metodologica.ipynb, docs/REPRODUCAO.md | validacao | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| valida_resultados_fase4.py | Reconciliação das saídas DR-Learner com predições externas e população fixa. | src/cria_notebook_fase4.py, src/documenta_fase4.py, notebooks/05_heterogeneidade_causal.ipynb, docs/REPRODUCAO.md | validacao | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| visualizacao_ipt.py | Tema acadêmico Plotly inspirado na identidade visual do IPT. | src/apresentacao_pt.py, src/cria_notebook_auditoria.py, src/cria_notebook_fase1.py, src/cria_notebook_fase2.py, src/cria_notebook_fase3.py, src/cria_notebook_fase4.py, src/entrega_fase5.py, notebooks/01_auditoria_sinasc_2024.ipynb, notebooks/02_amostra_desenho_e_overlap.ipynb, notebooks/03_ml_preditivo_e_aipw.ipynb, notebooks/04_robustez_e_auditoria_metodologica.ipynb, notebooks/05_heterogeneidade_causal.ipynb | visualizacao | Consolidar | Preservar cálculos e contratos em módulo conceitual. |
| __init__.py | Funções reutilizáveis da auditoria do SINASC 2024. | CLI/import direto | __init__ | Preservar | Preservar cálculos e contratos em módulo conceitual. |

## Decisões de arquitetura

- `auditoria_dados.py` tem responsabilidade própria: consultas descritivas de schema, chave, qualidade e amostra, antes espalhadas pela auditoria inicial e executor da Fase 1. Evita somá-las à leitura/conversão ou às rotinas estatísticas.
- `resume_fase4.py` contém ciência única: contraste externo, agregação e gate. Incorporado integralmente em heterogeneidade.
- Helpers de serialização ficam em sinasc; projeção SQL e carregamento validado em amostra.
- Aquisição reutilizável permanece em sinasc para evitar dependência src → scripts; baixar_dados.py é somente a entrada CLI.
- Validadores e contratos de preservação ficam em validacao. Nenhum hash de resultado ou tolerância foi removido.
- Testes não importavam os cinco geradores; dois testes de preparação automática foram substituídos por auditoria das fontes versionadas. Tradução, números, idioma e hashes continuam protegidos.

## Detalhes por arquivo

### apresentacao_pt.py

- Funções/classes: traduzir, rotulo, tabela_pt, exibir_pt, imprimir_pt, aplicar_tema_ipt, preparar_notebook, auditar_idioma.
- Imports: import ast; import builtins; import io; import re; import tokenize; from pathlib import Path; import nbformat; import pandas as pd; from IPython.display import display as _display, Markdown; from src.visualizacao_ipt import aplicar_tema_ipt as _tema.
- Notebooks consumidores: notebooks/01_auditoria_sinasc_2024.ipynb, notebooks/02_amostra_desenho_e_overlap.ipynb, notebooks/03_ml_preditivo_e_aipw.ipynb, notebooks/04_robustez_e_auditoria_metodologica.ipynb, notebooks/05_heterogeneidade_causal.ipynb.
- Testes consumidores: tests/test_idioma_notebooks.py.
- Artefatos literais de entrada/saída: *.ipynb.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### audita_covariaveis.py

- Funções/classes: validar_colunas_propensity, _smd_numerico, _smd_categorico, calcular_smd.
- Imports: from __future__ import annotations; from collections.abc import Sequence; import numpy as np; import pandas as pd.
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_fase1_amostra_e_overlap.py, tests/test_fase2_aipw.py, tests/test_fase4.py.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### audita_influencia.py

- Funções/classes: aipw_independente, ess_grupos, quantis, concentracao, perfil_extremos.
- Imports: import numpy as np; import pandas as pd.
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_fase3_robustez.py.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### audita_sinasc_2024.py

- Funções/classes: construir_baixo_peso_candidato, construir_tratamento_candidato, resumir_tratamento, resumir_outcome, _identificador_sql, _percentual, gerar_auditoria_parquet, _markdown_auditoria, executar_auditoria_projeto.
- Imports: from __future__ import annotations; import json; from pathlib import Path; from typing import Any; import duckdb; import pandas as pd; from src.baixa_dados_sinasc import verificar_arquivo_existente; from src.carrega_sinasc import detectar_formato_csv; from src.dicionario_sinasc import (     CODIGOS_ESPECIAIS_DOCUMENTADOS,     DESCRICOES_OFICIAIS,     X_PROVAVEL_PRE_TRATAMENTO,     grupo_temporal,     papel_analitico, ).
- Notebooks consumidores: notebooks/01_auditoria_sinasc_2024.ipynb.
- Testes consumidores: tests/test_audita_sinasc.py.
- Artefatos literais de entrada/saída: AUDITORIA_VIABILIDADE.md, auditoria_schema_sinasc_2024.json, auditoria_viabilidade_sinasc_2024.json, sinasc_2024.parquet.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### baixa_dados_sinasc.py

- Funções/classes: calcular_sha256, verificar_arquivo_existente, baixar_arquivo_oficial, baixar_fontes_e_gerar_manifesto.
- Imports: from __future__ import annotations; import hashlib; import json; from datetime import date; from pathlib import Path; from typing import Any; import requests.
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_baixa_dados_sinasc.py.
- Artefatos literais de entrada/saída: source_manifest.json.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### carrega_sinasc.py

- Funções/classes: FormatoCSV, descobrir_csv_no_zip, _detectar_encoding, detectar_formato_csv, iterar_csv_em_chunks, validar_schema_minimo.
- Imports: from __future__ import annotations; import csv; import zipfile; from collections.abc import Iterator, Sequence, Set; from dataclasses import dataclass; from pathlib import Path; import pandas as pd.
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_carrega_sinasc.py.
- Artefatos literais de entrada/saída: .csv.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### constroi_amostra_analitica.py

- Funções/classes: construir_tratamento, construir_outcome_baixo_peso, identificar_gestacao_unica, derivar_uf_residencia, _categoria_com_ignorado, _categorizar_perdas_fetais, preparar_covariaveis_principais, construir_cenarios_amostra.
- Imports: from __future__ import annotations; from collections.abc import Iterable; import pandas as pd.
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_fase1_amostra_e_overlap.py.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### cria_notebook_auditoria.py

- Funções/classes: criar_notebook.
- Imports: from __future__ import annotations; from pathlib import Path; import nbformat as nbf; from src.apresentacao_pt import preparar_notebook.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: 01_auditoria_sinasc_2024.ipynb.
- Classificação: gerador histórico; sem ciência única; não é apenas CLI.

### cria_notebook_fase1.py

- Funções/classes: criar_notebook.
- Imports: from __future__ import annotations; from pathlib import Path; import nbformat as nbf; from src.apresentacao_pt import preparar_notebook.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: 02_amostra_desenho_e_overlap.ipynb.
- Classificação: gerador histórico; sem ciência única; não é apenas CLI.

### cria_notebook_fase2.py

- Funções/classes: criar_notebook.
- Imports: from pathlib import Path; import nbformat as nbf; from src.apresentacao_pt import preparar_notebook.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: notebooks/03_ml_preditivo_e_aipw.ipynb.
- Classificação: gerador histórico; sem ciência única; não é apenas CLI.

### cria_notebook_fase3.py

- Funções/classes: criar_notebook.
- Imports: from pathlib import Path; import nbformat as nbf; from src.apresentacao_pt import preparar_notebook.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: notebooks/04_robustez_e_auditoria_metodologica.ipynb.
- Classificação: gerador histórico; sem ciência única; não é apenas CLI.

### cria_notebook_fase4.py

- Funções/classes: criar_notebook.
- Imports: from pathlib import Path; import nbformat as nbf; from src.apresentacao_pt import preparar_notebook.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: notebooks/05_heterogeneidade_causal.ipynb.
- Classificação: gerador histórico; sem ciência única; não é apenas CLI.

### diagnostica_overlap.py

- Funções/classes: diagnosticar_trimming, resumir_overlap, construir_pipeline_propensity, estimar_propensity_oof.
- Imports: from __future__ import annotations; from collections.abc import Sequence; from typing import Any; import warnings; import numpy as np; import pandas as pd; from src.audita_covariaveis import validar_colunas_propensity; from sklearn.exceptions import ConvergenceWarning; from sklearn.compose import ColumnTransformer; from sklearn.impute import SimpleImputer; from sklearn.linear_model import LogisticRegression; from sklearn.pipeline import Pipeline; from sklearn.preprocessing import OneHotEncoder, StandardScaler; from sklearn.base import clone; from sklearn.metrics import roc_auc_score; from sklearn.model_selection import StratifiedKFold.
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_fase1_amostra_e_overlap.py.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### dicionario_sinasc.py

- Funções/classes: papel_analitico, grupo_temporal.
- Imports: nenhum.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### documenta_fase4.py

- Funções/classes: tabela, documentar.
- Imports: import json; from src.executa_fase4 import ROOT.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: docs/methodology/HETEROGENEIDADE_FASE4.md, fase4_ajustes.json, fase4_resultados.json, fase4_validacao.json.
- Classificação: gerador histórico; sem ciência única; não é apenas CLI.

### entrega_fase5.py

- Funções/classes: ler, gravar, numero, verificar_metricas, links_quebrados, validar_dicionario, auditar_dicionario, metricas, marcador, tabela_md, tabela_html, figuras, linhas_robustez, gerar, validar.
- Imports: from __future__ import annotations; import argparse; import csv; import hashlib; import html; import json; import re; import unicodedata; from pathlib import Path; from urllib.parse import unquote, urlsplit; import duckdb; from pypdf import PdfReader; from src.dicionario_sinasc import CODIGOS_ESPECIAIS_DOCUMENTADOS, X_PROVAVEL_PRE_TRATAMENTO, POS_TRATAMENTO; import pandas as pd; import plotly.graph_objects as go; from src.visualizacao_ipt import aplicar_tema_ipt; from plotly.offline import get_plotlyjs.
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_entrega_fase5.py.
- Artefatos literais de entrada/saída: *.md, .html, .md, 0[1-5]*.ipynb, README.md, apresentacao/relatorio_interativo_sinasc_2024.html, auditoria_schema_sinasc_2024.json, data/processed/sinasc_2024.parquet, docs/GRAFICOS_FINAIS.md, docs/RESULTADOS_PRINCIPAIS.md, docs/SINTESE_EXECUTIVA.md, docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md, docs/dados/FLUXO_DOS_DADOS.md, docs/literature/referencias_centrais.json, fase1_amostra.json, fase1_overlap.json; histograma_propensity.csv, fase2_aipw.json, fase2_modelagem_preditiva.json, fase3_cluster.json, fase3_crossfit_geografico.json, fase3_gate.json, fase3_sensibilidades.json, fase4_resultados.json, outputs/diagnostics/fase5_metricas.json, outputs/diagnostics/fase5_validacao.json, outputs/tables/dicionario_analitico_sinasc_2024.csv, outputs/tables/dicionario_analitico_sinasc_2024.json, outputs/tables/fase5_histograma_propensity.json.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### estima_aipw.py

- Funções/classes: calcular_aipw, gerar_folds, cross_fitting, diagnosticos_influencia, resumir_especificacoes.
- Imports: import hashlib; import numpy as np; from sklearn.model_selection import StratifiedKFold; from src.modelagem_preditiva import (SEED, validar_x, criar_modelo, ajustar_modelo,                                      predizer, avaliar_probabilidades).
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_fase2_aipw.py.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### executa_fase1.py

- Funções/classes: _normalizar_json, _salvar_json, _registros, _markdown_tabela, _criar_views, _auditar_base, _auditar_tratamento, _auditar_peso, _distribuicao_peso, _auditar_gravidez, _fluxo_amostra, _auditar_missing, _smd_balanceamento, _perfil_tratamento, _positividade, _executar_propensity, executar_fase1, main.
- Imports: from __future__ import annotations; import argparse; import json; from pathlib import Path; from typing import Any; import duckdb; import numpy as np; import pandas as pd; from src.audita_covariaveis import (     COLUNAS_PROPENSITY_PRINCIPAL,     VARIAVEIS_PROIBIDAS_PROPENSITY, ); from src.diagnostica_overlap import estimar_propensity_oof, resumir_overlap.
- Notebooks consumidores: notebooks/02_amostra_desenho_e_overlap.ipynb.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: balanceamento_bruto.csv, balanceamento_bruto.md, distribuicao_peso_250g.csv, fase1_amostra.json, fase1_overlap.json, fluxo_amostra.csv, fluxo_amostra.md, histograma_propensity.csv, missing_x_principal.csv, positividade_perfis.csv, positividade_perfis.md, sinasc_2024.parquet.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### executa_fase2.py

- Funções/classes: classificar_gate, executar.
- Imports: import hashlib; import json; import platform; import time; from pathlib import Path; import duckdb; import numpy as np; import pandas as pd; import sklearn; from sklearn.metrics import roc_auc_score; from src.executa_fase1 import _criar_views, _salvar_json, _markdown_tabela; from src.audita_covariaveis import COLUNAS_PROPENSITY_PRINCIPAL; from src.modelagem_preditiva import benchmark, avaliar_probabilidades, SEED; from src.estima_aipw import cross_fitting, resumir_especificacoes; from src.diagnostica_overlap import resumir_overlap.
- Notebooks consumidores: notebooks/03_ml_preditivo_e_aipw.ipynb.
- Testes consumidores: tests/test_fase2_aipw.py.
- Artefatos literais de entrada/saída: RESULTADOS_FASE2.md, data/processed/sinasc_2024.parquet, fase1_amostra.json, fase1_overlap.json, fase2_aipw.json, fase2_modelagem_preditiva.json, fase2_sensibilidades.json, outputs/tables/fase2_predicoes_oof.npz.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### executa_fase4.py

- Funções/classes: salvar, patrimonio, executar.
- Imports: import json; from pathlib import Path; import numpy as np; from src.audita_covariaveis import COLUNAS_PROPENSITY_PRINCIPAL; from src.executa_robustez_fase3 import carregar_amostra,sha256,historico; from src.heterogeneidade_dr import particoes_municipais,ajuste_honesto,rotacoes; from src.valida_apresentacao import verificar_preservacao.
- Notebooks consumidores: notebooks/05_heterogeneidade_causal.ipynb.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: 0[1-4]*.ipynb, apresentacao_*.json, data/processed/sinasc_2024.parquet, fase1_*.json, fase3_*.json, fase4_ajustes.json, fase4_preflight.json, fase4_preservacao.json, outputs/diagnostics/fase3_gate.json, outputs/diagnostics/fase3_preservacao.json, outputs/diagnostics/fase4_ajustes.json, outputs/diagnostics/fase4_preservacao.json, outputs/tables/fase4_predicoes_oof.npz.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### executa_robustez_fase3.py

- Funções/classes: sha256, salvar_fase3, historico, carregar_amostra, crossfit_auditoria, carregar_ou_ajustar, resumo_predicoes, auditar_original, validar_fase2_sem_escrita, executar.
- Imports: import argparse; import hashlib; import json; import time; from pathlib import Path; import duckdb; import numpy as np; import pandas as pd; from sklearn.metrics import roc_auc_score; from src.executa_fase1 import _criar_views, _salvar_json; from src.audita_covariaveis import COLUNAS_PROPENSITY_PRINCIPAL; from src.audita_influencia import aipw_independente, concentracao, ess_grupos, perfil_extremos; from src.inferencia_cluster import resumo_cluster, bootstrap_cluster, leave_one_out, folds_agrupados; from src.estima_aipw import gerar_folds, calcular_aipw, diagnosticos_influencia; from src.modelagem_preditiva import validar_x, criar_modelo, ajustar_modelo, predizer, avaliar_probabilidades; from src.diagnostica_overlap import resumir_overlap; from src.simulacao_gate_influencia import simular; import src.valida_resultados_fase2 as validador; from src.valida_apresentacao import verificar_preservacao.
- Notebooks consumidores: notebooks/04_robustez_e_auditoria_metodologica.ipynb.
- Testes consumidores: tests/test_fase3_robustez.py.
- Artefatos literais de entrada/saída: 03_ml_preditivo_e_aipw.ipynb, _ajustes.json, _oof.npz, data/processed/sinasc_2024.parquet, fase3_cluster.json, fase3_crossfit_geografico.json, fase3_influencia.json, fase3_monte_carlo.json, fase3_preservacao.json, fase3_sensibilidades.json, outputs/diagnostics/fase2_aipw.json, outputs/tables/fase2_predicoes_oof.npz, outputs/tables/fase3_c3_propensity_oof.npz, sinasc_2024.parquet.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### heterogeneidade_dr.py

- Funções/classes: pseudo_desfecho, particoes_municipais, rotacoes, criar_regressor, ajustar_regressor, prever_regressor, ajuste_honesto, quintis, resumo_distribuicao, resumir_grupos.
- Imports: import hashlib; import duckdb; import numpy as np; import pandas as pd; from sklearn.base import clone; from sklearn.ensemble import HistGradientBoostingRegressor; from sklearn.linear_model import Ridge; from threadpoolctl import threadpool_limits; from src.estima_aipw import calcular_aipw; from src.modelagem_preditiva import (validar_x,criar_modelo,ajustar_modelo,predizer,SEED).
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_fase4.py.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### inferencia_cluster.py

- Funções/classes: agregar, resumo_cluster, bootstrap_cluster, leave_one_out, folds_agrupados.
- Imports: import numpy as np; import pandas as pd; from scipy.stats import t as student_t; from sklearn.model_selection import StratifiedGroupKFold.
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_fase3_robustez.py.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### literatura_fase5.py

- Funções/classes: obter, documentar.
- Imports: import argparse; import hashlib; import io; import json; import re; from concurrent.futures import ThreadPoolExecutor; from urllib.parse import urljoin; import requests; from pypdf import PdfReader; from src.entrega_fase5 import ROOT, gravar, tabela_md.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: .md, docs/literature/MANIFESTO_ARTIGOS.md, docs/literature/REFERENCIAS_CENTRAIS.md, docs/literature/manifesto_artigos.json, docs/literature/referencias_centrais.json.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### modelagem_preditiva.py

- Funções/classes: validar_x, criar_modelo, ajustar_modelo, predizer, avaliar_probabilidades, _reduzir_curva, benchmark.
- Imports: import warnings; import numpy as np; from sklearn.compose import ColumnTransformer; from sklearn.ensemble import HistGradientBoostingClassifier; from sklearn.exceptions import ConvergenceWarning; from sklearn.metrics import (average_precision_score, brier_score_loss, roc_auc_score,                              precision_recall_fscore_support, roc_curve, precision_recall_curve); from sklearn.calibration import calibration_curve; from sklearn.model_selection import train_test_split; from sklearn.pipeline import Pipeline; from sklearn.preprocessing import OrdinalEncoder; from threadpoolctl import threadpool_limits; from src.audita_covariaveis import COLUNAS_PROPENSITY_PRINCIPAL, validar_colunas_propensity; from src.diagnostica_overlap import construir_pipeline_propensity.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### prepara_sinasc_2024.py

- Funções/classes: ResultadoConversao, _resultado_existente, converter_zip_para_parquet.
- Imports: from __future__ import annotations; from dataclasses import dataclass; from pathlib import Path; import pyarrow as pa; import pyarrow.parquet as pq; from src.carrega_sinasc import (     detectar_formato_csv,     iterar_csv_em_chunks,     validar_schema_minimo, ).
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_prepara_sinasc.py.
- Artefatos literais de entrada/saída: sinasc_2024.parquet.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### resume_auditoria_fase3.py

- Funções/classes: gerar.
- Imports: import json; from pathlib import Path; import pandas as pd; from scipy.stats import binomtest; from src.executa_fase1 import _markdown_tabela.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: docs/methodology/ROBUSTEZ_FASE3.md, fase3_cluster.json, fase3_crossfit_geografico.json, fase3_gate.json, fase3_influencia.json, fase3_monte_carlo.json, fase3_sensibilidades.json, fase3_validacao.json.
- Classificação: gerador histórico; sem ciência única; não é apenas CLI.

### resume_fase4.py

- Funções/classes: contraste_extremos, classificar, resumo.
- Imports: import json; from itertools import combinations; import duckdb; import numpy as np; import pandas as pd; from scipy.stats import spearmanr,t as student_t; from src.executa_fase4 import ROOT,salvar,patrimonio; from src.executa_robustez_fase3 import carregar_amostra,sha256; from src.heterogeneidade_dr import quintis,resumo_distribuicao,resumir_grupos; from src.inferencia_cluster import resumo_cluster.
- Notebooks consumidores: notebooks/05_heterogeneidade_causal.ipynb.
- Testes consumidores: tests/test_fase4.py.
- Artefatos literais de entrada/saída: Protocolo anterior ao ajuste em HETEROGENEIDADE_FASE4.md, data/processed/sinasc_2024.parquet, fase2_aipw.json, fase4_ajustes.json, fase4_gate.json, fase4_preservacao.json, fase4_resultados.json, outputs/tables/fase4_predicoes_oof.npz.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### simulacao_gate_influencia.py

- Funções/classes: simular.
- Imports: import numpy as np; from src.audita_influencia import aipw_independente, ess_grupos.
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_fase3_robustez.py.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### valida_apresentacao.py

- Funções/classes: hash_arquivo, hash_fontes_notebook, NumerosTabela, numeros_notebook, verificar_preservacao, registrar_base, registrar_excecoes, validar.
- Imports: import hashlib; import json; import re; from html.parser import HTMLParser; from pathlib import Path; import argparse.
- Notebooks consumidores: nenhum.
- Testes consumidores: tests/test_idioma_notebooks.py.
- Artefatos literais de entrada/saída: *.json, .ipynb, 0[1-4]*.ipynb, notebooks/03_ml_preditivo_e_aipw.ipynb, outputs/diagnostics/apresentacao_base.json, outputs/diagnostics/apresentacao_preservacao.json, outputs/diagnostics/fase3_preservacao.json.
- Classificação: validador com guardas únicas.

### valida_resultados_fase2.py

- Funções/classes: validar.
- Imports: import json; import hashlib; from pathlib import Path; import duckdb; import numpy as np; from src.executa_fase1 import _criar_views, _salvar_json; from src.estima_aipw import resumir_especificacoes.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: data/processed/sinasc_2024.parquet, fase2_aipw.json, fase2_validacao.json, outputs/tables/fase2_predicoes_oof.npz.
- Classificação: validador com guardas únicas.

### valida_resultados_fase3.py

- Funções/classes: validar_folds_persistidos, comparar_linha, validar.
- Imports: import json; from pathlib import Path; import duckdb; import numpy as np; import pandas as pd; from src.valida_apresentacao import verificar_preservacao; from src.audita_influencia import aipw_independente; from src.executa_robustez_fase3 import (carregar_amostra,historico,salvar_fase3,                                        validar_fase2_sem_escrita,sha256).
- Notebooks consumidores: notebooks/04_robustez_e_auditoria_metodologica.ipynb.
- Testes consumidores: tests/test_validacao_fase3.py.
- Artefatos literais de entrada/saída: _ajustes.json, data/processed/sinasc_2024.parquet, fase2_predicoes_oof.npz, fase3_consprenat_oof.npz, fase3_crossfit_geografico.json, fase3_geografico_oof.npz, fase3_multiplas_oof.npz, fase3_p0_oof.npz, fase3_preservacao.json, fase3_sensibilidades.json, fase3_validacao.json, outputs/tables/fase3_c3_propensity_oof.npz.
- Classificação: validador com guardas únicas.

### valida_resultados_fase4.py

- Funções/classes: validar.
- Imports: import json; import numpy as np; from src.executa_fase4 import ROOT,salvar,patrimonio; from src.executa_robustez_fase3 import carregar_amostra,sha256; from src.heterogeneidade_dr import particoes_municipais,rotacoes,quintis; from src.resume_fase4 import classificar; import hashlib; import pandas as pd.
- Notebooks consumidores: notebooks/05_heterogeneidade_causal.ipynb.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: data/processed/sinasc_2024.parquet, fase4_ajustes.json, fase4_gate.json, fase4_preservacao.json, fase4_resultados.json, fase4_validacao.json, outputs/tables/fase4_predicoes_oof.npz.
- Classificação: validador com guardas únicas.

### visualizacao_ipt.py

- Funções/classes: configurar_plotly, aplicar_tema_ipt.
- Imports: from __future__ import annotations; import plotly.graph_objects as go; import plotly.io as pio.
- Notebooks consumidores: notebooks/01_auditoria_sinasc_2024.ipynb, notebooks/02_amostra_desenho_e_overlap.ipynb, notebooks/03_ml_preditivo_e_aipw.ipynb, notebooks/04_robustez_e_auditoria_metodologica.ipynb, notebooks/05_heterogeneidade_causal.ipynb.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

### __init__.py

- Funções/classes: nenhuma.
- Imports: nenhum.
- Notebooks consumidores: nenhum.
- Testes consumidores: nenhum.
- Artefatos literais de entrada/saída: retorno em memória / caminhos compostos.
- Classificação: biblioteca de lógica reutilizável; responsabilidade preservada.

