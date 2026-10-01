"""Contrato V2 pré-estimação: populações A/B/C, propensity diagnóstico, suporte e gates.

Escopo estritamente pré-efeito. Este módulo:

- constrói as populações candidatas da V2 (B: 1-3 vs 4-6; C: 1-3 vs 4-5) e a V1 (A: 1-3 vs 4-9)
  sobre as views congeladas de ``src.amostra`` (mesma elegibilidade, mesmas sete X);
- ajusta SOMENTE o escore de propensão logístico histórico (L2, C=1) em partições OOF
  para diagnosticar atribuição, suporte, balanceamento e ESS;
- aplica gates de viabilidade fixados antes dos resultados.

Não ajusta modelos de desfecho, não calcula AIPW, CATE nem qualquer efeito. A coluna de
desfecho não é materializada: ``y_p1`` válido entra apenas como critério de elegibilidade
herdado da V1. D (landmark) não é implementada.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
import platform
import time
from typing import Any
import warnings

import duckdb
import numpy as np
import pandas as pd

from src.amostra import _criar_views
from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL, VARIAVEIS_PROIBIDAS_PROPENSITY

# ---------------------------------------------------------------------------
# Contrato científico (congelado antes de qualquer efeito B/C)
# ---------------------------------------------------------------------------

VERSAO_CONTRATO_V2 = "v2-pre-estimacao-1 (2026-10-01; congelado antes de qualquer efeito B/C)"
VERSAO_CACHE = "v2-pre-estimacao-propensity-1"
ANOS = tuple(range(2014, 2025))
ANO_BASELINE = 2024
SEED = 20240925
FEATURES = tuple(COLUNAS_PROPENSITY_PRINCIPAL)
NUMERICAS = ("IDADEMAE_NUM",)
CATEGORICAS = tuple(c for c in FEATURES if c not in NUMERICAS)
MESES_TRATADOS = (1, 2, 3)

# Diagnóstico pré-V2 herda o contrato do notebook 08 (diagnóstico de overlap): 5 partições
# estratificadas por T. Os 3 folds estratificados por 2T+Y pertencem ao AIPW futuro.
N_FOLDS_DIAGNOSTICO = 5
ESTRATIFICACAO_DIAGNOSTICO = "T (StratifiedKFold, shuffle=True, random_state=20240925)"

FORMULACOES: dict[str, dict[str, Any]] = {
    "A_V1": {
        "controles": (4, 5, 6, 7, 8, 9),
        "papel": "V1_HISTORICA_PRESERVADA",
        "implementada": True,
        "descricao": "T=1: MESPRENAT 1-3; T=0: MESPRENAT 4-9 (contraste observacional padronizado histórico)",
    },
    "B": {
        "controles": (4, 5, 6),
        "papel": "V2_PRINCIPAL",
        "implementada": True,
        "descricao": "T=1: MESPRENAT 1-3; T=0: MESPRENAT 4-6; população elegível B = V1 com MESPRENAT 1-6",
    },
    "C": {
        "controles": (4, 5),
        "papel": "V2_SENSIBILIDADE_ESTRUTURAL",
        "implementada": True,
        "descricao": "T=1: MESPRENAT 1-3; T=0: MESPRENAT 4-5; população elegível C = V1 com MESPRENAT 1-5",
    },
    "D_LANDMARK": {
        "controles": None,
        "papel": "PENDENTE_NAO_IMPLEMENTADA",
        "implementada": False,
        "descricao": ("tempo zero no fim do 3º mês; T=1 já iniciou; T=0 ainda não iniciou. Exige distinguir "
                      "'ainda não/nunca iniciou' de 'desconhecido', o que os dados atuais não permitem"),
    },
}
FORMULACOES_DIAGNOSTICADAS = ("A_V1", "B", "C")

# Limiares de viabilidade. Proveniência: 0,10 / 0,20 / 0,10 são os guardrails do 08B
# (src.selecao_nuisance.selecionar_candidato_propensity); 0,50 é o gatilho de sinalização
# proposto no plano do notebook 09 (docs/temporal/PLANO_NOTEBOOK_09.md, §20).
LIMIARES = {
    "smd_ponderado_max": 0.10,
    "ess_relativo_bloqueio": 0.20,
    "ess_relativo_sinal": 0.50,
    "fora_005_095_max": 0.10,
}

CRITERIOS_GATES_V2: dict[str, Any] = {
    "unidade": "formulação x ano (2014-2024); cada ano é avaliado separadamente",
    "BLOQUEADO": {
        "B1_bracos": "T=0 ou T=1 ausente na população da formulação",
        "B2_particoes": ("alguma partição sem os dois braços no treino ou na validação, interseção "
                         "treino/validação ou cobertura OOF diferente de exatamente 1"),
        "B3_propensity_invalido": "propensity OOF não finito ou fora do intervalo aberto (0, 1)",
        "B4_vazamento": ("X diferente das sete covariáveis congeladas, variável proibida em X ou coluna de "
                         "desfecho materializada no diagnóstico"),
        "B5_convergencia": "algum ajuste logístico com ConvergenceWarning",
        "B6_ess_minimo": "ESS/N < 0,20 em algum braço (guardrail histórico do 08B)",
        "B7_contrato_dados": ("hash do Parquet diverge do manifesto, chave (UF_RESIDENCIA, CONTADOR) não única, "
                              "DTNASC inválida/fora do ano, ou N/T0/T1 não reconcilia com o 09c/notebook 08"),
    },
    "SINALIZADO": {
        "S1_smd_ponderado": "maior |SMD| ponderado (pesos ATE sem truncamento) > 0,10",
        "S2_caudas": "fração com propensity fora de [0,05; 0,95] > 0,10",
        "S3_ess_baixo": "ESS/N < 0,50 em algum braço (gatilho do plano do 09, §20)",
    },
    "APROVADO": "nenhuma condição de bloqueio ou sinalização",
    "informativo_sem_decisao": [
        "AUC, log-loss, Brier e erro de calibração por decis (qualidade preditiva não é critério causal)",
        "fração fora de [0,01; 0,99]",
        "quantis e máximo dos pesos ATE",
        "fração fora do suporte comum observado",
        "número de municípios de residência (planejamento da inferência agrupada futura)",
    ],
    "consolidacao": {
        "ordem_gravidade": "BLOQUEADO > SINALIZADO > APROVADO",
        "status_formulacao": "pior status entre os 11 anos da janela principal; janela 2018-2024 reportada à parte",
        "SUPORTE_V2": "status consolidado de B (principal)",
        "SUPORTE_SENSIBILIDADE_C": "status consolidado de C, reportado separadamente",
        "A_V1": "referência histórica; status calculado para comparação, não decide nada",
        "anos_sinalizados": "permanecem na análise; nenhum ano é removido por gate",
        "pronto": ("PRONTO_PARA_REVISAO_HUMANA_ANTES_DOS_EFEITOS se B não tiver ano BLOQUEADO; "
                   "caso contrário NAO_PRONTO_PARA_ESTIMAR_V2"),
    },
    "limite": ("Os gates avaliam viabilidade estatística de atribuição/suporte; não avaliam confundimento "
               "não medido, seleção por nascido vivo, mensuração de MESPRENAT nem qualquer efeito."),
}

QUANTIS_PROPENSITY = (0.0, 0.001, 0.01, 0.05, 0.5, 0.95, 0.99, 0.999, 1.0)
QUANTIS_PESOS = (0.5, 0.95, 0.99, 0.999, 1.0)
ORDEM_2024 = ("ordem física certificada do Parquet 2024 (contrato do notebook 08), "
              "reproduzida explicitamente por ORDER BY file_row_number")
ORDEM_TEMPORAL = "ORDER BY UF_RESIDENCIA, CAST(CONTADOR AS VARCHAR)"
ARQUIVOS_CODIGO = ("src/v2_pre_estimacao.py", "src/amostra.py", "src/diagnosticos.py",
                   "src/auditoria_dados.py")
_GRAVIDADE = {"APROVADO": 0, "SINALIZADO": 1, "BLOQUEADO": 2}
_COLUNAS_DESFECHO = frozenset({"Y_BAIXO_PESO", "Y_BAIXO_PESO_P0", "Y_P1", "Y_P0", "PESO", "PESO_NUM"})


# ---------------------------------------------------------------------------
# Utilidades de hash e serialização
# ---------------------------------------------------------------------------

def sha256_arquivo(caminho: str | Path, bloco: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for parte in iter(lambda: arquivo.read(bloco), b""):
            h.update(parte)
    return h.hexdigest()


def sha256_texto_linhas(valores: Iterator[str] | Sequence[str]) -> str:
    """Mesmo formato de ``src.temporal._sha256_texto_linhas`` (uma linha por valor)."""

    digest = hashlib.sha256()
    for valor in valores:
        digest.update(str(valor).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def sha256_vetor(valores: np.ndarray, dtype: str = "<f8") -> str:
    return hashlib.sha256(np.ascontiguousarray(np.asarray(valores).astype(dtype, copy=False)).tobytes()).hexdigest()


def _json_canonico(objeto: Any) -> str:
    return json.dumps(objeto, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def hash_objeto(objeto: Any) -> str:
    return hashlib.sha256(_json_canonico(objeto).encode("utf-8")).hexdigest()


def sha256_codigo(raiz: str | Path) -> str:
    """Hash composto dos módulos que definem população, X, pré-processamento e modelo."""

    raiz = Path(raiz)
    digest = hashlib.sha256()
    for relativo in ARQUIVOS_CODIGO:
        digest.update(relativo.encode("utf-8"))
        digest.update(b"\0")
        digest.update((raiz / relativo).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def versoes_bibliotecas() -> dict[str, str]:
    import sklearn

    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
            "sklearn": sklearn.__version__, "duckdb": duckdb.__version__}


def memoria_processo_mb() -> dict[str, float]:
    import psutil

    info = psutil.Process().memory_info()
    pico = getattr(info, "peak_wset", None)
    return {"rss_mb": info.rss / 2**20, "pico_mb": (pico / 2**20) if pico else float("nan")}


def _gravar_atomico(caminho: Path, conteudo: bytes) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_bytes(conteudo)
    os.replace(temporario, caminho)


# ---------------------------------------------------------------------------
# Populações
# ---------------------------------------------------------------------------

def definicao_tratamento(formulacao: str) -> str:
    controles = _controles(formulacao)
    return (f"T=1 se MESPRENAT em {list(MESES_TRATADOS)}; T=0 se MESPRENAT em {list(controles)}; "
            "demais (99, vazio, 10, inválido e meses fora da formulação) fora da população")


def _controles(formulacao: str) -> tuple[int, ...]:
    if formulacao not in FORMULACOES:
        raise ValueError(f"Formulação desconhecida: {formulacao}")
    if not FORMULACOES[formulacao]["implementada"]:
        raise ValueError(f"Formulação {formulacao} não está implementada (landmark pendente).")
    return tuple(FORMULACOES[formulacao]["controles"])


def classificar_tratamento(mesprenat: pd.Series, formulacao: str) -> pd.Series:
    """T por formulação a partir do texto bruto de MESPRENAT; NA fora da formulação.

    Mesma conversão das views congeladas (``try_cast`` inteiro): '01'..'09' são meses;
    '99', vazio, nulo, '10' e textos inválidos permanecem NA e nunca são reclassificados.
    """

    controles = _controles(formulacao)
    mes = pd.to_numeric(mesprenat.astype("string").str.strip(), errors="coerce")
    inteiro = mes.notna() & (mes == np.floor(mes))
    t = pd.Series(pd.NA, index=mesprenat.index, dtype="Int8")
    t[inteiro & mes.isin(MESES_TRATADOS)] = 1
    t[inteiro & mes.isin(controles)] = 0
    return t


def sql_populacao(conexao: duckdb.DuckDBPyConnection, formulacao: str, ano: int) -> str:
    """SQL da população da formulação, reaproveitando a projeção X da view congelada.

    A projeção é extraída de ``amostra_principal`` (mesmo padrão de ``src.amostra.carregar_amostra``
    e ``src.estimativas_temporais``). Elegibilidade herdada: T da V1 conhecido, ``y_p1`` válido e
    gestação única. A coluna de desfecho existe na view base, mas não é selecionada.
    """

    controles = _controles(formulacao)
    meses = ", ".join(str(m) for m in (*MESES_TRATADOS, *controles))
    sql_view = conexao.execute(
        "SELECT sql FROM duckdb_views() WHERE view_name='amostra_principal'"
    ).fetchone()[0]
    projecao = sql_view[sql_view.index(" AS SELECT ") + 4:sql_view.index(" FROM fase1_base")]
    conexao.execute(
        "CREATE OR REPLACE TEMP VIEW v2_base AS " + projecao
        + ", mesprenat_num, CAST(CODMUNRES AS VARCHAR) AS CODMUNRES_TXT, file_row_number FROM fase1_base "
        "WHERE tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num = 1"
    )
    ordem = (" ORDER BY file_row_number" if int(ano) == ANO_BASELINE
             else " ORDER BY UF_RESIDENCIA, CAST(contador AS VARCHAR)")
    colunas_x = ", ".join(FEATURES)
    return (
        'SELECT contador AS "contador", '
        f"CASE WHEN mesprenat_num BETWEEN {MESES_TRATADOS[0]} AND {MESES_TRATADOS[-1]} THEN 1 ELSE 0 END "
        f"AS tratamento, tratamento AS tratamento_v1, mesprenat_num, {colunas_x}, CODMUNRES_TXT AS CODMUNRES "
        f"FROM v2_base WHERE mesprenat_num IN ({meses})" + ordem
    )


def carregar_populacao(parquet: str | Path, ano: int, formulacao: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Materializa a população de uma formulação/ano com a ordem contratada; sem desfecho."""

    caminho = Path(parquet)
    inicio = time.perf_counter()
    with duckdb.connect() as conexao:
        _criar_views(conexao, caminho)
        # Sem ORDER BY, a ordem de uma consulta filtrada não é garantida (verificado em 2024:
        # duas leituras com sequências de chave diferentes). A ordem física certificada do
        # notebook 08 é reproduzida explicitamente pelo número de linha do arquivo; a view
        # ``sinasc`` é redefinida apenas para expor essa coluna (as demais views são as congeladas).
        texto = caminho.as_posix().replace("'", "''")
        conexao.execute(f"CREATE OR REPLACE TEMP VIEW sinasc AS SELECT * FROM read_parquet('{texto}', "
                        "file_row_number=true)")
        dados = conexao.execute(sql_populacao(conexao, formulacao, ano)).df()
        datas_invalidas = int(conexao.execute(
            "SELECT count(*) FROM sinasc WHERE try_strptime(DTNASC,'%d%m%Y') IS NULL "
            f"OR year(try_strptime(DTNASC,'%d%m%Y')) <> {int(ano)}"
        ).fetchone()[0])
    verificar_ausencia_desfecho(dados.columns)
    dados["tratamento"] = dados["tratamento"].astype(int)
    controles = _controles(formulacao)
    esperado_t = np.where(dados["mesprenat_num"].isin(MESES_TRATADOS), 1, 0)
    if not dados["mesprenat_num"].isin((*MESES_TRATADOS, *controles)).all():
        raise ValueError("Mês fora da formulação materializado.")
    if not np.array_equal(dados["tratamento"].to_numpy(), esperado_t):
        raise ValueError("T divergente da regra da formulação.")
    # A população B/C é subconjunto exato da V1: T coincide com a V1 nos meses mantidos.
    if not np.array_equal(dados["tratamento"].to_numpy(), dados["tratamento_v1"].astype(int).to_numpy()):
        raise ValueError("T da formulação diverge de T da V1 nos meses mantidos.")
    chaves = [f"{ano}|{uf}|{c}" for uf, c in zip(dados["UF_RESIDENCIA"], dados["contador"], strict=True)]
    chave_unica = not pd.Series(chaves).duplicated().any()
    n_por_mes = {int(k): int(v) for k, v in dados["mesprenat_num"].value_counts().sort_index().items()}
    codmun = dados["CODMUNRES"].astype("string")
    codmun_valido = codmun.str.fullmatch(r"\d{6}", na=False)
    meta = {
        "formulacao": formulacao,
        "ano": int(ano),
        "definicao_tratamento": definicao_tratamento(formulacao),
        "regra_ordenacao": ORDEM_2024 if int(ano) == ANO_BASELINE else ORDEM_TEMPORAL,
        "definicao_chave": "(ano, UF_RESIDENCIA, CONTADOR)",
        "sha256_sequencia_chave": sha256_texto_linhas(chaves),
        "chave_unica": bool(chave_unica),
        "n": int(len(dados)),
        "n_t0": int((dados["tratamento"] == 0).sum()),
        "n_t1": int((dados["tratamento"] == 1).sum()),
        "n_por_mesprenat": n_por_mes,
        "datas_invalidas": datas_invalidas,
        "n_municipios_residencia": int(codmun[codmun_valido].nunique()),
        "n_codmunres_invalido": int((~codmun_valido).sum()),
        "segundos_carga": time.perf_counter() - inicio,
    }
    dados = dados.drop(columns=["tratamento_v1"])
    return dados, meta


def verificar_ausencia_desfecho(colunas: Sequence[str]) -> None:
    normalizadas = {str(c).upper() for c in colunas}
    presentes = sorted(normalizadas & _COLUNAS_DESFECHO)
    if presentes:
        raise ValueError(f"Desfecho materializado no diagnóstico de propensity: {presentes}")


def validar_x(x: pd.DataFrame) -> None:
    """X deve ser exatamente as sete covariáveis congeladas, na ordem, sem proibidas."""

    proibidas = sorted({str(c).upper() for c in x.columns} & (VARIAVEIS_PROIBIDAS_PROPENSITY | _COLUNAS_DESFECHO))
    if proibidas:
        raise ValueError(f"Variáveis proibidas em X: {proibidas}")
    if list(x.columns) != list(FEATURES):
        raise ValueError(f"X deve respeitar exatamente as covariáveis congeladas: {list(FEATURES)}")


def reconciliar_n(meta: Mapping[str, Any], n_t1_referencia: int, n_t0_referencia: int) -> dict[str, Any]:
    """Compara T1/T0 com referências independentes (notebook 08 e D7 do 09c)."""

    checks = {"n_t1": int(meta["n_t1"]) == int(n_t1_referencia),
              "n_t0": int(meta["n_t0"]) == int(n_t0_referencia)}
    return {"aprovado": all(checks.values()), "checks": checks,
            "observado": {"n_t1": int(meta["n_t1"]), "n_t0": int(meta["n_t0"])},
            "referencia": {"n_t1": int(n_t1_referencia), "n_t0": int(n_t0_referencia)}}


def sha256_parquet_esperado(raiz: str | Path, ano: int) -> str:
    """SHA-256 certificado: manifesto anual (2014-2023) ou proveniência da Fase 2 (2024)."""

    raiz = Path(raiz)
    if int(ano) == ANO_BASELINE:
        fase2 = json.loads((raiz / "outputs/diagnostics/fase2_aipw.json").read_text(encoding="utf-8"))
        return fase2["provenance"]["parquet_sha256"]
    manifesto = json.loads((raiz / f"outputs/temporal/manifestos/sinasc_{int(ano)}.json").read_text(encoding="utf-8"))
    return manifesto["conversao"]["parquet_sha256"]


# ---------------------------------------------------------------------------
# Partições, pipeline e checkpoints
# ---------------------------------------------------------------------------

def particoes_diagnostico(t: Sequence[int]) -> list[tuple[np.ndarray, np.ndarray]]:
    """Cinco partições estratificadas por T, idênticas às do notebook 08."""

    from sklearn.model_selection import StratifiedKFold

    t = np.asarray(t, dtype=int)
    divisor = StratifiedKFold(n_splits=N_FOLDS_DIAGNOSTICO, shuffle=True, random_state=SEED)
    folds = list(divisor.split(np.zeros(len(t)), t))
    validar_particoes(folds, t)
    return folds


def validar_particoes(folds: Sequence[tuple[np.ndarray, np.ndarray]], t: Sequence[int]) -> dict[str, Any]:
    t = np.asarray(t, dtype=int)
    cobertura = np.zeros(len(t), dtype=np.int64)
    for k, (treino, validacao) in enumerate(folds, 1):
        if np.intersect1d(treino, validacao).size:
            raise ValueError(f"Partição {k}: interseção entre treino e validação.")
        if len(treino) + len(validacao) != len(t):
            raise ValueError(f"Partição {k}: treino e validação não cobrem a população.")
        for nome, idx in (("treino", treino), ("validação", validacao)):
            if set(np.unique(t[idx])) != {0, 1}:
                raise ValueError(f"Partição {k}: {nome} sem os dois braços.")
        cobertura[validacao] += 1
    if not np.all(cobertura == 1):
        raise ValueError("Cobertura OOF diferente de exatamente 1.")
    return {"n_folds": len(folds), "cobertura_exata": True}


def construir_pipeline():
    """Pipeline logístico histórico (mesma fábrica do notebook 08), sem busca de hiperparâmetros."""

    from src.diagnosticos import construir_pipeline_propensity

    return construir_pipeline_propensity(NUMERICAS, CATEGORICAS)


def descrever_pipeline(pipeline) -> dict[str, Any]:
    """Descrição determinística do pré-processamento e do modelo para o contrato do cache."""

    def parametros(estimador) -> dict[str, str]:
        return {k: str(v) for k, v in sorted(estimador.get_params(deep=False).items())}

    preprocessador = pipeline.named_steps["preprocessamento"]
    transformadores = []
    for nome, transformador, colunas in preprocessador.transformers:
        passos = [[passo, est.__class__.__name__, parametros(est)] for passo, est in transformador.steps]
        transformadores.append({"nome": nome, "colunas": list(colunas), "passos": passos})
    modelo = pipeline.named_steps["modelo"]
    return {
        "preprocessamento": {"classe": preprocessador.__class__.__name__,
                             "sparse_threshold": str(preprocessador.sparse_threshold),
                             "transformadores": transformadores},
        "modelo": {"classe": modelo.__class__.__name__, "parametros": parametros(modelo)},
    }


def contrato_fold(*, formulacao: str, ano: int, fold: int, meta: Mapping[str, Any],
                  indices_validacao: np.ndarray, codigo_sha256: str,
                  versoes: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Contrato científico determinístico do checkpoint (sem timestamp)."""

    contrato = {
        "versao_cache": VERSAO_CACHE,
        "formulacao": formulacao,
        "definicao_tratamento": definicao_tratamento(formulacao),
        "ano": int(ano),
        "fold": int(fold),
        "n_folds": N_FOLDS_DIAGNOSTICO,
        "estratificacao": ESTRATIFICACAO_DIAGNOSTICO,
        "features": list(FEATURES),
        "seed": SEED,
        "parquet_sha256": meta["parquet_sha256"],
        "regra_ordenacao": meta["regra_ordenacao"],
        "sha256_sequencia_chave": meta["sha256_sequencia_chave"],
        "n": int(meta["n"]), "n_t0": int(meta["n_t0"]), "n_t1": int(meta["n_t1"]),
        "indices_validacao_sha256": sha256_vetor(indices_validacao, "<i8"),
        "pipeline": descrever_pipeline(construir_pipeline()),
        "versoes": dict(versoes or versoes_bibliotecas()),
        "codigo_sha256": codigo_sha256,
    }
    contrato["fingerprint"] = hash_objeto(contrato)
    return contrato


def caminhos_checkpoint(pasta: str | Path, contrato: Mapping[str, Any]) -> dict[str, Path]:
    base = (Path(pasta) / f"codigo_{contrato['codigo_sha256'][:16]}" / contrato["formulacao"]
            / str(contrato["ano"]) / f"fold{contrato['fold']}")
    return {"metadados": base.with_suffix(".json"), "predicoes": base.with_suffix(".npz")}


def salvar_checkpoint(pasta: str | Path, contrato: Mapping[str, Any], e_validacao: np.ndarray,
                      log: Mapping[str, Any]) -> dict[str, Path]:
    e = np.asarray(e_validacao, dtype=np.float64)
    if not np.isfinite(e).all() or np.any((e <= 0) | (e >= 1)):
        raise ValueError("Checkpoint com propensity inválido.")
    caminhos = caminhos_checkpoint(pasta, contrato)
    caminhos["predicoes"].parent.mkdir(parents=True, exist_ok=True)
    temporario = caminhos["predicoes"].with_name(caminhos["predicoes"].stem + ".tmp.npz")
    np.savez_compressed(temporario, e=e)
    os.replace(temporario, caminhos["predicoes"])
    metadados = {"contrato": dict(contrato), "predicoes_sha256": sha256_vetor(e),
                 "n_validacao": int(len(e)), "log": dict(log)}
    _gravar_atomico(caminhos["metadados"],
                    (json.dumps(metadados, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n").encode("utf-8"))
    return caminhos


def ler_checkpoint(pasta: str | Path, contrato: Mapping[str, Any]) -> tuple[np.ndarray, dict] | None:
    """Ausente -> None. Presente e incompatível -> ValueError (o cache é rejeitado, nunca reutilizado)."""

    caminhos = caminhos_checkpoint(pasta, contrato)
    if not caminhos["metadados"].exists():
        return None
    metadados = json.loads(caminhos["metadados"].read_text(encoding="utf-8"))
    salvo = metadados.get("contrato", {})
    divergencias = sorted(k for k in set(salvo) | set(contrato) if salvo.get(k) != contrato.get(k))
    if divergencias:
        raise ValueError(f"Cache incompatível rejeitado ({caminhos['metadados']}): {divergencias}")
    if salvo.get("fingerprint") != hash_objeto({k: v for k, v in salvo.items() if k != "fingerprint"}):
        raise ValueError("Fingerprint do checkpoint não confere com o conteúdo do contrato.")
    if not caminhos["predicoes"].exists():
        raise ValueError("Metadados sem predições correspondentes; checkpoint rejeitado.")
    with np.load(caminhos["predicoes"], allow_pickle=False) as arquivo:
        e = arquivo["e"].astype(np.float64, copy=False)
    if sha256_vetor(e) != metadados["predicoes_sha256"] or len(e) != int(metadados["n_validacao"]):
        raise ValueError("Predições do checkpoint divergem do hash/N registrado.")
    if not np.isfinite(e).all() or np.any((e <= 0) | (e >= 1)):
        raise ValueError("Checkpoint contém propensity inválido.")
    return e, metadados["log"]


def ajustar_propensity_oof(dados: pd.DataFrame, meta: Mapping[str, Any], formulacao: str,
                           pasta_cache: str | Path, codigo_sha256: str) -> tuple[np.ndarray, dict[str, Any]]:
    """Propensity OOF (5 partições) com checkpoint por formulação/ano/partição."""

    from sklearn.base import clone
    from sklearn.exceptions import ConvergenceWarning

    x = dados.loc[:, list(FEATURES)]
    validar_x(x)
    verificar_ausencia_desfecho(dados.columns)
    t = dados["tratamento"].to_numpy(dtype=int)
    if set(np.unique(t)) != {0, 1}:
        raise ValueError("Propensity requer os dois braços.")
    folds = particoes_diagnostico(t)
    versoes = versoes_bibliotecas()
    pipeline = construir_pipeline()
    oof = np.full(len(t), np.nan)
    cobertura = np.zeros(len(t), dtype=np.int64)
    logs = []
    inicio = time.perf_counter()
    for k, (treino, validacao) in enumerate(folds, 1):
        contrato = contrato_fold(formulacao=formulacao, ano=meta["ano"], fold=k, meta=meta,
                                 indices_validacao=validacao, codigo_sha256=codigo_sha256, versoes=versoes)
        lido = ler_checkpoint(pasta_cache, contrato)
        if lido is not None:
            e_val, log = lido
            if len(e_val) != len(validacao):
                raise ValueError("Checkpoint com N de validação divergente.")
            log = {**log, "origem": "cache"}
        else:
            inicio_fold = time.perf_counter()
            modelo = clone(pipeline)
            with warnings.catch_warnings(record=True) as avisos:
                warnings.simplefilter("always", ConvergenceWarning)
                modelo.fit(x.iloc[treino], t[treino])
            if any(issubclass(a.category, ConvergenceWarning) for a in avisos):
                raise RuntimeError(f"{formulacao} {meta['ano']} partição {k}: propensity não convergiu.")
            e_val = modelo.predict_proba(x.iloc[validacao])[:, 1]
            log = {"fold": k, "n_treino": int(len(treino)), "n_validacao": int(len(validacao)),
                   "n_iter": int(np.max(modelo["modelo"].n_iter_)), "convergiu": True,
                   "segundos": time.perf_counter() - inicio_fold, "rss_mb": memoria_processo_mb()["rss_mb"]}
            salvar_checkpoint(pasta_cache, contrato, e_val, log)
            log = {**log, "origem": "ajuste"}
        oof[validacao] = e_val
        cobertura[validacao] += 1
        logs.append(log)
    if not np.all(cobertura == 1) or not np.isfinite(oof).all() or np.any((oof <= 0) | (oof >= 1)):
        raise ValueError("Propensity OOF inválido ou cobertura incompleta.")
    return oof, {"n_folds": N_FOLDS_DIAGNOSTICO, "folds": logs, "segundos_total": time.perf_counter() - inicio,
                 "todos_convergiram": all(bool(l.get("convergiu")) for l in logs),
                 "particoes_validas": True, "versoes": versoes}


# ---------------------------------------------------------------------------
# Diagnósticos de suporte, balanceamento e ESS
# ---------------------------------------------------------------------------

def pesos_ate(t: np.ndarray, e: np.ndarray) -> np.ndarray:
    t = np.asarray(t, dtype=int)
    e = np.asarray(e, dtype=float)
    if not np.isfinite(e).all() or np.any((e <= 0) | (e >= 1)):
        raise ValueError("Propensity deve ser finito e estritamente entre 0 e 1.")
    return np.where(t == 1, 1.0 / e, 1.0 / (1.0 - e))


def ess(pesos: np.ndarray) -> float:
    pesos = np.asarray(pesos, dtype=float)
    denominador = float(np.dot(pesos, pesos))
    return float(pesos.sum() ** 2 / denominador) if denominador > 0 else 0.0


def _media_variancia(valores: np.ndarray, pesos: np.ndarray) -> tuple[float, float]:
    soma = float(pesos.sum())
    media = float(np.dot(pesos, valores) / soma)
    variancia = float(np.dot(pesos, (valores - media) ** 2) / soma)
    return media, variancia


def smd(valores: np.ndarray, t: np.ndarray, pesos: np.ndarray) -> float:
    """SMD com variância combinada ((v0+v1)/2); mesma definição de ``src.selecao_nuisance``."""

    m0, v0 = _media_variancia(valores[t == 0], pesos[t == 0])
    m1, v1 = _media_variancia(valores[t == 1], pesos[t == 1])
    escala = np.sqrt((v0 + v1) / 2)
    if escala == 0:
        return 0.0 if m0 == m1 else float("inf")
    return float((m1 - m0) / escala)


def colunas_balanceamento(x: pd.DataFrame) -> Iterator[tuple[str, str, np.ndarray]]:
    """Idade (mediana imputada + indicador de ausência) e um indicador por nível categórico."""

    for coluna in NUMERICAS:
        valores = pd.to_numeric(x[coluna], errors="coerce")
        mediana = float(valores.median()) if valores.notna().any() else 0.0
        yield coluna, "media", valores.fillna(mediana).to_numpy(dtype=float)
        yield coluna, "AUSENTE", valores.isna().to_numpy(dtype=float)
    for coluna in CATEGORICAS:
        serie = x[coluna].astype("string").fillna("AUSENTE")
        for nivel in sorted(serie.unique().tolist()):
            yield coluna, str(nivel), (serie == nivel).to_numpy(dtype=float)


def balanceamento(x: pd.DataFrame, t: np.ndarray, e: np.ndarray) -> pd.DataFrame:
    t = np.asarray(t, dtype=int)
    pesos = pesos_ate(t, e)
    unitarios = np.ones(len(t), dtype=float)
    linhas = []
    for variavel, nivel, valores in colunas_balanceamento(x):
        linhas.append({"variavel": variavel, "nivel": nivel,
                       "smd_bruto": smd(valores, t, unitarios), "smd_ponderado": smd(valores, t, pesos)})
    tabela = pd.DataFrame(linhas)
    tabela["abs_smd_bruto"] = tabela["smd_bruto"].abs()
    tabela["abs_smd_ponderado"] = tabela["smd_ponderado"].abs()
    return tabela


def resumir_suporte(x: pd.DataFrame, t: Sequence[int], e: Sequence[float]) -> tuple[dict[str, Any], pd.DataFrame]:
    """Uma linha de diagnóstico (sem efeito) e a tabela de balanceamento por nível."""

    from src.selecao_nuisance import metricas_probabilidade

    t = np.asarray(t, dtype=int)
    e = np.asarray(e, dtype=float)
    if len(t) != len(e) or len(t) != len(x):
        raise ValueError("x, t e e com tamanhos diferentes.")
    pesos = pesos_ate(t, e)
    linha: dict[str, Any] = {"n": int(len(t)), "n_t0": int((t == 0).sum()), "n_t1": int((t == 1).sum())}
    linha["proporcao_t1"] = linha["n_t1"] / linha["n"]
    metricas = metricas_probabilidade(t, e)
    linha.update(auc_oof=metricas["auc"], log_loss=metricas["log_loss"], brier=metricas["brier"],
                 media_predita=metricas["media_predita"],
                 erro_calibracao_medio=metricas["erro_calibracao_medio"],
                 erro_calibracao_maximo=metricas["erro_calibracao_maximo"])
    for q in QUANTIS_PROPENSITY:
        linha[f"e_{_rotulo_quantil(q)}"] = float(np.quantile(e, q))
    for grupo, nome in ((0, "t0"), (1, "t1")):
        linha[f"e_{nome}_min"] = float(e[t == grupo].min())
        linha[f"e_{nome}_max"] = float(e[t == grupo].max())
    inferior = max(linha["e_t0_min"], linha["e_t1_min"])
    superior = min(linha["e_t0_max"], linha["e_t1_max"])
    linha["suporte_comum_inferior"] = inferior
    linha["suporte_comum_superior"] = superior
    fora_suporte = (e < inferior) | (e > superior)
    linha["fora_suporte_comum_n"] = int(fora_suporte.sum())
    linha["fora_suporte_comum_fracao"] = float(fora_suporte.mean())
    for a, b in ((0.01, 0.99), (0.05, 0.95)):
        rotulo = f"{int(round(a * 100)):03d}_{int(round(b * 100)):03d}"
        fora = (e < a) | (e > b)
        linha[f"fora_{rotulo}_n"] = int(fora.sum())
        linha[f"fora_{rotulo}_fracao"] = float(fora.mean())
        for grupo, nome in ((0, "t0"), (1, "t1")):
            linha[f"fora_{rotulo}_{nome}_n"] = int((fora & (t == grupo)).sum())
    for grupo, nome in ((0, "t0"), (1, "t1")):
        w = pesos[t == grupo]
        linha[f"ess_{nome}"] = ess(w)
        linha[f"ess_{nome}_sobre_n"] = linha[f"ess_{nome}"] / len(w)
        for q in QUANTIS_PESOS:
            linha[f"peso_{nome}_{_rotulo_quantil(q)}"] = float(np.quantile(w, q))
    balanco = balanceamento(x, t, e)
    pior_bruto = balanco.loc[balanco["abs_smd_bruto"].idxmax()]
    pior_ponderado = balanco.loc[balanco["abs_smd_ponderado"].idxmax()]
    linha["max_abs_smd_bruto"] = float(pior_bruto["abs_smd_bruto"])
    linha["max_abs_smd_bruto_variavel"] = f"{pior_bruto['variavel']}={pior_bruto['nivel']}"
    linha["max_abs_smd_ponderado"] = float(pior_ponderado["abs_smd_ponderado"])
    linha["max_abs_smd_ponderado_variavel"] = f"{pior_ponderado['variavel']}={pior_ponderado['nivel']}"
    return linha, balanco


def _rotulo_quantil(q: float) -> str:
    if q == 0:
        return "min"
    if q == 1:
        return "max"
    return "p" + f"{q * 100:g}".replace(".", "_")


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------

def avaliar_gate(linha: Mapping[str, Any], verificacoes: Mapping[str, bool]) -> dict[str, Any]:
    """Aplica literalmente CRITERIOS_GATES_V2 a uma linha formulação x ano.

    ``verificacoes`` traz as checagens estruturais (True = passou): bracos, particoes,
    propensity_valido, sem_vazamento, convergencia, contrato_dados.
    """

    obrigatorias = ("bracos", "particoes", "propensity_valido", "sem_vazamento", "convergencia", "contrato_dados")
    faltantes = [c for c in obrigatorias if c not in verificacoes]
    if faltantes:
        raise ValueError(f"Verificações estruturais ausentes: {faltantes}")
    bloqueios, sinais = [], []
    mapa = {"bracos": "B1_bracos", "particoes": "B2_particoes", "propensity_valido": "B3_propensity_invalido",
            "sem_vazamento": "B4_vazamento", "convergencia": "B5_convergencia", "contrato_dados": "B7_contrato_dados"}
    for chave, codigo in mapa.items():
        if not verificacoes[chave]:
            bloqueios.append(codigo)
    ess_min = min(float(linha["ess_t0_sobre_n"]), float(linha["ess_t1_sobre_n"]))
    if not np.isfinite(ess_min) or ess_min < LIMIARES["ess_relativo_bloqueio"]:
        bloqueios.append("B6_ess_minimo")
    if float(linha["max_abs_smd_ponderado"]) > LIMIARES["smd_ponderado_max"]:
        sinais.append("S1_smd_ponderado")
    if float(linha["fora_005_095_fracao"]) > LIMIARES["fora_005_095_max"]:
        sinais.append("S2_caudas")
    if ess_min < LIMIARES["ess_relativo_sinal"]:
        sinais.append("S3_ess_baixo")
    status = "BLOQUEADO" if bloqueios else ("SINALIZADO" if sinais else "APROVADO")
    return {"status": status, "bloqueios": bloqueios, "sinais": sinais,
            "motivo": "; ".join(bloqueios + sinais) if (bloqueios or sinais) else "nenhuma condição acionada"}


def pior_status(status: Sequence[str]) -> str:
    if not status:
        raise ValueError("Sem status para consolidar.")
    return max(status, key=lambda s: _GRAVIDADE[s])


def consolidar_gates(tabela: pd.DataFrame, janelas: Mapping[str, Sequence[int]]) -> dict[str, Any]:
    """Consolida status por formulação e janela; produz os veredictos de suporte."""

    resultado: dict[str, Any] = {"por_formulacao": {}}
    for formulacao, bloco in tabela.groupby("formulacao", sort=False):
        por_janela = {}
        for nome, anos in janelas.items():
            sub = bloco[bloco["ano"].isin(list(anos))]
            por_janela[nome] = {
                "status": pior_status(sub["status"].tolist()),
                "anos_aprovados": sorted(int(a) for a in sub.loc[sub.status == "APROVADO", "ano"]),
                "anos_sinalizados": sorted(int(a) for a in sub.loc[sub.status == "SINALIZADO", "ano"]),
                "anos_bloqueados": sorted(int(a) for a in sub.loc[sub.status == "BLOQUEADO", "ano"]),
            }
        resultado["por_formulacao"][formulacao] = por_janela
    b = resultado["por_formulacao"]["B"]["principal"]["status"]
    c = resultado["por_formulacao"]["C"]["principal"]["status"]
    resultado["SUPORTE_V2"] = f"SUPORTE_V2_{b}"
    resultado["SUPORTE_SENSIBILIDADE_C"] = f"SUPORTE_SENSIBILIDADE_C_{c}"
    resultado["PRONTIDAO"] = ("PRONTO_PARA_REVISAO_HUMANA_ANTES_DOS_EFEITOS" if b != "BLOQUEADO"
                              else "NAO_PRONTO_PARA_ESTIMAR_V2")
    return resultado


# ---------------------------------------------------------------------------
# Contrato congelado
# ---------------------------------------------------------------------------

CAMPOS_VOLATEIS_CONTRATO = ("registrado_em", "hash_contrato", "estado_git_no_registro")


def hash_contrato(contrato: Mapping[str, Any]) -> str:
    return hash_objeto({k: v for k, v in contrato.items() if k not in CAMPOS_VOLATEIS_CONTRATO})


def registrar_contrato(caminho: str | Path, contrato: Mapping[str, Any]) -> dict[str, Any]:
    """Grava o contrato uma única vez; se já existir, exige conteúdo científico idêntico."""

    caminho = Path(caminho)
    novo = dict(contrato)
    novo["hash_contrato"] = hash_contrato(novo)
    if caminho.exists():
        anterior = json.loads(caminho.read_text(encoding="utf-8"))
        if anterior.get("hash_contrato") != novo["hash_contrato"] or hash_contrato(anterior) != anterior.get("hash_contrato"):
            raise ValueError("Contrato V2 congelado divergente do registrado; não sobrescrever.")
        return anterior
    _gravar_atomico(caminho, (json.dumps(novo, ensure_ascii=False, indent=2, default=str) + "\n").encode("utf-8"))
    return novo


# ---------------------------------------------------------------------------
# Execução de uma formulação x ano (sem efeito)
# ---------------------------------------------------------------------------

def carregar_propensity_notebook08(raiz: str | Path, ano: int, meta: Mapping[str, Any]) -> np.ndarray | None:
    """Leitura somente-leitura do OOF da V1 (A) no cache do notebook 08, com contrato completo."""

    from src import temporal as tp

    if meta["formulacao"] != "A_V1":
        raise ValueError("Cache do notebook 08 só existe para a V1 (A).")
    raiz = Path(raiz)
    contrato = tp.criar_contrato_cache(
        ano=int(ano), parquet_sha256=meta["parquet_sha256"],
        codigo_sha256=tp.sha256_codigo_relevante_temporal(raiz),
        chave_sha256=meta["sha256_sequencia_chave"], regra_ordenacao=_regra_ordem_temporal(ano),
        n=meta["n"], n_t0=meta["n_t0"], n_t1=meta["n_t1"], features=FEATURES,
    )
    return tp.carregar_cache_propensity(raiz / "data/interim/temporal_overlap", contrato)


def _regra_ordem_temporal(ano: int) -> str:
    from src import temporal as tp

    return tp.ORDEM_2024_CERTIFICADA if int(ano) == ANO_BASELINE else tp.ORDEM_CHAVE_TEMPORAL


def executar_formulacao_ano(raiz: str | Path, formulacao: str, ano: int, pasta_cache: str | Path, *,
                            usar_cache_notebook08: bool = True) -> dict[str, Any]:
    """Carrega a população, obtém o propensity OOF e resume suporte. Nenhum efeito é calculado."""

    from src.temporal import caminhos_ano

    raiz = Path(raiz)
    inicio = time.perf_counter()
    parquet = caminhos_ano(raiz, ano).parquet
    sha_observado = sha256_arquivo(parquet)
    sha_esperado = sha256_parquet_esperado(raiz, ano)
    dados, meta = carregar_populacao(parquet, ano, formulacao)
    meta["parquet_sha256"] = sha_observado
    meta["parquet_sha256_confere"] = sha_observado == sha_esperado
    if not meta["parquet_sha256_confere"]:
        raise ValueError(f"Parquet {ano} diverge do hash certificado.")
    codigo = sha256_codigo(raiz)
    e = None
    origem = "ajuste_v2_pre"
    if formulacao == "A_V1" and usar_cache_notebook08:
        e = carregar_propensity_notebook08(raiz, ano, meta)
        if e is not None:
            origem = "cache_notebook08_somente_leitura"
    if e is None:
        e, ajuste = ajustar_propensity_oof(dados, meta, formulacao, pasta_cache, codigo)
    else:
        validar_x(dados.loc[:, list(FEATURES)])
        particoes_diagnostico(dados["tratamento"].to_numpy(dtype=int))
        ajuste = {"n_folds": N_FOLDS_DIAGNOSTICO, "folds": [], "segundos_total": 0.0,
                  "todos_convergiram": True, "particoes_validas": True,
                  "nota": "convergência certificada no notebook 08 (cache com contrato validado)"}
    t = dados["tratamento"].to_numpy(dtype=int)
    inicio_diag = time.perf_counter()
    linha, balanco = resumir_suporte(dados.loc[:, list(FEATURES)], t, e)
    segundos_diag = time.perf_counter() - inicio_diag
    linha = {"formulacao": formulacao, "ano": int(ano), **linha,
             "n_municipios_residencia": meta["n_municipios_residencia"],
             "origem_propensity": origem}
    balanco.insert(0, "ano", int(ano))
    balanco.insert(0, "formulacao", formulacao)
    memoria = memoria_processo_mb()
    execucao = {"segundos_carga": meta["segundos_carga"], "segundos_ajuste": ajuste["segundos_total"],
                "segundos_diagnostico": segundos_diag, "segundos_total": time.perf_counter() - inicio,
                "rss_mb": memoria["rss_mb"], "pico_mb": memoria["pico_mb"]}
    return {"linha": linha, "balanco": balanco, "meta": meta, "ajuste": ajuste, "execucao": execucao,
            "propensity": e, "tratamento": t, "codigo_sha256": codigo}
