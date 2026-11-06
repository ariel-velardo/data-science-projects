"""Fase 5 — A Auditoria Final: consolidação das fases em um relatório visual e exportável."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from veridia.fases.fase5_auditoria import relatorio_para_dict
from veridia.interface.componentes import PainelFeedback, botao, cabecalho_fase, fase_bloqueada, metrica
from veridia.interface.estado import ContextoTela
from veridia.interface.exportacao import NOMES_VERIFICACAO, relatorio_html, relatorio_json

NUMERO = 5
BUSCAS = {"BFS": "BFS", "DFS": "DFS iterativa", "DFS_RECURSIVA": "DFS recursiva"}
ORDENACOES = {"merge_sort": "Merge Sort", "quick_sort": "Quick Sort", "bubble_sort": "Bubble Sort"}


def relatorio_visual(relatorio: dict[str, Any]) -> None:
    """Desenha o relatório (dicionário de ``relatorio_para_dict``). Reutilizado pela tela Resultados."""
    consistente = relatorio["consistente"]
    with ui.column().classes("w-full gap-3").mark("relatorio"):
        ui.html(
            f'<span class="etiqueta {"ok" if consistente else "erro"}" style="font-size: 1rem; padding: 4px 14px">'
            f'{"Auditoria consistente" if consistente else "Auditoria inconsistente"}</span>'
        ).mark("relatorio-consistencia")
        with ui.row().classes("gap-6"):
            metrica("movimentos", relatorio["movimentos"])
            metrica("energia consumida", relatorio["energia_consumida"])
            metrica("estados explorados", relatorio["estados_explorados"])
            metrica("tempo da busca (ms)", f'{relatorio["tempo_busca_segundos"] * 1000:.2f}')
            metrica("tempo total (ms)", f'{relatorio["tempo_total_segundos"] * 1000:.2f}')
        ui.label(
            f'Busca: {BUSCAS.get(relatorio["algoritmo_busca"], relatorio["algoritmo_busca"])}. '
            f'Ordenação: {ORDENACOES.get(relatorio["algoritmo_ordenacao"], relatorio["algoritmo_ordenacao"])} '
            f'({relatorio["metricas_ordenacao"]["comparacoes"]} comparações em {relatorio["registros_conferidos"]} registros). '
            f'Trilha de origem: {"jogada manual" if relatorio["origem_trilha"] == "manual" else "referência do solver"}.'
        ).classes("texto-suave")

        with ui.row().classes("w-full gap-4 items-start").style("flex-wrap: wrap"):
            with ui.column().classes("gap-0").style("flex: 3 1 420px"):
                ui.label("Verificações").classes("titulo-3")
                for verificacao in relatorio["verificacoes"]:
                    with ui.row().classes("verificacao w-full no-wrap items-start gap-3").mark(f"verificacao-{verificacao['nome']}"):
                        ui.label("✓" if verificacao["ok"] else "✗").classes("marca-ok" if verificacao["ok"] else "marca-erro")
                        with ui.column().classes("gap-0"):
                            ui.label(NOMES_VERIFICACAO.get(verificacao["nome"], verificacao["nome"]))
                            ui.label(verificacao["detalhe"]).classes("texto-suave").style("font-size: 0.88rem")
            with ui.column().classes("gap-2").style("flex: 2 1 300px"):
                ui.label("Caminho no mapa").classes("titulo-3")
                ui.label(" > ".join(relatorio["caminho"]) or "nenhum").classes("dados").mark("relatorio-caminho")
                ui.label("Cadeia de custódia").classes("titulo-3")
                ui.label(" > ".join(relatorio["custodia"]) or "vazia").classes("dados")
                ui.label(f'Evidências (ordenadas com {ORDENACOES.get(relatorio["algoritmo_ordenacao"], "")})').classes("titulo-3")
                for evidencia in relatorio["evidencias_ordenadas"]:
                    ui.label(f'{evidencia["tipo"]}: {evidencia["id"]}').classes("dados texto-suave")


def botoes_exportacao(relatorio: dict[str, Any]) -> None:
    with ui.row().classes("gap-2"):
        botao(
            "Baixar JSON",
            lambda: ui.download.content(relatorio_json(relatorio), "relatorio-auditoria-veridia.json", "application/json"),
            icone="data_object",
            marca="baixar-json",
        )
        botao(
            "Baixar HTML para imprimir",
            lambda: ui.download.content(relatorio_html(relatorio), "relatorio-auditoria-veridia.html", "text/html"),
            icone="print",
            marca="baixar-html",
        )
    ui.label("O HTML abre em qualquer navegador; use Imprimir > Salvar como PDF para gerar o PDF.").classes(
        "texto-suave"
    ).style("font-size: 0.85rem")


def tela(ctx: ContextoTela) -> None:
    if fase_bloqueada(ctx, NUMERO):
        return
    ctx.memoria.pop("fase5_ultimo", None)  # mensagens antigas não reaparecem ao voltar à tela

    @ui.refreshable
    def conteudo() -> None:
        fase = ctx.sessao.fases[NUMERO]
        cabecalho_fase(
            ctx,
            NUMERO,
            conteudo.refresh,
            "A auditoria reconfere o estado atual de cada fase: refaz a ordenação, revalida a custódia, "
            "reexecuta sua trilha pelas regras e roda o solver. O quinto selo só vem se tudo estiver consistente.",
        )
        with ui.row().classes("painel w-full items-end gap-3 q-mt-md"):
            busca = ui.select(BUSCAS, value="BFS", label="Algoritmo de busca").props("dark outlined").style("min-width: 200px").mark("auditoria-busca")
            ordenacao = ui.select(ORDENACOES, value="merge_sort", label="Algoritmo de ordenação").props("dark outlined").style("min-width: 200px").mark("auditoria-ordenacao")

            def auditar() -> None:
                ctx.memoria["fase5_ultimo"] = ctx.agir(NUMERO, "executar_auditoria", busca.value, ordenacao.value)
                conteudo.refresh()

            botao("Executar auditoria", auditar, tipo="principal", icone="verified", marca="executar-auditoria")

        feedback = PainelFeedback(ctx, NUMERO, "Escolha os algoritmos e execute a auditoria.")
        ultimo = ctx.memoria.get("fase5_ultimo")
        if ultimo is not None:
            feedback.mostrar(ultimo)
        if fase.relatorio is not None:
            relatorio = relatorio_para_dict(fase.relatorio)
            with ui.column().classes("visor w-full gap-3 q-mt-md"):
                relatorio_visual(relatorio)
                botoes_exportacao(relatorio)

    conteudo()
