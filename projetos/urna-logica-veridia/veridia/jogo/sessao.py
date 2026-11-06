"""Sessão do jogo: progressão, selos e histórico (separados das regras dos enigmas).

A sessão não sabe COMO cada enigma funciona; ela só:
- cria as cinco fases;
- encaminha ações para a fase atual (``executar``), por nome;
- registra o histórico de ações relevantes (lista ligada, em ordem);
- concede o selo da fase quando ``fase.esta_concluida()`` se torna verdadeiro;
- controla a fase atual e o desbloqueio (fase N exige o selo N-1);
- reinicia fases individualmente.

Decisão: selos são conquistas permanentes da sessão. Reiniciar uma fase NÃO
remove selos. A Auditoria Final (Fase 5), porém, reconfere o estado ATUAL
de cada fase — se uma fase concluída for reiniciada, a auditoria acusa a
inconsistência mesmo com o selo guardado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from veridia.dados.gerador_registros import SEED_PADRAO
from veridia.estruturas.lista_ligada import ListaLigada
from veridia.fases.base import Fase, ResultadoAcao
from veridia.fases.fase1_arquivo import FaseArquivoEmbaralhado
from veridia.fases.fase2_triagem import FaseCentralTriagem
from veridia.fases.fase3_mapa import FaseMapaSecoes
from veridia.fases.fase4_cofre import FaseCofreEstados
from veridia.fases.fase5_auditoria import FaseAuditoriaFinal

TOTAL_FASES = 5

# Ações que apenas consultam: não entram no histórico.
CONSULTAS = frozenset(
    {
        "consultar",
        "comparar_algoritmos",
        "local_atual",
        "conexoes_disponiveis",
        "portas_bloqueadas",
        "pistas_coletadas",
        "energia_restante",
        "estrutura",
        "comparar",
        "buscar",
        "sugerir_solucao",
        "solicitar_solucao",
    }
)


@dataclass(frozen=True)
class RegistroHistorico:
    ordem: int
    fase: int
    acao: str
    argumentos: str
    sucesso: bool
    mensagem: str


class SessaoJogo:
    def __init__(self, seed: int = SEED_PADRAO) -> None:
        self.seed = seed
        self.reiniciar_jogo()

    def reiniciar_jogo(self) -> None:
        fase1 = FaseArquivoEmbaralhado(seed=self.seed)
        fase2 = FaseCentralTriagem()
        fase3 = FaseMapaSecoes()
        fase4 = FaseCofreEstados()
        fase5 = FaseAuditoriaFinal(fase1, fase2, fase3, fase4, obter_selos=lambda: set(self.selos))
        self.fases: dict[int, Fase] = {1: fase1, 2: fase2, 3: fase3, 4: fase4, 5: fase5}
        self.selos: set[int] = set()
        self.fase_atual = 1
        self.historico: ListaLigada[RegistroHistorico] = ListaLigada()

    # ------------------------------------------------------------------
    @property
    def fase(self) -> Fase:
        return self.fases[self.fase_atual]

    def fase_liberada(self, numero: int) -> bool:
        return numero == 1 or (numero - 1) in self.selos

    def jogo_concluido(self) -> bool:
        return len(self.selos) == TOTAL_FASES

    def _registrar(self, fase: int, acao: str, argumentos: str, resultado: ResultadoAcao) -> None:
        self.historico.inserir_fim(
            RegistroHistorico(len(self.historico) + 1, fase, acao, argumentos, resultado.sucesso, resultado.mensagem)
        )

    def ir_para_fase(self, numero: int) -> ResultadoAcao:
        if numero not in self.fases:
            return ResultadoAcao.falha(f"Fase inexistente: {numero}. Use 1 a {TOTAL_FASES}.")
        if not self.fase_liberada(numero):
            return ResultadoAcao.falha(f"Fase {numero} bloqueada: conquiste antes o selo da fase {numero - 1}.")
        self.fase_atual = numero
        fase = self.fases[numero]
        return ResultadoAcao.ok(f"Fase {numero} — {fase.titulo}. Objetivo: {fase.objetivo}")

    def executar(self, acao: str, *args: Any, **kwargs: Any) -> ResultadoAcao:
        """Executa uma ação da fase atual, registra no histórico e concede o selo se o objetivo for atingido."""
        numero, fase = self.fase_atual, self.fase
        if acao not in fase.ACOES:
            return ResultadoAcao.falha(f"Ação '{acao}' não existe na fase {numero}. Ações: {', '.join(fase.ACOES)}.")
        try:
            retorno = getattr(fase, acao)(*args, **kwargs)
        except TypeError as erro:
            return ResultadoAcao.falha(f"Argumentos inválidos para '{acao}': {erro}.")
        resultado = retorno if isinstance(retorno, ResultadoAcao) else ResultadoAcao.ok("Consulta realizada.", estado=retorno)

        if acao not in CONSULTAS:
            argumentos = ", ".join([repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()])
            self._registrar(numero, acao, argumentos, resultado)

        if numero not in self.selos and fase.esta_concluida():
            self.selos.add(numero)
            if numero < TOTAL_FASES:
                self.fase_atual = numero + 1
            extra = " Jogo concluído!" if self.jogo_concluido() else f" Fase {self.fase_atual} liberada."
            resultado = ResultadoAcao(
                resultado.sucesso,
                f"{resultado.mensagem} Selo {numero} de auditoria concedido!{extra}",
                {**resultado.dados, "selo_concedido": numero},
            )
        return resultado

    def reiniciar_fase(self, numero: int | None = None) -> ResultadoAcao:
        """Reinicia uma fase (a atual, por padrão) sem afetar as demais nem os selos."""
        numero = self.fase_atual if numero is None else numero
        if numero not in self.fases:
            return ResultadoAcao.falha(f"Fase inexistente: {numero}.")
        self.fases[numero].reiniciar()
        resultado = ResultadoAcao.ok(f"Fase {numero} reiniciada. Selos mantidos: {sorted(self.selos)}.")
        self._registrar(numero, "reiniciar_fase", "", resultado)
        return resultado

    def resumo(self) -> dict[str, Any]:
        return {
            "fase_atual": self.fase_atual,
            "selos": sorted(self.selos),
            "fases": [
                {
                    "numero": n,
                    "titulo": f.titulo,
                    "liberada": self.fase_liberada(n),
                    "selo": n in self.selos,
                    "concluida_agora": f.esta_concluida(),
                }
                for n, f in self.fases.items()
            ],
            "acoes_registradas": len(self.historico),
            "jogo_concluido": self.jogo_concluido(),
        }
