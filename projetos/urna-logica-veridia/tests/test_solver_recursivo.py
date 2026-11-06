import pytest

from veridia.busca.solver import busca_profundidade, busca_profundidade_recursiva, resolver_mapa
from veridia.dados.mapa_veridia import construir_mapa_veridia
from veridia.jogo import regras

# Grafo pequeno e controlado: 0-1, 0-2, 1-3, 2-3, 3-4; objetivo 4.
ADJ = {0: [1, 2], 1: [0, 3], 2: [0, 3], 3: [1, 2, 4], 4: [3]}


def suc(v):
    return [(f"{v}->{w}", w) for w in ADJ[v]]


def test_recursiva_em_grafo_pequeno_com_rastro():
    r = busca_profundidade_recursiva(0, suc, lambda v: v == 4, chave=lambda v: v)
    assert r.encontrou and r.acoes == ["0->1", "1->3", "3->4"]
    assert r.ordem_visita == [0, 1, 3, 2, 4]  # 2 é explorado e falha antes de 4
    eventos = [(p.profundidade, p.evento, p.estado) for p in r.rastro_recursao]
    assert eventos == [
        (0, "chamada", 0),
        (1, "chamada", 1),
        (2, "caso_base_repetido", 0),   # 1 -> 0: já visitado
        (2, "chamada", 3),
        (3, "caso_base_repetido", 1),   # 3 -> 1: já visitado
        (3, "chamada", 2),
        (4, "caso_base_repetido", 0),
        (4, "caso_base_repetido", 3),
        (3, "sem_saida", 2),            # backtracking
        (3, "chamada", 4),
        (3, "caso_base_objetivo", 4),
        (2, "retorno_sucesso", 3),      # o sucesso sobe até a raiz
        (1, "retorno_sucesso", 1),
        (0, "retorno_sucesso", 0),
    ]
    assert r.tamanho_max_fronteira == 4  # pilha de chamadas mais funda: 0 → 1 → 3 → 2 (4 níveis)


def test_recursiva_sem_solucao_e_inicial_objetivo():
    r = busca_profundidade_recursiva(0, suc, lambda v: v == 99, chave=lambda v: v)
    assert not r.encontrou and r.estados_explorados == 5 and r.rastro_recursao[-1].evento == "sem_saida"
    r = busca_profundidade_recursiva(4, suc, lambda v: v == 4, chave=lambda v: v)
    assert r.encontrou and r.acoes == [] and r.estados_caminho == [4]


def test_recursiva_e_iterativa_visitam_na_mesma_ordem_no_mapa():
    mapa = construir_mapa_veridia()
    iterativa = resolver_mapa(mapa, "DFS")
    recursiva = resolver_mapa(mapa, "DFS_RECURSIVA")
    assert recursiva.ordem_visita == iterativa.ordem_visita
    assert recursiva.acoes == iterativa.acoes
    final = regras.reproduzir_caminho(mapa, [m.destino for m in recursiva.acoes])
    assert regras.verificar_vitoria(mapa, final)
    assert recursiva.visitados.esta_balanceada()


def test_recursiva_mesmas_regras_sem_solucao():
    r = resolver_mapa(construir_mapa_veridia(energia_inicial=14), "DFS_RECURSIVA")
    assert not r.encontrou and r.estados_explorados == len(r.visitados)


@pytest.mark.parametrize("algoritmo", ["BFS", "DFS", "DFS_RECURSIVA"])
def test_metricas_complementares(algoritmo):
    mapa = construir_mapa_veridia()
    r = resolver_mapa(mapa, algoritmo)
    assert r.tempo_segundos > 0
    assert r.tamanho_max_fronteira >= 1
    assert r.custo_caminho == sum(m.custo for m in r.acoes) == mapa.energia_inicial - r.estado_final.energia
    arvore = r.arvore_busca()
    assert len(arvore) == len(r.visitados) - 1  # todo estado, exceto a raiz, tem exatamente um pai
    for chave_pai, chave_filho, acao in arvore:
        assert r.visitados.contem(chave_pai)
        assert acao.destino == chave_filho[0]


def test_tamanho_max_da_pilha_na_dfs_iterativa():
    r = busca_profundidade(0, suc, lambda v: v == 4, chave=lambda v: v)
    assert r.tamanho_max_fronteira >= 2
