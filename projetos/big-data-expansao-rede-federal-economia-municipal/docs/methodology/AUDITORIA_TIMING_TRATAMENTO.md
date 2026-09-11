# Auditoria de Timing do Tratamento

## Status atual: auditoria reproduzível dos Parquets processados

Esta é a auditoria operacional do timing observável para os **147 municípios
oficiais** da Expansão Fase II. Ela é executada por
`src/auditoria_timing_tratamento.py`, usa exclusivamente os dois Parquets
processados abaixo e grava uma linha por código IBGE em
`outputs/diagnostics/auditoria_timing_tratamento.csv`.

| Fonte | Uso |
|---|---|
| `data/processed/fase_ii_municipios.parquet` | Cadastro oficial: código IBGE, município e UF dos 147 municípios |
| `data/processed/painel_presenca_federal_ept_fase_ii_2007_2019.parquet` | Série município-ano 2007–2019 e flags de presença observada |

O script valida, antes da escrita, 147 códigos oficiais únicos e não nulos,
cobertura completa de 2007–2019, uma linha por município-ano, igualdade entre
as chaves do cadastro e do painel, flags booleanas e coerência dos
diagnósticos temporais. Não lê ZIPs brutos, não faz matching e não atribui um
tratamento causal definitivo.

### Definições observáveis separadas

As três definições não são intercambiáveis:

| Definição | Flag do painel | Significado |
|---|---|---|
| presença federal | `fl_presenca_federal` | Ao menos uma escola federal observada |
| presença federal com EPT | `fl_presenca_federal_ept` | Ao menos uma escola federal com oferta de EPT, independentemente de estar ativa |
| presença federal com EPT ativa | `fl_presenca_federal_ept_ativa` | Ao menos uma escola federal em atividade com oferta de EPT |

Para cada uma, a saída registra número de anos presentes, primeiro e último
ano, censura à esquerda, interrupções internas, número de interrupções e
trajetória monotônica. Há censura à esquerda quando a presença já é verdadeira
em 2007: o início pode ser anterior ao primeiro ano observável. Uma interrupção
é um bloco contíguo de anos falsos entre o primeiro e o último ano verdadeiros.
Uma trajetória é monotônica somente se, após o primeiro verdadeiro, permanece
verdadeira até 2019; nenhuma lacuna é corrigida silenciosamente.

Para cada primeiro ano não nulo, `n_pre = primeiro_ano - 2007` e
`n_pos = 2019 - primeiro_ano`; o próprio ano de primeira presença não integra
nenhuma das duas janelas. Para EPT federal ativa, a auditoria também registra
o primeiro ano da sequência final contínua até 2019. Esse campo é diagnóstico
e não substitui automaticamente o primeiro ano observado.

### Resultados reproduzidos na execução atual

| Primeiro ano observado | Presença federal | Federal com EPT | Federal com EPT ativa |
|---:|---:|---:|---:|
| 2007 | 6 | 2 | 2 |
| 2008 | 2 | 3 | 3 |
| 2009 | 22 | 23 | 23 |
| 2010 | 36 | 32 | 32 |
| 2011 | 66 | 69 | 69 |
| 2012 | 14 | 14 | 14 |
| 2013 | 1 | 3 | 3 |
| 2016 | 0 | 1 | 1 |

Em EPT federal ativa, há 2 municípios censurados à esquerda, 143 trajetórias
monotônicas e 4 intermitentes: Jequié/BA (`2918001`), Montes Claros/MG
(`3143302`), Nossa Senhora da Glória/SE (`2804508`) e Piracicaba/SP
(`3538709`). As quatro trajetórias têm uma interrupção interna; os primeiros
anos persistentes são, respectivamente, 2018, 2011, 2018 e 2018.

Com o primeiro ano de EPT federal ativa, 142 municípios atendem à regra de ao
menos 2 anos pré e 3 pós; 119 atendem à regra de ao menos 3 pré e 3 pós. A
coorte observável 2010–2013 soma 118 municípios (`32+69+14+3`) e 2010–2011
soma 101. Em particular, 2009 tem somente 2 anos pré e não é elegível na
regra 3/3.

### Reconciliações e limitações

- **150 → 147 está reconciliado:** as quatro regiões administrativas do DF
  são associadas ao código IBGE de Brasília, reduzindo 150 cidades-polo para
  147 municípios distintos.
- **144 não foi reproduzido:** a contagem histórica não tem lista de códigos
  IBGE disponível para reconciliação individual.
- **Dois números "119" com significados diferentes — a igualdade é
  coincidência:**
  1. **119 elegíveis pela regra 3/3 na auditoria atual:** soma
     `32+69+14+3+1 = 119`, onde 118 (`32+69+14+3`) vêm das coortes
     observáveis 2010–2013 e 1 município adicional tem o primeiro ano de
     EPT federal ativa observado em 2016 (caso de borda exato da regra:
     9 anos pré, 3 anos pós).
  2. **119 histórico não reproduzido:** distribuição documental
     `37+65+14+3`, atribuída inteiramente às coortes 2010–2013, sem lista
     individual de municípios disponível para conferência.

  As duas populações e as duas regras de elegibilidade não são
  equivalentes — a primeira vem de uma regra de janela pré/pós aplicada
  ao painel reproduzível; a segunda é uma contagem documental sem chave
  municipal. A coincidência numérica não deve ser interpretada como
  reprodução do número histórico.
- **53 e 47 não são populações operacionais:** não há artefatos individuais
  de common support, matching ou pares que permitam reconstituí-las.

As contagens históricas 144, 119, 53 e 47 não devem orientar estimação,
matching ou definição de população causal enquanto não forem reconstruídas
com chaves municipais e regras reproduzíveis. A decisão metodológica ainda
pendente é confrontar o timing anual observável com evidência institucional de
criação, inauguração e início efetivo das atividades, além de definir a
população identificável e o grupo de comparação.

---

## Nota histórica

Uma primeira tentativa desta auditoria foi executada antes da
reconstrução dos Parquets processados (`fase_ii_municipios.parquet` e
`painel_presenca_federal_ept_fase_ii_2007_2019.parquet`). Naquele
momento nenhuma fonte tabular existia no repositório, e a execução
produziu um CSV vazio (0 linhas). Essa versão foi integralmente
substituída pela auditoria reproduzível acima. Os detalhes daquela
execução — incluindo a varredura que constatou a ausência de dados —
não são reproduzidos aqui; permanecem preservados nos documentos de
freeze (`docs/freeze/`) quando necessário para rastreabilidade.
