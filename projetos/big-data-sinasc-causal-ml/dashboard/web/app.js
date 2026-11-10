"use strict";
(function () {
  const D = JSON.parse(document.getElementById("dados-painel").textContent);
  const COR = { t1: "#0B63B0", t0: "#D9791F", verde: "#1F9D8F", cinza: "#6B7C8C", marinho: "#123C59", grade: "#E4ECF2", eixo: "#B7C8D5", tinta: "#16303F", suave: "#4E6577" };
  const NOME = { t1: "T=1 (meses 1–3)", t0: "T=0 (meses 4–6)" };
  const estado = {};

  const semZeroNegativo = (t) => (/^-0(,0+)?$/.test(t) ? t.slice(1) : t.replace("-", "−"));
  const br = (v, c) => (v === null || v === undefined ? "—" : typeof v === "string" ? v : semZeroNegativo(v.toLocaleString("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c })));
  const int = (v) => br(v, 0);
  const pp = (v) => (v < 0 ? "−" : "+") + br(Math.abs(v), 2);
  const esc = (t) => String(t).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const largura = () => window.innerWidth;
  const celular = () => largura() < 620;

  Plotly.register({
    moduleType: "locale",
    name: "pt-BR",
    dictionary: {
      "Download plot as a png": "Baixar imagem",
      "Download plot": "Baixar imagem",
      "Zoom": "Ampliar",
      "Pan": "Mover",
      "Zoom in": "Aproximar",
      "Zoom out": "Afastar",
      "Autoscale": "Escala automática",
      "Reset axes": "Restaurar eixos",
      "Double-click to zoom back out": "Clique duas vezes para restaurar",
      "Double-click on legend to isolate one trace": "Clique duas vezes na legenda para isolar uma série",
      "Click to enter Colorscale title": "Título da escala",
    },
    format: { decimal: ",", thousands: ".", grouping: [3], currency: ["R$ ", ""], days: ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"], shortDays: ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"], months: ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"], shortMonths: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], date: "%d/%m/%Y" },
  });

  function eixo(extra) {
    return Object.assign({ gridcolor: COR.grade, zerolinecolor: COR.eixo, linecolor: COR.eixo, tickfont: { size: 12, color: COR.suave }, title: { font: { size: 12, color: COR.suave } }, automargin: true, fixedrange: celular() }, extra);
  }

  function layout(extra) {
    const base = {
      font: { family: '"Segoe UI", -apple-system, Roboto, Arial, sans-serif', size: 13, color: COR.tinta },
      separators: ",.",
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      margin: { t: 34, r: 16, b: 44, l: 16 },
      hoverlabel: { bgcolor: "#FFFFFF", bordercolor: COR.eixo, font: { color: COR.tinta, size: 13 }, align: "left" },
      legend: { orientation: "h", x: 0, y: 1.14, yanchor: "bottom", traceorder: "normal", font: { size: 12 } },
      showlegend: true,
      bargap: 0.28,
      dragmode: celular() ? false : "zoom",
    };
    const saida = Object.assign(base, extra);
    saida.xaxis = eixo(extra.xaxis || {});
    saida.yaxis = eixo(extra.yaxis || {});
    return saida;
  }

  const linhaRef = (eixoRef, valor, cor, traco) =>
    eixoRef === "x"
      ? { type: "line", xref: "x", yref: "paper", x0: valor, x1: valor, y0: 0, y1: 1, line: { color: cor || COR.eixo, width: 1, dash: traco || "solid" } }
      : { type: "line", xref: "paper", yref: "y", x0: 0, x1: 1, y0: valor, y1: valor, line: { color: cor || COR.eixo, width: 1, dash: traco || "solid" } };

  const CONFIG = {
    responsive: true,
    displaylogo: false,
    locale: "pt-BR",
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
    toImageButtonOptions: { format: "png", scale: 2 },
  };

  const anosF = () => D.serie.filter((l) => l.ano >= estado.f_ini && l.ano <= estado.f_fim);
  const eixoAnos = (titulo) => ({ dtick: celular() ? 2 : 1, tickangle: 0, title: { text: titulo || "" }, tickformat: "d" });
  const ABREVIACOES = [["Idade materna (anos)", "Idade"], ["Idade materna²", "Idade²"], ["Idade materna (descritiva)", "Idade"], ["Idade materna (faixa) (descritiva)", "Idade"], ["Idade materna (faixa)", "Idade"], ["Escolaridade", "Esc."], ["Raça/cor", "Raça"], ["Perdas fetais anteriores", "Perdas"], ["Situação conjugal (não ajustada)", "Conj."], ["Situação conjugal", "Conj."], ["Paridade", "Par."]];
  const rotuloEixo = (t) => {
    if (!celular()) return t;
    const [variavel, nivel] = t.split(" — ");
    const curta = (ABREVIACOES.find(([longa]) => longa === variavel) || [variavel, variavel])[1];
    return curta + " " + (nivel || "").replace("Ignorado/ausente", "ignorado").replace("Separada/divorciada", "separada").replace("Superior", "Sup.").replace("Fundamental", "Fund.");
  };

  const capital = () => D.recortes.find((r) => r.id === "sp_capital");
  const ordemRecortes = () => D.recortes.slice().reverse();

  /* ---- Gráficos: cada função devolve { data, layout, altura? } ---- */
  const G = {
    a_difs() {
      const r = D.resultados;
      return forest([
        { nome: "Bruta", v: r.dif_bruta.valor, ic: r.dif_bruta.ic, cor: COR.cinza, simbolo: "circle-open" },
        { nome: "Ajustada (ATO)", v: r.dif_ato.valor, ic: r.dif_ato.ic, cor: COR.t1, simbolo: "circle" },
      ]);
    },

    b_indicador() {
      const m = estado.b_metrica;
      const texto = document.querySelector('[data-filtro="b_metrica"]').selectedOptions[0].text;
      const rs = ordemRecortes();
      const valores = rs.map((r) => r[m]);
      const min = Math.min(...valores), max = Math.max(...valores), folga = Math.max((max - min) * 0.25, 0.1);
      return {
        data: [{
          type: "scatter", mode: "markers+text", name: texto,
          x: valores, y: rs.map((r) => r.nome), text: valores.map((v) => br(v, 2) + "%"), textposition: "middle right", cliponaxis: false,
          marker: { size: 13, color: rs.map((r) => (r.id === "sp_capital" ? COR.t1 : COR.cinza)), line: { width: 2, color: "#fff" } },
          hovertemplate: "<b>%{y}</b><br>%{x:.2f}%<extra></extra>",
          hoverlabel: {},
        }],
        layout: layout({ showlegend: false, margin: { t: 10, r: 70, b: 44, l: 16 }, xaxis: { title: { text: texto }, range: [min - folga, max + folga * 1.6], ticksuffix: "%" }, yaxis: {} }),
      };
    },

    b_exclusoes() {
      const rs = ordemRecortes();
      const etapas = [
        ["qualidade", "Essenciais inválidas", COR.marinho],
        ["multipla", "Gestação múltipla", COR.t1],
        ["peso", "Peso fora da faixa", COR.verde],
        ["mes79", "Início nos meses 7–9", COR.t0],
      ];
      return {
        data: etapas.map(([k, nome, cor]) => ({
          type: "bar", orientation: "h", name: nome, x: rs.map((r) => r.excl[k].pct), y: rs.map((r) => r.nome),
          customdata: rs.map((r) => r.excl[k].n), marker: { color: cor, line: { color: "#fff", width: 1.5 } },
          hovertemplate: "<b>%{y}</b><br>" + nome + ": %{x:.2f}%<br>%{customdata:,.0f} registros<extra></extra>",
        })),
        layout: layout({ barmode: "stack", xaxis: { title: { text: "% dos nascimentos do recorte" }, ticksuffix: "%" }, yaxis: {}, legend: { orientation: "h", x: 0, y: 1.04, yanchor: "bottom", font: { size: 12 } }, margin: { t: 60, r: 12, b: 44, l: 16 } }),
      };
    },

    b_grupos() {
      const rs = ordemRecortes();
      return {
        data: ["t1", "t0"].map((g) => ({
          type: "bar", orientation: "h", name: NOME[g], x: rs.map((r) => r["n_" + g]), y: rs.map((r) => r.nome),
          marker: { color: COR[g], line: { color: "#fff", width: 1.5 } },
          hovertemplate: "<b>%{y}</b><br>" + NOME[g] + ": %{x:,.0f}<extra></extra>",
        })),
        layout: layout({ barmode: "stack", xaxis: { title: { text: "Nascimentos elegíveis" }, tickformat: ",d" }, yaxis: {}, legend: { orientation: "h", x: 0, y: 1.04, yanchor: "bottom", font: { size: 12 } }, margin: { t: 40, r: 12, b: 44, l: 16 } }),
      };
    },

    b_variaveis() {
      const m = estado.b_medida;
      const { nomes, registros } = D.qualidade_variaveis;
      const rs = D.recortes;
      const vars = D.qualidade_variaveis.ordem;
      const achar = (r, v) => registros.find((x) => x.recorte === r.id && x.variavel === v);
      const z = vars.map((v) => rs.map((r) => achar(r, v)[m]));
      const texto = vars.map((v) => rs.map((r) => br(achar(r, v)[m], 2)));
      const planos = z.flat();
      const invertido = m === "ausente";
      return {
        data: [{
          type: "heatmap", name: "", z, x: rs.map((r) => r.nome), y: vars.map((v) => nomes[v]), text: texto, texttemplate: "%{text}", textfont: { size: celular() ? 10 : 12 }, xgap: 2, ygap: 2,
          zmin: Math.min(...planos), zmax: Math.max(...planos),
          colorscale: invertido ? [[0, "#F2F7FB"], [1, "#D9791F"]] : [[0, "#F2F7FB"], [0.5, "#9CC6E8"], [1, "#0B63B0"]],
          showscale: false,
          customdata: vars.map((v) => rs.map((r) => achar(r, v).medida)),
          hovertemplate: "<b>%{y}</b><br>%{x}<br>%{text}%<br>Medida: %{customdata}<extra></extra>",
        }],
        layout: layout({ showlegend: false, margin: { t: 10, r: 8, b: 60, l: 16 }, xaxis: { side: "bottom", tickangle: celular() ? -35 : 0 }, yaxis: { autorange: "reversed" } }),
      };
    },

    b_mesprenat() {
      const m = D.qualidade_anual.mesprenat;
      const cores = { "SP — capital": [COR.t1, "solid", "circle"], "SP — estado": [COR.verde, "solid", "square"], "SP — restante": [COR.cinza, "dash", "diamond"] };
      return {
        data: Object.keys(m).map((k) => ({
          type: "scatter", mode: "lines+markers", name: k, x: m[k].map((l) => l.ano), y: m[k].map((l) => l.pct),
          customdata: m[k].map((l) => [l.n_validos, l.n_nascimentos]), line: { color: cores[k][0], width: 2, dash: cores[k][1] }, marker: { size: 8, symbol: cores[k][2] },
          hovertemplate: "<b>" + k + ", %{x}</b><br>%{y:.2f}% válidos<br>%{customdata[0]:,.0f} de %{customdata[1]:,.0f}<extra></extra>",
        })),
        layout: layout({ xaxis: eixoAnos(), yaxis: { ticksuffix: "%", title: { text: "% dos nascimentos" } } }),
      };
    },

    b_serie_grupos() {
      const g = estado.b_grupo, t = D.qualidade_anual.tamanhos;
      const cores = { "SP — capital": [COR.t1, "solid", "circle"], "SP — estado": [COR.verde, "solid", "square"], "SP — restante": [COR.cinza, "dash", "diamond"] };
      const anos = D.qualidade_anual.capital.map((l) => l.ano);
      return {
        data: Object.keys(t).map((k) => ({
          type: "scatter", mode: "lines+markers", name: k, x: anos, y: t[k][g], line: { color: cores[k][0], width: 2, dash: cores[k][1] }, marker: { size: 8, symbol: cores[k][2] },
          hovertemplate: "<b>" + k + ", %{x}</b><br>%{y:,.0f} nascimentos<extra></extra>",
        })),
        layout: layout({ xaxis: eixoAnos(), yaxis: { title: { text: "Nascimentos elegíveis" }, tickformat: ",d", rangemode: "tozero" } }),
      };
    },

    c_exclusoes() {
      const et = D.funil.etapas.slice().reverse();
      return {
        data: [{
          type: "bar", orientation: "h", name: "Excluídos", x: et.map((e) => e.n), y: et.map((e) => e.rotulo), text: et.map((e) => int(e.n)), textposition: "outside", cliponaxis: false,
          customdata: et.map((e) => e.pct), marker: { color: COR.marinho },
          hovertemplate: "<b>%{y}</b><br>%{x:,.0f} registros<br>%{customdata:.2f}% dos nascimentos<extra></extra>",
        }],
        layout: layout({ showlegend: false, margin: { t: 8, r: 56, b: 30, l: 16 }, xaxis: { tickformat: ",d", rangemode: "tozero" }, yaxis: {} }),
      };
    },

    c_meses() {
      const m = D.temporalidade.distribuicao_meses;
      return {
        data: [{
          type: "bar", name: "Elegíveis", x: m.map((l) => l.mes), y: m.map((l) => l.pct), text: m.map((l) => br(l.pct, 2) + "%"), textposition: "outside", cliponaxis: false,
          marker: { color: m.map((l, i) => (i < 3 ? COR.t1 : COR.t0)) },
          hovertemplate: "<b>%{x}</b><br>%{y:.2f}% dos elegíveis<extra></extra>",
        }],
        layout: layout({ showlegend: false, margin: { t: 22, r: 8, b: 30, l: 16 }, yaxis: { ticksuffix: "%", rangemode: "tozero" }, xaxis: {} }),
      };
    },

    c_perfil() {
      const niveis = D.perfil.variaveis[estado.c_variavel].slice().reverse();
      const series = [["pct_total", "Todos os elegíveis", COR.cinza], ["pct_t0", NOME.t0, COR.t0], ["pct_t1", NOME.t1, COR.t1]];
      return {
        altura: Math.max(280, niveis.length * 74 + 110),
        data: series.map(([k, nome, cor]) => ({
          type: "bar", orientation: "h", name: nome, x: niveis.map((n) => n[k]), y: niveis.map((n) => n.nivel), text: niveis.map((n) => br(n[k], 1) + "%"), textposition: "outside", cliponaxis: false,
          marker: { color: cor },
          hovertemplate: "<b>%{y}</b><br>" + nome + ": %{x:.1f}%<extra></extra>",
        })),
        layout: layout({ barmode: "group", bargap: 0.25, margin: { t: 40, r: 50, b: 40, l: 16 }, xaxis: { ticksuffix: "%", title: { text: "% do grupo" }, rangemode: "tozero" }, yaxis: {}, legend: { orientation: "h", x: 0, y: 1.02, yanchor: "bottom", traceorder: "reversed", font: { size: 12 } } }),
      };
    },

    d_love() {
      const b = estado.d_bloco;
      const linhas = D.balanco.ato.filter((l) => !b || l.variavel.startsWith(b)).slice();
      const seg = { x: [], y: [] };
      linhas.forEach((l) => { seg.x.push(Math.abs(l.smd_antes), Math.abs(l.smd_depois), null); seg.y.push(rotuloEixo(l.rotulo), rotuloEixo(l.rotulo), null); });
      const hover = linhas.map((l) => [l.papel, l.t1_bruto, l.t0_bruto, l.t1_ato, l.t0_ato, br(l.smd_antes, 3), br(l.smd_depois, 3)]);
      const modelo = "<b>%{y}</b><br>%{customdata[0]}<br>T=1: %{customdata[1]} bruto, %{customdata[3]} ATO<br>T=0: %{customdata[2]} bruto, %{customdata[4]} ATO<br>SMD antes: %{customdata[5]}<br>SMD depois: %{customdata[6]}<extra></extra>";
      return {
        altura: Math.max(300, linhas.length * 26 + 110),
        data: [
          { type: "scatter", mode: "lines", x: seg.x, y: seg.y, line: { color: COR.eixo, width: 1.5 }, hoverinfo: "skip", showlegend: false, meta: { semTabela: true } },
          { type: "scatter", mode: "markers", name: "Antes (sem ponderação)", x: linhas.map((l) => Math.abs(l.smd_antes)), y: linhas.map((l) => rotuloEixo(l.rotulo)), customdata: hover, hovertemplate: modelo, marker: { size: 9, symbol: "circle-open", color: COR.cinza, line: { width: 2 } } },
          { type: "scatter", mode: "markers", name: "Depois (pesos ATO)", x: linhas.map((l) => Math.abs(l.smd_depois)), y: linhas.map((l) => rotuloEixo(l.rotulo)), customdata: hover, hovertemplate: modelo, marker: { size: 9, color: COR.t1 } },
        ],
        layout: layout({ margin: { t: 36, r: 16, b: 44, l: 16 }, legend: { orientation: "h", x: 0, y: 1.005, yanchor: "bottom", font: { size: 12 } }, xaxis: { title: { text: "|SMD|" }, range: [-0.01, 0.5] }, yaxis: { autorange: "reversed", type: "category", categoryorder: "array", categoryarray: linhas.map((l) => rotuloEixo(l.rotulo)), tickfont: { size: celular() ? 10 : 12, color: COR.suave } }, shapes: [linhaRef("x", 0.1, COR.t0, "dot"), linhaRef("x", 0.2, COR.t0, "dot")] }),
      };
    },

    d_smd() {
      const b = estado.d_bloco;
      const linhas = D.balanco.diagnostico.filter((l) => !b || l.rotulo.startsWith(b)).slice().sort((p, q) => Math.abs(q.smd) - Math.abs(p.smd));
      return {
        altura: Math.max(280, linhas.length * 24 + 90),
        data: [
          { type: "bar", orientation: "h", name: "Mais frequente em T=1", x: linhas.map((l) => (l.smd >= 0 ? l.smd : null)), y: linhas.map((l) => rotuloEixo(l.rotulo)), marker: { color: COR.t1 }, hovertemplate: "<b>%{y}</b><br>SMD: %{x:.3f}<extra></extra>" },
          { type: "bar", orientation: "h", name: "Mais frequente em T=0", x: linhas.map((l) => (l.smd < 0 ? l.smd : null)), y: linhas.map((l) => rotuloEixo(l.rotulo)), marker: { color: COR.t0 }, hovertemplate: "<b>%{y}</b><br>SMD: %{x:.3f}<extra></extra>" },
        ],
        layout: layout({ barmode: "overlay", margin: { t: 36, r: 16, b: 44, l: 16 }, legend: { orientation: "h", x: 0, y: 1.005, yanchor: "bottom", font: { size: 12 } }, xaxis: { title: { text: "SMD (T=1 − T=0)" }, zeroline: true }, yaxis: { autorange: "reversed", type: "category", categoryorder: "array", categoryarray: linhas.map((l) => rotuloEixo(l.rotulo)), tickfont: { size: celular() ? 10 : 12, color: COR.suave } } }),
      };
    },

    d_ps() {
      const mod = estado.d_modelo;
      const bloco = D.escores[mod];
      const seletor = document.querySelector('[data-filtro="d_medida"]');
      const pesoOpcao = seletor.querySelector('option[value="peso"]');
      pesoOpcao.disabled = mod !== "final";
      if (mod !== "final" && estado.d_medida === "peso") { estado.d_medida = "pct"; seletor.value = "pct"; }
      const med = estado.d_medida;
      const cx = bloco.caixas;
      const centro = cx.map((c) => (c.e0 + c.e1) / 2), largura_ = cx.map((c) => (c.e1 - c.e0) * 0.94);
      const rotulo = med === "pct" ? "% do grupo" : "% da soma dos pesos do grupo";
      const v1 = cx.map((c) => c[med + "_t1"]), v0 = cx.map((c) => c[med + "_t0"]);
      const faixa = cx.map((c) => br(c.e0, 3) + " a " + br(c.e1, 3));
      const maximo = Math.max(...v1, ...v0);
      const passo = maximo > 20 ? 10 : 5;
      const ticks = [];
      for (let t = -Math.ceil(maximo / passo) * passo; t <= Math.ceil(maximo / passo) * passo; t += passo) ticks.push(t);
      const nota = document.getElementById("nota-ps");
      nota.textContent = (mod === "diagnostico"
        ? "Modelo diagnóstico com seis covariáveis, incluindo situação conjugal, com predição fora da partição. O eixo começa em 0,70; " + bloco.fora_eixo_t1 + " registros de T=1 ficam abaixo desse valor."
        : "Modelo final do ATO, sem situação conjugal. Soma dos pesos disponível apenas neste modelo.");
      return {
        tabela: tabela([col("Faixa do escore", (l) => l.f, false), col(NOME.t1, (l) => br(l.a, 2) + "%"), col(NOME.t0, (l) => br(l.b, 2) + "%")], cx.map((c, i) => ({ f: faixa[i], a: v1[i], b: v0[i] }))),
        data: [
          { type: "bar", name: NOME.t1, x: centro, y: v1, width: largura_, customdata: faixa, marker: { color: COR.t1 }, hovertemplate: "<b>" + NOME.t1 + "</b><br>Escore: %{customdata}<br>%{y:.2f}% (" + rotulo + ")<extra></extra>" },
          { type: "bar", name: NOME.t0, x: centro, y: v0.map((v) => -v), width: largura_, customdata: cx.map((c, i) => [faixa[i], v0[i]]), marker: { color: COR.t0 }, hovertemplate: "<b>" + NOME.t0 + "</b><br>Escore: %{customdata[0]}<br>%{customdata[1]:.2f}% (" + rotulo + ")<extra></extra>" },
        ],
        layout: layout({ barmode: "overlay", xaxis: { title: { text: "Escore de propensão e(X)" } }, yaxis: { title: { text: rotulo + ", T=1 acima e T=0 abaixo" }, tickvals: ticks, ticktext: ticks.map((t) => br(Math.abs(t), 0) + "%"), zeroline: true } }),
      };
    },

    d_ess() {
      const n = D.pesos.find((p) => p.item === "n"), e = D.pesos.find((p) => p.item === "n efetivo (Kish)");
      const grupos = [NOME.t1, NOME.t0];
      return {
        data: [
          { type: "bar", name: "Registros (n)", x: grupos, y: [n.t1, n.t0], text: [int(n.t1), int(n.t0)], textposition: "outside", cliponaxis: false, marker: { color: "#B7C8D5" }, hovertemplate: "<b>%{x}</b><br>n: %{y:,.0f}<extra></extra>" },
          { type: "bar", name: "n efetivo (Kish)", x: grupos, y: [e.t1, e.t0], text: [int(e.t1), int(e.t0)], textposition: "outside", cliponaxis: false, marker: { color: COR.t1 }, hovertemplate: "<b>%{x}</b><br>n efetivo: %{y:,.0f}<extra></extra>" },
        ],
        layout: layout({ barmode: "group", margin: { t: 40, r: 10, b: 30, l: 16 }, yaxis: { tickformat: ",d", title: { text: "Nascimentos" } }, xaxis: {} }),
      };
    },

    d_conjugal() {
      const linhas = D.balanco.ato.filter((l) => l.variavel.startsWith("Situação")).map((l) => Object.assign({}, l, { curto: l.nivel }));
      const seg = { x: [], y: [] };
      linhas.forEach((l) => { seg.x.push(Math.abs(l.smd_antes), Math.abs(l.smd_depois), null); seg.y.push(l.curto, l.curto, null); });
      return {
        data: [
          { type: "scatter", mode: "lines", x: seg.x, y: seg.y, line: { color: COR.eixo, width: 1.5 }, hoverinfo: "skip", showlegend: false, meta: { semTabela: true } },
          { type: "scatter", mode: "markers", name: "Antes", x: linhas.map((l) => Math.abs(l.smd_antes)), y: linhas.map((l) => l.curto), marker: { size: 10, symbol: "circle-open", color: COR.cinza, line: { width: 2 } }, hovertemplate: "<b>%{y}</b><br>|SMD| antes: %{x:.3f}<extra></extra>" },
          { type: "scatter", mode: "markers", name: "Depois da ponderação principal", x: linhas.map((l) => Math.abs(l.smd_depois)), y: linhas.map((l) => l.curto), marker: { size: 10, color: COR.t0 }, hovertemplate: "<b>%{y}</b><br>|SMD| depois: %{x:.3f}<extra></extra>" },
        ],
        layout: layout({ xaxis: { title: { text: "|SMD|" }, range: [-0.01, 0.46] }, yaxis: { autorange: "reversed", type: "category" }, shapes: [linhaRef("x", 0.1, COR.t0, "dot")] }),
      };
    },

    e_riscos() {
      const r = D.resultados, grupos = ["t1", "t0"], nomes = grupos.map((g) => NOME[g]);
      const serie = (chave, ic, nome, simbolo, deslocamento) => ({
        type: "scatter", mode: "markers", name: nome,
        x: grupos.map((g, i) => i + deslocamento), y: grupos.map((g) => r[g][chave]),
        error_y: { type: "data", symmetric: false, array: grupos.map((g) => r[g][ic][1] - r[g][chave]), arrayminus: grupos.map((g) => r[g][chave] - r[g][ic][0]), color: COR.marinho, thickness: 1.6, width: 6 },
        marker: { size: 13, symbol: simbolo, color: grupos.map((g) => COR[g]), line: { width: 2, color: grupos.map((g) => COR[g]) } },
        customdata: grupos.map((g, i) => [br(r[g][ic][0], 2) + " a " + br(r[g][ic][1], 2), nomes[i]]),
        hovertemplate: "<b>%{customdata[1]}</b><br>" + nome + ": %{y:.2f}%<br>IC 95%: %{customdata[0]}<extra></extra>",
      });
      return {
        tabela: T.e_riscos(),
        data: [serie("risco_bruto", "ic_bruto", "Risco bruto", "circle-open", -0.1), serie("risco_ato", "ic_ato", "Risco ponderado ATO", "circle", 0.1)],
        layout: layout({ xaxis: { tickvals: [0, 1], ticktext: nomes, range: [-0.5, 1.5], showgrid: false, zeroline: false }, yaxis: { ticksuffix: "%", title: { text: "Risco de peso < 2.500 g" }, range: [7, 12] }, legend: { orientation: "h", x: 0, y: 1.06, yanchor: "bottom", itemsizing: "constant", font: { size: 12 } } }),
      };
    },

    e_difs() {
      const r = D.resultados;
      return forest([
        { nome: "Diferença bruta", v: r.dif_bruta.valor, ic: r.dif_bruta.ic, cor: COR.cinza, simbolo: "circle-open" },
        { nome: "Diferença ajustada (ATO)", v: r.dif_ato.valor, ic: r.dif_ato.ic, cor: COR.t1, simbolo: "circle" },
      ]);
    },

    e_incerteza() {
      const r = D.resultados, b = r.bootstrap;
      return forest([
        { nome: "IC por percentis", v: r.dif_ato.valor, ic: r.dif_ato.ic, cor: COR.t1, simbolo: "circle" },
        { nome: "IC normal (conferência)", v: r.dif_ato.valor, ic: b.ic_normal, cor: COR.verde, simbolo: "square" },
      ]);
    },

    e_sens() {
      const r = D.resultados, s = D.sensibilidade;
      return forest([
        { nome: "Principal, com IC 95%", v: r.dif_ato.valor, ic: r.dif_ato.ic, cor: COR.t1, simbolo: "circle" },
        { nome: "Com situação conjugal, sem IC", v: s.dif, ic: null, cor: COR.t0, simbolo: "diamond" },
      ]);
    },

    f_dif() {
      const a = anosF();
      return {
        data: [
          { type: "scatter", mode: celular() ? "lines+markers" : "lines+markers+text", name: "Diferença ATO (ajustada)", x: a.map((l) => l.ano), y: a.map((l) => l.dif_ato), text: a.map((l) => br(l.dif_ato, 2)), textposition: "top center", textfont: { size: celular() ? 10 : 12 }, cliponaxis: false, line: { color: COR.t1, width: 2.4 }, marker: { size: 9 }, customdata: a.map((l) => [l.risco_ato_t1, l.risco_ato_t0]), hovertemplate: "<b>%{x}</b><br>Diferença ATO: %{y:.2f} p.p.<br>Risco ATO: T=1 %{customdata[0]:.2f}%, T=0 %{customdata[1]:.2f}%<br>Sem IC anual<extra></extra>" },
          { type: "scatter", mode: "lines+markers", name: "Diferença bruta", x: a.map((l) => l.ano), y: a.map((l) => l.dif_bruta), line: { color: COR.cinza, width: 2, dash: "dash" }, marker: { size: 7, symbol: "circle-open" }, hovertemplate: "<b>%{x}</b><br>Diferença bruta: %{y:.2f} p.p.<extra></extra>" },
        ],
        layout: layout({ xaxis: eixoAnos(), yaxis: { title: { text: "Diferença T=1 − T=0 (p.p.)" }, range: [-2.8, 0.4], zeroline: true, zerolinewidth: 1.4 } }),
      };
    },

    f_riscos() {
      const a = anosF(), tipo = estado.f_risco, rotulo = tipo === "ato" ? "ponderado ATO" : "bruto";
      return {
        data: ["t1", "t0"].map((g) => ({
          type: "scatter", mode: "lines+markers", name: NOME[g], x: a.map((l) => l.ano), y: a.map((l) => l["risco_" + tipo + "_" + g]),
          line: { color: COR[g], width: 2.2 }, marker: { size: 8, symbol: g === "t1" ? "circle" : "square" },
          hovertemplate: "<b>" + NOME[g] + ", %{x}</b><br>Risco " + rotulo + ": %{y:.2f}%<extra></extra>",
        })),
        layout: layout({ xaxis: eixoAnos(), yaxis: { ticksuffix: "%", title: { text: "Risco " + rotulo } } }),
      };
    },

    f_t0() {
      const a = anosF();
      return {
        data: [{ type: "scatter", mode: celular() ? "lines+markers" : "lines+markers+text", name: "T=0 entre os elegíveis", x: a.map((l) => l.ano), y: a.map((l) => l.pct_t0), text: a.map((l) => br(l.pct_t0, 1)), textposition: "top center", textfont: { size: celular() ? 10 : 12 }, cliponaxis: false, line: { color: COR.t0, width: 2.4 }, marker: { size: 9 }, customdata: a.map((l) => [l.n_t0, l.n_elegiveis]), hovertemplate: "<b>%{x}</b><br>%{y:.2f}% dos elegíveis<br>%{customdata[0]:,.0f} de %{customdata[1]:,.0f}<extra></extra>" }],
        layout: layout({ showlegend: false, margin: { t: 26, r: 16, b: 44, l: 16 }, xaxis: eixoAnos(), yaxis: { ticksuffix: "%", rangemode: "tozero", title: { text: "% dos elegíveis" } } }),
      };
    },

    f_elegiveis() {
      const a = anosF();
      return {
        data: ["t1", "t0"].map((g) => ({
          type: "bar", name: NOME[g], x: a.map((l) => l.ano), y: a.map((l) => l["n_" + g]), marker: { color: COR[g], line: { color: "#fff", width: 1 } },
          customdata: a.map((l) => l.n_elegiveis), hovertemplate: "<b>" + NOME[g] + ", %{x}</b><br>%{y:,.0f} nascimentos<br>Elegíveis no ano: %{customdata:,.0f}<extra></extra>",
        })),
        layout: layout({ barmode: "stack", xaxis: eixoAnos(), yaxis: { tickformat: ",d", title: { text: "Nascimentos elegíveis" } } }),
      };
    },

    f_diag() {
      const a = anosF(), d = estado.f_diagnostico, x = a.map((l) => l.ano);
      const linha = (k, nome, cor, simbolo, tipo, fmt, sufixo) => ({ type: "scatter", mode: "lines+markers", name: nome, x, y: a.map((l) => l[k]), line: { color: cor, width: 2, dash: tipo || "solid" }, marker: { size: 8, symbol: simbolo || "circle" }, hovertemplate: "<b>" + nome + ", %{x}</b><br>%{y:" + fmt + "}" + (sufixo || "") + "<extra></extra>" });
      const opcoes = {
        smd: { data: [linha("smd_antes", "Antes", COR.cinza, "circle-open", "dash", ".4f"), linha("smd_depois", "Depois (ATO)", COR.t1, "circle", "solid", ".4f")], y: { title: { text: "Maior |SMD|" }, rangemode: "tozero" }, shapes: [linhaRef("y", 0.1, COR.t0, "dot")] },
        conjugal: { data: [linha("smd_conjugal", "Situação conjugal", COR.t0, "circle", "solid", ".4f")], y: { title: { text: "|SMD| após ATO" }, rangemode: "tozero" }, shapes: [linhaRef("y", 0.1, COR.t0, "dot"), linhaRef("y", 0.2, COR.t0, "dot")] },
        ess: { data: [linha("ess_pct_t1", NOME.t1, COR.t1, "circle", "solid", ".1f", "%"), linha("ess_pct_t0", NOME.t0, COR.t0, "square", "solid", ".1f", "%")], y: { ticksuffix: "%", title: { text: "n efetivo / n" }, range: [70, 102] } },
        suporte: { data: [linha("suporte_min", "Limite inferior", COR.t1, "circle", "solid", ".4f"), linha("suporte_max", "Limite superior", COR.verde, "square", "solid", ".4f")], y: { title: { text: "Escore" }, range: [0, 1.02] } },
        escore: { data: [linha("media_escore", "Média do escore", COR.t1, "circle", "solid", ".4f")], y: { title: { text: "Média de e(X)" }, range: [0.8, 1] } },
      }[d];
      return { data: opcoes.data, layout: layout({ showlegend: opcoes.data.length > 1, xaxis: eixoAnos(), yaxis: opcoes.y, shapes: opcoes.shapes || [] }) };
    },

    g_t0_duracao() {
      const f = D.temporalidade.por_faixa;
      const cores = [COR.t0, "#B7651A", "#8F4F13"];
      return {
        data: [3, 4, 5].map((i, k) => ({
          type: "bar", name: "Mês " + (i + 1), x: f.map((l) => l.faixa + " sem."), y: f.map((l) => l.pct_meses[i]), marker: { color: cores[k], line: { color: "#fff", width: 1.5 } },
          hovertemplate: "<b>Início no mês " + (i + 1) + "</b><br>%{x}<br>%{y:.2f}% dos nascimentos da faixa<extra></extra>",
        })),
        layout: layout({ barmode: "stack", xaxis: { title: { text: "Duração da gestação" } }, yaxis: { ticksuffix: "%", title: { text: "% da faixa" }, rangemode: "tozero" } }),
      };
    },

    g_lbw_duracao() {
      const f = D.temporalidade.por_faixa;
      return {
        data: [{ type: "bar", name: "Baixo peso", x: f.map((l) => l.faixa + " sem."), y: f.map((l) => l.pct_baixo_peso), text: f.map((l) => br(l.pct_baixo_peso, 2) + "%"), textposition: "outside", cliponaxis: false, marker: { color: COR.marinho }, customdata: f.map((l) => [l.n_baixo_peso, l.n]), hovertemplate: "<b>%{x}</b><br>%{y:.2f}% com baixo peso<br>%{customdata[0]:,.0f} de %{customdata[1]:,.0f}<extra></extra>" }],
        layout: layout({ showlegend: false, margin: { t: 26, r: 8, b: 44, l: 16 }, xaxis: { title: { text: "Duração da gestação" } }, yaxis: { ticksuffix: "%", title: { text: "% da faixa" }, range: [0, 108] } }),
      };
    },

    g_lbw_mes() {
      const m = D.temporalidade.por_mes;
      const rotulos = m.map((l) => l.mes + "<br>n = " + int(l.n));
      return {
        data: [
          { type: "bar", name: "Pré-termo (< 37 semanas)", x: rotulos, y: m.map((l) => l.pct_preterm), marker: { color: COR.marinho, line: { color: "#fff", width: 1.5 } }, hovertemplate: "<b>%{x}</b><br>Baixo peso e pré-termo: %{y:.2f}%<extra></extra>" },
          { type: "bar", name: "A termo (≥ 37 semanas)", x: rotulos, y: m.map((l) => l.pct_termo), marker: { color: COR.verde, line: { color: "#fff", width: 1.5 } }, customdata: m.map((l) => l.pct_total), hovertemplate: "<b>%{x}</b><br>Baixo peso e a termo: %{y:.2f}%<br>Total: %{customdata:.2f}%<extra></extra>" },
        ],
        layout: layout({ barmode: "stack", xaxis: {}, yaxis: { ticksuffix: "%", title: { text: "% dos nascimentos do mês" }, rangemode: "tozero" }, margin: { t: 34, r: 12, b: 62, l: 16 } }),
      };
    },

    g_inclusao() {
      const nomes = ["Incluídos em B (1–6)", "Início nos meses 7–9", "Ausente, ignorada ou outra", "Fora de B"];
      const linhas = nomes.map((n) => D.temporalidade.selecao.find((l) => l.grupo === n)).reverse();
      return {
        data: [{ type: "bar", orientation: "h", name: "Menos de 28 semanas", x: linhas.map((l) => (typeof l.lt28.pct === "number" ? l.lt28.pct : 0)), y: linhas.map((l) => l.grupo), text: linhas.map((l) => (typeof l.lt28.pct !== "number" ? "< 1% (menos de 10)" : l.lt28.aprox ? "≈ " + br(l.lt28.pct, 0) + "%" : br(l.lt28.pct, 2) + "%")), textposition: "outside", cliponaxis: false, marker: { color: COR.marinho }, customdata: linhas.map((l) => [typeof l.lt28.n === "string" ? "menos de 10" : (l.lt28.aprox ? "≈ " : "") + int(l.lt28.n), l.n]), hovertemplate: "<b>%{y}</b><br>%{text}<br>%{customdata[0]} de %{customdata[1]:,.0f}<extra></extra>" }],
        layout: layout({ showlegend: false, margin: { t: 10, r: 110, b: 40, l: 16 }, xaxis: { ticksuffix: "%", title: { text: "% do grupo" }, rangemode: "tozero" }, yaxis: {} }),
      };
    },
  };

  function forest(linhas) {
    const inv = linhas.slice().reverse();
    return {
      tabela: tabela([col("Estimativa", (l) => l.nome, false), col("Diferença (p.p.)", (l) => pp(l.v)), col("IC 95%", (l) => (l.ic ? br(l.ic[0], 2) + " a " + br(l.ic[1], 2) : "sem intervalo de confiança"))], linhas),
      data: inv.map((l) => ({
        type: "scatter", mode: "markers", name: l.nome, x: [l.v], y: [l.nome],
        marker: { size: 14, symbol: l.simbolo, color: l.cor, line: { width: 2, color: l.cor } },
        error_x: l.ic ? { type: "data", symmetric: false, array: [l.ic[1] - l.v], arrayminus: [l.v - l.ic[0]], color: l.cor, thickness: 2.2, width: 7 } : undefined,
        customdata: [l.ic ? br(l.ic[0], 2) + " a " + br(l.ic[1], 2) + " p.p." : "sem intervalo de confiança"],
        hovertemplate: "<b>" + l.nome + "</b><br>%{x:.2f} p.p.<br>IC 95%: %{customdata[0]}<extra></extra>",
      })),
      layout: layout({ showlegend: false, margin: { t: 8, r: 18, b: 44, l: 16 }, xaxis: { title: { text: "Diferença de risco (p.p.)" }, range: [-3, 0.3], zeroline: true, zerolinewidth: 1.4, zerolinecolor: COR.tinta }, yaxis: { type: "category", showgrid: false } }),
    };
  }

  /* ---- Tabelas ---- */
  function tabela(colunas, linhas, opcoes) {
    const o = opcoes || {};
    const cab = colunas.map((c) => '<th class="' + (c.n ? "num" : "") + '" scope="col">' + esc(c.t) + "</th>").join("");
    const corpo = linhas.map((l) => '<tr' + (o.destaque && o.destaque(l) ? ' class="destaque"' : "") + ">" + colunas.map((c) => '<td class="' + (c.n ? "num" : "") + '">' + esc(c.f(l)) + "</td>").join("") + "</tr>").join("");
    return '<div class="tabela-rolagem"><table><thead><tr>' + cab + "</tr></thead><tbody>" + corpo + "</tbody></table></div>";
  }
  const col = (t, f, n) => ({ t, f, n: n !== false });

  const T = {
    b_anual: () => tabela([col("Ano", (l) => l.ano, false), col("Mês válido, capital", (l) => br(l.pct_mes_capital, 2) + "%"), col("Mês válido, estado", (l) => br(l.pct_mes_estado, 2) + "%"), col("Elegíveis", (l) => int(l.n_elegiveis)), col("T=1", (l) => int(l.n_t1)), col("T=0", (l) => int(l.n_t0)), col("Retenção", (l) => br(l.pct_retencao, 2) + "%")], D.qualidade_anual.capital),
    b_campos: () => tabela([col("Indicador", (l) => l.indicador, false), col("Mínimo", (l) => br(l.min_capital, 2) + "%"), col("Máximo", (l) => br(l.max_capital, 2) + "%"), col("Menor vantagem", (l) => br(l.menor_vantagem, 2)), col("Maior vantagem", (l) => br(l.maior_vantagem, 2)), col("Anos superior", (l) => l.anos_superior), col("Anos inferior", (l) => l.anos_inferior)], D.qualidade_anual.campos),
    c_perfil: () => tabela([col("Nível", (l) => l.nivel, false), col("T=1", (l) => br(l.pct_t1, 1) + "%"), col("T=0", (l) => br(l.pct_t0, 1) + "%"), col("Todos", (l) => br(l.pct_total, 1) + "%"), col("Diferença (p.p.)", (l) => br(l.dif_pp, 1)), col("SMD", (l) => br(l.smd, 3))], D.perfil.variaveis[estado.c_variavel]),
    d_percentis: () => {
      const linhas = D.escores.diagnostico.percentis.map((l, i) => ({ item: l.item, d1: l.t1, d0: l.t0, f1: D.escores.final.percentis[i].t1, f0: D.escores.final.percentis[i].t0 }));
      return tabela([col("", (l) => l.item, false), col("Final T=1", (l) => br(l.f1, 4)), col("Final T=0", (l) => br(l.f0, 4)), col("Diag. T=1", (l) => br(l.d1, 4)), col("Diag. T=0", (l) => br(l.d0, 4))], linhas);
    },
    d_regioes: () => tabela([col("Região", (l) => l.regiao, false), col("T=1", (l) => int(l.n_t1) + " (" + br(l.pct_t1, 2) + "%)"), col("T=0", (l) => int(l.n_t0) + " (" + br(l.pct_t0, 2) + "%)")], D.escores.regioes),
    d_pesos: () => {
      const inteiros = new Set(["n", "n efetivo (Kish)"]);
      const fmt = (l, v) => (inteiros.has(l.item) ? int(v) : br(v, l.item.includes("/ n") ? 1 : 4));
      return tabela([col("", (l) => l.item, false), col("T=1 (peso 1−e)", (l) => fmt(l, l.t1)), col("T=0 (peso e)", (l) => fmt(l, l.t0))], D.pesos);
    },
    d_alvo: () => {
      const f = (l, v) => br(v, 1) + (l.unidade === "%" ? "%" : "");
      return tabela([col("Variável", (l) => l.variavel, false), col("Nível", (l) => l.nivel, false), col("Total", (l) => f(l, l.total)), col("T=1 bruto", (l) => f(l, l.t1_bruto)), col("T=0 bruto", (l) => f(l, l.t0_bruto)), col("T=1 ATO", (l) => f(l, l.t1_ato)), col("T=0 ATO", (l) => f(l, l.t0_ato))], D.perfil.populacao_alvo);
    },
    e_riscos: () => {
      const r = D.resultados;
      const ic = (x) => br(x[0], 2) + " a " + br(x[1], 2);
      return tabela([col("", (l) => l.n, false), col("Nascimentos", (l) => l.total), col("Casos", (l) => l.casos), col("Risco bruto", (l) => l.b), col("IC 95% bruto", (l) => l.bi), col("Risco ATO", (l) => l.a), col("IC 95% ATO", (l) => l.ai)], [
        { n: NOME.t1, total: int(r.t1.n), casos: int(r.t1.casos), b: br(r.t1.risco_bruto, 2) + "%", bi: ic(r.t1.ic_bruto), a: br(r.t1.risco_ato, 2) + "%", ai: ic(r.t1.ic_ato) },
        { n: NOME.t0, total: int(r.t0.n), casos: int(r.t0.casos), b: br(r.t0.risco_bruto, 2) + "%", bi: ic(r.t0.ic_bruto), a: br(r.t0.risco_ato, 2) + "%", ai: ic(r.t0.ic_ato) },
        { n: "Diferença T=1 − T=0", total: "", casos: "", b: pp(r.dif_bruta.valor) + " p.p.", bi: ic(r.dif_bruta.ic), a: pp(r.dif_ato.valor) + " p.p.", ai: ic(r.dif_ato.ic), d: true },
      ], { destaque: (l) => l.d });
    },
    e_sens: () => {
      const inteiro = (l) => l.item.includes("Tamanho efetivo");
      const quatro = (l) => l.item.includes("SMD");
      const f = (l, v) => (inteiro(l) ? int(v) : br(v, quatro(l) ? 4 : 2));
      return tabela([col("Medida", (l) => l.item, false), col("Principal", (l) => f(l, l.principal)), col("Com situação conjugal (sem IC)", (l) => f(l, l.sensibilidade))], D.sensibilidade.linhas);
    },
    f_anual: () => tabela([col("Ano", (l) => l.ano, false), col("Elegíveis", (l) => int(l.n_elegiveis)), col("T=1", (l) => int(l.n_t1)), col("T=0", (l) => int(l.n_t0)), col("T=0 (%)", (l) => br(l.pct_t0, 2)), col("Dif. bruta (p.p.)", (l) => br(l.dif_bruta, 2)), col("Risco ATO T=1", (l) => br(l.risco_ato_t1, 2) + "%"), col("Risco ATO T=0", (l) => br(l.risco_ato_t0, 2) + "%"), col("Dif. ATO (p.p.)", (l) => br(l.dif_ato, 2)), col("n ef. T=1", (l) => int(l.ess_t1)), col("n ef. T=0", (l) => int(l.ess_t0)), col("Fora do suporte T=1", (l) => int(l.n_fora_t1)), col("Fora do suporte T=0", (l) => int(l.n_fora_t0)), col("Iterações", (l) => l.iteracoes)], anosF()),
    g_selecao: () => {
      const c = (x) => (typeof x.n === "string" ? "< 10" : (x.aprox ? "≈ " : "") + int(x.n)) + " (" + (typeof x.pct === "string" ? "< 1%" : (x.aprox ? "≈ " + br(x.pct, 0) : br(x.pct, 2)) + "%") + ")";
      return tabela([col("Início do pré-natal", (l) => l.grupo, false), col("Nascimentos", (l) => int(l.n)), col("% do total", (l) => br(l.pct_total, 2)), col("< 28 semanas", (l) => c(l.lt28)), col("28–36 semanas", (l) => c(l.de28a36)), col("≥ 37 semanas", (l) => c(l.ge37))], D.temporalidade.selecao, { destaque: (l) => l.grupo.startsWith("Total") });
    },
    g_fontes: () => tabela([col("Arquivo", (l) => l.caminho, false), col("SHA-256", (l) => l.sha256, false)], D.meta.fontes),
    g_matriz: () => tabela(D.meta.matriz_colunas.map((t, i) => col(t, (l) => l[i], false)), D.meta.matriz),
  };

  const DEPENDENCIAS = { b_metrica: ["b_indicador"], b_medida: ["b_variaveis"], b_grupo: ["b_serie_grupos"], c_variavel: ["c_perfil", "t:c_perfil"], d_bloco: ["d_love", "d_smd"], d_modelo: ["d_ps"], d_medida: ["d_ps"], f_ini: ["f"], f_fim: ["f"], f_risco: ["f_riscos"], f_diagnostico: ["f_diag"] };

  /* ---- Tabela automática dos dados do gráfico ---- */
  function dadosDoGrafico(spec) {
    const tracos = spec.data.filter((t) => !(t.meta && t.meta.semTabela) && t.type !== "heatmap");
    if (spec.data[0].type === "heatmap") {
      const t = spec.data[0];
      return "<div class='tabela-rolagem'><table><thead><tr><th></th>" + t.x.map((x) => '<th class="num">' + esc(x) + "</th>").join("") + "</tr></thead><tbody>" + t.y.map((y, i) => "<tr><td>" + esc(y) + "</td>" + t.text[i].map((v) => '<td class="num">' + esc(v) + "</td>").join("") + "</tr>").join("") + "</tbody></table></div>";
    }
    const horizontal = tracos[0].orientation === "h" || (tracos[0].x && typeof tracos[0].x[0] === "number" && typeof tracos[0].y[0] === "string");
    const chave = (t) => (horizontal ? t.y : t.x);
    const valor = (t) => (horizontal ? t.x : t.y);
    const categorias = [];
    tracos.forEach((t) => chave(t).forEach((c) => { if (c !== null && !categorias.includes(c)) categorias.push(c); }));
    const rotulo = (c) => String(c).replace("<br>", ", ");
    const formatado = (t, i) => {
      if (i < 0) return "—";
      const v = valor(t)[i];
      if (v === null || v === undefined) return "—";
      if (typeof v !== "number") return String(v);
      if (Number.isInteger(v)) return int(v);
      return br(v, Math.abs(v) < 1 ? 4 : 2);
    };
    const celulas = categorias.map((c) => "<tr><td>" + esc(rotulo(c)) + "</td>" + tracos.map((t) => '<td class="num">' + esc(formatado(t, chave(t).indexOf(c))) + "</td>").join("") + "</tr>").join("");
    return "<div class='tabela-rolagem'><table><thead><tr><th></th>" + tracos.map((t) => '<th class="num">' + esc(t.name || "Valor") + "</th>").join("") + "</tr></thead><tbody>" + celulas + "</tbody></table></div>";
  }

  /* ---- Renderização ---- */
  const prontos = new Set();
  function desenhar(id) {
    const fig = document.querySelector('[data-fig="' + id + '"]');
    if (!fig) return;
    const spec = G[id]();
    const alvo = fig.querySelector(".plot");
    const alturaBase = fig.dataset.altura === "auto" ? spec.altura : Number(fig.dataset.altura);
    spec.layout.height = spec.altura || alturaBase;
    alvo.style.minHeight = spec.layout.height + "px";
    Plotly.react(alvo, spec.data, spec.layout, Object.assign({}, CONFIG, { toImageButtonOptions: Object.assign({}, CONFIG.toImageButtonOptions, { filename: "sinasc_" + id }) }));
    fig.querySelector(".tabela-fig").innerHTML = spec.tabela || dadosDoGrafico(spec);
    prontos.add(id);
  }

  function desenharTabela(nome) {
    document.querySelectorAll('[data-tabela="' + nome + '"]').forEach((el) => { el.innerHTML = T[nome](); });
  }

  function atualizarAba(letra) {
    const painel = document.getElementById("painel-" + letra);
    painel.querySelectorAll("[data-fig]").forEach((f) => desenhar(f.dataset.fig));
    painel.querySelectorAll("[data-tabela]").forEach((t) => desenharTabela(t.dataset.tabela));
    if (letra === "f") atualizarPeriodo();
  }

  function atualizarPeriodo() {
    const a = anosF();
    const soma = (k) => a.reduce((s, l) => s + l[k], 0);
    const eleg = soma("n_elegiveis"), t1 = soma("n_t1"), t0 = soma("n_t0");
    const periodo = estado.f_ini === estado.f_fim ? String(estado.f_ini) : estado.f_ini + " a " + estado.f_fim;
    document.getElementById("kpis-periodo").innerHTML = [
      ["Elegíveis no período", int(eleg), periodo, ""],
      ["T=1, início nos meses 1–3", int(t1), br((100 * t1) / eleg, 2) + "% dos elegíveis", " t1"],
      ["T=0, início nos meses 4–6", int(t0), br((100 * t0) / eleg, 2) + "% dos elegíveis", " t0"],
      ["Anos com estimativa pontual", String(a.length), "cada ano com modelo próprio", ""],
    ].map(([r, v, n, c]) => '<div class="kpi' + c + '"><span class="kpi-rotulo">' + r + '</span><span class="kpi-valor">' + v + '</span><span class="kpi-nota">' + n + "</span></div>").join("");
  }

  function abaAtiva() {
    return document.querySelector('.abas [aria-selected="true"]').dataset.aba;
  }

  function aplicarFiltro(chave) {
    const alvos = DEPENDENCIAS[chave] || [];
    if (alvos.includes("f")) {
      document.querySelectorAll("#painel-f [data-fig]").forEach((f) => desenhar(f.dataset.fig));
      desenharTabela("f_anual");
      atualizarPeriodo();
      return;
    }
    alvos.forEach((a) => (a.startsWith("t:") ? desenharTabela(a.slice(2)) : desenhar(a)));
  }

  function selecionarAba(letra, foco) {
    document.querySelectorAll(".abas button").forEach((b) => {
      const ativa = b.dataset.aba === letra;
      b.setAttribute("aria-selected", String(ativa));
      b.tabIndex = ativa ? 0 : -1;
      if (ativa) {
        if (foco) b.focus();
        b.scrollIntoView({ block: "nearest", inline: "center" });
      }
    });
    document.querySelectorAll(".painel").forEach((p) => { p.hidden = p.id !== "painel-" + letra; });
    atualizarAba(letra);
    try { history.replaceState(null, "", "#" + letra); } catch (erro) { /* file:// sem histórico */ }
    window.scrollTo(0, 0);
  }

  function iniciarFiltros() {
    const anos = D.serie.map((l) => l.ano);
    document.querySelectorAll("select[data-anos]").forEach((s) => {
      s.innerHTML = anos.map((a) => "<option>" + a + "</option>").join("");
      s.value = s.dataset.anos;
    });
    const variavel = document.querySelector('[data-filtro="c_variavel"]');
    variavel.innerHTML = D.perfil.ordem_variaveis.map((k) => '<option value="' + esc(k) + '">' + esc(k) + "</option>").join("");

    document.querySelectorAll("select[data-filtro]").forEach((s) => {
      const chave = s.dataset.filtro;
      const ler = () => { estado[chave] = s.dataset.anos ? Number(s.value) : s.value; };
      ler();
      s.addEventListener("change", () => {
        ler();
        if (chave === "f_ini" || chave === "f_fim") {
          const aviso = document.getElementById("aviso-periodo");
          aviso.textContent = "";
          if (estado.f_ini > estado.f_fim) {
            const outro = chave === "f_ini" ? "f_fim" : "f_ini";
            estado[outro] = estado[chave];
            document.querySelector('[data-filtro="' + outro + '"]').value = String(estado[chave]);
            aviso.textContent = "Período ajustado para manter o início antes do fim.";
          }
        }
        aplicarFiltro(chave);
      });
    });
  }

  function iniciarEstruturaFiguras() {
    document.querySelectorAll("[data-fig]").forEach((fig) => {
      const plot = document.createElement("div");
      plot.className = "plot";
      const detalhes = document.createElement("details");
      detalhes.className = "dados";
      detalhes.innerHTML = "<summary>Ver dados do gráfico</summary><div class='tabela-fig'></div>";
      const nota = fig.querySelector(":scope > .nota");
      if (nota) { fig.insertBefore(plot, nota); fig.appendChild(detalhes); } else { fig.appendChild(plot); fig.appendChild(detalhes); }
    });
  }

  function desenharFaixa() {
    const meses = D.temporalidade.distribuicao_meses;
    const maximo = Math.max(...meses.map((m) => m.pct));
    const alturaUtil = 118;
    const fora = D.temporalidade.selecao.find((l) => l.grupo === "Início nos meses 7–9");
    const colunas = meses.map((m, i) => '<div class="mes ' + (i < 3 ? "t1" : "t0") + '"><span class="valor">' + br(m.pct, m.pct < 10 ? 1 : 0) + '%</span><span class="coluna-mes" style="height:' + Math.max(4, (alturaUtil * m.pct) / maximo) + 'px"></span><span class="nome">' + (i + 1) + "</span></div>").join("");
    const fim = '<div class="mes fora"><span class="valor">' + int(fora.n) + ' fora</span><span class="coluna-mes"></span><span class="nome">7 8 9</span></div>';
    document.getElementById("faixa-meses").innerHTML = colunas + fim;
    document.getElementById("faixa-meses").insertAdjacentHTML("afterend", '<div class="grupo-meses"><span class="g1">T=1</span><span class="g0">T=0</span><span class="gx">fora da população</span></div>');
  }

  function desenharFunil() {
    const f = D.funil;
    const c = capital();
    const p1 = (100 * c.n_t1) / c.n_elegiveis;
    const passo = (rotulo, n, final) => '<div class="funil-passo"><div class="funil-barra' + (final ? " final" : "") + '" style="width:' + (100 * n) / f.inicial + "%;" + (final ? "--p1:" + p1 + "%" : "") + '"></div><div class="funil-rotulo"><span>' + esc(rotulo) + "</span><strong>" + int(n) + "</strong></div></div>";
    let html = passo("Nascimentos de mães residentes na capital, 2024", f.inicial, false);
    f.etapas.forEach((e, i) => {
      const ultima = i === f.etapas.length - 1;
      html += '<div class="funil-excl">Exclusão: ' + esc(e.rotulo) + ", " + int(e.n) + " (" + br(e.pct, 2) + "%)</div>";
      html += passo(ultima ? "População elegível (especificação B)" : "Após esta etapa", e.restante, ultima);
    });
    html += '<div class="funil-divisao"><span class="g1">T=1: ' + int(c.n_t1) + " (" + br(p1, 2) + '%)</span><span class="g0">T=0: ' + int(c.n_t0) + " (" + br(c.pct_t0, 2) + "%)</span></div>";
    document.getElementById("funil").innerHTML = html;
  }

  function iniciarCalculadora() {
    const entrada = document.getElementById("calc-e");
    const atualizar = () => {
      const e = Number(entrada.value);
      document.getElementById("calc-saida-e").textContent = br(e, 2);
      document.getElementById("calc-w1").textContent = br(1 - e, 2);
      document.getElementById("calc-w0").textContent = br(e, 2);
      document.getElementById("calc-i1").textContent = br(1 / e, 2);
      document.getElementById("calc-i0").textContent = br(1 / (1 - e), 2);
    };
    entrada.addEventListener("input", atualizar);
    atualizar();
  }

  function iniciarAbas() {
    const botoes = Array.from(document.querySelectorAll(".abas button"));
    botoes.forEach((b, i) => {
      b.addEventListener("click", () => selecionarAba(b.dataset.aba, false));
      b.addEventListener("keydown", (ev) => {
        const destino = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: botoes.length - 1 }[ev.key];
        if (destino === undefined) return;
        ev.preventDefault();
        selecionarAba(botoes[(destino + botoes.length) % botoes.length].dataset.aba, true);
      });
    });
    let temporizador;
    let larguraAnterior = largura();
    window.addEventListener("resize", () => {
      clearTimeout(temporizador);
      temporizador = setTimeout(() => {
        if ((largura() < 620) !== (larguraAnterior < 620)) atualizarAba(abaAtiva());
        larguraAnterior = largura();
      }, 180);
    });
  }

  iniciarEstruturaFiguras();
  iniciarFiltros();
  desenharFaixa();
  desenharFunil();
  iniciarCalculadora();
  iniciarAbas();
  const inicial = (location.hash || "#a").slice(1);
  selecionarAba(/^[a-g]$/.test(inicial) ? inicial : "a", false);
  document.documentElement.dataset.painelPronto = "1";
})();
