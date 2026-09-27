# Síntese executiva — Big Data & Analytics

## Problema e dados

Investigar se início precoce do pré-natal está associado a menor risco de baixo peso entre registros comparáveis em características observáveis. Fonte: SINASC 2024, Ministério da Saúde.

| Indicador | Resultado |
| --- | --- |
| Registros brutos | <span data-metrica="bruto">2.389.325</span> |
| Colunas originais | <span data-metrica="colunas">62</span> |
| Registros analíticos | <span data-metrica="n">2.251.570</span> |
| T=1: início até o terceiro mês | <span data-metrica="n_t1">1.942.045</span> |
| T=0: início após o terceiro mês | <span data-metrica="n_t0">309.525</span> |
| Baixo peso na população analítica (%) | <span data-metrica="prevalencia">7,894891</span> |
| UFs de residência | <span data-metrica="ufs">27</span> |
| C1 AIPW: estimativa (pp) | <span data-metrica="C1_estimativa_pp">-1,340527</span> |
| C2 AIPW: estimativa (pp) | <span data-metrica="C2_estimativa_pp">-1,231456</span> |
| CATE HGB média (pp) | <span data-metrica="cate_media_pp">-1,294100</span> |
| Gate da Fase 4 | <span data-metrica="gate4">HETEROGENEIDADE_SENSIVEL_A_MODELO</span> |

## O que o trabalho entrega

O volume nacional exige leitura seletiva, agregações e contratos reproduzíveis: DuckDB executa SQL sobre Parquet e Pandas materializa resumos. Big Data aqui é disciplina de processamento e veracidade, sem alegação de infraestrutura distribuída.

A predição compara logística e HGB com as mesmas sete características maternas. A discriminação é modesta; prever risco não responde se mudar o início do cuidado mudaria o desfecho.

O início precoce apresenta menor risco ajustado na população selecionada. A estabilidade numérica não comprova causalidade: confundimento residual, seleção de nascidos vivos e temporalidade das covariáveis continuam limitantes. O AIPW combina regressões de risco com o escore de propensão e avalia cada registro fora do treino. A auditoria municipal amplia a incerteza e mantém estimativas próximas.

O DR-Learner produz ordenação parcial, mas exagera a separação entre extremos e apresenta instabilidade de perfis. CATE previsto não é benefício individual conhecido. Não há recomendação clínica ou ROI.

## Conclusão

A contribuição é uma análise nacional reproduzível que distingue descrição, predição e estimativas sob hipóteses causais. Os resultados justificam discussão acadêmica; não demonstram que antecipar o pré-natal cause a redução estimada.

Gates preservados: Fase 0 `VIAVEL_COM_RESSALVAS`; Fase 1 `PRONTO_COM_RESSALVAS`; Fase 2 `RESULTADO_NAO_INTERPRETAVEL`; Fase 3 `GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR`; Fase 4 `HETEROGENEIDADE_SENSIVEL_A_MODELO`. A revisão da Fase 3 questiona o veto pela concentração de influência, sem apagar o gate histórico nem certificar identificação causal.

`MODELAGEM_CONCLUIDA = SIM`; `ARTIGO_COMPLETO = NAO`; `RELATORIO_HTML = SIM`; `CAUSALIDADE_PROVADA = NAO`.

[Resultados e ICs](RESULTADOS_PRINCIPAIS.md) · [Métodos](METODOLOGIA_DO_PROJETO.md) · [Referências](literature/REFERENCIAS_CENTRAIS.md).
