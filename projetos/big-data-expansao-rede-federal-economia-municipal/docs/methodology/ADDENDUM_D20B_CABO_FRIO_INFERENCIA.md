# Addendum D20B — Cabo Frio e inferência pré-estimação

## 1. Status e finalidade

Este addendum complementa o congelamento D14 sem reescrever o documento
original. A decisão foi tomada antes de qualquer ATT, event-study, p-valor ou
outro resultado causal na amostra real.

O addendum é metodologicamente necessário porque a decisão altera a população
tratada efetivamente utilizada no estimando principal, embora não altere a
população documental materializada na D15.

```text
POPULACAO_D15_TRATADOS = 129
POPULACAO_PRINCIPAL_ESTIMAVEL = 128
```

## 2. Decisão sobre Cabo Frio/RJ

Cabo Frio/RJ, código IBGE `3300704`, permanece documentado na D15 como tratado
com `g=2010`. O ano de 2009 é a transição institucional e permanece inelegível.
Na especificação principal, `base_period="universal"` e `anticipation=0`
definem `g-1` como período-base. Para Cabo Frio, `g-1=2009`, exatamente o ano
que não pode ser usado.

Portanto, Cabo Frio não possui período-base válido para a especificação
principal. A decisão D20B é:

- manter as 13 linhas de Cabo Frio na população documental D15;
- não imputar nem usar 2009;
- não alterar `g=2010`;
- não tratar o painel como repeated cross-section;
- não aceitar exclusão implícita por célula;
- excluir Cabo Frio integralmente somente da view/cópia de estimação principal;
- não alterar o parquet D15.

A view principal resultante contém 128 tratados, 4.963 controles, 5.091
municípios e 66.183 município-anos, em painel balanceado 2007–2019. As coortes
tratadas passam a 2009=21, 2010=26, 2011=66, 2012=13 e 2013=2.

Essa alteração decorre exclusivamente da incompatibilidade institucional
`Cabo Frio/2009 × referência g-1`, identificada antes de observar qualquer
efeito real. Ela não constitui seleção por resultado.

## 3. Inferência e referência `k=-1`

Com `base_period="universal"`, `k=-1` é uma referência determinística igual a
zero. Em `differences==0.3.0`, incluir essa célula de variância zero no
multiplier bootstrap torna as bandas simultâneas indefinidas.

A D20B valida o seguinte procedimento:

1. retirar `k=-1` apenas do conjunto usado para calcular o bootstrap;
2. estimar as bandas simultâneas para os demais períodos;
3. recolocar `k=-1` como zero somente na tabela/gráfico de apresentação;
4. manter erro-padrão e limites de `k=-1` ausentes, pois não foram estimados.

Em dados sintéticos D19, o procedimento não alterou:

- ATT(g,t) pós-tratamento;
- agregação por coorte;
- agregação simples;
- event-study para todo `k != -1`.

Qualquer mudança futura nessas estimativas deve bloquear a execução real.

## 4. Configuração final pré-especificada

```text
backend = differences==0.3.0
base_period = universal
control_group = never_treated
est_method = dr
boot_iterations = 1999
random_state = 20260924
n_jobs = 1
alpha = 0.05
bandas_simultaneas = true
cluster = entidade
```

`n_jobs=1` é deliberado. Neste ambiente, `differences==0.3.0` falhou dentro do
multiplier bootstrap com `n_jobs>1` por incompatibilidade Joblib/tqdm. Um único
processo é a configuração estável e evita que paralelismo altere ou impeça o
resultado.

Os 1.999 draws não foram executados na base real nesta unidade.

## 5. Limites do fechamento

Este addendum fecha somente as decisões técnicas sobre Cabo Frio, a view
principal estimável e a configuração de inferência. Ele não aprova tendências
paralelas, ausência de spillovers, suporte comum, validade do timing, desenho
causal ou interpretação causal final.

```text
D20B_EFEITO_REAL_ESTIMADO = NAO
DESENHO_CAUSAL_APROVADO = NAO
```
