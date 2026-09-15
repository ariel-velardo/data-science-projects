# Auditoria do Calendário Territorial Município-Ano (2007–2019)

## 0. Convenções e escopo

Convenção usada em todo o documento:

- **FATO DA FONTE** — algo explicitamente registrado em arquivo ou texto
  oficial do IBGE (com URL).
- **RESULTADO DA CONSTRUÇÃO** — algo observado ao executar
  `src/constroi_calendario_territorial_ibge.py` sobre os arquivos oficiais.
- **INFERÊNCIA** — interpretação nossa a partir dos dois anteriores.
- **NÃO VERIFICADO** — ponto que não foi possível comprovar nesta tarefa.

Nesta tarefa **não** foi extraído o CEMPRE nacional, **não** foi construído
painel CEMPRE, **não** houve merge causal, seleção de controles, matching,
common support, ATT, event study ou qualquer estimação, e **nenhum** cadastro
causal, contrato ou arquivo da Fase 0 CEMPRE foi alterado.

**Estado Git de partida** (conferido antes de qualquer alteração): branch
`main`, `HEAD` = `origin/main` = `1316709788de4af44b4aba20d28de176d1266396`;
pendências preexistentes, todas da Fase 0 CEMPRE e exatamente as esperadas:
`M .gitignore`, `?? data/raw/ibge/cempre/`,
`?? docs/data/AUDITORIA_PILOTO_CEMPRE.md`,
`?? src/constroi_painel_cempre.py`, `?? tests/test_constroi_painel_cempre.py`.

---

## 1. Objetivo

Construir, de forma reproduzível e auditável, uma tabela oficial
município-ano para 2007–2019 que responda:

> Para cada código municipal IBGE que aparece no universo territorial de
> 2007–2019, o município existia oficialmente naquele ano?

## 2. Por que o calendário é necessário

A auditoria do CEMPRE (`AUDITORIA_DISPONIBILIDADE_CEMPRE.md`, seções 6.4 e 7)
mostrou que a Tabela 1685 retorna **uma linha** com `V="..."` para Pescaria
Brava/SC (`4212650`) em 2007. O símbolo `...` ("dado numérico não
disponível") não informa sua causa. A especificação
(`ESPECIFICACAO_PAINEL_CEMPRE.md`, seções 6.2 e 7) exige que
`status_territorial` venha de uma fonte territorial oficial independente,
separada de `status_valor_api`, para distinguir:

- **A.** município existia, mas o dado CEMPRE está indisponível;
- **B.** município oficialmente não existia naquele ano.

---

## 3. Fontes oficiais investigadas

Data de acesso de todas as fontes abaixo: **2026-09-15** (downloads DTB às
03:08:26 UTC). Buscas na web serviram apenas para localizar URLs oficiais.

| Fonte | URL | Cobertura observada | Papel |
|---|---|---|---|
| **DTB — Divisão Territorial Brasileira** (IBGE) | `https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/divisao_territorial/` | pastas anuais 1940…2025, **com arquivo para cada ano de 2007 a 2019** | **fonte escolhida** |
| Página do produto DTB | `https://www.ibge.gov.br/geociencias/organizacao-do-territorio/estrutura-territorial/23701-divisao-territorial-brasileira.html` | — | identificação do produto (acesso por robô retornou HTTP 403) |
| Leia-me DTB 2013 | `…/divisao_territorial/2013/leiame_dtb_2013.txt` | 2013 | confirma composição da edição |
| Áreas Territoriais (IBGE) | `https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/areas_territoriais/` | pastas 2002, 2010, 2013–2025 (**faltam 2007–2009, 2011–2012**) | descartada: cobertura incompleta |
| Estimativas de População (IBGE/DPE/COPIS) | `https://ftp.ibge.gov.br/Estimativas_de_Populacao/` | sem pasta 2007 e 2010 | descartada como fonte de existência (seção 4.2); usada só como checagem |
| Alterações Toponímicas Municipais (IBGE) | `https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/alteracoes_toponimicas_municipais/` | arquivos 2014, 2017–2025 | corroboração de mudanças de nome |
| Evolução da Divisão Territorial do Brasil 1872–2010 | `…/estrutura_territorial/evolucao_da_divisao_territorial_do_brasil/` | até 2010 | não usada (termina em 2010) |
| API de localidades (`servicodados.ibge.gov.br/api/v1/localidades`) | — | somente composição **atual** | não usada para anos passados |
| API Biblioteca IBGE (histórico municipal) | `https://servicodados.ibge.gov.br/api/v1/biblioteca?aspas=3&codmun=2206720` | Nazária/PI | data oficial de instalação |
| Agência de Notícias IBGE, release de 27/06/2013 | `https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/14431-asi-novos-mapas-municipais-do-ibge-mostram-que-brasil-tem-agora-5570-municipios` | 2013 | municípios instalados em 2013 |

## 4. Fonte escolhida e justificativa

### 4.1 DTB anual

**FATO DA FONTE**: o geoftp oficial do IBGE mantém uma edição da DTB para
cada ano de 2007 a 2019. Cada edição lista os municípios da divisão
territorial oficial daquele ano, com código IBGE, nome e UF.

A DTB atende à prioridade 1 da tarefa: série anual oficial, com uma lista
por ano, código oficial e sem necessidade de reconstrução. **Nenhuma
reconstrução ou inferência foi necessária para obter a lista de qualquer
ano.**

Regra única de derivação:

```text
municipio_existia_no_ano = código presente na lista de municípios da edição DTB do próprio ano
```

### 4.2 Por que as Estimativas de População NÃO servem como fonte de existência

**FATO DA FONTE**:

- `Estimativas_2008/UF_Municipio.zip` (referência 1º/07/2008) **lista
  Nazária/PI** (`22`+`06720`), com 5.565 linhas municipais.
- `Estimativas_2012/estimativa_2012_TCU_20170614.xls` (referência
  1º/07/2012) lista Mojuí dos Campos, Pescaria Brava, Balneário Rincão,
  Pinto Bandeira e Paraíso das Águas, com a nota
  **"(3) Municípios instalados em 1º de janeiro de 2013."**

**INFERÊNCIA**: as Estimativas incluem municípios criados em lei mas ainda
não instalados, provavelmente para fins de FPM/TCU. Elas não medem
existência instalada naquele ano. Usá-las atribuiria existência a Pescaria
Brava em 2012 — exatamente o erro que o calendário deve evitar.

### 4.3 Data de referência das edições

**FATO DA FONTE**:

- o nome do arquivo de 2009 é `dtb_05_05_2009.zip`;
- as demais edições não trazem data de referência explícita no arquivo;
- as datas internas dos `.xls` são apenas metadados de arquivo
  (2007: 2007-08-28; 2008: 2008-03-12; 2010: 2012-04-26), não datas oficiais
  de referência.

**FATO DA FONTE** (datas oficiais de instalação dos 6 códigos que entram na
janela):

- Nazária/PI: "Elevado à categoria de município … pela Lei Estadual n.º
  4.810, de 14-12-1995, desmembrado de Teresina. … Instalado em
  01-01-2009." (API Biblioteca IBGE, campo `FORMACAO_ADMINISTRATIVA`).
- Os cinco de 2013: "Municípios instalados em 1º de janeiro de 2013"
  (Estimativas 2012). O release de 27/06/2013 registra "cinco deles como
  novos municípios instalados em 2013 … seus prefeitos foram eleitos no
  pleito realizado em 2012 … eleva o número dessas unidades territoriais, no
  Brasil, para 5.570".

**INFERÊNCIA**: todas as entradas da janela ocorreram em 1º de janeiro do
ano de primeira presença na DTB. Assim, o calendário anual é coerente tanto
com uma leitura "situação em 1º/jan" quanto com a referência do CEMPRE
(estoque em 31/12). Nenhum dos 6 casos fica ambíguo em granularidade anual.

---

## 5. Cobertura 2007–2019

### 5.1 Arquivos oficiais baixados

Local: `data/raw/ibge/territorio/dtb/`. Os `.zip` originais são **ignorados
pelo Git** (regra `*.zip` do `.gitignore`) e são lidos em memória, sem
extrair `.xls` em disco (`.xls` não é ignorado pelo projeto). Base das URLs:
`https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/divisao_territorial/<ano>/<arquivo>`.

| Ano | Arquivo | Bytes | SHA-256 |
|---|---|---:|---|
| 2007 | `dtb_2007.zip` | 461.511 | `dab746c294e13db3892b959258d84d4cc8dd5e2d0cb5e9cbc6e02a03ff58c3c9` |
| 2008 | `dtb_2008.zip` | 483.339 | `562e92c558a7180165032b352d2da9daf06b5fe7930e499b6f5bc365c832914a` |
| 2009 | `dtb_05_05_2009.zip` | 482.249 | `40771908994960ed0037d8e925998e078263f91559956ac251d48ce7dcbdbea6` |
| 2010 | `dtb_2010.zip` | 206.919 | `4cfbe9ae50b6e5d67179050a9041993940a2548abdba0057e6b9677f49fa95e1` |
| 2011 | `dtb_2011.zip` | 194.667 | `1981ccf854e78be8206f9cc6ac90c16ae5206d4bf2650e725750bf56b9e60f16` |
| 2012 | `dtb_2012.zip` | 178.326 | `4c13cebe5116bc9f8a76f6074ae40e757d45afb1c7147ff04ed261d69369aca0` |
| 2013 | `dtb_2013.zip` | 469.155 | `eeec2bde37b901a363f4a3973fb65ca028edaa481212253cc8b821db5f3d2c54` |
| 2014 | `dtb_2014_v2.zip` | 2.229.161 | `ceed87ef11e1477eaf3ad4f5f948746ca699187f6558e98e91589210af0a48d1` |
| 2015 | `dtb_2015_v2.zip` | 1.494.824 | `d101cffe61a81c8a4b8dedae29ee0dea429fd07e7816225d88d5c51b98ab5fd3` |
| 2016 | `DTB_2016_v2.zip` | 1.514.388 | `d5ce045b0fe4a9f5316625c9922bb95013b0ed8113b39efe76340fce89fabdac` |
| 2017 | `DTB_2017.zip` | 1.492.911 | `9788c2192465bc2f09c9163aa456332db5a489b9be7fe7e15ff076206b00e983` |
| 2018 | `DTB_2018.zip` | 1.482.231 | `7e6237235cbf2a04b245f6e4d085f608de10ce674f64c93ba5b523b57c0cdb0d` |
| 2019 | `DTB_2019_v2.zip` | 1.928.272 | `2aee1cfc43471245903aa2d27f4e42da4f465089a52c8c0f12a4221e32572fd3` |

Tamanho e SHA-256 ficam fixados no script. Se o IBGE substituir um arquivo,
a execução falha explicitamente; o conteúdo novo não é gravado nem usado.

### 5.2 Estratégia de normalização por ano

**RESULTADO DA CONSTRUÇÃO** — os formatos variam entre edições e cada um foi
tratado explicitamente:

| Anos | Membro `.xls` / aba | Nível | Código | Nome |
|---|---|---|---|---|
| 2007, 2008 | `DTB_<ano>.xls` / `DTB_Nome_Comum` | distrito/subdistrito | `UF` + `Município` (5 díg.) | `Nome_Município` |
| 2009 | `DTB_05_05_2009.xls` / `DTB_05_05_2009n` | distrito/subdistrito | `Município` (7 díg.) | `Município_Nome` |
| 2010 | `dtb_2010.xls` / `Município` | município | `Município` (7 díg.) | `Nome_Munic` |
| 2011, 2012 | `dtb_<ano>.xls` / `DTB_2011`, `Estrutura_2012___Município` | município | `UF` + `Munic` (5 díg.) | `Nome_Munic` |
| 2013 | `dtb_2013.xls` / `dtb_2013` | distrito/subdistrito | `Uf` + `Município` (5 díg.) | `Nome_Município` |
| 2014 | `DTB_2014_Municipio.xls` / `Plan1` | município | `Cod Municipio Completo` (7), conferido com `UF`+`Município` | `Nome_Município` |
| 2015–2019 | `…MUNICIPIO.xls` / `DTB_<ano>_Municipio` | município | `Código Município Completo` (7), conferido com `UF`+`Município` | `Nome_Município` |

Regras aplicadas em todos os anos:

- células de código e UF precisam ser **texto**; não há coerção de números;
- código final com exatamente 7 dígitos, tratado como string;
- prefixo do código igual à coluna UF;
- `Nome_UF` conferido contra a tabela estática de UFs;
- nas planilhas em nível de distrito, linhas colapsadas para uma por código
  **somente depois** de verificar que nome e UF são únicos por código;
- nas planilhas em nível de município, código repetido é erro;
- nomes preservados literalmente (apenas espaços externos removidos).

Linhas brutas → municípios: 2007: 10.561 → 5.564; 2008: 10.575 → 5.564;
2009: 10.644 → 5.565; 2013: 10.964 → 5.570; nas edições em nível de
município, linhas = municípios.

---

## 6. Schema final

`data/processed/calendario_territorial_municipios_2007_2019.parquet` — 72.410
linhas (5.570 códigos × 13 anos), 133.101 bytes.

| Campo | Tipo (Parquet) | Conteúdo |
|---|---|---|
| `codigo_municipio_ibge` | string (7 dígitos) | chave |
| `ano` | int64 | 2007–2019; chave |
| `municipio_existia_no_ano` | bool, não nulo | presença na DTB do ano |
| `nome_municipio_ano` | string nullable | nome literal na DTB do ano; nulo se inexistente |
| `uf_codigo` | string | prefixo de 2 dígitos do código |
| `uf_sigla` | string | sigla da UF |
| `fonte_territorial` | string | `IBGE - Divisão Territorial Brasileira (DTB)` |
| `versao_fonte` | string | edição, arquivo e SHA-256 |
| `fonte_ano` | string | URL oficial do `.zip` daquele ano |
| `observacao_territorial` | string nullable | entrada, ausência antes da primeira presença, mudança de nome frente à DTB anterior |

`data_vigencia_inicio` e `data_vigencia_fim`, previstos na especificação
CEMPRE (seção 7), **não foram incluídos**: a DTB não fornece datas de
vigência por município, e o calendário não inventa datas. As datas oficiais
de instalação dos 6 casos estão documentadas na seção 4.3.

---

## 7. Mudanças territoriais observadas

Fonte: `outputs/diagnostics/calendario_territorial_transicoes.csv`.

**RESULTADO DA CONSTRUÇÃO**:

| Classe | Casos |
|---|---:|
| `entrada` (ausente na DTB t−1, presente na DTB t) | **6** |
| `saida` (extinção/incorporação/fusão apareceriam aqui) | **0** |
| `mudanca_nome` (mesmo código, nome literal diferente) | **42** |
| `mudanca_uf` | **0** |
| `possivel_mudanca_codigo` (heurística: saída + entrada com mesmo nome e UF) | **0** |
| `lacuna_intermediaria` (código some e reaparece) | **0** |

A união dos códigos das 13 edições tem 5.570 códigos, idêntica ao conjunto
de 2019. **Nenhum código deixou de existir e nenhum código foi trocado**;
portanto **nenhum crosswalk de código é necessário** dentro da janela.

### 7.1 Entradas

| Código | Município | UF | Primeira DTB | Instalação oficial (FATO DA FONTE) |
|---|---|---|---|---|
| 2206720 | Nazária | PI | 2009 | 01-01-2009 (API Biblioteca IBGE) |
| 1504752 | Mojuí dos Campos | PA | 2013 | 1º/01/2013 (Estimativas 2012, nota 3) |
| 4212650 | Pescaria Brava | SC | 2013 | 1º/01/2013 (idem) |
| 4220000 | Balneário Rincão | SC | 2013 | 1º/01/2013 (idem) |
| 4314548 | Pinto Bandeira | RS | 2013 | 1º/01/2013 (idem) |
| 5006275 | Paraíso das Águas | MS | 2013 | 1º/01/2013 (idem) |

**Município de origem**: **FATO DA FONTE** apenas para Nazária
("desmembrado de Teresina"). Para os cinco de 2013, a origem **não foi
verificada** em texto oficial legível nesta tarefa.

### 7.2 Mudanças de nome (código estável)

As 42 mudanças por ano de edição: 2009: 3; 2010: 3; 2011: 1; 2012: 1;
2013: 2; 2014: 5; 2015: 7; 2016: 14; 2017: 1; 2018: 0; 2019: 5.

Em 18 casos os nomes são iguais após remover acento, caixa e pontuação
(diagnóstico, não regra). Nenhuma delas é tratada como erro.

**Corroboração** (FATO DA FONTE): as listas oficiais de Alterações
Toponímicas (2014, 2017, 2018, 2019) registram **37 das 42** mudanças, entre
elas:

- mudanças de denominação por lei: Campo de Santana→Tacima (2009);
  Santarém→Joca Claudino (2010); Embu→Embu das Artes (2011); Presidente
  Juscelino→Serra Caiada (2013); Augusto Severo→Campo Grande (2019);
  Fortaleza do Tabocão→Tabocão (2019);
- correções ortográficas datadas de 2016 pelo IBGE.

Registro parcial: "Sant' Ana"→"Sant'Ana do Livramento" difere só por um
espaço; a lista registra o ato de 1957.

**Sem registro nas listas consultadas** (5, todas de grafia):
Santa Isabel→Santa Izabel do Pará (1506500); Olho-d'Água→Olho d'Água do
Borges (2408409); Santa Teresinha→Santa Terezinha (2928505); Pingo-d'Água→
Pingo d'Água (3150539); Atilio→Atílio Vivacqua (3200706). Não há lista
toponímica publicada para 2015–2016 no FTP. Como o código é estável, isso
não afeta a identidade município-ano.

**INFERÊNCIA**: a data em que um nome muda na DTB pode atrasar em relação ao
ato legal. Exemplo: Seridó→São Vicente do Seridó, Lei Estadual 3.516 de
1968, só aparece na DTB 2013. `nome_municipio_ano` é "nome usado na edição
DTB do ano", não um histórico jurídico do topônimo.

---

## 8. Contagem de municípios por ano

`outputs/diagnostics/calendario_territorial_contagem_por_ano.csv` —
**RESULTADO DA CONSTRUÇÃO**:

| Ano | Existentes | Lista oficial DTB | Códigos da união inexistentes |
|---|---:|---:|---:|
| 2007 | 5.564 | 5.564 | 6 |
| 2008 | 5.564 | 5.564 | 6 |
| 2009 | 5.565 | 5.565 | 5 |
| 2010 | 5.565 | 5.565 | 5 |
| 2011 | 5.565 | 5.565 | 5 |
| 2012 | 5.565 | 5.565 | 5 |
| 2013 | 5.570 | 5.570 | 0 |
| 2014 | 5.570 | 5.570 | 0 |
| 2015 | 5.570 | 5.570 | 0 |
| 2016 | 5.570 | 5.570 | 0 |
| 2017 | 5.570 | 5.570 | 0 |
| 2018 | 5.570 | 5.570 | 0 |
| 2019 | 5.570 | 5.570 | 0 |

**Correção ao registro anterior do projeto**: a frase "5.564 municípios até
2012" (usada em `AUDITORIA_DISPONIBILIDADE_CEMPRE.md` e
`CADASTRO_NACIONAL_EXPOSICAO_REDE_FEDERAL.md`) é imprecisa segundo a DTB. O
correto é 5.564 em 2007–2008 e 5.565 em 2009–2012. A tabela de universo
anual do próprio `CADASTRO_NACIONAL_EXPOSICAO_REDE_FEDERAL.md` já registrava
5.564/5.565/5.570 corretamente. Nenhum desses documentos foi alterado nesta
tarefa.

**FATO DA FONTE complementar**: o `leiame_dtb_2013.txt` descreve a edição
2013 como "5568 municípios, o Distrito Estadual de Fernão de Noronha [sic]
e o Distrito Federal …, totalizando 5570 unidades". Portanto, "município" no
calendário segue a unidade com código municipal da DTB, **incluindo
Fernando de Noronha e Brasília**, como no restante do projeto e no N6 do
SIDRA.

---

## 9. Caso Pescaria Brava/SC (`4212650`)

**RESULTADO DA CONSTRUÇÃO** (derivado das DTB, sem regra específica para
este código; ver seção 11):

| Ano | `municipio_existia_no_ano` | `nome_municipio_ano` | `observacao_territorial` |
|---|---|---|---|
| 2007–2012 | **False** | nulo | "código ausente da DTB <ano>; primeira presença na janela: DTB 2013" |
| 2013 | **True** | Pescaria Brava | "entrada no calendário: código ausente da DTB 2012" |
| 2014–2019 | **True** | Pescaria Brava | nulo |

**Comparação com o CEMPRE** (leitura, sem alteração, da fixture
`data/raw/ibge/cempre/fixtures/tabela_1685_n6_4212650_pescaria_brava_2007_2013_2019.json`):

- 2007: 6/6 variáveis com `V="..."`;
- 2013 e 2019: 12/12 valores numéricos.

**INFERÊNCIA**, aplicando a especificação (seções 6.2–6.3):

- 2007: `status_valor_api = indisponivel` e
  `status_territorial = nao_existia_no_ano`. É o caso **B**, comportamento
  esperado, **não** `incompatibilidade_territorial`.
- 2013 e 2019: `existia_no_ano` com valor observado, coerente.
- 2008–2012: o calendário marca inexistência, mas o estado do CEMPRE nesses
  anos não foi consultado nesta tarefa.

---

## 10. Validações automáticas

Implementadas no script e executadas com sucesso na construção nacional:

1. arquivo local com tamanho e SHA-256 idênticos aos registrados;
2. membro `.xls`, aba e colunas esperadas presentes ("schema anual
   inesperado" interrompe);
3. células de código e UF textuais; código de 5 dígitos válido quando
   aplicável;
4. código municipal com exatamente 7 dígitos;
5. prefixo do código = UF; código completo = UF + código parcial (2014–2019);
6. `Nome_UF` compatível com o código de UF;
7. nome de município não vazio;
8. ano inteiro entre 2007 e 2019;
9. nível distrito: nome e UF únicos por código antes de colapsar;
10. ausência de duplicidade código-ano na lista anual;
11. calendário cobre exatamente os 13 anos;
12. ausência de duplicidade `(codigo, ano)` no calendário;
13. booleano não nulo e de tipo `bool`;
14. cada código da união com exatamente 13 linhas;
15. conjunto de códigos do calendário = união das listas anuais;
16. por ano: nenhum código True fora da lista oficial, nenhum código da
    lista oficial marcado False, contagem anual = tamanho da lista;
17. nome preenchido se e somente se o município existia;
18. `uf_codigo` = prefixo do código.

Nomes divergentes entre anos **não** são erro: são reportados em
`mudanca_nome` e em `observacao_territorial`.

---

## 11. Testes

`tests/test_constroi_calendario_territorial_ibge.py` — 44 testes
(`unittest`), todos com dados sintéticos pequenos, **sem internet e sem
leitura dos arquivos DTB reais**:

- **código**: válido; inválido (6 e 8 dígitos, letra, espaço, vazio, `None`,
  int, float); célula numérica não convertida; código de 5 dígitos
  inválido; prefixo ≠ UF; completo ≠ parcial; `Nome_UF` incompatível;
- **ano**: limites válidos; inválido (2006, 2020, string, float, bool,
  `None`); ano inválido na normalização; esquemas cobrindo exatamente
  2007–2019;
- **schema/duplicidade**: coluna ausente; coluna renomeada; planilha vazia;
  duplicidade em lista municipal; colapso de distritos; nomes divergentes
  no mesmo código; duplicidade código-ano; ano errado;
- **união e grade**: união de códigos; união vazia; 13 linhas por código;
  presente → True e ausente → False; **mesmo código `4212650` com fonte
  sintética diferente produz resultado diferente** (prova de que não há
  regra embutida); mudança de nome sem mudança de código; proveniência
  ausente;
- **validação do calendário**: True sem constar da fonte; presente marcado
  False; duplicidade; booleano nulo; código sem 13 linhas; nome para
  inexistente; anos incompletos;
- **transições**: classes com zero casos registradas; entrada, saída,
  lacuna e possível mudança de código; nome igual após normalização
  (diagnóstico);
- **reconciliação**: reporta sem excluir e sem modificar a entrada;
- **integridade sem rede**: SHA correto/incorreto; download desabilitado;
  download com conteúdo divergente não grava arquivo;
- **ausência de história embutida**: nenhum código municipal literal além
  do caso de auditoria (fora das funções de construção) e nenhuma contagem
  histórica no módulo.

Resultado: ver relatório final da tarefa (execução
`.venv\Scripts\python.exe -m unittest tests.test_constroi_calendario_territorial_ibge -v`).

---

## 12. Reconciliação estrutural com códigos do projeto

`outputs/diagnostics/calendario_territorial_reconciliacao_projeto.csv` —
somente leitura, somente diagnóstico; **nenhum município excluído,
selecionado ou alterado**.

**RESULTADO DA CONSTRUÇÃO**:

| Grupo | Códigos | Formato inválido | Fora do calendário | Existentes nos 13 anos | Inexistentes em algum ano |
|---|---:|---:|---:|---:|---:|
| Fase II (`fase_ii_municipios.parquet`) | 147 | 0 | 0 | 147 | 0 |
| Pool candidato (`pool_candidato_controles_sem_exposicao_2007_2019.parquet`) | 4.964 | 0 | 0 | 4.964 | 0 |

- Os 129 candidatos à amostra principal são subconjunto dos 147 e não foram
  reconciliados em arquivo separado (**INFERÊNCIA**: também existem nos 13
  anos).
- **Checagem cruzada independente**: no cadastro de elegibilidade (5.570
  códigos), os anos ausentes do universo INEP/Censo Escolar
  (`anos_ausentes_do_universo`) coincidem exatamente com os anos
  inexistentes no calendário DTB em **5.570/5.570** códigos, com 0
  divergências. A fonte educacional e a DTB são independentes e concordam
  inclusive quanto a Nazária (ausente 2007–2008) e aos cinco de 2013
  (ausentes 2007–2012).

Nenhuma divergência de código ou schema foi encontrada.

---

## 13. Limitações

1. **Granularidade anual, sem datas de vigência**: a DTB não informa data de
   início/fim por município. As datas de instalação dos 6 casos vêm de
   fontes oficiais auxiliares e estão só neste documento, não no Parquet.
2. **Data de referência das edições não uniforme nem explícita** (exceto
   2009). O risco foi neutralizado para esta janela porque todas as
   entradas ocorreram em 1º de janeiro (seção 4.3); em outra janela seria
   preciso reavaliar.
3. **Mudança de limites não é capturada**: código estável não implica
   território estável. O release de 2013 menciona 209 municípios com limites
   alterados. Municípios de origem de desmembramentos (por exemplo, Teresina
   em 2009) perdem território sem que o calendário marque isso. Para o
   CEMPRE, isso afeta a comparabilidade da série dos municípios de origem —
   ponto a tratar no pipeline, não resolvido aqui. A origem dos cinco de
   2013 não foi verificada.
4. **Nome da edição ≠ histórico jurídico do topônimo** (seção 7.2); 5
   mudanças de grafia sem registro nas listas consultadas.
5. **Edições `v2`** (2014, 2015, 2016, 2019): foram usados os arquivos hoje
   publicados; versões anteriores não estão no FTP.
6. **Raw não versionado**: a reprodutibilidade depende do FTP do IBGE e dos
   SHA-256 fixados. Fontes auxiliares (listas toponímicas, Estimativas, JSON
   da API Biblioteca) ficaram só no diretório temporário da sessão, fora do
   repositório.
7. **Dependência `xlrd`** (leitura de `.xls`): na construção inicial,
   `xlrd` 2.0.2 estava instalado no `.venv`, mas **ausente de
   `requirements.txt`**. A auditoria independente classificou essa lacuna como
   bloqueadora para reprodutibilidade em clone limpo. A correção posterior
   declarou `xlrd==2.0.2` em `requirements.txt` e foi validada conforme a
   seção 17.
8. **Artefatos ignorados pelo Git**: o Parquet (`data/processed/*`) e os CSVs
   (`*.csv` do `.gitignore` raiz) são ignorados. Só o manifesto JSON aparece
   como não rastreado. Versioná-los exigiria exceções no `.gitignore`, que
   não foi alterado.

## 14. Proveniência

Manifesto completo: `outputs/diagnostics/calendario_territorial_manifest.json`.
Contém, por ano:

- órgão, produto, URL, ano de referência, arquivo original, caminho local,
  data de acesso, tamanho e SHA-256 do `.zip`;
- membro `.xls` com tamanho e SHA-256, aba e abas disponíveis;
- colunas originais e usadas, nível, formato do código e transformação
  aplicada;
- número de linhas brutas e de municípios.

Contém ainda: contagens, eventos por classe, caso Pescaria Brava,
reconciliação, SHA-256 do script e dos artefatos, commit `HEAD` e versões de
Python/pandas/xlrd.

Fontes auxiliares consultadas e **não usadas na construção** (acesso
2026-09-15, arquivos fora do repositório):

| Fonte | URL | SHA-256 |
|---|---|---|
| Alterações Toponímicas 2014 | `…/alteracoes_toponimicas_municipais/Alteracoes_Toponimicas_Municipais_2014.xls` | `702cc3a36c2f68b22da8ad6f358b79088fc932f6595bcec289ef58dfc18f9e0c` |
| Alterações Toponímicas 2017 | `…/Alteracoes_Toponimicas_Municipais_2017.xls` | `22b3d99f4fce5b61a346e07096d15b5f107eeb5a061e90aad6ea6e788556b6da` |
| Alterações Toponímicas 2018 | `…/Alteracoes_Toponimicas_Municipais_2018.xls` | `d36e314770cd598ae2235a08719ff2c12f73e22ecb6ed130d25ccefe9f64dd8b` |
| Alterações Toponímicas 2019 | `…/Alteracoes_Toponimicas_Municipais_2019.xls` | `ed6a93eeee6c13a230f93ccc9191f8163960edb10a49d081c32144d131065101` |
| Estimativas 2008 | `https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2008/UF_Municipio.zip` | `899cb1b6c10fb5099e2f0abb604b73ce84376fa6a3a080fba7fc1a4c0a85d979` |
| Estimativas 2009 | `…/Estimativas_2009/UF_Municipio.zip` | `8254371826730c9b8955ca990133506d54c5b8aa3af572ada05d4dc150d18cbf` |
| Estimativas 2012 | `…/Estimativas_2012/estimativa_2012_TCU_20170614.xls` | `383e2f2d327c6fa15d087bbc2d03a248a7a83cee015ceb661b8c6e673065090c` |
| Estimativas 2013 | `…/Estimativas_2013/estimativa_2013_TCU_20170614.xls` | `64d29f9cdfdc8817690733ed94dfc2934f6f1d853a0f341ed5219dadce255067` |
| API Biblioteca — Nazária | `https://servicodados.ibge.gov.br/api/v1/biblioteca?aspas=3&codmun=2206720` | `b44946552af5050b2aef4a7e7a7bfcf06d23b171ffe6168d3621b50135d6555f` |
| Release Agência IBGE 27/06/2013 | URL da seção 3 | — |
| Leia-me DTB 2013 | `…/divisao_territorial/2013/leiame_dtb_2013.txt` | — |

---

## 15. Adequação para integrar o pipeline CEMPRE

O calendário fornece o insumo exigido por `ESPECIFICACAO_PAINEL_CEMPRE.md`
(seções 6.2 e 7):

- join por `(codigo_municipio_ibge, ano)`;
- `municipio_existia_no_ano = True` → `existia_no_ano`;
- `False` → `nao_existia_no_ano`;
- código fora da união → `indeterminado`. Nenhum é esperado: a Tabela 1685
  lista 5.570 localidades N6, número igual ao da união; a igualdade código a
  código **não foi verificada** nesta tarefa.

A tabela é derivada só da DTB e nunca de `valor_bruto`/`status_valor_api`,
preservando a separação exigida. A integração em si **não** foi feita.

Pontos a levar ao pipeline (não bloqueantes para o calendário):

- limites alterados em municípios de origem (limitação 3);
- `load_calendar_territorial` da Fase 0 usa uma fixture mínima e continua
  intacta; a troca pela tabela nacional é decisão da frente CEMPRE.

---

## 16. Gate da tarefa

| Critério | Avaliação |
|---|---|
| Fonte oficial defensável | **Sim** — DTB/IBGE, edição anual para cada ano |
| Cobertura dos 13 anos | **Sim** — 2007–2019, sem reconstrução |
| Códigos reproduzíveis | **Sim** — 7 dígitos, SHA-256 fixados, script determinístico |
| Calendário município-ano construído | **Sim** — 72.410 linhas, validações aprovadas |
| Contagens auditáveis | **Sim** — CSV + manifesto por edição |
| Pescaria Brava reconciliada | **Sim** — False 2007–2012, True 2013–2019, coerente com instalação oficial 1º/01/2013 e com `V="..."` em 2007 |
| Testes passando | ver relatório final da execução |
| Nenhuma anomalia bloqueante | **Sim** — anomalias apenas não bloqueantes (seção 13) |

## CALENDARIO_TERRITORIAL_APTO

Condicionado à suíte de testes desta tarefa passando integralmente (resultado
registrado no relatório final). Este veredito cobre apenas o calendário
territorial. Não aprova o piloto ou o painel CEMPRE e não implica qualquer
decisão causal.

---

## 17. Histórico do gate e correção de reprodutibilidade

### 17.1 Construção e autoavaliação iniciais

A construção inicial produziu o calendário territorial, os diagnósticos e o
manifesto descritos neste documento. A autoavaliação inicial registrou
`CALENDARIO_TERRITORIAL_APTO` na seção 16, condicionada à aprovação integral
da suíte territorial. Esse registro é histórico e não foi apagado.

### 17.2 Auditoria independente e reclassificação

A auditoria independente posterior confirmou a lógica territorial: fonte DTB,
cobertura anual, normalização, composição dos códigos, contagens, transições,
grade, Parquet, manifesto e reconciliação de Pescaria Brava. Identificou, porém,
um bloqueador de reprodutibilidade: o script importa `xlrd`, mas a dependência
não constava de `requirements.txt`. O gate foi então reclassificado como:

```text
CALENDARIO_TERRITORIAL_NAO_APTO
```

Essa reclassificação não questionou a lógica territorial; tratou apenas da
capacidade de reproduzir a construção em ambiente limpo.

### 17.3 Correção e nova autoavaliação

Foi declarada a dependência exata `xlrd==2.0.2` em `requirements.txt`. Na
`.venv` do projeto, as verificações posteriores registraram:

- `.venv\Scripts\python.exe -m pip check` → `No broken requirements found.`
- `.venv\Scripts\python.exe -c "import xlrd; print(xlrd.__version__)"` → `2.0.2`.
- `.venv\Scripts\python.exe -m unittest tests.test_constroi_calendario_territorial_ibge -v` → **44/44 testes OK**.

Nova autoavaliação após a correção:

| Critério | Status | Evidência resumida |
|---|---|---|
| Fonte oficial | ATENDIDO | DTB/IBGE anual 2007–2019 |
| Cobertura dos 13 anos | ATENDIDO | Uma edição DTB por ano |
| Schemas anuais | ATENDIDO | Validações explícitas por edição |
| Códigos reproduzíveis | ATENDIDO | Strings, UF e hash validados |
| Composição dos códigos | ATENDIDO | UF + cinco dígitos validado quando aplicável |
| Grid | ATENDIDO | 5.570 códigos × 13 anos = 72.410 linhas |
| Contagens | ATENDIDO | 5.564 / 5.565 / 5.570 por período |
| Transições | ATENDIDO | Uma entrada em 2009 e cinco em 2013; sem saídas |
| Pescaria Brava | ATENDIDO | False em 2007–2012; True em 2013–2019 |
| Proveniência | PARCIAL_NAO_BLOQUEANTE | URLs, hashes e manifesto; raw não versionado |
| Testes | PARCIAL_NAO_BLOQUEANTE | 44 testes unitários OK, com dados sintéticos |
| Artefato reproduzível | ATENDIDO | Script, fontes com hash e dependência declarada |
| Dependências reproduzíveis | ATENDIDO | `xlrd==2.0.2` declarado e importado |
| Ausência de bloqueador | ATENDIDO | Nenhum bloqueador remanescente |

```text
CALENDARIO_TERRITORIAL_APTO
```

As limitações das seções 13 e 15 permanecem: o calendário não harmoniza
fronteiras municipais, código estável não garante território estável, os ZIPs
raw DTB não são versionados, hashes detectam alteração silenciosa mas não
substituem arquivamento durável, e os testes unitários territoriais usam dados
sintéticos. Elas não invalidam o uso do calendário para existência municipal.
