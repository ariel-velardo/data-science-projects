# Esqueleto do artigo — não é o artigo completo

Título provisório: **Início do pré-natal e baixo peso ao nascer no SINASC 2024: predição, estimação ajustada e heterogeneidade exploratória**.

Os números devem ser retirados de [RESULTADOS_PRINCIPAIS.md](../RESULTADOS_PRINCIPAIS.md); referências completas em [REFERENCIAS_CENTRAIS.md](../literature/REFERENCIAS_CENTRAIS.md). O texto final será redigido após adequação às normas da disciplina.

| Seção | Objetivo e argumentos | Resultados que entram | Referências associadas | Figuras/tabelas candidatas |
|---|---|---|---|---|
| Resumo | Pergunta, fonte, métodos, conclusão condicional | N bruto/analítico; C1/C2; gate sensível da heterogeneidade | Sem citações, conforme normas | Nenhuma |
| 1. Introdução | Relevância do baixo peso e do início do pré-natal; formular pergunta associativa | Dimensão nacional e lacuna de interpretação | Vale; Falcão | Nenhuma |
| 2. Revisão de literatura | Relacionar assistência, qualidade SINASC e distinguir predição/causalidade | Achados de literatura sem comparar diretamente magnitudes incompatíveis | Vale; Falcão; Bonilha; Ranjbar | Quadro curto de estudos e diferenças de desenho |
| 3. Dados | Fonte oficial, unidade, T/Y/X, seleção e qualidade | Fluxo de exclusões, T1/T0, prevalência | Ministério da Saúde; Bonilha | Fluxo; perfil dos grupos; dicionário como suplemento |
| 4. Metodologia | SQL/Parquet, benchmark, propensity, AIPW, cross-fitting, clusters e DR-Learner | Protocolos congelados; sem números de resultado nesta seção | Funk; Petersen; Austin; Chernozhukov; Cameron; Chiang; Kennedy | SMD e overlap como diagnósticos; esquema das etapas |
| 5. Resultados | Separar descrição, predição, contraste ajustado e heterogeneidade | ROC-AUC/AP/Brier; associação bruta; C1/C2 e ICs; robustez; CATE e gate | Referências metodológicas apenas quando necessário | Tabela principal; ROC; AIPW; geografia; distribuição CATE |
| 6. Discussão | Interpretar estabilidade sem comprovação causal; explicar revisão do gate | Pequenas mudanças entre modelos/partições; instabilidade dos perfis | Vale; Falcão; Funk; Kennedy; Snowden | Comparação prevista versus externa como suplemento |
| 7. Limitações | Confundimento, seleção, temporalidade, mensuração e dependência | Ausência de identificação de benefício individual; alcance dos ICs | Snowden; Bonilha; Petersen; Cameron | Quadro de limitações e implicações |
| 8. Conclusão | Responder à pergunta com cautela e destacar reprodutibilidade | Contraste ajustado exploratório; heterogeneidade sensível; causalidade não provada | Sem introduzir novos estudos | Nenhuma |
| Referências | Padronizar conforme instrução da disciplina | Seleção central e documentação oficial | As 12 referências centrais, usando apenas as efetivamente citadas | Não se aplica |

Material disponível: cinco notebooks executados, dez gráficos no HTML, dicionário das 62 colunas, síntese, metodologia e fichas curtas. Não incluir todas as sensibilidades no corpo: manter as necessárias para sustentar a conclusão e encaminhar o restante ao suplemento, preservando os gates.

Não escrever que antecipar o cuidado causa a redução estimada, que um CATE negativo prova benefício individual ou que o controle é ausência de pré-natal. `CAUSALIDADE_PROVADA = NAO`.
