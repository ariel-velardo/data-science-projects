"""Mapa de uma fase: vértices (locais), conexões, pistas, portas e destino."""

from __future__ import annotations

from dataclasses import dataclass, field

from veridia.estruturas.grafo import Grafo
from veridia.modelos.evidencia import Evidencia


@dataclass(frozen=True)
class Vertice:
    id: str
    nome: str
    pista: str | None = None  # id da evidência encontrada neste local (se houver)


@dataclass
class Mapa:
    """Configuração estática de uma fase.

    O mapa NÃO muda durante o jogo; o que muda é o ``EstadoJogo``.

    Atributos:
        vertices: locais por id.
        grafo: conexões (lista de adjacência) com custos e portas.
        evidencias: catálogo de evidências por id.
        inicio / destino: ids dos vértices de partida e de chegada.
        pistas_necessarias: pistas que o jogador precisa ter para vencer.
        energia_inicial: energia disponível no começo da fase.
    """

    vertices: dict[str, Vertice]
    grafo: Grafo
    evidencias: dict[str, Evidencia]
    inicio: str
    destino: str
    pistas_necessarias: frozenset[str] = field(default_factory=frozenset)
    energia_inicial: int = 10

    def pista_em(self, vertice_id: str) -> str | None:
        return self.vertices[vertice_id].pista


def validar_mapa(mapa: Mapa) -> list[str]:
    """Checa a consistência interna do mapa. Lista vazia = mapa válido."""
    erros: list[str] = []
    ids_grafo = set(mapa.grafo.vertices())
    if ids_grafo != set(mapa.vertices):
        erros.append("vértices do grafo e do mapa não coincidem")
    for vertice_id, vertice in mapa.vertices.items():
        if vertice.id != vertice_id:
            erros.append(f"vértice {vertice_id!r} registrado com id {vertice.id!r}")
        if vertice.pista is not None and vertice.pista not in mapa.evidencias:
            erros.append(f"pista {vertice.pista!r} em {vertice_id!r} não existe no catálogo")
    if mapa.inicio not in mapa.vertices:
        erros.append(f"início inexistente: {mapa.inicio!r}")
    if mapa.destino not in mapa.vertices:
        erros.append(f"destino inexistente: {mapa.destino!r}")
    pistas_no_mapa = {v.pista for v in mapa.vertices.values() if v.pista is not None}
    faltando = set(mapa.pistas_necessarias) - pistas_no_mapa
    if faltando:
        erros.append(f"pistas necessárias que não estão em nenhum vértice: {sorted(faltando)}")
    for vertice_id in ids_grafo:
        for aresta in mapa.grafo.vizinhos(vertice_id):
            desconhecidas = aresta.pistas_exigidas - set(mapa.evidencias)
            if desconhecidas:
                erros.append(f"porta {aresta.porta!r} exige pistas inexistentes: {sorted(desconhecidas)}")
    if mapa.energia_inicial < 0:
        erros.append("energia inicial negativa")
    return erros
