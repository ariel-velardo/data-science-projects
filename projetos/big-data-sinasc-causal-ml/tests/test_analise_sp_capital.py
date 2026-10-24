"""Proteção da análise SP capital (ATO) contra regressões de organização e apresentação.

Os testes leem apenas arquivos versionados (notebooks executados, documentos e
HTML exportados); nenhum deles precisa das bases do SINASC nem reexecuta modelos.
"""
import base64
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
PRINCIPAL = RAIZ / "notebooks" / "principal"
NB06 = PRINCIPAL / "06_ato_sp_capital_2024.ipynb"
NB07 = PRINCIPAL / "07_evolucao_ato_sp_capital_2014_2024.ipynb"
NB08 = PRINCIPAL / "08_temporalidade_prenatal_sp_capital_2024.ipynb"
MIME_PLOTLY = "application/vnd.plotly.v1+json"


def _nb(caminho):
    return json.loads(caminho.read_text(encoding="utf-8"))


def _texto(valor):
    return "".join(valor) if isinstance(valor, list) else valor


def _celula(nb, ident):
    return next(c for c in nb["cells"] if c.get("id") == ident)


def _saidas_texto(celula):
    partes = []
    for o in celula.get("outputs", []):
        if o.get("output_type") == "stream":
            partes.append(_texto(o["text"]))
        for chave in ("text/plain", "text/html", "text/markdown"):
            if chave in o.get("data", {}):
                partes.append(_texto(o["data"][chave]))
    return "\n".join(partes)


def _vetor(v):
    if isinstance(v, dict) and "bdata" in v:
        arr = np.frombuffer(base64.b64decode(v["bdata"]), dtype=v["dtype"])
        if "shape" in v:
            forma = v["shape"] if isinstance(v["shape"], list) else [int(s) for s in str(v["shape"]).split(",")]
            arr = arr.reshape(forma)
        return arr
    return np.asarray(v)


def _tracos(nb):
    return [t for c in nb["cells"] for o in c.get("outputs", [])
            for t in o.get("data", {}).get(MIME_PLOTLY, {}).get("data", [])]


def links_quebrados(arquivo):
    """Links relativos (e âncoras) inexistentes; links dentro de blocos de código são ignorados."""
    texto = arquivo.read_text(encoding='utf-8')
    if arquivo.suffix == '.md':
        linhas, cerca = [], None
        for linha in texto.splitlines():
            marcador = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', linha)
            if cerca is None:
                if marcador:
                    cerca = marcador.group(1)
                else:
                    linhas.append(linha)
            elif (marcador and marcador.group(1)[0] == cerca[0]
                  and len(marcador.group(1)) >= len(cerca)
                  and not marcador.group(2).strip()):
                cerca = None
        texto = '\n'.join(linhas)
    destinos = re.findall(r'\]\(([^)]+)\)', texto)
    destinos += re.findall(r'(?:href|src)="([^"]+)"', texto) if arquivo.suffix == '.html' else []
    erros = []
    for destino in destinos:
        u = urlsplit(destino.strip('<>'))
        if u.scheme:
            continue
        alvo = arquivo.parent / unquote(u.path) if u.path else arquivo
        if not alvo.exists():
            erros.append(destino)
        elif u.fragment and alvo.suffix in {'.md', '.html'}:
            conteudo = alvo.read_text(encoding='utf-8')
            ids = set(re.findall(r'id="([^"]+)"', conteudo))
            for titulo in re.findall(r'^#+\s+(.+)$', conteudo, re.M):
                slug = re.sub(r'[^\w -]', '', titulo.lower()).replace(' ', '-')
                ids.add(slug)
                ids.add(''.join(c for c in unicodedata.normalize('NFD', slug) if not unicodedata.combining(c)))
            if unquote(u.fragment) not in ids:
                erros.append(destino)
    return sorted(set(erros))


# ---------------------------------------------------------------- estrutura

def test_estrutura_reorganizada():
    esperados = [
        "notebooks/principal/05a_qualidade_geografica_sp_2014_2024.ipynb",
        "notebooks/principal/05b_comparabilidade_sp_capital_2024.ipynb",
        "notebooks/principal/06_ato_sp_capital_2024.ipynb",
        "notebooks/principal/07_evolucao_ato_sp_capital_2014_2024.ipynb",
        "notebooks/principal/08_temporalidade_prenatal_sp_capital_2024.ipynb",
        "notebooks/entrega_1_nacional_aipw/04_estimacao_aipw.ipynb",
        "docs/sp_capital_ato/RESUMO_PARA_REDACAO.md",
        "docs/sp_capital_ato/PACOTE_REDACAO_ETAPA_1.pdf",
        "docs/entrega_1_nacional_aipw/RELATORIO_FINAL_DISCIPLINA.md",
        "docs/GUIA_REVISAO_MIKE.md",
        "outputs/qualidade_geografica_2024/qualidade_sp_por_ano.csv",
        "outputs/comparabilidade_sp_capital_2024/balanco_covariaveis_2024.csv",
        "outputs/entrega_1_nacional_aipw/tabelas/tabela2_B_principal.csv",
        "outputs/figuras_interativas/index.html",
        "requirements.txt",
    ]
    assert [p for p in esperados if not (RAIZ / p).is_file()] == []
    retirados = ["docs/entrega", "outputs/entrega", "outputs/compartilhamento_professora",
                 "notebooks/apoio_aula", "requirements_before_spark.txt", "outputs/temporal/figuras",
                 # fase inicial Brasil 2024 (G1), removida no lote 3 do expurgo
                 "notebooks/01_auditoria_sinasc_2024.ipynb", "notebooks/05_heterogeneidade_causal.ipynb",
                 "apresentacao", "docs/architecture", "docs/artigo", "docs/REPRODUCAO.md",
                 "src/validacao.py", "src/entrega.py", "scripts/validar_projeto.py", "scripts/executar_pipeline.py"]
    assert [p for p in retirados if (RAIZ / p).exists()] == []


def test_notebooks_principais_validos():
    import nbformat
    for caminho in sorted(PRINCIPAL.glob("*.ipynb")):
        nb = nbformat.read(caminho, as_version=4)
        nbformat.validate(nb)
        codigo = [c for c in nb.cells if c.cell_type == "code"]
        assert all(c.execution_count is not None for c in codigo), caminho.name
        assert not any(o.output_type == "error" for c in codigo for o in c.outputs), caminho.name
        for c in codigo:
            for o in c.outputs:
                if MIME_PLOTLY in o.get("data", {}):
                    assert "image/png" in o["data"], f"{caminho.name}: gráfico sem PNG estático"


# ------------------------------------------------- resultados de referência

def test_resultado_principal_notebook_06():
    nb = _nb(NB06)
    populacao = _saidas_texto(_celula(nb, "38960580"))
    assert "População: 114.694 nascimentos | T=1 104.576 | T=0 10.118 | casos de baixo peso 9.850" in populacao
    bootstrap = _saidas_texto(_celula(nb, "d7f7e271"))
    assert "Bootstrap: 1000 réplicas" in bootstrap and "1000/1000" in bootstrap
    linha = re.search(r"<th>Diferença T=1 − T=0</th>(.*?)</tr>", bootstrap, re.S).group(1)
    assert re.findall(r"<td>([^<]*)</td>", linha) == ["", "", "-2,00 p.p.", "-2,61 a -1,37", "-1,74 p.p.", "-2,36 a -1,12"]
    risco = next(t for t in _tracos(nb) if t.get("name") == "Risco ponderado ATO")
    assert np.round(_vetor(risco["y"]).astype(float), 2).tolist() == [8.68, 10.42]
    pesos = _saidas_texto(_celula(nb, "360e6d38"))
    assert re.search(r"n efetivo \(Kish\)\s+84\.995\s+10\.096", pesos)


def test_perfil_ponderado_separa_grupos_na_situacao_conjugal():
    perfil = _saidas_texto(_celula(_nb(NB06), "e7844949"))
    assert "T=1 ponderado (ATO)" in perfil and "T=0 ponderado (ATO)" in perfil
    assert "População de sobreposição (ATO)" not in perfil
    assert "casadas são 27,1% em T=1 e 18,6% em T=0" in perfil


def test_serie_historica_notebook_07():
    nb = _nb(NB07)
    ato = next(t for t in _tracos(nb) if t.get("name") == "Diferença ATO (ajustada)")
    assert _vetor(ato["x"]).astype(int).tolist() == list(range(2014, 2025))
    assert np.round(_vetor(ato["y"]).astype(float), 2).tolist() == [
        -1.11, -0.99, -1.08, -1.57, -1.80, -1.19, -0.58, -1.73, -1.77, -1.90, -1.74]
    assert "error_y" not in ato or not ato["error_y"].get("array"), "série sem IC anual"
    grupos = next(t for t in _tracos(nb) if t.get("name") == "T=0 entre os elegíveis")
    contagens = _vetor(grupos["customdata"]).astype(float).reshape(11, 3)
    assert contagens[:, 0].astype(int).tolist() == [24348, 24345, 21102, 18959, 17814, 17581,
                                                    15443, 12705, 12370, 11470, 10118]
    assert contagens[:, 2].astype(int).tolist() == [164987, 165787, 158025, 160429, 156806, 150427,
                                                    139283, 129761, 125306, 122244, 114694]


def test_contagens_notebook_08():
    texto = _saidas_texto(_celula(_nb(NB08), "complemento-temporalidade-tabela"))
    assert "Fora de B: 2.728/117.422 (2,32%)" in texto
    assert "43 fora de B; 546 em B; 589 no total" in texto


def test_textos_corrigidos_nao_voltam():
    proibidos = {
        NB06: ["balanço é exato", "atenua, mas não elimina", "mesmo perfil de idade"],
        NB07: ["estatisticamente significativa"],
        NB08: ["as faixas são confiáveis"],
        RAIZ / "docs/sp_capital_ato/RESUMO_PARA_REDACAO.md": ["atenua, mas não elimina", "mesmo perfil", "quase exato"],
    }
    for caminho, frases in proibidos.items():
        conteudo = caminho.read_text(encoding="utf-8")
        assert [f for f in frases if f in conteudo] == [], caminho.name


def test_secao_7_recupera_referencias_do_arquivo_salvo():
    """A sensibilidade do notebook 06 lê as saídas principais salvas; o contrato precisa continuar válido."""
    codigo = _texto(_celula(_nb(NB06), "sens-conjugal-2")["source"])
    codigo += "\nprint(round(dif_principal_sens, 2), ess_principal_sens)\n"
    saida = subprocess.run([sys.executable, "-c", "import sys; sys.dont_write_bytecode = True\n" + codigo],
                           cwd=PRINCIPAL, capture_output=True, text=True, encoding="utf-8", check=True)
    assert "Referência recuperada exclusivamente das saídas principais salvas." in saida.stdout
    assert "-1.74 [84995, 10096]" in saida.stdout


# ------------------------------------------------------------ fórmulas ATO

@pytest.fixture(scope="module")
def medidas_ato():
    """Executa a função ``medidas_ato`` exatamente como está no notebook 07."""
    from src.diagnosticos import validar_colunas_propensity

    def exigir(condicao, mensagem):
        if not condicao:
            raise ValueError(mensagem)
    ambiente = {"np": np, "exigir": exigir, "validar_colunas_propensity": validar_colunas_propensity}
    exec(_texto(_celula(_nb(NB07), "5ab39758")["source"]), ambiente)   # inclui a checagem manual do notebook
    return ambiente["medidas_ato"]


def test_formulas_ato_contra_implementacao_independente(medidas_ato):
    rng = np.random.default_rng(20241024)
    t = rng.integers(0, 2, 5000)
    e = rng.uniform(0.05, 0.95, 5000)
    y = rng.integers(0, 2, 5000)
    m = medidas_ato(t, y, e)
    w = np.where(t == 1, 1 - e, e)
    r1 = (w * y)[t == 1].sum() / w[t == 1].sum()
    r0 = (w * y)[t == 0].sum() / w[t == 0].sum()
    np.testing.assert_allclose([m["r1"], m["r0"], m["dif_ato_pp"]], [r1, r0, 100 * (r1 - r0)])
    np.testing.assert_allclose(m["w"], w)
    for g in (1, 0):
        assert m[f"ess{g}"] <= (t == g).sum()
        np.testing.assert_allclose(m[f"ess{g}"], w[t == g].sum() ** 2 / (w[t == g] ** 2).sum())


def test_riscos_normalizados_nao_dependem_da_escala_dos_pesos(medidas_ato):
    t = np.array([0, 0, 0, 1, 1, 1])
    y = np.array([0, 1, 1, 0, 0, 1])
    e = np.array([0.3, 0.5, 0.7, 0.4, 0.6, 0.8])
    base = medidas_ato(t, y, e)
    assert 0 <= base["r1"] <= 1 and 0 <= base["r0"] <= 1
    # Grupo com desfecho constante tem risco ponderado igual a esse desfecho, quaisquer que sejam os pesos.
    constante = medidas_ato(t, np.array([1, 1, 1, 0, 0, 0]), e)
    assert constante["r0"] == 1 and constante["r1"] == 0
    with pytest.raises(ValueError):
        medidas_ato(t, y, np.array([0.3, 0.5, 1.2, 0.4, 0.6, 0.8]))


# ------------------------------------------------- apresentação e documentos

def test_figuras_interativas_sincronizadas_e_offline():
    sys.path.insert(0, str(RAIZ))
    from scripts.exportar_figuras_interativas import DESTINO, verificar
    assert verificar() == []
    for html in DESTINO.glob("*.html"):
        texto = html.read_text(encoding="utf-8")
        assert not re.search(r'<script[^>]+src="https?://', texto), html.name
    assert (DESTINO / "plotly.min.js").stat().st_size > 1_000_000


def test_links_relativos_e_ancoras(tmp_path):
    p = tmp_path / 'pagina.md'
    p.write_text('[ok](alvo.md#secao) [erro](ausente.md) [web](https://example.org)', encoding='utf-8')
    (tmp_path / 'alvo.md').write_text('# Seção\n', encoding='utf-8')
    assert links_quebrados(p) == ['ausente.md']


def test_detecta_ancora_inexistente(tmp_path):
    p = tmp_path / 'pagina.md'
    p.write_text('[ruim](alvo.md#nao-existe)', encoding='utf-8')
    (tmp_path / 'alvo.md').write_text('# Seção\n', encoding='utf-8')
    assert links_quebrados(p) == ['alvo.md#nao-existe']


def test_links_em_bloco_codigo_sao_dados_mas_links_renderizados_sao_validados(tmp_path):
    p = tmp_path / 'baseline.md'
    p.write_text('```json\n{"fonte": "[histórico](ausente.md)"}\n```\n'
                 '[navegável](tambem-ausente.md)\n', encoding='utf-8')
    assert links_quebrados(p) == ['tambem-ausente.md']


def test_links_relativos_da_documentacao_e_dos_notebooks():
    arquivos = [RAIZ / "README.md", *(RAIZ / "docs").rglob("*.md"), *(RAIZ / "notebooks").rglob("*.md"),
                *(RAIZ / "outputs").rglob("*.md")]
    erros = {str(p.relative_to(RAIZ)): links_quebrados(p) for p in arquivos}
    assert {k: v for k, v in erros.items() if v} == {}
    quebrados = []
    for caminho in (RAIZ / "notebooks").rglob("*.ipynb"):
        for c in _nb(caminho)["cells"]:
            textos = [_texto(c["source"])] if c["cell_type"] == "markdown" else []
            textos += [_texto(o["data"]["text/markdown"]) for o in c.get("outputs", []) if "text/markdown" in o.get("data", {})]
            for destino in re.findall(r"\]\(([^)\s#]+)", "\n".join(textos)):
                if not re.match(r"^[a-z]+:", destino) and not (caminho.parent / destino).exists():
                    quebrados.append((caminho.name, destino))
    assert quebrados == []


def test_modulo_graficos():
    import plotly.graph_objects as go
    from src.graficos import fmt_br, layout_academico
    assert fmt_br(114694) == "114.694" and fmt_br(-1.7374, 2) == "-1,74"
    fig = layout_academico(go.Figure(), "Título", "Subtítulo", notas=["Nota 1", "Fonte"], nome_arquivo="teste")
    assert fig.layout.separators == ",." and fig.layout.meta == {"nome_arquivo": "teste"}
    assert [a.text for a in fig.layout.annotations] == ["Nota 1", "Fonte"]
