# Erratas interpretativas dos registros históricos

Data: 01/10/2026. Estas notas corrigem a **atribuição documental** de uma interpretação; não alteram dados, elegibilidade, código, estimativas, gates ou notebooks executados. Os artefatos históricos continuam como registros da decisão tomada à época.

## `MESPRENAT=99`

O estado documental atual é **`CODIFICACAO_OPERACIONAL_OBSERVADA`**. O Manual DNV 2022 orienta registrar mês desconhecido como “Ignorado”, mas a auditoria 09c/09d não encontrou nele uma associação literal entre o número `99` e esse significado para `MESPRENAT`. Portanto, não é sustentada a afirmação “o Manual DNV 2022 confirma que `MESPRENAT=99` significa ignorado”. O código `99` e valores vazios seguem fora de T na V1 e na V2; `CONSPRENAT=0` não é convertido automaticamente em controle. Uma confirmação oficial específica do código permanece pendente.

Ocorrências a ler com esta errata, sem reescrever os registros congelados:

- [Notebook 02](../../notebooks/02_amostra_desenho_e_overlap.ipynb) e [notebook 06](../../notebooks/06_auditoria_historica_sinasc.ipynb): formulações antigas que atribuem a semântica de `99` ao manual.
- [Baseline anterior à refatoração](../architecture/BASELINE_PRE_REFATORACAO.md): captura literal da interpretação antiga, inclusive a seção “Evidência documental nova”.
- [Estado histórico da Fase 1](../playbooks/ESTADO_ATUAL.md): frase que diz que a confirmação veio do manual; a seção atual no topo aponta para esta errata.
- [Fontes oficiais](../sources/FONTES_OFICIAIS.md): afirmação sobre o formulário e conclusão de que o manual resolve a semântica numérica.
- [Dicionário analítico 2024](../dados/DICIONARIO_ANALITICO_SINASC_2024.md): célula de `MESPRENAT` com “Manual 2022: 99=ignorado”.
- [Gerador da entrega histórica](../../src/entrega.py) e [auditoria de dados](../../src/auditoria_dados.py): textos/labels de proveniência documental que exigiriam revisão coordenada com saídas geradas; nenhuma execução foi feita aqui.

As formulações que apenas excluem `99` de T ou o chamam de código operacional observado não exigem correção científica. O [contrato V2](CONTRATO_V2_PRE_ESTIMACAO.md) registra a distinção correta. Os resumos locais de literatura citados no contrato V2 também devem ser lidos sob esta ressalva, sem edição nesta rodada.

## Leitura da auditoria 09b

O LOCO individual alterou pouco o ponto (máximo C1: 0,0346 p.p.). Exclusões conjuntas Top 5/10 chegaram a 0,1205 p.p. no Top 10, removendo até cerca de 13% da população observada. A inferência apresenta concentração em alguns clusters, e exclusões conjuntas de grandes municípios alteram moderadamente o ponto, **em uma população observada diferente**. Essas exclusões não definem estimandos alternativos. Nenhum sinal mudou, nenhum IC municipal passou a incluir zero e a transição 2021–2022 não foi explicada pelos clusters mais influentes. Esta leitura complementa o [09b](../../notebooks/09b_auditoria_inferencia_temporal.ipynb), sem alterar seus resultados.
