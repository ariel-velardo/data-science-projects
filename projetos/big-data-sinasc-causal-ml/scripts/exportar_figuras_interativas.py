"""Exporta os gráficos Plotly dos notebooks principais para HTML interativo.

A fonte é a saída salva de cada notebook de ``notebooks/principal/``: nada é
recalculado. Os arquivos vão para ``outputs/figuras_interativas/`` e
compartilham um único ``plotly.min.js`` local, de modo que funcionam offline e
sem cópias repetidas da biblioteca. ``index.html`` lista as figuras.

Uso, a partir da raiz do projeto, com a .venv ativa:
    python scripts/exportar_figuras_interativas.py              # grava
    python scripts/exportar_figuras_interativas.py --verificar  # só confere
"""
import argparse
import html
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PASTA_NOTEBOOKS = ROOT / "notebooks" / "principal"
DESTINO = ROOT / "outputs" / "figuras_interativas"
MIME_PLOTLY = "application/vnd.plotly.v1+json"


def _texto_simples(texto):
    return re.sub(r"<[^>]+>", " ", texto or "").replace("  ", " ").strip()


def _slug(texto):
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")[:50]


def figuras_salvas(pasta=PASTA_NOTEBOOKS):
    """Lista (notebook, nome, figura) na ordem dos notebooks e das células."""
    from src.graficos import CONFIG_PLOTLY
    itens = []
    for caminho in sorted(pasta.glob("*.ipynb")):
        nb = json.loads(caminho.read_text(encoding="utf-8"))
        prefixo = caminho.stem.split("_")[0]
        contador = 0
        for celula in nb["cells"]:
            for saida in celula.get("outputs", []):
                pacote = saida.get("data", {}).get(MIME_PLOTLY)
                if not pacote:
                    continue
                contador += 1
                layout = pacote.get("layout", {})
                titulo = layout.get("title", {})
                titulo = titulo.get("text", "") if isinstance(titulo, dict) else str(titulo)
                meta = layout.get("meta") if isinstance(layout.get("meta"), dict) else {}
                nome = meta.get("nome_arquivo") or f"{prefixo}_{contador}_{_slug(_texto_simples(titulo).split('<br>')[0])}"
                config = json.loads(json.dumps(pacote.get("config") or CONFIG_PLOTLY))
                config.setdefault("toImageButtonOptions", {})["filename"] = nome
                itens.append({"notebook": caminho.name, "nome": nome, "titulo": titulo,
                              "figura": {"data": pacote["data"], "layout": layout}, "config": config})
    nomes = [i["nome"] for i in itens]
    if len(nomes) != len(set(nomes)):
        raise ValueError("Nomes de figuras repetidos: " + ", ".join(sorted({n for n in nomes if nomes.count(n) > 1})))
    return itens


def html_figura(item):
    """HTML de uma figura, determinístico, referenciando plotly.min.js na mesma pasta."""
    import plotly.io as pio
    corpo = pio.to_html(item["figura"], include_plotlyjs="directory", full_html=True, validate=False,
                        config=item["config"], div_id=item["nome"])
    titulo = html.escape(_texto_simples(item["titulo"]).split("  ")[0])
    corpo = corpo.replace("<head>", f'<head><meta charset="utf-8"><title>{titulo}</title>', 1)
    return corpo.replace("<html>", '<html lang="pt-BR">', 1)


def html_indice(itens):
    linhas = []
    atual = None
    for item in itens:
        if item["notebook"] != atual:
            if atual is not None:
                linhas.append("</ul>")
            atual = item["notebook"]
            linhas.append(f"<h2>{html.escape(atual)}</h2><ul>")
        linhas.append(f'<li><a href="{item["nome"]}.html">{html.escape(_texto_simples(item["titulo"]))}</a></li>')
    linhas.append("</ul>")
    return ("<!doctype html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>Gráficos interativos — SP capital</title><style>"
            "body{font-family:Arial,Helvetica,sans-serif;max-width:900px;margin:32px auto;padding:0 16px;"
            "color:#133C5A;background:#fff;line-height:1.5}h1{font-size:22px}h2{font-size:16px;margin-top:28px}"
            "a{color:#00598E}li{margin:4px 0}p{color:#4A5A66}</style></head><body>"
            "<h1>Gráficos interativos — análise SP capital (ATO)</h1>"
            "<p>Gerados de <code>scripts/exportar_figuras_interativas.py</code> a partir das saídas salvas dos "
            "notebooks de <code>notebooks/principal/</code>. Funcionam offline: abra qualquer arquivo no navegador "
            "(passe o mouse para ver os valores; a câmera da barra de ferramentas salva a imagem em PNG).</p>"
            + "".join(linhas) + "</body></html>\n")


def conteudos(pasta=PASTA_NOTEBOOKS):
    """Mapa nome de arquivo -> conteúdo esperado (sem plotly.min.js)."""
    itens = figuras_salvas(pasta)
    arquivos = {f"{i['nome']}.html": html_figura(i) for i in itens}
    arquivos["index.html"] = html_indice(itens)
    return arquivos


def exportar(destino=DESTINO):
    import plotly
    destino.mkdir(parents=True, exist_ok=True)
    arquivos = conteudos()
    for nome, texto in arquivos.items():
        (destino / nome).write_text(texto, encoding="utf-8", newline="\n")
    js = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    (destino / "plotly.min.js").write_bytes(js.read_bytes())
    obsoletos = sorted(p.name for p in destino.glob("*.html") if p.name not in arquivos)
    return sorted(arquivos), obsoletos


def verificar(destino=DESTINO):
    divergentes = []
    for nome, texto in conteudos().items():
        alvo = destino / nome
        if not alvo.is_file() or alvo.read_text(encoding="utf-8") != texto:
            divergentes.append(nome)
    if not (destino / "plotly.min.js").is_file():
        divergentes.append("plotly.min.js")
    return divergentes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verificar", action="store_true", help="não grava; falha se houver HTML desatualizado")
    args = parser.parse_args(argv)
    if args.verificar:
        divergentes = verificar()
        if divergentes:
            print("Desatualizados:", ", ".join(divergentes))
            raise SystemExit(1)
        print("Figuras interativas sincronizadas com os notebooks.")
        return
    gravados, obsoletos = exportar()
    print(f"{len(gravados)} arquivos gravados em {DESTINO.relative_to(ROOT).as_posix()}/ (+ plotly.min.js)")
    if obsoletos:
        print("HTML sem figura correspondente (revisar manualmente):", ", ".join(obsoletos))


if __name__ == "__main__":
    main()
