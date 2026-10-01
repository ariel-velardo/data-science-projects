"""Seleção preditiva auditável do propensity score, sem usar efeitos causais.

O módulo é deliberadamente estreito: avalia uma pequena grade de regularização
para o modelo logístico já certificado e preserva C=1 sempre que ele estiver
dentro de um erro-padrão do melhor candidato e cumprir os guardrails.
"""
from __future__ import annotations

from collections.abc import Iterator
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path
from time import perf_counter
import unicodedata

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from src.modelagem_preditiva import CAT, NUM, ajustar_modelo, criar_modelo, predizer, validar_x


SEED = 20240925
BASELINE_C = 1.0
GRADE_C_PROPENSITY = (0.01, 0.1, 1.0, 10.0, 100.0)

_CHAVES_CAUSAIS_PROIBIDAS = (
    "aipw", "cate", "efeito", "estimativa", "significancia", "p_value",
    "intervalo_confianca", "ic95", "qini", "auuc",
)


def _vetor_binario(y, nome: str) -> np.ndarray:
    vetor = np.asarray(y, dtype=int)
    if vetor.ndim != 1 or len(vetor) == 0:
        raise ValueError(f"{nome} deve ser um vetor unidimensional não vazio.")
    if set(np.unique(vetor)) != {0, 1}:
        raise ValueError(f"{nome} deve conter as duas classes binárias 0 e 1.")
    return vetor


def metricas_probabilidade(y, p, n_bins: int = 10) -> dict[str, float]:
    """Calcula métricas preditivas e de calibração para probabilidades OOF."""
    y_arr = _vetor_binario(y, "y")
    p_arr = np.asarray(p, dtype=float)
    if p_arr.shape != y_arr.shape or not np.isfinite(p_arr).all():
        raise ValueError("p deve ser finito e ter o mesmo tamanho de y.")
    if np.any((p_arr < 0) | (p_arr > 1)):
        raise ValueError("p deve estar no intervalo [0, 1].")

    observado, previsto = calibration_curve(
        y_arr, p_arr, n_bins=min(int(n_bins), len(y_arr)), strategy="quantile"
    )
    erros = np.abs(observado - previsto)
    return {
        "log_loss": float(log_loss(y_arr, p_arr, labels=[0, 1])),
        "brier": float(brier_score_loss(y_arr, p_arr)),
        "auc": float(roc_auc_score(y_arr, p_arr)),
        "prevalencia": float(y_arr.mean()),
        "media_predita": float(p_arr.mean()),
        "erro_calibracao_medio": float(erros.mean()),
        "erro_calibracao_maximo": float(erros.max()),
    }


def _media_variancia_ponderadas(valores: np.ndarray, pesos: np.ndarray) -> tuple[float, float]:
    soma = float(pesos.sum())
    if soma <= 0:
        raise ValueError("Pesos devem ter soma positiva em ambos os grupos.")
    media = float(np.sum(pesos * valores) / soma)
    variancia = float(np.sum(pesos * (valores - media) ** 2) / soma)
    return media, variancia


def _smd(valores: np.ndarray, t: np.ndarray, pesos: np.ndarray) -> float:
    m0, v0 = _media_variancia_ponderadas(valores[t == 0], pesos[t == 0])
    m1, v1 = _media_variancia_ponderadas(valores[t == 1], pesos[t == 1])
    escala = sqrt((v0 + v1) / 2)
    if escala == 0:
        return 0.0 if m0 == m1 else float("inf")
    return float((m1 - m0) / escala)


def _colunas_balanceamento(
    x: pd.DataFrame,
    numericas: tuple[str, ...] | list[str],
    categoricas: tuple[str, ...] | list[str],
) -> Iterator[tuple[str, np.ndarray]]:
    """Itera colunas de balanÃ§o sem materializar todas simultaneamente."""
    for coluna in numericas:
        valores = pd.to_numeric(x[coluna], errors="coerce")
        mediana = float(valores.median()) if valores.notna().any() else 0.0
        yield coluna, valores.fillna(mediana).to_numpy(dtype=float)
        yield f"{coluna}=AUSENTE", valores.isna().to_numpy(dtype=float)
    for coluna in categoricas:
        serie = x[coluna].astype("string").fillna("AUSENTE")
        for nivel in sorted(serie.unique().tolist()):
            yield f"{coluna}={nivel}", (serie == nivel).to_numpy(dtype=float)


def _ess(pesos: np.ndarray) -> float:
    denominador = float(np.sum(pesos**2))
    return float(np.sum(pesos) ** 2 / denominador) if denominador > 0 else 0.0


def diagnosticos_propensity(
    x: pd.DataFrame,
    t,
    e,
    *,
    numericas: tuple[str, ...] | list[str] = tuple(NUM),
    categoricas: tuple[str, ...] | list[str] = tuple(CAT),
) -> dict[str, float]:
    """Resume overlap, ESS e maior SMD antes/depois dos pesos ATE não truncados."""
    t_arr = _vetor_binario(t, "t")
    e_arr = np.asarray(e, dtype=float)
    if len(x) != len(t_arr) or e_arr.shape != t_arr.shape:
        raise ValueError("x, t e e devem ter o mesmo número de observações.")
    if not np.isfinite(e_arr).all() or np.any((e_arr <= 0) | (e_arr >= 1)):
        raise ValueError("Propensities devem ser finitos e estritamente entre 0 e 1.")

    pesos = np.where(t_arr == 1, 1.0 / e_arr, 1.0 / (1.0 - e_arr))
    unitarios = np.ones(len(t_arr), dtype=float)
    max_bruto = 0.0
    max_ponderado = 0.0
    for _, valores in _colunas_balanceamento(x, numericas, categoricas):
        max_bruto = max(max_bruto, abs(_smd(valores, t_arr, unitarios)))
        max_ponderado = max(max_ponderado, abs(_smd(valores, t_arr, pesos)))
    n0 = int(np.sum(t_arr == 0))
    n1 = int(np.sum(t_arr == 1))
    return {
        "max_abs_smd_bruto": float(max_bruto),
        "max_abs_smd_ponderado": float(max_ponderado),
        "ess_t0": _ess(pesos[t_arr == 0]),
        "ess_t1": _ess(pesos[t_arr == 1]),
        "ess_t0_sobre_n": _ess(pesos[t_arr == 0]) / n0,
        "ess_t1_sobre_n": _ess(pesos[t_arr == 1]) / n1,
        "fora_005_095_fracao": float(np.mean((e_arr < 0.05) | (e_arr > 0.95))),
        "propensity_min": float(e_arr.min()),
        "propensity_max": float(e_arr.max()),
    }


def _hash_indices(indices: np.ndarray) -> str:
    return sha256(np.asarray(indices, dtype=np.int64).tobytes()).hexdigest()


def avaliar_grade_propensity(
    x: pd.DataFrame,
    t,
    *,
    candidatos: tuple[float, ...] = GRADE_C_PROPENSITY,
    n_folds: int = 3,
    seed: int = SEED,
) -> dict[str, object]:
    """Compara C por predições out-of-fold, sem receber ou consultar outcome."""
    validar_x(x)
    t_arr = _vetor_binario(t, "t")
    if len(x) != len(t_arr):
        raise ValueError("x e t devem ter o mesmo número de observações.")
    grade = tuple(float(c) for c in candidatos)
    if not grade or any((not np.isfinite(c)) or c <= 0 for c in grade):
        raise ValueError("Todos os candidatos C devem ser positivos e finitos.")

    splitter = StratifiedKFold(n_splits=int(n_folds), shuffle=True, random_state=int(seed))
    folds = list(splitter.split(x, t_arr))
    auditoria_folds = [
        {
            "fold": i,
            "n_treino": int(len(treino)),
            "n_validacao": int(len(validacao)),
            "hash_treino": _hash_indices(treino),
            "hash_validacao": _hash_indices(validacao),
        }
        for i, (treino, validacao) in enumerate(folds, start=1)
    ]
    cobertura = np.zeros(len(x), dtype=int)
    for _, validacao in folds:
        cobertura[validacao] += 1

    resultados: list[dict[str, float]] = []
    for c in grade:
        oof = np.full(len(x), np.nan, dtype=float)
        perdas_fold: list[float] = []
        for treino, validacao in folds:
            modelo = criar_modelo("logistica").set_params(modelo__C=c)
            modelo, _ = ajustar_modelo(modelo, x.iloc[treino], t_arr[treino])
            oof[validacao] = predizer(modelo, x.iloc[validacao])
            perdas_fold.append(float(log_loss(t_arr[validacao], oof[validacao], labels=[0, 1])))
        if not np.isfinite(oof).all():
            raise RuntimeError("Predições OOF incompletas.")
        se = float(np.std(perdas_fold, ddof=1) / sqrt(len(perdas_fold))) if len(perdas_fold) > 1 else 0.0
        resultados.append({
            "C": c,
            **metricas_probabilidade(t_arr, oof),
            "log_loss_se_folds": se,
            **diagnosticos_propensity(x, t_arr, oof),
        })

    return {
        "resultados": resultados,
        "auditoria": {
            "n": int(len(x)),
            "n_folds": int(n_folds),
            "seed": int(seed),
            "folds": auditoria_folds,
            "cobertura_min": int(cobertura.min()),
            "cobertura_max": int(cobertura.max()),
            "usa_outcome": False,
            "criterio_primario": "log_loss OOF",
        },
    }


def _normalizar_chave(chave: str) -> str:
    texto = unicodedata.normalize("NFKD", str(chave)).encode("ascii", "ignore").decode().lower()
    return texto.replace("-", "_").replace(" ", "_")


def selecionar_candidato_propensity(
    resultados: list[dict[str, float]],
    *,
    baseline_c: float = BASELINE_C,
    max_smd: float = 0.10,
    min_ess_ratio: float = 0.20,
    max_fracao_cauda: float = 0.10,
) -> dict[str, object]:
    """Aplica regra baseline-first de 1 EP e guardrails pré-especificados."""
    if not resultados:
        raise ValueError("resultados não pode ser vazio.")
    for resultado in resultados:
        proibidas = [
            chave for chave in resultado
            if any(termo in _normalizar_chave(chave) for termo in _CHAVES_CAUSAIS_PROIBIDAS)
        ]
        if proibidas:
            raise ValueError(f"Métrica causal proibida na seleção de nuisance model: {proibidas}")

    obrigatorias = {
        "C", "log_loss", "log_loss_se_folds", "brier", "erro_calibracao_medio",
        "max_abs_smd_ponderado", "ess_t0_sobre_n", "ess_t1_sobre_n",
        "fora_005_095_fracao",
    }
    for resultado in resultados:
        faltantes = obrigatorias - set(resultado)
        if faltantes:
            raise ValueError(f"Métricas obrigatórias ausentes: {sorted(faltantes)}")

    melhor = min(resultados, key=lambda r: float(r["log_loss"]))
    limite_um_ep = float(melhor["log_loss"]) + float(melhor["log_loss_se_folds"])

    def aprovado(r: dict[str, float]) -> bool:
        return (
            float(r["log_loss"]) <= limite_um_ep
            and float(r["max_abs_smd_ponderado"]) <= max_smd
            and min(float(r["ess_t0_sobre_n"]), float(r["ess_t1_sobre_n"])) >= min_ess_ratio
            and float(r["fora_005_095_fracao"]) <= max_fracao_cauda
        )

    elegiveis = [r for r in resultados if aprovado(r)]
    if not elegiveis:
        raise ValueError("Nenhum candidato passou a regra de 1 EP e os guardrails de overlap/balanço.")
    baseline = next((r for r in elegiveis if np.isclose(float(r["C"]), baseline_c)), None)
    if baseline is not None:
        escolhido = baseline
        criterio = "baseline-first dentro de 1 EP e guardrails"
    else:
        escolhido = min(
            elegiveis,
            key=lambda r: (
                float(r["log_loss"]), float(r["brier"]),
                float(r["erro_calibracao_medio"]), float(r["max_abs_smd_ponderado"]),
                -min(float(r["ess_t0_sobre_n"]), float(r["ess_t1_sobre_n"])),
                abs(np.log10(float(r["C"]))),
            ),
        )
        criterio = "melhor log_loss OOF entre candidatos dentro de 1 EP e guardrails"
    return {
        "C_escolhido": float(escolhido["C"]),
        "baseline_preservado": bool(np.isclose(float(escolhido["C"]), baseline_c)),
        "criterio": criterio,
        "melhor_log_loss": float(melhor["log_loss"]),
        "limite_um_ep": limite_um_ep,
        "guardrails": {
            "max_abs_smd_ponderado": max_smd,
            "min_ess_ratio_por_braco": min_ess_ratio,
            "max_fracao_fora_005_095": max_fracao_cauda,
        },
    }


def executar_selecao_nested_propensity(
    x: pd.DataFrame,
    t,
    *,
    candidatos: tuple[float, ...] = GRADE_C_PROPENSITY,
    n_folds_externos: int = 3,
    n_folds_internos: int = 3,
    seed: int = SEED,
) -> dict[str, object]:
    """Executa selecao nested do propensity sem outcome nem acesso cruzado entre folds."""
    validar_x(x)
    t_arr = _vetor_binario(t, "t")
    if len(x) != len(t_arr):
        raise ValueError("x e t devem ter o mesmo numero de observacoes.")
    grade = tuple(float(c) for c in candidatos)
    if not grade or any((not np.isfinite(c)) or c <= 0 for c in grade):
        raise ValueError("Todos os candidatos C devem ser positivos e finitos.")

    splitter_externo = StratifiedKFold(
        n_splits=int(n_folds_externos), shuffle=True, random_state=int(seed)
    )
    folds_externos = list(splitter_externo.split(x, t_arr))
    oof_externo = np.full(len(x), np.nan, dtype=float)
    fold_externo_id = np.zeros(len(x), dtype=np.int16)
    cobertura = np.zeros(len(x), dtype=np.int8)
    resultados_folds: list[dict[str, object]] = []
    resultados_candidatos: list[dict[str, object]] = []
    total_fits_realizados = 0
    inicio_total = perf_counter()

    for fold, (indices_treino, indices_validacao) in enumerate(folds_externos, start=1):
        print(
            f"Nested propensity outer fold {fold}/{n_folds_externos}: tuning interno",
            flush=True,
        )
        x_treino = x.iloc[indices_treino]
        t_treino = t_arr[indices_treino]

        inicio_tuning = perf_counter()
        avaliacao = avaliar_grade_propensity(
            x_treino,
            t_treino,
            candidatos=grade,
            n_folds=int(n_folds_internos),
            seed=int(seed),
        )
        tempo_tuning = perf_counter() - inicio_tuning
        total_fits_realizados += len(grade) * int(n_folds_internos)

        escolha = selecionar_candidato_propensity(avaliacao["resultados"])
        melhor = min(avaliacao["resultados"], key=lambda r: float(r["log_loss"]))
        limite = float(escolha["limite_um_ep"])
        for candidato in avaliacao["resultados"]:
            passa_guardrails = (
                float(candidato["max_abs_smd_ponderado"]) <= 0.10
                and min(
                    float(candidato["ess_t0_sobre_n"]),
                    float(candidato["ess_t1_sobre_n"]),
                ) >= 0.20
                and float(candidato["fora_005_095_fracao"]) <= 0.10
            )
            resultados_candidatos.append(
                {
                    "outer_fold": fold,
                    **candidato,
                    "dentro_um_ep": bool(float(candidato["log_loss"]) <= limite),
                    "passa_guardrails": bool(passa_guardrails),
                    "elegivel_regra_final": bool(
                        float(candidato["log_loss"]) <= limite and passa_guardrails
                    ),
                    "selecionado": bool(
                        np.isclose(float(candidato["C"]), float(escolha["C_escolhido"]))
                    ),
                }
            )

        inicio_refit = perf_counter()
        modelo = criar_modelo("logistica").set_params(
            modelo__C=float(escolha["C_escolhido"])
        )
        modelo, ajuste = ajustar_modelo(modelo, x_treino, t_treino)
        predicoes_fold = predizer(modelo, x.iloc[indices_validacao])
        tempo_refit = perf_counter() - inicio_refit
        total_fits_realizados += 1

        oof_externo[indices_validacao] = predicoes_fold
        fold_externo_id[indices_validacao] = fold
        cobertura[indices_validacao] += 1
        metricas_externas = metricas_probabilidade(t_arr[indices_validacao], predicoes_fold)
        diagnosticos_externos = diagnosticos_propensity(
            x.iloc[indices_validacao], t_arr[indices_validacao], predicoes_fold
        )
        resultados_folds.append(
            {
                "outer_fold": fold,
                "n_treino": int(len(indices_treino)),
                "n_validacao": int(len(indices_validacao)),
                "n_treino_t0": int(np.sum(t_treino == 0)),
                "n_treino_t1": int(np.sum(t_treino == 1)),
                "n_validacao_t0": int(np.sum(t_arr[indices_validacao] == 0)),
                "n_validacao_t1": int(np.sum(t_arr[indices_validacao] == 1)),
                "hash_treino": _hash_indices(indices_treino),
                "hash_validacao": _hash_indices(indices_validacao),
                "C_menor_log_loss_interno": float(melhor["C"]),
                "C_escolhido": float(escolha["C_escolhido"]),
                "baseline_preservado": bool(escolha["baseline_preservado"]),
                "limite_um_ep": limite,
                "criterio": str(escolha["criterio"]),
                "tempo_tuning_segundos": float(tempo_tuning),
                "tempo_refit_segundos": float(tempo_refit),
                "n_tuning_fits": len(grade) * int(n_folds_internos),
                "n_refits": 1,
                "n_validacao_usado_na_selecao": 0,
                "ajuste_refit": ajuste,
                "auditoria_inner": avaliacao["auditoria"],
                **{f"externo_{chave}": valor for chave, valor in metricas_externas.items()},
                **{f"externo_{chave}": valor for chave, valor in diagnosticos_externos.items()},
            }
        )
        print(
            f"Nested propensity outer fold {fold}/{n_folds_externos}: "
            f"C={float(escolha['C_escolhido']):g}, concluido",
            flush=True,
        )

    if not np.all(cobertura == 1) or not np.isfinite(oof_externo).all():
        raise RuntimeError("Predicoes OOF externas incompletas ou com cobertura diferente de um.")

    total_fits_previstos = int(n_folds_externos) * (
        len(grade) * int(n_folds_internos) + 1
    )
    return {
        "oof_externo": oof_externo,
        "fold_externo_id": fold_externo_id,
        "folds": resultados_folds,
        "candidatos": resultados_candidatos,
        "metricas_oof": {
            **metricas_probabilidade(t_arr, oof_externo),
            **diagnosticos_propensity(x, t_arr, oof_externo),
        },
        "auditoria": {
            "n": int(len(x)),
            "features": list(x.columns),
            "seed": int(seed),
            "n_folds_externos": int(n_folds_externos),
            "n_folds_internos": int(n_folds_internos),
            "n_candidatos": len(grade),
            "candidatos": list(grade),
            "n_refits": int(n_folds_externos),
            "total_fits_previstos": total_fits_previstos,
            "total_fits_realizados": total_fits_realizados,
            "cobertura_min": int(cobertura.min()),
            "cobertura_max": int(cobertura.max()),
            "usa_outcome": False,
            "criterio_primario": "log_loss OOF interno",
            "tempo_total_segundos": float(perf_counter() - inicio_total),
        },
    }


def _decisao_nested(folds: list[dict[str, object]]) -> str:
    escolhidos = [float(fold["C_escolhido"]) for fold in folds]
    if escolhidos and all(np.isclose(c, BASELINE_C) for c in escolhidos):
        return "BASELINE_C1_PRESERVADO"
    if escolhidos and all(np.isclose(c, escolhidos[0]) for c in escolhidos):
        return "SENSIBILIDADE_PROPENSITY_ALTERNATIVA_SELECIONADA"
    return "SELECAO_PROPENSITY_INSTAVEL"


def salvar_resultado_nested_propensity(
    resultado: dict[str, object],
    *,
    pasta_outputs: str | Path,
    caminho_cache: str | Path,
    contexto: dict[str, object],
    baseline_metricas: dict[str, float],
) -> dict[str, str]:
    """Salva tabelas pequenas de auditoria e mantem o vetor OOF fora do Git."""
    pasta = Path(pasta_outputs)
    cache = Path(caminho_cache)
    pasta.mkdir(parents=True, exist_ok=True)
    cache.parent.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        cache,
        propensity_oof=np.asarray(resultado["oof_externo"], dtype=float),
        fold_externo_id=np.asarray(resultado["fold_externo_id"], dtype=np.int16),
    )

    folds_csv = pasta / "nested_propensity_2024_folds.csv"
    candidatos_csv = pasta / "nested_propensity_2024_candidatos.csv"
    resumo_json = pasta / "nested_propensity_2024_resumo.json"

    folds_planos = []
    for fold in resultado["folds"]:
        linha = {
            chave: valor
            for chave, valor in fold.items()
            if not isinstance(valor, (dict, list, tuple))
        }
        linha["ajuste_refit"] = json.dumps(fold["ajuste_refit"], ensure_ascii=False)
        linha["auditoria_inner"] = json.dumps(fold["auditoria_inner"], ensure_ascii=False)
        folds_planos.append(linha)
    pd.DataFrame(folds_planos).to_csv(folds_csv, index=False, encoding="utf-8")
    pd.DataFrame(resultado["candidatos"]).to_csv(
        candidatos_csv, index=False, encoding="utf-8"
    )

    metricas_oof = resultado["metricas_oof"]
    diferencas = {
        chave: float(metricas_oof[chave]) - float(baseline_metricas[chave])
        for chave in metricas_oof
        if chave in baseline_metricas
    }
    resumo = {
        "status": "NESTED_PROPENSITY_2024_CONCLUIDO",
        "contexto": contexto,
        "auditoria": resultado["auditoria"],
        "folds": resultado["folds"],
        "metricas_oof_nested": metricas_oof,
        "baseline_c1_certificado": baseline_metricas,
        "diferenca_nested_menos_baseline_c1": diferencas,
        "decisao_propensity": _decisao_nested(resultado["folds"]),
        "cache_oof": {
            "caminho": cache.as_posix(),
            "sha256": sha256(cache.read_bytes()).hexdigest(),
            "bytes": cache.stat().st_size,
            "versionado": False,
        },
        "restricoes": {
            "usa_outcome": False,
            "estima_efeito_causal": False,
            "sobrescreve_cache_historico": False,
        },
    }
    resumo_json.write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "resumo": str(resumo_json),
        "folds": str(folds_csv),
        "candidatos": str(candidatos_csv),
        "cache_oof": str(cache),
    }
