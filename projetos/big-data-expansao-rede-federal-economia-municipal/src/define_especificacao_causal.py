"""D14 — especificação causal congelada (contrato de especificação).

Este módulo NÃO estima nenhum efeito, não roda Callaway-Sant'Anna, não faz
matching e não persiste amostra causal materializada. Ele apenas expressa,
como configuração explícita e testável, as decisões metodológicas do D14
sobre unidades tratadas/controle principais, exclusão do sigilo e janelas
de event-time — reaproveitando o cadastro causal já aprovado (D11/D12/D13),
sem recalcular nem reinterpretar timing.

Nenhuma coluna `post`, `event_time` ou `tratado` é criada de forma
persistente em nenhum artefato; `event_time()` é um utilitário didático,
calculado em memória.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

import diagnostica_identificacao_causal as d13

CHAVE_MUNICIPIO = d13.CHAVE_MUNICIPIO
COLUNA_OUTCOME_708 = d13.COLUNA_OUTCOME_708

# Município com a única célula de CEMPRE 708 sigilosa do pool estrutural
# (ano 2012). Excluído do painel causal principal inteiro (não apenas do
# ano 2012) para preservar um painel balanceado — nunca imputado, nunca
# zerado. Ver ESTADO_ATUAL.md / notebook, seção do D14 "Sigilo".
CODIGO_MUNICIPIO_SIGILO_EXCLUIR = "5003900"

# Único candidato com origem_coorte='institucional_validada' entre os 129 —
# ano_transicao=2009 (parcial, excluído da estimação) e
# primeiro_ano_completo=2010 (igual a ano_coorte_candidata). Documentado
# aqui apenas como referência; a regra em si já está no cadastro causal
# aprovado (D11) e não é reinterpretada.
CODIGO_CABO_FRIO = "3300704"


@dataclass(frozen=True)
class EspecificacaoCausal:
    """Contrato de especificação causal D14 — decisões congeladas.

    Nenhum campo aqui representa um efeito estimado; é configuração da
    especificação para uma etapa de estimação futura, ainda não executada.
    """

    outcome_principal: str = COLUNA_OUTCOME_708
    outcome_unidade: str = "pessoal ocupado assalariado (número de pessoas)"
    grupo_comparacao_principal: str = "never_treated_pool_estrutural_4964"
    not_yet_treated_no_principal: bool = False
    periodo_total_inicio: int = 2007
    periodo_total_fim: int = 2019
    janela_principal_k_min: int = -2
    janela_principal_k_max: int = 2
    janela_sensibilidade_k_min: int = -3
    janela_sensibilidade_k_max: int = 2
    k_referencia: int = -1
    # Duas dimensões distintas, nunca confundidas: o que os documentos
    # institucionais permitem afirmar (evidência) e o que a especificação
    # assume para poder identificar o efeito (suposição). Ausência de
    # evidência geral não é o mesmo que "zero antecipação comprovado" — é
    # a hipótese identificadora adotada na falta de uma regra geral.
    evidencia_institucional_antecipacao: str = "INSUFICIENTE_PARA_REGRA_GERAL"
    suposicao_antecipacao_principal_periodos: int = 0
    painel_balanceado_exigido: bool = True
    covariaveis_principal: tuple[str, ...] = field(default_factory=tuple)
    municipio_sigilo_excluido: str = CODIGO_MUNICIPIO_SIGILO_EXCLUIR
    transformacao_principal: str = "nivel"
    # Somente log1p: o pool de controles tem 3 zeros reais (zero_real/
    # zero_arredondado, D10) em 2007-2019; log() puro seria indefinido
    # para essas celulas. Ver notebook, secao de transformacao do outcome.
    transformacoes_sensibilidade: tuple[str, ...] = ("log1p",)


ESPECIFICACAO_CAUSAL_V1 = EspecificacaoCausal()


def unidades_tratadas_principal(painel: pd.DataFrame) -> pd.DataFrame:
    """Os 129 candidatos principais e sua coorte g — sem reinterpretar timing.

    `g` é lido diretamente de `ano_coorte_candidata`, o campo canônico já
    aprovado no cadastro causal (D11): para 128/129 é a proxy do Censo; para
    Cabo Frio (código 3300704) é `primeiro_ano_completo`, já igual a
    `ano_coorte_candidata` no cadastro. Nenhum recálculo é feito aqui.
    """
    tratados = painel.loc[painel["candidato_amostra_principal"] == True]  # noqa: E712
    return (
        tratados.groupby(CHAVE_MUNICIPIO, as_index=False)
        .agg(ano_coorte_candidata=("ano_coorte_candidata", "first"), origem_coorte=("origem_coorte", "first"))
    )


def unidades_controle_principal(painel: pd.DataFrame) -> pd.DataFrame:
    """Pool estrutural de 4.964 controles elegíveis, menos o único
    município com sigilo em 708/2012 (4.963 resultantes). Não faz matching,
    não filtra por outcome, não usa not-yet-treated.
    """
    pool = painel.loc[painel["fl_elegivel_controle_candidato"] == True]  # noqa: E712
    pool = pool.loc[pool[CHAVE_MUNICIPIO] != CODIGO_MUNICIPIO_SIGILO_EXCLUIR]
    return pool.groupby(CHAVE_MUNICIPIO, as_index=False).size().drop(columns="size")


def anos_excluidos_por_municipio(painel: pd.DataFrame) -> dict[str, list[int]]:
    """Reaproveita `anos_excluir_estimacao` do cadastro causal (formato
    ``"2009"`` ou ``"2009;2010"``), sem redefinir a regra. Para 128/129 é
    uma lista vazia; para Cabo Frio é ``[2009]``.
    """
    tratados = painel.loc[painel["candidato_amostra_principal"] == True]
    base = tratados.groupby(CHAVE_MUNICIPIO, as_index=False).agg(
        anos_excluir_estimacao=("anos_excluir_estimacao", "first")
    )
    resultado: dict[str, list[int]] = {}
    for row in base.itertuples(index=False):
        valor = row.anos_excluir_estimacao
        if valor is None or (isinstance(valor, float) and pd.isna(valor)) or valor == "":
            resultado[row.codigo_municipio_ibge] = []
        else:
            resultado[row.codigo_municipio_ibge] = [int(float(a)) for a in str(valor).split(";") if a]
    return resultado


def event_time(ano: int, coorte: int) -> int:
    """`k = t - g` — utilitário didático em memória, não persistido em
    nenhuma coluna de nenhum artefato."""
    return int(ano) - int(coorte)


def janela_principal_k(spec: EspecificacaoCausal = ESPECIFICACAO_CAUSAL_V1) -> range:
    return range(spec.janela_principal_k_min, spec.janela_principal_k_max + 1)


def janela_sensibilidade_k(spec: EspecificacaoCausal = ESPECIFICACAO_CAUSAL_V1) -> range:
    return range(spec.janela_sensibilidade_k_min, spec.janela_sensibilidade_k_max + 1)


def resumo_especificacao(spec: EspecificacaoCausal = ESPECIFICACAO_CAUSAL_V1) -> dict[str, Any]:
    """Resumo simples da especificação congelada, para exibição no notebook."""
    return {
        "outcome_principal": spec.outcome_principal,
        "grupo_comparacao_principal": spec.grupo_comparacao_principal,
        "not_yet_treated_no_principal": spec.not_yet_treated_no_principal,
        "periodo_total": f"{spec.periodo_total_inicio}-{spec.periodo_total_fim}",
        "janela_principal_k": list(janela_principal_k(spec)),
        "janela_sensibilidade_k": list(janela_sensibilidade_k(spec)),
        "k_referencia": spec.k_referencia,
        "evidencia_institucional_antecipacao": spec.evidencia_institucional_antecipacao,
        "suposicao_antecipacao_principal_periodos": spec.suposicao_antecipacao_principal_periodos,
        "painel_balanceado_exigido": spec.painel_balanceado_exigido,
        "covariaveis_principal": list(spec.covariaveis_principal),
        "municipio_sigilo_excluido": spec.municipio_sigilo_excluido,
        "transformacao_principal": spec.transformacao_principal,
        "transformacoes_sensibilidade": list(spec.transformacoes_sensibilidade),
    }
