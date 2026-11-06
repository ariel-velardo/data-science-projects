from veridia.demos import demo_busca, demo_fases, experimento_ordenacao


def test_demo_busca_executa(capsys):
    demo_busca.main([])
    saida = capsys.readouterr().out
    assert "=== BFS ===" in saida and "=== DFS ===" in saida and "Solução com" in saida


def test_demo_busca_sem_solucao(capsys):
    demo_busca.main(["--energia", "14"])
    assert "Nenhuma solução" in capsys.readouterr().out


def test_experimento_executa(capsys):
    experimento_ordenacao.main(["--tamanhos", "20", "40"])
    assert "quick_sort" in capsys.readouterr().out


def test_demo_fases_executa_partida_completa(capsys):
    demo_fases.main()
    saida = capsys.readouterr().out
    assert "Selos: [1, 2, 3, 4, 5] | jogo concluído: True" in saida
    assert "caso_base" in saida or "sem_saida" in saida
