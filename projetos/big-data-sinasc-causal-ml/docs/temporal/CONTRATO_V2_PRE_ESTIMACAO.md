# Contrato V2 — congelamento metodológico e diagnóstico pré-estimação

**Estado:** `DECISAO_V2_PRE_ESTIMACAO_CONGELADA` · `SUPORTE_V2_SINALIZADO` · `NENHUM_EFEITO_V2_ESTIMADO` · `V1_PRESERVADA` · `SEM_RESULT_SHOPPING` · `PRONTO_PARA_REVISAO_HUMANA_ANTES_DOS_EFEITOS`.

Documento complementar. A fonte de verdade das decisões é o notebook [09d_contrato_v2_pre_estimacao.ipynb](../../notebooks/09d_contrato_v2_pre_estimacao.ipynb). Este texto as resume para revisão e não acrescenta decisões. **Não houve commit**: o congelamento é documental e de artefatos, e a revisão humana decide sobre o commit.

## 1. Registro

| Campo | Valor |
| --- | --- |
| Contrato gravado em | 2026-10-01 13:39:46, antes de qualquer ajuste de propensity da V2 (nenhum checkpoint existia) |
| Branch / HEAD | `feature/expansao-temporal-sinasc` / `61efda505592ed80a352322b3dee9d80f894f6ef` |
| Artefato | `outputs/temporal/v2_pre_estimacao/contrato_v2_congelado.json` |
| SHA-256 do contrato (conteúdo científico) | `2174989c33b338f7215270050969efda1d3d8e09661aee97b1da547185927d0b` |
| SHA-256 dos critérios de gate | `84754340982770be7a6c2d545ed5013f36bdcfc7fbbeed071ce9ee57d106e516` |
| Código | `src/v2_pre_estimacao.py`; testes em `tests/test_v2_pre_estimacao.py` |
| Notebook 09c | `15801476ad37feb82d9b63cf4a5c38fb4c9096dcfc119bddea21823de6cffb99` |
| `criterios_gates_pre_v2.json` | `86bd1133623043b824ba6c4074e01927d52764e60eb0cab3f764a2bbcd9909ef` |
| `gates_pre_v2_resultados.json` | `df8acd73fa4c4333f69289b9e68328e47d285978032e89715743886f2fec8a41` |
| `manifesto_pre_v2.json` | `387d599acd6089fccc72ac4318c5618ac376086d22b7da2b49050b7798ad4d40` |
| `populacoes_candidatas_pre_v2.csv` | `f2faece1c77c1afc99b5dfc6889cb69ee68b63caac6be533f7f8c4d6620fc674` |
| `src/auditoria_pre_v2.py` | `0a0d67b7763df7a4a513aee3904420f04d8a902fd812421b44afd0eac394c086` |

O contrato não é regravado: uma reexecução falha se o conteúdo científico mudar e preserva o carimbo original.

## 2. Problema da V1

A V1 (`T=1` MESPRENAT 1–3; `T=0` 4–9) classifica o tratamento com o mês de início registrado ao nascimento. Pertencer aos meses 7–9 exige que a gestação tenha durado o suficiente para alcançá-los. Isso desalinha o tempo zero e a classificação e usa informação futura de modo desigual entre os braços (família do *immortal time bias*; *preterm delivery bias* / *gestational age bias* para o baixo peso). A V1 permanece intacta e passa a ser lida como **contraste observacional padronizado histórico**.

## 3. Evidência

**Literatura localizada e lida:**

- Vachuska (2025, p. 3; PDF conferido): o truncamento associa mecanicamente o início tardio a menos prematuridade, e o baixo peso "has the same issue". Na p. 7, o autor descreve a seleção por nascido vivo como *collider*.
- Hernán & Robins, *What If* (versão de 21/11/2025; PDF conferido): §22.4 (tempo zero, p. 315) e Fine Point 22.5 (períodos de carência, p. 317).
- Fichamentos da biblioteca do projeto: Wilcox 2011, Schisterman 2009 e Snowden 2018 (não ajustar por IG); Petersen 2012 (restringir muda o estimando); Crump 2009; Austin & Stuart 2015 (0,10 como convenção); Szwarcwald 2019; Bonilha 2018 e `DIVERGENCIAS_ENCONTRADAS.md` D1 (perdas fetais); a síntese do projeto recomenda o contraste "≤ 3º vs. 4º–6º mês".
- Textos de Schnitzer, Tyson e Hutcheon & Savitz não foram localizados localmente e **não são citados**. Os SHA-256 das fontes estão no contrato.

**09c (reconciliado):** M1 é uma fração de nascimentos elegíveis com IG válida (29,26 milhões), não de controles. Em L1, M1 vale 1,35% em A (393.831 nascimentos), 0,007% em B (2.115) e um único nascimento em C. O G2 é imaterial (38 registros em 27,9 milhões; código `10` em 2.607 registros de 2014). G1, G3 e G4 estão sinalizados; G5 e G6 aprovados; G7 leva B e C à discussão e mantém D pendente. O critério P1 (monotonicidade, D1) **falhou nos 11 anos** e continua registrado: a regra era mais forte que o padrão observado, o que não elimina a restrição mecânica nas gestações curtas.

## 4. Decisão

| Formulação | Definição | Papel |
| --- | --- | --- |
| A | 1–3 vs 4–9 | `V1_A_PRESERVADA_COMO_HISTORICA` |
| B | 1–3 vs 4–6; população V1 com MESPRENAT 1–6 | `V2_PRINCIPAL_B_1A3_VS_4A6` |
| C | 1–3 vs 4–5; população V1 com MESPRENAT 1–5 | `SENSIBILIDADE_V2_C_1A3_VS_4A5` |
| D | *landmark* no fim do 3º mês | `LANDMARK_D_PENDENTE` |

- **Justificativa de B.** B reduz quase completamente a região empiricamente vulnerável ao problema temporal identificado pelo 09c, preservando aproximadamente 86,8% dos controles da V1. Nenhum efeito de B ou C foi observado.
- **Papel de C.** C reduz marginalmente mais esse componente, mas remove 672.861 controles adicionais. É a sensibilidade mais restritiva.
- **Bloqueio de D.** Nenhuma variável distingue "ainda não/nunca iniciou" de "desconhecido": `99`, vazio, `CONSPRENAT=0` e `KOTELCHUCK` não destravam D.
- **Limitação fundamental.** B reduz substancialmente o componente empiricamente identificado de incompatibilidade temporal, sem eliminar todas as ameaças de identificação: classificação retrospectiva, informação futura, confundimento residual, seleção por nascido vivo, missing diferencial e mensuração de `MESPRENAT`.

## 5. Especificação congelada

- **Estimandos (distintos):**
  - B: contraste médio padronizado de risco de BPN (em pp) entre início 1–3 e 4–6, na população elegível B de cada ano.
  - C: o mesmo contraste com 4–5 como comparador, na população C.
  - Restringir o controle muda população, comparador e estimando.
- **Y:** `PESO < 2.500 g` (qualidade 500–6.000 g), inalterado. Não há ajuste por IG, consultas, parto, Apgar ou `KOTELCHUCK`.
- **X:** as sete dimensões congeladas. Perdas fetais é mantida; a sensibilidade sem ela fica para o futuro.
- **Missing:** `99`, vazio, `10` e inválidos ficam fora de T, sem imputação e sem reclassificação.
- **Janelas:** principal 2014–2024 (v1.1); sensibilidade 2018–2024 (v1). Sem *pooled*.
- **Nuisances futuros:** C1, C2 e C3 históricos, sem tuning, reajustados do zero em cada população, ano e partição. É proibido reutilizar predições da V1 ou os propensities diagnósticos.
- **Ajuste cruzado futuro:** 3 partições por `2T+Y`, seed 20240925.
- **Trimming futuro:** principal sem trimming; sensibilidade [0,05; 0,95]; [0,01; 0,99] apenas como diagnóstico.
- **Inferência futura:** erro-padrão agrupado por `CODMUNRES` com t(G−1) como leitura principal prudente; iid histórico como referência.
- **Diagnóstico desta rodada:**
  - logística L2, `C=1`, sete X e pré-processamento histórico, seed 20240925;
  - **5 partições estratificadas por T** — o contrato do notebook 08, escolhido porque esta etapa é diagnóstica, dispensa Y e é reconciliável com A;
  - em 2024, ordem física certificada, agora explícita (`ORDER BY file_row_number`), porque a consulta filtrada sem `ORDER BY` mostrou ordem não determinística.

## 6. Gates de viabilidade (fixados antes dos resultados)

- **BLOQUEADO:**
  - braço ausente;
  - partição inválida;
  - propensity não finito ou fora de (0, 1);
  - vazamento;
  - não convergência;
  - ESS/N < 0,20 em algum braço;
  - contrato de dados violado (hash, chave, datas, N).
- **SINALIZADO:**
  - maior |SMD| ponderado > 0,10;
  - fora de [0,05; 0,95] > 10%;
  - ESS/N < 0,50.
- **APROVADO:** caso contrário.
- **Consolidação:** pior status entre os anos. `SUPORTE_V2` = status de B; C é reportado à parte. Anos sinalizados permanecem.

## 7. Resultados do diagnóstico (sem efeito)

| | A (referência) | B | C |
| --- | --- | --- | --- |
| Controles por ano | 309.525–577.127 | 265.169–501.781 | 223.149–424.612 |
| Proporção tratada | 78,6%–86,3% | 80,8%–88,0% | 83,3%–89,7% |
| AUC OOF | 0,663–0,691 | 0,661–0,690 | 0,655–0,684 |
| ESS/N controles | 0,676–0,752 | 0,664–0,749 | 0,672–0,761 |
| ESS/N tratados | ≥ 0,976 | ≥ 0,982 | ≥ 0,987 |
| Maior \|SMD\| bruto → ponderado | 0,38–0,44 → 0,014–0,023 | 0,37–0,44 → 0,016–0,024 | 0,36–0,43 → 0,016–0,023 |
| Fora de [0,01; 0,99] | 0 | 0 | 0 |
| Fora de [0,05; 0,95] | 3,9%–6,6% | 6,2%–10,6% | 8,2%–14,9% |
| Peso máximo dos controles | 38–53 | 43–60 | 47–65 |
| Status por ano | 11 `APROVADO` | 10 `APROVADO`; 2024 `SINALIZADO` | 2014–2016 `APROVADO`; 2017–2024 `SINALIZADO` |

- As caudas estão inteiramente acima de 0,95 e são dominadas por tratados (peso ≤ 4,2). Elas crescem com a proporção tratada, que aumenta ao restringir o comparador.
- Nenhum ano foi bloqueado: B e C permanecem estatisticamente viáveis.
- O código novo reproduz o OOF certificado do notebook 08 para A com diferença máxima 0,0 em 2014 e 2024.
- **1ª execução (com ajustes):** 64 min no total (diagnóstico de 58 min; cerca de 19 s por partição; 110 ajustes novos de B e C, mais 10 do controle positivo). Memória: RSS máximo de 1,9 GB e pico do processo de 2,7 GB.
- **Reexecução de verificação:** 29 min. Os 120 checkpoints foram reutilizados com o contrato validado, o contrato manteve o carimbo original e as 33 linhas anuais saíram idênticas. O manifesto e `execucao_v2.*` refletem essa reexecução; o tempo de cada ajuste original fica preservado nos checkpoints (`particoes_v2.*`).
- Os checkpoints somam 240 arquivos e 195 MiB em `data/interim/v2_pre_estimacao/`.

## 8. Proibições

- AIPW B, C ou D; modelos de desfecho; CATE; tuning; procurar modelo melhor; decisão baseada em efeito.
- Alterar V1, 09, 09b ou 09c.
- Ajustar por IG ou restringir a termo.
- Tratar `99` ou vazio como "sem pré-natal"; usar `KOTELCHUCK`.
- Remover anos sinalizados.
- Commit ou push nesta rodada.

## 9. Documentos que precisarão de correção futura (não editados)

`MESPRENAT=99` foi reverificado: o Manual DNV 2022 (SHA-256 `5956ea4d…`, idêntico ao do 09c) define a categoria "Ignorado", mas o número 99 só aparece em códigos CID Q99.x. Registro: **`CODIFICACAO_OPERACIONAL_OBSERVADA`**, não definição oficial.

Documentos a corrigir, com revisão humana:

- `docs/sources/FONTES_OFICIAIS.md` (l. 33 e 37);
- `docs/playbooks/ESTADO_ATUAL.md` (l. 97);
- `docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md` (l. 58);
- `src/entrega.py` (l. 43 e 81);
- `src/auditoria_dados.py` (l. 455);
- notebooks 02 e 06 (via errata);
- `docs/temporal/EXPANSAO_TEMPORAL.md` e `PLANO_NOTEBOOK_09.md`, para acrescentar a leitura histórica da V1;
- os resumos da biblioteca externa sobre o kappa de perdas fetais.

`docs/architecture/BASELINE_PRE_REFATORACAO.md` é um registro histórico e não deve ser corrigido.

## 10. Próxima fase (após revisão humana)

1. Decidir o commit.
2. Retomar a frente 09b, pausada e preservada.
3. Implementar o AIPW V2 reproduzindo primeiro a V1 (A) em 2024 e, depois, estimar B e C ano a ano com C1/C2/C3. Anos `BLOQUEADO` não são estimados; os `SINALIZADO` (B 2024; C 2017–2024) são estimados e reportados com a sinalização.
4. Seguir o roadmap: sem perdas fetais, E-value, subgrupos, COVID-19, quebras temporais, D, PIG, CATE e meta-learners.
