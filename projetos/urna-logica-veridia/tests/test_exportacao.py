import importlib.util
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("exportar_projeto", RAIZ / "scripts" / "exportar_projeto.py")
exportador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exportador)


@pytest.fixture
def projeto_falso(tmp_path):
    """Projeto mínimo com arquivos que DEVEM e que NÃO devem ir para o ZIP."""
    raiz = tmp_path / "projeto"
    arquivos = {
        "README.md": "# leia",
        "pyproject.toml": "[project]",
        "CLAUDE.md": "regras",
        ".gitignore": ".venv/",
        ".gitattributes": "*.pdf binary",
        "veridia/__init__.py": "",
        "veridia/modulo.py": "x = 1",
        "tests/test_x.py": "def test(): pass",
        "docs/GUIA.md": "guia",
        "scripts/s.py": "",
        # proibidos
        ".env": "SENHA=1",
        "veridia/.env.local": "x",
        "veridia/__pycache__/modulo.cpython-311.pyc": "lixo",
        "veridia/modulo.pyc": "lixo",
        ".venv/Lib/site.py": "lixo",
        ".git/config": "lixo",
        "dist/antigo.zip": "lixo",
        ".pytest_cache/v/x": "lixo",
        "docs/credenciais.md": "segredo",
        "docs/rascunho.tmp": "lixo",
        "docs/imagem.png": "binário",
        "tests/token_api.txt": "segredo",
        "notas_pessoais.md": "fora da lista de inclusão",
    }
    for relativo, conteudo in arquivos.items():
        caminho = raiz / relativo
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
    return raiz


def test_exporta_somente_arquivos_permitidos(projeto_falso, tmp_path):
    saida = tmp_path / "saida" / "codigo.zip"
    caminho, arquivos = exportador.exportar(projeto_falso, saida)
    assert caminho == saida.resolve() and saida.exists()
    with zipfile.ZipFile(saida) as z:
        nomes = sorted(n.removeprefix("urna-logica-veridia/") for n in z.namelist())
    assert nomes == sorted(
        [
            ".gitattributes", ".gitignore", "CLAUDE.md", "README.md", "pyproject.toml",
            "docs/GUIA.md", "scripts/s.py", "tests/test_x.py", "veridia/__init__.py", "veridia/modulo.py",
        ]
    )
    assert exportador.conferir_zip(saida) == []
    assert (projeto_falso / ".env").exists() and (projeto_falso / "dist/antigo.zip").exists()  # originais intactos


def test_conferir_zip_detecta_conteudo_proibido(tmp_path):
    ruim = tmp_path / "ruim.zip"
    with zipfile.ZipFile(ruim, "w") as z:
        z.writestr("urna-logica-veridia/.venv/x.py", "")
        z.writestr("urna-logica-veridia/veridia/__pycache__/a.pyc", "")
    problemas = exportador.conferir_zip(ruim)
    assert any(".venv" in p for p in problemas) and any("essencial" in p for p in problemas)


def test_exporta_o_projeto_real(tmp_path):
    caminho, arquivos = exportador.exportar(RAIZ, tmp_path / "real.zip")
    nomes = {a.as_posix() for a in arquivos}
    assert {"veridia/busca/solver.py", "tests/test_solver.py", "docs/GUIA_TECNICO.md", "README.md", "pyproject.toml"} <= nomes
    assert not any(".venv" in n or "__pycache__" in n or n.endswith(".pyc") for n in nomes)
    assert exportador.conferir_zip(caminho) == []


def test_inclui_entrega_academica_sem_enunciado_original(projeto_falso, tmp_path):
    adicionais = {
        "docs/RELATORIO_ACADEMICO.pdf": "relatorio produzido pelo projeto",
        "docs/METRICAS_RODADA4.json": '{"repeticoes": 5}',
        "scripts/pytest-github-actions.yml": "name: pytest",
    }
    for nome, conteudo in adicionais.items():
        (projeto_falso / nome).write_text(conteudo, encoding="utf-8")
    (projeto_falso / "docs" / "EP Urna Lógica.pdf").write_text("enunciado externo", encoding="utf-8")

    caminho, arquivos = exportador.exportar(projeto_falso, tmp_path / "academico.zip")
    nomes = {a.as_posix() for a in arquivos}
    assert set(adicionais) <= nomes
    assert "docs/EP Urna Lógica.pdf" not in nomes
    assert exportador.conferir_zip(caminho) == []
