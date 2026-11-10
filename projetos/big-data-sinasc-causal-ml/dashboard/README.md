# Painel acadêmico SINASC

Painel interativo do estudo "Início do pré-natal e baixo peso ao nascer, São Paulo (capital), 2014–2024". É um único arquivo HTML que funciona offline, aberto diretamente pelo navegador.

**Abrir:** `dist/sinasc_dashboard_ipt.html`, com duplo clique, em Chrome ou Edge.

## Regenerar

Ative a `.venv` do projeto (`projetos/big-data-sinasc-causal-ml/.venv`). A partir da raiz do projeto:

```powershell
python dashboard/construir.py
python -m pytest dashboard/tests -q
node dashboard/verificacao/verificar_navegador.mjs
```

A geração lê somente notebooks salvos, CSVs e Markdown versionados. Não requer os Parquets, não reexecuta o bootstrap e não recalcula estimativas. O mesmo conteúdo de entrada produz os mesmos hashes (há teste para isso).

O verificador usa Chrome e Edge instalados e o Node 22 ou superior, sem dependências adicionais. Ele abre o arquivo com a rede desligada, percorre as sete abas em três larguras, aciona todos os filtros e grava `verificacao/relatorio_navegador.json` e as capturas em `verificacao/capturas/`.

## Organização

| Caminho | Função |
|---|---|
| `construir.py` | orquestra a geração e escreve o manifesto |
| `pipeline/fontes.py` | lê notebooks, tabelas HTML, figuras Plotly e CSVs |
| `pipeline/dados.py` | monta os agregados e aplica o controle de células pequenas |
| `pipeline/logo.py` | converte o logotipo vetorial do pacote Overleaf em SVG |
| `pipeline/matriz.py` | matriz de rastreabilidade dos indicadores |
| `pipeline/pagina.py` | embute estilo, script, dados e Plotly em um único HTML |
| `web/` | modelo HTML, CSS e gráficos em JavaScript |
| `tests/` | testes de consistência, divulgação e reprodutibilidade |
| `verificacao/` | verificação em navegador real e capturas |
| `dist/` | HTML, dados agregados, matriz e manifesto |
| `REGISTRO_METODOLOGICO.md` | transformações, fontes, avaliação de células pequenas e limitações |

## Manutenção

- Texto com números usa marcadores como `[[resultados.dif_ato.valor|pp]]` em `web/modelo.html`, resolvidos na geração. Evite digitar números à mão.
- Cada leitura de saída de notebook confere um trecho do título ou do cabeçalho. Se a posição de uma célula mudar, a geração falha em vez de pegar o valor errado; atualize o índice em `pipeline/dados.py`.
- Novos gráficos entram em `G` em `web/app.js` e num `<figure data-fig="...">` em `web/modelo.html`.
- Novas contagens devem passar por `mascarar()` e usar nomes iniciados em `n_`, que são cobertos pelo teste de células pequenas.
- O `.gitignore` do projeto ignora `*.html`, com exceções específicas para `dashboard/dist/sinasc_dashboard_ipt.html` e `dashboard/web/modelo.html`. O HTML final e o modelo necessário à regeneração são versionados e ficam disponíveis em clones futuros.
- O arquivo local `.gitattributes` preserva LF nos quatro artefatos de `dist/`, evitando conversão para CRLF em clones e exports e mantendo os hashes da entrega.
