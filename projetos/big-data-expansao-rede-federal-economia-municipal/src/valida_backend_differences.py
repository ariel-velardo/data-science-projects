"""D20A — validação segura do backend Python ``differences==0.3.0``.

O módulo permite ajustar ``ATTgt`` apenas em painéis sintéticos marcados pela
D19. Para a amostra real D15, a única operação pública é um dry-run estrutural:
preparar a cópia elegível, instanciar ``ATTgt`` e inspecionar o contrato, sem
chamar ``fit``.
"""
from __future__ import annotations

import importlib.metadata
import inspect
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from differences import ATTgt

import estima_did_escalonado as d19
import simula_did_escalonado as simulador
from simula_did_escalonado import ROTULO_FONTE_SINTETICA


VERSAO_DIFERENCES_VALIDADA = "0.3.0"
COLUNA_COORTE_API = "coorte_api"
BASE_PERIOD_PRINCIPAL = "universal"
CONTROL_GROUP_PRINCIPAL = "never_treated"
EST_METHOD_PRINCIPAL = "dr"
CODIGO_CABO_FRIO = "3300704"
BOOT_ITERATIONS_FINAL_D20B = 1999
RANDOM_STATE_FINAL_D20B = 20260924
# differences 0.3.0 falha no multiplier bootstrap com n_jobs > 1 neste
# ambiente (joblib/tqdm). Um processo preserva reprodutibilidade e resultado.
N_JOBS_FINAL_D20B = 1
ALPHA_FINAL_D20B = 0.05


def _exigir_backend_validado() -> None:
    versao = importlib.metadata.version("differences")
    if versao != VERSAO_DIFERENCES_VALIDADA:
        raise RuntimeError(
            f"versão de differences divergente: {versao}; "
            f"esperada {VERSAO_DIFERENCES_VALIDADA}"
        )


def auditar_api_differences() -> dict[str, Any]:
    """Documenta a API efetivamente importada, sem inferir parâmetros do R."""
    _exigir_backend_validado()
    assinatura_init = inspect.signature(ATTgt)
    assinatura_fit = inspect.signature(ATTgt.fit)
    assinatura_aggregate = inspect.signature(ATTgt.aggregate)
    return {
        "versao": importlib.metadata.version("differences"),
        "classe": "differences.ATTgt",
        "dataframe": "pandas.DataFrame com MultiIndex unidade-tempo",
        "indice": "dois níveis: entidade, tempo",
        "coorte": "primeiro período tratado",
        "never_treated_api": "coorte_nula",
        "base_period_opcoes": ("varying", "universal"),
        "anticipation_default": assinatura_init.parameters["anticipation"].default,
        "control_group_default": assinatura_fit.parameters["control_group"].default,
        "est_method_default": assinatura_fit.parameters["est_method"].default,
        "est_method_dr": "dr-mle; doubly robust localmente eficiente com propensity logit",
        "cluster_entidade_api": "cluster_var=None",
        "bootstrap_parametro": "boot_iterations",
        "random_state_parametro": "random_state",
        "n_jobs_parametro": "n_jobs",
        "agregacoes": tuple(
            valor
            for valor in ("simple", "cohort", "event", "time")
        ),
        "painel_desbalanceado_default": "repeated_cross_section",
        "painel_desbalanceado_panel": "as_repeated_cross_section=False",
        "assinatura_init": str(assinatura_init),
        "assinatura_fit": str(assinatura_fit),
        "assinatura_aggregate": str(assinatura_aggregate),
    }


def _validar_fonte_sintetica(painel: pd.DataFrame) -> None:
    if (
        "fonte_dados" not in painel.columns
        or painel.empty
        or not painel["fonte_dados"].eq(ROTULO_FONTE_SINTETICA).all()
    ):
        raise PermissionError("fit real proibido: somente dados sintéticos D19 são aceitos")
    obrigatorias = {"id", "ano", "coorte_g", "y", "cenario"}
    faltantes = obrigatorias - set(painel.columns)
    if faltantes:
        raise ValueError(f"painel sintético sem colunas: {sorted(faltantes)}")
    if painel.duplicated(["id", "ano"]).any():
        raise ValueError("painel sintético com chave id-ano duplicada")


def _dados_sinteticos_api(painel: pd.DataFrame) -> pd.DataFrame:
    _validar_fonte_sintetica(painel)
    dados = painel.copy(deep=True)
    dados[COLUNA_COORTE_API] = pd.to_numeric(dados["coorte_g"], errors="raise").astype(float)
    dados.loc[dados[COLUNA_COORTE_API].eq(0), COLUNA_COORTE_API] = np.nan
    return dados.set_index(["id", "ano"]).sort_index()


def construir_modelo_sintetico(
    painel: pd.DataFrame,
    *,
    base_period: str = BASE_PERIOD_PRINCIPAL,
    anticipation: int = 0,
) -> ATTgt:
    """Instancia a API real somente para dados sintéticos D19."""
    _exigir_backend_validado()
    dados = _dados_sinteticos_api(painel)
    return ATTgt(
        data=dados,
        cohort_column=COLUNA_COORTE_API,
        base_period=base_period,
        anticipation=anticipation,
    )


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
    resultado = resultado.reset_index()
    resultado = resultado.rename(columns=renomear_indices)
    resultado["inferencia"] = inferencia
    return resultado


def _adicionar_referencia_evento(evento: pd.DataFrame, inferencia: str) -> pd.DataFrame:
    if evento["event_time"].eq(-1).any():
        return evento
    referencia = {coluna: np.nan for coluna in evento.columns}
    referencia.update({"event_time": -1, "att": 0.0, "inferencia": inferencia})
    return (
        pd.concat([evento, pd.DataFrame([referencia])], ignore_index=True)
        .sort_values("event_time")
        .reset_index(drop=True)
    )


def configuracao_inferencia_final_d20b() -> dict[str, Any]:
    """Retorna a inferência pré-especificada, sem executar a amostra real."""
    return {
        "backend": f"differences=={VERSAO_DIFERENCES_VALIDADA}",
        "base_period": BASE_PERIOD_PRINCIPAL,
        "control_group": CONTROL_GROUP_PRINCIPAL,
        "est_method": EST_METHOD_PRINCIPAL,
        "boot_iterations": BOOT_ITERATIONS_FINAL_D20B,
        "random_state": RANDOM_STATE_FINAL_D20B,
        "n_jobs": N_JOBS_FINAL_D20B,
        "n_jobs_cpu_disponiveis": int(os.cpu_count() or 1),
        "n_jobs_justificativa": (
            "1; differences 0.3.0 falha com n_jobs>1 neste ambiente e "
            "n_jobs nao pode alterar o resultado"
        ),
        "alpha": ALPHA_FINAL_D20B,
        "nivel_confianca": 1.0 - ALPHA_FINAL_D20B,
        "bandas_simultaneas": True,
        "cluster": "entidade_automatico_cluster_var_None",
        "k_referencia": -1,
        "k_referencia_deterministico": 0.0,
        "executado_na_base_real": False,
        "definido_antes_do_efeito_real": True,
    }


def estimar_sintetico(
    painel: pd.DataFrame,
    *,
    base_period: str = BASE_PERIOD_PRINCIPAL,
    anticipation: int = 0,
    control_group: str = CONTROL_GROUP_PRINCIPAL,
    est_method: str = EST_METHOD_PRINCIPAL,
    as_repeated_cross_section: bool = False,
    boot_iterations: int = 0,
    random_state: int | None = None,
    n_jobs: int = 1,
    files_path: str | Path | None = None,
) -> dict[str, Any]:
    """Ajusta ATT(g,t) somente no DGP sintético reutilizado da D19.

    Em ``base_period='universal'`` o bootstrap 0.3.0 gera bandas ``NaN``
    se a célula determinística k=-1 for incluída (desvio-padrão zero). Para
    bootstrap, a referência é retirada pela API pública ``filter_gt`` e
    recolocada como zero apenas na tabela de event-study.
    """
    _validar_fonte_sintetica(painel)
    modelo = construir_modelo_sintetico(
        painel, base_period=base_period, anticipation=anticipation
    )

    workaround_referencia = bool(boot_iterations and base_period == "universal")
    if workaround_referencia:
        periodos = sorted(
            {
                int(tempo - coorte)
                for coorte in modelo._cohorts
                for tempo in modelo._times
                if int(tempo - coorte) != -1
            }
        )
        modelo.filter_gt(base_period="universal", relative_period=periodos)

    ajuste = modelo.fit(
        "y",
        est_method=est_method,
        control_group=control_group,
        as_repeated_cross_section=as_repeated_cross_section,
        cluster_var=None,
        alpha=0.05,
        boot_iterations=boot_iterations,
        random_state=random_state,
        n_jobs=n_jobs,
        progress_bar=False,
        files_path=files_path,
    )
    kwargs_agregacao = {
        "boot_iterations": boot_iterations,
        "random_state": random_state,
        "n_jobs": n_jobs,
    }
    inferencia = "bootstrap_simultanea" if boot_iterations else "analitica_pontual"
    att_gt = _normalizar_saida(
        ajuste.to_pandas(),
        renomear_indices={"cohort": "coorte", "time": "ano"},
        inferencia=inferencia,
    )
    evento_calculo_banda = _normalizar_saida(
        ajuste.aggregate("event", **kwargs_agregacao),
        renomear_indices={"relative_period": "event_time"},
        inferencia=inferencia,
    )
    evento = evento_calculo_banda.copy(deep=True)
    if workaround_referencia:
        evento = _adicionar_referencia_evento(evento, inferencia)
    coorte = _normalizar_saida(
        ajuste.aggregate("cohort", **kwargs_agregacao),
        renomear_indices={"cohort": "coorte"},
        inferencia=inferencia,
    )
    simples = _normalizar_saida(
        ajuste.aggregate("simple", **kwargs_agregacao),
        renomear_indices={},
        inferencia=inferencia,
    )

    elementos = ajuste._att_gt["full_sample"]["ATTgt_ntl"]
    falhas = [
        elemento
        for elemento in elementos
        if elemento.exception is not None
        or (elemento.base_period != elemento.time and not np.isfinite(elemento.ATT))
    ]
    contagens = painel.groupby("id")["ano"].nunique()
    cenario = painel["cenario"].drop_duplicates().tolist()
    n_coorte_2013 = int(
        painel.loc[painel["coorte_g"].eq(2013), "id"].nunique()
    )
    metadados = {
        "cenario": cenario[0] if len(cenario) == 1 else "MULTIPLOS",
        "n_celulas_falhas": len(falhas),
        "mensagens_falha": sorted({str(item.exception) for item in falhas}),
        "painel_balanceado": bool(modelo.is_balanced_panel),
        "como_repeated_cross_section": bool(modelo._as_rcs),
        "linhas_unidade_desbalanceada": int(contagens.min()),
        "n_coorte_2013": n_coorte_2013,
        "cluster": "entidade_automatico_cluster_var_None",
        "est_method_resolvido": "dr-mle" if est_method == "dr" else est_method,
        "workaround_bootstrap_k_menos_1": workaround_referencia,
        "efeito_real_estimado": False,
    }
    return {
        "modelo": modelo,
        "resultado": ajuste,
        "att_gt": att_gt,
        "event": evento,
        "event_calculo_banda": evento_calculo_banda,
        "cohort": coorte,
        "simple": simples,
        "metadados": metadados,
    }


def _comparar_estimativas_pontuais(
    sem_filtro: pd.DataFrame,
    com_workaround: pd.DataFrame,
    *,
    chaves: list[str],
    rotulo: str,
) -> tuple[pd.DataFrame, float, bool]:
    esquerda = sem_filtro[chaves + ["att"]].copy()
    direita = com_workaround[chaves + ["att"]].copy()
    comparacao = esquerda.merge(
        direita,
        on=chaves,
        how="outer",
        suffixes=("_sem_filtro", "_workaround"),
        indicator=True,
        validate="one_to_one",
    )
    if not comparacao["_merge"].eq("both").all():
        raise AssertionError(f"workaround alterou suporte de {rotulo}")
    comparacao["abs_diff"] = (
        comparacao["att_sem_filtro"] - comparacao["att_workaround"]
    ).abs()
    max_abs_diff = float(comparacao["abs_diff"].max()) if len(comparacao) else 0.0
    invariante = bool(np.allclose(
        comparacao["att_sem_filtro"],
        comparacao["att_workaround"],
        rtol=0.0,
        atol=1e-12,
        equal_nan=True,
    ))
    return comparacao.drop(columns="_merge"), max_abs_diff, invariante


def validar_workaround_k_menos_1(
    painel: pd.DataFrame,
    *,
    boot_iterations: int,
    random_state: int,
    n_jobs: int = N_JOBS_FINAL_D20B,
) -> dict[str, Any]:
    """Compara o cálculo universal sem filtro com o bootstrap sem ``k=-1``.

    A função aceita exclusivamente o DGP sintético D19. Qualquer mudança em
    estimativas pontuais pós-tratamento ou agregações bloqueia a validação.
    """
    _validar_fonte_sintetica(painel)
    if boot_iterations < 1:
        raise ValueError("boot_iterations deve ser positivo")
    sem_filtro = estimar_sintetico(
        painel,
        base_period=BASE_PERIOD_PRINCIPAL,
        boot_iterations=0,
        n_jobs=1,
    )
    com_workaround = estimar_sintetico(
        painel,
        base_period=BASE_PERIOD_PRINCIPAL,
        boot_iterations=boot_iterations,
        random_state=random_state,
        n_jobs=n_jobs,
    )

    att_pos_a = sem_filtro["att_gt"].loc[
        sem_filtro["att_gt"]["ano"].ge(sem_filtro["att_gt"]["coorte"])
    ]
    att_pos_b = com_workaround["att_gt"].loc[
        com_workaround["att_gt"]["ano"].ge(com_workaround["att_gt"]["coorte"])
    ]
    event_a = sem_filtro["event"].loc[
        sem_filtro["event"]["event_time"].ne(-1)
    ]
    event_b = com_workaround["event"].loc[
        com_workaround["event"]["event_time"].ne(-1)
    ]

    especificacoes = {
        "att_gt_pos_tratamento": (att_pos_a, att_pos_b, ["coorte", "base_period", "ano"]),
        "cohort": (sem_filtro["cohort"], com_workaround["cohort"], ["coorte"]),
        "simple": (sem_filtro["simple"], com_workaround["simple"], ["index"]),
        "event_k_diferente_menos_1": (event_a, event_b, ["event_time"]),
    }
    comparacoes: dict[str, pd.DataFrame] = {}
    max_abs_diff: dict[str, float] = {}
    invariantes: dict[str, bool] = {}
    for rotulo, (a, b, chaves) in especificacoes.items():
        tabela, maximo, invariante = _comparar_estimativas_pontuais(
            a, b, chaves=chaves, rotulo=rotulo
        )
        comparacoes[rotulo] = tabela
        max_abs_diff[rotulo] = maximo
        invariantes[rotulo] = invariante

    evento_calculo = com_workaround["event_calculo_banda"]
    referencia = com_workaround["event"].loc[
        com_workaround["event"]["event_time"].eq(-1)
    ]
    invariantes["k_menos_1_retirado_da_banda"] = bool(
        not evento_calculo["event_time"].eq(-1).any()
    )
    invariantes["k_menos_1_reposto_zero_apresentacao"] = bool(
        len(referencia) == 1
        and referencia["att"].eq(0.0).all()
        and referencia[["std_error", "ci_lower", "ci_upper"]].isna().all().all()
    )
    if not all(invariantes.values()):
        falhas = sorted(nome for nome, valor in invariantes.items() if not valor)
        raise AssertionError(f"workaround k=-1 alterou resultados: {falhas}")

    return {
        "configuracao_teste": {
            "base_period": BASE_PERIOD_PRINCIPAL,
            "boot_iterations": int(boot_iterations),
            "random_state": int(random_state),
            "n_jobs": int(n_jobs),
            "dados": ROTULO_FONTE_SINTETICA,
        },
        "invariantes": invariantes,
        "max_abs_diff": max_abs_diff,
        "comparacoes": comparacoes,
        "efeito_real_estimado": False,
    }


def comparar_att_gt(
    estimado: pd.DataFrame, verdade: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Compara somente células pós-tratamento estimadas com a verdade D19."""
    obrigatorias_estimado = {"coorte", "ano", "att"}
    faltantes = obrigatorias_estimado - set(estimado.columns)
    if faltantes:
        raise ValueError(f"estimativa ATT(g,t) sem colunas: {sorted(faltantes)}")
    comparacao = estimado.merge(
        verdade[["coorte_g", "ano", "att_gt_verdadeiro"]],
        left_on=["coorte", "ano"],
        right_on=["coorte_g", "ano"],
        how="inner",
        validate="one_to_one",
    )
    comparacao["bias"] = comparacao["att"] - comparacao["att_gt_verdadeiro"]
    erros = comparacao["bias"].to_numpy(dtype=float)
    correlacao = float(comparacao[["att", "att_gt_verdadeiro"]].corr().iloc[0, 1])
    cobertura = np.nan
    if {"ci_lower", "ci_upper"}.issubset(comparacao.columns):
        validos = comparacao["ci_lower"].notna() & comparacao["ci_upper"].notna()
        if validos.any():
            cobertura = float(
                comparacao.loc[validos, "att_gt_verdadeiro"].between(
                    comparacao.loc[validos, "ci_lower"],
                    comparacao.loc[validos, "ci_upper"],
                ).mean()
            )
    metricas: dict[str, float | int] = {
        "n_celulas": int(len(comparacao)),
        "bias_medio": float(np.mean(erros)),
        "mae": float(np.mean(np.abs(erros))),
        "rmse": float(np.sqrt(np.mean(np.square(erros)))),
        "correlacao": correlacao,
        "cobertura": float(cobertura),
    }
    return comparacao, metricas


def executar_cenarios_d19(*, n_unidades: int = 240) -> dict[str, pd.DataFrame]:
    """Executa exatamente os cinco geradores já definidos pela D19."""
    fabricas = (
        simulador.criar_cenario_limpo,
        simulador.criar_cenario_heterogeneo,
        simulador.criar_cenario_violacao_tendencias,
        simulador.criar_cenario_overlap_fraco,
        simulador.criar_cenario_coorte_pequena,
    )
    resumos: list[dict[str, Any]] = []
    comparacoes: list[pd.DataFrame] = []
    eventos: list[pd.DataFrame] = []
    coortes: list[pd.DataFrame] = []
    simples: list[pd.DataFrame] = []

    for fabrica in fabricas:
        dgp = fabrica(n_unidades=n_unidades)
        estimacao = estimar_sintetico(dgp.painel)
        comparacao, metricas = comparar_att_gt(estimacao["att_gt"], dgp.verdade_att_gt)
        cenario = str(dgp.metadados["cenario"])
        comparacao["cenario"] = cenario
        evento = estimacao["event"].copy()
        evento["cenario"] = cenario
        coorte = estimacao["cohort"].copy()
        coorte["cenario"] = cenario
        simples_cenario = estimacao["simple"].copy()
        simples_cenario["cenario"] = cenario

        resumos.append(
            {
                "cenario": cenario,
                **metricas,
                "n_celulas_falhas": estimacao["metadados"]["n_celulas_falhas"],
                "parallel_trends_verdadeira": dgp.metadados["parallel_trends_verdadeira"],
                "overlap_fraco": dgp.metadados["overlap_fraco"],
                "n_coorte_2013": estimacao["metadados"]["n_coorte_2013"],
            }
        )
        comparacoes.append(comparacao)
        eventos.append(evento)
        coortes.append(coorte)
        simples.append(simples_cenario)

    return {
        "resumo": pd.DataFrame(resumos),
        "att_gt_comparacao": pd.concat(comparacoes, ignore_index=True),
        "event": pd.concat(eventos, ignore_index=True),
        "cohort": pd.concat(coortes, ignore_index=True),
        "simple": pd.concat(simples, ignore_index=True),
    }


def executar_monte_carlo(
    *,
    seeds_ponto: list[int],
    seeds_bootstrap: list[int],
    n_unidades: int = 240,
    boot_iterations: int = 99,
) -> dict[str, Any]:
    """Monte Carlo ex ante no cenário limpo, sem alterar o DGP após resultados."""
    if not seeds_ponto:
        raise ValueError("seeds_ponto não pode ser vazio")
    if not seeds_bootstrap:
        raise ValueError("seeds_bootstrap não pode ser vazio")
    if boot_iterations < 1:
        raise ValueError("boot_iterations deve ser positivo")

    metricas_ponto: list[dict[str, Any]] = []
    comparacoes_ponto: list[pd.DataFrame] = []
    comparacoes_bootstrap: list[pd.DataFrame] = []
    falhas_convergencia = 0

    for seed in seeds_ponto:
        dgp = simulador.criar_cenario_limpo(seed=seed, n_unidades=n_unidades)
        estimacao = estimar_sintetico(dgp.painel)
        comparacao, metricas = comparar_att_gt(estimacao["att_gt"], dgp.verdade_att_gt)
        comparacao["seed"] = seed
        comparacoes_ponto.append(comparacao)
        falhas = int(estimacao["metadados"]["n_celulas_falhas"])
        falhas_convergencia += falhas
        metricas_ponto.append({"seed": seed, **metricas, "n_celulas_falhas": falhas})

    coberturas: list[dict[str, Any]] = []
    for seed in seeds_bootstrap:
        dgp = simulador.criar_cenario_limpo(seed=seed, n_unidades=n_unidades)
        estimacao = estimar_sintetico(
            dgp.painel,
            boot_iterations=boot_iterations,
            random_state=seed,
        )
        comparacao, metricas = comparar_att_gt(estimacao["att_gt"], dgp.verdade_att_gt)
        comparacao["seed"] = seed
        comparacoes_bootstrap.append(comparacao)
        falhas = int(estimacao["metadados"]["n_celulas_falhas"])
        falhas_convergencia += falhas
        coberturas.append(
            {
                "seed": seed,
                "cobertura": metricas["cobertura"],
                "n_celulas": metricas["n_celulas"],
                "n_celulas_falhas": falhas,
            }
        )

    todas_ponto = pd.concat(comparacoes_ponto, ignore_index=True)
    erros = todas_ponto["bias"].to_numpy(dtype=float)
    todas_bootstrap = pd.concat(comparacoes_bootstrap, ignore_index=True)
    validos = todas_bootstrap["ci_lower"].notna() & todas_bootstrap["ci_upper"].notna()
    cobertura = float(
        todas_bootstrap.loc[validos, "att_gt_verdadeiro"].between(
            todas_bootstrap.loc[validos, "ci_lower"],
            todas_bootstrap.loc[validos, "ci_upper"],
        ).mean()
    )
    resumo = {
        "bias_medio": float(np.mean(erros)),
        "mae": float(np.mean(np.abs(erros))),
        "rmse": float(np.sqrt(np.mean(np.square(erros)))),
        "correlacao": float(
            todas_ponto[["att", "att_gt_verdadeiro"]].corr().iloc[0, 1]
        ),
        "cobertura": cobertura,
        "n_celulas_ponto": int(len(todas_ponto)),
        "n_celulas_cobertura": int(validos.sum()),
        "n_falhas_convergencia": int(falhas_convergencia),
        "n_seeds_ponto": len(seeds_ponto),
        "n_seeds_bootstrap": len(seeds_bootstrap),
    }
    return {
        "configuracao": {
            "seeds_ponto": list(seeds_ponto),
            "seeds_bootstrap": list(seeds_bootstrap),
            "n_unidades": n_unidades,
            "boot_iterations": boot_iterations,
            "cenario": "LIMPO",
            "definido_antes_dos_resultados": True,
        },
        "por_seed_ponto": pd.DataFrame(metricas_ponto),
        "por_seed_bootstrap": pd.DataFrame(coberturas),
        "comparacoes_ponto": todas_ponto,
        "comparacoes_bootstrap": todas_bootstrap,
        "resumo": resumo,
    }


def executar_dry_run_real_sem_fit(
    caminho_parquet: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Prepara a D15 para a API e instancia ``ATTgt`` sem chamar ``fit``."""
    _exigir_backend_validado()
    caminho = Path(caminho_parquet)
    hash_antes = d19.sha256_arquivo(caminho)
    amostra = pd.read_parquet(caminho)
    base = d19.preparar_dados_estimador(amostra)
    validacao_d19 = d19.validar_dados_estimador(base)

    dados = base.loc[base["elegivel_estimacao_principal"].astype(bool)].copy(deep=True)
    dados[COLUNA_COORTE_API] = dados["g_backend"].astype(float)
    dados.loc[dados[COLUNA_COORTE_API].eq(0), COLUNA_COORTE_API] = np.nan
    dados_api = dados.set_index(["id_backend", "t_backend"]).sort_index()

    # O construtor valida MultiIndex, coorte nula e suporte de painel. Não há fit.
    modelo = ATTgt(
        data=dados_api.copy(deep=True),
        cohort_column=COLUNA_COORTE_API,
        base_period=BASE_PERIOD_PRINCIPAL,
        anticipation=0,
    )
    if hasattr(modelo, "_fit_res"):
        raise AssertionError("dry-run real não deveria possuir resultado de fit")

    cabo = dados.loc[dados["id_backend"].eq("3300704")]
    hash_depois = d19.sha256_arquivo(caminho)
    if hash_antes != hash_depois:
        raise AssertionError("parquet D15 foi alterado durante o dry-run D20A")
    auditoria = {
        **validacao_d19,
        "n_linhas_backend": int(len(dados_api)),
        "n_unidades": int(dados["id_backend"].nunique()),
        "n_linhas_cabo_frio": int(len(cabo)),
        "coorte_cabo_frio": int(cabo["g_backend"].drop_duplicates().item()),
        "painel_balanceado_backend": bool(modelo.is_balanced_panel),
        "never_treated_representado_por_nulo": bool(
            dados.loc[dados["papel_causal"].eq(d19.PAPEL_CONTROLE), COLUNA_COORTE_API]
            .isna()
            .all()
        ),
        "objeto_attgt_instanciado": True,
        "estimacao_executada": False,
        "fit_real_bloqueado": True,
        "sha256_antes": hash_antes,
        "sha256_depois": hash_depois,
        "byte_identical": True,
    }
    return dados_api, auditoria


def preparar_amostra_principal_estimavel(
    amostra_d15: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Deriva a view principal balanceada, excluindo apenas Cabo Frio.

    A função é pura: não escreve a D15, não imputa 2009, não muda ``g`` e
    não chama qualquer estimador. A exclusão decorre da incompatibilidade
    pré-estimação entre Cabo Frio/2009 e a referência universal ``g-1``.
    """
    obrigatorias = {
        "codigo_municipio_ibge",
        "ano",
        "papel_causal",
        "coorte_g",
        "elegivel_estimacao_principal",
    }
    faltantes = obrigatorias - set(amostra_d15.columns)
    if faltantes:
        raise ValueError(f"D15 sem colunas obrigatórias: {sorted(faltantes)}")
    if amostra_d15.duplicated(["codigo_municipio_ibge", "ano"]).any():
        raise ValueError("D15 com chave municipio-ano duplicada")

    trabalho = amostra_d15.copy(deep=True)
    trabalho["codigo_municipio_ibge"] = (
        trabalho["codigo_municipio_ibge"].astype("string").str.zfill(7)
    )
    tratados_d15 = trabalho.loc[
        trabalho["papel_causal"].eq(d19.PAPEL_TRATADO), "codigo_municipio_ibge"
    ].nunique()
    cabo = trabalho.loc[trabalho["codigo_municipio_ibge"].eq(CODIGO_CABO_FRIO)]
    if tratados_d15 != 129:
        raise ValueError(f"população documental D15 divergente: {tratados_d15} tratados")
    if len(cabo) != 13 or set(cabo["ano"].astype(int)) != set(range(2007, 2020)):
        raise ValueError("Cabo Frio não possui as 13 linhas documentais esperadas")
    if set(cabo["coorte_g"].dropna().astype(int)) != {2010}:
        raise ValueError("coorte de Cabo Frio divergente de g=2010")
    cabo_2009 = cabo.loc[cabo["ano"].eq(2009)]
    if len(cabo_2009) != 1 or bool(cabo_2009["elegivel_estimacao_principal"].item()):
        raise ValueError("Cabo Frio/2009 deveria ser a transição inelegível")

    view = trabalho.loc[
        ~trabalho["codigo_municipio_ibge"].eq(CODIGO_CABO_FRIO)
    ].copy(deep=True)
    view = view.sort_values(["codigo_municipio_ibge", "ano"]).reset_index(drop=True)

    anos_esperados = set(range(2007, 2020))
    anos_por_unidade = view.groupby("codigo_municipio_ibge")["ano"].agg(
        lambda valores: set(map(int, valores))
    )
    painel_balanceado = bool(
        len(anos_por_unidade) == 5091
        and anos_por_unidade.map(lambda anos: anos == anos_esperados).all()
    )
    tratados = view.loc[
        view["papel_causal"].eq(d19.PAPEL_TRATADO), "codigo_municipio_ibge"
    ].nunique()
    controles = view.loc[
        view["papel_causal"].eq(d19.PAPEL_CONTROLE), "codigo_municipio_ibge"
    ].nunique()
    coortes = (
        view.loc[view["papel_causal"].eq(d19.PAPEL_TRATADO)]
        .drop_duplicates("codigo_municipio_ibge")
        .groupby("coorte_g")["codigo_municipio_ibge"]
        .nunique()
    )
    contagem_coortes = {int(k): int(v) for k, v in coortes.items()}
    validacoes = {
        "POPULACAO_D15_TRATADOS": int(tratados_d15),
        "POPULACAO_PRINCIPAL_ESTIMAVEL": int(tratados),
        "n_controles": int(controles),
        "n_municipios": int(view["codigo_municipio_ibge"].nunique()),
        "n_linhas": int(len(view)),
        "painel_balanceado_2007_2019": painel_balanceado,
        "codigo_5003900_ausente": not view["codigo_municipio_ibge"].eq("5003900").any(),
        "cabo_frio_ausente_view": not view["codigo_municipio_ibge"].eq(CODIGO_CABO_FRIO).any(),
        "cabo_frio_presente_d15": bool(len(cabo) == 13),
        "contagem_coortes": contagem_coortes,
        "motivo_exclusao": "CABO_FRIO_2009_INCOMPATIVEL_COM_REFERENCIA_G_MENOS_1",
        "base_period": BASE_PERIOD_PRINCIPAL,
        "k_referencia": -1,
        "ano_base_cabo_frio": 2009,
        "g_cabo_frio": 2010,
        "imputacao_2009": False,
        "repeated_cross_section": False,
        "efeito_real_estimado": False,
    }
    esperados = {
        "POPULACAO_PRINCIPAL_ESTIMAVEL": 128,
        "n_controles": 4963,
        "n_municipios": 5091,
        "n_linhas": 66183,
        "contagem_coortes": {2009: 21, 2010: 26, 2011: 66, 2012: 13, 2013: 2},
    }
    divergencias = {
        chave: (validacoes[chave], esperado)
        for chave, esperado in esperados.items()
        if validacoes[chave] != esperado
    }
    if divergencias:
        raise AssertionError(f"view D20B divergente: {divergencias}")
    if not painel_balanceado or not validacoes["codigo_5003900_ausente"]:
        raise AssertionError("view D20B não satisfaz balanceamento/exclusões")
    if not view["elegivel_estimacao_principal"].astype(bool).all():
        raise AssertionError("view D20B ainda contém linha inelegível")
    return view, validacoes


def materializar_view_principal_estimavel(
    caminho_d15: str | Path,
    caminho_saida: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Persiste uma cópia derivada e comprova que a D15 não foi alterada."""
    origem = Path(caminho_d15)
    destino = Path(caminho_saida)
    if origem.resolve() == destino.resolve():
        raise ValueError("a view D20B não pode sobrescrever a D15")
    hash_antes = d19.sha256_arquivo(origem)
    view, auditoria = preparar_amostra_principal_estimavel(pd.read_parquet(origem))
    destino.parent.mkdir(parents=True, exist_ok=True)
    view.to_parquet(destino, index=False)
    hash_depois = d19.sha256_arquivo(origem)
    if hash_antes != hash_depois:
        raise AssertionError("parquet D15 foi alterado ao materializar a view D20B")
    auditoria = {
        **auditoria,
        "caminho_d15": str(origem),
        "caminho_view": str(destino),
        "sha256_d15_antes": hash_antes,
        "sha256_d15_depois": hash_depois,
        "d15_byte_identical": True,
        "sha256_view": d19.sha256_arquivo(destino),
    }
    return view, auditoria


def gates_d20a(
    *,
    monte_carlo_validado: bool,
    bootstrap_validado: bool,
    dry_run_validado: bool,
) -> dict[str, str]:
    """Mantém separados backend, inferência e decisão pendente de Cabo Frio."""
    return {
        "D20A_PYTHON_DIFERENCES_0_3_0_DISPONIVEL": "SIM",
        "D20A_BACKEND_CALLAWAY_SANTANNA_PYTHON_VALIDADO": "SIM",
        "D20A_CONVENCAO_COORTE_VALIDADA": "SIM",
        "D20A_BASE_PERIOD_VALIDADO": "SIM",
        "D20A_NEVER_TREATED_VALIDADO": "SIM",
        "D20A_ATT_GT_SINTETICO_VALIDADO": "SIM",
        "D20A_MONTE_CARLO_VALIDADO": "SIM" if monte_carlo_validado else "NAO",
        "D20A_EVENT_STUDY_SINTETICO_VALIDADO": "SIM",
        "D20A_INFERENCIA_VALIDADA": "PARCIAL" if bootstrap_validado else "NAO",
        "D20A_PAINEL_DESBALANCEADO_VALIDADO": "SIM",
        "D20A_CABO_FRIO_IMPLEMENTACAO_DEFINIDA": "BLOQUEADO_DECISAO",
        "D20A_DRY_RUN_REAL_BACKEND_VALIDADO": "SIM" if dry_run_validado else "NAO",
        "D20A_PRONTO_PARA_PRIMEIRA_ESTIMACAO_REAL": "NAO",
        "D20A_EFEITO_REAL_ESTIMADO": "NAO",
        "DESENHO_CAUSAL_APROVADO": "NAO",
    }


def gates_d20b(
    *,
    view_validada: bool,
    workaround_validado: bool,
    inferencia_configurada: bool,
) -> dict[str, str]:
    """Fecha somente os gates técnicos pré-estimação solicitados na D20B."""
    pronto = bool(view_validada and workaround_validado and inferencia_configurada)
    return {
        "D20B_CABO_FRIO_DECISAO_FECHADA": "SIM" if view_validada else "NAO",
        "D20B_POPULACAO_ESTIMAVEL_128_VALIDADA": "SIM" if view_validada else "NAO",
        "D20B_VIEW_BALANCEADA_VALIDADA": "SIM" if view_validada else "NAO",
        "D20B_WORKAROUND_K_MENOS_1_VALIDADO": "SIM" if workaround_validado else "NAO",
        "D20B_INFERENCIA_CONFIGURADA": "SIM" if inferencia_configurada else "NAO",
        "D20B_BOOTSTRAP_FINAL_PRE_ESPECIFICADO": "SIM" if inferencia_configurada else "NAO",
        "D20B_PRONTO_PARA_ESTIMACAO_REAL": "SIM" if pronto else "NAO",
        "D20B_EFEITO_REAL_ESTIMADO": "NAO",
        "DESENHO_CAUSAL_APROVADO": "NAO",
    }
