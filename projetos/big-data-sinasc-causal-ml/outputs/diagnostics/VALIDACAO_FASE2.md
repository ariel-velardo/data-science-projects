# Validação da entrega — 26/09/2026

- Ambiente: Python 3.11.9 da `.venv` deste projeto; scikit-learn 1.8.0.
- Notebook 02: 12/12 células de código executadas, 0 erros, 8 imagens PNG incorporadas.
- Notebook 03: 13/13 células de código executadas, 0 erros, 4 imagens PNG incorporadas.
- Curvas ROC, PR, calibração e intervalos AIPW exportados e inspecionados visualmente; gráficos de SMD, overlap e positividade da Fase 1 também inspecionados.
- Suíte: 40 testes aprovados, incluindo fórmula/SE, efeito zero, efeito conhecido, dupla robustez, guardas, separação OOF, ESS e gate.
- `pip check`: No broken requirements found.
- `git diff --check`: sem erros de whitespace.
- Reconciliação independente das predições OOF: 6 resultados conferidos até tolerância absoluta 1e-12; N, grupos, cobertura e ausência de NaN confirmados.
- Datas parseadas: 01/01/2024 a 31/12/2024, sem inválidas ou fora de 2024.
- SHA-256 do ZIP bruto preservado: `27e55de6359e1b1914301dc1d752d78e9535a7a52cc0640931dd94876aca6027`.
- Modelagem integral concluída em aproximadamente 293 segundos, sem amostragem redutora.
- Warnings do Jupyter sobre event loop/TCP local não interromperam execução. Nenhum ConvergenceWarning permaneceu nos modelos.

Resultados são exploratórios e sujeitos ao gate e limitações registrados. Validação computacional não confirma identificação causal.
