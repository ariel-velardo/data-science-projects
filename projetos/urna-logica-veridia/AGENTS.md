# AGENTS.md — VERÍDIA, O Enigma da Urna

Instruções para agentes (Codex e similares) que continuarem este projeto.
Sessões do Claude Code usam `CLAUDE.md`, que traz as mesmas regras.

## Contexto

Exercício Programa **Urna Lógica**, da disciplina Estruturas de Dados e Análise
de Algoritmos (Mestrado Profissional em Computação Aplicada, IPT). É um jogo
educacional de investigação sobre uma eleição **fictícia**, com cinco fases.
Cada fase demonstra estruturas e algoritmos implementados à mão em Python.
Todos os dados são fictícios: não use candidatos, partidos ou resultados reais.

Leia antes de começar:
1. `docs/CONTINUIDADE.md`: estado atual, decisões e próximos passos.
2. `docs/REQUISITOS_EP.md`: requisito, arquivo responsável e status.
3. `docs/GUIA_TECNICO.md`: funcionamento e complexidades.
4. Se o PDF oficial `EP Urna Lógica.pdf` estiver no workspace, ele prevalece.

## Arquitetura

```
veridia/
  estruturas/  Fila, Pilha, ListaLigada (dupla), ArvoreAVL, Grafo   (implementação própria)
  algoritmos/  ordenacao.py: Bubble, Merge e Quick Sort com métricas
  modelos/     RegistroVotacao, Evidencia, EstadoJogo (chave canônica), Mapa
  dados/       gerador de registros (seed fixa) e mapa de Verídia
  jogo/        regras.py (movimento, portas, pistas, vitória) e sessao.py (selos, progressão)
  busca/       solver.py: BFS, DFS iterativa, DFS recursiva, métricas, AVL de visitados
  fases/       fase1_arquivo … fase5_auditoria: controladores com ACOES e ResultadoAcao
  interface/   NiceGUI: app.py (raiz + rotas), estado.py (sessão por navegador),
               componentes.py, svg.py (mapa e AVL), exportacao.py (JSON/HTML),
               estilos.css, telas/ (uma tela por rota)
  demos/       demonstrações de terminal
scripts/exportar_projeto.py   ZIP limpo em dist/
tests/                        pytest (motor + interface com usuário simulado)
```

Fluxo: tela NiceGUI → `ContextoTela.agir(fase, ação, ...)` →
`SessaoJogo.executar` → método da fase → regras/estruturas/solver. A sessão é
a única que concede selos.

## Comandos

Use sempre a `.venv` deste projeto (Python 3.11), na pasta `projetos/urna-logica-veridia/`:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-interface.txt   # NiceGUI 4 + pytest + pytest-asyncio
python -m pytest                                      # suíte completa
python -m veridia.interface.app                       # interface em http://127.0.0.1:8080
python -m veridia.interface.app --porta 8090 --sem-navegador
python -m veridia.demos.demo_fases                    # partida completa no terminal
python scripts/exportar_projeto.py                    # dist/urna-logica-veridia-codigo.zip
```

## Restrições

- Não reescreva nem substitua estruturas e algoritmos de `estruturas/`,
  `algoritmos/` e `busca/` por bibliotecas prontas. Não crie versões
  paralelas (por exemplo, uma segunda AVL ou uma segunda lógica de movimento).
- Manual e solver usam as mesmas regras: mapa por `jogo/regras.py`, triagem
  pelos métodos de ação de `FaseCentralTriagem`.
- A interface não decide regras nem concede selos. Ela só chama ações por
  `ContextoTela.agir` e exibe `ResultadoAcao` e `consultar()`.
- Nenhuma solução fixa: caminhos e sequências vêm do solver ou do jogador.
- Ação inválida devolve `ResultadoAcao(sucesso=False, ...)` e não altera o estado.
- Rode a suíte completa após cada alteração. Não reduza testes para "passar".
- Sem refatorações amplas, sem novas dependências sem necessidade, sem
  banco de dados, login ou serviços externos.
- Não faça commit nem push automaticamente.
- Registre contribuições relevantes de IA em `docs/REGISTRO_IA.md` e atualize
  `docs/CONTINUIDADE.md` ao fim de cada rodada.
- Gere o ZIP limpo ao fim de cada rodada importante.

## Pontos de atenção (NiceGUI 4)

- `refresh()` de `ui.refreshable` é assíncrono: não use `pop` em mensagens
  guardadas para a próxima renderização (use `get` e limpe ao entrar ou reiniciar).
- O clique no SVG do mapa usa `emitEvent('veridia_local', id)`, registrado
  uma única vez em `app.raiz`, e é repassado para `ContextoTela.ao_clicar_local`.
- Testes de interface usam `nicegui.testing.user_simulation(root=app.raiz)`
  com um `GerenciadorSessoes` novo por teste (ver `tests/test_interface_app.py`).
