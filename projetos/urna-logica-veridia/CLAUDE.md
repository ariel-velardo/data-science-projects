# CLAUDE.md — VERÍDIA, O Enigma da Urna

Instruções permanentes para sessões do Claude Code neste projeto
(EP Urna Lógica — EDAA, Mestrado Profissional em Computação Aplicada, IPT).

## Antes de começar
- Leia `docs/CONTINUIDADE.md` (estado atual, decisões e próximos passos) e
  `docs/REQUISITOS_EP.md` (requisito → arquivo → status).
- Se `EP Urna Lógica.pdf` estiver no workspace, ele prevalece sobre qualquer
  resumo. Não invente exigências que não estejam nele.
- Ambiente: `.venv` deste projeto (Python 3.11). Testes: `python -m pytest`.

## Regras permanentes
1. **Python** é a linguagem da lógica do jogo; só biblioteca padrão (+ pytest).
   A interface **NiceGUI 4** (`veridia/interface/`, `python -m veridia.interface.app`)
   só chama as fases pela sessão (`ContextoTela.agir`) e exibe os resultados:
   nunca reimplementa regras nem concede selos.
2. **Preserve as estruturas e algoritmos implementados manualmente**
   (`veridia/estruturas/`, `veridia/algoritmos/`, `veridia/busca/`). Não troque
   por bibliotecas prontas nem crie versões paralelas (ex.: uma segunda AVL).
3. **Modo manual e solver usam os mesmos mecanismos**: mapa → `jogo/regras.py`;
   triagem → métodos de ação de `FaseCentralTriagem`. O solver só aplica essas
   mesmas funções.
4. **Nenhuma solução codificada**: respostas são descobertas pelas regras/solver
   e os testes revalidam soluções reexecutando as regras.
5. **Execute a suíte completa após cada alteração** e corrija falhas concretas.
6. **Sem refatorações extensas** sem necessidade demonstrada. Mudanças pequenas,
   incrementais e dentro de `projetos/urna-logica-veridia/`.
7. Ações de fase devolvem `ResultadoAcao`; ação inválida não altera o estado.
8. **Registre contribuições relevantes de IA** em `docs/REGISTRO_IA.md`.
9. **Não faça commit nem push** automaticamente.
10. **Atualize `docs/CONTINUIDADE.md`** ao fim de cada rodada (ou antes de o
    contexto se esgotar).
11. **Exporte um ZIP limpo** ao final de cada rodada importante:
    `python scripts/exportar_projeto.py` → `dist/urna-logica-veridia-codigo.zip`.

## Decisões já tomadas (não reabrir sem motivo)
- Coleta automática de pistas ao chegar a um local.
- Energia faz parte da chave canônica do estado.
- BFS minimiza número de movimentos (não energia); Dijkstra/A* fora do escopo atual.
- Selos são permanentes; a Auditoria Final reconfere o estado atual das fases.
- Movimentação nas métricas de ordenação = escrita de elemento (troca = 2).

## NiceGUI 4: cuidados aprendidos
- `ui.refreshable.refresh()` é assíncrono: guarde a última mensagem com `get`
  (não `pop`) e limpe ao entrar na tela ou reiniciar a fase.
- Não chame `ui.on` dentro das telas (acumula handlers). O clique do mapa é
  registrado uma vez em `app.raiz` e repassado para `ContextoTela.ao_clicar_local`.
- Botões sem destaque usam `color=None`; o Quasar sobrescreve cores por classe.
- Testes de interface: `user_simulation(root=app.raiz)` + `GerenciadorSessoes`
  novo por teste; aguarde elementos (`should_see`) antes de clicar após um refresh.

## Mapa rápido
- `veridia/jogo/sessao.py` — progressão, selos, histórico, reinício.
- `veridia/fases/fase{1..5}_*.py` — os cinco enigmas.
- `veridia/busca/solver.py` — BFS, DFS iterativa, DFS recursiva, métricas.
- `veridia/interface/` — app NiceGUI; `telas/` tem uma tela por rota.
- `veridia/demos/` — demos de terminal (`python -m veridia.demos.<nome>`).
