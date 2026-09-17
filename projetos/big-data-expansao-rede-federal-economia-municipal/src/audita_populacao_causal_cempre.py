"""D12 — auditoria offline da população causal e suporte temporal CEMPRE.

Este módulo não estima efeitos, não define uma amostra causal final e não
altera o painel integrado. Ele somente mede, para fins diagnósticos, a
disponibilidade de calendário e do outcome CEMPRE 708 por município/coorte.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PAINEL_INTEGRADO_PATH = ROOT / "data" / "processed" / "cempre_painel_analitico_com_cadastro_causal_2007_2019.parquet"
OUT_DIAGNOSTICO_PATH = ROOT / "outputs" / "diagnostics" / "auditoria_populacao_causal_cempre.csv"

CHAVE_MUNICIPIO = "codigo_municipio_ibge"
COLUNA_OUTCOME_708 = "pessoal_ocupado_assalariado"
COLUNA_STATUS_708 = "status_pessoal_ocupado_assalariado"
COORTES_DIAGNOSTICO = [2009, 2010, 2011, 2012, 2013]


def carrega_painel_integrado(caminho: Path | None = None) -> pd.DataFrame:
    """Carrega o artefato D11 apenas para leitura local."""
    return pd.read_parquet(caminho or PAINEL_INTEGRADO_PATH)


def _contagens_708(df_municipio: pd.DataFrame, coorte: int | None) -> dict[str, int | None]:
    valor_util = df_municipio[COLUNA_OUTCOME_708].notna()
    status = df_municipio[COLUNA_STATUS_708].fillna("").astype(str)
    pre = df_municipio["ano"] < coorte if coorte is not None else pd.Series(False, index=df_municipio.index)
    pos = df_municipio["ano"] >= coorte if coorte is not None else pd.Series(False, index=df_municipio.index)
    return {
        # Sem coorte institucionalmente definida, pré/pós não é zero: é
        # indeterminado. A disponibilidade total de 708 continua auditada.
        "n_pre_calendario": int(pre.sum()) if coorte is not None else None,
        "n_pos_calendario": int(pos.sum()) if coorte is not None else None,
        "n_pre_708_util": int((pre & valor_util).sum()) if coorte is not None else None,
        "n_pos_708_util": int((pos & valor_util).sum()) if coorte is not None else None,
        "n_708_total": int(len(df_municipio)),
        "n_708_missing": int((~valor_util).sum()),
        "n_708_observado": int((status == "observado").sum()),
        "n_708_zero": int(status.str.startswith("zero_").sum()),
        "n_708_sigilo": int((status == "sigilo").sum()),
        "n_708_indisponivel": int((status == "indisponivel").sum()),
    }


def anos_requeridos_janela_adjacente(coorte: int, n_pre: int, n_pos: int) -> list[int]:
    """Retorna os anos consecutivos requeridos na janela adjacente à coorte.

    ``n_pos`` inclui o ano da coorte. Assim, 2 pré + 3 pós para ``g``
    requer exatamente ``g-2, g-1, g, g+1, g+2``.
    """
    return list(range(coorte - n_pre, coorte + n_pos))


def _resultado_janela_adjacente(
    df_municipio: pd.DataFrame,
    coorte: int,
    n_pre: int,
    n_pos: int,
) -> tuple[bool, list[str]]:
    """Verifica calendário e outcome em cada ano da janela, sem contagens substitutas."""
    anos_requeridos = anos_requeridos_janela_adjacente(coorte, n_pre, n_pos)
    anos_presentes = set(df_municipio["ano"].astype(int))
    ausentes_calendario = [ano for ano in anos_requeridos if ano not in anos_presentes]

    por_ano = df_municipio.groupby("ano", sort=False)[COLUNA_OUTCOME_708].apply(lambda serie: serie.notna().any())
    outcome_inutil = [
        ano for ano in anos_requeridos
        if ano in anos_presentes and not bool(por_ano.loc[ano])
    ]
    motivos = (
        [f"calendario_ausente:{ano}" for ano in ausentes_calendario]
        + [f"outcome_708_inutil:{ano}" for ano in outcome_inutil]
    )
    return not motivos, motivos


def _classifica(motivos: list[str]) -> str:
    if not motivos:
        return "SUPORTE_TEMPORAL_SUFICIENTE"
    if any("calendario" in motivo for motivo in motivos):
        return "LIMITACAO_DE_JANELA"
    return "LIMITACAO_DE_OUTCOME"


def auditar_fase_ii(painel: pd.DataFrame) -> pd.DataFrame:
    """Produz uma linha diagnóstica por município Fase II, sem promovê-los.

    A disponibilidade de 708 é definida estritamente pela presença do valor
    numérico. Os status da fonte são apenas contados, nunca recodificados.
    """
    obrigatorias = {
        CHAVE_MUNICIPIO, "ano", COLUNA_OUTCOME_708, COLUNA_STATUS_708,
        "fase_ii", "status_populacao_causal", "candidato_amostra_principal",
        "ano_coorte_candidata",
    }
    ausentes = sorted(obrigatorias - set(painel.columns))
    if ausentes:
        raise ValueError(f"painel integrado sem colunas necessárias ao D12: {ausentes}")

    fase_ii = painel.loc[painel["fase_ii"] == True].copy()  # noqa: E712
    linhas: list[dict[str, Any]] = []
    for codigo, grupo in fase_ii.groupby(CHAVE_MUNICIPIO, sort=True):
        grupo = grupo.sort_values("ano")
        base = grupo.iloc[0]
        coorte_raw = base["ano_coorte_candidata"]
        coorte = int(coorte_raw) if pd.notna(coorte_raw) else None
        metricas = _contagens_708(grupo, coorte)
        candidato = bool(base["candidato_amostra_principal"])
        if candidato:
            elegivel_a, motivos_a = _resultado_janela_adjacente(grupo, coorte, n_pre=2, n_pos=3)
            elegivel_b, motivos_b = _resultado_janela_adjacente(grupo, coorte, n_pre=3, n_pos=3)
            motivos = sorted(set(motivos_a + motivos_b))
            classificacao = _classifica(motivos_a)
        else:
            elegivel_a = None
            elegivel_b = None
            motivos = ["fora_dos_129_candidatos_principais"]
            classificacao = "CASO_INSTITUCIONAL_FORA_DOS_129"

        linhas.append({
            CHAVE_MUNICIPIO: str(codigo),
            "status_populacao_causal": base["status_populacao_causal"],
            "candidato_amostra_principal": candidato,
            "ano_coorte_candidata": float(coorte) if coorte is not None else None,
            **metricas,
            "elegivel_diag_2pre_3pos": elegivel_a,
            "elegivel_diag_3pre_3pos": elegivel_b,
            "motivo_nao_elegibilidade_diagnostica": "; ".join(motivos) if motivos else "",
            "classificacao_diagnostica": classificacao,
        })

    return pd.DataFrame(linhas)


def resumo_por_coorte(painel: pd.DataFrame) -> pd.DataFrame:
    """Resume os candidatos principais por coorte a partir dos próprios dados."""
    diagnostico = auditar_fase_ii(painel)
    candidatos = diagnostico.loc[diagnostico["candidato_amostra_principal"] == True].copy()  # noqa: E712
    linhas: list[dict[str, Any]] = []
    for coorte, grupo in candidatos.groupby("ano_coorte_candidata", sort=True):
        linhas.append({
            "ano_coorte_candidata": int(coorte),
            "n_candidatos": int(len(grupo)),
            "primeiro_ano_pre_disponivel": int(coorte - grupo["n_pre_calendario"].min()),
            "ultimo_ano_pre_disponivel": int(coorte - 1),
            "primeiro_ano_pos_disponivel": int(coorte),
            "ultimo_ano_pos_disponivel": int(coorte + grupo["n_pos_calendario"].min() - 1),
            "min_n_pre_calendario": int(grupo["n_pre_calendario"].min()),
            "min_n_pos_calendario": int(grupo["n_pos_calendario"].min()),
            "min_n_pre_708_util": int(grupo["n_pre_708_util"].min()),
            "min_n_pos_708_util": int(grupo["n_pos_708_util"].min()),
            "n_elegivel_diag_2pre_3pos": int((grupo["elegivel_diag_2pre_3pos"] == True).sum()),  # noqa: E712
            "n_elegivel_diag_3pre_3pos": int((grupo["elegivel_diag_3pre_3pos"] == True).sum()),  # noqa: E712
        })
    return pd.DataFrame(linhas)


def auditar_controles_por_coorte(painel: pd.DataFrame, coortes: list[int] | None = None) -> pd.DataFrame:
    """Mede disponibilidade do pool estrutural; não faz matching nem seleção."""
    coortes = coortes or COORTES_DIAGNOSTICO
    controles = painel.loc[painel["fl_elegivel_controle_candidato"] == True].copy()  # noqa: E712
    nunca_expostos = painel.loc[painel["sem_exposicao_observada_2007_2019"] == True, CHAVE_MUNICIPIO].nunique()  # noqa: E712
    linhas: list[dict[str, Any]] = []
    for coorte in coortes:
        # Agregação vetorizada: preserva exatamente as contagens por
        # município usadas no diagnóstico, sem iterar 4.964 DataFrames por
        # coorte. Isso mantém a execução offline em escala nacional rápida.
        util = controles[COLUNA_OUTCOME_708].notna()
        metricas = pd.DataFrame({
            "n_pre_708_util": (util & (controles["ano"] < coorte)).groupby(controles[CHAVE_MUNICIPIO]).sum(),
            "n_pos_708_util": (util & (controles["ano"] >= coorte)).groupby(controles[CHAVE_MUNICIPIO]).sum(),
            "n_708_missing": (~util).groupby(controles[CHAVE_MUNICIPIO]).sum(),
            "n_708_total": controles.groupby(CHAVE_MUNICIPIO).size(),
        })
        def n_controles_janela_adjacente(n_pre: int) -> int:
            anos = anos_requeridos_janela_adjacente(coorte, n_pre=n_pre, n_pos=3)
            janela = controles.loc[controles["ano"].isin(anos), [CHAVE_MUNICIPIO, "ano", COLUNA_OUTCOME_708]].copy()
            por_municipio = janela.groupby(CHAVE_MUNICIPIO).agg(
                n_anos=("ano", "nunique"),
                n_708_util=(COLUNA_OUTCOME_708, lambda serie: int(serie.notna().sum())),
            )
            elegiveis = (por_municipio["n_anos"] == len(anos)) & (por_municipio["n_708_util"] == len(anos))
            return int(elegiveis.sum())

        controles_2pre_3pos = n_controles_janela_adjacente(n_pre=2)
        controles_3pre_3pos = n_controles_janela_adjacente(n_pre=3)
        completo = (metricas["n_708_missing"] == 0) & (metricas["n_708_total"] == 13)
        linhas.append({
            "ano_coorte_candidata": coorte,
            "n_controles_estruturais": int(len(metricas)),
            "n_nunca_expostos": int(nunca_expostos),
            "controles_2pre_3pos": controles_2pre_3pos,
            "controles_3pre_3pos": controles_3pre_3pos,
            "controles_708_completo_2007_2019": int(completo.sum()),
            "controles_com_missing_708": int((metricas["n_708_missing"] > 0).sum()),
        })
    return pd.DataFrame(linhas)


def executar_auditoria(caminho_painel: Path | None = None, caminho_saida: Path | None = None) -> dict[str, pd.DataFrame]:
    """Executa D12 offline e grava exclusivamente o CSV diagnóstico solicitado."""
    painel = carrega_painel_integrado(caminho_painel)
    diagnostico = auditar_fase_ii(painel)
    resumo = resumo_por_coorte(painel)
    controles = auditar_controles_por_coorte(painel)
    destino = caminho_saida or OUT_DIAGNOSTICO_PATH
    destino.parent.mkdir(parents=True, exist_ok=True)
    diagnostico.to_csv(destino, index=False, encoding="utf-8")
    return {"diagnostico": diagnostico, "resumo_coortes": resumo, "controles_por_coorte": controles}


def main() -> None:
    resultado = executar_auditoria()
    print(resultado["resumo_coortes"].to_string(index=False))
    print(resultado["controles_por_coorte"].to_string(index=False))


if __name__ == "__main__":
    main()
