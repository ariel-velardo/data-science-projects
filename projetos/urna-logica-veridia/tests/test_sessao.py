from tests.auxiliares import concluir_ate, concluir_fase1, concluir_fase2
from veridia.jogo.sessao import SessaoJogo


def test_sessao_inicial():
    s = SessaoJogo()
    assert s.fase_atual == 1 and s.selos == set() and not s.jogo_concluido()
    assert len(s.historico) == 0
    assert [f["liberada"] for f in s.resumo()["fases"]] == [True, False, False, False, False]


def test_fase_bloqueada_ate_conquistar_selo_anterior():
    s = SessaoJogo()
    r = s.ir_para_fase(3)
    assert not r.sucesso and "bloqueada" in r.mensagem and s.fase_atual == 1
    assert not s.ir_para_fase(9).sucesso


def test_selo_concedido_e_fase_avanca():
    s = SessaoJogo()
    r = concluir_fase1(s)
    assert r.sucesso and r.dados["selo_concedido"] == 1
    assert s.selos == {1} and s.fase_atual == 2
    assert s.ir_para_fase(1).sucesso and s.ir_para_fase(2).sucesso


def test_selo_nao_e_concedido_duas_vezes():
    s = SessaoJogo()
    concluir_fase1(s)
    s.ir_para_fase(1)
    r = s.executar("executar_ordenacao")
    assert "selo_concedido" not in r.dados and s.selos == {1}


def test_acao_inexistente_ou_argumentos_invalidos():
    s = SessaoJogo()
    assert not s.executar("mover", "PRACA").sucesso  # ação de outra fase
    r = s.executar("selecionar_algoritmo")  # falta argumento
    assert not r.sucesso and "Argumentos inválidos" in r.mensagem


def test_historico_registra_acoes_relevantes_em_ordem():
    s = SessaoJogo()
    s.executar("consultar")  # consulta não entra no histórico
    s.executar("selecionar_algoritmo", "bubble_sort")
    s.executar("selecionar_algoritmo", "heap_sort")
    registros = s.historico.para_lista()
    assert [r.acao for r in registros] == ["selecionar_algoritmo", "selecionar_algoritmo"]
    assert [r.ordem for r in registros] == [1, 2]
    assert registros[0].sucesso and not registros[1].sucesso
    assert registros[1].argumentos == "'heap_sort'"


def test_reiniciar_fase_mantem_selos_e_outras_fases():
    s = SessaoJogo()
    concluir_fase1(s)
    concluir_fase2(s)
    assert s.selos == {1, 2}
    r = s.reiniciar_fase(2)
    assert r.sucesso and s.selos == {1, 2}
    assert not s.fases[2].esta_concluida()  # fase 2 voltou ao início
    assert s.fases[1].esta_concluida()      # fase 1 intacta
    assert s.historico.ultimo().acao == "reiniciar_fase"
    assert not s.reiniciar_fase(7).sucesso


def test_jogo_completo_concede_cinco_selos():
    s = concluir_ate(SessaoJogo(), 4)
    assert s.selos == {1, 2, 3, 4} and s.fase_atual == 5
    r = s.executar("executar_auditoria")
    assert r.sucesso and s.jogo_concluido() and "Jogo concluído" in r.mensagem


def test_reiniciar_jogo():
    s = concluir_ate(SessaoJogo(), 2)
    s.reiniciar_jogo()
    assert s.selos == set() and s.fase_atual == 1 and len(s.historico) == 0
