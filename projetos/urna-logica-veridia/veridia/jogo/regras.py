"""Regras do jogo — fonte ÚNICA de verdade para o modo manual e para o solver.

Todas as funções são puras: recebem um ``EstadoJogo`` e devolvem um NOVO
estado (o original nunca é alterado). Isso permite que o solver explore
vários futuros a partir do mesmo estado sem efeitos colaterais.

Regras desta fundação:
1. O jogador começa em ``mapa.inicio`` com ``mapa.energia_inicial``.
2. Um movimento percorre UMA conexão a partir da posição atual e consome o
   custo dessa conexão em energia. Sem energia suficiente, não há movimento.
3. Conexões com porta exigem as pistas indicadas na primeira passagem.
   Depois de aberta, a porta fica registrada em ``portas_liberadas`` e não
   exige mais as pistas.
4. Ao chegar a um local com pista, ela é coletada automaticamente.
5. Vitória: estar no destino com todas as ``pistas_necessarias``.
"""

from __future__ import annotations

from dataclasses import dataclass

from veridia.estruturas.grafo import Aresta
from veridia.modelos.estado import EstadoJogo
from veridia.modelos.mapa import Mapa


class MovimentoInvalidoError(ValueError):
    """Tentativa de executar um movimento que as regras não permitem."""


@dataclass(frozen=True)
class Movimento:
    """Ação "ir de ``origem`` até ``destino``"."""

    origem: str
    destino: str
    custo: int
    porta_aberta: str | None = None  # porta aberta POR este movimento (se houver)

    def __str__(self) -> str:
        porta = f" (abre {self.porta_aberta})" if self.porta_aberta else ""
        return f"{self.origem} -> {self.destino} [custo {self.custo}]{porta}"


def coletar_pista(mapa: Mapa, estado: EstadoJogo) -> EstadoJogo:
    """Coleta a pista do local atual, se houver e ainda não tiver sido coletada."""
    pista = mapa.pista_em(estado.posicao)
    if pista is None or pista in estado.pistas:
        return estado
    return estado.com(pistas=estado.pistas | {pista})


def estado_inicial(mapa: Mapa) -> EstadoJogo:
    """Estado de partida (já coleta a pista do local inicial, se existir)."""
    return coletar_pista(mapa, EstadoJogo(posicao=mapa.inicio, energia=mapa.energia_inicial))


def motivo_bloqueio(estado: EstadoJogo, aresta: Aresta) -> str | None:
    """Explica por que a conexão não pode ser usada agora (None = permitido)."""
    if aresta.custo > estado.energia:
        return f"energia insuficiente: precisa de {aresta.custo}, tem {estado.energia}"
    if aresta.porta is not None and aresta.porta not in estado.portas_liberadas:
        faltando = aresta.pistas_exigidas - estado.pistas
        if faltando:
            return f"porta {aresta.porta!r} trancada: faltam as pistas {sorted(faltando)}"
    return None


def validar_movimento(mapa: Mapa, estado: EstadoJogo, destino: str) -> tuple[bool, str]:
    """Valida o movimento para ``destino``. Retorna (permitido, mensagem)."""
    if not mapa.grafo.contem_vertice(destino):
        return False, f"local inexistente: {destino!r}"
    aresta = mapa.grafo.aresta(estado.posicao, destino)
    if aresta is None:
        return False, f"não há conexão entre {estado.posicao} e {destino}"
    motivo = motivo_bloqueio(estado, aresta)
    if motivo is not None:
        return False, motivo
    return True, "movimento permitido"


def _aplicar(mapa: Mapa, estado: EstadoJogo, aresta: Aresta) -> tuple[Movimento, EstadoJogo]:
    """Aplica uma aresta já validada."""
    porta_aberta = None
    portas = estado.portas_liberadas
    if aresta.porta is not None and aresta.porta not in portas:
        porta_aberta = aresta.porta
        portas = portas | {aresta.porta}
    novo = estado.com(posicao=aresta.destino, energia=estado.energia - aresta.custo, portas_liberadas=portas)
    novo = coletar_pista(mapa, novo)
    return Movimento(aresta.origem, aresta.destino, aresta.custo, porta_aberta), novo


def mover(mapa: Mapa, estado: EstadoJogo, destino: str) -> tuple[Movimento, EstadoJogo]:
    """Executa o movimento (usado pelo modo manual). Levanta erro se inválido."""
    permitido, mensagem = validar_movimento(mapa, estado, destino)
    if not permitido:
        raise MovimentoInvalidoError(mensagem)
    aresta = mapa.grafo.aresta(estado.posicao, destino)
    assert aresta is not None
    return _aplicar(mapa, estado, aresta)


def gerar_sucessores(mapa: Mapa, estado: EstadoJogo) -> list[tuple[Movimento, EstadoJogo]]:
    """Todos os pares (movimento, novo estado) permitidos a partir de ``estado``.

    A ordem segue a lista de adjacência do grafo, o que torna BFS e DFS
    determinísticas. Custo: O(grau(posição)).
    """
    sucessores: list[tuple[Movimento, EstadoJogo]] = []
    for aresta in mapa.grafo.vizinhos(estado.posicao):
        if motivo_bloqueio(estado, aresta) is None:
            sucessores.append(_aplicar(mapa, estado, aresta))
    return sucessores


def verificar_vitoria(mapa: Mapa, estado: EstadoJogo) -> bool:
    return estado.posicao == mapa.destino and mapa.pistas_necessarias <= estado.pistas


def reproduzir_caminho(mapa: Mapa, destinos: list[str], inicial: EstadoJogo | None = None) -> EstadoJogo:
    """Aplica uma sequência de destinos com as regras (útil para validar soluções)."""
    estado = inicial if inicial is not None else estado_inicial(mapa)
    for destino in destinos:
        _, estado = mover(mapa, estado, destino)
    return estado
