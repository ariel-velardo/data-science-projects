import pytest

from veridia.estruturas import EstruturaVaziaError
from veridia.estruturas.lista_ligada import ListaLigada


def test_lista_vazia():
    lista = ListaLigada()
    assert lista.esta_vazia() and len(lista) == 0 and lista.para_lista() == []
    for operacao in (lista.primeiro, lista.ultimo, lista.remover_inicio, lista.remover_fim):
        with pytest.raises(EstruturaVaziaError):
            operacao()
    assert lista.buscar(1) == -1
    assert lista.remover(1) is False


def test_insercao_inicio_fim_e_meio():
    lista = ListaLigada()
    lista.inserir_fim(2)
    lista.inserir_inicio(1)
    lista.inserir_fim(4)
    lista.inserir_em(2, 3)
    assert lista.para_lista() == [1, 2, 3, 4]
    assert lista.primeiro() == 1 and lista.ultimo() == 4
    assert list(lista.percorrer_reverso()) == [4, 3, 2, 1]
    lista.inserir_em(0, 0)
    lista.inserir_em(5, 5)
    assert lista.para_lista() == [0, 1, 2, 3, 4, 5]
    assert lista.obter(4) == 4


def test_indices_invalidos():
    lista = ListaLigada([1])
    with pytest.raises(IndexError):
        lista.inserir_em(3, 9)
    with pytest.raises(IndexError):
        lista.obter(1)
    with pytest.raises(IndexError):
        lista.remover_em(-1)


def test_remocoes_mantem_ponteiros():
    lista = ListaLigada([1, 2, 3, 2])
    assert lista.remover(2) is True  # remove só a primeira ocorrência
    assert lista.para_lista() == [1, 3, 2]
    assert lista.remover_fim() == 2 and lista.ultimo() == 3
    assert lista.remover_inicio() == 1 and lista.primeiro() == 3
    assert lista.remover_em(0) == 3
    assert lista.esta_vazia()
    lista.inserir_fim(7)
    assert lista.primeiro() == lista.ultimo() == 7


def test_busca_com_duplicatas_e_predicado():
    lista = ListaLigada(["a", "b", "a"])
    assert lista.buscar("a") == 0 and lista.buscar("b") == 1 and lista.buscar("z") == -1
    assert "b" in lista and "z" not in lista
    assert lista.buscar_por(lambda x: x > "a") == "b"
    assert lista.buscar_por(lambda x: x == "z") is None
