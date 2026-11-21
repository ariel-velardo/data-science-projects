# Relatório de análises estatísticas (SINASC 2024)

Relatório das análises estatísticas do estudo sobre o início do pré-natal e o baixo peso ao nascer no município de São Paulo, em 2024. São 10 páginas, organizadas em seis seções:

1. pergunta, dados e população: fluxo de seleção, exposição, desfechos e informações ausentes;
2. peso ao nascer como variável contínua: teste t de Welch e ANOVA de Welch;
3. regressão logística para baixo peso:
   - desfechos e codificação;
   - dicionário das variáveis;
   - equação do modelo;
   - coeficientes e razões de chances com IC;
   - avaliação preditiva;
   - interpretabilidade por valores SHAP;
4. ponderação por sobreposição (ATO): escore de propensão, pesos, balanço, população-alvo e incerteza por bootstrap;
5. limitações;
6. síntese dos resultados.

Cada análise traz a justificativa, o procedimento, o resultado e a interpretação. Cada figura é seguida de um parágrafo de leitura que explica o objetivo, o que representam eixos, cores e marcadores, o padrão observado, a interpretação e o que a figura não permite concluir.

| Arquivo | Conteúdo |
|---|---|
| [RELATORIO_ANALISES_ESTATISTICAS_SINASC_2024.pdf](RELATORIO_ANALISES_ESTATISTICAS_SINASC_2024.pdf) | relatório em PDF (A4), gerado a partir de HTML |
| [main.tex](main.tex) | fonte LaTeX do mesmo conteúdo, a compilar com pdfLaTeX; ver a situação da compilação abaixo |
| [figuras/](figuras/) | as cinco figuras do relatório, em PDF vetorial (usado pelo `main.tex`) e em PNG de alta resolução |
| [historico/](historico/README.md) | versões de trabalho anteriores, preservadas para rastreabilidade; não fazem parte do material atual |

## Origem dos números e das figuras

Todos os valores vêm das saídas salvas dos notebooks [03_estimacao_ato.ipynb](../../notebooks/principal/03_estimacao_ato.ipynb), [05_temporalidade_prenatal.ipynb](../../notebooks/principal/05_temporalidade_prenatal.ipynb) e [06_analise_preditiva_e_peso.ipynb](../../notebooks/principal/06_analise_preditiva_e_peso.ipynb). O fluxo de seleção vem também da [comparação de recortes de 2024](../../outputs/qualidade_geografica_2024/RECOMENDACAO_RECORTE.md). A conferência automática encontrou cada número do texto nessas saídas, no PDF e no LaTeX.

As figuras foram exportadas da especificação Plotly salva nas saídas dos notebooks, sem recálculo. Para a página A4, mudou só a apresentação:
- largura menor, para que os textos fiquem legíveis;
- título e notas internas retirados, porque passam para a legenda da figura.

Os gráficos complementares, como as curvas ROC e de precisão × sensibilidade, a importância SHAP em barras, as razões de chances e os riscos do ATO, continuam nos notebooks.

## Compilação do LaTeX

O `main.tex` usa os pacotes `amsmath`, `tcolorbox` (`most`), `xcolor` (`table`), `needspace`, `graphicx` e `hyperref`, todos disponíveis no Overleaf.

**A compilação ainda não foi executada**, porque não havia distribuição LaTeX no ambiente de preparo. A fonte passou por validação estática:
- chaves e ambientes balanceados;
- equações `\[ \]` pareadas;
- cada comando conferido contra a lista de comandos conhecidos, o que detecta erros de digitação como `\qquadY`;
- caracteres compatíveis com pdfLaTeX;
- figuras existentes.

O PDF de referência é o gerado a partir de HTML. A compilação em LaTeX permanece pendente.

As fontes citadas no relatório limitam-se à origem dos dados (SINASC), à definição de baixo peso (OMS) e ao método de ponderação por sobreposição (Li, Morgan e Zaslavsky, 2018), já registrados em [sources/FONTES_OFICIAIS.md](../sources/FONTES_OFICIAIS.md) e na bibliografia do [pacote acadêmico](../sp_capital_ato/README.md).
