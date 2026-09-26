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

## Manual vigente de preenchimento da DNV

- Título: **Declaração de Nascido Vivo: manual de instruções para preenchimento**.
- Instituição: Ministério da Saúde, Secretaria de Vigilância em Saúde, Departamento de Análise Epidemiológica e Vigilância de Doenças Não Transmissíveis.
- Edição: 4ª edição, Brasília, 2022.
- Página institucional do SINASC: <https://www.gov.br/saude/pt-br/composicao/svsa/sistemas-de-informacao/sinasc>.
- PDF oficial: <https://svs.aids.gov.br/daent/cgiae/coesv/sistemas-informacao/sinasc/documentacao/declaracao-nascido-vivo-manual-instrucoes-preenchimento.pdf>.
- Acesso: 2026-09-25.
- Arquivo local: não baixado; a URL oficial foi consultada diretamente, portanto não há SHA-256 local.

Definições relevantes do bloco V (gestação e parto):

- histórico gestacional refere-se a eventos anteriores e não inclui a gestação atual;
- `CONSPRENAT` é o número exato de consultas; `0` representa ausência de pré-natal e dado desconhecido deve ser registrado como ignorado;
- `MESPRENAT` é o mês de gestação da primeira consulta; dado desconhecido deve ser registrado como ignorado;
- no formulário vigente, `99` representa o preenchimento **Ignorado** para o mês de início do pré-natal;
- `GRAVIDEZ`: `1=única`, `2=dupla`, `3=tripla ou mais`, `9=ignorado`; em gestações múltiplas, há uma DNV por nascido vivo;
- `TPMETESTIM`: `1=exame físico`, `2=outro método`, `9=ignorado`, usado quando a DUM é ignorada.

Consequência operacional: `MESPRENAT=99` é informação ignorada, não ausência de pré-natal. A análise principal mantém `99` e missing como `T=NA`. Registros com `CONSPRENAT=0` são descritos separadamente e não são incorporados automaticamente ao controle.

## Definição internacional do outcome

- Fonte: Organização Mundial da Saúde, indicador *Low birthweight*.
- URL: <https://www.who.int/data/nutrition/nlis/info/low-birth-weight>.
- Acesso: 2026-09-25.
- Definição: peso ao nascer inferior a 2.500 g, independentemente da idade gestacional.
- Observação de qualidade: a OMS recomenda registrar o primeiro peso após o nascimento e alerta para preferência por dígitos e erros de mensuração. A OMS não estabelece `500–6.000 g` como regra universal de inclusão.

## Limitação documental remanescente

O dicionário estrutural disponível no portal descreve a evolução até 2019, enquanto o arquivo auditado é de 2024. O manual de 2022 resolve a semântica substantiva de `MESPRENAT=99`, mas não substitui um layout técnico completo específico de 2024. O campo `OPORT_DN` continua sem definição no PDF estrutural localizado.

Hashes, tamanhos e caminhos locais estão em `data/raw/source_manifest.json`.
