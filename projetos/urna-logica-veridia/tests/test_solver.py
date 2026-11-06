import pytest

from veridia.busca.solver import busca_largura, busca_profundidade, resolver_mapa
from veridia.dados.mapa_veridia import construir_mapa_veridia
from veridia.jogo import regras


@pytest.fixture
def mapa():
    return construir_mapa_veridia()


@pytest.mark.parametrize("algoritmo", ["BFS", "DFS"])
def test_solucao_e_valida_quando_reproduzida_pelas_regras(mapa, algoritmo):
    r = resolver_mapa(mapa, algoritmo)
    assert r.encontrou
    # A solução não é confiada: é re-executada passo a passo pelas regras do jogo.
    final = regras.reproduzir_caminho(mapa, [m.destino for m in r.acoes])
    assert regras.verificar_vitoria(mapa, final)
    assert final == r.estado_final
    assert r.estados_caminho[0] == regras.estado_inicial(mapa)
    assert r.estados_caminho[-1] == r.estado_final
    assert len(r.estados_caminho) == r.comprimento + 1


def test_bfs_encontra_caminho_com_menos_movimentos(mapa):
    bfs = resolver_mapa(mapa, "BFS")
    dfs = resolver_mapa(mapa, "DFS")
    assert bfs.comprimento <= dfs.comprimento
    # Exaustivo: nenhum caminho com menos movimentos vence (verificação independente da BFS).
    fronteira = [regras.estado_inicial(mapa)]
    for _ in range(bfs.comprimento - 1):
        fronteira = [novo for e in fronteira for _, novo in regras.gerar_sucessores(mapa, e)]
        assert not any(regras.verificar_vitoria(mapa, e) for e in fronteira)


def test_solucao_usa_portas_condicionadas(mapa):
    r = resolver_mapa(mapa, "BFS")
    portas = {m.porta_aberta for m in r.acoes if m.porta_aberta}
    assert "portao_tribunal" in portas or "porta_lateral" in portas


@pytest.mark.parametrize("algoritmo", ["BFS", "DFS"])
def test_sem_solucao_quando_energia_insuficiente(algoritmo):
    r = resolver_mapa(construir_mapa_veridia(energia_inicial=14), algoritmo)
    assert not r.encontrou and r.acoes == [] and r.estado_final is None
    assert r.estados_explorados == len(r.visitados)  # espaço inteiro esgotado


def test_ordem_de_visita_e_contagens(mapa):
    r = resolver_mapa(mapa, "BFS")
    assert r.ordem_visita[0] == regras.estado_inicial(mapa)
    assert r.ordem_visita[-1] == r.estado_final
    assert r.estados_explorados == len(r.ordem_visita)
    assert r.estados_gerados == (len(r.visitados) - 1) + r.repetidos_descartados


@pytest.mark.parametrize("algoritmo", ["BFS", "DFS"])
def test_avl_nao_reprocessa_estados_e_permanece_balanceada(mapa, algoritmo):
    r = resolver_mapa(mapa, algoritmo)
    chaves_expandidas = [e.chave() for e in r.ordem_visita]
    assert len(chaves_expandidas) == len(set(chaves_expandidas))  # nenhum estado expandido 2x
    assert r.repetidos_descartados > 0  # o grafo tem ciclos: repetições foram detectadas e ignoradas
    assert r.visitados.esta_balanceada()
    n = len(r.visitados)
    assert r.visitados.altura() <= 1.45 * n.bit_length()


def test_avl_distingue_mesma_posicao_com_pistas_diferentes(mapa):
    r = resolver_mapa(mapa, "BFS")
    na_praca = [chave for chave in r.visitados.chaves() if chave[0] == "PRACA"]
    conjuntos_de_pistas = {chave[1] for chave in na_praca}
    assert len(conjuntos_de_pistas) > 1


def test_bfs_marca_na_entrada_dfs_na_saida_em_grafo_simples():
    # Grafo abstrato: 0-1, 0-2, 1-3, 2-3; objetivo 3. Mostra que o motor é genérico.
    adj = {0: [1, 2], 1: [0, 3], 2: [0, 3], 3: [1, 2]}

    def suc(v):
        return [(f"{v}->{w}", w) for w in adj[v]]

    bfs = busca_largura(0, suc, lambda v: v == 3, chave=lambda v: v)
    dfs = busca_profundidade(0, suc, lambda v: v == 3, chave=lambda v: v)
    assert bfs.ordem_visita == [0, 1, 2, 3]
    assert dfs.ordem_visita == [0, 1, 3]
    assert bfs.acoes == ["0->1", "1->3"] and dfs.acoes == ["0->1", "1->3"]


def test_estado_inicial_ja_vitorioso():
    r = busca_largura(5, lambda v: [], lambda v: v == 5, chave=lambda v: v)
    assert r.encontrou and r.acoes == [] and r.estados_caminho == [5]


def test_algoritmo_desconhecido(mapa):
    with pytest.raises(ValueError):
        resolver_mapa(mapa, "A*")
