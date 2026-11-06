"""Lista duplamente ligada.

Escolha: DUPLAMENTE ligada. Cada nó guarda referência ao anterior e ao
próximo, e a lista mantém ponteiros para início e fim. Com isso:

- inserir/remover no início ou no fim custa O(1) (na simplesmente ligada,
  remover no fim custaria O(n), pois seria preciso achar o penúltimo nó);
- o percurso pode ser feito nos dois sentidos (útil para "voltar" no
  histórico de ações do jogador).

O custo é um ponteiro extra por nó, irrelevante para o tamanho do jogo.

No jogo, a lista ligada é usada como lista de adjacência do grafo e pode
servir para o histórico de ações e o inventário de evidências.
"""

from __future__ import annotations

from typing import Any, Callable, Generic, Iterator, TypeVar

from veridia.estruturas.erros import EstruturaVaziaError

T = TypeVar("T")


class _No(Generic[T]):
    __slots__ = ("valor", "anterior", "proximo")

    def __init__(self, valor: T) -> None:
        self.valor = valor
        self.anterior: _No[T] | None = None
        self.proximo: _No[T] | None = None


class ListaLigada(Generic[T]):
    def __init__(self, valores: Any = None) -> None:
        self._inicio: _No[T] | None = None
        self._fim: _No[T] | None = None
        self._tamanho = 0
        if valores is not None:
            for valor in valores:
                self.inserir_fim(valor)

    # ---------- consultas ----------
    def __len__(self) -> int:
        return self._tamanho

    def esta_vazia(self) -> bool:
        return self._tamanho == 0

    def primeiro(self) -> T:
        """Valor do início. O(1)."""
        if self._inicio is None:
            raise EstruturaVaziaError("primeiro() em lista vazia")
        return self._inicio.valor

    def ultimo(self) -> T:
        """Valor do fim. O(1)."""
        if self._fim is None:
            raise EstruturaVaziaError("ultimo() em lista vazia")
        return self._fim.valor

    def buscar(self, valor: T) -> int:
        """Índice da primeira ocorrência de ``valor`` ou -1. O(n)."""
        for indice, atual in enumerate(self.percorrer()):
            if atual == valor:
                return indice
        return -1

    def buscar_por(self, predicado: Callable[[T], bool]) -> T | None:
        """Primeiro valor que satisfaz ``predicado`` ou None. O(n)."""
        for atual in self.percorrer():
            if predicado(atual):
                return atual
        return None

    def __contains__(self, valor: object) -> bool:
        return self.buscar(valor) != -1  # type: ignore[arg-type]

    def obter(self, indice: int) -> T:
        return self._no_em(indice).valor

    # ---------- percurso ----------
    def percorrer(self) -> Iterator[T]:
        """Percorre do início ao fim. O(n)."""
        atual = self._inicio
        while atual is not None:
            yield atual.valor
            atual = atual.proximo

    def percorrer_reverso(self) -> Iterator[T]:
        """Percorre do fim ao início. O(n)."""
        atual = self._fim
        while atual is not None:
            yield atual.valor
            atual = atual.anterior

    def __iter__(self) -> Iterator[T]:
        return self.percorrer()

    def para_lista(self) -> list[T]:
        return list(self.percorrer())

    def __repr__(self) -> str:
        return f"ListaLigada({self.para_lista()!r})"

    # ---------- inserção ----------
    def inserir_inicio(self, valor: T) -> None:
        novo = _No(valor)
        novo.proximo = self._inicio
        if self._inicio is None:
            self._fim = novo
        else:
            self._inicio.anterior = novo
        self._inicio = novo
        self._tamanho += 1

    def inserir_fim(self, valor: T) -> None:
        novo = _No(valor)
        novo.anterior = self._fim
        if self._fim is None:
            self._inicio = novo
        else:
            self._fim.proximo = novo
        self._fim = novo
        self._tamanho += 1

    def inserir_em(self, indice: int, valor: T) -> None:
        """Insere de modo que ``valor`` passe a ocupar ``indice`` (0..len)."""
        if not 0 <= indice <= self._tamanho:
            raise IndexError(f"índice {indice} fora do intervalo 0..{self._tamanho}")
        if indice == 0:
            self.inserir_inicio(valor)
            return
        if indice == self._tamanho:
            self.inserir_fim(valor)
            return
        seguinte = self._no_em(indice)
        anterior = seguinte.anterior
        assert anterior is not None
        novo = _No(valor)
        novo.anterior, novo.proximo = anterior, seguinte
        anterior.proximo = novo
        seguinte.anterior = novo
        self._tamanho += 1

    # ---------- remoção ----------
    def remover_inicio(self) -> T:
        if self._inicio is None:
            raise EstruturaVaziaError("remover_inicio() em lista vazia")
        no = self._inicio
        self._desligar(no)
        return no.valor

    def remover_fim(self) -> T:
        if self._fim is None:
            raise EstruturaVaziaError("remover_fim() em lista vazia")
        no = self._fim
        self._desligar(no)
        return no.valor

    def remover(self, valor: T) -> bool:
        """Remove a primeira ocorrência de ``valor``. Retorna False se não existir."""
        atual = self._inicio
        while atual is not None:
            if atual.valor == valor:
                self._desligar(atual)
                return True
            atual = atual.proximo
        return False

    def remover_em(self, indice: int) -> T:
        no = self._no_em(indice)
        self._desligar(no)
        return no.valor

    # ---------- auxiliares ----------
    def _no_em(self, indice: int) -> _No[T]:
        if not 0 <= indice < self._tamanho:
            raise IndexError(f"índice {indice} fora do intervalo 0..{self._tamanho - 1}")
        # Caminha pelo lado mais próximo (vantagem da lista dupla).
        if indice < self._tamanho // 2:
            atual = self._inicio
            for _ in range(indice):
                atual = atual.proximo  # type: ignore[union-attr]
        else:
            atual = self._fim
            for _ in range(self._tamanho - 1 - indice):
                atual = atual.anterior  # type: ignore[union-attr]
        assert atual is not None
        return atual

    def _desligar(self, no: _No[T]) -> None:
        if no.anterior is None:
            self._inicio = no.proximo
        else:
            no.anterior.proximo = no.proximo
        if no.proximo is None:
            self._fim = no.anterior
        else:
            no.proximo.anterior = no.anterior
        no.anterior = no.proximo = None
        self._tamanho -= 1
