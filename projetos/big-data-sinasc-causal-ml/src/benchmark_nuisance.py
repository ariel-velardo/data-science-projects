"""Benchmark preditivo de nuisance models, com CV aninhada e retomada segura.

O módulo não estima efeitos. A escolha de hiperparâmetros usa apenas os folds
internos; os folds externos servem exclusivamente para avaliar predição.
"""
from __future__ import annotations

import gc
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path
from time import perf_counter
import warnings

import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import log_loss
from sklearn.model_selection import StratifiedKFold, train_test_split
from threadpoolctl import threadpool_limits

from src.modelagem_preditiva import criar_modelo, validar_x
from src.selecao_nuisance import diagnosticos_propensity, metricas_probabilidade


SEED = 20240925
N_JOBS_ARVORES = 8
_PROIBIDAS = ("aipw", "ate", "att", "cate", "efeito", "estimativa", "p_value",
              "significancia", "ic95", "qini", "auuc")


def candidatos(familia: str) -> list[dict]:
    """Espaços imutáveis por execução, fixados antes de métricas externas."""
    if familia == "logistica":
        return [{"id": "logistica_c1", "familia": familia, "parametros": {"C": 1.0},
                 "historico": True}]
    if familia == "hgb":
        return [
            {"id": f"hgb_lr{lr:g}_leaf{folhas}_min{minimo}", "familia": familia,
             "parametros": {"learning_rate": lr, "max_leaf_nodes": folhas,
                            "min_samples_leaf": minimo, "l2_regularization": 1.0,
                            "max_iter": 100},
             "historico": lr == 0.1 and folhas == 15 and minimo == 100}
            for lr in (0.05, 0.1) for folhas in (15, 31) for minimo in (100, 500)
        ]
    if familia == "extra_trees":
        return [
            {"id": f"extra_{'sqrt' if mf == 'sqrt' else 'meio'}_min{minimo}",
             "familia": familia,
             "parametros": {"n_estimators": 200, "max_features": mf,
                            "min_samples_leaf": minimo, "max_depth": None,
                            "class_weight": None, "random_state": SEED,
                            "n_jobs": N_JOBS_ARVORES}, "historico": False}
            for mf in ("sqrt", 0.5) for minimo in (50, 200)
        ]
    if familia == "random_forest":
        return [{"id": "rf_viabilidade", "familia": familia,
                 "parametros": {"n_estimators": 200, "max_features": "sqrt",
                                "min_samples_leaf": 100, "random_state": SEED,
                                "n_jobs": N_JOBS_ARVORES}, "historico": False}]
    raise ValueError(f"Família desconhecida: {familia}")


def criar_pipeline(candidato: dict):
    """Mantém o preprocessing histórico em cada treino, sem ajuste global."""
    familia = candidato["familia"]
    parametros = candidato["parametros"]
    if familia == "logistica":
        return criar_modelo("logistica").set_params(modelo__C=parametros["C"])
    if familia == "hgb":
        return criar_modelo("hgb").set_params(
            **{f"modelo__{chave}": valor for chave, valor in parametros.items()})
    if familia in ("extra_trees", "random_forest"):
        classe = ExtraTreesClassifier if familia == "extra_trees" else RandomForestClassifier
        return clone(criar_modelo("logistica")).set_params(modelo=classe(**parametros))
    raise ValueError(f"Família desconhecida: {familia}")


def _sha_array(valores) -> str:
    return sha256(np.ascontiguousarray(valores).tobytes()).hexdigest()


def _hash_obj(objeto: dict) -> str:
    return sha256(json.dumps(objeto, sort_keys=True, ensure_ascii=False,
                            separators=(",", ":")).encode("utf-8")).hexdigest()


def _codigo_sha() -> str:
    return sha256(Path(__file__).read_bytes()).hexdigest()


def _contrato_base(x: pd.DataFrame, alvo: np.ndarray, tipo: str, familia: str,
                   especificacoes: list[dict], contrato: dict, n_externos: int,
                   n_internos: int, seed: int) -> dict:
    return {
        "versao": 1, "tipo": tipo, "familia": familia,
        "especificacoes": especificacoes, "dados": contrato,
        "features": list(x.columns), "n": len(x),
        "alvo_sha256": _sha_array(alvo.astype(np.int8)),
        "seed": seed, "n_externos": n_externos, "n_internos": n_internos,
        "codigo_sha256": _codigo_sha(), "sklearn": sklearn.__version__,
    }


def _salvar_json_novo(caminho: Path, valor: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("x", encoding="utf-8") as arquivo:
        json.dump(valor, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
        arquivo.write("\n")


def _ler_checkpoint(caminho: Path, esperado: dict) -> dict | None:
    if not caminho.exists():
        return None
    observado = json.loads(caminho.read_text(encoding="utf-8"))
    if observado.get("contrato") != esperado or observado.get("status") != "CONCLUIDO":
        raise ValueError(f"Checkpoint incompatível: {caminho}")
    return observado


def _ajustar_prever(candidato: dict, x_treino: pd.DataFrame, y_treino: np.ndarray,
                    x_validacao: pd.DataFrame) -> tuple[np.ndarray, float]:
    modelo = criar_pipeline(candidato)
    inicio = perf_counter()
    with threadpool_limits(limits=4), warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always", ConvergenceWarning)
        modelo.fit(x_treino, y_treino)
        predicoes = modelo.predict_proba(x_validacao)[:, 1]
    if any(issubclass(aviso.category, ConvergenceWarning) for aviso in avisos):
        raise RuntimeError("Modelo não convergiu com os hiperparâmetros congelados.")
    if not np.isfinite(predicoes).all() or np.any((predicoes < 0) | (predicoes > 1)):
        raise RuntimeError("Probabilidades inválidas.")
    segundos = perf_counter() - inicio
    del modelo
    gc.collect()
    return predicoes, segundos


def escolher_um_ep(resultados: list[dict]) -> dict:
    """Prefere histórico quando o log-loss está até 1 EP do mínimo interno."""
    if not resultados:
        raise ValueError("Sem candidatos.")
    for resultado in resultados:
        if any(any(termo in str(chave).lower() for termo in _PROIBIDAS)
               for chave in resultado):
            raise ValueError("Métrica causal proibida na seleção.")
        if not np.isfinite(float(resultado["log_loss"])):
            raise ValueError("Log-loss inválido.")
    melhor = min(resultados, key=lambda r: r["log_loss"])
    limite = melhor["log_loss"] + melhor["log_loss_se_folds"]
    elegiveis = [r for r in resultados if r["log_loss"] <= limite]
    return min(elegiveis, key=lambda r: (
        not r.get("historico", False), r.get("custo_relativo", 1),
        r["log_loss"], r["id"]))


def executar_familia(x: pd.DataFrame, alvo, tipo: str, familia: str,
                     especificacoes: list[dict], pasta_cache: Path, contrato: dict,
                     *, n_externos: int = 3, n_internos: int = 3,
                     seed: int = SEED) -> dict:
    """Uma família por vez; checkpoints por fit interno e validação externa.

    ``alvo`` é T no propensity ou Y no braço já filtrado do outcome.
    A API não recebe simultaneamente T e Y.
    """
    validar_x(x)
    alvo = np.asarray(alvo, dtype=np.int8)
    if alvo.ndim != 1 or len(alvo) != len(x) or set(np.unique(alvo)) != {0, 1}:
        raise ValueError("X/alvo inválidos; ambas as classes são obrigatórias.")
    if tipo not in ("propensity", "outcome_t0", "outcome_t1"):
        raise ValueError("Tipo inválido.")
    if not especificacoes or any(c["familia"] != familia for c in especificacoes):
        raise ValueError("Especificações incompatíveis com a família.")
    pasta_cache = Path(pasta_cache)
    pasta_cache.mkdir(parents=True, exist_ok=True)
    base = _contrato_base(x, alvo, tipo, familia, especificacoes, contrato,
                          n_externos, n_internos, seed)
    externo = StratifiedKFold(n_splits=n_externos, shuffle=True, random_state=seed)
    oof = np.full(len(x), np.nan, dtype=np.float64)
    cobertura = np.zeros(len(x), dtype=np.uint8)
    folds = []
    candidatos_internos = []
    fits_realizados = 0
    fits_reutilizados = 0
    inicio_total = perf_counter()
    for numero, (treino, validacao) in enumerate(externo.split(x, alvo), 1):
        if np.intersect1d(treino, validacao).size:
            raise RuntimeError("Leakage por interseção de índices externos.")
        contrato_externo = {**base, "outer_fold": numero,
                            "hash_treino": _sha_array(treino.astype(np.int64)),
                            "hash_validacao": _sha_array(validacao.astype(np.int64))}
        resultados = []
        if len(especificacoes) > 1:
            splitter = StratifiedKFold(n_splits=n_internos, shuffle=True,
                                       random_state=seed + numero)
            internos = list(splitter.split(x.iloc[treino], alvo[treino]))
            for candidato in especificacoes:
                perdas = []
                tempos = []
                for j, (tr_local, va_local) in enumerate(internos, 1):
                    tr = treino[tr_local]
                    va = treino[va_local]
                    contrato_inner = {**contrato_externo, "inner_fold": j,
                                      "candidato": candidato,
                                      "hash_inner_treino": _sha_array(tr.astype(np.int64)),
                                      "hash_inner_validacao": _sha_array(va.astype(np.int64))}
                    caminho = pasta_cache / f"{tipo}_{familia}_outer{numero}_{candidato['id']}_inner{j}.json"
                    salvo = _ler_checkpoint(caminho, contrato_inner)
                    if salvo is None:
                        pred, segundos = _ajustar_prever(candidato, x.iloc[tr], alvo[tr], x.iloc[va])
                        perda = float(log_loss(alvo[va], pred, labels=[0, 1]))
                        salvo = {"status": "CONCLUIDO", "contrato": contrato_inner,
                                 "n_treino": len(tr), "n_validacao": len(va),
                                 "log_loss": perda, "segundos": segundos}
                        _salvar_json_novo(caminho, salvo)
                        fits_realizados += 1
                        print(f"{tipo} {familia} {candidato['id']} outer={numero} inner={j} "
                              f"concluído {segundos:.1f}s checkpoint salvo", flush=True)
                        del pred
                    else:
                        fits_reutilizados += 1
                    perdas.append(salvo["log_loss"])
                    tempos.append(salvo["segundos"])
                resultado = {"id": candidato["id"], "historico": candidato["historico"],
                             "log_loss": float(np.mean(perdas)),
                             "log_loss_se_folds": float(np.std(perdas, ddof=1) / sqrt(len(perdas))),
                             "segundos_internos": float(sum(tempos)),
                             "outer_fold": numero}
                resultados.append(resultado)
                candidatos_internos.append(resultado)
            escolha = escolher_um_ep(resultados)
            candidato = next(c for c in especificacoes if c["id"] == escolha["id"])
        else:
            candidato = especificacoes[0]
            escolha = {"id": candidato["id"], "historico": candidato["historico"],
                       "log_loss": None, "log_loss_se_folds": None}
        contrato_pred = {**contrato_externo, "escolha": escolha["id"]}
        prefixo = pasta_cache / f"{tipo}_{familia}_outer{numero}_pred"
        metadata = _ler_checkpoint(prefixo.with_suffix(".json"), contrato_pred)
        if metadata is None:
            if prefixo.with_suffix(".npz").exists():
                raise ValueError(f"Checkpoint incompleto: {prefixo}")
            pred, segundos = _ajustar_prever(candidato, x.iloc[treino], alvo[treino],
                                             x.iloc[validacao])
            np.savez_compressed(prefixo.with_suffix(".npz"), pred=pred)
            metadata = {"status": "CONCLUIDO", "contrato": contrato_pred,
                        "n_treino": len(treino), "n_validacao": len(validacao),
                        "segundos": segundos, "pred_sha256": _sha_array(pred.astype("<f8"))}
            _salvar_json_novo(prefixo.with_suffix(".json"), metadata)
            fits_realizados += 1
            print(f"{tipo} {familia} {candidato['id']} outer={numero} "
                  f"concluído {segundos:.1f}s checkpoint salvo", flush=True)
        else:
            with np.load(prefixo.with_suffix(".npz")) as cache:
                pred = cache["pred"]
            if pred.shape != (len(validacao),) or _sha_array(pred.astype("<f8")) != metadata["pred_sha256"]:
                raise ValueError(f"Checkpoint incompatível: {prefixo}")
            fits_reutilizados += 1
        oof[validacao] = pred
        cobertura[validacao] += 1
        metricas = metricas_probabilidade(alvo[validacao], pred)
        if tipo == "propensity":
            metricas.update(diagnosticos_propensity(x.iloc[validacao], alvo[validacao], pred))
        folds.append({"outer_fold": numero, "familia": familia, "escolhido": candidato["id"],
                      "n_treino": len(treino), "n_validacao": len(validacao),
                      "hash_treino": contrato_externo["hash_treino"],
                      "hash_validacao": contrato_externo["hash_validacao"],
                      "n_validacao_usado_na_selecao": 0,
                      "segundos_refit": metadata["segundos"], **metricas})
        del pred
        gc.collect()
    if not np.all(cobertura == 1) or not np.isfinite(oof).all():
        raise RuntimeError("Cobertura externa diferente de 1 ou predição ausente.")
    metricas_oof = metricas_probabilidade(alvo, oof)
    if tipo == "propensity":
        metricas_oof.update(diagnosticos_propensity(x, alvo, oof))
    perdas_fold = [f["log_loss"] for f in folds]
    metricas_oof["log_loss_se_folds"] = float(np.std(perdas_fold, ddof=1) / sqrt(len(folds)))
    return {"tipo": tipo, "familia": familia, "n": len(x),
            "n_t0": int(np.sum(alvo == 0)) if tipo == "propensity" else None,
            "n_t1": int(np.sum(alvo == 1)) if tipo == "propensity" else None,
            "metricas_oof": metricas_oof, "folds": folds,
            "candidatos_internos": candidatos_internos,
            "oof": oof, "cobertura_min": int(cobertura.min()),
            "cobertura_max": int(cobertura.max()),
            "fits_previstos": n_externos * (len(especificacoes) * n_internos + 1)
            if len(especificacoes) > 1 else n_externos,
            "fits_realizados": fits_realizados, "fits_reutilizados": fits_reutilizados,
            "segundos_sessao": perf_counter() - inicio_total}


def executar_outcome(x: pd.DataFrame, t, y, braco: int, familia: str,
                     especificacoes: list[dict], pasta_cache: Path, contrato: dict,
                     *, n_externos: int = 3, n_internos: int = 3,
                     seed: int = SEED) -> dict:
    """Filtra o braço antes de qualquer partição ou escolha de hiperparâmetro."""
    validar_x(x)
    t = np.asarray(t, dtype=np.int8)
    y = np.asarray(y, dtype=np.int8)
    if braco not in (0, 1) or len(t) != len(x) or len(y) != len(x):
        raise ValueError("Dimensões ou braço inválidos.")
    if set(np.unique(t)) != {0, 1} or not set(np.unique(y)).issubset({0, 1}):
        raise ValueError("T/Y devem ser binários.")
    mascara = t == braco
    resultado = executar_familia(x.loc[mascara].reset_index(drop=True), y[mascara],
                                 f"outcome_t{braco}", familia, especificacoes,
                                 pasta_cache, {**contrato, "braco": braco},
                                 n_externos=n_externos, n_internos=n_internos, seed=seed)
    resultado["braco"] = braco
    return resultado


def media_macro(metricas_t0: dict, metricas_t1: dict) -> dict[str, float]:
    chaves = ("log_loss", "brier", "auc", "erro_calibracao_medio",
              "erro_calibracao_maximo", "prevalencia", "media_predita")
    return {chave: (float(metricas_t0[chave]) + float(metricas_t1[chave])) / 2
            for chave in chaves}


def amostra_viabilidade(t, n: int = 150_000, seed: int = SEED) -> np.ndarray:
    """Amostra determinística estratificada somente para custo, nunca seleção."""
    t = np.asarray(t, dtype=np.int8)
    if n >= len(t):
        return np.arange(len(t))
    indices, _ = train_test_split(np.arange(len(t)), train_size=n, stratify=t,
                                  random_state=seed)
    return np.sort(indices)


def medir_viabilidade(x: pd.DataFrame, alvo, especificacao: dict,
                      *, seed: int = SEED) -> dict:
    alvo = np.asarray(alvo, dtype=np.int8)
    tr, va = train_test_split(np.arange(len(x)), test_size=0.2, stratify=alvo,
                              random_state=seed)
    import psutil
    processo = psutil.Process()
    ram_antes = processo.memory_info().rss
    pred, segundos = _ajustar_prever(especificacao, x.iloc[tr], alvo[tr], x.iloc[va])
    ram_depois = processo.memory_info().rss
    return {"familia": especificacao["familia"], "candidato": especificacao["id"],
            "n_treino": len(tr), "n_validacao": len(va), "segundos": segundos,
            "rss_antes_bytes": ram_antes, "rss_depois_bytes": ram_depois,
            "nota": "Amostra apenas para custo; métricas preditivas não utilizadas."}
