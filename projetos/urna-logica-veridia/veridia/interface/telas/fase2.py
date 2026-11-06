"""Fase 2 — A Central de Triagem: fila, pilha, lista de custódia e arquivo."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.componentes import PainelFeedback, botao, cabecalho_fase, fase_bloqueada
from veridia.interface.estado import ContextoTela

NUMERO = 2
ACOES = (
    ("receber_na_custodia", "Receber na custódia", "Frente da fila vai para o fim da custódia."),
    ("guardar_na_pilha", "Guardar na pilha", "Frente da fila vai para o topo da pilha."),
    ("custodiar_da_pilha", "Pilha para custódia", "Topo da pilha vai para o fim da custódia."),
    ("arquivar_da_fila", "Arquivar da fila", "Frente da fila vai para o arquivo."),
    ("arquivar_da_pilha", "Arquivar da pilha", "Topo da pilha vai para o arquivo."),
)
NOMES_ACOES = {chave: nome for chave, nome, _ in ACOES}


def _ficha(texto: str, classe: str = "", marca: str | None = None) -> None:
    f = ui.label(texto).classes(f"ficha {classe}")
    if marca:
        f.mark(marca)


def tela(ctx: ContextoTela) -> None:
    if fase_bloqueada(ctx, NUMERO):
        return
    ctx.memoria.pop("fase2_ultimo", None)  # mensagens antigas não reaparecem ao voltar à tela

    @ui.refreshable
    def conteudo() -> None:
        fase = ctx.sessao.fases[NUMERO]
        estado = fase.consultar()
        cabecalho_fase(
            ctx,
            NUMERO,
            conteudo.refresh,
            "As evidências chegam pela fila e só a da frente pode sair. A pilha guarda até duas e só libera o "
            "topo. A custódia só cresce pelo fim. O que não entra na custódia vai para o arquivo: nada se perde.",
        )

        with ui.row().classes("w-full gap-4 q-mt-md items-start").style("flex-wrap: wrap"):
            with ui.column().classes("visor gap-4").style("flex: 3 1 560px; min-width: 0"):
                # Sequência exigida
                with ui.column().classes("gap-1"):
                    ui.label("Sequência exigida na custódia").classes("texto-suave")
                    with ui.row().classes("gap-2").mark("sequencia-alvo"):
                        for i, alvo in enumerate(estado["sequencia_alvo"]):
                            custodia = estado["custodia"]
                            if i < len(custodia):
                                classe = "alvo-ok" if custodia[i] == alvo else "alvo-erro"
                            else:
                                classe = "fantasma"
                            _ficha(alvo, classe)

                # Fila de entrada
                with ui.column().classes("gap-1"):
                    ui.label("Fila de entrada (sai pela frente, à esquerda)").classes("texto-suave")
                    with ui.row().classes("gap-2 items-end").mark("fila"):
                        if not estado["fila_entrada"]:
                            ui.label("Fila vazia").classes("texto-suave dados")
                        for i, evidencia in enumerate(estado["fila_entrada"]):
                            with ui.column().classes("gap-0 items-center"):
                                ui.label("frente" if i == 0 else "").classes("rotulo-ponta")
                                _ficha(evidencia, "destaque" if i == 0 else "")

                with ui.row().classes("w-full gap-6 items-start"):
                    # Pilha temporária
                    with ui.column().classes("gap-1"):
                        ui.label(f"Pilha temporária (capacidade {estado['capacidade_pilha']})").classes("texto-suave")
                        with ui.element("div").classes("pilha-coluna").mark("pilha"):
                            itens = estado["pilha_temporaria"]  # base → topo
                            for posicao in range(estado["capacidade_pilha"]):
                                if posicao < len(itens):
                                    topo = posicao == len(itens) - 1
                                    with ui.row().classes("items-center gap-2"):
                                        _ficha(itens[posicao], "destaque" if topo else "")
                                        ui.label("topo" if topo else "").classes("rotulo-ponta")
                                else:
                                    _ficha("vaga", "fantasma")

                    # Lista de custódia
                    with ui.column().classes("gap-1").style("flex: 1"):
                        ui.label("Lista de custódia (lista ligada, cresce pelo fim)").classes("texto-suave")
                        with ui.row().classes("gap-1 items-center").mark("custodia"):
                            if not estado["custodia"]:
                                ui.label("Vazia").classes("texto-suave dados")
                            for i, evidencia in enumerate(estado["custodia"]):
                                if i:
                                    ui.label("→").classes("seta-lista")
                                _ficha(evidencia)
                            if estado["custodia"]:
                                ui.label("→ fim").classes("seta-lista")

                # Arquivo
                with ui.column().classes("gap-1"):
                    ui.label("Arquivo (evidências preservadas fora da custódia)").classes("texto-suave")
                    with ui.row().classes("gap-2").mark("arquivo"):
                        if not estado["arquivo"]:
                            ui.label("Nada arquivado").classes("texto-suave dados")
                        for evidencia in estado["arquivo"]:
                            _ficha(evidencia, "arquivada")

            with ui.column().classes("painel gap-3").style("flex: 2 1 320px"):
                ui.label("Operações").classes("titulo-3")
                feedback = PainelFeedback(ctx, NUMERO)

                def executar(acao: str) -> None:
                    resultado = ctx.agir(NUMERO, acao)
                    ctx.memoria["fase2_ultimo"] = resultado
                    conteudo.refresh()

                with ui.grid(columns=2).classes("w-full gap-2"):
                    for chave, nome, dica in ACOES:
                        with botao(nome, lambda c=chave: executar(c), marca=f"acao-{chave}"):
                            ui.tooltip(dica)
                with ui.row().classes("gap-2"):
                    botao("Desfazer", lambda: executar("desfazer"), icone="undo", marca="acao-desfazer")
                    botao("Validar custódia", lambda: executar("validar"), tipo="principal", icone="fact_check", marca="acao-validar")
                ultimo = ctx.memoria.get("fase2_ultimo")
                if ultimo is not None:
                    feedback.mostrar(ultimo)

                sugestao_area = ui.column().classes("gap-1 w-full")

                def sugerir() -> None:
                    resultado = ctx.agir(NUMERO, "sugerir_solucao")
                    sugestao_area.clear()
                    with sugestao_area:
                        ui.label(resultado.mensagem).classes("texto-suave").mark("sugestao-texto")
                        for passo, acao in enumerate(resultado.dados.get("acoes", []), start=1):
                            ui.label(f"{passo}. {NOMES_ACOES[acao]}").classes("dados")
                        if resultado.sucesso:
                            ui.label("A sugestão não é aplicada: execute os passos você mesmo.").classes(
                                "texto-suave"
                            ).style("font-size: 0.85rem")

                botao("Pedir sugestão ao solver (BFS)", sugerir, icone="psychology", marca="acao-sugerir")

                if estado["historico"]:
                    ui.label("Histórico (mais recente primeiro; o desfazer retira daqui)").classes("texto-suave q-mt-sm")
                    with ui.column().classes("gap-0").mark("historico-pilha"):
                        for descricao in estado["historico"]:
                            ui.label(descricao).classes("dados texto-suave")

    conteudo()
