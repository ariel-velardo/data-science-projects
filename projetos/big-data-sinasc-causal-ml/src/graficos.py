"""Padrão visual dos gráficos Plotly da análise SP capital (notebooks 06–08).

Somente apresentação: as funções recebem valores já calculados nos notebooks e
não estimam nada. O tema base (fonte, grade, cores IPT) vem de
``src.visualizacao``, que não é alterado.
"""
from __future__ import annotations

import base64
import json

import plotly.graph_objects as go
import plotly.io as pio
from IPython.display import display

from src.visualizacao import CORES_IPT, aplicar_tema_base

# Identidade dos grupos, validada para daltonismo (ΔE CVD 19,6; contraste ≥ 3:1).
COR_T1 = CORES_IPT["AZUL_PRINCIPAL"]   # início nos meses 1–3
COR_T0 = "#C2571A"                     # início nos meses 4–6
# Papel neutro de referência (valores brutos, "antes"); usado sempre com forma
# de marcador ou traço distinto, nunca como única codificação.
COR_REFERENCIA = "#6B7B86"
COR_TEXTO = CORES_IPT["AZUL_ESCURO"]
COR_TEXTO_SECUNDARIO = "#4A5A66"
COR_GRADE = CORES_IPT["CINZA_GRADE"]
COR_FAIXA = "#F1F4F6"
# Rampa sequencial (um matiz, claro → escuro) para categorias ordenadas de T=0.
RAMPA_T0 = ["#F0B184", "#D9773A", "#9E4A12"]
# Dois tons do mesmo matiz para partes de um todo.
TONS_AZUIS = [CORES_IPT["AZUL_PRINCIPAL"], "#8DBAD6"]

FONTE_SINASC_2024 = "Fonte: SINASC 2024 (Ministério da Saúde/DATASUS). Elaboração própria."
FONTE_SINASC_SERIE = "Fonte: SINASC 2014–2024 (Ministério da Saúde/DATASUS). Elaboração própria."

CONFIG_PLOTLY = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


def fmt_br(valor, casas=0):
    """Número no padrão brasileiro: milhar com ponto, decimal com vírgula."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def layout_academico(figura, titulo, subtitulo=None, notas=(), nome_arquivo=None,
                     largura=1050, altura=560, margem_inferior=None, margem_esquerda=None):
    """Título com subtítulo, notas de rodapé (fonte e método) e formatação pt-BR.

    ``nome_arquivo`` vai para ``layout.meta`` e nomeia a imagem exportada pela
    barra de ferramentas e o HTML interativo gerado por
    ``scripts/exportar_figuras_interativas.py``. ``margem_esquerda`` (px) reserva
    espaço para rótulos longos no eixo y e mantém as notas alinhadas à esquerda.
    """
    aplicar_tema_base(figura)
    texto_titulo = f"<b>{titulo}</b>"
    if subtitulo:
        texto_titulo += f"<br><span style='font-size:13px;color:{COR_TEXTO_SECUNDARIO}'>{subtitulo}</span>"
    notas = [n for n in notas if n]
    base = margem_inferior if margem_inferior is not None else 90 + 18 * len(notas)
    figura.update_layout(
        title=dict(text=texto_titulo, x=0.01, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=18, color=COR_TEXTO)),
        width=largura, height=altura, separators=",.",
        font=dict(family="Arial, Helvetica, sans-serif", size=13, color=COR_TEXTO),
        margin=dict(t=82 if subtitulo else 62, b=base, **({"l": margem_esquerda, "r": 40} if margem_esquerda else {})),
        hoverlabel=dict(bgcolor="white", bordercolor=COR_GRADE,
                        font=dict(family="Arial, Helvetica, sans-serif", size=13, color=COR_TEXTO)),
        legend=dict(bgcolor="rgba(255,255,255,0)"),
    )
    if nome_arquivo:
        figura.update_layout(meta={"nome_arquivo": nome_arquivo})
    # Notas empilhadas abaixo da área do gráfico, depois dos rótulos do eixo x.
    inicio = base - 18 * len(notas) - 8
    x_notas = -(margem_esquerda - 20) / (largura - margem_esquerda - 40) if margem_esquerda else 0
    for i, nota in enumerate(notas):
        figura.add_annotation(
            x=x_notas, xref="paper", xanchor="left", y=0, yref="paper", yanchor="top",
            yshift=-(inicio + 18 * i), showarrow=False, align="left", text=nota,
            font=dict(size=11, color=COR_TEXTO_SECUNDARIO))
    return figura


def exibir_plotly(figura):
    """Saída única com Plotly interativo (com configuração) e PNG estático de apoio.

    O PNG permite leitura em visualizadores sem JavaScript (por exemplo, o GitHub).
    """
    nome = (figura.layout.meta or {}).get("nome_arquivo") if isinstance(figura.layout.meta, dict) else None
    config = json.loads(json.dumps(CONFIG_PLOTLY))
    if nome:
        config["toImageButtonOptions"]["filename"] = nome
    pacote = json.loads(pio.to_json(figura))
    pacote["config"] = config
    png = figura.to_image(format="png", scale=1.5)
    titulo = figura.layout.title.text or ""
    display({
        "application/vnd.plotly.v1+json": pacote,
        "image/png": base64.b64encode(png).decode("ascii"),
        "text/plain": titulo.split("<br>")[0].replace("<b>", "").replace("</b>", ""),
    }, raw=True)
