"""Grafo representado por lista de adjacência.

Para cada vértice guardamos uma ``ListaLigada`` com as arestas que saem dele.
Vantagens sobre a matriz de adjacência para o mapa do jogo (grafo esparso):
- memória O(V + E) em vez de O(V²);
- percorrer os vizinhos de v custa O(grau(v)), que é exatamente o que BFS e
  DFS fazem a cada expansão; no total, O(V + E).

Cada aresta pode ter uma PORTA, que exige um conjunto de pistas para ser
aberta. Conexões bidirecionais compartilham o mesmo id de porta: abrir em um
sentido abre nos dois.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from veridia.estruturas.lista_ligada import ListaLigada


@dataclass(frozen=True)
class Aresta:
    origem: str
    destino: str
    custo: int = 1
    porta: str | None = None
    pistas_exigidas: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        object.__setattr__(self, "pistas_exigidas", frozenset(self.pistas_exigidas))

    @property
    def condicionada(self) -> bool:
        return self.porta is not None


class Grafo:
    def __init__(self) -> None:
        self._adjacencia: dict[str, ListaLigada[Aresta]] = {}
        self._num_conexoes = 0

    def adicionar_vertice(self, vertice: str) -> None:
        if vertice in self._adjacencia:
            raise ValueError(f"vértice duplicado: {vertice!r}")
        self._adjacencia[vertice] = ListaLigada()

    def adicionar_aresta(
        self,
        origem: str,
        destino: str,
        custo: int = 1,
        porta: str | None = None,
        pistas_exigidas: frozenset[str] | set[str] = frozenset(),
        bidirecional: bool = True,
    ) -> None:
        for vertice in (origem, destino):
            if vertice not in self._adjacencia:
                raise KeyError(f"vértice inexistente: {vertice!r}")
        if origem == destino:
            raise ValueError("laços (origem == destino) não são permitidos")
        if custo <= 0:
            raise ValueError("custo deve ser positivo")
        if self.existe_aresta(origem, destino):
            raise ValueError(f"conexão duplicada: {origem} -> {destino}")
        exigidas = frozenset(pistas_exigidas)
        if exigidas and porta is None:
            raise ValueError("conexão que exige pistas precisa de um id de porta")
        if bidirecional and self.existe_aresta(destino, origem):
            raise ValueError(f"conexão duplicada: {destino} -> {origem}")
        self._adjacencia[origem].inserir_fim(Aresta(origem, destino, custo, porta, exigidas))
        if bidirecional:
            self._adjacencia[destino].inserir_fim(Aresta(destino, origem, custo, porta, exigidas))
        self._num_conexoes += 1

    def vizinhos(self, vertice: str) -> Iterator[Aresta]:
        """Arestas que saem de ``vertice``, na ordem de inserção. O(grau)."""
        if vertice not in self._adjacencia:
            raise KeyError(f"vértice inexistente: {vertice!r}")
        return iter(self._adjacencia[vertice])

    def aresta(self, origem: str, destino: str) -> Aresta | None:
        if origem not in self._adjacencia:
            return None
        return self._adjacencia[origem].buscar_por(lambda a: a.destino == destino)

    def existe_aresta(self, origem: str, destino: str) -> bool:
        return self.aresta(origem, destino) is not None

    def contem_vertice(self, vertice: str) -> bool:
        return vertice in self._adjacencia

    def vertices(self) -> list[str]:
        return list(self._adjacencia)

    def grau(self, vertice: str) -> int:
        return len(self._adjacencia[vertice])

    @property
    def num_vertices(self) -> int:
        return len(self._adjacencia)

    @property
    def num_conexoes(self) -> int:
        """Conexões cadastradas (uma bidirecional conta uma vez)."""
        return self._num_conexoes
