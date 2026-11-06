"""Experimento reproduzível: Bubble x Merge x Quick em registros fictícios.

Execução (com a .venv do projeto ativada, na pasta do projeto):
    python -m veridia.demos.experimento_ordenacao
    python -m veridia.demos.experimento_ordenacao --tamanhos 100 500 1000 --seed 2026

Para cada tamanho n e cada cenário de entrada (aleatório, já ordenado,
ordem inversa), ordena pela chave composta (zona, seção, horário) e imprime
comparações, movimentações e tempo. Também confere que os três algoritmos
produzem a mesma sequência de chaves.
"""

from __future__ import annotations

import argparse

from veridia.algoritmos.ordenacao import ALGORITMOS, CRITERIOS, MetricasOrdenacao
from veridia.dados.gerador_registros import SEED_PADRAO, gerar_registros

CENARIOS = ("aleatorio", "ordenado", "inverso")


def preparar_entrada(n: int, cenario: str, seed: int) -> list:
    registros = gerar_registros(n, seed=seed)
    chave = CRITERIOS["zona_secao_horario"]
    if cenario == "aleatorio":
        return registros
    if cenario == "ordenado":
        return sorted(registros, key=chave)  # sorted só PREPARA a entrada; não é o objeto de estudo
    if cenario == "inverso":
        return sorted(registros, key=chave, reverse=True)
    raise ValueError(f"cenário desconhecido: {cenario!r}")


def executar_experimento(tamanhos: list[int], seed: int = SEED_PADRAO) -> list[tuple[str, MetricasOrdenacao]]:
    chave = CRITERIOS["zona_secao_horario"]
    resultados: list[tuple[str, MetricasOrdenacao]] = []
    for n in tamanhos:
        for cenario in CENARIOS:
            entrada = preparar_entrada(n, cenario, seed)
            esperado = [chave(r) for r in sorted(entrada, key=chave)]
            for funcao in ALGORITMOS.values():
                saida, metricas = funcao(entrada, chave=chave)
                if [chave(r) for r in saida] != esperado:
                    raise AssertionError(f"{metricas.algoritmo} ordenou incorretamente ({cenario}, n={n})")
                resultados.append((cenario, metricas))
    return resultados


def formatar_tabela(resultados: list[tuple[str, MetricasOrdenacao]]) -> str:
    linhas = [f"{'n':>6} {'cenário':<10} {'algoritmo':<12} {'comparações':>12} {'movimentações':>14} {'tempo (ms)':>11}"]
    linhas.append("-" * len(linhas[0]))
    for cenario, m in resultados:
        linhas.append(
            f"{m.n:>6} {cenario:<10} {m.algoritmo:<12} {m.comparacoes:>12} {m.movimentacoes:>14} {m.tempo_segundos * 1000:>11.2f}"
        )
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tamanhos", type=int, nargs="+", default=[100, 500, 1000])
    parser.add_argument("--seed", type=int, default=SEED_PADRAO)
    args = parser.parse_args(argv)
    print(f"Chave: (zona, seção, horário) | seed={args.seed}\n")
    print(formatar_tabela(executar_experimento(args.tamanhos, args.seed)))
    print("\nTodos os algoritmos produziram a mesma ordem de chaves.")


if __name__ == "__main__":
    main()
