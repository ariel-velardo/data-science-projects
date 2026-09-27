# SINASC 2024 — pré-natal, baixo peso e aprendizado de máquina

Trabalho acadêmico de **Big Data & Analytics**. Fases 0–4 concluídas; Fase 5 consolida a entrega sem novos modelos.

## Pergunta

Entre gestantes comparáveis em características observáveis, iniciar o pré-natal até o terceiro mês de gestação está associado a uma redução no risco de baixo peso ao nascer?

O início precoce apresenta menor risco ajustado na população selecionada. A estabilidade numérica não comprova causalidade: confundimento residual, seleção de nascidos vivos e temporalidade das covariáveis continuam limitantes.

## Comece aqui

- Abra [o relatório interativo](apresentacao/relatorio_interativo_sinasc_2024.html) com dois cliques após baixar o arquivo. Funciona offline, sem Python ou servidor. O GitHub pode exibir o código em vez de renderizar.
- Leia a [síntese executiva](docs/SINTESE_EXECUTIVA.md), os [resultados](docs/RESULTADOS_PRINCIPAIS.md) e a [metodologia](docs/METODOLOGIA_DO_PROJETO.md).
- Consulte o [dicionário das 62 colunas](docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md), o [fluxo](docs/dados/FLUXO_DOS_DADOS.md), as [referências](docs/literature/REFERENCIAS_CENTRAIS.md) e o [esqueleto do artigo](docs/artigo/ESQUELETO_ARTIGO.md).

## Números centrais

| Indicador | Resultado |
| --- | --- |
| Registros brutos | <span data-metrica="bruto">2.389.325</span> |
| Colunas originais | <span data-metrica="colunas">62</span> |
| Registros analíticos | <span data-metrica="n">2.251.570</span> |
| T=1: início até o terceiro mês | <span data-metrica="n_t1">1.942.045</span> |
| T=0: início após o terceiro mês | <span data-metrica="n_t0">309.525</span> |
| Baixo peso na população analítica (%) | <span data-metrica="prevalencia">7,894891</span> |
| UFs de residência | <span data-metrica="ufs">27</span> |
| C1 AIPW: estimativa (pp) | <span data-metrica="C1_estimativa_pp">-1,340527</span> |
| C2 AIPW: estimativa (pp) | <span data-metrica="C2_estimativa_pp">-1,231456</span> |
| CATE HGB média (pp) | <span data-metrica="cate_media_pp">-1,294100</span> |
| Gate da Fase 4 | <span data-metrica="gate4">HETEROGENEIDADE_SENSIVEL_A_MODELO</span> |

## Fonte e arquitetura

Ministério da Saúde, [SINASC — dados abertos](https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc), recurso Nascidos Vivos 2024. [Documentação oficial](docs/sources/FONTES_OFICIAIS.md).

`data/raw/` preserva o ZIP e o dicionário; `data/processed/` guarda o Parquet; `src/` contém pipelines; `outputs/diagnostics/` registra números e contratos; `notebooks/` apresenta as fases; `docs/` consolida métodos/literatura; `apresentacao/` contém o HTML. Dados grandes e caches ficam locais.

## Notebooks e reprodução

Sequência: 01 auditoria → 02 amostra/overlap → 03 predição/AIPW → 04 robustez → 05 heterogeneidade. Veja [entradas, objetivos e saídas](docs/REPRODUCAO.md). Os cinco notebooks já estão executados.

No PowerShell, dentro deste projeto:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = "1"
python -m pytest -q tests
python -m src.entrega_fase5
python -m src.entrega_fase5 --validar
Start-Process .\apresentacao\relatorio_interativo_sinasc_2024.html
```

Para configurar um ambiente novo e reproduzir as fases, siga [REPRODUCAO.md](docs/REPRODUCAO.md). Abrir o HTML não exige reinstalar ou recalcular.

## Estado e limites

Gates preservados: Fase 0 `VIAVEL_COM_RESSALVAS`; Fase 1 `PRONTO_COM_RESSALVAS`; Fase 2 `RESULTADO_NAO_INTERPRETAVEL`; Fase 3 `GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR`; Fase 4 `HETEROGENEIDADE_SENSIVEL_A_MODELO`. A revisão da Fase 3 questiona o veto pela concentração de influência, sem apagar o gate histórico nem certificar identificação causal.

[Estado atual e histórico](docs/playbooks/ESTADO_ATUAL.md). `CAUSALIDADE_PROVADA = NAO`. A modelagem terminou; o artigo completo ainda não foi escrito. Uma versão Streamlit pode ser desenvolvida futuramente para portfólio.
