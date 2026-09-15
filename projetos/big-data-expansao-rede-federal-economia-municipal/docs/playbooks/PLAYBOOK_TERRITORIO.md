# Playbook Operacional — Calendário Territorial IBGE

## 0. Objetivo

Este documento rege o calendário territorial município-ano 2007–2019.

Pergunta operacional:

> O código municipal constava da divisão territorial oficial naquele ano?

O calendário identifica existência/presença oficial.

Ele NÃO harmoniza fronteiras geográficas históricas.

Contrato principal:

`docs/data/AUDITORIA_CALENDARIO_TERRITORIAL_2007_2019.md`

---

## 1. Fonte

Fonte:

**IBGE — Divisão Territorial Brasileira (DTB)**

Edições anuais utilizadas:

`2007–2019`

Não usar como fonte principal histórica:

- Wikipedia;
- Kaggle;
- terceiros;
- API de localidades atual;
- Estimativas de População.

Fontes oficiais auxiliares podem servir para conferência.

---

## 2. Regra de derivação

```text
municipio_existia_no_ano =
    código presente na lista municipal da edição DTB do próprio ano
```

Não inferir existência a partir de:

- CEMPRE;
- Censo Escolar;
- população;
- nome;
- contagem esperada.

---

## 3. Contagens confirmadas

- 2007–2008: **5.564**
- 2009–2012: **5.565**
- 2013–2019: **5.570**

A narrativa "5.564 até 2012 → 5.570 em 2013" é incorreta.

---

## 4. Entradas

### 2009

- `2206720` — Nazária/PI

Primeira DTB:

2009.

Instalação oficial documentada:

01/01/2009.

### 2013

- `1504752` — Mojuí dos Campos/PA
- `4212650` — Pescaria Brava/SC
- `4220000` — Balneário Rincão/SC
- `4314548` — Pinto Bandeira/RS
- `5006275` — Paraíso das Águas/MS

Instalação oficial:

01/01/2013.

---

## 5. Demais transições

Na janela:

- entradas: 6
- saídas: 0
- mudanças de UF: 0
- possíveis trocas de código: 0
- lacunas intermediárias: 0
- mudanças literais de nome: 42

Mudança de nome com código estável não cria nova identidade.

Não atribuir natureza jurídica à mudança sem fonte oficial.

---

## 6. Pescaria Brava

Código:

`4212650`

Resultado derivado das DTB:

- 2007–2012: `False`
- 2013–2019: `True`

O script não deve conter história específica para forçar esse resultado.

---

## 7. Formatos anuais

As edições não têm schema uniforme.

A implementação deve tratar explicitamente:

- nível municipal versus distrito/subdistrito;
- código completo de 7 dígitos;
- código parcial de 5 dígitos + UF;
- colunas;
- abas;
- membros XLS.

Códigos devem permanecer strings.

Não converter células numéricas silenciosamente.

---

## 8. Composição de código

Quando a fonte trouxer UF + 5 dígitos:

validar:

- UF textual de 2 dígitos;
- parcial textual de 5 dígitos;
- resultado final de 7;
- coerência do prefixo;
- coerência com código completo quando disponível.

---

## 9. Colapso de distrito

Antes de colapsar várias linhas para município, verificar unicidade de:

- nome municipal;
- UF;

dentro de cada código.

Divergência interrompe construção.

---

## 10. Grid

União:

**5.570 códigos**

Grid:

`5.570 × 13 = 72.410 linhas`

Cada código:

13 linhas.

Chave:

```text
(codigo_municipio_ibge, ano)
```

Sem duplicidade.

---

## 11. Schema atual

Campos:

- `codigo_municipio_ibge`
- `ano`
- `municipio_existia_no_ano`
- `nome_municipio_ano`
- `uf_codigo`
- `uf_sigla`
- `fonte_territorial`
- `versao_fonte`
- `fonte_ano`
- `observacao_territorial`

Datas de vigência não devem ser inventadas quando a DTB não as fornecer.

O campo essencial para CEMPRE é:

`municipio_existia_no_ano`

---

## 12. Integridade

Os 13 ZIPs devem ser identificados por:

- URL;
- tamanho;
- SHA-256.

Membros XLS podem ter hash próprio.

Se download/local divergir:

- falhar;
- investigar;
- não usar silenciosamente.

---

## 13. Raw e derivados

Raw:

`data/raw/ibge/territorio/dtb/`

não deve ser versionado automaticamente.

Artefato:

`data/processed/calendario_territorial_municipios_2007_2019.parquet`

Diagnósticos:

- contagem anual;
- transições;
- reconciliação;
- manifesto.

---

## 14. Manifesto

Registrar, quando disponível:

- órgão;
- produto;
- URL;
- ano;
- arquivo;
- data de acesso;
- tamanho;
- hash ZIP;
- membro XLS;
- hash XLS;
- aba;
- schema;
- transformação;
- n municípios;
- hash do script;
- commit;
- versões;
- hashes derivados.

---

## 15. Dependências

A leitura dos `.xls` históricos usa:

`xlrd`

Versão validada:

`xlrd==2.0.2`

A frente não é plenamente reproduzível em clone limpo enquanto uma
dependência importada diretamente estiver ausente das dependências
declaradas.

---

## 16. Validações

Validar:

- ano 2007–2019;
- código de 7 dígitos;
- duplicidade anual;
- duplicidade do calendário;
- grid completo;
- booleano não nulo;
- presença ↔ True;
- ausência ↔ False;
- contagem anual;
- UF coerente;
- schema anual.

---

## 17. Reconciliação estrutural

Resultados atuais confirmados:

- 147/147 Fase II existem nos 13 anos;
- 4.964/4.964 candidatos estruturais existem nos 13 anos.

A checagem é diagnóstica.

Não excluir ou selecionar município automaticamente.

---

## 18. Limitação de fronteiras

Código estável NÃO implica território estável.

Desmembramentos podem alterar:

- área;
- população;
- emprego;
- estabelecimentos;

do município de origem.

Isso não invalida o calendário de existência, mas importa para análise
econômica futura.

---

## 19. Nomes

`nome_municipio_ano` significa nome usado na DTB daquele ano.

Não é necessariamente histórico jurídico exato do topônimo.

---

## 20. Gate

`CALENDARIO_TERRITORIAL_APTO`

Requisitos:

1. fonte oficial;
2. cobertura dos 13 anos;
3. schemas normalizados;
4. códigos reproduzíveis;
5. composição validada;
6. grid correto;
7. contagens corretas;
8. transições corretas;
9. Pescaria Brava reconciliada;
10. proveniência;
11. testes;
12. artefato reproduzível;
13. dependências reproduzíveis;
14. nenhuma anomalia bloqueante.

Esse gate não autoriza CEMPRE nacional nem análise causal.

---

## 21. Integração com CEMPRE

Depois de apto, o calendário nacional pode substituir a fixture territorial
mínima da Fase 0.

Essa integração é tarefa própria.

Não modificar automaticamente o pipeline CEMPRE durante tarefa territorial.
