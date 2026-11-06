"""Exporta o código do projeto em um ZIP limpo para compartilhar ou revisar.

Uso (na pasta do projeto, com qualquer Python 3.11+; não depende de PowerShell):
    python scripts/exportar_projeto.py
    python scripts/exportar_projeto.py --saida C:/temp/veridia.zip

Gera ``dist/urna-logica-veridia-codigo.zip`` contendo apenas:
- pastas ``veridia/``, ``tests/``, ``docs/`` e ``scripts/`` (só arquivos
  .py, .md, .toml, .txt e .css);
- arquivos da raiz: README.md, AGENTS.md, CLAUDE.md, pyproject.toml, requirements*.txt
  .gitignore e .gitattributes;
- artefatos de entrega por nome explícito: relatório acadêmico PDF,
  métricas JSON da Rodada 4 e configuração YAML de CI. Outros PDFs,
  inclusive o enunciado original, não entram nessa lista.

Estratégia: LISTA DE INCLUSÃO (só entra o que foi previsto) somada a uma
lista de EXCLUSÃO (ambientes virtuais, caches, .git, dist, temporários,
segredos). Links simbólicos são ignorados e nenhum arquivo original é
alterado ou apagado. Ao final, o ZIP é reaberto e conferido.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
import zipfile
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
NOME_ZIP = "urna-logica-veridia-codigo.zip"
PREFIXO_ZIP = "urna-logica-veridia"

PASTAS_INCLUIDAS = ("veridia", "tests", "docs", "scripts")
EXTENSOES_PERMITIDAS = {".py", ".md", ".toml", ".txt", ".css"}
ARQUIVOS_RAIZ = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-interface.txt",
    ".gitignore",
    ".gitattributes",
)
ARQUIVOS_ENTREGA = (
    "docs/RELATORIO_ACADEMICO.pdf",
    "docs/METRICAS_RODADA4.json",
    "scripts/pytest-github-actions.yml",
)

PASTAS_EXCLUIDAS = {
    ".venv", "venv", "env", ".env", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".git", "dist", "build", ".idea", ".vscode", ".claude", "htmlcov", "saidas", "node_modules",
}
PADROES_EXCLUIDOS = (
    "*.pyc", "*.pyo", "*.tmp", "*.temp", "*.bak", "*.swp", "*~", "*.log",
    ".env", ".env.*", "*.env", "*.pem", "*.key", "*.p12", "*.pfx",
    "*secret*", "*segredo*", "*credential*", "*credencia*", "*token*", "*senha*", "*password*",
    ".coverage", ".DS_Store", "Thumbs.db", "desktop.ini", "*.local.*", "settings.local.json",
)


def _excluido(caminho_relativo: Path) -> bool:
    if any(parte in PASTAS_EXCLUIDAS for parte in caminho_relativo.parts[:-1]):
        return True
    nome = caminho_relativo.name.lower()
    return any(fnmatch.fnmatch(nome, padrao.lower()) for padrao in PADROES_EXCLUIDOS)


def listar_arquivos(raiz: Path = RAIZ_PROJETO) -> list[Path]:
    """Arquivos (relativos à raiz) que irão para o ZIP, em ordem determinística."""
    raiz = raiz.resolve()
    selecionados: set[Path] = set()

    for nome in (*ARQUIVOS_RAIZ, *ARQUIVOS_ENTREGA):
        caminho = raiz / nome
        if (
            caminho.is_file()
            and not caminho.is_symlink()
            and raiz in caminho.resolve().parents
            and not any((raiz / p).is_symlink() for p in caminho.relative_to(raiz).parents if p != Path("."))
        ):
            selecionados.add(Path(nome))

    for pasta in PASTAS_INCLUIDAS:
        base = raiz / pasta
        if not base.is_dir() or base.is_symlink():
            continue
        for caminho in base.rglob("*"):
            if caminho.is_symlink() or not caminho.is_file():
                continue
            relativo = caminho.relative_to(raiz)
            if any((raiz / Path(*relativo.parts[: i + 1])).is_symlink() for i in range(len(relativo.parts) - 1)):
                continue  # não segue pastas que sejam links
            if caminho.suffix.lower() not in EXTENSOES_PERMITIDAS or _excluido(relativo):
                continue
            if raiz not in caminho.resolve().parents:
                continue  # garantia extra: nada fora do projeto
            selecionados.add(relativo)
    return sorted(selecionados, key=lambda p: p.as_posix())


def conferir_zip(caminho_zip: Path) -> list[str]:
    """Problemas encontrados no ZIP (lista vazia = limpo)."""
    problemas: list[str] = []
    with zipfile.ZipFile(caminho_zip) as arquivo_zip:
        nomes = arquivo_zip.namelist()
        if arquivo_zip.testzip() is not None:
            problemas.append("ZIP corrompido")
    for nome in nomes:
        relativo = Path(nome).relative_to(PREFIXO_ZIP)
        if _excluido(relativo):
            problemas.append(f"arquivo proibido no ZIP: {nome}")
    for essencial in ("veridia/__init__.py", "README.md", "pyproject.toml"):
        if f"{PREFIXO_ZIP}/{essencial}" not in nomes:
            problemas.append(f"arquivo essencial ausente: {essencial}")
    return problemas


def exportar(raiz: Path = RAIZ_PROJETO, saida: Path | None = None) -> tuple[Path, list[Path]]:
    """Cria o ZIP e devolve (caminho do ZIP, arquivos incluídos). Não altera os originais."""
    raiz = raiz.resolve()
    saida = (saida or raiz / "dist" / NOME_ZIP).resolve()
    arquivos = listar_arquivos(raiz)
    saida.parent.mkdir(parents=True, exist_ok=True)
    temporario = saida.with_suffix(".zip.parcial")
    with zipfile.ZipFile(temporario, "w", compression=zipfile.ZIP_DEFLATED) as arquivo_zip:
        for relativo in arquivos:
            arquivo_zip.write(raiz / relativo, arcname=f"{PREFIXO_ZIP}/{relativo.as_posix()}")
    temporario.replace(saida)  # troca atômica: um ZIP antigo só é substituído quando o novo está completo
    return saida, arquivos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exporta o projeto em um ZIP limpo.")
    parser.add_argument("--saida", type=Path, default=None, help=f"caminho do ZIP (padrão: dist/{NOME_ZIP})")
    args = parser.parse_args(argv)

    caminho, arquivos = exportar(saida=args.saida)
    problemas = conferir_zip(caminho)
    tamanho_kb = caminho.stat().st_size / 1024
    print(f"ZIP gerado: {caminho}")
    print(f"{len(arquivos)} arquivos, {tamanho_kb:.1f} KB")
    for pasta in PASTAS_INCLUIDAS:
        quantidade = sum(1 for a in arquivos if a.parts[0] == pasta)
        print(f"  {pasta}/: {quantidade} arquivo(s)")
    print(f"  raiz: {sum(1 for a in arquivos if len(a.parts) == 1)} arquivo(s)")
    if problemas:
        print("PROBLEMAS:", *problemas, sep="\n  ")
        return 1
    print("Conferência: sem ambientes virtuais, caches, .git, dist, temporários ou segredos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
