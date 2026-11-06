"""Aplicação NiceGUI do VERÍDIA — ponto de entrada.

Execução (com a .venv do projeto ativada, na pasta do projeto):
    python -m veridia.interface.app                 # abre http://localhost:8080
    python -m veridia.interface.app --porta 8090 --sem-navegador

Arquitetura: uma única página raiz (``raiz``) desenha a barra superior com o
trilho de selos e um ``ui.sub_pages`` com as telas. Navegar entre telas não
recarrega a página nem perde a partida. Toda a lógica vem do motor Python
(``SessaoJogo``, fases, regras, solver); a interface só chama e exibe.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from nicegui import app, ui

from veridia.interface import componentes
from veridia.interface.estado import GERENCIADOR, ContextoTela
from veridia.interface.svg import EVENTO_CLIQUE_LOCAL
from veridia.interface.telas import (
    fase1,
    fase2,
    fase3,
    fase4,
    fase5,
    inicio,
    instrucoes,
    jogar,
    resolver,
    resultados,
    sair,
)

CSS = (Path(__file__).parent / "estilos.css").read_text(encoding="utf-8")

# Chave que apenas assina o cookie de identificação do navegador (não protege
# dados sensíveis: a aplicação roda localmente e não tem contas de usuário).
CHAVE_COOKIE = "veridia-ep-urna-logica-local"

NAVEGACAO = (
    ("Início", "/"),
    ("Jogar", "/jogar"),
    ("Resolver", "/resolver"),
    ("Instruções", "/instrucoes"),
    ("Resultados", "/resultados"),
    ("Sair", "/sair"),
)


def raiz() -> None:
    ui.add_css(CSS)
    ui.dark_mode(True)
    ui.colors(primary="#3fc7b3", secondary="#e3a948", negative="#e5686f", positive="#3fc7b3", dark="#18222e")
    ui.query("body").classes("veridia")

    ctx = ContextoTela(identificador=app.storage.browser["id"], gerenciador=GERENCIADOR)

    def clique_local(evento) -> None:
        destino = evento.args[0] if isinstance(evento.args, list) else evento.args
        if ctx.ao_clicar_local is not None and isinstance(destino, str):
            ctx.ao_clicar_local(destino)

    ui.on(EVENTO_CLIQUE_LOCAL, clique_local)

    with ui.element("header").classes("barra-topo w-full"):
        with ui.row().classes("barra-topo-interna items-center justify-between w-full"):
            with ui.row().classes("items-baseline gap-3").on("click", lambda: ui.navigate.to("/")):
                ui.label("VERÍDIA").classes("marca")
                ui.label("O Enigma da Urna").classes("marca-sub")

            @ui.refreshable
            def selos() -> None:
                componentes.trilho_selos(ctx)

            selos()
            ctx.atualizar_selos = selos.refresh
            with ui.row().classes("gap-0").props('role="navigation" aria-label="Menu"'):
                for texto, destino in NAVEGACAO:
                    ui.button(texto, on_click=lambda d=destino: ui.navigate.to(d), color=None).props("flat no-caps").classes(
                        "nav-botao"
                    ).mark(f"nav-{texto}")

    with ui.column().classes("moldura"):
        ui.sub_pages(
            {
                "/": lambda: inicio.tela(ctx),
                "/jogar": lambda: jogar.tela(ctx),
                "/fase/1": lambda: fase1.tela(ctx),
                "/fase/2": lambda: fase2.tela(ctx),
                "/fase/3": lambda: fase3.tela(ctx),
                "/fase/4": lambda: fase4.tela(ctx),
                "/fase/5": lambda: fase5.tela(ctx),
                "/resolver": lambda: resolver.tela(ctx),
                "/instrucoes": lambda: instrucoes.tela(ctx),
                "/resultados": lambda: resultados.tela(ctx),
                "/sair": lambda: sair.tela(ctx),
            }
        ).classes("w-full")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Interface do VERÍDIA — O Enigma da Urna.")
    parser.add_argument("--porta", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--sem-navegador", action="store_true", help="não abrir o navegador automaticamente")
    args = parser.parse_args(argv)
    ui.run(
        raiz,
        title="VERÍDIA — O Enigma da Urna",
        host=args.host,
        port=args.porta,
        dark=True,
        language="pt-BR",
        storage_secret=CHAVE_COOKIE,
        reload=False,
        show=not args.sem_navegador,
        favicon="🗳️",
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
