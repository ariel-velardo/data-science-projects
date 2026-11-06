# VERÍDIA — O Enigma da Urna

EP **Urna Lógica** — Estruturas de Dados e Análise de Algoritmos
Mestrado Profissional em Computação Aplicada (IPT).

Jogo educacional em que o jogador investiga uma eleição **fictícia** na
cidade de Verídia. O projeto já tem:

- **Fundação técnica (Rodada 1):** estruturas de dados, algoritmos de
  ordenação, grafo, BFS/DFS sobre o estado completo do jogo e controle de
  estados visitados com árvore AVL.
- **Motor das cinco fases (Rodada 2):** sessão com selos e progressão, os
  cinco enigmas executáveis, DFS recursiva, métricas de busca, auditoria
  final com relatório e exportação do código em ZIP.
- **Interface visual (Rodada 3):** aplicação NiceGUI com menu inicial
  (Jogar, Resolver, Instruções, Resultados, Sair), as cinco fases jogáveis,
  mapa interativo em SVG, visualização da AVL com rotações, Modo Resolver
  com exploração passo a passo e relatório final exportável (JSON e HTML).
- **Redesign visual (Rodada 5):** identidade inspirada nos tons azuis do
  IPT, "prancha técnica de auditoria": área de trabalho clara e instrumentos
  (mapa, AVL, estruturas, solver) em pranchas azul-profundo. Capa com os
  cinco selos, estruturas da Fase 2 com frente/topo/ponteiros, mapa
  redesenhado, rotações AVL antes/depois, passo a passo real da ordenação
  e Resolver com reprodução automática. Funciona offline (fontes do sistema).

| Fase | Enigma | Estruturas/algoritmos |
|---|---|---|
| 1 | O Arquivo Embaralhado | Bubble/Merge/Quick Sort, chave composta, AVL para integridade |
| 2 | A Central de Triagem | Fila, Pilha, Lista ligada, desfazer com pilha |
| 3 | O Mapa das Seções | Grafo, BFS, DFS (iterativa e recursiva), pistas e portas |
| 4 | O Cofre dos Estados | AVL, estados equivalentes × distintos, rotações |
| 5 | A Auditoria Final | integração das fases, solver, ordenação, relatório |

> Todos os dados são fictícios: não há candidatos, partidos ou resultados reais.
> As opções de voto são códigos como `OPC-A`, `BRANCO`, `NULO`.

## Estrutura

```
urna-logica-veridia/
├── veridia/
│   ├── modelos/      registro.py, evidencia.py, estado.py, mapa.py
│   ├── dados/        gerador_registros.py (seed fixa), mapa_veridia.py
│   ├── estruturas/   fila.py, pilha.py, lista_ligada.py, arvore_avl.py, grafo.py
│   ├── algoritmos/   ordenacao.py (Bubble, Merge, Quick + métricas)
│   ├── jogo/         regras.py (movimentos, portas, pistas, vitória), sessao.py (selos, progressão)
│   ├── fases/        base.py + fase1_arquivo … fase5_auditoria (os cinco enigmas)
│   ├── busca/        solver.py (BFS, DFS iterativa, DFS recursiva, métricas; visitados em AVL)
│   ├── interface/    app NiceGUI: app.py, estado.py, componentes.py, svg.py, rastro_ordenacao.py, exportacao.py, estilos.css, telas/
│   └── demos/        demo_fases.py, demo_busca.py, experimento_ordenacao.py
├── scripts/          exportar_projeto.py (ZIP limpo em dist/)
├── tests/            testes pytest
├── docs/             GUIA_TECNICO, REGISTRO_IA, REQUISITOS_EP, CONTINUIDADE
├── AGENTS.md                     (instruções para Codex e outros agentes)
├── CLAUDE.md                     (instruções permanentes para o Claude Code)
├── requirements.txt              (pytest)
└── requirements-interface.txt    (NiceGUI 4 + pytest-asyncio para a interface)
```

## Instalação (Windows / PowerShell)

Execute na pasta `projetos/urna-logica-veridia/`. Requer Python 3.11+.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-interface.txt   # inclui requirements.txt
```

Linux/macOS: `python3 -m venv .venv && source .venv/bin/activate`.

## Execução

Com a `.venv` **deste projeto** ativada:

```powershell
python -m veridia.interface.app                    # JOGO: abre http://127.0.0.1:8080 no navegador
python -m veridia.interface.app --porta 8090 --sem-navegador
python -m pytest                                   # todos os testes (motor + interface)
python -m veridia.demos.demo_fases                 # partida completa das 5 fases (terminal)
python -m veridia.demos.demo_busca                 # desafio resolvido por BFS e DFS
python -m veridia.demos.demo_busca --energia 14    # cenário sem solução
python -m veridia.demos.experimento_ordenacao      # Bubble x Merge x Quick
python -m veridia.demos.experimento_ordenacao --tamanhos 100 500 1000 2000 --seed 2026
python scripts/exportar_projeto.py                 # gera dist/urna-logica-veridia-codigo.zip
```

Uso programático (o mesmo caminho que a interface usa):

```python
from veridia.jogo.sessao import SessaoJogo

sessao = SessaoJogo()
sessao.executar("selecionar_algoritmo", "merge_sort")
sessao.executar("selecionar_criterio", "zona_secao_horario")
resultado = sessao.executar("executar_ordenacao")   # ResultadoAcao(sucesso, mensagem, dados)
print(resultado.mensagem, sessao.selos)
```

> Se os acentos aparecerem trocados no terminal do Windows, rode antes
> `$env:PYTHONIOENCODING = "utf-8"`.

## Princípios

- A lógica do jogo usa **apenas a biblioteca padrão** do Python; todas as
  estruturas e algoritmos obrigatórios foram implementados manualmente.
- **Regras em um único lugar** (`veridia/jogo/regras.py`): o modo manual
  e o solver usam as mesmas funções.
- **Nenhuma solução codificada**: o caminho é sempre descoberto pela busca e
  os testes revalidam a solução executando as regras passo a passo.

Documentação didática: [docs/GUIA_TECNICO.md](docs/GUIA_TECNICO.md).
Requisitos × implementação: [docs/REQUISITOS_EP.md](docs/REQUISITOS_EP.md).
Instruções para agentes: [AGENTS.md](AGENTS.md) (Codex) e [CLAUDE.md](CLAUDE.md) (Claude Code).
Estado atual e próximos passos: [docs/CONTINUIDADE.md](docs/CONTINUIDADE.md).
Registro de uso de IA: [docs/REGISTRO_IA.md](docs/REGISTRO_IA.md).

## Validação e entrega (06/11/2026)

A suíte local tem **185 testes aprovados**. A conferência com o enunciado
oficial e as pendências obrigatórias estão em
[docs/REQUISITOS_EP.md](docs/REQUISITOS_EP.md). O relatório da partida
exportado pelo jogo não substitui o relatório técnico acadêmico em PDF.

O relatório acadêmico foi preparado em
[Markdown editável](docs/RELATORIO_ACADEMICO.md) e
[PDF](docs/RELATORIO_ACADEMICO.pdf), com dez seções e evidências medidas.
É uma versão para revisão: faltam a confirmação de autoria/identificação,
as considerações pessoais e a curadoria humana do estudante. Os dados dos
experimentos estão em [docs/METRICAS_RODADA4.json](docs/METRICAS_RODADA4.json).

Para o repositório `data-science-projects`, a configuração de CI está
preparada em [scripts/pytest-github-actions.yml](scripts/pytest-github-actions.yml).
Uma cópia já foi instalada como `.github/workflows/veridia-pytest.yml` na
raiz do repositório, conforme o pedido desta rodada. Ela só será executada
após publicação; ainda não há resultado de CI no GitHub. O ZIP inclui
código, testes, documentação, PDF acadêmico, métricas JSON e configuração
YAML, por lista explícita. O enunciado externo continua excluído.
