# Roteiro de apresentação — 11 slides, cerca de 11 minutos

Tempo médio de 1 minuto por slide. As falas são sugestões para dizer com naturalidade, não para ler. Figuras em [outputs/entrega_1_nacional_aipw/figuras/](../../outputs/entrega_1_nacional_aipw/figuras/) (PNG para os slides; HTML interativo para eventuais perguntas).

---

## Slide 1 — O problema

- **Objetivo:** situar o tema e a relevância.
- **Conteúdo:**
  - baixo peso ao nascer (< 2.500 g) como marcador de risco neonatal;
  - recomendação de iniciar o pré-natal no 1º trimestre;
  - pergunta: o início precoce está associado a menos baixo peso, comparando gestantes parecidas?
- **Visual:** título e a pergunta de pesquisa em destaque. Sem gráfico.
- **Fala sugerida (≈ 45 s):**
  > "O baixo peso ao nascer, abaixo de 2,5 quilos, é um dos principais marcadores de risco para o recém-nascido. A recomendação é começar o pré-natal no primeiro trimestre. A pergunta do nosso trabalho é simples de enunciar e difícil de responder: entre gestantes parecidas, quem começa o pré-natal cedo tem menos bebês com baixo peso? O difícil é o 'entre gestantes parecidas': quem começa cedo é, em média, diferente de quem começa tarde."

## Slide 2 — Os dados

- **Objetivo:** mostrar a escala e a natureza da base.
- **Conteúdo:**
  - SINASC/DATASUS, 2014–2024;
  - 30,5 milhões de registros; 1 linha = 1 nascido vivo (DNV);
  - 61–62 colunas por ano;
  - CSV → Parquet → DuckDB.
- **Visual:** ficha resumida de [METADADOS_BASE.md](METADADOS_BASE.md) (tabela da seção 1, poucas linhas).
- **Fala sugerida (≈ 50 s):**
  > "Usamos o SINASC, o sistema do Ministério da Saúde que registra todos os nascidos vivos do país. São onze anos, de 2014 a 2024, cerca de 30 milhões e meio de registros: cada linha é uma declaração de nascido vivo. Baixamos os arquivos oficiais, guardamos o hash de cada um e convertemos para Parquet sem mexer nos valores. Todo o processamento foi feito em DuckDB. É Big Data no sentido prático: dá para estimar ano a ano com muita precisão, mas precisão não resolve viés, e esse vai ser o fio da apresentação."

## Slide 3 — Target e exposição

- **Objetivo:** definir Y e T sem ambiguidade.
- **Conteúdo:**
  - Y = 1 se `PESO` < 2.500 g (com faixa de qualidade 500–6.000 g);
  - T = 1 se `MESPRENAT` 1–3; T = 0 se 4–6 (formulação B);
  - prevalência de Y de cerca de 7–8%;
  - início precoce de 79% a 86%.
- **Visual:** Figura 1 (prevalência) e Figura 2 (início precoce), lado a lado.
- **Fala sugerida (≈ 60 s):**
  > "O desfecho é binário: baixo peso, sim ou não. A prevalência fica perto de 7% até 2020 e sobe para quase 8% de 2022 em diante. A exposição é o mês em que a gestante começou o pré-natal. Tratado é quem começou até o terceiro mês; o comparador é quem começou do quarto ao sexto mês. Repare que o início precoce cresceu muito no período: de 79% para 86%. Quem não informou o mês, ou registrou 99, fica de fora, e não tratamos isso como 'sem pré-natal'."

## Slide 4 — A matriz X–T–Y

- **Objetivo:** responder diretamente ao pedido da professora.
- **Conteúdo:**
  - X = n × 7: idade, escolaridade, raça/cor, situação conjugal, paridade, perdas fetais, UF;
  - T = n × 1; Y = n × 1;
  - o que fica fora de X: idade gestacional, consultas, parto, Apgar, Kotelchuck.
- **Visual:** diagrama da matriz de [MATRIZ_XTY.md](MATRIZ_XTY.md), seções 1 e 7.
- **Fala sugerida (≈ 60 s):**
  > "A base analítica tem três blocos. X são sete características da mãe que existem antes do pré-natal começar. T é uma coluna só: começou cedo ou tarde. Y é o baixo peso. Um ponto importante: não colocamos em X nada que acontece depois, como número de consultas, idade gestacional ou tipo de parto. Essas variáveis estão no caminho entre o pré-natal e o peso; ajustar por elas distorceria a comparação. E T não é misturado em X: ele tem um papel próprio no método, como vou mostrar."

## Slide 5 — Desenho observacional

- **Objetivo:** deixar claro que não é experimento e por que a formulação mudou.
- **Conteúdo:**
  - estudo observacional, sem sorteio;
  - hipóteses: intercambialidade condicional, positividade, consistência;
  - V1 (4–9) × V2 (4–6): o problema de quem só "chega" ao 7º–9º mês se a gestação durar.
- **Visual:** linha do tempo da gestação (meses 1–9) com as faixas T = 1, B e o trecho 7–9 excluído. Pode ser desenhada no próprio slide.
- **Fala sugerida (≈ 60 s):**
  > "Ninguém sorteou o mês de início do pré-natal; então, para ler o resultado como causal, precisamos supor que as sete variáveis de X capturam as diferenças relevantes entre os grupos. Essa hipótese não dá para testar. Além disso, encontramos um problema concreto na versão anterior do trabalho: só entra no grupo 'começou no oitavo mês' quem ainda estava grávida no oitavo mês. Isso exclui justamente os partos prematuros, que concentram o baixo peso. Por isso, a formulação principal compara o primeiro trimestre com o quarto a sexto mês. Isso reduz bastante o problema, mas não o elimina."

## Slide 6 — Método: AIPW com *cross-fitting*

- **Objetivo:** explicar o estimador sem fórmulas pesadas.
- **Conteúdo:**
  - e(X) = P(T = 1 | X);
  - m₁(X) e m₀(X);
  - AIPW = previsão + correção ponderada (duplamente robusto);
  - 3 partições estratificadas por T e Y;
  - C1/C2/C3;
  - IC agrupado por município.
- **Visual:** tabela das três funções de [MATRIZ_XTY.md](MATRIZ_XTY.md), seção 6, e um esquema das 3 partições.
- **Fala sugerida (≈ 60 s):**
  > "O AIPW usa dois tipos de modelo. Um estima a chance de cada gestante começar cedo, dado o seu perfil: é o escore de propensão. O outro estima o risco de baixo peso em cada grupo. O estimador combina os dois e é consistente se pelo menos um deles estiver certo; por isso se chama duplamente robusto. Para evitar sobreajuste, usamos ajuste cruzado: cada registro é previsto por modelos que nunca o viram. Testamos três combinações de modelos, de regressão logística a gradient boosting, e calculamos a incerteza agrupando por município, porque nascimentos da mesma cidade não são independentes."

## Slide 7 — Resultado principal (B)

- **Objetivo:** apresentar o número central.
- **Conteúdo:**
  - contraste C1 de −0,94 p.p. (2014) a −1,52 p.p. (2022);
  - 2024: −1,48 p.p. (IC95% −1,63 a −1,34);
  - todos os ICs abaixo de zero;
  - 2024 sinalizado por caudas da propensão.
- **Visual:** Figura 3 (B, C1 com IC95% municipal).
- **Fala sugerida (≈ 60 s):**
  > "Este é o resultado principal. Em todos os onze anos, o risco ajustado de baixo peso é menor para quem começou o pré-natal no primeiro trimestre: entre 0,9 e 1,5 ponto percentual a menos, numa prevalência de 7 a 8%. Em 2024, a diferença é de 1,48 ponto, com intervalo de 1,34 a 1,63. Nenhum intervalo chega perto de zero. O ano de 2024 aparece sinalizado porque um pouco mais de 10% dos registros têm escore de propensão extremo; ele foi mantido e reportado com essa ressalva."

## Slide 8 — Sensibilidades: comparador e modelos

- **Objetivo:** mostrar que a conclusão não depende de uma escolha específica.
- **Conteúdo:**
  - C (4–5): mesmo padrão, um pouco menos negativo;
  - C2 ≈ C3 (diferença ≤ 0,013 p.p.); C1 de 0,07 a 0,12 p.p. mais negativo;
  - *trimming* muda < 0,1 p.p.
- **Visual:** Figura 5 (C1/C2/C3) e, se houver espaço, um quadro pequeno com os números do *trimming*.
- **Fala sugerida (≈ 55 s):**
  > "Fizemos três tipos de checagem. Primeiro, um comparador mais restrito, só quarto e quinto mês: o padrão se repete, com valores um pouco menores, e vale lembrar que é outra pergunta, não uma correção da anterior. Segundo, trocamos os modelos: as duas versões com gradient boosting dão praticamente o mesmo número, e a logística fica uns 0,1 ponto mais negativa. Terceiro, removemos as observações com propensão extrema: a estimativa mexe menos de 0,1 ponto. Nenhuma dessas mudanças altera a conclusão."

## Slide 9 — Evolução temporal

- **Objetivo:** descrever a série sem atribuir causas.
- **Conteúdo:**
  - cresce de 2014 a 2018–2019; recua em 2020; volta a subir em 2021; pico em 2022; segue alto em 2023–2024;
  - B e C com o mesmo desenho;
  - sem teste formal de quebra.
- **Visual:** Figura 4 (B versus C com faixas de IC).
- **Fala sugerida (≈ 55 s):**
  > "Olhando no tempo, B e C contam a mesma história: a diferença aumenta até 2018 e 2019, recua em 2020, volta a subir e atinge o máximo em 2022, ficando alta depois. É tentador explicar 2020 pela pandemia ou 2022 por alguma política, mas não testamos isso. Não fizemos teste de quebra estrutural, e os intervalos de cada ano não consideram a dependência entre anos. Então tratamos isso como um padrão descritivo, que merece investigação própria."

## Slide 10 — Limitações

- **Objetivo:** ser transparente sobre o que o resultado não diz.
- **Conteúdo:**
  - confundimento residual (renda, tabagismo, nutrição, morbidades);
  - seleção por nascido vivo;
  - `MESPRENAT` retrospectivo;
  - problema temporal residual (D pendente);
  - IC sem dependência entre anos.
- **Visual:** lista curta, no máximo cinco itens.
- **Fala sugerida (≈ 50 s):**
  > "As principais limitações: primeiro, faltam variáveis importantes, como renda, tabagismo, nutrição e doenças prévias; mulheres com mais recursos tendem a começar cedo, e isso pode inflar a diferença. Segundo, só vemos gestações que terminaram em nascido vivo. Terceiro, o mês de início é registrado depois do parto, sem validação. E o problema temporal foi reduzido, não eliminado: a formulação que resolveria isso, a landmark, depende de informação que o SINASC não tem."

## Slide 11 — Conclusão

- **Objetivo:** fechar com a mensagem principal e o aprendizado metodológico.
- **Conteúdo:**
  - contraste AIPW ajustado consistente e negativo nos onze anos;
  - robusto a modelo, comparador e *trimming*;
  - estimativa sob hipóteses, não causalidade comprovada;
  - Big Data com disciplina causal.
- **Visual:** uma frase-síntese e o número de 2024 em destaque (−1,48 p.p.).
- **Fala sugerida (≈ 45 s):**
  > "Concluindo: com 27,5 milhões de nascidos vivos, o início do pré-natal no primeiro trimestre está associado a um risco de baixo peso de 0,9 a 1,5 ponto percentual menor, em todos os anos, com qualquer dos modelos e nas duas definições de comparador. É uma estimativa sob hipóteses, não uma prova de causalidade, mas é consistente com a recomendação de começar cedo. E o aprendizado principal para a disciplina é que volume de dados dá precisão; para chegar perto de causalidade, é preciso desenho."

---

**Perguntas prováveis e onde responder:** "por que não usar a idade gestacional?" → [MATRIZ_XTY.md](MATRIZ_XTY.md), seção 7; "o que é o 99?" → [DICIONARIO_TECNICO.md](DICIONARIO_TECNICO.md), linha `MESPRENAT`; "por que o município no erro-padrão?" → [relatório, seção 16](RELATORIO_FINAL_DISCIPLINA.md#16-inferência); números rápidos → [RESUMO_UMA_PAGINA.md](RESUMO_UMA_PAGINA.md).
