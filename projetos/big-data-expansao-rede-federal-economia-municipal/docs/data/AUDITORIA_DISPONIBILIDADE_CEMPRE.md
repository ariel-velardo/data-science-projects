# Auditoria de Disponibilidade do CEMPRE (2007–2019)

## 1. Objetivo e escopo

Responder, com base prioritariamente em fontes oficiais do IBGE: **é
possível construir um painel município-ano do CEMPRE, para 2007–2019,
com os indicadores econômicos registrados como outcome no
`CONTRATO_CAUSAL.md`, de forma reproduzível e comparável no tempo?**

Esta é uma tarefa de **inspeção e documentação**. Nesta etapa:

- **não** foi construído o painel econômico final;
- **não** foi feito merge com o cadastro de tratamento nem com o pool de
  controles;
- **não** foi feita qualquer estimação, matching, common support ou
  balanceamento;
- **não** foram alterados `CONTRATO_CAUSAL.md`, `PROTOCOLO_PRE_ANALISE.md`,
  `REVISAO_INTEGRADA_DESENHO_CAUSAL.md` ou qualquer cadastro causal.

Convenção de interpretação usada neste documento, mantida em todo o
texto:

- **FATO DA FONTE** = algo explicitamente documentado pelo IBGE (citado
  com URL e, quando aplicável, número de página do PDF oficial).
- **RESULTADO DA INSPEÇÃO** = algo observado nesta sessão via consulta
  de teste (API oficial).
- **INFERÊNCIA** = interpretação nossa a partir das evidências acima.
- Onde não foi possível comprovar algo nesta inspeção, o texto registra
  explicitamente **NÃO COMPROVADO NESTA INSPEÇÃO**, em vez de presumir.

## 1.1 Estado do repositório confirmado antes de iniciar

`git status --short`, `git branch --show-current`, `git rev-parse HEAD`
e `git rev-parse origin/main` foram conferidos antes de qualquer
alteração: branch `main`, HEAD e `origin/main` em
`48ec4ef67dab27f45ce84a604cf5f4839583fe50`, árvore de trabalho limpa —
exatamente o estado de referência esperado. Nenhuma alteração
inesperada foi encontrada.

Leitura prévia local: `CONTRATO_CAUSAL.md`, `PROTOCOLO_PRE_ANALISE.md`,
`REVISAO_INTEGRADA_DESENHO_CAUSAL.md`, `ROADMAP_ACADEMICO.md` e
`docs/data/AUDITORIA_CONSTRUCAO_CENSO_ESCOLAR.md` (único documento
existente em `docs/data/` antes desta tarefa, usado apenas como
referência de convenção de nomenclatura e estilo, preservada aqui).
Nenhum desses documentos foi alterado.

---

## 2. Fontes oficiais consultadas

| Fonte | URL | Data de acesso | Uso nesta auditoria |
|---|---|---|---|
| Publicação metodológica oficial: *Estatísticas do Cadastro Central de Empresas 2018* (IBGE, Coordenação de Cadastro e Classificações) | `https://biblioteca.ibge.gov.br/visualizacao/livros/liv101720.pdf` | 2026-09-14 | Fonte primária de definições, universo, regras de sigilo, critérios de incorporação de RAIS/CAGED e convenções de símbolos (baixada localmente para leitura; ver seção 10) |
| SIDRA — página da pesquisa CEMPRE | `https://sidra.ibge.gov.br/pesquisa/cempre/tabelas` | 2026-09-14 | Navegação das tabelas disponíveis e suas séries |
| SIDRA — Tabela 1685 (série histórica, encerrada em 2021) | `https://sidra.ibge.gov.br/tabela/1685` | 2026-09-14 | Tabela candidata principal para o painel município-ano |
| API oficial de metadados SIDRA (agregados) | `https://servicodados.ibge.gov.br/api/v3/agregados/1685/metadados` | 2026-09-14 | Metadados formais da Tabela 1685 (período, variáveis, níveis territoriais) |
| API oficial de dados SIDRA (apisidra) | `https://apisidra.ibge.gov.br/values/...` | 2026-09-14 | Consultas de teste em pequena escala (município único, UF pequena) |
| API de localidades da Tabela 1685 | `https://servicodados.ibge.gov.br/api/v3/agregados/1685/localidades/N6` | 2026-09-14 | Contagem de municípios cobertos pelo agregado |
| Notas técnicas oficiais do CEMPRE 2010 | `https://ftp.ibge.gov.br/Economia_Cadastro_de_Empresas/2010/notas_tecnicas.pdf` | 2026-09-14 | Comparabilidade da apropriação da RAIS entre 2008 e 2009 e exclusão de MEI |
| Publicação/notícia metodológica oficial do CEMPRE 2019 | `https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/30991-cempre-2019-numero-de-empresas-e-organizacoes-com-pelo-menos-um-trabalhador-cresceu-3-4` | 2026-09-14 | Mudança de critério de unidades ativas e incorporação gradual do eSocial em 2019 |

Nenhuma fonte secundária (blog, Kaggle, terceiros) foi usada como
evidência substantiva. Buscas na web serviram apenas para localizar as
URLs oficiais acima.

---

## 3. Disponibilidade 2007–2019

**FATO DA FONTE** (metadados oficiais da Tabela 1685,
`servicodados.ibge.gov.br/api/v3/agregados/1685/metadados`):
periodicidade anual, `"inicio": 2006, "fim": 2021`. A Tabela 1685
("Unidades locais, empresas e outras organizações atuantes, pessoal
ocupado total, pessoal ocupado assalariado, pessoal assalariado médio,
salários e outras remunerações e salário médio mensal — série encerrada
em 2021") tem período anual disponível de 2006–2021, portanto **os 13 anos de
2007–2019 estão contidos nessa série**, sem necessidade de combinar
tabelas históricas distintas dentro da janela do projeto. As ressalvas
metodológicas internas à série são tratadas na seção 8.

| Ano | Disponível? | Fonte/tabela | Observação |
|---|---|---|---|
| 2007 | Sim | SIDRA, Tabela 1685 (N6) | Primeiro ano da série sob CNAE 2.0 e da metodologia de unidades ativas reformulada (seção 8) |
| 2008 | Sim | SIDRA, Tabela 1685 (N6) | Último ano sob apropriação agregada de registros RAIS (seção 8) |
| 2009 | Sim | SIDRA, Tabela 1685 (N6) | Primeiro ano sob apropriação individualizada de registros RAIS (seção 8) |
| 2010 | Sim | SIDRA, Tabela 1685 (N6) | — |
| 2011 | Sim | SIDRA, Tabela 1685 (N6) | — |
| 2012 | Sim | SIDRA, Tabela 1685 (N6) | Último ano da malha municipal de 5.565 municípios (ver seção 7) |
| 2013 | Sim | SIDRA, Tabela 1685 (N6) | Primeiro ano da malha municipal de 5.570 municípios |
| 2014 | Sim | SIDRA, Tabela 1685 (N6) | — |
| 2015 | Sim | SIDRA, Tabela 1685 (N6) | — |
| 2016 | Sim | SIDRA, Tabela 1685 (N6) | — |
| 2017 | Sim | SIDRA, Tabela 1685 (N6) | — |
| 2018 | Sim | SIDRA, Tabela 1685 (N6) | Ano de referência da publicação metodológica consultada nesta auditoria |
| 2019 | Sim | SIDRA, Tabela 1685 (N6) | — |

**RESULTADO DA INSPEÇÃO**: consultas de teste retornaram valores
numéricos reais (não símbolos de ausência/supressão) para 2007, 2010,
2015 e 2019 em município de teste (seção 4). Não há, nos metadados
oficiais nem nas consultas de teste, qualquer indicação de lacuna de
ano dentro de 2007–2019 para esta tabela.

**Diferença entre ano de referência e ano de divulgação**: **NÃO
COMPROVADO NESTA INSPEÇÃO** em detalhe — a publicação de 2018 foi
impressa em 2020 (colofão do PDF, seção 10), o que indica defasagem de
divulgação, mas o efeito exato dessa defasagem em revisões retroativas
de anos anteriores não foi investigado nesta tarefa.

**Séries revisadas/republicadas**: a Tabela 1685 é explicitamente
rotulada como "série encerrada em 2021" pelo SIDRA, e a navegação da
pesquisa (seção 2) mostra uma **série corrente separada, 2022–2024**,
sob nova numeração de tabelas e a mesma CNAE 2.0. Como o projeto usa
apenas 2007–2019, essa transição de série (2021→2022) está fora da
janela e não afeta a construção do painel — mas fica registrada como
ponto de atenção caso o horizonte do projeto seja estendido no futuro
(seção 13).

---

## 4. Granularidade município-ano

**FATO DA FONTE**: metadados oficiais da Tabela 1685 listam
`"nivelTerritorial":{"Administrativo":["N1","N2","N6","N3"]}` — **N6 =
Município** está entre os níveis territoriais disponíveis (junto com
N1 Brasil, N2 Grande Região, N3 Unidade da Federação).

**RESULTADO DA INSPEÇÃO**: consulta de teste para São Paulo/SP
(`3550308`) e para Serra da Saudade/MG (`3166600`, o menor município do
Brasil em população) confirmou dados retornados em nível `N6` com
código de 7 dígitos, formato idêntico ao `codigo_municipio_ibge` já
usado em todo o projeto (ex.: `CADASTRO_NACIONAL_EXPOSICAO_REDE_FEDERAL.md`).
Exemplo: Serra da Saudade, `pessoal ocupado assalariado` = 183 (2007),
177 (2010), 219 (2015), 210 (2019) — valores numéricos plausíveis, não
símbolos de ausência.

**Estabilidade do código municipal**: o código de 7 dígitos retornado
(`D1C`) corresponde ao código IBGE padrão, o mesmo já reconciliado em
todas as demais fontes do projeto (Censo Escolar, geobr, Arranjos
Populacionais) — **não foi identificada, nesta inspeção, necessidade de
geocodificação por nome**. Mudanças de malha/código municipal durante o
período (criação de novos municípios) são tratadas na seção 7, não
nesta seção.

**Agregações que impeçam análise município-ano**: a Tabela 1685 não tem
nenhuma classificação de corte adicional (`"classificacoes":[]` nos
metadados oficiais) — ou seja, os valores retornados por município-ano
já são totais agregados sobre todas as atividades econômicas (CNAE) e
portes, não exigindo soma manual de categorias para obter o total
municipal. Isso é uma vantagem de simplicidade para o painel candidato.

Nenhum merge com os 147 municípios da Fase II foi feito nesta etapa,
conforme instruído.

---

## 5. Definição dos indicadores

As definições abaixo são **FATO DA FONTE**, extraídas do Glossário da
publicação *Estatísticas do Cadastro Central de Empresas 2018*
(`liv101720.pdf`, p. 105–106). Quando reproduzido, o texto entre aspas
é tradução literal; a interpretação operacional está identificada como
tal.

### 5.1 Pessoal ocupado assalariado (outcome primário do contrato)

**FATO DA FONTE**: o pessoal ocupado assalariado é a parcela do pessoal
ocupado em 31 de dezembro do ano de referência com vínculo empregatício
formal. A Tabela 1685 o divulga separadamente do pessoal ocupado total.

- **Unidade de medida**: pessoas.
- **Referência temporal**: fotografia em 31 de dezembro do ano de
  referência (estoque, não fluxo anual).
- **Interpretação operacional do projeto**: medida de **emprego formal
  registrado dentro do universo coberto pelo CEMPRE**. Não representa o
  emprego informal da economia municipal, MEI nem todo o emprego
  existente no município (ver seção 9 sobre o universo observado).

### 5.2 Pessoal ocupado total (outcome secundário)

> "Pessoas efetivamente ocupadas em 31.12 do ano de referência do
> Cadastro Central de Empresas – CEMPRE, incluindo pessoas assalariadas
> com e sem vínculo empregatício, bem como proprietários e sócios com
> atividade na unidade."

**Diferença explícita em relação a "pessoal ocupado assalariado"**:
pessoal ocupado total = pessoal ocupado assalariado **+** proprietários
e sócios com atividade na unidade. **Não são equivalentes** — a fonte
distingue os dois conceitos precisamente por essa inclusão adicional.

### 5.3 Número de unidades locais (outcome secundário)

> "Endereço de atuação da empresa ou outra organização que ocupa,
> geralmente, uma área contínua na qual são desenvolvidas uma ou mais
> atividades econômicas, identificado pelo número de ordem (sufixo) da
> inscrição no CNPJ. São consideradas as unidades locais estabelecidas
> no País." (definição de "unidade local"; a variável conta essas
> unidades por município)

- **Unidade de medida**: unidades.
- Uma mesma empresa pode ter mais de uma unidade local no mesmo
  município ou em municípios diferentes.

### 5.4 Salário médio mensal (outcome secundário)

> "Razão entre o total de salários e outras remunerações do ano de
> referência e o número médio de pessoas assalariadas em atividade no
> ano, dividida por 13 meses."

- Existem **duas variáveis** para este indicador na Tabela 1685
  (metadados oficiais, seção 3):
  - id `1606`, "Salário médio mensal", unidade **salários mínimos**;
  - id `10143`, "Salário médio mensal em reais", unidade **reais**.
- **RESULTADO DA INSPEÇÃO**: ambas retornaram valores para Serra da
  Saudade/MG em 2006, 2007, 2010, 2019 e 2021 — confirmação em pontos
  amostrais, não prova de cobertura integral município-ano.
- **Risco de comparabilidade explícito**: a versão em "salários
  mínimos" (id 1606) é uma medida alternativa e não é diretamente
  comparável entre anos sem separar o efeito da variação real do salário
  mínimo. A versão em **reais** (id 10143) já é disponibilizada pela
  Tabela 1685, mas seus valores são nominais: comparações monetárias
  intertemporais exigem deflacionamento. Converter salários mínimos em
  reais não substitui essa deflação; nenhuma escolha de deflator é feita
  nesta auditoria.

### 5.5 Pessoal assalariado médio (variável auxiliar, não outcome do contrato)

> "A partir do ano de referência 2006, também foi implementada, no
> CEMPRE, a variável pessoal assalariado médio para o cálculo do
> salário médio mensal" — ponderada por dias trabalhados no ano
> (peso 1/365 por dia, 1/12 por mês) quando a fonte é a RAIS Empregado;
> igual ao pessoal ocupado assalariado em 31/12 quando a fonte é a
> pesquisa anual por empresas do IBGE. (`liv101720.pdf`, p. 14)

Não é outcome primário nem secundário do `CONTRATO_CAUSAL.md`, mas é o
denominador do salário médio mensal — registrado aqui por
completude.

---

## 6. Sigilo, supressão, ausência e zeros

Este é o ponto mais crítico da inspeção. Toda a informação abaixo é
**FATO DA FONTE** (`liv101720.pdf`, p. 4 e p. 21).

### 6.1 Convenções de símbolos (p. 4, "Convenções")

| Símbolo | Significado oficial |
|---|---|
| `-` | Dado numérico igual a zero **não resultante de arredondamento** (zero real) |
| `..` | Não se aplica dado numérico |
| `...` | Dado numérico não disponível |
| `x` | Dado numérico **omitido para evitar a individualização da informação** (supressão por sigilo) |
| `0`; `0,0`; `0,00` | Zero resultante de arredondamento de um dado originalmente positivo |
| `-0`; `-0,0`; `-0,00` | Zero resultante de arredondamento de um dado originalmente negativo |

### 6.2 Resposta direta às duas perguntas obrigatórias

**"Um zero observado na fonte significa necessariamente zero
econômico?"** Não necessariamente. Um `-` é zero real (não
arredondado); mas `0`/`0,0`/`0,00` pode ser um valor originalmente
positivo muito pequeno, arredondado para zero na apresentação — a fonte
distingue os dois casos explicitamente com símbolos diferentes. Um
pipeline que trate qualquer "0" como zero exato, sem checar qual
convenção gerou o símbolo, pode confundir "sem atividade" com "atividade
pequena arredondada para baixo".

**"Como distinguir zero, ausência e supressão?"** Pelos significados documentados pelo IBGE: `-` = zero real; `..` = não aplicável; `...` = dado numérico não disponível; `x` = dado omitido por sigilo. São estados distintos, que não podem ser convertidos automaticamente em zero. A causa de `...`, porém, não é necessariamente identificável apenas pelo símbolo retornado: requer informação complementar quando, por exemplo, houver mudança de malha territorial.

### 6.3 Regra de desidentificação (sigilo estatístico)

> "Considera-se que há risco de identificação do informante quando o
> número de unidades, para o nível de agregação tabulado, for igual ou
> inferior a dois. Neste caso, os dados não podem ser divulgados. [...]
> A regra básica consiste em desidentificar, no mesmo nível de
> subtotalização ou totalização, as colunas para as quais se tenham
> informações relativas a apenas uma ou duas unidades econômicas. Tal
> procedimento consistiu em aplicar um (x) na célula correspondente ao
> valor a ser omitido, nas variáveis pessoal ocupado total, pessoal
> ocupado assalariado e salários e outras remunerações, **preservando-se
> os valores referentes ao número de unidades** (empresas e outras
> organizações e unidades locais) que não sofreram desidentificação. Em
> alguns casos, pode ocorrer omissão de informação referente a um
> conjunto maior de unidades, visando a preservar possíveis
> identificações por meio de diferenças entre os níveis de
> totalização das tabelas." (`liv101720.pdf`, p. 21)

Consequências práticas para o painel candidato:

- a supressão por sigilo atinge **pessoal ocupado total, pessoal
  ocupado assalariado e salários e outras remunerações** — ou seja, os
  outcomes primário e secundários do contrato estão sujeitos a essa
  regra;
- a regra básica citada **preserva** os valores de número de unidades locais (empresas/estabelecimentos) quando desidentifica os demais campos; isso não autoriza afirmar que essa contagem estará sempre observável em qualquer situação ou estado especial da fonte;
- o limiar (≤2 unidades no nível tabulado) é baixo o suficiente para
  que municípios muito pequenos, com poucas empresas atuantes, sejam
  candidatos a supressão — mas isso depende do nível de agregação
  tabulado: como a Tabela 1685 já é totalmente agregada por município
  (sem quebra por CNAE/porte), o risco de supressão é menor do que em
  tabelas desagregadas (ex. por seção CNAE), porque o total municipal
  soma todas as unidades do município, não uma fatia setorial.

### 6.4 Verificação empírica nesta sessão

**RESULTADO DA INSPEÇÃO**: as consultas de teste para Serra da Saudade/MG e os 15 municípios de Roraima retornaram valores numéricos. A consulta dirigida para Pescaria Brava/SC (`4212650`) em 2007 retornou uma linha com `V="..."`. Assim, nesta inspeção foram observados valores numéricos e `...`; **não** foram observados empiricamente `x`, `-` ou `..` na Tabela 1685. A API retorna `V` como *string*: o valor bruto deve ser preservado e os valores especiais devem receber classificação explícita, sem conversão automática para zero. **NÃO COMPROVADO NESTA INSPEÇÃO**: a frequência de cada símbolo no universo completo, bem como a causa específica de cada `...`. A regra de supressão em si é **FATO DA FONTE** (seção 6.3); sua incidência empírica nesta tabela agregada precisa ser verificada quando o painel completo for efetivamente extraído.

---

## 7. Cobertura municipal

**RESULTADO DA INSPEÇÃO**: a API de localidades da Tabela 1685
(`servicodados.ibge.gov.br/api/v3/agregados/1685/localidades/N6`)
retorna **5.570 municípios** — o número total de municípios brasileiros
na malha vigente desde 2013 (mesmo número já usado em
`CADASTRO_NACIONAL_EXPOSICAO_REDE_FEDERAL.md` para o universo do Censo
Escolar). Essa lista é a **união** de todos os municípios que aparecem
em algum ano do agregado (2006–2021) — não é, por si só, prova de que
todos os 5.570 têm registro em **todos** os 13 anos de 2007–2019.

**RESULTADO DA INSPEÇÃO**: a consulta oficial para Pescaria Brava/SC, código `4212650`, em 2007 retornou uma **linha** com `V="..."`, não simplesmente ausência de linha. Portanto, não se pode inferir automaticamente a inexistência histórica do município pela ausência física de registro em uma resposta da API, nem atribuir uma causa única a `...` apenas pelo valor. A construção futura deverá reconciliar os dados com calendário/malha territorial histórica; a implementação exata dessa reconciliação não é decidida nesta auditoria.

**INFERÊNCIA, com apoio parcial em teste**: as transições de 5.564 municípios em 2007–2008 para 5.565 em 2009–2012 e 5.570 desde 2013 tornam a cobertura territorial município-ano uma questão a verificar, mas a disponibilidade dos anos e do nível N6 não equivale à observação numérica de cada célula.
**NÃO COMPROVADO NESTA INSPEÇÃO**: a contagem exata de municípios com
registro no CEMPRE por ano (2007 vs. 2012 vs. 2013 vs. 2019) não foi
verificada nesta sessão, porque exigiria uma consulta de maior volume
(todos os municípios, cada ano) — evitada deliberadamente, conforme a
instrução de não baixar todos os anos/municípios nesta etapa. Esse é o
teste recomendado como primeira ação da próxima etapa (seção 12).

**RESULTADO DA INSPEÇÃO** (amostra pequena, Roraima, 15 municípios,
ano 2007): todos os 15 municípios retornaram valor numérico para
`número de unidades locais` em 2007 — nenhuma lacuna observada nessa
amostra específica. Roraima não passou por criação de novos municípios
no período 2007–2019, portanto essa amostra não testa o caso de risco
(municípios criados depois de 2007).

**Risco estrutural de cobertura desigual entre variáveis**: **NÃO
COMPROVADO NESTA INSPEÇÃO** — não foi feita comparação linha a linha
entre a cobertura de `número de unidades locais` (preservado pela regra básica de desidentificação, seção 6.3) e a cobertura de `pessoal ocupado assalariado`/`salários` (sujeitas a supressão) para um conjunto amplo de municípios. Não foi feita contagem observada que permita declarar uma relação de cobertura para todas as células.

---

## 8. Comparabilidade temporal

Distinção pedida na tarefa: (1) mudança meramente editorial; (2)
mudança de classificação; (3) mudança que pode afetar comparabilidade
do outcome. Cada item abaixo é classificado.

### 8.1 CNAE — estável dentro da janela do projeto (tipo 1, favorável)

**FATO DA FONTE** (`liv101720.pdf`, p. 16–17): "Em 2007, com o objetivo
de manter a comparabilidade internacional [...] passou a vigorar a
versão 2.0 da CNAE." A CNAE 2.0 está em vigor **desde exatamente 2007**
e permanece a mesma até o fim da série histórica (2021) usada nesta
tabela. **Consequência para o projeto**: a janela 2007–2019 inteira
está sob a mesma versão de classificação de atividades — **não há
quebra de CNAE dentro do período de interesse**. Como a Tabela 1685 não
usa CNAE como classificação de corte (seção 4), essa estabilidade é
ainda menos relevante operacionalmente para o outcome agregado, mas é
relevante caso o projeto deseje, no futuro, desagregar por setor.

### 8.2 Metodologia de seleção de unidades ativas — coincide com o início da janela (tipo 1/2, neutro para o projeto)

**FATO DA FONTE** (`liv101720.pdf`, p. 13): "A metodologia para
identificação de unidades ativas foi completamente reformulada a partir
da divulgação das Estatísticas do Cadastro Central de Empresas 2007."
**Consequência**: a reformulação coincide com o primeiro ano da janela
do projeto (2007) — não há, portanto, uma metodologia antiga e uma nova
dentro de 2007–2019; toda a janela já está sob a metodologia
reformulada.

### 8.3 Apropriação de dados da RAIS — quebra real dentro da janela (tipo 3, requer atenção)

**FATO DA FONTE** (`liv101720.pdf`, p. 12–13): "Até o ano de referência
2008, o processo de apropriação dos registros da RAIS [...] era feito a
partir dos registros consolidados de unidades locais [...] sem a
possibilidade de detalhamentos [...]. A partir do ano de referência
2009, todo o processo de apropriação de registros da RAIS passou a ser
feito com base nos registros individualizados dos empregados."

**Classificação**: tipo 3, ressalva real de comparabilidade. As notas técnicas oficiais do CEMPRE 2010 registram que, até 2008, a apropriação se baseava em registros agregados; a partir de 2009, em registros individualizados. A mesma fonte informa que a mudança, com incorporação mais ampla do Lote Complementar da RAIS, provocou acréscimo nacional aproximado de **0,32%** nos vínculos em 31 de dezembro, concentrado principalmente na administração pública. Esse percentual não pode ser extrapolado para municípios: a magnitude do efeito município-ano permanece **NÃO COMPROVADA NESTA INSPEÇÃO**. A série não é automaticamente inválida, mas o pipeline deverá diagnosticar a transição 2008→2009 antes de qualquer decisão analítica.

**Relevância direta para o projeto**: a fronteira 2008→2009 desta
mudança coincide exatamente com a fronteira de coortes já discutida em
`DIAGNOSTICO_ARRANJOS_POPULACIONAIS_FASE_II.md` (21 candidatos com
`ano_coorte_candidata=2009`) — vale registrar como possível fonte
adicional (não causal) de descontinuidade em torno de 2008/2009 no
outcome, a ser considerada na análise de sensibilidade, não como
argumento para excluir ou incluir municípios.

### 8.4 Exclusão de MEI — limitação do universo e risco de composição temporal (tipo 3)

Ver seção 9.2. O MEI não integra o universo observado pelo CEMPRE da forma relevante ao projeto, mas passa a ser institucionalmente relevante a partir de 2009. Portanto, sua exclusão não deve ser descrita apenas como limitação estrutural constante: também pode alterar a composição econômica observada ao longo do período, sem que sua magnitude tenha sido inferida nesta auditoria.

### 8.5 Transição 2018→2019 e eSocial — risco de comparabilidade (tipo 3)

**FATO DA FONTE**: a divulgação oficial do CEMPRE 2019 informa alteração do critério de seleção de unidades ativas e incorporação gradual de informações do eSocial, em substituição parcial à RAIS. Isso constitui risco de comparabilidade entre 2018 e 2019. Não se exclui 2019 nesta auditoria nem se presume efeito sobre cada município; a construção futura deverá produzir diagnóstico dirigido da transição 2018→2019 antes de qualquer decisão analítica.

### 8.6 Nenhuma conclusão de invalidade

Conforme instruído, nenhuma das mudanças acima é interpretada como
invalidando a série — são registradas como pontos de atenção
metodológica, a considerar na construção do painel e em análises de
robustez, não como motivo para descartar o outcome.

---

## 9. Cobertura populacional/universo do CEMPRE (complemento à seção 5)

### 9.1 Universo formal (FATO DA FONTE, `liv101720.pdf`, p. 9 e p. 16)

> "O Cadastro Central de Empresas – CEMPRE reúne informações cadastrais
> e econômicas de empresas e outras organizações formalmente
> constituídas [...] inscritas no Cadastro Nacional da Pessoa Jurídica –
> CNPJ, da Secretaria da Receita Federal, e suas respectivas unidades
> locais."

Fontes de atualização: pesquisas anuais por empresas do IBGE (Indústria,
Construção, Comércio, Serviços), SIMCAD (Sistema de Manutenção
Cadastral), e registros administrativos do Ministério do Trabalho
(RAIS e CAGED).

### 9.2 Exclusão explícita do MEI (risco relevante para o projeto)

> "Foram consideradas empresas as pessoas jurídicas classificadas com
> natureza jurídica de entidades empresariais [...] e de pessoas físicas
> com CNPJ [...], **excetuando-se as empresas registradas como
> Microempreendedores Individuais – MEI**." (`liv101720.pdf`, p. 16)

**Consequência para o projeto**: o regime MEI foi criado pela Lei Complementar 128/2008 e passa a ser institucionalmente relevante a partir de 2009. O MEI não integra o universo observado pelo CEMPRE da forma relevante a este projeto. Logo, além de delimitar a cobertura do indicador, sua exclusão pode introduzir mudança de composição econômica ao longo do período; a magnitude não foi inferida nesta auditoria. **INFERÊNCIA**: municípios pequenos, incluindo potencialmente municípios tratados e candidatos a controle, podem ter parte relevante de sua formalização recente fora do CEMPRE — o outcome mede emprego assalariado registrado no universo CEMPRE, não a totalidade da atividade econômica, do emprego formal ou do emprego municipal.

### 9.3 Exclusão de atividade informal

Por definição (seção 9.1), atividade sem registro formal (sem CNPJ) não
é capturada pelo CEMPRE em nenhuma hipótese — isso é conhecido e
esperado, não uma limitação nova, mas registrado aqui por completude
frente à pergunta da tarefa.

---

## 10. Proveniência

| Item | Órgão | Produto | Documento/tabela | URL | Data de acesso | Período coberto | Uso no projeto |
|---|---|---|---|---|---|---|---|
| Metadados formais | IBGE | CEMPRE | Tabela 1685 (API de agregados) | `https://servicodados.ibge.gov.br/api/v3/agregados/1685/metadados` | 2026-09-14 | 2006–2021 (metadados) | Confirmar período, variáveis e nível territorial |
| Publicação metodológica | IBGE, Coordenação de Cadastro e Classificações | Estatísticas do Cadastro Central de Empresas 2018 | `liv101720.pdf` | `https://biblioteca.ibge.gov.br/visualizacao/livros/liv101720.pdf` | 2026-09-14 | Ano de referência 2018 (mas notas técnicas valem para toda a série CNAE 2.0) | Definições, sigilo, universo, critérios RAIS |
| Consulta de teste — município único | IBGE | CEMPRE | Tabela 1685, API de valores | `https://apisidra.ibge.gov.br/values/t/1685/n6/3550308/...` e `.../3166600/...` | 2026-09-14 | 2007, 2010, 2015, 2019, 2021 (amostra) | Verificar granularidade, símbolos e valores plausíveis |
| Consulta dirigida — município com mudança territorial | IBGE | CEMPRE | Tabela 1685, API de valores | `https://apisidra.ibge.gov.br/values/t/1685/n6/4212650/v/706/p/2007` | 2026-09-14 | Pescaria Brava/SC, 2007 | Confirmar que uma linha com `V="..."` pode ser retornada para célula territorialmente problemática |
| Consulta de teste — UF pequena | IBGE | CEMPRE | Tabela 1685, API de valores | `https://apisidra.ibge.gov.br/values/t/1685/n6/in%20n3%2014/v/706/p/2007` | 2026-09-14 | 2007 | Verificar cobertura municipal completa numa UF pequena |
| Lista de localidades do agregado | IBGE | CEMPRE | Tabela 1685, API de localidades | `https://servicodados.ibge.gov.br/api/v3/agregados/1685/localidades/N6` | 2026-09-14 | União 2006–2021 | Contar municípios cobertos pelo agregado |
| Comparabilidade RAIS | IBGE | CEMPRE | Notas técnicas CEMPRE 2010 | `https://ftp.ibge.gov.br/Economia_Cadastro_de_Empresas/2010/notas_tecnicas.pdf` | 2026-09-14 | 2008→2009 | Documentar registros agregados até 2008, individualizados a partir de 2009 e o efeito nacional informado |
| Comparabilidade eSocial | IBGE | CEMPRE | Divulgação CEMPRE 2019 | `https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/30991-cempre-2019-numero-de-empresas-e-organizacoes-com-pelo-menos-um-trabalhador-cresceu-3-4` | 2026-09-14 | 2018→2019 | Documentar ajuste de critério e incorporação gradual do eSocial |

O único arquivo baixado para inspeção foi a publicação metodológica em
PDF (`liv101720.pdf`, ~1,3 MB), salva no diretório de scratchpad da
sessão (fora do repositório) apenas para leitura de texto — **não foi
copiada para dentro do projeto**, para não acumular download
desnecessário, conforme instruído. As consultas de API foram feitas
diretamente contra os endpoints oficiais, sem armazenamento local além
de arquivos temporários de teste (também na scratchpad, fora do
repositório).

---

## 11. Riscos para o desenho causal

Riscos identificados nesta inspeção, sem propor solução metodológica
(essa decisão cabe às próximas etapas e a Ariel):

1. **Exclusão de MEI** (seção 9.2) — pode subestimar diferencialmente a
   atividade econômica formal em municípios pequenos/rurais ao longo do
   tempo, incluindo potencialmente tratados e candidatos a controle;
   risco de viés se a propensão a formalizar via MEI correlacionar com
   presença de campus.
2. **Mudança na apropriação de dados da RAIS em 2009** (seção 8.3) —
   coincide com a fronteira de coortes 2008/2009 já discutida no
   diagnóstico de arranjos populacionais; risco de descontinuidade
   técnica no outcome não relacionada ao tratamento, mas que pode se
   confundir com efeito em torno dessa data.
3. **Supressão por sigilo (`x`) e outros estados especiais** (seção 6.3)
   — atingem diretamente os outcomes primário e secundários; se
   ocorrerem para municípios pequenos do pool de controle ou tratados,
   exigem classificação explícita e não podem ser tratados como zero. A
   regra básica preserva a contagem de unidades locais, sem garantir sua
   observação em toda situação da fonte.
4. **Estoque em 31/12, não fluxo anual** (seção 5.1) — o outcome é uma
   fotografia de fim de ano; efeitos de campi que abrem no meio do ano
   podem não aparecer integralmente no primeiro ano de tratamento,
   reforçando a relevância da discussão de antecipação/timing já
   registrada em `CONTRATO_CAUSAL.md`.
5. **Cobertura territorial variável (5.564→5.565→5.570 municípios)** (seção
   7) — ainda não quantificada para o CEMPRE especificamente; a consulta
   de Pescaria Brava/SC em 2007 retornou uma linha com `V="..."`. Isso
   exige reconciliação com calendário/malha territorial e não permite
   equiparar estados especiais a zero econômico ou ausência física de
   linha.
6. **Salário médio em salários mínimos vs. reais** (seção 5.4) — usar a
   série em salários mínimos como se substituísse deflação introduziria
   confusão com a política de valorização do salário mínimo. A série em
   reais é nominal e exige deflacionamento para comparação monetária no
   tempo.
7. **Transição RAIS/eSocial e ajuste de critério em 2019** (seção 8.5)
   — risco de comparabilidade 2018→2019 a diagnosticar antes de qualquer
   decisão analítica.

Nenhum desses riscos é, por si só, motivo para descartar o CEMPRE como
outcome — são pontos que a construção do painel e a análise de
sensibilidade precisam documentar e, quando possível, testar.

---

## 12. Forma de acesso e possibilidade de automação

| Alternativa | Fonte | Formato | Granularidade | Facilidade de automação | Riscos | Recomendação |
|---|---|---|---|---|---|---|
| **API SIDRA (apisidra.ibge.gov.br/values)** | Oficial, gratuita | JSON | Município-ano, variável selecionável | Alta — testada nesta sessão, requisições simples por URL, sem autenticação | Limite formal de paginação não confirmado nesta auditoria; valores `V` são strings e exigem tipagem explícita | **Recomendada como via principal**, com extração segmentada |
| **API de metadados (servicodados.ibge.gov.br/api/v3/agregados)** | Oficial, gratuita | JSON | Metadados da tabela (não dados) | Alta | Não retorna os dados em si, apenas schema | Usar em conjunto com a API de valores; registrar metadados da Tabela 1685 na proveniência e validar respostas contra eles |
| **Download manual via SIDRA (interface web)** | Oficial | XLS/CSV | Configurável pelo usuário | Baixa — requer interação manual | Não reproduzível sem documentar cada clique | Não recomendada como via principal; útil apenas para checagem pontual |
| **Publicação em PDF (liv101720.pdf e equivalentes)** | Oficial | PDF | Tabelas selecionadas, não o painel completo | Baixa para dados; boa para metodologia | Extração de tabelas de PDF é frágil | Usar apenas como fonte de metodologia (como nesta auditoria), não como fonte de dados numéricos |

Na extração futura, `V` deve inicialmente ser preservado como *string*. As respostas deverão ser extraídas de forma segmentada e validadas contra os metadados da Tabela 1685, que devem integrar a proveniência. Esta auditoria não confirmou limite formal de paginação.

**Consultas de schema realizadas** (pequenas, conforme instruído; nenhum
download em massa de todos os anos/municípios foi feito):

- `t/1685/n6/3550308/v/706,707,708,5944,662,1606/p/2007,2019` (São
  Paulo/SP, 2 anos);
- `t/1685/n6/3166600/v/706,707,708,662,1606/p/2007,2010,2015,2019`
  (Serra da Saudade/MG, 4 anos);
- `t/1685/n6/3166600/v/10143/p/2006,2010,2019,2021` (mesmo município,
  variável em reais);
- `t/1685/n6/in%20n3%2014/v/706/p/2007` (todos os 15 municípios de
  Roraima, 1 ano, 1 variável).

**Parâmetros necessários para a extração completa futura** (não
executada nesta tarefa): tabela `1685`; nível territorial `n6` (todos
os municípios); variáveis `706` (unidades locais), `707` (pessoal
ocupado total), `708` (pessoal ocupado assalariado), `5944` (pessoal
assalariado médio), `662` (salários e outras remunerações), `10143`
(salário médio mensal em reais); período `2007` a `2019` (13 valores
de `p`). Sem classificações adicionais a especificar (tabela já
agregada, seção 4).

---

## 13. Recomendação para a próxima etapa

Não construir ainda o painel final. Antes disso, recomenda-se, como
primeira ação dirigida (não executada nesta tarefa):

1. Consultar a API de valores para todos os municípios em anos de
   referência selecionados, contando linhas e estados de `V` por UF e
   confrontando-os com calendário/malha territorial histórica — sem
   ainda montar o painel completo de 13 anos.
2. Fazer uma varredura dirigida de `x`, `-`, `..` e `...`, especialmente
   em municípios pequenos, para medir sua frequência e separar a
   classificação do símbolo da explicação territorial complementar.
3. Diagnosticar as transições 2008→2009 (RAIS) e 2018→2019
   (RAIS/eSocial e critério de unidades ativas) antes de qualquer
   decisão analítica.
4. Só então desenhar o pipeline de extração completa, com tratamento
   explícito de `V` como *string* e dos símbolos da seção 6.1 como
   estados tipados, não como zero nem como erro de parsing.

---

## 14. Lacunas ainda abertas

- Cobertura territorial efetiva município-ano, incluindo a frequência de
  linhas e estados especiais — **NÃO COMPROVADO NESTA INSPEÇÃO**.
- Frequência real de `x`, `-`, `..` e `...` na Tabela 1685.
- Reconciliação dos dados com calendário/malha territorial histórica,
  necessária porque `...` não identifica sua causa apenas pelo valor.
- Diagnóstico de comparabilidade 2008→2009, sem extrapolar o efeito
  nacional da mudança RAIS para municípios.
- Diagnóstico de comparabilidade 2018→2019, em razão do ajuste de
  critério e da incorporação gradual do eSocial.
- Política analítica para sigilo/supressão e demais estados especiais.
- Escolha futura do deflator para salário em reais; nenhuma escolha é
  feita nesta auditoria.

Essas pendências não impedem a extração técnica inicial, mas impedem
declarar o painel analítico final como pronto.

---

## 15. Classificação final

## APTO_COM_RESSALVAS

**Motivo objetivo**: a Tabela 1685 do SIDRA disponibiliza os anos 2007–2019 e o nível municipal (N6), com os indicadores do `CONTRATO_CAUSAL.md` definidos pela fonte oficial e acesso automatizável via API gratuita sem autenticação. Isso é suficiente para afirmar a **viabilidade técnica da construção do painel**. Não equivale a afirmar cobertura numérica integral de cada célula município-ano: cada célula depende da malha territorial histórica e dos estados especiais devolvidos pela fonte.

As ressalvas que impedem declarar o painel analítico final como pronto sem mais verificação são: cobertura territorial efetiva e reconciliação da malha histórica; frequência e política de tratamento de `x`, `-`, `..` e `...`; diagnóstico RAIS 2008→2009; risco de composição associado ao MEI; diagnóstico RAIS/eSocial e critério de unidades ativas em 2018→2019; e escolha de deflator para salários. Elas exigem tratamento explícito na documentação e no desenho do pipeline, não apenas descoberta durante a construção.

Esta classificação reflete **exclusivamente a viabilidade técnica de construir o outcome município-ano**. Não valida a identificação causal e não significa que o painel analítico esteja pronto. A identificação continua dependendo de spillover, antecipação, grupo de comparação, covariáveis e suporte comum (todos em aberto, conforme `REVISAO_INTEGRADA_DESENHO_CAUSAL.md`).
