# Instruções para Claude Code

Antes de qualquer tarefa neste repositório:

1. leia `docs/playbooks/PLAYBOOK_PROJETO.md`;
2. leia `docs/playbooks/ESTADO_ATUAL.md`;
3. leia o playbook específico da frente:
   - CEMPRE: `docs/playbooks/PLAYBOOK_CEMPRE.md`
   - território: `docs/playbooks/PLAYBOOK_TERRITORIO.md`
   - auditoria: `docs/playbooks/PLAYBOOK_AUDITORIA.md`
4. leia os documentos contratuais específicos indicados nesses playbooks;
5. execute `scripts/agent_preflight.ps1`.

Regras:

- não avance automaticamente para o próximo gate;
- não altere outra unidade de trabalho aberta;
- não faça `git add`, commit ou push sem autorização explícita;
- não use `git add .` ou `git add -A`;
- preserve auditabilidade;
- testes passando não equivalem a validação causal;
- se houver contradição material entre documentos, pare e reporte;
- ao finalizar, informe arquivos, testes, anomalias, gate e Git status.

A instrução explícita do usuário para a tarefa atual prevalece sobre este
arquivo, desde que não contradiga um contrato metodológico/técnico que precise
ser explicitamente revisto.
