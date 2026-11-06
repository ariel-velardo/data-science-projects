"""Bubble Sort, Merge Sort e Quick Sort implementados manualmente, com métricas.

Interface comum:
    ordenado, metricas = merge_sort(registros, chave=CRITERIOS["zona_secao_horario"])

- ``registros`` nunca é modificado: os algoritmos trabalham em uma CÓPIA
  rasa da lista (os registros são imutáveis, então só as referências mudam
  de lugar).
- ``chave`` é uma função registro -> valor comparável. Para chave composta
  basta devolver uma tupla, comparada lexicograficamente pelo Python:
  primeiro a zona; em empate, a seção; em novo empate, o horário.
- ``decrescente=True`` inverte o sentido.

Definição das métricas (iguais para os três algoritmos, para comparação justa):
- comparações: número de vezes que duas chaves são comparadas;
- movimentações: número de ESCRITAS de um elemento em uma posição de
  memória do algoritmo — vetor principal ou vetor auxiliar do Merge Sort
  (uma troca = 2 escritas; cada cópia para/do auxiliar = 1 escrita);
- tempo: segundos medidos com ``time.perf_counter`` (inclui o overhead da
  contagem, por isso serve para comparar os algoritmos entre si, não para
  comparar com ``sorted``).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Sequence, TypeVar

from veridia.modelos.registro import RegistroVotacao

T = TypeVar("T")
FuncaoChave = Callable[[Any], Any]

CRITERIOS: dict[str, FuncaoChave] = {
    "zona_secao_horario": lambda r: (r.zona, r.secao, r.horario),
    "horario": lambda r: r.horario,
    "id": lambda r: r.id,
    "status_horario": lambda r: (r.status.value, r.horario),
}


def _identidade(x: Any) -> Any:
    return x


@dataclass
class MetricasOrdenacao:
    algoritmo: str
    n: int = 0
    comparacoes: int = 0
    movimentacoes: int = 0
    tempo_segundos: float = 0.0


class _Comparador:
    """Compara chaves contando as comparações."""

    def __init__(self, chave: FuncaoChave, decrescente: bool, metricas: MetricasOrdenacao) -> None:
        self.chave = chave
        self.decrescente = decrescente
        self.metricas = metricas

    def menor(self, a: Any, b: Any) -> bool:
        """True se ``a`` deve vir estritamente antes de ``b``."""
        self.metricas.comparacoes += 1
        ka, kb = self.chave(a), self.chave(b)
        return kb < ka if self.decrescente else ka < kb


def _executar(nome: str, dados: Sequence[T], chave: FuncaoChave | None, decrescente: bool, nucleo) -> tuple[list[T], MetricasOrdenacao]:
    vetor = list(dados)  # cópia: preserva a sequência original
    metricas = MetricasOrdenacao(algoritmo=nome, n=len(vetor))
    comparador = _Comparador(chave or _identidade, decrescente, metricas)
    inicio = time.perf_counter()
    nucleo(vetor, comparador, metricas)
    metricas.tempo_segundos = time.perf_counter() - inicio
    return vetor, metricas


# ----------------------------------------------------------------------
# Bubble Sort — O(n²) pior/médio, O(n) melhor (já ordenado), estável, in-place
# ----------------------------------------------------------------------
def _bubble(vetor: list, cmp: _Comparador, metricas: MetricasOrdenacao) -> None:
    n = len(vetor)
    for passada in range(n - 1):
        houve_troca = False
        # Após cada passada, o maior elemento restante "borbulha" para o fim.
        for j in range(n - 1 - passada):
            if cmp.menor(vetor[j + 1], vetor[j]):  # só troca se estritamente menor → estável
                vetor[j], vetor[j + 1] = vetor[j + 1], vetor[j]
                metricas.movimentacoes += 2
                houve_troca = True
        if not houve_troca:  # parada antecipada: vetor já ordenado
            break


def bubble_sort(dados: Sequence[T], chave: FuncaoChave | None = None, decrescente: bool = False):
    return _executar("bubble_sort", dados, chave, decrescente, _bubble)


# ----------------------------------------------------------------------
# Merge Sort — O(n log n) em todos os casos, estável, O(n) memória extra
# ----------------------------------------------------------------------
def _merge(vetor: list, cmp: _Comparador, metricas: MetricasOrdenacao) -> None:
    auxiliar = [None] * len(vetor)

    def ordenar(inicio: int, fim: int) -> None:  # intervalo semiaberto [inicio, fim)
        if fim - inicio <= 1:
            return
        meio = (inicio + fim) // 2
        ordenar(inicio, meio)
        ordenar(meio, fim)
        intercalar(inicio, meio, fim)

    def intercalar(inicio: int, meio: int, fim: int) -> None:
        for posicao in range(inicio, fim):  # cópia de trabalho para o auxiliar
            auxiliar[posicao] = vetor[posicao]
        metricas.movimentacoes += fim - inicio
        i, j, k = inicio, meio, inicio
        while i < meio and j < fim:
            # Em empate pega da metade ESQUERDA (não usa "menor" a seu favor) → estável.
            if cmp.menor(auxiliar[j], auxiliar[i]):
                vetor[k] = auxiliar[j]
                j += 1
            else:
                vetor[k] = auxiliar[i]
                i += 1
            metricas.movimentacoes += 1
            k += 1
        while i < meio:
            vetor[k] = auxiliar[i]
            i += 1
            k += 1
            metricas.movimentacoes += 1
        # Os elementos restantes da metade direita já estão na posição final.

    ordenar(0, len(vetor))


def merge_sort(dados: Sequence[T], chave: FuncaoChave | None = None, decrescente: bool = False):
    return _executar("merge_sort", dados, chave, decrescente, _merge)


# ----------------------------------------------------------------------
# Quick Sort — O(n log n) médio, O(n²) pior caso (raro com mediana de três),
# in-place, NÃO estável.
#
# Decisões de implementação:
# - pivô = mediana de três (início, meio, fim): os três elementos são
#   colocados em ordem e o do meio vira pivô. Evita o pior caso clássico
#   (pivô = extremo) em vetores já ordenados ou em ordem inversa;
# - partição de Hoare: dois índices andam um em direção ao outro e trocam
#   pares fora do lugar. Elementos IGUAIS ao pivô param os dois índices e
#   são distribuídos entre os lados, então muitas chaves repetidas (ex.:
#   mesma zona) não desequilibram a partição;
# - recursão só na parte MENOR e laço na maior: profundidade de pilha
#   O(log n), sem risco de estourar o limite de recursão do Python.
# ----------------------------------------------------------------------
def _quick(vetor: list, cmp: _Comparador, metricas: MetricasOrdenacao) -> None:
    def trocar(i: int, j: int) -> None:
        vetor[i], vetor[j] = vetor[j], vetor[i]
        metricas.movimentacoes += 2

    def particionar(inicio: int, fim: int) -> int:
        meio = (inicio + fim) // 2
        # Mediana de três: deixa vetor[inicio] <= vetor[meio] <= vetor[fim].
        if cmp.menor(vetor[meio], vetor[inicio]):
            trocar(inicio, meio)
        if cmp.menor(vetor[fim], vetor[inicio]):
            trocar(inicio, fim)
        if cmp.menor(vetor[fim], vetor[meio]):
            trocar(meio, fim)
        pivo = vetor[meio]
        i, j = inicio - 1, fim + 1
        while True:
            i += 1
            while cmp.menor(vetor[i], pivo):
                i += 1
            j -= 1
            while cmp.menor(pivo, vetor[j]):
                j -= 1
            if i >= j:
                return j  # [inicio, j] <= pivô <= [j+1, fim]
            trocar(i, j)

    def ordenar(inicio: int, fim: int) -> None:  # intervalo fechado [inicio, fim]
        while inicio < fim:
            corte = particionar(inicio, fim)
            if corte - inicio < fim - corte:
                ordenar(inicio, corte)
                inicio = corte + 1
            else:
                ordenar(corte + 1, fim)
                fim = corte

    ordenar(0, len(vetor) - 1)


def quick_sort(dados: Sequence[T], chave: FuncaoChave | None = None, decrescente: bool = False):
    return _executar("quick_sort", dados, chave, decrescente, _quick)


ALGORITMOS = {"bubble_sort": bubble_sort, "merge_sort": merge_sort, "quick_sort": quick_sort}


def ordenar_registros(
    registros: Sequence[RegistroVotacao],
    algoritmo: str = "merge_sort",
    criterio: str = "zona_secao_horario",
    decrescente: bool = False,
) -> tuple[list[RegistroVotacao], MetricasOrdenacao]:
    """Atalho usado pelo jogo: escolhe algoritmo e critério pelo nome."""
    if algoritmo not in ALGORITMOS:
        raise ValueError(f"algoritmo desconhecido: {algoritmo!r}. Opções: {sorted(ALGORITMOS)}")
    if criterio not in CRITERIOS:
        raise ValueError(f"critério desconhecido: {criterio!r}. Opções: {sorted(CRITERIOS)}")
    return ALGORITMOS[algoritmo](registros, chave=CRITERIOS[criterio], decrescente=decrescente)
