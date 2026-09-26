"""Gera o notebook didatico e reproduzivel da Fase 1."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from src.apresentacao_pt import preparar_notebook


def criar_notebook(destino: Path) -> None:
    nb = nbf.v4.new_notebook()
    nb["metadata"]["kernelspec"] = {
        "display_name": "Python (SINASC Fase 1)",
        "language": "python",
        "name": "sinasc-fase1",
    }
    nb["metadata"]["language_info"] = {"name": "python", "version": "3.11"}
    c = []
    c.append(
        nbf.v4.new_markdown_cell(
            """# Fase 1 — amostra, desenho e overlap

## 1. Objetivo

Definir a população analítica candidata, formalizar o contrato causal mínimo, auditar covariáveis pré-tratamento e avaliar comparabilidade. **Nenhum efeito causal é estimado neste notebook.**

Pergunta de trabalho: entre gestantes comparáveis em características observáveis, iniciar o pré-natal até o terceiro mês está associado a menor risco de baixo peso ao nascer?
"""
        )
    )
    c.append(
        nbf.v4.new_markdown_cell(
            """## 2. Estado herdado da Fase 0

- Fonte: SINASC 2024 oficial.
- Unidade: um registro por nascido vivo.
- Base: 2.389.325 registros e 62 colunas.
- Chave técnica candidata: `contador`.
- Gate anterior: `VIÁVEL_COM_RESSALVAS`.
"""
        )
    )
    c.append(
        nbf.v4.new_code_cell(
            """from pathlib import Path
import json
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from IPython.display import Markdown, display

raiz = next(
    candidato for candidato in (Path.cwd(), Path.cwd().parent)
    if (candidato / "src").is_dir() and (candidato / "data").is_dir()
).resolve()
sys.path.insert(0, str(raiz))

from src.executa_fase1 import executar_fase1
from src.visualizacao_ipt import CORES_IPT, aplicar_tema_ipt, configurar_plotly

configurar_plotly()
pio.renderers.default = "png"
# Recalcular com: python -m src.executa_fase1 (na .venv deste projeto).
# As tabelas abaixo leem os resultados integrais persistidos dessa execução.
amostra = json.loads((raiz / "outputs/diagnostics/fase1_amostra.json").read_text(encoding="utf-8"))
overlap = json.loads((raiz / "outputs/diagnostics/fase1_overlap.json").read_text(encoding="utf-8"))
print("Raiz:", raiz)
print("Status do overlap:", overlap["status"])
print("Efeito causal estimado: NÃO")

def salvar_figura(figura, nome, largura=1100, altura=650):
    caminho = (raiz / "outputs" / "figures" / nome).with_suffix(".html")
    figura.update_layout(width=largura, height=altura)
    figura.update_yaxes(automargin=True)
    figura.write_html(caminho, include_plotlyjs="cdn")
    figura.write_image(caminho.with_suffix('.png'))
    print("Figura interativa salva:", caminho)
"""
        )
    )
    c.append(
        nbf.v4.new_markdown_cell(
            """## 3. Evidência documental nova

O *Manual de Instruções para Preenchimento da Declaração de Nascido Vivo*, 4ª edição (Ministério da Saúde, 2022), confirma:

- `MESPRENAT`: mês de início do pré-natal;
- código `99`: ignorado;
- `CONSPRENAT`: número de consultas; `0` representa nenhuma consulta;
- `GRAVIDEZ`: 1 única, 2 dupla, 3 tripla ou mais, 9 ignorada.

Assim, `MESPRENAT=99` e missing não são convertidos em controle. Registros com `CONSPRENAT=0` ficam descritos separadamente devido a inconsistências possíveis com o mês informado.
"""
        )
    )
    c.append(nbf.v4.new_markdown_cell("## 4. Definição candidata de T"))
    c.append(
        nbf.v4.new_code_cell(
            """tratamento = pd.DataFrame(amostra["tratamento"])
display(tratamento)
fig_t = px.bar(
    tratamento, x="categoria_mesprenat", y="n",
    labels={"categoria_mesprenat": "Categoria", "n": "Registros"},
    text_auto=".3s",
)
fig_t.update_traces(marker_color=CORES_IPT["AZUL_PRINCIPAL"])
aplicar_tema_ipt(fig_t, "Elegibilidade de MESPRENAT")
fig_t.show()
salvar_figura(fig_t, "fase1_tratamento.png")
"""
        )
    )
    c.append(
        nbf.v4.new_markdown_cell(
            """Regra reproduzível: `T=1` para meses 1–3; `T=0` para meses 4–9; demais códigos são inelegíveis. Ausência de informação não é ausência de pré-natal.

## 5. Qualidade de Y

O desfecho é peso ao nascer abaixo de 2.500 g. A regra principal P1 restringe pesos a 500–6.000 g; P0, todo peso numérico positivo, permanece como sensibilidade.
"""
        )
    )
    c.append(
        nbf.v4.new_code_cell(
            """peso = pd.DataFrame(amostra["outcome_peso"])
display(peso)
dist_peso = pd.read_csv(raiz / "outputs/tables/distribuicao_peso_250g.csv")
fig_peso = px.bar(
    dist_peso, x="inicio_faixa_g", y="n",
    labels={"inicio_faixa_g": "Início da faixa (g)", "n": "Registros"},
)
fig_peso.update_traces(marker_color=CORES_IPT["CIANO"])
fig_peso.add_vline(x=2500, line_dash="dash", line_color=CORES_IPT["AZUL_ESCURO"])
aplicar_tema_ipt(fig_peso, "Distribuição de peso ao nascer em faixas de 250 g")
fig_peso.show()
salvar_figura(fig_peso, "fase1_peso.png")
"""
        )
    )
    c.append(nbf.v4.new_markdown_cell("## 6. Gestação única versus múltipla"))
    c.append(
        nbf.v4.new_code_cell(
            """gravidez = pd.DataFrame(amostra["gravidez"])
display(gravidez)
fig_g = go.Figure()
fig_g.add_bar(x=gravidez["tipo_gravidez"], y=gravidez["baixo_peso_pct"], name="Baixo peso (%)")
fig_g.add_bar(x=gravidez["tipo_gravidez"], y=gravidez["t1_pct"], name="T=1 (%)")
fig_g.update_layout(barmode="group")
aplicar_tema_ipt(fig_g, "Baixo peso e tratamento por tipo de gravidez")
fig_g.show()
salvar_figura(fig_g, "fase1_gravidez.png")
"""
        )
    )
    c.append(
        nbf.v4.new_markdown_cell(
            """Gestações múltiplas têm risco de baixo peso radicalmente distinto e uma gravidez pode gerar mais de um registro. A amostra principal fica restrita a gestação única; todas as gestações válidas permanecem como sensibilidade.

## 7. Covariáveis e temporalidade

Conjunto principal parcimonioso:

1. idade materna;
2. escolaridade materna;
3. raça/cor materna;
4. situação conjugal;
5. paridade;
6. histórico de perdas fetais;
7. UF de residência.

`IDADEPAI` e `SERIESCMAE` ficam fora por missing elevado. `CODOCUPMAE` permanece duvidosa devido à temporalidade/qualidade. Variáveis gestacionais, do parto e neonatais são proibidas no propensity principal.

## 8. DAG

O DAG de trabalho está em `docs/methodology/DAG_INICIAL.md`. Ele separa causas prévias de mediadores gestacionais e impede ajuste pós-tratamento.
"""
        )
    )
    c.append(nbf.v4.new_markdown_cell("## 9. Missing no conjunto X"))
    c.append(
        nbf.v4.new_code_cell(
            """missing = pd.DataFrame(amostra["missing_x_principal"])
display(missing[["variavel", "n_missing", "pct_total", "pct_t1", "pct_t0", "pct_y1", "pct_y0"]])
fig_m = px.bar(
    missing.sort_values("pct_total"), x="pct_total", y="variavel", orientation="h",
    labels={"pct_total": "Missing/ignorado (%)", "variavel": "Variável"},
)
fig_m.update_traces(marker_color=CORES_IPT["AZUL_MEDIO"])
aplicar_tema_ipt(fig_m, "Missing e códigos ignorados no X principal")
fig_m.update_yaxes(automargin=True)
fig_m.show()
salvar_figura(fig_m, "fase1_missing_x.png")
"""
        )
    )
    c.append(
        nbf.v4.new_markdown_cell(
            """Estratégia: categorias explícitas `IGNORADO` para X categóricas; mediana mais indicador de missing para idade no pipeline. Não há MICE nem exclusão complete-case.

## 10. Fluxo da amostra
"""
        )
    )
    c.append(
        nbf.v4.new_code_cell(
            """fluxo = pd.DataFrame(amostra["fluxo_amostra"])
display(fluxo)
fig_f = px.bar(
    fluxo, x="etapa", y="n_restante", text_auto=".4s",
    labels={"etapa": "Etapa", "n_restante": "N restante"},
)
fig_f.update_traces(marker_color=CORES_IPT["AZUL_PRINCIPAL"])
fig_f.update_yaxes(rangemode="tozero")
aplicar_tema_ipt(fig_f, "Fluxo da amostra analítica candidata")
fig_f.show()
salvar_figura(fig_f, "fase1_fluxo_amostra.png")
"""
        )
    )
    c.append(nbf.v4.new_markdown_cell("## 11. Perfil T=1 versus T=0"))
    c.append(
        nbf.v4.new_code_cell(
            """perfil_t = pd.DataFrame(amostra["perfil_tratamento_amostra_principal"])
display(perfil_t)
"""
        )
    )
    c.append(
        nbf.v4.new_markdown_cell(
            """A prevalência bruta de baixo peso nesta tabela é somente descritiva. Ela não é efeito causal nem será usada para selecionar o propensity.

## 12. SMD antes de qualquer ajuste
"""
        )
    )
    c.append(
        nbf.v4.new_code_cell(
            """balanceamento = pd.DataFrame(amostra["balanceamento_bruto"])
display(balanceamento)
fig_smd = px.bar(
    balanceamento.sort_values("smd_abs"), x="smd_abs", y="variavel", orientation="h",
    labels={"smd_abs": "|SMD|", "variavel": "Variável"},
)
fig_smd.update_traces(marker_color=CORES_IPT["CIANO"])
fig_smd.add_vline(x=0.1, line_dash="dash", line_color=CORES_IPT["AZUL_ESCURO"])
aplicar_tema_ipt(fig_smd, "Desequilíbrio bruto entre T=1 e T=0")
fig_smd.update_layout(margin=dict(l=210, r=40, t=80, b=80))
fig_smd.update_yaxes(automargin=True)
fig_smd.show()
salvar_figura(fig_smd, "fase1_smd_bruto.png")
"""
        )
    )
    c.append(
        nbf.v4.new_markdown_cell(
            """O SMD é o diagnóstico central; p-valores não são usados. Para categóricas, reporta-se o nível com maior SMD absoluto.

## 13. Propensity score diagnóstico

Modelo planejado: regressão logística L2, one-hot sparse, imputação simples explícita e 5 folds estratificados out-of-fold. O pipeline recebe apenas X pré-tratamento e possui guarda programática contra leakage. AUC, quando disponível, descreve separação de T; AUC alta não implica melhor validade causal.
"""
        )
    )
    c.append(
        nbf.v4.new_code_cell(
            """display(Markdown(f"**Status do propensity:** `{overlap['status']}`"))
if overlap["status"] == "CONCLUIDO":
    display(pd.DataFrame(overlap["trimming_diagnostico"]))
    print("Métricas:", overlap["metodo"])
else:
    print(overlap.get("erro", overlap.get("motivo")))
    print("Pendências:", overlap.get("diagnosticos_pendentes", []))
"""
        )
    )
    c.append(nbf.v4.new_markdown_cell("## 14. Overlap"))
    c.append(
        nbf.v4.new_code_cell(
            """hist_path = raiz / "outputs/tables/histograma_propensity.csv"
if overlap["status"] == "CONCLUIDO" and hist_path.exists():
    hist = pd.read_csv(hist_path)
    hist["centro"] = (hist["limite_inferior"] + hist["limite_superior"]) / 2
    hist["proporcao"] = hist["n"] / hist.groupby("grupo")["n"].transform("sum")
    fig_o = px.line(hist, x="centro", y="proporcao", color="grupo",
                    labels={"centro": "Propensity score", "proporcao": "Proporção dentro de cada grupo"})
    aplicar_tema_ipt(fig_o, "Distribuição out-of-fold do propensity por grupo")
    fig_o.show()
    salvar_figura(fig_o, "fase1_overlap_propensity.png")
else:
    display(Markdown("O overlap por propensity não pode ser interpretado até a dependência declarada ser instalada e o pipeline OOF ser executado."))
"""
        )
    )
    c.append(nbf.v4.new_markdown_cell("## 15. Positividade por perfis"))
    c.append(
        nbf.v4.new_code_cell(
            """positividade = pd.DataFrame(amostra["positividade_perfis"])
display(positividade)
fig_pos = px.scatter(
    positividade, x="proporcao_t1", y="perfil", size="n", color="perfil",
    hover_data=["categoria", "n_t1", "n_t0"],
    labels={"proporcao_t1": "Proporção T=1", "perfil": "Dimensão"},
)
fig_pos.add_vline(x=0.01, line_dash="dash", line_color=CORES_IPT["AZUL_ESCURO"])
fig_pos.add_vline(x=0.99, line_dash="dash", line_color=CORES_IPT["AZUL_ESCURO"])
aplicar_tema_ipt(fig_pos, "Positividade marginal em perfis pré-especificados")
fig_pos.show()
salvar_figura(fig_pos, "fase1_positividade_perfis.png")
"""
        )
    )
    c.append(
        nbf.v4.new_markdown_cell(
            """As margens simples não substituem o suporte multivariado do propensity. Elas apenas procuram bolsões óbvios de tratamento quase determinístico.

## 16. Sensibilidades de elegibilidade

- Peso: P1 (500–6.000 g) principal; P0 (>0 g) sensibilidade.
- Gravidez: única principal; todas as gestações válidas como sensibilidade.
- Ausência de pré-natal: `CONSPRENAT=0` descrito separadamente; não incorporado automaticamente a T=0.
- Trimming: 0,01–0,99 e 0,05–0,95 serão apenas diagnósticos, nunca regras automáticas nesta fase.

## 17. Gate da Fase 1
"""
        )
    )
    c.append(
        nbf.v4.new_code_cell(
            """if overlap["status"] == "CONCLUIDO":
    gate = "PRONTO_COM_RESSALVAS"
    justificativa = "Amostra e contrato são coerentes; overlap foi quantificado, mas confundimento não observado permanece uma hipótese forte."
else:
    gate = "NAO_PRONTO"
    justificativa = "A amostra está definida, porém o diagnóstico multivariado de overlap ainda não foi executado."
display(Markdown(f"### {gate}\\n\\n{justificativa}\\n\\n**EFEITO_CAUSAL_ESTIMADO = NÃO**"))
"""
        )
    )
    nb["cells"] = c
    destino.parent.mkdir(parents=True, exist_ok=True)
    preparar_notebook(nb)
    nbf.write(nb, destino)


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]
    caminho = raiz / "notebooks" / "02_amostra_desenho_e_overlap.ipynb"
    criar_notebook(caminho)
    print(caminho)
