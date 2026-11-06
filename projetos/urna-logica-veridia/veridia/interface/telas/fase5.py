"""Fase 5 — A Auditoria Final: consolidação das fases em um relatório visual e exportável."""

from __future__ import annotations

from typing import Any, Iterable

from nicegui import ui

from veridia.fases.fase5_auditoria import relatorio_para_dict
from veridia.interface.componentes import PainelFeedback, botao, cabecalho_fase, fase_bloqueada, metrica, metricas
from veridia.interface.estado import ContextoTela
from veridia.interface.exportacao import NOMES_VERIFICACAO, relatorio_html, relatorio_json

NUMERO = 5
BUSCAS = {"BFS": "BFS", "DFS": "DFS iterativa", "DFS_RECURSIVA": "DFS recursiva"}
ORDENACOES = {"merge_sort": "Merge Sort", "quick_sort": "Quick Sort", "bubble_sort": "Bubble Sort"}


def _cadeia(itens: Iterable[str], vazio: str, marca: str | None = None) -> None:
    itens = list(itens)
    caixa = ui.element("div").classes("cadeia")
    if marca:
        caixa.mark(marca)
    with caixa:
        if not itens:
            ui.label(vazio).classes("texto-suave texto-pequeno")
        for i, item in enumerate(itens):
            if i:
                ui.label("›").classes("elo-texto")
            ui.label(item).classes("passo")


def relatorio_visual(relatorio: dict[str, Any]) -> None:
    """Desenha o relatório (dicionário de ``relatorio_para_dict``). Reutilizado pela tela Resultados."""
    consistente = relatorio["consistente"]
    reprovadas = [v for v in relatorio["verificacoes"] if not v["ok"]]
    selos_antes = set(relatorio.get("selos", []))
    with ui.column().classes("w-full gap-4").mark("relatorio"):
        with ui.row().classes("veredito " + ("consistente" if consistente else "inconsistente")):
            with ui.element("div").classes("veredito-selos").props('aria-hidden="true"'):
                for numero in range(1, 6):
                    ok = consistente or numero in selos_antes
                    ui.label("✓" if ok else "✗").classes("mini-hex" + (" ok" if ok else ""))
            with ui.column().classes("gap-1").style("flex: 1 1 280px"):
                ui.label("Auditoria consistente" if consistente else "Auditoria inconsistente").classes(
                    "veredito-titulo"
                ).mark("relatorio-consistencia")
                if consistente:
                    ui.label(
                        f'As {len(relatorio["verificacoes"])} verificações foram aprovadas: o resultado de Verídia está certificado.'
                    )
                else:
                    ui.label(
                        f"{len(reprovadas)} de {len(relatorio['verificacoes'])} verificações reprovadas. "
                        "Refaça as fases indicadas e execute a auditoria de novo."
                    )
        if relatorio.get("inconsistencias"):
            with ui.column().classes("gap-0"):
                for inconsistencia in relatorio["inconsistencias"]:
                    ui.label(f"× {inconsistencia}").classes("historico-linha erro")

        with metricas():
            metrica("movimentos", relatorio["movimentos"], destaque=True)
            metrica("energia consumida", relatorio["energia_consumida"], destaque=True)
            metrica("estados explorados", relatorio["estados_explorados"])
            metrica("comparações na ordenação", relatorio["metricas_ordenacao"]["comparacoes"])
            metrica("tempo da busca (ms)", f'{relatorio["tempo_busca_segundos"] * 1000:.2f}')
            metrica("tempo total (ms)", f'{relatorio["tempo_total_segundos"] * 1000:.2f}')
        ui.label(
            f'Busca: {BUSCAS.get(relatorio["algoritmo_busca"], relatorio["algoritmo_busca"])}. '
            f'Ordenação: {ORDENACOES.get(relatorio["algoritmo_ordenacao"], relatorio["algoritmo_ordenacao"])} '
            f'({relatorio["metricas_ordenacao"]["comparacoes"]} comparações em {relatorio["registros_conferidos"]} registros). '
            f'Trilha de origem: {"jogada manual" if relatorio["origem_trilha"] == "manual" else "referência do solver"}.'
        ).classes("texto-suave texto-pequeno")

        with ui.row().classes("w-full gap-6 items-start").style("flex-wrap: wrap"):
            with ui.column().classes("gap-0").style("flex: 3 1 420px; min-width: 0"):
                ui.label("Verificações").classes("titulo-3")
                for verificacao in relatorio["verificacoes"]:
                    with ui.row().classes("verificacao w-full no-wrap items-start gap-3").mark(f"verificacao-{verificacao['nome']}"):
                        ui.label("Aprovada" if verificacao["ok"] else "Reprovada").classes(
                            "carimbo " + ("ok" if verificacao["ok"] else "erro")
                        )
                        with ui.column().classes("gap-0"):
                            ui.label(NOMES_VERIFICACAO.get(verificacao["nome"], verificacao["nome"])).style("font-weight: 600")
                            ui.label(verificacao["detalhe"]).classes("texto-suave texto-pequeno")
            with ui.column().classes("gap-2").style("flex: 2 1 300px; min-width: 0"):
                ui.label("Caminho no mapa").classes("titulo-3")
                _cadeia(relatorio["caminho"], "nenhum", "relatorio-caminho")
                ui.label("Cadeia de custódia").classes("titulo-3 q-mt-sm")
                _cadeia(relatorio["custodia"], "vazia")
                ui.label(
                    f'Evidências, ordenadas com {ORDENACOES.get(relatorio["algoritmo_ordenacao"], "")}'
                ).classes("titulo-3 q-mt-sm")
                with ui.column().classes("gap-0"):
                    for evidencia in relatorio["evidencias_ordenadas"]:
                        with ui.row().classes("gap-2 no-wrap items-baseline"):
                            ui.label(evidencia["tipo"]).classes("texto-suave texto-pequeno").style("min-width: 9em")
                            ui.label(evidencia["id"]).classes("dados")


def botoes_exportacao(relatorio: dict[str, Any]) -> None:
    with ui.row().classes("gap-2 items-center"):
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
            "texto-suave texto-pequeno"
        )


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
        with ui.row().classes("w-full gap-4 q-mt-lg items-start").style("flex-wrap: wrap"):
            with ui.column().classes("painel gap-3").style("flex: 1 1 300px"):
                ui.label("Parâmetros da auditoria").classes("titulo-3")
                busca = ui.select(BUSCAS, value="BFS", label="Algoritmo de busca").props("outlined").classes("w-full").mark("auditoria-busca")
                ordenacao = ui.select(ORDENACOES, value="merge_sort", label="Algoritmo de ordenação").props("outlined").classes(
                    "w-full"
                ).mark("auditoria-ordenacao")

                def auditar() -> None:
                    ctx.memoria["fase5_ultimo"] = ctx.agir(NUMERO, "executar_auditoria", busca.value, ordenacao.value)
                    conteudo.refresh()

                botao("Executar auditoria", auditar, tipo="principal", icone="verified", marca="executar-auditoria")
                feedback = PainelFeedback(ctx, NUMERO, "Escolha os algoritmos e execute a auditoria.")
                ultimo = ctx.memoria.get("fase5_ultimo")
                if ultimo is not None:
                    feedback.mostrar(ultimo)

            with ui.column().classes("painel gap-3").style("flex: 3 1 600px; min-width: 0"):
                if fase.relatorio is not None:
                    relatorio = relatorio_para_dict(fase.relatorio)
                    relatorio_visual(relatorio)
                    ui.separator()
                    botoes_exportacao(relatorio)
                else:
                    ui.label("Relatório da auditoria").classes("titulo-3")
                    ui.label(
                        "Ainda não executada. A auditoria confere a ordenação, a custódia, a trilha no mapa, "
                        "as evidências, o estado final, o cofre e os selos das fases 1 a 4."
                    ).classes("texto-suave")

    conteudo()
