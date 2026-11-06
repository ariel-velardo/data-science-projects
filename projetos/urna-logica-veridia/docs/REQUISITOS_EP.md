# Requisitos do EP × Implementação

Conferência em 06/11/2026 contra **EP Urna Lógica.pdf**, 20 páginas, lido
integralmente na pasta externa da disciplina indicada pelo aluno. O original
não foi movido, editado nem copiado para o repositório.

SHA-256: `D9EAE1E7D40D3CB166A1ABF5FE799E142FD6D946A158CF34C87D881F266501D0`.

Situações: **atendido** = implementação/evidência técnica confirmada;
**parcial** = existe trabalho, mas falta uma validação ou componente de entrega;
**pendente** = entrega ou atividade ainda não realizada. Evidência ausente não
foi tratada automaticamente como código ausente.

## Matriz oficial de rastreabilidade

Caminhos de testes abaixo são relativos a `tests/`; os demais são relativos
à raiz do projeto. A conferência do código não substitui revisão humana nem
demonstração em sala.

| Requisito do PDF | Página / seção | Arquivo ou módulo responsável | Situação | Evidência | Ação necessária |
|---|---|---|---|---|---|
| RF01: Jogar, Resolver, Instruções, Resultados, Sair | p.12, §11 | `veridia/interface/app.py`, `telas/inicio.py` | atendido | `test_interface_app.py::test_menu_inicial_com_cinco_opcoes` e navegação | Nenhuma de código |
| RF02: iniciar/reiniciar fase e consultar estado | p.12, §11; p.3, §3 | `veridia/jogo/sessao.py`, `veridia/fases/` | atendido | `test_sessao.py`, testes das fases e reinício na interface | Nenhuma de código |
| RF03: registros fictícios reproduzíveis | p.12, §11; p.5, §5.2 | `veridia/dados/gerador_registros.py`, `fase1_arquivo.py` | atendido | `test_modelos.py`, `test_fase1_arquivo.py`: seed, ids e validação | Nenhuma |
| RF04: três ordenações selecionáveis | p.12, §11; p.5, §5.2 | `veridia/algoritmos/ordenacao.py`, `telas/fase1.py` | atendido | `test_ordenacao.py`, teste de escolha/critério da Fase 1 | Nenhuma |
| RF05: fila, pilha e lista próprias | p.12, §11; p.6, §6.2 | `veridia/estruturas/`, `fase2_triagem.py` | atendido | `test_fila_pilha.py`, `test_lista_ligada.py`, `test_fase2_triagem.py` | Nenhuma |
| RF06: mapa como grafo, conexões válidas | p.12, §11; p.7, §7.1 | `grafo.py`, `mapa_veridia.py`, `jogo/regras.py` | atendido | 9 vértices, 12 conexões; `test_grafo.py`, `test_regras.py` | Conferir clique físico no SVG como validação prática adicional |
| RF07: BFS/DFS com visita e caminho | p.12, §11; p.8, §7.2 | `veridia/busca/solver.py`, `telas/resolver.py` | atendido | Ordem conhecida em grafo pequeno e caminhos reproduzidos em `test_solver.py` | Nenhuma |
| RF08: estados completos sem expansão repetida | p.12, §11; p.8–9, §7.3/8.1 | `modelos/estado.py`, `busca/solver.py` | atendido | Chave inclui posição/pistas/portas/energia; testes de chaves e de AVL no solver | Nenhuma |
| RF09: indexação por AVL | p.12, §11; p.9, §8.1 | `estruturas/arvore_avl.py`, `fase4_cofre.py` | atendido | `test_arvore_avl.py`, `test_fase4_cofre.py` | Nenhuma |
| RF10: tempo, estados, caminho e custo do solver | p.12, §11; p.18, §15.1 | `ResultadoBusca`, interface e demos | atendido | `test_solver_recursivo.py`, `METRICAS_RODADA4.json` | Revisar interpretação no relatório |
| RF11: ações manuais com feedback | p.13, §11 | `SessaoJogo`, controladores e telas | atendido | Integração das cinco fases e ações inválidas em `test_interface_app.py` | Demonstração em sala ainda necessária |
| RF12: relatório/log de IAG | p.13, §11; p.17, §14.4 | `REGISTRO_IA.md`, §9 do relatório acadêmico | parcial | Histórico preservado e sete interações recuperadas, com autoria das mudanças da IA explícita | Aluno completar suas alterações/decisões e validação pessoal em pelo menos cinco interações |
| Cinco fases integradas com objetivos e selos | p.3–4, §3–4 | `veridia/fases/`, `jogo/sessao.py` | atendido | `test_sessao.py`, cinco fases e auditoria na simulação | Nenhuma de código |
| Fase 1: registro próprio, vetor, geração e embaralhamento | p.4–5, §5.1–5.2 | `modelos/registro.py`, gerador e Fase 1 | atendido | Registro imutável; lista indexada; seed e validação de ids | Nenhuma |
| Fase 1: chave composta e integridade do lote | p.5, §5.3–5.4 | `fase1_arquivo.py`, `ordenacao.py` | atendido | `test_fase1_arquivo.py`: sem perda/duplicação/alteração, feedback de primeira inversão | Nenhuma |
| Comparar ordenação em tamanhos diferentes | p.5, §5.2; p.18, §15.1 | `demos/experimento_ordenacao.py`, relatório §8.2 | atendido | n=100/500/1000; três cenários; cinco repetições por combinação | Aluno revisar conclusões |
| Fase 2: FIFO/LIFO, operações, lista dupla, desfazer | p.6–7, §6.2–6.4 | estruturas próprias e `fase2_triagem.py` | atendido | Métodos mínimos, custódia, arquivo e desfazer; testes de estruturas vazias e ordem | Nenhuma |
| Regras reais, sem sequência fixa | p.7, §6.3; p.14, etapa 11 | triagem, regras do mapa e solver | atendido | Sucessores da triagem usam métodos de ação; caminhos do mapa reexecutados pelas regras | Nenhuma |
| Mapa próprio com bifurcação e alternativa | p.7, §7.1 | `dados/mapa_veridia.py` | atendido | 9 locais, 12 conexões e portas; `test_mapa_veridia_valido_e_com_tamanho_minimo` | Nenhuma |
| Condições de pistas/portas formalizadas | p.8–9, §7.4–7.5 | `jogo/regras.py`, mapa | atendido | Testes com/sem pistas, energia insuficiente e caminhos válidos; energias 18/15/14 | Nenhuma |
| Explicar BFS e distinguir número de arestas de custo | p.8, §7.2 | guia §6 e relatório §6/8 | atendido | BFS minimiza movimentos no espaço de estados; ausência de garantia de menor energia explícita | Aluno demonstrar entendimento |
| AVL: quatro rotações, altura, fatores, busca e chave | p.9, §8.1 | AVL própria e Fase 4 | atendido | Testes das quatro rotações e balanceamento; metadados reais das árvores | Nenhuma |
| Sequência AVL, desenhos antes/depois, buscas existente/inexistente no relatório | p.10, §8.3 | relatório §5.1 e JSON de métricas | atendido | A/B/D, desenho e árvore transitória identificada como reconstrução didática; buscas verificadas | Revisão acadêmica pelo aluno |
| Fase 5: integração, solver e relatório de consistência | p.10, §9.1 | `fase5_auditoria.py`, `telas/fase5.py` | atendido | `test_fase5_auditoria.py`; auditoria atualiza resultado e verifica reinício posterior a selo | Nenhuma |
| Comparar BFS/DFS em pelo menos dois cenários | p.10, §9.1 | Resolver e relatório §8.3 | atendido | Energias 18/15/14, métricas de cinco repetições e caminhos revalidados | Revisão das conclusões pelo aluno |
| Recursão, caso-base, retorno e árvore de busca | p.10–11, §9.2/10 | solver; relatório §6.1 | atendido | `test_solver_recursivo.py`, `arvore_busca()` e exemplo real pai/filho/ação | Aluno demonstrar os conceitos |
| Reutilizar ordenação no relatório final do jogo | p.11, §9.3 | `fase5_auditoria.py` | atendido | Evidências ordenadas pelo algoritmo escolhido, com métricas; testes da Fase 5 | Nenhuma |
| Modularidade, inválidos, reprodutibilidade e execução local | p.13, §12 | arquitetura, requirements e README | atendido | Motor padrão Python, NiceGUI local, pytest e seed; sem serviços pagos | Confirmar execução na máquina de apresentação |
| Casos mínimos de teste e integração | p.17, §15 | `tests/` | atendido | 183 originais aprovados; regressões/adaptações elevaram a suíte a 185 | Nenhuma de código identificada |
| Métricas de ordenação, busca, AVL e protocolo experimental | p.18, §15.1 | JSON de métricas e relatório §8 | atendido | 135 ordenações e 45 buscas, ambiente, cinco tempos brutos e medianas | Revisão acadêmica; não generalizar benchmark local |
| Código completo, geração e instruções | p.18, §16 | `README.md`, `veridia/`, exportador | atendido | Geração por seed, comandos de execução e ZIP com inclusões explícitas | Conferir ZIP final e executar antes da apresentação |
| Relatório técnico acadêmico PDF | p.18, §16/16.1 | `RELATORIO_ACADEMICO.md` e `.pdf` | parcial | Dez seções, tabelas medidas, árvores, complexidades e limitações preparados | Identificação/autoria, considerações pessoais e revisão final do estudante |
| Demonstrar jogo manual e solver em sala | p.18, §16 | aplicação e roteiro no relatório/README | pendente | Simulação completa e demos existem; apresentação em sala não ocorreu nesta sessão | Aluno realizar a demonstração |
| Critérios de avaliação | p.19, §17 | relatório §10.2 | atendido | Pesos transcritos: 20/20/20/20/15/15/10, soma 120 no PDF | Não normalizar sem esclarecimento da professora |
| Checklist final e responsabilidade técnica humana | p.20, §19–20 | relatório, registro IAG e matriz | parcial | Cobertura técnica confirmada; limites de validação declarados | Estudante revisar, compreender e assumir as decisões |

## Evidências da rodada

- PDF lido integralmente; somente informações efetivamente presentes foram
  usadas como exigências. Não foram implementados bônus da seção 18.
- Testes: 183 originais aprovados (23,65 s); 184 após regressão do grafo e
  ampliação dos testes de interface (19,28 s); 185 com empacotamento dos novos
  artefatos (25,08 s). Nenhum teste removido ou desabilitado.
- Defeito corrigido: `Grafo.adicionar_aresta` valida a aresta inversa antes de
  inserir a primeira direção. O teste falhou antes e passou após a correção.
- Servidor em `127.0.0.1:8090`: 11 rotas principais responderam HTTP 200.
  Isso comprova disponibilidade, não a execução de interações visuais.
- Simulação: partida integrada, evento do SVG despachado na raiz com exatamente
  um movimento, Resultados, JSON consistente e HTML com estilo de impressão;
  downloads HTTP 200. Os botões equivalentes continuam testados.
- O controle do Chrome foi bloqueado por não determinar a URL atual com
  segurança. Clique físico no mapa, revisão visual de Resultados e impressão
  do HTML continuam sem validação nesta rodada.
- `METRICAS_RODADA4.json`: seed 2026, tamanhos 100/500/1000, três entradas,
  cinco repetições; buscas em energias 18/15/14, cinco repetições. Saídas de
  ordenação equivalentes; todos os caminhos encontrados reproduzidos pelas
  regras. Com energia 14, os três algoritmos esgotaram 249 estados sem solução.
- Ambiente: Python 3.11.9, Windows build 26200, NiceGUI 4.0.0, pytest 9.2.0,
  pytest-asyncio 1.4.1.post1. Não foram instalados pacotes. Os tempos medidos
  incluem instrumentação e não representam benchmark de produção.

## Pendências obrigatórias restantes

1. **Alto, bloqueador da entrega acadêmica completa:** revisão do relatório
   preparado pelo aluno, identificação/autoria e considerações pessoais.
   O PDF e o Markdown existem; não são considerados homologados por sua geração.
2. **Alto, bloqueador da curadoria:** complementar em pelo menos cinco
   interações as alterações/decisões e a validação pessoal do estudante,
   conforme §14.4. Não atribuir ao aluno alterações executadas pela IA.
3. **Alto, atividade de entrega:** demonstrar partida manual e solver em
   sala, conforme §16. Confirmar que a professora consegue executar e jogar.

**Médio, validação prática pendente:** clique físico no SVG, visual de
Resultados e abertura/impressão do relatório de partida. O teste com pessoa
que não programou o jogo é recomendado no roteiro do §13; não foi convertido
em funcionalidade obrigatória ausente.

GitHub e CI atendem ao pedido desta rodada, mas não são entregáveis
acadêmicos expressamente exigidos pelo enunciado. Não foi identificada
necessidade de nova funcionalidade obrigatória após a correção concreta.
