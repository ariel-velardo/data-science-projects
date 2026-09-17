"""Testes focais do padrão visual IPT."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import visualizacao_ipt as visual  # noqa: E402


class TestVisualizacaoIpt(unittest.TestCase):
    def test_aplicar_tema_define_template_e_titulo(self) -> None:
        figura = visual.aplicar_tema_ipt(go.Figure(), titulo="Título de teste")
        self.assertEqual(figura.layout.paper_bgcolor, visual.CORES_IPT["BRANCO"])
        self.assertEqual(figura.layout.font.family, "Arial")
        self.assertEqual(figura.layout.title.text, "Título de teste")

    def test_salvar_figura_faz_fallback_html_sem_kaleido(self) -> None:
        class FiguraSemKaleido:
            def write_image(self, *_args, **_kwargs) -> None:
                raise ValueError("kaleido indisponível")

            def write_html(self, caminho: Path, **_kwargs) -> None:
                Path(caminho).write_text("<html></html>", encoding="utf-8")

        with tempfile.TemporaryDirectory() as diretorio:
            destino = visual.salvar_figura_ipt(FiguraSemKaleido(), Path(diretorio) / "grafico.png")

        self.assertEqual(destino.name, "grafico.html")
        self.assertEqual(destino.parent.name, "interactive")

    def test_salvar_figura_faz_fallback_html_quando_kaleido_lanca_runtimeerror(self) -> None:
        """Plotly >= 7 levanta RuntimeError (nao mais ImportError) quando o
        pacote Kaleido esta ausente. O fallback precisa capturar esse tipo
        tambem, sem propagar excecao."""

        class FiguraKaleidoAusenteRuntimeError:
            def write_image(self, *_args, **_kwargs) -> None:
                raise RuntimeError(
                    "Image export requires the Kaleido package, v1.0.0 or greater, "
                    'which can be installed using pip:\n\n    $ pip install --upgrade "kaleido>=1"'
                )

            def write_html(self, caminho: Path, **_kwargs) -> None:
                Path(caminho).write_text("<html></html>", encoding="utf-8")

        with tempfile.TemporaryDirectory() as diretorio:
            destino = visual.salvar_figura_ipt(FiguraKaleidoAusenteRuntimeError(), Path(diretorio) / "grafico.png")
            self.assertTrue(destino.exists())

        self.assertEqual(destino.name, "grafico.html")
        self.assertEqual(destino.parent.name, "interactive")


if __name__ == "__main__":
    unittest.main()
