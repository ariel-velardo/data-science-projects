# Resultados principais — SINASC 2024

O início precoce apresenta menor risco ajustado na população selecionada. A estabilidade numérica não comprova causalidade: confundimento residual, seleção de nascidos vivos e temporalidade das covariáveis continuam limitantes.

| Indicador | Resultado |
| --- | --- |
| Registros brutos | <span data-metrica="bruto">2.389.325</span> |
| Colunas originais | <span data-metrica="colunas">62</span> |
| Registros analíticos | <span data-metrica="n">2.251.570</span> |
| T=1: início até o terceiro mês | <span data-metrica="n_t1">1.942.045</span> |
| T=0: início após o terceiro mês | <span data-metrica="n_t0">309.525</span> |
| Baixo peso na população analítica (%) | <span data-metrica="prevalencia">7,894891</span> |
| UFs de residência | <span data-metrica="ufs">27</span> |
| Associação bruta NÃO CAUSAL (pp) | <span data-metrica="bruta">-1,423859</span> |
| Logística: ROC-AUC | <span data-metrica="pred_0_roc_auc">0,574248</span> |
| Logística: AP | <span data-metrica="pred_0_pr_auc_ap">0,100220</span> |
| Logística: Brier | <span data-metrica="pred_0_brier">0,072350</span> |
| HGB: ROC-AUC | <span data-metrica="pred_1_roc_auc">0,583494</span> |
| HGB: AP | <span data-metrica="pred_1_pr_auc_ap">0,104537</span> |
| HGB: Brier | <span data-metrica="pred_1_brier">0,072239</span> |
| C1 AIPW: estimativa (pp) | <span data-metrica="C1_estimativa_pp">-1,340527</span> |
| C1 AIPW: IC95% inferior iid (pp) | <span data-metrica="C1_ic95_inferior_pp">-1,462034</span> |
| C1 AIPW: IC95% superior iid (pp) | <span data-metrica="C1_ic95_superior_pp">-1,219019</span> |
| C2 AIPW: estimativa (pp) | <span data-metrica="C2_estimativa_pp">-1,231456</span> |
| C2 AIPW: IC95% inferior iid (pp) | <span data-metrica="C2_ic95_inferior_pp">-1,352938</span> |
| C2 AIPW: IC95% superior iid (pp) | <span data-metrica="C2_ic95_superior_pp">-1,109973</span> |
| C1 EP municipal (pp) | <span data-metrica="C1_cluster">0,068287</span> |
| C2 EP municipal (pp) | <span data-metrica="C2_cluster">0,067997</span> |
| CATE HGB média (pp) | <span data-metrica="cate_media_pp">-1,294100</span> |
| CATE HGB mediana (pp) | <span data-metrica="cate_mediana_pp">-1,289838</span> |
| CATE HGB p5 (pp) | <span data-metrica="cate_p05_pp">-3,923820</span> |
| CATE HGB p25 (pp) | <span data-metrica="cate_p25_pp">-1,962784</span> |
| CATE HGB p75 (pp) | <span data-metrica="cate_p75_pp">-0,427044</span> |
| CATE HGB p95 (pp) | <span data-metrica="cate_p95_pp">1,208079</span> |
| Correlação mediana dos perfis entre partições | <span data-metrica="estabilidade">0,157895</span> |
| Spearman HGB/Ridge | <span data-metrica="modelos">0,706556</span> |
| Gate histórico da Fase 2 | <span data-metrica="gate2">RESULTADO_NAO_INTERPRETAVEL</span> |
| Gate da Fase 3 | <span data-metrica="gate3">GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR</span> |
| Gate da Fase 4 | <span data-metrica="gate4">HETEROGENEIDADE_SENSIVEL_A_MODELO</span> |

## Robustez

| Cenário | Modelo | N | Estimativa (pp) | EP municipal (pp) | IC95% municipal (pp) |
| --- | --- | --- | --- | --- | --- |
| Municipal | C1 | 2.251.570 | -1,335914 | 0,067668 | -1,468570 a -1,203259 |
| Municipal | C2 | 2.251.570 | -1,235436 | 0,068406 | -1,369538 a -1,101333 |
| C3 | C3 | 2.251.570 | -1,232469 | 0,067628 | -1,365046 a -1,099892 |
| Excluir discordância | C1 | 2.250.506 | -1,330146 | 0,068663 | -1,464752 a -1,195541 |
| Excluir discordância | C2 | 2.250.506 | -1,220837 | 0,068532 | -1,355186 a -1,086489 |
| Peso positivo | C1 | 2.254.701 | -1,316646 | 0,068710 | -1,451343 a -1,181948 |
| Peso positivo | C2 | 2.254.701 | -1,213659 | 0,068556 | -1,348056 a -1,079263 |
| Incluir múltiplas | C1 | 2.304.013 | -1,133412 | 0,075878 | -1,282164 a -0,984661 |
| Incluir múltiplas | C2 | 2.304.013 | -1,027203 | 0,075711 | -1,175626 a -0,878780 |

Múltiplas e peso positivo definem outros alvos. ICs são condicionais e aproximados. Percentis de CATE são dispersão prevista, não confiança individual.

Gates preservados: Fase 0 `VIAVEL_COM_RESSALVAS`; Fase 1 `PRONTO_COM_RESSALVAS`; Fase 2 `RESULTADO_NAO_INTERPRETAVEL`; Fase 3 `GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR`; Fase 4 `HETEROGENEIDADE_SENSIVEL_A_MODELO`. A revisão da Fase 3 questiona o veto pela concentração de influência, sem apagar o gate histórico nem certificar identificação causal.

Fonte: JSONs históricos em `outputs/diagnostics/`; geração por `python -m src.entrega_fase5`. [Metodologia](METODOLOGIA_DO_PROJETO.md).
