"""Instruções: história, controles, como vencer cada fase e o que cada uma demonstra."""

from __future__ import annotations

from nicegui import ui

from veridia.interface.componentes import botao
from veridia.interface.estado import ContextoTela

FASES = (
    (
        "Fase 1: O Arquivo Embaralhado",
        "Ordenar os registros por zona, depois seção, depois horário.",
        "Escolha o algoritmo (Bubble, Merge ou Quick Sort) e o critério “Zona, seção e horário” e clique em "
        "Executar ordenação. Outros critérios ordenam, mas não deixam o arquivo no padrão exigido. O sistema confere "
        "a ordem par a par e verifica que nenhum registro sumiu ou se repetiu.",
        "Algoritmos de ordenação, chave composta, métricas de comparações e movimentações.",
    ),
    (
        "Fase 2: A Central de Triagem",
        "Montar a lista de custódia exatamente E2, E4, E1, E6.",
        "Só a evidência da frente da fila pode sair. A pilha guarda até duas e só libera a do topo. A custódia só "
        "cresce pelo fim. As que não entram na custódia vão para o arquivo. Dica: E1 chega antes de E2, mas precisa "
        "entrar depois dela. Errou? Use Desfazer.",
        "Fila (FIFO), pilha (LIFO), lista ligada e desfazer com pilha de histórico.",
    ),
    (
        "Fase 3: O Mapa das Seções",
        "Chegar ao Tribunal com a ata da seção, o log da urna e o registro de horário.",
        "Clique em um local destacado no mapa (ou nos botões “Ir para”). Cada conexão gasta a energia indicada. "
        "Portas trancadas pedem pistas; as pistas são coletadas ao chegar ao local. O assistente do solver pode "
        "sugerir um caminho a partir de onde você está.",
        "Grafo por lista de adjacência, BFS, DFS iterativa e DFS recursiva sobre o estado completo do jogo.",
    ),
    (
        "Fase 4: O Cofre dos Estados",
        "Classificar oito estados como novos ou repetidos.",
        "Um estado só repete outro se posição, pistas, portas abertas e energia forem todos iguais (a ordem das "
        "pistas não importa). Respostas corretas guardam o estado na árvore AVL, e você vê as rotações acontecerem.",
        "Árvore AVL: inserção, busca, altura, fator de balanceamento e rotações.",
    ),
    (
        "Fase 5: A Auditoria Final",
        "Gerar um relatório de auditoria consistente.",
        "Escolha um algoritmo de busca e um de ordenação e execute a auditoria. Ela refaz as conferências das fases "
        "anteriores; se você reiniciou alguma fase depois de ganhar o selo, a auditoria aponta a inconsistência.",
        "Integração: solver, reutilização da ordenação da Fase 1, métricas e relatório exportável.",
    ),
)


def _secao(titulo: str, *paragrafos: str) -> None:
    with ui.column().classes("gap-1 leitura"):
        ui.label(titulo).classes("titulo-3")
        for paragrafo in paragrafos:
            ui.label(paragrafo).classes("texto-suave")


def tela(ctx: ContextoTela) -> None:
    with ui.column().classes("gap-5 q-mt-xl"):
        ui.label("Instruções").classes("titulo-2")
        _secao(
            "A história",
            "Verídia é uma cidade fictícia. A apuração de uma eleição, também fictícia, foi questionada e você "
            "integra a Central de Auditoria. Cada fase resolvida devolve um selo de auditoria; com os cinco, "
            "o resultado está certificado.",
        )
        _secao(
            "Como jogar",
            "Use o menu do topo para navegar. Os cinco hexágonos no topo são os selos: apagado = bloqueado, "
            "contorno ciano = liberado, ciano preenchido com ✓ = conquistado. Clique em um selo liberado para entrar na fase.",
            "Em cada fase, leia o objetivo, use os botões de ação e acompanhe a resposta no quadro de mensagens: "
            "borda azul para ações aceitas, vermelha para ações recusadas (que não mudam nada no jogo).",
            "Desfazer: nas fases 2 e 3, o botão Desfazer volta a última ação. Reiniciar fase: recomeça só aquela "
            "fase e mantém os selos já conquistados.",
        )
        _secao(
            "Modo manual e solver",
            "No modo manual, você decide cada ação. O solver (assistentes das fases 2 e 3 e a tela Resolver) "
            "usa exatamente as mesmas regras, mas explora sozinho os estados possíveis com BFS ou DFS. Ele só "
            "sugere: os selos vêm das suas ações.",
        )

        ui.label("As cinco fases").classes("titulo-3")
        for titulo, objetivo, como, conceitos in FASES:
            with ui.expansion(titulo, icon="hexagon").classes("w-full painel painel-plano").mark(f"instrucao-{titulo.split(':')[0]}"):
                with ui.column().classes("gap-2 q-pa-md leitura"):
                    ui.label(f"Objetivo: {objetivo}")
                    ui.label(como).classes("texto-suave")
                    ui.label(f"O que demonstra: {conceitos}").classes("texto-suave").style("font-size: 0.9rem")

        _secao(
            "Estruturas e algoritmos implementados à mão",
            "Fila, pilha, lista duplamente ligada, árvore AVL, grafo por lista de adjacência, Bubble Sort, "
            "Merge Sort, Quick Sort, BFS, DFS iterativa e DFS recursiva, todos em Python, sem bibliotecas prontas.",
        )
        botao("Começar a jogar", lambda: ui.navigate.to("/jogar"), tipo="principal", marca="instrucoes-jogar")
