# Plano de reorganização

Plano baseado no [inventário](INVENTARIO_REPOSITORIO.md). Princípio geral: separar as três fases científicas sem tocar no que está congelado por hash, sem reexecutar estimações e sem apagar nada de forma irreversível.

## Decisões

### Estrutura de destino

```text
notebooks/
  principal/                    análise atual: SP capital, ATO
    05a_qualidade_geografica_sp_2014_2024.ipynb   (antes em outputs/qualidade_geografica_2024/)
    05b_comparabilidade_sp_capital_2024.ipynb     (antes em outputs/comparabilidade_sp_capital_2024/)
    06_ato_sp_capital_2024.ipynb
    07_evolucao_ato_sp_capital_2014_2024.ipynb
    08_temporalidade_prenatal_sp_capital_2024.ipynb
  entrega_1_nacional_aipw/      Entrega 1: série nacional 2014–2024 (antes principal/01–05)
  historico/                    desenvolvimento da extensão temporal nacional (inalterado)
  01–05 (raiz)                  fase inicial 2024 (inalterado: exigido pelo validador)
docs/
  GUIA_REVISAO_MIKE.md          novo
  sp_capital_ato/               análise atual: resumo para redação, PDF e fonte LaTeX da Etapa 1
  entrega_1_nacional_aipw/      Entrega 1 (antes docs/entrega/, parte nacional)
  manutencao/                   registros desta reorganização
  demais pastas                 inalteradas
outputs/
  figuras_interativas/          novo: HTML dos gráficos principais + plotly.min.js compartilhado
  entrega_1_nacional_aipw/      antes outputs/entrega/
  qualidade_geografica_2024/, comparabilidade_sp_capital_2024/, sinasc_sim_piloto_2024/   resultados da análise atual (sem notebooks e sem o ZIP bruto)
  diagnostics/, tables/, figures/, temporal/   inalterados (congelados ou referenciados por src/testes)
data/raw/sim/DO24OPEN_csv.zip   ZIP oficial do SIM, antes dentro de outputs/
_arquivo_local/                 fora do Git: material retirado da estrutura ativa e backup inicial
```

### Justificativas das escolhas não óbvias

- **Nome `entrega_1_nacional_aipw` em vez de `entrega_1`:** a análise atual já tem um pacote chamado "Etapa 1"; um nome só com o número repetiria a ambiguidade. O nome descritivo identifica fase, população e estimador.
- **`notebooks/principal/` mantém o nome:** o PDF entregue cita `notebooks/principal/06_ato_sp_capital_2024.ipynb` oito vezes, e a seção 7 do próprio notebook lê o arquivo por esse caminho.
- **Notebooks de qualidade e comparabilidade saem de `outputs/`:** são etapas da análise principal, anteriores ao 06; ficavam escondidos entre resultados. Eles gravam em `raiz/outputs/...` por caminho absoluto calculado, de modo que a mudança de pasta não altera onde gravam. Os prefixos `05a` e `05b` dão a ordem de leitura sem colidir com 06–08.
- **Caminhos citados no PDF da Etapa 1:** o PDF e sua fonte LaTeX são entregáveis já enviados e não são editados. `docs/sp_capital_ato/README.md` traz a tabela de correspondência entre caminhos antigos e novos.
- **Pastas congeladas não se movem:** `outputs/diagnostics/`, `outputs/tables/`, `apresentacao/` e os notebooks 01–05 da raiz têm hash ou caminho fixo nos validadores. `outputs/temporal/` é lido por `src/` e testes e citado no contrato V2 congelado.
- **`_arquivo_local/` é ignorado pelo Git:** guarda, sem apagar, o que sai da estrutura ativa (material de aula, pacote do compartilhamento anterior, ZIPs e anexos duplicados). Os arquivos de texto relevantes também estão no histórico do Git (commit `663becf`).

### Correções científicas (sem reexecutar estimações)

| Local | Correção |
|---|---|
| 06, perfil ponderado | apresentar T=1 e T=0 ponderados separadamente; distinguir covariáveis ajustadas de variáveis só de diagnóstico; situação conjugal sem proporção única |
| 06, 07, resumo | "balanço exato" → balanço aproximadamente igual nas covariáveis e nos termos do escore |
| 06, 08, resumo | restrição a 4–6 meses reduz a janela de início tardio, mas não demonstra atenuação do viés nem sua direção |
| 08 | "confiáveis" → separar consistência interna, completude e validade da mensuração |
| 07 | retirar formulações que sugerem teste de significância entre anos |

### Regeneração de saídas

- **06:** reexecutar as células determinísticas e baratas (consulta, escore logístico de 1 s, balanço, perfil, gráficos novos) e a seção 7 (um ajuste logístico); comparar as saídas das células não alteradas com as originais e manter as originais. O bootstrap **não** é reexecutado: o gráfico de riscos e o texto interpretativo usam os percentis já salvos, recuperados da saída original.
- **07:** nenhuma estimação anual é refeita. Os gráficos são regenerados a partir dos valores salvos (JSON Plotly em precisão integral e tabelas exibidas). Textos fixos alterados recebem a mesma substituição no código e na saída.
- **08:** descritivo, sem modelos; reexecução completa e barata, com comparação das tabelas.

## Checklist

- [x] 0. Proteção: branch, commit de snapshot, backup verificado, [estado inicial](ESTADO_INICIAL_REPOSITORIO.md)
- [x] 1. [Inventário](INVENTARIO_REPOSITORIO.md)
- [x] 2. Plano (este documento)
- [x] 3. Movimentações e atualização de referências; validadores e testes
- [x] 4. Consolidação de dependências
- [x] 5. Correções científicas nos notebooks 06–08 e no resumo
- [x] 6. Gráficos Plotly e exportação HTML interativa
- [x] 7. Testes leves de proteção
- [x] 8. README, guia de revisão e índices de pastas
- [x] 9. [Validação final](VALIDACAO_FINAL.md) e [relatório de alterações](ALTERACOES_REALIZADAS.md)
