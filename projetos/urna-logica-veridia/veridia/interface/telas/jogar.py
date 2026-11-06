"""Visão geral das cinco fases: liberadas, bloqueadas e conquistadas."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.componentes import CONTEUDO_FASES, botao, etiqueta
from veridia.interface.estado import ContextoTela


def proxima_fase(ctx: ContextoTela) -> int:
    """Primeira fase liberada ainda sem selo (ou a 5, se tudo estiver conquistado)."""
    sessao = ctx.sessao
    for numero in range(1, 6):
        if sessao.fase_liberada(numero) and numero not in sessao.selos:
            return numero
    return 5


def tela(ctx: ContextoTela) -> None:
    sessao = ctx.sessao
    alvo = proxima_fase(ctx)
    with ui.row().classes("w-full items-end justify-between q-mt-xl q-mb-md gap-3"):
        with ui.column().classes("gap-1"):
            ui.label("Fases da investigação").classes("titulo-2")
            ui.label("Cada fase libera a seguinte quando você conquista o selo dela.").classes("texto-suave")
        texto = "Ver resultados" if sessao.jogo_concluido() else f"Continuar na Fase {alvo}"
        botao(texto, lambda: ui.navigate.to("/resultados" if sessao.jogo_concluido() else f"/fase/{alvo}"),
              tipo="principal", icone="arrow_forward", marca="continuar")

    with ui.grid().classes("w-full gap-3").style("grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))"):
        for numero, fase in sessao.fases.items():
            liberada = sessao.fase_liberada(numero)
            conquistada = numero in sessao.selos
            atual = liberada and not conquistada and numero == alvo
            classe = "conquistada" if conquistada else ("liberada" if liberada else "bloqueada")
            with ui.column().classes(f"cartao-fase {classe}{' atual' if atual else ''} gap-2").mark(f"cartao-fase-{numero}"):
                with ui.row().classes("items-center gap-3 no-wrap"):
                    ui.label("✓" if conquistada else str(numero)).classes("cartao-hex")
                    ui.label(fase.titulo).classes("titulo-3")
                ui.label(CONTEUDO_FASES[numero]).classes("texto-suave texto-pequeno")
                with ui.row().classes("items-center justify-between w-full q-mt-auto"):
                    if conquistada:
                        etiqueta("Selo conquistado", "ok")
                    elif liberada:
                        etiqueta("Em andamento", "alerta")
                    else:
                        etiqueta("Bloqueada", "neutra")
                    if liberada:
                        botao("Revisitar" if conquistada else "Entrar", lambda n=numero: ui.navigate.to(f"/fase/{n}"),
                              tipo="principal" if atual else "secundario", marca=f"entrar-fase-{numero}")
