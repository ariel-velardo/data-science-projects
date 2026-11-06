"""Testes de integração da interface NiceGUI com usuário simulado (sem navegador).

Cada teste sobe a aplicação em memória (``user_simulation``) com um
gerenciador de sessões novo, para que as partidas de um teste não vazem
para outro.
"""

import json

import httpx2
import pytest
from nicegui import core
from nicegui.testing.user import User
from nicegui.testing.user_simulation import user_simulation

from tests.auxiliares import concluir_ate
from veridia.fases.fase2_triagem import FaseCentralTriagem
from veridia.fases.fase4_cofre import FaseCofreEstados
from veridia.interface import app as aplicacao
from veridia.interface.estado import GerenciadorSessoes

pytestmark = pytest.mark.asyncio


@pytest.fixture
def gerenciador(monkeypatch):
    novo = GerenciadorSessoes()
    monkeypatch.setattr(aplicacao, "GERENCIADOR", novo)
    return novo


def _sessao_unica(gerenciador):
    assert len(gerenciador) == 1
    return next(iter(gerenciador._sessoes.values()))


def _selecionar(user: User, marca: str, valor) -> None:
    elemento = next(iter(user.find(marker=marca).elements))
    elemento.set_value(valor)


async def test_menu_inicial_com_cinco_opcoes(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/")
        for texto in ("VERÍDIA", "Missão: recuperar os cinco selos de auditoria, um por fase."):
            await user.should_see(texto)
        for marca in ("menu-jogar", "menu-resolver", "menu-instrucoes", "menu-resultados", "menu-sair"):
            await user.should_see(marker=marca)
        await user.should_see("0 de 5 selos")
        user.find(marker="menu-jogar").trigger("click")
        await user.should_see("Fases da investigação")
        await user.should_see(marker="entrar-fase-1")
        await user.should_not_see(marker="entrar-fase-2")


async def test_navegacao_pelas_telas_do_menu(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/")
        for marca, texto in (
            ("nav-Instruções", "As cinco fases"),
            ("nav-Resolver", "Modo Resolver"),
            ("nav-Resultados", "Histórico de ações"),
            ("nav-Sair", "Sair do jogo"),
            ("nav-Jogar", "Fases da investigação"),
            ("nav-Início", "O Enigma da Urna"),
        ):
            user.find(marker=marca).click()
            await user.should_see(texto)


async def test_fase_bloqueada_mostra_aviso(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/fase/3")
        await user.should_see(marker="fase-bloqueada")
        await user.should_see("Fase 3 bloqueada")


async def test_fase1_criterio_errado_depois_certo_concede_selo(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/fase/1")
        await user.should_see("Arquivo embaralhado (30 registros)")
        user.find(marker="executar-ordenacao").click()
        await user.should_see("Selecione um algoritmo antes de ordenar.")
        _selecionar(user, "select-algoritmo", "quick_sort")
        _selecionar(user, "select-criterio", "horario")
        user.find(marker="executar-ordenacao").click()
        await user.should_see("fora de ordem")
        sessao = _sessao_unica(gerenciador)
        assert sessao.selos == set()
        _selecionar(user, "select-criterio", "zona_secao_horario")
        user.find(marker="executar-ordenacao").click()
        await user.should_see("Selo 1 de auditoria concedido")
        await user.should_see("Arquivo ordenado (30 registros)")
        await user.should_see("comparações")
        assert sessao.selos == {1}
        await user.should_see("1 de 5 selos")
        user.find(marker="comparar-algoritmos").click()
        await user.should_see(marker="comparacao-bubble_sort")
        user.find(marker="proxima-fase").click()
        await user.should_see("Sequência exigida na custódia")


async def test_reiniciar_fase_mantem_selo(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/")
        sessao = _sessao_unica(gerenciador)
        concluir_ate(sessao, 1)
        await user.open("/fase/1")
        await user.should_see("Arquivo ordenado (30 registros)")
        user.find(marker="reiniciar-fase").click()
        await user.should_see("Arquivo embaralhado (30 registros)")
        assert sessao.selos == {1} and sessao.fases[1].resultado is None


async def test_fase2_operacoes_invalidas_desfazer_e_solucao(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/")
        sessao = _sessao_unica(gerenciador)
        concluir_ate(sessao, 1)
        await user.open("/fase/2")
        user.find(marker="acao-custodiar_da_pilha").click()
        await user.should_see("A pilha temporária está vazia.")
        user.find(marker="acao-arquivar_da_fila").click()
        await user.should_see("E1 arquivada.")
        assert sessao.fases[2].consultar()["arquivo"] == ["E1"]
        user.find(marker="acao-desfazer").click()
        await user.should_see("Desfeito: E1: fila → arquivo.")
        assert sessao.fases[2].consultar()["arquivo"] == []
        user.find(marker="acao-sugerir").click()
        await user.should_see("Solução com 7 ações encontrada por BFS.")
        for acao in FaseCentralTriagem().sugerir_solucao().dados["acoes"]:
            user.find(marker=f"acao-{acao}").click()
        await user.should_see("Selo 2 de auditoria concedido")
        assert sessao.selos == {1, 2}


async def test_fase3_movimentos_bloqueio_desfazer_e_solver(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/")
        sessao = _sessao_unica(gerenciador)
        concluir_ate(sessao, 2)
        await user.open("/fase/3")
        await user.should_see("Você está em Praça Central.")
        await user.should_see(marker="mapa-svg")
        # Simula o evento enviado pelo SVG, incluindo o despacho registrado na raiz.
        ouvintes = [
            (elemento, ouvinte)
            for elemento in user.client.elements.values()
            for ouvinte in elemento._event_listeners.values()
            if ouvinte.type == "veridia_local"
        ]
        assert len(ouvintes) == 1
        elemento, ouvinte = ouvintes[0]
        user.client.handle_event({
            "id": elemento.id,
            "listener_id": ouvinte.id,
            "args": [json.dumps("ESCOLA")],
        })
        await user.should_see("Você está em Escola (local de votação).")
        assert len(sessao.fases[3].trilha()) == 1
        user.find(marker="desfazer-movimento").click()
        await user.should_see("Você está em Praça Central.")
        user.find(marker="mover-ESCOLA").click()
        await user.should_see("Você está em Escola (local de votação).")
        user.find(marker="mover-ARQUIVO").click()
        await user.should_see("porta 'porta_arquivo' trancada")
        user.find(marker="desfazer-movimento").click()
        await user.should_see("Você está em Praça Central.")
        _selecionar(user, "select-busca", "DFS_RECURSIVA")
        user.find(marker="calcular-caminho").click()
        await user.should_see("DFS_RECURSIVA encontrou 10 movimentos")
        await user.should_see(marker="caminho-sugerido")
        assert sessao.fases[3].estado.posicao == "PRACA"  # o solver não move o jogador
        _selecionar(user, "select-busca", "BFS")
        user.find(marker="calcular-caminho").click()
        await user.should_see("BFS encontrou 8 movimentos")
        for destino in [m.destino for m in sessao.fases[3].ultima_solucao.acoes]:
            await user.should_see(marker=f"mover-{destino}")  # o refresh da tela é assíncrono
            user.find(marker=f"mover-{destino}").click()
        await user.should_see("Selo 3 de auditoria concedido")
        assert sessao.selos == {1, 2, 3}


async def test_fase4_classificacao_rotacoes_e_busca(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/")
        sessao = _sessao_unica(gerenciador)
        concluir_ate(sessao, 3)
        await user.open("/fase/4")
        await user.should_see("Estado A")
        user.find(marker="resposta-repetido").click()
        await user.should_see("Incorreto")
        user.find(marker="comparar-estados").click()
        await user.should_see("A e C são equivalentes (mesma chave).")
        referencia = FaseCofreEstados()
        while referencia.candidato_atual() is not None:
            repetido = referencia.avl.contem(referencia.candidato_atual().estado.chave())
            resposta = "repetido" if repetido else "novo"
            referencia.classificar(resposta)
            user.find(marker=f"resposta-{resposta}").click()
        await user.should_see("Selo 4 de auditoria concedido")
        await user.should_see(marker="rotacao-D")
        await user.should_see(marker="rotacao-G")
        await user.should_see("Ao inserir D: rotação simples à esquerda (1x)")
        user.find(marker="buscar-cofre").click()
        await user.should_see("Estado encontrado no cofre: A.")
        _selecionar(user, "busca-energia", 3)
        user.find(marker="buscar-cofre").click()
        await user.should_see("Estado não está no cofre.")


async def test_fase5_auditoria_relatorio_e_resultados(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/")
        sessao = _sessao_unica(gerenciador)
        concluir_ate(sessao, 4)
        await user.open("/fase/5")
        _selecionar(user, "auditoria-busca", "DFS")
        _selecionar(user, "auditoria-ordenacao", "quick_sort")
        user.find(marker="executar-auditoria").click()
        await user.should_see("Selo 5 de auditoria concedido")
        await user.should_see("Auditoria consistente")
        await user.should_see(marker="verificacao-custodia")
        await user.should_see(marker="baixar-json")
        assert sessao.jogo_concluido()
        assert sessao.fases[5].relatorio.algoritmo_ordenacao == "quick_sort"
        user.find(marker="nav-Resultados").click()
        await user.should_see(marker="jogo-concluido")
        await user.should_see(marker="tabela-historico")
        await user.should_see(marker="relatorio")
        user.find(marker="baixar-json").click()
        resposta_json = await user.download.next(timeout=3)
        assert resposta_json.status_code == 200
        assert resposta_json.json()["consistente"] is True
        assert resposta_json.json()["algoritmo_ordenacao"] == "quick_sort"
        user.find(marker="baixar-html").click()
        resposta_html = await user.download.next(timeout=3)
        assert resposta_html.status_code == 200
        assert resposta_html.text.startswith("<!DOCTYPE html>")
        assert "Auditoria consistente" in resposta_html.text
        assert "@media print" in resposta_html.text


async def test_auditoria_inconsistente_apos_reinicio(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/")
        sessao = _sessao_unica(gerenciador)
        concluir_ate(sessao, 4)
        sessao.reiniciar_fase(2)
        await user.open("/fase/5")
        user.find(marker="executar-auditoria").click()
        await user.should_see("Auditoria inconsistente")
        assert 5 not in sessao.selos


async def test_resolver_executa_busca_real_e_passo_a_passo(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/resolver")
        _selecionar(user, "resolver-desafio", "mapa_15")
        _selecionar(user, "resolver-algoritmo", "DFS_RECURSIVA")
        user.find(marker="resolver-executar").click()
        await user.should_see("DFS_RECURSIVA encontrou uma solução com 8 ações.")
        await user.should_see(marker="rastro-recursao")
        await user.should_see("Estado expandido 1 de")
        user.find(marker="passo-proximo").click()
        await user.should_see("Estado expandido 2 de")
        user.find(marker="passo-fim").click()
        await user.should_see(marker="passo-atual")
        _selecionar(user, "resolver-desafio", "mapa_14")
        _selecionar(user, "resolver-algoritmo", "BFS")
        user.find(marker="resolver-executar").click()
        await user.should_see("BFS explorou todo o espaço alcançável e não há solução.")
        _selecionar(user, "resolver-desafio", "triagem")
        user.find(marker="resolver-executar").click()
        await user.should_see("BFS encontrou uma solução com 7 ações.")
        await user.should_see("Guardar na pilha")
        assert len(gerenciador) == 1 and _sessao_unica(gerenciador).selos == set()  # a partida não muda


async def test_sessoes_independentes_entre_navegadores(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as primeiro:
        await primeiro.open("/")
        concluir_ate(_sessao_unica(gerenciador), 1)
        segundo = User(httpx2.AsyncClient(transport=httpx2.ASGITransport(core.app), base_url="http://test"))
        await segundo.open("/fase/2")
        await segundo.should_see("Fase 2 bloqueada")
        await primeiro.open("/fase/2")
        await primeiro.should_see("Sequência exigida na custódia")
        assert len(gerenciador) == 2


async def test_sair_encerra_somente_a_propria_partida(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/")
        concluir_ate(_sessao_unica(gerenciador), 1)
        gerenciador.obter("outro-navegador")
        await user.open("/sair")
        await user.should_see("Você tem 1 de 5 selos.", retries=3)
        user.find(marker="encerrar-partida").click()
        await user.should_see(marker="partida-encerrada")
        assert gerenciador.existe("outro-navegador")
        user.find(marker="nova-partida").click()
        await user.should_see("0 de 5 selos")


async def test_instrucoes_explicam_as_fases(gerenciador):
    async with user_simulation(root=aplicacao.raiz) as user:
        await user.open("/instrucoes")
        for texto in ("A história", "Como jogar", "Modo manual e solver", "Fase 2: A Central de Triagem"):
            await user.should_see(texto)
