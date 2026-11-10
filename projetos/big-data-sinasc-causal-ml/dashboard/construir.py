"""Gera o painel, os dados agregados, a matriz e o manifesto de proveniência.

Uso, a partir da raiz do projeto e com a .venv do projeto ativa:
    python dashboard/construir.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import dados as modulo_dados  # noqa: E402
from pipeline import logo as modulo_logo  # noqa: E402
from pipeline import matriz as modulo_matriz  # noqa: E402
from pipeline import pagina  # noqa: E402
from pipeline.fontes import FONTES_VERSIONADAS, RAIZ_PROJETO, sha256  # noqa: E402

REFERENCIA_ORIGEM = "fd0d319e4b77dfa973b87f1a3c6fc6872968225e"
NOME_HTML = "sinasc_dashboard_ipt.html"


def _escrever(caminho: Path, conteudo: str) -> str:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    binario = conteudo.encode("utf-8")
    caminho.write_bytes(binario)
    return hashlib.sha256(binario).hexdigest()


def _matriz_markdown() -> str:
    cabecalho = "| " + " | ".join(modulo_matriz.COLUNAS) + " |"
    separador = "|" + "---|" * len(modulo_matriz.COLUNAS)
    linhas = ["| " + " | ".join(linha) + " |" for linha in modulo_matriz.MATRIZ]
    return "\n".join(
        [
            "# Matriz de rastreabilidade do painel",
            "",
            "Arquivo gerado por `dashboard/construir.py`. NB 01 a NB 05 são os notebooks principais.",
            "",
            cabecalho,
            separador,
            *linhas,
            "",
        ]
    )


def construir(saida: Path) -> dict:
    dados = modulo_dados.construir()
    logo = modulo_logo.extrair()
    fontes = [{"caminho": c, "sha256": sha256(RAIZ_PROJETO / c)} for c in FONTES_VERSIONADAS]
    dados["meta"] = {
        "referencia_origem": REFERENCIA_ORIGEM,
        "plotly_python": pagina.versao_plotly(),
        "cores_logotipo": logo["cores"],
        "fontes": fontes,
        "matriz_colunas": modulo_matriz.COLUNAS,
        "matriz": [list(linha) for linha in modulo_matriz.MATRIZ],
    }

    hash_dados = _escrever(
        saida / "dados_painel.json",
        json.dumps(dados, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
    )
    hash_html = _escrever(saida / NOME_HTML, pagina.montar(dados, logo["svg"]))
    hash_matriz = _escrever(saida / "MATRIZ_RASTREABILIDADE.md", _matriz_markdown())

    manifesto = {
        "artefato": NOME_HTML,
        "referencia_origem": REFERENCIA_ORIGEM,
        "granularidade": "agregados por recorte, ano, grupo, categoria ou faixa; sem registros individuais",
        "microdados_lidos": False,
        "regra_divulgacao": "contagens de 1 a 9 exibidas como <10; histogramas agrupados até 0 ou pelo menos 10 registros por grupo",
        "plotly_python": pagina.versao_plotly(),
        "fontes": fontes,
        "saidas": {
            NOME_HTML: hash_html,
            "dados_painel.json": hash_dados,
            "MATRIZ_RASTREABILIDADE.md": hash_matriz,
        },
        "limitacao_conhecida": "as estimativas permanecem as dos notebooks salvos; o painel não reexecuta análises",
    }
    _escrever(
        saida / "MANIFESTO_PROVENIENCIA.json",
        json.dumps(manifesto, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    return manifesto


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=Path(__file__).resolve().parent / "dist")
    argumentos = parser.parse_args()
    manifesto = construir(argumentos.saida)
    print(json.dumps(manifesto["saidas"], indent=2))


if __name__ == "__main__":
    main()
