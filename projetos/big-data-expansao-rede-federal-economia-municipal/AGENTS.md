# Instruções para Agentes

Antes de trabalhar neste projeto:

1. leia `docs/playbooks/PLAYBOOK_PROJETO.md`;
2. leia `docs/playbooks/ESTADO_ATUAL.md`;
3. leia o playbook especializado da frente;
4. leia os contratos técnicos/metodológicos correspondentes;
5. execute o preflight.

Playbooks especializados:

- `docs/playbooks/PLAYBOOK_CEMPRE.md`
- `docs/playbooks/PLAYBOOK_TERRITORIO.md`
- `docs/playbooks/PLAYBOOK_AUDITORIA.md`

Regras essenciais:

- uma frente não autoriza edição em outra;
- não avançar gates automaticamente;
- não fazer commit/push sem autorização;
- staging sempre explícito;
- auditoria é somente leitura por padrão;
- implementação não aprova sozinha gate material;
- construção de dados, diagnóstico, hipótese e causalidade são etapas
  distintas;
- qualquer divergência material entre estado Git e `ESTADO_ATUAL.md` deve
  ser reportada antes de alterações.

Relatório final mínimo:

- estado inicial;
- arquivos alterados;
- ações;
- testes;
- resultados;
- anomalias;
- gate;
- estado final;
- confirmação das ações proibidas que não ocorreram.

## Identidade visual acadêmica

- Plotly é a biblioteca preferencial para gráficos analíticos.
- Usar o tema central definido em `src/visualizacao_ipt.py`, com paleta inspirada na identidade visual do IPT; não criar paletas ad hoc.
- Gráficos usados em decisões metodológicas devem aparecer no notebook acadêmico principal.
