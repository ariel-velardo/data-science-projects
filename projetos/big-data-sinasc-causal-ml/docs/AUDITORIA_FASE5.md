# Auditoria da consolidação acadêmica

## Estado inicial

Fetch concluído, branch `main`, HEAD e origin/main em `07e9b7be28d3561a702f7f498c8a6632a9fde4e2`. Commits de Fase 3, PT-BR e Fase 4 confirmados. Nenhuma alteração pendente no projeto; pasta não rastreada em projeto vizinho preservada. A suíte inicial passou com 86 testes.

## Evidência de validação

| Verificação | Resultado | Limite |
|---|---|---|
| Testes completos | 93 aprovados: 86 herdados e 7 novos | Testes não identificam causalidade |
| Fases 2–3 | Seis resultados históricos e 22 linhas reconciliados | Sem reestimar auxiliares |
| Fase 4 | Cobertura única, partições municipais, pseudo-desfechos, perfis e preservação aprovados | CATE permanece sensível ao modelo |
| Cinco notebooks | 7 / 12 / 13 / 21 / 10 células executadas, sem erros | Inspeção dos arquivos entregues; não reexecução nesta fase |
| Apresentação histórica | `src.valida_apresentacao` aprovado | Contrato histórico cobre notebooks 01–04; notebook 05 conferido pela validação de Fase 4 e da entrega |
| Ambiente | `pip check` aprovado | Nenhum pacote instalado; `.venv` preservada |
| Consistência numérica | README, síntese, resultados e HTML reconciliados com JSONs | Arredondamento explícito a seis casas; contagens inteiras |
| Gráficos | Dez séries/layouts incorporados conferidos; dez PNGs inspecionados | Não substitui inspeção do layout completo do HTML |
| Dicionário | 62/62, ordem e nomes reconciliados; linhas HTML conferidas | OPORT_DN sem definição; códigos não documentados permanecem desconhecidos |
| Links locais | Caminhos Markdown e âncoras conferidos | PDFs não são dependência de navegação |
| Links externos | 24 URLs verificadas: 17 HTTP 200, 1 HTTP 202, 4 HTTP 403 e 2 sem resposta no prazo | HTTP 200 não demonstra conteúdo acessível: pode haver desafio de navegador; não se contornaram bloqueios |
| Idioma | Conteúdo novo em PT-BR; verificação de codificação e revisão de títulos/figuras | Títulos bibliográficos, identificadores e termos técnicos preservados |
| HTML | 14 seções, 10 figuras, runtime embutido; aproximadamente 4,94 MB | Abertura e controles não verificados em navegador |

Comandos, na `.venv` do projeto:

```powershell
python -m pytest -q tests
python -m src.valida_resultados_fase3
python -m src.valida_resultados_fase4
python -m src.valida_apresentacao
python -m src.entrega_fase5 --validar
python -m pip check
git diff --check
```

## Ressalva visual

O navegador interno estava indisponível. O Chrome recusou a URL `file://` pela política de segurança da ferramenta. Nenhum servidor alternativo, navegador alternativo ou comando indireto foi utilizado para contornar a recusa. As figuras foram inspecionadas como PNGs, separadamente da página. O estado da entrega é **APROVADO_COM_RESSALVA_VISUAL**: abrir o HTML manualmente e conferir busca, navegação, expansões e legibilidade antes da apresentação.

## Literatura e distribuição

Doze referências e doze fichas curtas. PDFs obtidos: Falcão, Ranjbar, Chernozhukov, Kennedy e Chiang. Não obtidos nesta sessão: Vale, Bonilha, Funk, Petersen, Austin, Cameron e Snowden; motivos no [manifesto](literature/MANIFESTO_ARTIGOS.md). Não se declara indisponibilidade mundial: somente resultado das tentativas públicas desta sessão.

PDFs e textos extraídos permanecem locais e não são versionados. Como `.gitignore` foi preservado, essa pasta pode aparecer como não rastreada no `git status`; não representa alteração de dados/modelos. HTML, dicionário JSON e histograma agregado JSON são exceções adicionadas explicitamente ao Git; não foram liberados diretórios inteiros de outputs.

## Contratos das saídas

| Artefato | Granularidade / chave | Validação | Limitação / próximo passo |
|---|---|---|---|
| Dicionário | Campo original / nome | 62 nomes únicos em ordem; missing do schema | Confirmar layout técnico de 2024 quando publicado/localizado |
| Resultados | Indicador ou cenário/modelo | JSONs históricos e marcadores numéricos | Interpretação condicional; usar na redação do artigo |
| HTML | Seção, figura e indicador | Estrutura, números, séries e tamanho | Conferência manual no navegador |
| Referências/fichas | Referência / ID bibliográfico | Fontes públicas, PDFs e manifesto | Adequar estilo bibliográfico às normas da disciplina |
| Esqueleto do artigo | Seção / título | Cobertura do argumento, resultados e referências | Escrever o artigo em etapa separada |

`MODELAGEM_CONCLUIDA = SIM`; `ARTIGO_COMPLETO = NAO`; `RELATORIO_HTML = SIM`; `CAUSALIDADE_PROVADA = NAO`.
