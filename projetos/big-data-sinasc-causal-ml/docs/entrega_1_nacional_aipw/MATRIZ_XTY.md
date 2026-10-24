# Matriz X–T–Y

Como os dados do SINASC são organizados para a análise causal, e por que o tratamento T não é "mais uma coluna" de X.

## 1. As três peças

Em cada ano, depois dos filtros de elegibilidade, cada linha é **um nascido vivo** e os dados são separados em três blocos:

```
            X (n × 7)                          T (n × 1)    Y (n × 1)
 ┌──────────────────────────────────────┐    ┌───────┐    ┌───────┐
 │ X1  X2  X3  X4  X5  X6  X7           │    │   T   │    │   Y   │
 │ 27  3   4   5   0   0   35           │    │   1   │    │   0   │
 │ 19  2   4   1   1   IGN 15           │    │   0   │    │   1   │
 │ ...                                  │    │  ...  │    │  ...  │
 └──────────────────────────────────────┘    └───────┘    └───────┘
```

*As linhas acima são ilustrativas, não registros reais.*

Na formulação principal B de 2024, **n = 2.207.214**: são 1.942.045 com T = 1 e 265.169 com T = 0.

## 2. X — covariáveis (n × 7)

São características da gestante que, em princípio, já existiam **antes** do início do pré-natal e que influenciam tanto o momento de início (T) quanto o peso ao nascer (Y). São os potenciais **confundidores** observados.

| | Variável analítica | Campo SINASC | Tipo | Categorias |
| --- | --- | --- | --- | --- |
| **X1** | Idade materna | `IDADEMAE` | numérica (10–59 anos) | — |
| **X2** | Escolaridade | `ESCMAE2010` | categórica | 0–5, `IGNORADO` |
| **X3** | Raça/cor | `RACACORMAE` | categórica | branca, preta, amarela, parda, indígena, `IGNORADO` |
| **X4** | Situação conjugal | `ESTCIVMAE` | categórica | solteira, casada, viúva, separada, união estável, `IGNORADO` |
| **X5** | Paridade | `PARIDADE` | categórica | nulípara, multípara |
| **X6** | Perdas fetais anteriores | `QTDFILMORT` | categórica | 0, 1, 2 ou mais, `IGNORADO` |
| **X7** | UF de residência | `CODMUNRES` (2 primeiros dígitos) | categórica | 27 UFs |

São sete colunas "conceituais". Depois da codificação *one-hot* usada na regressão logística, cada categoria vira uma coluna indicadora, e a matriz efetivamente ajustada fica bem mais larga. O conteúdo, porém, é o mesmo.

## 3. T — tratamento (n × 1)

| Valor | Significado (formulação B) | Campo |
| --- | --- | --- |
| T = 1 | início do pré-natal no 1º, 2º ou 3º mês | `MESPRENAT` ∈ {1, 2, 3} |
| T = 0 | início do pré-natal no 4º, 5º ou 6º mês | `MESPRENAT` ∈ {4, 5, 6} |

Registros com início no 7º–9º mês, mês ignorado (99) ou vazio não entram na formulação B. Na sensibilidade C, o comparador é apenas 4º–5º mês. T = 0 significa **início tardio**, e não ausência de pré-natal.

## 4. Y — desfecho (n × 1)

| Valor | Significado | Campo |
| --- | --- | --- |
| Y = 1 | baixo peso ao nascer (< 2.500 g) | `PESO` |
| Y = 0 | peso ≥ 2.500 g | `PESO` |

Só entram registros com 500 g ≤ `PESO` ≤ 6.000 g. Em 2024, a prevalência de Y = 1 é de 7,89% na população analítica histórica.

## 5. Por que T não é simplesmente misturado em X?

Num modelo **preditivo** comum, bastaria juntar tudo numa matriz [X, T] e prever Y. Em **inferência causal**, a pergunta é outra: *qual seria a diferença de risco se a mesma gestante tivesse iniciado o pré-natal cedo, em vez de tarde?* Para respondê-la, T recebe um papel próprio, por quatro razões:

1. **T é a "intervenção" de interesse, e não um preditor qualquer.** O objetivo não é prever Y bem, mas comparar dois cenários contrafactuais de T para os mesmos X.
2. **X explica T.** Gestantes com mais escolaridade, casadas ou de certas UFs iniciam o pré-natal mais cedo. Esse mecanismo de "quem recebe o tratamento" é modelado à parte, pelo **escore de propensão**.
3. **O efeito de T pode variar com X.** Ajustar um modelo de desfecho separado em cada braço (T = 1 e T = 0) evita impor que a diferença seja a mesma para todos os perfis.
4. **O coeficiente de T num modelo único não é o estimando.** Numa regressão logística com T dentro de X, o coeficiente de T é um log-*odds ratio* condicional, dependente da especificação, e não a diferença média de risco que se quer estimar.

## 6. As três funções que o AIPW usa

| Função | Fórmula | Pergunta que responde | Ajustada com |
| --- | --- | --- | --- |
| Escore de propensão | **e(X) = P(T = 1 \| X)** | Qual a chance de uma gestante com perfil X iniciar cedo? | X → T (todas as linhas) |
| Desfecho no braço precoce | **m₁(X) = E[Y \| T = 1, X]** | Qual o risco de BPN de quem tem perfil X e iniciou cedo? | X → Y, só linhas com T = 1 |
| Desfecho no braço tardio | **m₀(X) = E[Y \| T = 0, X]** | Qual o risco de BPN de quem tem perfil X e iniciou tarde? | X → Y, só linhas com T = 0 |

O AIPW combina as três funções:

- **m₁(X) − m₀(X)** dá, para cada gestante, a diferença de risco prevista entre os dois cenários;
- **e(X)** corrige essa previsão, dando mais peso às observações "raras" para o seu perfil (por exemplo, uma gestante com perfil típico de início precoce que iniciou tarde);
- a média dessas contribuições sobre todos os nascidos vivos é o **contraste AIPW ajustado**.

Se pelo menos um dos dois tipos de modelo (propensão ou desfechos) estiver bem especificado, a estimativa é consistente. Essa é a "dupla robustez". Ela vale **sob as hipóteses de identificação**: confundimento não medido não é corrigido por nenhum dos dois modelos.

## 7. O que nunca entra em X

| Campo | Por quê |
| --- | --- |
| `SEMAGESTAC`, `GESTACAO` | Idade gestacional: resulta da gestação e é mediadora/*collider* entre pré-natal e peso |
| `CONSPRENAT`, `CONSULTAS` | Consultas acumulam depois do início: fazem parte do caminho T → Y |
| `PARTO`, `APGAR1`, `APGAR5` | Ocorrem no parto ou depois dele |
| `KOTELCHUCK` | Índice que combina início (T) e número de consultas (mediadora) |

**Regra prática:** X deve descrever a gestante *antes* da decisão de iniciar o pré-natal. O que vem depois não é confundidor e pode distorcer a comparação.

---

Ver também o [dicionário técnico](DICIONARIO_TECNICO.md) e o [relatório final](RELATORIO_FINAL_DISCIPLINA.md#13-método-aipw).
