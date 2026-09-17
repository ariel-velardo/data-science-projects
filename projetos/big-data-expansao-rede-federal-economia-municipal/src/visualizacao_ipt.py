"""Identidade visual acadêmica inspirada na paleta institucional do IPT.

As cores são uma aproximação visual de referência, não códigos oficiais de
manual de marca. Este módulo concentra apenas escolhas de apresentação.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

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
        title={"font": {"color": CORES_IPT["AZUL_ESCURO"], "size": 20}, "x": 0.02, "xanchor": "left"},
        margin={"l": 60, "r": 35, "t": 70, "b": 55},
        legend={"orientation": "h", "y": -0.18, "x": 0, "xanchor": "left"},
        hoverlabel={"bgcolor": CORES_IPT["BRANCO"], "font": {"family": "Arial", "color": CORES_IPT["AZUL_ESCURO"]}},
        xaxis={"showline": True, "linecolor": CORES_IPT["CINZA_GRADE"], "gridcolor": CORES_IPT["CINZA_GRADE"], "zeroline": False},
        yaxis={"showline": True, "linecolor": CORES_IPT["CINZA_GRADE"], "gridcolor": CORES_IPT["CINZA_GRADE"], "zeroline": False},
    )
)


def aplicar_tema_ipt(fig: go.Figure, *, titulo: str | None = None) -> go.Figure:
    """Aplica o tema comum e mantém o gráfico pronto para ajustes específicos."""
    fig.update_layout(
        template=TEMPLATE_PLOTLY_IPT,
        paper_bgcolor=CORES_IPT["BRANCO"],
        plot_bgcolor=CORES_IPT["BRANCO"],
        font={"family": "Arial", "color": CORES_IPT["AZUL_ESCURO"], "size": 13},
    )
    if titulo is not None:
        fig.update_layout(title=titulo)
    return fig


def salvar_figura_ipt(fig: go.Figure, caminho_png: Path) -> Path:
    """Salva PNG quando Kaleido existe; sem ele, preserva a figura em HTML local."""
    try:
        fig.write_image(caminho_png, scale=2)
        return caminho_png
    except (ImportError, ValueError, RuntimeError):
        # Plotly >= 7 levanta RuntimeError (em vez de ImportError) quando o
        # Kaleido esta ausente; mantemos o mesmo fallback HTML documentado.
        caminho_html = caminho_png.parent / "interactive" / f"{caminho_png.stem}.html"
        caminho_html.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(caminho_html, include_plotlyjs=True, full_html=True)
        return caminho_html


def estilizar_tabela_ipt(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Aplica formatação leve a tabelas pequenas do notebook acadêmico."""
    return (
        df.style
        .set_table_styles([
            {"selector": "th", "props": [("background-color", CORES_IPT["AZUL_PRINCIPAL"]), ("color", CORES_IPT["BRANCO"]), ("font-weight", "bold")]},
            {"selector": "td", "props": [("color", CORES_IPT["AZUL_ESCURO"]), ("border-color", CORES_IPT["CINZA_GRADE"])]},
        ])
        .set_properties(**{"background-color": CORES_IPT["BRANCO"]})
        .set_properties(subset=pd.IndexSlice[::2, :], **{"background-color": CORES_IPT["CINZA_FUNDO"]})
    )
