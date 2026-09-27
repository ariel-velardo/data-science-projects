# Fase 4 — heterogeneidade causal exploratória

## Protocolo congelado antes da execução

Pré-condições: Fase 3 publicada em `48ce06b`; padronização PT-BR publicada em `1d27ab4`. O critério da Fase 3 permite exercício didático, sem comprovação causal. Não há novo erro material identificado no AIPW.

Pergunta: o contraste ajustado entre início precoce e tardio varia com os perfis maternos observáveis? O alvo causal candidato é E[Y(1)−Y(0)|X, S=1], com S representando a população selecionada. A interpretação causal continua condicionada a ausência de confundimento não observado, consistência, positividade e seleção defensável; os dados não demonstram essas hipóteses.

População fixa: 2.251.570 nascidos vivos em 2024, gestação única, peso 500–6.000 g e MESPRENAT 1–9. Chave `contador`, uma linha por nascido vivo; T=1 meses 1–3, T=0 meses 4–9; Y=1 peso <2.500 g. X: idade, escolaridade, raça/cor, situação conjugal, paridade, perdas fetais e UF maternas. Município é usado exclusivamente na separação e na incerteza, nunca como nova covariável. Nenhuma seleção por importância preditiva, nenhum recorte de suporte ou ajuste por consultas, parto, idade gestacional e variáveis neonatais.

### Separação dos dados

Embaralhar os códigos municipais únicos com semente 20240925 e distribuí-los em três partições, independentemente de T/Y. Em cada uma das três rotações: A ajusta e(X), m0(X), m1(X); B recebe essas previsões externas e fornece o pseudo-desfecho DR para ajustar a regressão de CATE; C recebe a previsão final e serve exclusivamente à avaliação dessa rodada. Nenhum município de C participa de A ou B. Cada nascimento é avaliado uma única vez. Codificadores e imputadores aprendem somente no respectivo treino.

O pseudo-desfecho é `psi=m1−m0 + T(Y−m1)/e − (1−T)(Y−m0)/(1−e)`. O modelo principal aprende E[psi|X] em B. Modelos auxiliares: propensão logística L2 e desfechos HGB, com os mesmos hiperparâmetros da Fase 2. A separação em três papéis custa eficiência, mas impede que o desfecho de C alcance o treino do CATE através dos modelos auxiliares. Não reutilizar indiscriminadamente os pseudo-desfechos OOF da Fase 2 para treinar e avaliar um segundo modelo.

### Modelos e diagnósticos fixos

- Principal: HistGradientBoostingRegressor, perda quadrática, 100 iterações, taxa 0,1, até 7 folhas, mínimo de 2.000 registros por folha, regularização L2=1, sem parada antecipada nem busca de hiperparâmetros. Categóricas nominais; categorias novas viram ausentes.
- Comparação simples: Ridge, alpha=10, idade padronizada/imputada e indicadores categóricos, ajustado nos mesmos pseudo-desfechos B. Não é um segundo método causal principal.
- Distribuição de CATE: média, mediana, p5/p25/p75/p95, amplitude p95−p5, extremos, proporções negativa/zero/positiva. Sinal individual não é verdade observada.
- Perfis pré-especificados: idade <20, 20–29, 30–34 e ≥35 anos (ausentes separados); escolaridade, raça/cor e paridade pelos códigos originais. Informar N e distribuição, sem ordenar grupos como prioridade clínica.
- Quintis crescentes do CATE: N, média prevista, distribuição de X e prevalência observada apenas descritiva. Empates repartidos por ordem aleatória reproduzível independente de Y; não representam diferenças reais entre pessoas empatadas.
- Estabilidade 1: correlação de Spearman, diferença média absoluta e concordância de sinal entre HGB e Ridge em C.
- Estabilidade 2: médias/dispersão por partição, correlação das médias de perfis entre partições (categorias com N≥1.000 em cada partição comparada) e separação entre quintis extremos usando psi de avaliação. Para essa avaliação, calcular quintis separadamente dentro de cada conjunto C; os quintis globais são somente descritivos. Esses contrastes usam dados externos ao aprendizado da regra da respectiva rodada.
- Incerteza: IC aproximado por município dos contrastes DR de validação, especialmente dentro de cada partição. Não é IC individual do CATE nem inclui integralmente incerteza dos modelos. Resultados combinados entre rotações compartilham dados de treino; seus ICs são apenas diagnósticos aproximados. Não usar desvio-padrão das previsões dividido por √N como erro-padrão do efeito aprendido.

### Critério de decisão exploratório

Regras operacionais fixadas antes de observar o CATE; não são testes universais. Falha estrutural/numérica implica `NAO_INTERPRETAVEL`. Se os contrastes DR entre quintis extremos não sustentarem separação na avaliação (IC contendo zero em todas as três partições), usar `HETEROGENEIDADE_NAO_EVIDENCIADA`. Caso contrário, correlação HGB/Ridge <0,5, correlação mediana de perfis entre partições <0,5, ou inversão do contraste pontual entre quintis em alguma partição implica `HETEROGENEIDADE_SENSIVEL_A_MODELO`; os demais casos recebem `HETEROGENEIDADE_EXPLORATORIA_ESTAVEL`. Nenhuma dessas categorias comprova benefício clínico diferencial.

### Decisão hipotética e limites

Uma eventual regra sob capacidade limitada exigiria intervenção bem definida, elegibilidade, custos, equidade, validação prospectiva e avaliação externa do valor da política. O efeito de *promover* início precoce não é automaticamente o contraste observado entre meses de início. Não calcular ROI sem custos e sem efeito dessa intervenção; não indicar pessoas para receber ou perder cuidados. O exercício atual não recomenda política clínica ou pública.

Causal Forest é opcional e foi omitido para manter um método transparente, sem dependências adicionais. Nenhuma Fase 5 ou artigo completo será iniciado.

## Fundamentação

Kennedy descreve a regressão em duas etapas sobre pseudo-desfechos duplamente robustos e o papel da separação amostral. Aqui acrescentamos um terceiro conjunto para avaliação externa e usamos municípios como unidade da separação; não afirmamos que os teoremas para amostras independentes certificam automaticamente esta aplicação agrupada. [Kennedy, artigo e seção 4](https://arxiv.org/html/2004.14497v3).

Parâmetros e tratamento de categorias/ausências do estimador conferidos na [documentação oficial do scikit-learn 1.8](https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html). Interpretação causal e seleção seguem a [auditoria do estimando da Fase 3](AUDITORIA_ESTIMANDO_FASE3.md).

## Resultados da execução

<!-- RESULTADOS_EXECUTADOS -->

### Conclusão

**HETEROGENEIDADE_SENSIVEL_A_MODELO**. Há ordenação parcial nos dados externos, mas os perfis não se mantêm suficientemente estáveis entre partições geográficas. A correlação mediana das médias de perfis é 0.157895, abaixo do critério exploratório 0,5. A concordância entre HGB e Ridge é moderada (Spearman 0.706556); isso não compensa a instabilidade geográfica.

Os contrastes DR externos Q5−Q1 são positivos nas três partições, porém bem menores que a separação prevista pelo modelo. Não confundir algum sinal de ordenação com calibração adequada da magnitude. O exercício não sustenta uma classificação estável de benefício por perfil e não autoriza uso clínico.

### População, execução e honestidade

N=2.251.570; tratados=1.942.045; controles=309.525. As datas, chave única, amostra, regras e sete covariáveis foram validadas antes de qualquer ajuste. Todas as regressões logísticas convergiram. Cada registro recebeu uma previsão externa, com município exclusivo em cada papel da rodada. Sem instalação de pacotes.

| Partição | N | T=1 | T=0 | Y=1 | Agrupamentos municipais |
| --- | --- | --- | --- | --- | --- |
| 1 | 756684 | 656380 | 100304 | 60203 | 1861 |
| 2 | 694101 | 598189 | 95912 | 54412 | 1860 |
| 3 | 800785 | 687476 | 113309 | 63144 | 1860 |

Os 5.581 códigos incluem os 11 códigos de município não especificado já auditados na Fase 3; não equivalem a 5.581 municípios identificados. A UF 53 está somente na partição 3; na avaliação dessa partição, é uma categoria nova tanto para os auxiliares quanto para o CATE. O HGB trata categoria desconhecida como ausente; a codificação indicadora do Ridge não aprende coeficiente próprio. Essa limitação de generalização para o DF é mantida explícita, sem excluir seus registros.

### Distribuição prevista

| Modelo | Média pp | Mediana pp | p5 pp | p25 pp | p75 pp | p95 pp | p95−p5 pp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HGB principal | -1.294100 | -1.289838 | -3.923820 | -1.962784 | -0.427044 | 1.208079 | 5.131899 |
| Ridge | -1.301716 | -1.319723 | -3.235409 | -2.114341 | -0.513669 | 0.711170 | 3.946578 |

HGB: 84.684% das previsões negativas e 15.316% positivas; nenhuma exatamente zero. Extremos: -33.251066 a 18.772904 pp. As caudas são muito mais amplas que o intervalo robusto e reforçam a inadequação de interpretar sinais individuais como verdade. Nenhum valor ficou fora de [−100,100] pp, mas respeitar esse limite matemático não demonstra plausibilidade causal ou calibração. Não houve recorte nem limitação artificial de previsões.

### Perfis pré-especificados

As tabelas seguem códigos/ordem de categorias, sem ordenação por suposto benefício. p5/p95 são percentis da distribuição prevista, **não ICs**. O contraste DR e seu IC são diagnósticos externos aproximados; não são ICs da média do CATE aprendido. Não houve correção para comparações múltiplas.

#### Faixa etária

| Categoria | N | CATE médio pp | p5 pp | p95 pp | Contraste DR pp | IC inferior pp | IC superior pp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 20–29 | 1111506 | -1.192529 | -2.939158 | 0.652119 | -1.141714 | -1.310514 | -0.972915 |
| 30–34 | 476754 | -1.188200 | -3.787487 | 1.369523 | -1.134816 | -1.443872 | -0.825761 |
| <20 | 257765 | -1.214452 | -3.427193 | 1.390028 | -1.096129 | -1.456992 | -0.735266 |
| Ausente | 32 | -2.502362 | -6.285188 | 4.654408 | -14.508657 | -45.089638 | 16.072324 |
| ≥35 | 405513 | -1.747545 | -6.965429 | 2.487129 | -1.592494 | -1.972584 | -1.212405 |

#### Escolaridade

| Categoria | N | CATE médio pp | p5 pp | p95 pp | Contraste DR pp | IC inferior pp | IC superior pp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 4971 | -2.202997 | -6.938617 | 1.255068 | -1.660927 | -3.890605 | 0.568750 |
| 1 | 43866 | -2.795149 | -7.642543 | 1.048199 | -2.938825 | -3.739837 | -2.137813 |
| 2 | 378758 | -1.496890 | -3.993202 | 0.714364 | -1.568785 | -1.837250 | -1.300319 |
| 3 | 1253913 | -1.305045 | -3.299005 | 0.632776 | -1.234379 | -1.410931 | -1.057828 |
| 4 | 116498 | -1.154266 | -4.090124 | 1.280705 | -0.952149 | -1.496586 | -0.407713 |
| 5 | 442808 | -0.944635 | -4.980105 | 2.882824 | -0.720763 | -1.087065 | -0.354461 |
| IGNORADO | 10756 | -2.237010 | -5.865471 | 0.626312 | -2.750794 | -4.232728 | -1.268859 |

#### Raça/cor

| Categoria | N | CATE médio pp | p5 pp | p95 pp | Contraste DR pp | IC inferior pp | IC superior pp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 752659 | -1.300865 | -4.065198 | 1.381188 | -1.216772 | -1.471560 | -0.961985 |
| 2 | 178771 | -1.482446 | -4.062007 | 0.784504 | -1.429636 | -1.836136 | -1.023136 |
| 3 | 10390 | -0.993308 | -4.648525 | 2.247128 | 0.094353 | -1.872983 | 2.061688 |
| 4 | 1254815 | -1.228970 | -3.672702 | 1.121250 | -1.178488 | -1.351271 | -1.005706 |
| 5 | 26785 | -1.410001 | -5.014175 | 1.021809 | -1.471446 | -2.610191 | -0.332702 |
| IGNORADO | 28150 | -2.821133 | -9.520087 | 1.690527 | -1.784238 | -3.323104 | -0.245372 |

#### Paridade

| Categoria | N | CATE médio pp | p5 pp | p95 pp | Contraste DR pp | IC inferior pp | IC superior pp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 831132 | -1.471179 | -3.981942 | 1.162531 | -1.445885 | -1.692443 | -1.199328 |
| 1 | 1420438 | -1.190488 | -3.873163 | 1.220620 | -1.082141 | -1.242218 | -0.922064 |


A categoria de idade ausente contém somente 32 registros: seu contraste DR é muito impreciso e não deve sustentar interpretação substantiva isolada. Ela permanece nas tabelas para reconciliar a população e fica fora das correlações de grandes perfis pelo critério N≥1.000 já definido.

Entre idades observadas, a média prevista varia aproximadamente de −1,19 pp (30–34 anos) a −1,75 pp (≥35 anos). Essa diferença descreve o modelo; a instabilidade entre partições impede convertê-la em afirmação de benefício causal diferencial. As demais dimensões também devem ser lidas com essa restrição, sem priorização por escolaridade, raça/cor ou paridade.

### Quintis globais — descrição

| Quintil | N | CATE HGB pp | Ridge pp | Idade média | Y observado % | T=1 % |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 450314 | -3.618153 | -2.443426 | 29.926908 | 9.181593 | 86.530510 |
| 2 | 450314 | -1.829008 | -1.918069 | 26.393598 | 8.192284 | 86.037743 |
| 3 | 450314 | -1.273301 | -1.302347 | 26.392355 | 7.525416 | 85.474136 |
| 4 | 450314 | -0.611021 | -0.754869 | 27.266723 | 7.076618 | 85.644017 |
| 5 | 450314 | 0.860981 | -0.089867 | 28.715745 | 7.498545 | 87.578223 |

As proporções completas de escolaridade, raça/cor, situação conjugal, paridade, perdas fetais e UF, dentro de cada quintil, estão no notebook 05 e em `fase4_resultados.json` (`quintis_composicao_x`). Cada distribuição reconcilia N e 100%. Essas características descrevem composição; nenhuma proporção observada de Y é interpretada como efeito causal.

### Estabilidade entre modelos e partições

Spearman HGB/Ridge=0.706556; diferença absoluta média=0.881772 pp; concordância de sinal=86.333%. Concordância de sinal é diagnóstico entre modelos, não acurácia individual.

| Partição | N | CATE HGB pp | CATE Ridge pp | Média psi externo pp | p5 pp | p95 pp |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 756684 | -1.563810 | -1.567181 | -1.081137 | -4.229827 | 0.735712 |
| 2 | 694101 | -0.974073 | -0.995533 | -1.256341 | -3.606283 | 1.876354 |
| 3 | 800785 | -1.316637 | -1.316262 | -1.309627 | -3.893727 | 1.028902 |

| Partição A | Partição B | Categorias comparáveis | Spearman dos perfis |
| --- | --- | --- | --- |
| 1 | 2 | 19 | 0.154386 |
| 1 | 3 | 19 | 0.157895 |
| 2 | 3 | 19 | 0.631579 |

A correlação de perfis combina as dimensões pré-especificadas e não corresponde a uma replicação em pessoas idênticas: a composição geográfica também varia. Essa diferença é parte do diagnóstico de transporte/estabilidade, não uma prova de que a instabilidade decorre exclusivamente do algoritmo.

### Avaliação externa dos quintis extremos

Quintis recalculados dentro de cada conjunto C para evitar que limites globais incorporem indiretamente desfechos de C através das demais rotações. Nenhum desfecho de C participa do ajuste da regra avaliada em C.

| Partição | Separação prevista pp | Separação DR externa pp | EP municipal pp | IC inferior pp | IC superior pp |
| --- | --- | --- | --- | --- | --- |
| 1 | 4.244585 | 0.953659 | 0.458958 | 0.053533 | 1.853785 |
| 2 | 4.727299 | 1.672817 | 0.426566 | 0.836218 | 2.509415 |
| 3 | 4.365400 | 1.488626 | 0.404256 | 0.695784 | 2.281469 |

Para cada conjunto externo, a contribuição da diferença é `I(Q5)(psi−media5)/N5 − I(Q1)(psi−media1)/N1`; somam-se essas contribuições por município. A variância é `G/(G−1) × soma(Ug²)`, com quantil t de G−1 graus de liberdade. A contribuição já inclui os denominadores N5/N1; não há divisão adicional por N². A validação reconstrói essa conta independentemente.

Os intervalos pressupõem regularidade, municípios independentes e funções fixas. Não são inferência pós-seleção completa, não incluem o viés de aprendizagem e não removem confundimento. As três rotações não devem ser combinadas como estudos independentes. Mesmo com IC externo positivo, a separação prevista é excessiva; não promover a dispersão do modelo a heterogeneidade causal estabelecida.

### ATE versus média de CATE

Média CATE HGB=-1.294100 pp; média psi externo=-1.216412 pp; C2 histórico=-1.231456 pp. A diferença CATE−psi é -0.077689 pp. Regularização, amostras de treino menores e separação geográfica explicam por que os estimadores não têm igualdade algébrica em amostra finita. Não se forçou concordância por recentralização.

### Validação e reprodução

- Pré-validação: `outputs/diagnostics/fase4_preflight.json`.
- Contrato e histórico: `fase4_ajustes.json` e `fase4_preservacao.json`.
- Reconciliação: `fase4_validacao.json`; pseudo-desfechos com tolerância absoluta 1e−12 e resumos com 1e−10; cobertura única, chaves, partições, quintis, perfis e composição reconciliados.
- Testes: fórmula DR, caso constante binário e regressão constante, heterogeneidade sintética conhecida, reprodutibilidade, guardas de covariáveis, ausência de interseção entre etapas, agregação, quintis e regras do critério exploratório.
- Artefatos: uma linha por registro no cache local ignorado `outputs/tables/fase4_predicoes_oof.npz`; resumos agregados e rastreáveis em JSON; notebook 05 executável. Limitação: sem CATE individual identificado, sem IC individual e sem recomendação clínica.

Na `.venv` do projeto:

```powershell
python -m src.executa_fase4
python -m src.resume_fase4
python -m src.valida_resultados_fase4
python -m src.documenta_fase4
python -m src.cria_notebook_fase4
python -m nbconvert --execute --to notebook --inplace --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=600 notebooks/05_heterogeneidade_causal.ipynb
python -m pytest -q tests
python -m src.valida_resultados_fase3
python -m src.valida_apresentacao
python -m src.apresentacao_pt
python -m pip check
git diff --check
```

Próximo passo metodológico possível, fora desta entrega: validação independente/prospectiva e avaliação de confundimento e seleção antes de qualquer uso operacional. Não escolher uma nova especificação apenas para melhorar o critério de decisão. Nenhuma política clínica, ROI, artigo completo ou Fase 5 foi produzido.
