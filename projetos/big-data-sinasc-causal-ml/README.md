# SINASC 2024: pré-natal precoce, baixo peso e inferência causal

Projeto acadêmico da disciplina **Big Data & Analytics**, em formato de artigo curto. A Fase 1 define a amostra analítica e audita o desenho observacional sobre início precoce do pré-natal e baixo peso ao nascer.

## Pergunta candidata

Entre gestantes comparáveis em características observáveis, iniciar o pré-natal até o terceiro mês de gestação está associado a uma redução no risco de baixo peso ao nascer?

Estrutura conceitual candidata:

- **X**: características observáveis anteriores ao tratamento;
- **T**: início do pré-natal até o terceiro mês;
- **Y**: peso ao nascer inferior a 2.500 g.

As definições foram congeladas na Fase 1. A Fase 2 estimou AIPW sob hipóteses observacionais, auditadas na Fase 3; causalidade não foi provada.

## Fonte

Ministério da Saúde, [Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc), recurso **Nascidos Vivos - 2024**. A provenance completa está em `data/raw/source_manifest.json`.

## Status

Fase 3 concluída no commit `48ce06b`: `GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR`. O registro histórico da Fase 2 permanece `RESULTADO_NAO_INTERPRETAVEL`; a auditoria revisa o uso da heurística como veto automático, sem certificar causalidade. Ver [robustez](docs/methodology/ROBUSTEZ_FASE3.md) e [estado atual](docs/playbooks/ESTADO_ATUAL.md).

## Estrutura

- `data/raw/`: ZIP e dicionário oficiais, ignorados pelo Git, mais manifesto versionável;
- `data/processed/`: Parquet reproduzível, ignorado pelo Git;
- `src/`: aquisição, leitura, preparação, auditoria e tema visual;
- `tests/`: testes unitários com dados sintéticos;
- `notebooks/`: narrativa acadêmica executável;
- `outputs/diagnostics/`: diagnósticos pequenos em JSON;
- `docs/`: fontes, metodologia e estado do projeto.

## Como executar o projeto localmente

No PowerShell, a partir da raiz do repositório `data-science-projects`:

```powershell
cd projetos\big-data-sinasc-causal-ml
if (-not (Test-Path .venv\Scripts\python.exe)) { py -3.11 -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q tests
```

A `.venv` existente está válida e não precisa ser recriada: Python 3.11.9, NumPy 2.4.6, Pandas 3.0.6, DuckDB 1.5.5, scikit-learn 1.8.0, Plotly 6.9.0 e Kaleido 1.4.0. `pip check` passou. O ambiente está ignorado pelo Git. Os requisitos têm intervalos de versões; igualdade numérica exata entre versões distintas não é garantida.

Use `.venv\Scripts\python.exe` no comando **Python: Select Interpreter** do VS Code e selecione esse mesmo ambiente no seletor de kernel do notebook. Para abrir o Jupyter, execute `python -m jupyter lab` com a `.venv` ativada. Os notebooks usam o kernel `python3`. Nenhum script auxiliar de instalação foi necessário.

## Reprodução da Fase 0

```powershell
python -m src.baixa_dados_sinasc
python -m src.prepara_sinasc_2024
python -m src.audita_sinasc_2024
python -m pytest -q tests
.\.venv\Scripts\jupyter-nbconvert.exe --execute --to notebook --inplace `
  --ExecutePreprocessor.kernel_name=python3 `
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

## Reprodução das Fases 2 e 3 e dos notebooks

Depois de preparar os dados locais e executar a Fase 1:

```powershell
python -m src.executa_fase2
python -m src.valida_resultados_fase2
python -m src.executa_robustez_fase3
python -m src.valida_resultados_fase3
python -m src.resume_auditoria_fase3
python -m src.cria_notebook_auditoria
python -m src.cria_notebook_fase1
python -m src.cria_notebook_fase2
python -m src.cria_notebook_fase3
python -m src.apresentacao_pt
Get-ChildItem notebooks\0[1-4]*.ipynb | Sort-Object Name | ForEach-Object {
    python -m nbconvert --execute --to notebook --inplace `
        --ExecutePreprocessor.kernel_name=python3 `
        --ExecutePreprocessor.timeout=600 $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Falha ao executar $($_.Name)" }
}
python -m src.valida_apresentacao
git diff --check
```

Os ajustes integrais são executados pelos módulos de cada fase; notebooks 02–04 consomem seus artefatos locais. Dados brutos, Parquet e predições grandes não são versionados. Os contratos de cache recusam dados/código incompatíveis. A reprodução histórica exata da Fase 3 está no checkpoint `48ce06b`; a tradução posterior mantém o manifesto original e documenta as duas exceções de apresentação em `outputs/diagnostics/apresentacao_preservacao.json`. Metadados voláteis de execução do notebook 03 são permitidos somente quando as fontes de todas as células permanecem iguais; a validação de apresentação reconcilia separadamente seus números exibidos.

## Limite metodológico

A Fase 2 executou AIPW cross-fitted para a diferença média de risco na população selecionada, sob hipóteses observacionais explícitas. O gate conservador e as limitações estão documentados; causalidade não foi provada. Não foram executados Causal Forest ou CATE/uplift.
