"""Converte o logotipo vetorial do pacote Overleaf em SVG, sem alterar seus traçados."""
from __future__ import annotations

import re
import zlib

from .fontes import LOGO_PDF, RAIZ_PROJETO

_TOKEN = re.compile(rb"/[^\s/\[\]<>]+|[-+]?\d*\.?\d+|[A-Za-z*'\"]+|\[|\]|<<|>>|\([^)]*\)")


def _conteudo_pagina(pdf: bytes) -> bytes:
    partes: list[bytes] = []
    iniciou = False
    for inicio in re.finditer(rb"stream\r?\n", pdf):
        fim = pdf.find(b"endstream", inicio.end())
        try:
            parte = zlib.decompress(pdf[inicio.end():fim])
        except zlib.error:
            continue
        if parte.startswith(b"/Layer"):
            iniciou = True
        if parte.startswith(b"%!PS"):
            break
        if iniciou:
            partes.append(parte)
    if not partes:
        raise ValueError("Conteúdo vetorial do logotipo não encontrado")
    return b"".join(partes)


def _aplicar(m, x, y):
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def _multiplicar(a, b):
    return [
        a[0] * b[0] + a[1] * b[2],
        a[0] * b[1] + a[1] * b[3],
        a[2] * b[0] + a[3] * b[2],
        a[2] * b[1] + a[3] * b[3],
        a[4] * b[0] + a[5] * b[2] + b[4],
        a[4] * b[1] + a[5] * b[3] + b[5],
    ]


def _hex(cor: list[float]) -> str:
    return "#" + "".join(f"{round(c * 255):02X}" for c in cor)


def extrair() -> dict:
    """Interpreta o subconjunto de operadores PDF usado pelo arquivo do logotipo."""
    fluxo = _conteudo_pagina((RAIZ_PROJETO / LOGO_PDF).read_bytes())
    pilha_op: list[float] = []
    matriz = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    pilha_estado: list[tuple] = []
    cor = [0.0, 0.0, 0.0]
    caminho: list[tuple] = []
    atual = (0.0, 0.0)
    pintados: list[tuple[str, list[tuple]]] = []

    for token in _TOKEN.findall(fluxo):
        if re.fullmatch(rb"[-+]?\d*\.?\d+", token):
            pilha_op.append(float(token))
            continue
        if token.startswith((b"/", b"(", b"[", b"]", b"<", b">")):
            continue
        op = token.decode("ascii")
        if op == "q":
            pilha_estado.append((list(matriz), list(cor)))
        elif op == "Q":
            matriz, cor = pilha_estado.pop()
        elif op == "cm":
            matriz = _multiplicar(pilha_op[-6:], matriz)
        elif op == "rg":
            cor = pilha_op[-3:]
        elif op == "m":
            atual = (pilha_op[-2], pilha_op[-1])
            caminho.append(("M", _aplicar(matriz, *atual)))
        elif op == "l":
            atual = (pilha_op[-2], pilha_op[-1])
            caminho.append(("L", _aplicar(matriz, *atual)))
        elif op == "c":
            a, b, c, d, e, f = pilha_op[-6:]
            caminho.append(("C", _aplicar(matriz, a, b), _aplicar(matriz, c, d), _aplicar(matriz, e, f)))
            atual = (e, f)
        elif op == "v":
            c, d, e, f = pilha_op[-4:]
            caminho.append(("C", _aplicar(matriz, *atual), _aplicar(matriz, c, d), _aplicar(matriz, e, f)))
            atual = (e, f)
        elif op == "y":
            a, b, e, f = pilha_op[-4:]
            caminho.append(("C", _aplicar(matriz, a, b), _aplicar(matriz, e, f), _aplicar(matriz, e, f)))
            atual = (e, f)
        elif op == "h":
            caminho.append(("Z",))
        elif op == "re":
            x, y, w, h = pilha_op[-4:]
            caminho.append(("M", _aplicar(matriz, x, y)))
            caminho.append(("L", _aplicar(matriz, x + w, y)))
            caminho.append(("L", _aplicar(matriz, x + w, y + h)))
            caminho.append(("L", _aplicar(matriz, x, y + h)))
            caminho.append(("Z",))
        elif op in {"f", "F", "f*"}:
            pintados.append((_hex(cor), caminho))
            caminho = []
        elif op == "n":
            caminho = []
        pilha_op = []

    pontos = [p for _, c in pintados for seg in c for p in seg[1:]]
    x0, x1 = min(p[0] for p in pontos), max(p[0] for p in pontos)
    y0, y1 = min(p[1] for p in pontos), max(p[1] for p in pontos)

    def fmt(p):
        return f"{p[0] - x0:.2f} {y1 - p[1]:.2f}"

    trechos = []
    for preenchimento, caminho in pintados:
        d = "".join(
            seg[0] + " ".join(fmt(p) for p in seg[1:]) if len(seg) > 1 else "Z" for seg in caminho
        )
        trechos.append(f'<path fill="{preenchimento}" fill-rule="evenodd" d="{d}"/>')
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {x1 - x0:.2f} {y1 - y0:.2f}" '
        'role="img" aria-label="Logotipo do IPT">' + "".join(trechos) + "</svg>"
    )
    cores = sorted({preenchimento for preenchimento, _ in pintados})
    return {"svg": svg, "cores": cores}
