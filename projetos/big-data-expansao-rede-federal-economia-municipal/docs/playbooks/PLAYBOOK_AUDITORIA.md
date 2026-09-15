# Playbook de Auditoria Técnica

## 0. Objetivo

Padronizar auditorias para evitar:

1. aprovação superficial porque testes passaram;
2. ciclos infinitos de revisão.

Pergunta central:

> O contrato da etapa foi demonstrado pelas evidências?

---

## 1. Independência

Quando houver gate material:

```text
implementação
→ testes
→ autoavaliação
→ auditoria independente
→ correção
→ spot-check
→ commit
```

Quem implementa não encerra sozinho o gate.

---

## 2. Auditoria ampla vs spot-check

### Auditoria ampla

Usar quando:

- etapa nova;
- arquitetura ainda não auditada;
- gate material;
- risco de erro silencioso.

### Spot-check

Usar quando:

- auditoria ampla já identificou problemas;
- correções foram feitas;
- não há evidência para reabrir tudo.

Spot-check verifica apenas:

- achados anteriores;
- efeitos colaterais diretos;
- gate afetado.

---

## 3. Evidência

"Está correto" não basta.

Para cada critério:

- status;
- arquivo/função;
- teste/comando;
- comportamento observado;
- conclusão.

---

## 4. Status por critério

Usar:

- `ATENDIDO`
- `PARCIAL_NAO_BLOQUEANTE`
- `NAO_ATENDIDO`

Evitar:

- "parece";
- "provavelmente";
- "quase".

---

## 5. Classificação

### BLOQUEANTE

Problema que:

- viola requisito obrigatório;
- pode gerar erro silencioso;
- impede reprodução;
- impede gate;
- compromete próxima etapa.

### IMPORTANTE_NAO_BLOQUEANTE

Problema real que não invalida o gate atual.

### DOCUMENTAL

Documento contém fato/contrato incorreto enquanto implementação/dado pode
estar correto.

### EDITORIAL

Forma/redação sem impacto técnico/metodológico.

---

## 6. Gate

Um gate pode ser aprovado quando:

- todos os bloqueantes estão atendidos;
- não há anomalia bloqueante;
- evidência é reproduzível;
- ressalvas estão classificadas.

Conclusões gerais:

- `APROVADO`
- `APROVADO_COM_RESSALVAS_NAO_BLOQUEANTES`
- `NAO_APROVADO`

Usar o nome específico do gate na resposta.

---

## 7. Testes não substituem auditoria

Inspecionar se existem:

- testes tautológicos;
- mocks insuficientes;
- ausência de casos adversariais;
- validação com a mesma constante do código;
- caminhos silenciosos não testados.

Não exigir arquitetura enterprise para projeto acadêmico.

---

## 8. Reprodutibilidade

Auditar:

- dependências declaradas;
- fontes;
- versões;
- hashes;
- fixtures;
- manifestos;
- capacidade de reconstrução.

Biblioteca importada pelo script e ausente das dependências declaradas é
problema de reprodutibilidade.

---

## 9. Git em auditoria

Auditoria é somente leitura por padrão.

Antes:

```powershell
git status --short -- .
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
```

Ao final:

confirmar que nenhum arquivo foi alterado.

---

## 10. Checklist — Fase 0 CEMPRE

### 1. Schema API

ATENDIDO se:

- fixture real;
- payload válido reconhecido;
- não-lista falha;
- `[]` falha;
- só cabeçalho falha;
- ausência de campos essenciais falha.

Bloqueante.

### 2. Fixture

ATENDIDO se real, pequena e usada por testes offline.

Bloqueante.

### 3. Parser

Exemplos:

- `1.234` → observado
- `-12.5` → observado
- `1,234` → desconhecido
- `12,5` → desconhecido

Bloqueante.

### 4. Símbolos

Cobrir:

- `-`
- zeros positivos;
- zeros negativos;
- `x`
- `..`
- `...`
- desconhecido.

Bloqueante.

### 5. API × território

Reconciliação não sobrescreve API.

Bloqueante.

### 6. Território

Pescaria Brava/2007:

- API indisponível;
- território inexistente;
- sem incompatibilidade.

Valor numérico para inexistente deve ser diagnosticado.

Bloqueante.

### 7. Requests

Determinísticos e corretos.

Bloqueante.

### 8. Retries

Erro transitório e persistente testados.

Bloqueante.

### 9. Cache

Demonstrar:

```text
miss → rede → grava
hit → zero rede
```

Cache inválido rejeitado.

Bloqueante.

### 10. Chave canônica

```text
(codigo_municipio_ibge, ano, codigo_variavel_sidra)
```

Duplicata consistente resolve; inconsistente falha.

Bloqueante.

### 11. `.gitignore`

Fixture versionável; raw/cache nacional ignorado.

Bloqueante antes da extração nacional.

### 12. Validações cruzadas

Reproduzíveis e diagnósticas.

### 13. Anos críticos

Representar:

- 2008
- 2009
- 2018
- 2019

Sem ajuste automático 0,32%.
Sem exclusão automática de 2019.

Bloqueante.

### 14. Testes específicos

Todos passam.

Bloqueante.

### 15. Auditoria atualizada

Histórico preservado.

### 16. Nenhuma anomalia bloqueante

Bloqueante.

---

## 11. Checklist — Território

Avaliar:

1. fonte oficial;
2. cobertura 2007–2019;
3. schemas anuais;
4. códigos;
5. composição de códigos;
6. grid;
7. contagens;
8. transições;
9. Pescaria Brava;
10. proveniência;
11. testes;
12. artefato reproduzível;
13. dependências reproduzíveis;
14. ausência de bloqueador.

---

## 12. Decisão de commit

`PODE_COMMITAR = SIM` somente quando:

- gate aprovado ou apenas com ressalvas realmente não bloqueantes;
- diff delimitado;
- nenhuma outra frente misturada;
- `git diff --check` limpo;
- testes necessários passaram.

Commit não é autorização automática para próxima etapa.

---

## 13. Evitar ciclo infinito

Depois de auditoria ampla:

- corrigir achados;
- fazer spot-check;
- se passar, encerrar.

Não abrir terceira auditoria ampla sem nova evidência relevante.

---

## 14. Formato final

```text
ESTADO GIT:
...

CRITÉRIOS:
| Critério | Status | Evidência |

BLOQUEADORES:
...

IMPORTANTES_NAO_BLOQUEANTES:
...

DOCUMENTAIS:
...

EDITORIAIS:
...

VEREDITO:
...

PODE_COMMITAR:
SIM/NÃO

PRÓXIMA ETAPA AUTORIZADA:
...

CONFIRMAÇÃO:
nenhum arquivo alterado.
```

Antes de auditar, ler:

`docs/playbooks/ESTADO_ATUAL.md`
