# Resumo de uma página

**Qual o problema?**
O baixo peso ao nascer (BPN) é um marcador importante de risco neonatal, e a recomendação é iniciar o pré-natal no 1º trimestre. Quem inicia cedo, porém, difere de quem inicia tarde. A pergunta é se, entre gestantes comparáveis, o início precoce está associado a menos BPN.

**Quais dados?**
SINASC (Ministério da Saúde/DATASUS), 2014–2024: 30.468.409 registros brutos, com 61 colunas por ano (62 em 2023–2024). Os arquivos oficiais estão preservados com SHA-256 e foram processados em Parquet com DuckDB.

**Qual a granularidade?**
1 linha = 1 nascido vivo = 1 Declaração de Nascido Vivo. A análise é separada por ano, sem *pooling*. A chave é (ano, UF, `CONTADOR`).

**Qual o target?**
Y = 1 se `PESO` < 2.500 g; Y = 0 se ≥ 2.500 g (regra de qualidade: 500–6.000 g). A prevalência é de cerca de 6,9%–7,2% até 2020, 7,4% em 2021 e 7,9% em 2022–2024. Em 2024: 7,894891% (N = 2.251.570).

**Qual o tratamento?**
O momento de início do pré-natal (`MESPRENAT`). Na formulação principal B, T = 1 corresponde ao 1º–3º mês e T = 0 ao 4º–6º mês. A sensibilidade C usa 4º–5º mês como comparador, e a V1 histórica (A) usava 4º–9º mês. O código 99 e o vazio ficam fora de T. A, B e C são estimandos distintos.

**Quais X?**
Sete: idade materna, escolaridade (`ESCMAE2010`), raça/cor, situação conjugal, paridade, perdas fetais anteriores e UF de residência. **Não** entram: idade gestacional, consultas, tipo de parto, Apgar e Kotelchuck (mediadoras, pós-tratamento ou *collider*).

**Qual o método?**
AIPW (duplamente robusto) com ajuste cruzado em 3 partições estratificadas por 2T + Y (semente 20240925). Há três especificações: C1 (logística + logística), C2 (logística + HGB) e C3 (HGB + HGB). O IC95% usa erro-padrão agrupado por município, com t(G − 1). A análise principal é sem recorte; a sensibilidade usa [0,05; 0,95]. Antes da V2, um controle positivo reproduziu a V1/2024 (141/141 checagens, diferença máxima de 2,2 × 10⁻¹⁶).

**Qual o principal resultado?**
Na formulação B (C1), o contraste AIPW ajustado é negativo em todos os anos: de −0,936 p.p. (2014) a −1,524 p.p. (2022). Em 2024, é de **−1,480 p.p. (IC95% municipal −1,626 a −1,335)**. Nenhum IC inclui zero.

- **C (4–5):** mesmo padrão, de 0,04 a 0,15 p.p. menos negativo.
- **C2 ≈ C3:** diferença ≤ 0,013 p.p.; C1 fica de 0,07 a 0,12 p.p. mais negativo.
- ***Trimming*:** muda no máximo 0,067 p.p. (B) e 0,096 p.p. (C).
- **Anos sinalizados:** B/2024 e C/2017–2024, por caudas de propensão acima de 10%; mantidos.
- **Evolução temporal:** a magnitude cresce até 2018–2019, recua em 2020, atinge o pico em 2022 e permanece alta em 2023–2024. É um padrão descritivo, sem teste formal e sem atribuição de causa.

**Qual a principal limitação?**
O estudo é observacional, com confundimento residual plausível (renda, tabagismo, nutrição, morbidades e planejamento da gravidez não observados). Somam-se a isso a seleção por nascido vivo, o registro retrospectivo de `MESPRENAT` e um problema temporal residual (B reduz, mas não elimina; a formulação *landmark* D está pendente).

**Qual a conclusão?**
Entre gestantes comparáveis nas sete características observadas, o início do pré-natal no 1º trimestre está associado a um risco de BPN de 0,9 a 1,5 p.p. menor do que o início no 4º–6º mês, de forma consistente entre 2014 e 2024, entre modelos e entre definições de comparador. É uma estimativa sob hipóteses de identificação, e não um efeito causal comprovado.

---

Detalhes: [relatório](RELATORIO_FINAL_DISCIPLINA.md) · [tabelas](TABELAS_RESULTADOS.md) · [metadados](METADADOS_BASE.md) · [dicionário](DICIONARIO_TECNICO.md) · [matriz X–T–Y](MATRIZ_XTY.md)
