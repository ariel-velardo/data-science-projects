import json

import pytest

from tests.auxiliares import concluir_ate
from veridia.fases.fase5_auditoria import relatorio_para_dict
from veridia.jogo.sessao import SessaoJogo


def _auditoria(sessao, *args):
    return sessao.fases[5].executar_auditoria(*args)


@pytest.mark.parametrize("busca, ordenacao", [("BFS", "merge_sort"), ("DFS", "bubble_sort"), ("DFS_RECURSIVA", "quick_sort")])
def test_auditoria_consistente(busca, ordenacao):
    s = concluir_ate(SessaoJogo(), 4)
    r = _auditoria(s, busca, ordenacao)
    assert r.sucesso
    rel = s.fases[5].relatorio
    assert rel.consistente and rel.inconsistencias == []
    assert rel.selos == [1, 2, 3, 4]
    assert rel.origem_trilha == "manual"
    assert rel.caminho[0] == "PRACA" and rel.caminho[-1] == "TRIBUNAL"
    assert rel.movimentos == len(rel.caminho) - 1 == 8
    assert rel.energia_consumida == 15
    assert rel.custodia == ["E2", "E4", "E1", "E6"]
    assert rel.algoritmo_ordenacao == ordenacao and rel.registros_conferidos == 30
    assert rel.estados_explorados > 0 and rel.tempo_total_segundos >= rel.tempo_busca_segundos >= 0
    tipos = [(e["tipo"], e["id"]) for e in rel.evidencias_ordenadas]
    assert tipos == sorted(tipos)  # organizadas pelo algoritmo de ordenação reutilizado
    assert all(v["ok"] for v in rel.verificacoes)
    assert s.fases[5].esta_concluida()


def test_auditoria_sem_nada_feito_e_inconsistente():
    s = SessaoJogo()
    r = _auditoria(s)
    rel = s.fases[5].relatorio
    assert not r.sucesso and not rel.consistente
    falhas = {v["nome"] for v in rel.verificacoes if not v["ok"]}
    assert {"ordenacao_registros", "custodia", "trilha", "cofre", "selos"} <= falhas
    assert rel.origem_trilha == "solver" and rel.movimentos > 0  # caminho de referência do solver
    assert not s.fases[5].esta_concluida()


def test_reinicio_de_fase_apos_selo_gera_inconsistencia():
    s = concluir_ate(SessaoJogo(), 4)
    s.reiniciar_fase(2)
    rel_r = _auditoria(s)
    assert not rel_r.sucesso
    rel = s.fases[5].relatorio
    assert rel.selos == [1, 2, 3, 4]  # selos preservados...
    assert [v["nome"] for v in rel.verificacoes if not v["ok"]] == ["custodia"]  # ...mas o estado atual não confere


def test_trilha_manual_incompleta_usa_solver_como_referencia():
    s = concluir_ate(SessaoJogo(), 2)
    s.executar("mover", "MERCADO")
    _auditoria(s)
    rel = s.fases[5].relatorio
    trilha = next(v for v in rel.verificacoes if v["nome"] == "trilha")
    assert not trilha["ok"] and "não chega ao destino" in trilha["detalhe"]
    assert rel.origem_trilha == "solver"


def test_algoritmos_invalidos():
    s = SessaoJogo()
    assert not _auditoria(s, "A*").sucesso
    assert not _auditoria(s, "BFS", "heap_sort").sucesso
    assert s.fases[5].relatorio is None


def test_relatorio_exportavel_em_json_e_reinicio():
    s = concluir_ate(SessaoJogo(), 4)
    _auditoria(s)
    dados = relatorio_para_dict(s.fases[5].relatorio)
    texto = json.dumps(dados, ensure_ascii=False)
    assert json.loads(texto)["consistente"] is True
    assert s.fases[5].consultar()["relatorio"]["movimentos"] == 8
    s.fases[5].reiniciar()
    assert s.fases[5].relatorio is None and not s.fases[5].esta_concluida()
