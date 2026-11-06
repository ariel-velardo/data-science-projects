"""Mapa fictício de Verídia usado na fundação técnica.

9 locais e 12 conexões, com bifurcações (Praça, Escola, Mercado, Ponte),
caminhos alternativos até o Tribunal e quatro PORTAS condicionadas a pistas:

    PRACA      — BIBLIOTECA, ESCOLA, MERCADO
    BIBLIOTECA — CARTORIO
    ESCOLA     — CARTORIO, ARQUIVO [porta_arquivo: lacre_rompido]
    MERCADO    — TORRE, PONTE
    TORRE      — PONTE
    ARQUIVO    — PONTE [passagem_ponte: lacre_rompido]
    PONTE      — TRIBUNAL [portao_tribunal: log_urna + registro_horario]
    CARTORIO   — TRIBUNAL [porta_lateral: ata_secao + log_urna + registro_horario]

Para vencer, o jogador precisa chegar ao Tribunal com as pistas
``ata_secao``, ``log_urna`` e ``registro_horario``. O ``lacre_rompido`` não é
exigido na vitória, mas é necessário para entrar no Arquivo (pelas duas
portas). O ``testemunho_feirante`` é uma pista irrelevante (distrator), que
cria estados na mesma posição com conjuntos de pistas diferentes.

Nenhum caminho de solução está codificado aqui: a solução é encontrada pelo
motor de busca a partir das regras.
"""

from __future__ import annotations

from veridia.estruturas.grafo import Grafo
from veridia.modelos.evidencia import Evidencia, TipoEvidencia
from veridia.modelos.mapa import Mapa, Vertice

ENERGIA_INICIAL_VERIDIA = 18


def construir_mapa_veridia(energia_inicial: int = ENERGIA_INICIAL_VERIDIA) -> Mapa:
    evidencias = {
        e.id: e
        for e in (
            Evidencia("ata_secao", TipoEvidencia.DOCUMENTO, "Ata da seção 3 com rasura no total de votantes."),
            Evidencia("lacre_rompido", TipoEvidencia.LACRE, "Lacre da urna com numeração divergente."),
            Evidencia("log_urna", TipoEvidencia.LOG_URNA, "Log da urna com eventos fora de sequência."),
            Evidencia("registro_horario", TipoEvidencia.REGISTRO_HORARIO, "Relógio da torre adiantado em 40 minutos."),
            Evidencia("testemunho_feirante", TipoEvidencia.TESTEMUNHO, "Feirante viu movimento na praça — sem relação com a urna."),
        )
    }

    vertices = {
        v.id: v
        for v in (
            Vertice("PRACA", "Praça Central"),
            Vertice("BIBLIOTECA", "Biblioteca Municipal", pista="ata_secao"),
            Vertice("CARTORIO", "Cartório Eleitoral", pista="lacre_rompido"),
            Vertice("ESCOLA", "Escola (local de votação)"),
            Vertice("MERCADO", "Mercado Público", pista="testemunho_feirante"),
            Vertice("ARQUIVO", "Arquivo Lacrado", pista="log_urna"),
            Vertice("TORRE", "Torre do Relógio", pista="registro_horario"),
            Vertice("PONTE", "Ponte Velha"),
            Vertice("TRIBUNAL", "Tribunal de Verídia"),
        )
    }

    grafo = Grafo()
    for vertice_id in vertices:
        grafo.adicionar_vertice(vertice_id)

    grafo.adicionar_aresta("PRACA", "BIBLIOTECA", custo=2)
    grafo.adicionar_aresta("PRACA", "ESCOLA", custo=1)
    grafo.adicionar_aresta("PRACA", "MERCADO", custo=1)
    grafo.adicionar_aresta("BIBLIOTECA", "CARTORIO", custo=2)
    grafo.adicionar_aresta("ESCOLA", "CARTORIO", custo=3)
    grafo.adicionar_aresta("ESCOLA", "ARQUIVO", custo=2, porta="porta_arquivo", pistas_exigidas={"lacre_rompido"})
    grafo.adicionar_aresta("MERCADO", "TORRE", custo=3)
    grafo.adicionar_aresta("MERCADO", "PONTE", custo=2)
    grafo.adicionar_aresta("TORRE", "PONTE", custo=1)
    grafo.adicionar_aresta("ARQUIVO", "PONTE", custo=2, porta="passagem_ponte", pistas_exigidas={"lacre_rompido"})
    grafo.adicionar_aresta(
        "PONTE", "TRIBUNAL", custo=2, porta="portao_tribunal", pistas_exigidas={"log_urna", "registro_horario"}
    )
    grafo.adicionar_aresta(
        "CARTORIO",
        "TRIBUNAL",
        custo=4,
        porta="porta_lateral",
        pistas_exigidas={"ata_secao", "log_urna", "registro_horario"},
    )

    return Mapa(
        vertices=vertices,
        grafo=grafo,
        evidencias=evidencias,
        inicio="PRACA",
        destino="TRIBUNAL",
        pistas_necessarias=frozenset({"ata_secao", "log_urna", "registro_horario"}),
        energia_inicial=energia_inicial,
    )
