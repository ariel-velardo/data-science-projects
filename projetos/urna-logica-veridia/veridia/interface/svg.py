"""Desenho em SVG do mapa (Fase 3 / Resolver) e da árvore AVL (Fase 4).

Funções puras: recebem os dados REAIS do motor (grafo, estado, árvore
serializada pela Fase 4) e devolvem texto SVG. Nada aqui decide regras: o
mapa pergunta a ``regras.motivo_bloqueio`` se cada conexão está liberada.

Somente as coordenadas de desenho dos locais são definidas aqui, porque o
modelo ``Mapa`` não tem posição geométrica (é um grafo abstrato).
"""

from __future__ import annotations

from html import escape
from typing import Any, Iterable

from veridia.jogo import regras
from veridia.modelos.estado import EstadoJogo
from veridia.modelos.mapa import Mapa

EVENTO_CLIQUE_LOCAL = "veridia_local"

LARGURA_MAPA, ALTURA_MAPA = 780, 450
POSICOES_MAPA: dict[str, tuple[int, int]] = {
    "BIBLIOTECA": (110, 70),
    "CARTORIO": (400, 62),
    "PRACA": (110, 215),
    "ESCOLA": (300, 200),
    "ARQUIVO": (490, 215),
    "TRIBUNAL": (690, 205),
    "MERCADO": (110, 360),
    "TORRE": (300, 395),
    "PONTE": (490, 360),
}

COR = {
    "agua": "#3fc7b3",
    "ambar": "#e3a948",
    "coral": "#e5686f",
    "linha": "#2a3848",
    "linha_clara": "#4a5d72",
    "grafite": "#212e3c",
    "fundo": "#08131f",
    "texto": "#dbe5ee",
    "suave": "#8fa1b3",
}


def _rotulo_curto(nome: str) -> str:
    return nome.split(" (")[0]


def posicoes_para(mapa: Mapa) -> dict[str, tuple[int, int]]:
    """Coordenadas de todos os vértices; vértices desconhecidos vão para uma faixa inferior."""
    posicoes = dict(POSICOES_MAPA)
    extras = [v for v in mapa.vertices if v not in posicoes]
    for i, vertice in enumerate(extras):
        posicoes[vertice] = (80 + i * 120, ALTURA_MAPA - 30)
    return posicoes


def svg_mapa(
    mapa: Mapa,
    estado: EstadoJogo,
    *,
    caminho: Iterable[str] | None = None,
    explorados: Iterable[str] | None = None,
    foco: str | None = None,
    clicavel: bool = True,
) -> str:
    """SVG do mapa no ``estado`` atual.

    - caminho: sequência de destinos sugerida pelo solver (desenhada a partir da posição atual);
    - explorados: locais já visitados pela busca (modo passo a passo);
    - foco: local do estado que a busca está expandindo agora;
    - clicavel: locais adjacentes e liberados emitem o evento de clique.
    """
    pos = posicoes_para(mapa)
    explorados_set = set(explorados or ())
    partes: list[str] = [
        f'<svg class="svg-mapa" viewBox="0 0 {LARGURA_MAPA} {ALTURA_MAPA}" role="img" '
        f'aria-label="Mapa de Verídia" xmlns="http://www.w3.org/2000/svg">'
    ]

    # Conexões (cada par desenhado uma vez)
    desenhadas: set[frozenset[str]] = set()
    liberados: set[str] = set()
    for vertice in mapa.grafo.vertices():
        for aresta in mapa.grafo.vizinhos(vertice):
            if aresta.origem == estado.posicao and regras.motivo_bloqueio(estado, aresta) is None:
                liberados.add(aresta.destino)
            par = frozenset((aresta.origem, aresta.destino))
            if par in desenhadas:
                continue
            desenhadas.add(par)
            (x1, y1), (x2, y2) = pos[aresta.origem], pos[aresta.destino]
            if aresta.porta is None:
                estilo = f'stroke="{COR["linha_clara"]}" stroke-width="2"'
            elif aresta.porta in estado.portas_liberadas:
                estilo = f'stroke="{COR["agua"]}" stroke-width="2" stroke-dasharray="2 5"'
            else:
                estilo = f'stroke="{COR["ambar"]}" stroke-width="2" stroke-dasharray="7 6"'
            partes.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {estilo}/>')
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if aresta.porta is not None and aresta.porta not in estado.portas_liberadas:
                exigidas = ", ".join(sorted(aresta.pistas_exigidas))
                partes.append(
                    f'<g><title>Porta {escape(aresta.porta)}: exige {escape(exigidas)}</title>'
                    f'<rect x="{mx - 9}" y="{my - 4}" width="18" height="14" rx="3" fill="{COR["ambar"]}"/>'
                    f'<path d="M{mx - 5} {my - 4} v-4 a5 5 0 0 1 10 0 v4" fill="none" stroke="{COR["ambar"]}" stroke-width="2"/></g>'
                )
            else:
                partes.append(
                    f'<text x="{mx}" y="{my - 6}" text-anchor="middle" font-size="12" fill="{COR["suave"]}" '
                    f'font-family="Consolas, monospace">{aresta.custo}</text>'
                )

    # Caminho sugerido
    sequencia = [estado.posicao] + list(caminho or ())
    if len(sequencia) > 1:
        pontos = " ".join(f"{pos[v][0]},{pos[v][1]}" for v in sequencia)
        partes.append(
            f'<polyline points="{pontos}" fill="none" stroke="{COR["agua"]}" stroke-width="7" '
            f'stroke-opacity="0.35" stroke-linejoin="round" stroke-linecap="round"/>'
        )

    # Locais
    for vertice_id, vertice in mapa.vertices.items():
        x, y = pos[vertice_id]
        atual = vertice_id == estado.posicao
        destino = vertice_id == mapa.destino
        pode_ir = clicavel and vertice_id in liberados
        if atual:
            preenchimento = COR["agua"]
        elif vertice_id == foco:
            preenchimento = COR["ambar"]
        elif vertice_id in explorados_set:
            preenchimento = "#1d4a4a"
        else:
            preenchimento = COR["grafite"]
        contorno = COR["agua"] if pode_ir else COR["linha_clara"]
        classe = "no-clicavel" if pode_ir else "no"
        evento = f' onclick="emitEvent(\'{EVENTO_CLIQUE_LOCAL}\', \'{vertice_id}\')"' if pode_ir else ""
        dica = "Clique para ir até aqui" if pode_ir else ("Você está aqui" if atual else vertice.nome)
        partes.append(f'<g class="{classe}" data-local="{vertice_id}"{evento}><title>{escape(dica)}</title>')
        if destino:
            partes.append(f'<circle cx="{x}" cy="{y}" r="33" fill="none" stroke="{COR["ambar"]}" stroke-width="2"/>')
        partes.append(
            f'<circle class="corpo" cx="{x}" cy="{y}" r="26" fill="{preenchimento}" stroke="{contorno}" stroke-width="2.5"/>'
        )
        if vertice.pista is not None:
            coletada = vertice.pista in estado.pistas
            partes.append(
                f'<circle cx="{x + 20}" cy="{y - 20}" r="7" fill="{COR["ambar"] if coletada else COR["fundo"]}" '
                f'stroke="{COR["ambar"]}" stroke-width="2"><title>Pista {escape(vertice.pista)}'
                f'{" (coletada)" if coletada else ""}</title></circle>'
            )
        partes.append(
            f'<text x="{x}" y="{y + 46}" text-anchor="middle" font-size="13" fill="{COR["texto"]}" '
            f'stroke="{COR["fundo"]}" stroke-width="5" paint-order="stroke" stroke-linejoin="round">'
            f"{escape(_rotulo_curto(vertice.nome))}</text></g>"
        )
    partes.append("</svg>")
    return "".join(partes)


# ----------------------------------------------------------------------
# Árvore AVL
# ----------------------------------------------------------------------
def _nos_em_ordem(no: dict[str, Any] | None, profundidade: int, saida: list[tuple[dict[str, Any], int]]) -> None:
    if no is None:
        return
    _nos_em_ordem(no.get("esquerda"), profundidade + 1, saida)
    saida.append((no, profundidade))
    _nos_em_ordem(no.get("direita"), profundidade + 1, saida)


def svg_arvore(arvore: dict[str, Any] | None, *, destaque: str | None = None, titulo: str = "Árvore AVL") -> str:
    """SVG de uma árvore serializada por ``fase4_cofre.serializar_arvore``.

    Posição horizontal = ordem em-ordem (chaves crescentes da esquerda para a
    direita); vertical = profundidade. Cada nó mostra rótulo, altura (h) e
    fator de balanceamento (f).
    """
    if arvore is None:
        return (
            f'<svg class="svg-arvore" viewBox="0 0 320 90" role="img" aria-label="{escape(titulo)}" '
            f'xmlns="http://www.w3.org/2000/svg"><text x="160" y="50" text-anchor="middle" font-size="14" '
            f'fill="{COR["suave"]}">Cofre vazio</text></svg>'
        )
    nos: list[tuple[dict[str, Any], int]] = []
    _nos_em_ordem(arvore, 0, nos)
    profundidade_max = max(p for _, p in nos)
    passo_x, passo_y, margem = 78, 78, 44
    largura = max(320, margem * 2 + passo_x * (len(nos) - 1))
    altura = margem * 2 + passo_y * profundidade_max + 20
    coordenadas = {id(no): (margem + i * passo_x, margem + p * passo_y) for i, (no, p) in enumerate(nos)}

    partes = [
        f'<svg class="svg-arvore" viewBox="0 0 {largura} {altura}" width="{largura}" height="{altura}" '
        f'role="img" aria-label="{escape(titulo)}" '
        f'xmlns="http://www.w3.org/2000/svg">'
    ]
    for no, _ in nos:
        x, y = coordenadas[id(no)]
        for filho in (no.get("esquerda"), no.get("direita")):
            if filho is not None:
                fx, fy = coordenadas[id(filho)]
                partes.append(f'<line x1="{x}" y1="{y}" x2="{fx}" y2="{fy}" stroke="{COR["linha_clara"]}" stroke-width="2"/>')
    for no, _ in nos:
        x, y = coordenadas[id(no)]
        rotulo = str(no.get("rotulo", "?"))
        fator = int(no.get("fator", 0))
        desbalanceado = abs(fator) > 1
        contorno = COR["coral"] if desbalanceado else (COR["ambar"] if rotulo == destaque else COR["agua"])
        partes.append(
            f'<g data-rotulo="{escape(rotulo)}"><title>{escape(str(no.get("chave", "")))}</title>'
            f'<circle cx="{x}" cy="{y}" r="22" fill="{COR["grafite"]}" stroke="{contorno}" stroke-width="2.5"/>'
            f'<text x="{x}" y="{y + 6}" text-anchor="middle" font-size="16" font-weight="700" fill="{COR["texto"]}">{escape(rotulo)}</text>'
            f'<text x="{x}" y="{y + 38}" text-anchor="middle" font-size="11.5" fill="{COR["coral"] if desbalanceado else COR["suave"]}" '
            f'font-family="Consolas, monospace">h={no.get("altura")} f={fator:+d}</text></g>'
        )
    partes.append("</svg>")
    return "".join(partes)
