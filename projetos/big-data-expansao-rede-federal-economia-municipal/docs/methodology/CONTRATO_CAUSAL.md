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

## Tratamento operacional candidato

> Primeira presença federal com EPT ativa observada no Censo Escolar.

Ressalva: essa definição

- é uma proxy anual;
- ainda depende de validação institucional (confronto com criação,
  inauguração e início efetivo das atividades);
- não transforma automaticamente trajetórias intermitentes em
  tratamento permanente.

---

## População causal principal

A população histórica de 47 pares em common support, coortes 2010–2011,
fica **temporariamente suspensa como população operacional**. Não há artefato
reproduzível que identifique individualmente common support, matching e pares.

Coortes 2012–2013: somente sensibilidade, caso a população identificável seja
reconstruída.

O universo histórico de 119 tratados permanece apenas como caracterização
histórica, não como estimativa causal principal. A auditoria reproduzível de
timing baseada no Censo Escolar registra 118 municípios com primeira presença
federal EPT ativa em 2010–2013; isso não reconstitui o antigo matching nem
autoriza substituir a população de 47 pares.

## Grupo de comparação candidato

Municípios never-treated pareados — **grupo de comparação candidato**,
não um grupo principal já validado: depende da reconstrução reproduzível
do common support e do matching (ver "População causal principal"
acima).

---

## Estimador principal candidato

Callaway–Sant'Anna.

## Estimando candidato

ATT dinâmico por event-time para tratados das coortes 2010–2011 com
suporte comum — **estimando candidato**, condicionado à reconstrução
reproduzível do common support e do matching.

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
