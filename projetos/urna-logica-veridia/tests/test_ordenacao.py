from datetime import time

import pytest

from veridia.algoritmos.ordenacao import (
    ALGORITMOS,
    CRITERIOS,
    bubble_sort,
    merge_sort,
    ordenar_registros,
    quick_sort,
)
from veridia.dados.gerador_registros import gerar_registros
from veridia.demos.experimento_ordenacao import executar_experimento
from veridia.modelos.registro import RegistroVotacao

TODOS = list(ALGORITMOS.values())
CHAVE = CRITERIOS["zona_secao_horario"]


@pytest.mark.parametrize("ordenar", TODOS)
def test_vetor_vazio(ordenar):
    saida, m = ordenar([])
    assert saida == [] and m.comparacoes == 0 and m.movimentacoes == 0


@pytest.mark.parametrize("ordenar", TODOS)
def test_um_elemento(ordenar):
    saida, m = ordenar([42])
    assert saida == [42] and m.comparacoes == 0


@pytest.mark.parametrize("ordenar", TODOS)
def test_valores_repetidos(ordenar):
    dados = [3, 1, 3, 3, 2, 1, 3, 2, 2, 1]
    assert ordenar(dados)[0] == sorted(dados)
    assert ordenar([7] * 30)[0] == [7] * 30


@pytest.mark.parametrize("ordenar", TODOS)
def test_ja_ordenado_e_ordem_inversa(ordenar):
    dados = list(range(200))
    assert ordenar(dados)[0] == dados
    assert ordenar(dados[::-1])[0] == dados


@pytest.mark.parametrize("ordenar", TODOS)
def test_decrescente(ordenar):
    dados = [5, 2, 9, 1, 5]
    assert ordenar(dados, decrescente=True)[0] == [9, 5, 5, 2, 1]


@pytest.mark.parametrize("ordenar", TODOS)
def test_chave_composta_zona_secao_horario(ordenar):
    registros = gerar_registros(300, seed=11)
    saida, _ = ordenar(registros, chave=CHAVE)
    assert [CHAVE(r) for r in saida] == sorted(CHAVE(r) for r in registros)
    # desempate explícito: mesma zona e seção ficam em ordem de horário
    for a, b in zip(saida, saida[1:]):
        if (a.zona, a.secao) == (b.zona, b.secao):
            assert a.horario <= b.horario


@pytest.mark.parametrize("ordenar", TODOS)
def test_preserva_registros_originais(ordenar):
    registros = gerar_registros(150, seed=3)
    copia = list(registros)
    saida, _ = ordenar(registros, chave=CHAVE)
    assert registros == copia  # lista de entrada intacta
    assert saida is not registros
    assert sorted(r.id for r in saida) == sorted(r.id for r in registros)  # nenhum registro perdido/duplicado


@pytest.mark.parametrize("ordenar", [bubble_sort, merge_sort])
def test_estabilidade(ordenar):
    # mesma chave (zona, seção, horário), ids diferentes: a ordem original deve ser mantida
    t = time(9, 0)
    registros = [RegistroVotacao(f"R{i}", 1, 1, "OPC-A", t) for i in range(5)]
    registros.insert(2, RegistroVotacao("R0X", 0, 1, "OPC-A", t))
    saida, _ = ordenar(registros, chave=CHAVE)
    assert [r.id for r in saida] == ["R0X", "R0", "R1", "R2", "R3", "R4"]


def test_metricas_coerentes_com_a_teoria():
    dados = list(range(100))
    _, bubble_ordenado = bubble_sort(dados)
    assert bubble_ordenado.comparacoes == 99 and bubble_ordenado.movimentacoes == 0  # melhor caso O(n)
    _, bubble_inverso = bubble_sort(dados[::-1])
    assert bubble_inverso.comparacoes == 100 * 99 // 2  # pior caso n(n-1)/2
    assert bubble_inverso.movimentacoes == 2 * (100 * 99 // 2)  # cada par invertido = 1 troca
    for m in (bubble_ordenado, bubble_inverso):
        assert m.tempo_segundos >= 0 and m.n == 100

    # Com n = 500 a diferença O(n²) x O(n log n) já é de uma ordem de grandeza.
    inverso = list(range(500))[::-1]
    _, bubble = bubble_sort(inverso)
    _, merge = merge_sort(inverso)
    _, quick = quick_sort(inverso)
    assert merge.comparacoes * 10 < bubble.comparacoes
    assert quick.comparacoes * 10 < bubble.comparacoes


def test_quick_sort_nao_estoura_recursao_em_entrada_grande_ordenada():
    dados = list(range(20_000))
    assert quick_sort(dados)[0] == dados


def test_ordenar_registros_por_nome_e_erros():
    registros = gerar_registros(50)
    saida, m = ordenar_registros(registros, "quick_sort", "horario")
    assert [r.horario for r in saida] == sorted(r.horario for r in registros)
    assert m.algoritmo == "quick_sort"
    with pytest.raises(ValueError):
        ordenar_registros(registros, "heap_sort")
    with pytest.raises(ValueError):
        ordenar_registros(registros, criterio="partido")


def test_experimento_reproduzivel_pequeno():
    r1 = executar_experimento([30], seed=5)
    r2 = executar_experimento([30], seed=5)
    assert len(r1) == 9  # 3 cenários x 3 algoritmos
    assert [(c, m.algoritmo, m.comparacoes, m.movimentacoes) for c, m in r1] == [
        (c, m.algoritmo, m.comparacoes, m.movimentacoes) for c, m in r2
    ]
