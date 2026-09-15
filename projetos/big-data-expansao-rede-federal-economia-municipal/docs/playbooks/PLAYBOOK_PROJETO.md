# Playbook Operacional do Projeto

## 0. Finalidade

Este documento é o playbook operacional estável do projeto:

**Expansão da Rede Federal e Economia Municipal**

Repositório:

`C:\GitHub\data-science-projects\projetos\big-data-expansao-rede-federal-economia-municipal`

Seu objetivo é evitar reconstrução de contexto em cada nova sessão de Claude,
Codex ou outro agente.

Este playbook NÃO substitui documentos metodológicos ou técnicos específicos.

### Ordem de autoridade

Quando houver conflito:

1. instrução explícita da tarefa atual;
2. documento contratual/metodológico específico da frente;
3. playbook especializado da frente;
4. este playbook geral;
5. `docs/playbooks/ESTADO_ATUAL.md` para estado operacional.

Se houver contradição material, não escolher uma versão silenciosamente:
pare e reporte.

---

## 1. Pergunta de pesquisa

Pergunta principal:

> A entrada em funcionamento de campi associados à Expansão Fase II da
> Rede Federal alterou a atividade econômica dos municípios?

Unidade:

`município-ano`

Janela principal:

`2007–2019`

Objetivo:

- realizar inferência causal somente se houver identificação defensável;
- caso contrário, produzir análise descritiva/analytics rigorosa;
- nunca forçar causalidade.

Idioma de trabalho e documentação:

**PT-BR**.

---

## 2. Princípios metodológicos

Separar sempre:

1. construção de dados;
2. diagnóstico;
3. hipótese;
4. conclusão causal.

Testes passando NÃO validam causalidade.

Não selecionar especificações com base em:

- sinal do efeito;
- significância;
- tamanho do ATT;
- narrativa desejada.

Não tratar:

- maior número de controles;
- melhor ajuste preditivo;
- ausência de erro de software;

como identificação causal.

Hipótese aberta não é bug.

---

## 3. Populações vigentes

### Fase II

Lista institucional reconstruída:

**147 municípios.**

Todos os 147:

- `ever_treated = true`
- `pode_ser_controle = false`

Not-yet-treated Phase II como controle temporário NÃO está autorizado no
desenho vigente.

### Candidatos à amostra principal

Atualmente:

**129 municípios**

com:

`candidato_amostra_principal = true`

Esses 129 NÃO são a amostra causal final.

Coortes:

- 2009: 21
- 2010: 27
- 2011: 66
- 2012: 13
- 2013: 2

Logo:

- 2009–2010: 48
- 2010–2011: 93

A amostra identificável futura pode ser menor que 129.

### Pool estrutural de controles

Pool atual:

**4.964 candidatos estruturais a controle.**

Eles ainda NÃO são controles causalmente validados.

### Números históricos

Valores antigos como 144, 119, 53 e 47 são históricos arquivados e não devem
ser reutilizados como população corrente sem reprodução explícita.

---

## 4. Desenho causal vigente

Outcome econômico principal pretendido:

**CEMPRE — pessoal ocupado assalariado (SIDRA 708).**

Estimador candidato principal, se identificação for defensável:

**Callaway–Sant'Anna.**

TWFE convencional não é o estimador principal.

Matching:

- pode ser usado futuramente;
- não é obrigatório;
- não deve ser introduzido automaticamente.

Spillover, distância e Arranjos Populacionais:

- são diagnósticos;
- não constituem prova;
- não geram exclusão automática.

DAG é hipótese de trabalho.

Mediadores não devem ser controlados automaticamente.

---

## 5. Documentos contratuais

### Metodologia

- `docs/methodology/CONTRATO_CAUSAL.md`
- `docs/methodology/PROTOCOLO_PRE_ANALISE.md`
- `docs/methodology/ROADMAP_ACADEMICO.md`
- `docs/methodology/REVISAO_INTEGRADA_DESENHO_CAUSAL.md`

### CEMPRE

- `docs/data/AUDITORIA_DISPONIBILIDADE_CEMPRE.md`
- `docs/data/ESPECIFICACAO_PAINEL_CEMPRE.md`
- `docs/data/AUDITORIA_PILOTO_CEMPRE.md`
- `docs/playbooks/PLAYBOOK_CEMPRE.md`

### Território

- `docs/data/AUDITORIA_CALENDARIO_TERRITORIAL_2007_2019.md`
- `docs/playbooks/PLAYBOOK_TERRITORIO.md`

### Auditoria

- `docs/playbooks/PLAYBOOK_AUDITORIA.md`

### Estado corrente

- `docs/playbooks/ESTADO_ATUAL.md`

---

## 6. Separação de unidades de trabalho

Uma frente aberta NÃO autoriza alteração em outra.

Antes de editar, identificar:

- unidade autorizada;
- arquivos permitidos;
- arquivos proibidos;
- estado Git inicial.

Se existirem duas unidades de trabalho não commitadas, manter separação
rigorosa.

Não aproveitar uma tarefa para fazer melhorias laterais.

---

## 7. Preflight obrigatório

No início de implementação ou auditoria, executar:

```powershell
.\scripts\agent_preflight.ps1
```

ou, no mínimo:

```powershell
git status --short -- .
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
python -c "import sys; print(sys.executable)"
python -m pip check
```

Se o estado divergir materialmente de `ESTADO_ATUAL.md`, parar e reportar.

---

## 8. Política Git

O projeto está dentro de um monorepo.

Preferir:

```powershell
git status --short -- .
```

Existe historicamente uma pendência externa possível em:

`../concessao_credito/.claude/`

Não tocar nela.

Nunca usar automaticamente:

```text
git add .
git add -A
```

Quando autorizado a commitar, usar paths explícitos.

Antes do commit:

```powershell
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
```

Commit e push só com autorização explícita.

---

## 9. Política de dados e artefatos

Código, testes, documentação, pequenos fixtures e manifestos podem ser
versionados quando deliberadamente previstos.

Raw nacional e artefatos grandes normalmente não pertencem ao Git.

Antes de criar artefatos:

1. verificar `.gitignore`;
2. respeitar padrões atuais;
3. evitar liberar diretórios raw inteiros;
4. versionar apenas exceções pequenas intencionais.

---

## 10. Política de testes

Preferir:

- testes unitários offline;
- fixtures pequenas;
- integração controlada;
- falha explícita para schema inesperado.

Não depender permanentemente da internet em testes unitários.

Não rodar automaticamente toda a suíte do projeto quando a alteração é
isolada.

Rodar:

- testes diretamente relacionados;
- `git diff --check`.

---

## 11. Política de documentação

Decisões metodológicas, auditorias e etapas reproduzíveis relevantes devem
ficar documentadas.

Não apagar histórico de uma decisão posteriormente corrigida.

Quando uma auditoria independente reprovar uma autoavaliação, registrar:

1. implementação inicial;
2. autoavaliação;
3. achado da auditoria;
4. reclassificação do gate;
5. correção;
6. nova verificação.

---

## 12. Gates principais

### CEMPRE

1. `PILOTO_TECNICO_APROVADO`
2. `PAINEL_TECNICO_CONSTRUIDO`
3. `PAINEL_ANALITICO_APROVADO`

A extração nacional só pode começar após o primeiro gate estar aprovado de
forma independente.

### Território

`CALENDARIO_TERRITORIAL_APTO`

Aprova somente o calendário de existência municipal.

Não aprova CEMPRE nem inferência causal.

---

## 13. Papel dos agentes

### Claude Code

Preferencial para:

- implementação;
- scripts;
- testes;
- documentação operacional;
- execução de pipelines.

Padrão:

**Sonnet / Medium / sem subagentes**

quando não houver motivo concreto para configuração mais pesada.

### Codex

Preferencial para:

- auditoria independente;
- segunda opinião;
- inspeção delicada de lógica;
- spot-check.

Auditoria é somente leitura por padrão.

### ChatGPT

Preferencial para:

- raciocínio metodológico;
- desenho do projeto;
- decisões de escopo;
- interpretação de resultados;
- coordenação entre agentes.

---

## 14. Implementação não aprova a si mesma

Quando houver gate material:

1. agente A implementa;
2. agente A testa e pode autoavaliar;
3. agente B audita independentemente;
4. só então o gate é fechado.

---

## 15. Não avançar automaticamente

Ao terminar uma tarefa:

- não iniciar outra frente;
- não executar extração nacional;
- não fazer merge causal;
- não fazer commit/push;

salvo autorização explícita.

---

## 16. Relatório final mínimo

Toda tarefa relevante deve informar:

- estado Git inicial;
- arquivos alterados/criados;
- ações executadas;
- testes;
- resultados;
- anomalias;
- limitações;
- gate, se aplicável;
- estado Git final;
- confirmação das ações proibidas que NÃO ocorreram.

---

## 17. Atualização do playbook

Este arquivo deve mudar pouco.

Informações transitórias pertencem a:

`docs/playbooks/ESTADO_ATUAL.md`
