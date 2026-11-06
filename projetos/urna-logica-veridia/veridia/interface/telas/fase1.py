"""Fase 1 — O Arquivo Embaralhado: terminal de conferência de registros."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from veridia.interface.componentes import PainelFeedback, botao, cabecalho_fase, etiqueta, fase_bloqueada, metrica, metricas
from veridia.interface.estado import ContextoTela
from veridia.interface.rastro_ordenacao import rastrear
from veridia.interface.svg import svg_perfil_ordem

NUMERO = 1
TAMANHO_AMOSTRA = 8
NOMES_ALGORITMOS = {"bubble_sort": "Bubble Sort", "merge_sort": "Merge Sort", "quick_sort": "Quick Sort"}
NOMES_CRITERIOS = {
    "zona_secao_horario": "Zona, seção e horário",
    "horario": "Somente horário",
    "id": "Identificador do registro",
    "status_horario": "Status e horário",
}
COLUNAS = [
    {"name": "id", "label": "Registro", "field": "id", "align": "left"},
    {"name": "zona", "label": "Zona", "field": "zona", "align": "right"},
    {"name": "secao", "label": "Seção", "field": "secao", "align": "right"},
    {"name": "horario", "label": "Horário", "field": "horario", "align": "left"},
    {"name": "opcao", "label": "Opção", "field": "opcao", "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "align": "left"},
]


def _linhas(registros) -> list[dict]:
    return [
        {
            "posicao": i,
            "id": r.id,
            "zona": r.zona,
            "secao": r.secao,
            "horario": r.horario.strftime("%H:%M:%S"),
            "opcao": r.codigo_opcao,
            "status": r.status.value.capitalize(),
        }
        for i, r in enumerate(registros, start=1)
    ]


def _perfil(registros) -> None:
    """Faixa com a zona e a seção de cada registro, na ordem em que estão agora."""
    valores = [r.zona * 1000 + r.secao for r in registros]
    quedas = sum(1 for i in range(1, len(valores)) if valores[i] < valores[i - 1])
    with ui.column().classes("visor w-full gap-1").style("padding: 10px 12px"):
        ui.html(svg_perfil_ordem(valores), sanitize=False).classes("w-full")
        texto = (
            "Escada contínua: zona e seção sempre crescem ao longo do arquivo."
            if quedas == 0
            else f"{quedas} quedas de zona ou seção (em âmbar) ao longo do arquivo."
        )
        ui.label(f"Perfil de zona e seção, um traço por registro. {texto}").classes("texto-suave texto-pequeno")


def _barra(valor: float, maior: float, texto: str, classe: str = "") -> None:
    largura = max(2.0, 100 * valor / (maior or 1))
    with ui.element("div").classes("trilha-barra"):
        ui.element("div").classes(f"barra {classe}").style(f"width: {largura * 0.7:.1f}%")
        ui.label(texto).classes("valor")


def tela(ctx: ContextoTela) -> None:
    if fase_bloqueada(ctx, NUMERO):
        return

    @ui.refreshable
    def conteudo() -> None:
        fase = ctx.sessao.fases[NUMERO]
        ordenado = fase.resultado is not None
        cabecalho_fase(
            ctx,
            NUMERO,
            conteudo.refresh,
            "Os registros chegaram fora de ordem. Escolha um algoritmo e um critério: o arquivo só é aceito "
            "quando fica em ordem de zona, depois seção e, por fim, horário, sem perder nenhum registro.",
        )
        with ui.row().classes("w-full gap-4 q-mt-lg items-start").style("flex-wrap: wrap"):
            with ui.column().classes("painel gap-3").style("flex: 3 1 560px; min-width: 0"):
                registros = fase.resultado if ordenado else fase.lote
                with ui.row().classes("items-center justify-between w-full gap-2"):
                    titulo_tabela = "Arquivo ordenado" if ordenado else "Arquivo embaralhado"
                    ui.label(f"{titulo_tabela} ({len(fase.lote)} registros)").classes("titulo-3").mark("titulo-tabela")
                    if ordenado and not fase.inconsistencias:
                        etiqueta(f"Ordenado com {NOMES_ALGORITMOS.get(fase.metricas.algoritmo, '')}", "ok")
                    elif ordenado:
                        etiqueta("Ordenado, mas fora do padrão", "erro")
                    else:
                        etiqueta("Ordem de chegada", "alerta")
                _perfil(registros)
                ui.table(rows=_linhas(registros), columns=COLUNAS, row_key="posicao", pagination=10).classes(
                    "w-full" + (" tabela-ordenada" if ordenado else "")
                ).props("dense flat").mark("tabela-registros")
                if fase.inconsistencias:
                    ui.label(f"Problema encontrado: {fase.inconsistencias[0]}").classes("etiqueta erro").style(
                        "white-space: normal"
                    )

            with ui.column().classes("painel gap-3").style("flex: 2 1 320px"):
                ui.label("Conferência").classes("titulo-3")
                algoritmo = ui.select(NOMES_ALGORITMOS, label="Algoritmo de ordenação", value=fase.algoritmo).classes(
                    "w-full"
                ).props("outlined").mark("select-algoritmo")
                criterio = ui.select(NOMES_CRITERIOS, label="Critério", value=fase.criterio).classes("w-full").props(
                    "outlined"
                ).mark("select-criterio")
                ui.label(
                    "Chave composta: compara a zona; se empatar, a seção; se ainda empatar, o horário."
                ).classes("texto-suave texto-pequeno")
                feedback = PainelFeedback(ctx, NUMERO, "Escolha o algoritmo e o critério e execute a ordenação.")

                def ordenar() -> None:
                    for acao, valor in (("selecionar_algoritmo", algoritmo.value), ("selecionar_criterio", criterio.value)):
                        if valor is None:
                            feedback.mostrar(ctx.agir(NUMERO, "executar_ordenacao"))  # a fase explica o que falta
                            return
                        resposta = ctx.agir(NUMERO, acao, valor)
                        if not resposta.sucesso:
                            feedback.mostrar(resposta)
                            return
                    resultado = ctx.agir(NUMERO, "executar_ordenacao")
                    ctx.memoria["fase1_ultimo"] = resultado
                    conteudo.refresh()

                botao("Executar ordenação", ordenar, tipo="principal", icone="sort", marca="executar-ordenacao")
                ultimo = ctx.memoria.get("fase1_ultimo")
                if ultimo is not None and ordenado:
                    feedback.mostrar(ultimo)
                if fase.metricas is not None:
                    with metricas():
                        metrica("comparações", fase.metricas.comparacoes, destaque=True)
                        metrica("movimentações", fase.metricas.movimentacoes)
                        metrica("tempo (ms)", f"{fase.metricas.tempo_segundos * 1000:.2f}")
                    ui.label("Movimentação = escrita de um elemento no vetor; uma troca conta 2.").classes(
                        "texto-suave texto-pequeno"
                    )

        # Comparação dos três algoritmos (não altera a fase)
        with ui.column().classes("painel gap-2 w-full q-mt-md"):
            with ui.row().classes("items-center justify-between w-full gap-2") as topo:
                with ui.column().classes("gap-0"):
                    ui.label("Comparar os três algoritmos").classes("titulo-3")
                    ui.label("Mesmo lote e chave composta. Não altera a fase.").classes("texto-suave texto-pequeno")
            area = ui.column().classes("w-full gap-0")

            def comparar() -> None:
                tabela = ctx.agir(NUMERO, "comparar_algoritmos").dados["tabela"]
                maior_comp = max(linha["comparacoes"] for linha in tabela) or 1
                maior_mov = max(linha["movimentacoes"] for linha in tabela) or 1
                area.clear()
                with area:
                    for linha in tabela:
                        with ui.element("div").classes("linha-algoritmo").mark(f"comparacao-{linha['algoritmo']}"):
                            with ui.column().classes("gap-0"):
                                ui.label(NOMES_ALGORITMOS[linha["algoritmo"]]).classes("rotulo-secao")
                                ui.label(f'{linha["tempo_segundos"] * 1000:.2f} ms').classes("texto-suave texto-pequeno")
                            with ui.column().classes("gap-1"):
                                _barra(linha["comparacoes"], maior_comp, f'{linha["comparacoes"]} comparações')
                                _barra(linha["movimentacoes"], maior_mov, f'{linha["movimentacoes"]} movimentações', "mov")

            with topo:
                botao("Comparar", comparar, icone="bar_chart", marca="comparar-algoritmos")

        passo_a_passo(ctx, fase)

    conteudo()


def passo_a_passo(ctx: ContextoTela, fase: Any) -> None:
    """Reproduz as comparações reais de um algoritmo sobre uma amostra do lote."""
    memoria: dict[str, Any] = ctx.memoria.setdefault("fase1_rastro", {"algoritmo": "bubble_sort", "passo": 0})

    with ui.column().classes("visor w-full gap-3 q-mt-md").mark("rastro-ordenacao"):
        with ui.row().classes("items-end justify-between w-full gap-3"):
            with ui.column().classes("gap-0 leitura"):
                ui.label("Passo a passo da ordenação").classes("titulo-3")
                ui.label(
                    f"O algoritmo real ordena os {TAMANHO_AMOSTRA} primeiros registros do lote. Cada passo é uma "
                    "comparação que ele fez de fato, na ordem em que fez. A fase não é alterada."
                ).classes("texto-suave texto-pequeno")
            seletor = ui.select(NOMES_ALGORITMOS, value=memoria["algoritmo"], label="Algoritmo").props(
                "outlined dense dark"
            ).style("min-width: 180px").mark("rastro-algoritmo")

        def ir(novo: int) -> None:
            memoria["passo"] = max(0, min(memoria.get("total", 1) - 1, novo))
            visao.refresh()

        def avancar() -> None:
            if memoria["passo"] >= memoria.get("total", 1) - 1:
                parar()
                return
            ir(memoria["passo"] + 1)

        def parar() -> None:
            memoria["tocando"] = False
            relogio.deactivate()
            visao.refresh()

        def alternar() -> None:
            if memoria.get("tocando"):
                parar()
                return
            if memoria["passo"] >= memoria.get("total", 1) - 1:
                memoria["passo"] = 0
            memoria["tocando"] = True
            relogio.activate()
            visao.refresh()

        relogio = ui.timer(0.7, avancar, active=False)
        memoria["tocando"] = False

        @ui.refreshable
        def visao() -> None:
            rastro = rastrear(fase.lote[:TAMANHO_AMOSTRA], memoria["algoritmo"])
            total = len(rastro.comparacoes)
            i = max(0, min(memoria["passo"], total - 1))
            atual = rastro.comparacoes[i] if total else None
            comparados = {atual.a, atual.b} if atual else set()

            def fichas(titulo: str, registros) -> None:
                ui.label(titulo).classes("rotulo-secao")
                with ui.element("div").classes("amostra"):
                    for r in registros:
                        classe = "ficha comparada" if r.id in comparados else "ficha"
                        with ui.element("div").classes(classe):
                            ui.label(r.id)
                            ui.html(f"<small>z{r.zona} s{r.secao} {r.horario.strftime('%H:%M')}</small>", sanitize=False)

            fichas("Entrada, na ordem de chegada", rastro.entrada)
            if atual:
                resposta = "sim" if atual.a_antes else "não"
                ui.label(
                    f"Comparação {i + 1} de {total}: {atual.a} deve vir antes de {atual.b}? {resposta}."
                ).classes("titulo-3").mark("rastro-passo")
            fichas(f"Saída do {NOMES_ALGORITMOS[memoria['algoritmo']]}", rastro.saida)
            with metricas():
                metrica("comparações", rastro.metricas.comparacoes, destaque=True)
                metrica("movimentações", rastro.metricas.movimentacoes)

            memoria["total"] = total
            with ui.row().classes("controles-passo"):
                botao("Início", lambda: ir(0), icone="first_page", marca="rastro-inicio")
                botao("Anterior", lambda: ir(memoria["passo"] - 1), icone="chevron_left", marca="rastro-anterior")
                botao("Próximo", lambda: ir(memoria["passo"] + 1), icone="chevron_right", marca="rastro-proximo")
                botao("Pausar" if memoria.get("tocando") else "Reproduzir", alternar,
                      tipo="principal", icone="pause" if memoria.get("tocando") else "play_arrow", marca="rastro-reproduzir")
                botao("Fim", lambda: ir(total - 1), icone="last_page", marca="rastro-fim")

        def trocar_algoritmo(evento) -> None:
            memoria.update(algoritmo=evento.value, passo=0)
            parar()

        seletor.on_value_change(trocar_algoritmo)
        visao()
