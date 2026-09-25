"""D20C–D20E: estimação causal real, robustezes e auditoria pós-estimação.

Este módulo é deliberadamente separado da infraestrutura sintética D19/D20A.
Ele aceita apenas a view real congelada D20B, valida seus hashes e contrato,
executa ``differences==0.3.0`` com a configuração pré-especificada e preserva
o resultado principal antes de qualquer sensibilidade.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import time
import warnings
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from differences import ATTgt

from visualizacao_ipt import CORES_IPT, aplicar_tema_ipt


ROOT = Path(__file__).resolve().parents[1]
PAPEL_TRATADO = "TRATADO_PRINCIPAL"
PAPEL_CONTROLE = "CONTROLE_NEVER_TREATED"
OUTCOME_PRIMARIO = "pessoal_ocupado_assalariado"
HASH_D15_ESPERADO = "7c24c01b569ed6d10f773d00599b5010e1607696f46d716827182a078e4d733b"
HASH_VIEW_D20B_ESPERADO = "91b0a14b38740a56c1b6b3912e1ad3252632037b9044c992ec5331a932a10969"
VERSAO_DIFERENCES = "0.3.0"
TOLERANCIA_REPRODUTIBILIDADE = 1e-10
COORTES_PRINCIPAIS = (2009, 2010, 2011, 2012, 2013)
ORDEM_ESPECIFICACOES = (
    "principal",
    "log1p",
    "janela_3pre",
    "suporte",
    "spillover_25km",
    "spillover_50km",
    "spillover_100km",
    "arranjo_populacional",
)


@dataclass(frozen=True)
class ConfiguracaoEstimacao:
    backend: str = "differences==0.3.0"
    outcome: str = OUTCOME_PRIMARIO
    base_period: str = "universal"
    control_group: str = "never_treated"
    est_method: str = "dr"
    anticipation: int = 0
    as_repeated_cross_section: bool = False
    boot_iterations: int = 1999
    random_state: int = 20260924
    n_jobs: int = 1
    alpha: float = 0.05
    k_referencia: int = -1
    janela_principal: tuple[int, ...] = (-2, -1, 0, 1, 2)


CONFIGURACAO_PRINCIPAL = ConfiguracaoEstimacao()


ROTULOS = {
    "principal": "ESTIMATIVA_PRINCIPAL",
    "log1p": "ROBUSTEZ_LOG1P",
    "janela_3pre": "ROBUSTEZ_JANELA_3PRE",
    "suporte": "SENSIBILIDADE_DE_SUPORTE__NAO_AMOSTRA_PRINCIPAL",
    "spillover_25km": "SENSIBILIDADE_SPILLOVER_25KM",
    "spillover_50km": "SENSIBILIDADE_SPILLOVER_50KM",
    "spillover_100km": "SENSIBILIDADE_SPILLOVER_100KM",
    "arranjo_populacional": "SENSIBILIDADE_ARRANJO_POPULACIONAL",
}


def sha256_arquivo(caminho: str | Path) -> str:
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def _codigo_7(series: pd.Series) -> pd.Series:
    return series.astype("string").str.zfill(7)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _json_seguro(valor: Any) -> Any:
    if isinstance(valor, (np.integer,)):
        return int(valor)
    if isinstance(valor, (np.floating,)):
        return None if not np.isfinite(valor) else float(valor)
    if isinstance(valor, (np.bool_,)):
        return bool(valor)
    if isinstance(valor, Path):
        return str(valor)
    raise TypeError(f"tipo não serializável: {type(valor)!r}")


def _escrever_json(caminho: Path, conteudo: dict[str, Any]) -> None:
    caminho.write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=2, default=_json_seguro),
        encoding="utf-8",
    )


def _exigir_backend() -> None:
    versao = importlib.metadata.version("differences")
    if versao != VERSAO_DIFERENCES:
        raise RuntimeError(
            f"backend divergente: differences=={versao}; esperado {VERSAO_DIFERENCES}"
        )


def carregar_validar_view_principal(
    caminho: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Carrega a view D20B e bloqueia qualquer divergência do freeze."""
    caminho = Path(caminho)
    if sha256_arquivo(caminho) != HASH_VIEW_D20B_ESPERADO:
        raise AssertionError("hash da view D20B diverge do congelado")
    dados = pd.read_parquet(caminho)
    dados = dados.copy(deep=True)
    dados["codigo_municipio_ibge"] = _codigo_7(dados["codigo_municipio_ibge"])
    obrigatorias = {
        "codigo_municipio_ibge",
        "ano",
        "papel_causal",
        "coorte_g",
        OUTCOME_PRIMARIO,
        "elegivel_estimacao_principal",
    }
    faltantes = obrigatorias - set(dados.columns)
    if faltantes:
        raise ValueError(f"view D20B sem colunas obrigatórias: {sorted(faltantes)}")
    unidades = dados.sort_values("ano").drop_duplicates("codigo_municipio_ibge")
    tratados = unidades.loc[unidades["papel_causal"].eq(PAPEL_TRATADO)]
    controles = unidades.loc[unidades["papel_causal"].eq(PAPEL_CONTROLE)]
    coortes = {
        int(k): int(v)
        for k, v in tratados.groupby("coorte_g").size().sort_index().items()
    }
    auditoria = {
        "n_linhas": int(len(dados)),
        "n_municipios": int(dados["codigo_municipio_ibge"].nunique()),
        "n_tratados": int(len(tratados)),
        "n_controles": int(len(controles)),
        "anos": [int(x) for x in sorted(dados["ano"].unique())],
        "painel_balanceado": bool(
            dados.groupby("codigo_municipio_ibge")["ano"].nunique().eq(13).all()
        ),
        "chave_unica": bool(
            not dados.duplicated(["codigo_municipio_ibge", "ano"]).any()
        ),
        "outcome_nulos": int(dados[OUTCOME_PRIMARIO].isna().sum()),
        "coortes": coortes,
        "cabo_frio_ausente": bool(
            not dados["codigo_municipio_ibge"].eq("3300704").any()
        ),
        "codigo_5003900_ausente": bool(
            not dados["codigo_municipio_ibge"].eq("5003900").any()
        ),
        "todas_linhas_elegiveis": bool(
            dados["elegivel_estimacao_principal"].astype(bool).all()
        ),
    }
    esperado = {
        "n_linhas": 66183,
        "n_municipios": 5091,
        "n_tratados": 128,
        "n_controles": 4963,
        "anos": list(range(2007, 2020)),
        "painel_balanceado": True,
        "chave_unica": True,
        "outcome_nulos": 0,
        "coortes": {2009: 21, 2010: 26, 2011: 66, 2012: 13, 2013: 2},
        "cabo_frio_ausente": True,
        "codigo_5003900_ausente": True,
        "todas_linhas_elegiveis": True,
    }
    divergencias = {
        k: (auditoria[k], v) for k, v in esperado.items() if auditoria[k] != v
    }
    if divergencias:
        raise AssertionError(f"view D20B diverge do contrato: {divergencias}")
    return dados, auditoria


def _validar_painel_derivado(dados: pd.DataFrame) -> None:
    if dados.empty:
        raise ValueError("população derivada vazia")
    if dados.duplicated(["codigo_municipio_ibge", "ano"]).any():
        raise ValueError("população derivada com chave duplicada")
    if set(dados["ano"].astype(int).unique()) != set(range(2007, 2020)):
        raise ValueError("população derivada alterou o calendário 2007-2019")
    if not dados.groupby("codigo_municipio_ibge")["ano"].nunique().eq(13).all():
        raise ValueError("população derivada não é painel balanceado")
    if dados["outcome_modelo"].isna().any():
        raise ValueError("outcome_modelo contém nulos")


def construir_populacao_especificacao(
    view: pd.DataFrame,
    especificacao: str,
    *,
    overlap: pd.DataFrame,
    distancias: pd.DataFrame,
    arranjos: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Aplica somente filtros pré-especificados e preserva o painel integral."""
    if especificacao not in ORDEM_ESPECIFICACOES:
        raise ValueError(f"especificação desconhecida: {especificacao}")
    dados = view.copy(deep=True)
    dados["codigo_municipio_ibge"] = _codigo_7(dados["codigo_municipio_ibge"])
    codigos_excluidos: list[str] = []
    escala = "nivel"

    if especificacao == "janela_3pre":
        remover = dados.loc[
            dados["papel_causal"].eq(PAPEL_TRATADO) & dados["coorte_g"].eq(2009),
            "codigo_municipio_ibge",
        ].unique()
        codigos_excluidos = sorted(map(str, remover))
        dados = dados.loc[~dados["codigo_municipio_ibge"].isin(remover)].copy()
    elif especificacao == "suporte":
        overlap = overlap.copy()
        overlap["codigo_municipio_ibge"] = _codigo_7(overlap["codigo_municipio_ibge"])
        extremos = overlap.loc[
            overlap["status_suporte_att"].eq("TRATADO_ACIMA_MAX_CONTROLES")
            & overlap["tratado"].astype(bool),
            "codigo_municipio_ibge",
        ].drop_duplicates()
        if len(extremos) != 5:
            raise AssertionError(f"D18 deveria identificar cinco tratados extremos; recebeu {len(extremos)}")
        codigos_excluidos = sorted(extremos.tolist())
        dados = dados.loc[~dados["codigo_municipio_ibge"].isin(extremos)].copy()
    elif especificacao.startswith("spillover_"):
        coluna = {
            "spillover_25km": "fl_ate_25_km",
            "spillover_50km": "fl_ate_50_km",
            "spillover_100km": "fl_ate_100_km",
        }[especificacao]
        diag = distancias.copy()
        diag["codigo_municipio_ibge"] = _codigo_7(diag["codigo_municipio_ibge"])
        excluir = set(diag.loc[diag[coluna].astype(bool), "codigo_municipio_ibge"])
        codigos_excluidos = sorted(
            set(dados.loc[dados["papel_causal"].eq(PAPEL_CONTROLE), "codigo_municipio_ibge"])
            & excluir
        )
        mask = dados["papel_causal"].eq(PAPEL_CONTROLE) & dados[
            "codigo_municipio_ibge"
        ].isin(codigos_excluidos)
        dados = dados.loc[~mask].copy()
    elif especificacao == "arranjo_populacional":
        diag = arranjos.copy()
        diag["codigo_municipio_ibge"] = _codigo_7(diag["codigo_municipio_ibge"])
        excluir = set(
            diag.loc[
                diag["fl_mesmo_arranjo_populacional_fase_ii"].astype(bool),
                "codigo_municipio_ibge",
            ]
        )
        codigos_excluidos = sorted(
            set(dados.loc[dados["papel_causal"].eq(PAPEL_CONTROLE), "codigo_municipio_ibge"])
            & excluir
        )
        mask = dados["papel_causal"].eq(PAPEL_CONTROLE) & dados[
            "codigo_municipio_ibge"
        ].isin(codigos_excluidos)
        dados = dados.loc[~mask].copy()

    if especificacao == "log1p":
        escala = "log1p"
        dados["outcome_modelo"] = np.log1p(
            pd.to_numeric(dados[OUTCOME_PRIMARIO], errors="raise")
        )
    else:
        dados["outcome_modelo"] = pd.to_numeric(
            dados[OUTCOME_PRIMARIO], errors="raise"
        )

    dados = dados.sort_values(["codigo_municipio_ibge", "ano"]).reset_index(drop=True)
    _validar_painel_derivado(dados)
    unidades = dados.drop_duplicates("codigo_municipio_ibge")
    tratados = unidades.loc[unidades["papel_causal"].eq(PAPEL_TRATADO)]
    controles = unidades.loc[unidades["papel_causal"].eq(PAPEL_CONTROLE)]
    coortes = {
        int(k): int(v)
        for k, v in tratados.groupby("coorte_g").size().sort_index().items()
    }
    auditoria = {
        "especificacao": especificacao,
        "rotulo": ROTULOS[especificacao],
        "n_linhas": int(len(dados)),
        "n_municipios": int(dados["codigo_municipio_ibge"].nunique()),
        "n_tratados": int(len(tratados)),
        "n_controles": int(len(controles)),
        "coortes": coortes,
        "anos": [int(x) for x in sorted(dados["ano"].unique())],
        "escala_outcome": escala,
        "codigos_excluidos": codigos_excluidos,
        "tratados_preservados_spillover": bool(
            especificacao not in {
                "spillover_25km", "spillover_50km", "spillover_100km",
                "arranjo_populacional",
            }
            or len(tratados) == 128
        ),
    }
    esperados = {
        "principal": (128, 4963),
        "log1p": (128, 4963),
        "janela_3pre": (107, 4963),
        "suporte": (123, 4963),
        "spillover_25km": (128, 4589),
        "spillover_50km": (128, 3488),
        "spillover_100km": (128, 1323),
        "arranjo_populacional": (128, 4818),
    }
    observado = (auditoria["n_tratados"], auditoria["n_controles"])
    if observado != esperados[especificacao]:
        raise AssertionError(
            f"população {especificacao} divergente: {observado}; esperado {esperados[especificacao]}"
        )
    return dados, auditoria


def preparar_dados_api(
    dados: pd.DataFrame, *, outcome_modelo: str = "nivel"
) -> pd.DataFrame:
    """Converte um painel real já validado para a API ``ATTgt``."""
    trabalho = dados.copy(deep=True)
    trabalho["codigo_municipio_ibge"] = _codigo_7(
        trabalho["codigo_municipio_ibge"]
    )
    if "outcome_modelo" not in trabalho:
        if outcome_modelo == "log1p":
            trabalho["outcome_modelo"] = np.log1p(
                pd.to_numeric(trabalho[OUTCOME_PRIMARIO], errors="raise")
            )
        elif outcome_modelo == "nivel":
            trabalho["outcome_modelo"] = pd.to_numeric(
                trabalho[OUTCOME_PRIMARIO], errors="raise"
            )
        else:
            raise ValueError(f"escala de outcome desconhecida: {outcome_modelo}")
    trabalho["coorte_api"] = pd.to_numeric(
        trabalho["coorte_g"], errors="coerce"
    ).astype(float)
    trabalho.loc[trabalho["papel_causal"].eq(PAPEL_CONTROLE), "coorte_api"] = np.nan
    return trabalho.set_index(["codigo_municipio_ibge", "ano"]).sort_index()


def _achar_coluna(frame: pd.DataFrame, nome_final: str) -> Any | None:
    for coluna in frame.columns:
        partes = coluna if isinstance(coluna, tuple) else (coluna,)
        if partes[-1] == nome_final:
            return coluna
    return None


def _normalizar_saida(
    frame: pd.DataFrame,
    *,
    renomear_indices: dict[str, str],
    inferencia: str,
) -> pd.DataFrame:
    coluna_att = _achar_coluna(frame, "ATT")
    if coluna_att is None:
        raise ValueError("saída differences sem coluna ATT")
    resultado = pd.DataFrame(index=frame.index)
    resultado["att"] = frame[coluna_att].to_numpy()
    for origem, destino in (
        ("std_error", "std_error"),
        ("lower", "ci_lower"),
        ("upper", "ci_upper"),
        ("zero_not_in_cband", "zero_fora_intervalo"),
    ):
        coluna = _achar_coluna(frame, origem)
        if coluna is not None:
            resultado[destino] = frame[coluna].to_numpy()
    resultado = resultado.reset_index().rename(columns=renomear_indices)
    resultado["inferencia"] = inferencia
    return resultado


def _construir_modelo(dados_api: pd.DataFrame, cfg: ConfiguracaoEstimacao) -> ATTgt:
    return ATTgt(
        data=dados_api.copy(deep=True),
        cohort_column="coorte_api",
        base_period=cfg.base_period,
        anticipation=cfg.anticipation,
    )


def _ajustar(
    modelo: ATTgt,
    cfg: ConfiguracaoEstimacao,
    *,
    bootstrap: bool,
) -> ATTgt:
    return modelo.fit(
        "outcome_modelo",
        est_method=cfg.est_method,
        control_group=cfg.control_group,
        as_repeated_cross_section=cfg.as_repeated_cross_section,
        cluster_var=None,
        alpha=cfg.alpha,
        boot_iterations=cfg.boot_iterations if bootstrap else 0,
        random_state=cfg.random_state if bootstrap else None,
        n_jobs=cfg.n_jobs,
        progress_bar=False,
    )


def _filtrar_referencia_bootstrap(modelo: ATTgt, cfg: ConfiguracaoEstimacao) -> None:
    periodos = sorted(
        {
            int(tempo - coorte)
            for coorte in modelo._cohorts
            for tempo in modelo._times
            if int(tempo - coorte) != cfg.k_referencia
        }
    )
    modelo.filter_gt(base_period=cfg.base_period, relative_period=periodos)


def _combinar_ponto_inferencia(
    ponto: pd.DataFrame,
    inferencia: pd.DataFrame,
    *,
    chaves: list[str],
    nome: str,
    referencia_evento: bool = False,
) -> pd.DataFrame:
    colunas_inf = chaves + [
        c for c in ("att", "std_error", "ci_lower", "ci_upper", "zero_fora_intervalo")
        if c in inferencia.columns
    ]
    combinado = ponto[chaves + ["att"]].merge(
        inferencia[colunas_inf],
        on=chaves,
        how="left" if referencia_evento else "inner",
        suffixes=("_ponto", "_bootstrap"),
        validate="one_to_one",
    )
    disponivel = combinado["att_bootstrap"].notna()
    if not np.allclose(
        combinado.loc[disponivel, "att_ponto"],
        combinado.loc[disponivel, "att_bootstrap"],
        rtol=0.0,
        atol=1e-12,
    ):
        raise AssertionError(f"workaround k=-1 alterou estimativas de {nome}")
    combinado = combinado.drop(columns="att_bootstrap").rename(
        columns={"att_ponto": "att"}
    )
    combinado["inferencia"] = "bootstrap_simultanea_95"
    return combinado


def estimar_att_gt_real(
    dados: pd.DataFrame,
    *,
    especificacao: str,
    cfg: ConfiguracaoEstimacao = CONFIGURACAO_PRINCIPAL,
) -> dict[str, Any]:
    """Executa o estimador real com o workaround D20B sem mudar pontos."""
    _exigir_backend()
    dados_api = preparar_dados_api(dados)
    inicio = time.perf_counter()
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        ajuste_ponto = _ajustar(_construir_modelo(dados_api, cfg), cfg, bootstrap=False)
        modelo_boot = _construir_modelo(dados_api, cfg)
        _filtrar_referencia_bootstrap(modelo_boot, cfg)
        ajuste_boot = _ajustar(modelo_boot, cfg, bootstrap=True)
        kwargs = {
            "boot_iterations": cfg.boot_iterations,
            "random_state": cfg.random_state,
            "n_jobs": cfg.n_jobs,
        }

        att_ponto = _normalizar_saida(
            ajuste_ponto.to_pandas(),
            renomear_indices={
                "cohort": "coorte_g",
                "base_period": "periodo_base",
                "time": "ano",
            },
            inferencia="pontual_completa",
        )
        att_boot = _normalizar_saida(
            ajuste_boot.to_pandas(),
            renomear_indices={
                "cohort": "coorte_g",
                "base_period": "periodo_base",
                "time": "ano",
            },
            inferencia="bootstrap_simultanea_95",
        )
        event_ponto = _normalizar_saida(
            ajuste_ponto.aggregate("event"),
            renomear_indices={"relative_period": "event_time"},
            inferencia="pontual_completa",
        )
        event_boot = _normalizar_saida(
            ajuste_boot.aggregate("event", **kwargs),
            renomear_indices={"relative_period": "event_time"},
            inferencia="bootstrap_simultanea_95",
        )
        cohort_ponto = _normalizar_saida(
            ajuste_ponto.aggregate("cohort"),
            renomear_indices={"cohort": "coorte_g"},
            inferencia="pontual_completa",
        )
        cohort_boot = _normalizar_saida(
            ajuste_boot.aggregate("cohort", **kwargs),
            renomear_indices={"cohort": "coorte_g"},
            inferencia="bootstrap_simultanea_95",
        )
        simple_ponto = _normalizar_saida(
            ajuste_ponto.aggregate("simple"),
            renomear_indices={},
            inferencia="pontual_completa",
        )
        simple_boot = _normalizar_saida(
            ajuste_boot.aggregate("simple", **kwargs),
            renomear_indices={},
            inferencia="bootstrap_simultanea_95",
        )

    att_gt = _combinar_ponto_inferencia(
        att_ponto,
        att_boot,
        chaves=["coorte_g", "periodo_base", "ano"],
        nome="ATT(g,t)",
        referencia_evento=True,
    )
    att_gt["coorte_g"] = att_gt["coorte_g"].astype(int)
    att_gt["periodo_base"] = att_gt["periodo_base"].astype(int)
    att_gt["ano"] = att_gt["ano"].astype(int)
    att_gt["event_time"] = att_gt["ano"] - att_gt["coorte_g"]
    referencia = att_gt["event_time"].eq(cfg.k_referencia)
    for coluna in ("std_error", "ci_lower", "ci_upper", "zero_fora_intervalo"):
        if coluna not in att_gt:
            att_gt[coluna] = np.nan
        att_gt.loc[referencia, coluna] = np.nan
    contagens = (
        dados.loc[dados["papel_causal"].eq(PAPEL_TRATADO)]
        .drop_duplicates("codigo_municipio_ibge")
        .groupby("coorte_g")["codigo_municipio_ibge"]
        .nunique()
    )
    att_gt["n_tratados_relevante"] = att_gt["coorte_g"].map(contagens).astype(int)
    att_gt["indicador_inferencia"] = np.where(
        referencia, "REFERENCIA_DETERMINISTICA_SEM_INFERENCIA", "BANDA_SIMULTANEA_95"
    )
    mensagens = sorted({str(item.message) for item in avisos})
    att_gt["mensagens_warnings"] = " | ".join(mensagens)
    att_gt["status_celula"] = np.where(
        referencia,
        "REFERENCIA_K_MENOS_1",
        np.where(np.isfinite(att_gt["att"]), "ESTIMADA", "FALHA"),
    )
    falhas_pos = att_gt.loc[
        att_gt["ano"].ge(att_gt["coorte_g"]) & ~np.isfinite(att_gt["att"])
    ]
    if not falhas_pos.empty:
        raise RuntimeError(
            "células ATT(g,t) pós-tratamento falharam: "
            + falhas_pos[["coorte_g", "ano"]].to_dict("records").__repr__()
        )

    event = _combinar_ponto_inferencia(
        event_ponto,
        event_boot,
        chaves=["event_time"],
        nome="event-study",
        referencia_evento=True,
    ).sort_values("event_time").reset_index(drop=True)
    ref_event = event["event_time"].eq(cfg.k_referencia)
    if ref_event.sum() != 1 or event.loc[ref_event, "att"].item() != 0.0:
        raise AssertionError("referência k=-1 ausente ou diferente de zero")
    for coluna in ("std_error", "ci_lower", "ci_upper", "zero_fora_intervalo"):
        if coluna not in event:
            event[coluna] = np.nan
        event.loc[ref_event, coluna] = np.nan
    event["indicador_inferencia"] = np.where(
        ref_event, "REFERENCIA_DETERMINISTICA_SEM_INFERENCIA", "BANDA_SIMULTANEA_95"
    )

    cohort = _combinar_ponto_inferencia(
        cohort_ponto, cohort_boot, chaves=["coorte_g"], nome="cohort"
    )
    cohort["coorte_g"] = cohort["coorte_g"].astype(int)
    cohort["n_tratados"] = cohort["coorte_g"].map(contagens).astype(int)
    cohort["suporte_temporal"] = cohort["coorte_g"].map(
        lambda g: f"2007-2019; k={2007-int(g)}...{2019-int(g)}"
    )
    cohort["warning_precisao"] = np.where(
        cohort["n_tratados"].eq(2), "COORTE_2013_N2_PRECISAO_CRITICA", ""
    )
    simple = _combinar_ponto_inferencia(
        simple_ponto, simple_boot, chaves=["index"], nome="simple"
    )
    simple["agregacao"] = "simple_global"
    duracao = time.perf_counter() - inicio
    metadados = {
        "especificacao": especificacao,
        "rotulo": ROTULOS[especificacao],
        "duracao_segundos": duracao,
        "n_celulas_att_gt": int(len(att_gt)),
        "n_celulas_pos_tratamento": int(att_gt["ano"].ge(att_gt["coorte_g"]).sum()),
        "n_celulas_pos_falhas": 0,
        "warnings": mensagens,
        "workaround_k_menos_1": True,
        "estimativa_pontual_invariante": True,
    }
    return {
        "att_gt": att_gt,
        "simple": simple,
        "cohort": cohort,
        "event": event,
        "metadados": metadados,
    }


def _erro_assimetrico(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "type": "data",
        "symmetric": False,
        "array": (frame["ci_upper"] - frame["att"]).to_numpy(),
        "arrayminus": (frame["att"] - frame["ci_lower"]).to_numpy(),
        "color": CORES_IPT["AZUL_MEDIO"],
        "thickness": 1.2,
    }


def _figura_evento(frame: pd.DataFrame, titulo: str) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=frame["event_time"],
            y=frame["att"],
            mode="lines+markers",
            name="ATT dinâmico",
            line={"color": CORES_IPT["AZUL_PRINCIPAL"]},
            marker={"size": 8},
            error_y=_erro_assimetrico(frame),
            customdata=np.column_stack([frame["ci_lower"], frame["ci_upper"]]),
            hovertemplate="k=%{x}<br>ATT=%{y:,.2f}<br>Banda 95%=[%{customdata[0]:,.2f}; %{customdata[1]:,.2f}]<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color=CORES_IPT["AZUL_ESCURO"])
    fig.add_vline(x=-1, line_dash="dot", line_color=CORES_IPT["CIANO"])
    fig.update_xaxes(title="Tempo relativo ao tratamento (k)", dtick=1)
    fig.update_yaxes(title="ATT — pessoal ocupado assalariado")
    aplicar_tema_ipt(fig, titulo=titulo)
    return fig


def _figura_coorte(frame: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=frame["coorte_g"],
            y=frame["att"],
            mode="markers",
            marker={"size": 11, "color": CORES_IPT["AZUL_PRINCIPAL"]},
            error_y=_erro_assimetrico(frame),
            text=frame["n_tratados"],
            hovertemplate="Coorte=%{x}<br>ATT=%{y:,.2f}<br>n tratados=%{text}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color=CORES_IPT["AZUL_ESCURO"])
    fig.update_xaxes(title="Coorte de tratamento", dtick=1)
    fig.update_yaxes(title="ATT agregado da coorte")
    aplicar_tema_ipt(fig, titulo="D20C — ATT agregado por coorte e bandas simultâneas de 95%")
    return fig


def _exigir_ausentes(caminhos: list[Path]) -> None:
    existentes = [str(p.relative_to(ROOT)) for p in caminhos if p.exists()]
    if existentes:
        raise FileExistsError(
            "recusa de sobrescrita silenciosa; artefatos já existem: " + ", ".join(existentes)
        )


def _salvar_csv(frame: pd.DataFrame, caminho: Path) -> None:
    frame.to_csv(caminho, index=False, encoding="utf-8-sig")


def _registro_arquivo(caminho: Path) -> dict[str, str]:
    return {
        "path": caminho.relative_to(ROOT).as_posix(),
        "sha256": sha256_arquivo(caminho),
    }


def _carregar_insumos_robustez() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    overlap = pd.read_csv(
        ROOT / "outputs" / "diagnostics" / "D18_overlap_att.csv",
        dtype={"codigo_municipio_ibge": "string"},
    )
    distancias = pd.read_parquet(
        ROOT / "data" / "processed" / "diagnostico_distancias_spillover_fase_ii.parquet"
    )
    arranjos = pd.read_parquet(
        ROOT / "data" / "processed" / "diagnostico_arranjos_populacionais_fase_ii.parquet"
    )
    return overlap, distancias, arranjos


def executar_d20c(
    view: pd.DataFrame,
    auditoria_view: dict[str, Any],
    *,
    out_dir: Path,
    fig_dir: Path,
    overlap: pd.DataFrame,
    distancias: pd.DataFrame,
    arranjos: pd.DataFrame,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Executa, persiste e congela o resultado principal antes das robustezes."""
    arquivos = [
        out_dir / "D20C_att_gt_principal.csv",
        out_dir / "D20C_agregacao_simples.csv",
        out_dir / "D20C_agregacao_coorte.csv",
        out_dir / "D20C_event_study_completo.csv",
        out_dir / "D20C_event_study_principal.csv",
        out_dir / "D20C_manifesto_resultado.json",
        fig_dir / "D20C_event_study_principal.html",
        fig_dir / "D20C_event_study_completo.html",
        fig_dir / "D20C_att_coorte.html",
    ]
    _exigir_ausentes(arquivos)
    dados, populacao = construir_populacao_especificacao(
        view,
        "principal",
        overlap=overlap,
        distancias=distancias,
        arranjos=arranjos,
    )
    resultado = estimar_att_gt_real(dados, especificacao="principal")
    janela = resultado["event"].loc[
        resultado["event"]["event_time"].isin(CONFIGURACAO_PRINCIPAL.janela_principal)
    ].copy()
    if set(janela["event_time"]) != set(CONFIGURACAO_PRINCIPAL.janela_principal):
        raise AssertionError("janela principal não possui k=-2,-1,0,+1,+2")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    _salvar_csv(resultado["att_gt"], arquivos[0])
    _salvar_csv(resultado["simple"], arquivos[1])
    _salvar_csv(resultado["cohort"], arquivos[2])
    _salvar_csv(resultado["event"], arquivos[3])
    _salvar_csv(janela, arquivos[4])
    _figura_evento(
        janela, "D20C — Event-study principal (k=-2 a +2)"
    ).write_html(arquivos[6], include_plotlyjs=True, full_html=True)
    _figura_evento(
        resultado["event"], "D20C — Event-study completo (diagnóstico)"
    ).write_html(arquivos[7], include_plotlyjs=True, full_html=True)
    _figura_coorte(resultado["cohort"]).write_html(
        arquivos[8], include_plotlyjs=True, full_html=True
    )
    outputs = [_registro_arquivo(p) for p in arquivos[:5] + arquivos[6:]]
    manifesto = {
        "unidade": "D20C",
        "criado_em_utc": datetime.now(timezone.utc).isoformat(),
        "git": {"branch": _git("branch", "--show-current"), "head": _git("rev-parse", "HEAD")},
        "inputs": {
            "d15": {
                "path": "data/processed/amostra_causal_cempre_2007_2019.parquet",
                "sha256": HASH_D15_ESPERADO,
            },
            "view_d20b": {
                "path": "data/processed/amostra_principal_estimavel_d20b_2007_2019.parquet",
                "sha256": HASH_VIEW_D20B_ESPERADO,
            },
        },
        "configuracao": asdict(CONFIGURACAO_PRINCIPAL),
        "populacao": auditoria_view,
        "outcome": OUTCOME_PRIMARIO,
        "agregacoes": ["ATT(g,t)", "simple", "cohort", "event"],
        "metadados_execucao": resultado["metadados"],
        "outputs": outputs,
        "gates": {
            "D20C_AMOSTRA_PRINCIPAL_VALIDADA": "SIM",
            "D20C_ATT_GT_REAL_ESTIMADO": "SIM",
            "D20C_AGREGACAO_SIMPLE_ESTIMADA": "SIM",
            "D20C_AGREGACAO_COORTE_ESTIMADA": "SIM",
            "D20C_EVENT_STUDY_REAL_ESTIMADO": "SIM",
            "D20C_BOOTSTRAP_1999_CONCLUIDO": "SIM",
            "D20C_BANDAS_SIMULTANEAS_VALIDAS": "SIM",
            "D20C_RESULTADO_PRINCIPAL_CONGELADO": "SIM",
            "DESENHO_CAUSAL_APROVADO": "NAO",
        },
    }
    _escrever_json(arquivos[5], manifesto)
    return resultado, manifesto


def _salvar_robustez(
    nome: str,
    resultado: dict[str, Any],
    populacao: dict[str, Any],
    *,
    out_dir: Path,
) -> dict[str, Any]:
    prefixo = out_dir / f"D20D_{nome}"
    caminhos = {
        "att_gt": prefixo.with_name(prefixo.name + "_att_gt.csv"),
        "simple": prefixo.with_name(prefixo.name + "_simple.csv"),
        "cohort": prefixo.with_name(prefixo.name + "_cohort.csv"),
        "event": prefixo.with_name(prefixo.name + "_event_study.csv"),
        "manifesto": prefixo.with_name(prefixo.name + "_manifesto.json"),
    }
    _exigir_ausentes(list(caminhos.values()))
    _salvar_csv(resultado["att_gt"], caminhos["att_gt"])
    _salvar_csv(resultado["simple"], caminhos["simple"])
    _salvar_csv(resultado["cohort"], caminhos["cohort"])
    _salvar_csv(resultado["event"], caminhos["event"])
    manifesto = {
        "unidade": "D20D",
        "especificacao": nome,
        "rotulo": ROTULOS[nome],
        "criado_em_utc": datetime.now(timezone.utc).isoformat(),
        "configuracao": asdict(CONFIGURACAO_PRINCIPAL),
        "populacao": populacao,
        "metadados_execucao": resultado["metadados"],
        "outputs": [_registro_arquivo(p) for k, p in caminhos.items() if k != "manifesto"],
        "resultado_principal_substituido": False,
    }
    _escrever_json(caminhos["manifesto"], manifesto)
    return manifesto


def _linha_comparativa(
    nome: str,
    resultado: dict[str, Any],
    populacao: dict[str, Any],
) -> dict[str, Any]:
    simple = resultado["simple"].iloc[0]
    event = resultado["event"].set_index("event_time")
    coortes = ",".join(map(str, sorted(populacao["coortes"])))
    observacao = {
        "principal": "Especificação principal congelada",
        "log1p": "Estimando em escala log1p; não comparável 1:1 a empregos em nível",
        "janela_3pre": "Coortes 2010-2013; painel 2007-2019 integral",
        "suporte": "Exclui apenas cinco tratados extremos D18; não é amostra principal",
        "spillover_25km": "Exclui controles pré-classificados a <=25 km",
        "spillover_50km": "Exclui controles pré-classificados a <=50 km",
        "spillover_100km": "Exclui controles pré-classificados a <=100 km",
        "arranjo_populacional": "Classificação IBGE 2010; sensibilidade temporalmente limitada",
    }[nome]
    linha: dict[str, Any] = {
        "especificacao": nome,
        "n_tratados": populacao["n_tratados"],
        "n_controles": populacao["n_controles"],
        "escala_outcome": populacao["escala_outcome"],
        "coortes": coortes,
        "ATT_simple": simple["att"],
        "banda_lower": simple.get("ci_lower", np.nan),
        "banda_upper": simple.get("ci_upper", np.nan),
        "observacao_metodologica": observacao,
    }
    for k in (0, 1, 2):
        linha[f"ATT_event_k{k}"] = event.loc[k, "att"] if k in event.index else np.nan
    return linha


def executar_d20d(
    view: pd.DataFrame,
    principal: dict[str, Any],
    *,
    out_dir: Path,
    overlap: pd.DataFrame,
    distancias: pd.DataFrame,
    arranjos: pd.DataFrame,
) -> tuple[dict[str, dict[str, Any]], pd.DataFrame, pd.DataFrame]:
    """Executa cada robustez em artefatos independentes."""
    hash_principal_antes = sha256_arquivo(out_dir / "D20C_att_gt_principal.csv")
    resultados: dict[str, dict[str, Any]] = {"principal": principal}
    populacoes: dict[str, dict[str, Any]] = {}
    _, populacoes["principal"] = construir_populacao_especificacao(
        view, "principal", overlap=overlap, distancias=distancias, arranjos=arranjos
    )
    for nome in ORDEM_ESPECIFICACOES[1:]:
        dados, populacao = construir_populacao_especificacao(
            view, nome, overlap=overlap, distancias=distancias, arranjos=arranjos
        )
        resultado = estimar_att_gt_real(dados, especificacao=nome)
        _salvar_robustez(nome, resultado, populacao, out_dir=out_dir)
        resultados[nome] = resultado
        populacoes[nome] = populacao
        if sha256_arquivo(out_dir / "D20C_att_gt_principal.csv") != hash_principal_antes:
            raise AssertionError("robustez alterou o resultado principal congelado")

    comparativa = pd.DataFrame(
        [_linha_comparativa(nome, resultados[nome], populacoes[nome]) for nome in ORDEM_ESPECIFICACOES]
    )
    principal_att = float(comparativa.loc[comparativa["especificacao"].eq("principal"), "ATT_simple"].item())
    estabilidade = comparativa[["especificacao", "escala_outcome", "ATT_simple", "banda_lower", "banda_upper"]].copy()
    comparavel = estabilidade["escala_outcome"].eq("nivel")
    estabilidade["diferenca_absoluta_principal"] = np.where(
        comparavel, estabilidade["ATT_simple"] - principal_att, np.nan
    )
    estabilidade["diferenca_relativa_principal"] = np.where(
        comparavel & ~np.isclose(principal_att, 0.0),
        (estabilidade["ATT_simple"] - principal_att) / abs(principal_att),
        np.nan,
    )
    estabilidade["mudanca_sinal"] = np.where(
        comparavel,
        np.sign(estabilidade["ATT_simple"]) != np.sign(principal_att),
        pd.NA,
    )
    p = comparativa.loc[comparativa["especificacao"].eq("principal")].iloc[0]
    estabilidade["intervalos_sobrepostos_descritivo"] = np.where(
        comparavel,
        (estabilidade["banda_lower"] <= p["banda_upper"])
        & (estabilidade["banda_upper"] >= p["banda_lower"]),
        pd.NA,
    )
    caminhos = [
        out_dir / "D20D_tabela_comparativa.csv",
        out_dir / "D20D_estabilidade.csv",
        out_dir / "D20D_gates.json",
    ]
    _exigir_ausentes(caminhos)
    _salvar_csv(comparativa, caminhos[0])
    _salvar_csv(estabilidade, caminhos[1])
    gates = {
        "D20D_LOG1P_EXECUTADO": "SIM",
        "D20D_JANELA_3PRE_EXECUTADA": "SIM",
        "D20D_SUPORTE_EXECUTADO": "SIM",
        "D20D_SPILLOVER_25_EXECUTADO": "SIM",
        "D20D_SPILLOVER_50_EXECUTADO": "SIM",
        "D20D_SPILLOVER_100_EXECUTADO": "SIM",
        "D20D_ARRANJO_EXECUTADO": "SIM",
        "D20D_ROBUSTEZES_PRE_ESPECIFICADAS_CONCLUIDAS": "SIM",
        "DESENHO_CAUSAL_APROVADO": "NAO",
    }
    _escrever_json(caminhos[2], gates)
    return resultados, comparativa, estabilidade


def _resumo_leads(event: pd.DataFrame) -> dict[str, Any]:
    leads = event.loc[event["event_time"].lt(-1)].copy()
    validos = leads.dropna(subset=["ci_lower", "ci_upper"])
    return {
        "n_leads": int(len(leads)),
        "event_times": [int(x) for x in leads["event_time"]],
        "max_abs_att": float(leads["att"].abs().max()) if len(leads) else None,
        "n_bandas_excluem_zero": int(
            ((validos["ci_lower"] > 0) | (validos["ci_upper"] < 0)).sum()
        ),
        "interpretacao": "diagnostico_pos_estimacao; nao comprova nem refuta automaticamente tendencias paralelas",
    }


def _matriz_evidencia(
    resultados: dict[str, dict[str, Any]],
    comparativa: pd.DataFrame,
) -> pd.DataFrame:
    principal = resultados["principal"]
    leads = _resumo_leads(principal["event"])
    suporte = comparativa.loc[comparativa["especificacao"].eq("suporte")].iloc[0]
    spill = comparativa.loc[
        comparativa["especificacao"].isin(
            ["spillover_25km", "spillover_50km", "spillover_100km", "arranjo_populacional"]
        )
    ]
    coorte_2013 = principal["cohort"].loc[principal["cohort"]["coorte_g"].eq(2013)].iloc[0]
    linhas = [
        ("pre_tendencias", f"{leads['n_leads']} leads; máximo |ATT|={leads['max_abs_att']}", "Leads reportados com bandas simultâneas", "Janela 3 pré preservada", "Poder limitado e heterogeneidade pré", "Diagnóstico; não prova tendências paralelas"),
        ("overlap", "Cinco tratados extremos diagnosticados antes da estimação", "Principal preserva 128 tratados", f"Suporte: ATT simple={suporte['ATT_simple']}", "Sensibilidade não corrige o principal", "Comparar magnitude sem substituir estimando"),
        ("escala", "Diferenças de nível e assimetria documentadas em D17/D18", "Outcome em nível", "log1p em escala distinta", "Não há conversão exata para empregos", "Não comparar ATT log 1:1 com nível"),
        ("spillover", "Controles próximos/mesmo arranjo pré-classificados", "Sem filtro espacial", f"ATT simple variou entre {spill['ATT_simple'].min()} e {spill['ATT_simple'].max()}", "Distância e arranjo são proxies", "Diferenças são compatíveis, não prova de spillover"),
        ("timing_proxy", "128/129 timings D15 eram proxy Censo; Cabo Frio tratado por addendum", "anticipation=0", "Nenhuma janela alternativa executada", "Antecipação substantiva permanece possível", "Hipótese identificadora, não fato observado"),
        ("coorte_pequena", f"Coorte 2013 n=2; ATT={coorte_2013['att']}", "Coorte preservada", "Presente em sensibilidades aplicáveis", "Alta imprecisão e baixa generalização", "Separar magnitude de incerteza"),
        ("influencia_municipios_grandes", "D18 mostrou influência material pré-tratamento", "Nenhuma exclusão retrospectiva", "Não foi criada robustez top-N", "Estimativas em nível podem ser influenciadas por porte", "Interpretar como efeito médio em nível"),
        ("inferencia", "Multiplier bootstrap, 1.999 draws, cluster entidade", "Bandas simultâneas 95%", "Mesma configuração em todas robustezes", "Poucas unidades na coorte 2013", "Incerteza deve acompanhar cada estimativa"),
        ("validade_externa", "População principal efetivamente estimável: 128 tratados", "Estimando restrito ao suporte observado", "Sensibilidades mudam população/controles", "Não representa automaticamente os 147 municípios institucionais", "Generalização deve permanecer delimitada"),
    ]
    return pd.DataFrame(
        linhas,
        columns=[
            "dimensao",
            "evidencia_observada",
            "resultado_principal",
            "sensibilidades",
            "risco_residual",
            "impacto_interpretacao",
        ],
    )


def auditar_reprodutibilidade_principal(
    view: pd.DataFrame,
    *,
    out_dir: Path,
    overlap: pd.DataFrame,
    distancias: pd.DataFrame,
    arranjos: pd.DataFrame,
) -> dict[str, Any]:
    """Repete o principal em memória com a mesma seed e compara os outputs."""
    dados, _ = construir_populacao_especificacao(
        view,
        "principal",
        overlap=overlap,
        distancias=distancias,
        arranjos=arranjos,
    )
    repeticao = estimar_att_gt_real(dados, especificacao="principal")
    contratos = {
        "att_gt": (
            pd.read_csv(out_dir / "D20C_att_gt_principal.csv"),
            repeticao["att_gt"],
            ["coorte_g", "periodo_base", "ano"],
        ),
        "simple": (
            pd.read_csv(out_dir / "D20C_agregacao_simples.csv"),
            repeticao["simple"],
            ["index"],
        ),
        "cohort": (
            pd.read_csv(out_dir / "D20C_agregacao_coorte.csv"),
            repeticao["cohort"],
            ["coorte_g"],
        ),
        "event": (
            pd.read_csv(out_dir / "D20C_event_study_completo.csv"),
            repeticao["event"],
            ["event_time"],
        ),
    }
    maximos: dict[str, float] = {}
    for nome, (congelado, novo, chaves) in contratos.items():
        numericas = [
            c for c in ("att", "std_error", "ci_lower", "ci_upper")
            if c in congelado.columns and c in novo.columns
        ]
        comparacao = congelado[chaves + numericas].merge(
            novo[chaves + numericas],
            on=chaves,
            how="outer",
            suffixes=("_congelado", "_repeticao"),
            indicator=True,
            validate="one_to_one",
        )
        if not comparacao["_merge"].eq("both").all():
            raise AssertionError(f"repetição alterou o suporte de {nome}")
        diffs: list[float] = []
        for coluna in numericas:
            a = comparacao[f"{coluna}_congelado"].to_numpy(dtype=float)
            b = comparacao[f"{coluna}_repeticao"].to_numpy(dtype=float)
            mask = np.isfinite(a) | np.isfinite(b)
            if not np.array_equal(np.isnan(a), np.isnan(b)):
                raise AssertionError(f"repetição alterou missingness de {nome}.{coluna}")
            if mask.any():
                diffs.append(float(np.max(np.abs(a[mask] - b[mask]))))
        maximos[nome] = max(diffs, default=0.0)
    max_abs_diff = max(maximos.values(), default=0.0)
    if max_abs_diff > TOLERANCIA_REPRODUTIBILIDADE:
        raise AssertionError(
            f"seed congelada não reproduziu o principal: max_abs_diff={max_abs_diff}"
        )
    return {
        "reproduzivel": True,
        "random_state": CONFIGURACAO_PRINCIPAL.random_state,
        "boot_iterations": CONFIGURACAO_PRINCIPAL.boot_iterations,
        "n_jobs": CONFIGURACAO_PRINCIPAL.n_jobs,
        "max_abs_diff": max_abs_diff,
        "tolerancia_numerica": TOLERANCIA_REPRODUTIBILIDADE,
        "max_abs_diff_por_objeto": maximos,
        "duracao_repeticao_segundos": repeticao["metadados"]["duracao_segundos"],
        "outputs_principais_sobrescritos": False,
    }


def executar_d20e(
    view: pd.DataFrame,
    resultados: dict[str, dict[str, Any]],
    comparativa: pd.DataFrame,
    *,
    out_dir: Path,
    reprodutibilidade: dict[str, Any],
) -> dict[str, Any]:
    """Audita somente resultados existentes; não cria nova especificação."""
    principal = resultados["principal"]
    att_gt = principal["att_gt"]
    event = principal["event"]
    cohort = principal["cohort"]
    simple = principal["simple"]
    ref = event.loc[event["event_time"].eq(-1)]
    verificacoes = {
        "att_gt_sem_duplicidade": bool(
            not att_gt.duplicated(["coorte_g", "periodo_base", "ano"]).any()
        ),
        "att_gt_pos_finito": bool(
            np.isfinite(att_gt.loc[att_gt["ano"].ge(att_gt["coorte_g"]), "att"]).all()
        ),
        "event_time_correto": bool(
            (att_gt["event_time"] == att_gt["ano"] - att_gt["coorte_g"]).all()
        ),
        "referencia_k_menos_1": bool(
            len(ref) == 1
            and ref["att"].item() == 0.0
            and ref[["std_error", "ci_lower", "ci_upper"]].isna().all().all()
        ),
        "coortes_completas": bool(set(cohort["coorte_g"]) == set(COORTES_PRINCIPAIS)),
        "simple_unico": bool(len(simple) == 1),
        "hash_d15_integro": bool(
            sha256_arquivo(ROOT / "data" / "processed" / "amostra_causal_cempre_2007_2019.parquet")
            == HASH_D15_ESPERADO
        ),
        "hash_view_d20b_integro": bool(
            sha256_arquivo(ROOT / "data" / "processed" / "amostra_principal_estimavel_d20b_2007_2019.parquet")
            == HASH_VIEW_D20B_ESPERADO
        ),
    }
    if not all(verificacoes.values()):
        raise AssertionError(
            "auditoria D20E encontrou inconsistência: "
            + str([k for k, v in verificacoes.items() if not v])
        )
    media_pre = float(
        view.loc[
            view["papel_causal"].eq(PAPEL_TRATADO)
            & view["ano"].lt(view["coorte_g"]),
            OUTCOME_PRIMARIO,
        ].mean()
    )
    att_simple = float(simple["att"].iloc[0])
    contextualizacao = {
        "denominador": "media de municipio-ano pre-tratamento dos 128 tratados",
        "media_pre_tratamento": media_pre,
        "att_simple_nivel": att_simple,
        "att_sobre_media_pre": att_simple / media_pre,
        "rotulo": "CONTEXTUALIZACAO_DESCRITIVA_NAO_NOVO_ESTIMANDO_CAUSAL",
    }
    matriz = _matriz_evidencia(resultados, comparativa)
    caminhos = [
        out_dir / "D20E_matriz_evidencia.csv",
        out_dir / "D20E_auditoria_pos_estimacao.json",
    ]
    _exigir_ausentes(caminhos)
    _salvar_csv(matriz, caminhos[0])
    auditoria = {
        "unidade": "D20E",
        "criado_em_utc": datetime.now(timezone.utc).isoformat(),
        "verificacoes": verificacoes,
        "reprodutibilidade_seed": reprodutibilidade,
        "pesos_agregacao": {
            "expostos_saida_publica": False,
            "status": "NAO_EXPOSTOS_PELA_SAIDA_PUBLICA_DIFFERENCES_0_3_0",
            "auditoria_realizada": (
                "agregacoes simple, cohort e event foram obtidas diretamente da API; "
                "não foi inferida ponderação alternativa a partir das tabelas finais"
            ),
        },
        "leads": _resumo_leads(event),
        "contextualizacao_magnitude": contextualizacao,
        "coorte_2013": cohort.loc[cohort["coorte_g"].eq(2013)].to_dict("records")[0],
        "comparacao_suporte": comparativa.loc[
            comparativa["especificacao"].isin(["principal", "suporte"])
        ].to_dict("records"),
        "comparacao_spillover": comparativa.loc[
            comparativa["especificacao"].isin(
                ["principal", "spillover_25km", "spillover_50km", "spillover_100km", "arranjo_populacional"]
            )
        ].to_dict("records"),
        "gates": {
            "D20E_AUDITORIA_POS_ESTIMACAO_CONCLUIDA": "SIM",
            "D20E_PRE_TENDENCIAS_REAVALIADAS": "SIM",
            "D20E_OVERLAP_REAVALIADO": "SIM",
            "D20E_SPILLOVER_REAVALIADO": "SIM",
            "D20E_COORTE_2013_REAVALIADA": "SIM",
            "D20E_MATRIZ_EVIDENCIA_PRODUZIDA": "SIM",
            "D20E_INTERPRETACAO_CAUSAL_PENDENTE_REVISAO": "SIM",
            "DESENHO_CAUSAL_APROVADO": "NAO",
        },
    }
    _escrever_json(caminhos[1], auditoria)
    return auditoria


def executar_pipeline() -> dict[str, Any]:
    """Executa D20C, congela, executa D20D e então audita em D20E."""
    d15 = ROOT / "data" / "processed" / "amostra_causal_cempre_2007_2019.parquet"
    view_path = ROOT / "data" / "processed" / "amostra_principal_estimavel_d20b_2007_2019.parquet"
    if sha256_arquivo(d15) != HASH_D15_ESPERADO:
        raise AssertionError("hash D15 divergente antes da estimação")
    view, auditoria_view = carregar_validar_view_principal(view_path)
    overlap, distancias, arranjos = _carregar_insumos_robustez()
    out_dir = ROOT / "outputs" / "causal"
    fig_dir = ROOT / "outputs" / "figures" / "interactive"
    principal, manifesto = executar_d20c(
        view,
        auditoria_view,
        out_dir=out_dir,
        fig_dir=fig_dir,
        overlap=overlap,
        distancias=distancias,
        arranjos=arranjos,
    )
    resultados, comparativa, estabilidade = executar_d20d(
        view,
        principal,
        out_dir=out_dir,
        overlap=overlap,
        distancias=distancias,
        arranjos=arranjos,
    )
    reprodutibilidade = auditar_reprodutibilidade_principal(
        view,
        out_dir=out_dir,
        overlap=overlap,
        distancias=distancias,
        arranjos=arranjos,
    )
    auditoria = executar_d20e(
        view,
        resultados,
        comparativa,
        out_dir=out_dir,
        reprodutibilidade=reprodutibilidade,
    )
    if sha256_arquivo(d15) != HASH_D15_ESPERADO:
        raise AssertionError("hash D15 divergente depois da estimação")
    if sha256_arquivo(view_path) != HASH_VIEW_D20B_ESPERADO:
        raise AssertionError("hash D20B divergente depois da estimação")
    return {
        "manifesto_principal": manifesto,
        "comparativa": comparativa,
        "estabilidade": estabilidade,
        "auditoria": auditoria,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--executar",
        action="store_true",
        help="executa a primeira estimação real e todas as robustezes pré-especificadas",
    )
    grupo.add_argument(
        "--auditar-reprodutibilidade",
        action="store_true",
        help="repete o principal em memória e atualiza somente a auditoria D20E",
    )
    args = parser.parse_args()
    if args.executar:
        resumo = executar_pipeline()
        print(resumo["comparativa"].to_string(index=False))
        return
    view_path = ROOT / "data" / "processed" / "amostra_principal_estimavel_d20b_2007_2019.parquet"
    view, _ = carregar_validar_view_principal(view_path)
    overlap, distancias, arranjos = _carregar_insumos_robustez()
    out_dir = ROOT / "outputs" / "causal"
    resultado = auditar_reprodutibilidade_principal(
        view,
        out_dir=out_dir,
        overlap=overlap,
        distancias=distancias,
        arranjos=arranjos,
    )
    caminho_auditoria = out_dir / "D20E_auditoria_pos_estimacao.json"
    auditoria = json.loads(caminho_auditoria.read_text(encoding="utf-8"))
    auditoria["reprodutibilidade_seed"] = resultado
    _escrever_json(caminho_auditoria, auditoria)
    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=_json_seguro))


if __name__ == "__main__":
    main()
