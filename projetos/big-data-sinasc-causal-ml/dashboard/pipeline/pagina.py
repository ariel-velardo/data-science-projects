"""Monta o HTML único: modelo, estilo, script, dados agregados e Plotly embutidos."""
from __future__ import annotations

import json
import re
from pathlib import Path

import plotly
from plotly.offline import get_plotlyjs

WEB = Path(__file__).resolve().parents[1] / "web"
_TOKEN = re.compile(r"\[\[([^\]|]+)(?:\|([a-z0-9]+))?\]\]")


def _br(valor: float, casas: int) -> str:
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar(valor, formato: str | None) -> str:
    if formato in {None, "txt"}:
        return str(valor)
    if formato == "int":
        return _br(valor, 0)
    if formato in {"d1", "d2", "d3", "d4"}:
        return _br(valor, int(formato[1])).replace("-", "−")
    if formato == "pp":
        sinal = "−" if valor < 0 else "+"
        return f"{sinal}{_br(abs(valor), 2)}"
    raise ValueError(f"Formato desconhecido: {formato}")


def resolver(dados: dict, caminho: str):
    atual = dados
    for parte in caminho.split("."):
        if isinstance(atual, list):
            atual = atual[int(parte)]
        else:
            atual = atual[parte]
    return atual


def preencher(modelo: str, dados: dict) -> str:
    return _TOKEN.sub(lambda m: formatar(resolver(dados, m[1]), m[2]), modelo)


def json_embutido(dados: dict) -> str:
    texto = json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return texto.replace("</", "<\\/")


def montar(dados: dict, logo_svg: str) -> str:
    modelo = (WEB / "modelo.html").read_text(encoding="utf-8")
    html = preencher(modelo, dados)
    substituicoes = {
        "<!--ESTILO-->": (WEB / "estilo.css").read_text(encoding="utf-8"),
        "<!--LOGO-->": logo_svg,
        "<!--DADOS-->": json_embutido(dados),
        "<!--PLOTLY-->": get_plotlyjs().replace("</script", "<\\/script"),
        "<!--APP-->": (WEB / "app.js").read_text(encoding="utf-8"),
    }
    for marcador, conteudo in substituicoes.items():
        if html.count(marcador) != 1:
            raise ValueError(f"Marcador ausente ou repetido: {marcador}")
        html = html.replace(marcador, conteudo)
    return html


def versao_plotly() -> str:
    return plotly.__version__
