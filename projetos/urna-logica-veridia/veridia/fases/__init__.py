"""As cinco fases de Verídia (lógica dos enigmas, sem interface).

1. fase1_arquivo   — O Arquivo Embaralhado   (ordenação de registros)
2. fase2_triagem   — A Central de Triagem    (fila, pilha, lista ligada, desfazer)
3. fase3_mapa      — O Mapa das Seções       (grafo, BFS/DFS, pistas e portas)
4. fase4_cofre     — O Cofre dos Estados     (AVL e estados repetidos)
5. fase5_auditoria — A Auditoria Final       (integração, solver, ordenação, métricas)

A progressão (selos, fase atual, histórico) fica em ``veridia.jogo.sessao``.
"""

from veridia.fases.base import Fase, ResultadoAcao

__all__ = ["Fase", "ResultadoAcao"]
