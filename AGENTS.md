# AGENTS.md

## 1. Escopo do Workspace

Estas instruÃ§Ãµes valem para todo o workspace `datascience`.

Este workspace contÃ©m mÃºltiplos projetos independentes de CiÃªncia de Dados, Machine Learning, InferÃªncia Causal, CRM Analytics, ExperimentaÃ§Ã£o, Uplift Modeling, OtimizaÃ§Ã£o de DecisÃ£o, CrÃ©dito, Forecasting e construÃ§Ã£o de pipelines analÃ­ticos orientados a produÃ§Ã£o.

Cada projeto deve ficar dentro de:

- `projetos/<nome-do-projeto>/`

Exemplos atuais:

- `projetos/starbucks-customer-rewards-program-dataset/`
- `projetos/inferencia-causal/`

A raiz do workspace deve conter apenas arquivos gerais, como:

- `AGENTS.md`
- `README.md`
- `.gitignore`
- scripts administrativos do workspace

NÃ£o trate a raiz `datascience/` como se fosse um Ãºnico projeto.

---

## 2. Regra de Escopo ObrigatÃ³rio

Antes de modificar qualquer arquivo, identifique explicitamente o escopo da tarefa.

Para qualquer tarefa de implementaÃ§Ã£o, revisÃ£o ou refatoraÃ§Ã£o, apresente antes:

1. projeto alvo;
2. arquivos que pretende ler;
3. arquivos que pretende modificar;
4. arquivos ou pastas que nÃ£o serÃ£o alterados;
5. plano curto de validaÃ§Ã£o.

Nunca altere arquivos fora da pasta ou dos arquivos mencionados pelo usuÃ¡rio.

Se o usuÃ¡rio pedir para trabalhar em um projeto especÃ­fico, modifique apenas arquivos dentro da pasta desse projeto.

Ao trabalhar em um projeto, trate a pasta desse projeto como a raiz lÃ³gica da tarefa.

Exemplo:

- Se o projeto alvo for `projetos/starbucks-customer-rewards-program-dataset/`, nÃ£o altere `projetos/inferencia-causal/` sem autorizaÃ§Ã£o explÃ­cita.
- Se o projeto alvo for `projetos/inferencia-causal/`, nÃ£o altere `projetos/starbucks-customer-rewards-program-dataset/` sem autorizaÃ§Ã£o explÃ­cita.

NÃ£o altere automaticamente:

- `.venv/`
- `.venv_workspace_antiga/`
- dados brutos;
- arquivos grandes;
- outros projetos nÃ£o citados;
- `AGENTS.md`;
- `.gitignore`;
- `README.md` da raiz.

NÃ£o crie, mova, renomeie ou delete arquivos sem pedido explÃ­cito.

---

## 3. Regras Operacionais

Trabalhe de forma incremental.

Prefira mudanÃ§as pequenas, seguras e fÃ¡ceis de revisar.

NÃ£o instale pacotes sem pedido explÃ­cito.

NÃ£o crie pastas sem pedido explÃ­cito.

NÃ£o apague arquivos.

NÃ£o altere arquivos fora do escopo solicitado.

Antes de editar arquivos, apresente um plano curto.

Depois de editar arquivos, liste o que foi alterado e explique como validar.

NÃ£o gere cÃ³digo com placeholders.

NÃ£o deixe cÃ³digo incompleto.

Prefira cÃ³digo claro, modular, testÃ¡vel e reutilizÃ¡vel.

Prefira validaÃ§Ãµes explÃ­citas em vez de apenas inspeÃ§Ã£o visual.

Mantenha notebooks legÃ­veis e com narrativa analÃ­tica.

Mova lÃ³gica reutilizÃ¡vel para funÃ§Ãµes apenas quando isso melhorar clareza ou reuso.

---

## 4. Ambientes Virtuais

Cada projeto deve ter seu prÃ³prio ambiente virtual `.venv`.

Exemplo:

- `projetos/starbucks-customer-rewards-program-dataset/.venv/`
- `projetos/inferencia-causal/.venv/`

NÃ£o use a `.venv` da raiz para desenvolvimento de projetos.

NÃ£o edite, mova ou apague ambientes virtuais sem pedido explÃ­cito.

Ao orientar execuÃ§Ã£o de cÃ³digo, sempre indique qual `.venv` deve ser ativada.

---

## 5. Stack PadrÃ£o

Use DuckDB como motor analÃ­tico principal para:

- leitura de arquivos locais;
- parsing de JSON;
- transformaÃ§Ãµes SQL;
- joins;
- agregaÃ§Ãµes;
- janelas temporais;
- validaÃ§Ãµes de dados;
- construÃ§Ã£o de ABTs.

Use Pandas principalmente para:

- materializar resultados finais;
- inspeÃ§Ã£o leve;
- visualizaÃ§Ã£o;
- preparaÃ§Ã£o para modelagem;
- integraÃ§Ã£o com bibliotecas de ML.

Evite fazer joins relacionais pesados e agregaÃ§Ãµes grandes em Pandas quando DuckDB for mais apropriado.

---

## 6. Estrutura Esperada dos Projetos

Pastas relevantes podem incluir:

- `data/`: dados brutos, tratados ou locais.
- `notebooks/`: notebooks exploratÃ³rios e narrativos.
- `playbooks_tecnicos/`: guias metodolÃ³gicos e tÃ©cnicos.
- `src/`: cÃ³digo reutilizÃ¡vel, caso exista.
- `tests/`: validaÃ§Ãµes e testes, caso exista.
- `reports/`: saÃ­das analÃ­ticas, grÃ¡ficos, tabelas e materiais executivos.
- `app/`: aplicaÃ§Ã£o, interface ou dashboard.
- `backend/`: APIs, serviÃ§os auxiliares ou lÃ³gica de backend.

NÃ£o presuma que uma pasta existe. Inspecione antes.

---

## 7. Uso dos Playbooks TÃ©cnicos

Use apenas o playbook necessÃ¡rio para a tarefa atual.

NÃ£o leia todos os playbooks sem necessidade.

Os playbooks principais de inferÃªncia causal ficam em:

- `projetos/inferencia-causal/playbooks_tecnicos/`

O projeto Starbucks tambÃ©m pode ter uma cÃ³pia local em:

- `projetos/starbucks-customer-rewards-program-dataset/playbooks_tecnicos/`

Ãndice dos playbooks:

- `00_contexto_operacional_projeto.md`: regras operacionais e disciplina de trabalho.
- `01_inferencia_causal_uplift.md`: inferÃªncia causal, uplift, CATE e efeitos de tratamento.
- `02_abt_temporal_qualidade_dados.md`: desenho de ABT, consistÃªncia temporal e qualidade de dados.
- `03_estimadores_validacao_causal.md`: estimadores, assumptions, validaÃ§Ã£o e overlap.
- `04_otimizacao_roi_politica_decisao.md`: ROI, restriÃ§Ãµes, polÃ­tica de decisÃ£o e otimizaÃ§Ã£o.
- `05_design_sistema_ml_causal_producao.md`: design de produÃ§Ã£o, pipelines, contratos e monitoramento.
- `06_governanca_revisao_comunicacao.md`: revisÃ£o crÃ­tica, governanÃ§a, comunicaÃ§Ã£o e limitaÃ§Ãµes.

Se o nome real do arquivo for diferente, use o arquivo existente e nÃ£o renomeie sem pedido explÃ­cito.

---

## 8. Quando Aplicar Regras de InferÃªncia Causal

As regras de inferÃªncia causal devem ser aplicadas quando a tarefa envolver:

- tratamento;
- intervenÃ§Ã£o;
- campanha;
- cupom;
- desconto;
- incentivo;
- polÃ­tica de decisÃ£o;
- experimento;
- teste A/B;
- uplift;
- CATE;
- impacto incremental;
- ROI incremental;
- personalizaÃ§Ã£o de aÃ§Ã£o;
- avaliaÃ§Ã£o de efeito.

Quando o problema for apenas preditivo, exploratÃ³rio ou descritivo, nÃ£o force uma interpretaÃ§Ã£o causal.

NÃ£o confunda prediÃ§Ã£o com causalidade.

Para qualquer problema causal ou com intervenÃ§Ã£o, defina explicitamente:

- decisÃ£o de negÃ³cio ou decisÃ£o operacional;
- unidade de anÃ¡lise;
- tratamento/intervenÃ§Ã£o;
- grupo controle/comparaÃ§Ã£o;
- momento de decisÃ£o;
- outcome;
- janela do outcome;
- features prÃ©-tratamento;
- variÃ¡veis pÃ³s-tratamento que devem ser excluÃ­das;
- assumptions;
- limitaÃ§Ãµes.

Features devem estar disponÃ­veis antes do momento de decisÃ£o.

Targets devem ser medidos depois do momento de decisÃ£o.

NÃ£o use variÃ¡veis pÃ³s-tratamento como features.

NÃ£o apresente modelo de propensÃ£o como se fosse uplift causal.

Caso nÃ£o exista grupo controle ou estratÃ©gia de identificaÃ§Ã£o defensÃ¡vel, deixe claro que o resultado Ã© preditivo ou associativo, nÃ£o causal.

---

## 9. Regras de ABT

Em projetos causais, a ABT deve documentar:

- chave primÃ¡ria;
- granularidade;
- ID da entidade;
- ID do tratamento, quando aplicÃ¡vel;
- flag de tratamento;
- momento de decisÃ£o;
- janela de features;
- janela de outcome;
- colunas de target;
- colunas proibidas por leakage;
- flags de qualidade.

A ABT deve ser validada para:

- dados nÃ£o vazios;
- schema esperado;
- unicidade da chave;
- presenÃ§a de tratamento e controle;
- ausÃªncia de nulos crÃ­ticos;
- ausÃªncia de timestamps impossÃ­veis;
- ausÃªncia de feature leakage;
- ausÃªncia de target leakage.

---

## 10. Regras de Modelagem

Comece com um baseline simples e defensÃ¡vel antes de modelos complexos.

Para problemas preditivos, use mÃ©tricas preditivas adequadas.

Para problemas causais ou de uplift, prefira mÃ©tricas como:

- uplift por decil;
- Qini/AUUC, quando aplicÃ¡vel;
- ganho incremental;
- comparaÃ§Ã£o entre tratamento e controle;
- heterogeneidade de efeito;
- valor de negÃ³cio;
- ROI.

NÃ£o use acurÃ¡cia, F1 ou ROC-AUC como mÃ©trica principal para qualidade de uplift ou decisÃ£o causal.

---

## 11. Regras de DecisÃ£o

Score de modelo nÃ£o Ã© entrega final.

Quando o projeto envolver decisÃ£o, gere uma polÃ­tica acionÃ¡vel sempre que possÃ­vel.

Uma polÃ­tica deve considerar:

- efeito esperado;
- valor esperado;
- custo esperado;
- valor lÃ­quido esperado;
- ROI;
- elegibilidade;
- capacidade;
- orÃ§amento;
- risco;
- fallback.

NÃ£o recomende tratar automaticamente toda unidade com score positivo.

Para incentivos, descontos, cupons, cashback, pricing, retenÃ§Ã£o ou aÃ§Ãµes operacionais, considere custo e risco de canibalizaÃ§Ã£o.

---

## 12. Regras de Design de ProduÃ§Ã£o

Separe conceitualmente a lÃ³gica em:

1. ingestÃ£o;
2. normalizaÃ§Ã£o;
3. construÃ§Ã£o de features;
4. construÃ§Ã£o da ABT;
5. modelagem ou estimaÃ§Ã£o de efeito;
6. avaliaÃ§Ã£o;
7. polÃ­tica de decisÃ£o;
8. monitoramento.

Prefira contratos explÃ­citos para tabelas e saÃ­das importantes.

Toda saÃ­da importante deve conter:

- nome do artefato;
- granularidade;
- chave;
- validaÃ§Ã£o;
- limitaÃ§Ã£o conhecida;
- prÃ³ximo passo.

---

## 13. Regras de RevisÃ£o

Antes de considerar uma tarefa concluÃ­da, verifique:

- A mudanÃ§a ficou dentro do escopo?
- As assumptions de dados estÃ£o explÃ­citas?
- As regras temporais foram respeitadas?
- Existe leakage?
- A mÃ©trica estÃ¡ alinhada Ã  decisÃ£o?
- As limitaÃ§Ãµes foram declaradas?
- A saÃ­da Ã© acionÃ¡vel?
- Existe validaÃ§Ã£o?

Classifique problemas como:

- crÃ­tico: invalida o resultado;
- alto: resultado apenas exploratÃ³rio;
- mÃ©dio: usar com ressalvas;
- baixo: melhoria de manutenÃ§Ã£o ou clareza.

---

## 14. Formato de Resposta

Para tarefas de planejamento:

1. plano curto;
2. riscos;
3. arquivos provavelmente afetados;
4. plano de validaÃ§Ã£o.

Para tarefas de implementaÃ§Ã£o:

1. plano curto antes da ediÃ§Ã£o;
2. mudanÃ§a mÃ­nima e dentro do escopo;
3. arquivos alterados;
4. instruÃ§Ãµes de validaÃ§Ã£o;
5. limitaÃ§Ãµes restantes.

Para tarefas de revisÃ£o:

1. achados por severidade;
2. evidÃªncia;
3. correÃ§Ã£o recomendada;
4. indicaÃ§Ã£o se Ã© bloqueador ou nÃ£o.


## 15. Exceção controlada — projeto SINASC

A regra geral de não apagar arquivos permanece vigente.

Exclusivamente em `projetos/big-data-sinasc-causal-ml/`,
esta seção estabelece uma exceção específica à proibição
de exclusões da seção 3.

São permitidas exclusões expressamente autorizadas pelo
responsável pelo projeto, desde que:

- as áreas e categorias estejam delimitadas na autorização;
- cada remoção tenha suas dependências e referências verificadas;
- a obsolescência ou redundância esteja comprovada;
- notebooks, código científico, dados, manifestos, hashes,
  resultados, fontes LaTeX, PDFs e pacotes acadêmicos sejam preservados;
- documentos metodológicos exclusivos e arquivos locais únicos
  sejam preservados;
- os caminhos resolvidos permaneçam dentro do projeto,
  sem seguir links simbólicos ou junções;
- não sejam excluídos diretórios indiscriminadamente;
- caches autorizados sejam limitados ao projeto,
  excluindo ambientes virtuais;
- documentos administrativos não rastreados sejam removidos
  somente após validação final e confirmação de que não
  possuem informações indispensáveis exclusivas;
- testes, links e integridade científica sejam validados;
- exclusões de arquivos versionados sejam registradas no Git;
- exclusões de arquivos ignorados ou não rastreados
  sejam explicitamente descritas no relatório final.

Esta exceção não concede autorização geral para apagar arquivos.
Cada operação deve respeitar o escopo aprovado.

A exceção não alcança outros projetos, o laboratório externo,
suas instruções, branches ou worktrees.

Todas as demais proteções continuam vigentes.

Registrada mediante autorização explícita do responsável
pelo projeto em 29/10/2026.
