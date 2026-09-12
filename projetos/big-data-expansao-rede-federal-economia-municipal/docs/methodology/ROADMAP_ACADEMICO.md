# Roadmap da fase acadêmica

## Situação atual (2026-09-12)

Desenho Causal v1 consolidado em `CONTRATO_CAUSAL.md`: cadastro causal
preliminar aprovado e versionado (147 municípios, 129 candidatos
preliminares — ver `CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`), pergunta de
pesquisa formalizada, estimando candidato formalizado, DAG causal
elaborado, mecanismos de antecipação e spillover catalogados como
decisões abertas. Nenhum estimador foi executado.

## Próxima etapa técnica (pós-Desenho Causal v1)

Depois deste contrato, é necessário construir, nesta ordem:

1. **cadastro nacional de exposição** à Rede Federal, para impedir que um
   município tratado por outra fase/campus entre no pool de controles;
2. **pool reproduzível de controles candidatos**, aplicando as exclusões
   registradas em `CONTRATO_CAUSAL.md` (seção "Grupo de comparação
   candidato");
3. **painel econômico municipal CEMPRE 2007–2019**, reproduzível, com
   provenance documentada;
4. **covariáveis pré-tratamento** justificadas pelo DAG de
   `CONTRATO_CAUSAL.md` (não variáveis pós-tratamento/mediadoras);
5. **regras de spillover e antecipação**, fundamentadas em evidência
   institucional ou análise de sensibilidade — nunca fixadas por
   conveniência;
6. **common support e balanceamento** entre tratados e o pool de
   controles construído nos passos 1-2;
7. **somente então** event study e ATT (Callaway–Sant'Anna).

Nenhuma dessas etapas foi executada nesta consolidação documental.

---

## Etapa 1 — Fundamentação

- revisão de literatura; **(parcial — Faveri, Petterini e Barbosa, 2018,
  ver `docs/institutional/EXPANSAO_FASE_II.md`, seção 6; revisão
  adicional ainda pendente para as covariáveis do DAG)**
- reconstrução histórica da Expansão Fase II; **(concluída — ver
  `docs/institutional/EXPANSAO_FASE_II.md` e
  `docs/institutional/AUDITORIA_LISTA_FASE_II.md`)**
- documentação das regras institucionais de seleção e implantação.
  **(concluída — critérios social/geográfico/desenvolvimentista, ver
  `docs/institutional/EXPANSAO_FASE_II.md`, seção 3)**

## Etapa 2 — Identificação

- elaborar DAG; **(concluído — ver `CONTRATO_CAUSAL.md`, seção "DAG
  causal")**
- definir estimando; **(formalizado como candidato — ver
  `CONTRATO_CAUSAL.md`, seção "Estimando candidato")**
- definir outcome primário e secundários; **(formalizado — pessoal
  ocupado assalariado do CEMPRE como primário; ver `CONTRATO_CAUSAL.md`)**
- formalizar população causal; **(cadastro institucional e elegibilidade
  temporal formalizados — ver `CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`;
  população causal identificável ainda depende das etapas 3-6 acima)**
- formalizar timing; **(concluído para a proxy do Censo e as exceções
  documentadas — ver `CADASTRO_CAUSAL_TRATAMENTO_FASE_II.md`)**
- definir antecipação; **(aberto — ver `CONTRATO_CAUSAL.md`, seção
  "Antecipação")**
- definir spillovers; **(aberto — ver `CONTRATO_CAUSAL.md`, seção
  "Spillovers")**
- definir grupo de comparação. **(aberto — ver `CONTRATO_CAUSAL.md`,
  seção "Grupo de comparação candidato")**

## Etapa 3 — Dados

- reconstruir fontes oficiais necessárias;
- validar timing externamente;
- criar pipeline reproduzível;
- documentar provenance dos dados.

## Etapa 4 — Análise

- análise descritiva;
- balanceamento;
- event study;
- staggered DiD;
- inferência;
- robustez;
- sensibilidade;
- heterogeneidade.

## Etapa 5 — Redação

- resultados;
- validade interna;
- validade externa;
- limitações;
- discussão;
- conclusão.
