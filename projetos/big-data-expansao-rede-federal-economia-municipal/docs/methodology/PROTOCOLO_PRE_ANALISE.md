# Protocolo Pré-Análise

## 1. Finalidade

Este documento registra o estado metodológico do projeto antes da
estimação de qualquer efeito pós-tratamento.

Seu objetivo é separar claramente:

1. decisões já congeladas na fase exploratória;
2. especificações candidatas vindas da exploração;
3. decisões ainda abertas que precisam de fundamentação acadêmica ex ante.

Nenhuma escolha metodológica deve ser alterada posteriormente apenas
porque produz resultados mais favoráveis.

---

# 2. Pergunta de pesquisa atual

Pergunta candidata:

> Qual foi o efeito da chegada de novos campi da Rede Federal de Educação
> Profissional, Científica e Tecnológica, associados à Expansão Fase II,
> sobre a atividade econômica dos municípios brasileiros?

A redação final ainda poderá ser refinada após a revisão de literatura
e a reconstrução institucional.

Mudanças futuras na formulação da pergunta não podem ser motivadas pela
observação dos efeitos estimados.

---

# 3. Status do projeto

FASE_EXPLORATORIA = ENCERRADA

VIABILIDADE_CAUSAL = PROMISSORA_COM_RESSALVAS

EFEITO_CAUSAL_ESTIMADO = NAO

FASE_ATUAL = DESENVOLVIMENTO_ACADEMICO

CADASTRO_CAUSAL_PRELIMINAR = APROVADO_E_VERSIONADO (147 municípios oficiais;
ver seção 4.8 e `docs/methodology/CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`).

---

# 4. Decisões já congeladas

## 4.1 Política

Expansão da Rede Federal de Educação Profissional, Científica e
Tecnológica, com foco na chamada Expansão Fase II.

## 4.2 Unidade de análise

Município-ano.

## 4.3 Definição conceitual do tratamento

Presença operacional de campus da Rede Federal associado à Expansão Fase
II no município.

O Censo Escolar fornece apenas uma **proxy anual observacional** dessa
presença operacional (primeiro ano com EPT federal ativa) — a primeira
observação no Censo não equivale automaticamente a criação
administrativa, autorização, inauguração ou início institucional das
atividades; essas datas, quando documentadas, têm precedência sobre a
proxy (ver `CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`).

O tratamento é conceitualmente absorvente: uma vez presente, o campus não
deixa de ter existido. Municípios com trajetória intermitente na flag do
Censo e sem validação institucional que confirme a natureza da lacuna
permanecem sob revisão, fora da especificação absorvente principal (ver
`CONTRATO_CAUSAL.md`, seção "Tratamento candidato").

## 4.4 Interpretação do timing

O ano de tratamento deve ser interpretado como:

"proxy anual de primeira presença operacional observada no Censo Escolar".

Ele não deve ser denominado automaticamente:

- ano de criação;
- ano de autorização;
- ano de inauguração.

## 4.5 Horizonte econômico principal explorado

2007–2019.

O encerramento em 2019 evita incorporar diretamente o choque da
pandemia de COVID-19 ao desenho principal.

## 4.6 Tratamento escalonado

Os municípios recebem tratamento em anos distintos.

Um modelo TWFE ingênuo não será utilizado como estimador causal
principal.

## 4.7 Validade externa

O suporte comum observado na exploração foi limitado.

Portanto, qualquer estimando futuro deve explicitar a diferença entre:

- população de interesse;
- população tratada observada;
- população tratada com suporte comum;
- população efetivamente utilizada na estimação.

Não será feita generalização automática para toda a Expansão Fase II.

## 4.8 Cadastro causal preliminar aprovado (sincronização 2026-09-12)

Desde a aprovação e o versionamento de
`docs/methodology/CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`
(`src/constroi_cadastro_causal_fase_ii.py`,
`src/excecoes_institucionais_fase_ii.json`), este é o cadastro reproduzível
de referência para a população institucional e a elegibilidade temporal —
substitui, para esse propósito, o estado exploratório descrito na seção 5:

- **147** municípios oficiais (população institucional; `ever_treated=true`,
  `pode_ser_controle=false` para todos os 147, sem exceção);
- **129** candidatos preliminares à amostra principal;
- **10** candidatos com ressalva;
- **5** sob revisão;
- **2** excluídos da população principal (Brasília/DF, Duque de Caxias/RJ —
  expostos institucionalmente, nunca utilizáveis como controle);
- **1** estimando especial (Porto Alegre/RS).

Três camadas continuam distintas e não devem ser confundidas: população
institucional (147), elegibilidade temporal (condição mecânica necessária,
não suficiente) e população causal identificável (ainda não construída —
depende de common support, matching e do grupo de comparação; ver seção
6.5 e `CONTRATO_CAUSAL.md`, seção "Cadastro causal aprovado"). Os 129
candidatos preliminares **não são a amostra causal final**.

O outcome primário (pessoal ocupado assalariado do CEMPRE) e os outcomes
secundários já estão formalizados no `CONTRATO_CAUSAL.md` — ver nota nas
seções 6.1 e 6.2 abaixo, mantidas para registro do raciocínio exploratório
que levou à escolha.

---

# 5. Resultados exploratórios que funcionam como diagnóstico

**Nota (2026-09-12): esta seção é histórica — anterior ao cadastro causal
reproduzível da seção 4.8. Os números abaixo (144, 119, 53, 47) não são
substituídos automaticamente pelos números atuais (147, 129, ...): são
populações obtidas por métodos diferentes, e a equivalência não pode ser
presumida (ver `docs/methodology/AUDITORIA_TIMING_TRATAMENTO.md`, seção
"Reconciliações e limitações", para a reconciliação parcial já feita).**

Estes resultados orientam o desenvolvimento, mas não constituem ainda
a especificação causal final.

## 5.1 Municípios Fase II

Municípios únicos identificados: 144.

## 5.2 Tratados principais inicialmente considerados

2010 = 37

2011 = 65

2012 = 14

2013 = 3

Total = 119.

## 5.3 Common support

119 tratados inicialmente considerados.

53 tratados permaneceram no suporte comum exploratório.

## 5.4 Matching exploratório

Melhor configuração exploratória encontrada:

- nearest-neighbor;
- K = 1;
- com reposição;
- exact matching por UF;
- somente variáveis pré-tratamento.

Resultados aproximados:

- 53 tratados matched;
- 51 controles únicos;
- ESS dos controles ≈ 49,3;
- mediana |SMD| ≈ 0,0225;
- máximo |SMD| ≈ 0,2248.

GATE_MATCHING = ALERTA.

## 5.5 Amostra core exploratória

Coorte 2010 = 17 tratados.

Coorte 2011 = 30 tratados.

Total = 47 pares.

As coortes 2012 e 2013 foram consideradas pequenas e permanecem como
candidatas a análises de sensibilidade.

## 5.6 Pré-tendências

Janela exploratória balanceada:

k = -3, -2, -1.

Os resultados foram considerados promissores, mas não comprovam
tendências paralelas.

## 5.7 Placebos

Foram encontrados sinais pré-tratamento em algumas combinações de
coorte e outcome.

Esses sinais permanecem como alerta para:

- antecipação;
- erro de timing;
- seleção dinâmica;
- choques locais prévios;
- instabilidade amostral.

GATE_ESTATISTICO_FINAL = PROMISSOR_COM_ALERTAS.

---

# 6. Itens ainda NÃO congelados

Os seguintes elementos precisam ser definidos academicamente antes da
estimação final:

## 6.1 Outcome primário

**Atualização (2026-09-12): já formalizado como outcome primário no
`CONTRATO_CAUSAL.md` — pessoal ocupado assalariado do CEMPRE, ligado ao
canal mais direto do tratamento (contratação de servidores/terceirizados e
consumo local associado ao campus). Ver seção 4.8. A escolha foi feita
antes da observação de qualquer efeito estimado.** Candidatos considerados
nesta fase exploratória, antes da formalização (registro histórico do
raciocínio que levou à escolha):

- pessoal ocupado assalariado;
- pessoal ocupado total;
- número de unidades locais;
- salário médio mensal.

A escolha do outcome primário deve ser baseada em:

- pergunta substantiva;
- mecanismo econômico;
- literatura;
- qualidade da mensuração;
- interpretação causal.

Não será escolhido o outcome que apresentar o maior efeito estimado.

## 6.2 Outcomes secundários

**Atualização (2026-09-12): já definidos no `CONTRATO_CAUSAL.md`** — pessoal
ocupado total, número de unidades locais e salário médio mensal, pelo
mesmo mecanismo institucional do outcome primário (canais adjacentes:
criação de estabelecimentos, efeito salarial, emprego não assalariado).

## 6.3 Estimando

**Atualização (2026-09-12): já formalizado no `CONTRATO_CAUSAL.md`** como
$ATT(g,t)$ no enquadramento de Callaway–Sant'Anna, aplicado ao
subconjunto causal identificável de municípios tratados — condicionado à
definição válida do timing, à elegibilidade temporal, ao grupo de
comparação e à existência de suporte comum —, com agregação possível por
coorte e por tempo relativo ao evento (event-time).

O que permanece aberto são decisões **operacionais** sobre como esse
estimando será efetivamente calculado, não a ausência de formalização:

- composição final da população causal identificável (depende de common
  support e matching, ver seção 6.4);
- never-treated vs. not-yet-treated como grupo de comparação (seção 6.5);
- horizonte pós-tratamento e forma de agregação (por coorte, por
  event-time, ou geral);
- estratégia de inferência e clusterização (seção 6.9);
- regras de antecipação e spillovers (seções 6.7-6.8).

Essas decisões abertas não devem ser lidas como ausência de formalização
do estimando — apenas como parâmetros operacionais ainda a fixar dentro
do enquadramento já definido.

## 6.4 População causal principal

**Ver seção 4.8 para o cadastro causal preliminar já aprovado (147
municípios, 129 candidatos preliminares).** O que segue permanece
histórico/exploratório e não deve ser lido como a especificação atual:

Ainda deve ser formalizada a relação entre:

- 144 municípios Fase II;
- 119 tratados 2010–2013;
- 53 tratados com suporte comum;
- 47 tratados das coortes 2010–2011.

A amostra de 47 pares não será automaticamente transformada em
população causal principal apenas porque apresentou diagnóstico
exploratório favorável.

## 6.5 Grupo de comparação

O pool conservador de aproximadamente 4.958 municípios permanece como
referência exploratória — **ele não pode ser adotado automaticamente como
pool final**: é preciso primeiro excluir municípios tratados por outras
fases da Rede Federal, com presença federal anterior, potencialmente
contaminados por spillover, ou sem suporte comum. Ver `CONTRATO_CAUSAL.md`,
seção "Grupo de comparação candidato", para a lista completa de exclusões
a decidir e as alternativas ainda abertas (never-treated vs. not-yet-treated).

Ainda deve ser definido formalmente:

- never-treated;
- not-yet-treated;
- combinação admissível;
- regras adicionais de exclusão.

## 6.6 Estimador principal

Candidatos:

- Callaway–Sant'Anna;
- Sun–Abraham;
- outro estimador moderno para staggered adoption.

A decisão precisa ser fundamentada antes da análise final.

## 6.7 Antecipação

Mecanismos catalogados no DAG de `CONTRATO_CAUSAL.md` (anúncio, obras,
contratação, preparação do campus podem antecipar efeitos). Ainda será
definido se:

- antecipação = 0;
- antecipação = 1 ano;
- outra janela possui justificativa institucional.

## 6.8 Spillovers

Ver `CONTRATO_CAUSAL.md`, seção "Spillovers", para a lista de mecanismos
(deslocamento de estudantes/trabalhadores, compras e contratação locais,
mercado de trabalho compartilhado com vizinhos, comércio/serviços
regionais). Precisamos avaliar:

- proximidade geográfica;
- deslocamento de estudantes e trabalhadores;
- efeitos sobre municípios vizinhos;
- possível exclusão de controles próximos.

Distâncias como 30 km ou 50 km serão consideradas apenas se houver
fundamentação substantiva.

## 6.9 Inferência

Ainda devem ser definidos:

- nível de clusterização;
- procedimento de inferência;
- eventuais ajustes para número reduzido de clusters/coortes.

---

# 7. Casos de timing que exigem tratamento explícito

## Sobral/CE

- pertence à Fase II;
- há evidência externa de entrada/criação em 2008;
- inauguração oficial em 2009;
- não deve ser usado como controle;
- pode permanecer fora do timing principal uniforme pelo Censo;
- pode entrar em sensibilidade com timing externo.

## Campinas/SP

- pertence à Fase II;
- início de atividades do IFSP em 2013;
- não pode ser controle;
- pode entrar em análise de sensibilidade com timing externo 2013.

Nenhum desses casos deve ser corrigido silenciosamente na
especificação principal.

**Atualização (2026-09-12):** ambos os casos já têm status explícito no
cadastro causal aprovado — Sobral/CE como `candidato_com_ressalva`
(coorte candidata 2010, ver `src/excecoes_institucionais_fase_ii.json`) e
Campinas/SP como `sob_revisao` (sem ano civil completo confirmado). Ver
`CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`, seção "Casos especiais".

---

# 8. Mecanismos econômicos

Um campus da Rede Federal pode afetar o município por diferentes canais:

1. contratação direta de professores, técnicos e outros trabalhadores;
2. consumo local de servidores e estudantes;
3. demanda por serviços;
4. formação de capital humano;
5. atração de empresas;
6. criação de novos estabelecimentos;
7. mudanças salariais;
8. efeitos sobre composição setorial;
9. deslocamentos de atividade entre municípios.

O aumento de emprego público diretamente associado ao campus é um
efeito econômico real da política.

Entretanto, análises futuras poderão separar:

- efeito direto da presença do campus;
- efeitos indiretos sobre atividade econômica privada.

---

# 9. Fontes principais candidatas

## Política e tratamento

- MEC;
- relação histórica de campi dos Institutos Federais;
- Censo Escolar.

## Atividade econômica

IBGE / Cadastro Central de Empresas — CEMPRE.

Período exploratório principal:

2007–2019.

## Possíveis complementos

- população municipal IBGE;
- CEMPRE por setor;
- RAIS, apenas se necessária;
- documentos institucionais dos Institutos Federais.

---

# 10. Ordem obrigatória antes da estimação

**Atualização (2026-09-12):** o cadastro causal preliminar (147
municípios, 129 candidatos preliminares) e a auditoria institucional da
Fase II já estão concluídos como trabalho fundacional — ver
`CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`,
`docs/institutional/EXPANSAO_FASE_II.md` e
`docs/institutional/AUDITORIA_LISTA_FASE_II.md`. A pergunta de pesquisa, o
outcome primário, o estimando e o DAG já foram formalizados em
`CONTRATO_CAUSAL.md`. A sequência técnica vigente a partir daqui é a de
`ROADMAP_ACADEMICO.md`:

1. construir cadastro nacional de exposição à Rede Federal;
2. construir pool reproduzível de municípios de comparação;
3. construir painel municipal do CEMPRE 2007–2019;
4. incorporar covariáveis pré-tratamento (justificadas pelo DAG);
5. formalizar regras de antecipação e spillovers;
6. avaliar suporte comum e balanceamento;
7. executar event study e estimação de ATT.

Revisão de literatura adicional e reconstrução institucional continuam
como atividades paralelas de apoio — especialmente para fundamentar
covariáveis, antecipação e spillovers —, não como a próxima etapa técnica
exclusiva.

Não executar a etapa 7 antes da conclusão documental das etapas
anteriores.

---

# 11. Regra contra specification searching

Após o início da análise pós-tratamento, mudanças metodológicas só
serão aceitas se:

1. forem motivadas por erro identificado;
2. tiverem justificativa substantiva independente do resultado;
3. forem documentadas;
4. a especificação originalmente definida também permanecer reportada,
   sempre que tecnicamente possível.

---

# 12. Próxima atividade

A próxima atividade técnica é **construir o cadastro nacional de
exposição à Rede Federal** (para impedir que municípios tratados por
outras fases/campi entrem no pool de controles) e, em seguida, **derivar
o pool reproduzível de municípios de comparação** — ver
`ROADMAP_ACADEMICO.md`, seção "Próxima etapa técnica".

Revisão de literatura adicional e reconstrução institucional permanecem
como atividades paralelas de apoio (mecanismo causal, covariáveis,
antecipação, spillovers), não como etapa principal anterior ao cadastro
nacional de exposição.