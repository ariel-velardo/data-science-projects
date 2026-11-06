"""Resultados: progresso da sessão, histórico de ações, métricas por fase e relatório final."""

from __future__ import annotations

from nicegui import ui

from veridia.fases.fase5_auditoria import relatorio_para_dict
from veridia.interface.componentes import botao, etiqueta, metrica, metricas
from veridia.interface.estado import ContextoTela
from veridia.interface.telas.fase5 import botoes_exportacao, relatorio_visual


def tela(ctx: ContextoTela) -> None:
    sessao = ctx.sessao
    resumo = sessao.resumo()
    with ui.column().classes("gap-1 q-mt-xl"):
        ui.label("Resultados").classes("titulo-2")
        if sessao.jogo_concluido():
            ui.label("Investigação concluída: os cinco selos foram recuperados.").classes("titulo-3").style(
                "color: var(--agua)"
            ).mark("jogo-concluido")
        else:
            ui.label(f"{len(sessao.selos)} de 5 selos conquistados.").classes("texto-suave").mark("selos-resumo")

    with ui.grid().classes("w-full gap-3 q-mt-md").style("grid-template-columns: repeat(auto-fit, minmax(200px, 1fr))"):
        for fase in resumo["fases"]:
            situacao = "Selo conquistado" if fase["selo"] else ("Liberada" if fase["liberada"] else "Bloqueada")
            classe = "ok" if fase["selo"] else ("alerta" if fase["liberada"] else "")
            estado_cartao = "conquistada" if fase["selo"] else ("liberada" if fase["liberada"] else "bloqueada")
            with ui.column().classes(f"cartao-fase {estado_cartao} gap-2").mark(f"resultado-fase-{fase['numero']}"):
                with ui.row().classes("items-center gap-3 no-wrap"):
                    ui.label("✓" if fase["selo"] else str(fase["numero"])).classes("cartao-hex")
                    ui.label(fase["titulo"]).classes("titulo-3")
                etiqueta(situacao, classe or "neutra")
                if fase["selo"] and not fase["concluida_agora"]:
                    ui.label("Fase reiniciada depois do selo.").classes("texto-suave").style("font-size: 0.85rem")

    f1, f3, f4 = sessao.fases[1], sessao.fases[3], sessao.fases[4]
    with ui.column().classes("painel w-full gap-3 q-mt-md"):
        ui.label("Métricas da partida").classes("titulo-3")
        with metricas():
            metrica("ações registradas", resumo["acoes_registradas"])
            if f1.metricas is not None:
                metrica(f"comparações ({f1.metricas.algoritmo})", f1.metricas.comparacoes)
            metrica("movimentos no mapa", len(f3.trilha()))
            metrica("energia gasta no mapa", f3.mapa.energia_inicial - f3.estado.energia)
            metrica("estados no cofre", len(f4.avl))
            metrica("erros no cofre", f4.erros)

    with ui.column().classes("painel w-full gap-2 q-mt-md"):
        ui.label("Histórico de ações").classes("titulo-3")
        registros = sessao.historico.para_lista()
        if not registros:
            ui.label("Nenhuma ação registrada ainda. Comece em Jogar.").classes("texto-suave")
        else:
            colunas = [
                {"name": "ordem", "label": "#", "field": "ordem", "align": "right"},
                {"name": "fase", "label": "Fase", "field": "fase", "align": "right"},
                {"name": "acao", "label": "Ação", "field": "acao", "align": "left"},
                {"name": "resultado", "label": "Resultado", "field": "resultado", "align": "left"},
                {"name": "mensagem", "label": "Mensagem", "field": "mensagem", "align": "left"},
            ]
            linhas = [
                {
                    "ordem": r.ordem,
                    "fase": r.fase,
                    "acao": f"{r.acao}({r.argumentos})",
                    "resultado": "aceita" if r.sucesso else "recusada",
                    "mensagem": r.mensagem,
                }
                for r in reversed(registros)
            ]
            ui.table(rows=linhas, columns=colunas, row_key="ordem", pagination=10).props("dense flat wrap-cells").classes(
                "w-full"
            ).mark("tabela-historico")

    relatorio = sessao.fases[5].relatorio
    with ui.column().classes("painel w-full gap-3 q-mt-md"):
        ui.label("Relatório da Auditoria Final").classes("titulo-3")
        if relatorio is None:
            ui.label("A auditoria ainda não foi executada. Ela fica disponível na Fase 5.").classes("texto-suave").mark(
                "sem-relatorio"
            )
            if sessao.fase_liberada(5):
                botao("Ir para a Fase 5", lambda: ui.navigate.to("/fase/5"), tipo="principal")
        else:
            dados = relatorio_para_dict(relatorio)
            relatorio_visual(dados)
            ui.separator()
            botoes_exportacao(dados)
