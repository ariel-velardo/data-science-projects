"""Motor de busca em espaço de estados: BFS (fila) e DFS (pilha).

O motor é GENÉRICO: recebe um estado inicial e três funções —
``sucessores(estado)``, ``objetivo(estado)`` e ``chave(estado)`` — e não sabe
nada sobre mapas ou pistas. Assim ele poderá ser reaproveitado nas fases
3, 4 e 5 com outras regras. ``resolver_mapa`` liga o motor às regras de
``veridia.jogo.regras``.

Controle de visitados com ÁRVORE AVL:
    chave canônica do estado  →  (chave do estado pai, ação que levou até ele, estado)

A mesma AVL serve para duas coisas:
1. impedir que um estado já visto seja processado de novo (busca O(log V));
2. reconstruir o caminho, seguindo os ponteiros de pai até o estado inicial.

Complexidade (V = estados alcançáveis, E = transições entre eles):
    BFS e DFS visitam cada estado no máximo uma vez → O(V + E) expansões,
    cada uma com consulta/inserção na AVL O(log V): O((V + E) log V) no total.

Três buscas estão disponíveis:
- ``busca_largura``                BFS com a Fila do projeto;
- ``busca_profundidade``           DFS iterativa com a Pilha do projeto;
- ``busca_profundidade_recursiva`` DFS recursiva (demonstração de recursão).
As duas DFS visitam os estados exatamente na mesma ordem.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Iterable, TypeVar

from veridia.estruturas.arvore_avl import ArvoreAVL
from veridia.estruturas.fila import Fila
from veridia.estruturas.pilha import Pilha
from veridia.jogo import regras
from veridia.modelos.mapa import Mapa

E = TypeVar("E")  # tipo do estado
A = TypeVar("A")  # tipo da ação

FuncaoSucessores = Callable[[Any], Iterable[tuple[Any, Any]]]


@dataclass
class ResultadoBusca(Generic[E, A]):
    algoritmo: str
    encontrou: bool
    estado_final: E | None = None
    acoes: list[A] = field(default_factory=list)          # caminho como sequência de ações
    estados_caminho: list[E] = field(default_factory=list)  # estados do início ao fim
    ordem_visita: list[E] = field(default_factory=list)     # ordem em que os estados foram EXPANDIDOS
    estados_explorados: int = 0      # estados retirados da fronteira e expandidos
    estados_gerados: int = 0         # sucessores produzidos (incluindo repetidos)
    repetidos_descartados: int = 0   # sucessores ignorados por já estarem na AVL
    visitados: ArvoreAVL | None = None
    tempo_segundos: float = 0.0      # duração da busca (time.perf_counter)
    tamanho_max_fronteira: int = 0   # maior fila (BFS), maior pilha (DFS) ou profundidade máxima (recursiva)
    rastro_recursao: list["PassoRecursao"] = field(default_factory=list)  # só na DFS recursiva

    @property
    def comprimento(self) -> int:
        return len(self.acoes)

    @property
    def custo_caminho(self) -> int:
        """Soma dos custos das ações (energia consumida no mapa). Ação sem ``custo`` vale 1."""
        return sum(getattr(acao, "custo", 1) for acao in self.acoes)

    def arvore_busca(self) -> list[tuple[Any, Any, Any]]:
        """Relações pai -> filho da árvore de busca: lista de (chave_pai, chave_filho, ação).

        Derivada da AVL de visitados (cada estado guarda seu pai), sem memória
        extra durante a busca. A raiz (estado inicial) não tem pai e não
        aparece como filho. Ordem: crescente pela chave do filho.
        """
        if self.visitados is None:
            return []
        return [
            (chave_pai, chave_filho, acao)
            for chave_filho, (chave_pai, acao, _estado) in self.visitados.em_ordem()
            if chave_pai is not None
        ]


@dataclass(frozen=True)
class PassoRecursao:
    """Um evento do rastreamento da DFS recursiva.

    Eventos:
      "chamada"            entrou em explorar(estado) pela primeira vez;
      "caso_base_repetido" estado já visitado: retorna fracasso sem expandir;
      "caso_base_objetivo" estado é objetivo: retorna sucesso;
      "retorno_sucesso"    um filho achou o objetivo: propaga o sucesso para cima;
      "sem_saida"          todos os filhos falharam: retorna fracasso (backtracking).
    """

    profundidade: int
    evento: str
    estado: Any


def _reconstruir_caminho(visitados: ArvoreAVL, chave_final: Any) -> tuple[list, list]:
    """Segue os ponteiros de pai na AVL, do estado final até o inicial. O(L log V)."""
    acoes: list = []
    estados: list = []
    chave = chave_final
    while chave is not None:
        chave_pai, acao, estado = visitados.buscar(chave)
        estados.append(estado)
        if acao is not None:
            acoes.append(acao)
        chave = chave_pai
    acoes.reverse()
    estados.reverse()
    return acoes, estados


def busca_largura(
    inicial: E,
    sucessores: FuncaoSucessores,
    objetivo: Callable[[E], bool],
    chave: Callable[[E], Any] = lambda e: e.chave(),
) -> ResultadoBusca:
    """BFS: explora em camadas usando FILA. Encontra o caminho com MENOS AÇÕES.

    O estado é marcado como visitado ao ENTRAR na fila, para que nunca haja
    duas cópias do mesmo estado na fronteira.
    """
    inicio = time.perf_counter()
    visitados: ArvoreAVL = ArvoreAVL()
    resultado = ResultadoBusca(algoritmo="BFS", encontrou=False, visitados=visitados)

    visitados.inserir(chave(inicial), (None, None, inicial))
    fila: Fila = Fila()
    fila.enfileirar(inicial)

    while not fila.esta_vazia():
        resultado.tamanho_max_fronteira = max(resultado.tamanho_max_fronteira, len(fila))
        atual = fila.desenfileirar()
        chave_atual = chave(atual)
        resultado.estados_explorados += 1
        resultado.ordem_visita.append(atual)
        if objetivo(atual):
            resultado.encontrou = True
            resultado.estado_final = atual
            resultado.acoes, resultado.estados_caminho = _reconstruir_caminho(visitados, chave_atual)
            break
        for acao, proximo in sucessores(atual):
            resultado.estados_gerados += 1
            chave_proximo = chave(proximo)
            if visitados.inserir(chave_proximo, (chave_atual, acao, proximo)):
                fila.enfileirar(proximo)
            else:
                resultado.repetidos_descartados += 1
    resultado.tempo_segundos = time.perf_counter() - inicio
    return resultado


def busca_profundidade(
    inicial: E,
    sucessores: FuncaoSucessores,
    objetivo: Callable[[E], bool],
    chave: Callable[[E], Any] = lambda e: e.chave(),
) -> ResultadoBusca:
    """DFS iterativa com PILHA. Encontra UM caminho (não necessariamente o mais curto).

    A pilha guarda trios (estado, chave do pai, ação). O estado só é marcado
    como visitado ao SAIR da pilha — isso reproduz a ordem da DFS recursiva e
    garante que o pai registrado é o do ramo que realmente o expandiu.
    Sucessores são empilhados em ordem inversa para que o primeiro vizinho
    da lista de adjacência seja explorado primeiro.
    """
    inicio = time.perf_counter()
    visitados: ArvoreAVL = ArvoreAVL()
    resultado = ResultadoBusca(algoritmo="DFS", encontrou=False, visitados=visitados)

    pilha: Pilha = Pilha()
    pilha.empilhar((inicial, None, None))

    while not pilha.esta_vazia():
        resultado.tamanho_max_fronteira = max(resultado.tamanho_max_fronteira, len(pilha))
        atual, chave_pai, acao = pilha.desempilhar()
        chave_atual = chave(atual)
        if not visitados.inserir(chave_atual, (chave_pai, acao, atual)):
            resultado.repetidos_descartados += 1
            continue
        resultado.estados_explorados += 1
        resultado.ordem_visita.append(atual)
        if objetivo(atual):
            resultado.encontrou = True
            resultado.estado_final = atual
            resultado.acoes, resultado.estados_caminho = _reconstruir_caminho(visitados, chave_atual)
            break
        filhos = list(sucessores(atual))
        for acao_filho, filho in reversed(filhos):
            resultado.estados_gerados += 1
            if visitados.contem(chave(filho)):
                resultado.repetidos_descartados += 1
                continue
            pilha.empilhar((filho, chave_atual, acao_filho))
    resultado.tempo_segundos = time.perf_counter() - inicio
    return resultado


def busca_profundidade_recursiva(
    inicial: E,
    sucessores: FuncaoSucessores,
    objetivo: Callable[[E], bool],
    chave: Callable[[E], Any] = lambda e: e.chave(),
) -> ResultadoBusca:
    """DFS RECURSIVA — demonstração explícita de recursão.

    A função interna ``explorar(estado)`` resolve o problema "existe caminho
    deste estado até um objetivo?" reduzindo-o ao MESMO problema para cada
    sucessor:

    - CASO-BASE 1 (repetido): o estado já está na AVL -> devolve fracasso sem
      expandir. Cada chamada que passa daqui insere um estado NOVO; como o
      espaço de estados é finito, a recursão sempre termina.
    - CASO-BASE 2 (objetivo): o estado satisfaz ``objetivo`` -> devolve sucesso.
    - PASSO RECURSIVO (redução): chama ``explorar`` para cada sucessor.
    - CONDIÇÃO DE RETORNO: o primeiro sucessor que devolve sucesso faz a
      chamada atual devolver sucesso imediatamente (propagação até a raiz).
      Se todos falharem, devolve fracasso e a chamada anterior tenta o
      próximo irmão (backtracking).

    A pilha de chamadas do Python faz o papel da Pilha explícita da DFS
    iterativa; por isso as duas visitam os estados na MESMA ordem.
    ``tamanho_max_fronteira`` registra a profundidade máxima da recursão e
    ``rastro_recursao`` cada chamada/retorno, para demonstrar o rastreamento.
    Limite prático: a profundidade não pode passar do limite de recursão do
    Python (~1000), folgado para os mapas do jogo (cerca de 20 níveis).
    """
    inicio = time.perf_counter()
    visitados: ArvoreAVL = ArvoreAVL()
    resultado = ResultadoBusca(algoritmo="DFS_RECURSIVA", encontrou=False, visitados=visitados)
    rastro = resultado.rastro_recursao

    def explorar(estado: Any, chave_pai: Any, acao: Any, profundidade: int) -> Any:
        """Devolve a chave do estado objetivo encontrado, ou None (fracasso)."""
        chave_atual = chave(estado)
        if not visitados.inserir(chave_atual, (chave_pai, acao, estado)):
            resultado.repetidos_descartados += 1
            rastro.append(PassoRecursao(profundidade, "caso_base_repetido", estado))
            return None
        resultado.estados_explorados += 1
        resultado.ordem_visita.append(estado)
        resultado.tamanho_max_fronteira = max(resultado.tamanho_max_fronteira, profundidade + 1)
        rastro.append(PassoRecursao(profundidade, "chamada", estado))
        if objetivo(estado):
            rastro.append(PassoRecursao(profundidade, "caso_base_objetivo", estado))
            return chave_atual
        for acao_filho, filho in sucessores(estado):
            resultado.estados_gerados += 1
            encontrado = explorar(filho, chave_atual, acao_filho, profundidade + 1)
            if encontrado is not None:
                rastro.append(PassoRecursao(profundidade, "retorno_sucesso", estado))
                return encontrado
        rastro.append(PassoRecursao(profundidade, "sem_saida", estado))
        return None

    chave_final = explorar(inicial, None, None, 0)
    if chave_final is not None:
        resultado.encontrou = True
        resultado.acoes, resultado.estados_caminho = _reconstruir_caminho(visitados, chave_final)
        resultado.estado_final = resultado.estados_caminho[-1]
    resultado.tempo_segundos = time.perf_counter() - inicio
    return resultado


BUSCAS: dict[str, Callable[..., ResultadoBusca]] = {
    "BFS": busca_largura,
    "DFS": busca_profundidade,
    "DFS_RECURSIVA": busca_profundidade_recursiva,
}


def resolver_mapa(mapa: Mapa, algoritmo: str = "BFS", inicial=None) -> ResultadoBusca:
    """Resolve uma fase usando as MESMAS regras do modo manual.

    ``algoritmo``: "BFS", "DFS" (iterativa) ou "DFS_RECURSIVA".
    """
    if inicial is None:
        inicial = regras.estado_inicial(mapa)
    if algoritmo.upper() not in BUSCAS:
        raise ValueError(f"algoritmo desconhecido: {algoritmo!r}. Opções: {sorted(BUSCAS)}.")
    return BUSCAS[algoritmo.upper()](
        inicial,
        sucessores=lambda estado: regras.gerar_sucessores(mapa, estado),
        objetivo=lambda estado: regras.verificar_vitoria(mapa, estado),
    )
