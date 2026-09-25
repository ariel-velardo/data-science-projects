"""Infraestrutura segura para uma futura estimação DiD escalonada (D19).

O módulo audita backends, materializa o contrato e prepara/valida a amostra
real em modo dry-run. Não implementa Callaway–Sant'Anna de forma caseira e
não contém função que ajuste esse estimador na amostra real.

A única estimação disponível aqui é TWFE convencional, protegida para aceitar
exclusivamente painéis marcados como sintéticos da D19.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from simula_did_escalonado import ROTULO_FONTE_SINTETICA


PAPEL_TRATADO = "TRATADO_PRINCIPAL"
PAPEL_CONTROLE = "CONTROLE_NEVER_TREATED"
OUTCOME_PRIMARIO = "pessoal_ocupado_assalariado"
PERIODO = tuple(range(2007, 2020))
COORTES = (2009, 2010, 2011, 2012, 2013)
HASH_D15_ESPERADO = "7c24c01b569ed6d10f773d00599b5010e1607696f46d716827182a078e4d733b"
ROTULO_DRY_RUN_REAL = "AMOSTRA_REAL_D15_DRY_RUN_NAO_ESTIMAR"


def _versao_python(nome_distribuicao: str) -> str | None:
    try:
        return importlib.metadata.version(nome_distribuicao)
    except importlib.metadata.PackageNotFoundError:
        return None


def _versao_r_did() -> str | None:
    rscript = shutil.which("Rscript") or shutil.which("Rscript.exe")
    if rscript is None:
        return None
    comando = [
        rscript,
        "-e",
        "if (requireNamespace('did', quietly=TRUE)) cat(as.character(packageVersion('did'))) else quit(status=2)",
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True, check=False)
    if resultado.returncode != 0:
        return None
    return resultado.stdout.strip() or None


def auditar_backends() -> pd.DataFrame:
    """Inventaria backends locais sem instalar pacotes nem acessar rede."""
    versao_did = _versao_r_did()
    versao_differences = _versao_python("differences")
    versao_statsmodels = _versao_python("statsmodels")
    linhas = [
        {
            "backend": "did",
            "linguagem": "R",
            "versao": versao_did or "AUSENTE__REFERENCIA_DOCUMENTAL_2.5.1",
            "disponivel_no_ambiente": versao_did is not None,
            "suporta_group_time_ATT": "SIM",
            "suporta_never_treated": "SIM",
            "suporta_anticipation": "SIM",
            "suporta_event_study": "SIM__aggte_dynamic",
            "suporta_covariaveis": "SIM",
            "suporta_inferencia_cluster": "SIM",
            "observacao": (
                "Implementação canônica dos autores; att_gt/aggte. "
                "R/Rscript e pacote did não estão disponíveis neste ambiente."
            ),
        },
        {
            "backend": "differences",
            "linguagem": "Python",
            "versao": versao_differences or "AUSENTE__REFERENCIA_DOCUMENTAL_0.3.0",
            "disponivel_no_ambiente": versao_differences is not None,
            "suporta_group_time_ATT": "SIM",
            "suporta_never_treated": "SIM",
            "suporta_anticipation": "NAO_VALIDADO_LOCALMENTE",
            "suporta_event_study": "SIM__aggregate_event",
            "suporta_covariaveis": "SIM",
            "suporta_inferencia_cluster": "NAO_VALIDADO_LOCALMENTE",
            "observacao": (
                "ATTgt declara compatibilidade com Callaway–Sant'Anna, mas o pacote "
                "não está instalado e sua semântica completa não foi validada localmente."
            ),
        },
        {
            "backend": "statsmodels",
            "linguagem": "Python",
            "versao": versao_statsmodels or "AUSENTE",
            "disponivel_no_ambiente": versao_statsmodels is not None,
            "suporta_group_time_ATT": "NAO",
            "suporta_never_treated": "NAO_COMO_CS",
            "suporta_anticipation": "NAO_COMO_CS",
            "suporta_event_study": "NAO_COMO_CS",
            "suporta_covariaveis": "SIM",
            "suporta_inferencia_cluster": "SIM__REGRESSAO",
            "observacao": (
                "Disponível apenas para demonstração TWFE em dados sintéticos; "
                "não é backend Callaway–Sant'Anna."
            ),
        },
    ]
    return pd.DataFrame(linhas)


def selecionar_backend(auditoria: pd.DataFrame) -> dict[str, Any]:
    """Seleciona somente backend instalado e com group-time ATT declarado."""
    candidatos = auditoria.copy()
    suporte = candidatos["suporta_group_time_ATT"].isin([True, "SIM"])
    disponivel = candidatos["disponivel_no_ambiente"].astype(bool)
    elegiveis = candidatos.loc[suporte & disponivel]
    if elegiveis.empty:
        return {
            "gate": "BLOQUEADO_DEPENDENCIA",
            "backend_selecionado": None,
            "usar_aproximacao_caseira": False,
            "recomendacao": "Disponibilizar R + did==2.5.1 ou aprovar auditoria equivalente de differences==0.3.0.",
        }
    prioridade = {"did": 0, "differences": 1}
    escolhido = elegiveis.assign(
        prioridade=elegiveis["backend"].map(prioridade).fillna(99)
    ).sort_values("prioridade").iloc[0]
    return {
        "gate": "PENDENTE_VALIDACAO_SINTETICA",
        "backend_selecionado": escolhido["backend"],
        "usar_aproximacao_caseira": False,
        "recomendacao": "Executar cenários sintéticos antes de liberar a amostra real.",
    }


def contrato_estimador_d19() -> pd.DataFrame:
    """Contrato congelado da interface futura, sem executar estimação."""
    campos = [
        ("id", "codigo_municipio_ibge"),
        ("tempo", "ano"),
        ("grupo_coorte", "coorte_g; 0 no backend para never-treated"),
        ("controle", "never-treated"),
        ("outcome", OUTCOME_PRIMARIO),
        ("anticipation", "0"),
        ("periodo_estimacao", "2007-2019_INTEGRAL"),
        ("mascara", "elegivel_estimacao_principal"),
        ("tratados_populacao_principal", "129"),
        ("controles", "4963"),
        ("referencia_dinamica", "k=-1"),
        ("janela_reporte_principal", "k=-2,-1,0,+1,+2"),
        ("janela_sensibilidade", "k=-3,-2,-1,0,+1,+2; coortes 2010-2013"),
        ("painel_backend", "long; panel=TRUE; não truncar pela janela de reporte"),
        ("covariaveis_principal", "nenhuma; xformla=~1"),
    ]
    resultado = pd.DataFrame(campos, columns=["campo", "valor"])
    resultado["status"] = "CONTRATO_D19_SEM_ESTIMACAO_REAL"
    return resultado


def mapeamento_backend_did_r() -> pd.DataFrame:
    """Mapeia o contrato para a API oficial planejada do pacote R ``did``."""
    linhas = [
        ("unidade", "idname", "codigo_municipio_ibge", "chave municipal congelada"),
        ("período", "tname", "ano", "painel anual 2007-2019"),
        ("first treatment", "gname", "g_backend", "coorte; zero para never-treated"),
        ("outcome", "yname", OUTCOME_PRIMARIO, "outcome primário D14"),
        ("painel", "panel", "TRUE", "município-ano longitudinal"),
        ("painel balanceado", "allow_unbalanced_panel", "FALSE", "contrato principal; máscara Cabo Frio deve ser tratada explicitamente"),
        ("controle", "control_group", "nevertreated", "grupo principal congelado"),
        ("antecipação", "anticipation", "0", "hipótese identificadora congelada"),
        ("covariáveis", "xformla", "~1", "principal incondicional"),
        ("método", "est_method", "dr", "default oficial; intercepto apenas no principal"),
        ("período-base", "base_period", "universal", "normaliza g-1 a zero no reporte dinâmico"),
        ("ATT(g,t)", "att_gt", "objeto MP", "células grupo-tempo"),
        ("agregação dinâmica", "aggte(type)", "dynamic", "efeitos por event-time"),
        ("agregação por grupo", "aggte(type)", "group", "efeitos por coorte"),
        ("agregação global", "aggte(type)", "simple", "resumo global com ressalva de ponderação"),
        ("bootstrap", "bstrap", "TRUE", "multiplier bootstrap"),
        ("bandas simultâneas", "cband", "TRUE", "inferência conjunta"),
        ("iterações", "biters", "1000_MÍNIMO_A_CONFIRMAR_D20", "não reduzir por conveniência"),
        ("cluster", "clustervars", "codigo_municipio_ibge", "cluster na unidade do painel"),
        ("nível", "alp", "0.05", "bandas de 95%"),
        ("influence function", "compute_inffunc", "TRUE", "necessária para inferência e aggte"),
    ]
    return pd.DataFrame(
        linhas,
        columns=["conceito_artigo", "parametro_backend", "valor_projeto", "justificativa"],
    )


def preparar_dados_estimador(amostra: pd.DataFrame) -> pd.DataFrame:
    """Prepara colunas do backend em dry-run, sem ajustar qualquer modelo."""
    obrigatorias = {
        "codigo_municipio_ibge",
        "ano",
        "coorte_g",
        "papel_causal",
        "elegivel_estimacao_principal",
        "tempo_relativo",
        OUTCOME_PRIMARIO,
    }
    faltantes = obrigatorias - set(amostra.columns)
    if faltantes:
        raise ValueError(f"amostra D15 sem colunas obrigatórias: {sorted(faltantes)}")
    dados = amostra.copy(deep=True)
    dados["id_backend"] = dados["codigo_municipio_ibge"].astype("string").str.zfill(7)
    dados["t_backend"] = pd.to_numeric(dados["ano"], errors="raise").astype(int)
    dados["g_backend"] = pd.to_numeric(dados["coorte_g"], errors="coerce").fillna(0).astype(int)
    dados["y_backend"] = pd.to_numeric(dados[OUTCOME_PRIMARIO], errors="raise")
    dados["controle_never_treated"] = dados["papel_causal"].eq(PAPEL_CONTROLE)
    dados["tratado_no_periodo"] = (
        dados["g_backend"].gt(0) & dados["t_backend"].ge(dados["g_backend"])
    ).astype(int)
    event_time = pd.Series(pd.NA, index=dados.index, dtype="Int64")
    mask_tratado = dados["g_backend"].gt(0)
    event_time.loc[mask_tratado] = (
        dados.loc[mask_tratado, "t_backend"] - dados.loc[mask_tratado, "g_backend"]
    ).astype(int)
    dados["event_time_backend"] = event_time
    dados["fonte_dados"] = ROTULO_DRY_RUN_REAL
    dados["modo_execucao"] = "PREPARAR_E_VALIDAR_SEM_FIT"
    return dados


def validar_dados_estimador(dados: pd.DataFrame) -> dict[str, Any]:
    """Valida a estrutura preparada e falha diante de divergência do contrato."""
    obrigatorias = {
        "id_backend",
        "t_backend",
        "g_backend",
        "y_backend",
        "papel_causal",
        "elegivel_estimacao_principal",
        "event_time_backend",
        "fonte_dados",
    }
    faltantes = obrigatorias - set(dados.columns)
    if faltantes:
        raise ValueError(f"dados preparados sem colunas: {sorted(faltantes)}")
    if not dados["fonte_dados"].eq(ROTULO_DRY_RUN_REAL).all():
        raise ValueError("dry-run real recebeu fonte incompatível")
    if dados.duplicated(["id_backend", "t_backend"]).any():
        raise ValueError("chave município-ano duplicada")
    if set(dados["t_backend"].unique()) != set(PERIODO):
        raise ValueError("período diverge de 2007-2019")
    if dados["y_backend"].isna().any():
        raise ValueError("outcome real contém nulos")
    por_unidade = dados.sort_values("t_backend").drop_duplicates("id_backend")
    if not set(por_unidade["papel_causal"]).issubset({PAPEL_TRATADO, PAPEL_CONTROLE}):
        raise ValueError("papel causal fora do contrato")
    contagens_anos = dados.groupby("id_backend")["t_backend"].nunique()
    if not contagens_anos.eq(len(PERIODO)).all():
        raise ValueError("painel-base não está balanceado em 13 anos")
    tratados = por_unidade.loc[por_unidade["papel_causal"].eq(PAPEL_TRATADO)]
    controles = por_unidade.loc[por_unidade["papel_causal"].eq(PAPEL_CONTROLE)]
    contagem_coortes = {
        int(chave): int(valor)
        for chave, valor in tratados.groupby("g_backend").size().sort_index().items()
    }
    if contagem_coortes != {2009: 21, 2010: 27, 2011: 66, 2012: 13, 2013: 2}:
        raise ValueError(f"coortes divergentes: {contagem_coortes}")
    if dados["id_backend"].eq("5003900").any():
        raise ValueError("município 5003900 deveria estar integralmente ausente")
    cabo = dados.loc[dados["id_backend"].eq("3300704")]
    anos_inelegiveis = cabo.loc[~cabo["elegivel_estimacao_principal"].astype(bool), "t_backend"].tolist()
    if anos_inelegiveis != [2009]:
        raise ValueError(f"máscara Cabo Frio divergente: {anos_inelegiveis}")
    mask_tratado = dados["g_backend"].gt(0)
    event_time_esperado = dados.loc[mask_tratado, "t_backend"] - dados.loc[mask_tratado, "g_backend"]
    if not (
        dados.loc[mask_tratado, "event_time_backend"].astype(int).to_numpy()
        == event_time_esperado.to_numpy()
    ).all():
        raise ValueError("event-time incompatível com t-g")
    if dados.loc[~mask_tratado, "event_time_backend"].notna().any():
        raise ValueError("never-treated não deve possuir event-time")
    return {
        "n_linhas": int(len(dados)),
        "n_elegiveis": int(dados["elegivel_estimacao_principal"].astype(bool).sum()),
        "n_unidades": int(dados["id_backend"].nunique()),
        "n_tratados": int(len(tratados)),
        "n_controles": int(len(controles)),
        "contagem_coortes": contagem_coortes,
        "anos": [int(ano) for ano in sorted(dados["t_backend"].unique())],
        "painel_base_balanceado": True,
        "chave_unica": True,
        "anos_inelegiveis_cabo_frio": anos_inelegiveis,
        "codigo_5003900_ausente": True,
        "estimacao_executada": False,
        "rotulo": "DRY_RUN_ESTRUTURAL_AMOSTRA_REAL_SEM_ESTIMACAO",
    }


def resumo_coortes_para_reporte(dados: pd.DataFrame) -> pd.DataFrame:
    """Preserva todas as coortes e sinaliza precisão sem excluir unidades."""
    unidades = dados.loc[dados["g_backend"].gt(0)].drop_duplicates("id_backend")
    resultado = unidades.groupby("g_backend", as_index=False).agg(n_tratados=("id_backend", "nunique"))
    resultado = resultado.rename(columns={"g_backend": "coorte_g"})
    resultado["warning_precisao"] = np.where(
        resultado["n_tratados"].le(2), "COORTE_N2_PRECISAO_CRITICA", "SEM_WARNING_CRITICO_N2"
    )
    resultado["regra"] = "REPORTAR_SEM_EXCLUIR"
    return resultado


def estimar_twfe_sintetico(painel: pd.DataFrame) -> dict[str, float | int | str]:
    """Ajusta TWFE convencional exclusivamente para a demonstração sintética."""
    if "fonte_dados" not in painel or not painel["fonte_dados"].eq(ROTULO_FONTE_SINTETICA).all():
        raise ValueError("TWFE da D19 aceita somente dados sintéticos explicitamente marcados")
    obrigatorias = {"id", "ano", "y", "tratado_no_periodo"}
    faltantes = obrigatorias - set(painel.columns)
    if faltantes:
        raise ValueError(f"painel sintético sem colunas: {sorted(faltantes)}")
    dados = painel.copy()
    modelo = smf.ols("y ~ tratado_no_periodo + C(id) + C(ano)", data=dados)
    ajuste = modelo.fit(cov_type="cluster", cov_kwds={"groups": dados["id"]})
    return {
        "coeficiente_twfe": float(ajuste.params["tratado_no_periodo"]),
        "erro_padrao_cluster_id": float(ajuste.bse["tratado_no_periodo"]),
        "n_observacoes": int(ajuste.nobs),
        "rotulo": "TWFE_CONVENCIONAL_APENAS_DADOS_SINTETICOS",
        "interpretacao": "NAO_EQUIVALE_A_ATT_GT_CALLAWAY_SANTANNA",
    }


def sha256_arquivo(caminho: str | Path) -> str:
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def executar_dry_run_real(caminho_parquet: str | Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Lê, prepara e valida D15; nunca chama estimador."""
    caminho = Path(caminho_parquet)
    hash_antes = sha256_arquivo(caminho)
    amostra = pd.read_parquet(caminho)
    preparados = preparar_dados_estimador(amostra)
    validacao = validar_dados_estimador(preparados)
    hash_depois = sha256_arquivo(caminho)
    if hash_antes != hash_depois:
        raise AssertionError("parquet D15 foi alterado durante o dry-run")
    validacao["sha256_antes"] = hash_antes
    validacao["sha256_depois"] = hash_depois
    validacao["byte_identical"] = True
    return preparados, validacao


def plano_operacional_d20() -> pd.DataFrame:
    """Especificação operacional futura; nada desta tabela é executado na D19."""
    linhas = [
        ("backend", "R did", "2.5.1", "BLOQUEADO_DEPENDENCIA"),
        ("funcao_principal", "att_gt", "backend oficial", "NAO_EXECUTADO_D19"),
        ("idname", "codigo_municipio_ibge", "contrato D14-D19", "CONGELADO"),
        ("tname", "ano", "2007-2019 integral", "CONGELADO"),
        ("gname", "g_backend", "0 para never-treated", "CONGELADO"),
        ("yname", OUTCOME_PRIMARIO, "nível", "CONGELADO"),
        ("control_group", "nevertreated", "principal", "CONGELADO"),
        ("anticipation", "0", "hipótese identificadora", "CONGELADO"),
        ("base_period", "universal", "k=-1 normalizado", "RECOMENDADO_D19"),
        ("xformla", "~1", "principal incondicional", "CONGELADO"),
        ("est_method", "dr", "default oficial com intercepto", "RECOMENDADO_D19"),
        ("cluster", "codigo_municipio_ibge", "unidade do painel", "RECOMENDADO_D19"),
        ("bootstrap", "multiplier bootstrap", "bstrap=TRUE", "RECOMENDADO_D19"),
        ("bandas", "simultâneas", "cband=TRUE; alp=0.05", "RECOMENDADO_D19"),
        ("biters", "1000 mínimo", "confirmar orçamento computacional sem escolher por resultado", "RECOMENDADO_D19"),
        ("ATT(g,t)", "objeto MP", "células grupo-tempo", "PLANEJADO"),
        ("agregações", "dynamic; group; simple", "reportar perguntas distintas", "PLANEJADO"),
        ("janela_reporte", "k=-2...+2", "não truncar painel de estimação", "CONGELADO"),
        ("sensibilidades", "plano D18", "log1p; k=-3...+2; coortes; spillover; suporte", "PRE_ESPECIFICADO"),
        ("regra_de_execucao", "exige nova tarefa D20 e dependência aprovada", "sem execução automática", "BLOQUEADO_D19"),
    ]
    return pd.DataFrame(linhas, columns=["item", "valor", "justificativa", "status"])


def gates_d19(backend_gate: str) -> dict[str, str]:
    """Deriva gates sem converter ausência de backend em sucesso."""
    backend_validado = backend_gate == "VALIDADO"
    return {
        "D19_BACKEND_CALLAWAY_SANTANNA_VALIDADO": (
            "SIM" if backend_validado else "BLOQUEADO_DEPENDENCIA"
        ),
        "D19_DGP_SINTETICO_VALIDADO": "SIM",
        "D19_ATT_GT_SINTETICO_VALIDADO": "SIM" if backend_validado else "NAO",
        "D19_HETEROGENEIDADE_SINTETICA_VALIDADA": "SIM",
        "D19_EVENT_STUDY_SINTETICO_VALIDADO": "SIM" if backend_validado else "NAO",
        "D19_INFERENCIA_CONFIGURADA": "SIM" if backend_validado else "NAO",
        "D19_DRY_RUN_AMOSTRA_REAL_VALIDADO": "SIM",
        "D19_INFRAESTRUTURA_PRONTA_PARA_ESTIMACAO_REAL": "SIM" if backend_validado else "NAO",
        "D19_EFEITO_CAUSAL_REAL_ESTIMADO": "NAO",
        "DESENHO_CAUSAL_APROVADO": "NAO",
    }
