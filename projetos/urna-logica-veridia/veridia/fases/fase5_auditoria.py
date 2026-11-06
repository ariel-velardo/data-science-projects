"""Fase 5 — A Auditoria Final (integração, solver, ordenação e métricas).

A auditoria reconfere, a partir do estado ATUAL das fases anteriores (nada é
lido de respostas guardadas), se a investigação é consistente:

1. ordenacao_registros  — o lote da Fase 1 está ordenado e íntegro; o lote é
                          reordenado com o algoritmo escolhido e o resultado
                          precisa coincidir (reuso explícito da Fase 1);
2. custodia             — a cadeia de custódia da Fase 2 é E2 → E4 → E1 → E6;
3. trilha               — a trilha manual da Fase 3 é reexecutada pelas regras;
                          o solver é executado para conferir que existe
                          caminho e para fornecer métricas;
4. evidencias_necessarias — o estado final tem as pistas exigidas;
5. estado_final         — o estado final é vitorioso segundo as regras;
6. cofre                — a Fase 4 foi concluída com a AVL balanceada;
7. selos                — os selos 1 a 4 foram obtidos.

O relatório (``RelatorioAuditoria``) organiza as evidências coletadas com um
algoritmo de ordenação da Fase 1 e pode ser convertido em dicionário de
tipos simples (``relatorio_para_dict``) para exibição ou exportação (JSON).
Objetivo verificável: um relatório consistente (nenhuma inconsistência).
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from veridia.algoritmos.ordenacao import ALGORITMOS, CRITERIOS
from veridia.busca.solver import BUSCAS, resolver_mapa
from veridia.fases.base import Fase, ResultadoAcao
from veridia.fases.fase1_arquivo import CRITERIO_OBJETIVO, verificar_ordenacao
from veridia.jogo import regras
from veridia.jogo.regras import MovimentoInvalidoError

if TYPE_CHECKING:
    from veridia.fases.fase1_arquivo import FaseArquivoEmbaralhado
    from veridia.fases.fase2_triagem import FaseCentralTriagem
    from veridia.fases.fase3_mapa import FaseMapaSecoes
    from veridia.fases.fase4_cofre import FaseCofreEstados


@dataclass
class RelatorioAuditoria:
    consistente: bool
    selos: list[int]
    algoritmo_busca: str
    algoritmo_ordenacao: str
    origem_trilha: str                 # "manual" (Fase 3) ou "solver" (referência)
    caminho: list[str]                 # locais visitados, do início ao fim
    movimentos: int
    energia_consumida: int
    estados_explorados: int            # pelo solver
    tempo_busca_segundos: float
    tempo_total_segundos: float
    registros_conferidos: int
    metricas_ordenacao: dict[str, Any]
    custodia: list[str]
    evidencias_ordenadas: list[dict[str, str]]
    verificacoes: list[dict[str, Any]] = field(default_factory=list)  # {nome, ok, detalhe}
    inconsistencias: list[str] = field(default_factory=list)


def relatorio_para_dict(relatorio: RelatorioAuditoria) -> dict[str, Any]:
    """Dicionário só com tipos simples (str, int, float, bool, list, dict, None) — pronto para JSON."""
    return asdict(relatorio)


class FaseAuditoriaFinal(Fase):
    numero = 5
    titulo = "A Auditoria Final"
    objetivo = "Produzir um relatório de auditoria consistente reunindo as quatro fases anteriores."
    ACOES = ("executar_auditoria", "consultar")

    def __init__(
        self,
        fase1: "FaseArquivoEmbaralhado",
        fase2: "FaseCentralTriagem",
        fase3: "FaseMapaSecoes",
        fase4: "FaseCofreEstados",
        obter_selos: Callable[[], set[int]],
    ) -> None:
        self.fase1, self.fase2, self.fase3, self.fase4 = fase1, fase2, fase3, fase4
        self.obter_selos = obter_selos
        self.reiniciar()

    def reiniciar(self) -> None:
        self.relatorio: RelatorioAuditoria | None = None

    def esta_concluida(self) -> bool:
        return self.relatorio is not None and self.relatorio.consistente

    def consultar(self) -> dict[str, Any]:
        return {
            "relatorio": None if self.relatorio is None else relatorio_para_dict(self.relatorio),
            "concluida": self.esta_concluida(),
        }

    # ------------------------------------------------------------------
    def executar_auditoria(self, algoritmo_busca: str = "BFS", algoritmo_ordenacao: str = "merge_sort") -> ResultadoAcao:
        if algoritmo_busca.upper() not in BUSCAS:
            return ResultadoAcao.falha(f"Algoritmo de busca desconhecido: {algoritmo_busca!r}.")
        if algoritmo_ordenacao not in ALGORITMOS:
            return ResultadoAcao.falha(f"Algoritmo de ordenação desconhecido: {algoritmo_ordenacao!r}.")

        inicio = time.perf_counter()
        verificacoes: list[dict[str, Any]] = []

        def verificar(nome: str, ok: bool, detalhe: str) -> None:
            verificacoes.append({"nome": nome, "ok": ok, "detalhe": detalhe})

        # 1. Ordenação dos registros (reuso explícito de um algoritmo da Fase 1)
        ordenar = ALGORITMOS[algoritmo_ordenacao]
        chave_registro = CRITERIOS[CRITERIO_OBJETIVO]
        reordenado, metricas_reg = ordenar(self.fase1.lote, chave=chave_registro)
        if self.fase1.resultado is None:
            verificar("ordenacao_registros", False, "Fase 1: o lote ainda não foi ordenado.")
        else:
            problemas = verificar_ordenacao(self.fase1.lote, self.fase1.resultado)
            coincide = [chave_registro(r) for r in reordenado] == [chave_registro(r) for r in self.fase1.resultado]
            if problemas:
                verificar("ordenacao_registros", False, f"Fase 1: {problemas[0]}.")
            elif not coincide:
                verificar("ordenacao_registros", False, f"Fase 1: resultado difere da reordenação com {algoritmo_ordenacao}.")
            else:
                verificar("ordenacao_registros", True, f"{len(reordenado)} registros conferidos com {algoritmo_ordenacao}.")

        # 2. Cadeia de custódia
        custodia = list(self.fase2.custodia)
        verificar(
            "custodia",
            self.fase2.esta_concluida(),
            "Custódia válida." if self.fase2.esta_concluida() else f"Fase 2: custódia {custodia} incompleta ou incorreta.",
        )

        # 3. Trilha no mapa: manual reexecutada pelas regras; solver sempre executado
        mapa = self.fase3.mapa
        solucao = resolver_mapa(mapa, algoritmo_busca)
        destinos_manuais = [m.destino for m in self.fase3.trilha()]
        final_manual = None
        motivo_trilha = "Fase 3: nenhum movimento manual registrado"
        if destinos_manuais:
            try:
                final_manual = regras.reproduzir_caminho(mapa, destinos_manuais)
                if not regras.verificar_vitoria(mapa, final_manual):
                    motivo_trilha = "Fase 3: a trilha manual não chega ao destino com as pistas necessárias"
                    final_manual = None
            except MovimentoInvalidoError as erro:
                motivo_trilha = f"Fase 3: a trilha manual viola as regras ({erro})"
        if final_manual is not None:
            origem, destinos, estado_final = "manual", destinos_manuais, final_manual
            verificar(
                "trilha", True,
                f"Trilha manual com {len(destinos)} movimentos revalidada; {solucao.algoritmo} confirma que há caminho "
                f"({solucao.comprimento} movimentos).",
            )
        else:
            origem, destinos, estado_final = "solver", [m.destino for m in solucao.acoes], solucao.estado_final
            referencia = "caminho de referência fornecido pelo solver" if solucao.encontrou else "o solver também não encontrou caminho"
            verificar("trilha", False, f"{motivo_trilha}; {referencia}.")

        # 4 e 5. Evidências necessárias e estado final
        if estado_final is None:
            verificar("evidencias_necessarias", False, "Sem estado final para conferir.")
            verificar("estado_final", False, "Sem estado final para conferir.")
            pistas_finais: set[str] = set()
            energia_consumida = 0
        else:
            faltando = sorted(mapa.pistas_necessarias - estado_final.pistas)
            verificar(
                "evidencias_necessarias",
                not faltando,
                "Todas as pistas necessárias coletadas." if not faltando else f"Faltam pistas: {faltando}.",
            )
            vitoria = regras.verificar_vitoria(mapa, estado_final) and estado_final.energia >= 0
            verificar("estado_final", vitoria, f"Estado final {estado_final} {'é' if vitoria else 'não é'} vitorioso.")
            pistas_finais = set(estado_final.pistas)
            energia_consumida = mapa.energia_inicial - estado_final.energia

        # 6. Cofre
        verificar(
            "cofre",
            self.fase4.esta_concluida(),
            "Cofre de estados concluído e balanceado." if self.fase4.esta_concluida() else "Fase 4: cofre não concluído.",
        )

        # 7. Selos
        selos = sorted(self.obter_selos())
        faltam_selos = [n for n in (1, 2, 3, 4) if n not in selos]
        verificar("selos", not faltam_selos, "Selos 1 a 4 obtidos." if not faltam_selos else f"Selos ausentes: {faltam_selos}.")

        # Evidências coletadas organizadas com o mesmo algoritmo de ordenação (tipo, id)
        evidencias = [mapa.evidencias[p] for p in pistas_finais]
        evidencias_ordenadas, _ = ordenar(evidencias, chave=lambda e: (e.tipo.value, e.id))

        inconsistencias = [v["detalhe"] for v in verificacoes if not v["ok"]]
        self.relatorio = RelatorioAuditoria(
            consistente=not inconsistencias,
            selos=selos,
            algoritmo_busca=solucao.algoritmo,
            algoritmo_ordenacao=algoritmo_ordenacao,
            origem_trilha=origem,
            caminho=[mapa.inicio] + destinos if estado_final is not None else [],
            movimentos=len(destinos) if estado_final is not None else 0,
            energia_consumida=energia_consumida,
            estados_explorados=solucao.estados_explorados,
            tempo_busca_segundos=solucao.tempo_segundos,
            tempo_total_segundos=time.perf_counter() - inicio,
            registros_conferidos=len(reordenado),
            metricas_ordenacao={
                "comparacoes": metricas_reg.comparacoes,
                "movimentacoes": metricas_reg.movimentacoes,
                "tempo_segundos": metricas_reg.tempo_segundos,
            },
            custodia=custodia,
            evidencias_ordenadas=[{"id": e.id, "tipo": e.tipo.value, "descricao": e.descricao} for e in evidencias_ordenadas],
            verificacoes=verificacoes,
            inconsistencias=inconsistencias,
        )
        dados = {"relatorio": relatorio_para_dict(self.relatorio)}
        if inconsistencias:
            return ResultadoAcao.falha(f"Auditoria inconsistente: {len(inconsistencias)} problema(s). {inconsistencias[0]}", **dados)
        return ResultadoAcao.ok("Auditoria consistente: a investigação de Verídia está comprovada.", **dados)
