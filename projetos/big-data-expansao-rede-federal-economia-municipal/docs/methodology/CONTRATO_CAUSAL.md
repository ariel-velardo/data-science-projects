# Contrato Causal

## Data da decisão

2026-09-08.

## Uso

Trabalho final da disciplina de Big Data & Analytics, com finalidade de
exercício metodológico rigoroso.

---

## Pergunta

Efeito da chegada de novos campi da Rede Federal sobre a atividade
econômica municipal.

## Unidade

Município-ano.

## Janela

2007–2019.

---

## Outcome primário

Pessoal ocupado assalariado do CEMPRE.

## Outcomes secundários

- pessoal ocupado total;
- número de unidades locais;
- salário médio mensal.

---

## Tratamento operacional atual

Primeira presença federal EPT observada no Censo Escolar.

Ressalva: esse timing é uma proxy anual e ainda precisa ser confrontado
com criação, inauguração e início efetivo das atividades na
reconstrução institucional.

---

## População causal principal

47 pares em common support, coortes 2010–2011.

Coortes 2012–2013: somente sensibilidade.

Universo original de 119 tratados: caracterização e validade externa,
não estimativa causal principal.

## Controles principais

Municípios never-treated pareados.

---

## Estimador principal candidato

Callaway–Sant'Anna.

## Estimando

ATT dinâmico por event-time para tratados das coortes 2010–2011 com
suporte comum.

TWFE convencional: não usar como estimador causal principal.

---

## Critério de interpretação

- suporte e balanceamento adequados;
- leads avaliados por magnitude e incerteza, não apenas p-valor;
- ausência de antecipação relevante;
- resultado não explicado exclusivamente por uma coorte;
- heterogeneidade entre coortes não invalida automaticamente;
- significância do ATT não define sucesso;
- pré-tendências economicamente relevantes, ausência de suporte ou
  contaminação dos controles invalidam a interpretação causal.

---

## Itens ainda abertos

- antecipação;
- spillovers;
- inferência e clusterização;
- validação institucional do timing;
- mecanismo causal e DAG.

## Próxima etapa

Revisão de literatura e reconstrução institucional antes da estimação.

---

## Status do documento

- Decisões analíticas ex ante registradas.
- Desenho causal ainda não validado.
- Nenhum efeito causal estimado.
- Contrato sujeito somente a alterações motivadas por evidência
  institucional ou erro documentado, nunca pelo resultado do ATT.
