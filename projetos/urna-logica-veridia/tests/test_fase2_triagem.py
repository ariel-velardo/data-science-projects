import pytest

from veridia.fases.fase2_triagem import FaseCentralTriagem


@pytest.fixture
def fase():
    return FaseCentralTriagem()


def test_estado_inicial(fase):
    c = fase.consultar()
    assert c["fila_entrada"] == ["E1", "E2", "E3", "E4", "E5", "E6"]
    assert c["frente_da_fila"] == "E1" and c["topo_da_pilha"] is None
    assert c["custodia"] == [] and c["arquivo"] == [] and not c["concluida"]


def test_solucao_manual_completa(fase):
    for acao in [
        "guardar_na_pilha",      # E1 espera na pilha
        "receber_na_custodia",   # E2
        "arquivar_da_fila",      # E3
        "receber_na_custodia",   # E4
        "custodiar_da_pilha",    # E1
        "arquivar_da_fila",      # E5
        "receber_na_custodia",   # E6
    ]:
        assert getattr(fase, acao)().sucesso, acao
    assert fase.esta_concluida() and fase.validar().sucesso
    assert fase.consultar()["arquivo"] == ["E3", "E5"]  # nada desapareceu


def test_solucao_descoberta_pelo_solver_e_aplicavel(fase):
    r = fase.sugerir_solucao()
    assert r.sucesso and len(r.dados["acoes"]) == 7
    for acao in r.dados["acoes"]:
        assert getattr(fase, acao)().sucesso
    assert fase.esta_concluida()


@pytest.mark.parametrize("acao", ["custodiar_da_pilha", "arquivar_da_pilha"])
def test_pilha_vazia_nao_altera_estado(fase, acao):
    antes = fase.instantaneo()
    r = getattr(fase, acao)()
    assert not r.sucesso and "vazia" in r.mensagem
    assert fase.instantaneo() == antes and fase.historico.esta_vazia()


def test_fila_vazia_nao_altera_estado(fase):
    for _ in range(6):
        fase.arquivar_da_fila()
    antes = fase.instantaneo()
    for acao in ["receber_na_custodia", "guardar_na_pilha", "arquivar_da_fila"]:
        r = getattr(fase, acao)()
        assert not r.sucesso and "vazia" in r.mensagem
    assert fase.instantaneo() == antes


def test_pilha_cheia(fase):
    fase.guardar_na_pilha()
    fase.guardar_na_pilha()
    antes = fase.instantaneo()
    r = fase.guardar_na_pilha()
    assert not r.sucesso and "cheia" in r.mensagem and fase.instantaneo() == antes


def test_pilha_respeita_lifo(fase):
    fase.guardar_na_pilha()  # E1
    fase.guardar_na_pilha()  # E2 (topo)
    assert fase.consultar()["topo_da_pilha"] == "E2"
    fase.custodiar_da_pilha()
    assert fase.consultar()["custodia"] == ["E2"]


def test_desfazer_restaura_estado_anterior(fase):
    inicial = fase.instantaneo()
    fase.guardar_na_pilha()
    depois_1 = fase.instantaneo()
    fase.receber_na_custodia()
    r = fase.desfazer()
    assert r.sucesso and "E2" in r.mensagem and fase.instantaneo() == depois_1
    fase.desfazer()
    assert fase.instantaneo() == inicial
    assert not fase.desfazer().sucesso  # histórico vazio


def test_erro_corrigido_com_desfazer(fase):
    fase.arquivar_da_fila()  # arquivou E1, que é necessária: sem solução
    assert not fase.sugerir_solucao().sucesso
    fase.desfazer()
    assert fase.sugerir_solucao().sucesso


def test_validar_explica_o_que_falta(fase):
    fase.receber_na_custodia()  # E1 cedo demais
    r = fase.validar()
    assert not r.sucesso and any("difere" in p for p in r.dados["problemas"])
    assert any("fila" in p for p in r.dados["problemas"])


def test_reinicio(fase):
    fase.guardar_na_pilha()
    fase.receber_na_custodia()
    fase.reiniciar()
    assert fase.consultar()["fila_entrada"] == ["E1", "E2", "E3", "E4", "E5", "E6"]
    assert fase.historico.esta_vazia() and fase.consultar()["custodia"] == []


def test_configuracao_invalida():
    with pytest.raises(ValueError):
        FaseCentralTriagem(chegada=("E1", "E1"))
    with pytest.raises(ValueError):
        FaseCentralTriagem(alvo=("E9",))
