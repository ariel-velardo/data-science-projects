# SINASC 2024 — recorte recomendado

**Priorizar São Paulo — capital; alternativa: estado de São Paulo.** A capital tem a melhor qualidade conjunta das variáveis essenciais e a maior retenção, com 10.118 controles. A escolha não usa a magnitude da associação com baixo peso.

| Recorte | Nascimentos | Essenciais¹ | Elegíveis B | Retenção | T=1 | T=0 |
|---|---:|---:|---:|---:|---:|---:|
| Sudeste | 904.365 | 97,16% | 842.998 | 93,21% | 758.924 | 84.074 |
| SP — estado | 470.887 | 97,93% | 442.733 | 94,02% | 402.207 | 40.526 |
| SP — capital | 120.789 | 99,04% | 114.694 | 94,95% | 104.576 | 10.118 |
| Minas Gerais | 219.819 | 95,49% | 201.200 | 91,53% | 182.626 | 18.574 |
| Rio de Janeiro | 163.722 | 96,93% | 151.969 | 92,82% | 131.899 | 20.070 |
| Espírito Santo | 49.937 | 98,06% | 47.096 | 94,31% | 42.192 | 4.904 |

¹ MESPRENAT 1–9, GRAVIDEZ 1–3 e PESO inteiro 500–6.000 g simultaneamente; peso segue a faixa operacional do piloto, não um domínio clínico validado.

**Qualidade.** MESPRENAT válido: Sudeste 97,32%, SP 98,08%, capital 99,15%: ganhos de 0,76 p.p. e 1,08 p.p., respectivamente. Peso na faixa: 99,86%/99,86%/99,89%; gravidez válida: 99,96%/99,98%/99,99%. A vantagem concentra-se no início do pré-natal.

Na capital versus SP, escolaridade válida: 99,98%/99,26%; raça/cor: 99,96%/99,12%; situação conjugal: 99,92%/99,77%; QTDFILMORT preenchido: 99,97%/99,65%. MG tem o menor MESPRENAT válido (95,65%); RJ, o menor preenchimento de QTDFILMORT (97,88%). ES tem qualidade essencial próxima a SP (98,06%/97,93%), mas amostra menor: SP é a alternativa de maior abrangência.

**Limitações.** Todos os recortes têm milhares nos dois grupos; viabilidade para estimação/subgrupos ainda depende de precisão e overlap. Na capital, T=0 representa 8,82%. IDADEMAE e PARIDADE estão preenchidas em 100% em todos os recortes; PARIDADE aceita 0/1. O dicionário não confirma limites/sentinelas de IDADEMAE e QTDFILMORT: validade fica vazia nos CSVs; sete registros com 99 em cada campo no Sudeste são sinalizados sem reclassificação.

**Método.** Base completa [sinasc_2024.parquet](../../data/processed/sinasc_2024.parquet); uma linha por nascimento; DTNASC em 2024. Residência: CODMUNRES (código IBGE do município; prefixos de UF 31=MG, 32=ES, 33=RJ, 35=SP); capital 355030. Recortes sobrepostos não se somam. Definições oficiais dos campos: [dicionário local](../../docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md). Escolhas metodológicas do estudo, não definições oficiais — elegíveis: gestação única, peso 500–6.000 g, meses 1–3 (T=1) ou 4–6 (T=0); covariáveis não filtradas. Exclusões sequenciais: qualidade essencial → múltiplas → peso fora da faixa → meses 7–9. As três últimas são exclusões da população analítica, não ausência/invalidade.

**Entrega e validação.** CSVs UTF-8/BOM, separador “;”, decimal ponto; chaves recorte_id e (recorte_id, variavel). Qualidade/retenção: denominador total; proporções T: elegíveis; baixo peso (<2.500 g): cada grupo, apenas descritivo. Seis recortes, contagens, percentuais, capital ⊂ SP ⊂ Sudeste e abertura dos três arquivos conferidos.

**Próximo passo:** validar manualmente o recorte com a orientadora e revisar temporalidade das covariáveis e identificação causal. Preenchimento não resolve confundimento, seleção de nascidos vivos ou leakage. População causal ainda não aprovada; nenhum modelo executado.
