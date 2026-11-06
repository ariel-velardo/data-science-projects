import pytest

from veridia.fases.fase4_cofre import FaseCofreEstados
from veridia.modelos.estado import EstadoJogo


@pytest.fixture
def fase():
    return FaseCofreEstados()


def _responder_certo(fase):
    repetido = fase.avl.contem(fase.candidato_atual().estado.chave())
    return fase.classificar("repetido" if repetido else "novo")


def test_a_b_diferentes_a_c_equivalentes(fase):
    ab = fase.comparar("A", "B")
    assert not ab.dados["equivalentes"] and ab.dados["diferencas"] == ["pistas"]
    assert fase.comparar("A", "C").dados["equivalentes"]
    assert fase.comparar("A", "E").dados["diferencas"] == ["energia"]
    assert fase.comparar("B", "H").dados["diferencas"] == ["portas_liberadas"]
    assert fase.comparar("D", "F").dados["equivalentes"]  # ordem das pistas não importa
    assert not fase.comparar("A", "Z").sucesso


def test_classificacao_errada_nao_altera_cofre(fase):
    r = fase.classificar("repetido")  # A é novo
    assert not r.sucesso and fase.indice == 0 and len(fase.avl) == 0 and fase.erros == 1
    _responder_certo(fase)  # A
    _responder_certo(fase)  # B
    r = fase.classificar("novo")  # C é repetido de A
    assert not r.sucesso and "A" in r.mensagem and fase.indice == 2
    assert not fase.classificar("talvez").sucesso


def test_repetido_identifica_equivalente(fase):
    _responder_certo(fase)
    _responder_certo(fase)
    r = fase.classificar("repetido")
    assert r.sucesso and r.dados["equivalente"] == "A"
    assert len(fase.avl) == 2  # duplicata não foi inserida


def test_rotacao_com_estrutura_antes_e_depois(fase):
    for _ in range(3):
        _responder_certo(fase)  # A, B, C
    r = _responder_certo(fase)  # D: A < B < D em linha → rotação à esquerda
    assert r.dados["rotacoes"] == {"esquerda": 1}
    antes, depois = r.dados["antes"], r.dados["depois"]
    assert antes["rotulo"] == "A" and antes["direita"]["rotulo"] == "B" and antes["esquerda"] is None
    assert depois["rotulo"] == "B" and depois["esquerda"]["rotulo"] == "A" and depois["direita"]["rotulo"] == "D"
    assert depois["fator"] == 0


def test_busca_existente_e_inexistente(fase):
    _responder_certo(fase)
    assert fase.buscar(EstadoJogo("PRACA", energia=18)).dados == {"encontrado": True, "rotulo": "A"}
    assert fase.buscar(EstadoJogo("PRACA", {"autenticacao"}, energia=18)).dados["encontrado"] is False
    assert len(fase.buscas) == 2


def test_fase_completa_balanceada(fase):
    while fase.candidato_atual() is not None:
        assert _responder_certo(fase).sucesso
    assert fase.esta_concluida()
    assert len(fase.avl) == 6 and fase.avl.esta_balanceada()
    assert len(fase.rotacoes_observadas) >= 2
    assert all(abs(n["fator"]) <= 1 for n in fase.fatores())
    assert fase.estrutura().dados["arvore"]["altura"] == fase.avl.altura()
    assert not fase.classificar("novo").sucesso  # nada mais a classificar


def test_reinicio(fase):
    _responder_certo(fase)
    fase.classificar("repetido")
    fase.reiniciar()
    assert fase.indice == 0 and fase.erros == 0 and len(fase.avl) == 0 and fase.rotacoes_observadas == []
