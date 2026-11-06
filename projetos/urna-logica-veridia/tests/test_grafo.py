import pytest

from veridia.estruturas.grafo import Grafo


def _grafo():
    g = Grafo()
    for v in "ABCD":
        g.adicionar_vertice(v)
    return g


def test_aresta_bidirecional_e_contagem():
    g = _grafo()
    g.adicionar_aresta("A", "B", custo=2)
    g.adicionar_aresta("B", "C", porta="p", pistas_exigidas={"x"}, bidirecional=False)
    assert g.num_conexoes == 2
    assert [a.destino for a in g.vizinhos("B")] == ["A", "C"]
    assert g.existe_aresta("A", "B") and g.existe_aresta("B", "A")
    assert not g.existe_aresta("C", "B")
    assert g.aresta("B", "C").pistas_exigidas == frozenset({"x"})
    assert g.grau("D") == 0


def test_operacoes_invalidas():
    g = _grafo()
    with pytest.raises(ValueError):
        g.adicionar_vertice("A")
    with pytest.raises(KeyError):
        g.adicionar_aresta("A", "Z")
    with pytest.raises(ValueError):
        g.adicionar_aresta("A", "A")
    with pytest.raises(ValueError):
        g.adicionar_aresta("A", "B", custo=0)
    with pytest.raises(ValueError):
        g.adicionar_aresta("A", "B", pistas_exigidas={"x"})  # exige pista mas não tem porta
    g.adicionar_aresta("A", "B")
    with pytest.raises(ValueError):
        g.adicionar_aresta("B", "A")
    with pytest.raises(KeyError):
        list(g.vizinhos("Z"))


def test_aresta_bidirecional_recusada_preserva_grafo():
    g = _grafo()
    g.adicionar_aresta("B", "A", bidirecional=False)
    antes = {v: list(g.vizinhos(v)) for v in g.vertices()}

    with pytest.raises(ValueError, match="conexão duplicada"):
        g.adicionar_aresta("A", "B")

    assert {v: list(g.vizinhos(v)) for v in g.vertices()} == antes
    assert g.num_conexoes == 1
