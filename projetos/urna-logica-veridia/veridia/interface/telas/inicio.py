"""Tela inicial: capa com a missão e os cinco selos, a ação principal e as demais opções do menu."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.componentes import TITULOS_FASES, fio_custodia
from veridia.interface.estado import ContextoTela
from veridia.interface.telas.jogar import proxima_fase

NARRATIVA = (
    "Na cidade fictícia de Verídia, a apuração de uma eleição foi posta em dúvida. "
    "Os registros das seções chegaram embaralhados, as evidências se misturaram na triagem "
    "e o log de uma urna mostra eventos fora de sequência. Você integra a Central de Auditoria: "
    "cada fase resolvida devolve um dos cinco selos que certificam o resultado."
)


def _navegavel(elemento, destino: str):
    elemento.on("click", lambda: ui.navigate.to(destino))
    elemento.on("keydown.enter", lambda: ui.navigate.to(destino))
    return elemento


def _opcao(icone: str, titulo: str, descricao: str, destino: str, marca: str) -> None:
    cartao = _navegavel(ui.column().classes("opcao-menu w-full").props('role="link" tabindex="0"').mark(marca), destino)
    with cartao:
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.icon(icone)
            ui.label(titulo).classes("titulo-3")
        ui.label(descricao).classes("texto-suave texto-pequeno")


def tela(ctx: ContextoTela) -> None:
    sessao = ctx.sessao
    iniciada = bool(sessao.selos) or len(sessao.historico) > 0

    with ui.element("section").classes("capa"):
        with ui.column().classes("capa-interna"):
            with ui.column().classes("gap-3"):
                ui.label("VERÍDIA").classes("titulo-1")
                ui.label("O Enigma da Urna").classes("capa-subtitulo")
                ui.label(NARRATIVA).classes("capa-texto")
                ui.label("Missão: recuperar os cinco selos de auditoria, um por fase.").classes("capa-missao")
            fio_custodia(ctx)

    # Ação principal: o que fazer primeiro.
    if sessao.jogo_concluido():
        titulo, descricao, destino = "Ver o relatório final", "Os cinco selos foram recuperados. Confira a auditoria.", "/resultados"
    elif iniciada:
        alvo = proxima_fase(ctx)
        titulo = "Continuar partida"
        descricao = f"Você tem {len(sessao.selos)} de 5 selos. Retome na Fase {alvo}: {TITULOS_FASES[alvo]}."
        destino = "/jogar"
    else:
        titulo, descricao, destino = "Jogar", "Comece pela Fase 1, O Arquivo Embaralhado, e avance conquistando selos.", "/jogar"

    with ui.column().classes("menu w-full"):
        principal = _navegavel(
            ui.row().classes("acao-principal w-full").props('role="link" tabindex="0"').mark("menu-jogar"), destino
        )
        with principal:
            ui.icon("play_circle")
            with ui.column().classes("gap-1"):
                ui.label(titulo).classes("acao-titulo")
                ui.label(descricao).classes("acao-descricao")

        with ui.grid().classes("w-full gap-3").style("grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))"):
            _opcao("route", "Resolver", "Veja BFS, DFS e DFS recursiva resolverem os desafios, passo a passo.", "/resolver", "menu-resolver")
            _opcao("menu_book", "Instruções", "História, controles e como vencer cada fase.", "/instrucoes", "menu-instrucoes")
            _opcao("assessment", "Resultados", "Progresso, histórico de ações, métricas e relatório final.", "/resultados", "menu-resultados")

        with ui.row().classes("w-full items-center justify-between q-mt-sm gap-2"):
            ui.label("Todos os dados são fictícios: não há candidatos, partidos ou resultados reais.").classes(
                "texto-suave texto-pequeno"
            )
            ui.button("Sair e encerrar a partida", on_click=lambda: ui.navigate.to("/sair"), icon="logout", color=None).props(
                "flat no-caps"
            ).classes("link-sair").mark("menu-sair")
