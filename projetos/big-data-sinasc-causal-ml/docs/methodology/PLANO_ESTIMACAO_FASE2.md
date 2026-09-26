# Plano congelado da Fase 2

Registrado em 26/09/2026, após o checkpoint Fase 1 `caf1446`, antes de estimar efeitos. Gate herdado: PRONTO_COM_RESSALVAS.

## População, variáveis e alvo

Usar exatamente a view `amostra_principal` da Fase 1: 2.251.570 registros de nascidos vivos SINASC 2024, gestações únicas, peso 500–6.000 g e MESPRENAT 1–9. Chave contador completa/única. T=1 meses 1–3; T=0 meses 4–9. Y=1 peso <2.500 g. Não reclassificar discordâncias CONSPRENAT/MESPRENAT em função dos resultados.

X congelado: IDADEMAE_NUM, ESCOLARIDADE_MAE, RACA_COR_MAE, SITUACAO_CONJUGAL, PARIDADE_CAT, PERDAS_FETAIS_CAT, UF_RESIDENCIA. Preservar as transformações da Fase 1. Guardas proíbem outcome, tratamento e variáveis posteriores em X.

Alvo principal: diferença média absoluta de risco sob T=1 versus T=0 na população selecionada, sem trimming adicional. Não extrapolar a todas as gestantes/concepções. Nascido vivo, peso e informação disponível são critérios observados posteriormente ao tratamento: potencial seleção/collider limita a interpretação como intervenção numa população pré-tratamento. Não há identificação de um estrato principal de sobreviventes.

Sensibilidades: subpopulações selecionadas por propensity OOF entre 0,01–0,99 e 0,05–0,95; não substituir silenciosamente a população principal. Refazer o propensity com 3 folds na Fase 2; diferenças mínimas de N em relação ao diagnóstico de 5 folds são esperadas e serão expostas.

## Predição

Divisão estratificada por Y 80/20, seed 20240925. Apenas X; sem T. Comparar logística L2 (C=1, L-BFGS, max_iter=500, tol=1e-5) e HistGradientBoosting (100 iterações máximas, 15 folhas, min_samples_leaf=100, learning_rate=0,1, l2=1, early stopping com validação interna de 10% do treino). Sem tuning. Logística: one-hot sparse, mediana/indicador de idade e padronização. HGB: códigos categóricos nominais aprendidos no treino, desconhecidos como NaN; missing numérico nativo. Mesmas informações X, codificação apropriada a cada estimador.

Métricas no teste: ROC-AUC, average precision (identificada como PR-AUC/AP), Brier, precision/recall/F1 ao limiar fixo 0,5, curva ROC, PR e calibração em decis de probabilidade. Limiar não otimizado usando teste.

## AIPW cross-fitted

Três folds estratificados por (T,Y), seed 20240925, amostra integral. Escolha computacional prévia: 3 propensity + 6 outcomes logísticos + 6 outcomes não lineares. Cada observação é avaliada exatamente uma vez; treino/validação disjuntos e pré-processamento ajustado somente no treino. Ambos os modelos outcome predizem m0 e m1 em todo o fold de validação.

C1: propensity logístico e outcomes logísticos separados por T. C2: mesmo propensity C1 e outcomes HGB separados por T. Não selecionar especificação pela estimativa. Capturar convergência logística; ampliar max_iter se necessário, sem mudar X.

Pseudo-outcome: `psi = m1 - m0 + T*(Y-m1)/e - (1-T)*(Y-m0)/(1-e)`.
Estimativa = média de psi; IF = psi - média; SE = desvio-padrão amostral de IF / sqrt(N); IC95% = estimativa ± 1,96 SE. Reportar em pontos percentuais. Não fazer clipping ou trimming oculto.

SE assume observações independentes e condições assintóticas dos nuisances. Não corrige dependência por município/família (mãe não identificável), erro de mensuração nem confundimento. Nos estratos de propensity estimado, o IC é aproximado, condicional à regra de seleção aprendida, sem incorporar sua incerteza.

## Diagnósticos e decisão

Reportar propensity, pesos observados T/e e (1-T)/(1-e), ESS por grupo, percentis de psi/IF, máximo |IF| e participação dos 1% maiores |IF| na soma de IF². Reconciliar N por especificação/regra. Associação bruta será rotulada NÃO CAUSAL.

Critérios exploratórios pré-especificados, não universais: RESULTADO_NAO_INTERPRETAVEL para falha de convergência/validação, ausência de grupo, valores inválidos ou concentração >50% da soma IF² no 1% extremo. RESULTADO_SENSIVEL_A_ESPECIFICACAO se C1/C2 mudarem sinal ou diferirem >0,25 ponto percentual, ou trimming alterar estimativa >0,5 ponto percentual. Caso contrário, RESULTADO_EXPLORATORIO_ESTAVEL. Estabilidade numérica não valida identificação.

Não identificado placebo/negative control adequado. Heterogeneidade opcional será omitida para manter a análise parcimoniosa. Não estimar CATE nem usar Causal Forest.

## Reprodução

Referências metodológicas consultadas: [AIPW e cross-fitting](https://pmc.ncbi.nlm.nih.gov/articles/PMC8796813/), [dupla robustez](https://pmc.ncbi.nlm.nih.gov/articles/PMC3070495/) e [HGB no sklearn 1.8](https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html). A consistência duplamente robusta não dispensa condições de taxa/convergência dos nuisance models para inferência Wald válida.

Ambiente: `.venv` deste projeto. `python -m src.executa_fase2` produz JSONs pequenos, tabela Markdown e curvas; o notebook 03 apresenta e valida esses resultados persistidos, com comando explícito para recalcular. Nenhum ajuste usa os resultados para alterar desenho.

Comandos de reprodução no PowerShell, a partir da raiz deste projeto:

```powershell
.\.venv\Scripts\Activate.ps1
python -m src.executa_fase2
python -m src.valida_resultados_fase2
python -m src.cria_notebook_fase2
$sinascKernelPrefix = Join-Path $env:TEMP 'sinasc-fase1-jupyter'
python -m ipykernel install --prefix $sinascKernelPrefix --name sinasc-fase1
$env:JUPYTER_PATH = Join-Path $sinascKernelPrefix 'share\jupyter'
$env:IPYTHONDIR = Join-Path $env:TEMP 'sinasc-fase1-ipython'
python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=sinasc-fase1 --ExecutePreprocessor.timeout=600 notebooks/03_ml_preditivo_e_aipw.ipynb
python -m pytest tests -q
python -m pip check
git diff --check
```

O registro temporário de kernel aponta para o Python da `.venv`; não instala pacotes globalmente. Figuras PNG precisam do navegador já usado pelo Kaleido neste ambiente; os notebooks entregues já contêm as imagens.
