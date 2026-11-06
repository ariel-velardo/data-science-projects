"""Fase 1 — O Arquivo Embaralhado (ordenação de registros).

Enigma: os registros de votação fictícios de Verídia chegaram embaralhados.
O jogador escolhe um algoritmo (Bubble, Merge ou Quick Sort) e um critério
de ordenação e executa a ordenação. A fase é concluída quando o resultado
está ordenado pela chave composta (zona, seção, horário) e nenhum registro
foi perdido, duplicado ou alterado.

A verificação NÃO compara com uma resposta guardada: ela confere, par a par,
se cada registro tem chave <= à do seguinte e se o conjunto de registros é
exatamente o do lote original (usando a árvore AVL para detectar ids
repetidos ou ausentes).
"""

from __future__ import annotations

import random
from typing import Any, Sequence

from veridia.algoritmos.ordenacao import ALGORITMOS, CRITERIOS, MetricasOrdenacao
from veridia.dados.gerador_registros import SEED_PADRAO, gerar_registros
from veridia.estruturas.arvore_avl import ArvoreAVL
from veridia.fases.base import Fase, ResultadoAcao
from veridia.modelos.registro import RegistroVotacao, validar_registros

CRITERIO_OBJETIVO = "zona_secao_horario"
TAMANHO_LOTE_PADRAO = 30


def _formatar(chave: Any) -> str:
    """Chave legível: (5, 2, 08:13:51) em vez de (5, 2, datetime.time(8, 13, 51))."""
    partes = chave if isinstance(chave, tuple) else (chave,)
    return "(" + ", ".join(str(p) for p in partes) + ")"


def verificar_ordenacao(
    original: Sequence[RegistroVotacao],
    resultado: Sequence[RegistroVotacao],
    criterio: str = CRITERIO_OBJETIVO,
) -> list[str]:
    """Lista de inconsistências entre ``original`` e ``resultado`` (vazia = correto).

    Confere: (1) mesma quantidade; (2) nenhum id duplicado, ausente ou
    estranho; (3) registros não alterados; (4) ordem não decrescente pela chave.
    Custo: O(n log n) pelas operações na AVL.
    """
    problemas: list[str] = []
    chave = CRITERIOS[criterio]
    if len(original) != len(resultado):
        problemas.append(f"quantidade diferente: original {len(original)}, resultado {len(resultado)}")

    por_id: ArvoreAVL = ArvoreAVL()
    for registro in original:
        por_id.inserir(registro.id, registro)
    vistos: ArvoreAVL = ArvoreAVL()
    for registro in resultado:
        if not vistos.inserir(registro.id):
            problemas.append(f"registro duplicado: {registro.id}")
        elif not por_id.contem(registro.id):
            problemas.append(f"registro que não existia no lote: {registro.id}")
        elif por_id.buscar(registro.id) != registro:
            problemas.append(f"registro alterado: {registro.id}")
    for registro in original:
        if not vistos.contem(registro.id):
            problemas.append(f"registro perdido: {registro.id}")

    for posicao in range(len(resultado) - 1):
        atual, seguinte = resultado[posicao], resultado[posicao + 1]
        if chave(seguinte) < chave(atual):
            problemas.append(
                f"fora de ordem na posição {posicao + 1}: {atual.id} {_formatar(chave(atual))} vem antes de "
                f"{seguinte.id} {_formatar(chave(seguinte))}"
            )
            break  # a primeira quebra de ordem basta como feedback
    return problemas


class FaseArquivoEmbaralhado(Fase):
    numero = 1
    titulo = "O Arquivo Embaralhado"
    objetivo = (
        "Ordenar o lote de registros por zona, seção e horário, sem perder, "
        "duplicar ou alterar nenhum registro."
    )
    ACOES = (
        "carregar_lote",
        "selecionar_algoritmo",
        "selecionar_criterio",
        "executar_ordenacao",
        "verificar",
        "comparar_algoritmos",
        "consultar",
    )

    def __init__(self, quantidade: int = TAMANHO_LOTE_PADRAO, seed: int = SEED_PADRAO) -> None:
        self.quantidade = quantidade
        self.seed = seed
        self.reiniciar()

    # ------------------------------------------------------------------
    def reiniciar(self) -> None:
        registros = gerar_registros(self.quantidade, seed=self.seed)
        random.Random(self.seed).shuffle(registros)  # embaralhamento reproduzível
        self.lote: tuple[RegistroVotacao, ...] = tuple(registros)
        self._limpar_execucao()

    def _limpar_execucao(self) -> None:
        self.algoritmo: str | None = None
        self.criterio: str | None = None
        self.resultado: list[RegistroVotacao] | None = None
        self.metricas: MetricasOrdenacao | None = None
        self.inconsistencias: list[str] = []

    def esta_concluida(self) -> bool:
        return self.resultado is not None and not self.inconsistencias

    def consultar(self) -> dict[str, Any]:
        return {
            "tamanho_lote": len(self.lote),
            "algoritmo": self.algoritmo,
            "criterio": self.criterio,
            "algoritmos_disponiveis": sorted(ALGORITMOS),
            "criterios_disponiveis": sorted(CRITERIOS),
            "ordenado": self.resultado is not None,
            "inconsistencias": list(self.inconsistencias),
            "concluida": self.esta_concluida(),
        }

    # ------------------------------------------------------------------
    def carregar_lote(self, registros: Sequence[RegistroVotacao]) -> ResultadoAcao:
        """Substitui o lote atual por outro (validado). Lote inválido não é carregado."""
        registros = list(registros)
        if not registros:
            return ResultadoAcao.falha("Lote vazio: nada para ordenar.")
        erros = validar_registros(registros)
        if erros:
            return ResultadoAcao.falha(f"Lote inválido ({len(erros)} problema(s)): {erros[0]}", erros=erros)
        self.lote = tuple(registros)
        self._limpar_execucao()
        return ResultadoAcao.ok(f"Lote com {len(registros)} registros carregado.")

    def selecionar_algoritmo(self, nome: str) -> ResultadoAcao:
        if nome not in ALGORITMOS:
            return ResultadoAcao.falha(f"Algoritmo desconhecido: {nome!r}. Opções: {', '.join(sorted(ALGORITMOS))}.")
        self.algoritmo = nome
        return ResultadoAcao.ok(f"Algoritmo selecionado: {nome}.")

    def selecionar_criterio(self, nome: str) -> ResultadoAcao:
        if nome not in CRITERIOS:
            return ResultadoAcao.falha(f"Critério desconhecido: {nome!r}. Opções: {', '.join(sorted(CRITERIOS))}.")
        self.criterio = nome
        return ResultadoAcao.ok(f"Critério selecionado: {nome}.")

    def executar_ordenacao(self) -> ResultadoAcao:
        """Ordena o lote com o algoritmo e critério escolhidos e verifica o objetivo."""
        if self.algoritmo is None:
            return ResultadoAcao.falha("Selecione um algoritmo antes de ordenar.")
        if self.criterio is None:
            return ResultadoAcao.falha("Selecione um critério antes de ordenar.")
        resultado, metricas = ALGORITMOS[self.algoritmo](self.lote, chave=CRITERIOS[self.criterio])
        self.resultado, self.metricas = resultado, metricas
        self.inconsistencias = verificar_ordenacao(self.lote, resultado, CRITERIO_OBJETIVO)
        dados = {
            "comparacoes": metricas.comparacoes,
            "movimentacoes": metricas.movimentacoes,
            "tempo_segundos": metricas.tempo_segundos,
            "inconsistencias": list(self.inconsistencias),
        }
        if self.inconsistencias:
            dica = ""
            if self.criterio != CRITERIO_OBJETIVO:
                dica = f" O critério '{self.criterio}' não organiza por zona, seção e horário."
            return ResultadoAcao.falha(
                f"Ordenação executada, mas o arquivo continua fora do padrão: {self.inconsistencias[0]}.{dica}",
                **dados,
            )
        return ResultadoAcao.ok(
            f"Arquivo organizado com {self.algoritmo}: {metricas.comparacoes} comparações, "
            f"{metricas.movimentacoes} movimentações.",
            **dados,
        )

    def verificar(self) -> ResultadoAcao:
        """Reconfere o resultado atual (sem reordenar)."""
        if self.resultado is None:
            return ResultadoAcao.falha("Nenhuma ordenação executada ainda.")
        problemas = verificar_ordenacao(self.lote, self.resultado, CRITERIO_OBJETIVO)
        if problemas:
            return ResultadoAcao.falha(f"{len(problemas)} inconsistência(s): {problemas[0]}", inconsistencias=problemas)
        return ResultadoAcao.ok("Ordenação conferida: ordem correta e nenhum registro perdido ou duplicado.")

    def comparar_algoritmos(self) -> ResultadoAcao:
        """Roda os três algoritmos no lote atual pelo critério objetivo (não altera a fase)."""
        tabela = []
        for nome, funcao in ALGORITMOS.items():
            _, m = funcao(self.lote, chave=CRITERIOS[CRITERIO_OBJETIVO])
            tabela.append(
                {"algoritmo": nome, "comparacoes": m.comparacoes, "movimentacoes": m.movimentacoes, "tempo_segundos": m.tempo_segundos}
            )
        return ResultadoAcao.ok("Comparação dos três algoritmos no lote atual.", tabela=tabela)
