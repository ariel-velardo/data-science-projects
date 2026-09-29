# Refatoração estrutural de src

## Baseline

HEAD inicial `5ae8e272dd82016928b84dd3629decbecc1bff82`, main sincronizada após fetch; 93 testes aprovados. Dados, métricas, gates e fontes registrados no [baseline](BASELINE_PRE_REFATORACAO.md).

## Alterações implementadas

35 arquivos Python históricos deram lugar a 13 arquivos em src (12 módulos conceituais e inicializador), com três CLIs em scripts. Cinco geradores foram removidos após migrar consumidores e passar 104 testes. Os notebooks são fontes versionadas.

Os cálculos científicos de 122 funções/classes permanecem idênticos por comparação de AST. A geração de figuras tem somente import atualizado. Os controladores e guardas foram adaptados à arquitetura; os contratos históricos e tolerâncias permanecem.

[A arquitetura final](ARQUITETURA_FINAL.md) e [a auditoria por arquivo](AUDITORIA_SRC.md) documentam consolidações, remoções e responsabilidades. A validação final foi concluída, com contrato histórico e ciência preservados; nenhum merge foi realizado.
