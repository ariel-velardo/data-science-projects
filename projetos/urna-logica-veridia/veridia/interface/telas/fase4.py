"""Fase 4 — O Cofre dos Estados: estados equivalentes × distintos na árvore AVL."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.componentes import PainelFeedback, botao, cabecalho_fase, etiqueta, fase_bloqueada, metrica, metricas
from veridia.interface.estado import ContextoTela
from veridia.interface.svg import nos_reposicionados, svg_arvore
from veridia.modelos.estado import EstadoJogo

NUMERO = 4
NOMES_ROTACOES = {
    "esquerda": "rotação simples à esquerda",
    "direita": "rotação simples à direita",
    "dupla_esq_dir": "rotação dupla esquerda-direita",
    "dupla_dir_esq": "rotação dupla direita-esquerda",
}
NOMES_ATRIBUTOS = ("Posição", "Pistas", "Portas abertas", "Energia")


def _descrever_rotacoes(rotacoes: dict[str, int]) -> str:
    return ", ".join(f"{NOMES_ROTACOES.get(tipo, tipo)} ({n}x)" for tipo, n in rotacoes.items())


def _valores(estado: EstadoJogo) -> tuple[str, ...]:
    """Os quatro componentes da chave canônica, como texto."""
    chave = estado.chave()
    return (str(chave[0]), ", ".join(chave[1]) or "nenhuma", ", ".join(chave[2]) or "nenhuma", str(chave[3]))


def _atributos(estado: EstadoJogo) -> None:
    with ui.element("div").classes("atributos"):
        for rotulo, valor in zip(NOMES_ATRIBUTOS, _valores(estado)):
            ui.label(rotulo).classes("texto-suave texto-pequeno")
            ui.label(valor).classes("dados")


def tela(ctx: ContextoTela) -> None:
    if fase_bloqueada(ctx, NUMERO):
        return
    ctx.memoria.pop("fase4_ultimo", None)  # mensagens antigas não reaparecem ao voltar à tela

    @ui.refreshable
    def conteudo() -> None:
        fase = ctx.sessao.fases[NUMERO]
        cabecalho_fase(
            ctx,
            NUMERO,
            lambda: (ctx.memoria.pop("fase4_destaque", None), conteudo.refresh()),
            "Estados chegam ao cofre um por vez. Dois estados só são o mesmo se TODOS os atributos da chave "
            "coincidem: posição, pistas, portas abertas e energia. O cofre é uma árvore AVL indexada por essa chave.",
        )

        with ui.row().classes("w-full gap-4 q-mt-lg items-start").style("flex-wrap: wrap"):
            with ui.column().classes("painel gap-3").style("flex: 2 1 340px"):
                atual = fase.candidato_atual()
                with ui.row().classes("items-center gap-2 w-full no-wrap"):
                    ui.label(f"Classificados: {fase.indice} de {len(fase.candidatos)}").classes("texto-suave").mark(
                        "progresso-cofre"
                    )
                    with ui.row().classes("gap-1 no-wrap").props('aria-hidden="true"'):
                        for i, candidato in enumerate(fase.candidatos):
                            cor = ("var(--azul-medio)" if i < fase.indice
                                   else ("var(--ciano)" if i == fase.indice else "var(--linha)"))
                            ui.element("div").style(f"width: 14px; height: 6px; border-radius: 2px; background: {cor}")
                if atual is not None:
                    ui.label(f"Estado {atual.rotulo}").classes("titulo-2").mark("candidato-atual")
                    ui.label(atual.descricao).classes("texto-suave")
                    _atributos(atual.estado)

                    def classificar(resposta: str) -> None:
                        resultado = ctx.agir(NUMERO, "classificar", resposta)
                        if resultado.sucesso and "rotacoes" in resultado.dados:
                            ctx.memoria["fase4_destaque"] = atual.rotulo
                        ctx.memoria["fase4_ultimo"] = resultado
                        conteudo.refresh()

                    ui.label("Esta chave já está guardada no cofre?").classes("rotulo-secao")
                    with ui.row().classes("gap-2"):
                        botao("Novo estado", lambda: classificar("novo"), tipo="principal", icone="add_box", marca="resposta-novo")
                        botao("Estado repetido", lambda: classificar("repetido"), icone="content_copy", marca="resposta-repetido")
                else:
                    ui.label("Todos os estados foram classificados.").classes("titulo-3").mark("cofre-completo")
                feedback = PainelFeedback(ctx, NUMERO, "Decida se o estado já está guardado no cofre.")
                ultimo = ctx.memoria.get("fase4_ultimo")
                if ultimo is not None:
                    feedback.mostrar(ultimo)
                if fase.erros:
                    ui.label(f"Respostas incorretas até agora: {fase.erros}").classes("texto-suave texto-pequeno")

                # Comparação de dois candidatos, atributo por atributo
                ui.separator()
                ui.label("Comparar dois estados").classes("titulo-3")
                ui.label("Repetido = os quatro atributos iguais. A ordem das pistas não importa.").classes(
                    "texto-suave texto-pequeno"
                )
                rotulos = [c.rotulo for c in fase.candidatos]
                por_rotulo = {c.rotulo: c for c in fase.candidatos}
                with ui.row().classes("gap-2 items-center"):
                    a = ui.select(rotulos, value="A", label="Estado").props("outlined dense").style("width: 96px").mark("comparar-a")
                    b = ui.select(rotulos, value="C", label="com").props("outlined dense").style("width: 96px").mark("comparar-b")

                    def comparar() -> None:
                        resposta = ctx.agir(NUMERO, "comparar", a.value, b.value)
                        resposta_comparacao.set_text(resposta.mensagem)
                        detalhe.clear()
                        if not resposta.sucesso or a.value not in por_rotulo or b.value not in por_rotulo:
                            return
                        va, vb = _valores(por_rotulo[a.value].estado), _valores(por_rotulo[b.value].estado)
                        with detalhe, ui.element("div").classes("comparacao-grade"):
                            for cabecalho in ("Atributo", a.value, b.value, ""):
                                ui.label(cabecalho).classes("cab")
                            for nome, x, y in zip(NOMES_ATRIBUTOS, va, vb):
                                ui.label(nome).classes("texto-suave texto-pequeno")
                                ui.label(x).classes("dados")
                                ui.label(y).classes("dados")
                                ui.label("=" if x == y else "≠").classes("igual" if x == y else "diferente")

                    botao("Comparar", comparar, marca="comparar-estados")
                resposta_comparacao = ui.label("").classes("texto-suave").mark("comparacao-resultado")
                detalhe = ui.column().classes("w-full gap-1")

            with ui.column().classes("visor gap-3").style("flex: 3 1 520px; min-width: 0"):
                ui.label("O cofre: árvore AVL indexada pela chave").classes("titulo-3")
                with metricas():
                    metrica("estados no cofre", len(fase.avl), destaque=True)
                    metrica("altura da árvore", fase.avl.altura())
                    metrica("rotações", sum(fase.avl.rotacoes.values()))
                ui.html(
                    svg_arvore(fase.estrutura().dados["arvore"], destaque=ctx.memoria.get("fase4_destaque")),
                    sanitize=False,
                ).classes("w-full").mark("arvore-svg")
                ui.label(
                    "h = altura do nó; f = fator de balanceamento (altura à esquerda menos à direita). Na AVL, todo "
                    "nó tem f entre -1 e +1. Sem rotações, chaves chegando em ordem formariam uma corrente com altura "
                    "igual ao número de estados; balanceada, a altura cresce como log n e a busca no cofre visita "
                    "poucos nós."
                ).classes("texto-suave texto-pequeno")

                for registro in fase.rotacoes_observadas:
                    inserido = registro["rotulo_inserido"]
                    movidos = nos_reposicionados(registro["antes"], registro["depois"])
                    with ui.column().classes("rotacao-bloco w-full gap-2").mark(f"rotacao-{inserido}"):
                        ui.label(f"Ao inserir {inserido}: {_descrever_rotacoes(registro['rotacoes'])}").classes("titulo-3")
                        ui.label(
                            f"A inserção de {inserido} deixou um nó com fator ±2. A rotação devolveu todos os fatores "
                            "ao intervalo de -1 a +1 sem mudar a ordem das chaves."
                            + (f" Mudaram de lugar: {', '.join(sorted(movidos))} (contorno âmbar)." if movidos else "")
                        ).classes("texto-suave texto-pequeno")
                        with ui.row().classes("w-full gap-2 no-wrap items-stretch").style("flex-wrap: wrap"):
                            with ui.column().classes("rotacao-quadro gap-1"):
                                etiqueta("Antes da inserção")
                                ui.html(svg_arvore(registro["antes"], titulo="Antes", movidos=movidos), sanitize=False).classes("w-full")
                            ui.icon("arrow_forward").classes("rotacao-seta")
                            with ui.column().classes("rotacao-quadro gap-1"):
                                etiqueta("Depois da rotação", "ok")
                                ui.html(
                                    svg_arvore(registro["depois"], destaque=inserido, titulo="Depois", movidos=movidos),
                                    sanitize=False,
                                ).classes("w-full")

        # Busca demonstrativa
        with ui.column().classes("painel gap-2 w-full q-mt-md"):
            ui.label("Consultar o cofre").classes("titulo-3")
            ui.label("Monte um estado e procure a chave dele na AVL: busca O(log n), sem percorrer todos os nós.").classes(
                "texto-suave texto-pequeno"
            )
            locais = sorted({c.estado.posicao for c in fase.candidatos} | {"BIBLIOTECA", "TRIBUNAL"})
            pistas = sorted({p for c in fase.candidatos for p in c.estado.pistas})
            portas = sorted({p for c in fase.candidatos for p in c.estado.portas_liberadas})
            with ui.row().classes("gap-2 items-center"):
                posicao = ui.select(locais, value="PRACA", label="Posição").props("outlined dense").style("min-width: 150px").mark("busca-posicao")
                sel_pistas = ui.select(pistas, value=[], multiple=True, label="Pistas").props("outlined dense use-chips").style("min-width: 200px").mark("busca-pistas")
                sel_portas = ui.select(portas, value=[], multiple=True, label="Portas").props("outlined dense use-chips").style("min-width: 180px").mark("busca-portas")
                energia = ui.number("Energia", value=18, min=0, max=99, step=1, format="%d").props("outlined dense").style("width: 110px").mark("busca-energia")

                def buscar() -> None:
                    estado = EstadoJogo(posicao.value, set(sel_pistas.value or []), set(sel_portas.value or []), int(energia.value or 0))
                    resultado = ctx.agir(NUMERO, "buscar", estado)
                    resultado_busca.set_text(f"{resultado.mensagem} Chave procurada: {estado.chave()}")

                botao("Buscar no cofre", buscar, icone="search", marca="buscar-cofre")
            resultado_busca = ui.label("").classes("dados").mark("busca-resultado")

    conteudo()
