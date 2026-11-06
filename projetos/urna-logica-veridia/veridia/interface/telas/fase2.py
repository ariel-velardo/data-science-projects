"""Fase 2 — A Central de Triagem: fila, pilha, lista de custódia e arquivo."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from veridia.interface.componentes import PainelFeedback, botao, botao_acao, cabecalho_fase, fase_bloqueada
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
DESTINOS = {
    "receber_na_custodia": "o fim da custódia",
    "guardar_na_pilha": "o topo da pilha",
    "arquivar_da_fila": "o arquivo",
    "custodiar_da_pilha": "o fim da custódia",
    "arquivar_da_pilha": "o arquivo",
}


def _ficha(texto: str, classe: str = "", marca: str | None = None) -> None:
    f = ui.label(texto).classes(f"ficha {classe}")
    if marca:
        f.mark(marca)


def _novos(estado: dict[str, Any], anterior: dict[str, Any] | None, chave: str) -> set[str]:
    """Evidências que acabaram de chegar a uma estrutura (só para animar a chegada)."""
    if anterior is None:
        return set()
    return set(estado[chave]) - set(anterior.get(chave, []))


def _cabeca(nome: str, regra: str) -> None:
    with ui.row().classes("estrutura-cabeca"):
        ui.label(nome).classes("estrutura-nome")
        ui.label(regra).classes("estrutura-regra")


def tela(ctx: ContextoTela) -> None:
    if fase_bloqueada(ctx, NUMERO):
        return
    ctx.memoria.pop("fase2_ultimo", None)  # mensagens antigas não reaparecem ao voltar à tela
    ctx.memoria.pop("fase2_anterior", None)

    @ui.refreshable
    def conteudo() -> None:
        fase = ctx.sessao.fases[NUMERO]
        estado = fase.consultar()
        anterior = ctx.memoria.get("fase2_anterior")
        ctx.memoria["fase2_anterior"] = {k: list(estado[k]) for k in ("fila_entrada", "pilha_temporaria", "custodia", "arquivo")}
        cabecalho_fase(
            ctx,
            NUMERO,
            lambda: (ctx.memoria.pop("fase2_anterior", None), conteudo.refresh()),
            "As evidências chegam pela fila e só a da frente pode sair. A pilha guarda até duas e só libera o "
            "topo. A custódia só cresce pelo fim. O que não entra na custódia vai para o arquivo: nada se perde.",
        )

        fila, pilha, custodia = estado["fila_entrada"], estado["pilha_temporaria"], estado["custodia"]
        frente = fila[0] if fila else None
        topo = pilha[-1] if pilha else None
        capacidade = estado["capacidade_pilha"]

        with ui.row().classes("w-full gap-4 q-mt-lg items-start").style("flex-wrap: wrap"):
            with ui.column().classes("visor gap-5").style("flex: 3 1 560px; min-width: 0"):
                # Sequência exigida
                with ui.column().classes("estrutura w-full"):
                    _cabeca("Sequência exigida na custódia", "a custódia precisa ficar exatamente assim")
                    with ui.element("div").classes("alvo-trilho").mark("sequencia-alvo"):
                        for i, alvo in enumerate(estado["sequencia_alvo"]):
                            if i < len(custodia):
                                classe = "alvo-ok" if custodia[i] == alvo else "alvo-erro"
                            else:
                                classe = "fantasma"
                            _ficha(alvo, classe)

                # Fila de entrada
                novos_fila = _novos(estado, anterior, "fila_entrada")
                with ui.column().classes("estrutura w-full"):
                    _cabeca("Fila de entrada", "FIFO: só sai a evidência da frente")
                    with ui.element("div").classes("fila-trilho").mark("fila"):
                        ui.icon("west").classes("saida-seta").props('aria-label="saída da fila"')
                        if not fila:
                            ui.label("Fila vazia").classes("texto-suave dados").style("align-self: center")
                        for i, evidencia in enumerate(fila):
                            ponta = "frente" if i == 0 else ("fim" if i == len(fila) - 1 else "")
                            with ui.column().classes("gap-1 items-center"):
                                ui.label(ponta).classes("ponta")
                                _ficha(evidencia, ("destaque" if i == 0 else "") + (" nova" if evidencia in novos_fila else ""))

                with ui.row().classes("w-full gap-6 items-start").style("flex-wrap: wrap"):
                    # Pilha temporária
                    novos_pilha = _novos(estado, anterior, "pilha_temporaria")
                    with ui.column().classes("estrutura"):
                        _cabeca("Pilha temporária", f"LIFO, até {capacidade}")
                        with ui.element("div").classes("pilha-caixa").mark("pilha"):
                            for posicao in range(capacidade):  # base → topo (a caixa empilha de baixo para cima)
                                with ui.element("div").classes("pilha-linha"):
                                    if posicao < len(pilha):
                                        e_topo = posicao == len(pilha) - 1
                                        _ficha(pilha[posicao], ("destaque" if e_topo else "") + (" nova" if pilha[posicao] in novos_pilha else ""))
                                        ui.label("topo" if e_topo else "").classes("ponta")
                                    else:
                                        _ficha("vaga", "fantasma")

                    # Lista de custódia
                    novos_custodia = _novos(estado, anterior, "custodia")
                    with ui.column().classes("estrutura").style("flex: 1 1 260px; min-width: 0"):
                        _cabeca("Lista de custódia", "lista ligada: só cresce pelo fim")
                        with ui.element("div").classes("custodia-trilho").mark("custodia"):
                            if not custodia:
                                ui.label("Vazia: início aponta para nulo").classes("texto-suave dados")
                            for i, evidencia in enumerate(custodia):
                                if i:
                                    ui.element("div").classes("elo")
                                with ui.column().classes("gap-1 items-center"):
                                    ui.label("início" if i == 0 else ("fim" if i == len(custodia) - 1 else "")).classes("ponta")
                                    with ui.element("div").classes("no-lista" + (" nova" if evidencia in novos_custodia else "")):
                                        _ficha(evidencia)
                                        ui.element("div").classes("ponteiro")
                            if custodia:
                                ui.element("div").classes("elo")
                                ui.label("nulo").classes("nulo")

                # Arquivo
                novos_arquivo = _novos(estado, anterior, "arquivo")
                with ui.column().classes("estrutura w-full"):
                    _cabeca("Arquivo", "evidências preservadas fora da custódia")
                    with ui.row().classes("gap-2").mark("arquivo"):
                        if not estado["arquivo"]:
                            ui.label("Nada arquivado").classes("texto-suave dados")
                        for evidencia in estado["arquivo"]:
                            _ficha(evidencia, "arquivada" + (" nova" if evidencia in novos_arquivo else ""))

            with ui.column().classes("painel gap-3").style("flex: 2 1 320px"):
                ui.label("Operações").classes("titulo-3")

                def executar(acao: str) -> None:
                    resultado = ctx.agir(NUMERO, acao)
                    ctx.memoria["fase2_ultimo"] = resultado
                    conteudo.refresh()

                def efeito(chave: str, origem: str | None, motivo_vazio: str) -> tuple[str, bool]:
                    if origem is None:
                        return motivo_vazio, False
                    if chave == "guardar_na_pilha" and len(pilha) >= capacidade:
                        return f"{origem} não cabe: a pilha está cheia", False
                    return f"{origem} vai para {DESTINOS[chave]}", True

                for titulo, origem, vazio, chaves in (
                    (f"Da frente da fila ({frente or 'vazia'})", frente, "a fila está vazia",
                     ("receber_na_custodia", "guardar_na_pilha", "arquivar_da_fila")),
                    (f"Do topo da pilha ({topo or 'vazia'})", topo, "a pilha está vazia",
                     ("custodiar_da_pilha", "arquivar_da_pilha")),
                ):
                    with ui.column().classes("grupo-acoes w-full"):
                        ui.label(titulo).classes("rotulo-secao")
                        with ui.grid().classes("w-full gap-2").style("grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))"):
                            for chave in chaves:
                                texto, disponivel = efeito(chave, origem, vazio)
                                botao_acao(NOMES_ACOES[chave], texto, lambda c=chave: executar(c),
                                           marca=f"acao-{chave}", disponivel=disponivel)

                with ui.row().classes("gap-2 w-full items-center"):
                    desfazer = botao("Desfazer", lambda: executar("desfazer"), icone="undo", marca="acao-desfazer")
                    with desfazer:
                        ui.tooltip(f"Desfaz: {estado['historico'][0]}" if estado["historico"] else "Nada para desfazer")
                    botao("Validar custódia", lambda: executar("validar"), tipo="principal", icone="fact_check", marca="acao-validar")

                feedback = PainelFeedback(ctx, NUMERO, "Escolha uma operação. Ações inválidas são recusadas e não mudam nada.")
                ultimo = ctx.memoria.get("fase2_ultimo")
                if ultimo is not None:
                    feedback.mostrar(ultimo)

                if estado["historico"]:
                    ui.label("Pilha de desfazer (topo primeiro)").classes("rotulo-secao q-mt-sm")
                    with ui.column().classes("gap-0").mark("historico-pilha"):
                        for i, descricao in enumerate(estado["historico"]):
                            ui.label(("topo: " if i == 0 else "") + descricao).classes("dados texto-suave")

                ui.separator()
                sugestao_area = ui.column().classes("gap-1 w-full")

                def sugerir() -> None:
                    resultado = ctx.agir(NUMERO, "sugerir_solucao")
                    sugestao_area.clear()
                    with sugestao_area:
                        ui.label(resultado.mensagem).classes("texto-suave").mark("sugestao-texto")
                        for passo, acao in enumerate(resultado.dados.get("acoes", []), start=1):
                            with ui.element("div").classes("passo-sugerido"):
                                ui.label(str(passo)).classes("numero")
                                ui.label(NOMES_ACOES[acao])
                        if resultado.sucesso:
                            ui.label("A sugestão não é aplicada: execute os passos você mesmo.").classes(
                                "texto-suave texto-pequeno"
                            )

                botao("Pedir sugestão ao solver (BFS)", sugerir, icone="psychology", marca="acao-sugerir")

    conteudo()
