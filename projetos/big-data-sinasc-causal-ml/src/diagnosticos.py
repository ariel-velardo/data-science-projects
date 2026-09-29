"""Covariáveis, balanceamento e suporte."""
from __future__ import annotations

from collections.abc import Sequence
import numpy as np
import pandas as pd
from typing import Any
import warnings

COLUNAS_PROPENSITY_PRINCIPAL = (
    "IDADEMAE_NUM",
    "ESCOLARIDADE_MAE",
    "RACA_COR_MAE",
    "SITUACAO_CONJUGAL",
    "PARIDADE_CAT",
    "PERDAS_FETAIS_CAT",
    "UF_RESIDENCIA",
)

VARIAVEIS_PROIBIDAS_PROPENSITY = frozenset(
    {
        "PESO",
        "Y_BAIXO_PESO",
        "Y_BAIXO_PESO_P0",
        "GESTACAO",
        "SEMAGESTAC",
        "CONSPRENAT",
        "CONSULTAS",
        "PARTO",
        "APGAR1",
        "APGAR5",
        "KOTELCHUCK",
        "TPAPRESENT",
        "STTRABPART",
        "STCESPARTO",
        "TPROBSON",
        "IDANOMAL",
        "CODANOMAL",
        "LOCNASC",
        "CODESTAB",
        "TPNASCASSI",
        "DTNASC",
        "HORANASC",
        "RACACOR",
        "SEXO",
        "TPMETESTIM",
    }
)

def validar_colunas_propensity(colunas: Sequence[str]) -> None:
    """Falha se outcome, mediadores ou variáveis posteriores entrarem em X."""

    normalizadas = {str(coluna).upper() for coluna in colunas}
    proibidas = sorted(normalizadas & VARIAVEIS_PROIBIDAS_PROPENSITY)
    if proibidas:
        raise ValueError(
            "Variáveis proibidas no propensity por leakage/pós-tratamento: "
            + ", ".join(proibidas)
        )

def _smd_numerico(tratados: pd.Series, controles: pd.Series) -> float:
    media_t = tratados.mean()
    media_c = controles.mean()
    variancia_pooled = (tratados.var(ddof=1) + controles.var(ddof=1)) / 2
    if pd.isna(variancia_pooled) or variancia_pooled == 0:
        return 0.0 if media_t == media_c else float("inf")
    return float((media_t - media_c) / np.sqrt(variancia_pooled))

def _smd_categorico(tratados: pd.Series, controles: pd.Series) -> float:
    categorias = sorted(set(tratados.dropna().astype(str)) | set(controles.dropna().astype(str)))
    maior = 0.0
    for categoria in categorias:
        p_t = tratados.astype("string").eq(categoria).mean()
        p_c = controles.astype("string").eq(categoria).mean()
        variancia_pooled = (p_t * (1 - p_t) + p_c * (1 - p_c)) / 2
        if variancia_pooled == 0:
            smd = 0.0 if p_t == p_c else float("inf")
        else:
            smd = float((p_t - p_c) / np.sqrt(variancia_pooled))
        maior = max(maior, abs(smd))
    return maior

def calcular_smd(
    dados: pd.DataFrame,
    tratamento: str,
    numericas: Sequence[str],
    categoricas: Sequence[str],
) -> pd.DataFrame:
    """Calcula SMD absoluto; para categóricas, retorna o pior nível observado."""

    linhas: list[dict[str, float | str]] = []
    grupo_t = dados.loc[dados[tratamento].eq(1)]
    grupo_c = dados.loc[dados[tratamento].eq(0)]
    if grupo_t.empty or grupo_c.empty:
        raise ValueError("SMD requer observações em T=1 e T=0.")

    for coluna in numericas:
        t = pd.to_numeric(grupo_t[coluna], errors="coerce").dropna()
        c = pd.to_numeric(grupo_c[coluna], errors="coerce").dropna()
        smd = _smd_numerico(t, c)
        linhas.append(
            {
                "variavel": coluna,
                "tipo": "numerica",
                "media_t1": float(t.mean()),
                "media_t0": float(c.mean()),
                "smd": smd,
                "smd_abs": abs(smd),
            }
        )

    for coluna in categoricas:
        t = grupo_t[coluna].fillna("IGNORADO")
        c = grupo_c[coluna].fillna("IGNORADO")
        smd_abs = _smd_categorico(t, c)
        linhas.append(
            {
                "variavel": coluna,
                "tipo": "categorica_max_nivel",
                "media_t1": np.nan,
                "media_t0": np.nan,
                "smd": smd_abs,
                "smd_abs": smd_abs,
            }
        )
    return pd.DataFrame(linhas).sort_values("smd_abs", ascending=False).reset_index(drop=True)


def diagnosticar_trimming(
    propensity: Sequence[float], tratamento: Sequence[int]
) -> pd.DataFrame:
    """Quantifica perdas sob regras candidatas sem aplicar trimming definitivo."""

    escore = np.asarray(propensity, dtype=float)
    t = np.asarray(tratamento, dtype=int)
    if len(escore) != len(t):
        raise ValueError("propensity e tratamento devem ter o mesmo tamanho.")
    if np.isnan(escore).any() or ((escore < 0) | (escore > 1)).any():
        raise ValueError("propensity deve conter probabilidades válidas entre 0 e 1.")

    regras = (
        ("sem_trimming", 0.0, 1.0),
        ("0.01_0.99", 0.01, 0.99),
        ("0.05_0.95", 0.05, 0.95),
    )
    linhas = []
    for nome, inferior, superior in regras:
        manter = (escore >= inferior) & (escore <= superior)
        linhas.append(
            {
                "regra": nome,
                "limite_inferior": inferior,
                "limite_superior": superior,
                "n_total": len(escore),
                "n_mantido": int(manter.sum()),
                "n_excluido": int((~manter).sum()),
                "n_tratado_mantido": int((manter & (t == 1)).sum()),
                "n_controle_mantido": int((manter & (t == 0)).sum()),
                "n_tratado_excluido": int(((~manter) & (t == 1)).sum()),
                "n_controle_excluido": int(((~manter) & (t == 0)).sum()),
            }
        )
    return pd.DataFrame(linhas)

def resumir_overlap(
    propensity: Sequence[float], tratamento: Sequence[int]
) -> dict[str, Any]:
    """Resume extremos, percentis, suporte observado e trimming candidato."""

    escore = np.asarray(propensity, dtype=float)
    t = np.asarray(tratamento, dtype=int)
    percentis = [0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1]
    grupos: dict[str, Any] = {}
    for valor, nome in ((0, "controle"), (1, "tratado")):
        grupo = escore[t == valor]
        grupos[nome] = {
            "n": int(len(grupo)),
            "min": float(np.min(grupo)),
            "max": float(np.max(grupo)),
            "percentis": {
                f"p{int(p * 100):02d}": float(np.quantile(grupo, p)) for p in percentis
            },
            "prop_abaixo_0_01": float(np.mean(grupo < 0.01)),
            "prop_acima_0_99": float(np.mean(grupo > 0.99)),
            "prop_abaixo_0_05": float(np.mean(grupo < 0.05)),
            "prop_acima_0_95": float(np.mean(grupo > 0.95)),
        }
    suporte_inferior = max(grupos["controle"]["min"], grupos["tratado"]["min"])
    suporte_superior = min(grupos["controle"]["max"], grupos["tratado"]["max"])
    return {
        "grupos": grupos,
        "suporte_comum_observado": {
            "inferior": suporte_inferior,
            "superior": suporte_superior,
        },
        "trimming_diagnostico": diagnosticar_trimming(escore, t).to_dict("records"),
    }

def construir_pipeline_propensity(
    colunas_numericas: Sequence[str], colunas_categoricas: Sequence[str]
):
    """Monta regressão logística L2 sparse; importa sklearn somente quando usada."""

    colunas = [*colunas_numericas, *colunas_categoricas]
    validar_colunas_propensity(colunas)
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
    except ModuleNotFoundError as erro:
        raise RuntimeError(
            "scikit-learn não está instalado na .venv do projeto; "
            "instale a dependência declarada em requirements.txt."
        ) from erro

    numerico = Pipeline(
        [
            ("imputa", SimpleImputer(strategy="median", add_indicator=True)),
            ("padroniza", StandardScaler()),
        ]
    )
    categorico = Pipeline(
        [
            ("imputa", SimpleImputer(strategy="most_frequent")),
            (
                "one_hot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=True),
            ),
        ]
    )
    preprocessador = ColumnTransformer(
        [
            ("numericas", numerico, list(colunas_numericas)),
            ("categoricas", categorico, list(colunas_categoricas)),
        ],
        sparse_threshold=1.0,
    )
    return Pipeline(
        [
            ("preprocessamento", preprocessador),
            (
                "modelo",
                LogisticRegression(
                    C=1.0,
                    solver="lbfgs",
                    max_iter=500,
                    tol=1e-5,
                    random_state=20240925,
                ),
            ),
        ]
    )

def estimar_propensity_oof(
    x: pd.DataFrame,
    tratamento: pd.Series,
    colunas_numericas: Sequence[str],
    colunas_categoricas: Sequence[str],
    n_folds: int = 5,
) -> tuple[np.ndarray, dict[str, float | int]]:
    """Gera probabilidades out-of-fold estratificadas sem usar o outcome."""

    try:
        from sklearn.base import clone
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import StratifiedKFold
    except ModuleNotFoundError as erro:
        raise RuntimeError(
            "scikit-learn não está instalado na .venv do projeto."
        ) from erro

    pipeline = construir_pipeline_propensity(colunas_numericas, colunas_categoricas)
    validar_colunas_propensity(x.columns)
    if set(x.columns) != set(colunas_numericas) | set(colunas_categoricas):
        raise ValueError("X deve conter exatamente as covariáveis declaradas.")
    t = tratamento.astype(int).to_numpy()
    if set(np.unique(t)) != {0, 1}:
        raise ValueError("Propensity requer ambos os grupos de tratamento.")
    oof = np.empty(len(x), dtype=float)
    cobertura = np.zeros(len(x), dtype=int)
    convergencia = []
    folds = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=20240925)
    from sklearn.exceptions import ConvergenceWarning
    for fold, (treino, validacao) in enumerate(folds.split(x, t), 1):
        modelo = clone(pipeline)
        with warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter("always", ConvergenceWarning)
            modelo.fit(x.iloc[treino], t[treino])
        falhou = any(issubclass(a.category, ConvergenceWarning) for a in avisos)
        if falhou:
            raise RuntimeError(f"Propensity não convergiu no fold {fold}; rever max_iter.")
        convergencia.append({"fold": fold, "n_iter": int(modelo['modelo'].n_iter_.max()), "convergiu": True})
        print(f"Propensity fold {fold}/{n_folds}: convergiu", flush=True)
        oof[validacao] = modelo.predict_proba(x.iloc[validacao])[:, 1]
        cobertura[validacao] += 1
    if not np.all(cobertura == 1) or not np.all(np.isfinite(oof)):
        raise ValueError("Predições OOF inválidas ou cobertura incompleta.")
    return oof, {"n_folds": n_folds, "auc_oof": float(roc_auc_score(t, oof)), "convergencia": convergencia, "solver": "lbfgs", "max_iter": 500, "tol": 1e-5}
