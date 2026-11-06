"""Rastro das comparações feitas por um algoritmo de ordenação REAL (Fase 1).

Os algoritmos de ``veridia/algoritmos/ordenacao.py`` não guardam etapas e não
são alterados. Para mostrar o passo a passo, este módulo chama o próprio
algoritmo com uma função de chave "observada": cada comparação do
``_Comparador`` consulta a chave dos dois registros comparados, nessa ordem,
então a sequência de chamadas revela exatamente quais pares foram comparados.

Nada aqui altera a fase: é uma demonstração sobre uma amostra do lote.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from veridia.algoritmos.ordenacao import ALGORITMOS, CRITERIOS, MetricasOrdenacao
from veridia.fases.fase1_arquivo import CRITERIO_OBJETIVO
from veridia.modelos.registro import RegistroVotacao


@dataclass(frozen=True)
class Comparacao:
    a: str            # id do registro passado primeiro ao comparador
    b: str            # id do segundo registro
    a_antes: bool     # resposta do comparador: a deve vir estritamente antes de b?


@dataclass(frozen=True)
class RastroOrdenacao:
    algoritmo: str
    entrada: tuple[RegistroVotacao, ...]
    saida: tuple[RegistroVotacao, ...]
    comparacoes: tuple[Comparacao, ...]
    metricas: MetricasOrdenacao


def rastrear(registros: Sequence[RegistroVotacao], algoritmo: str, criterio: str = CRITERIO_OBJETIVO) -> RastroOrdenacao:
    chave = CRITERIOS[criterio]
    chamadas: list[tuple[str, Any]] = []

    def chave_observada(registro: RegistroVotacao) -> Any:
        valor = chave(registro)
        chamadas.append((registro.id, valor))
        return valor

    saida, metricas = ALGORITMOS[algoritmo](registros, chave=chave_observada)
    if len(chamadas) != 2 * metricas.comparacoes:  # garante a leitura em pares
        raise RuntimeError("rastro de comparações inconsistente com as métricas do algoritmo")
    comparacoes = tuple(
        Comparacao(a=ida, b=idb, a_antes=ka < kb)
        for (ida, ka), (idb, kb) in zip(chamadas[0::2], chamadas[1::2])
    )
    return RastroOrdenacao(algoritmo, tuple(registros), tuple(saida), comparacoes, metricas)
