# Estado Atual

STATUS = FASE_5_CONSOLIDADA_COM_RESSALVA_VISUAL
FASE_ATUAL = FASE_5_ENTREGA_ACADEMICA
DATA_INICIO = 2026-09-25
DATA_ATUALIZACAO = 2026-09-27
GATE_FASE_0 = VIAVEL_COM_RESSALVAS
GATE_FASE_1 = PRONTO_COM_RESSALVAS
EFEITO_CAUSAL_ESTIMADO = SIM
MODELO_CAUSAL_EXECUTADO = SIM
CAUSALIDADE_PROVADA = NAO
GATE_FASE_2 = RESULTADO_NAO_INTERPRETAVEL
GATE_FASE_3 = GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR
GATE_FASE_4 = HETEROGENEIDADE_SENSIVEL_A_MODELO

MODELAGEM_CONCLUIDA = SIM
ARTIGO_COMPLETO = NAO
RELATORIO_HTML = SIM

## Consolidação acadêmica — Fase 5

- Estado inicial reconstruído: fetch concluído; branch main; HEAD e origin/main em `07e9b7be28d3561a702f7f498c8a6632a9fde4e2`. Histórico confirmado: `48ce06b` → `1d27ab4` → `07e9b7b`. Projeto inicialmente limpo; uma pasta não rastreada em outro projeto foi preservada.
- Suíte inicial: 86 testes aprovados. Cinco notebooks com 7, 12, 13, 21 e 10 células de código executadas, sem saídas de erro. Nenhuma modelagem das Fases 0–4 foi refeita.
- Entregas: dicionário 62/62 em Markdown/CSV/JSON, fluxo, metodologia, resultados, síntese, reprodução, esqueleto do artigo e dez gráficos no HTML autocontido. [README](../../README.md), [métodos](../METODOLOGIA_DO_PROJETO.md) e [relatório](../../apresentacao/relatorio_interativo_sinasc_2024.html).
- Literatura: 12 referências centrais, cinco PDFs públicos obtidos e sete tentativas sem PDF. Fichas distinguem leitura dirigida de PDF e síntese limitada a fontes públicas. PDFs/textos ficam locais, fora do staging. [Manifesto](../literature/MANIFESTO_ARTIGOS.md).
- Validação histórica: seis resultados da Fase 2 e 22 linhas da Fase 3 reconciliados; Fase 4 aprovada, incluindo pseudo-desfechos, cobertura única, partições e preservação. Auditoria de apresentação e pip check aprovados. Validação da entrega confere números, séries dos gráficos, dicionário, links e notebooks.
- Ressalva: a política de segurança do navegador bloqueou a URL local do HTML. Não houve tentativa de contorno. Verificação estática concluída; abertura e controles no navegador permanecem para conferência manual. Figuras exportadas separadamente para inspeção.
- Rastreabilidade: `outputs/diagnostics/fase5_validacao.json` e `fase5_links_externos.json`. HTML e dois JSONs pequenos em diretórios ignorados recebem staging explícito; `.gitignore` preservado.
- Suíte final: 93 testes aprovados. [Auditoria da Fase 5](../AUDITORIA_FASE5.md) registra evidências, comandos, PDFs e a pendência de inspeção do HTML no navegador.
- Registros abaixo são históricos: proibições de iniciar Fase 5 descrevem autorizações antigas, superadas pelo pedido desta sessão. Artigo completo e Fase 6 permanecem fora do escopo.

## Resultado da Fase 4

- Sequência cumprida: Fase 3 publicada em `48ce06b`, padronização PT-BR publicada em `1d27ab4`, seguida de DR-Learner exploratório.
- N=2.251.570; T, Y, regras de qualidade e sete X preservados. Três partições municipais independentes de T/Y, com rotação dos papéis de ajuste auxiliar, treino do CATE e avaliação. Nenhum município compartilhado entre papéis na mesma rodada; cada registro avaliado uma vez.
- Principal HGBRegressor: CATE médio −1,294100 pp; mediana −1,289838 pp; p5 −3,923820; p25 −1,962784; p75 −0,427044; p95 +1,208079 pp. Previsões negativas: 84,684%; isso não é frequência de benefício individual verdadeiro.
- Ridge: média −1,301716 pp; Spearman com HGB 0,706556. Correlação mediana das médias dos grandes perfis entre partições: 0,157895, abaixo do critério exploratório 0,5. Instabilidade também pode refletir composição geográfica.
- Separação prevista Q5−Q1: aproximadamente 4,24–4,73 pp; contraste DR externo: 0,95–1,67 pp. Há ordenação parcial, com magnitude excessiva e baixa estabilidade de perfis. Critério final: `HETEROGENEIDADE_SENSIVEL_A_MODELO`.
- CATE não foi recentrado para coincidir com ATE. Média psi externa −1,216412 pp; C2 histórico −1,231456 pp, preservado. Idade ausente (N=32) é muito imprecisa; UF 53 é categoria nova na rodada de sua avaliação.
- Resultados, protocolo prévio e limitações: [HETEROGENEIDADE_FASE4.md](../methodology/HETEROGENEIDADE_FASE4.md). Sem política clínica, ROI, Causal Forest, artigo completo ou Fase 5.
- Validação final: 86 testes aprovados, `pip check` sem inconsistências e cinco notebooks executados sem erros. Notebook 05: dez células de código executadas; gráficos finais inspecionados e auditoria de idioma aprovada.
- Recuperação do checkpoint pelo repositório: 22 linhas da Fase 3 e seis resultados históricos da Fase 2 reconciliados novamente a partir dos artefatos, sem refazer ajustes pesados. A validação da Fase 4 confirmou cobertura única, separação municipal, pseudo-desfechos, quintis, perfis e preservação das Fases 0–3. As únicas mudanças históricas de apresentação continuam documentadas no manifesto da etapa PT-BR.
- Entregas computacionais e documentais autorizadas concluídas. Esta atualização integra o commit separado da Fase 4; o histórico Git registra sua publicação.

## Auditoria metodológica da Fase 3

- A fórmula AIPW, as seis linhas históricas e os 18 arquivos protegidos foram reconciliados sem erro material e sem reescrever a Fase 2. O gate histórico acima permanece registrado.
- O limiar de 50% de IF² no 1% mais extremo é uma heurística, não um teste universal de invalidade. A revisão de 13 referências, o contraexemplo analítico e 800 replicações Monte Carlo sustentam a revisão de seu uso como veto automático. Isso não comprova identificação causal.
- C1: −1,340527 pp; C2: −1,231456 pp. Erros-padrão agrupados por município: 0,068287 e 0,067997 pp, respectivamente. A dependência geográfica aumenta a incerteza em aproximadamente 10%.
- O ajuste cruzado agrupado por município altera as estimativas em menos de 0,005 pp. Nenhuma exclusão de UF inverte o sinal. O modelo C3 de propensão HGB resulta em −1,232469 pp.
- Excluir discordância de consultas ou ampliar a regra de peso tem pouca influência; incluir gestações múltiplas altera a magnitude em aproximadamente 0,20 pp e muda a população-alvo.
- Confundimento residual, seleção de nascidos vivos e temporalidade de covariáveis continuam limitantes. O estimando observável é uma associação padronizada na população selecionada; sua interpretação causal exige hipóteses não verificadas.
- Validação: 22 linhas da Fase 3 reconciliadas, 65 testes aprovados e `pip check` sem inconsistências. Notebook 04 executado integralmente; registros em `outputs/diagnostics/fase3_validacao.json`.
- Evidências e limitações: [relatório completo](../methodology/ROBUSTEZ_FASE3.md), [literatura](../literature/AUDITORIA_GATE_INFLUENCIA.md) e [estimando](../methodology/AUDITORIA_ESTIMANDO_FASE3.md).
- Sequência posterior já cumprida: publicação da Fase 3, padronização e reexecução dos notebooks 01–04 em português e execução da Fase 4 exclusivamente como exercício didático exploratório. Não há autorização para Fase 5 ou artigo completo.

## Objetivo

### Padronização PT-BR posterior à Fase 3

- Notebooks 01–04 regenerados por suas fontes e executados integralmente. Títulos, narrativa, tabelas e figuras usam a camada compartilhada `src/apresentacao_pt.py`; identificadores reais e nomes técnicos são preservados.
- Verificação automática de idioma aprovada. Todos os números extraídos das tabelas HTML e os hashes dos diagnósticos anteriores permaneceram iguais (`python -m src.valida_apresentacao`). Suíte: 72 testes aprovados.
- A `.venv` existente foi mantida: Python 3.11.9, `pip check` aprovado e ambiente ignorado pelo Git. Nenhum pacote instalado. Execução manual documentada no README.
- O manifesto original da Fase 3 permanece intacto. As alterações autorizadas no notebook 03 e em seu gerador constam em `apresentacao_preservacao.json`; metadados de execução são separados das fontes das células. Os contratos de quatro caches tiveram apenas o hash da guarda de preservação atualizado, após conferir igualdade textual do restante do executor contra `48ce06b`. Nenhuma predição ou ajuste foi alterado.
- O HTML foi exportado e os gráficos PNG conferidos. A abertura do arquivo local no navegador foi bloqueada pela política de URL; a inspeção visual usou os PNGs locais, sem contornar esse bloqueio.

Comparar predição de baixo peso e estimação AIPW cross-fitted sob as hipóteses e população congeladas da Fase 1. Fase 1 publicada no checkpoint `caf1446`.

## Pergunta candidata

Entre gestantes comparáveis em características observáveis, iniciar o pré-natal até o terceiro mês de gestação está associado a uma redução no risco de baixo peso ao nascer?

## Fonte de dados

- Portal de Dados Abertos do SUS / Ministério da Saúde.
- Recurso candidato: `Nascidos Vivos - 2024`.
- URL do ZIP informada: `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINASC/csv/SINASC_2024_csv.zip`.
- Dicionário oficial localizado: `SINASC: Estrutura de 1996 a 2019`.
- Manual oficial mais recente utilizado: `Declaração de Nascido Vivo: manual de instruções para preenchimento`, 4ª edição, Ministério da Saúde, 2022.

## Definições candidatas

- Tratamento: `MESPRENAT` 1-3 versus 4-9; código 99 e missing excluídos da definição candidata.
- Outcome: `PESO` inferior a 2.500 g, com regra principal de qualidade entre 500 e 6.000 g; peso numérico positivo permanece como sensibilidade.
- Unidade de análise: um registro de nascido vivo; `contador` é único nesta extração, sem garantia de estabilidade longitudinal.
- Controle/comparação: início após o terceiro mês; ausência de pré-natal não será incluída automaticamente.
- População principal: nascidos vivos com T conhecido, peso principal válido e gestação única.
- Amostra candidata: 2.251.570 registros; T=1: 1.942.045 (86,253%); T=0: 309.525 (13,747%).

## Decisões herdadas da Fase 1

- Escopo restrito ao ano de 2024 e ao desenho da Fase 1, sem estimação de efeito.
- Fonte principal exclusivamente institucional oficial.
- Dados brutos serão preservados byte a byte e não versionados.
- Dúvidas não bloqueantes serão registradas como `QUESTAO_ABERTA` e tratadas conservadoramente.
- O bruto oficial foi preservado e seu hash SHA-256 registrado no manifesto.
- `MESPRENAT=99` foi confirmado no manual oficial como ignorado e permanece inelegível.
- Gestação única foi escolhida como principal; gestações múltiplas ficam como sensibilidade.
- X principal: idade materna, escolaridade materna, raça/cor materna, situação conjugal, paridade, perdas fetais e UF de residência.
- Missing categórico recebe categoria explícita; idade usa mediana e indicador no pipeline.
- O balanceamento bruto apresenta desequilíbrio material, especialmente em situação conjugal e escolaridade.
- Nenhum perfil marginal pré-especificado apresentou T praticamente determinístico; isso não substitui o overlap multivariado.
- Propensity logístico L2 em 5 folds OOF: AUC 0,662873; todos convergiram (49–58 iterações, L-BFGS).
- Suporte comum observado: 0,306807–0,973928. Não há scores fora de 0,01–0,99.
- Sensibilidade 0,05–0,95 excluiria 147.550 registros (140.879 tratados e 6.671 controles).
- Gate `PRONTO_COM_RESSALVAS`: suporte permite o exercício exploratório; confundimento não observado, seleção de nascidos vivos e mensuração continuam limitantes.

## Decisões abertas

- Registros com `CONSPRENAT=0` e mês válido são discordantes (684 precoces e 414 tardios na base). A classificação segue MESPRENAT; zero consultas não é usado para criar controles nem para excluir retroativamente registros.
- Estabilidade e significado operacional de `contador` entre extrações.
- Plausibilidade de exchangeability condicional diante de confundidores socioeconômicos e de acesso não observados.

## Riscos metodológicos iniciais

- Confundimento residual em dados observacionais.
- Temporalidade ambígua de variáveis coletadas ao longo da gestação.
- Missing e códigos especiais na variável de início do pré-natal.
- Possível viés de seleção ao excluir registros sem informação válida.
- Risco de leakage ao usar consultas, idade gestacional, parto ou características neonatais como X.

## Recomendações metodológicas após a entrega

1. Discutir com orientação acadêmica a revisão do gate de concentração de influência concluída na Fase 3, sem reinterpretá-lo como teste universal de invalidade.
2. Avaliar seleção, confundimento não observado e incerteza por dependência geográfica antes de promover conclusões causais.
3. Usar os notebooks como material do trabalho, mantendo resultados condicionais e limitações explícitas.

## Resultado da Fase 2

- População integral preservada: 2.251.570. Sem trimming oculto. Três folds estratificados T/Y, seed 20240925.
- Predição (teste N=450.314): logística ROC-AUC 0,574248, AP 0,100220, Brier 0,072350; HGB 0,583494, 0,104537 e 0,072239. Discriminação limitada, calibração por decis razoável. Precision/recall/F1 ao limiar 0,5 são zero.
- Associação bruta NÃO CAUSAL: −1,423859 pp.
- C1 AIPW: −1,340527 pp (SE 0,061994; IC95% −1,462034 a −1,219019).
- C2 AIPW: −1,231456 pp (SE 0,061981; IC95% −1,352938 a −1,109973).
- 0,01–0,99 não altera N; 0,05–0,95 mantém 2.103.319, C1 −1,382662 pp e C2 −1,273369 pp.
- Todos os ajustes logísticos convergiram. HGB usa early stopping interno ao treino.
- Gate `RESULTADO_NAO_INTERPRETAVEL` segundo regra conservadora pré-especificada: top 1% de |IF| concentra 78,8% de IF² (limite do plano 50%). Estimativas são estáveis entre modelos e trimming; o gate decorre desse diagnóstico, não de falha de execução.
- Este limiar não é um critério universal de identificação ou validade assintótica. Contribuição máxima individual é ~0,0015 pp; ESS dos controles ~232.772. Os resultados e esse contraponto são preservados para revisão.
- Sem placebo defensável; heterogeneidade omitida; nenhum Causal Forest ou artigo final produzido.
