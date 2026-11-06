"""Fase 3 — O Mapa das Seções: grafo interativo, movimentos manuais e assistente do solver."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.componentes import PainelFeedback, botao, cabecalho_fase, etiqueta, fase_bloqueada, metrica, metricas
from veridia.interface.estado import ContextoTela
from veridia.interface.svg import COR, svg_mapa

NUMERO = 3
ALGORITMOS = {"BFS": "BFS (largura, fila)", "DFS": "DFS (profundidade, pilha)", "DFS_RECURSIVA": "DFS recursiva (pilha de chamadas)"}


def _limpar_solver(ctx: ContextoTela) -> None:
    """A sugestão vale para o estado em que foi calculada; muda o estado, some a sugestão."""
    ctx.memoria.pop("fase3_sugestao", None)
    ctx.memoria.pop("fase3_solver", None)


def legenda() -> None:
    c = COR
    itens = (
        f'<svg width="16" height="16"><circle cx="8" cy="8" r="7" fill="{c["ciano"]}"/></svg>você está aqui',
        f'<svg width="16" height="16"><circle cx="8" cy="8" r="6" fill="{c["prancha2"]}" stroke="{c["ciano"]}" stroke-width="2.5"/></svg>'
        "pode ir (clique)",
        f'<svg width="16" height="16"><circle cx="8" cy="8" r="7" fill="none" stroke="{c["branco"]}" stroke-width="1.5" '
        'stroke-dasharray="3 3"/></svg>destino',
        f'<svg width="14" height="14"><rect x="3" y="3" width="8" height="8" transform="rotate(45 7 7)" fill="{c["ambar"]}" '
        f'stroke="{c["ambar"]}" stroke-width="1.5"/></svg>pista (cheia = coletada)',
        f'<svg width="28" height="10"><line x1="0" y1="5" x2="28" y2="5" stroke="{c["ambar"]}" stroke-width="2.5" '
        'stroke-dasharray="7 5"/></svg>porta trancada',
        f'<svg width="28" height="10"><line x1="0" y1="5" x2="28" y2="5" stroke="{c["ciano"]}" stroke-width="2.5" '
        'stroke-dasharray="3 5"/></svg>porta aberta',
        f'<svg width="22" height="16"><rect x="1" y="1" width="20" height="14" rx="7" fill="{c["profundo"]}" '
        f'stroke="{c["linha_fraca"]}"/><text x="11" y="12" text-anchor="middle" font-size="10" fill="{c["suave"]}">2</text></svg>'
        "custo em energia",
    )
    with ui.row().classes("legenda-mapa"):
        for item in itens:
            ui.html(f"<span>{item}</span>", sanitize=False)


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

        with ui.row().classes("w-full gap-4 q-mt-lg items-start").style("flex-wrap: wrap"):
            with ui.column().classes("visor gap-3").style("flex: 5 1 640px; min-width: 0"):
                with ui.row().classes("items-center justify-between w-full gap-2"):
                    ui.label("Mapa das seções").classes("titulo-3")
                    if sugestao:
                        etiqueta(f"Caminho sugerido pela {sugestao[0]}, numerado", "ok")
                    else:
                        ui.label("Clique em um local com contorno ciano para ir até ele.").classes("texto-suave texto-pequeno")
                ui.html(
                    svg_mapa(fase.mapa, fase.estado, caminho=sugestao[1] if sugestao else None), sanitize=False
                ).classes("w-full").mark("mapa-svg")
                legenda()

            with ui.column().classes("painel gap-3").style("flex: 2 1 300px"):
                local = fase.mapa.vertices[estado["posicao"]].nome
                ui.label(f"Você está em {local}.").classes("titulo-3").mark("local-atual")
                inicial = fase.mapa.energia_inicial
                with metricas():
                    metrica("energia restante", f'{estado["energia"]} de {inicial}', destaque=True)
                    metrica("movimentos", len(estado["trilha"]))
                ui.linear_progress(value=estado["energia"] / inicial if inicial else 0, show_value=False, size="8px",
                                   color="primary").props("rounded track-color=blue-1").classes("w-full")

                ui.label("Pistas para vencer").classes("rotulo-secao")
                with ui.column().classes("gap-0"):
                    for pista in sorted(fase.mapa.pistas_necessarias):
                        tem = pista in fase.estado.pistas
                        with ui.row().classes("items-center gap-2 no-wrap"):
                            ui.icon("check_circle" if tem else "radio_button_unchecked").style(
                                f"color: {'var(--azul-medio)' if tem else 'var(--tinta-fraca)'}"
                            )
                            ui.label(pista.replace("_", " ")).classes("" if tem else "texto-suave")
                ui.label("Pistas coletadas: " + (", ".join(estado["pistas"]) or "nenhuma")).classes(
                    "dados texto-suave"
                ).mark("pistas-coletadas")
                faltando = sorted(fase.mapa.pistas_necessarias - fase.estado.pistas)
                if not faltando:
                    ui.label("Você tem todas as pistas. Vá ao Tribunal.").classes("texto-suave")

                feedback = PainelFeedback(ctx, NUMERO, "Clique em um local destacado no mapa ou use os botões abaixo.")
                ultimo = ctx.memoria.get("fase3_ultimo")
                if ultimo is not None:
                    feedback.mostrar(ultimo)

                ui.label("Ir para").classes("rotulo-secao")
                with ui.column().classes("gap-1 w-full"):
                    for conexao in estado["conexoes"]:
                        texto = f'{conexao["nome"]} (custo {conexao["custo"]})'
                        b = botao(
                            texto,
                            lambda d=conexao["destino"]: mover(d),
                            tipo="secundario",
                            icone="lock" if conexao["bloqueada"] else "east",
                            marca=f'mover-{conexao["destino"]}',
                        ).classes("w-full").props("align=left")
                        if conexao["bloqueada"]:
                            b.classes("indisponivel").style("opacity: 0.6")
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
                    ui.label("Trilha percorrida").classes("rotulo-secao")
                    with ui.element("div").classes("cadeia").mark("trilha"):
                        for passo, movimento in enumerate(estado["trilha"], start=1):
                            if passo > 1:
                                ui.label("›").classes("elo-texto")
                            ui.label(f"{passo}. {movimento}").classes("passo")

        # Assistente do solver
        with ui.column().classes("painel gap-3 w-full q-mt-md"):
            with ui.row().classes("items-end justify-between w-full gap-3"):
                with ui.column().classes("gap-1 leitura"):
                    ui.label("Assistente do solver").classes("titulo-3")
                    ui.label(
                        "O solver usa as mesmas regras do jogo e calcula a partir da sua posição atual. Ele só sugere: "
                        "você decide se segue o caminho. A BFS acha o menor número de movimentos, não necessariamente "
                        "o menor gasto de energia."
                    ).classes("texto-suave texto-pequeno")
                with ui.row().classes("items-center gap-3"):
                    escolha = ui.select(ALGORITMOS, value=sugestao[0] if sugestao else "BFS", label="Algoritmo").props(
                        "outlined dense"
                    ).style("min-width: 250px").mark("select-busca")

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
                with metricas():
                    if busca.encontrou:
                        metrica("movimentos", busca.comprimento, destaque=True)
                        metrica("energia do caminho", busca.custo_caminho, destaque=True)
                    metrica("estados explorados", busca.estados_explorados)
                    metrica("repetidos descartados", busca.repetidos_descartados)
                    metrica("profundidade máxima" if busca.algoritmo == "DFS_RECURSIVA" else "maior fronteira",
                            busca.tamanho_max_fronteira)
                    metrica("tempo (ms)", f"{busca.tempo_segundos * 1000:.2f}")
                if busca.encontrou:
                    ui.label("Caminho sugerido (numerado no mapa)").classes("rotulo-secao")
                    with ui.element("div").classes("cadeia").mark("caminho-sugerido"):
                        for i, movimento in enumerate(busca.acoes, start=1):
                            if i > 1:
                                ui.label("›").classes("elo-texto")
                            ui.label(f"{i}. {movimento.destino}").classes("passo")
                ui.label("Ordem de exploração (primeiros estados expandidos)").classes("rotulo-secao")
                with ui.column().classes("gap-0"):
                    for i, estado_explorado in enumerate(busca.ordem_visita[:12], start=1):
                        ui.label(f"{i:>2}. {estado_explorado}").classes("dados texto-suave")
                    if len(busca.ordem_visita) > 12:
                        ui.label(
                            f"... e mais {len(busca.ordem_visita) - 12}. Veja a exploração completa, passo a passo, em Resolver."
                        ).classes("texto-suave texto-pequeno")

    conteudo()
