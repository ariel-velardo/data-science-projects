"""Testes de integridade do painel, sobre os artefatos gerados e as fontes salvas.

Requer dashboard/construir.py já executado. Uso, a partir da raiz do projeto:
    python -m pytest dashboard/tests -q
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import construir as construtor  # noqa: E402
from pipeline.fontes import RAIZ_PROJETO, Notebook, inteiro, ler_texto, sha256  # noqa: E402

DIST = BASE / "dist"
HTML = DIST / construtor.NOME_HTML


@pytest.fixture(scope="module")
def dados() -> dict:
    return json.loads((DIST / "dados_painel.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifesto() -> dict:
    return json.loads((DIST / "MANIFESTO_PROVENIENCIA.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def html() -> str:
    return HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def proprio(html: str) -> str:
    """HTML sem a biblioteca Plotly, isto é, somente o conteúdo escrito para o painel."""
    inicio = html.index("<script><!--PLOTLY-->") if "<!--PLOTLY-->" in html else None
    assert inicio is None, "marcador do Plotly não substituído"
    scripts = list(re.finditer(r"<script>(.*?)</script>", html, re.S))
    assert len(scripts) == 2, "esperados o Plotly e o script do painel"
    plotly = scripts[0]
    return html[: plotly.start()] + html[plotly.end():]


def _pares(obj, caminho=""):
    if isinstance(obj, dict):
        for chave, valor in obj.items():
            yield from _pares(valor, f"{caminho}.{chave}")
    elif isinstance(obj, list):
        for indice, valor in enumerate(obj):
            yield from _pares(valor, f"{caminho}[{indice}]")
    else:
        yield caminho, obj


# Valores críticos do pedido
def test_populacao_2024(dados):
    d = dados["destaques"]
    assert (d["n_elegiveis"], d["n_t1"], d["n_t0"]) == (114694, 104576, 10118)
    assert d["n_t1"] + d["n_t0"] == d["n_elegiveis"]
    assert d["n_casos"] == 9850


def test_resultado_principal(dados):
    r = dados["resultados"]
    assert r["dif_ato"] == {"valor": -1.74, "ic": [-2.36, -1.12]}
    assert r["dif_bruta"] == {"valor": -2.0, "ic": [-2.61, -1.37]}
    assert round(r["dif_ato_precisa"], 2) == r["dif_ato"]["valor"]
    assert r["bootstrap"]["replicas"] == r["bootstrap"]["convergidas"] == 1000


def test_sem_ic_anual_nem_na_sensibilidade(dados):
    assert dados["sensibilidade"]["dif"] == -1.63
    assert dados["sensibilidade"]["ic"] is None
    for linha in dados["serie"]:
        assert not [chave for chave in linha if chave.startswith("ic") or "_ic" in chave]


def test_valores_iguais_ao_resumo_redigido(dados):
    resumo = ler_texto("docs/sp_capital_ato/RESUMO_PARA_REDACAO.md")
    for trecho in ("104.576", "10.118", "114.694", "**−1,74 p.p.** (−2,36 a −1,12)", "**−2,00 p.p.** (−2,61 a −1,37)", "**−1,63** (sem IC)"):
        assert trecho in resumo
    for linha in dados["serie"]:
        ano = linha["ano"]
        dif = f"{linha['dif_ato']:.2f}".replace("-", "−").replace(".", ",")
        padrao = rf"\| {ano} \|.*\*\*{dif}\*\* \|"
        assert re.search(padrao, resumo), ano


# Denominadores e reconciliações
def test_funil_reconcilia(dados):
    f = dados["funil"]
    assert f["inicial"] - sum(e["n"] for e in f["etapas"]) == f["elegiveis"] == 114694
    assert [e["restante"] for e in f["etapas"]] == [119761, 116551, 116429, 114694]


def test_recortes_aninhados(dados):
    r = {x["id"]: x for x in dados["recortes"]}
    assert r["sp_capital"]["n_nascimentos"] < r["sp_estado"]["n_nascimentos"] < r["sudeste"]["n_nascimentos"]
    for item in r.values():
        assert item["n_t1"] + item["n_t0"] == item["n_elegiveis"]


def test_serie_coerente(dados):
    serie = dados["serie"]
    assert [l["ano"] for l in serie] == list(range(2014, 2025))
    for linha in serie:
        assert linha["n_t1"] + linha["n_t0"] == linha["n_elegiveis"]
        assert linha["pct_t0"] == pytest.approx(100 * linha["n_t0"] / linha["n_elegiveis"], abs=0.006)
    assert sum(l["n_elegiveis"] for l in serie) == 1587749
    assert sum(l["n_t0"] for l in serie) == 186255
    ultimo = serie[-1]
    assert (ultimo["dif_ato"], ultimo["n_elegiveis"]) == (-1.74, 114694)
    r = dados["resultados"]
    assert (ultimo["risco_ato_t1"], ultimo["risco_ato_t0"]) == (r["t1"]["risco_ato"], r["t0"]["risco_ato"])


def test_serie_coincide_com_qualidade_anual(dados):
    capital = {l["ano"]: l for l in dados["qualidade_anual"]["capital"]}
    for linha in dados["serie"]:
        assert capital[linha["ano"]]["n_elegiveis"] == linha["n_elegiveis"]
        assert capital[linha["ano"]]["n_t0"] == linha["n_t0"]


def test_selecao_reconcilia(dados):
    s = {l["grupo"]: l for l in dados["temporalidade"]["selecao"]}
    assert s["Incluídos em B (1–6)"]["n"] + s["Fora de B"]["n"] == s["Total antes do filtro"]["n"] == 117422
    assert s["Início nos meses 7–9"]["n"] + s["Ausente, ignorada ou outra"]["n"] == s["Fora de B"]["n"]
    a = dados["temporalidade"]["ausentes"]
    assert a["campo_ausente"] + a["codigo_99"] == a["total"] == s["Ausente, ignorada ou outra"]["n"]


def test_faixas_de_duracao_somam_conhecidos(dados):
    faixas = dados["temporalidade"]["por_faixa"]
    assert sum(f["n"] for f in faixas) == 114687
    assert sum(f["n_baixo_peso"] for f in faixas) == 9850


def test_histogramas_percentuais(dados):
    for modelo in ("diagnostico", "final"):
        caixas = dados["escores"][modelo]["caixas"]
        for grupo in ("pct_t1", "pct_t0"):
            assert sum(c[grupo] for c in caixas) == pytest.approx(100, abs=0.2)
        for atual, proximo in zip(caixas, caixas[1:]):
            assert atual["e1"] == pytest.approx(proximo["e0"], abs=1e-3)


def test_todas_as_onze_figuras_origem(dados):
    assert sum(dados["figuras_origem"].values()) == 11


# Divulgação e segurança
def test_sem_contagens_pequenas(dados):
    pequenos = [
        caminho
        for caminho, valor in _pares({k: v for k, v in dados.items() if k != "meta"})
        if isinstance(valor, int) and not isinstance(valor, bool) and 1 <= valor <= 9
        and re.search(r"(^|[._\[])n(_|$|\.)|casos|baixo_peso", caminho)
    ]
    assert pequenos == []


def test_perfil_sem_contagens_por_categoria(dados):
    for niveis in dados["perfil"]["variaveis"].values():
        for nivel in niveis:
            assert not [c for c in nivel if c.startswith("n") and c != "nivel" or c.startswith("_")]


def test_caixas_nao_expoem_contagens(dados):
    for modelo in ("diagnostico", "final"):
        for caixa in dados["escores"][modelo]["caixas"]:
            assert set(caixa) <= {"e0", "e1", "pct_t1", "pct_t0", "peso_t1", "peso_t0"}


def test_smd_sem_precisao_que_recupere_celulas(dados):
    """Com seis casas, o SMD e os percentuais identificam o par exato de contagens de categorias raras."""
    valores = [l["smd"] for l in dados["balanco"]["diagnostico"]]
    for linha in dados["balanco"]["ato"]:
        valores += [linha["smd_antes"], linha["smd_depois"]]
    assert all(round(v, 3) == v for v in valores)


def test_celula_suprimida_nao_recuperavel_por_subtracao(dados):
    s = {l["grupo"]: l for l in dados["temporalidade"]["selecao"]}
    tardio, ausente, fora = s["Início nos meses 7–9"], s["Ausente, ignorada ou outra"], s["Fora de B"]
    assert tardio["lt28"]["n"] == "<10"
    celulas = [tardio["de28a36"], tardio["ge37"], ausente["lt28"], ausente["de28a36"], ausente["ge37"]]
    for celula in celulas:
        assert celula["n"] % 10 == 0 and isinstance(celula["pct"], int) and celula["aprox"] is True

    def faixa(celula: dict, linha: dict) -> list[int]:
        return [
            v for v in range(celula["n"] - 5, celula["n"] + 6)
            if round(100 * v / linha["n"]) == celula["pct"]
        ]

    desconhecidos = fora["n"] - fora["lt28"]["n"] - fora["de28a36"]["n"] - fora["ge37"]["n"]
    possiveis = set()
    for x in range(1, 10):
        a = fora["lt28"]["n"] - x
        if a not in faixa(ausente["lt28"], ausente):
            continue
        for y in faixa(tardio["de28a36"], tardio):
            b = fora["de28a36"]["n"] - y
            if b not in faixa(ausente["de28a36"], ausente):
                continue
            for z in faixa(tardio["ge37"], tardio):
                c = fora["ge37"]["n"] - z
                if c not in faixa(ausente["ge37"], ausente):
                    continue
                u_tardio, u_ausente = tardio["n"] - x - y - z, ausente["n"] - a - b - c
                if u_tardio >= 0 and u_ausente >= 0 and u_tardio + u_ausente == desconhecidos:
                    possiveis.add(x)
    assert len(possiveis) >= 5, sorted(possiveis)


def test_campos_sem_uso_com_risco_de_divulgacao_removidos(dados):
    assert "metodos_ig" not in dados["temporalidade"]
    proibidos = {"peso_fora_t1", "peso_fora_t0", "max_peso_t1", "max_peso_t0"}
    for linha in dados["serie"]:
        assert not proibidos & set(linha)


def test_idades_extremas_nao_alteram_denominadores(dados):
    tabela = Notebook("04").tabela(24, 0, "Idades imputadas")[2:]
    imputadas = {int(l[0]): int(l[6]) for l in tabela}
    assert {a: n for a, n in imputadas.items() if n} == {2017: 1, 2022: 1, 2023: 1}
    populacao = {int(l[0]): inteiro(l[1]) for l in Notebook("04").tabela(17, 0, "Elegíveis")[2:]}
    capital = {l["ano"]: l["n_elegiveis"] for l in dados["qualidade_anual"]["capital"]}
    for linha in dados["serie"]:
        assert linha["n_elegiveis"] == populacao[linha["ano"]] == capital[linha["ano"]]


def test_sem_identificadores_ou_microdados(proprio):
    proibidos = ["CONTADOR", "CODESTAB", "DTNASC", "NUMERODN", "CODMUNNASC", "355030", "60 anos", "61 anos", "62 anos"]
    assert [p for p in proibidos if p in proprio] == []


def test_sem_numero_nacional_aipw(proprio):
    assert "−1,48" not in proprio
    assert "-1.48" not in proprio


def test_sem_linguagem_causal_ou_reducao_relativa(proprio):
    texto = re.sub(r"<script.*?</script>", " ", proprio, flags=re.S)
    assert not re.search(r"(?i)causa redu|reduz o risco|reduziu o risco|efeito do pré-natal|previne", texto)
    assert not re.search(r"\d+\s*% (menor|de redução)", texto)
    assert "associação ajustada" in texto.lower()


# Autossuficiência
def test_sem_chamadas_externas(proprio):
    sem_namespace = proprio.replace("http://www.w3.org/2000/svg", "")
    assert not re.findall(r"(?:https?:)?//[a-z0-9.-]+\.[a-z]{2,}", sem_namespace)
    assert not re.search(r"\b(fetch|XMLHttpRequest|importScripts)\s*\(", sem_namespace)
    assert not re.search(r"<(script|link|img|iframe)[^>]+(src|href)=", sem_namespace)


def test_politica_de_conteudo_bloqueia_rede(html):
    assert "connect-src 'none'" in html
    assert "default-src 'none'" in html


def test_plotly_embutido(html):
    assert "plotly.js v" in html[:1_000_000] or "plotly.js" in html
    assert len(html) > 4_000_000


# Proveniência e reprodutibilidade
def test_manifesto_confere_com_fontes(manifesto):
    assert manifesto["referencia_origem"] == "fd0d319e4b77dfa973b87f1a3c6fc6872968225e"
    assert manifesto["microdados_lidos"] is False
    assert len(manifesto["fontes"]) >= 13
    for fonte in manifesto["fontes"]:
        assert not fonte["caminho"].startswith("data/")
        assert sha256(RAIZ_PROJETO / fonte["caminho"]) == fonte["sha256"]


def test_manifesto_confere_com_saidas(manifesto):
    for nome, esperado in manifesto["saidas"].items():
        assert hashlib.sha256((DIST / nome).read_bytes()).hexdigest() == esperado


def test_construcao_deterministica(tmp_path, manifesto):
    novo = construtor.construir(tmp_path)
    assert novo["saidas"] == manifesto["saidas"]


def test_matriz_cobre_as_abas():
    conteudo = (DIST / "MATRIZ_RASTREABILIDADE.md").read_text(encoding="utf-8")
    for aba in ("B:", "C:", "D:", "E:", "F:", "G:"):
        assert aba in conteudo
