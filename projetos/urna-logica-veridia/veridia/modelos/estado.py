"""Estado do jogo e sua representação canônica.

O estado é a *configuração completa* do jogo em um instante — não apenas a
posição. Dois estados na mesma sala, mas com pistas diferentes, são estados
diferentes: o jogador com mais pistas pode abrir portas que o outro não pode.

A chave canônica (``EstadoJogo.chave``) é uma tupla de tipos simples, com os
conjuntos convertidos em tuplas ORDENADAS. Isso garante que:

1. estados equivalentes produzem chaves iguais, independentemente da ordem em
   que as pistas foram coletadas;
2. chaves são totalmente comparáveis com ``<``, requisito da árvore AVL.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

ChaveEstado = tuple[str, tuple[str, ...], tuple[str, ...], int]


@dataclass(frozen=True)
class EstadoJogo:
    """Configuração imutável do jogo.

    Atributos:
        posicao: id do vértice onde o jogador está.
        pistas: ids das evidências coletadas.
        portas_liberadas: ids das portas já abertas (permanecem abertas).
        energia: energia restante; cada movimento consome o custo da conexão.
    """

    posicao: str
    pistas: frozenset[str] = field(default_factory=frozenset)
    portas_liberadas: frozenset[str] = field(default_factory=frozenset)
    energia: int = 0

    def __post_init__(self) -> None:
        # Aceita set/list na construção, mas armazena sempre frozenset.
        object.__setattr__(self, "pistas", frozenset(self.pistas))
        object.__setattr__(self, "portas_liberadas", frozenset(self.portas_liberadas))

    def chave(self) -> ChaveEstado:
        """Representação canônica, hashable e comparável do estado.

        A energia faz parte da chave: dois estados idênticos exceto pela
        energia não são equivalentes, pois o de menor energia pode não
        conseguir completar o mesmo caminho.
        """
        return (
            self.posicao,
            tuple(sorted(self.pistas)),
            tuple(sorted(self.portas_liberadas)),
            self.energia,
        )

    def com(self, **alteracoes) -> "EstadoJogo":
        """Cria um novo estado alterando apenas os campos informados."""
        return replace(self, **alteracoes)

    def __str__(self) -> str:
        pistas = ",".join(sorted(self.pistas)) or "-"
        portas = ",".join(sorted(self.portas_liberadas)) or "-"
        return f"[{self.posicao} | pistas={pistas} | portas={portas} | energia={self.energia}]"
