"""Pilha LIFO (último a entrar, primeiro a sair).

Implementada com nós encadeados: o topo é o primeiro nó. Empilhar e
desempilhar custam O(1).

No jogo, a pilha é a fronteira da Busca em Profundidade (DFS) e pode ser
usada para "desfazer" a última ação no modo manual.
"""

from __future__ import annotations

from typing import Generic, Iterator, TypeVar

from veridia.estruturas.erros import EstruturaVaziaError

T = TypeVar("T")


class _No(Generic[T]):
    __slots__ = ("valor", "abaixo")

    def __init__(self, valor: T, abaixo: "_No[T] | None") -> None:
        self.valor = valor
        self.abaixo = abaixo


class Pilha(Generic[T]):
    def __init__(self) -> None:
        self._topo: _No[T] | None = None
        self._tamanho = 0

    def empilhar(self, valor: T) -> None:
        """push. O(1)."""
        self._topo = _No(valor, self._topo)
        self._tamanho += 1

    def desempilhar(self) -> T:
        """pop: remove e devolve o topo. O(1)."""
        if self._topo is None:
            raise EstruturaVaziaError("desempilhar() em pilha vazia")
        no = self._topo
        self._topo = no.abaixo
        self._tamanho -= 1
        return no.valor

    def topo(self) -> T:
        """peek/top: consulta o topo sem remover. O(1)."""
        if self._topo is None:
            raise EstruturaVaziaError("topo() em pilha vazia")
        return self._topo.valor

    def esta_vazia(self) -> bool:
        """isEmpty. O(1)."""
        return self._tamanho == 0

    def __len__(self) -> int:
        return self._tamanho

    def __iter__(self) -> Iterator[T]:
        """Percorre do topo para a base."""
        atual = self._topo
        while atual is not None:
            yield atual.valor
            atual = atual.abaixo

    def __repr__(self) -> str:
        return f"Pilha(topo→base {list(self)!r})"

    # Nomes do enunciado (aliases).
    push = empilhar
    pop = desempilhar
    peek = topo
    top = topo
    isEmpty = esta_vazia
