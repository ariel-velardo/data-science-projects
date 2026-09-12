"""
constroi_cadastro_nacional_exposicao_rede_federal.py
======================================================
Constrói o cadastro nacional de exposição OBSERVADA à Rede Federal,
município-ano, 2007-2019.

Este cadastro é insumo da etapa 1 do `ROADMAP_ACADEMICO.md`
("construir cadastro nacional de exposição") e servirá, em etapa
POSTERIOR e fora do escopo deste script, para montar o pool de
municípios de comparação da Expansão Fase II. Esta rotina NÃO seleciona
controles causais, NÃO executa matching, NÃO avalia suporte comum e NÃO
estima nenhum efeito causal.

A exposição aqui descrita é puramente observacional: presença federal de
EPT ativa no Censo Escolar (`TP_DEPENDENCIA==1`, `TP_SITUACAO_FUNCIONAMENTO==1`,
`IN_PROF==1`) — a mesma regra já usada em `constroi_painel_censo_escolar.py`.
Essa regra identifica presença federal de EPT ativa observada; ela NÃO
identifica, por si só, fase de expansão, criação administrativa,
inauguração, início institucional exato ou pertencimento à Expansão Fase
II (ver `CONTRATO_CAUSAL.md`, seção "Tratamento candidato"). Portanto,
nenhuma linha deste cadastro deve ser lida como tratamento Fase II.

Saídas:
  data/processed/cadastro_nacional_exposicao_rede_federal_municipio_ano_2007_2019.parquet
  data/processed/resumo_exposicao_rede_federal_municipio_2007_2019.parquet

Reutiliza (não recalcula) os agregados federais já construídos por
`constroi_painel_censo_escolar.py`:
  data/interim/censo_federal_municipio_ano_2007_2019.parquet

Constrói apenas o universo municipal anual — para poder representar
exposição zero — diretamente dos microdados brutos locais, lendo em
chunks só as colunas de identificação, sem filtrar por dependência
administrativa (reutiliza `csv_path_in_zip` de
`constroi_painel_censo_escolar.py` para a leitura direta do ZIP).

Não presume uma grade fixa de município × ano: o universo observado em
cada ano é preservado como está no Censo daquele ano (pode variar por
criação/desmembramento/fusão territorial); mudanças de cobertura ficam
registradas explicitamente no resumo municipal (`anos_ausentes_do_universo`).

Uso:
  python src/constroi_cadastro_nacional_exposicao_rede_federal.py

Requer apenas: stdlib + pandas + pyarrow. Não baixa dados nem extrai
CSVs para disco.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

import constroi_painel_censo_escolar as painel_censo

# ---------------------------------------------------------------------------
# Configuração global
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"

FEDERAL_MUNICIPIO_ANO_PATH = DATA_INTERIM / "censo_federal_municipio_ano_2007_2019.parquet"
FASE_II_PAINEL_PATH = DATA_PROCESSED / "painel_presenca_federal_ept_fase_ii_2007_2019.parquet"
FASE_II_MUNICIPIOS_PATH = DATA_PROCESSED / "fase_ii_municipios.parquet"

OUT_PAINEL_NACIONAL = (
    DATA_PROCESSED / "cadastro_nacional_exposicao_rede_federal_municipio_ano_2007_2019.parquet"
)
OUT_RESUMO_MUNICIPAL = DATA_PROCESSED / "resumo_exposicao_rede_federal_municipio_2007_2019.parquet"

ANOS: list[int] = painel_censo.ANOS  # 2007 … 2019 — reutiliza a mesma janela do painel Fase II
ANO_INICIAL, ANO_FINAL = ANOS[0], ANOS[-1]

CHUNKSIZE = painel_censo.CHUNKSIZE

UNIVERSO_USECOLS = ["NU_ANO_CENSO", "CO_MUNICIPIO", "NO_MUNICIPIO", "SG_UF", "CO_UF"]
UNIVERSO_DTYPE: dict[str, str] = {c: "str" for c in UNIVERSO_USECOLS}

COUNT_COLS = [
    "qt_escolas_federais", "qt_escolas_em_atividade", "qt_escolas_com_ept",
    "qt_escolas_com_ept_tecnica", "qt_escolas_federal_ept_ativa",
    "qt_mat_prof", "qt_mat_prof_tec", "qt_tur_prof", "qt_tur_prof_tec",
    "qt_doc_prof", "qt_doc_prof_tec",
]

# flag -> contagem que a define; ordem = observada, ativa, EPT, EPT ativa (proxy principal)
FLAG_DEFINITIONS: dict[str, str] = {
    "fl_presenca_federal": "qt_escolas_federais",
    "fl_presenca_federal_ativa": "qt_escolas_em_atividade",
    "fl_presenca_federal_ept": "qt_escolas_com_ept",
    "fl_presenca_federal_ept_ativa": "qt_escolas_federal_ept_ativa",
}
PROXY_PRINCIPAL = "fl_presenca_federal_ept_ativa"


# ---------------------------------------------------------------------------
# 1. Universo municipal anual (direto dos microdados brutos)
# ---------------------------------------------------------------------------


def read_municipal_universe_from_zip(year: int) -> pd.DataFrame:
    """Lê, diretamente do ZIP bruto do Censo Escolar, o universo de
    municípios observados naquele ano — TODAS as dependências
    administrativas, não apenas federais, porque o objetivo é
    representar exposição zero (um município sem escola federal ainda
    existe e ainda deve aparecer no painel, com contagens zero).

    Lê apenas 5 colunas de identificação, em chunks, sem nunca extrair o
    CSV para disco. Reutiliza `csv_path_in_zip` de
    `constroi_painel_censo_escolar.py` em vez de replicar a lógica de
    abertura do ZIP.
    """
    zip_path, csv_name = painel_censo.csv_path_in_zip(year)
    with zipfile.ZipFile(zip_path) as z:
        raw_bytes = z.read(csv_name)

    buf = io.BytesIO(raw_bytes)
    reader = pd.read_csv(
        buf,
        sep=";",
        usecols=UNIVERSO_USECOLS,
        dtype=UNIVERSO_DTYPE,
        chunksize=CHUNKSIZE,
        low_memory=False,
        encoding="latin-1",
        encoding_errors="replace",
    )

    partes: list[pd.DataFrame] = []
    for chunk in reader:
        chunk["CO_MUNICIPIO"] = chunk["CO_MUNICIPIO"].astype(str).str.strip().str.zfill(7)
        chunk["CO_UF"] = chunk["CO_UF"].astype(str).str.strip().str.zfill(2)
        chunk["NU_ANO_CENSO"] = chunk["NU_ANO_CENSO"].astype(str).str.strip()
        partes.append(chunk.drop_duplicates(subset=["CO_MUNICIPIO"], keep="first"))

    universo = pd.concat(partes, ignore_index=True)
    universo = universo.drop_duplicates(subset=["CO_MUNICIPIO"], keep="first").reset_index(drop=True)

    discordantes = sorted(set(universo["NU_ANO_CENSO"].unique()) - {str(year)})
    if discordantes:
        print(
            "  [AVISO] Universo {}: NU_ANO_CENSO contém valores inesperados {} "
            "(mantido o ano do arquivo).".format(year, discordantes),
            file=sys.stderr,
        )
    # O ano é dado pelo arquivo (um ZIP = um ano do Censo), não pela coluna:
    # mesma convenção de robustez adotada em constroi_painel_censo_escolar.py.
    universo["NU_ANO_CENSO"] = str(year)

    return universo[UNIVERSO_USECOLS]


def build_universo_2007_2019() -> pd.DataFrame:
    """Concatena o universo municipal observado em cada um dos 13 anos.

    Não presume uma grade fixa: o número de municípios por ano é
    preservado exatamente como observado no Censo daquele ano.
    """
    partes = [read_municipal_universe_from_zip(year) for year in ANOS]
    universo = pd.concat(partes, ignore_index=True)
    universo = universo.sort_values(["NU_ANO_CENSO", "CO_MUNICIPIO"], kind="stable").reset_index(drop=True)
    return universo


# ---------------------------------------------------------------------------
# 2. Painel nacional município-ano (universo + contagens federais)
# ---------------------------------------------------------------------------


def build_painel_nacional(universo: pd.DataFrame, federal_mun_ano: pd.DataFrame) -> pd.DataFrame:
    """Left join do universo municipal anual com as contagens federais já
    construídas por `constroi_painel_censo_escolar.py` — preenche zero
    onde não há registro federal. `validate="one_to_one"` garante que
    nenhuma das duas tabelas tem chave duplicada antes da junção."""
    federal = federal_mun_ano.copy()
    federal["CO_MUNICIPIO"] = federal["CO_MUNICIPIO"].astype(str).str.strip().str.zfill(7)
    federal["NU_ANO_CENSO"] = federal["NU_ANO_CENSO"].astype(str).str.strip()

    painel = universo.merge(
        federal[["CO_MUNICIPIO", "NU_ANO_CENSO", *COUNT_COLS]],
        on=["CO_MUNICIPIO", "NU_ANO_CENSO"],
        how="left",
        validate="one_to_one",
    )

    for col in COUNT_COLS:
        painel[col] = painel[col].fillna(0).astype("Int64")

    for flag, count_col in FLAG_DEFINITIONS.items():
        painel[flag] = painel[count_col] > 0

    id_cols = ["CO_MUNICIPIO", "NU_ANO_CENSO", "NO_MUNICIPIO", "SG_UF", "CO_UF"]
    painel = painel[id_cols + COUNT_COLS + list(FLAG_DEFINITIONS)]
    painel = painel.sort_values(["CO_MUNICIPIO", "NU_ANO_CENSO"], kind="stable").reset_index(drop=True)
    return painel


# ---------------------------------------------------------------------------
# 3. Validações do painel nacional (validações 1-9)
# ---------------------------------------------------------------------------


def validate_painel_nacional(painel: pd.DataFrame) -> None:
    """Valida estrutura do painel nacional. Nunca corrige silenciosamente:
    levanta `ValueError` com exemplos concretos diante de qualquer
    violação."""
    anos = pd.to_numeric(painel["NU_ANO_CENSO"], errors="coerce")
    if anos.isna().any():
        raise ValueError("NU_ANO_CENSO contém valor não numérico ou nulo no painel nacional.")
    anos_presentes = set(anos.astype(int).unique())
    anos_esperados = set(ANOS)
    if anos_presentes != anos_esperados:
        raise ValueError(
            f"Painel nacional deve cobrir exatamente {ANO_INICIAL}-{ANO_FINAL}. "
            f"Faltando: {sorted(anos_esperados - anos_presentes)}; "
            f"excedentes: {sorted(anos_presentes - anos_esperados)}."
        )

    chave = painel[["CO_MUNICIPIO", "NU_ANO_CENSO"]]
    dup = chave.duplicated()
    if dup.any():
        raise ValueError(
            f"Chave município-ano duplicada no painel nacional ({int(dup.sum())} casos). "
            f"Exemplos: {chave[dup].head(5).to_dict('records')}"
        )

    if painel["CO_MUNICIPIO"].isna().any():
        raise ValueError("CO_MUNICIPIO nulo no painel nacional.")

    tamanho_errado = painel.loc[painel["CO_MUNICIPIO"].str.len() != 7, "CO_MUNICIPIO"]
    if not tamanho_errado.empty:
        raise ValueError(
            f"CO_MUNICIPIO com comprimento != 7 em {len(tamanho_errado)} linhas. "
            f"Exemplos: {tamanho_errado.head(5).tolist()}"
        )

    incoerente_uf = painel.loc[painel["CO_MUNICIPIO"].str[:2] != painel["CO_UF"]]
    if not incoerente_uf.empty:
        raise ValueError(
            f"CO_UF incoerente com os dois primeiros dígitos de CO_MUNICIPIO em "
            f"{len(incoerente_uf)} linhas. Exemplos: "
            f"{incoerente_uf[['CO_MUNICIPIO', 'CO_UF']].head(5).to_dict('records')}"
        )

    for col in COUNT_COLS:
        negativos = painel.loc[painel[col].fillna(0) < 0]
        if not negativos.empty:
            raise ValueError(
                f"Contagem negativa em {col} ({len(negativos)} linhas). Exemplos: "
                f"{negativos[['CO_MUNICIPIO', 'NU_ANO_CENSO', col]].head(5).to_dict('records')}"
            )

    for flag, count_col in FLAG_DEFINITIONS.items():
        incoerente = painel.loc[painel[flag] != (painel[count_col] > 0)]
        if not incoerente.empty:
            raise ValueError(
                f"Flag {flag} incoerente com a contagem {count_col} em {len(incoerente)} "
                f"linhas. Exemplos: "
                f"{incoerente[['CO_MUNICIPIO', 'NU_ANO_CENSO', flag, count_col]].head(5).to_dict('records')}"
            )

    implicacao_quebrada = painel.loc[
        painel["fl_presenca_federal_ept_ativa"] & ~painel["fl_presenca_federal"]
    ]
    if not implicacao_quebrada.empty:
        raise ValueError(
            "fl_presenca_federal_ept_ativa=True sem fl_presenca_federal=True em "
            f"{len(implicacao_quebrada)} linhas (EPT ativa deve implicar presença federal). "
            f"Exemplos: {implicacao_quebrada[['CO_MUNICIPIO', 'NU_ANO_CENSO']].head(5).to_dict('records')}"
        )


# ---------------------------------------------------------------------------
# 4. Reconciliações (validações 9-11)
# ---------------------------------------------------------------------------


def validate_reconciliacao_federal(painel: pd.DataFrame, federal_mun_ano: pd.DataFrame) -> None:
    """Reconcilia o painel nacional com `censo_federal_municipio_ano_2007_2019.parquet`:
    nenhum registro federal positivo pode ter sido perdido pelo merge à
    esquerda, as contagens devem bater exatamente para as chaves em
    comum, e todo município SEM registro federal deve ter contagens
    exatamente zero (validação 9)."""
    federal = federal_mun_ano.copy()
    federal["CO_MUNICIPIO"] = federal["CO_MUNICIPIO"].astype(str).str.strip().str.zfill(7)
    federal["NU_ANO_CENSO"] = federal["NU_ANO_CENSO"].astype(str).str.strip()

    chave_federal = set(zip(federal["CO_MUNICIPIO"], federal["NU_ANO_CENSO"]))
    chave_painel = set(zip(painel["CO_MUNICIPIO"], painel["NU_ANO_CENSO"]))

    ausentes = sorted(chave_federal - chave_painel)
    if ausentes:
        raise ValueError(
            f"{len(ausentes)} município-ano com registro federal positivo ausente do "
            f"universo do painel nacional (perdido pelo merge à esquerda). "
            f"Exemplos: {ausentes[:5]}."
        )

    comparaveis = painel.merge(
        federal[["CO_MUNICIPIO", "NU_ANO_CENSO", *COUNT_COLS]],
        on=["CO_MUNICIPIO", "NU_ANO_CENSO"],
        how="inner",
        suffixes=("_painel", "_federal"),
    )
    for col in COUNT_COLS:
        divergentes = comparaveis.loc[comparaveis[f"{col}_painel"] != comparaveis[f"{col}_federal"]]
        if not divergentes.empty:
            raise ValueError(
                f"Divergência em {col} entre o painel nacional e "
                f"censo_federal_municipio_ano_2007_2019.parquet ({len(divergentes)} casos). "
                f"Exemplos: {divergentes[['CO_MUNICIPIO', 'NU_ANO_CENSO', f'{col}_painel', f'{col}_federal']].head(5).to_dict('records')}"
            )

    painel_idx = pd.MultiIndex.from_arrays([painel["CO_MUNICIPIO"], painel["NU_ANO_CENSO"]])
    federal_idx = pd.MultiIndex.from_arrays([federal["CO_MUNICIPIO"], federal["NU_ANO_CENSO"]])
    tem_registro_federal = painel_idx.isin(federal_idx)
    sem_federal = painel.loc[~tem_registro_federal]
    nao_zerado = sem_federal.loc[(sem_federal[COUNT_COLS] != 0).any(axis=1)]
    if not nao_zerado.empty:
        raise ValueError(
            f"{len(nao_zerado)} município-ano SEM registro em "
            f"censo_federal_municipio_ano_2007_2019.parquet têm contagem diferente de zero. "
            f"Exemplos: {nao_zerado[['CO_MUNICIPIO', 'NU_ANO_CENSO']].head(5).to_dict('records')}"
        )


def _chaves_duplicadas(df: pd.DataFrame) -> list[tuple[str, str]]:
    """Retorna as chaves (CO_MUNICIPIO, NU_ANO_CENSO) que aparecem mais de
    uma vez em `df`, sem duplicar a própria chave na lista retornada."""
    chave = df[["CO_MUNICIPIO", "NU_ANO_CENSO"]]
    repetidas = chave[chave.duplicated(keep=False)].drop_duplicates()
    return list(repetidas.itertuples(index=False, name=None))


def validate_reconciliacao_fase_ii(
    painel: pd.DataFrame, fase_ii_painel: pd.DataFrame, fase_ii_codes: set[str]
) -> None:
    """Reconcilia o subconjunto dos 147 municípios da Fase II, dentro do
    painel nacional, contra `painel_presenca_federal_ept_fase_ii_2007_2019.parquet`
    já aprovado — para todas as colunas comparáveis (contagens + as 3
    flags que já existiam naquele painel).

    Valida os conjuntos COMPLETOS de chaves (município-ano) dos dois lados
    contra o conjunto esperado (147 municípios × 13 anos) ANTES de
    comparar qualquer valor. Um merge interno (`how="inner"`) nunca é
    usado como substituto dessa validação: ele descarta silenciosamente
    qualquer chave de um lado que não exista no outro, o que aceitaria
    uma chave excedente no painel Fase II de referência sem erro."""
    esperado = {(codigo, str(ano)) for codigo in fase_ii_codes for ano in ANOS}

    fase_ii = fase_ii_painel.copy()
    fase_ii["CO_MUNICIPIO"] = fase_ii["CO_MUNICIPIO"].astype(str).str.strip().str.zfill(7)
    fase_ii["NU_ANO_CENSO"] = fase_ii["NU_ANO_CENSO"].astype(str).str.strip()

    subset = painel.loc[painel["CO_MUNICIPIO"].isin(fase_ii_codes)].copy()

    # 1-2: ausência de chaves duplicadas, verificada separadamente em cada lado.
    duplicadas_fase_ii = _chaves_duplicadas(fase_ii)
    if duplicadas_fase_ii:
        raise ValueError(
            f"Lado: painel Fase II de referência. Chave município-ano duplicada "
            f"({len(duplicadas_fase_ii)} chaves). Exemplos: {duplicadas_fase_ii[:5]}."
        )
    duplicadas_nacional = _chaves_duplicadas(subset)
    if duplicadas_nacional:
        raise ValueError(
            f"Lado: subconjunto Fase II do painel nacional. Chave município-ano "
            f"duplicada ({len(duplicadas_nacional)} chaves). Exemplos: {duplicadas_nacional[:5]}."
        )

    chave_fase_ii = set(zip(fase_ii["CO_MUNICIPIO"], fase_ii["NU_ANO_CENSO"]))
    chave_nacional = set(zip(subset["CO_MUNICIPIO"], subset["NU_ANO_CENSO"]))

    # 3, 5, 6: painel Fase II de referência deve ser exatamente o conjunto esperado.
    ausentes_fase_ii = sorted(esperado - chave_fase_ii)
    excedentes_fase_ii = sorted(chave_fase_ii - esperado)
    if ausentes_fase_ii or excedentes_fase_ii:
        raise ValueError(
            f"Lado: painel Fase II de referência. Conjunto de chaves diverge do "
            f"esperado ({len(fase_ii_codes)} municípios × {len(ANOS)} anos = "
            f"{len(esperado)} chaves). Ausentes: {ausentes_fase_ii[:5]}. "
            f"Excedentes: {excedentes_fase_ii[:5]}."
        )

    # 4, 5, 6: subconjunto Fase II do painel nacional deve ser exatamente o conjunto esperado.
    ausentes_nacional = sorted(esperado - chave_nacional)
    excedentes_nacional = sorted(chave_nacional - esperado)
    if ausentes_nacional or excedentes_nacional:
        raise ValueError(
            f"Lado: subconjunto Fase II do painel nacional. Conjunto de chaves diverge "
            f"do esperado ({len(fase_ii_codes)} municípios × {len(ANOS)} anos = "
            f"{len(esperado)} chaves). Ausentes: {ausentes_nacional[:5]}. "
            f"Excedentes: {excedentes_nacional[:5]}."
        )

    # 7: só agora, com os dois conjuntos de chaves provadamente iguais ao
    # esperado, comparar valores — o merge com validate="one_to_one" é
    # seguro porque ambos os lados já são, por construção, únicos e
    # idênticos em chave.
    colunas_comparaveis = COUNT_COLS + [
        "fl_presenca_federal", "fl_presenca_federal_ept", "fl_presenca_federal_ept_ativa",
    ]
    comparado = subset.merge(
        fase_ii[["CO_MUNICIPIO", "NU_ANO_CENSO", *colunas_comparaveis]],
        on=["CO_MUNICIPIO", "NU_ANO_CENSO"],
        how="inner",
        suffixes=("_nacional", "_fase_ii"),
        validate="one_to_one",
    )
    if len(comparado) != len(esperado):
        raise ValueError(
            f"Reconciliação Fase II produziu {len(comparado)} linhas comparáveis; "
            f"esperado {len(esperado)}."
        )

    for col in colunas_comparaveis:
        divergentes = comparado.loc[comparado[f"{col}_nacional"] != comparado[f"{col}_fase_ii"]]
        if not divergentes.empty:
            raise ValueError(
                f"Divergência em {col} entre o subconjunto Fase II do painel nacional e o "
                f"painel Fase II aprovado ({len(divergentes)} casos). Exemplos: "
                f"{divergentes[['CO_MUNICIPIO', 'NU_ANO_CENSO', f'{col}_nacional', f'{col}_fase_ii']].head(5).to_dict('records')}"
            )


# ---------------------------------------------------------------------------
# 5. Resumo municipal da exposição observada
# ---------------------------------------------------------------------------


def summarize_observed_exposure(years: list[int], exposed: list[bool]) -> dict[str, Any]:
    """Resume a exposição observada (proxy `fl_presenca_federal_ept_ativa`)
    de um município a partir apenas dos anos em que ele aparece no
    universo do Censo — sem presumir cobertura de 13 anos.

    Não reaproveita `auditoria_timing_tratamento.summarize_presence_trajectory`
    porque aquela função exige, por contrato, exatamente os 13 anos
    2007-2019 em ordem (adequado à grade fixa 147×13 da Fase II) — aqui o
    universo de anos observados pode ser menor ou descontínuo por
    município, e forçar aquele contrato faria a função levantar erro em
    qualquer município com cobertura incompleta, que é exatamente o caso
    que esta rotina precisa tratar explicitamente, não excluir.
    """
    anos_expostos = sorted(year for year, exp in zip(years, exposed) if exp)
    if not anos_expostos:
        return {
            "primeiro_ano_exposicao_observada": None,
            "ultimo_ano_exposicao_observada": None,
            "n_anos_com_exposicao_observada": 0,
            "padrao_intermitente_exposicao_observada": False,
            "anos_expostos": "",
        }

    primeiro, ultimo = anos_expostos[0], anos_expostos[-1]
    exposicao_por_ano = dict(zip(years, exposed))
    observados_na_janela = [
        exposicao_por_ano[y] for y in years if primeiro <= y <= ultimo
    ]
    intermitente = any(not e for e in observados_na_janela)

    return {
        "primeiro_ano_exposicao_observada": primeiro,
        "ultimo_ano_exposicao_observada": ultimo,
        "n_anos_com_exposicao_observada": len(anos_expostos),
        "padrao_intermitente_exposicao_observada": intermitente,
        "anos_expostos": ";".join(str(y) for y in anos_expostos),
    }


def build_resumo_municipal(painel: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por código municipal observado em 2007-2019, resumindo a
    exposição observada à proxy principal (`fl_presenca_federal_ept_ativa`).

    Usa nomes que deixam claro que se trata de exposição OBSERVADA na
    janela (não conclusão institucional): `sem_exposicao_observada_2007_2019`,
    nunca "never-treated"; o primeiro ano observado não é tratado como
    coorte causal validada.
    """
    linhas: list[dict[str, Any]] = []
    for codigo, grupo in painel.groupby("CO_MUNICIPIO", sort=False):
        grupo = grupo.sort_values("NU_ANO_CENSO", kind="stable")
        anos_no_universo = grupo["NU_ANO_CENSO"].astype(int).tolist()
        exposto = grupo[PROXY_PRINCIPAL].astype(bool).tolist()
        resumo_exposicao = summarize_observed_exposure(anos_no_universo, exposto)

        ultima_linha = grupo.iloc[-1]
        anos_ausentes = sorted(set(ANOS) - set(anos_no_universo))
        n_exposicao = resumo_exposicao["n_anos_com_exposicao_observada"]

        linhas.append({
            "codigo_municipio_ibge": codigo,
            "municipio": ultima_linha["NO_MUNICIPIO"],
            "uf": ultima_linha["SG_UF"],
            "co_uf": ultima_linha["CO_UF"],
            "primeiro_ano_exposicao_observada": resumo_exposicao["primeiro_ano_exposicao_observada"],
            "ultimo_ano_exposicao_observada": resumo_exposicao["ultimo_ano_exposicao_observada"],
            "n_anos_no_universo": len(anos_no_universo),
            "n_anos_com_exposicao_observada": n_exposicao,
            "exposicao_observada_em_2007": bool(
                any(y == ANO_INICIAL and e for y, e in zip(anos_no_universo, exposto))
            ),
            "exposicao_observada_2007_2019": n_exposicao > 0,
            "sem_exposicao_observada_2007_2019": n_exposicao == 0,
            "presente_nos_13_anos_do_universo": len(anos_no_universo) == len(ANOS),
            "padrao_intermitente_exposicao_observada": resumo_exposicao["padrao_intermitente_exposicao_observada"],
            "anos_expostos": resumo_exposicao["anos_expostos"],
            "anos_ausentes_do_universo": ";".join(str(a) for a in anos_ausentes),
        })

    colunas = [
        "codigo_municipio_ibge", "municipio", "uf", "co_uf",
        "primeiro_ano_exposicao_observada", "ultimo_ano_exposicao_observada",
        "n_anos_no_universo", "n_anos_com_exposicao_observada",
        "exposicao_observada_em_2007", "exposicao_observada_2007_2019",
        "sem_exposicao_observada_2007_2019", "presente_nos_13_anos_do_universo",
        "padrao_intermitente_exposicao_observada", "anos_expostos", "anos_ausentes_do_universo",
    ]
    resumo = pd.DataFrame(linhas)[colunas]
    resumo["primeiro_ano_exposicao_observada"] = resumo["primeiro_ano_exposicao_observada"].astype("Int64")
    resumo["ultimo_ano_exposicao_observada"] = resumo["ultimo_ano_exposicao_observada"].astype("Int64")
    resumo["n_anos_no_universo"] = resumo["n_anos_no_universo"].astype("Int64")
    resumo["n_anos_com_exposicao_observada"] = resumo["n_anos_com_exposicao_observada"].astype("Int64")
    resumo = resumo.sort_values("codigo_municipio_ibge", kind="stable").reset_index(drop=True)
    return resumo


# ---------------------------------------------------------------------------
# 6. Validações do resumo municipal (validações 12-15)
# ---------------------------------------------------------------------------


def validate_resumo_municipal(resumo: pd.DataFrame, painel: pd.DataFrame) -> None:
    """Reconcilia o resumo municipal contra o painel nacional, recomputando
    cada agregado diretamente do painel — nunca chamando
    `build_resumo_municipal` de volta, para que a validação não seja uma
    tautologia sobre a própria função que construiu o resumo."""
    if resumo["codigo_municipio_ibge"].isna().any() or resumo["codigo_municipio_ibge"].duplicated().any():
        raise ValueError("Resumo municipal deve ter um código municipal único e não nulo por linha.")

    if set(resumo["codigo_municipio_ibge"]) != set(painel["CO_MUNICIPIO"]):
        raise ValueError("Conjunto de municípios do resumo diverge do conjunto observado no painel nacional.")

    indexado = resumo.set_index("codigo_municipio_ibge", drop=False)

    n_anos_painel = painel.groupby("CO_MUNICIPIO").size().reindex(indexado.index)
    incoerente_n_anos = indexado.index[indexado["n_anos_no_universo"] != n_anos_painel]
    if len(incoerente_n_anos):
        raise ValueError(f"n_anos_no_universo incoerente com o painel nacional: {incoerente_n_anos.tolist()[:5]}")

    n_exp_painel = painel.groupby("CO_MUNICIPIO")[PROXY_PRINCIPAL].sum().reindex(indexado.index)
    incoerente_n_exp = indexado.index[indexado["n_anos_com_exposicao_observada"] != n_exp_painel]
    if len(incoerente_n_exp):
        raise ValueError(
            f"n_anos_com_exposicao_observada incoerente com o painel nacional: {incoerente_n_exp.tolist()[:5]}"
        )

    grupos_painel = {
        codigo: grupo.sort_values("NU_ANO_CENSO", kind="stable")
        for codigo, grupo in painel.groupby("CO_MUNICIPIO", sort=False)
    }

    for row in resumo.itertuples(index=False):
        anos_expostos = [int(a) for a in row.anos_expostos.split(";") if a]
        primeiro_esperado = min(anos_expostos) if anos_expostos else None
        ultimo_esperado = max(anos_expostos) if anos_expostos else None
        primeiro_real = None if pd.isna(row.primeiro_ano_exposicao_observada) else int(row.primeiro_ano_exposicao_observada)
        ultimo_real = None if pd.isna(row.ultimo_ano_exposicao_observada) else int(row.ultimo_ano_exposicao_observada)
        if primeiro_real != primeiro_esperado or ultimo_real != ultimo_esperado:
            raise ValueError(
                f"{row.codigo_municipio_ibge}: primeiro/último ano incoerente com "
                f"anos_expostos={row.anos_expostos!r}."
            )

        grupo = grupos_painel[row.codigo_municipio_ibge]
        anos_grupo = grupo["NU_ANO_CENSO"].astype(int).tolist()
        exposto_grupo = dict(zip(anos_grupo, grupo[PROXY_PRINCIPAL].astype(bool).tolist()))
        if primeiro_real is None:
            intermitente_esperado = False
        else:
            janela = [exposto_grupo[a] for a in anos_grupo if primeiro_real <= a <= ultimo_real]
            intermitente_esperado = any(not e for e in janela)
        if bool(row.padrao_intermitente_exposicao_observada) != intermitente_esperado:
            raise ValueError(
                f"{row.codigo_municipio_ibge}: padrao_intermitente_exposicao_observada "
                f"incoerente com o painel nacional."
            )

        anos_ausentes = [int(a) for a in row.anos_ausentes_do_universo.split(";") if a]
        if int(row.n_anos_no_universo) + len(anos_ausentes) != len(ANOS):
            raise ValueError(
                f"{row.codigo_municipio_ibge}: n_anos_no_universo + anos_ausentes_do_universo "
                f"!= {len(ANOS)}."
            )
        if bool(row.presente_nos_13_anos_do_universo) != (len(anos_ausentes) == 0):
            raise ValueError(
                f"{row.codigo_municipio_ibge}: presente_nos_13_anos_do_universo incoerente "
                f"com anos_ausentes_do_universo."
            )


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def main() -> dict[str, Any]:
    print("=" * 70)
    print("CADASTRO NACIONAL DE EXPOSIÇÃO À REDE FEDERAL — 2007-2019")
    print("=" * 70)

    print("\n[1] Lendo agregados locais já construídos (não recalcula EPT federal)...")
    federal_mun_ano = pd.read_parquet(FEDERAL_MUNICIPIO_ANO_PATH)
    fase_ii_painel = pd.read_parquet(FASE_II_PAINEL_PATH)
    fase_ii_mun = pd.read_parquet(FASE_II_MUNICIPIOS_PATH)
    fase_ii_codes = set(fase_ii_mun["codigo_municipio_ibge"].astype(str).str.zfill(7))
    print(f"    censo_federal_municipio_ano: {len(federal_mun_ano):,} linhas")
    print(f"    painel Fase II aprovado: {len(fase_ii_painel):,} linhas")
    print(f"    municípios Fase II: {len(fase_ii_codes)}")

    print("\n[2] Construindo universo municipal anual a partir dos microdados brutos...")
    universo = build_universo_2007_2019()
    contagem_por_ano = universo.groupby("NU_ANO_CENSO").size().to_dict()
    for ano, n in sorted(contagem_por_ano.items()):
        print(f"    {ano}: {n:,} municípios no universo")

    print("\n[3] Montando o painel nacional município-ano...")
    painel = build_painel_nacional(universo, federal_mun_ano)
    print(f"    Linhas do painel nacional: {len(painel):,}")
    print(f"    Municípios distintos: {painel['CO_MUNICIPIO'].nunique():,}")

    print("\n[4] Validando o painel nacional...")
    validate_painel_nacional(painel)
    validate_reconciliacao_federal(painel, federal_mun_ano)
    validate_reconciliacao_fase_ii(painel, fase_ii_painel, fase_ii_codes)
    print("    OK — validações estruturais e reconciliações do painel nacional passaram.")

    print("\n[5] Construindo o resumo municipal da exposição observada...")
    resumo = build_resumo_municipal(painel)
    print(f"    Linhas do resumo municipal: {len(resumo):,}")

    print("\n[6] Validando o resumo municipal...")
    validate_resumo_municipal(resumo, painel)
    print("    OK — validações do resumo municipal passaram.")

    print("\n[7] Salvando Parquets...")
    OUT_PAINEL_NACIONAL.parent.mkdir(parents=True, exist_ok=True)
    painel.to_parquet(OUT_PAINEL_NACIONAL, index=False, engine="pyarrow")
    resumo.to_parquet(OUT_RESUMO_MUNICIPAL, index=False, engine="pyarrow")
    print(f"    {OUT_PAINEL_NACIONAL}")
    print(f"    {OUT_RESUMO_MUNICIPAL}")

    n_total_mun = int(resumo["codigo_municipio_ibge"].nunique())
    n_sem_exposicao = int(resumo["sem_exposicao_observada_2007_2019"].sum())
    n_em_2007 = int(resumo["exposicao_observada_em_2007"].sum())
    n_com_primeiro_ano = int(resumo["primeiro_ano_exposicao_observada"].notna().sum())
    n_primeira_2008_2019 = n_com_primeiro_ano - n_em_2007
    n_intermitente = int(resumo["padrao_intermitente_exposicao_observada"].sum())
    n_13_anos = int(resumo["presente_nos_13_anos_do_universo"].sum())

    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)
    print(f"Total de municípios distintos observados 2007-2019: {n_total_mun:,}")
    print(f"Sem exposição observada (sem_exposicao_observada_2007_2019): {n_sem_exposicao:,}")
    print(f"Exposição já observada em 2007: {n_em_2007:,}")
    print(f"Primeira exposição observada entre 2008 e 2019: {n_primeira_2008_2019:,}")
    print(f"Padrão intermitente de exposição observada: {n_intermitente:,}")
    print(f"Presentes nos 13 anos do universo: {n_13_anos:,} / {n_total_mun:,}")
    print(f"Reconciliação exata do subconjunto Fase II ({len(fase_ii_codes)} municípios): OK")

    return {
        "n_painel": len(painel),
        "n_resumo": len(resumo),
        "contagem_por_ano": contagem_por_ano,
        "n_total_mun": n_total_mun,
        "n_sem_exposicao": n_sem_exposicao,
        "n_em_2007": n_em_2007,
        "n_primeira_2008_2019": n_primeira_2008_2019,
        "n_intermitente": n_intermitente,
        "n_13_anos": n_13_anos,
    }


if __name__ == "__main__":
    main()
