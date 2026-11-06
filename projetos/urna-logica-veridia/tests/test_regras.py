import pytest

from veridia.dados.mapa_veridia import construir_mapa_veridia
from veridia.jogo import regras
from veridia.jogo.regras import MovimentoInvalidoError


@pytest.fixture
def mapa():
    return construir_mapa_veridia()


def test_estado_inicial(mapa):
    e = regras.estado_inicial(mapa)
    assert e.posicao == "PRACA" and e.energia == mapa.energia_inicial
    assert e.pistas == frozenset() and e.portas_liberadas == frozenset()


def test_movimento_valido_consome_energia_e_coleta_pista(mapa):
    e0 = regras.estado_inicial(mapa)
    mov, e1 = regras.mover(mapa, e0, "BIBLIOTECA")
    assert e1.posicao == "BIBLIOTECA" and e1.energia == e0.energia - 2
    assert "ata_secao" in e1.pistas
    assert mov.custo == 2 and mov.porta_aberta is None
    assert e0.posicao == "PRACA"  # o estado original não muda


def test_movimento_sem_conexao_ou_local_inexistente(mapa):
    e0 = regras.estado_inicial(mapa)
    assert regras.validar_movimento(mapa, e0, "TRIBUNAL")[0] is False
    assert regras.validar_movimento(mapa, e0, "LUA")[0] is False
    with pytest.raises(MovimentoInvalidoError):
        regras.mover(mapa, e0, "TORRE")


def test_porta_trancada_sem_pista_e_aberta_com_pista(mapa):
    _, na_escola = regras.mover(mapa, regras.estado_inicial(mapa), "ESCOLA")
    permitido, motivo = regras.validar_movimento(mapa, na_escola, "ARQUIVO")
    assert not permitido and "lacre_rompido" in motivo

    com_lacre = na_escola.com(pistas=na_escola.pistas | {"lacre_rompido"})
    mov, no_arquivo = regras.mover(mapa, com_lacre, "ARQUIVO")
    assert mov.porta_aberta == "porta_arquivo"
    assert "porta_arquivo" in no_arquivo.portas_liberadas
    assert "log_urna" in no_arquivo.pistas


def test_porta_liberada_nao_exige_pista_de_novo(mapa):
    _, na_escola = regras.mover(mapa, regras.estado_inicial(mapa), "ESCOLA")
    sem_pistas_mas_porta_aberta = na_escola.com(portas_liberadas={"porta_arquivo"})
    mov, _ = regras.mover(mapa, sem_pistas_mas_porta_aberta, "ARQUIVO")
    assert mov.porta_aberta is None


def test_energia_insuficiente(mapa):
    sem_energia = regras.estado_inicial(mapa).com(energia=1)
    permitido, motivo = regras.validar_movimento(mapa, sem_energia, "BIBLIOTECA")
    assert not permitido and "energia" in motivo
    destinos = {m.destino for m, _ in regras.gerar_sucessores(mapa, sem_energia)}
    assert destinos == {"ESCOLA", "MERCADO"}  # só os de custo 1


def test_sucessores_respeitam_regras_e_ordem_de_adjacencia(mapa):
    e0 = regras.estado_inicial(mapa)
    sucessores = regras.gerar_sucessores(mapa, e0)
    assert [m.destino for m, _ in sucessores] == ["BIBLIOTECA", "ESCOLA", "MERCADO"]
    for mov, novo in sucessores:
        assert regras.validar_movimento(mapa, e0, mov.destino)[0]
        assert novo.energia == e0.energia - mov.custo


def test_coletar_pista_idempotente(mapa):
    e = regras.estado_inicial(mapa).com(posicao="TORRE")
    e1 = regras.coletar_pista(mapa, e)
    assert regras.coletar_pista(mapa, e1) is e1
    assert regras.coletar_pista(mapa, regras.estado_inicial(mapa)) == regras.estado_inicial(mapa)


def test_vitoria_exige_destino_e_pistas(mapa):
    todas = mapa.pistas_necessarias
    assert regras.verificar_vitoria(mapa, regras.estado_inicial(mapa).com(posicao="TRIBUNAL", pistas=todas))
    assert not regras.verificar_vitoria(mapa, regras.estado_inicial(mapa).com(posicao="PONTE", pistas=todas))
    faltando_uma = set(todas) - {"ata_secao"}
    assert not regras.verificar_vitoria(mapa, regras.estado_inicial(mapa).com(posicao="TRIBUNAL", pistas=faltando_uma))
