import pytest

from veridia.dados.mapa_veridia import construir_mapa_veridia
from veridia.fases.fase3_mapa import FaseMapaSecoes
from veridia.jogo import regras


@pytest.fixture
def fase():
    return FaseMapaSecoes()


def test_consultas_iniciais(fase):
    assert fase.local_atual().dados["id"] == "PRACA"
    assert fase.energia_restante().dados["energia"] == 18
    destinos = [c["destino"] for c in fase.conexoes_disponiveis().dados["conexoes"]]
    assert destinos == ["BIBLIOTECA", "ESCOLA", "MERCADO"]
    assert fase.pistas_coletadas().dados["pistas"] == []
    portas = {p["porta"] for p in fase.portas_bloqueadas().dados["portas"]}
    assert portas == {"porta_arquivo", "passagem_ponte", "portao_tribunal", "porta_lateral"}


def test_porta_bloqueada_com_mensagem_e_sem_mudanca(fase):
    fase.mover("ESCOLA")
    antes = fase.estado
    conexao = next(c for c in fase.conexoes_disponiveis().dados["conexoes"] if c["destino"] == "ARQUIVO")
    assert conexao["bloqueada"] and "lacre_rompido" in conexao["motivo"]
    r = fase.mover("ARQUIVO")
    assert not r.sucesso and "lacre_rompido" in r.mensagem and fase.estado == antes


def test_movimento_sem_conexao(fase):
    r = fase.mover("TRIBUNAL")
    assert not r.sucesso and "não há conexão" in r.mensagem


def test_movimento_coleta_pista_e_abre_porta(fase):
    r = fase.mover("BIBLIOTECA")
    assert r.sucesso and r.dados["pistas_novas"] == ["ata_secao"]
    fase.mover("CARTORIO")
    fase.mover("ESCOLA")
    r = fase.mover("ARQUIVO")
    assert "porta_arquivo" in r.mensagem
    assert "porta_arquivo" not in {p["porta"] for p in fase.portas_bloqueadas().dados["portas"]}


def test_desfazer_movimento(fase):
    fase.mover("BIBLIOTECA")
    assert fase.desfazer().sucesso
    assert fase.estado == regras.estado_inicial(fase.mapa)
    assert not fase.desfazer().sucesso


@pytest.mark.parametrize("algoritmo", ["BFS", "DFS", "DFS_RECURSIVA"])
def test_solucao_do_solver_aplicada_pelo_modo_manual(algoritmo):
    fase = FaseMapaSecoes()
    r = fase.solicitar_solucao(algoritmo)
    assert r.sucesso and fase.estado == regras.estado_inicial(fase.mapa)  # solicitar não move
    for destino in r.dados["caminho"]:
        assert fase.mover(destino).sucesso
    assert fase.esta_concluida()
    assert r.dados["custo"] == 18 - fase.estado.energia
    assert [m.destino for m in fase.trilha()] == r.dados["caminho"]


def test_solucao_a_partir_do_estado_atual(fase):
    fase.mover("MERCADO")
    r = fase.solicitar_solucao("BFS")
    assert r.sucesso and r.dados["caminho"][0] in {"PRACA", "TORRE", "PONTE"}


def test_sem_solucao_e_algoritmo_invalido():
    fase = FaseMapaSecoes(construir_mapa_veridia(energia_inicial=14))
    assert not fase.solicitar_solucao("BFS").sucesso
    assert not fase.solicitar_solucao("A*").sucesso


def test_reinicio(fase):
    fase.mover("BIBLIOTECA")
    fase.reiniciar()
    assert fase.estado == regras.estado_inicial(fase.mapa) and fase.trilha() == []
