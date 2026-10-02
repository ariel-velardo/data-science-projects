# Tabelas de resultados

Cinco tabelas finais. Os valores foram extraídos de `outputs/temporal/estimacao_v2/` (V2), `outputs/temporal/estimativas/aipw_anual.csv` (V1) e `outputs/temporal/tabelas/descritiva_anual.csv`. As versões em CSV, sem arredondamento, estão em [outputs/entrega/tabelas/](../../outputs/entrega/tabelas/).

**Convenções:**

- p.p. = pontos percentuais;
- contraste = risco padronizado de BPN com início precoce menos o risco com início tardio, de modo que valores negativos indicam menor risco no início precoce;
- IC95% municipal = erro-padrão agrupado por município de residência, com crítico t(G − 1);
- estimativas sem recorte de suporte, salvo na Tabela 4;
- arredondamento em 3 casas decimais; diferenças calculadas antes do arredondamento.

## Tabela 1 — Perfil da base por ano

<!-- T1_INICIO -->
| Ano | N bruto | N analítico (A) | Y = 1 (%) | Início precoce, A (%) | N B | Início precoce, B (%) | N C |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2014 | 2.979.259 | 2.691.119 | 6,93 | 78,55 | 2.615.773 | 80,82 | 2.538.604 |
| 2015 | 3.017.668 | 2.745.846 | 6,98 | 79,40 | 2.673.272 | 81,56 | 2.599.919 |
| 2016 | 2.857.800 | 2.626.594 | 7,04 | 80,27 | 2.560.827 | 82,33 | 2.492.767 |
| 2017 | 2.923.535 | 2.695.676 | 7,03 | 81,02 | 2.630.828 | 83,01 | 2.562.927 |
| 2018 | 2.944.932 | 2.734.473 | 7,02 | 81,74 | 2.672.423 | 83,63 | 2.606.245 |
| 2019 | 2.849.146 | 2.645.383 | 7,19 | 82,40 | 2.586.743 | 84,27 | 2.524.898 |
| 2020 | 2.730.145 | 2.535.311 | 7,09 | 82,48 | 2.476.058 | 84,45 | 2.415.861 |
| 2021 | 2.677.101 | 2.481.267 | 7,37 | 83,91 | 2.425.844 | 85,83 | 2.371.495 |
| 2022 | 2.561.922 | 2.397.626 | 7,85 | 84,18 | 2.344.255 | 86,10 | 2.291.516 |
| 2023 | 2.537.576 | 2.389.346 | 7,89 | 85,23 | 2.340.125 | 87,02 | 2.291.075 |
| 2024 | 2.389.325 | 2.251.570 | 7,89 | 86,25 | 2.207.214 | 87,99 | 2.165.194 |
| **Total** | **30.468.409** | **28.194.211** | — | — | **27.533.362** | — | **26.860.501** |
<!-- T1_FIM -->

- **N analítico (A):** gestação única, `MESPRENAT` 1–9 conhecido e 500 ≤ `PESO` ≤ 6.000 g.
- **Y = 1 (%) e início precoce (A):** calculados sobre o N analítico (A).
- **Início precoce (B):** proporção de T = 1 na população B (meses 1–6).

## Tabela 2 — Formulação B (principal), sem recorte

T = 1: início no 1º–3º mês; T = 0: início no 4º–6º mês.

<!-- T2_INICIO -->
| Ano | N | C1 (p.p.) | IC95% municipal C1 | C2 (p.p.) | C3 (p.p.) | Suporte (09d) |
| --- | ---: | ---: | :---: | ---: | ---: | --- |
| 2014 | 2.615.773 | −0,936 | −1,046 a −0,827 | −0,859 | −0,853 | Aprovado |
| 2015 | 2.673.272 | −1,003 | −1,111 a −0,896 | −0,913 | −0,920 | Aprovado |
| 2016 | 2.560.827 | −1,090 | −1,230 a −0,949 | −0,994 | −0,990 | Aprovado |
| 2017 | 2.630.828 | −1,126 | −1,268 a −0,984 | −1,044 | −1,036 | Aprovado |
| 2018 | 2.672.423 | −1,256 | −1,409 a −1,103 | −1,177 | −1,169 | Aprovado |
| 2019 | 2.586.743 | −1,210 | −1,339 a −1,082 | −1,122 | −1,109 | Aprovado |
| 2020 | 2.476.058 | −1,066 | −1,210 a −0,922 | −0,992 | −0,989 | Aprovado |
| 2021 | 2.425.844 | −1,252 | −1,394 a −1,110 | −1,171 | −1,166 | Aprovado |
| 2022 | 2.344.255 | −1,524 | −1,671 a −1,377 | −1,433 | −1,432 | Aprovado |
| 2023 | 2.340.125 | −1,429 | −1,570 a −1,288 | −1,339 | −1,332 | Aprovado |
| 2024 | 2.207.214 | −1,480 | −1,626 a −1,335 | −1,373 | −1,361 | **Sinalizado** |
<!-- T2_FIM -->

- **C1:** propensão logística + desfechos logísticos. **C2:** propensão logística + desfechos HGB. **C3:** propensão HGB + desfechos HGB.
- **Suporte "Sinalizado":** mais de 10% dos registros com escore de propensão fora de [0,05; 0,95], pelo critério fixado no notebook 09d antes da estimação. O ano não é bloqueado nem removido.

## Tabela 3 — Formulação C (sensibilidade), sem recorte

T = 1: início no 1º–3º mês; T = 0: início no 4º–5º mês. **É um estimando diferente de B.**

<!-- T3_INICIO -->
| Ano | N | C1 (p.p.) | IC95% municipal C1 | C2 (p.p.) | C3 (p.p.) | Suporte (09d) |
| --- | ---: | ---: | :---: | ---: | ---: | --- |
| 2014 | 2.538.604 | −0,851 | −0,963 a −0,740 | −0,773 | −0,770 | Aprovado |
| 2015 | 2.599.919 | −0,953 | −1,066 a −0,840 | −0,864 | −0,872 | Aprovado |
| 2016 | 2.492.767 | −1,018 | −1,154 a −0,881 | −0,931 | −0,926 | Aprovado |
| 2017 | 2.562.927 | −1,028 | −1,171 a −0,884 | −0,953 | −0,941 | **Sinalizado** |
| 2018 | 2.606.245 | −1,179 | −1,333 a −1,025 | −1,110 | −1,104 | **Sinalizado** |
| 2019 | 2.524.898 | −1,160 | −1,298 a −1,021 | −1,077 | −1,067 | **Sinalizado** |
| 2020 | 2.415.861 | −0,963 | −1,112 a −0,814 | −0,892 | −0,888 | **Sinalizado** |
| 2021 | 2.371.495 | −1,183 | −1,327 a −1,038 | −1,104 | −1,101 | **Sinalizado** |
| 2022 | 2.291.516 | −1,487 | −1,633 a −1,341 | −1,411 | −1,410 | **Sinalizado** |
| 2023 | 2.291.075 | −1,333 | −1,479 a −1,187 | −1,240 | −1,236 | **Sinalizado** |
| 2024 | 2.165.194 | −1,330 | −1,475 a −1,184 | −1,215 | −1,217 | **Sinalizado** |
<!-- T3_FIM -->

## Tabela 4 — Recorte de suporte (*trimming*), C1

Recorte: mantêm-se apenas registros com escore de propensão em [0,05; 0,95]. Diferença = estimativa com recorte − estimativa sem recorte; valor negativo = contraste mais negativo após o recorte.

<!-- T4_INICIO -->
| Ano | Formulação | Excluído (%) | C1 sem recorte (p.p.) | C1 com [0,05; 0,95] (p.p.) | Diferença (p.p.) |
| --- | :---: | ---: | ---: | ---: | ---: |
| 2014 | B | 6,22 | −0,936 | −0,931 | +0,005 |
| 2015 | B | 6,30 | −1,003 | −0,999 | +0,004 |
| 2016 | B | 7,47 | −1,090 | −1,094 | −0,005 |
| 2017 | B | 8,12 | −1,126 | −1,114 | +0,012 |
| 2018 | B | 8,50 | −1,256 | −1,238 | +0,018 |
| 2019 | B | 8,34 | −1,210 | −1,208 | +0,002 |
| 2020 | B | 8,14 | −1,066 | −1,060 | +0,006 |
| 2021 | B | 9,28 | −1,252 | −1,285 | −0,033 |
| 2022 | B | 8,54 | −1,524 | −1,475 | +0,049 |
| 2023 | B | 9,75 | −1,429 | −1,496 | −0,067 |
| 2024 | B | 10,56 | −1,480 | −1,536 | −0,055 |
| 2014 | C | 8,14 | −0,851 | −0,865 | −0,014 |
| 2015 | C | 8,22 | −0,953 | −0,951 | +0,002 |
| 2016 | C | 9,47 | −1,018 | −1,044 | −0,026 |
| 2017 | C | 10,41 | −1,028 | −1,023 | +0,004 |
| 2018 | C | 10,99 | −1,179 | −1,143 | +0,036 |
| 2019 | C | 10,99 | −1,160 | −1,167 | −0,008 |
| 2020 | C | 10,80 | −0,963 | −0,953 | +0,010 |
| 2021 | C | 12,64 | −1,183 | −1,217 | −0,034 |
| 2022 | C | 12,05 | −1,487 | −1,455 | +0,032 |
| 2023 | C | 13,74 | −1,333 | −1,429 | −0,096 |
| 2024 | C | 14,94 | −1,330 | −1,412 | −0,083 |
<!-- T4_FIM -->

- **Maior mudança absoluta:** 0,067 p.p. em B (2023) e 0,096 p.p. em C (2023).
- **Registros fora de [0,01; 0,99]:** nenhum, em todos os anos e formulações.
- **ICs após o recorte:** nenhum passa a incluir zero.

## Tabela 5 — Comparação resumida A, B e C

| | **A — V1 histórica** | **B — V2 principal** | **C — sensibilidade** |
| --- | --- | --- | --- |
| Definição de T = 1 | `MESPRENAT` 1–3 | `MESPRENAT` 1–3 | `MESPRENAT` 1–3 |
| Definição de T = 0 | `MESPRENAT` 4–9 | `MESPRENAT` 4–6 | `MESPRENAT` 4–5 |
| N total (11 anos) | 28.194.211 | 27.533.362 | 26.860.501 |
| C1, faixa 2014–2024 (p.p.) | −0,849 (2014) a −1,388 (2022) | −0,936 (2014) a −1,524 (2022) | −0,851 (2014) a −1,487 (2022) |
| C1 em 2024 (p.p.) | −1,341 | −1,480 | −1,330 |
| Maior limite superior do IC95% municipal (C1) | −0,744 | −0,827 | −0,740 |
| Anos com suporte sinalizado | nenhum | 2024 | 2017–2024 |
| Exposição ao problema temporal | **alta**: o comparador inclui 7º–9º mês, acessível apenas a gestações longas | **reduzida**, não eliminada | **reduzida um pouco mais**, com perda de controles |
| Interpretação | Contraste observacional padronizado histórico; controle positivo da V2 | **Resultado principal**: contraste AIPW ajustado sob hipóteses de identificação | Verifica se a conclusão depende do 6º mês no comparador |

**Leitura:** as três formulações apontam na mesma direção e têm o mesmo desenho temporal. Elas **não** são o mesmo estimando, e as diferenças entre elas não devem ser lidas como "correção" de uma pela outra. Os valores de A vêm do notebook 09 (V1). Em 2024, A foi reproduzido pelo novo código com diferença máxima de 2,2 × 10⁻¹⁶ (141/141 checagens).
