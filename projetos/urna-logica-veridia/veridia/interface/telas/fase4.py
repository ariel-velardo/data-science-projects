"""Fase 4 — O Cofre dos Estados: estados equivalentes × distintos na árvore AVL."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.componentes import PainelFeedback, botao, cabecalho_fase, fase_bloqueada, metrica
from veridia.interface.estado import ContextoTela
from veridia.interface.svg import svg_arvore
from veridia.modelos.estado import EstadoJogo

NUMERO = 4
NOMES_ROTACOES = {
    "esquerda": "rotação simples à esquerda",
    "direita": "rotação simples à direita",
    "dupla_esq_dir": "rotação dupla esquerda-direita",
    "dupla_dir_esq": "rotação dupla direita-esquerda",
}


def _descrever_rotacoes(rotacoes: dict[str, int]) -> str:
    return ", ".join(f"{NOMES_ROTACOES.get(tipo, tipo)} ({n}x)" for tipo, n in rotacoes.items())


def _atributos(estado: EstadoJogo) -> None:
    chave = estado.chave()
    linhas = (
        ("Posição", chave[0]),
        ("Pistas", ", ".join(chave[1]) or "nenhuma"),
        ("Portas abertas", ", ".join(chave[2]) or "nenhuma"),
        ("Energia", chave[3]),
    )
    with ui.grid(columns=2).classes("gap-x-6 gap-y-1"):
        for rotulo, valor in linhas:
            ui.label(rotulo).classes("texto-suave")
            ui.label(str(valor)).classes("dados")


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

        with ui.row().classes("w-full gap-4 q-mt-md items-start").style("flex-wrap: wrap"):
            with ui.column().classes("painel gap-3").style("flex: 2 1 340px"):
                atual = fase.candidato_atual()
                ui.label(f"Classificados: {fase.indice} de {len(fase.candidatos)}").classes("texto-suave").mark(
                    "progresso-cofre"
                )
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
                    ui.label(f"Respostas incorretas até agora: {fase.erros}").classes("texto-suave")

                # Comparação de dois candidatos
                ui.label("Comparar dois estados").classes("titulo-3 q-mt-sm")
                rotulos = [c.rotulo for c in fase.candidatos]
                with ui.row().classes("gap-2 items-center"):
                    a = ui.select(rotulos, value="A", label="Estado").props("dark outlined dense").style("width: 100px").mark("comparar-a")
                    b = ui.select(rotulos, value="C", label="com").props("dark outlined dense").style("width: 100px").mark("comparar-b")
                    resposta_comparacao = ui.label("").classes("texto-suave").mark("comparacao-resultado")
                    botao(
                        "Comparar",
                        lambda: resposta_comparacao.set_text(ctx.agir(NUMERO, "comparar", a.value, b.value).mensagem),
                        marca="comparar-estados",
                    )

            with ui.column().classes("visor gap-3").style("flex: 3 1 520px; min-width: 0"):
                with ui.row().classes("gap-6"):
                    metrica("estados no cofre", len(fase.avl))
                    metrica("altura da árvore", fase.avl.altura())
                    metrica("rotações", sum(fase.avl.rotacoes.values()))
                ui.html(
                    svg_arvore(fase.estrutura().dados["arvore"], destaque=ctx.memoria.get("fase4_destaque")),
                    sanitize=False,
                ).classes("w-full").mark("arvore-svg")
                ui.label("h = altura do nó; f = fator de balanceamento (altura à esquerda menos à direita). "
                         "Na AVL, todo nó tem f entre -1 e +1.").classes("texto-suave").style("font-size: 0.85rem")

                for registro in fase.rotacoes_observadas:
                    with ui.column().classes("w-full gap-1").mark(f"rotacao-{registro['rotulo_inserido']}"):
                        ui.label(
                            f"Ao inserir {registro['rotulo_inserido']}: {_descrever_rotacoes(registro['rotacoes'])}"
                        ).classes("titulo-3")
                        with ui.row().classes("w-full gap-3 no-wrap"):
                            with ui.column().classes("gap-0").style("flex: 1; min-width: 0"):
                                ui.label("Antes da inserção").classes("texto-suave")
                                ui.html(svg_arvore(registro["antes"], titulo="Antes"), sanitize=False).classes("w-full")
                            with ui.column().classes("gap-0").style("flex: 1; min-width: 0"):
                                ui.label("Depois da rotação").classes("texto-suave")
                                ui.html(
                                    svg_arvore(registro["depois"], destaque=registro["rotulo_inserido"], titulo="Depois"),
                                    sanitize=False,
                                ).classes("w-full")

        # Busca demonstrativa
        with ui.column().classes("painel gap-2 w-full q-mt-md"):
            ui.label("Consultar o cofre").classes("titulo-3")
            ui.label("Monte um estado e procure a chave dele na AVL: busca O(log n), sem percorrer todos os nós.").classes(
                "texto-suave"
            )
            locais = sorted({c.estado.posicao for c in fase.candidatos} | {"BIBLIOTECA", "TRIBUNAL"})
            pistas = sorted({p for c in fase.candidatos for p in c.estado.pistas})
            portas = sorted({p for c in fase.candidatos for p in c.estado.portas_liberadas})
            with ui.row().classes("gap-2 items-center"):
                posicao = ui.select(locais, value="PRACA", label="Posição").props("dark outlined dense").style("min-width: 150px").mark("busca-posicao")
                sel_pistas = ui.select(pistas, value=[], multiple=True, label="Pistas").props("dark outlined dense use-chips").style("min-width: 200px").mark("busca-pistas")
                sel_portas = ui.select(portas, value=[], multiple=True, label="Portas").props("dark outlined dense use-chips").style("min-width: 180px").mark("busca-portas")
                energia = ui.number("Energia", value=18, min=0, max=99, step=1, format="%d").props("dark outlined dense").style("width: 110px").mark("busca-energia")
                resultado_busca = ui.label("").classes("dados").mark("busca-resultado")

                def buscar() -> None:
                    estado = EstadoJogo(posicao.value, set(sel_pistas.value or []), set(sel_portas.value or []), int(energia.value or 0))
                    resultado = ctx.agir(NUMERO, "buscar", estado)
                    resultado_busca.set_text(f"{resultado.mensagem} Chave procurada: {estado.chave()}")

                botao("Buscar no cofre", buscar, icone="search", marca="buscar-cofre")

    conteudo()
