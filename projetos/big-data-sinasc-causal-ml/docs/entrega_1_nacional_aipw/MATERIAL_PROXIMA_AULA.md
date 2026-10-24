# Material para a próxima aula

Os três pontos solicitados: **(1) dicionário técnico, (2) matriz X–T–Y e (3) metadados da base.** Versão enxuta para projetar em tela; os detalhes estão nos documentos linkados.

---

## 1. Dicionário técnico

**Base raw:** 62 campos distintos em 2014–2024 (61 por ano até 2022; 62 em 2023–2024, com `OPORT_DN`). Todos são texto no CSV original. Lista completa: [DICIONARIO_TECNICO.md — Parte B](DICIONARIO_TECNICO.md#parte-b--dicionário-raw-todas-as-colunas-20142024) e [CSV](../../outputs/entrega_1_nacional_aipw/dicionario_raw_2014_2024.csv).

| Papel | Campos | Quantos |
| --- | --- | ---: |
| **Y** | `PESO` | 1 |
| **T** | `MESPRENAT` | 1 |
| **X** | `IDADEMAE`, `ESCMAE2010`, `RACACORMAE`, `ESTCIVMAE`, `PARIDADE`, `QTDFILMORT`, `CODMUNRES` (→ UF) | 7 |
| Elegibilidade | `GRAVIDEZ` (única), `DTNASC` (ano válido); `PESO` também (500–6.000 g) | 2 (+1) |
| Auxiliar | `CONTADOR` (chave); `CODMUNRES` também (cluster do erro-padrão) | 1 (+1) |
| Auditoria (fora de X) | `CONSPRENAT`, `CONSULTAS`, `SEMAGESTAC`, `GESTACAO`, `PARTO`, `KOTELCHUCK`, `ESCMAE`, `QTDGESTANT`, `QTDFILVIVO`, `TPMETESTIM`, `DTULTMENST` | 11 |
| Não utilizado | demais campos (Apgar, local do parto, anomalias, datas administrativas…) | 39 |

**Regras de codificação que importam:**

- Y = 1 se `PESO` < 2.500 g.
- T = 1 se `MESPRENAT` 1–3; T = 0 se 4–6. Os códigos 99 e vazio ficam fora de T, e não significam "sem pré-natal".
- Código 9 ou vazio nas categóricas → `IGNORADO`, que permanece no modelo; nenhum registro é excluído por missing em X.
- Perdas fetais: 0 / 1 / 2 ou mais / `IGNORADO`.
- Idade: 10–59 anos; fora disso, ausente, com imputação pela mediana e indicador de ausência.

Dicionário analítico completo, com tipo, missing e uso de cada variável: [DICIONARIO_TECNICO.md — Parte A](DICIONARIO_TECNICO.md#parte-a--dicionário-analítico).

---

## 2. Matriz X–T–Y

```
 X  (n × 7)                                   T (n × 1)        Y (n × 1)
 X1 idade · X2 escolaridade · X3 raça/cor     1 = 1º–3º mês    1 = peso < 2.500 g
 X4 situação conjugal · X5 paridade           0 = 4º–6º mês    0 = peso ≥ 2.500 g
 X6 perdas fetais · X7 UF
```

Exemplo de 2024, formulação B: n = 2.207.214 (T = 1: 1.942.045; T = 0: 265.169).

**Por que T não entra em X:**

| Função | Ajustada com | Para quê |
| --- | --- | --- |
| e(X) = P(T = 1 \| X) | X → T | quem tende a começar cedo |
| m₁(X) = E[Y \| T = 1, X] | X → Y, só T = 1 | risco com início precoce |
| m₀(X) = E[Y \| T = 0, X] | X → Y, só T = 0 | risco com início tardio |

O AIPW combina as três funções para estimar a diferença média de risco, m₁ − m₀, corrigida pela propensão.

**Nunca em X:** idade gestacional, consultas, tipo de parto, Apgar e Kotelchuck, por serem pós-exposição, mediadoras ou *collider*.

Explicação completa: [MATRIZ_XTY.md](MATRIZ_XTY.md).

---

## 3. Metadados da base

| Item | Valor |
| --- | --- |
| Dataset / instituição | SINASC — Ministério da Saúde / DATASUS (Portal de Dados Abertos do SUS) |
| Período | 2014–2024 (11 anos, análise por ano) |
| Cobertura | Brasil; 27 UFs; cerca de 5.580 municípios |
| Granularidade | 1 linha = 1 nascido vivo (DNV) |
| Volume bruto | **30.468.409** registros; 9,93 GB de CSV |
| População analítica | A: 28.194.211 · **B: 27.533.362** · C: 26.860.501 |
| Formato | CSV (`;`, UTF-8) em ZIP → Parquet (texto) → DuckDB |
| Target | BPN: 6,93% (2014) → 7,89% (2024) |
| Tratamento | início precoce (1º–3º mês): 78,55% (2014) → 86,25% (2024), população A |
| Features | 7 |
| Missing principal | `MESPRENAT` desconhecido: 7,57% (2014) → 3,39% (2024) da base bruta |
| Extração | 25/09/2026 (2024) e 29/09/2026 (2014–2023); SHA-256 por arquivo |
| Software | Python 3.11.9, DuckDB 1.5.5, pandas 3.0.6, scikit-learn 1.8.0 |

**Registros por ano:**

| | 2014 | 2016 | 2018 | 2020 | 2022 | 2024 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| N bruto | 2.979.259 | 2.857.800 | 2.944.932 | 2.730.145 | 2.561.922 | 2.389.325 |
| N analítico (B) | 2.615.773 | 2.560.827 | 2.672.423 | 2.476.058 | 2.344.255 | 2.207.214 |
| Colunas | 61 | 61 | 61 | 61 | 61 | 62 |

Todos os anos, fluxo de filtros e hashes: [METADADOS_BASE.md](METADADOS_BASE.md).
