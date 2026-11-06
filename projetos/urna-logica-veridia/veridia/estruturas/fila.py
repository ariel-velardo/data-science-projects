"""Fila FIFO (primeiro a entrar, primeiro a sair).

Implementada com nós encadeados e ponteiros para início e fim, de modo que
enfileirar e desenfileirar custam O(1). (Usar ``list.pop(0)`` do Python
custaria O(n), pois desloca todos os elementos.)

No jogo, a fila é a fronteira da Busca em Largura (BFS).
"""

from __future__ import annotations

from typing import Generic, Iterator, TypeVar

from veridia.estruturas.erros import EstruturaVaziaError

T = TypeVar("T")


class _No(Generic[T]):
    __slots__ = ("valor", "proximo")

    def __init__(self, valor: T) -> None:
        self.valor = valor
        self.proximo: _No[T] | None = None


class Fila(Generic[T]):
    def __init__(self) -> None:
        self._inicio: _No[T] | None = None
        self._fim: _No[T] | None = None
        self._tamanho = 0

    def enfileirar(self, valor: T) -> None:
        """enqueue: insere no fim. O(1)."""
        novo = _No(valor)
        if self._fim is None:
            self._inicio = novo
        else:
            self._fim.proximo = novo
        self._fim = novo
        self._tamanho += 1

    def desenfileirar(self) -> T:
        """dequeue: remove e devolve o elemento do início. O(1)."""
        if self._inicio is None:
            raise EstruturaVaziaError("desenfileirar() em fila vazia")
        no = self._inicio
        self._inicio = no.proximo
        if self._inicio is None:
            self._fim = None
        self._tamanho -= 1
        return no.valor

    def frente(self) -> T:
        """front/peek: consulta o início sem remover. O(1)."""
        if self._inicio is None:
            raise EstruturaVaziaError("frente() em fila vazia")
        return self._inicio.valor

    def esta_vazia(self) -> bool:
        """isEmpty. O(1)."""
        return self._tamanho == 0

    def __len__(self) -> int:
        return self._tamanho

    def __iter__(self) -> Iterator[T]:
        atual = self._inicio
        while atual is not None:
            yield atual.valor
            atual = atual.proximo

    def __repr__(self) -> str:
        return f"Fila({list(self)!r})"

    # Nomes do enunciado (aliases).
    enqueue = enfileirar
    dequeue = desenfileirar
    front = frente
    peek = frente
    isEmpty = esta_vazia
