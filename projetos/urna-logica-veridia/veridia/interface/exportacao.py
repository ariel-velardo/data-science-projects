"""Exportação do relatório da Auditoria Final (JSON e HTML imprimível).

Recebe o dicionário de ``fase5_auditoria.relatorio_para_dict`` — nenhum dado
é recalculado aqui. O HTML é autocontido (CSS embutido, sem fontes ou
scripts externos) e pode ser salvo em PDF pela opção "Imprimir" do navegador.
"""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from typing import Any

NOMES_VERIFICACAO = {
    "ordenacao_registros": "Ordenação dos registros (Fase 1)",
    "custodia": "Cadeia de custódia (Fase 2)",
    "trilha": "Trilha no mapa (Fase 3)",
    "evidencias_necessarias": "Evidências necessárias",
    "estado_final": "Estado final pelas regras",
    "cofre": "Cofre de estados (Fase 4)",
    "selos": "Selos das fases 1 a 4",
}


def relatorio_json(relatorio: dict[str, Any]) -> str:
    return json.dumps(relatorio, ensure_ascii=False, indent=2)


def relatorio_html(relatorio: dict[str, Any], gerado_em: datetime | None = None) -> str:
    gerado_em = gerado_em or datetime.now()
    consistente = bool(relatorio.get("consistente"))
    verificacoes = "".join(
        f'<tr><td class="{"ok" if v["ok"] else "erro"}">{"Aprovada" if v["ok"] else "Reprovada"}</td>'
        f'<td>{escape(NOMES_VERIFICACAO.get(v["nome"], v["nome"]))}</td><td>{escape(v["detalhe"])}</td></tr>'
        for v in relatorio.get("verificacoes", [])
    )
    evidencias = "".join(
        f'<tr><td>{escape(e["tipo"])}</td><td>{escape(e["id"])}</td><td>{escape(e["descricao"])}</td></tr>'
        for e in relatorio.get("evidencias_ordenadas", [])
    )
    metricas_ord = relatorio.get("metricas_ordenacao", {})
    linhas_resumo = [
        ("Selos obtidos (antes da auditoria)", ", ".join(map(str, relatorio.get("selos", []))) or "nenhum"),
        ("Algoritmo de busca", relatorio.get("algoritmo_busca", "")),
        ("Algoritmo de ordenação", relatorio.get("algoritmo_ordenacao", "")),
        ("Origem da trilha", relatorio.get("origem_trilha", "")),
        ("Caminho", " > ".join(relatorio.get("caminho", [])) or "nenhum"),
        ("Movimentos", relatorio.get("movimentos", 0)),
        ("Energia consumida", relatorio.get("energia_consumida", 0)),
        ("Estados explorados pelo solver", relatorio.get("estados_explorados", 0)),
        ("Tempo da busca (ms)", f'{relatorio.get("tempo_busca_segundos", 0) * 1000:.2f}'),
        ("Tempo total da auditoria (ms)", f'{relatorio.get("tempo_total_segundos", 0) * 1000:.2f}'),
        ("Registros conferidos", relatorio.get("registros_conferidos", 0)),
        (
            "Ordenação: comparações / movimentações",
            f'{metricas_ord.get("comparacoes", 0)} / {metricas_ord.get("movimentacoes", 0)}',
        ),
        ("Cadeia de custódia", " > ".join(relatorio.get("custodia", [])) or "vazia"),
    ]
    resumo = "".join(f"<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>" for k, v in linhas_resumo)
    inconsistencias = relatorio.get("inconsistencias", [])
    lista_inc = (
        "<ul>" + "".join(f"<li>{escape(i)}</li>" for i in inconsistencias) + "</ul>"
        if inconsistencias
        else "<p>Nenhuma inconsistência encontrada.</p>"
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Relatório da Auditoria Final — Verídia</title>
<style>
  body {{ font-family: "Segoe UI", system-ui, Arial, sans-serif; color: #14202c; margin: 32px; max-width: 900px; }}
  h1 {{ font-size: 1.6rem; margin: 0 0 4px; }}
  h2 {{ font-size: 1.1rem; margin: 28px 0 8px; border-bottom: 1px solid #ccd6df; padding-bottom: 4px; }}
  .selo {{ display: inline-block; padding: 4px 12px; border-radius: 999px; font-weight: 700;
          background: {"#d7f3ee" if consistente else "#fbe0e2"}; color: {"#0d6b5d" if consistente else "#9b2830"}; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.92rem; }}
  th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #e3e9ee; vertical-align: top; }}
  th {{ width: 38%; color: #44566a; font-weight: 600; }}
  td.ok {{ color: #0d6b5d; font-weight: 700; }} td.erro {{ color: #9b2830; font-weight: 700; }}
  .rodape {{ margin-top: 32px; color: #6a7c8e; font-size: 0.82rem; }}
  @media print {{ body {{ margin: 12mm; }} }}
</style></head><body>
<h1>Relatório da Auditoria Final — Verídia</h1>
<p><span class="selo">{"Auditoria consistente" if consistente else "Auditoria inconsistente"}</span></p>
<h2>Resumo</h2><table>{resumo}</table>
<h2>Verificações</h2><table>{verificacoes}</table>
<h2>Inconsistências</h2>{lista_inc}
<h2>Evidências coletadas (ordenadas por tipo e id com {escape(str(relatorio.get("algoritmo_ordenacao", "")))})</h2>
<table>{evidencias or '<tr><td>Nenhuma evidência.</td></tr>'}</table>
<p class="rodape">Gerado em {gerado_em.strftime("%d/%m/%Y %H:%M")} pelo VERÍDIA — O Enigma da Urna.
Eleição e dados inteiramente fictícios.</p>
</body></html>"""
