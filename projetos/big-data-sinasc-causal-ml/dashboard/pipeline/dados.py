"""Constrói os agregados do painel a partir das evidências salvas.

Regra de divulgação: contagens de 1 a 9 viram "<10" e histogramas têm caixas agrupadas
até que cada grupo tenha 0 ou pelo menos 10 registros. SMD têm três casas, e as linhas que
permitiriam recuperar uma célula suprimida por subtração são arredondadas. Nenhum microdado é lido.
"""
from __future__ import annotations

import re

from .fontes import (
    CSV_RECORTES,
    CSV_VARIAVEIS,
    RESUMO,
    Notebook,
    contagem_pct,
    inteiro,
    ler_csv,
    ler_texto,
    numero,
)

MASCARA = "<10"
ANOS = list(range(2014, 2025))
LIMIAR_CELULA = 10
BASE_ARREDONDAMENTO = 10
CASAS_SMD = 3
LINHAS_ARREDONDADAS = {"Início nos meses 7–9", "Ausente, ignorada ou outra"}


def mascarar(valor: int) -> int | str:
    return MASCARA if 1 <= valor < LIMIAR_CELULA else int(valor)


def _pct(linha: dict[str, str], campo: str) -> float | None:
    return round(float(linha[campo]), 2) if linha[campo] else None


def _corpo(tabela: list[list[str]], inicio: int) -> list[list[str]]:
    return tabela[inicio:]


def recortes() -> list[dict]:
    tipos = {
        "sudeste": "regiao",
        "sp_estado": "estado",
        "sp_capital": "municipio",
        "mg": "estado",
        "rj": "estado",
        "es": "estado",
    }
    saida = []
    for linha in ler_csv(CSV_RECORTES):
        saida.append(
            {
                "id": linha["recorte_id"],
                "nome": linha["recorte"],
                "tipo": tipos[linha["recorte_id"]],
                "n_nascimentos": int(linha["n_nascimentos"]),
                "n_elegiveis": int(linha["n_elegiveis"]),
                "n_t1": int(linha["n_t1"]),
                "n_t0": int(linha["n_t0"]),
                "pct_essenciais": _pct(linha, "pct_essenciais_validas"),
                "pct_mesprenat": _pct(linha, "pct_mesprenat_valido"),
                "pct_peso": _pct(linha, "pct_peso_valido"),
                "pct_gravidez": _pct(linha, "pct_gravidez_valido"),
                "pct_retencao": _pct(linha, "pct_elegiveis"),
                "pct_t0": _pct(linha, "pct_t0"),
                "excl": {
                    "qualidade": {
                        "n": int(linha["n_excl_qualidade_essenciais"]),
                        "pct": _pct(linha, "pct_excl_qualidade_essenciais"),
                    },
                    "multipla": {
                        "n": int(linha["n_excl_populacao_gestacao_multipla"]),
                        "pct": _pct(linha, "pct_excl_populacao_gestacao_multipla"),
                    },
                    "peso": {
                        "n": int(linha["n_excl_populacao_peso_fora_faixa"]),
                        "pct": _pct(linha, "pct_excl_populacao_peso_fora_faixa"),
                    },
                    "mes79": {
                        "n": int(linha["n_excl_populacao_mes_7_9"]),
                        "pct": _pct(linha, "pct_excl_populacao_mes_7_9"),
                    },
                },
            }
        )
    return saida


def qualidade_variaveis() -> dict:
    nomes = {
        "MESPRENAT": "Mês de início do pré-natal",
        "PESO": "Peso ao nascer",
        "GRAVIDEZ": "Tipo de gravidez",
        "IDADEMAE": "Idade materna",
        "ESCMAE2010": "Escolaridade",
        "RACACORMAE": "Raça/cor",
        "ESTCIVMAE": "Situação conjugal",
        "PARIDADE": "Paridade",
        "QTDFILMORT": "Perdas fetais anteriores",
    }
    linhas = ler_csv(CSV_VARIAVEIS)
    registros = []
    for linha in linhas:
        valida = _pct(linha, "pct_valido")
        registros.append(
            {
                "recorte": linha["recorte_id"],
                "variavel": linha["variavel"],
                "valor": valida if valida is not None else _pct(linha, "pct_preenchido"),
                "medida": "válido" if valida is not None else "preenchido",
                "ausente": _pct(linha, "pct_ausente"),
            }
        )
    return {"nomes": nomes, "ordem": list(nomes), "registros": registros}


def qualidade_anual(nb01: Notebook) -> dict:
    figura = nb01.figura(18, "MESPRENAT válido")
    grupos = nb01.figura(21, "Tamanho dos grupos")
    tabela = _corpo(nb01.tabela(16, 0, "Retenção capital"), 2)
    mesprenat = {}
    for traco in figura:
        mesprenat[traco["name"]] = [
            {
                "ano": int(ano),
                "pct": round(valor, 2),
                "n_validos": int(extra[0]),
                "n_nascimentos": int(extra[1]),
            }
            for ano, valor, extra in zip(traco["x"], traco["y"], traco["customdata"])
        ]
    tamanhos: dict[str, dict[str, list[int]]] = {}
    for indice, traco in enumerate(grupos):
        rotulo = "t1" if indice < 3 else "t0"
        tamanhos.setdefault(traco["name"], {})[rotulo] = [int(v) for v in traco["y"]]
    capital = [
        {
            "ano": int(linha[0]),
            "pct_mes_capital": numero(linha[1]),
            "pct_mes_estado": numero(linha[2]),
            "pct_mes_restante": numero(linha[3]),
            "n_elegiveis": inteiro(linha[4]),
            "n_t1": inteiro(linha[5]),
            "n_t0": inteiro(linha[6]),
            "pct_retencao": numero(linha[7]),
        }
        for linha in tabela
    ]
    acumulado = [
        {
            "recorte": linha[0],
            "n_nascimentos": inteiro(linha[1]),
            "n_elegiveis": inteiro(linha[2]),
            "n_t1": inteiro(linha[3]),
            "n_t0": inteiro(linha[4]),
            "pct_retencao": numero(linha[5]),
            "pct_mes": numero(linha[6]),
            "pct_t0": numero(linha[7]),
        }
        for linha in _corpo(nb01.tabela(16, 1, "Nascimentos"), 2)
    ]
    campos = [
        {
            "indicador": linha[0],
            "min_capital": numero(linha[1]),
            "max_capital": numero(linha[2]),
            "menor_vantagem": numero(linha[3]),
            "maior_vantagem": numero(linha[4]),
            "anos_superior": inteiro(linha[5]),
            "anos_inferior": inteiro(linha[6]),
        }
        for linha in _corpo(nb01.tabela(24, 0, "Mínimo capital"), 2)
    ]
    return {
        "mesprenat": mesprenat,
        "tamanhos": tamanhos,
        "capital": capital,
        "acumulado": acumulado,
        "campos": campos,
    }


def perfil(nb02: Notebook, nb03: Notebook) -> dict:
    tabela = _corpo(nb02.tabela(12, 0, "Diferença T1−T0"), 2)
    variaveis: dict[str, list[dict]] = {}
    idade = None
    for linha in tabela:
        nome, nivel = linha[0], linha[1]
        if nome == "Idade materna (anos)":
            achado1 = re.fullmatch(r"([\d,]+) \(([\d,]+)\)", linha[2])
            achado0 = re.fullmatch(r"([\d,]+) \(([\d,]+)\)", linha[3])
            idade = {
                "media_t1": numero(achado1[1]),
                "dp_t1": numero(achado1[2]),
                "media_t0": numero(achado0[1]),
                "dp_t0": numero(achado0[2]),
                "smd": numero(linha[5]),
            }
            continue
        n1, p1 = contagem_pct(linha[2])
        n0, p0 = contagem_pct(linha[3])
        variaveis.setdefault(nome, []).append(
            {
                "nivel": nivel,
                "pct_t1": p1,
                "pct_t0": p0,
                "_n1": n1,
                "_n0": n0,
                "dif_pp": round(numero(linha[4]), 1),
                "smd": numero(linha[5]),
            }
        )
    n_t1, n_t0 = None, None
    for nome, niveis in variaveis.items():
        soma1 = sum(item["_n1"] for item in niveis)
        soma0 = sum(item["_n0"] for item in niveis)
        n_t1, n_t0 = n_t1 or soma1, n_t0 or soma0
        if (soma1, soma0) != (n_t1, n_t0):
            raise ValueError(f"Níveis de {nome} não somam os totais dos grupos")
        for item in niveis:
            item["pct_total"] = round(100 * (item.pop("_n1") + item.pop("_n0")) / (n_t1 + n_t0), 1)

    ponderado = _corpo(nb03.tabela(20, 0, "Papel no ajuste"), 2)
    populacao = [
        {
            "variavel": linha[0],
            "nivel": linha[1],
            "papel": linha[2],
            "total": numero(linha[3]),
            "t1_bruto": numero(linha[4]),
            "t0_bruto": numero(linha[5]),
            "t1_ato": numero(linha[6]),
            "t0_ato": numero(linha[7]),
            "unidade": "anos" if linha[1] == "média" else "%",
        }
        for linha in ponderado
    ]
    return {
        "variaveis": variaveis,
        "ordem_variaveis": list(variaveis),
        "idade": idade,
        "populacao_alvo": populacao,
    }


def balanco(nb02: Notebook, nb03: Notebook) -> dict:
    figura = nb03.figura(18, "Balanço das covariáveis antes e depois")
    antes = figura[1]
    linhas = []
    for rotulo, extra in zip(antes["y"], antes["customdata"]):
        variavel, _, nivel = rotulo.partition(" — ")
        linhas.append(
            {
                "rotulo": rotulo,
                "variavel": variavel,
                "nivel": nivel,
                "papel": extra[0],
                "t1_bruto": extra[1],
                "t0_bruto": extra[2],
                "t1_ato": extra[3],
                "t0_ato": extra[4],
                "smd_antes": round(extra[5], 6),
                "smd_depois": round(extra[6], 6),
            }
        )

    love = nb02.figura(15, "Balanço das covariáveis maternas")
    diagnostico = []
    for traco in love:
        for rotulo, extra in zip(traco["y"], traco["customdata"]):
            diagnostico.append({"rotulo": rotulo, "smd": round(extra[0], CASAS_SMD) + 0.0})

    resumo = [
        {"variavel": linha[0], "smd_max": numero(linha[1]), "nivel": linha[2]}
        for linha in _corpo(nb02.tabela(13, 0, "|SMD| máximo"), 2)
    ]
    return {"ato": linhas, "diagnostico": diagnostico, "resumo": resumo}


def _agrupar_caixas(caixas: list[dict]) -> list[dict]:
    """Une caixas adjacentes até cada grupo ter 0 ou pelo menos 10 registros."""

    def aceitavel(caixa: dict) -> bool:
        return all(caixa[g] == 0 or caixa[g] >= LIMIAR_CELULA for g in ("n1", "n0"))

    def somar(a: dict, b: dict) -> dict:
        resultado = {"e0": a["e0"], "e1": b["e1"]}
        for chave in a:
            if chave not in resultado:
                resultado[chave] = a[chave] + b[chave]
        return resultado

    saida: list[dict] = []
    acumulado = None
    for caixa in caixas:
        acumulado = somar(acumulado, caixa) if acumulado else dict(caixa)
        if aceitavel(acumulado):
            saida.append(acumulado)
            acumulado = None
    while acumulado is not None:
        if not saida:
            raise ValueError("Histograma sem caixas divulgáveis")
        combinado = somar(saida.pop(), acumulado)
        if aceitavel(combinado):
            saida.append(combinado)
            acumulado = None
        else:
            acumulado = combinado
    return saida


def _publicar_caixas(caixas: list[dict]) -> list[dict]:
    publicadas = []
    for caixa in caixas:
        item = {"e0": round(caixa["e0"], 4), "e1": round(caixa["e1"], 4)}
        for chave, valor in caixa.items():
            if chave.startswith("pct") or chave.startswith("peso"):
                item[chave] = round(valor, 2)
        publicadas.append(item)
    return publicadas


def escores(nb02: Notebook, nb03: Notebook, n_t1: int, n_t0: int) -> dict:
    diag = nb02.figura(22, "Escore de propensão estimado")
    t1, t0 = diag[0], diag[1]
    caixas = []
    largura = t1["x"][1] - t1["x"][0]
    for i, centro in enumerate(t1["x"]):
        caixas.append(
            {
                "e0": centro - largura / 2,
                "e1": centro + largura / 2,
                "pct_t1": t1["customdata"][i][0],
                "pct_t0": t0["customdata"][i][0],
                "n1": int(t1["customdata"][i][1]),
                "n0": int(t0["customdata"][i][1]),
            }
        )
    diagnostico = _agrupar_caixas(caixas)

    final = nb03.figura(15, "Escore de propensão e pesos")
    caixas = []
    largura = final[0]["x"][1] - final[0]["x"][0]
    for i, centro in enumerate(final[0]["x"]):
        extra1, extra0 = final[0]["customdata"][i], final[2]["customdata"][i]
        caixas.append(
            {
                "e0": centro - largura / 2,
                "e1": centro + largura / 2,
                "pct_t1": extra1[1],
                "pct_t0": extra0[1],
                "peso_t1": extra1[3],
                "peso_t0": extra0[3],
                "n1": int(extra1[2]),
                "n0": int(extra0[2]),
            }
        )
    ato = _agrupar_caixas(caixas)

    for nome, conjunto in {"diagnostico": diagnostico, "final": ato}.items():
        cobertura = {g: sum(c[g] for c in conjunto) for g in ("n1", "n0")}
        if cobertura["n1"] > n_t1 or cobertura["n0"] > n_t0:
            raise ValueError(f"Histograma {nome} excede os totais dos grupos")

    def sem_cauda_vazia(conjunto: list[dict]) -> list[dict]:
        while conjunto and conjunto[-1]["n1"] == 0 and conjunto[-1]["n0"] == 0:
            conjunto = conjunto[:-1]
        return conjunto

    diagnostico, ato = sem_cauda_vazia(diagnostico), sem_cauda_vazia(ato)

    def percentis(tabela: list[list[str]]) -> list[dict]:
        return [{"item": l[0], "t1": numero(l[1]), "t0": numero(l[2])} for l in tabela]

    regioes = []
    for linha in _corpo(nb02.tabela(20, 3, "T=1 n (%)"), 2):
        n1, p1 = _contagem_pct_duas(linha[1])
        n0, p0 = _contagem_pct_duas(linha[2])
        regioes.append(
            {"regiao": linha[0], "n_t1": mascarar(n1), "pct_t1": p1, "n_t0": mascarar(n0), "pct_t0": p0}
        )
    return {
        "diagnostico": {
            "caixas": _publicar_caixas(diagnostico),
            "percentis": percentis(_corpo(nb02.tabela(20, 1, "T=1 (meses 1–3)"), 1)),
            "fora_eixo_t1": mascarar(n_t1 - sum(c["n1"] for c in diagnostico)),
            "fora_eixo_t0": mascarar(n_t0 - sum(c["n0"] for c in diagnostico)),
        },
        "final": {
            "caixas": _publicar_caixas(ato),
            "percentis": percentis(_corpo(nb03.tabela(11, 0, "T=1 (meses 1–3)"), 1)),
            "fora_eixo_t1": mascarar(n_t1 - sum(c["n1"] for c in ato)),
            "fora_eixo_t0": mascarar(n_t0 - sum(c["n0"] for c in ato)),
        },
        "regioes": regioes,
    }


def _contagem_pct_duas(texto: str) -> tuple[int, float]:
    achado = re.fullmatch(r"\s*([\d.]+)\s*\(([\d,]+)%\)\s*", texto)
    if not achado:
        raise ValueError(f"Célula n (%) inválida: {texto!r}")
    return inteiro(achado[1]), float(achado[2].replace(",", "."))


def pesos(nb03: Notebook) -> list[dict]:
    return [
        {"item": linha[0], "t1": numero(linha[1]), "t0": numero(linha[2])}
        for linha in _corpo(nb03.tabela(13, 0, "T=1 (peso 1−e)"), 1)
    ]


def resultados(nb03: Notebook) -> dict:
    tabela = _corpo(nb03.tabela(22, 1, "Risco bruto (%)"), 1)
    t1, t0, dif = tabela

    def ic(texto: str) -> list[float]:
        a, b = texto.split(" a ")
        return [numero(a), numero(b)]

    grupo = lambda linha: {  # noqa: E731
        "n": inteiro(linha[1]),
        "casos": inteiro(linha[2]),
        "risco_bruto": numero(linha[3]),
        "ic_bruto": ic(linha[4]),
        "risco_ato": numero(linha[5]),
        "ic_ato": ic(linha[6]),
    }
    figura = nb03.figura(23, "Risco de baixo peso ao nascer")
    fluxo = nb03.fluxo(22)
    achado = re.search(
        r"EP bootstrap ([\d,]+) p\.p\.; IC normal ([−-][\d,]+) a ([−-][\d,]+) p\.p\.", fluxo
    )
    media = re.search(r"Média das réplicas ([−-][\d,]+) p\.p\.", fluxo)
    replicas = re.search(r"réplicas com convergência: (\d+)/(\d+)", fluxo)
    return {
        "t1": grupo(t1),
        "t0": grupo(t0),
        "dif_bruta": {"valor": numero(dif[3]), "ic": ic(dif[4])},
        "dif_ato": {"valor": numero(dif[5]), "ic": ic(dif[6])},
        "dif_ato_precisa": round(figura[3]["x"][0], 4),
        "dif_bruta_precisa": round(figura[2]["x"][0], 4),
        "bootstrap": {
            "ep": numero(achado[1]),
            "ic_normal": [numero(achado[2]), numero(achado[3])],
            "media_replicas": numero(media[1]),
            "convergidas": int(replicas[1]),
            "replicas": int(replicas[2]),
            "semente": 20240925,
        },
    }


def sensibilidade(nb03: Notebook) -> dict:
    tabela = _corpo(nb03.tabela(31, 0, "Sensibilidade com situação conjugal"), 1)
    linhas = [{"item": l[0], "principal": numero(l[1]), "sensibilidade": numero(l[2])} for l in tabela]
    perfil_sens = [
        {"item": l[0], "p_t1": l[1], "p_t0": l[2], "s_t1": l[3], "s_t0": l[4]}
        for l in _corpo(nb03.tabela(33, 0, "Principal T=1"), 2)
    ]
    return {
        "linhas": linhas,
        "perfil": perfil_sens,
        "dif": linhas[0]["sensibilidade"],
        "ic": None,
    }


def serie(nb04: Notebook) -> list[dict]:
    pop = {l[0]: l for l in _corpo(nb04.tabela(17, 0, "Elegíveis"), 2)}
    ato = {l[0]: l for l in _corpo(nb04.tabela(19, 0, "Risco ATO T=1"), 2)}
    smd = {l[0]: l for l in _corpo(nb04.tabela(21, 0, "Máx. |SMD| antes"), 2)}
    sup = {l[0]: l for l in _corpo(nb04.tabela(23, 0, "Suporte mín."), 2)}
    conc = {l[0]: l for l in _corpo(nb04.tabela(24, 0, "Média e(X)"), 2)}
    linhas = []
    for ano in map(str, ANOS):
        p, a, s, u, c = pop[ano], ato[ano], smd[ano], sup[ano], conc[ano]
        linhas.append(
            {
                "ano": int(ano),
                "n_elegiveis": inteiro(p[1]),
                "n_t1": inteiro(p[2]),
                "n_t0": inteiro(p[3]),
                "pct_t0": numero(p[4]),
                "risco_bruto_t1": numero(p[5]),
                "risco_bruto_t0": numero(p[6]),
                "dif_bruta": numero(p[7]),
                "risco_ato_t1": numero(a[1]),
                "risco_ato_t0": numero(a[2]),
                "dif_ato": numero(a[3]),
                "ess_t1": inteiro(a[4]),
                "ess_t0": inteiro(a[5]),
                "ess_pct_t1": numero(a[6]),
                "ess_pct_t0": numero(a[7]),
                "smd_antes": numero(s[1]),
                "smd_depois": numero(s[2]),
                "smd_conjugal": numero(s[4]),
                "smd_adolescente": numero(s[5]),
                "suporte_min": numero(u[1]),
                "suporte_max": numero(u[2]),
                "n_fora_t1": mascarar(inteiro(u[3])),
                "n_fora_t0": mascarar(inteiro(u[4])),
                "media_escore": numero(c[1]),
                "iteracoes": inteiro(c[5]),
            }
        )
    return linhas


FAIXAS_AGRUPADAS = [
    ("< 28", ["< 22", "22–27"]),
    ("28–31", ["28–31"]),
    ("32–36", ["32–36"]),
    ("≥ 37", ["37–41", "42 ou mais"]),
]


def temporalidade(nb05: Notebook) -> dict:
    cruzada = {l[0]: l for l in _corpo(nb05.tabela(11, 1, "T=1 (1–3)"), 2)}
    baixo_peso = {l[0]: l for l in _corpo(nb05.tabela(18, 0, "Casos de baixo peso"), 2)}
    meses = ["Mês 1", "Mês 2", "Mês 3", "Mês 4", "Mês 5", "Mês 6"]

    por_faixa = []
    for rotulo, originais in FAIXAS_AGRUPADAS:
        contagens = [sum(inteiro(cruzada[o][i]) for o in originais) for i in range(1, 7)]
        if min(contagens) < LIMIAR_CELULA:
            raise ValueError(f"Faixa {rotulo} ainda contém célula pequena: {contagens}")
        n_faixa = sum(inteiro(cruzada[o][9]) for o in originais)
        casos = sum(inteiro(baixo_peso[o][2]) for o in originais)
        por_faixa.append(
            {
                "faixa": rotulo,
                "n": n_faixa,
                "pct_meses": [round(100 * c / n_faixa, 2) for c in contagens],
                "pct_t0": round(100 * sum(contagens[3:]) / n_faixa, 2),
                "n_baixo_peso": casos,
                "pct_baixo_peso": round(100 * casos / n_faixa, 2),
            }
        )

    figura = nb05.figura(20, "Baixo peso por mês de início")
    preterm, termo = figura[0], figura[1]
    por_mes = []
    for i, mes in enumerate(meses):
        casos_pre, casos_termo = int(preterm["customdata"][i][4]), int(termo["customdata"][i][4])
        if min(casos_pre, casos_termo) < LIMIAR_CELULA:
            raise ValueError(f"{mes}: célula pequena no baixo peso")
        por_mes.append(
            {
                "mes": mes,
                "n": int(preterm["customdata"][i][1]),
                "pct_preterm": round(preterm["y"][i], 2),
                "pct_termo": round(termo["y"][i], 2),
                "pct_total": round(preterm["y"][i] + termo["y"][i], 2),
            }
        )

    totais_mes = cruzada["Total"][1:7]
    n_total = inteiro(cruzada["Total"][9])
    distribuicao = [
        {"mes": mes, "pct": round(100 * inteiro(valor) / n_total, 2)}
        for mes, valor in zip(meses, totais_mes)
    ]

    def celula(texto: str, arredondar: bool) -> dict:
        n, p = _contagem_pct_duas(texto)
        if 1 <= n < LIMIAR_CELULA:
            return {"n": MASCARA, "pct": "<1"}
        if arredondar:
            return {"n": BASE_ARREDONDAMENTO * round(n / BASE_ARREDONDAMENTO), "pct": round(p), "aprox": True}
        return {"n": n, "pct": p}

    selecao = []
    for linha in _corpo(nb05.tabela(28, 0, "Início do pré-natal"), 2):
        arredondar = linha[0] in LINHAS_ARREDONDADAS
        selecao.append(
            {
                "grupo": linha[0],
                "n": inteiro(linha[1]),
                "pct_total": numero(linha[2]),
                "lt28": celula(linha[8], arredondar),
                "de28a36": celula(linha[5], arredondar),
                "ge37": celula(linha[6], arredondar),
            }
        )

    resumo = ler_texto(RESUMO)
    ausentes = re.search(
        r"Os ([\d.]+) registros sem início informado incluem ([\d.]+) com campo ausente "
        r"e ([\d.]+) com código 99",
        resumo,
    )
    return {
        "por_faixa": por_faixa,
        "por_mes": por_mes,
        "distribuicao_meses": distribuicao,
        "selecao": selecao,
        "ausentes": {
            "total": inteiro(ausentes[1]),
            "campo_ausente": inteiro(ausentes[2]),
            "codigo_99": inteiro(ausentes[3]),
        },
    }


def construir() -> dict:
    nb01, nb02, nb03, nb04, nb05 = (Notebook(c) for c in ("01", "02", "03", "04", "05"))
    lista_recortes = recortes()
    capital = next(r for r in lista_recortes if r["id"] == "sp_capital")
    res = resultados(nb03)
    figuras_por_nb = {nb.chave: nb.total_figuras() for nb in (nb01, nb02, nb03, nb04, nb05)}
    dados = {
        "figuras_origem": figuras_por_nb,
        "recortes": lista_recortes,
        "qualidade_variaveis": qualidade_variaveis(),
        "qualidade_anual": qualidade_anual(nb01),
        "perfil": perfil(nb02, nb03),
        "balanco": balanco(nb02, nb03),
        "escores": escores(nb02, nb03, res["t1"]["n"], res["t0"]["n"]),
        "pesos": pesos(nb03),
        "resultados": res,
        "sensibilidade": sensibilidade(nb03),
        "serie": serie(nb04),
        "temporalidade": temporalidade(nb05),
    }
    dados["funil"] = {
        "inicial": capital["n_nascimentos"],
        "etapas": [
            {"chave": "qualidade", "rotulo": "Variáveis essenciais inválidas"},
            {"chave": "multipla", "rotulo": "Gestação múltipla"},
            {"chave": "peso", "rotulo": "Peso fora de 500–6.000 g"},
            {"chave": "mes79", "rotulo": "Início nos meses 7–9"},
        ],
        "elegiveis": capital["n_elegiveis"],
    }
    restante = dados["funil"]["inicial"]
    for etapa in dados["funil"]["etapas"]:
        restante -= capital["excl"][etapa["chave"]]["n"]
        etapa["n"] = capital["excl"][etapa["chave"]]["n"]
        etapa["pct"] = capital["excl"][etapa["chave"]]["pct"]
        etapa["restante"] = restante
    if restante != dados["funil"]["elegiveis"]:
        raise ValueError("Funil não reconcilia com os elegíveis")
    casada = next(
        linha for linha in dados["balanco"]["ato"]
        if linha["variavel"].startswith("Situação") and linha["nivel"] == "Casada"
    )
    ajustadas = [
        abs(linha["smd_depois"]) for linha in dados["balanco"]["ato"]
        if linha["papel"] == "Covariável ajustada no escore"
    ]
    dados["resultados"]["dif_ato_abs"] = abs(res["dif_ato"]["valor"])
    dados["destaques"] = {
        "n_elegiveis": capital["n_elegiveis"],
        "n_t1": capital["n_t1"],
        "n_t0": capital["n_t0"],
        "n_casos": res["t1"]["casos"] + res["t0"]["casos"],
        "pct_t1": round(100 - capital["pct_t0"], 2),
        "pct_t0": capital["pct_t0"],
        "smd_max_ato": round(max(ajustadas), 4),
        "smd_casada_antes": round(casada["smd_antes"], 3),
        "smd_casada_depois": round(casada["smd_depois"], 3),
        "sens_mudanca": round(abs(res["dif_ato"]["valor"] - dados["sensibilidade"]["dif"]), 2),
    }
    for linha in dados["balanco"]["ato"]:
        linha["smd_antes"] = round(linha["smd_antes"], CASAS_SMD) + 0.0
        linha["smd_depois"] = round(linha["smd_depois"], CASAS_SMD) + 0.0
    dados["serie_nota_imputacao"] = (
        "Em menos de 10 registros da série, a idade fora de 10–59 anos recebeu a imputação "
        "prevista no pipeline; nenhum registro foi excluído."
    )
    return dados
