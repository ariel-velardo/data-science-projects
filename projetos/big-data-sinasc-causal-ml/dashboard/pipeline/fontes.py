"""Leitura das evidências salvas: notebooks, CSVs e Markdown.

Nada aqui recalcula resultado. Cada acesso a uma saída de notebook informa o texto
esperado, para que uma mudança de posição das células interrompa a geração.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import numpy as np

RAIZ_PROJETO = Path(__file__).resolve().parents[2]

NOTEBOOKS = {
    "01": "notebooks/principal/01_qualidade_geografica.ipynb",
    "02": "notebooks/principal/02_comparabilidade.ipynb",
    "03": "notebooks/principal/03_estimacao_ato.ipynb",
    "04": "notebooks/principal/04_evolucao_historica.ipynb",
    "05": "notebooks/principal/05_temporalidade_prenatal.ipynb",
}
CSV_RECORTES = "outputs/qualidade_geografica_2024/comparacao_recortes_2024.csv"
CSV_VARIAVEIS = "outputs/qualidade_geografica_2024/qualidade_variaveis_2024.csv"
RECOMENDACAO = "outputs/qualidade_geografica_2024/RECOMENDACAO_RECORTE.md"
RESUMO = "docs/sp_capital_ato/RESUMO_PARA_REDACAO.md"
GUIA = "docs/GUIA_REVISAO_MIKE.md"
DICIONARIO = "docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md"
DAG_DOC = "docs/methodology/DAG_INICIAL.md"
DAG_TEX = "docs/sp_capital_ato/PACOTE_REDACAO_ETAPA_1_OVERLEAF/figuras/fig4_dag.tex"
LOGO_PDF = "docs/sp_capital_ato/PACOTE_REDACAO_ETAPA_2_OVERLEAF/logo_ipt.pdf"

FONTES_VERSIONADAS = [
    *NOTEBOOKS.values(),
    CSV_RECORTES,
    CSV_VARIAVEIS,
    RECOMENDACAO,
    RESUMO,
    GUIA,
    DICIONARIO,
    DAG_DOC,
    DAG_TEX,
    LOGO_PDF,
]


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def ler_texto(relativo: str) -> str:
    return (RAIZ_PROJETO / relativo).read_text(encoding="utf-8")


def ler_csv(relativo: str) -> list[dict[str, str]]:
    with open(RAIZ_PROJETO / relativo, encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def numero(texto: str) -> float | None:
    """Converte número em formato brasileiro, com unidade opcional."""
    limpo = (
        texto.strip()
        .replace("−", "-")
        .replace("%", "")
        .replace("p.p.", "")
        .replace("anos", "")
        .strip()
    )
    if limpo in {"", "—"}:
        return None
    return float(limpo.replace(".", "").replace(",", "."))


def inteiro(texto: str) -> int:
    valor = numero(texto)
    if valor is None or not float(valor).is_integer():
        raise ValueError(f"Contagem inválida: {texto!r}")
    return int(valor)


def contagem_pct(texto: str) -> tuple[int, float]:
    """Interpreta células como ``6.889 (6,6%)``."""
    achado = re.fullmatch(r"\s*([\d.]+)\s*\(([\d,]+)%\)\s*", texto)
    if not achado:
        raise ValueError(f"Célula n (%) inválida: {texto!r}")
    return inteiro(achado[1]), float(achado[2].replace(",", "."))


class _LeitorTabela(HTMLParser):
    """Leitor de tabelas HTML do pandas com expansão de rowspan e colspan."""

    def __init__(self) -> None:
        super().__init__()
        self.tabelas: list[list[list[str]]] = []
        self._linha: list[str] | None = None
        self._celula: list[str] | None = None
        self._atributos: dict[str, str] = {}
        self._pendentes: dict[int, tuple[int, str]] = {}

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tabelas.append([])
            self._pendentes = {}
        elif tag == "tr" and self.tabelas:
            self._linha = []
            self._aplicar_pendentes()
        elif tag in {"td", "th"} and self._linha is not None:
            self._celula = []
            self._atributos = dict(attrs)

    def handle_data(self, data):
        if self._celula is not None:
            self._celula.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._celula is not None:
            texto = "".join(self._celula).strip()
            colspan = int(self._atributos.get("colspan", 1))
            rowspan = int(self._atributos.get("rowspan", 1))
            for _ in range(colspan):
                indice = len(self._linha)
                self._linha.append(texto)
                if rowspan > 1:
                    self._pendentes[indice] = (rowspan - 1, texto)
                self._aplicar_pendentes()
            self._celula = None
        elif tag == "tr" and self._linha is not None:
            self.tabelas[-1].append(self._linha)
            self._linha = None

    def _aplicar_pendentes(self) -> None:
        while len(self._linha) in self._pendentes:
            indice = len(self._linha)
            restantes, texto = self._pendentes[indice]
            self._linha.append(texto)
            if restantes > 1:
                self._pendentes[indice] = (restantes - 1, texto)
            else:
                del self._pendentes[indice]


def _decodificar(valor):
    if isinstance(valor, dict):
        if "bdata" in valor:
            matriz = np.frombuffer(base64.b64decode(valor["bdata"]), dtype=valor["dtype"])
            if "shape" in valor:
                matriz = matriz.reshape([int(x) for x in str(valor["shape"]).split(",")])
            return matriz.tolist()
        return {chave: _decodificar(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [_decodificar(item) for item in valor]
    return valor


class Notebook:
    def __init__(self, chave: str) -> None:
        self.chave = chave
        self.caminho = NOTEBOOKS[chave]
        conteudo = json.loads(ler_texto(self.caminho))
        self.celulas = conteudo["cells"]

    def figura(self, celula: int, titulo_contem: str) -> list[dict]:
        for saida in self.celulas[celula].get("outputs", []):
            dados = saida.get("data", {}).get("application/vnd.plotly.v1+json")
            if dados:
                titulo = dados["layout"].get("title", {})
                titulo = titulo.get("text", "") if isinstance(titulo, dict) else str(titulo)
                if titulo_contem not in titulo:
                    raise ValueError(f"NB {self.chave} célula {celula}: título inesperado: {titulo}")
                return _decodificar(dados["data"])
        raise ValueError(f"NB {self.chave} célula {celula}: figura ausente")

    def tabela(self, celula: int, saida: int, cabecalho_contem: str) -> list[list[str]]:
        html = "".join(self.celulas[celula]["outputs"][saida]["data"]["text/html"])
        leitor = _LeitorTabela()
        leitor.feed(html)
        linhas = leitor.tabelas[0]
        topo = " | ".join(" | ".join(linha) for linha in linhas[:2])
        if cabecalho_contem not in topo:
            raise ValueError(f"NB {self.chave} célula {celula}/{saida}: cabeçalho inesperado: {topo}")
        return linhas

    def fluxo(self, celula: int) -> str:
        return "".join(
            "".join(saida.get("text", []))
            for saida in self.celulas[celula].get("outputs", [])
            if saida.get("output_type") == "stream"
        )

    def total_figuras(self) -> int:
        return sum(
            "application/vnd.plotly.v1+json" in saida.get("data", {})
            for celula in self.celulas
            if celula["cell_type"] == "code"
            for saida in celula.get("outputs", [])
        )
