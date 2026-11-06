"""Tela inicial: narrativa curta, missão e as cinco opções do menu."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.estado import ContextoTela

NARRATIVA = (
    "Na cidade fictícia de Verídia, a apuração de uma eleição foi posta em dúvida. "
    "Os registros das seções chegaram embaralhados, as evidências se misturaram na triagem "
    "e o log de uma urna mostra eventos fora de sequência. Você integra a Central de Auditoria: "
    "cada fase resolvida devolve um dos cinco selos que certificam o resultado."
)


def _opcao(titulo: str, descricao: str, destino: str, marca: str) -> None:
    cartao = ui.column().classes("opcao-menu gap-1 w-full").props('role="link" tabindex="0"').mark(marca)
    cartao.on("click", lambda: ui.navigate.to(destino))
    cartao.on("keydown.enter", lambda: ui.navigate.to(destino))
    with cartao:
        ui.label(titulo).classes("titulo-3")
        ui.label(descricao).classes("texto-suave")


def tela(ctx: ContextoTela) -> None:
    sessao = ctx.sessao
    iniciada = bool(sessao.selos) or len(sessao.historico) > 0
    with ui.column().classes("capa gap-4"):
        ui.label("VERÍDIA").classes("titulo-1").style("letter-spacing: 0.12em")
        ui.label("O Enigma da Urna").classes("titulo-2 texto-suave").style("font-weight: 500")
        ui.label(NARRATIVA).classes("capa-texto")
        ui.label("Missão: recuperar os cinco selos de auditoria, um por fase.").classes("titulo-3").style(
            "color: var(--agua)"
        )

    with ui.grid().classes("w-full gap-3").style("grid-template-columns: repeat(auto-fit, minmax(210px, 1fr))"):
        _opcao(
            "Continuar partida" if iniciada else "Jogar",
            f"Você tem {len(sessao.selos)} de 5 selos. Retome de onde parou." if iniciada else "Comece pela Fase 1 e avance conquistando selos.",
            "/jogar",
            "menu-jogar",
        )
        _opcao("Resolver", "Veja BFS, DFS e DFS recursiva resolverem os desafios, passo a passo.", "/resolver", "menu-resolver")
        _opcao("Instruções", "História, controles e como vencer cada fase.", "/instrucoes", "menu-instrucoes")
        _opcao("Resultados", "Progresso, histórico de ações, métricas e relatório final.", "/resultados", "menu-resultados")
        _opcao("Sair", "Encerre sua partida sem afetar outras pessoas.", "/sair", "menu-sair")

    ui.label("Todos os dados são fictícios: não há candidatos, partidos ou resultados reais.").classes(
        "texto-suave q-mt-lg"
    ).style("font-size: 0.85rem")
