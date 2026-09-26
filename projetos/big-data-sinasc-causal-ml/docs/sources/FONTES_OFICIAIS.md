# Fontes oficiais

## Conjunto SINASC

- Instituição: Ministério da Saúde, Portal de Dados Abertos do SUS.
- Página do conjunto: <https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc>
- Recurso: **Nascidos Vivos - 2024**.
- CSV oficial: <https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINASC/csv/SINASC_2024_csv.zip>
- Acesso: 2026-09-25.

## Dicionário

- Recurso oficial: **Dicionário de Dados**.
- Arquivo localizado a partir da página oficial: <https://diaad.s3.sa-east-1.amazonaws.com/sinasc/SINASC+-+Estrutura.pdf>
- Título interno: *SINASC: Estrutura de 1996 a 2019 - Dicionário de Dados - Evolução Temporal dos Campos*.
- Acesso: 2026-09-25.

## Limitação documental

O dicionário oficial disponível no portal descreve a evolução da estrutura até 2019, enquanto o arquivo auditado é de 2024. As 62 colunas reais foram confrontadas com esse documento. O campo `OPORT_DN` não foi localizado no PDF, e o código `99` observado em `MESPRENAT` não tem definição explícita nele. Ambos permanecem como questões abertas; nenhuma semântica foi inventada.

Hashes, tamanhos e caminhos locais estão em `data/raw/source_manifest.json`.
