from dataclasses import replace
from datetime import time

import pytest

from veridia.algoritmos.ordenacao import CRITERIOS
from veridia.dados.gerador_registros import gerar_registros
from veridia.fases.fase1_arquivo import FaseArquivoEmbaralhado, verificar_ordenacao
from veridia.modelos.registro import RegistroVotacao

CHAVE = CRITERIOS["zona_secao_horario"]


def test_lote_inicial_embaralhado_e_reproduzivel():
    a, b = FaseArquivoEmbaralhado(seed=5), FaseArquivoEmbaralhado(seed=5)
    assert a.lote == b.lote
    assert [r.id for r in a.lote] != sorted(r.id for r in a.lote)  # embaralhado em relação à geração
    assert not a.esta_concluida()


@pytest.mark.parametrize("algoritmo", ["bubble_sort", "merge_sort", "quick_sort"])
def test_criterio_correto_conclui_com_qualquer_algoritmo(algoritmo):
    f = FaseArquivoEmbaralhado()
    f.selecionar_algoritmo(algoritmo)
    f.selecionar_criterio("zona_secao_horario")
    r = f.executar_ordenacao()
    assert r.sucesso and f.esta_concluida()
    assert r.dados["comparacoes"] > 0
    assert f.verificar().sucesso


@pytest.mark.parametrize("criterio", ["horario", "id", "status_horario"])
def test_criterio_incorreto_nao_conclui(criterio):
    f = FaseArquivoEmbaralhado()
    f.selecionar_algoritmo("merge_sort")
    f.selecionar_criterio(criterio)
    r = f.executar_ordenacao()
    assert not r.sucesso and "fora de ordem" in r.mensagem
    assert not f.esta_concluida()


def test_selecao_invalida_e_execucao_sem_selecao():
    f = FaseArquivoEmbaralhado()
    assert not f.executar_ordenacao().sucesso
    assert not f.selecionar_algoritmo("heap_sort").sucesso
    f.selecionar_algoritmo("merge_sort")
    assert not f.executar_ordenacao().sucesso  # falta critério
    assert not f.selecionar_criterio("partido").sucesso
    assert not f.verificar().sucesso  # nada ordenado ainda


def test_lote_invalido_nao_e_carregado():
    f = FaseArquivoEmbaralhado()
    lote_anterior = f.lote
    assert not f.carregar_lote([]).sucesso
    ruim = RegistroVotacao("R1", 1, 1, "PARTIDO-REAL", time(9, 0))
    assert not f.carregar_lote([ruim]).sucesso
    duplicado = gerar_registros(3)
    assert not f.carregar_lote(duplicado + duplicado[:1]).sucesso
    assert f.lote == lote_anterior


def test_carregar_lote_valido_e_ordenar():
    f = FaseArquivoEmbaralhado()
    assert f.carregar_lote(list(reversed(gerar_registros(12, seed=9)))).sucesso
    f.selecionar_algoritmo("bubble_sort")
    f.selecionar_criterio("zona_secao_horario")
    assert f.executar_ordenacao().sucesso and len(f.resultado) == 12


def test_reinicio_volta_ao_lote_original():
    f = FaseArquivoEmbaralhado()
    original = f.lote
    f.carregar_lote(gerar_registros(5, seed=1))
    f.selecionar_algoritmo("quick_sort")
    f.reiniciar()
    assert f.lote == original and f.algoritmo is None and f.resultado is None


def test_verificacao_detecta_perda_duplicacao_alteracao_e_ordem():
    lote = gerar_registros(10, seed=4)
    ordenado = sorted(lote, key=CHAVE)
    assert verificar_ordenacao(lote, ordenado) == []
    assert any("perdido" in p for p in verificar_ordenacao(lote, ordenado[:-1]))
    assert any("duplicado" in p for p in verificar_ordenacao(lote, ordenado[:-1] + ordenado[:1]))
    alterado = ordenado[:]
    alterado[0] = replace(alterado[0], codigo_opcao="NULO" if alterado[0].codigo_opcao != "NULO" else "BRANCO")
    assert any("alterado" in p for p in verificar_ordenacao(lote, alterado))
    assert any("fora de ordem" in p for p in verificar_ordenacao(lote, list(reversed(ordenado))))


def test_comparar_algoritmos_nao_altera_a_fase():
    f = FaseArquivoEmbaralhado()
    r = f.comparar_algoritmos()
    assert [linha["algoritmo"] for linha in r.dados["tabela"]] == ["bubble_sort", "merge_sort", "quick_sort"]
    assert f.resultado is None and not f.esta_concluida()
