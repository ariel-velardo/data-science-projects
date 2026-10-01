"""AIPW independente por ano, com controle positivo e caches exclusivos do notebook 09."""
from __future__ import annotations

from hashlib import sha256
import gc
import json
import os
from pathlib import Path
import platform
import shutil
from time import perf_counter

import duckdb
import numpy as np
import pandas as pd
import sklearn

from src.amostra import _criar_views, carregar_amostra
from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL, resumir_overlap
from src.inferencia_causal import calcular_aipw, diagnosticos_influencia, gerar_folds
from src.modelagem_preditiva import ajustar_modelo, criar_modelo, predizer, validar_x
from src.robustez import resumo_cluster
from src.selecao_nuisance import diagnosticos_propensity, metricas_probabilidade
from src.temporal import JANELAS, caminhos_ano


RAIZ = Path(__file__).resolve().parents[1]
SEED = 20240925
N_FOLDS = 3
PREDICOES = ("e", "m0_C1", "m1_C1", "m0_C2", "m1_C2", "e_C3")
CHAVES_HISTORICAS = (
    "data/processed/sinasc_2024.parquet", "data/raw/source_manifest.json",
    "outputs/diagnostics/fase1_amostra.json", "outputs/diagnostics/fase2_aipw.json",
    "outputs/tables/fase2_predicoes_oof.npz", "outputs/tables/fase3_c3_propensity_oof.npz",
)


def hash_arquivo(caminho: Path) -> str:
    digest = sha256()
    with Path(caminho).open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(8 * 1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def hash_vetor(valores) -> str:
    return sha256(np.ascontiguousarray(valores).tobytes()).hexdigest()


def hash_chaves(ano: int, dados: pd.DataFrame) -> str:
    digest = sha256()
    for uf, contador in zip(dados["UF_RESIDENCIA"], dados["contador"], strict=True):
        digest.update(f"{ano}|{uf}|{contador}\n".encode("utf-8"))
    return digest.hexdigest()


def normalizar_colunas_identificacao(dados: pd.DataFrame) -> pd.DataFrame:
    """Normaliza a caixa variável dos identificadores brutos, sem ambiguidade."""
    renomear = {}
    for nome, padrao in (("contador", "contador"), ("codmunres", "CODMUNRES")):
        colunas = [coluna for coluna in dados.columns if coluna.casefold() == nome]
        if len(colunas) != 1:
            raise ValueError(f"Coluna {padrao} ausente ou ambígua.")
        renomear[colunas[0]] = padrao
    return dados.rename(columns=renomear)


def validar_registros(dados: pd.DataFrame, ano: int) -> dict:
    """Valida a unidade, as sete X, T/Y, clusters e chave antes de modelar."""
    proibidas = {"APGAR1", "APGAR5", "GESTACAO", "PARTO", "CONSULTAS",
                 "CONSPRENAT", "SEMAGESTAC", "IDADEGESTACIONAL"}
    if proibidas.intersection(dados.columns):
        raise ValueError("Variável pós-tratamento presente nos registros de modelagem.")
    exigidas = ["contador", "tratamento", "Y_BAIXO_PESO",
                *COLUNAS_PROPENSITY_PRINCIPAL, "CODMUNRES"]
    if list(dados.columns) != exigidas:
        raise ValueError("Schema ou ordem das sete features divergente do contrato.")
    if dados.empty or dados[exigidas].isna().any().drop("IDADEMAE_NUM").any():
        raise ValueError("Dados vazios ou nulos críticos.")
    x = dados.loc[:, list(COLUNAS_PROPENSITY_PRINCIPAL)]
    validar_x(x)
    t = dados.tratamento.to_numpy()
    y = dados.Y_BAIXO_PESO.to_numpy()
    if set(np.unique(t)) != {0, 1} or set(np.unique(y)) != {0, 1}:
        raise ValueError("T/Y exigem ambas as classes binárias.")
    if len(np.unique(2 * t + y, return_counts=True)[0]) != 4 or np.bincount(2*t+y).min() < N_FOLDS:
        raise ValueError("Estratos T/Y insuficientes para três folds.")
    chave = pd.MultiIndex.from_arrays([dados.UF_RESIDENCIA, dados.contador])
    if chave.has_duplicates or dados.contador.isna().any():
        raise ValueError("chave temporal duplicada ou ausente.")
    if ano == 2024:
        if not dados.contador.is_monotonic_increasing:
            raise ValueError("ordem AIPW 2024 por contador divergente.")
    elif not pd.MultiIndex.from_arrays([dados.UF_RESIDENCIA.astype(str),
                                        dados.contador.astype(str)]).is_monotonic_increasing:
        raise ValueError("ordem temporal UF/CONTADOR divergente.")
    municipio = dados.CODMUNRES.astype(str)
    if not municipio.str.fullmatch(r"\d{6}").all() or municipio.nunique() < 2:
        raise ValueError("Município ausente, inválido ou sem clusters suficientes.")
    if not municipio.str[:2].eq(dados.UF_RESIDENCIA.astype(str)).all():
        raise ValueError("UF e município divergentes.")
    return {"ano": int(ano), "n": int(len(dados)), "n_t0": int((t == 0).sum()),
            "n_t1": int((t == 1).sum()), "features": list(x.columns),
            "chave_sha256": hash_chaves(ano, dados),
            "t_sha256": hash_vetor(np.asarray(t, dtype=np.int8)),
            "y_sha256": hash_vetor(np.asarray(y, dtype=np.int8)),
            "schema": {col: str(dados[col].dtype) for col in exigidas},
            "n_clusters": int(municipio.nunique())}


def particoes(t, y) -> tuple[list, dict]:
    folds = gerar_folds(t, y, N_FOLDS, SEED)
    cobertura = np.zeros(len(t), dtype=np.uint8)
    auditoria = []
    estratos = 2 * np.asarray(t) + np.asarray(y)
    for numero, (treino, validacao) in enumerate(folds, 1):
        if np.intersect1d(treino, validacao).size:
            raise ValueError("Leakage: treino e validação se intersectam.")
        if set(estratos[treino]) != {0, 1, 2, 3} or set(estratos[validacao]) != {0, 1, 2, 3}:
            raise ValueError("Fold sem quatro estratos T/Y.")
        cobertura[validacao] += 1
        auditoria.append({"fold": numero, "n_treino": int(len(treino)),
                         "n_validacao": int(len(validacao)),
                         "hash_treino": hash_vetor(np.asarray(treino, dtype=np.int64)),
                         "hash_validacao": hash_vetor(np.asarray(validacao, dtype=np.int64))})
    if not np.all(cobertura == 1):
        raise ValueError("Cobertura OOF inválida.")
    return folds, {"n_folds": N_FOLDS, "seed": SEED, "estratificacao": "2*T+Y",
                   "cobertura_min": 1, "cobertura_max": 1, "folds": auditoria}


def guardar_checkpoint(prefixo: Path, contrato: dict, pred: np.ndarray, log: dict) -> None:
    """Grava predições e contrato uma única vez; jamais substitui cache existente."""
    prefixo = Path(prefixo)
    caminho = prefixo.with_suffix(".npz")
    metadata = prefixo.with_suffix(".json")
    if caminho.exists() or metadata.exists():
        raise FileExistsError(f"Checkpoint já existe: {prefixo}")
    prefixo.parent.mkdir(parents=True, exist_ok=True)
    valores = np.asarray(pred, dtype=np.float64)
    if valores.ndim != 1 or not np.isfinite(valores).all() or np.any((valores < 0) | (valores > 1)):
        raise ValueError("Probabilidades OOF inválidas.")
    temporario = prefixo.with_suffix(".npz.tmp")
    with temporario.open("xb") as arquivo:
        np.savez_compressed(arquivo, pred=valores)
    os.replace(temporario, caminho)
    conteudo = {"status": "CONCLUIDO", "contrato": contrato,
                "pred_sha256": hash_vetor(valores), "arquivo_sha256": hash_arquivo(caminho),
                "n": int(len(valores)), "log": log}
    with metadata.open("x", encoding="utf-8") as arquivo:
        json.dump(conteudo, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
        arquivo.write("\n")


def ler_checkpoint(prefixo: Path, contrato: dict) -> tuple[np.ndarray, dict] | None:
    prefixo = Path(prefixo)
    caminho = prefixo.with_suffix(".npz")
    metadata = prefixo.with_suffix(".json")
    if not caminho.exists() and not metadata.exists():
        return None
    if not caminho.exists() or not metadata.exists():
        raise ValueError(f"Checkpoint incompleto: {prefixo}")
    salvo = json.loads(metadata.read_text(encoding="utf-8"))
    if salvo.get("contrato") != contrato or salvo.get("status") != "CONCLUIDO":
        raise ValueError(f"Checkpoint incompatível: {prefixo}")
    if hash_arquivo(caminho) != salvo["arquivo_sha256"]:
        raise ValueError(f"Checkpoint corrompido: {prefixo}")
    with np.load(caminho) as arquivo:
        pred = arquivo["pred"]
    if len(pred) != salvo["n"] or hash_vetor(pred) != salvo["pred_sha256"]:
        raise ValueError(f"Predições incompatíveis: {prefixo}")
    return pred, salvo["log"]


def resumir_aipw(dados: pd.DataFrame, pred: dict, ano: int) -> list[dict]:
    """Aplica as duas regras pré-fixadas a C1/C2/C3 com SE iid e municipal."""
    t = dados.tratamento.to_numpy(dtype=int)
    y = dados.Y_BAIXO_PESO.to_numpy(dtype=int)
    grupos = dados.CODMUNRES.to_numpy(dtype=str)
    linhas = []
    for spec, nome_e, outcome, rotulo_e, rotulo_m in (
        ("C1", "e", "C1", "logistica_C1", "logistica_historica"),
        ("C2", "e", "C2", "logistica_C1", "hgb_historico"),
        ("C3", "e_C3", "C2", "hgb_historico", "hgb_historico"),
    ):
        e = np.asarray(pred[nome_e], dtype=float)
        m0 = np.asarray(pred[f"m0_{outcome}"], dtype=float)
        m1 = np.asarray(pred[f"m1_{outcome}"], dtype=float)
        for regra, lo, hi in (("sem_trimming", 0., 1.), ("0.05_0.95", .05, .95)):
            if not all(np.isfinite(v).all() for v in (e, m0, m1)):
                linhas.append({"ano": int(ano), "especificacao": spec, "trimming": regra,
                               "status": "BLOQUEADO", "motivo": "Nuisance OOF incompleto",
                               "estimativa_pp": None, "propensity_modelo": rotulo_e,
                               "outcome_modelo": rotulo_m})
                continue
            mask = (e >= lo) & (e <= hi)
            if not (t[mask] == 0).any() or not (t[mask] == 1).any():
                linhas.append({"ano": int(ano), "especificacao": spec, "trimming": regra,
                               "status": "BLOQUEADO", "motivo": "Suporte sem ambos os braços",
                               "estimativa_pp": None, "propensity_modelo": rotulo_e,
                               "outcome_modelo": rotulo_m})
                continue
            iid, psi = calcular_aipw(y[mask], t[mask], e[mask], m0[mask], m1[mask])
            cluster = resumo_cluster(psi, grupos[mask])
            influencia = diagnosticos_influencia(psi, t[mask], e[mask])
            pesos = influencia["pesos_por_grupo"]
            linhas.append({"ano": int(ano), "especificacao": spec, "trimming": regra,
                           "n": iid["n"], "n_t0": iid["n_t0"], "n_t1": iid["n_t1"],
                           "n_excluido": int((~mask).sum()),
                           "estimativa_pp": iid["estimativa_pp"],
                           "se_iid_pp": iid["se_pp"],
                           "ic95_iid_inferior_pp": iid["ic95_inferior_pp"],
                           "ic95_iid_superior_pp": iid["ic95_superior_pp"],
                           "se_cluster_pp": cluster["se_cluster_pp"],
                           "ic95_cluster_inferior_pp": cluster["ic95_cluster_inferior_pp"],
                           "ic95_cluster_superior_pp": cluster["ic95_cluster_superior_pp"],
                           "n_clusters": cluster["n_clusters"],
                           "ess_t0": pesos["0"]["ess"], "ess_t1": pesos["1"]["ess"],
                           "ess_t0_sobre_n": pesos["0"]["ess"] / iid["n_t0"],
                           "ess_t1_sobre_n": pesos["1"]["ess"] / iid["n_t1"],
                           "fora_005_095_fracao": float(np.mean((e < .05) | (e > .95))),
                           "propensity_min": float(e.min()), "propensity_max": float(e.max()),
                           "top1_if2": influencia["frac_variancia_top1pct"],
                           "propensity_modelo": rotulo_e, "outcome_modelo": rotulo_m,
                           "status": "CONCLUIDO"})
    return linhas


def montar_janelas(linhas: list[dict]) -> tuple[list[dict], list[dict]]:
    principal = [r for r in linhas if r["ano"] in JANELAS["principal"]["anos"]]
    sensibilidade = [r for r in principal if r["ano"] in JANELAS["sensibilidade"]["anos"]]
    if sensibilidade != [r for r in principal if 2018 <= r["ano"] <= 2024]:
        raise ValueError("Janelas divergentes.")
    return principal, sensibilidade


def _json(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _salvar_json(caminho: Path, objeto: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    temporario.write_text(json.dumps(objeto, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                         encoding="utf-8")
    os.replace(temporario, caminho)


def _salvar_csv(caminho: Path, linhas: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    pd.DataFrame(linhas).to_csv(temporario, index=False)
    os.replace(temporario, caminho)


def _rss() -> int | None:
    try:
        import psutil
        info = psutil.Process().memory_info()
        return int(getattr(info, "peak_wset", info.rss))
    except ImportError:
        return None


def _memoria_disponivel() -> int | None:
    try:
        import psutil
        return int(psutil.virtual_memory().available)
    except ImportError:
        return None


def verificar_baseline(raiz: Path = RAIZ) -> dict:
    referencia = _json(raiz / "outputs/temporal/modelos_nuisance/baseline_hashes_iniciais.json")
    divergencias = []
    for nome, esperado in referencia.items():
        if nome.startswith("data/interim/temporal_overlap/"):
            continue
        caminho = raiz / nome
        if not caminho.is_file() or hash_arquivo(caminho) != esperado:
            divergencias.append(nome)
    return {"status": "BASELINE_2024_PRESERVADO" if not divergencias else "BASELINE_2024_COMPROMETIDO",
            "n_artefatos": sum(not n.startswith("data/interim/temporal_overlap/") for n in referencia),
            "divergencias": divergencias}


def carregar_dados_ano(raiz: Path, ano: int) -> tuple[pd.DataFrame, dict]:
    """Lê só o ano solicitado, reproduzindo a projeção e a ordem congeladas."""
    raiz = Path(raiz)
    contrato_temporal = _json(raiz / "outputs/temporal/contrato_temporal.json")
    veredito = contrato_temporal["vereditos"][str(ano)]
    if veredito["v1.1"] not in ("APROVADO", "APROVADO_COM_HARMONIZACAO"):
        raise ValueError(f"Ano {ano} não admitido em v1.1.")
    if ano >= 2018 and veredito["v1"] != "APROVADO":
        raise ValueError(f"Ano {ano} não admitido em v1 estrito.")
    caminhos = caminhos_ano(raiz, ano)
    if not caminhos.parquet.is_file():
        raise ValueError(f"Parquet ausente: {caminhos.parquet}")
    parquet_sha = hash_arquivo(caminhos.parquet)
    if ano == 2024:
        historico = _json(raiz / "outputs/diagnostics/fase2_aipw.json")
        if parquet_sha != historico["provenance"]["parquet_sha256"]:
            raise ValueError("Parquet 2024 divergente do certificado.")
        inicio = perf_counter()
        bruto, _ = carregar_amostra(caminhos.parquet)
        bruto = normalizar_colunas_identificacao(bruto)
        dados = bruto.loc[:, ["contador", "tratamento", "Y_BAIXO_PESO",
                              *COLUNAS_PROPENSITY_PRINCIPAL, "CODMUNRES"]].copy()
        regra = "ORDER BY contador (AIPW histórico)"
    else:
        manifesto = _json(caminhos.manifesto)
        if parquet_sha != manifesto["conversao"]["parquet_sha256"]:
            raise ValueError(f"Hash do Parquet {ano} diverge do manifesto.")
        inicio = perf_counter()
        with duckdb.connect() as conexao:
            _criar_views(conexao, caminhos.parquet)
            sql = conexao.execute(
                "SELECT sql FROM duckdb_views() WHERE view_name='amostra_principal'"
            ).fetchone()[0]
            projecao = sql[sql.index(" AS SELECT ") + 4:sql.index(" FROM fase1_base")]
            consulta = (projecao + ", CODMUNRES FROM fase1_base "
                        "WHERE tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num = 1 "
                        "ORDER BY UF_RESIDENCIA, CAST(contador AS VARCHAR)")
            bruto = conexao.execute(consulta).df()
            datas_invalidas = conexao.execute(
                "SELECT count(*) FROM sinasc WHERE try_strptime(DTNASC,'%d%m%Y') IS NULL "
                f"OR year(try_strptime(DTNASC,'%d%m%Y')) <> {ano}"
            ).fetchone()[0]
        if datas_invalidas:
            raise ValueError(f"Datas inválidas/fora do ano {ano}: {datas_invalidas}")
        bruto = normalizar_colunas_identificacao(bruto)
        dados = bruto.loc[:, ["contador", "tratamento", "Y_BAIXO_PESO",
                              *COLUNAS_PROPENSITY_PRINCIPAL, "CODMUNRES"]].copy()
        regra = "ORDER BY UF_RESIDENCIA, CAST(CONTADOR AS VARCHAR)"
    contrato = validar_registros(dados, ano)
    auditoria = pd.read_csv(raiz / "outputs/temporal/tabelas/auditoria_anos.csv")
    esperado = auditoria.loc[auditoria.ano.eq(ano)].iloc[0]
    if contrato["n"] != int(esperado.n_apos_regras_basicas):
        raise ValueError(f"N de {ano} diverge do fluxo A3 certificado.")
    contrato.update(parquet_sha256=parquet_sha, ordem=regra,
                    tempo_leitura_preparo_segundos=perf_counter() - inicio)
    print(f"{ano} | preparo | N={len(dados)} | {contrato['tempo_leitura_preparo_segundos']:.1f}s | RSS={_rss()}", flush=True)
    return dados, contrato


def _contrato_fit(entrada: dict, fold: dict, nome: str, tipo: str,
                  alvo: np.ndarray, modelo) -> dict:
    parametros = {k: v for k, v in modelo["modelo"].get_params().items()
                  if isinstance(v, (str, int, float, bool, type(None), list))}
    return {"ano": entrada["ano"], "modelo": nome, "fold": fold["fold"],
            "parquet_sha256": entrada["parquet_sha256"], "n": entrada["n"],
            "n_t0": entrada["n_t0"], "n_t1": entrada["n_t1"],
            "t_sha256": entrada["t_sha256"], "y_sha256": entrada["y_sha256"],
            "features": entrada["features"], "schema": entrada["schema"],
            "ordem": entrada["ordem"], "chave_sha256": entrada["chave_sha256"],
            "seed": SEED, "n_folds": N_FOLDS,
            "hash_treino": fold["hash_treino"], "hash_validacao": fold["hash_validacao"],
            "alvo_sha256": hash_vetor(np.asarray(alvo, dtype=np.int8)),
            "tipo": tipo, "parametros": parametros,
            "preprocessing": repr(modelo["preprocessamento"]),
            "codigo_sha256": {nome: hash_arquivo(RAIZ / "src" / nome)
                              for nome in ("estimativas_temporais.py", "modelagem_preditiva.py",
                                           "inferencia_causal.py", "robustez.py", "amostra.py", "temporal.py")},
            "python": platform.python_version(), "sklearn": sklearn.__version__,
            "duckdb": duckdb.__version__, "numpy": np.__version__}


def ajustar_ano(dados: pd.DataFrame, entrada: dict, pasta_cache: Path) -> tuple[dict, dict]:
    """Executa os 18 fits de um ano, ou lê checkpoints compatíveis por modelo/fold."""
    x = dados.loc[:, list(COLUNAS_PROPENSITY_PRINCIPAL)]
    t = dados.tratamento.to_numpy(dtype=int)
    y = dados.Y_BAIXO_PESO.to_numpy(dtype=int)
    folds, auditoria = particoes(t, y)
    pred = {nome: np.full(len(dados), np.nan, dtype=np.float64) for nome in PREDICOES}
    tempos = []
    for numero, (treino, validacao) in enumerate(folds, 1):
        info = auditoria["folds"][numero - 1]
        tarefas = [("e", "logistica", treino, t[treino]),
                   ("m0_C1", "logistica", treino[t[treino] == 0], y[treino[t[treino] == 0]]),
                   ("m1_C1", "logistica", treino[t[treino] == 1], y[treino[t[treino] == 1]]),
                   ("m0_C2", "hgb", treino[t[treino] == 0], y[treino[t[treino] == 0]]),
                   ("m1_C2", "hgb", treino[t[treino] == 1], y[treino[t[treino] == 1]]),
                   ("e_C3", "hgb", treino, t[treino])]
        for nome, tipo, indices, alvo in tarefas:
            modelo = criar_modelo(tipo)
            contrato = _contrato_fit(entrada, info, nome, tipo, alvo, modelo)
            prefixo = pasta_cache / str(entrada["ano"]) / f"{nome}_fold{numero}"
            inicio = perf_counter()
            salvo = ler_checkpoint(prefixo, contrato)
            if salvo is None:
                try:
                    modelo, ajuste = ajustar_modelo(modelo, x.iloc[indices], alvo)
                    valores = predizer(modelo, x.iloc[validacao])
                except RuntimeError as erro:
                    if nome != "e_C3":
                        raise
                    print(f"{entrada['ano']} | C3 | fold {numero}/3 | BLOQUEADO: {erro}", flush=True)
                    tempos.append({"ano": entrada["ano"], "modelo": nome, "fold": numero,
                                   "segundos_sessao": perf_counter() - inicio,
                                   "reutilizado": False, "status": "BLOQUEADO", "motivo": str(erro)})
                    del modelo
                    gc.collect()
                    continue
                segundos = perf_counter() - inicio
                log = {"segundos_fit": segundos, "ajuste": ajuste,
                       "rss_pico_bytes": _rss(), "reutilizado": False}
                guardar_checkpoint(prefixo, contrato, valores, log)
                print(f"{entrada['ano']} | {nome} | fold {numero}/3 | {segundos:.1f}s | RSS={log['rss_pico_bytes']} | checkpoint OK", flush=True)
            else:
                valores, log = salvo
                segundos = perf_counter() - inicio
                print(f"{entrada['ano']} | {nome} | fold {numero}/3 | cache OK", flush=True)
            if len(valores) != len(validacao):
                raise ValueError(f"Tamanho OOF inválido: {prefixo}")
            pred[nome][validacao] = valores
            tempos.append({"ano": entrada["ano"], "modelo": nome, "fold": numero,
                           "segundos_sessao": segundos, "segundos_fit": log.get("segundos_fit", 0),
                           "reutilizado": bool(salvo), "rss_pico_bytes": _rss()})
            del modelo, valores
            gc.collect()
        del tarefas
    if any(not np.isfinite(pred[nome]).all() for nome in PREDICOES if nome != "e_C3"):
        raise ValueError("OOF incompleto ou inválido.")
    return pred, {"folds": auditoria, "tempos": tempos}


def diagnosticos_ano(dados: pd.DataFrame, pred: dict, ano: int) -> list[dict]:
    x = dados.loc[:, list(COLUNAS_PROPENSITY_PRINCIPAL)]
    t = dados.tratamento.to_numpy(dtype=int)
    y = dados.Y_BAIXO_PESO.to_numpy(dtype=int)
    linhas = []
    for nome, rotulo in (("e", "logistica_C1"), ("e_C3", "hgb_historico")):
        e = pred[nome]
        if not np.isfinite(e).all():
            linhas.append({"ano": ano, "alvo": "propensity", "modelo": rotulo,
                           "status": "BLOQUEADO", "motivo": "OOF incompleto"})
            continue
        d = {**metricas_probabilidade(t, e), **diagnosticos_propensity(x, t, e)}
        suporte = resumir_overlap(e, t)["suporte_comum_observado"]
        d.update(ano=ano, alvo="propensity", modelo=rotulo,
                 suporte_comum_inferior=suporte["inferior"],
                 suporte_comum_superior=suporte["superior"])
        linhas.append(d)
    for nome in ("m0_C1", "m1_C1", "m0_C2", "m1_C2"):
        grupo = int(nome[1])
        mask = t == grupo
        d = metricas_probabilidade(y[mask], pred[nome][mask])
        d.update(ano=ano, alvo=f"outcome_t{grupo}", modelo=nome)
        linhas.append(d)
    return linhas


def sinalizacoes(diagnosticos: list[dict], linhas: list[dict]) -> list[str]:
    avisos = []
    for d in diagnosticos:
        if d["alvo"] != "propensity" or d.get("status") == "BLOQUEADO":
            continue
        nome = d["modelo"]
        if d["max_abs_smd_ponderado"] > .10:
            avisos.append(f"{nome}: SMD ponderado > 0,10")
        if d["fora_005_095_fracao"] > .10:
            avisos.append(f"{nome}: caudas > 10%")
        if min(d["ess_t0_sobre_n"], d["ess_t1_sobre_n"]) < .50:
            avisos.append(f"{nome}: ESS/N < 0,50")
    for r in linhas:
        if r["status"] == "BLOQUEADO":
            continue
        if r["top1_if2"] > .50:
            avisos.append(f"{r['especificacao']}/{r['trimming']}: influência concentrada")
        if r["se_iid_pp"] and r["se_cluster_pp"] / r["se_iid_pp"] > 2:
            avisos.append(f"{r['especificacao']}/{r['trimming']}: SE cluster > 2x iid")
    return avisos


def predicoes_certificadas_2024(raiz: Path, dados: pd.DataFrame,
                                entrada: dict) -> tuple[dict, dict]:
    """Reusa arrays históricos apenas após validar bytes, ordem e folds."""
    referencia = _json(raiz / "outputs/temporal/modelos_nuisance/baseline_hashes_iniciais.json")
    nomes = ("outputs/tables/fase2_predicoes_oof.npz",
             "outputs/tables/fase3_c3_propensity_oof.npz")
    hashes = {}
    for nome in nomes:
        hashes[nome] = hash_arquivo(raiz / nome)
        if hashes[nome] != referencia[nome]:
            raise ValueError(f"Cache histórico divergente: {nome}")
    fase2 = _json(raiz / "outputs/diagnostics/fase2_aipw.json")
    if (entrada["parquet_sha256"] != fase2["provenance"]["parquet_sha256"]
            or entrada["features"] != fase2["provenance"]["x"]
            or fase2["provenance"]["seed"] != SEED
            or fase2["provenance"]["ordem"] != "contador"):
        raise ValueError("Contrato AIPW 2024 incompatível com cache certificado.")
    folds, auditoria = particoes(dados.tratamento.to_numpy(),
                                dados.Y_BAIXO_PESO.to_numpy())
    for info, antigo in zip(auditoria["folds"], fase2["folds"], strict=True):
        if (info["n_treino"] != antigo["n_treino"]
                or info["n_validacao"] != antigo["n_validacao"]
                or info["hash_validacao"] != antigo["sha256_indices_validacao"]):
            raise ValueError("Folds 2024 não reconciliam com a Fase 2.")
    with np.load(raiz / nomes[0]) as arquivo:
        pred = {nome: arquivo[nome] for nome in PREDICOES if nome != "e_C3"}
        cobertura = arquivo["cobertura"]
        fold_id = arquivo["fold_id"]
    if len(cobertura) != len(dados) or not np.all(cobertura == 1):
        raise ValueError("Cobertura histórica OOF inválida.")
    for numero, (_, validacao) in enumerate(folds, 1):
        if not np.all(fold_id[validacao] == numero):
            raise ValueError("fold_id histórico divergente.")
    with np.load(raiz / nomes[1]) as arquivo:
        if not np.array_equal(arquivo["contador"], dados.contador.to_numpy(dtype=str)):
            raise ValueError("Ordem/contador C3 histórico divergente.")
        pred["e_C3"] = arquivo["e_C3"]
    if any(len(v) != len(dados) or not np.isfinite(v).all() for v in pred.values()):
        raise ValueError("Predições OOF históricas inválidas.")
    return pred, {"origem": "caches históricos somente leitura", "hashes": hashes,
                  "folds": auditoria, "chave_sha256": entrada["chave_sha256"]}


def reconciliar_2024(raiz: Path, entrada: dict, linhas: list[dict],
                     diagnosticos: list[dict], cache: dict) -> dict:
    fase2 = _json(raiz / "outputs/diagnostics/fase2_aipw.json")
    fase3 = _json(raiz / "outputs/diagnostics/fase3_sensibilidades.json")["S0"]
    checks = {"n": entrada["n"] == fase2["provenance"]["n"],
              "parquet": entrada["parquet_sha256"] == fase2["provenance"]["parquet_sha256"],
              "features": entrada["features"] == fase2["provenance"]["x"],
              "folds": len(cache["folds"]["folds"]) == fase2["n_folds"] == 3}
    deltas = {}
    for linha in linhas:
        spec = linha["especificacao"]
        regra = linha["trimming"]
        id_ = f"{spec}_{regra}"
        if linha["status"] != "CONCLUIDO":
            checks[id_] = False
            continue
        historico3 = next(r for r in fase3["resultados"]
                          if r["especificacao"] == spec and r["populacao"] == regra)
        historico2 = (next(r for r in fase2["resultados"]
                           if r["especificacao"] == spec and r["populacao"] == regra)
                      if spec in ("C1", "C2") else None)
        esperado = historico2 or historico3
        campos = ("n", "n_t0", "n_t1", "n_excluido", "estimativa_pp",
                  "se_cluster_pp", "ic95_cluster_inferior_pp",
                  "ic95_cluster_superior_pp", "n_clusters")
        for campo in campos:
            fonte = historico3 if campo in ("se_cluster_pp", "ic95_cluster_inferior_pp",
                                           "ic95_cluster_superior_pp", "n_clusters") else esperado
            observado = linha[campo]
            valor = fonte[campo]
            delta = float(observado - valor)
            deltas[f"{id_}_{campo}"] = delta
            checks[f"{id_}_{campo}"] = (delta == 0 if campo in ("n", "n_t0", "n_t1",
                                                               "n_excluido", "n_clusters")
                                           else abs(delta) <= 1e-12)
        for novo, antigo in (("se_iid_pp", "se_pp"),
                             ("ic95_iid_inferior_pp", "ic95_inferior_pp"),
                             ("ic95_iid_superior_pp", "ic95_superior_pp")):
            delta = float(linha[novo] - esperado[antigo])
            deltas[f"{id_}_{novo}"] = delta
            checks[f"{id_}_{novo}"] = abs(delta) <= 1e-12
    for d in diagnosticos:
        if d["alvo"] != "propensity":
            continue
        spec = "C3" if d["modelo"] == "hgb_historico" else "C1"
        esperado = fase3["nuisance"][spec]["propensity"]
        if "roc_auc" in esperado:
            checks[f"{spec}_auc"] = abs(d["auc"] - esperado["roc_auc"]) <= 1e-12
    falhas = sorted(k for k, valido in checks.items() if not valido)
    return {"status": "CONTROLE_POSITIVO_2024_APROVADO" if not falhas
            else "CONTROLE_POSITIVO_2024_REPROVADO", "tolerancia_absoluta": 1e-12,
            "checks": checks, "falhas": falhas, "deltas": deltas,
            "cache": cache, "n": entrada["n"], "n_t0": entrada["n_t0"],
            "n_t1": entrada["n_t1"]}


def _projecao_custo(segundos_2024: float, rss_pico: int | None,
                    disco_livre: int, memoria_livre: int | None) -> dict:
    runtime = pd.read_csv(RAIZ / "outputs/temporal/modelos_nuisance/benchmark_runtime.csv")
    historico = runtime.loc[runtime.familia.eq("hgb_historico"), "segundos_certificados"].sum()
    outcomes_log = runtime.loc[(runtime.familia.eq("logistica"))
                               & (runtime.alvo.ne("propensity")), "segundos_certificados"].sum()
    propensity_log = pd.read_csv(RAIZ / "outputs/temporal/modelos_nuisance/custo_projetado.csv")
    propensity_log = float(propensity_log.loc[(propensity_log.alvo.eq("propensity"))
                                          & (propensity_log.familia.eq("logistica")),
                                          "segundos_projetados"].iloc[0])
    fit_ano = float(historico + outcomes_log + propensity_log)
    # Custo observado de leitura, diagnósticos e reconciliação de 2024; 2x para anos maiores.
    extra_ano = 2 * segundos_2024
    projecao = 10 * (fit_ano + extra_ano)
    cache_estimado = 3 * 1024**3
    memoria_segura = (memoria_livre is not None and memoria_livre >= 8 * 1024**3
                      and (rss_pico is None or memoria_livre >= 2 * rss_pico))
    disco_seguro = disco_livre >= max(6 * 1024**3, 2 * cache_estimado)
    return {"fit_por_ano_segundos": fit_ano, "overhead_por_ano_segundos": extra_ano,
            "restante_2014_2023_segundos": projecao,
            "restante_2014_2023_horas": projecao / 3600,
            "limite_horas": 6, "rss_pico_2024_bytes": rss_pico,
            "memoria_livre_bytes": memoria_livre, "memoria_segura": memoria_segura,
            "disco_livre_bytes": disco_livre, "cache_estimado_bytes": cache_estimado,
            "disco_seguro": disco_seguro,
            "continuar": projecao <= 6 * 3600 and memoria_segura and disco_seguro}


def _persistir_tabelas(pasta: Path, efeitos: list[dict], diagnosticos: list[dict],
                       execucoes: list[dict]) -> None:
    _salvar_csv(pasta / "aipw_anual.csv", efeitos)
    _salvar_csv(pasta / "diagnosticos_nuisance_anual.csv", diagnosticos)
    _salvar_csv(pasta / "execucao_anos.csv", execucoes)
    validas = [r for r in efeitos if r["status"] != "BLOQUEADO"]
    principal, sensibilidade = montar_janelas(validas)
    _salvar_csv(pasta / "aipw_janela_principal.csv", principal)
    _salvar_csv(pasta / "aipw_sensibilidade_2018_2024.csv", sensibilidade)
    _salvar_csv(pasta / "inferencia_anual.csv", [
        {k: r.get(k) for k in ("ano", "especificacao", "trimming", "n", "n_clusters",
                               "estimativa_pp", "se_iid_pp", "ic95_iid_inferior_pp",
                               "ic95_iid_superior_pp", "se_cluster_pp",
                               "ic95_cluster_inferior_pp", "ic95_cluster_superior_pp", "status")}
        for r in efeitos])


def _conferir_reexecucao_anual(caminho: Path, linhas: list[dict]) -> None:
    """Protege resultados já gravados quando uma correção técnica exige novos fits."""
    if not caminho.exists():
        return
    anterior = _json(caminho)["efeitos"]
    por_chave = {(r["especificacao"], r["trimming"]): r for r in anterior}
    if len(por_chave) != len(linhas):
        raise ValueError(f"Reexecução anual incompatível: {caminho}")
    for atual in linhas:
        salvo = por_chave.get((atual["especificacao"], atual["trimming"]))
        if salvo is None:
            raise ValueError(f"Especificação anual ausente na reexecução: {caminho}")
        for campo in ("n", "n_t0", "n_t1", "n_excluido", "estimativa_pp",
                      "se_iid_pp", "se_cluster_pp"):
            if abs(atual[campo] - salvo[campo]) > 1e-12:
                raise ValueError(f"Reexecução anual divergiu em {campo}: {caminho}")


def executar_analise(raiz: Path = RAIZ) -> dict:
    """Reconcilia 2024 e só prossegue se os dez gates operacionais permitirem."""
    raiz = Path(raiz)
    pasta = raiz / "outputs/temporal/estimativas"
    # v1 permanece intacto após a correção da capitalização de 2016.
    cache_raiz = raiz / "data/interim/estimativas_temporais/v2"
    plano = raiz / "docs/temporal/PLANO_NOTEBOOK_09.md"
    plano_sha = hash_arquivo(plano)
    if plano_sha != "2663d33b0e5b4ed4b137b615a33e96a9afb8be7e1ec594a37b6488118762c484":
        raise ValueError("Plano 09 diverge do SHA-256 congelado antes dos efeitos.")
    baseline_antes = verificar_baseline(raiz)
    if baseline_antes["status"] != "BASELINE_2024_PRESERVADO":
        raise ValueError(f"Baseline histórico divergente: {baseline_antes['divergencias']}")
    efeitos: list[dict] = []
    diagnosticos: list[dict] = []
    execucoes: list[dict] = []
    inicio_2024 = perf_counter()
    dados, entrada = carregar_dados_ano(raiz, 2024)
    pred, cache24 = predicoes_certificadas_2024(raiz, dados, entrada)
    diag24 = diagnosticos_ano(dados, pred, 2024)
    linhas24 = resumir_aipw(dados, pred, 2024)
    reconciliacao = reconciliar_2024(raiz, entrada, linhas24, diag24, cache24)
    tempo_2024 = perf_counter() - inicio_2024
    reconciliacao.update(tempo_total_segundos=tempo_2024,
                         tempo_leitura_preparo_segundos=entrada["tempo_leitura_preparo_segundos"],
                         rss_pico_bytes=_rss(),
                         baseline=baseline_antes)
    _salvar_json(pasta / "reconciliacao_2024.json", reconciliacao)
    _salvar_json(cache_raiz / "2024/reutilizacao_historica.json",
                 {"status": "VALIDADO", "plano_sha256": plano_sha,
                  "entrada": entrada, "cache": cache24})
    print(f"2024 | controle positivo | {reconciliacao['status']} | {tempo_2024:.1f}s | RSS={_rss()}", flush=True)
    efeitos.extend(linhas24)
    diagnosticos.extend(diag24)
    execucoes.append({"ano": 2024, "status": reconciliacao["status"],
                      "tempo_total_segundos": tempo_2024, "rss_pico_bytes": _rss(),
                      "cache": "histórico somente leitura; referência nova validada"})
    _persistir_tabelas(pasta, efeitos, diagnosticos, execucoes)
    del dados, pred
    gc.collect()
    if reconciliacao["status"] != "CONTROLE_POSITIVO_2024_APROVADO":
        return {"plano": "PLANO_NOTEBOOK_09_CONGELADO", "controle_2024": reconciliacao,
                "execucao": "EXECUCAO_TEMPORAL_PARCIAL", "anos": execucoes,
                "baseline": verificar_baseline(raiz)}
    disco = shutil.disk_usage(cache_raiz)
    custo = _projecao_custo(tempo_2024, _rss(), disco.free, _memoria_disponivel())
    _salvar_json(pasta / "orcamento_apos_2024.json", custo)
    print(f"2024 | orçamento | restante={custo['restante_2014_2023_horas']:.2f}h | "
          f"RAM segura={custo['memoria_segura']} | disco seguro={custo['disco_seguro']}", flush=True)
    if not custo["continuar"]:
        resultado = {"plano": "PLANO_NOTEBOOK_09_CONGELADO", "controle_2024": reconciliacao,
                     "execucao": "EXECUCAO_HISTORICA_ADIADA_POR_ORCAMENTO", "orcamento": custo,
                     "anos": execucoes, "baseline": verificar_baseline(raiz)}
        _salvar_json(pasta / "manifesto_notebook_09.json", resultado)
        return resultado
    status_global = "EXECUCAO_TEMPORAL_COMPLETA"
    for ano in range(2014, 2024):
        inicio_ano = perf_counter()
        try:
            dados, entrada = carregar_dados_ano(raiz, ano)
            pred, log_fit = ajustar_ano(dados, entrada, cache_raiz)
            diag = diagnosticos_ano(dados, pred, ano)
            linhas = resumir_aipw(dados, pred, ano)
            _conferir_reexecucao_anual(pasta / f"ano_{ano}.json", linhas)
            avisos = sinalizacoes(diag, linhas)
            bloqueados = [r for r in linhas if r["status"] == "BLOQUEADO"]
            status = "SINALIZADO" if avisos or bloqueados else "CONCLUIDO"
            for linha in linhas:
                linha["parquet_sha256"] = entrada["parquet_sha256"]
                linha["chave_sha256"] = entrada["chave_sha256"]
                if status == "SINALIZADO" and linha["status"] == "CONCLUIDO":
                    linha["status"] = "SINALIZADO"
            diagnosticos.extend(diag)
            efeitos.extend(linhas)
            tempo = perf_counter() - inicio_ano
            cache_bytes = sum(p.stat().st_size for p in (cache_raiz / str(ano)).rglob("*")
                              if p.is_file())
            execucao = {"ano": ano, "status": status, "n": entrada["n"],
                        "n_t0": entrada["n_t0"], "n_t1": entrada["n_t1"],
                        "tempo_total_segundos": tempo, "rss_pico_bytes": _rss(),
                        "cache_bytes": cache_bytes, "avisos": avisos,
                        "especificacoes_bloqueadas": sorted({r["especificacao"] for r in bloqueados}),
                        "parquet_sha256": entrada["parquet_sha256"],
                        "chave_sha256": entrada["chave_sha256"]}
            execucoes.append(execucao)
            _salvar_json(pasta / f"ano_{ano}.json",
                         {"entrada": entrada, "folds": log_fit["folds"],
                          "tempos": log_fit["tempos"], "execucao": execucao,
                          "efeitos": linhas, "diagnosticos": diag})
            _persistir_tabelas(pasta, efeitos, diagnosticos, execucoes)
            print(f"{ano} | ano completo | {status} | {tempo:.1f}s | RSS={_rss()} | cache={cache_bytes}", flush=True)
            del dados, pred
            gc.collect()
        except (ValueError, RuntimeError, OSError, MemoryError, KeyError) as erro:
            status_global = "EXECUCAO_TEMPORAL_PARCIAL"
            execucoes.append({"ano": ano, "status": "BLOQUEADO", "motivo": str(erro),
                              "tempo_total_segundos": perf_counter() - inicio_ano})
            _persistir_tabelas(pasta, efeitos, diagnosticos, execucoes)
            print(f"{ano} | BLOQUEADO | {erro}", flush=True)
            break
    baseline_final = verificar_baseline(raiz)
    if baseline_final["status"] != "BASELINE_2024_PRESERVADO":
        status_global = "EXECUCAO_TEMPORAL_PARCIAL"
    if len([r for r in execucoes if r["status"] in ("CONCLUIDO", "SINALIZADO")]) != 10:
        status_global = "EXECUCAO_TEMPORAL_PARCIAL"
    resultado = {"plano": "PLANO_NOTEBOOK_09_CONGELADO",
                 "plano_sha256": plano_sha, "controle_2024": reconciliacao,
                 "execucao": status_global, "orcamento": custo, "anos": execucoes,
                 "baseline": baseline_final,
                 "limitacoes": ["Confundimento não medido e seleção de nascidos vivos permanecem possíveis.",
                                "Inferência municipal não cobre automaticamente dependência entre anos."]}
    _salvar_json(pasta / "manifesto_notebook_09.json", resultado)
    return resultado
