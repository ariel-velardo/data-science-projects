"""Testes dos módulos puros da interface (sem servidor): sessões, SVG e exportação."""

import json
import re

import pytest
from nicegui import ui

from tests.auxiliares import concluir_ate
from veridia.dados.mapa_veridia import construir_mapa_veridia
from veridia.fases.fase4_cofre import FaseCofreEstados, serializar_arvore
from veridia.fases.fase5_auditoria import relatorio_para_dict
from veridia.interface import app as aplicacao
from veridia.interface.estado import ContextoTela, GerenciadorSessoes
from veridia.interface.exportacao import relatorio_html, relatorio_json
from veridia.interface.svg import EVENTO_CLIQUE_LOCAL, svg_arvore, svg_mapa
from veridia.jogo import regras
from veridia.jogo.sessao import SessaoJogo


def test_gerenciador_cria_sessoes_independentes_e_descarta():
    g = GerenciadorSessoes()
    a, b = g.obter("navegador-a"), g.obter("navegador-b")
    assert a is not b and g.obter("navegador-a") is a and len(g) == 2
    a.executar("selecionar_algoritmo", "merge_sort")
    assert len(a.historico) == 1 and len(b.historico) == 0
    assert g.descartar("navegador-a") and not g.existe("navegador-a")
    assert not g.descartar("navegador-a")
    assert g.obter("navegador-a") is not a  # nova partida
    with pytest.raises(ValueError):
        g.obter("")


def test_contexto_agir_reposiciona_fase_e_respeita_bloqueio():
    ctx = ContextoTela("x", gerenciador=GerenciadorSessoes())
    assert not ctx.agir(3, "mover", "ESCOLA").sucesso  # fase 3 bloqueada
    concluir_ate(ctx.sessao, 1)
    assert ctx.sessao.fase_atual == 2
    resultado = ctx.agir(1, "verificar")  # volta para a fase 1 antes de agir
    assert resultado.sucesso and ctx.sessao.fase_atual == 1


def test_svg_mapa_reflete_estado_real():
    mapa = construir_mapa_veridia()
    estado = regras.estado_inicial(mapa)
    svg = svg_mapa(mapa, estado)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert all(f'data-local="{v}"' in svg for v in mapa.vertices)
    clicaveis = set(re.findall(rf"emitEvent\('{EVENTO_CLIQUE_LOCAL}', '(\w+)'\)", svg))
    assert clicaveis == {d.destino for d, _ in regras.gerar_sucessores(mapa, estado)}
    assert svg.count("Porta ") == 4  # quatro portas trancadas no início
    assert "polyline" not in svg


def test_svg_mapa_portas_abertas_caminho_e_sem_clique():
    mapa = construir_mapa_veridia()
    estado = regras.reproduzir_caminho(mapa, ["BIBLIOTECA", "CARTORIO", "ESCOLA", "ARQUIVO"])
    svg = svg_mapa(mapa, estado, caminho=["PONTE", "TORRE"], clicavel=False)
    assert svg.count("Porta ") == 3 and "polyline" in svg
    assert "emitEvent" not in svg


def test_svg_arvore_reflete_avl_real():
    fase = FaseCofreEstados()
    assert "Cofre vazio" in svg_arvore(None)
    while fase.candidato_atual() is not None:
        repetido = fase.avl.contem(fase.candidato_atual().estado.chave())
        fase.classificar("repetido" if repetido else "novo")
    arvore = serializar_arvore(fase.avl.raiz, fase._rotulos())
    svg = svg_arvore(arvore, destaque="H")
    assert sorted(re.findall(r'data-rotulo="(\w)"', svg)) == sorted(rotulo for _, rotulo in fase.avl.em_ordem())
    assert svg.count("<line") == len(fase.avl) - 1  # árvore: n - 1 arestas
    assert "f=+2" not in svg and "f=-2" not in svg


def test_exportacao_json_e_html():
    sessao = concluir_ate(SessaoJogo(), 4)
    sessao.executar("executar_auditoria")
    dados = relatorio_para_dict(sessao.fases[5].relatorio)
    assert json.loads(relatorio_json(dados))["consistente"] is True
    html = relatorio_html(dados)
    assert html.startswith("<!DOCTYPE html>") and "Auditoria consistente" in html
    assert "PRACA &gt; BIBLIOTECA" in html  # caminho escapado
    assert "http" not in html.split("</style>")[0]  # nenhum recurso externo
    inconsistente = dict(dados, consistente=False, inconsistencias=["Fase 2: <custódia> incompleta"])
    html2 = relatorio_html(inconsistente)
    assert "Auditoria inconsistente" in html2 and "&lt;custódia&gt;" in html2



def test_main_configura_ui_run(monkeypatch):
    chamado = {}
    monkeypatch.setattr(ui, "run", lambda raiz, **kwargs: chamado.update(raiz=raiz, **kwargs))
    aplicacao.main(["--porta", "8091", "--sem-navegador"])
    assert chamado["raiz"] is aplicacao.raiz and chamado["port"] == 8091 and chamado["show"] is False
    assert chamado["storage_secret"] and chamado["reload"] is False
