# Impacto da Expansão da Rede Federal sobre a Atividade Econômica Municipal

Projeto desenvolvido no contexto da disciplina de Big Data & Analytics.

## Pergunta de pesquisa

Qual foi o efeito da chegada de novos campi da Rede Federal de Educação Profissional, Científica e Tecnológica, associados à Expansão Fase II, sobre a atividade econômica dos municípios brasileiros?

## Objetivo

Avaliar se a chegada de novos campi da Rede Federal esteve associada a mudanças na atividade econômica dos municípios tratados, utilizando dados públicos oficiais e métodos modernos de inferência causal para tratamentos escalonados no tempo.

## Status

FASE_EXPLORATORIA = ENCERRADA

VIABILIDADE_CAUSAL = PROMISSORA_COM_RESSALVAS

EFEITO_CAUSAL_ESTIMADO = NAO

FASE_ATUAL = DESENVOLVIMENTO_ACADEMICO

**PAUSADO EM 25/09/2026.** Ver
`docs/playbooks/ESTADO_ATUAL.md` (seção 33) para o registro de pausa,
o último gate concluído e o ponto de retomada.

Nenhuma afirmação causal final foi estabelecida.

## Unidade de análise

Município-ano.

## Política analisada

Expansão da Rede Federal de Educação Profissional, Científica e Tecnológica, com foco na chamada Expansão Fase II.

## Tratamento

Primeira presença federal de EPT observada no município associada à Expansão Fase II.

O timing principal deve ser interpretado como proxy anual de primeira presença operacional observada no Censo Escolar.

Não deve ser interpretado automaticamente como data de criação, autorização ou inauguração do campus.

## Outcomes candidatos

- pessoal ocupado assalariado;
- pessoal ocupado total;
- número de unidades locais;
- salário médio mensal.

Outcome primário congelado ex ante no D14: **pessoal ocupado assalariado
do CEMPRE**. Os demais outcomes permanecem secundários.

## Estratégia causal

O tratamento é escalonado no tempo.

Estimadores TWFE ingênuos não serão utilizados como especificação causal principal.

O estimador futuro candidato principal foi congelado no D14 como
Callaway–Sant'Anna para adoção escalonada. Ele ainda não foi executado e
o desenho causal não está aprovado.

## Limitação central de validade externa

A fase exploratória mostrou suporte comum limitado.

A população causal principal candidata não representa automaticamente todos os municípios tratados pela Expansão Fase II.

## Estrutura

- `data/raw`: fontes originais;
- `data/interim`: dados intermediários;
- `data/processed`: bases analíticas;
- `docs/freeze`: registro das decisões congeladas;
- `docs/methodology`: decisões metodológicas da fase acadêmica;
- `docs/literature`: revisão de literatura;
- `docs/institutional`: reconstrução histórica e institucional;
- `notebooks`: análises exploratórias e acadêmicas;
- `src`: pipeline reproduzível;
- `outputs`: tabelas e figuras finais.

## Integridade metodológica

As decisões da fase exploratória não devem ser alteradas retroativamente com base nos resultados pós-tratamento.

Mudanças substantivas futuras devem possuir justificativa metodológica independente dos efeitos encontrados.

## D20A — validação do backend Python

O backend `differences==0.3.0` foi instalado somente na `.venv` do projeto e
validado com dados sintéticos. A instalação acrescentou apenas o próprio
pacote; `numpy`, `pandas`, `scikit-learn`, `statsmodels` e `scipy` mantiveram
suas versões, e `pip check` permaneceu sem conflitos.

A validação confirmou ATT grupo-tempo, agregações simples, por coorte e por
tempo relativo, controles *never-treated*, `base_period='universal'`, modo
painel e Monte Carlo com sementes pré-fixadas. A inferência é classificada
como parcial porque a referência determinística `k=-1` precisa ser excluída
do bootstrap na versão 0.3.0 e reinserida como zero apenas na apresentação.

A decisão sobre Cabo Frio permanece bloqueada: excluir somente 2009 preserva
as demais observações no objeto, mas impede que o município participe das
células pós-tratamento da coorte 2010 que usam 2009 como período-base. O
dry-run da D15 não chamou `.fit()` e confirmou o arquivo byte a byte.

**Nenhum efeito real foi estimado, a primeira estimação real não está
autorizada e o desenho causal não está aprovado.** A evidência completa está
em `notebooks/07_validacao_backend_differences.ipynb`.

## D20B — fechamento pré-estimação

A D20B separa explicitamente a população documental da população estimável:

- `POPULACAO_D15_TRATADOS = 129`;
- `POPULACAO_PRINCIPAL_ESTIMAVEL = 128`.

Cabo Frio/RJ permanece intacto na D15, mas é excluído integralmente apenas da
view principal de estimação. Com `g=2010`, o período-base universal é 2009,
ano de transição institucional inelegível. Não houve imputação, alteração da
coorte, uso de repeated cross-section ou exclusão implícita por célula.

A view derivada tem 4.963 controles, 5.091 municípios e 66.183 linhas em
painel balanceado 2007–2019. O workaround de `k=-1` foi validado em dados
sintéticos: ATT pós-tratamento, agregações por coorte e simples e event-study
para `k != -1` ficaram invariantes.

O bootstrap final foi pré-especificado com 1.999 repetições,
`random_state=20260924`, `n_jobs=1` e bandas simultâneas de 95%. Essa
configuração não foi executada na base real. O addendum correspondente está em
`docs/methodology/ADDENDUM_D20B_CABO_FRIO_INFERENCIA.md`.

`D20B_PRONTO_PARA_ESTIMACAO_REAL = SIM` fecha somente esses bloqueios
técnicos; não executa automaticamente a estimação e não aprova o desenho
causal.
