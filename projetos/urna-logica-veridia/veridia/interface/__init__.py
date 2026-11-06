"""Interface gráfica NiceGUI do VERÍDIA.

Execução: ``python -m veridia.interface.app`` (abre http://127.0.0.1:8080).

Regra de arquitetura: a interface apenas CHAMA o motor — ações das fases
pela ``SessaoJogo`` (via ``ContextoTela.agir``), regras e solver — e exibe os
resultados. Ela não reimplementa regras nem concede selos. Assim, o modo
manual e o solver usam exatamente a mesma lógica.

Módulos:
- app.py         página raiz, rotas e ``main()``;
- estado.py      uma ``SessaoJogo`` por navegador e o contexto de cada aba;
- componentes.py trilho de selos, cabeçalho de fase, feedback, métricas;
- svg.py         desenho do mapa e da árvore AVL a partir dos dados reais;
- exportacao.py  relatório final em JSON e HTML imprimível;
- estilos.css    identidade visual;
- telas/         uma tela por rota (início, jogar, fases 1–5, resolver,
                 instruções, resultados, sair).
"""
