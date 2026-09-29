# Expansão temporal do SINASC — frente em desenvolvimento

| | |
|---|---|
| **Referência certificada** | SINASC **2024**, notebooks 01–05, commit `a3c9095` ([certificação](../architecture/CERTIFICACAO_REFATORACAO.md)) |
| **Extensão em desenvolvimento** | análise multianual, branch `feature/expansao-temporal-sinasc` |
| **Validade causal da extensão** | **não estabelecida**; nenhuma estimativa multianual foi produzida |

Acrescentar anos não aumenta automaticamente a validade causal. A pergunta desta frente é se o padrão observado em 2024 é estável ou particular daquele ano.

## Regras de convivência com 2024

- Os notebooks 01–05, os JSONs de `outputs/diagnostics/`, os caches `.npz`, `data/raw/SINASC_2024_csv.zip`, `data/raw/source_manifest.json` e `data/processed/sinasc_2024.parquet` não são alterados nem migrados.
- Os módulos de `src/` e `scripts/` certificados estão ancorados por hash em [preservacao_refatoracao.json](../architecture/preservacao_refatoracao.json); a extensão vive em um módulo novo, `src/temporal.py`, sem editar os existentes.
- Para `ano=2024`, `src.temporal.caminhos_ano` devolve os caminhos legados; `baixar_sinasc_ano(raiz, 2024)` apenas verifica o SHA-256 do ZIP contra o manifesto histórico, sem rede e sem escrita.

## Estrutura de arquivos por ano

| Artefato | 2024 (legado, intocado) | Outros anos |
|---|---|---|
| ZIP bruto | `data/raw/SINASC_2024_csv.zip` | `data/raw/sinasc/<ano>/SINASC_<ano>_csv.zip` (local, ignorado pelo Git) |
| Parquet textual | `data/processed/sinasc_2024.parquet` | `data/processed/sinasc/sinasc_<ano>.parquet` (local) |
| Proveniência | `data/raw/source_manifest.json` | `outputs/temporal/manifestos/sinasc_<ano>.json` (versionado) |
| Auditoria de esquema | notebooks 01–02 | `outputs/temporal/inspecao_schema_sinasc.json`, `outputs/temporal/compatibilidade_anos.json` |

## Resultado da auditoria histórica (notebook 06)

Fonte: Portal de Dados Abertos do SUS, recursos "Nascidos Vivos - <ano>", inspecionados por HTTP Range (cabeçalho e ~1,5 MB por ano; ≈47 MB lidos no total), consulta em 29/09/2026.

| Anos | Classe | Motivo |
|---|---|---|
| 1996–2009 | incompatível | não existe `MESPRENAT`; tratamento não construível |
| 2010–2013 | sensibilidade pendente | transição da nova DN; faltam `PARIDADE` (2010–2013), `ESCMAE2010` (2010–2011) e `CONSPRENAT` (2013) |
| **2014–2024** | **janela principal provisória** | esquema de 2024 completo (exceto `OPORT_DN`, sem uso) e mesmos códigos nas variáveis críticas |
| 2025 | excluído por ora | publicado como "preliminar" |
| 2026 | excluído | "1ª prévia", arquivo parcial |

Diferenças de formato dentro da janela: caixa dos nomes (2016 em minúsculas; `contador`/`CONTADOR`), posição da chave (última coluna em 2016 e 2018–2022), aspas variáveis. A leitura deve ser por nome, sem diferenciar caixa, e a chave multianual é `(ano, CONTADOR)`.

Detalhes, riscos substantivos (COVID-19 em 2020–2021, Zika em 2015–2016, mudança de composição, dicionário oficial só até 2019) e os critérios de admissão de cada ano estão no [notebook 06](../../notebooks/06_auditoria_historica_sinasc.ipynb).

## Desenho em camadas e notebooks planejados

| Notebook | Camada | Conteúdo | Estado |
|---|---|---|---|
| 06_auditoria_historica_sinasc | — | disponibilidade, esquema, códigos, janela e critérios | criado |
| 07_descritiva_temporal_sinasc | A | N, fluxo A0–A3, ausentes/ignorados, prevalência de Y, proporção de T, covariáveis e UF por ano | planejado |
| 08_estabilidade_temporal_overlap | B | SMD, composição, escore de propensão, suporte comum e positividade por ano | planejado |
| 09_estabilidade_temporal_estimativas | C | AIPW independente por ano com C1/C2 congeladas | planejado |
| (eventual) | D | análise empilhada, só se A–C justificarem; não é automaticamente a principal | não planejado |

## Uso

Na `.venv` deste projeto, no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = '1'
python -m pytest -q tests/test_temporal.py
python -m nbconvert --execute --to notebook --inplace --ExecutePreprocessor.kernel_name=python3 notebooks\06_auditoria_historica_sinasc.ipynb
```

O download dos anos 2014–2023 (≈1,15 GB comprimidos) ainda **não** foi feito e requer autorização explícita.
