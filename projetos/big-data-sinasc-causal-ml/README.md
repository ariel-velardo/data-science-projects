# SINASC 2024: pré-natal precoce, baixo peso e inferência causal

Projeto acadêmico da disciplina **Big Data & Analytics**, em formato de artigo curto. A Fase 1 define a amostra analítica e audita o desenho observacional sobre início precoce do pré-natal e baixo peso ao nascer.

## Pergunta candidata

Entre gestantes comparáveis em características observáveis, iniciar o pré-natal até o terceiro mês de gestação está associado a uma redução no risco de baixo peso ao nascer?

Estrutura conceitual candidata:

- **X**: características observáveis anteriores ao tratamento;
- **T**: início do pré-natal até o terceiro mês;
- **Y**: peso ao nascer inferior a 2.500 g.

As definições ainda são candidatas. Nenhum efeito causal foi estimado.

## Fonte

Ministério da Saúde, [Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc), recurso **Nascidos Vivos - 2024**. A provenance completa está em `data/raw/source_manifest.json`.

## Status

`FASE_2_ML_E_AIPW` executada — benchmark e AIPW cross-fitted concluídos. Gate conservador `RESULTADO_NAO_INTERPRETAVEL` por concentração da função de influência; ver `docs/methodology/RESULTADOS_E_LIMITACOES_FASE2.md`. Causalidade não provada.

## Estrutura

- `data/raw/`: ZIP e dicionário oficiais, ignorados pelo Git, mais manifesto versionável;
- `data/processed/`: Parquet reproduzível, ignorado pelo Git;
- `src/`: aquisição, leitura, preparação, auditoria e tema visual;
- `tests/`: testes unitários com dados sintéticos;
- `notebooks/`: narrativa acadêmica executável;
- `outputs/diagnostics/`: diagnósticos pequenos em JSON;
- `docs/`: fontes, metodologia e estado do projeto.

## Ambiente

No PowerShell, a partir da raiz deste projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Reprodução da Fase 0

```powershell
python -m src.baixa_dados_sinasc
python -m src.prepara_sinasc_2024
python -m src.audita_sinasc_2024
python -m pytest -q tests
.\.venv\Scripts\jupyter-nbconvert.exe --execute --to notebook --inplace `
  --ExecutePreprocessor.kernel_name=sinasc-fase0 `
  --ExecutePreprocessor.timeout=600 notebooks/01_auditoria_sinasc_2024.ipynb
```

O download é idempotente e não sobrescreve o bruto existente. A preparação mantém os campos originais como texto, preservando zeros à esquerda, e não sobrescreve silenciosamente o Parquet.

## Reprodução da Fase 1

```powershell
python -m src.executa_fase1
python -m src.cria_notebook_fase1
python -m pytest -q tests
```

O notebook principal é `notebooks/02_amostra_desenho_e_overlap.ipynb`. O propensity score é apenas diagnóstico de suporte e não estima efeito de tratamento.

## Limite metodológico

A Fase 2 executou AIPW cross-fitted para a diferença média de risco na população selecionada, sob hipóteses observacionais explícitas. O gate conservador e as limitações estão documentados; causalidade não foi provada. Não foram executados Causal Forest ou CATE/uplift.
