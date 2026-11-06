"""Demonstração em terminal das cinco fases jogadas pela sessão.

Execução (com a .venv do projeto ativada, na pasta do projeto):
    python -m veridia.demos.demo_fases

Joga a partida inteira usando somente ações válidas da sessão — incluindo
alguns erros propositais para mostrar o feedback e o DESFAZER. As sequências
das fases 2 e 3 são descobertas pelo solver (nada é codificado), e a
classificação da Fase 4 é respondida consultando a própria AVL. Ao final,
imprime o relatório da auditoria e um trecho do rastro da DFS recursiva.
"""

from __future__ import annotations

from veridia.busca.solver import resolver_mapa
from veridia.dados.mapa_veridia import construir_mapa_veridia
from veridia.fases.base import ResultadoAcao
from veridia.jogo.sessao import SessaoJogo


def _mostrar(rotulo: str, resultado: ResultadoAcao) -> None:
    marca = "ok " if resultado.sucesso else "ERR"
    print(f"  [{marca}] {rotulo}: {resultado.mensagem}")


def main() -> None:
    sessao = SessaoJogo()

    print("=== Fase 1 — O Arquivo Embaralhado ===")
    _mostrar("algoritmo", sessao.executar("selecionar_algoritmo", "quick_sort"))
    _mostrar("critério errado", sessao.executar("selecionar_criterio", "horario"))
    _mostrar("ordenar", sessao.executar("executar_ordenacao"))
    _mostrar("critério certo", sessao.executar("selecionar_criterio", "zona_secao_horario"))
    _mostrar("ordenar", sessao.executar("executar_ordenacao"))

    print("\n=== Fase 2 — A Central de Triagem ===")
    _mostrar("custodiar da pilha vazia", sessao.executar("custodiar_da_pilha"))
    _mostrar("arquivar E1 (erro)", sessao.executar("arquivar_da_fila"))
    _mostrar("sugerir solução", sessao.executar("sugerir_solucao"))
    _mostrar("desfazer", sessao.executar("desfazer"))
    sugestao = sessao.executar("sugerir_solucao")
    _mostrar("sugerir solução", sugestao)
    for acao in sugestao.dados["acoes"]:
        _mostrar(acao, sessao.executar(acao))

    print("\n=== Fase 3 — O Mapa das Seções ===")
    _mostrar("ir ao Tribunal direto", sessao.executar("mover", "TRIBUNAL"))
    plano = sessao.executar("solicitar_solucao", "BFS")
    _mostrar("solver BFS", plano)
    for destino in plano.dados["caminho"]:
        _mostrar(f"mover {destino}", sessao.executar("mover", destino))

    print("\n=== Fase 4 — O Cofre dos Estados ===")
    cofre = sessao.fases[4]
    _mostrar("comparar A e B", sessao.executar("comparar", "A", "B"))
    _mostrar("comparar A e C", sessao.executar("comparar", "A", "C"))
    _mostrar("A é repetido? (erro)", sessao.executar("classificar", "repetido"))
    while cofre.candidato_atual() is not None:
        atual = cofre.candidato_atual()
        resposta = "repetido" if cofre.avl.contem(atual.estado.chave()) else "novo"
        _mostrar(f"{atual.rotulo} ({atual.descricao}) → {resposta}", sessao.executar("classificar", resposta))

    print("\n=== Fase 5 — A Auditoria Final ===")
    auditoria = sessao.executar("executar_auditoria", "BFS", "merge_sort")
    _mostrar("auditoria", auditoria)
    relatorio = auditoria.dados["relatorio"]
    for chave in ("consistente", "selos", "caminho", "movimentos", "energia_consumida", "estados_explorados", "custodia"):
        print(f"    {chave}: {relatorio[chave]}")
    print(f"    evidências ordenadas (merge_sort): {[e['id'] for e in relatorio['evidencias_ordenadas']]}")

    print(f"\nSelos: {sorted(sessao.selos)} | jogo concluído: {sessao.jogo_concluido()} | ações no histórico: {len(sessao.historico)}")

    print("\n=== Rastro da DFS recursiva no mapa (primeiros 12 eventos) ===")
    recursiva = resolver_mapa(construir_mapa_veridia(), "DFS_RECURSIVA")
    for passo in recursiva.rastro_recursao[:12]:
        print(f"  {'  ' * passo.profundidade}[{passo.profundidade}] {passo.evento}: {passo.estado}")
    print(
        f"  ... {len(recursiva.rastro_recursao)} eventos; profundidade máxima {recursiva.tamanho_max_fronteira}; "
        f"caminho de {recursiva.comprimento} movimentos."
    )


if __name__ == "__main__":
    main()
