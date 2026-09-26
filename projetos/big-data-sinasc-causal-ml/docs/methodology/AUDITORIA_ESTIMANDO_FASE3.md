# Auditoria do estimando — Fase 3

Esta auditoria conceitual preserva a população e T/Y/X da Fase 2. Nenhuma sensibilidade torna os nascidos vivos representativos de todas as concepções.

## Qual população está efetivamente descrita?

A extração SINASC 2024, com um registro por nascido vivo, `contador` único nesta extração, gestação registrada como única, peso observado entre 500 e 6.000 g e mês de início do pré-natal entre 1 e 9. São 2.251.570 registros. A unidade não é uma gestante identificada longitudinalmente nem uma concepção acompanhada desde o início.

Tratamento: início registrado nos meses 1–3; comparação: meses 4–9. Não se compara com ausência de pré-natal. Outcome: peso <2.500 g medido ao nascer. X: idade, escolaridade, raça/cor, situação conjugal, paridade, perdas fetais e UF. Município só identifica cluster. Não entram consultas, idade gestacional, tipo de parto, Apgar ou características neonatais.

O alvo estatístico, se os modelos recuperam as funções relevantes na distribuição selecionada S=1, é:

`E_{X|S=1}[ E(Y|T=1,X,S=1) − E(Y|T=0,X,S=1) ]`.

Essa padronização de contrastes observacionais é bem definida. Sua equivalência a um efeito causal requer hipóteses adicionais; não decorre do uso de AIPW nem da significância do intervalo.

## Momento da decisão e seleção

Uma política de início precoce deveria ser definida antes ou no início da gestação, com elegibilidade conhecida nesse momento e acompanhamento posterior. Aqui T é classificado retrospectivamente pelo mês registrado; não existe data individual de decisão, calendário de consultas completo ou tempo zero comum observado. A data de nascimento delimita 2024; não prova que todas as X foram medidas antes do início do pré-natal.

| Critério | Risco para uma intervenção no início da gestação |
|---|---|
| Nascido vivo | Sobrevivência até o nascimento pode ser afetada pelo tratamento e por causas de baixo peso. Condicionar sobrevivência pode abrir um collider; baixo peso ao nascer não é definido da mesma forma para concepções que não chegam a nascer vivas |
| Peso observado e intervalo P1 | Disponibilidade/mensuração e restrição em uma variável que define Y podem depender de tratamento, qualidade assistencial ou vulnerabilidade. A sensibilidade P0 relaxa o intervalo, mas ainda condiciona peso positivo observado |
| Gestação única registrada | Multiplicidade em grande parte se determina antes do pré-natal; registro ao final, por si só, não prova que seja pós-tratamento causalmente. Contudo, sobrevivência fetal diferencial, redução/perda de fetos e classificação final podem fazer a restrição diferir de uma elegibilidade basal conhecida |
| MESPRENAT observado | Informação pode depender de acesso, assistência e qualidade do registro. Excluir missing não é automaticamente ignorável. Exigir início em 1–9 restringe a quem tem pré-natal registrado; não representa uma política incluindo ausência de assistência |
| X no nascimento | Escolaridade, residência e situação conjugal são proxies de estado anterior, com temporalidade não demonstrada; idade e história reprodutiva também dependem da qualidade do registro |

Estrutura conceitual possível: `T → S ← U → Y`. Ajustar as sete X não necessariamente bloqueia a seleção criada por S, pois U pode não estar medido. Esta é uma hipótese de viés plausível, não uma estimativa empírica da direção ou tamanho do viés. Referências: [seleção perinatal](https://pmc.ncbi.nlm.nih.gov/articles/PMC6510491/) e [eventos competidores e nascimento vivo](https://pmc.ncbi.nlm.nih.gov/articles/PMC7755108/).

## Interpretação defensável

Uma diferença ajustada exploratória de risco de baixo peso entre início precoce e tardio **na população de registros selecionada**, estimada por AIPW com predições fora da amostra. Pode ser apresentada como estimativa sob hipóteses observacionais explicitamente não verificadas. Os diagnósticos Fase 3 avaliam estabilidade numérica e parte da incerteza amostral, não a identificação do efeito.

Para dar uma interpretação causal, seria necessário defender consistência de uma intervenção bem definida, intercambialidade condicional, positividade, ausência de interferência relevante, temporalidade de X e hipóteses que conectem a seleção observada aos outcomes potenciais. Diferentes conteúdos/qualidades de pré-natal dentro da mesma faixa de meses tornam a consistência especialmente substantiva. Nada nesta auditoria demonstra essas condições.

## Interpretações não defensáveis

- “Antecipar o pré-natal causa redução de X pp em todas as gestantes/concepções.”
- “Este é o efeito nos bebês que nasceriam vivos sob qualquer tratamento.” O estrato principal `S(1)=S(0)=1` não é observado nem identificado.
- “AIPW ou SE municipal remove confundimento, seleção ou viés de mensuração.”
- “Excluir discordâncias ou ampliar peso/multiplicidade corrige o viés de seleção.” São novos contrastes condicionais de sensibilidade.
- “O controle representa gestantes sem pré-natal” ou “o ganho pode ser convertido em ROI de uma política”. Não há desenho/intervenção/custos que sustentem essas afirmações.

## Limites das sensibilidades

Excluir CONSPRENAT=0 usa informação de consultas acumuladas, posterior ao início; é análise de discordância do registro, não ajuste causal por consultas. P0 adiciona pesos fora de 500–6.000 g sem mudar o limiar de Y; pode incluir erros de mensuração. Todas as gestações válidas incluem registros correlacionados de irmãos sem identificador da gestação. Clustering por residência pode abranger muitos desses pares, mas não comprova sua correspondência nem resolve dependência familiar entre endereços. Por isso a análise com múltiplas serve apenas à estabilidade direcional/magnitude.

## Conclusão conceitual

O risco de seleção já constava do plano da Fase 2; não é um erro novo de implementação nem razão para apagar seus resultados. A Fase 3 deve aprofundá-lo e manter a interpretação exploratória. Não há solução identificada nesta extração para transportar o contraste a todas as concepções ou recuperar um efeito em sobreviventes sob ambas as exposições. CATE/uplift e recomendações individuais permanecem fora de escopo.
