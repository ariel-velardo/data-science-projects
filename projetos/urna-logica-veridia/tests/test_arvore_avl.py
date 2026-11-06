import random

import pytest

from veridia.dados.mapa_veridia import construir_mapa_veridia
from veridia.estruturas.arvore_avl import ArvoreAVL
from veridia.modelos.estado import EstadoJogo


def test_arvore_vazia():
    a = ArvoreAVL()
    assert a.esta_vazia() and a.altura() == 0 and len(a) == 0
    assert not a.contem(1)
    with pytest.raises(KeyError):
        a.buscar(1)
    assert a.chaves() == [] and a.esta_balanceada()


def test_insercao_e_busca():
    a = ArvoreAVL()
    assert a.inserir(5, "cinco")
    assert a.inserir(3, "tres")
    assert a.buscar(5) == "cinco" and 3 in a and 4 not in a


def test_duplicata_nao_insere_nem_sobrescreve():
    a = ArvoreAVL()
    assert a.inserir("k", 1) is True
    assert a.inserir("k", 2) is False
    assert len(a) == 1 and a.buscar("k") == 1


def test_chave_none_invalida():
    with pytest.raises(ValueError):
        ArvoreAVL().inserir(None)


@pytest.mark.parametrize(
    "chaves, rotacao",
    [
        ([3, 2, 1], "direita"),        # caso LL
        ([1, 2, 3], "esquerda"),       # caso RR
        ([3, 1, 2], "dupla_esq_dir"),  # caso LR
        ([1, 3, 2], "dupla_dir_esq"),  # caso RL
    ],
)
def test_quatro_casos_de_rotacao(chaves, rotacao):
    a = ArvoreAVL()
    for c in chaves:
        a.inserir(c)
    assert a.raiz.chave == 2
    assert a.altura() == 2
    assert a.rotacoes[rotacao] == 1
    assert a.fator_balanceamento(a.raiz) == 0


def test_rotacao_sem_filho_e_invalida():
    a = ArvoreAVL()
    a.inserir(1)
    with pytest.raises(ValueError):
        a.rotacionar_direita(a.raiz)
    with pytest.raises(ValueError):
        a.rotacionar_esquerda(a.raiz)


def test_insercao_ordenada_mantem_altura_logaritmica():
    a = ArvoreAVL()
    for i in range(1023):  # em uma BST comum a altura seria 1023
        a.inserir(i)
    assert a.altura() == 10  # árvore perfeita com 1023 nós
    assert a.esta_balanceada()
    assert a.chaves() == list(range(1023))


def test_insercoes_aleatorias_permanecem_balanceadas():
    rng = random.Random(0)
    a = ArvoreAVL()
    chaves = rng.sample(range(10_000), 2000)
    for c in chaves:
        a.inserir(c)
        assert abs(a.fator_balanceamento(a.raiz)) <= 1
    assert a.esta_balanceada()
    assert a.chaves() == sorted(chaves)
    assert a.altura() <= 1.45 * 11  # limite teórico ~1,44·log2(n)


def test_esta_balanceada_detecta_arvore_corrompida():
    a = ArvoreAVL()
    for c in [1, 2, 3]:
        a.inserir(c)
    a.raiz.chave = 99  # quebra a ordem de BST
    assert not a.esta_balanceada()


def test_indexa_estados_do_jogo():
    a = ArvoreAVL()
    e1 = EstadoJogo("PRACA", {"a"}, energia=3)
    e2 = EstadoJogo("PRACA", {"a", "b"}, energia=3)
    e1_equivalente = EstadoJogo("PRACA", ["a"], energia=3)
    assert a.inserir(e1.chave(), e1)
    assert a.inserir(e2.chave(), e2)
    assert not a.inserir(e1_equivalente.chave(), e1_equivalente)
    assert len(a) == 2


def test_indexa_evidencias_por_id():
    mapa = construir_mapa_veridia()
    a = ArvoreAVL()
    for ev in mapa.evidencias.values():
        a.inserir(ev.id, ev)
    assert a.chaves() == sorted(mapa.evidencias)
    assert a.buscar("log_urna").descricao.startswith("Log")
