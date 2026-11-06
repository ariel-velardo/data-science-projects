"""Fase 4 — O Cofre dos Estados (árvore AVL e estados repetidos).

Uma sequência de estados de investigação chega ao cofre. Para cada um, o
jogador decide se é NOVO ou REPETIDO (equivalente a um estado já guardado).
O sistema confere a resposta consultando a árvore AVL do projeto pela chave
canônica do estado (posição, pistas, portas, energia):

- resposta correta e estado novo  → o estado é inserido na AVL;
- resposta correta e repetido     → o sistema mostra a qual estado ele equivale;
- resposta errada                 → feedback explicativo, nada muda.

Estados didáticos: A (Praça, sem autenticação), B (Praça, com autenticação)
e C (idêntico a A) — A e B são diferentes, A e C são equivalentes. Os demais
mostram que energia e portas também fazem parte da chave e que a ordem das
pistas não importa. A ordem de chegada foi escolhida para provocar rotações
(D causa uma rotação simples à esquerda; G, uma simples à direita); a fase
guarda a árvore ANTES e DEPOIS de cada rotação para a interface exibir.

Objetivo verificável: todos os estados classificados corretamente, a AVL
balanceada e pelo menos uma rotação observada.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from veridia.estruturas.arvore_avl import ArvoreAVL, NoAVL
from veridia.fases.base import Fase, ResultadoAcao
from veridia.modelos.estado import ChaveEstado, EstadoJogo

RESPOSTAS = ("novo", "repetido")


@dataclass(frozen=True)
class EstadoCandidato:
    rotulo: str
    estado: EstadoJogo
    descricao: str


CANDIDATOS_PADRAO: tuple[EstadoCandidato, ...] = (
    EstadoCandidato("A", EstadoJogo("PRACA", set(), set(), 18), "Praça, sem pista de autenticação, energia 18"),
    EstadoCandidato("B", EstadoJogo("PRACA", {"autenticacao"}, set(), 18), "Praça, com pista de autenticação, energia 18"),
    EstadoCandidato("C", EstadoJogo("PRACA", set(), set(), 18), "Praça, sem pista de autenticação, energia 18"),
    EstadoCandidato("D", EstadoJogo("TORRE", {"autenticacao", "lacre"}, set(), 15), "Torre, autenticação e lacre, energia 15"),
    EstadoCandidato("E", EstadoJogo("PRACA", set(), set(), 17), "Praça, sem pistas, energia 17"),
    EstadoCandidato("F", EstadoJogo("TORRE", ["lacre", "autenticacao"], set(), 15), "Torre, lacre e autenticação, energia 15"),
    EstadoCandidato("G", EstadoJogo("ESCOLA", set(), set(), 17), "Escola, sem pistas, energia 17"),
    EstadoCandidato(
        "H", EstadoJogo("PRACA", {"autenticacao"}, {"porta_arquivo"}, 18), "Praça, autenticação, porta do arquivo aberta, energia 18"
    ),
)


def serializar_arvore(no: NoAVL | None, rotulos: dict[Any, str] | None = None) -> dict[str, Any] | None:
    """Converte a AVL em dicionários aninhados (rótulo, chave, altura, fator) para exibição."""
    if no is None:
        return None
    rotulos = rotulos or {}
    return {
        "rotulo": rotulos.get(no.chave, str(no.chave)),
        "chave": str(no.chave),
        "altura": no.altura,
        "fator": ArvoreAVL.fator_balanceamento(no),
        "esquerda": serializar_arvore(no.esquerda, rotulos),
        "direita": serializar_arvore(no.direita, rotulos),
    }


class FaseCofreEstados(Fase):
    numero = 4
    titulo = "O Cofre dos Estados"
    objetivo = "Classificar cada estado como novo ou repetido; o cofre (AVL) deve continuar balanceado."
    ACOES = ("classificar", "buscar", "comparar", "estrutura", "consultar")

    def __init__(self, candidatos: tuple[EstadoCandidato, ...] = CANDIDATOS_PADRAO) -> None:
        rotulos = [c.rotulo for c in candidatos]
        if len(set(rotulos)) != len(rotulos):
            raise ValueError("rótulos de candidatos repetidos")
        self.candidatos = tuple(candidatos)
        self.reiniciar()

    def reiniciar(self) -> None:
        self.avl: ArvoreAVL[ChaveEstado, str] = ArvoreAVL()  # chave canônica → rótulo do 1º estado guardado
        self.indice = 0
        self.erros = 0
        self.rotacoes_observadas: list[dict[str, Any]] = []
        self.buscas: list[dict[str, Any]] = []

    def _rotulos(self) -> dict[Any, str]:
        return {chave: rotulo for chave, rotulo in self.avl.em_ordem()}

    def esta_concluida(self) -> bool:
        return self.indice == len(self.candidatos) and bool(self.rotacoes_observadas) and self.avl.esta_balanceada()

    def candidato_atual(self) -> EstadoCandidato | None:
        return self.candidatos[self.indice] if self.indice < len(self.candidatos) else None

    def consultar(self) -> dict[str, Any]:
        atual = self.candidato_atual()
        return {
            "candidato_atual": None if atual is None else {"rotulo": atual.rotulo, "descricao": atual.descricao, "estado": str(atual.estado)},
            "classificados": self.indice,
            "total": len(self.candidatos),
            "erros": self.erros,
            "estados_no_cofre": len(self.avl),
            "altura": self.avl.altura(),
            "fatores": self.fatores(),
            "rotacoes": dict(self.avl.rotacoes),
            "rotacoes_observadas": len(self.rotacoes_observadas),
            "concluida": self.esta_concluida(),
        }

    def fatores(self) -> list[dict[str, Any]]:
        """Altura e fator de balanceamento de cada nó, em ordem de chave."""
        resultado: list[dict[str, Any]] = []

        def visitar(no: NoAVL | None) -> None:
            if no is None:
                return
            visitar(no.esquerda)
            resultado.append({"rotulo": no.valor, "altura": no.altura, "fator": ArvoreAVL.fator_balanceamento(no)})
            visitar(no.direita)

        visitar(self.avl.raiz)
        return resultado

    # ------------------------------------------------------------------
    def classificar(self, resposta: str) -> ResultadoAcao:
        """Classifica o estado atual como "novo" ou "repetido"."""
        atual = self.candidato_atual()
        if atual is None:
            return ResultadoAcao.falha("Todos os estados já foram classificados.")
        if resposta not in RESPOSTAS:
            return ResultadoAcao.falha(f"Resposta inválida: {resposta!r}. Use 'novo' ou 'repetido'.")

        chave = atual.estado.chave()
        ja_existe = self.avl.contem(chave)
        if (resposta == "repetido") != ja_existe:
            self.erros += 1
            if ja_existe:
                return ResultadoAcao.falha(
                    f"Incorreto: {atual.rotulo} tem a mesma posição, pistas, portas e energia de "
                    f"{self.avl.buscar(chave)} — é um estado repetido."
                )
            return ResultadoAcao.falha(
                f"Incorreto: nenhum estado guardado tem a chave {chave}. "
                "Basta um atributo diferente (pistas, portas ou energia) para ser um estado novo."
            )

        self.indice += 1
        if ja_existe:
            equivalente = self.avl.buscar(chave)
            return ResultadoAcao.ok(f"Correto: {atual.rotulo} é equivalente a {equivalente}.", equivalente=equivalente)

        antes = serializar_arvore(self.avl.raiz, self._rotulos())
        rotacoes_antes = dict(self.avl.rotacoes)
        self.avl.inserir(chave, atual.rotulo)
        rotacoes_novas = {tipo: n - rotacoes_antes[tipo] for tipo, n in self.avl.rotacoes.items() if n != rotacoes_antes[tipo]}
        dados: dict[str, Any] = {"altura": self.avl.altura(), "rotacoes": rotacoes_novas}
        mensagem = f"Correto: {atual.rotulo} é novo e foi guardado no cofre (altura {self.avl.altura()})."
        if rotacoes_novas:
            registro = {
                "rotulo_inserido": atual.rotulo,
                "rotacoes": rotacoes_novas,
                "antes": antes,
                "depois": serializar_arvore(self.avl.raiz, self._rotulos()),
            }
            self.rotacoes_observadas.append(registro)
            dados["antes"], dados["depois"] = registro["antes"], registro["depois"]
            mensagem += f" A inserção desbalanceou a árvore e provocou rotação: {rotacoes_novas}."
        return ResultadoAcao.ok(mensagem, **dados)

    def buscar(self, estado: EstadoJogo) -> ResultadoAcao:
        """Procura um estado (qualquer, não só candidatos) no cofre. O(log n)."""
        chave = estado.chave()
        encontrado = self.avl.contem(chave)
        self.buscas.append({"chave": str(chave), "encontrado": encontrado})
        if encontrado:
            return ResultadoAcao.ok(f"Estado encontrado no cofre: {self.avl.buscar(chave)}.", encontrado=True, rotulo=self.avl.buscar(chave))
        return ResultadoAcao.ok("Estado não está no cofre.", encontrado=False)

    def comparar(self, rotulo_a: str, rotulo_b: str) -> ResultadoAcao:
        """Compara dois candidatos atributo por atributo."""
        por_rotulo = {c.rotulo: c for c in self.candidatos}
        if rotulo_a not in por_rotulo or rotulo_b not in por_rotulo:
            return ResultadoAcao.falha(f"Rótulos válidos: {', '.join(por_rotulo)}.")
        ea, eb = por_rotulo[rotulo_a].estado, por_rotulo[rotulo_b].estado
        nomes = ("posicao", "pistas", "portas_liberadas", "energia")
        diferencas = [nome for nome, va, vb in zip(nomes, ea.chave(), eb.chave()) if va != vb]
        if not diferencas:
            return ResultadoAcao.ok(f"{rotulo_a} e {rotulo_b} são equivalentes (mesma chave).", equivalentes=True, diferencas=[])
        return ResultadoAcao.ok(
            f"{rotulo_a} e {rotulo_b} são diferentes em: {', '.join(diferencas)}.", equivalentes=False, diferencas=diferencas
        )

    def estrutura(self) -> ResultadoAcao:
        return ResultadoAcao.ok(
            f"Cofre com {len(self.avl)} estados, altura {self.avl.altura()}.",
            arvore=serializar_arvore(self.avl.raiz, self._rotulos()),
            fatores=self.fatores(),
        )
