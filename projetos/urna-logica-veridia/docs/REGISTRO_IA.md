# Registro de Uso de IA

Projeto: VERÍDIA — O Enigma da Urna (EP Urna Lógica, EDAA, IPT).
Ferramentas: Claude Code (modelo Claude Opus 5.5), nas rodadas 1–3,
e Codex, na rodada 4.
Sessões: Rodada 1 (fundação técnica), Rodada 2 (motor das cinco fases) e
Rodada 3 (interface NiceGUI), em 05/11/2026; Rodada 4 (conferência oficial
e preparação de publicação), em 05–06/11/2026.
Entre as rodadas, o aluno revisou o código externamente e reexecutou os 89 testes.

O código foi gerado pela IA a partir de uma especificação escrita pelo
aluno, organizada em 7 blocos. O enunciado oficial (`EP Urna Lógica.pdf`)
**não estava disponível no workspace nas rodadas 1–3**: a implementação
seguiu o resumo de requisitos do prompt. Na rodada 4, o aluno indicou a
pasta externa da disciplina, o PDF foi lido e a conferência técnica foi
registrada em `REQUISITOS_EP.md`. O aluno continua responsável pela revisão
final, pela compreensão do código e pela curadoria humana exigida no EP.

---

## Rodada 1 — Contribuições por bloco

### Bloco 1 — Estrutura inicial
- **Objetivo:** organizar o projeto e o ambiente.
- **Abordagem:** pacote `veridia/` com subpacotes por responsabilidade;
  `.venv` própria (Python 3.11.9, já que o 3.13 instalado é RC); apenas
  `pytest` instalado; NiceGUI separado em `requirements-interface.txt` (não
  instalado); `pyproject.toml` com a configuração do pytest.
- **Validação:** `pytest --version` dentro da `.venv`.

### Bloco 2 — Modelagem do domínio
- **Objetivo:** registros, evidências, estado, mapa, gerador e validações.
- **Abordagem:** dataclasses imutáveis; `EstadoJogo.chave()` como tupla
  canônica ordenada; gerador com `random.Random(seed)` isolado; opções de
  voto como códigos fictícios (`OPC-A`…`OPC-E`, `BRANCO`, `NULO`).
- **Validação:** testes de reprodutibilidade, de validação e de equivalência
  e distinção de chaves (`tests/test_modelos.py`).

### Bloco 3 — Estruturas de dados
- **Objetivo:** fila, pilha, lista ligada e AVL implementadas do zero.
- **Abordagem:** nós encadeados; lista **duplamente** ligada (justificativa
  no guia, seção 3.3); AVL com altura armazenada, as quatro rotações e
  `esta_balanceada()` para auditoria. O grafo (Bloco 5) foi feito aqui por
  ser dependência do `Mapa`.
- **Validação:** testes de vazio, duplicatas, operações inválidas, quatro
  casos de rotação e 2.000 inserções aleatórias verificando o balanceamento.

### Bloco 4 — Ordenação
- **Objetivo:** Bubble, Merge e Quick com métricas e chave composta.
- **Abordagem:** interface comum `(ordenado, métricas)`; entrada nunca
  alterada; métricas com definição única para os três algoritmos.
- **Mudança durante a sessão:** o Quick Sort começou com partição em 3 vias
  (Dijkstra). O experimento mostrou 38.520 comparações em entrada ordenada
  contra 16.056 na aleatória (n = 1000), e a partição foi trocada por Hoare
  com mediana de três (≈ 14.000 nos três cenários). Também passaram a ser
  contadas como movimentação as cópias do Merge Sort para o vetor auxiliar.
- **Validação:** todos os casos-limite pedidos, estabilidade (Bubble/Merge),
  métricas conferidas com fórmulas fechadas (n−1 e n(n−1)/2) e um
  experimento que confere se os três algoritmos produzem a mesma ordem.

### Bloco 5 — Grafo, BFS e DFS
- **Objetivo:** mapa com ≥ 8 vértices e ≥ 10 conexões; buscas sobre o
  estado completo.
- **Abordagem:** regras puras em `jogo/regras.py`; motor genérico em
  `busca/solver.py` (recebe `sucessores`, `objetivo` e `chave`).
- **Mudança durante a sessão:** a primeira versão do mapa deixava o Arquivo
  acessível pela Ponte sem o lacre, o que tornava a porta do Arquivo
  inútil. A própria BFS revelou o problema. A conexão Arquivo–Ponte ganhou
  a porta `passagem_ponte`.
- **Validação:** toda solução é reexecutada pelas regras; a otimalidade da
  BFS é conferida por enumeração exaustiva; o cenário sem solução (energia
  14) é testado.

### Bloco 6 — AVL no solver
- **Abordagem:** uma única AVL `chave → (pai, ação, estado)` serve de
  conjunto de visitados e de árvore de pais para reconstruir o caminho.
- **Validação:** nenhum estado é expandido duas vezes; os repetidos são
  contados; a AVL fica balanceada e com altura ≤ 1,45·log₂ n; estados na
  mesma posição com pistas diferentes coexistem; a demo mostra
  equivalentes sendo rejeitados.

### Bloco 7 — Testes e documentação
- 89 testes pytest passando (`python -m pytest`, ≈ 1 s).
- `README.md`, `docs/GUIA_TECNICO.md` e este registro.

---

## Rodada 2 — Motor das cinco fases

Especificação do aluno: sessão e progressão, as cinco fases, recursão,
métricas, testes, documentação, `CLAUDE.md` e exportação em ZIP. O PDF do
enunciado continuava fora do workspace.

| Etapa | Abordagem | Validação |
|---|---|---|
| Progressão | `jogo/sessao.py`: selos, desbloqueio sequencial, histórico em lista ligada, ações por nome restritas a `Fase.ACOES` | `test_sessao.py` |
| Fase 1 | reutiliza `ordenacao.py`; `verificar_ordenacao` sem gabarito (pares vizinhos + AVL por id) | `test_fase1_arquivo.py` |
| Fase 2 | Fila/Pilha/ListaLigada reais; desfazer por retratos na pilha de histórico; solução descoberta por BFS aplicando os próprios métodos de ação | `test_fase2_triagem.py` |
| Fase 3 | controlador fino sobre `regras.py` e `solver.py`; desfazer de movimento | `test_fase3_mapa.py` |
| Fase 4 | mesma `ArvoreAVL`; sequência A…H escolhida para gerar rotações à esquerda e à direita; árvores antes/depois serializadas | `test_fase4_cofre.py` |
| Fase 5 | reconfere o estado atual das fases; solver sempre executado; evidências organizadas pelo algoritmo de ordenação escolhido; relatório → dict/JSON | `test_fase5_auditoria.py` |
| Recursão e métricas | `busca_profundidade_recursiva` com rastro; `tempo_segundos`, `tamanho_max_fronteira`, `custo_caminho`, `arvore_busca()`; nenhuma assinatura existente alterada | `test_solver_recursivo.py` + os 89 testes antigos |
| Entrega | `scripts/exportar_projeto.py` (inclusão + exclusão, conferência do ZIP), `CLAUDE.md`, `REQUISITOS_EP.md`, `CONTINUIDADE.md`, demo `demo_fases` | `test_exportacao.py`, `test_demos.py` |

Problemas encontrados e corrigidos durante a rodada:
- Na Fase 5, uma trilha manual incompleta ficava registrada com origem
  "manual" e mensagem de "solver". A lógica foi reescrita: a trilha manual
  só é usada se for revalidada e vitoriosa; caso contrário, o caminho de
  referência é o do solver.
- O teste de rastro recursivo foi escrito primeiro com a ordem de visita
  errada (esquecia o vértice 2, que falha antes do objetivo). A expectativa
  foi corrigida após conferência manual do rastro.
- O feedback da Fase 1 exibia `datetime.time(...)`. A chave passou a ser
  formatada como `(zona, seção, HH:MM:SS)`.

Resultado: 162 testes aprovados (89 antigos + 73 novos).

## Rodada 3 — Interface visual NiceGUI

Especificação do aluno: interface completa para as cinco fases, menu com as
cinco opções, Modo Resolver, instruções, resultados, exportação do relatório,
testes de interface, `AGENTS.md` e ZIP limpo. Foi usada a skill
`frontend-design` para definir a identidade visual (paleta escura
azul/grafite com verde-água; trilho de cinco selos hexagonais como elemento
central; fontes do sistema, para funcionar offline).

| Item | Abordagem | Validação |
|---|---|---|
| Ambiente | NiceGUI 4.0.0 e pytest-asyncio instalados na `.venv` existente via `requirements-interface.txt` | `pip`, suíte completa |
| Arquitetura | página raiz + `ui.sub_pages`; `GerenciadorSessoes` por id de navegador; `ContextoTela.agir` como única porta para as fases | protótipo testado antes da implementação; `test_sessoes_independentes_entre_navegadores` |
| Telas | uma por rota em `interface/telas/`; componentes comuns em `componentes.py` | 14 testes com usuário simulado |
| Visualizações | `svg.py` desenha mapa e AVL a partir dos dados reais (sem árvore ou grafo fictício) | `test_interface_modulos.py` compara o SVG com o motor |
| Resolver | instâncias novas dos desafios; uma execução da busca real; passo a passo sobre `ordem_visita` | `test_resolver_executa_busca_real_e_passo_a_passo` |
| Exportação | JSON e HTML imprimível autocontido | `test_exportacao_json_e_html` |
| Motor | única mudança: `FaseCentralTriagem.resolver(algoritmo)` e `sugerir_solucao(algoritmo="BFS")`, compatíveis com a API anterior | os 162 testes antigos continuam passando |

Problemas encontrados e corrigidos:
- No NiceGUI 4, `refresh()` é assíncrono. Mensagens guardadas com `pop`
  eram consumidas pela renderização errada quando havia dois cliques
  seguidos. O teste da Fase 2 revelou o problema; a causa foi confirmada
  contando renderizações. Correção: `get` e limpeza explícita ao entrar na
  tela ou reiniciar a fase.
- `ui.on` registra o handler no layout do cliente. Chamá-lo dentro da tela
  acumularia handlers a cada redesenho (movimentos duplicados). O evento do
  mapa passou a ser registrado uma vez na raiz.
- Verificação visual com Chrome em modo headless (capturas de tela das
  telas Início, Jogar, Fases 1 a 5, Resolver e Instruções) revelou: botões secundários
  preenchidos pela classe de cor do Quasar, grade do menu com metade da
  largura, siglas redundantes e nomes cortados no mapa, e árvore AVL
  ampliada demais. Todos corrigidos e recapturados. As telas Resultados e
  Sair não foram capturadas; elas são cobertas pelos testes
  com usuário simulado. As capturas usaram um lançador temporário, fora do
  projeto, que prepara sessões em estados intermediários; nenhum arquivo do
  projeto foi alterado para isso.
- Na tela da Fase 3, uma sugestão do solver continuava visível depois de
  um movimento. Ela passou a ser descartada quando o estado muda.

Resultado: 183 testes aprovados (162 antigos + 21 de interface).

## Rodada 4 — Conferência oficial e preparação para GitHub

Pedido do aluno: conferir o PDF, executar os 183 testes, verificar a aplicação,
preparar somente este projeto para o primeiro commit, configurar CI simples e
identificar pendências obrigatórias. Em 06/11, o aluno informou a pasta do
enunciado e confirmou publicação no repositório atual `data-science-projects`.

| Ferramenta/data | Objetivo | Contribuição da IA aproveitada | Alterações da IA nesta rodada | Validação |
|---|---|---|---|---|
| Codex, 05–06/11/2026 | Conferir requisitos reais | Leitura integral do PDF oficial (20 páginas), rastreabilidade RF01–RF12 e separação de código, relatório de partida e entrega acadêmica | Atualização de `REQUISITOS_EP.md` | Conferência das seções 3–12, 14.4–16 e 19 com arquivos e testes |
| Codex, 06/11/2026 | Corrigir somente erro demonstrado | Identificou mutação parcial em conexão bidirecional recusada por conflito com aresta inversa dirigida | Validação antecipada em `grafo.py` e teste de regressão | Teste falhou antes da correção; suíte completa passou depois |
| Codex, 05–06/11/2026 | Verificar interface e exportação | HTTP nas rotas principais e simulação do evento do mapa e downloads | Ampliação de dois testes existentes em `test_interface_app.py` | Um movimento por evento; Resultados e downloads JSON/HTML com HTTP 200 e conteúdo esperado |
| Codex, 06/11/2026 | Preparar publicação restrita | Exclusões locais e configuração simples de pytest para o monorepo | `.gitignore`, `scripts/pytest-github-actions.yml`, documentação e manifesto de seleção | Revisão dos nomes/conteúdo candidatos; YAML estruturalmente validado; GitHub ainda não executado |
| Codex, 06/11/2026 | Validar evidência experimental | Execução de ordenação e buscas existentes, sem novos modelos ou funcionalidades | Registro dos cenários, ambiente e limitações | Seed 2026, n=100/500/1000, energias 18/15/14, soluções reproduzidas pelas regras |
| Codex, 06/11/2026 | Preparar o relatório acadêmico solicitado no anexo | Organização em dez seções, figuras textuais de AVL/árvore de busca, tabela de sete interações e limitações de autoria | `RELATORIO_ACADEMICO.md`, PDF e `METRICAS_RODADA4.json` | Cinco repetições: 135 ordenações e 45 buscas; extração de texto e renderização do PDF para inspeção visual |
| Codex, 06/11/2026 | Completar o pacote de entrega | Inclusão por nome de PDF acadêmico, métricas JSON e YAML de CI, preservando exclusão do enunciado | Exportador e teste de empacotamento ampliados | Teste falhou antes da alteração e a suíte passou com 185 testes depois |

Essa tabela registra **trabalho da IA**. Não substitui a tabela da seção 14.4
do PDF: o aluno deve confirmar e acrescentar o campo de alterações feitas
por ele e sua validação humana em pelo menos cinco interações reais. Não há
evidência nesta sessão para atribuir ao aluno revisões que a IA executou.

Resultado observado: suíte original com 183 aprovados (23,65 s); depois da
regressão do grafo e dos testes ampliados, 184 aprovados (19,28 s). Com o
novo teste de inclusão dos artefatos acadêmicos, **185 aprovados (25,08 s)**.
Após incluir `.gitattributes` no pacote, a suíte permaneceu com **185
aprovados (25,14 s)**. O atributo binário protege o PDF contra conversão
de quebras de linha no checkout Git; o teste do pacote verifica a inclusão
desse arquivo de configuração.
Não foram instalados pacotes, substituídos algoritmos por bibliotecas,
alterados dados brutos, feitos commits ou push.

Limitações da conferência: controle do Chrome bloqueado por não determinar
a URL atual com segurança; clique físico no SVG e impressão em PDF ainda
precisam ser verificados por pessoa. HTTP/simulação não foram considerados
prova de layout ou impressão. Uma tentativa de executar a simulação por
stdin encontrou conflito do modo script do NiceGUI; a validação foi feita
no pytest, que é o caminho já adotado pelo projeto. A extração inicial do
PDF teve problema de codificação do caminho no pipe PowerShell e foi
repetida com descoberta de caminho e saída UTF-8, sem alterar o original.

O workflow inicialmente ficou preparado dentro do projeto por limite de
escopo. O pedido anexado posteriormente autorizou sua preparação na raiz:
foi criado `.github/workflows/veridia-pytest.yml`, somente para o VERÍDIA.
A execução no GitHub depende da futura publicação e ainda não foi observada.

O anexo também pediu relatório acadêmico e estratégia segura de publicação.
Foram preparados Markdown editável e PDF de 13 páginas, sem instalar pacotes.
O ambiente local já dispunha de pypdf e pypdfium2; a geração utilizou texto
vetorial e fontes PDF padrão, e a inspeção usou imagens renderizadas.
O arquivo original da professora permaneceu externo, apenas lido.

Git: sparse checkout ativo, projeto fora da seleção e branch atual com 37
commits além da referência local de `origin/main`. Não foi feita troca de
branch nem alteração do sparse checkout. A proposta é `feat/veridia-entrega`
derivada da main atualizada, em worktree isolada, após aprovação. A consulta
Git remota falhou por Schannel sem credenciais; o conector GitHub confirmou
`main` como branch padrão. Não houve commit nem push.

## Pontos históricos que exigiam revisão humana (rodadas 1–3)

Situação atual: a conferência técnica do item 1 foi executada na rodada 4.
A cobertura simulada do item 9 foi ampliada, mas o clique físico continua
pendente. Os demais registros abaixo preservam a origem das decisões e
não são novas funcionalidades obrigatórias a implementar nesta rodada.

1. **Conformidade com o enunciado em PDF.** Conferir nomes exigidos,
   formato de entrega, as cinco fases e as métricas solicitadas.
   Ver `docs/REQUISITOS_EP.md`.
2. **Coleta automática de pistas:** mantida por decisão do aluno (Rodada 2).
3. **Energia na chave do estado:** mantida por decisão do aluno. Efeito
   conhecido: a DFS oscila (Praça ↔ Biblioteca) antes de achar a solução.
4. **Critério de otimalidade:** a BFS minimiza movimentos, não energia.
   Dijkstra/A* ficaram fora do escopo por decisão do aluno.
5. **Regras de game design da Rodada 2** (decisões da IA, a confirmar):
   capacidade 2 da pilha na Fase 2; selos permanentes após reinício;
   desbloqueio estritamente sequencial; o solver da Fase 3 só sugere (não
   joga pelo usuário); a Fase 4 exige uma rotação observada; os oito
   estados A…H da Fase 4.
6. **Definição de "movimentação"** nas métricas de ordenação (escritas,
   troca = 2). Confirmar se a professora espera outra convenção (por
   exemplo, troca = 3 atribuições).
7. **Narrativa e dados do mapa** (nomes, pistas, custos, energia 18) são
   provisórios e precisam de revisão de game design.
8. **Interface (Rodada 3), decisões da IA a confirmar:** textos de
   instruções e narrativa; coordenadas de desenho do mapa (`svg.py`);
   cenários do Resolver (energia 18, 15 e 14); a partida fica guardada só
   em memória do servidor; o PDF do relatório é obtido pelo "Imprimir" do
   navegador a partir do HTML (não há gerador de PDF próprio).
9. **Teste em navegador real pela pessoa usuária:** os testes de interface
   usam usuário simulado, e as capturas foram feitas em Chrome headless.
   Interações de mouse no SVG (clique nos locais do mapa) não são
   exercitadas pelos testes automáticos.
10. **Revisar a didática do `GUIA_TECNICO.md`** antes de usá-lo na
   apresentação: os números citados vêm da execução desta sessão (seed
   2026).

## Próximas tarefas sugeridas

Ver `docs/CONTINUIDADE.md` (interface NiceGUI, menu, gravação do relatório
e conferência com o PDF).
