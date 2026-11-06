import pytest

from veridia.estruturas import EstruturaVaziaError
from veridia.estruturas.fila import Fila
from veridia.estruturas.pilha import Pilha


def test_fila_vazia():
    f = Fila()
    assert f.esta_vazia() and f.isEmpty() and len(f) == 0
    with pytest.raises(EstruturaVaziaError):
        f.desenfileirar()
    with pytest.raises(EstruturaVaziaError):
        f.frente()


def test_fila_fifo_e_aliases():
    f = Fila()
    for x in [1, 2, 3]:
        f.enqueue(x)
    assert f.front() == 1 and f.peek() == 1 and len(f) == 3
    assert [f.dequeue(), f.desenfileirar(), f.dequeue()] == [1, 2, 3]
    assert f.esta_vazia()


def test_fila_aceita_duplicatas_e_reuso_apos_esvaziar():
    f = Fila()
    f.enfileirar("a")
    f.enfileirar("a")
    assert list(f) == ["a", "a"]
    f.desenfileirar()
    f.desenfileirar()
    f.enfileirar("b")  # o ponteiro de fim precisa ter sido reiniciado
    assert f.frente() == "b" and len(f) == 1


def test_pilha_vazia():
    p = Pilha()
    assert p.esta_vazia() and p.isEmpty()
    with pytest.raises(EstruturaVaziaError):
        p.desempilhar()
    with pytest.raises(EstruturaVaziaError):
        p.topo()


def test_pilha_lifo_com_duplicatas_e_aliases():
    p = Pilha()
    for x in [1, 2, 2, 3]:
        p.push(x)
    assert p.peek() == 3 and p.top() == 3 and len(p) == 4
    assert [p.pop(), p.desempilhar(), p.pop(), p.pop()] == [3, 2, 2, 1]
    assert p.esta_vazia()
