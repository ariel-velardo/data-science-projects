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
| Tabelas agregadas por ano | — | `outputs/temporal/tabelas/*.csv` (versionadas com `git add -f`, pois a raiz do workspace ignora `*.csv`; sem registros individuais) |
| Contrato das janelas | — | `outputs/temporal/contrato_temporal.json` (versionado) |
| Figuras | `outputs/figures/` (local) | `outputs/figures/temporal_*.png` (local, fora do Git; incorporadas ao notebook 07) |
| Registro de execução | — | `data/interim/temporal_registro_execucao.jsonl` (local, ignorado pelo Git) |

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

## Critérios de admissão — versão 1

Fixados em 29/09/2026 **antes** da leitura dos arquivos completos de 2014–2023 e sem nenhuma estimativa multianual. Implementados em `src.temporal.CRITERIOS_ADMISSAO` e `avaliar_criterios`; a auditoria usa as mesmas views congeladas de 2024 (`amostra._criar_views`), e sua aplicação ao Parquet certificado reproduz exatamente o fluxo A0–A3 e a tabela de ausentes de `fase1_amostra.json`.

| Critério | Regra | Falha implica |
|---|---|---|
| C01 arquivo íntegro | SHA-256 = manifesto; CRC íntegro; um único CSV | exclusão |
| C02 esquema identificável | nomes únicos sem diferenciar caixa; leitura por nome | exclusão |
| C03 desfecho presente | `PESO` | exclusão |
| C04 tratamento presente | `MESPRENAT` | exclusão |
| C05 covariáveis presentes | `IDADEMAE`, `ESCMAE2010`, `RACACORMAE`, `ESTCIVMAE`, `PARIDADE`, `QTDFILMORT`, `CODMUNRES`, `GRAVIDEZ`, `DTNASC` | exclusão |
| C06 codificação compatível | valores fora do domínio documentado ≤ 0,1% dos registros por campo | exclusão, salvo mapeamento documentado |
| C07 datas do ano | `DTNASC` válida e no ano do arquivo; até 0,01% admite exclusão documentada | harmonização ou exclusão |
| C08 `CONTADOR` utilizável | completo e único no ano; chave `(ano, CONTADOR)` | exclusão |
| C09 domínio de T | T=1 e T=0 presentes na população principal | exclusão |
| C10 domínio de Y | `PESO` não inteiro ≤ 0,1%; Y=0 e Y=1 presentes | exclusão |
| C11 categorias de X | níveis derivados contidos nos de 2024; município com 6 dígitos (até 0,01% com documentação) | exclusão ou harmonização |
| C12 ignorados quantificados | diferença > 5 p.p. frente a 2024 em ignorados de X ou T desconhecido | alerta, não exclusão |
| C13 baseline protegido | caminhos próprios; hashes de 2024 inalterados | exclusão |
| C14 fluxo reconciliável | bruto ≥ A0 ≥ A1 ≥ A2 = A3 > 0 | exclusão |
| C15 dado consolidado | sem qualificador preliminar/prévia | exclusão |

Veredito: qualquer falha → `NAO_APROVADO`; só harmonizações → `APROVADO_COM_HARMONIZACAO`; caso contrário → `APROVADO`. Alertas não excluem, mas precisam ser discutidos. Mudança de tolerância exige nova versão, justificada e registrada antes de qualquer estimativa.

### Emenda v1.1 — harmonização H1 (chave)

Registrada depois da leitura dos arquivos completos e **antes de qualquer estimativa**; restrita ao C08, sem tocar tolerâncias de T, Y ou X.

| Variável | Anos | Valor original | Valor harmonizado | Justificativa |
|---|---|---|---|---|
| `CONTADOR` | 2014–2017 | contador reinicia em 1 em cada UF de residência (27 sequências; ~2,3 milhões de repetições por ano) | chave `(ano, substr(CODMUNRES, 1, 2), CONTADOR)`, verificada única em cada ano | todas as linhas completas são distintas (sem duplicação de registros); afeta só o identificador técnico |

H1 é uma **harmonização de identificador**: não altera tratamento, desfecho, covariáveis, regras de inclusão, frequências nem valores científicos.

**Cronologia (não reescrever):** v1 fixada antes da leitura dos arquivos completos → H1 identificada após essa leitura (29/09/2026) → H1 **aprovada em revisão humana** (30/09/2026) → nenhuma estimação causal multianual até então. H1 não fazia parte da v1 original.

| Contrato | 2014–2017 | 2018–2024 |
|---|---|---|
| v1 (estrito, original) | `NAO_APROVADO` (C08) | `APROVADO` |
| v1.1 = v1 + H1 | `APROVADO_COM_HARMONIZACAO` | `APROVADO` |

Ambos os resultados ficam em `outputs/temporal/tabelas/criterios_admissao.csv` (`resultado` e `resultado_v1_estrito`) e `auditoria_anos.csv` (`veredito_v1`, `veredito_v1_1`); contratos, janelas e vereditos em `outputs/temporal/contrato_temporal.json`.

## Janelas congeladas (30/09/2026)

| Janela | Anos | Contrato | Uso |
|---|---|---|---|
| **Principal** | 2014–2024 | v1.1 | análise principal dos notebooks 08 e 09 |
| **Sensibilidade** | 2018–2024 | v1 estrito | **obrigatória** nos notebooks 08 e 09 |

As duas janelas são sempre reportadas; a escolha entre elas não pode depender de resultados futuros (`src.temporal.JANELAS`).

## Chave temporal

A camada temporal usa a chave uniforme `(ano, UF_res, CONTADOR)`, com `UF_res = substr(CODMUNRES, 1, 2)`, em todos os anos. Ela foi verificada única e com `CODMUNRES` bem formado em 2014–2024; em 2018–2024 equivale a `CONTADOR`, já único. `src.temporal.validar_chave_temporal` falha explicitamente se isso deixar de valer. A chave **identifica** registros e **não define ordem de processamento**; o contrato certificado de 2024 continua usando `CONTADOR`, sem alteração.

## Desenho em camadas e notebooks planejados

| Notebook | Camada | Conteúdo | Estado |
|---|---|---|---|
| 06_auditoria_historica_sinasc | — | disponibilidade, esquema, códigos, janela e critérios | criado |
| 07_descritiva_temporal_sinasc | A | N, fluxo A0–A3, ausentes/ignorados, prevalência de Y, proporção de T, covariáveis e UF por ano | criado |
| 08_estabilidade_temporal_overlap | B | SMD, composição, escore de propensão, suporte comum e positividade por ano | criado e executado |
| 08b_selecao_modelos_nuisance | B | seleção aninhada do propensity logístico em 2024 | revisado; C=1 preservado |
| 08c_benchmark_modelos_nuisance | B | benchmark preditivo das famílias de nuisance models em 2024 | parcial por orçamento; fechamento aprovado |
| 09_estabilidade_temporal_estimativas | C | AIPW independente por ano com C1/C2 congeladas | planejado |
| 10 — PoC Spark | independente | prova de conceito em branch própria | fora do desenho causal desta branch |
| (eventual) | D | análise empilhada, só se A–C justificarem; não é automaticamente a principal | não planejado |

## Uso

Na `.venv` deste projeto, no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = '1'
python -m pytest -q tests/test_temporal.py
python -m nbconvert --execute --to notebook --inplace --ExecutePreprocessor.kernel_name=python3 notebooks\06_auditoria_historica_sinasc.ipynb
```

## Situação dos dados (notebook 07)

Os ZIPs oficiais de 2014–2023 foram baixados um ano por vez (≈1,15 GB), com retomada por HTTP Range, verificação de tamanho e CRC, e convertidos para Parquet textual com a mesma rotina de 2024. Os SHA-256 de ZIP e Parquet estão nos manifestos por ano. A auditoria aplicada ao Parquet certificado de 2024 reproduz exatamente o fluxo A0–A3 e os ausentes de `fase1_amostra.json`.

Resumo descritivo (sem inferência): a prevalência do tratamento cresce de 78,6% (2014) para 86,3% (2024); o baixo peso fica em 6,9–7,2% até 2020 e apresenta uma **mudança de nível descritiva** por volta de 2021–2022, para ~7,9% em 2022–2024 (**possível mudança temporal a investigar**, sem atribuição causal a COVID-19 ou Zika); a associação bruta T=1 versus T=0 é negativa em todos os anos e passa de −0,72 p.p. para −1,42 p.p. 2024 está no extremo recente das tendências observadas e é semelhante em direção a 2022–2023. Detalhes no [notebook 07](../../notebooks/07_descritiva_temporal_sinasc.ipynb).

## Estabilidade temporal, suporte e positividade (notebook 08)

O notebook 08 foi executado na `.venv` do projeto para 2014–2024, com a janela 2018–2024 como sensibilidade obrigatória. A análise é diagnóstica: não estima AIPW, CATE, efeitos causais nem modelos empilhados. O pipeline anual de propensão replica o contrato certificado de 2024 (mesmas sete covariáveis pré-tratamento, pré-processamento, regressão logística, 5 folds estratificados e seed `20240925`). A comparação positiva de 2024 reproduziu exatamente N, grupos, AUC, quantis, suporte comum, caudas e histograma do artefato certificado.

Principais achados:

- há desequilíbrio bruto persistente entre tratamento e controle: o pior `|SMD|` anual cai de 0,441 em 2014 para 0,375 em 2024, mas permanece acima do limite diagnóstico de 0,10;
- a composição converge gradualmente para 2024; o pior `|SMD|` temporal fica abaixo de 0,10 somente a partir de 2022;
- não há perfis marginais com proporção de tratamento ≤1% ou ≥99%; células menores que 100 registros aparecem apenas na categoria `FAIXA_IDADE_MAE=IGNORADO`;
- nenhum registro fica fora de `[0,01; 0,99]`, enquanto 3,86%–6,55% ficam fora de `[0,05; 0,95]`; essas caudas são predominantemente tratadas e não devem ser somadas entre dimensões de perfil porque se sobrepõem;
- o ESS relativo melhora no período, mas o número absoluto de controles cai de aproximadamente 577 mil para 309 mil e o ESS de T=0 de aproximadamente 400 mil para 233 mil;
- os diagnósticos ao redor de 2021–2022 não mostram uma deterioração conjunta capaz de explicar, sozinha, a mudança descritiva do desfecho no notebook 07;
- a janela de sensibilidade 2018–2024 preserva as mesmas conclusões qualitativas.

Conclusão operacional: a fase C pode ser planejada com estimações independentes por ano, ambas as janelas congeladas e reporte obrigatório de N, caudas, suporte e ESS. Isso é uma autorização para **planejar** o notebook 09, não uma validação causal antecipada. Resultados, contrato diagnóstico e benchmarks estão em `outputs/temporal/`; caches locais com fingerprint ficam em `data/interim/temporal_overlap/`. Detalhes no [notebook 08](../../notebooks/08_estabilidade_temporal_overlap.ipynb).

## Fechamento de 08B e 08C

A sequência da expansão é: 06 auditoria histórica; 07 descrição temporal; 08 diagnóstico de overlap/positividade; 08B seleção do propensity logístico; 08C benchmark preditivo das famílias de nuisance models; 09 estimativas causais temporais, ainda não implementadas. A PoC Spark 10 segue em branch independente e não participa da especificação causal.

Em 08B, a seleção aninhada completa em 2024 (`N=2.251.570`, `T=0: 309.525`, `T=1: 1.942.045`, três folds externos e três internos, 48 fits) escolheu `C=1` nos três folds externos. O propensity principal continua `LogisticRegression` L2 com `C=1` (`BASELINE_C1_PRESERVADO`).

Em 08C, o HGB foi avaliado integralmente, ExtraTrees central teve três folds externos e RandomForest foi avaliado apenas no piloto de custo. A grade completa de ExtraTrees foi interrompida pela regra computacional pré-especificada: a projeção revisada foi de 12,61 horas. A revisão humana aceitou essa pendência pelo custo desproporcional, sem atribuí-la a resultado preditivo ou falha metodológica. O veredito factual permanece `BENCHMARK_NUISANCE_2024_PARCIAL`; registram-se `PENDENCIA_EXTRATREES_ACEITA_POR_ORCAMENTO`, `REVISAO_HUMANA_08B_08C_APROVADA` e `PRONTO_PARA_FECHAR_08B_08C`.

O HGB histórico fica como sensibilidade de propensity (`PROPENSITY_SENSIBILIDADE_ML_RECOMENDADA`): em 2024, log-loss 0,377690 versus 0,380096 e maior SMD ponderado 0,007294 versus 0,021745 no baseline. A fração fora de `[0,05; 0,95]` passou de 0,06580 para 0,06735, sem colapso de ESS. Para os outcomes, mantêm-se os modelos históricos logístico (C1) e HGB (C2): o HGB histórico teve ganho preditivo nos dois braços, mas a regra de 1 EP preservou sua configuração em 3/3 folds de cada braço (`OUTCOMES_HISTORICOS_MANTIDOS`). Nenhum efeito causal foi calculado em 08B/08C; ganho preditivo não implica melhoria causal. Os resumos agregados e o contrato de decisão estão em `outputs/temporal/tuning/` e `outputs/temporal/modelos_nuisance/`.

Para reproduzir o preparo dos dados (reutiliza arquivos íntegros; não toca 2024):

```powershell
python -c "from src import temporal as tp; tp.preparar_anos('.', range(2014, 2024))"
```
