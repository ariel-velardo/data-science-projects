# Robustez e auditoria metodológica — Fase 3

AUDITORIA / SENSIBILIDADE FASE 3, 26/09/2026. Histórico Fase 2 preservado byte a byte. População principal e T/Y/X congelados. Não houve Causal Forest, CATE, meta-learners, uplift ou busca por um resultado mais favorável.

**GATE_REVISAO_FASE3 = GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR**.

O veto automático pelo top 1% >50% de IF² é excessivamente conservador como diagnóstico de invalidade numérica/inferencial. AIPW histórico reconciliado, contribuição individual pequena, ajustes geográficos estáveis e simulação oráculo questionam esse veto. A inclusão de múltiplas muda a magnitude em cerca de 0,20 pp e define outro alvo. Seleção, confundimento e temporalidade continuam impedindo uma interpretação causal forte; o gate histórico não foi alterado.

## 1. Auditoria da implementação

Score: `psi=m1−m0+T(Y−m1)/e−(1−T)(Y−m0)/(1−e)`; `IF=psi−média(psi)`.
Estimativa: média por nascido vivo, não média por município. SE iid: `sqrt(sum(IF²)/[N(N−1)])`; IC histórico ±1,96 SE. Não houve clipping ou normalização Hájek oculta. Pesos observados: 1/e para tratados, 1/(1−e) para controles; ESS por grupo `(sum w)²/sum(w²)`.

`aipw_independente` usa correções separadas por grupo sem chamar `calcular_aipw`. Reconciliação de todos os pseudo-outcomes com atol=1e−12; estimativas/SE históricos coincidem exatamente. Top 1% usa ceil(N×0,01), ordenação por |IF| equivalente a IF²; ESS coincide com a implementação histórica. Testes analíticos verificam sinal, centralização e escala. Nenhum erro material foi encontrado no AIPW original.

| especificacao | populacao | n | delta_estimativa | delta_se | max_delta_psi | delta_top1 |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | sem_trimming | 2251570 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| C1 | 0.01_0.99 | 2251570 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| C1 | 0.05_0.95 | 2103319 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| C2 | sem_trimming | 2251570 | 0.000000 | 0.000000 | 0.000000 | -0.000000 |
| C2 | 0.01_0.99 | 2251570 | 0.000000 | 0.000000 | 0.000000 | -0.000000 |
| C2 | 0.05_0.95 | 2103319 | 0.000000 | 0.000000 | 0.000000 | -0.000000 |

## 2. Literatura e status do limiar

A [revisão dirigida](../literature/AUDITORIA_GATE_INFLUENCIA.md) reúne 13 referências sobre IF/AIPW, dupla robustez, positivity, ESS, outcomes raros, inferência agrupada e seleção perinatal. Não foi localizada recomendação formal para o critério top1%/50%; trata-se da heurística do exercício. A busca não é uma revisão sistemática nem prova de inexistência absoluta.

Kennedy e Chernozhukov et al. fundamentam IF/ortogonalidade; Petersen et al. tratam positivity; Balzer et al. discutem informação com outcomes raros; Cameron–Miller e MacKinnon et al. discutem inferência agrupada; Chiang et al. fundamentam divisões que respeitam clusters. A derivação própria de um AIPW oráculo com e=0,85, m0=0,08 e m1=0,07 produz top1% ≈66,3% com IF limitada e overlap. Portanto, ultrapassar 50% não constitui invalidade universal.

## 3. Concentração da influência

| especificacao | top_pct | n | fracao_if2 | fracao_abs_if | contribuicao_psi_pp | contribuicao_if_pp |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | 0.010000 | 226 | 0.070984 | 0.008107 | -0.247728 | -0.247593 |
| C1 | 0.050000 | 1126 | 0.219395 | 0.031406 | -0.959778 | -0.959107 |
| C1 | 0.100000 | 2252 | 0.323710 | 0.053368 | -1.631133 | -1.629793 |
| C1 | 0.500000 | 11258 | 0.638805 | 0.159694 | -4.883577 | -4.876874 |
| C1 | 1.000000 | 22516 | 0.787812 | 0.242131 | -7.404465 | -7.391060 |
| C1 | 2.000000 | 45032 | 0.848183 | 0.312934 | -6.866572 | -6.839762 |
| C1 | 5.000000 | 112579 | 0.896027 | 0.428068 | -3.396185 | -3.329158 |
| C1 | 10.000000 | 225157 | 0.955485 | 0.594045 | 1.605558 | 1.739611 |
| C2 | 0.010000 | 226 | 0.071336 | 0.008128 | -0.248380 | -0.248256 |
| C2 | 0.050000 | 1126 | 0.219784 | 0.031420 | -0.960265 | -0.959649 |
| C2 | 0.100000 | 2252 | 0.323964 | 0.053358 | -1.630937 | -1.629705 |
| C2 | 0.500000 | 11258 | 0.638783 | 0.159611 | -4.879339 | -4.873181 |
| C2 | 1.000000 | 22516 | 0.787666 | 0.241988 | -7.364814 | -7.352499 |
| C2 | 2.000000 | 45032 | 0.847928 | 0.312453 | -6.861062 | -6.836432 |
| C2 | 5.000000 | 112579 | 0.895448 | 0.427158 | -3.402257 | -3.340684 |
| C2 | 10.000000 | 225157 | 0.954781 | 0.592915 | 1.598771 | 1.721916 |

Faixas cumulativas; frações entre 0 e 1. `contribuicao_psi_pp=100×sum(psi_top)/N` e `contribuicao_if_pp=100×sum(IF_top)/N`. Estas contribuições líquidas não são efeitos causais dos extremos. A curva do notebook ordena do maior para o menor |IF| e explicita o sentido dos eixos.

| especificacao | max_fracao_IF2 | max_contribuicao_pp |
| --- | --- | --- |
| C1 | 0.000584 | 0.001498 |
| C2 | 0.000527 | 0.001423 |

O top 1% contém 22.516 registros, e o top 0,01% contém 226. O máximo individual responde por menos de 0,06% de IF². A concentração é coletiva, com contribuição especialmente forte de controles com Y=1; não há evidência de uma única observação dominar a estimativa. Isso não constitui prova de regularidade assintótica.

## 4. Perfil dos extremos

| especificacao | top_pct | n | prop_t0 | prop_y1 |
| --- | --- | --- | --- | --- |
| C1 | 0.100000 | 2252 | 1.000000 | 1.000000 |
| C1 | 1.000000 | 22516 | 1.000000 | 0.999600 |
| C1 | 5.000000 | 112579 | 0.552679 | 0.698150 |
| C2 | 0.100000 | 2252 | 1.000000 | 1.000000 |
| C2 | 1.000000 | 22516 | 1.000000 | 0.995914 |
| C2 | 5.000000 | 112579 | 0.545466 | 0.705354 |

| especificacao | top_pct | idade_mediana | e_mediano | e_p99 |
| --- | --- | --- | --- | --- |
| C1 | 100.0 | 27.000000 | 0.873386 | 0.963647 |
| C1 | 0.1 | 33.000000 | 0.939437 | 0.966998 |
| C1 | 1.0 | 27.000000 | 0.856271 | 0.959404 |
| C1 | 5.0 | 27.000000 | 0.843500 | 0.962863 |
| C2 | 100.0 | 27.000000 | 0.873386 | 0.963647 |
| C2 | 0.1 | 33.000000 | 0.939437 | 0.966998 |
| C2 | 1.0 | 27.000000 | 0.856878 | 0.960933 |
| C2 | 5.0 | 27.000000 | 0.843396 | 0.962863 |

No top 0,1%, a idade mediana é 33 anos (27 no conjunto), e e mediano ≈0,939. Escolaridade código 5, raça/cor código 1 e situação conjugal código 2 são mais frequentes nesse extremo; o JSON e notebook preservam os códigos e distribuições completas. No top 1%, a composição aproxima-se mais do conjunto: mediana de idade 27 anos, maioria nos códigos de escolaridade 3, raça/cor 4, situação conjugal 1, paridade 1 e zero perdas fetais. Essas descrições não identificam mecanismos causais.

A probabilidade pequena relevante é **1−e entre controles**, não e pequeno. O top 1% tem mediana e≈0,856, menor que 0,873 no conjunto; o top 0,1% mostra a cauda de e alto. São Paulo responde por cerca de 20,7% do top 1%, próximo de sua participação amostral; os extremos aparecem em todas as 27 UFs. A combinação outcome pouco frequente + grupo minoritário + pesos explica aritmeticamente o padrão, sem interpretação causal dessa seleção.

## 5. Dependência e inferência municipal

CODMUNRES recuperado na própria projeção SQL da base, com ORDER BY contador. Sem join que expanda N. Chave completa e única; nenhuma data de nascimento inválida ou fora de 2024. T permanece meses 1–3 versus 4–9; outcome é medido ao nascer. O mês de decisão e a temporalidade pré-tratamento das X não são observados diretamente.

N=2,251,570; T=1=1,942,045; T=0=309,525; 5,581 códigos de residência. Destes, 11 códigos terminados em 0000 representam município não especificado: 37 registros. Assim, são 5.570 códigos municipais e 11 agrupamentos residuais, sem alegar validação cadastral individual dos 5.570 códigos. Os códigos residuais ficam juntos por UF no cálculo integral e nos folds; sua exclusão é uma sensibilidade separada.

| quantil | n_cluster |
| --- | --- |
| 0 | 1.000000 |
| 0.01 | 11.000000 |
| 0.05 | 20.000000 |
| 0.5 | 117.000000 |
| 0.95 | 1286.000000 |
| 0.99 | 4604.000000 |
| 1 | 116429.000000 |

Há 43 agrupamentos com N<10. O maior contém 116,429 registros (5.17% de N). A maior participação de um cluster na soma dos scores municipais ao quadrado é 5.42% em C1, código 211130. Não se confunde tamanho de cluster com influência.

Para `U_g=sum_i IF_i`, `V_cluster=[G/(G−1)] sum_g U_g²/N²`. IC95% por t_(G−1). Independência entre municípios permanece assumida. A sensibilidade municipal não incorpora dependência espacial entre municípios, confundimento ou seleção. UF não foi usada como cluster principal.

| especificacao | populacao | n | estimativa_pp | se_iid_pp | se_cluster_pp | ic95_cluster_inferior_pp | ic95_cluster_superior_pp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | sem_trimming | 2251570 | -1.340527 | 0.061994 | 0.068287 | -1.474397 | -1.206657 |
| C1 | 0.05_0.95 | 2103319 | -1.382662 | 0.060840 | 0.068626 | -1.517196 | -1.248127 |
| C2 | sem_trimming | 2251570 | -1.231456 | 0.061981 | 0.067997 | -1.364757 | -1.098155 |
| C2 | 0.05_0.95 | 2103319 | -1.273369 | 0.060813 | 0.068371 | -1.407403 | -1.139335 |

Exclusão somente dos 37 registros de município não especificado, sem refazer nuisances:

| especificacao | populacao | n | estimativa_pp | se_iid_pp | se_cluster_pp | ic95_cluster_inferior_pp | ic95_cluster_superior_pp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | sem_trimming | 2251533 | -1.340996 | 0.061994 | 0.068286 | -1.474863 | -1.207129 |
| C1 | 0.05_0.95 | 2103284 | -1.383121 | 0.060841 | 0.068624 | -1.517651 | -1.248591 |
| C2 | sem_trimming | 2251533 | -1.231927 | 0.061982 | 0.067995 | -1.365224 | -1.098629 |
| C2 | 0.05_0.95 | 2103284 | -1.273831 | 0.060814 | 0.068368 | -1.407859 | -1.139802 |

## 6. Bootstrap por clusters

500 réplicas, seed 20240925; G sorteios uniformes com reposição. Estimativa por réplica `sum_g K_g sum_i psi_i / sum_g K_g n_g`. Denominador variável preserva o alvo por nascido vivo. Nuisances e trimming fixos: não incorpora sua incerteza completa. SE/bootstrap e percentis são sensibilidades condicionais, não uma inferência completa validada.

| especificacao | populacao | se_iid_pp | se_cluster_pp | se_bootstrap_pp | ic_percentil_inf | ic_percentil_sup |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | sem_trimming | 0.061994 | 0.068287 | 0.072235 | -1.474935 | -1.191432 |
| C1 | 0.05_0.95 | 0.060840 | 0.068626 | 0.073294 | -1.516978 | -1.233590 |
| C2 | sem_trimming | 0.061981 | 0.067997 | 0.072250 | -1.364401 | -1.084545 |
| C2 | 0.05_0.95 | 0.060813 | 0.068371 | 0.073339 | -1.404946 | -1.120422 |

## 7. Cross-fitting geográfico

StratifiedGroupKFold em três folds, estratificação conjunta T/Y, seed 20240925. Mesmo código de residência nunca aparece em treino e validação. Nuisances e codificações são aprendidos no treino externo; HGB mantém early stopping interno ao treino. Município não entra em X. C1 usa logística e C2 outcomes HGB. Sem tuning.

| fold | n_treino | n_validacao | intersecao_registros | n_clusters_treino | n_clusters_validacao | intersecao_clusters |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1501047 | 750523 | 0 | 3724 | 1857 | 0 |
| 2 | 1501045 | 750525 | 0 | 3720 | 1861 | 0 |
| 3 | 1501048 | 750522 | 0 | 3718 | 1863 | 0 |

| fold | T0_Y0 | T0_Y1 | T1_Y0 | T1_Y1 |
| --- | --- | --- | --- | --- |
| 1 | 93762 | 9413 | 597508 | 49840 |
| 2 | 93763 | 9413 | 597508 | 49841 |
| 3 | 93762 | 9412 | 597508 | 49840 |

| folds | especificacao | populacao | n | estimativa_pp | se_iid_pp | se_cluster_pp | ic95_cluster_inferior_pp | ic95_cluster_superior_pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| aleatorio | C1 | sem_trimming | 2251570 | -1.340527 | 0.061994 | 0.068287 | -1.474397 | -1.206657 |
| aleatorio | C1 | 0.05_0.95 | 2103319 | -1.382662 | 0.060840 | 0.068626 | -1.517196 | -1.248127 |
| aleatorio | C2 | sem_trimming | 2251570 | -1.231456 | 0.061981 | 0.067997 | -1.364757 | -1.098155 |
| aleatorio | C2 | 0.05_0.95 | 2103319 | -1.273369 | 0.060813 | 0.068371 | -1.407403 | -1.139335 |
| agrupado | C1 | sem_trimming | 2251570 | -1.335914 | 0.062486 | 0.067668 | -1.468570 | -1.203259 |
| agrupado | C1 | 0.05_0.95 | 2101625 | -1.377466 | 0.061109 | 0.066723 | -1.508270 | -1.246663 |
| agrupado | C2 | sem_trimming | 2251570 | -1.235436 | 0.062465 | 0.068406 | -1.369538 | -1.101333 |
| agrupado | C2 | 0.05_0.95 | 2101625 | -1.276798 | 0.061079 | 0.067422 | -1.408972 | -1.144624 |

| folds | especificacao | AUC_propensity | Brier_propensity |
| --- | --- | --- | --- |
| aleatorio | C1 | 0.662862 | 0.113490 |
| aleatorio | C2 | 0.662862 | 0.113490 |
| agrupado | C1 | 0.657925 | 0.113864 |
| agrupado | C2 | 0.657925 | 0.113864 |

| folds | especificacao | populacao | ESS_T0 | ESS_T1 | top1_IF2 |
| --- | --- | --- | --- | --- | --- |
| aleatorio | C1 | sem_trimming | 232772.240802 | 1927132.766493 | 0.787812 |
| aleatorio | C1 | 0.05_0.95 | 244237.072311 | 1787300.439233 | 0.761472 |
| aleatorio | C2 | sem_trimming | 232772.240802 | 1927132.766493 | 0.787666 |
| aleatorio | C2 | 0.05_0.95 | 244237.072311 | 1787300.439233 | 0.760897 |
| agrupado | C1 | sem_trimming | 232082.762165 | 1926748.407698 | 0.790323 |
| agrupado | C1 | 0.05_0.95 | 244168.609637 | 1785614.360730 | 0.763090 |
| agrupado | C2 | sem_trimming | 232082.762165 | 1926748.407698 | 0.789734 |
| agrupado | C2 | 0.05_0.95 | 244168.609637 | 1785614.360730 | 0.762149 |

Performance preditiva OOF dos outcomes, avaliada somente no grupo de tratamento observado:

| folds | especificacao | grupo | AUC | AP | Brier |
| --- | --- | --- | --- | --- | --- |
| aleatorio | C1 | 0 | 0.583803 | 0.120885 | 0.082281 |
| aleatorio | C1 | 1 | 0.571815 | 0.096928 | 0.070736 |
| aleatorio | C2 | 0 | 0.588761 | 0.122982 | 0.082204 |
| aleatorio | C2 | 1 | 0.580691 | 0.101489 | 0.070630 |
| agrupado | C1 | 0 | 0.583460 | 0.120338 | 0.082295 |
| agrupado | C1 | 1 | 0.570738 | 0.096655 | 0.070745 |
| agrupado | C2 | 0 | 0.588449 | 0.122379 | 0.082216 |
| agrupado | C2 | 1 | 0.579632 | 0.100854 | 0.070646 |

Essas métricas não avaliam identificação causal. O cross-fitting agrupado altera C1/C2 em menos de 0,005 pp no contraste sem trimming; o propensity AUC cai ligeiramente. A estabilidade é observada nesta divisão única, não prova de invariância a todas as partições ou ausência de dependência espacial. A UF Distrito Federal ficou inteiramente no fold 3 (32.039 registros), por ser representada por um único município; categorias não vistas recebem o tratamento já definido no pipeline (one-hot desconhecido ignorado; HGB desconhecido como missing), sem adicionar informação da validação. Nenhuma outra UF ficou ausente dos respectivos treinos externos.

## 8. Leave-one-UF-out

Pseudo-outcomes históricos fixos. Retirar UF muda composição e alvo; não estima CATE regional e não refaz nuisance models.

| especificacao | grupo | n_removido | estimativa_pp | mudanca_pp |
| --- | --- | --- | --- | --- |
| C1 | 11 | 18782 | -1.338634 | 0.001893 |
| C1 | 12 | 11862 | -1.347241 | -0.006714 |
| C1 | 13 | 62614 | -1.358348 | -0.017821 |
| C1 | 14 | 11105 | -1.338846 | 0.001681 |
| C1 | 15 | 108354 | -1.350720 | -0.010193 |
| C1 | 16 | 11746 | -1.347738 | -0.007211 |
| C1 | 17 | 21119 | -1.341928 | -0.001402 |
| C1 | 21 | 86044 | -1.353563 | -0.013036 |
| C1 | 22 | 36612 | -1.323972 | 0.016554 |
| C1 | 23 | 95379 | -1.347422 | -0.006895 |
| C1 | 24 | 34611 | -1.366434 | -0.025907 |
| C1 | 25 | 45121 | -1.354118 | -0.013591 |
| C1 | 26 | 104748 | -1.331778 | 0.008749 |
| C1 | 27 | 43786 | -1.345724 | -0.005197 |
| C1 | 28 | 26296 | -1.347572 | -0.007046 |
| C1 | 29 | 147071 | -1.352421 | -0.011895 |
| C1 | 31 | 204343 | -1.296451 | 0.044076 |
| C1 | 32 | 47804 | -1.309596 | 0.030930 |
| C1 | 33 | 154987 | -1.324167 | 0.016360 |
| C1 | 35 | 449148 | -1.247043 | 0.093484 |
| C1 | 41 | 124944 | -1.339554 | 0.000973 |
| C1 | 42 | 90688 | -1.353739 | -0.013212 |
| C1 | 43 | 107292 | -1.376231 | -0.035704 |
| C1 | 50 | 36503 | -1.330867 | 0.009660 |
| C1 | 51 | 53061 | -1.360362 | -0.019836 |
| C1 | 52 | 85511 | -1.345737 | -0.005210 |
| C1 | 53 | 32039 | -1.345132 | -0.004605 |
| C2 | 11 | 18782 | -1.229635 | 0.001821 |
| C2 | 12 | 11862 | -1.238140 | -0.006684 |
| C2 | 13 | 62614 | -1.248704 | -0.017248 |
| C2 | 14 | 11105 | -1.230371 | 0.001085 |
| C2 | 15 | 108354 | -1.239265 | -0.007809 |
| C2 | 16 | 11746 | -1.238228 | -0.006773 |
| C2 | 17 | 21119 | -1.232665 | -0.001210 |
| C2 | 21 | 86044 | -1.244111 | -0.012655 |
| C2 | 22 | 36612 | -1.214867 | 0.016589 |
| C2 | 23 | 95379 | -1.242930 | -0.011474 |
| C2 | 24 | 34611 | -1.257063 | -0.025608 |
| C2 | 25 | 45121 | -1.244603 | -0.013148 |
| C2 | 26 | 104748 | -1.223380 | 0.008076 |
| C2 | 27 | 43786 | -1.236231 | -0.004775 |
| C2 | 28 | 26296 | -1.238471 | -0.007015 |
| C2 | 29 | 147071 | -1.244272 | -0.012816 |
| C2 | 31 | 204343 | -1.191472 | 0.039984 |
| C2 | 32 | 47804 | -1.199536 | 0.031919 |
| C2 | 33 | 154987 | -1.216666 | 0.014790 |
| C2 | 35 | 449148 | -1.132881 | 0.098574 |
| C2 | 41 | 124944 | -1.229059 | 0.002396 |
| C2 | 42 | 90688 | -1.245374 | -0.013918 |
| C2 | 43 | 107292 | -1.267428 | -0.035972 |
| C2 | 50 | 36503 | -1.220786 | 0.010670 |
| C2 | 51 | 53061 | -1.250566 | -0.019110 |
| C2 | 52 | 85511 | -1.237638 | -0.006182 |
| C2 | 53 | 32039 | -1.235601 | -0.004145 |

C1: faixa [-1.376231; -1.247043] pp; maior mudança UF 35, +0.093484 pp, N removido=449,148. Nenhuma exclusão inverte o sinal ou elimina a maior parte da magnitude nacional.

C2: faixa [-1.267428; -1.132881] pp; maior mudança UF 35, +0.098574 pp, N removido=449,148. Nenhuma exclusão inverte o sinal ou elimina a maior parte da magnitude nacional.

## 9. Monte Carlo do gate

N=50.000, 200 réplicas/cenário, efeito verdadeiro −1 pp. X~Uniforme(−1,1). S1: e=.5, m0=.105; S2: e=.85, m0=.1085; S3: e=.85+.10X, m0=.0885+.02X; S4: e=.995 se X>.6 e .81375 caso contrário, m0=.0885+.02X. Todos: m1=m0−.01, T~Bernoulli(e), Y~Bernoulli(mT). E[Y]=10% S1/S2 e 8% S3/S4. Seed base 20240925+j. Nuisances verdadeiros, não ajustados: a simulação isola a regra, não modela erros ML ou seleção do estudo.

| cenario | bias_pp | MCSE_bias_pp | RMSE_pp | cobertura | MCSE_cobertura | P_gate | IC_MC_P_inf | IC_MC_P_sup | ESS_T0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | 0.027424 | 0.017913 | 0.254177 | 0.960000 | 0.013856 | 0.000000 | 0.000000 | 0.018275 | 24988.580000 |
| S2 | 0.001414 | 0.028767 | 0.405810 | 0.950000 | 0.015411 | 0.020000 | 0.005476 | 0.050414 | 7486.700000 |
| S3 | -0.073079 | 0.026096 | 0.375312 | 0.975000 | 0.011040 | 1.000000 | 0.981725 | 1.000000 | 6215.628502 |
| S4 | -0.087381 | 0.071764 | 1.016127 | 0.895000 | 0.021677 | 1.000000 | 0.981725 | 1.000000 | 1140.967141 |

S3 aciona o gate em todas as réplicas, com cobertura 97,5%; S4 também o aciona em todas, mas a cobertura cai para 89,5%. A heurística não separa adequadamente concentração típica de um caso com precisão/cobertura prejudicadas. S4 tem em média apenas cerca de cinco controles com evento no estrato e=.995; isso ajuda a entender a aproximação finita pior, mesmo com oráculo.

Frequências empíricas 0/1 não têm incerteza nula: a tabela usa intervalo binomial exato para P(gate). O bias estimado de S3 é −0,0731 pp (MCSE 0,0261 pp), cerca de 2,8 MCSE, e foi mantido sem novas seeds ou seleção de resultados. Com 200 réplicas, não se afirma recuperação exata ou garantia de cobertura. As réplicas individuais (estimativa, erro, erro quadrático, cobertura, concentração e ESS) estão no JSON.

## 10. Sensibilidades de elegibilidade

S0=P1 histórica. Excluir CONSPRENAT=0 preserva T e reajusta nuisances C1/C2. P0 mantém gestação única, relaxando peso para todo valor numérico positivo. MULTIPLAS mantém P1 e inclui GRAVIDEZ 1/2/3. A projeção de X é reutilizada exatamente do SQL congelado; só filtros e regra de peso mudam. Todas são sensibilidades com populações-alvo diferentes, nunca substituições da principal.

| cenario | n | n_t1 | n_t0 | prevalencia | n_consprenat_zero | n_peso_fora_p1 | n_multipla |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | 2251570 | 1942045 | 309525 | 0.078949 | 1064 | 0 | 0 |
| CONSPRENAT | 2250506 | 1941385 | 309121 | 0.078891 | 0 | 0 | 0 |
| P0 | 2254701 | 1944812 | 309889 | 0.080204 | 1066 | 3131 | 0 |
| MULTIPLAS | 2304013 | 1988680 | 315333 | 0.091521 | 1094 | 0 | 52443 |

| cenario | especificacao | populacao | n | estimativa_pp | se_iid_pp | se_cluster_pp | ic95_cluster_inferior_pp | ic95_cluster_superior_pp | diferenca_p1_pp | diferenca_relativa_abs_p1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CONSPRENAT | C1 | sem_trimming | 2250506 | -1.330146 | 0.061996 | 0.068663 | -1.464752 | -1.195541 | 0.010381 | 0.007744 |
| CONSPRENAT | C1 | 0.05_0.95 | 2102367 | -1.368032 | 0.060811 | 0.068992 | -1.503282 | -1.232782 | 0.014630 | 0.010581 |
| CONSPRENAT | C2 | sem_trimming | 2250506 | -1.220837 | 0.061982 | 0.068532 | -1.355186 | -1.086489 | 0.010618 | 0.008623 |
| CONSPRENAT | C2 | 0.05_0.95 | 2102367 | -1.257726 | 0.060781 | 0.068934 | -1.392863 | -1.122588 | 0.015643 | 0.012285 |
| P0 | C1 | sem_trimming | 2254701 | -1.316646 | 0.062302 | 0.068710 | -1.451343 | -1.181948 | 0.023881 | 0.017815 |
| P0 | C1 | 0.05_0.95 | 2106146 | -1.358046 | 0.061124 | 0.069006 | -1.493325 | -1.222767 | 0.024615 | 0.017803 |
| P0 | C2 | sem_trimming | 2254701 | -1.213659 | 0.062281 | 0.068556 | -1.348056 | -1.079263 | 0.017797 | 0.014452 |
| P0 | C2 | 0.05_0.95 | 2106146 | -1.253563 | 0.061096 | 0.069002 | -1.388834 | -1.118291 | 0.019806 | 0.015554 |
| MULTIPLAS | C1 | sem_trimming | 2304013 | -1.133412 | 0.065180 | 0.075878 | -1.282164 | -0.984661 | 0.207114 | 0.154502 |
| MULTIPLAS | C1 | 0.05_0.95 | 2147344 | -1.192948 | 0.063529 | 0.075004 | -1.339985 | -1.045910 | 0.189714 | 0.137209 |
| MULTIPLAS | C2 | sem_trimming | 2304013 | -1.027203 | 0.065154 | 0.075711 | -1.175626 | -0.878780 | 0.204253 | 0.165863 |
| MULTIPLAS | C2 | 0.05_0.95 | 2147344 | -1.084863 | 0.063496 | 0.074953 | -1.231800 | -0.937925 | 0.188506 | 0.148037 |

`diferenca_relativa_abs_p1 = (estimativa_sens−estimativa_P1)/abs(estimativa_P1)`. Na versão com trimming, o comparador é o P1 da mesma regra; limiares OOF podem selecionar indivíduos diferentes. A prevalência usa o denominador da própria amostra sem trimming.

Múltiplas podem gerar vários nascidos vivos correlacionados da mesma gestação, sem ID de mãe/gestação para verificar a dependência. Município provavelmente reúne muitos irmãos, mas não permite demonstrar isso nem resolve todos os vínculos. Os SE são apresentados como sensibilidade computacional; a conclusão substantiva restringe-se a direção e magnitude.

## 11. C3: dependência da especificação do propensity

HGB com hiperparâmetros já congelados para o projeto, sem tuning. Propensity OOF nos mesmos três folds aleatórios da Fase 2; outcomes HGB C2 OOF reutilizados. Isso isola a mudança de e e não reutiliza treinamento que contenha o registro avaliado. As sete X são validadas explicitamente. C3 não foi selecionada como novo resultado principal.

| especificacao | populacao | n | estimativa_pp | se_iid_pp | se_cluster_pp | ic95_cluster_inferior_pp | ic95_cluster_superior_pp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | sem_trimming | 2251570 | -1.340527 | 0.061994 | 0.068287 | -1.474397 | -1.206657 |
| C1 | 0.05_0.95 | 2103319 | -1.382662 | 0.060840 | 0.068626 | -1.517196 | -1.248127 |
| C2 | sem_trimming | 2251570 | -1.231456 | 0.061981 | 0.067997 | -1.364757 | -1.098155 |
| C2 | 0.05_0.95 | 2103319 | -1.273369 | 0.060813 | 0.068371 | -1.407403 | -1.139335 |
| C3 | sem_trimming | 2251570 | -1.232469 | 0.061044 | 0.067628 | -1.365046 | -1.099892 |
| C3 | 0.05_0.95 | 2096706 | -1.250146 | 0.060684 | 0.069204 | -1.385813 | -1.114480 |

| especificacao | AUC | Brier | suporte_min | suporte_max |
| --- | --- | --- | --- | --- |
| C1 | 0.662862 | 0.113490 | 0.298450 | 0.974221 |
| C2 | 0.662862 | 0.113490 | 0.298450 | 0.974221 |
| C3 | 0.671222 | 0.112829 | 0.288720 | 0.976008 |

| especificacao | populacao | ESS_T0 | ESS_T1 | top1_IF2 | peso_max_T0 |
| --- | --- | --- | --- | --- | --- |
| C1 | sem_trimming | 232772.240802 | 1927132.766493 | 0.787812 | 38.791759 |
| C1 | 0.05_0.95 | 244237.072311 | 1787300.439233 | 0.761472 | 19.995383 |
| C2 | sem_trimming | 232772.240802 | 1927132.766493 | 0.787666 | 38.791759 |
| C2 | 0.05_0.95 | 244237.072311 | 1787300.439233 | 0.760897 | 19.995383 |
| C3 | sem_trimming | 233219.782769 | 1924961.889904 | 0.790267 | 41.679717 |
| C3 | 0.05_0.95 | 243400.209926 | 1778188.513681 | 0.764929 | 19.997666 |

## 12. Estimando e interpretação

Ver [auditoria do estimando](AUDITORIA_ESTIMANDO_FASE3.md). Alvo estatístico: padronização da diferença de médias condicionais na população selecionada `S=1`. Nascimento vivo, peso observado/P1 e MESPRENAT observado podem induzir seleção dependente da exposição e de determinantes do outcome. Restrição a gestação única conhecida ao final não equivale automaticamente a uma elegibilidade basal conhecida.

Defensável: contraste ajustado exploratório entre pré-natal precoce e tardio nos registros selecionados, com hipóteses explícitas. Não defensável: efeito identificado em todas as gestantes/concepções, efeito no estrato que nasceria vivo sob ambos os tratamentos ou recomendação individual de política/ROI. Nuisances, clusters e sensibilidades não resolvem confundimento residual nem seleção. Esse risco já constava da Fase 2; não é novo erro material de implementação.

## 13. Gate adicional e achados por severidade

| dimensao | evidencia | limite |
| --- | --- | --- |
| Literatura | 13 referências; não localizado fundamento para top1/50 como critério universal | Busca dirigida, não sistemática |
| Implementação | Seis combinações históricas reproduzidas; deltas de estimativa e SE iguais a zero | Corretude computacional não identifica causalidade |
| Influência | Top 1% ~78,8%; máximo individual <0,06% de IF²; extremos predominantemente controles com Y=1 | Concentração coletiva merece diagnóstico; não é prova de regularidade |
| Inferência geográfica | SE municipal aumenta ~10%; bootstrap condicional fica ligeiramente acima do sandwich | Independência entre municípios e incerteza completa dos nuisances não verificadas |
| Ajuste geográfico | Três folds sem cluster compartilhado; mudança C1/C2 <0,005 pp | Uma partição; DF ausente de um treino externo |
| Monte Carlo | S3: gate 100%, cobertura 97,5%; S4: gate 100%, cobertura 89,5% | 200 réplicas/cenário; oráculo iid não valida o SINASC |
| C3 | Propensity HGB: -1,232469 pp, próximo de C2 -1,231456 pp | Estabilidade entre modelos não exclui viés comum |
| Elegibilidade | CONSPRENAT muda ~0,01 pp; P0 ~0,02 pp; múltiplas ~0,20 pp, sem mudança de sinal | Múltiplas têm alvo e dependência distintos; não equivalem à principal |
| Estimando | Contraste padronizado na população selecionada de nascidos vivos | Não identifica efeito em todas as concepções nem em estrato principal de sobreviventes |

- **Alto, bloqueador de promoção causal:** seleção, confundimento e temporalidade de X não demonstrados. Correção recomendada: manter interpretação exploratória e declarar o alvo selecionado; não há correção identificada nesta extração.
- **Médio, ressalva inferencial:** dependência entre municípios e nuisances estimados não são eliminados pelos ICs. Correção aplicada: sandwich, bootstrap condicional e folds agrupados; não alegar inferência completa.
- **Médio, interpretação do diagnóstico:** top1/50 é excessivo como veto universal; corrigida a interpretação em registro adicional, preservado o gate histórico.
- **Baixo, qualidade geográfica:** 37 registros em 11 códigos sem município especificado. Correção aplicada: identificação explícita e sensibilidade por exclusão; sem exclusão silenciosa.

## 14. Artefatos, reprodução e validação

Na raiz deste projeto, ative `.venv` (`.\.venv\Scripts\Activate.ps1`). Nenhum pacote foi instalado ou ambiente alterado.

```powershell
python -m src.executa_robustez_fase3
python -m src.valida_resultados_fase3
python -m src.resume_auditoria_fase3
python -m src.cria_notebook_fase3
python -m nbconvert --execute --to notebook --inplace --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=600 notebooks/04_robustez_e_auditoria_metodologica.ipynb
python -m pytest tests -q
python -m pip check
git diff --check
```

O kernel python3 deve resolver para o Python da `.venv`; o notebook verifica isso. Caches completos ficam em outputs/tables, ignorados pelo Git. O executor valida hashes de cache, chaves, dados e código antes de reutilizar; não aceita silenciosamente cache incompatível. Gate é decisão metodológica explícita em fase3_gate.json, não algoritmo que escolhe o efeito desejado.

O validador herdado Fase 2 é executado com sua rotina de persistência interceptada: compara o JSON gerado ao histórico sem sobrescrevê-lo. Os hashes de fontes, Parquet, bruto, predições e artefatos Fase 2 são conferidos antes e depois. A validação Fase 3 recalcula estimativas/SE com implementação independente e sandwich via SQL.

Validação numérica: 22 linhas Fase 3 reconciliadas com atol=1e−12; seis resultados históricos Fase 2 reproduzidos. Folds geográficos respeitam clusters. A execução e inspeção visual do notebook e os checks finais são registrados no estado do projeto.

| artefato | granularidade | chave | validacao | limitacao | proximo_passo |
| --- | --- | --- | --- | --- | --- |
| fase3_influencia.json | especificação/faixa/perfil/UF | C1/C2 + top_pct ou UF | reconciliação independente | descrição de extremos | interpretar com contexto |
| fase3_cluster.json | especificação/regra | spec + trimming | sandwich analítico/SQL | clusters independentes; nuisances fixos | reportar SE alternativo |
| fase3_crossfit_geografico.json | fold/spec/regra | tipo_fold + spec + regra | cluster exclusivo por fold | uma partição; espaço entre municípios | manter como sensibilidade |
| fase3_monte_carlo.json | cenário/réplica | cenário + réplica | DGP conhecido e seed fixa | oráculo iid | não extrapolar cobertura ao SINASC |
| fase3_sensibilidades.json | população/spec/regra | população + spec + regra | N e efeitos reconciliados | novos alvos selecionados | reportar magnitude/direção |

## 15. Recomendação para o artigo — até cinco pontos

1. Apresentar o contraste como ajustado e exploratório na população selecionada, sem linguagem de efeito identificado em todas as gestantes.
2. Preservar o gate original e explicar sua revisão adicional com literatura, contraexemplo e Monte Carlo, sem reescrever a história.
3. Mostrar C1/C2, SE municipal e cross-fitting agrupado; C3 e elegibilidades como sensibilidades, sem selecionar pelo sinal/significância.
4. Usar concentração completa, perfil T/Y e contribuição máxima individual para distinguir eventos coletivamente influentes de registros dominantes.
5. Dar espaço explícito a seleção de nascidos vivos, mensuração e confundimento residual; adiar heterogeneidade causal e recomendação de política.
