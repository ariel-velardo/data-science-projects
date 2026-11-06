"""Desenho em SVG do mapa (Fase 3 / Resolver), da árvore AVL (Fase 4) e do
perfil de ordem dos registros (Fase 1).

Funções puras: recebem os dados REAIS do motor (grafo, estado, árvore
serializada pela Fase 4, registros) e devolvem texto SVG. Nada aqui decide
regras: o mapa pergunta a ``regras.motivo_bloqueio`` se cada conexão está
liberada.

Somente as coordenadas de desenho dos locais (e o lado do rótulo) são
definidas aqui, porque o modelo ``Mapa`` não tem posição geométrica.
"""

from __future__ import annotations

from html import escape
from typing import Any, Iterable, Sequence

from veridia.jogo import regras
from veridia.modelos.estado import EstadoJogo
from veridia.modelos.mapa import Mapa

EVENTO_CLIQUE_LOCAL = "veridia_local"

LARGURA_MAPA, ALTURA_MAPA = 980, 556
RAIO_LOCAL = 24
POSICOES_MAPA: dict[str, tuple[int, int]] = {
    "BIBLIOTECA": (210, 92),
    "CARTORIO": (500, 92),
    "PRACA": (210, 258),
    "ESCOLA": (380, 258),
    "ARQUIVO": (560, 258),
    "TRIBUNAL": (790, 258),
    "MERCADO": (210, 398),
    "TORRE": (385, 472),
    "PONTE": (560, 398),
}
# Lado do rótulo de cada local, escolhido para não cruzar conexões.
LADO_ROTULO: dict[str, str] = {
    "BIBLIOTECA": "acima",
    "CARTORIO": "acima",
    "PRACA": "esquerda",
    "ESCOLA": "abaixo",
    "ARQUIVO": "acima",
    "TRIBUNAL": "direita",
    "MERCADO": "esquerda",
    "TORRE": "abaixo",
    "PONTE": "abaixo",
}

COR = {
    "profundo": "#0B2038",
    "prancha2": "#11294A",
    "institucional": "#163E63",
    "medio": "#1679AC",
    "ciano": "#76C8EC",
    "branco": "#ECF6FB",
    "suave": "#9FBAD1",
    "linha": "#3B6187",
    "linha_fraca": "#22456B",
    "explorado": "#2E6E9E",
    "ambar": "#F0B04A",
    "erro": "#F2897F",
}
FONTE_SVG = "Bahnschrift, 'Segoe UI', system-ui, sans-serif"


def _rotulo_curto(nome: str) -> str:
    return nome.split(" (")[0]


def _nome_pista(pista: str) -> str:
    return pista.replace("_", " ")


def posicoes_para(mapa: Mapa) -> dict[str, tuple[int, int]]:
    """Coordenadas de todos os vértices; vértices desconhecidos vão para uma faixa inferior."""
    posicoes = dict(POSICOES_MAPA)
    extras = [v for v in mapa.vertices if v not in posicoes]
    for i, vertice in enumerate(extras):
        posicoes[vertice] = (80 + i * 120, ALTURA_MAPA - 30)
    return posicoes


def _texto(x: float, y: float, conteudo: str, *, tamanho: float = 15, cor: str = COR["branco"],
           ancora: str = "middle", peso: int = 600, halo: bool = True) -> str:
    contorno = (f' stroke="{COR["profundo"]}" stroke-width="5" paint-order="stroke" stroke-linejoin="round"'
                if halo else "")
    return (f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="{ancora}" font-size="{tamanho}" font-weight="{peso}" '
            f'font-family="{FONTE_SVG}" fill="{cor}"{contorno}>{escape(conteudo)}</text>')


def _rotulos_local(x: int, y: int, lado: str, nome: str, sub: str | None, cor_sub: str) -> str:
    """Nome do local e uma linha de apoio (pista ou destino) no lado escolhido."""
    r = RAIO_LOCAL
    if lado == "acima":
        linhas = [(x, y - r - (28 if sub else 12), "middle")] + ([(x, y - r - 11, "middle")] if sub else [])
    elif lado == "esquerda":
        linhas = [(x - r - 12, y + (0 if sub else 5), "end")] + ([(x - r - 12, y + 17, "end")] if sub else [])
    elif lado == "direita":
        linhas = [(x + r + 12, y + (0 if sub else 5), "start")] + ([(x + r + 12, y + 17, "start")] if sub else [])
    else:  # abaixo
        linhas = [(x, y + r + 19, "middle")] + ([(x, y + r + 35, "middle")] if sub else [])
    partes = [_texto(linhas[0][0], linhas[0][1], nome, ancora=linhas[0][2])]
    if sub:
        partes.append(_texto(linhas[1][0], linhas[1][1], sub, tamanho=12.5, cor=cor_sub, ancora=linhas[1][2], peso=400))
    return "".join(partes)


def _cadeado(x: float, y: float, cor: str) -> str:
    return (f'<rect x="{x - 5:.1f}" y="{y - 1:.1f}" width="10" height="8" rx="1.5" fill="{cor}"/>'
            f'<path d="M{x - 3:.1f} {y - 1:.1f} v-3 a3 3 0 0 1 6 0 v3" fill="none" stroke="{cor}" stroke-width="1.6"/>')


def svg_mapa(
    mapa: Mapa,
    estado: EstadoJogo,
    *,
    caminho: Iterable[str] | None = None,
    explorados: Iterable[str] | None = None,
    foco: str | None = None,
    clicavel: bool = True,
    rota: Sequence[str] | None = None,
) -> str:
    """SVG do mapa no ``estado`` atual.

    - caminho: sequência de destinos sugerida pelo solver (desenhada a partir da posição atual);
    - explorados: locais já expandidos pela busca (modo passo a passo);
    - foco: local que a busca está expandindo agora;
    - clicavel: locais adjacentes e liberados emitem o evento de clique;
    - rota: posições do caminho final encontrado pelo solver, desde o início (traço fino).
    """
    pos = posicoes_para(mapa)
    explorados_set = set(explorados or ())
    partes: list[str] = [
        f'<svg class="svg-mapa" viewBox="0 0 {LARGURA_MAPA} {ALTURA_MAPA}" role="img" '
        f'aria-label="Mapa de Verídia" xmlns="http://www.w3.org/2000/svg">'
    ]

    # Conexões liberadas a partir da posição atual (perguntando às regras).
    liberados: set[str] = set()
    for aresta in mapa.grafo.vizinhos(estado.posicao):
        if regras.motivo_bloqueio(estado, aresta) is None:
            liberados.add(aresta.destino)

    # Conexões (cada par desenhado uma vez) e, depois, os marcadores de custo/porta por cima.
    desenhadas: set[frozenset[str]] = set()
    marcadores: list[str] = []
    for vertice in mapa.grafo.vertices():
        for aresta in mapa.grafo.vizinhos(vertice):
            par = frozenset((aresta.origem, aresta.destino))
            if par in desenhadas:
                continue
            desenhadas.add(par)
            (x1, y1), (x2, y2) = pos[aresta.origem], pos[aresta.destino]
            saindo_daqui = clicavel and estado.posicao in par and (par - {estado.posicao}) <= liberados
            trancada = aresta.porta is not None and aresta.porta not in estado.portas_liberadas
            if trancada:
                estilo = f'stroke="{COR["ambar"]}" stroke-width="2.5" stroke-dasharray="8 6"'
            elif aresta.porta is not None:
                estilo = f'stroke="{COR["ciano"]}" stroke-width="2.5" stroke-dasharray="3 5"'
            elif saindo_daqui:
                estilo = f'stroke="{COR["ciano"]}" stroke-width="3"'
            else:
                estilo = f'stroke="{COR["linha"]}" stroke-width="2.5"'
            partes.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {estilo} stroke-linecap="round"/>')

            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if trancada:
                exigidas = ", ".join(_nome_pista(p) for p in sorted(aresta.pistas_exigidas))
                marcadores.append(
                    f'<g><title>Porta {escape(aresta.porta)}: exige {escape(exigidas)}</title>'
                    f'<rect x="{mx - 23:.1f}" y="{my - 12:.1f}" width="46" height="24" rx="12" fill="{COR["profundo"]}" '
                    f'stroke="{COR["ambar"]}" stroke-width="1.6"/>'
                    f'{_cadeado(mx - 8, my - 1, COR["ambar"])}'
                    f'{_texto(mx + 9, my + 5, str(aresta.custo), tamanho=13.5, cor=COR["ambar"], halo=False)}</g>'
                )
            else:
                dica = (f"Passagem {aresta.porta} liberada; custo {aresta.custo}" if aresta.porta
                        else f"Custo {aresta.custo} de energia")
                cor = COR["ciano"] if (aresta.porta or saindo_daqui) else COR["suave"]
                marcadores.append(
                    f'<g><title>{escape(dica)}</title>'
                    f'<rect x="{mx - 13:.1f}" y="{my - 11:.1f}" width="26" height="22" rx="11" fill="{COR["profundo"]}" '
                    f'stroke="{COR["linha_fraca"] if cor == COR["suave"] else cor}" stroke-width="1.4"/>'
                    f'{_texto(mx, my + 5, str(aresta.custo), tamanho=13.5, cor=cor, halo=False)}</g>'
                )

    # Rota final encontrada pelo solver (Resolver), desde o início.
    if rota and len(rota) > 1:
        d = " ".join(("M" if i == 0 else "L") + f"{pos[v][0]} {pos[v][1]}" for i, v in enumerate(rota))
        partes.append(
            f'<path d="{d}" fill="none" stroke="{COR["ciano"]}" stroke-width="2" stroke-dasharray="1 7" '
            f'stroke-linecap="round" opacity="0.9"><title>Caminho encontrado pelo solver</title></path>'
        )

    # Caminho sugerido a partir da posição atual (Fase 3), com a ordem dos passos.
    sequencia = [estado.posicao] + list(caminho or ())
    passos_por_local: dict[str, list[int]] = {}
    if len(sequencia) > 1:
        pontos = " ".join(f"{pos[v][0]},{pos[v][1]}" for v in sequencia)
        partes.append(
            f'<polyline points="{pontos}" fill="none" stroke="{COR["ciano"]}" stroke-width="12" '
            f'stroke-opacity="0.28" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for passo, local in enumerate(sequencia[1:], start=1):
            passos_por_local.setdefault(local, []).append(passo)

    partes.extend(marcadores)

    # Locais
    for vertice_id, vertice in mapa.vertices.items():
        x, y = pos[vertice_id]
        atual = vertice_id == estado.posicao
        destino = vertice_id == mapa.destino
        pode_ir = clicavel and vertice_id in liberados
        if atual:
            preenchimento = COR["ciano"]
        elif vertice_id == foco:
            preenchimento = COR["ambar"]
        elif vertice_id in explorados_set:
            preenchimento = COR["explorado"]
        else:
            preenchimento = COR["prancha2"]
        contorno = COR["ciano"] if pode_ir else (COR["branco"] if atual else COR["linha"])
        nome = _rotulo_curto(vertice.nome)
        if pode_ir:
            chamada = f"emitEvent('{EVENTO_CLIQUE_LOCAL}', '{vertice_id}')"
            abertura = (
                f'<g class="no-clicavel" data-local="{vertice_id}" role="button" tabindex="0" '
                f'aria-label="Ir para {escape(nome)}" onclick="{chamada}" '
                f'onkeydown="if(event.key===\'Enter\'||event.key===\' \'){{event.preventDefault();{chamada}}}">'
                f'<title>Clique para ir até {escape(nome)}</title>'
            )
        else:
            dica = "Você está aqui" if atual else vertice.nome
            abertura = f'<g class="no" data-local="{vertice_id}"><title>{escape(dica)}</title>'
        partes.append(abertura)
        if destino:
            partes.append(
                f'<circle cx="{x}" cy="{y}" r="{RAIO_LOCAL + 8}" fill="none" stroke="{COR["branco"]}" '
                f'stroke-width="1.5" stroke-dasharray="4 4"/>'
            )
        if atual:
            partes.append(f'<circle cx="{x}" cy="{y}" r="{RAIO_LOCAL + 6}" fill="{COR["ciano"]}" opacity="0.22"/>')
        partes.append(
            f'<circle class="corpo" cx="{x}" cy="{y}" r="{RAIO_LOCAL}" fill="{preenchimento}" '
            f'stroke="{contorno}" stroke-width="{3 if pode_ir else 2}"/>'
        )
        if atual:  # marcador de "você": cabeça e ombros
            partes.append(
                f'<circle cx="{x}" cy="{y - 6}" r="5.5" fill="{COR["profundo"]}"/>'
                f'<path d="M{x - 10} {y + 12} a10 9 0 0 1 20 0 z" fill="{COR["profundo"]}"/>'
            )
        elif destino:  # bandeira de chegada
            partes.append(
                f'<path d="M{x - 6} {y + 11} V{y - 11}" stroke="{COR["branco"]}" stroke-width="2"/>'
                f'<path d="M{x - 5} {y - 11} h13 l-4 5 l4 5 h-13 z" fill="{COR["branco"]}"/>'
            )
        if vertice.pista is not None:
            coletada = vertice.pista in estado.pistas
            px, py = x + 18, y - 18
            partes.append(
                f'<rect x="{px - 6}" y="{py - 6}" width="12" height="12" transform="rotate(45 {px} {py})" '
                f'fill="{COR["ambar"] if coletada else COR["profundo"]}" stroke="{COR["ambar"]}" stroke-width="2">'
                f'<title>Pista {escape(_nome_pista(vertice.pista))}{" (coletada)" if coletada else ""}</title></rect>'
            )
        if passos_por_local.get(vertice_id):
            numeros = ",".join(map(str, passos_por_local[vertice_id]))
            largura = 12 + 8 * len(numeros)
            bx, by = x - RAIO_LOCAL - 2, y + RAIO_LOCAL - 4
            partes.append(
                f'<rect x="{bx - largura / 2:.1f}" y="{by - 10}" width="{largura}" height="20" rx="10" fill="{COR["ciano"]}"/>'
                f'{_texto(bx, by + 4.5, numeros, tamanho=12.5, cor=COR["profundo"], halo=False)}'
            )
        if destino:
            sub, cor_sub = "destino", COR["branco"]
        elif vertice.pista is not None:
            sub, cor_sub = f"pista: {_nome_pista(vertice.pista)}", COR["ambar"]
        else:
            sub, cor_sub = None, COR["suave"]
        partes.append(_rotulos_local(x, y, LADO_ROTULO.get(vertice_id, "abaixo"), nome, sub, cor_sub))
        partes.append("</g>")
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


def _pais(no: dict[str, Any] | None, pai: str | None = None, saida: dict[str, str | None] | None = None) -> dict[str, str | None]:
    saida = {} if saida is None else saida
    if no is not None:
        rotulo = str(no.get("rotulo"))
        saida[rotulo] = pai
        _pais(no.get("esquerda"), rotulo, saida)
        _pais(no.get("direita"), rotulo, saida)
    return saida


def nos_reposicionados(antes: dict[str, Any] | None, depois: dict[str, Any] | None) -> set[str]:
    """Rótulos que já estavam na árvore e mudaram de pai entre ``antes`` e ``depois``.

    Só compara as duas árvores serializadas pelo motor: serve para destacar,
    no desenho, os nós deslocados pela rotação.
    """
    pais_antes, pais_depois = _pais(antes), _pais(depois)
    return {r for r, pai in pais_depois.items() if r in pais_antes and pais_antes[r] != pai}


def svg_arvore(
    arvore: dict[str, Any] | None,
    *,
    destaque: str | None = None,
    titulo: str = "Árvore AVL",
    movidos: Iterable[str] = (),
) -> str:
    """SVG de uma árvore serializada por ``fase4_cofre.serializar_arvore``.

    Posição horizontal = ordem em-ordem (chaves crescentes da esquerda para a
    direita); vertical = profundidade. Cada nó mostra rótulo, altura (h) e
    fator de balanceamento (f). ``destaque`` marca o nó recém-inserido e
    ``movidos`` os nós que mudaram de lugar em uma rotação.
    """
    if arvore is None:
        return (
            f'<svg class="svg-arvore" viewBox="0 0 320 90" role="img" aria-label="{escape(titulo)}" '
            f'xmlns="http://www.w3.org/2000/svg">{_texto(160, 50, "Cofre vazio", tamanho=14, cor=COR["suave"], halo=False, peso=400)}</svg>'
        )
    movidos_set = set(movidos)
    nos: list[tuple[dict[str, Any], int]] = []
    _nos_em_ordem(arvore, 0, nos)
    profundidade_max = max(p for _, p in nos)
    passo_x, passo_y, margem = 74, 84, 40
    ocupado = margem * 2 + passo_x * (len(nos) - 1)
    largura = max(300, ocupado)
    deslocamento = (largura - ocupado) // 2  # centraliza árvores pequenas
    altura = margem * 2 + passo_y * profundidade_max + 24
    coordenadas = {id(no): (deslocamento + margem + i * passo_x, margem + p * passo_y) for i, (no, p) in enumerate(nos)}

    partes = [
        f'<svg class="svg-arvore" viewBox="0 0 {largura} {altura}" width="{largura}" height="{altura}" '
        f'role="img" aria-label="{escape(titulo)}" xmlns="http://www.w3.org/2000/svg">'
    ]
    for no, _ in nos:
        x, y = coordenadas[id(no)]
        for filho in (no.get("esquerda"), no.get("direita")):
            if filho is not None:
                fx, fy = coordenadas[id(filho)]
                partes.append(f'<line x1="{x}" y1="{y}" x2="{fx}" y2="{fy}" stroke="{COR["linha"]}" stroke-width="2"/>')
    for no, _ in nos:
        x, y = coordenadas[id(no)]
        rotulo = str(no.get("rotulo", "?"))
        fator = int(no.get("fator", 0))
        desbalanceado = abs(fator) > 1
        inserido = rotulo == destaque
        if desbalanceado:
            contorno, preenchimento, cor_rotulo = COR["erro"], COR["prancha2"], COR["branco"]
        elif inserido:
            contorno, preenchimento, cor_rotulo = COR["ciano"], COR["ciano"], COR["profundo"]
        else:
            contorno, preenchimento, cor_rotulo = COR["ciano"], COR["prancha2"], COR["branco"]
        cor_fator = COR["erro"] if desbalanceado else (COR["ciano"] if fator else COR["suave"])
        notas = []
        if inserido:
            notas.append("recém-inserido")
        if rotulo in movidos_set:
            notas.append("mudou de posição na rotação")
        dica = f'{no.get("chave", "")}' + (f" ({'; '.join(notas)})" if notas else "")
        partes.append(f'<g data-rotulo="{escape(rotulo)}"><title>{escape(dica)}</title>')
        if rotulo in movidos_set:
            partes.append(
                f'<circle cx="{x}" cy="{y}" r="28" fill="none" stroke="{COR["ambar"]}" stroke-width="2" stroke-dasharray="4 3"/>'
            )
        texto_altura = f"h={no.get('altura')}"
        texto_fator = f"f={fator:+d}"
        partes.append(
            f'<circle cx="{x}" cy="{y}" r="21" fill="{preenchimento}" stroke="{contorno}" stroke-width="2.5"/>'
            + _texto(x, y + 6, rotulo, tamanho=17, cor=cor_rotulo, halo=False)
            + _texto(x - 3, y + 40, texto_altura, tamanho=11.5, cor=COR["suave"], ancora="end", peso=400)
            + _texto(x + 3, y + 40, texto_fator, tamanho=11.5, cor=cor_fator, ancora="start")
            + "</g>"
        )
    partes.append("</svg>")
    return "".join(partes)


# ----------------------------------------------------------------------
# Fase 1: perfil de ordem dos registros
# ----------------------------------------------------------------------
def svg_perfil_ordem(valores: Sequence[float], *, rotulo: str = "Perfil de zona e seção") -> str:
    """Barras na ordem atual dos registros; altura = zona e seção do registro.

    Um arquivo em ordem forma uma escada crescente. Barras em âmbar marcam
    uma queda em relação à anterior (onde a sequência quebra).
    """
    n = len(valores)
    if n == 0:
        return ""
    largura, altura = 600, 56
    menor, maior = min(valores), max(valores)
    faixa = (maior - menor) or 1
    passo = largura / n
    partes = [
        f'<svg class="perfil-ordem" viewBox="0 0 {largura} {altura}" preserveAspectRatio="none" role="img" '
        f'aria-label="{escape(rotulo)}" xmlns="http://www.w3.org/2000/svg">'
    ]
    for i, valor in enumerate(valores):
        h = 8 + (altura - 10) * (valor - menor) / faixa
        quebra = i > 0 and valor < valores[i - 1]
        cor = COR["ambar"] if quebra else COR["ciano"]
        partes.append(
            f'<rect x="{i * passo + 1:.1f}" y="{altura - h:.1f}" width="{max(passo - 2, 1):.1f}" height="{h:.1f}" '
            f'rx="1" fill="{cor}"/>'
        )
    partes.append("</svg>")
    return "".join(partes)
