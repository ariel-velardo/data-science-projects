# Guia Técnico — VERÍDIA, O Enigma da Urna

Material de estudo do projeto: o que foi implementado, como cada peça
funciona, por que foi feita assim e quanto custa (complexidade).

- Seções 1 a 9: fundação técnica (Rodada 1) — estruturas, ordenação, regras,
  BFS/DFS — atualizadas com a DFS recursiva e as novas métricas (6.7 e 6.8).
- Seções 10 a 13: motor das cinco fases (Rodada 2) — sessão, fases,
  auditoria final e exportação.
- Seção 14: interface NiceGUI (Rodada 3) — telas, sessões por navegador,
  visualizações e testes de interface.

Notação: *n* = número de elementos; *V* = vértices (ou estados); *E* =
arestas (ou transições); *L* = comprimento do caminho.

---

## 1. Visão geral: como os módulos se conectam

```
           dados/                       modelos/
  gerador_registros ──► RegistroVotacao      EstadoJogo ◄─── chave() canônica
  mapa_veridia ───────► Mapa (Grafo + Vertices + Evidencias)
                               │
                               ▼
  estruturas/   ListaLigada ─► Grafo (lista de adjacência)
                Fila ────────────────┐
                Pilha ───────────────┤
                ArvoreAVL ───────────┤
                                     ▼
  jogo/regras.py  ──(sucessores, vitória)──►  busca/solver.py (BFS, DFS)
        ▲                                            │
        └──── futuro modo manual (NiceGUI) ──────────┘ mesma lógica

  algoritmos/ordenacao.py ◄── RegistroVotacao (fases de auditoria de registros)

  jogo/sessao.py (progressão, selos, histórico)
        │ executar("ação", ...)
        ▼
  fases/  fase1_arquivo ── ordenacao.py + AVL (integridade)
          fase2_triagem ── Fila + Pilha + ListaLigada (+ BFS para sugerir solução)
          fase3_mapa ───── regras.py + solver.py
          fase4_cofre ──── ArvoreAVL + EstadoJogo.chave()
          fase5_auditoria ─ fases 1–4 + solver + ordenação (relatório)
```

Princípios:

1. **O mapa é estático; o estado muda.** `Mapa` descreve a fase (locais,
   conexões, portas, pistas, destino). `EstadoJogo` descreve o jogador em um
   instante (posição, pistas, portas abertas, energia).
2. **Regras puras em um só lugar.** `jogo/regras.py` recebe um estado e
   devolve um novo estado, sem alterar o original. O solver pode então
   "experimentar futuros" sem efeitos colaterais, e o modo manual usará
   exatamente as mesmas funções.
3. **Motor de busca genérico.** `busca/solver.py` não conhece mapas: recebe
   funções `sucessores`, `objetivo` e `chave`. Na Rodada 2 ele passou a
   resolver também a Fase 2 (triagem) sem nenhuma alteração.
4. **Progressão separada dos enigmas.** A `SessaoJogo` só conhece selos,
   fase atual e histórico; cada fase conhece só o próprio enigma.

---

## 2. Modelos do domínio (`veridia/modelos/`)

| Modelo | Campos | Observações |
|---|---|---|
| `RegistroVotacao` | id, zona, seção, código de opção, horário, status | Imutável (`frozen`). `validar_registro` / `validar_registros` (inclui unicidade de id). |
| `Evidencia` | id, tipo, descrição, estado | `com_estado()` devolve uma cópia; o id único serve de chave na AVL. |
| `EstadoJogo` | posição, pistas, portas liberadas, energia | Imutável e hashable. `chave()` dá a representação canônica. |
| `Mapa` | vértices, grafo, evidências, início, destino, pistas necessárias, energia inicial | `validar_mapa` checa a consistência interna. |

### 2.1 Representação canônica do estado

```python
chave = (posicao, tuple(sorted(pistas)), tuple(sorted(portas_liberadas)), energia)
```

- **Por que ordenar?** Conjuntos não têm ordem; `{"a","b"}` e `{"b","a"}` são
  o mesmo conjunto. Ordenando, estados equivalentes geram a mesma tupla
  independentemente da ordem de coleta das pistas.
- **Por que tupla?** Tuplas de strings/inteiros são comparáveis com `<`
  (ordem lexicográfica). A AVL precisa disso para decidir esquerda/direita.
- **Por que a energia entra na chave?** Dois estados iguais exceto pela
  energia *não* são equivalentes: o de menor energia pode não conseguir
  terminar o mesmo caminho. Retirar a energia poderia fazer a busca
  descartar o único estado que leva à vitória.
  *Custo:* a DFS pode "oscilar" entre dois locais (cada ida e volta gera
  estado novo, com menos energia). Ver pendências na seção 9.

### 2.2 Geração reproduzível

`gerar_registros(quantidade, seed=2026)` usa `random.Random(seed)`, um
gerador **próprio** — não o estado global de `random`. A mesma seed gera os
mesmos registros sempre, em qualquer ordem de execução dos testes.

---

## 3. Estruturas de dados (`veridia/estruturas/`)

Todas foram implementadas do zero, com nós encadeados. Operações inválidas
em estrutura vazia levantam `EstruturaVaziaError` (subclasse de `IndexError`).

### 3.1 Fila FIFO — `fila.py`

Nós encadeados com ponteiros para **início** e **fim**.

| Operação | Nome no código (alias) | Custo |
|---|---|---|
| enqueue | `enfileirar` | O(1): liga o novo nó após o fim |
| dequeue | `desenfileirar` | O(1): avança o início |
| front/peek | `frente` | O(1) |
| isEmpty | `esta_vazia` | O(1) |

*Por que não `list.pop(0)`?* Removeria do início de um vetor, deslocando
todos os elementos: O(n). **Papel no jogo:** fronteira da BFS.

### 3.2 Pilha LIFO — `pilha.py`

Nós encadeados; o topo é o primeiro nó.

| Operação | Nome no código (alias) | Custo |
|---|---|---|
| push | `empilhar` | O(1) |
| pop | `desempilhar` | O(1) |
| peek/top | `topo` | O(1) |
| isEmpty | `esta_vazia` | O(1) |

**Papel no jogo:** fronteira da DFS, percurso em ordem da AVL e, no futuro,
"desfazer" no modo manual.

### 3.3 Lista duplamente ligada — `lista_ligada.py`

**Escolha: duplamente ligada.** Cada nó aponta para o anterior e o próximo,
e a lista guarda início e fim. Assim, remover do **fim** é O(1) (na
simplesmente ligada seria O(n), pois é preciso achar o penúltimo) e é
possível percorrer nos dois sentidos. O custo é um ponteiro extra por nó.

| Operação | Custo |
|---|---|
| `inserir_inicio`, `inserir_fim`, `remover_inicio`, `remover_fim` | O(1) |
| `primeiro`, `ultimo` (consulta ao início e ao fim) | O(1) |
| `inserir_em(i)`, `remover_em(i)`, `obter(i)` | O(n) (caminha pelo lado mais próximo) |
| `buscar(valor)`, `remover(valor)`, `buscar_por(predicado)` | O(n) |
| `percorrer`, `percorrer_reverso` | O(n) |

**Papel no jogo:** cada vértice do grafo guarda suas arestas em uma
`ListaLigada` (lista de adjacência). No futuro, pode guardar o histórico de
ações e o inventário de evidências.

### 3.4 Árvore AVL — `arvore_avl.py`

Árvore binária de busca em que, para **todo** nó,
`|altura(esquerda) − altura(direita)| ≤ 1`. Isso limita a altura a cerca de
1,44·log₂ n, então busca e inserção custam **O(log n) no pior caso**. Uma BST
comum degenera em lista (altura n) quando as chaves chegam ordenadas; o
teste `test_insercao_ordenada_mantem_altura_logaritmica` insere 0..1022 em
ordem e verifica altura 10.

- **Altura:** guardada em cada nó (folha = 1, vazio = 0), recalculada na
  volta da recursão: `1 + max(alt_esq, alt_dir)`.
- **Fator de balanceamento:** `altura(esq) − altura(dir)`.
- **Rebalanceamento** (nó `z` com |fator| > 1 após inserir):

| Caso | Situação | Correção |
|---|---|---|
| LL | fator(z) > 1 e fator(z.esq) ≥ 0 | rotação simples à **direita** em z |
| RR | fator(z) < −1 e fator(z.dir) ≤ 0 | rotação simples à **esquerda** em z |
| LR | fator(z) > 1 e fator(z.esq) < 0 | esquerda em z.esq, depois direita em z |
| RL | fator(z) < −1 e fator(z.dir) > 0 | direita em z.dir, depois esquerda em z |

Rotação à direita (a esquerda é o espelho):

```
        z               y
       / \             / \
      y   T4   →      x   z
     / \                 / \
    x   T3              T3  T4
```

Cada rotação é O(1): troca três ponteiros e recalcula duas alturas.

- **Chaves únicas:** `inserir(chave, valor)` devolve `False` se a chave já
  existir e **não** sobrescreve o valor. É exatamente o teste "já visitei
  este estado?" do solver.
- `rotacoes` conta as rotações realizadas. As duplas também incrementam os
  contadores das simples que as compõem.
- `esta_balanceada()` reverifica do zero a ordem de BST, a propriedade AVL
  e as alturas armazenadas; é usada nos testes.

**Papel no jogo:** conjunto de estados visitados do solver (chave = chave
canônica do estado; valor = pai, ação e estado) e índice de evidências por
id.

### 3.5 Grafo — `grafo.py`

Lista de adjacência: `dict[vértice → ListaLigada[Aresta]]`. Cada `Aresta`
tem origem, destino, custo, `porta` opcional e `pistas_exigidas`. Nas
conexões bidirecionais, os dois sentidos compartilham o mesmo id de porta.

| | Lista de adjacência | Matriz de adjacência |
|---|---|---|
| Memória | O(V + E) | O(V²) |
| Percorrer vizinhos de v | O(grau(v)) | O(V) |
| "Existe aresta u→v?" | O(grau(u)) | O(1) |

O mapa é esparso (9 vértices, 12 conexões) e BFS/DFS percorrem vizinhos o
tempo todo, então a lista de adjacência é a escolha natural.

---

## 4. Algoritmos de ordenação (`veridia/algoritmos/ordenacao.py`)

**Papel no jogo:** organizar os registros de votação fictícios (por exemplo
por zona → seção → horário) para que o jogador detecte anomalias, como
horários fora da janela, duplicidades e sequências estranhas.

Interface comum: `ordenado, metricas = merge_sort(registros, chave=..., decrescente=False)`.

- A entrada **nunca é modificada**: o algoritmo trabalha em uma cópia. Os
  registros são imutáveis, então só as referências mudam de posição.
- **Chave composta:** `CRITERIOS["zona_secao_horario"] = lambda r: (r.zona, r.secao, r.horario)`.
  O Python compara tuplas lexicograficamente: compara a zona e, em caso de
  empate, a seção; persistindo o empate, o horário.
- **Métricas:** `comparacoes` (cada comparação entre chaves), `movimentacoes`
  (cada escrita de elemento no vetor ou no auxiliar; uma troca conta 2) e
  `tempo_segundos` (`perf_counter`, inclui o custo da instrumentação).

| Algoritmo | Melhor | Médio | Pior | Memória extra | Estável? |
|---|---|---|---|---|---|
| Bubble Sort | O(n) (com parada antecipada) | O(n²) | O(n²) | O(1) | Sim |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Sim |
| Quick Sort | O(n log n) | O(n log n) | O(n²) (raro) | O(log n) (pilha) | Não |

Decisões de implementação:

- **Bubble Sort:** troca só se o da direita for *estritamente* menor (o que o
  torna estável) e para quando uma passada inteira não faz trocas. Com vetor
  ordenado, isso dá n−1 comparações e 0 movimentações (testado).
- **Merge Sort:** top-down. Em empate, pega da metade esquerda (estável).
  Usa um vetor auxiliar alocado uma única vez.
- **Quick Sort:**
  - *pivô por mediana de três* (início, meio, fim): evita o pior caso O(n²)
    em entrada já ordenada ou invertida;
  - *partição de Hoare:* elementos iguais ao pivô param os dois índices e
    são divididos entre os lados, então muitas chaves repetidas não
    desequilibram a partição;
  - *recursão só no lado menor* (laço no maior): profundidade O(log n), sem
    estourar o limite de recursão do Python. Há um teste com 20.000
    elementos já ordenados.
  - Uma primeira versão usava partição em 3 vias (Dijkstra). Ela foi
    trocada porque gerava quase 3× mais comparações em entrada ordenada.

Experimento (`python -m veridia.demos.experimento_ordenacao`, seed 2026,
chave zona/seção/horário, n = 1000):

| cenário | algoritmo | comparações | movimentações |
|---|---|---|---|
| aleatório | bubble | 497.222 | 515.162 |
| aleatório | merge | 8.686 | 19.283 |
| aleatório | quick | 15.146 | 5.292 |
| ordenado | bubble | 999 | 0 |
| ordenado | merge | 4.932 | 14.908 |
| ordenado | quick | 13.975 | 4 |
| inverso | bubble | 499.500 | 998.996 |
| inverso | merge | 5.045 | 19.951 |
| inverso | quick | 13.976 | 1.008 |

Leitura rápida: o Bubble é quadrático (≈ n²/2 comparações), exceto no
melhor caso. Merge e Quick ficam na ordem de n log₂ n ≈ 10.000. O Merge faz
menos comparações e o Quick bem menos movimentações, porque só troca o que
está fora do lugar. Os tempos variam de máquina para máquina; comparações e
movimentações são determinísticas.

---

## 5. Regras do jogo (`veridia/jogo/regras.py`)

1. O jogador começa em `mapa.inicio` com `mapa.energia_inicial`.
2. Cada movimento percorre **uma** conexão e gasta o custo dela em energia.
3. Uma porta exige suas pistas **na primeira passagem**. Depois fica em
   `portas_liberadas` e não exige mais nada.
4. Ao chegar a um local com pista, ela é **coletada automaticamente**.
5. **Vitória:** estar no destino com todas as `pistas_necessarias`.

Funções: `estado_inicial`, `validar_movimento` (devolve `(permitido,
mensagem)`, útil para a interface explicar o bloqueio), `mover` (modo
manual; levanta `MovimentoInvalidoError`), `coletar_pista`,
`gerar_sucessores` (O(grau)), `verificar_vitoria` e `reproduzir_caminho`
(reexecuta uma solução, usada nos testes).

### 5.1 O mapa de Verídia (`dados/mapa_veridia.py`)

9 locais e 12 conexões. As bifurcações estão na Praça, na Escola, no
Mercado e na Ponte. Há 4 portas:

| Conexão | Custo | Porta | Exige |
|---|---|---|---|
| Praça – Biblioteca | 2 | | |
| Praça – Escola | 1 | | |
| Praça – Mercado | 1 | | |
| Biblioteca – Cartório | 2 | | |
| Escola – Cartório | 3 | | |
| Escola – Arquivo | 2 | porta_arquivo | lacre_rompido |
| Mercado – Torre | 3 | | |
| Mercado – Ponte | 2 | | |
| Torre – Ponte | 1 | | |
| Arquivo – Ponte | 2 | passagem_ponte | lacre_rompido |
| Ponte – Tribunal | 2 | portao_tribunal | log_urna, registro_horario |
| Cartório – Tribunal | 4 | porta_lateral | ata_secao, log_urna, registro_horario |

Pistas: Biblioteca → `ata_secao`; Cartório → `lacre_rompido`; Arquivo →
`log_urna`; Torre → `registro_horario`; Mercado → `testemunho_feirante`
(distrator, não exigido). A vitória exige estar no Tribunal com
`ata_secao`, `log_urna` e `registro_horario`.

---

## 6. Busca em espaço de estados (`veridia/busca/solver.py`)

### 6.1 Por que buscar sobre *estados* e não sobre *vértices*?

Se a busca marcasse apenas "já passei pela Praça", nunca voltaria à Praça
depois de pegar uma pista, e esse retorno pode ser necessário para abrir
uma porta. O grafo de **estados** tem um nó para cada combinação
(posição, pistas, portas, energia), e suas arestas são os movimentos
válidos gerados por `gerar_sucessores`. BFS e DFS percorrem esse grafo
implícito, gerado sob demanda.

### 6.2 BFS — Busca em Largura (com `Fila`)

```
marcar inicial como visitado; enfileirar inicial
enquanto fila não vazia:
    atual = desenfileirar
    se objetivo(atual): reconstruir caminho e parar
    para cada (ação, próximo) em sucessores(atual):
        se AVL.inserir(chave(próximo), (chave(atual), ação, próximo)):  # era inédito
            enfileirar próximo
```

- Explora em **camadas** (0 movimentos, 1 movimento, 2, …). Por isso, o
  primeiro estado vitorioso desenfileirado está no caminho com **menos
  movimentos**. O teste `test_bfs_encontra_caminho_com_menos_movimentos`
  confirma isso por enumeração exaustiva das camadas anteriores.
- Marca como visitado **ao enfileirar**, o que evita duplicatas na fila.
- **Atenção:** "menos movimentos" não é "menos energia". Para minimizar
  custo seria preciso Dijkstra / custo uniforme (fila de prioridade).

### 6.3 DFS — Busca em Profundidade (com `Pilha`)

- Empilha `(estado, chave_pai, ação)` e marca como visitado **ao
  desempilhar**. Isso reproduz a ordem da DFS recursiva e garante que o pai
  registrado é o do ramo que de fato expandiu o estado.
- Empilha os sucessores em ordem inversa, para que o primeiro vizinho da
  lista de adjacência seja explorado primeiro.
- Encontra **um** caminho válido, não necessariamente o mais curto (no mapa:
  BFS = 8 movimentos, DFS = 10).

### 6.4 O papel da AVL no solver

Uma única AVL guarda `chave canônica → (chave do pai, ação, estado)` e
cumpre três funções:

1. **Visitados:** `inserir` devolve `False` para um estado repetido, que é
   então descartado (`repetidos_descartados`). Custo O(log V) em vez do O(V)
   de procurar em uma lista.
2. **Distinção correta:** a mesma posição com pistas diferentes gera chaves
   diferentes (teste `test_avl_distingue_mesma_posicao_com_pistas_diferentes`).
3. **Reconstrução do caminho:** a partir do estado final, segue `chave do pai`
   até a raiz (pai `None`) e inverte a lista: O(L log V).

### 6.5 Métricas expostas por `ResultadoBusca`

`acoes`, `estados_caminho`, `ordem_visita` (ordem de expansão),
`estados_explorados`, `estados_gerados`, `repetidos_descartados` e
`visitados` (a própria AVL, para inspecionar a altura e o balanceamento).

Resultado no mapa padrão (energia 18):

| | movimentos | explorados | gerados | repetidos | AVL (n / altura) |
|---|---|---|---|---|---|
| BFS | 8 | 308 | 703 | 279 | 425 / 11 |
| DFS | 10 | 188 | 331 | 139 | 188 / 9 |

Com energia 14 não há solução (o caminho mais barato custa 15). As duas
buscas esgotam o espaço alcançável e relatam isso.

### 6.6 Complexidade

Seja V o número de estados alcançáveis e E o número de transições:

- cada estado é expandido no máximo uma vez, e cada transição é gerada uma
  vez por expansão: O(V + E) operações de fila/pilha (O(1) cada);
- cada transição consulta ou insere na AVL: O(log V);
- **total: O((V + E) · log V)** de tempo, tratando a comparação de chaves
  como custo constante. A AVL e os registros por estado usam O(V).
  A DFS marca na retirada e pode manter duplicatas pendentes; com fronteira,
  sucessores materializados e rastro, o limite conservador de memória total
  é O(V + E). A composição da chave também custa mais quando há muitas pistas.

O próprio V pode ser grande: no pior caso é |vértices| × 2^|pistas| ×
2^|portas| × (energia+1). Esse é o motivo de mapas pequenos e de, no
futuro, regras de poda.

### 6.7 DFS recursiva — `busca_profundidade_recursiva`

A demonstração de recursão exigida pelo enunciado. A função interna
`explorar(estado)` responde: "existe caminho deste estado até o objetivo?"

```
explorar(estado, pai, ação, profundidade):
    se AVL.inserir(chave(estado), (pai, ação, estado)) falhar:   # CASO-BASE 1: repetido
        devolve FRACASSO
    se objetivo(estado):                                         # CASO-BASE 2: objetivo
        devolve SUCESSO
    para cada (ação_filho, filho) em sucessores(estado):         # PASSO RECURSIVO (redução)
        se explorar(filho, chave(estado), ação_filho, profundidade+1) = SUCESSO:
            devolve SUCESSO                                      # CONDIÇÃO DE RETORNO (propaga)
    devolve FRACASSO                                             # sem saída → backtracking
```

- **Redução do problema:** cada chamada que passa do caso-base 1 insere um
  estado NOVO na AVL. Como o espaço de estados é finito, o número de
  chamadas "úteis" é no máximo V: a recursão sempre termina.
- **Pilha implícita:** a pilha de chamadas do Python faz o papel da `Pilha`
  da DFS iterativa. Por isso as duas visitam os estados **na mesma ordem**
  e acham o mesmo caminho (teste `test_recursiva_e_iterativa_visitam_na_mesma_ordem_no_mapa`).
- **Rastreamento:** `rastro_recursao` registra cada evento
  (`chamada`, `caso_base_repetido`, `caso_base_objetivo`, `retorno_sucesso`,
  `sem_saida`) com a profundidade. O teste
  `test_recursiva_em_grafo_pequeno_com_rastro` confere o rastro completo em
  um grafo de 5 vértices, e `python -m veridia.demos.demo_fases` imprime o
  início do rastro no mapa com indentação por profundidade.
- **Limite:** a profundidade não pode passar do limite de recursão do
  Python (≈ 1000). No mapa, a profundidade máxima é 12.
- Disponível como `resolver_mapa(mapa, "DFS_RECURSIVA")`.

### 6.8 Métricas complementares de `ResultadoBusca`

Acrescentadas na Rodada 2, com valores padrão, sem mudar a assinatura das
funções existentes:

| Métrica | Significado |
|---|---|
| `tempo_segundos` | duração da busca (`time.perf_counter`) |
| `tamanho_max_fronteira` | maior tamanho da fila (BFS), da pilha (DFS) ou profundidade máxima da recursão |
| `custo_caminho` | soma dos custos das ações = energia consumida |
| `arvore_busca()` | relações (pai, filho, ação) da árvore de busca, derivadas da AVL |
| `rastro_recursao` | eventos da DFS recursiva |

No mapa padrão: fronteira máxima BFS = 135, DFS = 15, recursiva = 12.
Custo: BFS = 15 (8 movimentos), DFS = 17 (10 movimentos). A BFS continua
minimizando **movimentos**, não energia (sem Dijkstra/A* nesta etapa).

---

## 7. Testes (`tests/`)

`python -m pytest` executa 185 testes (89 da Rodada 1, 73 da Rodada 2,
21 da Rodada 3 e 2 testes de grafo/empacotamento da Rodada 4):

| Arquivo | O que cobre |
|---|---|
| `test_modelos.py` | seed reproduzível, validações, chave canônica, mapa mínimo (≥ 8 vértices, ≥ 10 conexões, portas, bifurcações) |
| `test_fila_pilha.py` | FIFO/LIFO, vazias, duplicatas, aliases do enunciado |
| `test_lista_ligada.py` | inserções/remoções nas pontas e no meio, índices inválidos, busca com duplicatas |
| `test_arvore_avl.py` | 4 casos de rotação, duplicatas, chave inválida, inserção ordenada e aleatória, estados e evidências como chave |
| `test_grafo.py` | arestas bidirecionais/direcionadas, operações inválidas |
| `test_ordenacao.py` | vazio, 1 elemento, repetidos, ordenado, inverso, chave composta, preservação da entrada, estabilidade, métricas vs. teoria |
| `test_regras.py` | movimentos válidos/inválidos, portas, energia, coleta, vitória |
| `test_solver.py` | solução revalidada pelas regras, otimalidade da BFS, sem solução, AVL sem reprocessamento e balanceada, motor genérico |
| `test_demos.py` | as demos executam (inclui a partida completa) |
| `test_sessao.py` | selos, desbloqueio, histórico, ação inválida, reinício individual, jogo completo |
| `test_fase1_arquivo.py` | critério correto/incorreto, lote inválido, perda/duplicação/alteração, reinício |
| `test_fase2_triagem.py` | solução manual e do solver, fila/pilha vazias, pilha cheia, LIFO, desfazer, reinício |
| `test_fase3_mapa.py` | consultas, portas e bloqueios, desfazer, solução do solver aplicada manualmente |
| `test_fase4_cofre.py` | A×B diferentes, A×C equivalentes, rotação com antes/depois, buscas, reinício |
| `test_fase5_auditoria.py` | auditoria consistente/inconsistente, reinício após selo, JSON |
| `test_solver_recursivo.py` | rastro recursivo, mesma ordem da iterativa, métricas e árvore de busca |
| `test_exportacao.py` | ZIP só com arquivos permitidos, sem venv/cache/segredos |
| `test_interface_modulos.py` | sessões por navegador, SVG do mapa e da AVL a partir dos dados reais, exportação JSON/HTML, `main()` |
| `test_interface_app.py` | usuário simulado: menu, navegação, bloqueio, as cinco fases, reinício, feedback inválido, Resolver, sessões independentes, Sair |

---

## 8. Perguntas prováveis e respostas curtas

- **Por que a AVL e não um `set` do Python?** O enunciado pede a AVL. Ela
  ainda dá O(log n) garantido, mantém as chaves em ordem (percurso em ordem)
  e permite medir altura e rotações. Um `set` (tabela hash) daria O(1)
  médio, mas sem ordem e sem ser uma estrutura implementada por nós.
- **O que impede a busca de entrar em loop?** O grafo de estados tem
  ciclos (ir e voltar). A AVL de visitados impede expandir um estado duas
  vezes. Além disso, cada movimento reduz a energia, o que torna o espaço
  finito.
- **Como garanto que a solução não está "decorada"?** O mapa não contém
  caminhos. Os testes reexecutam a solução com `reproduzir_caminho` e
  verificam a vitória. Mudar a energia para 14 faz a solução desaparecer.
- **Por que BFS e DFS acham caminhos diferentes?** A BFS garante o menor
  número de movimentos. A DFS segue o primeiro vizinho até o fim e volta
  apenas quando bloqueia.
- **Onde está a recursão?** Em `busca_profundidade_recursiva` (seção 6.7):
  dois casos-base (repetido, objetivo), passo recursivo nos sucessores e
  retorno imediato no primeiro sucesso.
- **Como funciona o desfazer?** Fase 2: antes de cada movimentação, um
  retrato (fila, pilha, custódia, arquivo) é empilhado na `Pilha` de
  histórico; desfazer desempilha e restaura. Fase 3: a pilha guarda
  (movimento, estado anterior), e o estado é imutável.
- **O solver da Fase 2 não "cola" a resposta?** Ele não conhece a
  resposta: faz uma BFS em que cada sucessor é obtido chamando o próprio
  método de ação (`guardar_na_pilha`, …) em uma cópia da fase.

---

## 9. Limitações conhecidas e próximos passos

Ver a lista detalhada em [REGISTRO_IA.md](REGISTRO_IA.md#pontos-que-exigem-revisão-humana).
Resumo: não há fila de prioridade (custo mínimo de energia); a energia na
chave infla o espaço de estados (decisão mantida); a lógica das cinco fases
e a interface NiceGUI estão implementadas. A conferência técnica com o PDF
oficial foi feita na Rodada 4. O relatório acadêmico foi preparado em
`RELATORIO_ACADEMICO.md` e `.pdf`; faltam sua revisão pelo aluno e a curadoria
humana de IAG, além da demonstração e da validação prática
em navegador. Estado completo: [CONTINUIDADE.md](CONTINUIDADE.md) e
[REQUISITOS_EP.md](REQUISITOS_EP.md).

---

## 10. Sessão e progressão (`veridia/jogo/sessao.py`)

`SessaoJogo` cria as cinco fases e controla:

| Item | Como |
|---|---|
| Fase atual | `fase_atual`; `ir_para_fase(n)` só se a fase estiver liberada |
| Desbloqueio | fase N exige o selo da fase N-1 |
| Selos | conjunto `selos`; concedido quando `fase.esta_concluida()` fica verdadeiro após uma ação |
| Histórico | `ListaLigada` de `RegistroHistorico(ordem, fase, ação, argumentos, sucesso, mensagem)`; consultas não entram |
| Ações | `executar("nome", *args)`: só nomes listados em `Fase.ACOES`; argumentos errados → falha, sem exceção |
| Reinício | `reiniciar_fase(n)` reinicia só aquela fase; **selos são mantidos** |
| Conclusão | `jogo_concluido()` quando há 5 selos |

Toda ação devolve `ResultadoAcao(sucesso, mensagem, dados)`. Ações
inválidas devolvem `sucesso=False` com explicação e **não alteram** o estado.
`dados` traz o que a interface precisa exibir (métricas, árvores, caminhos).

## 11. As cinco fases (`veridia/fases/`)

### 11.1 Fase 1 — O Arquivo Embaralhado (`fase1_arquivo.py`)

- Lote de 30 registros gerado com seed e **embaralhado** (`random.Random(seed).shuffle`).
- Ações: `selecionar_algoritmo` (bubble/merge/quick), `selecionar_criterio`,
  `executar_ordenacao`, `verificar`, `carregar_lote`, `comparar_algoritmos`.
- **Objetivo:** resultado ordenado por (zona, seção, horário) e íntegro.
- **Verificação sem gabarito** (`verificar_ordenacao`): compara pares
  vizinhos (chave[i] ≤ chave[i+1]) e usa **AVLs** por id para detectar
  registros perdidos, duplicados, estranhos ou alterados. Custo O(n log n).
- Critério errado (ex.: só horário) → ordena, mas a verificação aponta a
  primeira posição fora de ordem e explica o porquê.
- Lote inválido (vazio, registro inválido, id repetido) não é carregado.

### 11.2 Fase 2 — A Central de Triagem (`fase2_triagem.py`)

E1…E6 chegam pela **fila**. A **custódia** (lista ligada) precisa ficar
E2 → E4 → E1 → E6. A **pilha** temporária (capacidade 2) guarda
evidências que chegaram cedo demais; o **arquivo** (lista ligada) recebe as
que não entram na custódia, então nada desaparece.

| Ação | Movimento |
|---|---|
| `receber_na_custodia` | frente da fila → fim da custódia |
| `guardar_na_pilha` | frente da fila → topo da pilha |
| `custodiar_da_pilha` | topo da pilha → fim da custódia |
| `arquivar_da_fila` / `arquivar_da_pilha` | → arquivo |
| `desfazer` | restaura o retrato do topo da pilha de histórico |

- **Objetivo:** custódia exata, fila e pilha vazias, as seis evidências
  contabilizadas uma vez.
- **Por que é um enigma:** E1 chega antes de E2 mas entra depois, então
  precisa esperar na pilha. E3 e E5 precisam ser arquivadas no momento
  certo. Arquivar E1 torna a fase insolúvel até o desfazer.
- **Solução real, não programada:** `sugerir_solucao` roda a BFS genérica
  sobre retratos `(fila, pilha, custódia, arquivo)`. Os sucessores vêm dos
  **mesmos métodos de ação**, executados em cópias. Resultado: 7 ações.
- Ação impossível (fila ou pilha vazia, pilha cheia) → mensagem, estado intacto.

### 11.3 Fase 3 — O Mapa das Seções (`fase3_mapa.py`)

Controlador do modo manual sobre `regras.py`, o mesmo código usado pelo
solver. Consultas: `local_atual`, `conexoes_disponiveis` (com motivo de
bloqueio), `portas_bloqueadas` (com pistas que faltam), `pistas_coletadas`,
`energia_restante`. Ações: `mover`, `desfazer` (pilha de pares (movimento,
estado anterior)) e `solicitar_solucao(BFS | DFS | DFS_RECURSIVA)`, que
calcula a partir do estado atual e não move o jogador.
**Objetivo:** `regras.verificar_vitoria`. Teste-chave: a solução de cada
algoritmo é aplicada passo a passo com `mover` e conclui a fase.

### 11.4 Fase 4 — O Cofre dos Estados (`fase4_cofre.py`)

Oito estados chegam ao cofre (a mesma `ArvoreAVL`, sem segunda
implementação). Para cada um, o jogador responde "novo" ou "repetido".

| Rótulo | Estado | Lição |
|---|---|---|
| A | Praça, sem autenticação, energia 18 | — |
| B | Praça, com autenticação, 18 | difere de A só nas pistas → novo |
| C | igual a A | equivalente → repetido |
| D | Torre, autenticação + lacre, 15 | A < B < D em linha → **rotação à esquerda** |
| E | Praça, sem pistas, 17 | difere de A só na energia → novo |
| F | Torre, lacre + autenticação, 15 | ordem das pistas não importa → repetido de D |
| G | Escola, sem pistas, 17 | desbalanceia à esquerda → **rotação à direita** |
| H | Praça, autenticação, porta do arquivo aberta, 18 | difere de B só nas portas → novo |

- Resposta errada → explicação, nada muda (conta em `erros`).
- Inserção que provoca rotação devolve `dados["antes"]` e
  `dados["depois"]`: árvores serializadas (rótulo, chave, altura, fator,
  filhos) prontas para desenhar.
- Também há `buscar` (chave existente/inexistente), `comparar` (atributos
  que diferem), `estrutura` e `fatores()`.
- **Objetivo:** todos classificados, AVL balanceada, ≥ 1 rotação observada.

### 11.5 Fase 5 — A Auditoria Final (`fase5_auditoria.py`)

`executar_auditoria(algoritmo_busca, algoritmo_ordenacao)` reconfere o
**estado atual** das fases (não confia em flags):

| Verificação | Como |
|---|---|
| `ordenacao_registros` | `verificar_ordenacao` + reordena o lote com o algoritmo escolhido e compara as chaves |
| `custodia` | Fase 2 concluída |
| `trilha` | reexecuta a trilha manual da Fase 3 com `regras.reproduzir_caminho`; o solver sempre roda (métricas e caminho de referência) |
| `evidencias_necessarias` | pistas do estado final ⊇ pistas necessárias |
| `estado_final` | `regras.verificar_vitoria` |
| `cofre` | Fase 4 concluída |
| `selos` | selos 1–4 presentes |

O `RelatorioAuditoria` traz consistência, selos, caminho, algoritmos,
movimentos, energia consumida, estados explorados, tempos, métricas da
ordenação, custódia, **evidências ordenadas** (pelo algoritmo de ordenação
escolhido, por tipo e id: reuso explícito da Fase 1), verificações e
inconsistências. `relatorio_para_dict` gera um dicionário de tipos simples,
pronto para a interface ou para `json.dumps`.

Exemplo de inconsistência proposital: concluir as fases 1–4 e reiniciar a
Fase 2. Os selos continuam, mas a auditoria acusa `custodia`.

## 12. Demonstração da partida

`python -m veridia.demos.demo_fases` joga as cinco fases pela sessão, com
erros propositais (critério errado, pilha vazia, arquivar E1 e desfazer,
movimento sem conexão, classificação errada). Depois imprime o relatório
e o início do rastro da DFS recursiva. Pode servir de roteiro para a
apresentação.

## 13. Exportação do código (`scripts/exportar_projeto.py`)

`python scripts/exportar_projeto.py` gera `dist/urna-logica-veridia-codigo.zip`.
Usa uma **lista de inclusão** (`veridia/`, `tests/`, `docs/`, `scripts/` com
extensões .py/.md/.toml/.txt, mais os arquivos da raiz) e uma **lista de
exclusão** (ambientes virtuais, caches, `.git`, `dist`, temporários e
nomes que sugerem segredos). Não segue links simbólicos, grava em arquivo
temporário e troca no fim, reabre o ZIP para conferir e não altera os
originais.

Na Rodada 4, três artefatos foram incluídos por nome explícito:
`docs/RELATORIO_ACADEMICO.pdf`, `docs/METRICAS_RODADA4.json` e
`scripts/pytest-github-actions.yml`. Outros PDFs/JSON/YAML não são incluídos
automaticamente. O enunciado original permanece externo e excluído.

---

## 14. Interface NiceGUI (`veridia/interface/`)

Execução: `python -m veridia.interface.app` (abre `http://127.0.0.1:8080`).

### 14.1 Arquitetura

```
app.raiz()  ── barra superior (marca, trilho de selos, menu)
            └─ ui.sub_pages: /, /jogar, /fase/1..5, /resolver, /instrucoes, /resultados, /sair
                   │
                   ▼ cada tela recebe ContextoTela
ContextoTela.agir(fase, "ação", ...) ─► SessaoJogo.executar ─► fase ─► regras / estruturas / solver
```

| Módulo | Papel |
|---|---|
| `app.py` | página raiz, roteamento, tema, `main()` com `ui.run` |
| `estado.py` | `GerenciadorSessoes` (id do navegador → `SessaoJogo`) e `ContextoTela` |
| `componentes.py` | trilho de selos, cabeçalho de fase, painel de feedback, métricas, botões |
| `svg.py` | desenho do mapa e da AVL a partir dos dados reais (funções puras) |
| `exportacao.py` | relatório em JSON e em HTML imprimível, sem recursos externos |
| `estilos.css` | identidade visual (paleta abismo/grafite/verde-água/âmbar) |
| `telas/` | uma função `tela(ctx)` por rota |

Decisões importantes:

- **Uma partida por navegador.** O NiceGUI dá a cada navegador um id em
  cookie (`app.storage.browser["id"]`). O `GerenciadorSessoes` associa esse
  id a uma `SessaoJogo`. Jogadores diferentes nunca compartilham partida, e
  navegar ou recarregar continua a mesma partida. Não há banco: reiniciar o
  servidor zera as partidas.
- **Selos só pela sessão.** Nenhum botão concede selo. A tela chama
  `ContextoTela.agir`, que reposiciona a fase atual (a sessão avança para a
  fase seguinte quando concede um selo) e chama `SessaoJogo.executar`.
- **Sair** descarta só a partida daquele navegador. O servidor continua no
  ar para outras pessoas.
- **Mapa clicável.** Cada local alcançável no SVG chama
  `emitEvent('veridia_local', id)`. O evento é registrado uma única vez na
  raiz e repassado para a tela do mapa, que chama `mover` pela sessão. Os
  botões "Ir para" fazem o mesmo; botões de destinos bloqueados também
  chamam `mover`, e a mensagem de bloqueio vem das regras.
- **AVL desenhada a partir da árvore real.** A Fase 4 usa
  `fase.estrutura()` e os registros `antes/depois` guardados pela própria fase
  em cada rotação. A posição horizontal é a ordem em-ordem das chaves.
- **Resolver sem recálculo.** Cada execução chama a busca real uma vez; o
  passo a passo percorre `ResultadoBusca.ordem_visita` já registrado. No mapa,
  cada passo desenha o estado expandido (posição, pistas e portas daquele
  estado) e os locais já expandidos.

### 14.2 O que cada tela mostra

| Tela | Conteúdo |
|---|---|
| Início | narrativa, missão dos cinco selos, as cinco opções do menu |
| Jogar | cartões das fases (bloqueada, em andamento, selo conquistado) e "Continuar" |
| Fase 1 | tabela de registros, algoritmo e critério, resultado ordenado, métricas, comparação dos três algoritmos |
| Fase 2 | sequência exigida, fila (frente destacada), pilha com vagas e topo, custódia encadeada, arquivo, operações, histórico, sugestão BFS |
| Fase 3 | mapa SVG (posição, destinos, portas trancadas/abertas, pistas, destino), energia, pistas, trilha, desfazer, assistente BFS/DFS/DFS recursiva com caminho e ordem de exploração |
| Fase 4 | candidato atual e atributos, novo/repetido, explicação, AVL com h e f, rotações com antes e depois, comparação de estados, busca de chave |
| Fase 5 | escolha dos algoritmos, consistência, verificações, métricas, caminho, custódia, evidências ordenadas, exportação JSON/HTML |
| Resolver | desafios (triagem; mapa com energia 18, 15 e 14), três algoritmos, métricas, ações, passo a passo, rastro da recursão, tabela comparativa |
| Instruções | história, controles, manual × solver, como vencer cada fase, estruturas demonstradas |
| Resultados | selos por fase, métricas da partida, histórico de ações, relatório final |
| Sair | encerra a partida deste navegador |

### 14.3 Testes de interface

`tests/test_interface_app.py` usa o usuário simulado do NiceGUI
(`nicegui.testing.user_simulation`), sem navegador real. Ele abre telas,
clica em botões, escolhe opções e confere textos e o estado da sessão. Os
testes cobrem as cinco fases, o reinício, o feedback de ações inválidas, as
sessões independentes, o Resolver e o Sair. Um ponto de atenção: no NiceGUI 4,
`refresh()` é assíncrono, então os testes aguardam o elemento aparecer
(`should_see`) antes de clicar nele.
