"""Sair: encerra somente a partida deste navegador; o servidor continua no ar."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.componentes import botao
from veridia.interface.estado import ContextoTela


def tela(ctx: ContextoTela) -> None:
    area = ui.column().classes("painel gap-3 leitura q-mt-xl")

    def encerrar() -> None:
        ctx.gerenciador.descartar(ctx.identificador)
        ctx.memoria.clear()
        ctx.atualizar_selos()
        area.clear()
        with area:
            ui.label("Partida encerrada").classes("titulo-2").mark("partida-encerrada")
            ui.label(
                "Seu progresso foi descartado. Você já pode fechar esta aba. "
                "O jogo continua disponível para outras pessoas conectadas."
            ).classes("texto-suave")
            botao("Começar nova partida", lambda: ui.navigate.to("/"), tipo="principal", marca="nova-partida")

    with area:
        ui.label("Sair do jogo").classes("titulo-2")
        ui.label(
            f"Você tem {len(ctx.sessao.selos)} de 5 selos. Se apenas fechar a aba, a partida fica guardada "
            "neste navegador enquanto o servidor estiver aberto. Encerrar apaga o seu progresso e não "
            "afeta outros jogadores."
        ).classes("texto-suave")
        with ui.row().classes("gap-2"):
            botao("Encerrar minha partida", encerrar, tipo="perigo", icone="logout", marca="encerrar-partida")
            botao("Voltar ao menu", lambda: ui.navigate.to("/"), marca="voltar-menu")
