"""Componentes visuais reutilizados pelas telas.

Nada aqui decide regras: os componentes só leem a sessão (selos, fases
liberadas) e exibem ``ResultadoAcao`` devolvidos pelo motor.
"""

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

# O que cada fase demonstra, em linguagem de jogador (capa e Jogar).
CONTEUDO_FASES = {
    1: "Ordenação com chave composta: Bubble, Merge e Quick Sort.",
    2: "Fila, pilha e lista ligada, com desfazer.",
    3: "Grafo, BFS e DFS, pistas, portas e energia.",
    4: "Árvore AVL, estados equivalentes e rotações.",
    5: "Integração: solver, ordenação e relatório.",
}

DESCRICAO_ESTADO = {"conquistado": "selo conquistado", "liberado": "fase liberada", "bloqueado": "bloqueada"}


def estado_selo(ctx: ContextoTela, numero: int) -> str:
    sessao = ctx.sessao
    if numero in sessao.selos:
        return "conquistado"
    return "liberado" if sessao.fase_liberada(numero) else "bloqueado"


def trilho_selos(ctx: ContextoTela) -> None:
    """Os cinco selos na barra: bloqueado, liberado, conquistado; a fase atual tem um anel."""
    sessao = ctx.sessao
    vistos: set[int] = ctx.memoria.setdefault("selos_vistos", set())
    with ui.row().classes("trilho").mark("trilho-selos"):
        for numero in range(1, 6):
            if numero > 1:
                ui.element("div").classes("trilho-ponte" + (" feita" if (numero - 1) in sessao.selos else ""))
            estado = estado_selo(ctx, numero)
            recem = " recem" if estado == "conquistado" and numero not in vistos else ""
            descricao = DESCRICAO_ESTADO[estado]
            atual = numero == sessao.fase_atual and not sessao.jogo_concluido()
            with ui.element("div").classes("selo-anel" + (" atual" if atual else "")):
                selo = ui.element("div").classes(f"selo {estado}{recem}").props(
                    f'role="button" tabindex="0" aria-label="Fase {numero}, {descricao}"'
                ).mark(f"selo-{numero}")
                with selo:
                    ui.label("✓" if estado == "conquistado" else str(numero))
                    ui.tooltip(f"Fase {numero}: {TITULOS_FASES[numero]} ({descricao})")
                if estado != "bloqueado":
                    selo.on("click", lambda n=numero: ui.navigate.to(f"/fase/{n}"))
                    selo.on("keydown.enter", lambda n=numero: ui.navigate.to(f"/fase/{n}"))
        ui.label(f"{len(sessao.selos)} de 5 selos").classes("trilho-contagem")
    vistos.update(sessao.selos)


def fio_custodia(ctx: ContextoTela) -> None:
    """Versão grande do trilho, na capa: os cinco selos ligados pelo fio de custódia."""
    sessao = ctx.sessao
    with ui.element("div").classes("fio").mark("fio-custodia"):
        for numero in range(1, 6):
            estado = estado_selo(ctx, numero)
            feita = " feita" if (numero - 1) in sessao.selos else ""
            etapa = ui.element("div").classes(f"fio-etapa {estado}{feita}").props(
                f'aria-label="Fase {numero}: {TITULOS_FASES[numero]}, {DESCRICAO_ESTADO[estado]}"'
            )
            if estado != "bloqueado":
                etapa.props('role="link" tabindex="0"')
                etapa.on("click", lambda n=numero: ui.navigate.to(f"/fase/{n}"))
                etapa.on("keydown.enter", lambda n=numero: ui.navigate.to(f"/fase/{n}"))
            with etapa:
                ui.label("✓" if estado == "conquistado" else str(numero)).classes("fio-hex")
                with ui.element("div"):
                    ui.label(TITULOS_FASES[numero]).classes("fio-titulo")
                    ui.label(CONTEUDO_FASES[numero]).classes("fio-conteudo")


def metrica(rotulo: str, valor: Any, *, destaque: bool = False) -> None:
    with ui.column().classes("metrica" + (" destaque" if destaque else "")):
        ui.label(str(valor)).classes("metrica-valor")
        ui.label(rotulo).classes("metrica-rotulo")


def metricas() -> ui.row:
    """Contêiner padrão de métricas (use com ``with``)."""
    return ui.row().classes("metricas")


def etiqueta(texto: str, tipo: str = "") -> ui.html:
    return ui.html(f'<span class="etiqueta {tipo}">{texto}</span>', sanitize=False)


def botao(texto: str, ao_clicar: Callable[[], Any], *, tipo: str = "secundario", icone: str | None = None, marca: str | None = None):
    # Só o botão principal usa a cor de destaque; os demais não recebem classe de cor do Quasar.
    cor = "primary" if tipo == "principal" else None
    b = ui.button(texto, on_click=ao_clicar, icon=icone, color=cor).classes(f"botao-{tipo}").props("unelevated no-caps")
    if marca:
        b.mark(marca)
    return b


def botao_acao(nome: str, efeito: str, ao_clicar: Callable[[], Any], *, marca: str, disponivel: bool = True):
    """Botão de operação em duas linhas: o nome e o efeito previsto (ex.: qual evidência se move).

    ``disponivel`` só muda a aparência: o clique continua chegando à fase, que
    decide e explica quando a operação é inválida.
    """
    b = ui.button(on_click=ao_clicar, color=None).classes(
        "botao-secundario botao-acao w-full" + ("" if disponivel else " indisponivel")
    ).props("unelevated no-caps align=left").mark(marca)
    with b:
        ui.label(nome).classes("acao-nome")
        ui.label(efeito).classes("acao-efeito")
    return b


class PainelFeedback:
    """Mostra a resposta da última ação e um pequeno histórico desta tela."""

    def __init__(self, ctx: ContextoTela, numero_fase: int | None = None, mensagem_inicial: str = "") -> None:
        self.ctx = ctx
        self.numero_fase = numero_fase
        self.mensagens: list[tuple[bool, str]] = []
        with ui.column().classes("w-full gap-2") as self.raiz:
            self.caixa = ui.column().classes("feedback w-full gap-2").props('role="status" aria-live="polite"').mark("feedback")
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
                    botao(f"Ir para a Fase {proxima}", lambda p=proxima: ui.navigate.to(f"/fase/{p}"),
                          tipo="principal", icone="arrow_forward", marca="proxima-fase")
                else:
                    botao("Ver resultados", lambda: ui.navigate.to("/resultados"), tipo="principal",
                          icone="assessment", marca="ver-resultados")
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
        ui.label("Esta fase não existe.").classes("titulo-2 q-mt-lg")
        botao("Voltar às fases", lambda: ui.navigate.to("/jogar"))
        return True
    if not sessao.fase_liberada(numero):
        with ui.row().classes("painel leitura q-mt-xl items-start no-wrap gap-4").mark("fase-bloqueada"):
            ui.label(str(numero)).classes("cartao-hex")
            with ui.column().classes("gap-2"):
                ui.label(f"Fase {numero} bloqueada").classes("titulo-2")
                ui.label(f"Conquiste primeiro o selo da Fase {numero - 1}, {TITULOS_FASES[numero - 1]}.").classes("texto-suave")
                botao(f"Ir para a Fase {numero - 1}", lambda: ui.navigate.to(f"/fase/{numero - 1}"), tipo="principal", icone="arrow_back")
        return True
    sessao.ir_para_fase(numero)
    ctx.atualizar_selos()
    return False


def cabecalho_fase(ctx: ContextoTela, numero: int, ao_reiniciar: Callable[[], None], explicacao: str) -> None:
    fase = ctx.sessao.fases[numero]
    conquistado = numero in ctx.sessao.selos
    with ui.row().classes("cabecalho-fase"):
        ui.label("✓" if conquistado else str(numero)).classes("cabecalho-hex" + (" conquistado" if conquistado else ""))
        with ui.column().classes("gap-1 leitura"):
            ui.label(f"Fase {numero}: {fase.titulo}").classes("titulo-2")
            ui.label(fase.objetivo).classes("cabecalho-objetivo")
            ui.label(explicacao).classes("texto-suave texto-pequeno")
        with ui.row().classes("cabecalho-acoes"):
            etiqueta("Selo conquistado" if conquistado else "Selo pendente", "ok" if conquistado else "neutra")

            def reiniciar() -> None:
                ctx.sessao.reiniciar_fase(numero)
                ctx.memoria.pop(f"fase{numero}_ultimo", None)
                ctx.atualizar_selos()
                ui.notify(f"Fase {numero} reiniciada. Seus selos foram mantidos.", position="top")
                ao_reiniciar()

            botao("Reiniciar fase", reiniciar, icone="restart_alt", marca="reiniciar-fase")
            botao("Fases", lambda: ui.navigate.to("/jogar"), icone="grid_view")
