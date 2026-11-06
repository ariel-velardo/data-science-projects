"""Visão geral das cinco fases: liberadas, bloqueadas e conquistadas."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.componentes import botao
from veridia.interface.estado import ContextoTela

CONTEUDO = {
    1: "Ordenação: Bubble, Merge e Quick Sort com chave composta.",
    2: "Fila, pilha e lista ligada, com desfazer.",
    3: "Grafo, BFS e DFS, pistas, portas e energia.",
    4: "Árvore AVL, estados equivalentes e rotações.",
    5: "Integração: solver, ordenação e relatório.",
}


def proxima_fase(ctx: ContextoTela) -> int:
    """Primeira fase liberada ainda sem selo (ou a 5, se tudo estiver conquistado)."""
    sessao = ctx.sessao
    for numero in range(1, 6):
        if sessao.fase_liberada(numero) and numero not in sessao.selos:
            return numero
    return 5


def tela(ctx: ContextoTela) -> None:
    sessao = ctx.sessao
    with ui.row().classes("w-full items-end justify-between q-mt-lg q-mb-md"):
        with ui.column().classes("gap-1"):
            ui.label("Fases da investigação").classes("titulo-2")
            ui.label("Cada fase libera a seguinte quando você conquista o selo dela.").classes("texto-suave")
        alvo = proxima_fase(ctx)
        texto = "Ver resultados" if sessao.jogo_concluido() else f"Continuar na Fase {alvo}"
        botao(texto, lambda: ui.navigate.to("/resultados" if sessao.jogo_concluido() else f"/fase/{alvo}"), tipo="principal", marca="continuar")

    with ui.grid().classes("w-full gap-3").style("grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))"):
        for numero, fase in sessao.fases.items():
            liberada = sessao.fase_liberada(numero)
            conquistada = numero in sessao.selos
            classe = "conquistada" if conquistada else ("" if liberada else "bloqueada")
            with ui.column().classes(f"cartao-fase {classe} gap-2").mark(f"cartao-fase-{numero}"):
                ui.label(f"Fase {numero}").classes("texto-suave").style("font-size: 0.85rem")
                ui.label(fase.titulo).classes("titulo-3")
                ui.label(CONTEUDO[numero]).classes("texto-suave").style("font-size: 0.9rem")
                if conquistada:
                    ui.html('<span class="etiqueta ok">Selo conquistado</span>')
                elif liberada:
                    ui.html('<span class="etiqueta alerta">Em andamento</span>')
                else:
                    ui.html('<span class="etiqueta">Bloqueada</span>')
                if liberada:
                    botao("Entrar", lambda n=numero: ui.navigate.to(f"/fase/{n}"), marca=f"entrar-fase-{numero}")
