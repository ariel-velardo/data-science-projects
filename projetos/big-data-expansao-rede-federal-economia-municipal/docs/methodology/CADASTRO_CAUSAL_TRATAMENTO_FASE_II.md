# Cadastro Causal Preliminar de Tratamento — Expansão Fase II

## Finalidade e escopo

`src/constroi_cadastro_causal_fase_ii.py` constrói uma linha por município
oficial da Fase II, combinando o timing observado no Censo Escolar (calculado
diretamente do painel, nunca de um CSV auxiliar) com decisões institucionais
versionadas em `src/excecoes_institucionais_fase_ii.json`.

Esta etapa **não** executa matching, common support, ATT, event study,
`did_multiplegt_dyn`, HonestDiD ou qualquer estimação causal. Ela também não
altera os Parquets de origem. **O cadastro gerado não autoriza, por si só,
estimar efeitos causais.**

## Definição causal adotada

O tratamento operacional candidato é **"presença operacional de campus da
Expansão Fase II no município"**. Sob essa definição o tratamento é
absorvente — mas a flag anual de EPT ativa do Censo Escolar é evidência
observacional, não uma prova automática de abertura ou fechamento
institucional do campus. As duas coisas podem divergir (uma unidade pode
permanecer aberta enquanto a classificação curricular específica de "EPT"
oscila no Censo), e o cadastro trata essa divergência explicitamente em vez de
escondê-la atrás de um valor padrão.

## Populações distintas

| População | Definição | Onde aparece |
|---|---|---|
| **Institucional** | Os 147 municípios oficiais da Fase II, sem qualquer filtro. | Todo o cadastro; `fase_ii=true` e `ever_treated=true` para os 147. |
| **Temporalmente elegível** | Subconjunto que atende a uma janela mínima de anos pré/pós dentro de 2007–2019. | `elegivel_temporal_2pre_3pos`, `elegivel_temporal_3pre_3pos`. |
| **Candidata à amostra principal** | Subconjunto curado que combina status institucional, ausência de tratamento preexistente ao painel, coorte definida e elegibilidade temporal mínima. | `candidato_amostra_principal`. **Elegibilidade temporal bruta não é convertida automaticamente em candidatura** — um município pode ser temporalmente elegível e, ainda assim, ficar fora da amostra principal por razões institucionais (ex.: Porto Alegre, Duque de Caxias, Brasília). |
| **Efetivamente estimada** | Ainda não existe. Depende de common support, matching e definição do grupo de comparação, fora do escopo desta etapa. | Não construída aqui. |

A população institucional nunca é usada para reproduzir contagens históricas
sem chave municipal (144, 119, 53, 47): nenhum município é adicionado,
removido ou substituído para bater com esses números.

## Todos os 147 municípios pertencem à Fase II

Isso tem duas consequências estruturais, verificadas em toda execução:

- `ever_treated=true` para os 147 municípios — nenhum pode, no futuro, virar
  never-treated.
- `pode_ser_controle=false` para os 147 municípios — mesmo os excluídos da
  amostra principal continuam expostos institucionalmente; exclusão da
  amostra principal **não significa ausência de tratamento** e nunca
  autoriza usar o município como controle.

## Campos temporais — camadas separadas

| Campo | Significado | Quem preenche |
|---|---|---|
| `ano_inicio_observado_censo` | Primeiro ano com EPT federal ativa, calculado **diretamente do painel município-ano**. | Sempre calculado pelo script; nunca lido de um CSV auxiliar. |
| `intermitencia_observada_no_painel` | Se a trajetória de EPT ativa do município tem alguma interrupção interna, calculado do mesmo painel. | Sempre calculado. |
| `ano_evento_institucional` | Ano de criação/autorização/inauguração/início de atividades, quando documentado por fonte institucional. | Só por exceção no JSON; nulo por padrão. |
| `ano_transicao` | Ano em que a exposição começou no meio do calendário (ano parcial). Nunca integra o pré-tratamento limpo. | Só por exceção; nulo quando o mês do início é desconhecido — a incerteza fica explícita, não escondida. |
| `primeiro_ano_completo` | Primeiro ano civil integralmente exposto, quando isso é sustentado por evidência (não apenas por existir um `ano_evento_institucional`). | Só por exceção; permanece nulo para todo município sem validação institucional individual — **nunca copiado automaticamente do Censo**. |
| `ano_coorte_candidata` | Ano usado como `G` na especificação principal candidata. | Para município sem exceção, é a proxy do Censo (`origem_coorte='proxy_censo'`). Para município com evidência institucional, é o `primeiro_ano_completo` validado (`origem_coorte='institucional_validada'`). Quando não há coorte defensável (Brasília, Duque de Caxias, Contagem, Campinas, os três casos intermitentes), fica nulo (`origem_coorte='nao_aplicavel'`). |
| `origem_coorte` | `institucional_validada` / `proxy_censo` / `nao_aplicavel` — de onde vem `ano_coorte_candidata`. | Sempre explícito; nunca ambíguo entre proxy e validação. |
| `anos_sensibilidade` | Anos alternativos documentados para teste futuro de robustez (não a coorte principal). | Lista; ex.: Montes Claros mantém 2012 como sensibilidade mesmo usando 2011 como coorte. |
| `anos_excluir_estimacao` | Anos que não podem ser usados nem como pré nem como pós na especificação principal (tipicamente o ano de transição). | Sempre inclui `ano_transicao`, quando existente. |

O primeiro ano observado no Censo **não** equivale a criação, autorização,
inauguração ou início das aulas. Um município sem validação institucional
individual usa a seguinte semântica, aplicada de forma consistente: `ano_evento_institucional`,
`ano_transicao` e `primeiro_ano_completo` ficam nulos; `ano_coorte_candidata`
é a proxy do Censo; `origem_coorte='proxy_censo'`;
`validacao_institucional_individual=false`.

## Elegibilidade temporal, validação e revisão — três eixos independentes

- `elegivel_temporal_2pre_3pos` / `elegivel_temporal_3pre_3pos`: puramente
  mecânicas, calculadas de `n_pre_limpo` e `n_pos_disponivel`.
- `validacao_institucional_individual`: verdadeiro somente quando o município
  foi pesquisado com fonte externa ao painel (institucional, legislativa ou
  acadêmica) — nunca apenas por ter uma exceção no JSON motivada por auditoria
  interna de dados (`nivel_evidencia='auditoria_local_dados'`, como os casos
  do padrão Escola Agrícola de Jundiaí e a intermitência de Jequié/N.S. da
  Glória/Piracicaba, permanecem com `validacao_institucional_individual=false`).
- `revisao_prioritaria`: independente da validação. **Um município pode não
  ter validação individual e, ainda assim, não estar na fila prioritária de
  revisão** (a maioria dos ~128 municípios sem exceção no JSON está nesse
  caso: proxy sem validação, mas sem problema conhecido).

`candidato_amostra_principal` combina os três eixos com o status curado —
não é um espelho de nenhum deles isoladamente. Em particular, a contagem de
municípios elegíveis por uma regra temporal de janela **não é o tamanho da
população causal principal**: elegibilidade temporal é condição necessária,
não suficiente.

## Tratamento absorvente e trajetórias intermitentes

`tratamento_absorvente=true` significa que, uma vez definida `ano_coorte_candidata`,
o município permanece tratado na série hipotética a partir dali, mesmo que a
flag anual de EPT ativa do Censo desapareça temporariamente depois. Isso só é
permitido quando há `validacao_institucional_individual=true` documentada —
nunca por padrão. Uma trajetória intermitente observada no painel
(`intermitencia_observada_no_painel=true`) sem essa validação **não pode**
ser classificada como absorvente: o cadastro falha a validação antes de
gravar o CSV se isso acontecer.

Isso distingue dois padrões que são frequentemente confundidos:

- **Jequié/BA, Nossa Senhora da Glória/SE e Piracicaba/SP**: a mesma entidade
  (mesmo campus) tem uma lacuna observada de EPT ativa no meio da série, sem
  confirmação institucional externa de fechamento. Ficam `sob_revisao`, fora
  da amostra principal, com `tratamento_absorvente=false` — a especificação
  ingênua absorvente (que ignoraria a lacuna) fica documentada apenas como
  `anos_sensibilidade` para teste futuro, não estimada agora.
- **Montes Claros/MG**: a intermitência agregada no nível municipal vem de
  **duas entidades diferentes** — o Colégio Agrícola Athayde (ligado à UFMG,
  EPT ativa só em 2007–2008) e o Campus Montes Claros do IFNMG (a partir de
  2011). Não é o mesmo campus fechando e reabrindo. Por isso Montes Claros
  mantém `tratamento_absorvente=true` a partir de 2011, com validação
  institucional individual documentando a distinção entre as duas entidades —
  nunca por presumir automaticamente que a série municipal agregada
  representa um único campus.

## Casos especiais

| Município | Situação | `status_populacao_causal` |
|---|---|---|
| **Brasília/DF** | Planaltina preexistente + múltiplas ondas administrativas (uma delas rotulada pelo próprio IFB como "3ª etapa de expansão", distinta da Fase II) sob um único código IBGE. Nenhum ano único é defensável. | `excluido_principal` |
| **Duque de Caxias/RJ** | A UNED que origina o Campus já operava desde 2006, antes do início do painel (2007). Não existe período pré-tratamento observável dentro do painel; `G=2007` seria uma censura à esquerda disfarçada de início. `tratamento_preexistente_painel=true`. | `excluido_principal` |
| **Porto Alegre/RS** | Já havia presença federal EPT ativa contínua desde 2007 (Campus Porto Alegre histórico); a chegada do Campus Restinga em 2010/2011 é uma expansão adicional, não a primeira exposição do município. Mantido como estimando especial documentado, não como candidato principal. | `especial_estimando` |
| **Alcântara/MA e Abaetetuba/PA** | Início em 2008 (ano parcial); apenas 1 ano pré-tratamento dentro do painel (2007). Identidade institucional bem estabelecida, mas insuficiência mecânica de pré-períodos. | `candidato_com_ressalva` (inelegível à janela mínima) |
| **Jequié/BA, N.S. da Glória/SE, Piracicaba/SP** | Lacuna observacional de EPT ativa no mesmo campus, sem validação institucional de fechamento. | `sob_revisao` |
| **Montes Claros/MG** | Ver seção anterior — duas entidades distintas, não reversão operacional. | `candidato_com_ressalva` |
| **Sobral/CE** | Três fatos distintos e complementares (criação administrativa da UnED em 2008, transformação legal em Campus em dez/2008, inauguração oficial em set/2009) registrados separadamente, sem misturar seus significados; nenhuma data foi lida em fonte primária nesta revisão. | `candidato_com_ressalva` |
| **Campinas/SP** | Atividades documentadas a partir de agosto de 2013, mas sem confirmação de ano civil completo (dificuldades operacionais registradas até a sede definitiva de 2019). | `sob_revisao` |
| **Cabedelo/PB** | Identidade do polo (Campus Cabedelo) razoavelmente estabelecida; timing exato não confirmado em fonte primária. | `candidato_com_ressalva` |
| **Contagem/MG** | Operação provisória documentada desde 2012; nenhum ano civil plenamente estabilizado confirmado antes da sede própria de 2019. | `sob_revisao` |
| **Padrão Escola Agrícola de Jundiaí (RN)** | Cinco municípios do IFRN com um padrão de correspondência recorrente na base MEC/SISTEC; sem pesquisa institucional externa individual nesta revisão (evidência = auditoria local de dados). | `candidato_com_ressalva` |

## Tabela cruzada (gerada, não hardcoded)

O script expõe `build_status_crosstab(registry)`, que cruza `status_populacao_causal`,
`elegivel_temporal_2pre_3pos`, `elegivel_temporal_3pre_3pos`,
`candidato_amostra_principal`, `validacao_institucional_individual` e
`revisao_prioritaria`, sempre a partir do cadastro atual. Nenhuma contagem é
mantida manualmente neste documento porque poderia divergir do CSV — para
ver os números correntes, execute o script (`print_summary`) ou leia
`outputs/diagnostics/cadastro_causal_tratamento_fase_ii.csv` diretamente. Os
testes (`tests/test_constroi_cadastro_causal_fase_ii.py`) verificam que a
soma das linhas dessa tabela sempre bate com os 147 municípios oficiais.

## Proveniência das decisões institucionais

Cada exceção em `src/excecoes_institucionais_fase_ii.json` que reivindica
`validacao_institucional_individual=true` é obrigada a trazer ao menos uma
entrada em `fontes`, cada uma com: `url_ou_caminho`, `titulo`, `orgao`,
`data_evidencia_ou_acesso`, `nivel_evidencia`, `descricao_factual` e
`campo_sustentado`. Nenhuma fonte é inventada: quando a evidência disponível é
insuficiente (por exemplo, uma portaria citada por fonte secundária mas nunca
lida diretamente no Diário Oficial), isso fica registrado explicitamente no
próprio nível de evidência (`indicio_secundario`) e no texto de
`descricao_factual`, e os campos não comprovados (datas, coortes) permanecem
nulos em vez de receber um valor de conveniência.

## Validações executadas antes de gravar o CSV

**Sobre o painel** (reaproveitando a validação já existente em
`src/auditoria_timing_tratamento.py`, aplicada por município, não apenas
globalmente):

- exatamente 1.911 linhas (147 × 13);
- exatamente 147 códigos municipais únicos;
- chave município-ano única;
- exatamente 13 observações para cada um dos 147 municípios;
- anos exatamente iguais a 2007–2019 para cada código;
- nenhum código fora da lista oficial e nenhum município oficial sem
  observação.

Se `outputs/diagnostics/auditoria_timing_tratamento.csv` existir (ele é
ignorado pelo Git e pode faltar num clone limpo), o script confere,
opcionalmente, se o cálculo direto do painel bate exatamente com o CSV — e
falha com uma mensagem clara em caso de divergência, sem nunca depender
desse CSV como fonte obrigatória.

**Sobre o JSON de exceções**: JSON válido; schema e campos obrigatórios;
tipos; código IBGE existente na lista oficial; valores permitidos de
`status_populacao_causal`, `origem_coorte` e `nivel_evidencia`; anos dentro de
limites plausíveis (2006–2019); coerência cronológica entre evento, transição
e primeiro ano completo; coerência entre `tratamento_preexistente_painel` e
ausência de coorte dentro do painel; coerência entre `anos_excluir_estimacao`
e `ano_transicao`; e proveniência mínima sempre que uma validação
institucional é reivindicada.

**Sobre o cadastro final**: as mesmas 147 linhas, únicas e não nulas;
`ever_treated=true` e `pode_ser_controle=false` para todas; nenhum município
excluído, especial, sob revisão, com ressalva ou institucionalmente
inelegível pode ser `candidato_amostra_principal`; nenhum candidato à amostra
principal pode estar sem coorte ou sem elegibilidade temporal mínima;
qualquer não-candidato tem `motivo_exclusao_principal` preenchido; trajetória
intermitente só pode ser tratada como absorvente com validação institucional
documentada; e o tratamento absorvente, quando construído, é monotônico.

## Fora do escopo desta etapa

Matching, common support, construção definitiva de controles, ATT, event
study, Callaway–Sant'Anna, `did_multiplegt_dyn`, HonestDiD, download de novos
dados, alteração de Parquets ou qualquer estimação causal. O cadastro é um
cadastro causal **preliminar e auditável**, não uma autorização para estimar
efeitos.
