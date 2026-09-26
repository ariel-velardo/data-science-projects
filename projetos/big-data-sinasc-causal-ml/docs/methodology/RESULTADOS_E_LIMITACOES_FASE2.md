# Fase 2 — resultados, diagnóstico e limites

## Leitura principal

Benchmark preditivo e AIPW foram executados com sucesso na amostra integral de 2.251.570 registros. T/Y/X foram preservados. A tabela numérica reproduzível está em `outputs/diagnostics/RESULTADOS_FASE2.md`; plano anterior à estimação em `PLANO_ESTIMACAO_FASE2.md`.

**Gate: RESULTADO_NAO_INTERPRETAVEL**, pela regra conservadora de concentração de influência definida no plano. Isso não significa falha numérica do AIPW nem prova de que toda estimativa é inválida; impede promover uma conclusão causal com este gate sem revisão metodológica.

## Predição

| Modelo | ROC-AUC | AP (PR-AUC) | Brier |
|---|---:|---:|---:|
| Logística | 0,574248 | 0,100220 | 0,072350 |
| HistGradientBoosting | 0,583494 | 0,104537 | 0,072239 |

Teste N=450.314, prevalência 7,89494%; treino N=1.801.256. Brier do baseline constante aprendido no treino = 0,072716. HGB melhora modestamente a discriminação. Os decis têm previsto/observado próximos, mas isso não garante calibração individual ou em todos os subgrupos. Nenhum modelo produz classificação positiva ao limiar fixo 0,5: precision, recall e F1 são zero. O limiar é inadequado para detecção operacional neste risco baixo; não foi otimizado no teste. A conclusão principal é discriminação limitada, não boa performance por acurácia.

## Associação e AIPW

ASSOCIAÇÃO BRUTA — NÃO CAUSAL: risco T=1 de 7,69915%, risco T=0 de 9,12301%, diferença −1,42386 pp.

Sob as hipóteses de identificação explicitadas, C1 produz diferença ajustada de −1,34053 pp (SE 0,06199; IC95% −1,46203 a −1,21902); C2 produz −1,23146 pp (SE 0,06198; IC95% −1,35294 a −1,10997). Não escrever que o início precoce causa essa redução com base nestes números.

Três folds OOF na amostra completa, codificação aprendida somente no treino. AUC do propensity 0,662862, apenas descritiva. Todos os ajustes logísticos convergiram; histórico das tentativas/iterações está no JSON. C1/C2 usam o mesmo propensity e diferentes modelos de outcome; a diferença é 0,10907 pp, abaixo do limiar exploratório 0,25 pp do plano.

## Suporte e influência

0,01–0,99 preserva toda a amostra. 0,05–0,95 mantém 2.103.319 (1.800.499 tratados, 302.820 controles), retirando 148.251. A diferença frente à Fase 1 de 5 folds (2.104.020 mantidos) decorre da estimação OOF com 3 folds e ordenação explícita por contador. Não há clipping de probabilidades.

Na população mais restrita, C1 = −1,38266 pp e C2 = −1,27337 pp, alteração de aproximadamente −0,042 pp. O alvo é essa subpopulação, não a população principal automaticamente.

Peso máximo observado entre controles = 38,79; ESS ≈232.772 controles e 1.927.133 tratados. Sob 0,05–0,95, peso máximo de controle ≈20 e ESS ≈244.237 controles. A precisão e ESS permanecem amplas.

Entretanto, os 1% maiores |IF| concentram 78,78% de IF² em C1 e 78,77% em C2, e cerca de 76% após trimming. Isso ultrapassa os 50% pré-especificados, acionando o gate conservador. O limiar é uma decisão deste exercício, **não um teste estatístico ou critério universal**. Outcomes binários pouco frequentes combinados com controles minoritários podem concentrar variância mesmo quando N é grande. A maior contribuição individual é apenas 0,00150 pp em C1 e 0,00142 pp em C2: concentração coletiva não equivale a um único registro dominando a estimativa. Não mudar retrospectivamente o gate para obter uma conclusão desejada.

## Identificação e incerteza

- Ausência de confundimento não observado é uma hipótese forte: faltam renda, tabagismo, IMC/nutrição, doenças prévias, planejamento, qualidade e barreiras de acesso.
- Covariáveis no nascimento são proxies de estado pré-tratamento; temporalidade perfeita não pode ser confirmada para escolaridade, estado civil e residência.
- Timing retrospectivo, códigos ignorados e discordância mês/consultas geram possível erro de mensuração.
- Seleção por nascido vivo, informação e peso pode condicionar variáveis afetadas pelo tratamento. O contraste não identifica automaticamente um efeito em todas as concepções ou em um estrato principal de sobreviventes.
- SE por IF assume independência e condições de regularidade dos nuisances. Não incorpora dependência geográfica/familiar, erro de mensuração, confundimento ou incerteza da regra de suporte estimada.
- Dupla robustez não prova hipóteses causais nem garante cobertura do IC se ambos os nuisances estiverem inadequados. O IC pequeno resulta em parte do grande N.

Não identificado placebo/negative control adequado. Heterogeneidade foi omitida para preservar escopo. A entrega é um exercício reproduzível, com resultado quantitativo e gate explicitamente conservador.
