# Playbook do Projeto SINASC 2024

## Escopo

Este projeto avalia, na Fase 0, a disponibilidade e a qualidade dos dados oficiais do SINASC 2024 para uma futura análise do início precoce do pré-natal e do baixo peso ao nascer.

## Limite vigente

- Estruturar o projeto, adquirir fontes oficiais, registrar provenance e auditar dados.
- Construir apenas definições diagnósticas candidatas de tratamento e outcome.
- Não estimar efeitos causais, não selecionar o conjunto causal final de covariáveis e não iniciar o artigo.

## Contrato analítico

- Unidade candidata: registro de nascido vivo no SINASC 2024, a confirmar nos dados e na documentação.
- Tratamento candidato: início do pré-natal até o terceiro mês, sem classificar automaticamente ausência de pré-natal como controle.
- Outcome candidato: peso ao nascer inferior a 2.500 g, após validação do campo e de seus códigos.
- Covariáveis: classificar provisoriamente por temporalidade; disponibilidade não implica papel de confundidor.
- Variáveis posteriores ao início do pré-natal não podem ser usadas automaticamente como ajuste causal.

## Gates

1. **Preflight**: Git seguro e escopo isolado.
2. **Fonte**: ZIP oficial e documentação identificados com provenance.
3. **Dados**: schema, granularidade, chaves, datas, missing e códigos auditados.
4. **Viabilidade**: capacidade de construir T e Y e disponibilidade de X pré-tratamento documentadas.

Nenhum gate posterior é aprovado automaticamente. A conclusão desta sessão termina no gate de viabilidade da Fase 0.

## Validação mínima

- Testes unitários com fixtures sintéticas.
- Pipeline reproduzível e idempotente para o bruto.
- Notebook executado do início ao fim.
- Diagnósticos factuais reconciliados com as saídas do pipeline.
- Revisão do diff, staging explícito e ausência de dados grandes no Git.

## Ações proibidas nesta fase

- ATE, ATT, matching, propensity score causal, AIPW, DML ou Causal Forest.
- Afirmações causais ou seleção final de covariáveis por correlação.
- Alterações em outros projetos, no Git global ou em dados brutos.
- Expansão para outros anos sem necessidade técnica demonstrada.
