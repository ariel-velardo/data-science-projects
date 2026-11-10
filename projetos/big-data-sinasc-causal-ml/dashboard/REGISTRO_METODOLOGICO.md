# Registro metodológico do painel

Registra como as evidências já produzidas pelo projeto foram transformadas em agregados para o painel. Não há análise nova: nenhum modelo foi ajustado, nenhum bootstrap foi executado e nenhum Parquet foi lido.

## Artefato

| Item | Definição |
|---|---|
| Artefato | `dist/sinasc_dashboard_ipt.html` e `dist/dados_painel.json` |
| Granularidade | agregados por recorte, ano, grupo, categoria ou faixa; nenhum registro individual |
| Chave | definida por bloco em `dados_painel.json`, por exemplo `ano` em `serie` e `id` em `recortes` |
| Validação | `tests/test_integridade.py` e `verificacao/verificar_navegador.mjs` |
| Referência de origem | `fd0d319e4b77dfa973b87f1a3c6fc6872968225e` |
| Proveniência | `dist/MANIFESTO_PROVENIENCIA.json`, com SHA-256 de cada fonte e saída |
| Rastreabilidade | `dist/MATRIZ_RASTREABILIDADE.md` |

## Fontes

- Saídas salvas dos cinco notebooks de `notebooks/principal/`.
- `outputs/qualidade_geografica_2024/`: dois CSVs e a recomendação de recorte.
- `docs/sp_capital_ato/RESUMO_PARA_REDACAO.md`: conferência cruzada e detalhamento dos registros sem início informado.
- `docs/GUIA_REVISAO_MIKE.md`, `docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md`, `docs/methodology/DAG_INICIAL.md` e `fig4_dag.tex`: definições, leitura e diagrama.
- `logo_ipt.pdf` do pacote Overleaf: vetor do logotipo. O arquivo é idêntico nos pacotes das Etapas 1 e 2.

## As 11 figuras dos notebooks

Todas foram reconstruídas a partir de valores extraídos; o JSON original das figuras não é embutido.

| Notebook e célula | Figura | No painel |
|---|---|---|
| 01, célula 18 | Mês de início válido por ano | `b_mesprenat` |
| 01, célula 21 | Grupos por ano e recorte | `b_serie_grupos` |
| 02, célula 15 | Balanço antes do ajuste | `d_smd` |
| 02, célula 22 | Escore fora da partição | `d_ps`, modelo diagnóstico |
| 03, célula 15 | Escore e pesos ATO | `d_ps`, modelo final |
| 03, célula 18 | Balanço antes e depois | `d_love` e `d_conjugal` |
| 03, célula 23 | Riscos e diferenças | `e_riscos`, `e_difs` e `a_difs` |
| 04, célula 27 | Diferença ATO por ano | `f_dif` |
| 04, célula 29 | T=0 entre os elegíveis | `f_t0` |
| 05, célula 13 | Início nos meses 4–6 por duração | `g_t0_duracao`, com faixas agrupadas |
| 05, célula 20 | Baixo peso por mês de início | `g_lbw_mes` |

Medidas que estavam em tabelas ou no relatório e ganharam gráfico: comparação dos seis recortes, exclusões sequenciais, mapa de qualidade por variável, funil, composição por mês de início, perfil materno, n efetivo, incerteza da diferença ATO, sensibilidade conjugal, riscos anuais, elegíveis por ano, diagnósticos anuais, baixo peso por duração e seleção pelo filtro de início.

## Transformações

1. Tabelas HTML salvas são lidas com expansão de `rowspan`, e números em formato brasileiro são convertidos.
2. Cada leitura confere título ou cabeçalho esperado.
3. Percentuais de qualidade são arredondados para duas casas; os do perfil materno para uma.
4. O percentual do perfil em "todos os elegíveis" é recalculado como soma das contagens dos dois grupos dividida por 114.694. As contagens permanecem internas à geração.
5. Durações gestacionais são agrupadas em `< 28`, `28–31`, `32–36` e `≥ 37` semanas. Os percentuais dessas faixas são recalculados sobre o denominador da faixa agrupada.
6. Filtros de período na aba de série somam contagens de anos disjuntos e recalculam o percentual sobre os elegíveis do período. Nenhum filtro altera estimativa, risco, intervalo ou diagnóstico.

Não foi necessária nenhuma agregação nova sobre microdados.

## Avaliação de células pequenas

Regra adotada: contagens de 1 a 9 não aparecem; são exibidas como `< 10`.

| Ponto avaliado | Tratamento |
|---|---|
| Histogramas de escore, com caixas de 1 registro | caixas adjacentes unidas até cada grupo ter 0 ou pelo menos 10 registros; contagens não publicadas |
| Perfil materno, com categorias de 3 a 6 registros em T=0 | apenas percentuais com uma casa; sem contagens por categoria, o que evita recuperação por subtração |
| Duração × mês de início | faixas agrupadas; a geração falha se restar célula de 1 a 9 |
| Linhas de incluídos e excluídos | células pequenas como `< 10 (< 1%)`; coluna de duração desconhecida omitida; linhas "7–9" e "ausente" com contagens em múltiplos de 10 e percentuais inteiros, pois a subtração `43 − 40` recuperava a célula suprimida |
| Balanço das covariáveis | SMD publicados com três casas, as mesmas das tabelas dos notebooks; com seis casas, SMD e percentuais identificavam o par exato de contagens em cinco categorias raras |
| Dados embutidos sem uso | removidos `peso_fora_*`, `max_peso_*` e `metodos_ig`, que delimitavam contagens mascaradas ou descreviam um único registro e não apareciam no painel |
| Fora do suporte por ano | valores de 1 a 9 como `< 10` |
| Idades individuais fora de 10–59 anos em 2017, 2022 e 2023 | removidas; só há nota agregada |
| Faixas de "pouca representação" do notebook 02 | descritas qualitativamente; contagens não publicadas |

Riscos residuais aceitos, de baixa severidade:

- Comparar os denominadores de "duração conhecida" com o total revela quantos registros não têm duração informada: 5 em T=1 e 2 em T=0. É uma contagem de campo ausente, sem atributo adicional e sem identificador. Por mês de início o valor não é recuperável, pois o total exato de cada mês não é publicado.
- Mínimo e máximo do escore por grupo e os limites do suporte comum são valores de um único registro. Permanecem por serem o próprio diagnóstico de sobreposição; o escore não vem acompanhado de covariáveis, coeficientes ou identificadores.
- Com percentuais de uma casa e SMD de três casas, as contagens das categorias raras ficam em intervalos, e não em valores únicos.

Filtros não criam novos cruzamentos: selecionam métrica, modelo, covariável ou período. O filtro de período soma somente elegíveis, T=1 e T=0 de anos disjuntos.

Os documentos acadêmicos já entregues citam algumas dessas contagens exatas (por exemplo, 3 gestações com menos de 28 semanas entre os meses 7–9). O painel é mais restritivo por ser um material interativo destinado a circular separadamente.

## Identidade visual

Não foi localizado manual de marca ou paleta oficial do IPT em fonte pública. O logotipo vem do arquivo "IPT_Nova Marca COR" do pacote Overleaf, convertido em SVG sem alterar os traçados. As cores `#123C59` e `#00B3E2` foram lidas desse arquivo. As demais cores são derivações próprias para gráficos, com verificação de contraste e daltonismo, e não devem ser chamadas de paleta oficial.

## Limitações do painel

- Os resultados são os dos notebooks salvos; erros de origem seriam herdados. A conferência cruza notebooks, CSVs e o resumo de redação, mas não reexecuta análises.
- A estimativa principal é associação ajustada na população de sobreposição, e não efeito causal.
- A série anual não tem intervalos de confiança nem testes, e cada ano tem população de sobreposição própria.
- A sensibilidade com situação conjugal não tem intervalo de confiança.
- O DAG é uma hipótese de trabalho já adotada no projeto e não foi validado empiricamente.
- A verificação em navegador cobriu Chrome e Edge em Windows, com larguras emuladas. Não houve teste em aparelhos físicos, nem em Firefox ou Safari.

## Idades extremas

Três registros da série, um em cada ano de 2017, 2022 e 2023, tinham idade fora de 10–59 anos e receberam a imputação pela mediana anual prevista no notebook 04, sem exclusão. O painel omite apenas o valor individual dessas idades. Nenhuma estatística ou denominador foi alterado: os totais anuais do painel são iguais aos dos notebooks 01 e 04, o que é verificado em teste, e o estudo de 2024 não teve imputação.

## Próximo passo

Revisão do conteúdo pela autoria do estudo antes do envio do pacote acadêmico.
