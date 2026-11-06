"""Componentes visuais reutilizados pelas telas."""

from __future__ import annotations

from typing import Any, Callable

from nicegui import ui

from veridia.fases.base import ResultadoAcao
from veridia.interface.estado import ContextoTela

TITULOS_FASES = {
    1: "O Arquivo Embaralhado",
    2: "A Central de Triagem",
    3: "O Mapa das Seções",
    4: "O Cofre dos Estados",
    5: "A Auditoria Final",
}


def trilho_selos(ctx: ContextoTela) -> None:
    """Os cinco selos: bloqueado, liberado, conquistado; a fase atual tem um anel."""
    sessao = ctx.sessao
    vistos: set[int] = ctx.memoria.setdefault("selos_vistos", set())
    with ui.row().classes("trilho").mark("trilho-selos"):
        for numero in range(1, 6):
            if numero > 1:
                ui.element("div").classes("trilho-ponte" + (" feita" if (numero - 1) in sessao.selos else ""))
            conquistado = numero in sessao.selos
            liberado = sessao.fase_liberada(numero)
            estado = "conquistado" if conquistado else ("liberado" if liberado else "bloqueado")
            recem = " recem" if conquistado and numero not in vistos else ""
            descricao = {"conquistado": "selo conquistado", "liberado": "fase liberada", "bloqueado": "bloqueada"}[estado]
            with ui.element("div").classes("selo-anel" + (" atual" if numero == sessao.fase_atual and not sessao.jogo_concluido() else "")):
                selo = ui.element("div").classes(f"selo {estado}{recem}").props(
                    f'role="button" tabindex="0" aria-label="Fase {numero}, {descricao}"'
                ).mark(f"selo-{numero}")
                with selo:
                    ui.label("✓" if conquistado else str(numero))
                    ui.tooltip(f"Fase {numero}: {TITULOS_FASES[numero]} ({descricao})")
                if liberado:
                    selo.on("click", lambda n=numero: ui.navigate.to(f"/fase/{n}"))
        ui.label(f"{len(sessao.selos)} de 5 selos").classes("texto-suave").style("margin-left: 8px; font-size: 0.85rem")
    vistos.update(sessao.selos)


def metrica(rotulo: str, valor: Any) -> None:
    with ui.column().classes("metrica gap-0"):
        ui.label(str(valor)).classes("metrica-valor")
        ui.label(rotulo).classes("metrica-rotulo")


def botao(texto: str, ao_clicar: Callable[[], Any], *, tipo: str = "secundario", icone: str | None = None, marca: str | None = None):
    # Só o botão principal usa a cor de destaque; os demais não recebem classe de cor do Quasar.
    cor = "primary" if tipo == "principal" else None
    props = "unelevated no-caps" + (" text-color=black" if tipo == "principal" else "")
    b = ui.button(texto, on_click=ao_clicar, icon=icone, color=cor).classes(f"botao-{tipo}").props(props)
    if marca:
        b.mark(marca)
    return b


class PainelFeedback:
    """Mostra a resposta da última ação e um pequeno histórico desta tela."""

    def __init__(self, ctx: ContextoTela, numero_fase: int | None = None, mensagem_inicial: str = "") -> None:
        self.ctx = ctx
        self.numero_fase = numero_fase
        self.mensagens: list[tuple[bool, str]] = []
        with ui.column().classes("w-full gap-2") as self.raiz:
            self.caixa = ui.column().classes("feedback w-full gap-1").mark("feedback")
            with self.caixa:
                self.texto = ui.label(mensagem_inicial or "Aguardando sua primeira ação.").mark("feedback-texto")
                self.extra = ui.row().classes("gap-2")
            self.lista = ui.column().classes("gap-0 w-full")

    def mostrar(self, resultado: ResultadoAcao) -> None:
        selo = resultado.dados.get("selo_concedido")
        self.caixa.classes(remove="ok erro selo-ganho")
        self.caixa.classes("selo-ganho" if selo else ("ok" if resultado.sucesso else "erro"))
        self.texto.set_text(resultado.mensagem)
        self.extra.clear()
        if selo:
            ui.notify(f"Selo {selo} conquistado!", type="positive", position="top")
            proxima = selo + 1
            with self.extra:
                if proxima <= 5:
                    botao(f"Ir para a Fase {proxima}", lambda p=proxima: ui.navigate.to(f"/fase/{p}"), tipo="principal", marca="proxima-fase")
                else:
                    botao("Ver resultados", lambda: ui.navigate.to("/resultados"), tipo="principal", marca="ver-resultados")
        self.mensagens.insert(0, (resultado.sucesso, resultado.mensagem))
        del self.mensagens[6:]
        self.lista.clear()
        with self.lista:
            for sucesso, mensagem in self.mensagens[1:]:
                ui.label(("• " if sucesso else "× ") + mensagem).classes("historico-linha" + ("" if sucesso else " erro"))


def fase_bloqueada(ctx: ContextoTela, numero: int) -> bool:
    """Se a fase estiver bloqueada, desenha o aviso e devolve True. Caso contrário posiciona a sessão nela."""
    sessao = ctx.sessao
    if numero not in range(1, 6):
        ui.label("Esta fase não existe.").classes("titulo-2")
        botao("Voltar às fases", lambda: ui.navigate.to("/jogar"))
        return True
    if not sessao.fase_liberada(numero):
        with ui.column().classes("painel gap-3 leitura").mark("fase-bloqueada"):
            ui.label(f"Fase {numero} bloqueada").classes("titulo-2")
            ui.label(f"Conquiste primeiro o selo da Fase {numero - 1}, {TITULOS_FASES[numero - 1]}.").classes("texto-suave")
            botao(f"Ir para a Fase {numero - 1}", lambda: ui.navigate.to(f"/fase/{numero - 1}"), tipo="principal")
        return True
    sessao.ir_para_fase(numero)
    ctx.atualizar_selos()
    return False


def cabecalho_fase(ctx: ContextoTela, numero: int, ao_reiniciar: Callable[[], None], explicacao: str) -> None:
    fase = ctx.sessao.fases[numero]
    conquistado = numero in ctx.sessao.selos
    with ui.row().classes("w-full items-start justify-between gap-4 q-mt-lg"):
        with ui.column().classes("gap-1 leitura"):
            ui.label(f"Fase {numero}: {fase.titulo}").classes("titulo-2")
            ui.label(fase.objetivo).classes("texto-suave")
            ui.label(explicacao).classes("texto-suave").style("font-size: 0.9rem")
        with ui.row().classes("items-center gap-2"):
            ui.html(
                f'<span class="etiqueta {"ok" if conquistado else ""}">'
                f'{"Selo conquistado" if conquistado else "Selo pendente"}</span>'
            )

            def reiniciar() -> None:
                ctx.sessao.reiniciar_fase(numero)
                ctx.memoria.pop(f"fase{numero}_ultimo", None)
                ctx.atualizar_selos()
                ui.notify(f"Fase {numero} reiniciada. Seus selos foram mantidos.", position="top")
                ao_reiniciar()

            botao("Reiniciar fase", reiniciar, icone="restart_alt", marca="reiniciar-fase")
            botao("Fases", lambda: ui.navigate.to("/jogar"), icone="grid_view")
