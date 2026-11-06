"""Fase 3 — O Mapa das Seções (grafo, BFS, DFS, pistas e portas).

Controlador do modo manual sobre o mapa de Verídia. Ele NÃO tem regras
próprias: todo movimento passa por ``veridia.jogo.regras`` — as mesmas
funções usadas pelo solver (``veridia.busca.solver.resolver_mapa``).

Objetivo verificável: ``regras.verificar_vitoria`` — estar no Tribunal com
as pistas necessárias. Pistas são coletadas automaticamente ao chegar a um
local. A energia faz parte do estado (e da chave canônica).

O histórico de movimentos é uma Pilha de pares (movimento, estado anterior),
o que permite DESFAZER o último movimento.
"""

from __future__ import annotations

from typing import Any

from veridia.busca.solver import BUSCAS, ResultadoBusca, resolver_mapa
from veridia.dados.mapa_veridia import construir_mapa_veridia
from veridia.estruturas.pilha import Pilha
from veridia.fases.base import Fase, ResultadoAcao
from veridia.jogo import regras
from veridia.jogo.regras import Movimento
from veridia.modelos.estado import EstadoJogo
from veridia.modelos.mapa import Mapa


class FaseMapaSecoes(Fase):
    numero = 3
    titulo = "O Mapa das Seções"
    objetivo = "Chegar ao Tribunal com a ata da seção, o log da urna e o registro de horário."
    ACOES = (
        "mover",
        "desfazer",
        "solicitar_solucao",
        "local_atual",
        "conexoes_disponiveis",
        "portas_bloqueadas",
        "pistas_coletadas",
        "energia_restante",
        "consultar",
    )

    def __init__(self, mapa: Mapa | None = None) -> None:
        self.mapa = mapa if mapa is not None else construir_mapa_veridia()
        self.reiniciar()

    def reiniciar(self) -> None:
        self.estado: EstadoJogo = regras.estado_inicial(self.mapa)
        self.historico: Pilha[tuple[Movimento, EstadoJogo]] = Pilha()
        self.ultima_solucao: ResultadoBusca | None = None

    def esta_concluida(self) -> bool:
        return regras.verificar_vitoria(self.mapa, self.estado)

    def trilha(self) -> list[Movimento]:
        """Movimentos manuais desde o início, em ordem cronológica."""
        return [movimento for movimento, _ in reversed(list(self.historico))]

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def local_atual(self) -> ResultadoAcao:
        vertice = self.mapa.vertices[self.estado.posicao]
        return ResultadoAcao.ok(f"Você está em {vertice.nome}.", id=vertice.id, nome=vertice.nome)

    def _conexoes(self) -> list[dict[str, Any]]:
        conexoes = []
        for aresta in self.mapa.grafo.vizinhos(self.estado.posicao):
            motivo = regras.motivo_bloqueio(self.estado, aresta)
            conexoes.append(
                {
                    "destino": aresta.destino,
                    "nome": self.mapa.vertices[aresta.destino].nome,
                    "custo": aresta.custo,
                    "porta": aresta.porta,
                    "porta_liberada": aresta.porta is not None and aresta.porta in self.estado.portas_liberadas,
                    "pistas_exigidas": sorted(aresta.pistas_exigidas),
                    "bloqueada": motivo is not None,
                    "motivo": motivo,
                }
            )
        return conexoes

    def conexoes_disponiveis(self) -> ResultadoAcao:
        conexoes = self._conexoes()
        livres = [c["destino"] for c in conexoes if not c["bloqueada"]]
        return ResultadoAcao.ok(f"Destinos possíveis: {', '.join(livres) or 'nenhum'}.", conexoes=conexoes)

    def portas_bloqueadas(self) -> ResultadoAcao:
        """Portas ainda trancadas em TODO o mapa, com as pistas que faltam para cada uma."""
        portas: dict[str, dict[str, Any]] = {}
        for vertice in self.mapa.grafo.vertices():
            for aresta in self.mapa.grafo.vizinhos(vertice):
                if aresta.porta is None or aresta.porta in self.estado.portas_liberadas or aresta.porta in portas:
                    continue
                portas[aresta.porta] = {
                    "porta": aresta.porta,
                    "entre": sorted((aresta.origem, aresta.destino)),
                    "faltam": sorted(aresta.pistas_exigidas - self.estado.pistas),
                }
        lista = sorted(portas.values(), key=lambda p: p["porta"])
        return ResultadoAcao.ok(f"{len(lista)} porta(s) ainda fechada(s).", portas=lista)

    def pistas_coletadas(self) -> ResultadoAcao:
        pistas = sorted(self.estado.pistas)
        faltando = sorted(self.mapa.pistas_necessarias - self.estado.pistas)
        return ResultadoAcao.ok(
            f"Pistas: {', '.join(pistas) or 'nenhuma'}. Faltam para a vitória: {', '.join(faltando) or 'nenhuma'}.",
            pistas=pistas,
            faltando=faltando,
        )

    def energia_restante(self) -> ResultadoAcao:
        return ResultadoAcao.ok(f"Energia restante: {self.estado.energia}.", energia=self.estado.energia)

    def consultar(self) -> dict[str, Any]:
        return {
            "posicao": self.estado.posicao,
            "pistas": sorted(self.estado.pistas),
            "portas_liberadas": sorted(self.estado.portas_liberadas),
            "energia": self.estado.energia,
            "conexoes": self._conexoes(),
            "trilha": [str(m) for m in self.trilha()],
            "concluida": self.esta_concluida(),
        }

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------
    def mover(self, destino: str) -> ResultadoAcao:
        permitido, mensagem = regras.validar_movimento(self.mapa, self.estado, destino)
        if not permitido:
            return ResultadoAcao.falha(f"Movimento bloqueado: {mensagem}.")
        anterior = self.estado
        movimento, self.estado = regras.mover(self.mapa, anterior, destino)
        self.historico.empilhar((movimento, anterior))
        novas = sorted(self.estado.pistas - anterior.pistas)
        partes = [f"Você foi para {self.mapa.vertices[destino].nome} (energia {self.estado.energia})."]
        if movimento.porta_aberta:
            partes.append(f"Porta aberta: {movimento.porta_aberta}.")
        if novas:
            partes.append(f"Pista coletada: {', '.join(novas)}.")
        if self.esta_concluida():
            partes.append("Destino alcançado com todas as pistas!")
        return ResultadoAcao.ok(" ".join(partes), movimento=str(movimento), pistas_novas=novas)

    def desfazer(self) -> ResultadoAcao:
        if self.historico.esta_vazia():
            return ResultadoAcao.falha("Nenhum movimento para desfazer.")
        movimento, anterior = self.historico.desempilhar()
        self.estado = anterior
        return ResultadoAcao.ok(f"Movimento desfeito: {movimento}.")

    def solicitar_solucao(self, algoritmo: str = "BFS") -> ResultadoAcao:
        """Pede ao solver um caminho a partir do estado ATUAL (não o aplica)."""
        if algoritmo.upper() not in BUSCAS:
            return ResultadoAcao.falha(f"Algoritmo desconhecido: {algoritmo!r}. Opções: {', '.join(sorted(BUSCAS))}.")
        resultado = resolver_mapa(self.mapa, algoritmo, inicial=self.estado)
        self.ultima_solucao = resultado
        metricas = {
            "algoritmo": resultado.algoritmo,
            "estados_explorados": resultado.estados_explorados,
            "tempo_segundos": resultado.tempo_segundos,
            "tamanho_max_fronteira": resultado.tamanho_max_fronteira,
        }
        if not resultado.encontrou:
            return ResultadoAcao.falha(
                "Não existe caminho vitorioso a partir daqui (energia ou portas). Desfaça movimentos ou reinicie.",
                **metricas,
            )
        return ResultadoAcao.ok(
            f"{resultado.algoritmo} encontrou {resultado.comprimento} movimentos (custo {resultado.custo_caminho}).",
            caminho=[m.destino for m in resultado.acoes],
            movimentos=[str(m) for m in resultado.acoes],
            custo=resultado.custo_caminho,
            **metricas,
        )
