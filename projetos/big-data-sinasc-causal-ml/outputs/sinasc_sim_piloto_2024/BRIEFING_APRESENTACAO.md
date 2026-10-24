# Briefing para apresentação — SINASC + SIM 2024

**1. Pergunta causal original**
O início precoce do pré-natal reduz o risco de baixo peso ao nascer?

**2. Fontes oficiais e recorte**
SINASC e SIM, Ministério da Saúde/DATASUS. SINASC reutilizado de `data/processed/sinasc_2024.parquet`; SIM proveniente do [arquivo oficial DO24OPEN_csv.zip](https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SIM/csv/DO24OPEN_csv.zip), já preparado localmente. Residência em MG, ES, RJ ou SP; nascimentos e ocorrências de óbito em 2024. A interpretação de idade segue o [dicionário oficial](https://svs.aids.gov.br/daent/cgiae/coesv/sistemas-informacao/sim/documentacao/dicionario-de-dados-SIM-tabela-DOM.pdf) e as regras do `LEIA_ME.txt` existente.

**3. Quantidade de registros**
SINASC: **904.365 nascidos vivos**, com 903.067 pesos válidos. SIM utilizado: **10.432 óbitos infantis selecionados**. Totais calculados nos recortes completos, sem extrapolar amostras.

**4. Comparação descritiva de pré-natal**
Gestação única e peso entre 500 e 6.000 g (especificação B): início nos meses 1–3, 758.924 nascimentos e 61.974 com baixo peso (**8,17%**); meses 4–6, 84.074 nascimentos e 8.751 com baixo peso (**10,41%**). Diferença bruta T1−T0: **-2,24 pontos percentuais. DESCRITIVA, NÃO CAUSAL.**

**5. Quatro estados**

| UF | Nascidos vivos | Baixo peso válido | Baixo peso / peso válido | Óbitos infantis selecionados |
|---|---:|---:|---:|---:|
| ES | 49.937 | 4.508 | 9,04% | 602 |
| MG | 219.819 | 22.701 | 10,34% | 2.431 |
| RJ | 163.722 | 16.233 | 9,93% | 2.174 |
| SP | 470.887 | 46.799 | 9,95% | 5.225 |

Peso válido: 500–6.000 g; baixo peso válido: 500–2.499 g. O resumo estadual inclui todos os nascimentos; a comparação do item 4 restringe a gestação única e início nos meses 1–6.

**6. Principal resultado do painel municipal**
O painel conserva **1.672 códigos de residência** do SINASC: 1.133 com registros no recorte SIM e 539 sem linha correspondente. Os 10.432 óbitos selecionados encontram código correspondente no SINASC. Incluem-se os códigos residuais `310000`, `320000`, `330000`, `350000`, mantidos para preservar os totais e separados conceitualmente de municípios identificados; não se deve anunciar 1.672 municípios identificados.

Sem correspondência, `obitos_infantis_selecionados` fica **em branco**, com `status_sim=SEM_LINHA_NO_RECORTE_SIM`: ausência de linha não comprova ausência de óbitos. Percentuais com denominador zero também ficam em branco.

**7. Perfil dos registros infantis selecionados**
Dos 10.432 registros, **8.462 têm peso válido** (81,12%); **5.867 têm baixo peso**, correspondendo a **69,33% dos pesos válidos**. Os 1.970 registros restantes não entram nesse denominador. Esse percentual entre falecidos **não estima o risco de morrer entre nascidos com baixo peso**.

| Idade ao óbito | Registros | % dos selecionados |
|---|---:|---:|
| Neonatal precoce (0–6 dias) | 4.979 | 47,73% |
| Neonatal tardio (7–27 dias) | 1.970 | 18,88% |
| Pós-neonatal (28–364 dias) | 3.483 | 33,39% |
| Indeterminada | 0 | 0,00% |

Minutos e horas foram classificados como neonatal precoce; dias foram separados nos limites 6/7 e 27/28; meses 1–11 como pós-neonatal. O código `400` indica zero anos, mas não distingue essas faixas: quando presente, recebe indeterminada. O código bruto não foi interpretado como dias.

**8. O que foi cruzado**
Cada base foi agregada separadamente por `CODMUNRES`; depois, os indicadores do SIM foram acrescentados por **LEFT JOIN** aos códigos do SINASC. O cruzamento é territorial. **Não houve vinculação de indivíduos, mães ou declarações.**

**9. Limitações que devem aparecer nos slides**
A comparação bruta não é causal. Óbitos ocorridos em 2024 não representam acompanhamento individual dos nascimentos de 2024; não foi calculada taxa oficial de mortalidade infantil. O SIM utilizado é um subconjunto já selecionado, com exclusões de códigos de idade registradas no `LEIA_ME.txt`; os resultados não recuperam essas exclusões. **Óbitos fetais estão indisponíveis na fonte atual.** Pesos ausentes ou fora de 500–6.000 g ficam fora dos percentuais. Proporções municipais com poucos nascimentos exigem cautela.

**10. CSVs que fundamentam os números**
Caminhos relativos à raiz do projeto:

- `outputs/sinasc_sim_piloto_2024/painel_municipal_2024.csv`
- `outputs/sinasc_sim_piloto_2024/perfil_obitos_infantis_2024.csv`
- `outputs/sinasc_sim_piloto_2024/resumo_sinasc_sim_2024.csv`
- `outputs/sinasc_sim_piloto_2024/comparacao_descritiva_prenatal_2024.csv`

No perfil, `SUDESTE_TOTAL` é uma linha de totalização: não deve ser somada novamente às quatro UFs. CSVs usam ponto e vírgula e decimal ponto; importar `CODMUNRES` como texto. Percentuais do Sudeste usam somas dos numeradores e denominadores, não médias simples dos percentuais municipais.
