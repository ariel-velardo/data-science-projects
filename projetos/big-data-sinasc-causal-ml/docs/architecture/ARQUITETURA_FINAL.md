# Arquitetura final

O projeto usa módulos por responsabilidade científica/técnica. Os nomes dos artefatos históricos `faseN_*` permanecem para preservar resultados, proveniência e referências documentais.

```text
src/
    __init__.py
    sinasc.py
    amostra.py
    auditoria_dados.py
    diagnosticos.py
    modelagem_preditiva.py
    inferencia_causal.py
    robustez.py
    heterogeneidade.py
    visualizacao.py
    entrega.py
    literatura.py
    validacao.py
scripts/
    baixar_dados.py
    executar_pipeline.py
    validar_projeto.py
notebooks/
    01_auditoria_sinasc_2024.ipynb
    02_amostra_desenho_e_overlap.ipynb
    03_ml_preditivo_e_aipw.ipynb
    04_robustez_e_auditoria_metodologica.ipynb
    05_heterogeneidade_causal.ipynb
```

| Módulo | Responsabilidade |
|---|---|
| sinasc | Fontes oficiais, hashes, leitura textual, conversão idempotente, metadados e serialização |
| amostra | Regras de elegibilidade, sete X congeladas, projeção SQL e carregamento com validação de chave/datas |
| auditoria_dados | Auditoria descritiva de schema, qualidade, fluxo e perfis da população |
| diagnosticos | Guarda de leakage, SMD e propensity usado para diagnóstico de suporte |
| modelagem_preditiva | Modelos auxiliares congelados e benchmark preditivo independente |
| inferencia_causal | AIPW, ajuste cruzado, influência, sensibilidades de suporte e gate histórico |
| robustez | Implementação independente, influência, clusters, simulação e sensibilidades de elegibilidade |
| heterogeneidade | DR-Learner, papéis municipais disjuntos, contrastes externos, resumos e gate |
| visualizacao | Tema IPT e camada PT-BR; sem geração ou tradução automática de notebooks |
| entrega | Geração do HTML e documentos consolidados a partir de agregados |
| literatura | Comportamento bibliográfico preservado; downloads somente por opção explícita |
| validacao | Reconciliação histórica, hashes, contratos, métricas, séries, links, idioma e execução dos notebooks |

`auditoria_dados` é o único módulo conceitual adicional à hipótese inicial: reúne consultas descritivas extensas, sem misturar leitura/conversão com os diagnósticos estatísticos. Há 12 módulos conceituais, além do inicializador. Scripts apenas orquestram; nenhuma lógica científica foi transferida a eles.

## Execução

Ative exclusivamente a `.venv` deste projeto no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = '1'
python -m src.entrega
python scripts/validar_projeto.py --rapida
```

Reprodução deliberada dos cálculos existentes, quando necessária:

```powershell
python scripts/executar_pipeline.py --etapa dados
python scripts/executar_pipeline.py --etapa amostra
python scripts/executar_pipeline.py --etapa preditivo
python scripts/executar_pipeline.py --etapa causal
python scripts/executar_pipeline.py --etapa robustez
python scripts/executar_pipeline.py --etapa heterogeneidade
```

`--etapa todas` segue essa ordem. A etapa dados usa o ZIP local; aquisição explícita é `python scripts/baixar_dados.py`. As etapas de modelagem reproduzem os estimadores congelados e podem levar tempo; não são chamadas para validar artefatos existentes. Nenhuma delas foi executada para reajustar modelos na refatoração.

## Validação

`python -m src.validacao` equivale à validação rápida. Ela confere imports, artefatos agregados, números publicados, gates, 62 campos, links, fontes e execução registrada dos cinco notebooks, idioma, HTML autocontido e séries/layouts dos gráficos. A proteção impede inclusão das estruturas individuais conhecidas no HTML.

`python scripts/validar_projeto.py --completa` acrescenta hashes dos arquivos grandes, reconciliação independente das Fases 2–4, suíte de testes e execução direta dos cinco notebooks via nbconvert. Exige os dados e caches locais; ausência ou incompatibilidade falha explicitamente, sem reajuste automático.

`python -m src.validacao --notebooks` executa somente os cinco notebooks e confere seus resultados. O kernel `python3` deve usar a `.venv`; os notebooks 04 e 05 verificam o interpretador. Nenhum gerador ou wrapper antigo é necessário.

## Notebooks e módulos

| Fonte versionada | Imports diretos de src | Entradas científicas |
|---|---|---|
| 01 | auditoria_dados, visualizacao | Parquet preservado |
| 02 | auditoria_dados, visualizacao | JSONs e tabelas da amostra/overlap |
| 03 | visualizacao | JSONs preditivos e AIPW |
| 04 | visualizacao, validacao | Agregados e reconciliação de robustez com caches |
| 05 | visualizacao, validacao | Agregados e reconciliação de heterogeneidade |

As células apresentam e auditam resultados; os ajustes completos ficam nos módulos científicos. Descrição, predição e inferência causal continuam distintas. Narrativas históricas e limitações são mantidas, inclusive os estados das fases na época de sua produção.

## Preservação e manutenção

[Baseline imutável](BASELINE_PRE_REFATORACAO.md) e [manifesto adicional](preservacao_refatoracao.json) ligam hashes anteriores aos destinos atuais. Os manifestos originais e contratos de cache não foram reescritos. Uma exceção exige hash anterior conhecido e hash de cada destino correspondente; não aceita alteração de dados, parâmetros, chaves ou cache.

Mudanças futuras em código protegido exigem auditoria e atualização explícita do manifesto; divergências são bloqueadas. Fontes de notebooks são verificadas separadamente dos metadados de execução. Números exibidos são comparados ao baseline. O HTML deve continuar idêntico ao baseline nesta refatoração.

[Reprodução completa](../REPRODUCAO.md) · [Inventário anterior](AUDITORIA_SRC.md) · [Relatório da refatoração](REFATORACAO_SRC.md).
