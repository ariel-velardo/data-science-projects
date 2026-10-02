"""Estimação AIPW V2: controle positivo A/2024, B principal (1-3 vs 4-6) e C sensibilidade (1-3 vs 4-5).

Reaproveita o contrato do notebook 09 (``src.estimativas_temporais``): leitura e ordem por ano,
sete X, três partições por 2T+Y com seed 20240925, C1/C2/C3 históricos, AIPW, SE iid e SE
municipal com t(G-1). Acrescenta apenas o recorte de MESPRENAT por formulação, um cache próprio
cujo contrato inclui a formulação e a reconciliação de A/2024 com nuisances reajustados do zero.
Nenhuma predição da V1 ou do diagnóstico 09d é reutilizada; os arrays históricos são apenas lidos
para comparação no controle positivo.
"""
from __future__ import annotations

from hashlib import sha256
import gc
import inspect
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import duckdb
import numpy as np
import pandas as pd

from src import estimativas_temporais as et
from src.amostra import _criar_views
from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL
from src.inferencia_causal import calcular_aipw, diagnosticos_influencia
from src.modelagem_preditiva import ajustar_modelo, criar_modelo, predizer
from src.robustez import resumo_cluster
from src.temporal import caminhos_ano


RAIZ = et.RAIZ
VERSAO_CACHE = "estimacao-v2-aipw-1"
ANOS = tuple(range(2014, 2025))
ANO_CONTROLE = 2024
MESES_TRATADOS = (1, 2, 3)
FORMULACOES = {
    "A": {"meses": (1, 2, 3, 4, 5, 6, 7, 8, 9), "papel": "V1_HISTORICA_CONTROLE_POSITIVO",
          "referencia_09d": "A_V1"},
    "B": {"meses": (1, 2, 3, 4, 5, 6), "papel": "V2_PRINCIPAL", "referencia_09d": "B"},
    "C": {"meses": (1, 2, 3, 4, 5), "papel": "V2_SENSIBILIDADE", "referencia_09d": "C"},
}
ESPERADO_A2024 = {"n": 2251570, "n_t0": 309525, "n_t1": 1942045}
HASH_CONTRATO_V2 = "2174989c33b338f7215270050969efda1d3d8e09661aee97b1da547185927d0b"
TOLERANCIA = 1e-12
PASTA_CACHE = Path("data/interim/estimacao_v2")
PASTA_SAIDA = Path("outputs/temporal/estimacao_v2")
TAREFAS = ("e", "m0_C1", "m1_C1", "m0_C2", "m1_C2", "e_C3")


# ---------------------------------------------------------------------------
# População
# ---------------------------------------------------------------------------

def _mesprenat_alinhado(parquet: Path, ano: int) -> pd.DataFrame:
    """Chave e MESPRENAT na mesma projeção, filtro e ordem do AIPW histórico do ano."""
    ordem = ("ORDER BY contador_k" if ano == ANO_CONTROLE
             else "ORDER BY uf_k, CAST(contador_k AS VARCHAR)")
    with duckdb.connect() as conexao:
        _criar_views(conexao, parquet)
        sql = conexao.execute(
            "SELECT sql FROM duckdb_views() WHERE view_name='amostra_principal'"
        ).fetchone()[0]
        projecao = sql[sql.index(" AS SELECT ") + 4:sql.index(" FROM fase1_base")]
        consulta = ("SELECT contador AS contador_k, UF_RESIDENCIA AS uf_k, mesprenat_num FROM ("
                    + projecao + ", mesprenat_num FROM fase1_base "
                    "WHERE tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num = 1) "
                    + ordem)
        return conexao.execute(consulta).df()


def carregar_v1_com_mes(raiz: Path, ano: int) -> tuple[pd.DataFrame, np.ndarray, dict]:
    """População V1 certificada do notebook 09 e o MESPRENAT de cada registro, na mesma ordem."""
    dados, entrada = et.carregar_dados_ano(raiz, ano)
    chaves = _mesprenat_alinhado(caminhos_ano(raiz, ano).parquet, ano)
    if (len(chaves) != len(dados)
            or not np.array_equal(chaves.contador_k.astype(str).to_numpy(),
                                  dados.contador.astype(str).to_numpy())
            or not np.array_equal(chaves.uf_k.astype(str).to_numpy(),
                                  dados.UF_RESIDENCIA.astype(str).to_numpy())):
        raise ValueError(f"{ano}: MESPRENAT não alinha com a ordem/chave do AIPW histórico.")
    mes = chaves.mesprenat_num.to_numpy()
    if not np.isin(mes, FORMULACOES["A"]["meses"]).all():
        raise ValueError(f"{ano}: população V1 com MESPRENAT fora de 1-9.")
    if not np.array_equal(dados.tratamento.to_numpy(dtype=int), np.isin(mes, MESES_TRATADOS).astype(int)):
        raise ValueError(f"{ano}: T da V1 diverge de MESPRENAT 1-3.")
    return dados, mes.astype(int), entrada


def populacao(dados: pd.DataFrame, mes: np.ndarray, formulacao: str) -> tuple[pd.DataFrame, dict]:
    """Subconjunto da V1 com MESPRENAT da formulação, preservando a ordem; T não é reclassificado."""
    meses = FORMULACOES[formulacao]["meses"]
    mes = np.asarray(mes, dtype=int)
    if len(mes) != len(dados):
        raise ValueError("MESPRENAT e dados com tamanhos diferentes.")
    mascara = np.isin(mes, meses)
    sub = dados.loc[mascara].reset_index(drop=True)
    t_esperado = np.isin(mes[mascara], MESES_TRATADOS).astype(int)
    if not np.array_equal(sub.tratamento.to_numpy(dtype=int), t_esperado):
        raise ValueError(f"{formulacao}: T diverge da regra 1-3 vs {meses[3:]}.")
    valores, contagens = np.unique(mes[mascara], return_counts=True)
    return sub, {"n_por_mesprenat": {str(int(v)): int(c) for v, c in zip(valores, contagens)}}


def suporte_09d(raiz: Path) -> pd.DataFrame:
    tabela = pd.read_csv(raiz / "outputs/temporal/v2_pre_estimacao/diagnostico_suporte_v2.csv")
    return tabela.loc[:, ["formulacao", "ano", "n", "n_t0", "n_t1", "status", "motivo"]]


def entrada_formulacao(raiz: Path, sub: pd.DataFrame, ano: int, formulacao: str,
                       entrada_v1: dict, referencia: pd.DataFrame) -> dict:
    """Contrato de dados da formulação; N/T0/T1 devem reconciliar com o 09d."""
    entrada = et.validar_registros(sub, ano)
    entrada.update(parquet_sha256=entrada_v1["parquet_sha256"],
                   ordem=f"{entrada_v1['ordem']}; subconjunto MESPRENAT {list(FORMULACOES[formulacao]['meses'])}",
                   formulacao=formulacao)
    ref = referencia.loc[referencia.formulacao.eq(FORMULACOES[formulacao]["referencia_09d"])
                         & referencia.ano.eq(ano)]
    if len(ref) != 1:
        raise ValueError(f"{formulacao}/{ano}: referência 09d ausente.")
    ref = ref.iloc[0]
    if (entrada["n"], entrada["n_t0"], entrada["n_t1"]) != (int(ref.n), int(ref.n_t0), int(ref.n_t1)):
        raise ValueError(f"{formulacao}/{ano}: N/T0/T1 diverge do 09d.")
    if ref.status == "BLOQUEADO":
        raise ValueError(f"{formulacao}/{ano}: ano BLOQUEADO no 09d não deve ser estimado.")
    entrada.update(status_suporte_09d=str(ref.status), motivo_suporte_09d=str(ref.motivo))
    return entrada


# ---------------------------------------------------------------------------
# Ajuste com cache próprio
# ---------------------------------------------------------------------------

def sha256_codigo_v2() -> str:
    """Hash do código que define população, partições e ajustes (não inclui relatórios)."""
    partes = [VERSAO_CACHE, repr(FORMULACOES), repr(MESES_TRATADOS)]
    partes += [inspect.getsource(f) for f in (_mesprenat_alinhado, carregar_v1_com_mes,
                                                populacao, contrato_ajuste, ajustar)]
    return sha256("\n".join(partes).encode("utf-8")).hexdigest()


def contrato_ajuste(entrada: dict, fold: dict, nome: str, tipo: str, alvo: np.ndarray,
                    modelo, codigo_v2: str) -> dict:
    contrato = et._contrato_fit(entrada, fold, nome, tipo, alvo, modelo)
    contrato.update(versao_cache=VERSAO_CACHE, formulacao=entrada["formulacao"],
                    meses=list(FORMULACOES[entrada["formulacao"]]["meses"]),
                    estratificacao="2*T+Y", codigo_v2_sha256=codigo_v2)
    return contrato


def ajustar(dados: pd.DataFrame, entrada: dict, pasta_cache: Path) -> tuple[dict, dict]:
    """18 ajustes (6 nuisances x 3 partições) ou leitura de checkpoints com contrato idêntico.

    Cache de outro código fica em outra pasta e é ignorado; cache na mesma pasta com contrato
    divergente é rejeitado (ValueError). Falha de convergência interrompe a execução.
    """
    x = dados.loc[:, list(COLUNAS_PROPENSITY_PRINCIPAL)]
    t = dados.tratamento.to_numpy(dtype=int)
    y = dados.Y_BAIXO_PESO.to_numpy(dtype=int)
    folds, auditoria = et.particoes(t, y)
    codigo_v2 = sha256_codigo_v2()
    base = Path(pasta_cache) / f"codigo_{codigo_v2[:16]}" / entrada["formulacao"] / str(entrada["ano"])
    pred = {nome: np.full(len(dados), np.nan) for nome in TAREFAS}
    logs = []
    for numero, (treino, validacao) in enumerate(folds, 1):
        info = auditoria["folds"][numero - 1]
        t0, t1 = treino[t[treino] == 0], treino[t[treino] == 1]
        tarefas = [("e", "logistica", treino, t[treino]),
                   ("m0_C1", "logistica", t0, y[t0]), ("m1_C1", "logistica", t1, y[t1]),
                   ("m0_C2", "hgb", t0, y[t0]), ("m1_C2", "hgb", t1, y[t1]),
                   ("e_C3", "hgb", treino, t[treino])]
        for nome, tipo, indices, alvo in tarefas:
            modelo = criar_modelo(tipo)
            contrato = contrato_ajuste(entrada, info, nome, tipo, alvo, modelo, codigo_v2)
            prefixo = base / f"{nome}_fold{numero}"
            inicio = perf_counter()
            salvo = et.ler_checkpoint(prefixo, contrato)
            if salvo is None:
                modelo, log_ajuste = ajustar_modelo(modelo, x.iloc[indices], alvo)
                valores = predizer(modelo, x.iloc[validacao])
                log = {"segundos_fit": perf_counter() - inicio, "ajuste": log_ajuste,
                       "rss_pico_bytes": et._rss(), "reutilizado": False}
                et.guardar_checkpoint(prefixo, contrato, valores, log)
                print(f"{entrada['formulacao']}/{entrada['ano']} | {nome} | fold {numero}/3 | "
                      f"{log['segundos_fit']:.1f}s | ajuste novo", flush=True)
            else:
                valores, log = salvo
            if len(valores) != len(validacao):
                raise ValueError(f"Tamanho OOF inválido: {prefixo}")
            pred[nome][validacao] = valores
            logs.append({"formulacao": entrada["formulacao"], "ano": entrada["ano"], "modelo": nome,
                         "fold": numero, "reutilizado": salvo is not None,
                         "segundos_fit": float(log.get("segundos_fit", 0.0)),
                         "n_iter": log.get("ajuste", {}).get("n_iter"),
                         "tentativas": len(log.get("ajuste", {}).get("tentativas", []))})
            del modelo, valores
        gc.collect()
    for nome, valores in pred.items():
        if not np.isfinite(valores).all() or np.any((valores <= 0) | (valores >= 1)):
            raise ValueError(f"{entrada['formulacao']}/{entrada['ano']}: OOF {nome} não finito, "
                             "incompleto ou fora de (0, 1).")
    return pred, {"folds": auditoria, "ajustes": logs, "pasta_cache": base.as_posix(),
                  "codigo_v2_sha256": codigo_v2}


# ---------------------------------------------------------------------------
# Diagnóstico de checkpoint rejeitado (operacional; fora do hash do código V2)
# ---------------------------------------------------------------------------

# Espelha a tabela de tarefas de ``ajustar``: (tipo, braço do treino, alvo). Mantida fora de
# ``ajustar`` porque o código-fonte dele entra no hash da pasta de cache.
_ESPEC_TAREFAS = {"e": ("logistica", None, "t"), "m0_C1": ("logistica", 0, "y"),
                  "m1_C1": ("logistica", 1, "y"), "m0_C2": ("hgb", 0, "y"),
                  "m1_C2": ("hgb", 1, "y"), "e_C3": ("hgb", None, "t")}
_CAMPOS_AMBIENTE = ("python", "sklearn", "numpy", "duckdb")


def _abreviar(valor) -> str:
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False)
    texto = " ".join(texto.split())
    return texto if len(texto) <= 40 else f"{texto[:16]}…"


def divergencias_contrato(salvo: dict, atual: dict, prefixo: str = "") -> list[tuple[str, str, str]]:
    """Campos (achatados) em que dois contratos diferem, com valores abreviados."""
    saida = []
    for chave in sorted(set(salvo) | set(atual)):
        a, b = salvo.get(chave, "<ausente>"), atual.get(chave, "<ausente>")
        if isinstance(a, dict) and isinstance(b, dict):
            saida += divergencias_contrato(a, b, f"{prefixo}{chave}.")
        elif a != b:
            saida.append((f"{prefixo}{chave}", _abreviar(a), _abreviar(b)))
    return saida


def contrato_atual(dados: pd.DataFrame, entrada: dict, nome: str, numero: int) -> dict:
    """Contrato que ``ajustar`` exige hoje para o nuisance ``nome`` na partição ``numero``."""
    tipo, braco, variavel = _ESPEC_TAREFAS[nome]
    t = dados.tratamento.to_numpy(dtype=int)
    y = dados.Y_BAIXO_PESO.to_numpy(dtype=int)
    folds, auditoria = et.particoes(t, y)
    treino = folds[numero - 1][0]
    indices = treino if braco is None else treino[t[treino] == braco]
    alvo = (t if variavel == "t" else y)[indices]
    return contrato_ajuste(entrada, auditoria["folds"][numero - 1], nome, tipo, alvo,
                           criar_modelo(tipo), sha256_codigo_v2())


def ajustar_com_diagnostico(dados: pd.DataFrame, entrada: dict, pasta_cache: Path) -> tuple[dict, dict]:
    """``ajustar``; se um checkpoint for rejeitado, a mensagem lista os campos divergentes.

    Apenas lê o JSON do checkpoint rejeitado: nada é apagado, reescrito ou reajustado aqui.
    """
    try:
        return ajustar(dados, entrada, pasta_cache)
    except ValueError as erro:
        marcador = "Checkpoint incompatível: "
        if not str(erro).startswith(marcador):
            raise
        prefixo = Path(str(erro).removeprefix(marcador))
        nome, numero = prefixo.name.rsplit("_fold", 1)
        salvo = json.loads(prefixo.with_suffix(".json").read_text(encoding="utf-8"))
        diferencas = divergencias_contrato(salvo.get("contrato") or {},
                                           contrato_atual(dados, entrada, nome, int(numero)))
        if salvo.get("status") != "CONCLUIDO":
            diferencas.append(("status", _abreviar(salvo.get("status")), "CONCLUIDO"))
        linhas = [f"Checkpoint incompatível: {entrada['formulacao']}/{entrada['ano']}/{nome}/fold{numero}",
                  str(prefixo), "", "Diferenças:"]
        linhas += [f"- {campo}: salvo={a} atual={b}" for campo, a, b in diferencas]
        linhas += ["", f"Python em uso: {sys.executable}"]
        if any(campo in _CAMPOS_AMBIENTE for campo, _, _ in diferencas):
            linhas.append(f"Versão divergente: selecione o kernel da .venv do projeto "
                          f"({RAIZ / '.venv' / 'Scripts' / 'python.exe'}).")
        linhas.append("O checkpoint não foi alterado; o contrato do cache continua exigindo igualdade.")
        raise ValueError("\n".join(linhas)) from erro


# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------

def resumir(dados: pd.DataFrame, pred: dict, entrada: dict) -> list[dict]:
    """Linhas históricas de ``resumir_aipw`` mais trimming e influência descritivos."""
    ano, formulacao = entrada["ano"], entrada["formulacao"]
    linhas = et.resumir_aipw(dados, pred, ano)
    t = dados.tratamento.to_numpy(dtype=int)
    y = dados.Y_BAIXO_PESO.to_numpy(dtype=int)
    grupos = dados.CODMUNRES.to_numpy(dtype=str)
    saida = []
    for linha in linhas:
        if linha["status"] != "CONCLUIDO":
            raise ValueError(f"{formulacao}/{ano} {linha['especificacao']}: {linha.get('motivo')}")
        spec = linha["especificacao"]
        e = pred["e_C3" if spec == "C3" else "e"]
        outcome = "C2" if spec == "C3" else spec
        lo, hi = (0.0, 1.0) if linha["trimming"] == "sem_trimming" else (0.05, 0.95)
        mask = (e >= lo) & (e <= hi)
        iid, psi = calcular_aipw(y[mask], t[mask], e[mask], pred[f"m0_{outcome}"][mask],
                                 pred[f"m1_{outcome}"][mask])
        if abs(iid["estimativa_pp"] - linha["estimativa_pp"]) > TOLERANCIA:
            raise ValueError("Recalculo do AIPW diverge de resumir_aipw.")
        cluster = resumo_cluster(psi, grupos[mask])
        influencia = diagnosticos_influencia(psi, t[mask], e[mask])
        fora_001 = (e < 0.01) | (e > 0.99)
        saida.append({"formulacao": formulacao, "ano": ano, **linha,
                      "n_total": int(len(t)),
                      "n_excluido_t0": int((~mask & (t == 0)).sum()),
                      "n_excluido_t1": int((~mask & (t == 1)).sum()),
                      "pct_excluido": 100 * float((~mask).mean()),
                      "fora_001_099_n": int(fora_001.sum()),
                      "razao_se_cluster_iid": cluster["razao_se"],
                      "critico_t": cluster["critico_t"],
                      "max_fracao_u2_municipio": cluster["max_fracao_variancia_cluster"],
                      "municipio_maior_u2": cluster["cluster_maior_if2"],
                      "max_contribuicao_individual_pp": influencia["max_contribuicao_individual_pp"],
                      "status_suporte_09d": entrada["status_suporte_09d"],
                      "sinalizado_09d": entrada["status_suporte_09d"] == "SINALIZADO"})
    return saida


# ---------------------------------------------------------------------------
# Controle positivo A/2024
# ---------------------------------------------------------------------------

def reconciliar_a2024(raiz: Path, entrada: dict, pred: dict, linhas: list[dict],
                      diagnosticos: list[dict], log: dict) -> dict:
    """Reconcilia o refit A/2024 com Fase 2/3 e notebook 09, na tolerância histórica (1e-12)."""
    historicas = [{k: v for k, v in r.items() if k not in ("formulacao",)} for r in linhas]
    base = et.reconciliar_2024(raiz, entrada, historicas, diagnosticos, {"folds": log["folds"]})
    checks, deltas = dict(base["checks"]), dict(base["deltas"])
    for campo, valor in ESPERADO_A2024.items():
        checks[f"esperado_{campo}"] = entrada[campo] == valor
    fase2 = et._json(raiz / "outputs/diagnostics/fase2_aipw.json")
    for novo, antigo in zip(log["folds"]["folds"], fase2["folds"], strict=True):
        k = novo["fold"]
        checks[f"fold{k}_n_treino"] = novo["n_treino"] == antigo["n_treino"]
        checks[f"fold{k}_n_validacao"] = novo["n_validacao"] == antigo["n_validacao"]
        checks[f"fold{k}_indices_validacao"] = novo["hash_validacao"] == antigo["sha256_indices_validacao"]
    ref09 = et._json(raiz / "data/interim/estimativas_temporais/v2/2024/reutilizacao_historica.json")["entrada"]
    for campo in ("chave_sha256", "t_sha256", "y_sha256", "parquet_sha256", "n_clusters"):
        checks[f"notebook09_{campo}"] = entrada[campo] == ref09[campo]
    # Comparação somente leitura do OOF refeito com o OOF histórico (não reutilizado).
    with np.load(raiz / "outputs/tables/fase2_predicoes_oof.npz") as arquivo:
        historico = {nome: arquivo[nome] for nome in TAREFAS if nome != "e_C3"}
        fold_id = arquivo["fold_id"]
    with np.load(raiz / "outputs/tables/fase3_c3_propensity_oof.npz") as arquivo:
        historico["e_C3"] = arquivo["e_C3"]
        contador_c3 = arquivo["contador"]
    checks["ordem_contador_c3"] = bool(np.array_equal(contador_c3, np.asarray(log["contador"], dtype=str)))
    for numero, validacao_hash in enumerate(log["folds"]["folds"], 1):
        idx = np.flatnonzero(fold_id == numero)
        checks[f"fold{numero}_fold_id_historico"] = et.hash_vetor(idx.astype(np.int64)) == validacao_hash["hash_validacao"]
    for nome in TAREFAS:
        delta = float(np.max(np.abs(pred[nome] - historico[nome])))
        deltas[f"oof_{nome}_max_abs"] = delta
        checks[f"oof_{nome}"] = delta <= TOLERANCIA
    aipw09 = pd.read_csv(raiz / "outputs/temporal/estimativas/aipw_anual.csv")
    for linha in linhas:
        ref = aipw09.loc[aipw09.ano.eq(2024) & aipw09.especificacao.eq(linha["especificacao"])
                         & aipw09.trimming.eq(linha["trimming"])].iloc[0]
        for campo in ("estimativa_pp", "se_iid_pp", "se_cluster_pp", "ic95_cluster_inferior_pp",
                      "ic95_cluster_superior_pp", "n_excluido"):
            delta = float(linha[campo] - ref[campo])
            chave = f"notebook09_{linha['especificacao']}_{linha['trimming']}_{campo}"
            deltas[chave] = delta
            checks[chave] = abs(delta) <= TOLERANCIA
    falhas = sorted(k for k, ok in checks.items() if not ok)
    return {"status": "CONTROLE_POSITIVO_A2024_APROVADO" if not falhas else "CONTROLE_POSITIVO_A2024_REPROVADO",
            "tolerancia_absoluta": TOLERANCIA, "n": entrada["n"], "n_t0": entrada["n_t0"],
            "n_t1": entrada["n_t1"], "n_checks": len(checks), "falhas": falhas,
            "max_abs_delta": max(abs(v) for v in deltas.values()), "checks": checks, "deltas": deltas,
            "nota": ("Nuisances A/2024 reajustados do zero no cache V2; OOF da Fase 2/3 apenas lido "
                     "para comparação, nunca reutilizado.")}


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------

def _verificar_contrato_congelado(raiz: Path) -> str:
    from src.v2_pre_estimacao import hash_contrato
    contrato = et._json(raiz / "outputs/temporal/v2_pre_estimacao/contrato_v2_congelado.json")
    if contrato.get("hash_contrato") != HASH_CONTRATO_V2 or hash_contrato(contrato) != HASH_CONTRATO_V2:
        raise ValueError("Contrato V2 congelado divergente do registrado.")
    return HASH_CONTRATO_V2


def _git(raiz: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "indisponivel"


def _executar_formulacao(raiz: Path, dados: pd.DataFrame, mes: np.ndarray, entrada_v1: dict,
                         formulacao: str, referencia: pd.DataFrame) -> dict:
    inicio = perf_counter()
    ano = entrada_v1["ano"]
    sub, composicao = populacao(dados, mes, formulacao)
    entrada = entrada_formulacao(raiz, sub, ano, formulacao, entrada_v1, referencia)
    entrada.update(composicao)
    pred, log = ajustar_com_diagnostico(sub, entrada, raiz / PASTA_CACHE)
    diagnosticos = [{"formulacao": formulacao, **d} for d in et.diagnosticos_ano(sub, pred, ano)]
    linhas = resumir(sub, pred, entrada)
    log["contador"] = sub.contador.to_numpy(dtype=str) if (formulacao, ano) == ("A", ANO_CONTROLE) else None
    resultado = {"entrada": entrada, "pred": pred, "log": log, "linhas": linhas,
                 "diagnosticos": diagnosticos}
    novos = sum(not a["reutilizado"] for a in log["ajustes"])
    resultado["execucao"] = {"formulacao": formulacao, "ano": ano, "n": entrada["n"],
                             "n_t0": entrada["n_t0"], "n_t1": entrada["n_t1"],
                             "n_municipios": entrada["n_clusters"],
                             "status_suporte_09d": entrada["status_suporte_09d"],
                             "ajustes_novos": novos, "ajustes_reutilizados": len(log["ajustes"]) - novos,
                             "segundos_fit_checkpoints": sum(a["segundos_fit"] for a in log["ajustes"]),
                             "segundos_sessao": perf_counter() - inicio, "rss_pico_bytes": et._rss(),
                             "chave_sha256": entrada["chave_sha256"], "t_sha256": entrada["t_sha256"],
                             "y_sha256": entrada["y_sha256"], "parquet_sha256": entrada["parquet_sha256"],
                             "pasta_cache": log["pasta_cache"]}
    print(f"{formulacao}/{ano} | N={entrada['n']} T0={entrada['n_t0']} T1={entrada['n_t1']} | "
          f"novos={novos} | {resultado['execucao']['segundos_sessao']:.1f}s | RSS={et._rss()}", flush=True)
    return resultado


def _persistir(pasta: Path, linhas: list[dict], diagnosticos: list[dict], execucoes: list[dict]) -> None:
    tabela = pd.DataFrame(linhas).sort_values(["formulacao", "ano", "especificacao", "trimming"],
                                              ascending=[True, True, True, False])
    et._salvar_csv(pasta / "resultados_anuais.csv", tabela.to_dict("records"))
    sem = tabela.loc[tabela.trimming.eq("sem_trimming")]
    com = tabela.loc[tabela.trimming.eq("0.05_0.95")]
    chaves = ["formulacao", "ano", "especificacao"]
    trimming = sem[chaves + ["n", "estimativa_pp", "ic95_cluster_inferior_pp", "ic95_cluster_superior_pp",
                             "fora_001_099_n", "status_suporte_09d"]].merge(
        com[chaves + ["n", "n_excluido", "n_excluido_t0", "n_excluido_t1", "pct_excluido", "estimativa_pp",
                      "ic95_cluster_inferior_pp", "ic95_cluster_superior_pp"]],
        on=chaves, suffixes=("_sem_trimming", "_005_095"), validate="one_to_one")
    trimming["delta_trimming_pp"] = trimming.estimativa_pp_005_095 - trimming.estimativa_pp_sem_trimming
    et._salvar_csv(pasta / "trimming.csv", trimming.to_dict("records"))
    inferencia = tabela[chaves + ["trimming", "n", "n_clusters", "estimativa_pp", "se_iid_pp",
                                  "ic95_iid_inferior_pp", "ic95_iid_superior_pp", "se_cluster_pp",
                                  "critico_t", "ic95_cluster_inferior_pp", "ic95_cluster_superior_pp",
                                  "razao_se_cluster_iid", "status_suporte_09d"]]
    et._salvar_csv(pasta / "inferencia.csv", inferencia.to_dict("records"))
    influencia = sem[chaves + ["n", "top1_if2", "max_fracao_u2_municipio", "municipio_maior_u2",
                               "razao_se_cluster_iid", "max_contribuicao_individual_pp",
                               "ess_t0_sobre_n", "ess_t1_sobre_n", "propensity_min", "propensity_max",
                               "status_suporte_09d"]]
    et._salvar_csv(pasta / "influencia.csv", influencia.to_dict("records"))
    et._salvar_csv(pasta / "diagnosticos_nuisance.csv", diagnosticos)
    et._salvar_csv(pasta / "execucao.csv", execucoes)


def executar(raiz: Path = RAIZ, formulacoes: tuple[str, ...] = ("A", "B", "C"),
             anos: tuple[int, ...] = ANOS, gravar_saidas: bool = True) -> dict:
    """Controle positivo A/2024 sempre primeiro; B/C só depois de aprovado. Anos sequenciais."""
    raiz = Path(raiz)
    inicio = perf_counter()
    hash_contrato = _verificar_contrato_congelado(raiz)
    baseline = et.verificar_baseline(raiz)
    if baseline["status"] != "BASELINE_2024_PRESERVADO":
        raise ValueError(f"Baseline histórico divergente: {baseline['divergencias']}")
    referencia = suporte_09d(raiz)
    pasta = raiz / PASTA_SAIDA
    linhas, diagnosticos, execucoes = [], [], []

    dados, mes, entrada_v1 = carregar_v1_com_mes(raiz, ANO_CONTROLE)
    a = _executar_formulacao(raiz, dados, mes, entrada_v1, "A", referencia)
    controle = reconciliar_a2024(raiz, a["entrada"], a["pred"], a["linhas"], a["diagnosticos"], a["log"])
    controle.update(execucao=a["execucao"], folds=a["log"]["folds"])
    print(f"A/2024 | {controle['status']} | {controle['n_checks']} checks | "
          f"max |delta|={controle['max_abs_delta']:.3e}", flush=True)
    if gravar_saidas:
        et._salvar_json(pasta / "controle_positivo_a2024.json", controle)
    if controle["status"] != "CONTROLE_POSITIVO_A2024_APROVADO":
        raise RuntimeError(f"Controle positivo A/2024 reprovado: {controle['falhas']}")
    linhas += a["linhas"]
    diagnosticos += a["diagnosticos"]
    execucoes.append(a["execucao"])
    del a
    gc.collect()

    alvo = [f for f in formulacoes if f in ("B", "C")]
    for ano in sorted(anos, key=lambda x: (x != ANO_CONTROLE, x)):
        if not alvo:
            break
        if ano != ANO_CONTROLE:
            del dados, mes
            gc.collect()
            dados, mes, entrada_v1 = carregar_v1_com_mes(raiz, ano)
        for formulacao in alvo:
            r = _executar_formulacao(raiz, dados, mes, entrada_v1, formulacao, referencia)
            linhas += r["linhas"]
            diagnosticos += r["diagnosticos"]
            execucoes.append(r["execucao"])
            del r
            gc.collect()
            if gravar_saidas:
                _persistir(pasta, linhas, diagnosticos, execucoes)
    if gravar_saidas:
        _persistir(pasta, linhas, diagnosticos, execucoes)
    manifesto = {
        "etapa": "ESTIMACAO_V2", "contrato_v2_hash": hash_contrato,
        "git": {"branch": _git(raiz, "branch", "--show-current"), "head": _git(raiz, "rev-parse", "HEAD")},
        "controle_positivo_a2024": controle["status"],
        "formulacoes": {f: FORMULACOES[f] for f in formulacoes},
        "anos": sorted(anos), "seed": et.SEED, "n_folds": et.N_FOLDS, "estratificacao": "2*T+Y",
        "features": list(COLUNAS_PROPENSITY_PRINCIPAL),
        "especificacoes": {"C1": "propensity logística L2 C=1; outcomes logísticos",
                           "C2": "propensity logística L2 C=1; outcomes HGB histórico",
                           "C3": "propensity HGB histórico; outcomes HGB histórico (C2)"},
        "trimming": {"principal": "sem_trimming", "sensibilidade": "[0,05; 0,95]",
                     "diagnostico": "[0,01; 0,99] (apenas contagem)"},
        "inferencia": {"principal": "SE agrupado por CODMUNRES, IC t(G-1)", "referencia": "SE iid, IC normal"},
        "cache": {"pasta": (raiz / PASTA_CACHE).as_posix(), "versao": VERSAO_CACHE,
                  "codigo_v2_sha256": sha256_codigo_v2(),
                  "ajustes_novos": sum(e["ajustes_novos"] for e in execucoes),
                  "ajustes_reutilizados": sum(e["ajustes_reutilizados"] for e in execucoes),
                  "segundos_fit_checkpoints": sum(e["segundos_fit_checkpoints"] for e in execucoes)},
        "baseline_final": et.verificar_baseline(raiz)["status"],
        "segundos_sessao": perf_counter() - inicio, "rss_pico_bytes": et._rss(),
        "versoes": {"python": __import__("platform").python_version(),
                    "sklearn": __import__("sklearn").__version__, "numpy": np.__version__,
                    "pandas": pd.__version__, "duckdb": duckdb.__version__},
        "execucoes": execucoes,
        "limitacoes": ["Contraste AIPW padronizado sob hipóteses de identificação não verificáveis.",
                       "Confundimento residual, seleção por nascido vivo e mensuração de MESPRENAT.",
                       "B/C reduzem, mas não eliminam, o problema temporal da exposição.",
                       "IC municipal não cobre dependência entre anos nem toda a incerteza dos nuisances."],
    }
    if gravar_saidas:
        et._salvar_json(pasta / "manifesto_estimacao_v2.json", manifesto)
    print(f"Concluído | {manifesto['segundos_sessao'] / 60:.1f} min | novos={manifesto['cache']['ajustes_novos']} "
          f"| reutilizados={manifesto['cache']['ajustes_reutilizados']}", flush=True)
    return {"manifesto": manifesto, "controle": controle, "linhas": linhas}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--formulacoes", default="A,B,C")
    parser.add_argument("--sem-saidas", action="store_true")
    argumentos = parser.parse_args()
    executar(formulacoes=tuple(argumentos.formulacoes.split(",")), gravar_saidas=not argumentos.sem_saidas)
