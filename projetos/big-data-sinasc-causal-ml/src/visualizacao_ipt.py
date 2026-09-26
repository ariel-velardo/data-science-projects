"""Tema acadêmico Plotly inspirado na identidade visual do IPT."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

CORES_IPT = {
    "AZUL_PRINCIPAL": "#00598E",
    "AZUL_ESCURO": "#133C5A",
    "CIANO": "#04B4E3",
    "AZUL_MEDIO": "#226986",
    "AZUL_CLARO": "#82B0C6",
    "BRANCO": "#FFFFFF",
    "CINZA_FUNDO": "#F5F7F9",
    "CINZA_GRADE": "#D9E7EE",
}

PALETA_IPT = [
    CORES_IPT["AZUL_PRINCIPAL"],
    CORES_IPT["CIANO"],
    CORES_IPT["AZUL_MEDIO"],
    CORES_IPT["AZUL_CLARO"],
    CORES_IPT["AZUL_ESCURO"],
]

TEMPLATE_PLOTLY_IPT = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor=CORES_IPT["BRANCO"],
        plot_bgcolor=CORES_IPT["BRANCO"],
        font={"family": "Arial", "color": CORES_IPT["AZUL_ESCURO"], "size": 13},
        colorway=PALETA_IPT,
        title={"font": {"color": CORES_IPT["AZUL_ESCURO"], "size": 20}, "x": 0.02},
        margin={"l": 65, "r": 35, "t": 75, "b": 60},
        legend={"orientation": "h", "y": -0.2, "x": 0},
        xaxis={"showline": True, "linecolor": CORES_IPT["CINZA_GRADE"], "gridcolor": CORES_IPT["CINZA_GRADE"], "zeroline": False},
        yaxis={"showline": True, "linecolor": CORES_IPT["CINZA_GRADE"], "gridcolor": CORES_IPT["CINZA_GRADE"], "zeroline": False},
    )
)


def configurar_plotly() -> None:
    """Registra e ativa o tema comum do projeto."""

    pio.templates["ipt_academico"] = TEMPLATE_PLOTLY_IPT
    pio.templates.default = "ipt_academico"
    pio.renderers.default = "png"


def aplicar_tema_ipt(figura: go.Figure, titulo: str | None = None) -> go.Figure:
    """Aplica o tema e um título opcional a uma figura Plotly."""

    figura.update_layout(template=TEMPLATE_PLOTLY_IPT)
    if titulo:
        figura.update_layout(title=titulo)
    return figura
