# Resumo para redação acadêmica — início do pré-natal e baixo peso ao nascer, São Paulo (capital), 2024

Documento de consolidação para a redação de introdução, metodologia, resultados e discussão. Reúne decisões e números já produzidos; nenhuma análise nova foi executada para prepará-lo. Os números foram transcritos das saídas salvas dos notebooks indicados na seção 6, com seus denominadores. Ao citar um valor, prefira conferir na fonte indicada.

Convenções: p.p. = pontos percentuais; diferenças sempre calculadas como T=1 − T=0; SMD = diferença média padronizada; IC 95% = intervalo de confiança de 95%.

---

## 1. Problema de pesquisa

**Pergunta principal.** Entre nascidos vivos de mães residentes no município de São Paulo em 2024, o início do pré-natal no primeiro trimestre está associado a menor risco de baixo peso ao nascer, quando comparado ao início entre o 4º e o 6º mês de gestação, após ajuste por características maternas observadas?

**Hipótese investigada.** O início precoce do pré-natal permite rastreamento, suplementação e manejo antecipado de condições de risco, o que reduziria o risco de baixo peso. A hipótese empírica avaliada nesta versão é mais restrita: a de que, após ponderação por características maternas observadas, persiste uma diferença negativa de risco entre T=1 e T=0. Os dados permitem estimar uma **associação ajustada**; não identificam, por si sós, o efeito causal.

**Exposição, desfecho e população.**

| Elemento | Definição |
|---|---|
| Unidade de análise | Declaração de Nascido Vivo (um registro por nascimento); não é coorte de gestantes |
| Exposição T=1 (tratados) | Início do pré-natal nos meses 1–3 (`MESPRENAT` 1–3) |
| Comparação T=0 (controles) | Início do pré-natal nos meses 4–6 (`MESPRENAT` 4–6) |
| Desfecho Y=1 | Peso ao nascer inferior a 2.500 g |
| População | Nascimentos de 2024, mãe residente no município de São Paulo (`CODMUNRES=355030`), gestação única, peso entre 500 e 6.000 g, início do pré-natal nos meses 1–6 ("especificação B") |

Inícios nos meses 7–9 ficam fora da população; a comparação com 4–6 meses evita confrontar o 1º trimestre com inícios muito tardios, mais sujeitos ao problema de duração gestacional descrito na seção 5.

---

## 2. Origem dos dados

**SINASC.** Sistema de Informações sobre Nascidos Vivos (Ministério da Saúde/DATASUS), microdados públicos da Declaração de Nascido Vivo. Base usada nesta versão: `data/processed/sinasc_2024.parquet` (arquivo local completo de 2024, sem amostragem). Definições de campos e códigos: `docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md`. O dicionário disponível corresponde a layout até 2019; códigos não enumerados ali (por exemplo, limites de `IDADEMAE` e a sentinela 99 de `QTDFILMORT`) não foram presumidos.

**Período disponível, 2014–2024.** Há bases locais completas para os onze anos (`data/processed/sinasc/sinasc_2014.parquet` a `sinasc_2023.parquet` e `data/processed/sinasc_2024.parquet`). A série foi usada primeiro para avaliar qualidade e viabilidade amostral do recorte. A **estimação principal** (seções 3 e 4, com bootstrap e IC 95%) é exclusivamente de 2024. Depois, a mesma especificação foi estimada **separadamente em cada ano de 2014 a 2024**, sem IC anual e sem modelo combinado entre anos (seção 9).

**Justificativa da escolha de São Paulo, capital.** A orientação metodológica foi concentrar a investigação em localidades com melhor qualidade de dados. A escolha foi feita por critérios de preenchimento e retenção, **sem usar a magnitude da associação com o desfecho**.

- *Comparação geográfica de 2024* (`outputs/qualidade_geografica_2024/RECOMENDACAO_RECORTE.md`): a capital apresentou a maior proporção de registros com as variáveis essenciais simultaneamente válidas (`MESPRENAT` 1–9, `GRAVIDEZ` 1–3 e peso inteiro 500–6.000 g): 99,04%, contra 97,93% no estado de São Paulo e 97,16% no Sudeste. `MESPRENAT` válido: 99,15% (capital), 98,08% (estado), 97,32% (Sudeste). Retenção na especificação B: 94,95% dos 120.789 nascimentos da capital. Escolaridade, raça/cor, situação conjugal e perdas fetais também tiveram preenchimento maior na capital que no estado.
- *Série temporal 2014–2024* (`outputs/qualidade_geografica_2024/qualidade_sp_2014_2024.ipynb` e `qualidade_sp_por_ano.csv`): `MESPRENAT` válido na capital foi superior ao do estado e ao do restante do estado em 11 de 11 anos, variando de 98,45% (2014) a 99,15% (2024). No período, a capital somou 1.587.749 nascimentos elegíveis (1.401.494 em T=1 e 186.255 em T=0), retenção acumulada de 94,61%.
- *Ponto de atenção da série:* o número de controles na capital caiu 58,44% entre 2014 (24.348; 14,76% dos elegíveis) e 2024 (10.118; 8,82%), enquanto o total de elegíveis caiu 30,48%. A queda motivou o diagnóstico de comparabilidade, mas não constitui, por si só, violação de positividade.

O estado de São Paulo foi registrado como alternativa de maior abrangência; não foi analisado nesta versão.

**Papel complementar do SIM.** O Sistema de Informações sobre Mortalidade de 2024 (arquivo oficial `DO24OPEN_csv.zip`) foi explorado de forma **exclusivamente descritiva** para o Sudeste (`outputs/sinasc_sim_piloto_2024/`). Foram selecionados 10.432 óbitos infantis com códigos de idade compatíveis com o dicionário do SIM (5.225 de residentes no estado de São Paulo); 944 óbitos não fetais com `IDADE=999` e 162 registros com códigos 100/200 sem detalhamento não foram classificados como infantis. A fonte utilizada **não contém óbitos fetais** (`TIPOBITO=1`) para o Sudeste em 2024: ausência de registro não significa ausência de mortes fetais. Não foi calculada taxa oficial de mortalidade infantil. O SIM não entra na estimação.

**Diferença entre análise individual e cruzamento territorial.** A estimação ATO usa **registros individuais** do SINASC: exposição, covariáveis e desfecho pertencem ao mesmo nascimento. O cruzamento SINASC + SIM foi **territorial**: cada base foi agregada separadamente por município de residência (`CODMUNRES`) e os indicadores do SIM foram acrescentados ao painel do SINASC por junção de códigos (1.672 códigos de residência, dos quais 1.133 com registros no recorte do SIM; incluem códigos residuais `xx0000`, que não são municípios identificados). Não houve vinculação de indivíduos, mães ou declarações; óbitos ocorridos em 2024 não correspondem ao acompanhamento dos nascidos em 2024. Associações observadas nesse painel são ecológicas e não podem ser transpostas ao nível individual.

---

## 3. Preparação metodológica

### 3.1 Critérios de inclusão e exclusão

Seleção aplicada ao SINASC 2024 com a projeção SQL congelada do projeto (`src/amostra.py`), acrescida dos filtros de município e meses 1–6:

1. residência materna no município de São Paulo (`CODMUNRES=355030`);
2. gestação única (`GRAVIDEZ=1`); múltiplas e ignoradas excluídas;
3. peso inteiro entre 500 e 6.000 g (faixa operacional do projeto, não domínio clínico validado);
4. `MESPRENAT` entre 1 e 6.

Registros com covariáveis incompletas **não** foram excluídos. Verificações registradas: chave `CONTADOR` única e não nula, todas as datas de nascimento em 2024, contagens idênticas à referência da comparação geográfica. Não houve exclusão por suporte do escore de propensão (seção 3.4).

### 3.2 Tratamento e controle

T=1: início nos meses 1–3; T=0: início nos meses 4–6. O desfecho não foi usado na definição de covariáveis, no diagnóstico de comparabilidade nem no ajuste do escore de propensão.

### 3.3 Covariáveis utilizadas

Todas são registradas no parto e tratadas como aproximações de condições anteriores à exposição. "Ignorado" (código 9 ou nulo) é mantido como indicador de ausência, nunca interpretado como categoria substantiva.

| Covariável | Campo | Codificação | Papel no modelo principal |
|---|---|---|---|
| Idade materna | `IDADEMAE` | anos (10–59) e idade² | incluída; termo quadrático porque o desequilíbrio se concentra nas adolescentes |
| Escolaridade | `ESCMAE2010` | 0–5; Ignorado | incluída |
| Raça/cor | `RACACORMAE` | 1–5; Ignorado | incluída |
| Paridade | `PARIDADE` | nulípara / multípara | incluída |
| Perdas fetais anteriores | `QTDFILMORT` | 0 / 1 / 2 ou mais; Ignorado | incluída com ressalva (ver abaixo) |
| Situação conjugal | `ESTCIVMAE` | 1–5; Ignorado | **excluída** do modelo principal; usada em diagnóstico e em sensibilidade |

- *Perdas fetais anteriores:* o dicionário define o campo como número de perdas fetais e abortos anteriores à gestação atual, portanto anterior à exposição. Na população analisada, 99,98% dos registros têm valor não sentinela e 99,99% estão entre 0 e 9; não há código 99. Ressalvas: o campo mistura perdas espontâneas e abortos, provavelmente sub-registrados.
- *Situação conjugal:* excluída por temporalidade frágil — casamento ou união podem ocorrer depois do início do pré-natal.
- *Idade:* nenhum registro fora de 10–59 anos; não houve imputação.
- *Variáveis vedadas como controle* (posteriores à exposição, mediadoras ou desfecho): peso ao nascer, idade gestacional (`GESTACAO`, `SEMAGESTAC`), número de consultas (`CONSULTAS`, `CONSPRENAT`), tipo de parto, Apgar, índice de Kotelchuck, grupo de Robson e demais campos do parto. O bloqueio é verificado por código (`src/diagnosticos.py::validar_colunas_propensity`).
- *UF de residência:* constante no recorte; não usada.
- *Não incorporadas nesta versão:* outros campos possivelmente anteriores à exposição (`QTDGESTANT`, `QTDFILVIVO`, `IDADEPAI`, `CODOCUPMAE`).

### 3.4 Diagnóstico de comparabilidade e de sobreposição

Realizado antes da estimação, sem uso do desfecho (`outputs/comparabilidade_sp_capital_2024/comparabilidade_sp_capital_2024.ipynb`).

**Definição de SMD.** Numéricas: $(\bar x_1-\bar x_0)/\sqrt{(s_1^2+s_0^2)/2}$. Categóricas: um indicador por nível, $(p_1-p_0)/\sqrt{[p_1(1-p_1)+p_0(1-p_0)]/2}$, com $p_g$ calculado sobre todos os elegíveis do grupo $g$ (inclusive "Ignorado"); o resumo de cada variável é o maior |SMD| entre seus níveis. Os valores 0,1 e 0,2 foram usados como referências convencionais, não como testes; p-valores não foram usados como critério de equilíbrio.

**Desequilíbrio antes de qualquer ajuste** (maior |SMD| por variável):

| Variável | |SMD| | Nível mais desequilibrado | T=1 | T=0 |
|---|---:|---|---:|---:|
| Escolaridade | 0,452 | Superior completo | 31,1% | 12,9% |
| Situação conjugal | 0,421 | Casada | 36,5% | 18,1% |
| Idade materna | 0,270 | Média (anos) | 29,3 | 27,5 |
| Raça/cor | 0,199 | Branca | 45,9% | 36,1% |
| Paridade | 0,166 | Nulípara | 40,4% | 32,4% |
| Perdas fetais anteriores | 0,041 | Uma | 17,1% | 15,6% |

A faixa de 10–19 anos concentra-se em T=0 (11,9% contra 6,6%). O padrão é compatível com um gradiente socioeconômico: o início nos meses 4–6 é mais frequente entre mães mais jovens, menos escolarizadas e sem união formal.

**Sobreposição no diagnóstico** (regressão logística L2 com seis covariáveis — incluindo situação conjugal, sem idade² —, predições fora da partição de treino, 5 partições estratificadas, semente 20240925):

- AUC fora da partição: 0,655 (discriminação modesta; as covariáveis registradas explicam pouco do momento de início).
- Escore estimado: 0,514–0,986 em T=1 e 0,712–0,981 em T=0; nenhum registro abaixo de 0,05 ou acima de 0,99.
- Fora do suporte comum observado: 125 tratados e nenhum controle.
- Cauda superior com controles relativamente escassos: acima de 0,95, 28.683 tratados (27,4% de T=1) e 982 controles (9,7% de T=0); na faixa 0,975–1,000, 5.366 tratados para 106 controles.
- Como $P(T=1)\approx0{,}91$, o recorte simétrico 0,05–0,95 retiraria 27,4% dos tratados; limites simétricos convencionais foram considerados inadequados. Pesos do tipo $1/(1-e)$ seriam elevados para controles com escore alto (razão $e/(1-e)$ de até ≈ 52).

Essa combinação — suporte comum amplo, mas escore concentrado perto de 1 — motivou a escolha da ponderação por sobreposição.

### 3.5 Definição do ATO e da população de sobreposição

Estimação em `notebooks/principal/06_ato_sp_capital_2024.ipynb`.

1. **Escore de propensão** $e(X)=P(T=1\mid X)$: regressão logística com penalização L2 (C=1), numéricas padronizadas, categóricas em indicadores, sem pesos de classe (`src/diagnosticos.py::construir_pipeline_propensity`). Ajuste na amostra inteira, porque a propriedade de balanço dos pesos de sobreposição depende do ajuste no mesmo conjunto. Convergência em 81 iterações; média do escore 0,9118, igual à proporção observada de T=1 (0,9118).
2. **Pesos de sobreposição:** $w_i=1-e(X_i)$ se $T_i=1$; $w_i=e(X_i)$ se $T_i=0$. Os pesos são limitados a [0, 1].
3. **Riscos ponderados**, com pesos normalizados dentro de cada grupo: $\hat r_t=\sum_{i:T_i=t}w_iY_i\big/\sum_{i:T_i=t}w_i$. **Diferença ATO** $=\hat r_1-\hat r_0$, em p.p.
4. **População de sobreposição (população-alvo):** densidade proporcional a $f(x)\,e(x)\,[1-e(x)]$, que enfatiza perfis em que os dois momentos de início são frequentes. Não é a população total (ATE) nem a dos tratados (ATT).
5. **Suporte com as covariáveis finais:** escore de 0,6232 a 0,9760 em T=1 e de 0,6910 a 0,9760 em T=0; suporte comum observado 0,6910–0,9760. Seis tratados ficaram abaixo do mínimo dos controles, com 0,022% da soma dos pesos de T=1. Regra fixada antes de calcular riscos: nenhum recorte automático. **Nenhum registro foi excluído.**
6. **Propriedades a declarar no texto:** com escore logístico, as médias ponderadas dos termos incluídos no modelo tornam-se iguais entre grupos (com a penalização L2, aproximadamente); o balanço quase exato nessas covariáveis é esperado por construção e não demonstra ausência de confundimento. Com um único modelo de escore e sem modelo de desfecho, o estimador **não é duplamente robusto**.

### 3.6 Procedimento bootstrap e intervalo de confiança

- Bootstrap não paramétrico com **B=1.000** réplicas: em cada réplica, os 114.694 nascimentos são reamostrados com reposição; o escore de propensão é **reajustado** com a mesma especificação; os pesos, os riscos e as diferenças são recalculados.
- IC 95% por percentis (2,5 e 97,5) das réplicas. Conferências: erro-padrão bootstrap e intervalo normal correspondente.
- Sementes derivadas de `SeedSequence(20240925)`, uma por réplica (resultado independente do número de processos paralelos). Todas as 1.000 réplicas convergiram.
- A reamostragem trata nascimentos como independentes (seção 5).

**Sensibilidade com situação conjugal** (seção 7 do mesmo notebook): mesma população, codificações, idade e idade², logística L2, ajuste na amostra inteira, pesos ATO e ausência de recorte, acrescentando `SITUACAO_CONJUGAL` ao escore. Análise exploratória, **sem bootstrap e sem IC**.

---

## 4. Resultados

### 4.1 População analisada

| Grupo | Nascimentos | % do total | Casos de baixo peso |
|---|---:|---:|---:|
| T=1 (meses 1–3) | 104.576 | 91,18 | 8.797 |
| T=0 (meses 4–6) | 10.118 | 8,82 | 1.053 |
| Total | 114.694 | 100,00 | 9.850 |

Nenhum registro foi excluído por suporte ou por covariável incompleta.

### 4.2 Riscos brutos e ajustados

| | T=1 | T=0 | Diferença T=1 − T=0 |
|---|---:|---:|---:|
| Risco bruto (%) | 8,41 (IC 95% 8,25 a 8,59) | 10,41 (9,84 a 11,00) | **−2,00 p.p.** (−2,61 a −1,37) |
| Risco ponderado ATO (%) | 8,68 (8,49 a 8,87) | 10,42 (9,85 a 11,00) | **−1,74 p.p.** (−2,36 a −1,12) |

- Denominadores: riscos brutos sobre todos os nascimentos de cada grupo; riscos ATO com pesos normalizados dentro do grupo.
- Todos os intervalos são bootstrap por percentis (1.000 réplicas com reestimação do escore).
- Diferença ATO: erro-padrão bootstrap 0,32 p.p.; intervalo normal de conferência −2,37 a −1,11 p.p.; média das réplicas −1,75 p.p. O intervalo não inclui zero.
- A ponderação reduziu a magnitude da diferença bruta em cerca de 13%.

**Redação sugerida:** na população de sobreposição, comparando gestantes com o mesmo perfil de idade, escolaridade, raça/cor, paridade e perdas fetais anteriores, o início do pré-natal nos meses 1–3 esteve associado a um risco de baixo peso 1,74 p.p. menor (IC 95%: −2,36 a −1,12) que o início nos meses 4–6.

### 4.3 Balanço das covariáveis

SMD com o mesmo denominador não ponderado antes e depois da ponderação.

- **Covariáveis ajustadas:** maior |SMD| caiu de 0,452 para 0,0031. Esperado por construção (seção 3.5).
- **Situação conjugal (não ajustada no modelo principal):** permaneceu desequilibrada — "casada" com SMD 0,421 antes e 0,194 depois da ponderação. Entre as linhas não ajustadas ou descritivas, o maior |SMD| após a ponderação foi 0,194.
- **Faixa de 10–19 anos (descritiva):** 11,1% em T=1 e 11,3% em T=0 após a ponderação.

### 4.4 Pesos e tamanhos amostrais efetivos

Tamanho efetivo de Kish por grupo, $n_{ef}=(\sum w_i)^2/\sum w_i^2$:

| | T=1 (peso 1 − e) | T=0 (peso e) |
|---|---:|---:|
| n | 104.576 | 10.118 |
| n efetivo (Kish) | 84.995 | 10.096 |
| n efetivo / n | 81,3% | 99,8% |
| Peso mínimo – máximo | 0,0240 – 0,3768 | 0,6910 – 0,9760 |
| Mediana do peso | 0,0876 | 0,8936 |
| Maior participação individual na soma dos pesos | 0,0042% | 0,0108% |

Não há pesos extremos.

### 4.5 Perfil da população de sobreposição

Médias ponderadas (iguais entre grupos nas covariáveis ajustadas) comparadas à população total:

| Característica | População total | População de sobreposição |
|---|---:|---:|
| Idade materna média (anos) | 29,1 | 27,6 |
| 10–19 anos | 7,1% | 11,1% |
| Escolaridade: ensino médio | 55,0% | 65,2% |
| Superior completo | 29,5% | 13,8% |
| Raça/cor branca | 45,0% | 36,7% |
| Raça/cor parda | 42,7% | 49,7% |
| Nulípara | 39,7% | 32,9% |

A população de sobreposição é mais jovem e menos escolarizada que a população total; seu perfil se aproxima do grupo T=0. O resultado vale para essa população.

### 4.6 Sensibilidade com situação conjugal

| | Principal | Com situação conjugal |
|---|---:|---:|
| Diferença T=1 − T=0 (p.p.) | −1,74 (IC 95% −2,36 a −1,12) | **−1,63** (sem IC) |
| Risco ponderado T=1 / T=0 (%) | 8,68 / 10,42 | 8,77 / 10,40 |
| Maior |SMD| no conjunto diagnóstico comum | 0,1945 | 0,0111 |
| SMD — casada | 0,1945 | 0,0001 |
| n efetivo T=1 / T=0 | 84.995 / 10.096 | 82.323 / 10.094 |

A magnitude absoluta diminuiu 0,107 p.p. (6,1%), na mesma direção. Leitura correta:

- A comparação é apenas entre estimativas pontuais, sem teste de diferença entre modelos e **sem intervalo de confiança para a sensibilidade**; não se deve aplicar a ela o IC do modelo principal.
- Incluir situação conjugal altera os pesos e pode alterar a população-alvo; a diferença entre estimativas mistura mudança de ajuste e mudança de população e não pode ser atribuída apenas à correção de confundimento.
- A situação conjugal é medida no parto e sua condição anterior à exposição não está demonstrada.

---

## 5. Limitações

**Associação ajustada versus efeito causal identificado.** O resultado principal é uma associação ajustada por covariáveis observadas, sob ponderação ATO, na população de sobreposição. Interpretá-lo como efeito causal exigiria, entre outras hipóteses, ausência de confundimento não medido (ignorabilidade condicional), positividade, consistência da exposição e especificação adequada do escore. Balanço e sobreposição nas covariáveis observadas são condições necessárias para a comparação, mas não comprovam essas hipóteses.

- **Confundimento não observado.** Renda, cobertura por plano privado ou uso exclusivo do SUS, planejamento e desejo da gestação, tabagismo, estado nutricional, condições clínicas prévias e acesso geográfico à unidade de saúde não estão no SINASC e podem afetar tanto o momento de início do pré-natal quanto o peso ao nascer. A AUC modesta do escore (0,655 no diagnóstico) indica que grande parte da variação no momento de início não é explicada pelas covariáveis registradas. A situação conjugal, excluída por temporalidade, permanece desequilibrada no modelo principal.
- **Exposição medida retrospectivamente.** `MESPRENAT` é registrado na Declaração de Nascido Vivo, no parto, a partir de recordação ou transcrição do cartão da gestante. Erros de classificação entre meses adjacentes (3 e 4, por exemplo) são plausíveis e não foram quantificados.
- **Duração gestacional e oportunidade de início tardio.** Gestações mais curtas têm menos tempo para que o pré-natal comece tardiamente, e a prematuridade está fortemente ligada ao baixo peso. Restringir T=0 aos meses 4–6 atenua, mas não elimina, essa ligação entre duração da gestação e classificação da exposição. Ajustar pela idade gestacional não é solução, por ser variável posterior à exposição.
- **Seleção por nascidos vivos.** A população inclui apenas gestações que resultaram em nascido vivo. Se o momento de início do pré-natal afeta perdas fetais, a comparação entre nascidos vivos pode ser enviesada. A fonte do SIM utilizada não contém óbitos fetais para o Sudeste em 2024, o que impede avaliar essa seleção com os dados atuais.
- **Temporalidade e mensuração das covariáveis.** Todas as covariáveis são registradas no parto. A escolaridade pode mudar durante a gestação em adolescentes; perdas fetais anteriores misturam perdas espontâneas e abortos, com provável sub-registro; limites de idade e sentinelas não estão confirmados no dicionário disponível. A confiabilidade de campos de história reprodutiva e de assistência no SINASC é menor que a de peso e tipo de gravidez, conforme estudo de validação em maternidades públicas da capital (Bonilha et al., 2018).
- **Alcance da população de sobreposição.** O estimando ATO refere-se a uma população definida pelos próprios pesos — mais jovem e menos escolarizada que o total — e não se generaliza automaticamente para todas as gestantes da capital (ATE), para as que iniciaram cedo (ATT), para outros municípios ou para outros anos. Mudar as covariáveis muda essa população.
- **Incerteza e independência dos registros.** O bootstrap reamostra nascimentos como unidades independentes. Agrupamento por estabelecimento de saúde, por região de residência ou por mães com mais de um parto no ano tende a aumentar a incerteza; o IC apresentado pode, portanto, ser estreito demais. O intervalo cobre apenas a variabilidade amostral, não vieses de confundimento, mensuração ou seleção.
- **Modelo.** A validade da ponderação depende de o escore logístico de efeitos principais, com idade quadrática, representar adequadamente a relação entre X e T. O estimador não é duplamente robusto.

---

## 6. Material de apoio à redação

Caminhos relativos à raiz do projeto. Os gráficos estão incorporados aos notebooks (versão interativa e imagem estática na mesma saída); não há arquivos de imagem separados para esta versão.

| Seção do trabalho | Material | Onde |
|---|---|---|
| Introdução / problema | Contexto, pergunta e literatura brasileira já levantada | `docs/literature/REFERENCIAS_CENTRAIS.md`; `docs/literature/fichas/` |
| Dados — SINASC e dicionário | Definições de campos, códigos e papéis analíticos | `docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md`; `src/sinasc.py` (descrições oficiais e classificação temporal) |
| Dados — escolha do recorte (2024) | Tabela de seis recortes, qualidade e retenção | `outputs/qualidade_geografica_2024/RECOMENDACAO_RECORTE.md`; `comparacao_recortes_2024.csv`; `qualidade_variaveis_2024.csv` |
| Dados — série 2014–2024 | Gráficos e tabelas de qualidade e de contagens anuais | `outputs/qualidade_geografica_2024/qualidade_sp_2014_2024.ipynb`; `qualidade_sp_por_ano.csv` |
| Dados — SIM e cruzamento territorial | Regras, exclusões e totais descritivos | `outputs/sinasc_sim_piloto_2024/LEIA_ME.txt`; `BRIEFING_APRESENTACAO.md`; `resumo_sinasc_sim_2024.csv`; `painel_municipal_2024.csv`; `perfil_obitos_infantis_2024.csv`; `comparacao_descritiva_prenatal_2024.csv` |
| Metodologia — seleção e covariáveis | Projeção SQL congelada; pipeline do escore; lista de variáveis vedadas | `src/amostra.py`; `src/diagnosticos.py` |
| Metodologia — comparabilidade | Tabela por nível, gráfico de balanço (seção 5), escore e histograma espelhado (seção 6), faixas de pouca representação | `outputs/comparabilidade_sp_capital_2024/comparabilidade_sp_capital_2024.ipynb`; `balanco_covariaveis_2024.csv`; `resumo_propensity_2024.csv` |
| Metodologia — ATO e bootstrap | Definições (seção 2), suporte com covariáveis finais, procedimento bootstrap (seção 5) | `notebooks/principal/06_ato_sp_capital_2024.ipynb` |
| Resultados — riscos | Tabela de riscos brutos e ponderados com IC; gráfico de riscos (seção 5) | `notebooks/principal/06_ato_sp_capital_2024.ipynb` |
| Resultados — balanço e pesos | Tabela de pesos e n efetivo (seção 3); tabela e gráfico de balanço antes/depois (seção 4); perfil da população de sobreposição | `notebooks/principal/06_ato_sp_capital_2024.ipynb` |
| Resultados — sensibilidade | Comparação de estimativa, balanço, n efetivo e perfil (seção 7) | `notebooks/principal/06_ato_sp_capital_2024.ipynb` |
| Resultados — série histórica 2014–2024 | Estimativas ATO anuais, população e riscos brutos, diagnósticos de balanço, suporte e pesos, gráficos da associação e da proporção T=0 (seções 3 a 7); base da seção 9 deste resumo | `notebooks/principal/07_evolucao_ato_sp_capital_2014_2024.ipynb` |
| Discussão — temporalidade e seleção | Duração gestacional por mês de início, baixo peso por duração, nascimentos fora da especificação B (seção 5.1) e conclusão (seção 6); base da seção 10 deste resumo | `notebooks/principal/08_temporalidade_prenatal_sp_capital_2024.ipynb` |
| Discussão | Interpretação e limitações já redigidas (seção 6 do notebook ATO; seção 7 do notebook de comparabilidade) | os dois notebooks acima |

**Material de fase anterior, não misturar:** `docs/entrega/RELATORIO_FINAL_DISCIPLINA.md`, `TABELAS_RESULTADOS.md` e demais arquivos de `docs/entrega/` referem-se à série **nacional** 2014–2024 estimada com AIPW e erros-padrão agrupados por município. População, estimando e estimador são diferentes; seus números (por exemplo, −1,48 p.p. em 2024) não devem ser combinados com os desta versão. Podem ser citados como contexto ou comparação explícita.

---

## 7. Referências metodológicas

Selecionadas entre as referências já identificadas e verificadas no projeto (`docs/literature/REFERENCIAS_CENTRAIS.md` e lista de referências de `docs/entrega/RELATORIO_FINAL_DISCIPLINA.md`). A única referência acrescentada depois é Li, Morgan e Zaslavsky (2018), referência primária dos pesos de sobreposição, já incorporada a este documento e ao pacote acadêmico aprovado (ver o fim desta seção).

**Pré-natal, baixo peso e qualidade do SINASC**

- BONILHA, E. A. et al. Coverage, completeness and reliability of the data in the Information System on Live Births in public maternity wards in the municipality in São Paulo, Brazil, 2011. *Epidemiologia e Serviços de Saúde*, v. 27, e201712811, 2018. DOI: 10.5123/S1679-49742018000100011.
- CORMAN, H.; DAVE, D. M.; REICHMAN, N. *Effects of prenatal care on birth outcomes: reconciling a messy literature*. NBER Working Paper 24885, 2018. DOI: 10.3386/w24885.
- FALCÃO, I. R. et al. Factors associated with low birth weight at term: a population-based linkage study of the 100 million Brazilian cohort. *BMC Pregnancy and Childbirth*, v. 20, 536, 2020. DOI: 10.1186/s12884-020-03226-x.
- SZWARCWALD, C. L. et al. Avaliação das informações do Sistema de Informações sobre Nascidos Vivos (SINASC), Brasil. *Cadernos de Saúde Pública*, v. 35, n. 10, e00214918, 2019. DOI: 10.1590/0102-311X00214918.
- VACHUSKA, K. Can early prenatal care initiation reduce racial inequalities in birth outcomes? A causal decomposition approach. *SSM – Population Health*, v. 31, 101838, 2025. DOI: 10.1016/j.ssmph.2025.101838.
- VALE, C. C. R.; ALMEIDA, N. K. O.; ALMEIDA, R. M. V. R. Association between prenatal care adequacy indexes and low birth weight outcome. *Revista Brasileira de Ginecologia e Obstetrícia*, v. 43, p. 256–263, 2021. DOI: 10.1055/s-0041-1728779.
- VIELLAS, E. F. et al. Assistência pré-natal no Brasil. *Cadernos de Saúde Pública*, v. 30, supl. 1, p. S85–S100, 2014. DOI: 10.1590/0102-311X00126013.
- WORLD HEALTH ORGANIZATION. *Low birthweight* (indicador NLIS). Disponível em: <https://www.who.int/data/nutrition/nlis/info/low-birth-weight>.

**Escore de propensão, sobreposição e ponderação**

- AUSTIN, P. C.; STUART, E. A. Moving towards best practice when using inverse probability of treatment weighting (IPTW) using the propensity score to estimate causal treatment effects in observational studies. *Statistics in Medicine*, v. 34, p. 3661–3679, 2015. DOI: 10.1002/sim.6607. — SMD, diagnóstico de pesos e balanço.
- CRUMP, R. K.; HOTZ, V. J.; IMBENS, G. W.; MITNIK, O. A. Dealing with limited overlap in estimation of average treatment effects. *Biometrika*, v. 96, n. 1, p. 187–199, 2009. DOI: 10.1093/biomet/asn055. — sobreposição limitada e redefinição da população-alvo.
- PETERSEN, M. L. et al. Diagnosing and responding to violations in the positivity assumption. *Statistical Methods in Medical Research*, v. 21, p. 31–54, 2012. DOI: 10.1177/0962280210386207. — positividade e mudança de alvo.

**Identificação causal, seleção e ajuste**

- HERNÁN, M. A.; ROBINS, J. M. *Causal Inference: What If*. Boca Raton: Chapman & Hall/CRC. Versão de 21 nov. 2025. — hipóteses de identificação.
- SCHISTERMAN, E. F.; COLE, S. R.; PLATT, R. W. Overadjustment bias and unnecessary adjustment in epidemiologic studies. *Epidemiology*, v. 20, n. 4, p. 488–495, 2009. DOI: 10.1097/EDE.0b013e3181a819a1. — exclusão de variáveis posteriores à exposição.
- SNOWDEN, J. M. et al. The curse of the perinatal epidemiologist: inferring causation amidst selection. *Current Epidemiology Reports*, v. 5, p. 379–387, 2018. DOI: 10.1007/s40471-018-0172-x. — seleção por nascimento vivo.
- WILCOX, A. J.; WEINBERG, C. R.; BASSO, O. On the pitfalls of adjusting for gestational age at birth. *American Journal of Epidemiology*, v. 174, n. 9, p. 1062–1068, 2011. DOI: 10.1093/aje/kwr230. — por que não ajustar pela idade gestacional.
- VANDERWEELE, T. J.; DING, P. Sensitivity analysis in observational research: introducing the E-value. *Annals of Internal Medicine*, v. 167, n. 4, p. 268–274, 2017. DOI: 10.7326/M16-2607. — sensibilidade a confundimento não medido (questão aberta).

**Inferência com dependência**

- CAMERON, A. C.; MILLER, D. L. A practitioner's guide to cluster-robust inference. *Journal of Human Resources*, v. 50, p. 317–372, 2015. DOI: 10.3368/jhr.50.2.317. — subestimação da incerteza quando se ignora agrupamento.

**Contraste com a fase anterior (AIPW), se citada:** FUNK, M. J. et al. Doubly robust estimation of causal effects. *American Journal of Epidemiology*, v. 173, p. 761–767, 2011. DOI: 10.1093/aje/kwq439.

**Referência primária dos pesos de sobreposição (ATO).** Já incorporada ao pacote acadêmico aprovado (`docs/entrega/PACOTE_REDACAO_ETAPA_1_OVERLEAF/referencias.bib`, chave `li2018`; índice em `docs/entrega/artigos/LEIA_ME.md`):

- LI, F.; MORGAN, K. L.; ZASLAVSKY, A. M. Balancing covariates via propensity score weighting. *Journal of the American Statistical Association*, v. 113, n. 521, p. 390–400, 2018. DOI: 10.1080/01621459.2016.1260466. — pesos de sobreposição e população-alvo do ATO.

A versão publicada é de acesso restrito; o pacote contém o preprint dos autores (arXiv:1404.1785). Referências do bootstrap e do tamanho efetivo de Kish continuam não catalogadas; se forem citadas, é preciso localizá-las, conferir os dados bibliográficos e registrá-las antes.

---

## 8. Questões ainda abertas

Registradas para trabalhos futuros; nenhuma foi iniciada nesta versão.

1. **Confundimento não medido:** quantificar a robustez da associação (por exemplo, valor E) e buscar um controle negativo defensável.
2. **Inferência com dependência:** bootstrap ou variância agrupada por estabelecimento de nascimento ou região de residência.
3. **Incerteza da sensibilidade:** a estimativa com situação conjugal (−1,63 p.p.) não tem IC; se for usada além de forma descritiva, exige bootstrap próprio.
4. **Conjunto de ajuste:** revisar com diagrama causal a inclusão de situação conjugal e de campos possivelmente anteriores à exposição ainda não usados (`QTDGESTANT`, `QTDFILVIVO`, `IDADEPAI`, `CODOCUPMAE`).
5. **Temporalidade da exposição:** avaliar desenhos que reduzam a dependência entre duração gestacional e oportunidade de início tardio, sem condicionar em variáveis posteriores à exposição.
6. **Seleção por nascido vivo:** obter fonte do SIM com óbitos fetais e, se houver autorização e base adequada, vinculação individual SINASC–SIM.
7. **Estabilidade temporal e geográfica:** a repetição da especificação na capital em cada ano de 2014–2024 já foi realizada (seção 9), com estimativas pontuais. Permanecem abertas a quantificação da incerteza anual e dos contrastes entre anos e, como extensão opcional, a aplicação ao estado de São Paulo, explicitando que cada população de sobreposição é diferente.
8. **Referências metodológicas complementares:** quando o bootstrap ou o tamanho amostral efetivo de Kish forem citados no texto, localizar suas referências, conferir os dados bibliográficos e registrá-las no pacote acadêmico (seção 7).

---

## 9. Resultados históricos — 2014 a 2024

Fonte: `notebooks/principal/07_evolucao_ato_sp_capital_2014_2024.ipynb` (saídas salvas). Esta seção complementa as seções 2 e 4: a especificação de 2024 (população, T, Y, covariáveis, escore logístico L2 e pesos ATO, sem recorte de suporte) foi repetida **separadamente em cada um dos onze anos**, com um modelo de escore por ano e sem modelo combinado. A estimativa de 2024 reproduz a do notebook 06. Todos os onze ajustes convergiram (53 a 97 iterações). Três registros de idade fora de 10–59 anos (um em 2017, um em 2022 e um em 2023) foram mantidos e receberam a imputação prevista no pipeline, com autorização manual; nenhum registro foi excluído.

| Ano | Elegíveis | T=0: n (% dos elegíveis) | Dif. bruta (p.p.) | Risco ATO T=1 / T=0 (%) | **Dif. ATO (p.p.)** | n efetivo T=1 / T=0 |
|---|---:|---:|---:|---:|---:|---:|
| 2014 | 164.987 | 24.348 (14,76) | −1,28 | 7,61 / 8,72 | **−1,11** | 108.879 / 24.155 |
| 2015 | 165.787 | 24.345 (14,68) | −1,17 | 7,61 / 8,60 | **−0,99** | 110.184 / 24.153 |
| 2016 | 158.025 | 21.102 (13,35) | −1,32 | 7,80 / 8,88 | **−1,08** | 108.773 / 20.978 |
| 2017 | 160.429 | 18.959 (11,82) | −1,77 | 7,68 / 9,24 | **−1,57** | 112.037 / 18.879 |
| 2018 | 156.806 | 17.814 (11,36) | −2,05 | 7,75 / 9,55 | **−1,80** | 108.388 / 17.733 |
| 2019 | 150.427 | 17.581 (11,69) | −1,43 | 7,87 / 9,06 | **−1,19** | 106.088 / 17.509 |
| 2020 | 139.283 | 15.443 (11,09) | −0,75 | 7,62 / 8,20 | **−0,58** | 99.307 / 15.389 |
| 2021 | 129.761 | 12.705 (9,79) | −1,97 | 8,04 / 9,77 | **−1,73** | 92.163 / 12.666 |
| 2022 | 125.306 | 12.370 (9,87) | −2,06 | 8,46 / 10,23 | **−1,77** | 88.856 / 12.331 |
| 2023 | 122.244 | 11.470 (9,38) | −2,20 | 8,66 / 10,56 | **−1,90** | 89.016 / 11.440 |
| 2024 | 114.694 | 10.118 (8,82) | −2,00 | 8,68 / 10,42 | **−1,74** | 84.995 / 10.096 |

Diferenças calculadas como T=1 − T=0. Riscos brutos sobre todos os nascimentos do grupo; riscos ATO com pesos normalizados dentro do grupo; n efetivo de Kish.

**Direção e magnitude.** A diferença ATO é **negativa nos onze anos**. A magnitude varia de −0,58 p.p. (2020) a −1,90 p.p. (2023), amplitude de 1,33 p.p., sem tendência monotônica: 2014–2016 ficam próximos de −1 p.p.; 2017–2018 têm magnitudes maiores; 2019–2020 aproximam-se de zero; 2021–2024 voltam a valores mais negativos. As diferenças entre anos são descritivas e **não foram testadas**; não se afirma significância estatística de nenhuma mudança temporal.

**Redução do grupo T=0.** T=0 cai de 24.348 (14,76% dos elegíveis) em 2014 para 10.118 (8,82%) em 2024, queda de 58,44%; T=1 cai 25,64% (de 140.639 para 104.576), e os elegíveis passam de 164.987 para 114.694. A proporção de T=0 tem pequenas reversões em 2019 e 2022, portanto não cai de forma estritamente monotônica. Em 2024 estão os menores n efetivos dos dois grupos.

**Diagnósticos essenciais de balanço e de pesos.**

- Covariáveis ajustadas: maior |SMD| entre 0,452 e 0,548 antes da ponderação e no máximo **0,0070** depois (2020); nenhum termo acima de 0,1 em nenhum ano. Esse balanço é esperado por construção (seção 3.5) e não demonstra ausência de confundimento.
- Situação conjugal, fora do modelo: maior |SMD| após ATO entre **0,184 e 0,207**, acima de 0,1 em todos os anos e acima de 0,2 em 2014 e 2019.
- Pesos: retenção mínima do n efetivo de 77,4% em T=1 e 99,2% em T=0; maior participação individual na soma dos pesos de 0,0108%; maior massa de pesos fora do suporte comum empírico de 0,0329% (2023, T=1). Nenhum recorte foi aplicado.

**Incerteza.** **Não há intervalos de confiança anuais** nem teste de diferença entre anos. O IC 95% de −2,36 a −1,12 p.p. pertence apenas a 2024 (seção 4.2) e não deve ser estendido aos demais anos. n efetivo elevado não equivale a precisão demonstrada.

**População de sobreposição variável.** Cada ano tem sua própria população de sobreposição, e ela pode mudar ao longo do período. A média do escore passa de 0,8524 (2014) para 0,9118 (2024), e o limite inferior do suporte comum, de 0,3240 para 0,6910. Assim, a série não descreve uma associação em população fixa: variações entre anos podem refletir mudança de composição, e não apenas da associação.

**Interpretação.** Cada estimativa anual é uma **associação ajustada pelas covariáveis observadas** na população de sobreposição do ano, não necessariamente um efeito causal. A série amplia a descrição da consistência temporal da direção da associação, mas não elimina confundimento não observado, seleção por nascido vivo nem os problemas de temporalidade da exposição e das covariáveis. Estes números não devem ser combinados com os da série nacional AIPW da fase anterior (seção 6).

---

## 10. Temporalidade e seleção da exposição

Fonte: `notebooks/principal/08_temporalidade_prenatal_sp_capital_2024.ipynb` (seções 5.1 e 6), análise **descritiva** de 2024, sem novos modelos. Recorte: os mesmos critérios da especificação B (seção 3.1), **antes** do filtro de início do pré-natal; duração pelas faixas oficiais de `GESTACAO`.

| Início do pré-natal | Nascimentos | % de 117.422 | < 28 semanas: n (% da linha) |
|---|---:|---:|---:|
| Meses 1–6 (incluídos em B) | 114.694 | 97,68 | 546 (0,48) |
| Fora de B | 2.728 | 2,32 | 43 (1,58) |
| — meses 7–9 | 1.735 | 1,48 | 3 (0,17) |
| — ausente ou ignorado | 993 | 0,85 | 40 (4,03) |
| Total antes do filtro | 117.422 | 100,00 | 589 (0,50) |

Os 993 registros sem início informado incluem 889 com campo ausente e 104 com código 99 (ignorado); nenhum outro código foi observado. A duração é desconhecida em 3 excluídos e 7 incluídos, mantidos nos denominadores. Entre os incluídos, as 546 gestações com menos de 28 semanas dividem-se em 487 em T=1 (0,47%) e 59 em T=0 (0,58%).

**O que os dados mostram.** Há **diferenças de composição entre incluídos e excluídos**: a proporção de gestações com menos de 28 semanas é maior entre os excluídos (1,58% contra 0,48%), concentrada nos registros com início ausente ou ignorado (4,03%), e não nos inícios nos meses 7–9 (0,17%). Dentro de B, os meses 4–6 não têm menos gestações curtas que os meses 1–3.

**O que os dados não mostram.**

- A concentração de gestações curtas entre os excluídos **não identifica a magnitude nem a direção** do possível viés causal temporal. Ela descreve seleção observada; não demonstra que o viés seja grande.
- A proporção de 0,48% entre os incluídos refere-se a uma população já selecionada pelo início nos meses 1–6; **não demonstra que o viés seja pequeno** nem o limita a essa fração.
- A análise **não permite afirmar** que uma sensibilidade com comparador nos meses 4–5 corrigiria o problema: ela continuaria restrita aos incluídos em B e não alcançaria a seleção anterior ao filtro de início.

**Limitações para a interpretação causal.** Informação de início ausente ou ignorada não equivale a ausência de pré-natal. A concordância entre `GESTACAO` e `SEMAGESTAC` é consistência entre campos, não validação independente da idade gestacional; em 2024, 37,62% das idades gestacionais foram estimadas por exame físico e 18,68% trazem um código de método ausente do dicionário. O recorte abrange apenas nascidos vivos registrados e não recupera óbitos fetais. A duração gestacional, registrada no parto e potencialmente mediadora ou variável de seleção, **permanece fora do ajuste principal**. Em conjunto, o estudo **não demonstra a magnitude nem a direção** do possível viés temporal; a limitação descrita na seção 5 continua aberta (questão 5 da seção 8).
