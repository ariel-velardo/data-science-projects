"""Modo Resolver: os algoritmos de busca reais resolvendo os desafios, com exploração passo a passo.

Os desafios são instâncias NOVAS (não mexem na partida do jogador). Cada
execução chama o solver real uma vez; o passo a passo apenas percorre
``ResultadoBusca.ordem_visita`` já registrado, sem recalcular a busca.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Callable

from nicegui import ui

from veridia.busca.solver import ResultadoBusca, resolver_mapa
from veridia.dados.mapa_veridia import construir_mapa_veridia
from veridia.fases.fase2_triagem import FaseCentralTriagem
from veridia.interface.componentes import botao, metrica, metricas
from veridia.interface.estado import ContextoTela
from veridia.interface.svg import svg_mapa
from veridia.interface.telas.fase2 import NOMES_ACOES

ALGORITMOS = {"BFS": "BFS (fila)", "DFS": "DFS iterativa (pilha)", "DFS_RECURSIVA": "DFS recursiva"}

# Como cada algoritmo guarda a fronteira: o que o jogador precisa saber para ler a exploração.
ESTRUTURAS = {
    "BFS": ("view_week", "Fila (FIFO)", "Expande em camadas: todos os estados a 1 ação, depois a 2... "
            "Garante o menor número de ações."),
    "DFS": ("layers", "Pilha explícita (LIFO)", "Mergulha em um ramo até não poder seguir e só então volta. "
            "Acha um caminho qualquer, às vezes explorando menos."),
    "DFS_RECURSIVA": ("account_tree", "Pilha de chamadas", "A mesma ideia da DFS, mas cada passo é uma chamada "
                      "recursiva; voltar é retornar da função."),
}
JANELA_PASSOS = 48


@dataclass(frozen=True)
class Desafio:
    chave: str
    nome: str
    descricao: str
    tipo: str              # "triagem" ou "mapa"
    energia: int | None = None


DESAFIOS = {
    d.chave: d
    for d in (
        Desafio("triagem", "Fase 2: Central de Triagem", "Montar a custódia E2, E4, E1, E6 a partir da fila inicial.", "triagem"),
        Desafio("mapa_18", "Fase 3: mapa com energia 18", "Cenário padrão: sobra energia para desvios.", "mapa", 18),
        Desafio("mapa_15", "Fase 3: mapa com energia 15", "Cenário difícil: só caminhos de custo mínimo funcionam.", "mapa", 15),
        Desafio("mapa_14", "Fase 3: mapa com energia 14", "Cenário sem saída: nenhum caminho vence.", "mapa", 14),
    )
}


def executar_desafio(chave: str, algoritmo: str) -> tuple[ResultadoBusca, Any]:
    """Roda o solver real no desafio. Devolve (resultado, mapa ou None)."""
    desafio = DESAFIOS[chave]
    if desafio.tipo == "triagem":
        return FaseCentralTriagem().resolver(algoritmo), None
    mapa = construir_mapa_veridia(energia_inicial=desafio.energia)
    return resolver_mapa(mapa, algoritmo), mapa


def descrever_acao(acao: Any) -> str:
    return NOMES_ACOES.get(acao, str(acao)) if isinstance(acao, str) else str(acao)


def comparar(chaves: tuple[str, ...] = ("mapa_18", "mapa_15", "triagem")) -> list[dict[str, Any]]:
    linhas = []
    for chave in chaves:
        for algoritmo in ALGORITMOS:
            resultado, _ = executar_desafio(chave, algoritmo)
            linhas.append(
                {
                    "desafio": DESAFIOS[chave].nome,
                    "algoritmo": ALGORITMOS[algoritmo],
                    "encontrou": "sim" if resultado.encontrou else "não",
                    "acoes": resultado.comprimento if resultado.encontrou else "-",
                    "energia": resultado.custo_caminho if resultado.encontrou and DESAFIOS[chave].tipo == "mapa" else "-",
                    "explorados": resultado.estados_explorados,
                    "fronteira": resultado.tamanho_max_fronteira,
                    "tempo": f"{resultado.tempo_segundos * 1000:.1f}",
                }
            )
    return linhas


def _tabela_comparacao(linhas: list[dict[str, Any]]) -> str:
    """Tabela agrupada por desafio, com barra proporcional aos estados explorados dentro do grupo."""
    partes = [
        '<table class="tabela-busca"><thead><tr><th>Algoritmo</th><th>Solução</th><th>Ações</th>'
        "<th>Energia</th><th>Estados explorados</th><th>Maior fronteira</th><th>Tempo (ms)</th></tr></thead><tbody>"
    ]
    grupos: dict[str, list[dict[str, Any]]] = {}
    for linha in linhas:
        grupos.setdefault(linha["desafio"], []).append(linha)
    for desafio, itens in grupos.items():
        maior = max(item["explorados"] for item in itens) or 1
        partes.append(f'<tr class="grupo"><td colspan="7">{escape(desafio)}</td></tr>')
        for item in itens:
            largura = max(4, round(90 * item["explorados"] / maior))
            solucao = "sim" if item["encontrou"] == "sim" else '<span class="nao">não</span>'
            partes.append(
                f'<tr><td>{escape(item["algoritmo"])}</td><td>{solucao}</td><td>{item["acoes"]}</td>'
                f'<td>{item["energia"]}</td><td><span class="barra" style="width:{largura}px"></span>{item["explorados"]}</td>'
                f'<td>{item["fronteira"]}</td><td>{item["tempo"]}</td></tr>'
            )
    partes.append("</tbody></table>")
    return "".join(partes)


def _retrato_triagem(retrato) -> None:
    fila, pilha, custodia, arquivo = retrato
    for rotulo, itens, ponta in (
        ("Fila (frente à esquerda)", fila, "frente"),
        ("Pilha (topo à direita)", pilha, "topo"),
        ("Custódia (início à esquerda)", custodia, None),
        ("Arquivo", arquivo, None),
    ):
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.label(rotulo).classes("texto-suave texto-pequeno").style("width: 190px; flex: none")
            with ui.row().classes("gap-1"):
                if not itens:
                    ui.label("vazia").classes("texto-suave dados")
                for i, item in enumerate(itens):
                    destaque = (ponta == "frente" and i == 0) or (ponta == "topo" and i == len(itens) - 1)
                    ui.label(item).classes("ficha" + (" destaque" if destaque else ""))


def _rotulo_passo(estado: Any, tipo: str) -> str:
    return estado.posicao if tipo == "mapa" else ""


def tela(ctx: ContextoTela) -> None:
    with ui.column().classes("gap-1 q-mt-xl leitura"):
        ui.label("Modo Resolver").classes("titulo-2")
        ui.label(
            "Aqui os algoritmos jogam sozinhos, com as mesmas regras do modo manual. Escolha um desafio e um "
            "algoritmo, veja a solução e avance pela exploração estado a estado. A sua partida não é alterada."
        ).classes("texto-suave")

    @ui.refreshable
    def painel() -> None:
        memoria: dict[str, Any] = ctx.memoria.setdefault("resolver", {"desafio": "mapa_18", "algoritmo": "BFS"})
        with ui.column().classes("painel w-full gap-3 q-mt-md"):
            with ui.row().classes("w-full items-end gap-3"):
                desafio = ui.select({k: d.nome for k, d in DESAFIOS.items()}, value=memoria["desafio"], label="Desafio").props(
                    "outlined"
                ).style("min-width: 280px").mark("resolver-desafio")
                algoritmo = ui.select(ALGORITMOS, value=memoria["algoritmo"], label="Algoritmo").props("outlined").style(
                    "min-width: 220px"
                ).mark("resolver-algoritmo")

                def executar() -> None:
                    resultado, mapa = executar_desafio(desafio.value, algoritmo.value)
                    memoria.update(desafio=desafio.value, algoritmo=algoritmo.value, resultado=resultado, mapa=mapa, passo=0)
                    painel.refresh()

                botao("Executar busca", executar, tipo="principal", icone="play_arrow", marca="resolver-executar")
            ui.label(DESAFIOS[memoria["desafio"]].descricao).classes("texto-suave texto-pequeno")
            with ui.grid().classes("w-full gap-3").style("grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))"):
                for chave, (icone, estrutura, explicacao) in ESTRUTURAS.items():
                    escolhido = chave == memoria["algoritmo"]
                    with ui.column().classes("cartao-fase gap-1" + (" atual" if escolhido else "")):
                        with ui.row().classes("items-center gap-2 no-wrap"):
                            ui.icon(icone).style("color: var(--azul-medio); font-size: 1.4rem")
                            ui.label(ALGORITMOS[chave]).classes("titulo-3")
                        ui.label(estrutura).classes("rotulo-secao")
                        ui.label(explicacao).classes("texto-suave texto-pequeno")

        resultado: ResultadoBusca | None = memoria.get("resultado")
        if resultado is None:
            return
        tipo = DESAFIOS[memoria["desafio"]].tipo
        icone, estrutura, _ = ESTRUTURAS.get(resultado.algoritmo, ("search", resultado.algoritmo, ""))
        with ui.column().classes("visor w-full gap-4 q-mt-md").mark("resolver-resultado"):
            with ui.row().classes("w-full items-start justify-between gap-3"):
                with ui.column().classes("gap-1"):
                    if resultado.encontrou:
                        ui.label(f"{resultado.algoritmo} encontrou uma solução com {resultado.comprimento} ações.").classes(
                            "titulo-2"
                        ).mark("resolver-mensagem")
                    else:
                        ui.label(f"{resultado.algoritmo} explorou todo o espaço alcançável e não há solução.").classes(
                            "titulo-2"
                        ).mark("resolver-mensagem")
                    ui.label(DESAFIOS[memoria["desafio"]].nome).classes("texto-suave")
                with ui.row().classes("estrutura-busca"):
                    ui.icon(icone)
                    with ui.column().classes("gap-0"):
                        ui.label("Estrutura usada").classes("texto-suave texto-pequeno")
                        ui.label(estrutura).classes("titulo-3")

            with metricas():
                if resultado.encontrou:
                    metrica("ações no caminho", resultado.comprimento, destaque=True)
                    if tipo == "mapa":
                        metrica("custo energético", resultado.custo_caminho, destaque=True)
                metrica("estados explorados", resultado.estados_explorados)
                metrica("sucessores gerados", resultado.estados_gerados)
                metrica("repetidos descartados", resultado.repetidos_descartados)
                metrica("maior fronteira" if resultado.algoritmo != "DFS_RECURSIVA" else "profundidade máxima", resultado.tamanho_max_fronteira)
                metrica("tempo (ms)", f"{resultado.tempo_segundos * 1000:.2f}")
            if resultado.encontrou:
                ui.label("Caminho encontrado").classes("rotulo-secao")
                with ui.element("div").classes("cadeia").mark("resolver-acoes"):
                    for i, acao in enumerate(resultado.acoes, start=1):
                        if i > 1:
                            ui.label("›").classes("elo-texto")
                        ui.label(f"{i}. {descrever_acao(acao)}").classes("passo")
            explorar_passos(resultado, memoria, tipo)

    def explorar_passos(resultado: ResultadoBusca, memoria: dict[str, Any], tipo: str) -> None:
        total = len(resultado.ordem_visita)
        rota = None
        if tipo == "mapa" and resultado.encontrou and resultado.estados_caminho:
            rota = [e.posicao for e in resultado.estados_caminho]
        with ui.column().classes("w-full gap-2 rotacao-bloco"):
            ui.label("Exploração passo a passo").classes("titulo-3")
            ui.label(
                "Cada passo é um estado retirado da fronteira e expandido, na ordem registrada pelo solver. "
                + ("No mapa: ciano = local do estado expandido agora; azul-escuro = locais já expandidos; "
                   "pontilhado = caminho final encontrado." if tipo == "mapa" else
                   "Abaixo, o retrato das estruturas no estado expandido.")
            ).classes("texto-suave texto-pequeno leitura")

        def ir(novo: int) -> None:
            memoria["passo"] = max(0, min(total - 1, novo))
            passo_view.refresh()

        def avancar() -> None:
            if memoria["passo"] >= total - 1:
                parar()
                return
            ir(memoria["passo"] + 1)

        def parar() -> None:
            memoria["tocando"] = False
            relogio.deactivate()
            passo_view.refresh()

        def alternar() -> None:
            if memoria.get("tocando"):
                parar()
                return
            if memoria["passo"] >= total - 1:
                memoria["passo"] = 0
            memoria["tocando"] = True
            relogio.activate()
            passo_view.refresh()

        relogio = ui.timer(0.45, avancar, active=False)
        memoria["tocando"] = False

        @ui.refreshable
        def passo_view() -> None:
            i = memoria["passo"]
            estado = resultado.ordem_visita[i]
            with ui.row().classes("items-center gap-3 w-full"):
                ui.label(f"Estado expandido {i + 1} de {total}").classes("titulo-3").mark("passo-atual")
                ui.linear_progress(value=(i + 1) / total, show_value=False, size="6px", color="accent").props(
                    "rounded track-color=blue-10"
                ).style("flex: 1 1 160px; max-width: 320px")
            inicio = max(0, min(i - JANELA_PASSOS // 2, total - JANELA_PASSOS))
            chips = []
            for j in range(inicio, min(total, inicio + JANELA_PASSOS)):
                classe = "agora" if j == i else ("visto" if j < i else "")
                rotulo = _rotulo_passo(resultado.ordem_visita[j], tipo)
                chips.append(f'<span class="passo-chip {classe}">{j + 1}{" " + escape(rotulo) if rotulo else ""}</span>')
            ui.html(f'<div class="ordem-exploracao" aria-label="Ordem de exploração">{"".join(chips)}</div>', sanitize=False).classes("w-full")
            if tipo == "mapa":
                explorados = {e.posicao for e in resultado.ordem_visita[:i]}
                ui.html(
                    svg_mapa(memoria["mapa"], estado, explorados=explorados, foco=None, clicavel=False, rota=rota),
                    sanitize=False,
                ).classes("w-full")
            else:
                _retrato_triagem(estado)
            ui.label(str(estado)).classes("estado-chave")
            with ui.row().classes("controles-passo"):
                atalhos: list[tuple[str, str, Callable[[], None], str]] = [
                    ("Início", "first_page", lambda: ir(0), "passo-inicio"),
                    ("Anterior", "chevron_left", lambda: ir(memoria["passo"] - 1), "passo-anterior"),
                    ("Próximo", "chevron_right", lambda: ir(memoria["passo"] + 1), "passo-proximo"),
                    ("+10", "fast_forward", lambda: ir(memoria["passo"] + 10), "passo-mais10"),
                    ("Último", "last_page", lambda: ir(total - 1), "passo-fim"),
                ]
                for texto, icone, acao, marca in atalhos:
                    botao(texto, acao, icone=icone, marca=marca)
                botao("Pausar" if memoria.get("tocando") else "Reproduzir", alternar, tipo="principal",
                      icone="pause" if memoria.get("tocando") else "play_arrow", marca="passo-reproduzir")

        passo_view()

        if resultado.rastro_recursao:
            with ui.expansion("Rastro da recursão (chamadas e retornos)").classes("w-full").mark("rastro-recursao"):
                for passo in resultado.rastro_recursao[:40]:
                    ui.label(f"{'  ' * passo.profundidade}[{passo.profundidade}] {passo.evento}: {passo.estado}").classes(
                        "recursao-linha"
                    )
                if len(resultado.rastro_recursao) > 40:
                    ui.label(f"... {len(resultado.rastro_recursao) - 40} eventos a mais.").classes("texto-suave texto-pequeno")

    painel()

    # Comparação entre algoritmos
    with ui.column().classes("painel w-full gap-2 q-mt-md"):
        with ui.row().classes("w-full items-end justify-between gap-3") as topo:
            with ui.column().classes("gap-1 leitura"):
                ui.label("Comparar BFS e DFS").classes("titulo-3")
                ui.label(
                    "A BFS garante o menor número de AÇÕES, porque explora por camadas. Em mapas com custos diferentes "
                    "por conexão, isso não garante o menor gasto de ENERGIA. A DFS acha um caminho qualquer, às vezes "
                    "explorando menos estados. Com energia 14, os três algoritmos esgotam a busca e provam que não há saída."
                ).classes("texto-suave texto-pequeno")
        area = ui.column().classes("w-full rolagem-x")

        def montar() -> None:
            area.clear()
            with area:
                ui.html(_tabela_comparacao(comparar()), sanitize=False).classes("w-full").mark("tabela-comparacao")
                ui.label("Barras: estados explorados, relativos ao maior valor de cada desafio. Tempos medidos agora, nesta máquina.").classes(
                    "texto-suave texto-pequeno"
                )

        with topo:
            botao("Comparar nos cenários", montar, icone="compare_arrows", marca="resolver-comparar")
