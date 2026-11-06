from datetime import time

import pytest

from veridia.dados.gerador_registros import gerar_registros
from veridia.dados.mapa_veridia import construir_mapa_veridia
from veridia.modelos.estado import EstadoJogo
from veridia.modelos.evidencia import EstadoEvidencia, Evidencia, TipoEvidencia, validar_evidencia
from veridia.modelos.mapa import validar_mapa
from veridia.modelos.registro import (
    CODIGOS_OPCAO,
    RegistroVotacao,
    StatusRegistro,
    validar_registro,
    validar_registros,
)


def test_gerador_reproduzivel_com_mesma_seed():
    assert gerar_registros(200, seed=7) == gerar_registros(200, seed=7)


def test_gerador_muda_com_outra_seed():
    assert gerar_registros(50, seed=1) != gerar_registros(50, seed=2)


def test_registros_gerados_sao_validos_e_ids_unicos():
    registros = gerar_registros(500)
    assert len(registros) == 500
    assert validar_registros(registros) == []
    assert len({r.id for r in registros}) == 500
    assert all(r.codigo_opcao in CODIGOS_OPCAO for r in registros)


def test_gerador_quantidade_zero_e_negativa():
    assert gerar_registros(0) == []
    with pytest.raises(ValueError):
        gerar_registros(-1)


def test_validacao_detecta_problemas():
    ruim = RegistroVotacao("", 0, -1, "PARTIDO-X", time(22, 0), StatusRegistro.VALIDO)
    assert len(validar_registro(ruim)) == 5


def test_validacao_detecta_id_repetido():
    r = RegistroVotacao("R1", 1, 1, "OPC-A", time(9, 0))
    assert any("repetido" in e for e in validar_registros([r, r]))


def test_registro_imutavel():
    r = RegistroVotacao("R1", 1, 1, "OPC-A", time(9, 0))
    with pytest.raises(AttributeError):
        r.zona = 2  # type: ignore[misc]


def test_evidencia_com_estado_nao_altera_original():
    e = Evidencia("x", TipoEvidencia.LACRE, "lacre")
    coletada = e.com_estado(EstadoEvidencia.COLETADA)
    assert e.estado is EstadoEvidencia.OCULTA
    assert coletada.estado is EstadoEvidencia.COLETADA
    assert validar_evidencia(e) == []
    assert validar_evidencia(Evidencia("", TipoEvidencia.LACRE, " ")) != []


def test_chave_canonica_independe_da_ordem_das_pistas():
    a = EstadoJogo("PRACA", {"b", "a"}, {"p2", "p1"}, 5)
    b = EstadoJogo("PRACA", ["a", "b"], ["p1", "p2"], 5)
    assert a.chave() == b.chave()
    assert a == b and hash(a) == hash(b)


def test_mesma_posicao_pistas_diferentes_sao_estados_distintos():
    a = EstadoJogo("PRACA", {"a"}, energia=5)
    b = EstadoJogo("PRACA", {"a", "b"}, energia=5)
    assert a.chave() != b.chave()
    assert (a.chave() < b.chave()) or (b.chave() < a.chave())  # chaves comparáveis


def test_mapa_veridia_valido_e_com_tamanho_minimo():
    mapa = construir_mapa_veridia()
    assert validar_mapa(mapa) == []
    assert mapa.grafo.num_vertices >= 8
    assert mapa.grafo.num_conexoes >= 10
    portas = {a.porta for v in mapa.grafo.vertices() for a in mapa.grafo.vizinhos(v) if a.condicionada}
    assert len(portas) >= 2
    bifurcacoes = [v for v in mapa.grafo.vertices() if mapa.grafo.grau(v) >= 3]
    assert len(bifurcacoes) >= 2
