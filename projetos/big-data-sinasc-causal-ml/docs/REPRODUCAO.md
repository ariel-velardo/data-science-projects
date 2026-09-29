# Reprodução e mapa dos notebooks

## Abrir a entrega pronta

Baixe `apresentacao/relatorio_interativo_sinasc_2024.html` e abra com dois cliques. O HTML é autocontido, usa apenas agregados e não exige Python, internet ou servidor. Referências externas exigem internet somente quando clicadas. Não é necessário refazer modelagem para consultar os resultados.

## Ambiente

Use exclusivamente a `.venv` deste projeto. A sessão de consolidação não instalou pacotes nem alterou o ambiente. Para **configuração manual de um ambiente novo**, execute no PowerShell:

```powershell
cd C:\GitHub\data-science-projects\projetos\big-data-sinasc-causal-ml
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = '1'
python -m pip install -r requirements.txt
python -m pip check
```

Se a `.venv` já existe, apenas ative-a; não a recrie. As versões do checkpoint estão no README histórico: `git show 07e9b7b:projetos/big-data-sinasc-causal-ml/README.md`. Os requisitos possuem intervalos; versões distintas não garantem igualdade numérica exata.

## Regenerar somente a Fase 5

```powershell
python -m src.literatura
python -m src.entrega
python scripts/validar_projeto.py --rapida
python -m pytest -q tests
python -m pip check
Start-Process .\apresentacao\relatorio_interativo_sinasc_2024.html
```

O gerador lê JSONs históricos, o dicionário versionado e o histograma agregado de propensity. Não lê caches individuais nem chama modelos. O histograma local da Fase 1 também é distribuído em JSON pela Fase 5 para permitir regeneração sem dados brutos. Os artefatos reconstruídos `outputs/tables/distribuicao_peso_250g.csv` e `outputs/tables/histograma_propensity.csv` são versionados e necessários ao contrato de reprodução; seus hashes permanecem ancorados.

Para refazer somente a auditoria dos códigos ignorados no dicionário (leitura do Parquet, sem alterar dados): `python -m src.entrega --auditar-dicionario`. Exige Parquet e PDF estrutural locais. Para tentar novamente downloads públicos: `python -m src.literatura --baixar`. PDFs ficam locais; não são necessários ao HTML.

## Reproduzir historicamente as Fases 0–4

Os comandos abaixo são documentação de reprodução, **não foram executados para ajustar modelos na Fase 5**. Exigem dados/caches locais ou download e tempo de processamento. Os contratos recusam caches incompatíveis.

```powershell
python scripts/baixar_dados.py
python scripts/executar_pipeline.py --etapa dados
python scripts/executar_pipeline.py --etapa amostra
python scripts/executar_pipeline.py --etapa preditivo
python scripts/executar_pipeline.py --etapa causal
python scripts/executar_pipeline.py --etapa robustez
python scripts/executar_pipeline.py --etapa heterogeneidade
python scripts/validar_projeto.py --completa
```

O checkpoint exato da Fase 3 é `48ce06b`, seguido da padronização `1d27ab4` e da Fase 4 `07e9b7b`. Os manifestos de preservação registram exceções de apresentação autorizadas. Validadores históricos de Fases 3–4 leem caches grandes para reconciliar resultados; não treinam modelos.

## Notebooks: entradas, objetivos e saídas

| Notebook | Entrada | Objetivo | Principais saídas |
|---|---|---|---|
| [01 — auditoria](../notebooks/01_auditoria_sinasc_2024.ipynb) | Parquet oficial preservado | Schema, chaves, T/Y candidatos, qualidade | Auditoria descritiva, campos ausentes, distribuição de peso/mês |
| [02 — amostra e overlap](../notebooks/02_amostra_desenho_e_overlap.ipynb) | JSONs e tabelas da Fase 1 | Explicitar desenho, fluxo e suporte | Perfil T/Y, SMD, propensity, gate |
| [03 — predição e AIPW](../notebooks/03_ml_preditivo_e_aipw.ipynb) | JSONs da Fase 2 | Comparar risco e contraste ajustado | ROC, AP, Brier, AIPW, sensibilidades |
| [04 — robustez](../notebooks/04_robustez_e_auditoria_metodologica.ipynb) | JSONs, Parquet e caches Fases 2–3 | Auditar IF, inferência municipal e gate | Reconciliação, clusters, Monte Carlo e sensibilidades |
| [05 — heterogeneidade](../notebooks/05_heterogeneidade_causal.ipynb) | JSONs, Parquet e cache da Fase 4 | Expor DR-Learner e validação externa | CATE, perfis, quintis, estabilidade e gate |

Os notebooks são registros históricos das fases. Frases como “Fase 5 não iniciada” descrevem o checkpoint em que foram produzidos, não o estado corrente. Os cinco arquivos `.ipynb` são agora artefatos-fonte versionados. Edite-os diretamente; a reprodução executa as fontes existentes via nbconvert/Jupyter:

```powershell
Get-ChildItem notebooks\0[1-5]*.ipynb | Sort-Object Name | ForEach-Object {
    python -m nbconvert --execute --to notebook --inplace `
        --ExecutePreprocessor.kernel_name=python3 `
        --ExecutePreprocessor.timeout=600 $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Falha em $($_.Name)" }
}
python scripts/validar_projeto.py --rapida
```

Selecione o interpretador `.venv\Scripts\python.exe` no VS Code/Jupyter; o kernel `python3` deve apontar para ele. Os notebooks 04–05 verificam esse caminho. A execução com `--inplace` atualiza outputs e metadados; não reconstrói nem traduz as fontes das células. Os cinco geradores históricos foram removidos. Os PNGs históricos dependem do navegador já utilizado pelo Kaleido; o HTML final não depende dele.

## Validação da entrega

`python scripts/validar_projeto.py --rapida` compara números marcados no README, síntese, resultados e HTML com os JSONs, exige cobertura das 62 colunas, verifica links internos, codificação e execução registrada dos notebooks. A inspeção visual e o teste de busca/navegação são complementares; testes estáticos não substituem navegador.

[Metodologia](METODOLOGIA_DO_PROJETO.md) · [Resultados](RESULTADOS_PRINCIPAIS.md).

## Arquitetura e validação consolidada

[Arquitetura final](architecture/ARQUITETURA_FINAL.md) e [auditoria da migração](architecture/REFATORACAO_SRC.md). Os comandos dos relatórios metodológicos históricos referem-se aos checkpoints em que foram produzidos; use os comandos desta página para a arquitetura atual.

- `python scripts/executar_pipeline.py --etapa todas`: reprodução deliberada das seis etapas existentes; pode ajustar modelos. Não necessário para conferir a entrega pronta.
- `python scripts/validar_projeto.py --rapida` ou `python -m src.validacao`: agregados, imports, métricas, gates, links, dicionário, HTML e estado/fontes/números dos cinco notebooks.
- `python scripts/validar_projeto.py --completa`: acrescenta reconciliação independente histórica, hashes dos dados/caches, testes e execução direta dos notebooks. Não reajusta modelos científicos; testes usam somente exemplos sintéticos.
- `python -m src.validacao --notebooks`: execução direta e conferência dos cinco notebooks; exige dados e caches locais.

Os contratos de cache antigos permanecem intactos. A correspondência entre hashes antigos e módulos conceituais está documentada em `docs/architecture/preservacao_refatoracao.json`; qualquer mudança de destino, dados ou contrato continua bloqueando a reutilização. Nenhum pacote foi instalado na refatoração.
