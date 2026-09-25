"""DGPs reproduzíveis para validar infraestrutura de DiD escalonado na D19.

O módulo gera somente dados sintéticos e a verdade causal conhecida por
construção. Ele não contém estimador Callaway–Sant'Anna e não lê a amostra real.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd


ROTULO_FONTE_SINTETICA = "SINTETICO_D19"
ROTULO_VERDADE = "VERDADE_DGP_NAO_ESTIMATIVA"


@dataclass(frozen=True)
class ConfiguracaoDGP:
    """Parâmetros controláveis de um painel com adoção escalonada."""

    n_unidades: int = 240
    anos: tuple[int, ...] = tuple(range(2007, 2020))
    coortes: tuple[int, ...] = (2010, 2012, 2013)
    proporcao_never_treated: float = 0.40
    efeitos_coorte: tuple[float, ...] = (2.0, 4.0, 6.0)
    efeito_dinamico: float = 1.0
    desvio_efeito_individual: float = 0.0
    media_efeito_fixo_individual: float = 50.0
    desvio_efeito_fixo_individual: float = 8.0
    tendencia_comum: float = 1.0
    desvio_ruido: float = 1.0
    antecipacao_periodos: int = 0
    efeito_antecipacao: float = 0.0
    violacao_parallel_trends: float = 0.0
    overlap_fraco: bool = False
    coorte_pequena: int | None = None
    tamanho_coorte_pequena: int = 2
    seed: int = 1901
    nome_cenario: str = "LIMPO"


@dataclass(frozen=True)
class ResultadoDGP:
    painel: pd.DataFrame
    verdade_att_gt: pd.DataFrame
    verdade_event_time: pd.DataFrame
    metadados: dict[str, Any]


def _validar_configuracao(config: ConfiguracaoDGP) -> None:
    if config.n_unidades < len(config.coortes) + 1:
        raise ValueError("n_unidades insuficiente para coortes e never-treated")
    if not 0 < config.proporcao_never_treated < 1:
        raise ValueError("proporcao_never_treated deve estar estritamente entre 0 e 1")
    if len(config.coortes) != len(config.efeitos_coorte):
        raise ValueError("efeitos_coorte deve ter um valor para cada coorte")
    if len(set(config.anos)) != len(config.anos) or tuple(sorted(config.anos)) != config.anos:
        raise ValueError("anos deve ser sequência única e crescente")
    if len(set(config.coortes)) != len(config.coortes):
        raise ValueError("coortes não podem se repetir")
    if not set(config.coortes).issubset(set(config.anos)):
        raise ValueError("todas as coortes devem pertencer ao painel")
    if config.antecipacao_periodos < 0:
        raise ValueError("antecipacao_periodos não pode ser negativo")
    if config.coorte_pequena is not None and config.coorte_pequena not in config.coortes:
        raise ValueError("coorte_pequena deve pertencer a coortes")


def _contagens_coortes(config: ConfiguracaoDGP, n_tratados: int) -> dict[int, int]:
    coortes = list(config.coortes)
    contagens: dict[int, int] = {}
    restante = n_tratados
    coortes_restantes = coortes.copy()
    if config.coorte_pequena is not None:
        if config.tamanho_coorte_pequena < 1 or config.tamanho_coorte_pequena >= n_tratados:
            raise ValueError("tamanho_coorte_pequena incompatível com n_tratados")
        contagens[config.coorte_pequena] = config.tamanho_coorte_pequena
        restante -= config.tamanho_coorte_pequena
        coortes_restantes.remove(config.coorte_pequena)
    if not coortes_restantes:
        if restante:
            raise ValueError("não há coorte para alocar tratados restantes")
        return contagens
    base, sobra = divmod(restante, len(coortes_restantes))
    for indice, coorte in enumerate(coortes_restantes):
        contagens[coorte] = base + int(indice < sobra)
    if any(valor < 1 for valor in contagens.values()):
        raise ValueError("cada coorte deve conter ao menos uma unidade")
    return {coorte: contagens[coorte] for coorte in coortes}


def _logistica(valor: np.ndarray) -> np.ndarray:
    valor_seguro = np.clip(valor, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-valor_seguro))


def simular_painel_did_escalonado(config: ConfiguracaoDGP) -> ResultadoDGP:
    """Gera painel longo, ATT(g,t) verdadeiro e curva verdadeira por event-time."""
    _validar_configuracao(config)
    rng = np.random.default_rng(config.seed)
    n_never = int(round(config.n_unidades * config.proporcao_never_treated))
    n_never = min(max(n_never, 1), config.n_unidades - len(config.coortes))
    n_tratados = config.n_unidades - n_never
    contagens = _contagens_coortes(config, n_tratados)

    grupos = np.concatenate(
        [np.zeros(n_never, dtype=int)]
        + [np.repeat(coorte, contagens[coorte]) for coorte in config.coortes]
    )
    grupos = rng.permutation(grupos)
    ids = np.array([f"S{indice:06d}" for indice in range(1, config.n_unidades + 1)])
    ever_treated = grupos > 0

    if config.overlap_fraco:
        x = np.where(
            ever_treated,
            rng.normal(2.8, 0.35, config.n_unidades),
            rng.normal(0.0, 0.75, config.n_unidades),
        )
        propensity = _logistica(-1.25 + 1.35 * x)
    else:
        x = rng.normal(0.0, 1.0, config.n_unidades)
        propensity = _logistica(-0.25 + 0.30 * x)

    efeito_fixo = (
        config.media_efeito_fixo_individual
        + 2.0 * x
        + rng.normal(0.0, config.desvio_efeito_fixo_individual, config.n_unidades)
    )
    heterogeneidade_individual = rng.normal(
        0.0, config.desvio_efeito_individual, config.n_unidades
    )
    efeito_por_coorte = dict(zip(config.coortes, config.efeitos_coorte, strict=True))
    ano_inicial = min(config.anos)
    linhas: list[dict[str, Any]] = []

    for posicao, identificador in enumerate(ids):
        coorte = int(grupos[posicao])
        for ano in config.anos:
            k = ano - coorte if coorte > 0 else np.nan
            tendencia_especifica = (
                config.violacao_parallel_trends * (ano - ano_inicial) if coorte > 0 else 0.0
            )
            efeito_tempo = config.tendencia_comum * (ano - ano_inicial) + 0.5 * np.sin(
                (ano - ano_inicial) / 2.0
            )
            y0 = efeito_fixo[posicao] + efeito_tempo + tendencia_especifica
            efeito = 0.0
            if coorte > 0 and ano >= coorte:
                efeito = (
                    efeito_por_coorte[coorte]
                    + config.efeito_dinamico * (ano - coorte)
                    + heterogeneidade_individual[posicao]
                )
            elif (
                coorte > 0
                and config.antecipacao_periodos > 0
                and -config.antecipacao_periodos <= k <= -1
            ):
                efeito = config.efeito_antecipacao
            ruido = rng.normal(0.0, config.desvio_ruido)
            linhas.append(
                {
                    "id": identificador,
                    "ano": int(ano),
                    "coorte_g": coorte,
                    "ever_treated": bool(coorte > 0),
                    "tratado_no_periodo": int(coorte > 0 and ano >= coorte),
                    "event_time": k,
                    "x_baseline": float(x[posicao]),
                    "propensity_score_dgp": float(propensity[posicao]),
                    "y0_sem_tratamento": float(y0),
                    "efeito_verdadeiro": float(efeito),
                    "y": float(y0 + efeito + ruido),
                    "fonte_dados": ROTULO_FONTE_SINTETICA,
                    "cenario": config.nome_cenario,
                }
            )

    painel = pd.DataFrame(linhas).sort_values(["id", "ano"]).reset_index(drop=True)
    painel["event_time"] = painel["event_time"].astype("Float64")
    tratados = painel.loc[painel["coorte_g"].gt(0)].copy()
    verdade_att_gt = (
        tratados.loc[tratados["ano"].ge(tratados["coorte_g"])]
        .groupby(["coorte_g", "ano"], as_index=False)
        .agg(
            att_gt_verdadeiro=("efeito_verdadeiro", "mean"),
            n_tratados_coorte=("id", "nunique"),
        )
    )
    verdade_att_gt["event_time"] = verdade_att_gt["ano"] - verdade_att_gt["coorte_g"]
    verdade_att_gt["natureza"] = ROTULO_VERDADE
    verdade_att_gt["cenario"] = config.nome_cenario
    verdade_event_time = (
        tratados.groupby("event_time", as_index=False)
        .agg(
            efeito_verdadeiro=("efeito_verdadeiro", "mean"),
            n_unidades=("id", "nunique"),
        )
        .sort_values("event_time")
        .reset_index(drop=True)
    )
    verdade_event_time["natureza"] = ROTULO_VERDADE
    verdade_event_time["cenario"] = config.nome_cenario
    metadados = {
        "cenario": config.nome_cenario,
        "seed": config.seed,
        "n_unidades": config.n_unidades,
        "n_never_treated": n_never,
        "n_tratados": n_tratados,
        "contagem_coortes": contagens,
        "parallel_trends_verdadeira": config.violacao_parallel_trends == 0.0,
        "overlap_fraco": config.overlap_fraco,
        "anticipation_periodos": config.antecipacao_periodos,
    }
    return ResultadoDGP(painel, verdade_att_gt, verdade_event_time, metadados)


def agregar_verdade_att(
    verdade_att_gt: pd.DataFrame,
    tipo: Literal["grupo", "dinamica", "global"],
) -> pd.DataFrame:
    """Agrega a verdade do DGP; não calcula qualquer estimativa."""
    obrigatorias = {"coorte_g", "ano", "event_time", "att_gt_verdadeiro", "n_tratados_coorte"}
    faltantes = obrigatorias - set(verdade_att_gt.columns)
    if faltantes:
        raise ValueError(f"verdade ATT(g,t) sem colunas: {sorted(faltantes)}")
    trabalho = verdade_att_gt.copy()
    trabalho["ponderado"] = trabalho["att_gt_verdadeiro"] * trabalho["n_tratados_coorte"]
    if tipo == "grupo":
        resultado = trabalho.groupby("coorte_g", as_index=False).agg(
            soma_ponderada=("ponderado", "sum"), peso=("n_tratados_coorte", "sum")
        )
        resultado["att_verdadeiro_agregado"] = resultado["soma_ponderada"] / resultado["peso"]
    elif tipo == "dinamica":
        resultado = trabalho.groupby("event_time", as_index=False).agg(
            soma_ponderada=("ponderado", "sum"), peso=("n_tratados_coorte", "sum")
        )
        resultado["att_verdadeiro_agregado"] = resultado["soma_ponderada"] / resultado["peso"]
    elif tipo == "global":
        resultado = pd.DataFrame(
            {
                "soma_ponderada": [trabalho["ponderado"].sum()],
                "peso": [trabalho["n_tratados_coorte"].sum()],
            }
        )
        resultado["att_verdadeiro_agregado"] = resultado["soma_ponderada"] / resultado["peso"]
    else:
        raise ValueError("tipo deve ser 'grupo', 'dinamica' ou 'global'")
    resultado["tipo_agregacao"] = tipo
    resultado["natureza"] = ROTULO_VERDADE
    return resultado.drop(columns=["soma_ponderada"]).reset_index(drop=True)


def diagnosticar_tendencias_nao_tratadas(painel: pd.DataFrame) -> dict[str, float | bool]:
    """Compara slopes de Y(0) antes da primeira coorte do DGP."""
    primeira_coorte = int(painel.loc[painel["coorte_g"].gt(0), "coorte_g"].min())
    pre = painel.loc[painel["ano"].lt(primeira_coorte)].copy()
    pre["grupo"] = np.where(pre["coorte_g"].gt(0), "TRATADOS", "NEVER_TREATED")

    def slope(grupo: pd.DataFrame) -> float:
        x = grupo["ano"].to_numpy(dtype=float)
        y = grupo["y0_sem_tratamento"].to_numpy(dtype=float)
        return float(np.polyfit(x, y, 1)[0])

    slopes = (
        pre.groupby(["grupo", "id"], as_index=False)
        .apply(lambda frame: pd.Series({"slope": slope(frame)}), include_groups=False)
    )
    medias = slopes.groupby("grupo")["slope"].mean()
    diferenca = float(medias["TRATADOS"] - medias["NEVER_TREATED"])
    return {
        "slope_y0_tratados": float(medias["TRATADOS"]),
        "slope_y0_controles": float(medias["NEVER_TREATED"]),
        "diferenca_slope_pre": diferenca,
        "violacao_detectavel_no_dgp": bool(abs(diferenca) > 0.10),
    }


def diagnosticar_overlap_dgp(painel: pd.DataFrame) -> dict[str, float | int]:
    """Resume suporte dos scores conhecidos do DGP no nível da unidade."""
    unidades = painel.drop_duplicates("id")
    tratados = unidades.loc[unidades["coorte_g"].gt(0), "propensity_score_dgp"]
    controles = unidades.loc[unidades["coorte_g"].eq(0), "propensity_score_dgp"]
    min_c, max_c = float(controles.min()), float(controles.max())
    dentro = tratados.between(min_c, max_c)
    return {
        "score_min_tratados": float(tratados.min()),
        "score_max_tratados": float(tratados.max()),
        "score_min_controles": min_c,
        "score_max_controles": max_c,
        "n_tratados_acima_max_controles": int(tratados.gt(max_c).sum()),
        "n_tratados_abaixo_min_controles": int(tratados.lt(min_c).sum()),
        "fracao_tratados_no_suporte": float(dentro.mean()),
    }


def criar_cenario_limpo(seed: int = 1901, n_unidades: int = 240) -> ResultadoDGP:
    return simular_painel_did_escalonado(
        ConfiguracaoDGP(seed=seed, n_unidades=n_unidades, nome_cenario="LIMPO")
    )


def criar_cenario_heterogeneo(seed: int = 1902, n_unidades: int = 240) -> ResultadoDGP:
    return simular_painel_did_escalonado(
        ConfiguracaoDGP(
            seed=seed,
            n_unidades=n_unidades,
            efeitos_coorte=(1.0, 5.0, 10.0),
            efeito_dinamico=1.75,
            desvio_efeito_individual=0.5,
            nome_cenario="HETEROGENEIDADE_FORTE",
        )
    )


def criar_cenario_violacao_tendencias(seed: int = 1903, n_unidades: int = 240) -> ResultadoDGP:
    return simular_painel_did_escalonado(
        ConfiguracaoDGP(
            seed=seed,
            n_unidades=n_unidades,
            violacao_parallel_trends=0.75,
            nome_cenario="VIOLACAO_PARALLEL_TRENDS",
        )
    )


def criar_cenario_overlap_fraco(seed: int = 1904, n_unidades: int = 240) -> ResultadoDGP:
    return simular_painel_did_escalonado(
        ConfiguracaoDGP(
            seed=seed,
            n_unidades=n_unidades,
            overlap_fraco=True,
            nome_cenario="OVERLAP_FRACO",
        )
    )


def criar_cenario_coorte_pequena(seed: int = 1905, n_unidades: int = 240) -> ResultadoDGP:
    return simular_painel_did_escalonado(
        ConfiguracaoDGP(
            seed=seed,
            n_unidades=n_unidades,
            coorte_pequena=2013,
            tamanho_coorte_pequena=2,
            nome_cenario="COORTE_2013_N2",
        )
    )
