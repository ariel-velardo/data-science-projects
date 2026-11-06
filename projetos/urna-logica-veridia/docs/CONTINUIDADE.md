# Continuidade do Desenvolvimento

Última atualização: 06/11/2026 — **Rodada 5**, redesign visual inspirado no IPT
(branch local `feat/veridia-redesign-ipt`, sem commit).

## Rodada 5 — redesign visual (resumo)

- Worktree isolada: `C:/GitHub/data-science-projects-veridia-redesign`,
  branch `feat/veridia-redesign-ipt` criada a partir de `f42506a`
  (`feat/veridia-entrega`). O sparse checkout DESTA worktree foi ajustado
  para `.github` + `projetos/urna-logica-veridia` (as outras worktrees não
  foram tocadas). Sem commit, push ou merge.
- Direção "prancha técnica de auditoria": papel claro + pranchas azul-profundo;
  paleta `#0B2038 #163E63 #1679AC #76C8EC #ECF6FB`; âmbar/vermelho só
  semânticos; Bahnschrift + Segoe UI (offline). Tema Quasar agora é claro
  (`ui.dark_mode(False)`); selects dentro de pranchas usam `props("dark")`.
- Arquivos alterados: `interface/estilos.css`, `app.py` (barra), `componentes.py`,
  `svg.py` (mapa novo, AVL com h/f coloridos e nós deslocados, perfil de
  ordem), todas as telas. Novo: `interface/rastro_ordenacao.py`.
- Marcas (`mark`) e textos verificados pelos testes foram preservados.
  O mapa mantém `emitEvent('veridia_local', ...)`, "Porta " apenas em portas
  trancadas, `polyline` apenas para caminho sugerido; a AVL mantém
  `<line>` só para arestas.
- Cuidado NiceGUI: timers de "Reproduzir" (Fase 1 e Resolver) ficam FORA do
  `ui.refreshable` que redesenham, senão o próprio timer é destruído a cada passo.
- Testes: 185 aprovados. Verificação visual por Chrome headless + CDP
  (capturas no scratchpad da sessão, não versionadas): Início, Jogar, Fases 1–5
  (consistente e inconsistente), Resolver, Resultados, Instruções e Sair em
  1440 px; Início, Jogar, Fases 2 e 3 e Resolver em 390 px. Clique físico
  no SVG (nó Escola) confirmado nas duas larguras.
- Pendências: revisão humana da identidade; conferir em navegador do aluno
  (Bahnschrift ausente fora do Windows); Fases 1, 4 e 5 não capturadas em
  390 px; impressão do HTML exportado não reconferida (exportação não mudou).

## Estado atual (funcionando)

- **Rodada 1:** estruturas (fila, pilha, lista dupla, AVL, grafo), ordenação
  (Bubble/Merge/Quick com métricas), modelos, gerador com seed, mapa de
  Verídia, regras, BFS e DFS iterativa com AVL de visitados.
- **Rodada 2:** `SessaoJogo` (selos, progressão, histórico, reinício), as
  cinco fases em `veridia/fases/`, DFS recursiva com rastro, métricas de
  busca, auditoria final com relatório, `demo_fases`, exportador de ZIP.
- **Rodada 3:** interface NiceGUI completa em `veridia/interface/`:
  - menu inicial com Jogar, Resolver, Instruções, Resultados e Sair;
  - trilho dos cinco selos na barra superior (bloqueado/liberado/conquistado), que também navega;
  - as cinco fases jogáveis, todas chamando a sessão (`ContextoTela.agir`);
  - Fase 3 com mapa SVG clicável + botões; Fase 4 com AVL real e rotações antes/depois;
  - Modo Resolver: fases 2 e 3, BFS/DFS/DFS recursiva, passo a passo, rastro, comparação em 3 cenários;
  - Resultados com histórico, métricas e relatório; exportação JSON e HTML imprimível;
  - sessão independente por navegador; Sair descarta só a própria partida.
- Única mudança no motor na Rodada 3: `FaseCentralTriagem.resolver(algoritmo)`
  e `sugerir_solucao(algoritmo="BFS")` (compatível com a API anterior).
- **Rodada 4:** enunciado oficial de 20 páginas localizado na pasta externa
  da disciplina indicada pelo aluno e conferido; rastreabilidade RF01–RF12
  e pendências acadêmicas em `REQUISITOS_EP.md`. O enunciado original não
  foi copiado para o projeto.
- Correção mínima em `Grafo.adicionar_aresta`: valida a direção inversa
  antes de inserir uma conexão bidirecional. Antes, um conflito com aresta
  dirigida inversa lançava erro após alterar parcialmente a adjacência.
  Teste de regressão reproduziu a falha antes da correção.
- Testes existentes da interface ampliados para despachar o evento do mapa
  pela raiz e baixar JSON/HTML a partir de Resultados via simulação.
- Pedido ampliado pelo aluno: relatório acadêmico em Markdown e PDF criado,
  com dez seções, tabela de IAG e medições reais. JSON de métricas inclui
  cinco repetições por combinação: 135 ordenações e 45 buscas. O exportador
  inclui esses artefatos e a configuração YAML por nomes explícitos.

**Última tela funcional:** todas as rotas (`/`, `/jogar`, `/fase/1` a `/fase/5`,
`/resolver`, `/instrucoes`, `/resultados`, `/sair`).

## Testes e validação

- Rodada 4: `.\.venv\Scripts\python.exe -m pytest` → **185 aprovados**,
  25,14 s na validação final do empacotamento. A execução após correção do grafo
  e ampliação dos testes de interface havia passado com 184 em 19,28 s.
  A suíte original de 183 também passou (23,65 s) antes das alterações.
- Ambiente local existente: Python 3.11.9, NiceGUI 4.0.0, pytest 9.2.0,
  pytest-asyncio 1.4.1.post1; nenhum pacote instalado nesta rodada.
- Testes de interface com usuário simulado do NiceGUI (sem navegador):
  menu, navegação, bloqueio, cinco fases, reinício, ações inválidas,
  Resolver, sessões independentes, Sair.
- Servidor iniciado com `python -m veridia.interface.app --porta 8090 --sem-navegador`:
  sobe sem erros; todas as rotas respondem HTTP 200; rota inexistente responde 404.
- Verificação visual com Chrome headless (capturas de Início, Jogar, Fases 1–5,
  Resolver e Instruções; as de fases avançadas com sessões preparadas por um
  lançador temporário fora do projeto). Problemas de layout encontrados
  foram corrigidos e recapturados. Resultados e Sair não foram capturadas
  (cobertas por testes com usuário simulado).
- Rodada 4: servidor local na porta 8090 confirmado; as 11 rotas principais
  responderam HTTP 200. A tentativa de iniciar outra instância na mesma
  porta foi recusada por endereço em uso; a instância já existente respondeu
  às verificações. Não foi encerrado processo alheio.
- O evento `veridia_local` foi despachado na simulação até o listener da raiz:
  exatamente um movimento, com desfazer e botões preservados nos testes.
  Resultados exibiu histórico e relatório, e os downloads reais na simulação
  retornaram HTTP 200, JSON consistente e HTML com estilo de impressão.
- **Limite de validação:** o controle do Chrome foi bloqueado por não
  conseguir determinar a URL atual com segurança. Clique físico no SVG,
  layout de Resultados no navegador e impressão do HTML ainda precisam de
  conferência manual. Simulação/HTTP 200 não foram apresentados como essa
  verificação visual.
- Ordenação: seed 2026, n=100/500/1000, entradas aleatórias/ordenadas/inversas;
  conferência inicial com uma execução por combinação e depois protocolo
  acadêmico com cinco repetições, saídas equivalentes nos três algoritmos.
  Buscas: energias 18/15/14, três algoritmos, caminhos revalidados pelas
  regras. Resultados resumidos em `REQUISITOS_EP.md`.

## Decisões tomadas

| Decisão | Motivo |
|---|---|
| Fases são controladores em memória; sessão só cuida da progressão | separar progressão das regras dos enigmas |
| Selos são permanentes; reiniciar fase não remove selo | a Fase 5 reconfere o estado atual |
| Desfazer da Fase 2 guarda retratos na pilha de histórico | a Fila não tem "inserir na frente" |
| Solvers aplicam os mesmos métodos/regras do modo manual | mesmas regras para manual e solver |
| Interface: página raiz + `ui.sub_pages` | navegação sem recarregar; barra de selos persistente |
| Interface: `GerenciadorSessoes` por `app.storage.browser["id"]` | jogadores isolados, sem banco |
| Interface: `ContextoTela.agir` reposiciona a fase atual antes de agir | a sessão avança de fase ao conceder selo |
| Interface: evento de clique do mapa registrado uma vez na raiz | `ui.on` acumularia handlers por redesenho |
| Interface: mensagens guardadas com `get`, limpas ao entrar/reiniciar | `refresh()` do NiceGUI 4 é assíncrono |
| Relatório em PDF via "Imprimir" do HTML | sem dependências ou serviços externos |
| Mantidos: coleta automática, energia na chave, BFS minimiza movimentos | decisões confirmadas pelo aluno |

## Pendências e próximos passos

1. **Entrega acadêmica:** revisar `RELATORIO_ACADEMICO.md` e o PDF de
   13 páginas, preparados conforme as seções 8.3, 9, 14.4, 15.1 e 16.
   Confirmar identificação/autoria e acrescentar considerações pessoais.
   Checklist em `REQUISITOS_EP.md`, sem pendências de bônus.
2. **Curadoria humana:** aluno confirmar decisões, alterações próprias e
   validações em pelo menos cinco interações de IAG e consolidar a tabela
   exigida no relatório. Não preencher autoria humana por suposição.
3. **Validação prática e apresentação:** clicar no mapa em navegador real,
   abrir os downloads e conferir a impressão; demonstrar partida manual e
   solver em sala. Teste por pessoa que não programou o jogo é recomendado.
4. **Publicação:** revisar os arquivos preparados e autorizar commit/push.
   Não houve commit nem push nesta rodada. Nenhum outro projeto foi alterado.
5. **CI:** `scripts/pytest-github-actions.yml` foi copiado para
   `.github/workflows/veridia-pytest.yml` na raiz de `data-science-projects`,
   autorização expressa no pedido anexado em 06/11.
   Configura Python 3.11, instala `requirements-interface.txt` no runner e
   roda a suíte completa, com filtros apenas para VERÍDIA e seu workflow.
   Configuração validada estruturalmente; será disparada após publicação.
   Execução Linux no GitHub ainda não ocorreu.

## Preparação para GitHub

- Repositório: `data-science-projects`; branch encontrada:
  `chore/reorganizacao-revisao-mike`; remoto `origin` do repositório atual.
  Não criar Git aninhado nem mudar branch automaticamente.
- Branch principal remota confirmada como `main` pelo conector GitHub.
  A referência local `origin/main` é `5ae8e272dd82016928b84dd3629decbecc1bff82`.
  A branch atual tem 37 commits além dela. `git ls-remote` falhou por
  credenciais Schannel indisponíveis; não foi alegada atualização dessa ref.
- Sparse checkout ativo em modo cone. VERÍDIA e `.github` não estavam na
  seleção. Não foi alterada essa configuração nem trocada a branch.
  Staging restrito deve usar `git add --sparse` para os caminhos autorizados.
- **Branch proposta:** `feat/veridia-entrega`, derivada de `origin/main`
  atualizado antes da publicação, com integração dos arquivos revisados em
  worktree isolada. Criar essa worktree/branch e realizar commit/push requer
  aprovação; não publicar a branch atual, que inclui outros trabalhos.
- `.gitignore` local reforçado para ambientes, caches, ZIPs, logs, armazenamento
  NiceGUI e arquivos usuais de credenciais. A chave `CHAVE_COOKIE` do app é
  um valor público de desenvolvimento local, documentado no código; não é
  uma credencial de serviço. Aplicação permanece com host padrão de loopback.
- `.gitattributes` local marca PDFs como binários, impedindo conversão de
  quebras de linha pelo Git; incluída também no ZIP. O PDF acadêmico será
  conferido byte a byte entre disco, índice e pacote.
- O ZIP `projetos/urna-logica-veridia.zip`, já existente fora desta pasta,
  não faz parte da preparação e não foi alterado.
- O ZIP limpo em `dist/` deve ser regenerado após atualizar a documentação;
  permanece ignorado no Git. O exportador inclui o relatório acadêmico e
  o JSON/YAML nomeados explicitamente. O enunciado externo continua excluído.
- O índice será limitado aos arquivos desta pasta; o manifesto abaixo
  permite revisar a seleção antes de qualquer commit/push.

## Arquivos para o próximo agente consultar

`AGENTS.md` (Codex) ou `CLAUDE.md` (Claude Code) → `docs/CONTINUIDADE.md` →
`docs/REQUISITOS_EP.md` → `veridia/interface/app.py` → `veridia/interface/estado.py`
→ tela em que for trabalhar (`veridia/interface/telas/`) → fase correspondente
em `veridia/fases/` → `docs/GUIA_TECNICO.md` (seção 14 para a interface).

## Manifesto dos arquivos preparados para o commit inicial

Seleção: **91 arquivos do projeto + 1 workflow na raiz = 92 arquivos**.
Os caminhos no bloco são relativos a `projetos/urna-logica-veridia/`.
O arquivo adicional autorizado é `.github/workflows/veridia-pytest.yml`,
relativo à raiz do repositório. Ambientes, caches, temporários, ZIPs e o
PDF original da professora ficam excluídos.

A preparação do índice não constitui commit nem autorização de push.
A branch pretendida para a publicação é `feat/veridia-entrega`, a partir da
main atualizada; essa operação ainda não foi realizada.

```text
.gitattributes
.gitignore
AGENTS.md
CLAUDE.md
README.md
docs/CONTINUIDADE.md
docs/GUIA_TECNICO.md
docs/METRICAS_RODADA4.json
docs/REGISTRO_IA.md
docs/RELATORIO_ACADEMICO.md
docs/RELATORIO_ACADEMICO.pdf
docs/REQUISITOS_EP.md
pyproject.toml
requirements-interface.txt
requirements.txt
scripts/exportar_projeto.py
scripts/pytest-github-actions.yml
tests/__init__.py
tests/auxiliares.py
tests/test_arvore_avl.py
tests/test_demos.py
tests/test_exportacao.py
tests/test_fase1_arquivo.py
tests/test_fase2_triagem.py
tests/test_fase3_mapa.py
tests/test_fase4_cofre.py
tests/test_fase5_auditoria.py
tests/test_fila_pilha.py
tests/test_grafo.py
tests/test_interface_app.py
tests/test_interface_modulos.py
tests/test_lista_ligada.py
tests/test_modelos.py
tests/test_ordenacao.py
tests/test_regras.py
tests/test_sessao.py
tests/test_solver.py
tests/test_solver_recursivo.py
veridia/__init__.py
veridia/algoritmos/__init__.py
veridia/algoritmos/ordenacao.py
veridia/busca/__init__.py
veridia/busca/solver.py
veridia/dados/__init__.py
veridia/dados/gerador_registros.py
veridia/dados/mapa_veridia.py
veridia/demos/__init__.py
veridia/demos/demo_busca.py
veridia/demos/demo_fases.py
veridia/demos/experimento_ordenacao.py
veridia/estruturas/__init__.py
veridia/estruturas/arvore_avl.py
veridia/estruturas/erros.py
veridia/estruturas/fila.py
veridia/estruturas/grafo.py
veridia/estruturas/lista_ligada.py
veridia/estruturas/pilha.py
veridia/fases/__init__.py
veridia/fases/base.py
veridia/fases/fase1_arquivo.py
veridia/fases/fase2_triagem.py
veridia/fases/fase3_mapa.py
veridia/fases/fase4_cofre.py
veridia/fases/fase5_auditoria.py
veridia/interface/__init__.py
veridia/interface/app.py
veridia/interface/componentes.py
veridia/interface/estado.py
veridia/interface/estilos.css
veridia/interface/exportacao.py
veridia/interface/svg.py
veridia/interface/telas/__init__.py
veridia/interface/telas/fase1.py
veridia/interface/telas/fase2.py
veridia/interface/telas/fase3.py
veridia/interface/telas/fase4.py
veridia/interface/telas/fase5.py
veridia/interface/telas/inicio.py
veridia/interface/telas/instrucoes.py
veridia/interface/telas/jogar.py
veridia/interface/telas/resolver.py
veridia/interface/telas/resultados.py
veridia/interface/telas/sair.py
veridia/jogo/__init__.py
veridia/jogo/regras.py
veridia/jogo/sessao.py
veridia/modelos/__init__.py
veridia/modelos/estado.py
veridia/modelos/evidencia.py
veridia/modelos/mapa.py
veridia/modelos/registro.py
```
