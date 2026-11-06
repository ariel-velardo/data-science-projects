"""Funções que concluem cada fase pela sessão, usando apenas ações válidas.

Nenhuma resposta é fixa: a Fase 2 e a Fase 3 usam o solver para descobrir a
sequência; a Fase 4 consulta a própria árvore para responder.
"""

from veridia.jogo.sessao import SessaoJogo


def concluir_fase1(sessao: SessaoJogo, algoritmo: str = "merge_sort"):
    sessao.executar("selecionar_algoritmo", algoritmo)
    sessao.executar("selecionar_criterio", "zona_secao_horario")
    return sessao.executar("executar_ordenacao")


def concluir_fase2(sessao: SessaoJogo):
    resultado = None
    for acao in sessao.executar("sugerir_solucao").dados["acoes"]:
        resultado = sessao.executar(acao)
    return resultado


def concluir_fase3(sessao: SessaoJogo, algoritmo: str = "BFS"):
    resultado = None
    for destino in sessao.executar("solicitar_solucao", algoritmo).dados["caminho"]:
        resultado = sessao.executar("mover", destino)
    return resultado


def concluir_fase4(sessao: SessaoJogo):
    fase = sessao.fases[4]
    resultado = None
    while fase.candidato_atual() is not None:
        repetido = fase.avl.contem(fase.candidato_atual().estado.chave())
        resultado = sessao.executar("classificar", "repetido" if repetido else "novo")
    return resultado


def concluir_ate(sessao: SessaoJogo, ultima_fase: int) -> SessaoJogo:
    etapas = [concluir_fase1, concluir_fase2, concluir_fase3, concluir_fase4]
    for etapa in etapas[:ultima_fase]:
        etapa(sessao)
    return sessao
