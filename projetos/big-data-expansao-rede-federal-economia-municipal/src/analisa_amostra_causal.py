"""Funções puras da D16 para auditar e descrever a amostra causal.

O módulo não estima efeitos, não seleciona especificações e não grava
artefatos. A narrativa e a interpretação permanecem no notebook acadêmico.
"""
from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

import define_especificacao_causal as d14


ANOS_PAINEL = tuple(range(2007, 2020))
PAPEL_TRATADO = "TRATADO_PRINCIPAL"
PAPEL_CONTROLE = "CONTROLE_NEVER_TREATED"
COLUNAS_OBRIGATORIAS = {
    "codigo_municipio_ibge",
    "ano",
    "papel_causal",
    "candidato_amostra_principal",
    "fl_elegivel_controle_candidato",
    "ano_coorte_candidata",
    "coorte_g",
    "tempo_relativo",
    "elegivel_estimacao_principal",
    "motivo_nao_elegibilidade_estimacao",
    "pessoal_ocupado_assalariado",
    "status_pessoal_ocupado_assalariado",
}


def _codigos(frame: pd.DataFrame) -> pd.Series:
    return frame["codigo_municipio_ibge"].astype("string").str.zfill(7)


def validar_amostra_causal(amostra: pd.DataFrame) -> dict[str, int]:
    """Valida contratos estruturais D14/D15 e retorna contagens auditáveis."""
    faltantes = COLUNAS_OBRIGATORIAS - set(amostra.columns)
    if faltantes:
        raise ValueError(f"amostra causal sem colunas obrigatórias: {sorted(faltantes)}")
    if amostra.empty:
        raise ValueError("amostra causal vazia")

    trabalho = amostra.copy()
    trabalho["codigo_municipio_ibge"] = _codigos(trabalho)
    if trabalho.duplicated(["codigo_municipio_ibge", "ano"]).any():
        raise ValueError("amostra causal com chave municipio-ano duplicada")

    papeis_invalidos = set(trabalho["papel_causal"].dropna()) - {PAPEL_TRATADO, PAPEL_CONTROLE}
    if papeis_invalidos:
        raise ValueError(f"papel causal inesperado: {sorted(papeis_invalidos)}")

    tratados = set(trabalho.loc[trabalho["papel_causal"].eq(PAPEL_TRATADO), "codigo_municipio_ibge"])
    controles = set(trabalho.loc[trabalho["papel_causal"].eq(PAPEL_CONTROLE), "codigo_municipio_ibge"])
    if tratados & controles:
        raise ValueError("municipio marcado simultaneamente como tratado e controle")
    if d14.CODIGO_MUNICIPIO_SIGILO_EXCLUIR in set(trabalho["codigo_municipio_ibge"]):
        raise ValueError(f"municipio {d14.CODIGO_MUNICIPIO_SIGILO_EXCLUIR} deveria estar excluido")

    anos_esperados = set(ANOS_PAINEL)
    anos_por_unidade = trabalho.groupby("codigo_municipio_ibge")["ano"].agg(set)
    unidades_desbalanceadas = int(anos_por_unidade.map(lambda anos: anos != anos_esperados).sum())
    if unidades_desbalanceadas:
        raise ValueError(f"painel base desbalanceado em {unidades_desbalanceadas} unidade(s)")

    tratado = trabalho["papel_causal"].eq(PAPEL_TRATADO)
    controle = trabalho["papel_causal"].eq(PAPEL_CONTROLE)
    if (tratado & ~trabalho["candidato_amostra_principal"].eq(True)).any():
        raise ValueError("tratado sem candidato_amostra_principal=True")
    if (controle & ~trabalho["fl_elegivel_controle_candidato"].eq(True)).any():
        raise ValueError("controle sem fl_elegivel_controle_candidato=True")
    if (tratado & trabalho["fl_elegivel_controle_candidato"].eq(True)).any():
        raise ValueError("tratado tambem marcado como controle no pool estrutural")
    if (controle & trabalho["candidato_amostra_principal"].eq(True)).any():
        raise ValueError("controle tambem marcado como tratado candidato")
    if trabalho.loc[tratado, "coorte_g"].isna().any():
        raise ValueError("tratado sem coorte_g")
    if trabalho.loc[controle, "coorte_g"].notna().any():
        raise ValueError("controle com coorte_g preenchida")

    tempo_esperado = trabalho.loc[tratado, "ano"] - trabalho.loc[tratado, "coorte_g"]
    if not tempo_esperado.eq(trabalho.loc[tratado, "tempo_relativo"]).all():
        raise ValueError("tempo_relativo incompatível com ano - coorte_g")

    inelegiveis = trabalho.loc[~trabalho["elegivel_estimacao_principal"]]
    esperado_inelegivel = (
        inelegiveis["codigo_municipio_ibge"].eq(d14.CODIGO_CABO_FRIO)
        & inelegiveis["ano"].eq(2009)
        & inelegiveis["motivo_nao_elegibilidade_estimacao"].eq(
            "ANO_TRANSICAO_INSTITUCIONAL_CABO_FRIO_2009"
        )
    )
    if len(inelegiveis) != 1 or not esperado_inelegivel.all():
        raise ValueError("mascara de elegibilidade diverge de Cabo Frio/2009")

    return {
        "n_tratados": len(tratados),
        "n_controles": len(controles),
        "n_unidades": trabalho["codigo_municipio_ibge"].nunique(),
        "n_linhas": len(trabalho),
        "n_linhas_elegiveis": int(trabalho["elegivel_estimacao_principal"].sum()),
        "sobreposicao_tratado_controle": len(tratados & controles),
        "unidades_painel_desbalanceado": unidades_desbalanceadas,
    }


def cobertura_event_time(amostra: pd.DataFrame) -> pd.DataFrame:
    """Conta tratados presentes e elegíveis em cada valor observado de k."""
    tratados = amostra.loc[amostra["papel_causal"].eq(PAPEL_TRATADO)].copy()
    total = (
        tratados.groupby("tempo_relativo", as_index=False)
        .agg(n_tratados_no_painel=("codigo_municipio_ibge", "nunique"))
    )
    elegiveis = (
        tratados.loc[tratados["elegivel_estimacao_principal"]]
        .groupby("tempo_relativo", as_index=False)
        .agg(n_tratados_elegiveis=("codigo_municipio_ibge", "nunique"))
    )
    resultado = total.merge(elegiveis, on="tempo_relativo", how="left")
    resultado["n_tratados_elegiveis"] = resultado["n_tratados_elegiveis"].fillna(0).astype(int)
    resultado["perda_por_mascara"] = (
        resultado["n_tratados_no_painel"] - resultado["n_tratados_elegiveis"]
    )
    resultado["tempo_relativo"] = resultado["tempo_relativo"].astype(int)
    return resultado.sort_values("tempo_relativo").reset_index(drop=True)


def _unidades_com_janela_completa(
    amostra: pd.DataFrame,
    codigos_populacao: Iterable[str],
    k_min: int,
    k_max: int,
) -> set[str]:
    codigos = {str(codigo).zfill(7) for codigo in codigos_populacao}
    necessario = set(range(k_min, k_max + 1))
    base = amostra.loc[
        amostra["papel_causal"].eq(PAPEL_TRATADO)
        & amostra["elegivel_estimacao_principal"]
        & _codigos(amostra).isin(codigos)
        & amostra["tempo_relativo"].between(k_min, k_max)
    ].copy()
    base["codigo_municipio_ibge"] = _codigos(base)
    observados = base.groupby("codigo_municipio_ibge")["tempo_relativo"].agg(
        lambda valores: {int(valor) for valor in valores}
    )
    return set(observados.loc[observados.map(lambda valores: necessario.issubset(valores))].index)


def diagnostico_janelas(amostra: pd.DataFrame) -> pd.DataFrame:
    """Separa população por suporte de coorte de cobertura elegível completa."""
    tratados = amostra.loc[amostra["papel_causal"].eq(PAPEL_TRATADO)].copy()
    por_unidade = tratados.groupby("codigo_municipio_ibge", as_index=False).agg(coorte_g=("coorte_g", "first"))
    especificacoes = [
        ("principal_k_-2_2", -2, 2, set(por_unidade["codigo_municipio_ibge"])),
        (
            "sensibilidade_k_-3_2",
            -3,
            2,
            set(por_unidade.loc[por_unidade["coorte_g"].ge(2010), "codigo_municipio_ibge"]),
        ),
    ]
    linhas: list[dict[str, int | str]] = []
    for nome, k_min, k_max, populacao in especificacoes:
        completas = _unidades_com_janela_completa(amostra, populacao, k_min, k_max)
        linhas.append(
            {
                "janela": nome,
                "k_min": k_min,
                "k_max": k_max,
                "n_periodos": k_max - k_min + 1,
                "n_tratados_populacao": len(populacao),
                "n_tratados_janela_completa_elegivel": len(completas),
                "perda_por_cobertura": len(populacao) - len(completas),
            }
        )
    return pd.DataFrame(linhas)


def distribuicao_coortes(amostra: pd.DataFrame) -> pd.DataFrame:
    """Resume as coortes tratadas sem contar linhas repetidas como unidades."""
    tratados = amostra.loc[amostra["papel_causal"].eq(PAPEL_TRATADO)]
    resultado = (
        tratados.groupby("coorte_g", as_index=False)
        .agg(
            n_tratados=("codigo_municipio_ibge", "nunique"),
            n_observacoes_painel=("ano", "size"),
            n_observacoes_elegiveis=("elegivel_estimacao_principal", "sum"),
        )
        .sort_values("coorte_g")
        .reset_index(drop=True)
    )
    resultado["coorte_g"] = resultado["coorte_g"].astype(int)
    resultado["n_observacoes_elegiveis"] = resultado["n_observacoes_elegiveis"].astype(int)
    return resultado


def resumo_amostra_causal(amostra: pd.DataFrame) -> pd.DataFrame:
    """Produz tabela longa pequena para exportação diagnóstica."""
    validacao = validar_amostra_causal(amostra)
    medidas = [
        ("tratados", validacao["n_tratados"]),
        ("controles_never_treated", validacao["n_controles"]),
        ("municipios_total", validacao["n_unidades"]),
        ("municipio_anos_painel_base", validacao["n_linhas"]),
        ("observacoes_elegiveis_estimacao", validacao["n_linhas_elegiveis"]),
        ("observacoes_inelegiveis_estimacao", validacao["n_linhas"] - validacao["n_linhas_elegiveis"]),
        ("anos_inicio", min(ANOS_PAINEL)),
        ("anos_fim", max(ANOS_PAINEL)),
    ]
    return pd.DataFrame(medidas, columns=["medida", "valor"])
