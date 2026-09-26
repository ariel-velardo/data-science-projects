# Gate Fase 1: PRONTO_COM_RESSALVAS

Avaliação em 26/09/2026, sobre a população candidata de 2.251.570 nascidos vivos.

A regressão logística L2 (L-BFGS, C=1, tolerância 1e-5, máximo 500 iterações) convergiu nos cinco folds estratificados: 54, 58, 49, 51 e 57 iterações. AUC OOF = 0,662873, apenas descritiva do assignment. A mudança do solver SAGA para L-BFGS foi técnica; T/Y/X e a penalização L2 foram preservados.

O suporte comum observado é [0,306807; 0,973928]. Não houve scores abaixo de 0,01 ou acima de 0,99. A regra 0,05–0,95 manteria 2.104.020 registros, retirando 140.879 tratados e 6.671 controles (6,55% da população total). Ela modifica a população-alvo e será somente sensibilidade.

O maior SMD bruto é 0,375 (situação conjugal), seguido de 0,331 (escolaridade). Nenhuma margem pré-especificada mostrou assignment quase determinístico. Isso não demonstra positividade em todas as combinações de X nem ausência de confundimento. Os scores são dependentes da forma funcional; o modelo alternativo de propensity, opcional, foi omitido para manter a fase parcimoniosa.

Há suporte para a primeira estimação exploratória sob hipóteses explícitas. Permanecem limitações: confundidores ausentes, covariáveis registradas no nascimento como proxies de características prévias, mensuração retrospectiva do mês, seleção por nascido vivo e peso/informação disponível. Não se extrapola o resultado a todas as concepções.

CONSPRENAT=0 não define o tratamento. Existem 1.098 registros com mês válido e zero consultas na base, uma discordância documentada. Eles seguem a regra MESPRENAT, sem mudança retrospectiva da amostra. A frase anterior de que todos estariam fora do controle era imprecisa e foi corrigida no estado do projeto.

Nenhum efeito causal foi estimado na Fase 1. Artefatos numéricos: `outputs/diagnostics/fase1_amostra.json` e `fase1_overlap.json`.
