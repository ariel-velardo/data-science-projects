"""Elegibilidade, covariáveis e projeção SQL congelada."""
from __future__ import annotations

from collections.abc import Iterable
import pandas as pd
from pathlib import Path
import hashlib
import json
import platform
import sklearn
import duckdb

COLUNAS_BRUTAS_X_PRINCIPAL = (
    "IDADEMAE",
    "ESCMAE2010",
    "RACACORMAE",
    "ESTCIVMAE",
    "PARIDADE",
    "QTDFILMORT",
    "CODMUNRES",
)

COLUNAS_DERIVADAS_X_PRINCIPAL = (
    "IDADEMAE_NUM",
    "ESCOLARIDADE_MAE",
    "RACA_COR_MAE",
    "SITUACAO_CONJUGAL",
    "PARIDADE_CAT",
    "PERDAS_FETAIS_CAT",
    "UF_RESIDENCIA",
)

def construir_tratamento(mes_inicio_prenatal: pd.Series) -> pd.Series:
    """Define T=1 para meses 1-3, T=0 para 4-9 e NA nos demais casos."""

    mes = pd.to_numeric(mes_inicio_prenatal, errors="coerce")
    tratamento = pd.Series(pd.NA, index=mes_inicio_prenatal.index, dtype="Int8")
    tratamento.loc[mes.between(1, 3)] = 1
    tratamento.loc[mes.between(4, 9)] = 0
    return tratamento

def construir_outcome_baixo_peso(
    peso: pd.Series, regra_peso: str = "P1"
) -> pd.Series:
    """Define Y (<2.500 g) sob P0 (>0 g) ou P1 (500-6.000 g)."""

    regra = regra_peso.upper()
    if regra not in {"P0", "P1"}:
        raise ValueError("regra_peso deve ser 'P0' ou 'P1'.")
    peso_num = pd.to_numeric(peso, errors="coerce")
    valido = peso_num.gt(0)
    if regra == "P1":
        valido &= peso_num.between(500, 6000)
    outcome = pd.Series(pd.NA, index=peso.index, dtype="Int8")
    outcome.loc[valido] = peso_num.loc[valido].lt(2500).astype("Int8")
    return outcome

def identificar_gestacao_unica(gravidez: pd.Series) -> pd.Series:
    """Retorna True somente para GRAVIDEZ=1; múltipla/ignorada/missing são False."""

    return pd.to_numeric(gravidez, errors="coerce").eq(1).fillna(False).astype(bool)

def derivar_uf_residencia(codigo_municipio: pd.Series) -> pd.Series:
    """Deriva os dois primeiros dígitos da UF sem modificar CODMUNRES."""

    codigo = codigo_municipio.astype("string")
    valido = codigo.str.fullmatch(r"\d{6}", na=False)
    uf = pd.Series(pd.NA, index=codigo.index, dtype="string")
    uf.loc[valido] = codigo.loc[valido].str[:2]
    return uf

def _categoria_com_ignorado(
    serie: pd.Series, codigos_ignorados: Iterable[str] = ("9", "99")
) -> pd.Series:
    categoria = serie.astype("string").str.strip()
    ignorado = categoria.isna() | categoria.isin(tuple(codigos_ignorados))
    return categoria.mask(ignorado, "IGNORADO").fillna("IGNORADO")

def _categorizar_perdas_fetais(serie: pd.Series) -> pd.Series:
    valor = pd.to_numeric(serie, errors="coerce")
    valor = valor.mask(valor.eq(99))
    saida = pd.Series("IGNORADO", index=serie.index, dtype="string")
    saida.loc[valor.eq(0)] = "0"
    saida.loc[valor.eq(1)] = "1"
    saida.loc[valor.ge(2)] = "2_OU_MAIS"
    return saida

def preparar_covariaveis_principais(dados: pd.DataFrame) -> pd.DataFrame:
    """Cria o X principal parcimonioso, preservando as colunas geográficas brutas."""

    ausentes = sorted(set(COLUNAS_BRUTAS_X_PRINCIPAL) - set(dados.columns))
    if ausentes:
        raise ValueError(f"Colunas necessárias para X ausentes: {', '.join(ausentes)}")

    preparado = dados.copy()
    idade = pd.to_numeric(preparado["IDADEMAE"], errors="coerce")
    preparado["IDADEMAE_NUM"] = idade.mask(~idade.between(10, 59))
    preparado["ESCOLARIDADE_MAE"] = _categoria_com_ignorado(
        preparado["ESCMAE2010"], ("9",)
    )
    preparado["RACA_COR_MAE"] = _categoria_com_ignorado(
        preparado["RACACORMAE"], ("9",)
    )
    preparado["SITUACAO_CONJUGAL"] = _categoria_com_ignorado(
        preparado["ESTCIVMAE"], ("9",)
    )
    preparado["PARIDADE_CAT"] = _categoria_com_ignorado(
        preparado["PARIDADE"], ("9", "99")
    )
    preparado["PERDAS_FETAIS_CAT"] = _categorizar_perdas_fetais(
        preparado["QTDFILMORT"]
    )
    preparado["UF_RESIDENCIA"] = derivar_uf_residencia(
        preparado["CODMUNRES"]
    ).fillna("IGNORADO")
    return preparado

def construir_cenarios_amostra(
    dados: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Constrói A0-A3 e um fluxo reconciliável, sem estimar efeito causal."""

    obrigatorias = {"MESPRENAT", "PESO", "GRAVIDEZ", *COLUNAS_BRUTAS_X_PRINCIPAL}
    ausentes = sorted(obrigatorias - set(dados.columns))
    if ausentes:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(ausentes)}")

    trabalho = dados.copy()
    trabalho["tratamento"] = construir_tratamento(trabalho["MESPRENAT"])
    trabalho["Y_BAIXO_PESO_P0"] = construir_outcome_baixo_peso(
        trabalho["PESO"], "P0"
    )
    trabalho["Y_BAIXO_PESO"] = construir_outcome_baixo_peso(
        trabalho["PESO"], "P1"
    )
    trabalho["GESTACAO_UNICA"] = identificar_gestacao_unica(trabalho["GRAVIDEZ"])

    etapas: list[dict[str, int | float | str]] = []
    total_inicial = len(trabalho)

    def aplicar(etapa: str, motivo: str, mascara: pd.Series) -> None:
        nonlocal trabalho
        n_antes = len(trabalho)
        trabalho = trabalho.loc[mascara.loc[trabalho.index]].copy()
        n_restante = len(trabalho)
        etapas.append(
            {
                "etapa": etapa,
                "n_antes": n_antes,
                "n_excluido": n_antes - n_restante,
                "motivo": motivo,
                "n_restante": n_restante,
                "percentual_base_inicial": (
                    round(100 * n_restante / total_inicial, 6) if total_inicial else 0.0
                ),
            }
        )

    aplicar(
        "A0",
        "T conhecido (MESPRENAT 1-9) e PESO numérico positivo",
        trabalho["tratamento"].notna() & trabalho["Y_BAIXO_PESO_P0"].notna(),
    )
    aplicar(
        "A1",
        "Qualidade P1: 500 g <= PESO <= 6.000 g",
        trabalho["Y_BAIXO_PESO"].notna(),
    )
    aplicar(
        "A2",
        "Amostra principal restrita a gestação única (GRAVIDEZ=1)",
        trabalho["GESTACAO_UNICA"],
    )
    n_antes_x = len(trabalho)
    trabalho = preparar_covariaveis_principais(trabalho)
    etapas.append(
        {
            "etapa": "A3",
            "n_antes": n_antes_x,
            "n_excluido": 0,
            "motivo": (
                "X principal preparado; missing tratado no pipeline, sem exclusão "
                "complete-case"
            ),
            "n_restante": len(trabalho),
            "percentual_base_inicial": (
                round(100 * len(trabalho) / total_inicial, 6) if total_inicial else 0.0
            ),
        }
    )
    return trabalho, pd.DataFrame(etapas)

def _criar_views(conexao: duckdb.DuckDBPyConnection, parquet: Path) -> None:
    caminho = parquet.as_posix().replace("'", "''")
    conexao.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW sinasc AS
        SELECT * FROM read_parquet('{caminho}')
        """
    )
    conexao.execute(
        """
        CREATE OR REPLACE TEMP VIEW fase1_base AS
        SELECT
            *,
            try_cast(MESPRENAT AS INTEGER) AS mesprenat_num,
            try_cast(PESO AS INTEGER) AS peso_num,
            try_cast(GRAVIDEZ AS INTEGER) AS gravidez_num,
            CASE
                WHEN try_cast(MESPRENAT AS INTEGER) BETWEEN 1 AND 3 THEN 1
                WHEN try_cast(MESPRENAT AS INTEGER) BETWEEN 4 AND 9 THEN 0
            END AS tratamento,
            CASE WHEN try_cast(PESO AS INTEGER) > 0
                 THEN CAST(try_cast(PESO AS INTEGER) < 2500 AS INTEGER) END AS y_p0,
            CASE WHEN try_cast(PESO AS INTEGER) BETWEEN 500 AND 6000
                 THEN CAST(try_cast(PESO AS INTEGER) < 2500 AS INTEGER) END AS y_p1
        FROM sinasc
        """
    )
    conexao.execute(
        """
        CREATE OR REPLACE TEMP VIEW amostra_principal AS
        SELECT
            contador,
            tratamento,
            y_p1 AS Y_BAIXO_PESO,
            CASE WHEN try_cast(IDADEMAE AS INTEGER) BETWEEN 10 AND 59
                 THEN try_cast(IDADEMAE AS DOUBLE) END AS IDADEMAE_NUM,
            CASE WHEN try_cast(ESCMAE2010 AS INTEGER) = 9 OR ESCMAE2010 IS NULL
                 THEN 'IGNORADO' ELSE CAST(try_cast(ESCMAE2010 AS INTEGER) AS VARCHAR)
            END AS ESCOLARIDADE_MAE,
            CASE WHEN try_cast(RACACORMAE AS INTEGER) = 9 OR RACACORMAE IS NULL
                 THEN 'IGNORADO' ELSE CAST(try_cast(RACACORMAE AS INTEGER) AS VARCHAR)
            END AS RACA_COR_MAE,
            CASE WHEN try_cast(ESTCIVMAE AS INTEGER) = 9 OR ESTCIVMAE IS NULL
                 THEN 'IGNORADO' ELSE CAST(try_cast(ESTCIVMAE AS INTEGER) AS VARCHAR)
            END AS SITUACAO_CONJUGAL,
            CASE WHEN try_cast(PARIDADE AS INTEGER) IN (9, 99) OR PARIDADE IS NULL
                 THEN 'IGNORADO' ELSE CAST(try_cast(PARIDADE AS INTEGER) AS VARCHAR)
            END AS PARIDADE_CAT,
            CASE
                WHEN try_cast(QTDFILMORT AS INTEGER) = 0 THEN '0'
                WHEN try_cast(QTDFILMORT AS INTEGER) = 1 THEN '1'
                WHEN try_cast(QTDFILMORT AS INTEGER) BETWEEN 2 AND 98 THEN '2_OU_MAIS'
                ELSE 'IGNORADO'
            END AS PERDAS_FETAIS_CAT,
            CASE WHEN regexp_full_match(CAST(CODMUNRES AS VARCHAR), '[0-9]{6}')
                 THEN substr(CAST(CODMUNRES AS VARCHAR), 1, 2)
                 ELSE 'IGNORADO' END AS UF_RESIDENCIA
        FROM fase1_base
        WHERE tratamento IS NOT NULL
          AND y_p1 IS NOT NULL
          AND gravidez_num = 1
        """
    )

def carregar_amostra(parquet, cenario='P1'):
    """Reutiliza a projeção SQL congelada; altera somente filtros de sensibilidade."""
    filtros={
        'P1':'tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num = 1',
        'CONSPRENAT':'tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num = 1 AND (try_cast(CONSPRENAT AS INTEGER) IS DISTINCT FROM 0)',
        'P0':'tratamento IS NOT NULL AND y_p0 IS NOT NULL AND gravidez_num = 1',
        'MULTIPLAS':'tratamento IS NOT NULL AND y_p1 IS NOT NULL AND gravidez_num IN (1,2,3)',
    }
    if cenario not in filtros:
        raise ValueError('Cenário desconhecido.')
    with duckdb.connect() as c:
        _criar_views(c,Path(parquet))
        sql=c.execute("SELECT sql FROM duckdb_views() WHERE view_name='amostra_principal'").fetchone()[0]
        inicio=sql.index(' AS SELECT ')+4
        fim=sql.index(' FROM fase1_base')
        projecao=sql[inicio:fim]
        if cenario=='P0':
            projecao=projecao.replace('y_p1 AS Y_BAIXO_PESO','y_p0 AS Y_BAIXO_PESO')
        consulta=(projecao+', CODMUNRES, try_cast(CONSPRENAT AS INTEGER) AS CONSPRENAT_NUM, '
                  'gravidez_num, peso_num FROM fase1_base WHERE '+filtros[cenario]+' ORDER BY contador')
        dados=c.execute(consulta).df()
        datas=c.execute("SELECT count(*) FILTER (WHERE try_strptime(DTNASC,'%d%m%Y') IS NULL OR year(try_strptime(DTNASC,'%d%m%Y'))<>2024) FROM sinasc").fetchone()[0]
    if datas or dados.empty or dados.contador.isna().any() or dados.contador.duplicated().any():
        raise ValueError('Datas/chave/população inválidas.')
    if dados.CODMUNRES.isna().any() or not dados.CODMUNRES.astype(str).str.fullmatch(r'\d{6}').all():
        raise ValueError('Município ausente ou malformado: não agrupar missing silenciosamente.')
    return dados, dict(cenario=cenario,n=len(dados),n_t1=int(dados.tratamento.sum()),
        n_t0=int((dados.tratamento==0).sum()),prevalencia=float(dados.Y_BAIXO_PESO.mean()),
        n_clusters=int(dados.CODMUNRES.nunique()),n_consprenat_zero=int((dados.CONSPRENAT_NUM==0).sum()),
        codigos_municipio_nao_especificado={str(k):int(v) for k,v in dados.loc[dados.CODMUNRES.str.endswith('0000'),'CODMUNRES'].value_counts().items()},
        n_multipla=int((dados.gravidez_num!=1).sum()),n_peso_fora_p1=int((~dados.peso_num.between(500,6000)).sum()),
        datas_invalidas=int(datas),chave='contador única, não nula; ordem explícita',sql=consulta,
        sha256_ordem_contador=hashlib.sha256('\n'.join(dados.contador.astype(str)).encode()).hexdigest())


def carregar_exercicio(raiz):
    """Valida datas, chave e contrato antes de materializar X/T/Y."""
    pasta = raiz / 'outputs/diagnostics'
    parquet = raiz / 'data/processed/sinasc_2024.parquet'
    fase1 = json.loads((pasta/'fase1_amostra.json').read_text(encoding='utf-8'))
    overlap1 = json.loads((pasta/'fase1_overlap.json').read_text(encoding='utf-8'))
    if overlap1['status'] != 'CONCLUIDO':
        raise ValueError('Fase 1 sem overlap concluído.')
    with duckdb.connect() as c:
        _criar_views(c, parquet)
        # ORDER BY garante identidade dos índices OOF entre execuções.
        dados = c.execute('SELECT * FROM amostra_principal ORDER BY contador').df()
        datas = c.execute("""
            WITH d AS (SELECT try_strptime(DTNASC, '%d%m%Y') AS data FROM sinasc)
            SELECT CAST(min(data) AS VARCHAR) AS minimo, CAST(max(data) AS VARCHAR) AS maximo,
                   count(*) FILTER (WHERE data IS NULL) AS n_missing,
                   count(*) FILTER (WHERE year(data) <> 2024) AS n_fora_2024 FROM d
        """).df().to_dict('records')[0]
        if datas['n_missing'] or datas['n_fora_2024']:
            raise ValueError('Datas inválidas ou fora do ano congelado.')
    if len(dados) != fase1['fluxo_amostra'][-1]['n_restante']:
        raise ValueError('N divergiu do contrato Fase 1.')
    if dados.contador.isna().any() or dados.contador.duplicated().any():
        raise ValueError('Chave inválida.')
    from src.diagnosticos import COLUNAS_PROPENSITY_PRINCIPAL
    from src.modelagem_preditiva import SEED
    x = dados.loc[:, list(COLUNAS_PROPENSITY_PRINCIPAL)]
    t = dados.tratamento.to_numpy(dtype=int)
    y = dados.Y_BAIXO_PESO.to_numpy(dtype=int)
    provenance = {'python': platform.python_version(), 'sklearn': sklearn.__version__,
                  'seed': SEED, 'n': len(dados), 'chave': 'contador', 'ordem': 'contador',
                  'parquet_sha256': hashlib.sha256(parquet.read_bytes()).hexdigest(),
                  'datas_nascimento': datas,
                  'x': list(x.columns), 't': 'MESPRENAT 1-3 versus 4-9', 'y': 'PESO <2500',
                  'populacao': 'SINASC 2024, gravidez única, peso 500-6000g, mês válido'}
    return dados, x, t, y, provenance
