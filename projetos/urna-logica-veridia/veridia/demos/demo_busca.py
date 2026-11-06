"""Demonstração em terminal: o desafio de Verídia resolvido por BFS e por DFS.

Execução (com a .venv do projeto ativada, na pasta do projeto):
    python -m veridia.demos.demo_busca
    python -m veridia.demos.demo_busca --energia 14     # cenário sem solução

Mostra, para cada algoritmo: caminho encontrado, estados explorados,
repetidos descartados pela AVL, tamanho/altura da AVL e as primeiras
entradas da ordem de visita. No fim, demonstra a AVL distinguindo estados
na mesma posição com pistas diferentes e reconhecendo estados equivalentes.
"""

from __future__ import annotations

import argparse
import math

from veridia.busca.solver import ResultadoBusca, resolver_mapa
from veridia.dados.mapa_veridia import ENERGIA_INICIAL_VERIDIA, construir_mapa_veridia
from veridia.estruturas.arvore_avl import ArvoreAVL
from veridia.jogo import regras
from veridia.modelos.estado import EstadoJogo


def descrever(resultado: ResultadoBusca, mostrar_visitas: int = 8) -> str:
    linhas = [f"=== {resultado.algoritmo} ==="]
    if resultado.encontrou:
        linhas.append(f"Solução com {resultado.comprimento} movimentos:")
        for passo, (acao, estado) in enumerate(zip(resultado.acoes, resultado.estados_caminho[1:]), start=1):
            linhas.append(f"  {passo:>2}. {acao}  ->  {estado}")
    else:
        linhas.append("Nenhuma solução: todo o espaço de estados alcançável foi explorado.")
    avl = resultado.visitados
    assert avl is not None
    n = len(avl)
    linhas += [
        f"Estados explorados (expandidos): {resultado.estados_explorados}",
        f"Sucessores gerados:              {resultado.estados_gerados}",
        f"Repetidos descartados pela AVL:  {resultado.repetidos_descartados}",
        f"AVL de visitados: {n} estados, altura {avl.altura()} "
        f"(log2(n) ≈ {math.log2(n):.1f}), balanceada = {avl.esta_balanceada()}",
        f"Rotações realizadas: {avl.rotacoes}",
        f"Primeiras {mostrar_visitas} visitas:",
    ]
    linhas += [f"  {i:>2}. {e}" for i, e in enumerate(resultado.ordem_visita[:mostrar_visitas], start=1)]
    return "\n".join(linhas)


def demonstrar_avl_de_estados() -> str:
    avl: ArvoreAVL = ArvoreAVL()
    a = EstadoJogo("PRACA", {"ata_secao"}, energia=10)
    b = EstadoJogo("PRACA", {"ata_secao", "testemunho_feirante"}, energia=10)
    a_equivalente = EstadoJogo("PRACA", ["ata_secao"], energia=10)
    return "\n".join(
        [
            "=== AVL: estados equivalentes x distintos ===",
            f"Inserir {a}: {avl.inserir(a.chave(), a)}",
            f"Inserir {b} (mesma posição, pistas diferentes): {avl.inserir(b.chave(), b)}",
            f"Inserir {a_equivalente} (equivalente ao primeiro): {avl.inserir(a_equivalente.chave(), a_equivalente)}",
            f"Total na AVL: {len(avl)}",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--energia", type=int, default=ENERGIA_INICIAL_VERIDIA)
    args = parser.parse_args(argv)

    mapa = construir_mapa_veridia(energia_inicial=args.energia)
    print(f"Mapa: {mapa.grafo.num_vertices} locais, {mapa.grafo.num_conexoes} conexões")
    print(f"Início: {mapa.inicio} | Destino: {mapa.destino} | Energia: {mapa.energia_inicial}")
    print(f"Pistas necessárias: {sorted(mapa.pistas_necessarias)}")
    print(f"Estado inicial: {regras.estado_inicial(mapa)}\n")
    for algoritmo in ("BFS", "DFS"):
        print(descrever(resolver_mapa(mapa, algoritmo)))
        print()
    print(demonstrar_avl_de_estados())


if __name__ == "__main__":
    main()
