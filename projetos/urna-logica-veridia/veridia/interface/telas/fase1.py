"""Fase 1 — O Arquivo Embaralhado: terminal de conferência de registros."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.componentes import PainelFeedback, botao, cabecalho_fase, fase_bloqueada, metrica
from veridia.interface.estado import ContextoTela

NUMERO = 1
NOMES_ALGORITMOS = {"bubble_sort": "Bubble Sort", "merge_sort": "Merge Sort", "quick_sort": "Quick Sort"}
NOMES_CRITERIOS = {
    "zona_secao_horario": "Zona, seção e horário",
    "horario": "Somente horário",
    "id": "Identificador do registro",
    "status_horario": "Status e horário",
}
COLUNAS = [
    {"name": "id", "label": "Registro", "field": "id", "align": "left"},
    {"name": "zona", "label": "Zona", "field": "zona", "align": "right"},
    {"name": "secao", "label": "Seção", "field": "secao", "align": "right"},
    {"name": "horario", "label": "Horário", "field": "horario", "align": "left"},
    {"name": "opcao", "label": "Opção", "field": "opcao", "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "align": "left"},
]


def _linhas(registros) -> list[dict]:
    return [
        {
            "posicao": i,
            "id": r.id,
            "zona": r.zona,
            "secao": r.secao,
            "horario": r.horario.strftime("%H:%M:%S"),
            "opcao": r.codigo_opcao,
            "status": r.status.value.capitalize(),
        }
        for i, r in enumerate(registros, start=1)
    ]


def tela(ctx: ContextoTela) -> None:
    if fase_bloqueada(ctx, NUMERO):
        return

    @ui.refreshable
    def conteudo() -> None:
        fase = ctx.sessao.fases[NUMERO]
        cabecalho_fase(
            ctx,
            NUMERO,
            conteudo.refresh,
            "Os registros chegaram fora de ordem. Escolha um algoritmo e um critério: o arquivo só é aceito "
            "quando fica em ordem de zona, depois seção e, por fim, horário, sem perder nenhum registro.",
        )
        with ui.row().classes("w-full gap-4 q-mt-md no-wrap items-start").style("flex-wrap: wrap"):
            with ui.column().classes("visor gap-2").style("flex: 3 1 560px; min-width: 0"):
                titulo_tabela = "Arquivo ordenado" if fase.resultado is not None else "Arquivo embaralhado"
                ui.label(f"{titulo_tabela} ({len(fase.lote)} registros)").classes("titulo-3").mark("titulo-tabela")
                registros = fase.resultado if fase.resultado is not None else fase.lote
                ui.table(rows=_linhas(registros), columns=COLUNAS, row_key="posicao", pagination=10).classes(
                    "w-full"
                ).props("dense flat dark").mark("tabela-registros")
                if fase.inconsistencias:
                    ui.label(f"Problema encontrado: {fase.inconsistencias[0]}").classes("etiqueta erro").style(
                        "white-space: normal"
                    )

            with ui.column().classes("painel gap-3").style("flex: 2 1 320px"):
                ui.label("Conferência").classes("titulo-3")
                algoritmo = ui.select(NOMES_ALGORITMOS, label="Algoritmo de ordenação", value=fase.algoritmo).classes(
                    "w-full"
                ).props("dark outlined").mark("select-algoritmo")
                criterio = ui.select(NOMES_CRITERIOS, label="Critério", value=fase.criterio).classes("w-full").props(
                    "dark outlined"
                ).mark("select-criterio")
                ui.label(
                    "Chave composta: compara a zona; se empatar, a seção; se ainda empatar, o horário."
                ).classes("texto-suave").style("font-size: 0.85rem")
                feedback = PainelFeedback(ctx, NUMERO)

                def ordenar() -> None:
                    for acao, valor, nome in (
                        ("selecionar_algoritmo", algoritmo.value, "um algoritmo"),
                        ("selecionar_criterio", criterio.value, "um critério"),
                    ):
                        if valor is None:
                            feedback.mostrar(ctx.agir(NUMERO, "executar_ordenacao"))  # a fase explica o que falta
                            return
                        resposta = ctx.agir(NUMERO, acao, valor)
                        if not resposta.sucesso:
                            feedback.mostrar(resposta)
                            return
                    resultado = ctx.agir(NUMERO, "executar_ordenacao")
                    ctx.memoria["fase1_ultimo"] = resultado
                    conteudo.refresh()

                botao("Executar ordenação", ordenar, tipo="principal", icone="sort", marca="executar-ordenacao")
                ultimo = ctx.memoria.get("fase1_ultimo")
                if ultimo is not None and fase.resultado is not None:
                    feedback.mostrar(ultimo)
                if fase.metricas is not None:
                    with ui.row().classes("gap-4"):
                        metrica("comparações", fase.metricas.comparacoes)
                        metrica("movimentações", fase.metricas.movimentacoes)
                        metrica("tempo (ms)", f"{fase.metricas.tempo_segundos * 1000:.2f}")

        with ui.column().classes("painel gap-2 w-full q-mt-md"):
            with ui.row().classes("items-center justify-between w-full") as topo:
                with ui.column().classes("gap-0"):
                    ui.label("Comparar os três algoritmos").classes("titulo-3")
                    ui.label("Mesmo lote e chave composta. Não altera a fase.").classes("texto-suave")
            area = ui.column().classes("w-full gap-2")

            def comparar() -> None:
                tabela = ctx.agir(NUMERO, "comparar_algoritmos").dados["tabela"]
                maior = max(linha["comparacoes"] for linha in tabela) or 1
                area.clear()
                with area:
                    for linha in tabela:
                        with ui.row().classes("items-center w-full gap-3").mark(f"comparacao-{linha['algoritmo']}"):
                            ui.label(NOMES_ALGORITMOS[linha["algoritmo"]]).style("width: 110px")
                            largura = max(2, round(100 * linha["comparacoes"] / maior))
                            ui.element("div").style(
                                f"height: 10px; width: {largura}%; max-width: 55%; background: var(--agua); border-radius: 3px"
                            )
                            ui.label(
                                f'{linha["comparacoes"]} comparações, {linha["movimentacoes"]} movimentações, '
                                f'{linha["tempo_segundos"] * 1000:.2f} ms'
                            ).classes("dados texto-suave")

            with topo:
                botao("Comparar", comparar, icone="bar_chart", marca="comparar-algoritmos")


    conteudo()
