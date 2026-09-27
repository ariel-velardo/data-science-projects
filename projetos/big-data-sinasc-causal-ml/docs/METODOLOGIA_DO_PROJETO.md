# Metodologia do projeto

Síntese das Fases 0–4 para a disciplina Big Data & Analytics. Os protocolos originais permanecem preservados, inclusive decisões posteriormente revistas. A Fase 5 organiza resultados existentes, sem alterar amostra ou estimadores.

## 1. Problema

Entre gestantes comparáveis em características observáveis, iniciar o pré-natal até o terceiro mês de gestação está associado a uma redução no risco de baixo peso ao nascer?

A decisão acadêmica é avaliar o que dados observacionais sustentam sobre esse contraste. O estudo não implementa uma intervenção de promoção do cuidado, política clínica ou cálculo de ROI.

## 2. Fonte

SINASC 2024, disponibilizado pelo Ministério da Saúde. O ZIP original é preservado, com hash e proveniência. O layout oficial disponível descreve a estrutura até 2019; o manual da DNV de 2022 complementa a semântica de preenchimento. [Fontes oficiais](sources/FONTES_OFICIAIS.md) e [dicionário analítico](dados/DICIONARIO_ANALITICO_SINASC_2024.md).

## 3. Unidade e chave

Uma linha por nascido vivo, não por gestante acompanhada longitudinalmente. `contador` é único nesta extração, sem garantia de estabilidade entre extrações. Não há identificação validada da mãe para relacionar gestações ou irmãos.

## 4. Tratamento e tempo

T=1: primeira consulta no primeiro, segundo ou terceiro mês. T=0: início entre o quarto e o nono mês. `MESPRENAT=99`, nulos e valores fora desse domínio não definem tratamento conhecido. Zero consultas não é automaticamente convertido em controle.

O momento de decisão conceitual é o início da gestação. Não existe tempo zero individual observado: o mês é informado retrospectivamente. Uma política que promova início precoce não é equivalente à exposição observada. [Contrato](methodology/CONTRATO_CAUSAL_FASE1.md).

## 5. Desfecho e janela

Y=1 corresponde a peso ao nascer inferior a 2.500 g, medido no nascimento ocorrido em 2024; Y=0 nos demais pesos elegíveis. O intervalo principal de qualidade é 500–6.000 g, uma decisão do projeto, não regra universal da OMS. A sensibilidade P0 aceita peso numérico positivo.

## 6. População

Nascidos vivos com T conhecido, peso principal válido e gestação única. O [fluxo de N](dados/FLUXO_DOS_DADOS.md) mostra as exclusões sequenciais. Não houve seleção somente de casos completos em X nem trimming oculto. Seleção por sobrevivência, informação e peso pode condicionar variáveis associadas à exposição e ao desfecho.

## 7. Covariáveis

Sete dimensões congeladas: idade, escolaridade, raça/cor, situação conjugal, paridade, perdas fetais e UF maternas. Raça/cor é marcador social/contextual, sem interpretação biológica essencialista. A escolha foi conceitual, sem seleção automática por importância preditiva.

Consultas acumuladas, idade gestacional, parto, Apgar, local/estabelecimento do parto e índices de adequação não entram no ajuste. Podem ser posteriores ao tratamento, mediadores ou marcadores de seleção. Sexo é biologicamente anterior, mas não foi considerado confundidor do início do pré-natal. Gravidez única define elegibilidade. [DAG](methodology/DAG_INICIAL.md) e [auditoria de X](methodology/AUDITORIA_COVARIAVEIS_FASE1.md).

## 8. Preparação

Leitura e transformações em DuckDB/SQL sobre Parquet; códigos originais preservados como texto. Chaves, datas, domínios e contagens são validados. Categorias ausentes recebem tratamento explícito; idade usa imputação/indicador no pipeline logístico e tratamento nativo no HGB. Codificadores e imputadores são aprendidos somente no treino correspondente.

O volume nacional motiva processamento seletivo, agregação e contratos verificáveis. Não se alega computação distribuída. Pandas é usado para resultados materializados e integração com modelos.

## 9. Descrição

Frequências, ausência de informação, prevalência de baixo peso, perfis T=1/T=0 e SMD descrevem os dados. A diferença bruta entre grupos é **NÃO CAUSAL**. Valores descritivos dependem do denominador: prevalência bruta, analítica e do teste não são intercambiáveis.

## 10. Predição, causalidade e heterogeneidade

| Pergunta | Alvo | O que não demonstra |
|---|---|---|
| Predição: quem apresenta maior risco? | Probabilidade de Y a partir de X | Que intervir em T mudaria Y |
| Causal: qual seria a diferença média estimada sob tratamentos diferentes, condicionada às hipóteses adotadas? | Contraste médio de desfechos potenciais; operacionalmente, associação padronizada na população selecionada | Identificação causal apenas por ajustar modelos |
| Heterogeneidade: esse efeito estimado parece variar de forma sistemática entre perfis? | CATE candidato | Benefício individual conhecido |

ROC-AUC baixa/modesta não invalida AIPW por si só: a qualidade relevante dos modelos auxiliares e suas taxas de erro não se resumem à discriminação de Y. Bom modelo preditivo não prova efeito causal. CATE variável pode refletir ruído, regularização, confundimento ou diferenças de composição.

O benchmark compara logística L2 e HistGradientBoosting com as mesmas sete X, sem T, divisão 80/20 estratificada por Y e semente fixa. Métricas: ROC-AUC, average precision (AP), Brier e calibração. O limiar 0,5 não foi otimizado no teste e não produz positivos; não se propõe classificação clínica. [Plano preditivo e causal](methodology/PLANO_ESTIMACAO_FASE2.md). Contexto de ML: Ranjbar et al.; estudos de pré-natal: Vale et al. e Falcão et al. na [seleção bibliográfica](literature/REFERENCIAS_CENTRAIS.md).

## 11. Propensity e overlap

O escore de propensão estima a probabilidade de T=1 dado X; não é uplift. Na Fase 1, cinco partições geram previsões fora do treino para diagnóstico. SMD, distribuições de e e pesos informam suporte e desequilíbrio. AUC não certifica positividade, intercambialidade ou controle de confundimento. Trimming muda a população-alvo. [Gate da Fase 1](methodology/GATE_FASE1.md); fundamentos: Petersen et al. e Austin–Stuart.

## 12. AIPW

O estimador combina regressões de Y sob os dois tratamentos e correções ponderadas pelo tratamento recebido:

`psi = m1(X) − m0(X) + T[Y−m1(X)]/e(X) − (1−T)[Y−m0(X)]/[1−e(X)]`.

A média de psi é o contraste estimado; a função de influência é psi centrado. C1 usa propensão e desfechos logísticos. C2 compartilha a propensão e usa HGB nos desfechos. O alvo observável é a diferença de médias condicionais padronizada pela distribuição de X nos registros selecionados. Sua leitura causal requer consistência, intercambialidade, positividade, ausência de interferência relevante, mensuração e seleção defensáveis.

Dupla robustez de consistência não basta para garantir cobertura de ICs com quaisquer auxiliares. Os ICs históricos iid usam a variância da função de influência e não incluem confundimento ou seleção. Não houve escolha do resultado mais favorável. Fundamentos: Funk et al. e Chernozhukov et al.

## 13. Ajuste cruzado

A Fase 2 usa três partições estratificadas por T/Y; cada observação recebe previsões fora do seu treino. A quantidade de partições difere do diagnóstico da Fase 1, explicando pequenas diferenças no recorte de suporte. A Fase 3 separa também por município. A Fase 4 acrescenta separação entre treino dos auxiliares, treino do CATE e avaliação.

## 14. Robustez

A Fase 3 reconciliou os pseudo-desfechos, estimativas e erros-padrão, examinou influência, simulou cenários com efeito conhecido e avaliou sensibilidades de suporte, discordância de consultas, pesos, múltiplas e propensão HGB (C3).

O gate da Fase 2, `RESULTADO_NAO_INTERPRETAVEL`, foi acionado pela concentração de IF² no extremo. A revisão `GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR` questiona essa heurística como veto universal. O histórico permanece intacto; rever um critério estatístico não comprova causalidade. [Auditoria completa](methodology/ROBUSTEZ_FASE3.md).

## 15. Dependência geográfica

Os erros-padrão municipais agregam a função de influência por `CODMUNRES`, com correção finita e quantil t. O bootstrap usa municípios, com auxiliares fixos; é sensibilidade condicional. Os códigos de residência incluem agrupamentos residuais sem município especificado, explicitados na auditoria. Dependência entre municípios e vínculos familiares não observados permanecem limitações. Fundamentos: Cameron–Miller e Chiang et al.; a implementação não é multiway DML.

## 16. DR-Learner

Três conjuntos municipais, independentes de T/Y na divisão: A ajusta os auxiliares, B aprende a regressão do pseudo-desfecho e C avalia. Há rotação dos papéis e avaliação única por registro. HGB é o principal; Ridge é comparação simples.

Gate: `HETEROGENEIDADE_SENSIVEL_A_MODELO`. Ordenação parcial não compensa magnitude exagerada e instabilidade dos perfis. Percentis de previsões não são ICs; ICs de contrastes DR externos tratam funções aprendidas como fixas. Não houve recentralização para aproximar CATE médio do ATE. [Protocolo e resultados](methodology/HETEROGENEIDADE_FASE4.md); fundamento: Kennedy.

## 17. Limitações

Faltam confundidores importantes, como renda, tabagismo, nutrição, morbidades e acesso/qualidade. X no parto aproxima condições anteriores, sem verificação perfeita. Seleção de nascidos vivos e critérios de qualidade limitam transporte para todas as concepções. O grande N reduz parte da incerteza amostral, mas não o viés de identificação. Snowden et al. fundamentam a discussão de seleção. [Auditoria do estimando](methodology/AUDITORIA_ESTIMANDO_FASE3.md).

## 18. Conclusões permitidas

É defensável apresentar contraste ajustado exploratório, comparar estimadores e discutir estabilidade e limites. Não é defensável afirmar causalidade provada, benefício individual, efeito em todas as gestantes ou indicação clínica. Não há avaliação identificada de uma política nem custos para ROI.

`CAUSALIDADE_PROVADA = NAO`.

[Resultados principais](RESULTADOS_PRINCIPAIS.md) · [Reprodução](REPRODUCAO.md) · [Síntese executiva](SINTESE_EXECUTIVA.md).
