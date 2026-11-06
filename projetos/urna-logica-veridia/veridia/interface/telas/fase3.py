"""Fase 3 — O Mapa das Seções: grafo interativo, movimentos manuais e assistente do solver."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.componentes import PainelFeedback, botao, cabecalho_fase, fase_bloqueada, metrica
from veridia.interface.estado import ContextoTela
from veridia.interface.svg import svg_mapa

NUMERO = 3
ALGORITMOS = {"BFS": "BFS (largura, fila)", "DFS": "DFS (profundidade, pilha)", "DFS_RECURSIVA": "DFS recursiva"}


def _limpar_solver(ctx: ContextoTela) -> None:
    """A sugestão vale para o estado em que foi calculada; muda o estado, some a sugestão."""
    ctx.memoria.pop("fase3_sugestao", None)
    ctx.memoria.pop("fase3_solver", None)


def legenda() -> None:
    with ui.row().classes("gap-4 texto-suave").style("font-size: 0.82rem"):
        ui.html(
            '<span><svg width="14" height="14"><circle cx="7" cy="7" r="6" fill="#3fc7b3"/></svg> você está aqui</span>'
        )
        ui.html(
            '<span><svg width="14" height="14"><circle cx="7" cy="7" r="5.5" fill="none" stroke="#3fc7b3" stroke-width="2"/></svg>'
            " destino possível</span>"
        )
        ui.html(
            '<span><svg width="14" height="14"><circle cx="7" cy="7" r="5.5" fill="none" stroke="#e3a948" stroke-width="2"/></svg>'
            " pista (cheia = coletada)</span>"
        )
        ui.html(
            '<span><svg width="26" height="10"><line x1="0" y1="5" x2="26" y2="5" stroke="#e3a948" stroke-width="2" '
            'stroke-dasharray="7 6"/></svg> porta trancada</span>'
        )
        ui.html(
            '<span><svg width="26" height="10"><line x1="0" y1="5" x2="26" y2="5" stroke="#3fc7b3" stroke-width="2" '
            'stroke-dasharray="2 5"/></svg> porta aberta</span>'
        )
        ui.label("Números nas linhas: custo em energia.")


def tela(ctx: ContextoTela) -> None:
    if fase_bloqueada(ctx, NUMERO):
        return
    ctx.memoria.pop("fase3_ultimo", None)  # mensagens antigas não reaparecem ao voltar à tela

    @ui.refreshable
    def conteudo() -> None:
        fase = ctx.sessao.fases[NUMERO]
        estado = fase.consultar()
        sugestao = ctx.memoria.get("fase3_sugestao")  # (algoritmo, caminho) calculado a partir do estado atual
        cabecalho_fase(
            ctx,
            NUMERO,
            lambda: (_limpar_solver(ctx), conteudo.refresh()),
            "Cada conexão gasta a energia indicada na linha. Portas trancadas só abrem com as pistas certas, "
            "e as pistas são coletadas automaticamente quando você chega ao local.",
        )

        def mover(destino: str) -> None:
            resultado = ctx.agir(NUMERO, "mover", destino)
            if resultado.sucesso:
                _limpar_solver(ctx)
            ctx.memoria["fase3_ultimo"] = resultado
            conteudo.refresh()

        ctx.ao_clicar_local = mover

        with ui.row().classes("w-full gap-4 q-mt-md items-start").style("flex-wrap: wrap"):
            with ui.column().classes("visor gap-2").style("flex: 3 1 560px; min-width: 0"):
                ui.html(
                    svg_mapa(fase.mapa, fase.estado, caminho=sugestao[1] if sugestao else None), sanitize=False
                ).classes("w-full").mark("mapa-svg")
                legenda()

            with ui.column().classes("painel gap-3").style("flex: 2 1 320px"):
                with ui.row().classes("gap-6"):
                    metrica("energia restante", estado["energia"])
                    metrica("movimentos", len(estado["trilha"]))
                local = fase.mapa.vertices[estado["posicao"]].nome
                ui.label(f"Você está em {local}.").classes("titulo-3").mark("local-atual")
                faltando = sorted(fase.mapa.pistas_necessarias - fase.estado.pistas)
                ui.label(
                    "Pistas coletadas: " + (", ".join(estado["pistas"]) or "nenhuma")
                ).classes("dados").mark("pistas-coletadas")
                ui.label(
                    "Faltam para vencer: " + (", ".join(faltando) or "nenhuma. Vá ao Tribunal.")
                ).classes("texto-suave")

                feedback = PainelFeedback(ctx, NUMERO, "Clique em um local destacado no mapa ou use os botões abaixo.")
                ultimo = ctx.memoria.get("fase3_ultimo")
                if ultimo is not None:
                    feedback.mostrar(ultimo)

                ui.label("Ir para").classes("texto-suave")
                with ui.column().classes("gap-1 w-full"):
                    for conexao in estado["conexoes"]:
                        texto = f'{conexao["nome"]} (custo {conexao["custo"]})'
                        b = botao(
                            texto,
                            lambda d=conexao["destino"]: mover(d),
                            tipo="secundario",
                            icone="lock" if conexao["bloqueada"] else "east",
                            marca=f'mover-{conexao["destino"]}',
                        ).classes("w-full")
                        if conexao["bloqueada"]:
                            b.style("opacity: 0.6")
                            with b:
                                ui.tooltip(conexao["motivo"])
                def desfazer() -> None:
                    resultado = ctx.agir(NUMERO, "desfazer")
                    if resultado.sucesso:
                        _limpar_solver(ctx)
                    ctx.memoria["fase3_ultimo"] = resultado
                    conteudo.refresh()

                botao("Desfazer último movimento", desfazer, icone="undo", marca="desfazer-movimento")
                if estado["trilha"]:
                    ui.label("Trilha percorrida").classes("texto-suave")
                    with ui.column().classes("gap-0").mark("trilha"):
                        for passo, movimento in enumerate(estado["trilha"], start=1):
                            ui.label(f"{passo}. {movimento}").classes("dados texto-suave")

        # Assistente do solver
        with ui.column().classes("painel gap-3 w-full q-mt-md"):
            ui.label("Assistente do solver").classes("titulo-3")
            ui.label(
                "O solver usa as mesmas regras do jogo e calcula a partir da sua posição atual. Ele só sugere: "
                "você decide se segue o caminho. A BFS acha o menor número de movimentos, não necessariamente "
                "o menor gasto de energia."
            ).classes("texto-suave leitura")
            with ui.row().classes("items-center gap-3"):
                escolha = ui.select(ALGORITMOS, value=sugestao[0] if sugestao else "BFS", label="Algoritmo").props(
                    "dark outlined"
                ).style("min-width: 240px").mark("select-busca")

                def calcular() -> None:
                    resultado = ctx.agir(NUMERO, "solicitar_solucao", escolha.value)
                    if resultado.sucesso:
                        ctx.memoria["fase3_sugestao"] = (escolha.value, resultado.dados["caminho"])
                    else:
                        ctx.memoria.pop("fase3_sugestao", None)
                    ctx.memoria["fase3_solver"] = resultado
                    conteudo.refresh()

                botao("Calcular caminho", calcular, tipo="principal", icone="route", marca="calcular-caminho")

            resposta = ctx.memoria.get("fase3_solver")
            busca = fase.ultima_solucao
            if resposta is not None and busca is not None:
                ui.label(resposta.mensagem).classes("titulo-3" if resposta.sucesso else "etiqueta erro").mark(
                    "solver-mensagem"
                )
                with ui.row().classes("gap-6"):
                    metrica("estados explorados", busca.estados_explorados)
                    metrica("repetidos descartados", busca.repetidos_descartados)
                    metrica("maior fronteira", busca.tamanho_max_fronteira)
                    metrica("tempo (ms)", f"{busca.tempo_segundos * 1000:.2f}")
                    if busca.encontrou:
                        metrica("energia do caminho", busca.custo_caminho)
                if busca.encontrou:
                    ui.label("Caminho sugerido (destacado no mapa): " + " > ".join(m.destino for m in busca.acoes)).classes(
                        "dados"
                    ).mark("caminho-sugerido")
                ui.label("Ordem de exploração (primeiros estados expandidos)").classes("texto-suave")
                with ui.column().classes("gap-0"):
                    for i, estado_explorado in enumerate(busca.ordem_visita[:12], start=1):
                        ui.label(f"{i:>2}. {estado_explorado}").classes("dados texto-suave")
                    if len(busca.ordem_visita) > 12:
                        ui.label(
                            f"... e mais {len(busca.ordem_visita) - 12}. Veja a exploração completa, passo a passo, em Resolver."
                        ).classes("texto-suave")

    conteudo()
