"""Regressão logística do desfecho (notebook 06): preditores, previsão fora da amostra e OR ajustadas.

Modela P(Y=1 | X1, X), diferente do escore de propensão do notebook 03, que modela P(T=1 | X). Mede
capacidade preditiva e associação condicional; nenhuma das duas identifica efeito causal.
"""
from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.diagnosticos import validar_colunas_propensity

SEMENTE = 20240925
Z95 = 1.959963984540054
X1 = "X1_INICIO_1_3"
NUMERICAS = ("IDADEMAE_NUM", "IDADEMAE_QUAD")
# Níveis declarados sobre a codificação de src.amostra._criar_views; o primeiro de cada tupla é a referência.
# Regra estrutural, fixada antes do ajuste e sem olhar a associação com o desfecho: níveis com menos de 100
# nascimentos na P6 são agregados ("sem escolaridade" com "fundamental I"; "ignorado" na categoria modal, que é a
# referência), para que a logística sem penalização tenha estimativas finitas em todas as dobras.
CATEGORIAS = {
    "ESCOLARIDADE_MAE": (("3", "0-1", "2", "4", "5"), {"0": "0-1", "1": "0-1", "IGNORADO": "3"}),
    "RACA_COR_MAE": (("1", "2", "3", "4", "5"), {"IGNORADO": "1"}),
    "PARIDADE_CAT": (("0", "1"), {}),
    "PERDAS_FETAIS_CAT": (("0", "1", "2_OU_MAIS"), {"IGNORADO": "0"}),
}
PREDITORES_M3 = (X1, *NUMERICAS, *CATEGORIAS)
MODELOS = {
    "M0": (),
    "M1": (X1,),
    "M3": PREDITORES_M3,
    "M3 sem X1": tuple(p for p in PREDITORES_M3 if p != X1),
}
# Nomes de apresentação (tabelas, legendas e textos); as chaves internas acima ficam só na implementação.
ROTULOS_MODELOS = {
    "M0": "Modelo de referência (prevalência)",
    "M1": "Modelo com início do pré-natal",
    "M3": "Regressão logística ajustada (pré-natal e características maternas)",
    "M3 sem X1": "Modelo ajustado apenas com características maternas",
}
ROTULOS_AMOSTRAS = {"P6": "amostra principal (início nos meses 1–6)",
                    "P9": "amostra de sensibilidade (início nos meses 1–9)"}


_AVISO_C_INFINITO = "Setting penalty=None will ignore the C and l1_ratio parameters"


@contextmanager
def _ajuste_sem_penalizacao():
    """Aviso de convergência vira erro; ignora só o aviso espúrio do scikit-learn 1.8.0 para ``C=np.inf``.

    Em ``sklearn/linear_model/_logistic.py`` (1.8.0), ``C=np.inf`` define ``penalty=None`` e, em seguida, avisa que
    C será ignorado; o ajuste segue sem penalização, como diz a docstring ("C=np.inf results in unpenalized
    logistic regression").
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        warnings.filterwarnings("ignore", message=_AVISO_C_INFINITO, category=UserWarning)
        yield


def ajustar_modelo(modelo, x: pd.DataFrame, y: np.ndarray):
    """Ajusta o modelo na amostra inteira com as mesmas regras de aviso da validação cruzada."""
    with _ajuste_sem_penalizacao():
        return modelo.fit(x, y)


def definir_desfechos(peso: pd.Series) -> pd.DataFrame:
    """Y_2500 = peso < 2.500 g (desfecho do estudo, critério da OMS); Y_2600 = peso < 2.600 g (sensibilidade do corte)."""
    peso = pd.Series(peso, dtype=float)
    if peso.isna().any() or not peso.between(500, 6000).all():
        raise ValueError("Peso nulo ou fora de 500–6.000 g: fora da elegibilidade do estudo.")
    return pd.DataFrame({"Y_2500": (peso < 2500).astype(int), "Y_2600": (peso < 2600).astype(int)})


def validar_preditores(colunas: Sequence[str]) -> None:
    """Lista de permissão: só X1 e as covariáveis anteriores à gestação do escore do 03 podem entrar."""
    validar_colunas_propensity(colunas)
    extras = sorted(set(colunas) - set(PREDITORES_M3))
    if extras:
        raise ValueError("Preditores fora da lista de permissão (vazamento ou variável não justificada): "
                         + ", ".join(extras))


def codificar_preditores(dados: pd.DataFrame) -> pd.DataFrame:
    """X1, idade, idade² e categorias agregadas pela regra estrutural; falha com nível não declarado."""
    x = pd.DataFrame(index=dados.index)
    x[X1] = dados[X1].astype(int)
    x["IDADEMAE_NUM"] = dados.IDADEMAE_NUM.astype(float)
    x["IDADEMAE_QUAD"] = x.IDADEMAE_NUM ** 2
    if not x[X1].isin([0, 1]).all() or x.IDADEMAE_NUM.isna().any():
        raise ValueError("X1 deve ser 0/1 e a idade não pode ser nula.")
    for coluna, (niveis, agregacao) in CATEGORIAS.items():
        valores = dados[coluna].astype(str).replace(agregacao)
        novos = sorted(set(valores) - set(niveis))
        if novos:
            raise ValueError(f"{coluna}: nível não declarado {novos}.")
        x[coluna] = valores.astype(object)
    return x[list(PREDITORES_M3)]


def construir_modelo(preditores: Sequence[str]):
    """M0 = prevalência do treino; demais: logística sem penalização (C=np.inf no scikit-learn 1.8)."""
    validar_preditores(preditores)
    if not preditores:
        return DummyClassifier(strategy="prior")
    partes = []
    numericas = [p for p in preditores if p in NUMERICAS]
    categoricas = [p for p in preditores if p in CATEGORIAS]
    if numericas:
        partes.append(("numericas", StandardScaler(), numericas))
    if X1 in preditores:
        partes.append(("x1", "passthrough", [X1]))
    if categoricas:
        partes.append(("categoricas", OneHotEncoder(
            categories=[list(CATEGORIAS[c][0]) for c in categoricas],
            drop=[CATEGORIAS[c][0][0] for c in categoricas],
            handle_unknown="error", sparse_output=False), categoricas))
    return Pipeline([
        ("preprocessamento", ColumnTransformer(partes, remainder="drop", verbose_feature_names_out=False)),
        ("modelo", LogisticRegression(C=np.inf, solver="newton-cholesky", max_iter=100, tol=1e-10)),
    ])


def prever_fora_da_amostra(modelo, x: pd.DataFrame, y: np.ndarray, n_dobras: int = 5,
                           semente: int = SEMENTE) -> tuple[np.ndarray, np.ndarray]:
    """Probabilidade fora da amostra por validação cruzada estratificada; devolve também a dobra de cada linha.

    ``cross_val_predict`` clona e ajusta o pipeline inteiro (padronização, codificação e modelo) só no treino de
    cada dobra. Aviso de convergência vira erro.
    """
    y = np.asarray(y)
    dobras = list(StratifiedKFold(n_dobras, shuffle=True, random_state=semente).split(x, y))
    with _ajuste_sem_penalizacao():
        p = cross_val_predict(modelo, x, y, cv=dobras, method="predict_proba")[:, 1]
    dobra = np.empty(len(y), dtype=int)
    for k, (_, teste) in enumerate(dobras):
        dobra[teste] = k
    return p, dobra


def _inclinacao_calibracao(y: np.ndarray, p: np.ndarray) -> float:
    """Coeficiente da logística de Y em logit(p); NaN se a estimativa não existe ou não tem sentido.

    Previsões quase constantes (amplitude do logit < 1e-3, como o M0 na validação cruzada, que prevê a
    prevalência de cada dobra de treino) não permitem estimar inclinação.
    """
    escore = logit(np.clip(p, 1e-12, 1 - 1e-12)).reshape(-1, 1)
    if np.ptp(escore) < 1e-3:
        return float("nan")
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        warnings.filterwarnings("ignore", message=_AVISO_C_INFINITO, category=UserWarning)
        ajuste = LogisticRegression(C=np.inf, solver="newton-cholesky", tol=1e-10).fit(escore, y)
    if any(issubclass(a.category, (ConvergenceWarning, RuntimeWarning)) for a in avisos):
        return float("nan")
    return float(ajuste.coef_[0, 0])


def metricas_probabilisticas(y: np.ndarray, p: np.ndarray) -> dict:
    """ROC-AUC, average precision (referência = prevalência), Brier e calibração (média e inclinação)."""
    y, p = np.asarray(y), np.asarray(p, dtype=float)
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Probabilidades inválidas.")
    return {"prevalencia": float(y.mean()), "roc_auc": float(roc_auc_score(y, p)),
            "average_precision": float(average_precision_score(y, p)), "brier": float(brier_score_loss(y, p)),
            "dif_media_prevista_observada": float(p.mean() - y.mean()),
            "inclinacao_calibracao": _inclinacao_calibracao(y, p)}


def curva_calibracao(y: np.ndarray, p: np.ndarray, grupos: int = 10) -> pd.DataFrame:
    """Risco previsto médio e proporção observada por grupos de risco previsto, com IC 95% de Wilson."""
    p = np.asarray(p, dtype=float)
    grupo = pd.qcut(pd.Series(p).rank(method="first"), grupos, labels=False)
    curva = pd.DataFrame({"g": grupo, "y": np.asarray(y), "p": p}).groupby("g").agg(
        n=("y", "size"), previsto=("p", "mean"), observado=("y", "mean"))
    n, obs = curva.n, curva.observado
    centro = (obs + Z95 ** 2 / (2 * n)) / (1 + Z95 ** 2 / n)
    meia = Z95 * np.sqrt(obs * (1 - obs) / n + Z95 ** 2 / (4 * n ** 2)) / (1 + Z95 ** 2 / n)
    return curva.assign(ic95_inf=centro - meia, ic95_sup=centro + meia)


def razoes_de_chances(modelo: Pipeline, x: pd.DataFrame, y: np.ndarray) -> tuple[pd.DataFrame, dict]:
    """OR ajustadas com IC 95% de Wald pela informação observada, e diagnóstico numérico do ajuste.

    Os termos de idade (padronizados, com quadrado) ficam fora da tabela: não têm uma OR única.
    O diagnóstico traz o maior |gradiente| por observação (≈ 0 no máximo de verossimilhança) e o
    número de condição da matriz de informação.
    """
    y = np.asarray(y, dtype=float)
    desenho = np.asarray(modelo[:-1].transform(x), dtype=float)
    nomes = list(modelo[:-1].get_feature_names_out())
    regressao = modelo[-1]
    matriz = np.column_stack([np.ones(len(y)), desenho])
    beta = np.r_[regressao.intercept_, regressao.coef_.ravel()]
    p = expit(matriz @ beta)
    informacao = (matriz * (p * (1 - p))[:, None]).T @ matriz
    ep = np.sqrt(np.diag(np.linalg.inv(informacao)))
    tabela = pd.DataFrame({"coef": beta[1:], "ep": ep[1:]}, index=nomes).drop(index=list(NUMERICAS), errors="ignore")
    tabela["or"] = np.exp(tabela.coef)
    tabela["ic95_inf"] = np.exp(tabela.coef - Z95 * tabela.ep)
    tabela["ic95_sup"] = np.exp(tabela.coef + Z95 * tabela.ep)
    diagnostico = {"gradiente_max": float(np.abs(matriz.T @ (y - p)).max() / len(y)),
                   "condicao": float(np.linalg.cond(informacao)),
                   "iteracoes": int(np.max(regressao.n_iter_))}
    return tabela, diagnostico


# ------------------------------------------------------------------ equação e dicionário do M3

# Rótulos dos níveis depois da agregação de CATEGORIAS; a referência é o primeiro nível de cada tupla.
ROTULOS_NIVEIS = {
    "ESCOLARIDADE_MAE": {"3": "médio", "0-1": "nenhuma ou fundamental I", "2": "fundamental II",
                         "4": "superior incompleto", "5": "superior completo"},
    "RACA_COR_MAE": {"1": "branca", "2": "preta", "3": "amarela", "4": "parda", "5": "indígena"},
    "PARIDADE_CAT": {"0": "nulípara", "1": "multípara"},
    "PERDAS_FETAIS_CAT": {"0": "nenhuma", "1": "uma", "2_OU_MAIS": "duas ou mais"},
}

# Dicionário das variáveis do M3: origem no SINASC, nome no modelo, codificação, referência e ignorados.
DICIONARIO_M3 = (
    {"sinasc": "PESO", "modelo": "Y_2500 / Y_2600", "significado": "Peso ao nascer (g); define os desfechos",
     "tipo": "desfecho binário", "codificacao": "Y_2500 = 1 se PESO < 2.500 g; Y_2600 = 1 se PESO < 2.600 g; 0 caso contrário",
     "referencia": "Y = 0", "ignorados": "Fora da população: só entram pesos de 500 a 6.000 g"},
    {"sinasc": "MESPRENAT", "modelo": X1, "significado": "Mês de gestação no início do pré-natal",
     "tipo": "exposição binária", "codificacao": "1 = meses 1–3; 0 = meses 4–6 (amostra principal)", "referencia": "meses 4–6 (X1 = 0)",
     "ignorados": "Vazio ou 99: fora da população (993 registros)"},
    {"sinasc": "IDADEMAE", "modelo": "IDADEMAE_NUM, IDADEMAE_QUAD", "significado": "Idade da mãe (anos)",
     "tipo": "numérica", "codificacao": "idade e idade², cada termo padronizado: (valor − média)/DP da amostra de ajuste",
     "referencia": "—", "ignorados": "Nenhum na amostra principal (idade fora de 10–59 viraria nulo e o modelo falharia)"},
    {"sinasc": "ESCMAE2010", "modelo": "ESCOLARIDADE_MAE", "significado": "Escolaridade da mãe (categorias de 2010)",
     "tipo": "categórica ordinal", "codificacao": "4 indicadores 0/1: nenhuma ou fund. I (0 e 1 agregados), fund. II, "
     "superior incompleto, superior completo", "referencia": "médio (3)", "ignorados": "Código 9 ou vazio → médio (moda)"},
    {"sinasc": "RACACORMAE", "modelo": "RACA_COR_MAE", "significado": "Raça/cor da mãe", "tipo": "categórica nominal",
     "codificacao": "4 indicadores 0/1: preta, amarela, parda, indígena", "referencia": "branca (1)",
     "ignorados": "Código 9 ou vazio → branca (moda)"},
    {"sinasc": "PARIDADE", "modelo": "PARIDADE_CAT", "significado": "Primeira gestação ou não", "tipo": "binária",
     "codificacao": "1 indicador 0/1: multípara", "referencia": "nulípara (0)", "ignorados": "Nenhum na amostra principal"},
    {"sinasc": "QTDFILMORT", "modelo": "PERDAS_FETAIS_CAT", "significado": "Perdas fetais e abortos anteriores",
     "tipo": "categórica ordinal", "codificacao": "2 indicadores 0/1: uma; duas ou mais", "referencia": "nenhuma (0)",
     "ignorados": "Código 99 ou vazio → nenhuma (moda)"},
)


def nome_do_termo(termo: str) -> str:
    """Rótulo legível de um termo do desenho do M3 (nome de saída do ``ColumnTransformer``)."""
    fixos = {"Intercepto": "Intercepto", X1: "X1: início nos meses 1–3", "IDADEMAE_NUM": "Idade (padronizada)",
             "IDADEMAE_QUAD": "Idade² (padronizada)"}
    if termo in fixos:
        return fixos[termo]
    for variavel, rotulos in ROTULOS_NIVEIS.items():
        if termo.startswith(variavel + "_") and termo[len(variavel) + 1:] in rotulos:
            nome = {"ESCOLARIDADE_MAE": "Escolaridade", "RACA_COR_MAE": "Raça/cor", "PARIDADE_CAT": "Paridade",
                    "PERDAS_FETAIS_CAT": "Perdas fetais"}[variavel]
            return f"{nome}: {rotulos[termo[len(variavel) + 1:]]}"
    raise KeyError(termo)


def coeficientes_modelo(modelo: Pipeline) -> pd.DataFrame:
    """Coeficientes efetivamente estimados pelo pipeline ajustado, na escala do desenho e na escala original.

    Escala do desenho: a que o ``LogisticRegression`` vê (idade e idade² padronizadas; X1 e indicadores em 0/1).
    Escala original: equação algebricamente equivalente com idade em anos e idade² em anos², obtida com a média e o
    desvio-padrão do ``StandardScaler`` ajustado (b = β/σ; o intercepto absorve −Σ β·μ/σ). X1 e indicadores não
    mudam. Nada é reconstruído a partir de OR arredondadas.
    """
    preprocessamento, regressao = modelo[:-1][-1], modelo[-1]
    nomes = list(preprocessamento.get_feature_names_out())
    beta = pd.Series(regressao.coef_.ravel(), index=nomes)
    tabela = pd.DataFrame({"coef_desenho": pd.concat([pd.Series({"Intercepto": float(regressao.intercept_[0])}), beta])})
    original = tabela.coef_desenho.copy()
    tabela["media_padronizacao"] = np.nan
    tabela["dp_padronizacao"] = np.nan
    if "numericas" in preprocessamento.named_transformers_:
        escala = preprocessamento.named_transformers_["numericas"]
        for termo, media, dp in zip(escala.feature_names_in_, escala.mean_, escala.scale_):
            tabela.loc[termo, ["media_padronizacao", "dp_padronizacao"]] = [media, dp]
            original[termo] = beta[termo] / dp
            original["Intercepto"] -= beta[termo] * media / dp
    tabela["coef_original"] = original
    tabela["rotulo"] = [nome_do_termo(t) for t in tabela.index]
    return tabela


def preditor_linear_escala_original(coeficientes: pd.DataFrame, x: pd.DataFrame) -> np.ndarray:
    """η = logit P(Y=1 | X) calculado só com a tabela ``coef_original`` e os preditores codificados (sem o pipeline).

    Serve para verificar a equação publicada: deve coincidir com ``decision_function`` do pipeline.
    """
    b = coeficientes.coef_original
    eta = np.full(len(x), b["Intercepto"], dtype=float)
    for termo, valor in b.drop("Intercepto").items():
        if termo in (X1, *NUMERICAS):
            eta += valor * x[termo].to_numpy(dtype=float)
            continue
        variavel = next(v for v in CATEGORIAS if termo.startswith(v + "_"))
        eta += valor * (x[variavel].astype(str).to_numpy() == termo[len(variavel) + 1:])
    return eta


def resumo_descritivo_m3(x: pd.DataFrame, y_2500: np.ndarray, y_2600: np.ndarray) -> pd.DataFrame:
    """n, % e proporção de cada desfecho por nível das variáveis do M3 (já codificadas e agregadas)."""
    y25, y26 = np.asarray(y_2500), np.asarray(y_2600)
    linhas = []

    def linha(variavel, nivel, mascara):
        n = int(mascara.sum())
        linhas.append({"variavel": variavel, "nivel": nivel, "n": n, "pct": 100 * n / len(x),
                       "pct_y2500": 100 * y25[mascara].mean(), "pct_y2600": 100 * y26[mascara].mean()})

    for valor, nome in [(1, "meses 1–3"), (0, "meses 4–6")]:
        linha("X1", nome, x[X1].to_numpy() == valor)
    idade = x.IDADEMAE_NUM.to_numpy(dtype=float)
    for nome, mascara in [("< 20 anos", idade < 20), ("20–34 anos", (idade >= 20) & (idade < 35)),
                          ("≥ 35 anos", idade >= 35)]:
        linha("Idade", nome, mascara)
    for variavel, rotulos in ROTULOS_NIVEIS.items():
        valores = x[variavel].astype(str).to_numpy()
        for codigo, nome in rotulos.items():
            linha(variavel, nome, valores == codigo)
    return pd.DataFrame(linhas)
