# Validação final da reorganização

Executada em 24/10/2026 na branch `chore/reorganizacao-revisao-mike`, com a `.venv` do projeto (Python 3.11.9). Nenhuma estimação foi refeita para validar.

## Resultado

| Verificação | Como | Resultado |
|---|---|---|
| Suíte de testes | `python -m pytest -q tests` | **335 aprovados** (322 da linha de base + 13 novos em `tests/test_analise_sp_capital.py`) |
| Preservação das fases anteriores | `python scripts/validar_projeto.py --rapida` (hashes do baseline, gates, notebooks 01–05 da raiz, métricas do README, links de `docs/`) | aprovada |
| Links relativos | `src.validacao.links_quebrados` em README, `docs/`, `notebooks/` e `outputs/`; varredura dos links em markdown de todos os notebooks | nenhum quebrado (dois links quebrados anteriores, nos históricos 09 e 10, foram corrigidos) |
| Estrutura dos notebooks principais | `nbformat.validate`; células de código executadas; ausência de saídas de erro; PNG de apoio em cada gráfico Plotly | 5 notebooks válidos; 11 gráficos, todos com PNG |
| Preservação das saídas | comparação célula a célula (por `id`) com o snapshot original `663becf` | ver tabela abaixo |
| Números nos textos regenerados | comparação frase a frase e da sequência de números com o original | sequência de números idêntica nos três textos; só as frases corrigidas mudaram |
| Contrato da seção 7 do notebook 06 | execução da célula de recuperação contra o arquivo novo | recupera −1,74 p.p., n efetivo [84.995; 10.096] e máximo \|SMD\| 0,1945 (teste automatizado) |
| Exportação interativa | `python scripts/exportar_figuras_interativas.py --verificar`; renderização de um HTML com o Chrome *headless* | sincronizada; sem scripts de CDN; renderiza offline com `plotly.min.js` local |
| Dependências | versão instalada de cada pacote de `requirements.txt` conferida contra o especificador; `pip check` | todas satisfeitas; sem conflitos |
| Credenciais | busca por padrões de chave, token, senha e chave privada | nenhuma ocorrência (apenas identificadores internos do Plotly.js no HTML de 2024) |
| Git | `git status` | árvore limpa ao final; nada enviado ao remoto |

### Saídas por notebook, comparadas ao estado original

| Notebook | Células de código | Saídas idênticas ao original | Saídas alteradas (intencionais) |
|---|---:|---:|---|
| 05a qualidade geográfica | 10 | 10 | nenhuma (só um link em markdown) |
| 05b comparabilidade | 12 | 11 | texto de limitações (uma frase sobre temporalidade) |
| 06 ATO 2024 | 18 (2 novas) | 13, incluindo o bootstrap e toda a seção 7 | gráfico de balanço, tabela de perfil, gráfico de riscos, texto interpretativo; novo gráfico do escore e dos pesos |
| 07 série 2014–2024 | 17 | 14, incluindo todas as tabelas e estimações anuais | dois gráficos; uma frase da interpretação |
| 08 temporalidade | 11 | 9 | dois gráficos |

No 06 e no 08, as células não alteradas foram reexecutadas e reproduziram as saídas originais, que foram mantidas. As únicas diferenças eram voláteis: duração da execução e fragmentação do `stdout`. No 07, apenas a configuração e os gráficos foram executados, alimentados pelos valores salvos.

### Valores de referência conferidos (testes automatizados)

| Valor | Esperado | Fonte conferida |
|---|---|---|
| Nascimentos / T=1 / T=0 / casos | 114.694 / 104.576 / 10.118 / 9.850 | saída da célula de população do 06 |
| Risco ATO T=1 / T=0 | 8,68% / 10,42% | traço "Risco ponderado ATO" do gráfico do 06 |
| Diferença ATO e IC 95% | −1,74 p.p. (−2,36 a −1,12) | tabela do bootstrap do 06 |
| Diferença bruta e IC 95% | −2,00 p.p. (−2,61 a −1,37) | idem |
| Bootstrap | 1.000 réplicas, 1.000 convergiram | idem |
| n efetivo (Kish) | 84.995 / 10.096 | tabela de pesos do 06 |
| Situação conjugal ponderada | casadas 27,1% (T=1) e 18,6% (T=0) | tabela de perfil do 06 |
| Série ATO 2014–2024 | −1,11; −0,99; −1,08; −1,57; −1,80; −1,19; −0,58; −1,73; −1,77; −1,90; −1,74 | gráfico da série do 07 |
| T=0 e elegíveis por ano | 24.348 … 10.118; 164.987 … 114.694 | gráfico de participação do 07 |
| Seleção antes do filtro de início | 2.728 de 117.422 fora de B; 43 / 546 / 589 com < 28 semanas | tabela complementar do 08 |

Os mesmos valores constam do [resumo para redação](../sp_capital_ato/RESUMO_PARA_REDACAO.md) e do PDF da Etapa 1.

## O que não foi validado

- **Reexecução integral** do bootstrap do 06 e das onze estimações anuais do 07: não feita, por decisão de preservação. A reprodutibilidade do ajuste pontual de 2024 foi conferida (riscos idênticos aos salvos, com tolerância de 1e-12).
- **`scripts/validar_projeto.py --completa`**: não executado, porque reexecuta os notebooks da fase inicial e lê caches grandes.
- **Instalação em ambiente novo** a partir do `requirements.txt`: não testada, já que a tarefa não autorizava instalar pacotes; a `.venv` existente satisfaz todos os especificadores.
- **Exibição no Jupyter Lab e no VS Code** da configuração da barra de ferramentas embutida nas saídas: não inspecionada visualmente; foi conferida nos HTML exportados e nas imagens PNG.
- **Renderização no GitHub**: não verificada (nada foi enviado ao remoto).

## Riscos e pendências conhecidos

- `python -m src.entrega` sem argumentos regenera o README da fase inicial 2024 e **sobrescreve o README atual**. O módulo é congelado por hash e não foi alterado; há avisos no README e em `docs/REPRODUCAO.md`.
- O PDF da Etapa 1 cita caminhos anteriores à reorganização; correspondência em [`docs/sp_capital_ato/README.md`](../sp_capital_ato/README.md).
- Notebooks históricos 09c e 09d listam `requirements_before_spark.txt` entre os arquivos com hash; se fossem reexecutados, precisariam do arquivo, que está no commit `663becf`.
- `_arquivo_local/` (122 MB, fora do Git) guarda o material retirado e o backup inicial; só existe nesta máquina.
