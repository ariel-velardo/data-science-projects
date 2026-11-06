"""Árvore AVL (árvore binária de busca autobalanceada).

Cada nó guarda uma CHAVE única e comparável (por exemplo, a chave canônica
de um ``EstadoJogo`` ou o id de uma ``Evidencia``) e um VALOR associado.

Invariante AVL: para todo nó, |altura(esq) - altura(dir)| <= 1.
Garante altura O(log n), logo busca e inserção O(log n) no pior caso —
diferente de uma BST comum, que degenera em lista (O(n)) quando as chaves
chegam ordenadas.

Convenções:
- altura de árvore vazia = 0; altura de uma folha = 1.
- fator de balanceamento = altura(esquerda) - altura(direita).
  fator > 1  → pesada à esquerda; fator < -1 → pesada à direita.

Casos de rebalanceamento após inserção no nó desbalanceado ``z``:
- Esquerda-Esquerda (LL): rotação simples à direita em z.
- Direita-Direita  (RR): rotação simples à esquerda em z.
- Esquerda-Direita (LR): rotação à esquerda no filho esquerdo, depois à direita em z.
- Direita-Esquerda (RL): rotação à direita no filho direito, depois à esquerda em z.
"""

from __future__ import annotations

from typing import Any, Generic, Iterator, TypeVar

from veridia.estruturas.pilha import Pilha

K = TypeVar("K")
V = TypeVar("V")


class NoAVL(Generic[K, V]):
    __slots__ = ("chave", "valor", "esquerda", "direita", "altura")

    def __init__(self, chave: K, valor: V) -> None:
        self.chave = chave
        self.valor = valor
        self.esquerda: NoAVL[K, V] | None = None
        self.direita: NoAVL[K, V] | None = None
        self.altura = 1


class ArvoreAVL(Generic[K, V]):
    def __init__(self) -> None:
        self.raiz: NoAVL[K, V] | None = None
        self._tamanho = 0
        # Contadores didáticos: quantas rotações de cada tipo ocorreram.
        self.rotacoes: dict[str, int] = {"esquerda": 0, "direita": 0, "dupla_esq_dir": 0, "dupla_dir_esq": 0}

    # ------------------------------------------------------------------
    # Altura e fator de balanceamento
    # ------------------------------------------------------------------
    @staticmethod
    def altura_no(no: NoAVL | None) -> int:
        return 0 if no is None else no.altura

    def altura(self) -> int:
        """Altura da árvore inteira. O(1) (fica armazenada na raiz)."""
        return self.altura_no(self.raiz)

    @classmethod
    def fator_balanceamento(cls, no: NoAVL | None) -> int:
        if no is None:
            return 0
        return cls.altura_no(no.esquerda) - cls.altura_no(no.direita)

    @classmethod
    def _atualizar_altura(cls, no: NoAVL) -> None:
        no.altura = 1 + max(cls.altura_no(no.esquerda), cls.altura_no(no.direita))

    # ------------------------------------------------------------------
    # Rotações (todas O(1): só trocam ponteiros e recalculam 2 alturas)
    # ------------------------------------------------------------------
    def rotacionar_direita(self, z: NoAVL[K, V]) -> NoAVL[K, V]:
        """Rotação simples à direita.

                z               y
               / \\            / \\
              y   T4   →     x    z
             / \\                / \\
            x   T3             T3  T4
        """
        y = z.esquerda
        if y is None:
            raise ValueError("rotação à direita exige filho esquerdo")
        t3 = y.direita
        y.direita = z
        z.esquerda = t3
        self._atualizar_altura(z)
        self._atualizar_altura(y)
        self.rotacoes["direita"] += 1
        return y

    def rotacionar_esquerda(self, z: NoAVL[K, V]) -> NoAVL[K, V]:
        """Rotação simples à esquerda (espelho da rotação à direita)."""
        y = z.direita
        if y is None:
            raise ValueError("rotação à esquerda exige filho direito")
        t2 = y.esquerda
        y.esquerda = z
        z.direita = t2
        self._atualizar_altura(z)
        self._atualizar_altura(y)
        self.rotacoes["esquerda"] += 1
        return y

    def rotacionar_esquerda_direita(self, z: NoAVL[K, V]) -> NoAVL[K, V]:
        """Rotação dupla (caso LR): esquerda no filho esquerdo, depois direita em z."""
        assert z.esquerda is not None
        z.esquerda = self.rotacionar_esquerda(z.esquerda)
        self.rotacoes["dupla_esq_dir"] += 1
        return self.rotacionar_direita(z)

    def rotacionar_direita_esquerda(self, z: NoAVL[K, V]) -> NoAVL[K, V]:
        """Rotação dupla (caso RL): direita no filho direito, depois esquerda em z."""
        assert z.direita is not None
        z.direita = self.rotacionar_direita(z.direita)
        self.rotacoes["dupla_dir_esq"] += 1
        return self.rotacionar_esquerda(z)

    def _rebalancear(self, no: NoAVL[K, V]) -> NoAVL[K, V]:
        self._atualizar_altura(no)
        fator = self.fator_balanceamento(no)
        if fator > 1:  # pesada à esquerda
            if self.fator_balanceamento(no.esquerda) < 0:
                return self.rotacionar_esquerda_direita(no)  # LR
            return self.rotacionar_direita(no)  # LL
        if fator < -1:  # pesada à direita
            if self.fator_balanceamento(no.direita) > 0:
                return self.rotacionar_direita_esquerda(no)  # RL
            return self.rotacionar_esquerda(no)  # RR
        return no

    # ------------------------------------------------------------------
    # Inserção e busca
    # ------------------------------------------------------------------
    def inserir(self, chave: K, valor: Any = None) -> bool:
        """Insere ``chave`` com ``valor``. O(log n).

        Retorna True se inseriu e False se a chave já existia (chaves são
        únicas: o valor existente NÃO é sobrescrito).
        """
        if chave is None:
            raise ValueError("chave None não é permitida")
        self._inseriu = False
        self.raiz = self._inserir(self.raiz, chave, valor)
        if self._inseriu:
            self._tamanho += 1
        return self._inseriu

    def _inserir(self, no: NoAVL[K, V] | None, chave: K, valor: Any) -> NoAVL[K, V]:
        if no is None:
            self._inseriu = True
            return NoAVL(chave, valor)
        if chave < no.chave:  # type: ignore[operator]
            no.esquerda = self._inserir(no.esquerda, chave, valor)
        elif no.chave < chave:  # type: ignore[operator]
            no.direita = self._inserir(no.direita, chave, valor)
        else:
            return no  # duplicata: nada muda
        return self._rebalancear(no)

    def _buscar_no(self, chave: K) -> NoAVL[K, V] | None:
        atual = self.raiz
        while atual is not None:
            if chave < atual.chave:  # type: ignore[operator]
                atual = atual.esquerda
            elif atual.chave < chave:  # type: ignore[operator]
                atual = atual.direita
            else:
                return atual
        return None

    def contem(self, chave: K) -> bool:
        """True se a chave está na árvore. O(log n)."""
        return self._buscar_no(chave) is not None

    def buscar(self, chave: K) -> V:
        """Valor associado à chave. O(log n). KeyError se não existir."""
        no = self._buscar_no(chave)
        if no is None:
            raise KeyError(chave)
        return no.valor

    def __contains__(self, chave: object) -> bool:
        return self.contem(chave)  # type: ignore[arg-type]

    def __len__(self) -> int:
        return self._tamanho

    def esta_vazia(self) -> bool:
        return self._tamanho == 0

    # ------------------------------------------------------------------
    # Percurso e verificação
    # ------------------------------------------------------------------
    def em_ordem(self) -> Iterator[tuple[K, V]]:
        """Percurso em ordem (chaves crescentes), iterativo com a Pilha do projeto."""
        pilha: Pilha[NoAVL[K, V]] = Pilha()
        atual = self.raiz
        while not pilha.esta_vazia() or atual is not None:
            while atual is not None:
                pilha.empilhar(atual)
                atual = atual.esquerda
            atual = pilha.desempilhar()
            yield atual.chave, atual.valor
            atual = atual.direita

    def chaves(self) -> list[K]:
        return [chave for chave, _ in self.em_ordem()]

    def esta_balanceada(self) -> bool:
        """Verifica (do zero) a propriedade AVL, a ordenação e as alturas armazenadas."""

        def verificar(no: NoAVL | None, minimo: Any, maximo: Any) -> int:
            if no is None:
                return 0
            if minimo is not None and not (minimo < no.chave):
                raise AssertionError("ordem de BST violada")
            if maximo is not None and not (no.chave < maximo):
                raise AssertionError("ordem de BST violada")
            h_esq = verificar(no.esquerda, minimo, no.chave)
            h_dir = verificar(no.direita, no.chave, maximo)
            if abs(h_esq - h_dir) > 1:
                raise AssertionError(f"nó {no.chave!r} desbalanceado")
            altura = 1 + max(h_esq, h_dir)
            if altura != no.altura:
                raise AssertionError(f"altura armazenada incorreta em {no.chave!r}")
            return altura

        try:
            verificar(self.raiz, None, None)
        except AssertionError:
            return False
        return True
