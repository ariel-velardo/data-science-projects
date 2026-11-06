"""Fase 2 — A Central de Triagem (fila, pilha, lista ligada e desfazer).

Seis evidências (E1..E6) chegam pela FILA de entrada, nessa ordem. O jogador
precisa montar a LISTA DE CUSTÓDIA exatamente na sequência E2 → E4 → E1 → E6.

Estruturas (todas implementadas no projeto):
- fila de entrada   (Fila)        — só se acessa a evidência da FRENTE;
- pilha temporária  (Pilha)       — capacidade 2; só se acessa o TOPO;
- lista de custódia (ListaLigada) — só recebe evidências no FIM;
- arquivo           (ListaLigada) — evidências que não entram na custódia
                                    ficam registradas aqui (nada desaparece);
- histórico         (Pilha)       — retrato das estruturas antes de cada
                                    ação, usado pelo DESFAZER.

Ações de movimentação:
    receber_na_custodia  frente da fila  → fim da custódia
    guardar_na_pilha     frente da fila  → topo da pilha (se houver espaço)
    custodiar_da_pilha   topo da pilha   → fim da custódia
    arquivar_da_fila     frente da fila  → arquivo
    arquivar_da_pilha    topo da pilha   → arquivo
    desfazer             restaura o retrato do topo do histórico

Objetivo verificável: custódia == E2, E4, E1, E6; fila e pilha vazias; as
seis evidências contabilizadas uma única vez (custódia + arquivo).

Por que é um enigma: E1 chega antes de E2 mas precisa entrar DEPOIS dela,
então tem de esperar na pilha; E3 e E5 precisam ser arquivadas no momento
certo; arquivar ou custodiar fora de ordem só se corrige com DESFAZER.
A solução não está programada: ``sugerir_solucao`` a descobre com a BFS do
motor de busca, aplicando estas mesmas ações.
"""

from __future__ import annotations

from typing import Any

from veridia.busca.solver import BUSCAS, ResultadoBusca
from veridia.estruturas.fila import Fila
from veridia.estruturas.lista_ligada import ListaLigada
from veridia.estruturas.pilha import Pilha
from veridia.fases.base import Fase, ResultadoAcao

EVIDENCIAS_CHEGADA: tuple[str, ...] = ("E1", "E2", "E3", "E4", "E5", "E6")
SEQUENCIA_ALVO: tuple[str, ...] = ("E2", "E4", "E1", "E6")
CAPACIDADE_PILHA = 2

ACOES_MOVIMENTO: tuple[str, ...] = (
    "receber_na_custodia",
    "guardar_na_pilha",
    "custodiar_da_pilha",
    "arquivar_da_fila",
    "arquivar_da_pilha",
)

# Retrato imutável e comparável: (fila frente→fim, pilha base→topo, custódia, arquivo)
Instantaneo = tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]


class FaseCentralTriagem(Fase):
    numero = 2
    titulo = "A Central de Triagem"
    objetivo = "Montar a lista de custódia E2 → E4 → E1 → E6, sem perder nenhuma evidência."
    ACOES = ACOES_MOVIMENTO + ("desfazer", "validar", "sugerir_solucao", "consultar")

    def __init__(
        self,
        chegada: tuple[str, ...] = EVIDENCIAS_CHEGADA,
        alvo: tuple[str, ...] = SEQUENCIA_ALVO,
        capacidade_pilha: int = CAPACIDADE_PILHA,
    ) -> None:
        if len(set(chegada)) != len(chegada):
            raise ValueError("evidências de chegada repetidas")
        if not set(alvo) <= set(chegada):
            raise ValueError("a sequência alvo contém evidências que não chegam pela fila")
        self.chegada = tuple(chegada)
        self.alvo = tuple(alvo)
        self.capacidade_pilha = capacidade_pilha
        self.reiniciar()

    # ------------------------------------------------------------------
    # Estado, retrato e restauração
    # ------------------------------------------------------------------
    def reiniciar(self) -> None:
        self.fila: Fila[str] = Fila()
        for evidencia in self.chegada:
            self.fila.enfileirar(evidencia)
        self.pilha: Pilha[str] = Pilha()
        self.custodia: ListaLigada[str] = ListaLigada()
        self.arquivo: ListaLigada[str] = ListaLigada()
        self.historico: Pilha[tuple[str, Instantaneo]] = Pilha()

    def instantaneo(self) -> Instantaneo:
        return (
            tuple(self.fila),
            tuple(reversed(list(self.pilha))),  # a Pilha itera topo→base; guardamos base→topo
            tuple(self.custodia),
            tuple(self.arquivo),
        )

    def restaurar(self, retrato: Instantaneo) -> None:
        """Reconstrói fila, pilha, custódia e arquivo a partir de um retrato (não mexe no histórico)."""
        fila, pilha, custodia, arquivo = retrato
        self.fila = Fila()
        for e in fila:
            self.fila.enfileirar(e)
        self.pilha = Pilha()
        for e in pilha:
            self.pilha.empilhar(e)
        self.custodia = ListaLigada(custodia)
        self.arquivo = ListaLigada(arquivo)

    def consultar(self) -> dict[str, Any]:
        fila, pilha, custodia, arquivo = self.instantaneo()
        return {
            "fila_entrada": list(fila),
            "frente_da_fila": fila[0] if fila else None,
            "pilha_temporaria": list(pilha),
            "topo_da_pilha": pilha[-1] if pilha else None,
            "capacidade_pilha": self.capacidade_pilha,
            "custodia": list(custodia),
            "arquivo": list(arquivo),
            "sequencia_alvo": list(self.alvo),
            "historico": [descricao for descricao, _ in self.historico],  # mais recente primeiro
            "concluida": self.esta_concluida(),
        }

    # ------------------------------------------------------------------
    # Objetivo
    # ------------------------------------------------------------------
    def _problemas(self) -> list[str]:
        problemas: list[str] = []
        custodia = tuple(self.custodia)
        if custodia != self.alvo:
            problemas.append(f"custódia {list(custodia)} difere da sequência exigida {list(self.alvo)}")
        if not self.fila.esta_vazia():
            problemas.append(f"ainda há {len(self.fila)} evidência(s) na fila de entrada")
        if not self.pilha.esta_vazia():
            problemas.append(f"ainda há {len(self.pilha)} evidência(s) na pilha temporária")
        contabilizadas = list(self.custodia) + list(self.arquivo) + list(self.fila) + list(self.pilha)
        if sorted(contabilizadas) != sorted(self.chegada):
            problemas.append("evidências perdidas ou duplicadas")
        return problemas

    def esta_concluida(self) -> bool:
        return not self._problemas()

    def validar(self) -> ResultadoAcao:
        problemas = self._problemas()
        if problemas:
            return ResultadoAcao.falha("Custódia ainda inválida: " + "; ".join(problemas) + ".", problemas=problemas)
        return ResultadoAcao.ok("Cadeia de custódia válida: E2 → E4 → E1 → E6, demais evidências arquivadas.")

    # ------------------------------------------------------------------
    # Movimentações (ação inválida → falha sem alterar nada)
    # ------------------------------------------------------------------
    def _registrar(self, descricao: str) -> None:
        self.historico.empilhar((descricao, self.instantaneo()))

    def receber_na_custodia(self) -> ResultadoAcao:
        if self.fila.esta_vazia():
            return ResultadoAcao.falha("A fila de entrada está vazia.")
        evidencia = self.fila.frente()
        self._registrar(f"{evidencia}: fila → custódia")
        self.custodia.inserir_fim(self.fila.desenfileirar())
        return ResultadoAcao.ok(f"{evidencia} entrou na custódia.", evidencia=evidencia)

    def guardar_na_pilha(self) -> ResultadoAcao:
        if self.fila.esta_vazia():
            return ResultadoAcao.falha("A fila de entrada está vazia.")
        if len(self.pilha) >= self.capacidade_pilha:
            return ResultadoAcao.falha(f"A pilha temporária está cheia (capacidade {self.capacidade_pilha}).")
        evidencia = self.fila.frente()
        self._registrar(f"{evidencia}: fila → pilha")
        self.pilha.empilhar(self.fila.desenfileirar())
        return ResultadoAcao.ok(f"{evidencia} guardada no topo da pilha.", evidencia=evidencia)

    def custodiar_da_pilha(self) -> ResultadoAcao:
        if self.pilha.esta_vazia():
            return ResultadoAcao.falha("A pilha temporária está vazia.")
        evidencia = self.pilha.topo()
        self._registrar(f"{evidencia}: pilha → custódia")
        self.custodia.inserir_fim(self.pilha.desempilhar())
        return ResultadoAcao.ok(f"{evidencia} saiu da pilha e entrou na custódia.", evidencia=evidencia)

    def arquivar_da_fila(self) -> ResultadoAcao:
        if self.fila.esta_vazia():
            return ResultadoAcao.falha("A fila de entrada está vazia.")
        evidencia = self.fila.frente()
        self._registrar(f"{evidencia}: fila → arquivo")
        self.arquivo.inserir_fim(self.fila.desenfileirar())
        return ResultadoAcao.ok(f"{evidencia} arquivada.", evidencia=evidencia)

    def arquivar_da_pilha(self) -> ResultadoAcao:
        if self.pilha.esta_vazia():
            return ResultadoAcao.falha("A pilha temporária está vazia.")
        evidencia = self.pilha.topo()
        self._registrar(f"{evidencia}: pilha → arquivo")
        self.arquivo.inserir_fim(self.pilha.desempilhar())
        return ResultadoAcao.ok(f"{evidencia} arquivada a partir da pilha.", evidencia=evidencia)

    def desfazer(self) -> ResultadoAcao:
        if self.historico.esta_vazia():
            return ResultadoAcao.falha("Nada para desfazer.")
        descricao, retrato = self.historico.desempilhar()
        self.restaurar(retrato)
        return ResultadoAcao.ok(f"Desfeito: {descricao}.", desfeita=descricao)

    # ------------------------------------------------------------------
    # Solver (mesmas ações do modo manual)
    # ------------------------------------------------------------------
    def _copia_em(self, retrato: Instantaneo) -> "FaseCentralTriagem":
        copia = FaseCentralTriagem(self.chegada, self.alvo, self.capacidade_pilha)
        copia.restaurar(retrato)
        return copia

    def resolver(self, algoritmo: str = "BFS") -> ResultadoBusca:
        """Executa a busca (BFS, DFS ou DFS_RECURSIVA) a partir do estado ATUAL, sem aplicá-la.

        Os sucessores de cada retrato são obtidos chamando os MESMOS métodos de
        ação do modo manual em uma cópia da fase.
        """
        if algoritmo.upper() not in BUSCAS:
            raise ValueError(f"algoritmo desconhecido: {algoritmo!r}. Opções: {sorted(BUSCAS)}.")

        def sucessores(retrato: Instantaneo):
            for acao in ACOES_MOVIMENTO:
                copia = self._copia_em(retrato)
                if getattr(copia, acao)().sucesso:
                    yield acao, copia.instantaneo()

        return BUSCAS[algoritmo.upper()](
            self.instantaneo(),
            sucessores=sucessores,
            objetivo=lambda retrato: self._copia_em(retrato).esta_concluida(),
            chave=lambda retrato: retrato,
        )

    def sugerir_solucao(self, algoritmo: str = "BFS") -> ResultadoAcao:
        """Descobre uma sequência de ações a partir do estado ATUAL (não a aplica). BFS dá a menor."""
        if algoritmo.upper() not in BUSCAS:
            return ResultadoAcao.falha(f"Algoritmo desconhecido: {algoritmo!r}. Opções: {', '.join(sorted(BUSCAS))}.")
        resultado = self.resolver(algoritmo)
        if not resultado.encontrou:
            return ResultadoAcao.falha(
                "Não há solução a partir daqui. Use desfazer ou reinicie a fase.",
                estados_explorados=resultado.estados_explorados,
            )
        return ResultadoAcao.ok(
            f"Solução com {resultado.comprimento} ações encontrada por {resultado.algoritmo}.",
            acoes=list(resultado.acoes),
            estados_explorados=resultado.estados_explorados,
        )
