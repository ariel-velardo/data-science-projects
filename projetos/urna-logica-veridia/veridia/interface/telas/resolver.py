"""Modo Resolver: os algoritmos de busca reais resolvendo os desafios, com exploração passo a passo.

Os desafios são instâncias NOVAS (não mexem na partida do jogador). Cada
execução chama o solver real uma vez; o passo a passo apenas percorre
``ResultadoBusca.ordem_visita`` já registrado, sem recalcular a busca.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from nicegui import ui

from veridia.busca.solver import ResultadoBusca, resolver_mapa
from veridia.dados.mapa_veridia import construir_mapa_veridia
from veridia.fases.fase2_triagem import FaseCentralTriagem
from veridia.interface.componentes import botao, metrica
from veridia.interface.estado import ContextoTela
from veridia.interface.svg import svg_mapa
from veridia.interface.telas.fase2 import NOMES_ACOES

ALGORITMOS = {"BFS": "BFS (fila)", "DFS": "DFS iterativa (pilha)", "DFS_RECURSIVA": "DFS recursiva"}


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


def _retrato_triagem(retrato) -> None:
    fila, pilha, custodia, arquivo = retrato
    for rotulo, itens in (("Fila", fila), ("Pilha (base a topo)", pilha), ("Custódia", custodia), ("Arquivo", arquivo)):
        with ui.row().classes("items-center gap-2"):
            ui.label(rotulo).classes("texto-suave").style("width: 150px")
            if not itens:
                ui.label("vazia").classes("texto-suave dados")
            for item in itens:
                ui.label(item).classes("ficha")


def tela(ctx: ContextoTela) -> None:
    with ui.column().classes("gap-1 q-mt-lg leitura"):
        ui.label("Modo Resolver").classes("titulo-2")
        ui.label(
            "Aqui os algoritmos jogam sozinhos, com as mesmas regras do modo manual. Escolha um desafio e um "
            "algoritmo, veja a solução e avance pela exploração estado a estado. A sua partida não é alterada."
        ).classes("texto-suave")

    @ui.refreshable
    def painel() -> None:
        memoria: dict[str, Any] = ctx.memoria.setdefault("resolver", {"desafio": "mapa_18", "algoritmo": "BFS"})
        with ui.row().classes("painel w-full items-end gap-3 q-mt-md"):
            desafio = ui.select({k: d.nome for k, d in DESAFIOS.items()}, value=memoria["desafio"], label="Desafio").props(
                "dark outlined"
            ).style("min-width: 280px").mark("resolver-desafio")
            algoritmo = ui.select(ALGORITMOS, value=memoria["algoritmo"], label="Algoritmo").props("dark outlined").style(
                "min-width: 220px"
            ).mark("resolver-algoritmo")

            def executar() -> None:
                resultado, mapa = executar_desafio(desafio.value, algoritmo.value)
                memoria.update(desafio=desafio.value, algoritmo=algoritmo.value, resultado=resultado, mapa=mapa, passo=0)
                painel.refresh()

            botao("Executar busca", executar, tipo="principal", icone="play_arrow", marca="resolver-executar")
        ui.label(DESAFIOS[memoria["desafio"]].descricao).classes("texto-suave")

        resultado: ResultadoBusca | None = memoria.get("resultado")
        if resultado is None:
            return
        tipo = DESAFIOS[memoria["desafio"]].tipo
        with ui.column().classes("visor w-full gap-3 q-mt-md").mark("resolver-resultado"):
            if resultado.encontrou:
                ui.label(f"{resultado.algoritmo} encontrou uma solução com {resultado.comprimento} ações.").classes("titulo-3").mark("resolver-mensagem")
            else:
                ui.label(f"{resultado.algoritmo} explorou todo o espaço alcançável e não há solução.").classes("titulo-3").mark("resolver-mensagem")
            with ui.row().classes("gap-6"):
                metrica("estados explorados", resultado.estados_explorados)
                metrica("sucessores gerados", resultado.estados_gerados)
                metrica("repetidos descartados", resultado.repetidos_descartados)
                metrica("maior fronteira" if resultado.algoritmo != "DFS_RECURSIVA" else "profundidade máxima", resultado.tamanho_max_fronteira)
                metrica("tempo (ms)", f"{resultado.tempo_segundos * 1000:.2f}")
                if resultado.encontrou and tipo == "mapa":
                    metrica("energia do caminho", resultado.custo_caminho)
            if resultado.encontrou:
                ui.label("Sequência de ações").classes("texto-suave")
                with ui.column().classes("gap-0").mark("resolver-acoes"):
                    for i, acao in enumerate(resultado.acoes, start=1):
                        ui.label(f"{i}. {descrever_acao(acao)}").classes("dados")
            explorar_passos(resultado, memoria, tipo)

    def explorar_passos(resultado: ResultadoBusca, memoria: dict[str, Any], tipo: str) -> None:
        total = len(resultado.ordem_visita)
        ui.label("Exploração passo a passo").classes("titulo-3 q-mt-sm")

        @ui.refreshable
        def passo_view() -> None:
            i = memoria["passo"]
            estado = resultado.ordem_visita[i]
            ui.label(f"Estado expandido {i + 1} de {total}").classes("texto-suave").mark("passo-atual")
            if tipo == "mapa":
                explorados = {e.posicao for e in resultado.ordem_visita[:i]}
                ui.html(svg_mapa(memoria["mapa"], estado, explorados=explorados, clicavel=False), sanitize=False).classes("w-full")
                ui.label(str(estado)).classes("dados")
            else:
                _retrato_triagem(estado)

        def ir(novo: int) -> None:
            memoria["passo"] = max(0, min(total - 1, novo))
            passo_view.refresh()

        atalhos: list[tuple[str, str, Callable[[], None], str]] = [
            ("Início", "first_page", lambda: ir(0), "passo-inicio"),
            ("Anterior", "chevron_left", lambda: ir(memoria["passo"] - 1), "passo-anterior"),
            ("Próximo", "chevron_right", lambda: ir(memoria["passo"] + 1), "passo-proximo"),
            ("+10", "fast_forward", lambda: ir(memoria["passo"] + 10), "passo-mais10"),
            ("Último", "last_page", lambda: ir(total - 1), "passo-fim"),
        ]
        with ui.row().classes("gap-2"):
            for texto, icone, acao, marca in atalhos:
                botao(texto, acao, icone=icone, marca=marca)
        ui.label(
            "BFS expande em camadas (todos os estados a 1 movimento, depois a 2...). DFS mergulha em um ramo "
            "até não poder seguir e só então volta. Os locais em verde-escuro já foram expandidos."
        ).classes("texto-suave").style("font-size: 0.85rem")
        passo_view()

        if resultado.rastro_recursao:
            with ui.expansion("Rastro da recursão (chamadas e retornos)").classes("w-full").mark("rastro-recursao"):
                for passo in resultado.rastro_recursao[:40]:
                    ui.label(f"{'  ' * passo.profundidade}[{passo.profundidade}] {passo.evento}: {passo.estado}").classes(
                        "dados texto-suave"
                    ).style("white-space: pre")
                if len(resultado.rastro_recursao) > 40:
                    ui.label(f"... {len(resultado.rastro_recursao) - 40} eventos a mais.").classes("texto-suave")

    painel()

    # Comparação entre algoritmos
    with ui.column().classes("painel w-full gap-2 q-mt-md"):
        ui.label("Comparar BFS e DFS").classes("titulo-3")
        ui.label(
            "A BFS garante o menor número de AÇÕES, porque explora por camadas. Em mapas com custos diferentes "
            "por conexão, isso não garante o menor gasto de ENERGIA. A DFS acha um caminho qualquer, às vezes "
            "explorando menos estados. Com energia 14, os três algoritmos esgotam a busca e provam que não há saída."
        ).classes("texto-suave leitura")
        area = ui.column().classes("w-full")

        def montar() -> None:
            area.clear()
            with area:
                colunas = [
                    {"name": "desafio", "label": "Desafio", "field": "desafio", "align": "left"},
                    {"name": "algoritmo", "label": "Algoritmo", "field": "algoritmo", "align": "left"},
                    {"name": "encontrou", "label": "Solução", "field": "encontrou"},
                    {"name": "acoes", "label": "Ações", "field": "acoes"},
                    {"name": "energia", "label": "Energia", "field": "energia"},
                    {"name": "explorados", "label": "Explorados", "field": "explorados"},
                    {"name": "fronteira", "label": "Maior fronteira", "field": "fronteira"},
                    {"name": "tempo", "label": "Tempo (ms)", "field": "tempo"},
                ]
                linhas = [dict(linha, id=i) for i, linha in enumerate(comparar())]
                ui.table(rows=linhas, columns=colunas, row_key="id").props("dense flat dark").classes("w-full").mark("tabela-comparacao")

        botao("Comparar nos cenários", montar, icone="compare_arrows", marca="resolver-comparar")
