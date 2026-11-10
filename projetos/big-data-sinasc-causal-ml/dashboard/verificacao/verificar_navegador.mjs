// Verifica o HTML em Chrome e Edge reais, sem rede, por CDP (Node 22 ou superior).
// Uso: node dashboard/verificacao/verificar_navegador.mjs
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const AQUI = dirname(fileURLToPath(import.meta.url));
const HTML = resolve(AQUI, "../dist/sinasc_dashboard_ipt.html");
const CAPTURAS = resolve(AQUI, "capturas");
const ABAS = ["a", "b", "c", "d", "e", "f", "g"];
const VIEWPORTS = {
  desktop: { width: 1440, height: 900, mobile: false, deviceScaleFactor: 1 },
  tablet: { width: 820, height: 1100, mobile: true, deviceScaleFactor: 1 },
  celular: { width: 390, height: 844, mobile: true, deviceScaleFactor: 2 },
};
const NAVEGADORES = {
  chrome: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  edge: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
};
const ESPERADOS = ["114.694", "104.576", "10.118", "−1,74 p.p.", "−2,36 a −1,12 p.p."];

const pausa = (ms) => new Promise((r) => setTimeout(r, ms));

class Sessao {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pendentes = new Map();
    this.ouvintes = [];
    this.sessionId = undefined;
    ws.addEventListener("message", (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pendentes.has(m.id)) {
        const { ok, erro } = this.pendentes.get(m.id);
        this.pendentes.delete(m.id);
        m.error ? erro(new Error(JSON.stringify(m.error))) : ok(m.result);
      } else if (m.method) {
        this.ouvintes.forEach((f) => f(m));
      }
    });
  }

  enviar(method, params = {}, global = false) {
    const id = ++this.id;
    const msg = { id, method, params };
    if (this.sessionId && !global) msg.sessionId = this.sessionId;
    return new Promise((ok, erro) => {
      const limite = setTimeout(() => {
        this.pendentes.delete(id);
        erro(new Error(`Sem resposta em 60 s: ${method} ${String(params.expression || "").slice(0, 80)}`));
      }, 60000);
      this.pendentes.set(id, { ok: (v) => { clearTimeout(limite); ok(v); }, erro: (e) => { clearTimeout(limite); erro(e); } });
      this.ws.send(JSON.stringify(msg));
    });
  }

  async avaliar(expressao) {
    const r = await this.enviar("Runtime.evaluate", { expression: expressao, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  }

  async esperar(expressao, limite = 30000) {
    const t0 = Date.now();
    while (Date.now() - t0 < limite) {
      if (await this.avaliar(expressao)) return true;
      await pausa(100);
    }
    throw new Error("Tempo esgotado: " + expressao);
  }
}

async function abrirNavegador(caminho) {
  const perfil = mkdtempSync(join(tmpdir(), "sinasc-cdp-"));
  const proc = spawn(
    caminho,
    ["--headless=new", "--remote-debugging-port=0", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--user-data-dir=${perfil}`, "about:blank"],
    { stdio: ["ignore", "ignore", "pipe"] },
  );
  const url = await new Promise((ok, erro) => {
    let buffer = "";
    proc.stderr.on("data", (d) => {
      buffer += d;
      const m = buffer.match(/ws:\/\/\S+/);
      if (m) ok(m[0]);
    });
    setTimeout(() => erro(new Error("Navegador não iniciou")), 30000);
  });
  const ws = new WebSocket(url);
  await new Promise((ok) => ws.addEventListener("open", ok));
  return { proc, ws, perfil };
}

const PLOTS_OK = (aba) => `(() => {
  const p = document.getElementById('painel-${aba}');
  return [...p.querySelectorAll('[data-fig]')].every(x => x.querySelector('.plot .main-svg'));
})()`;

const SONDA = (aba) => `(() => {
  const p = document.getElementById('painel-${aba}');
  const figs = [...p.querySelectorAll('[data-fig]')].map(f => {
    const g = f.querySelector('.plot');
    const n = (g.data || []).reduce((s, t) => s + ((t.x && t.x.length) || (t.z && t.z.length) || 0), 0);
    return { id: f.dataset.fig, tracos: (g.data || []).length, pontos: n, svg: !!g.querySelector('.main-svg'), tabela: f.querySelectorAll('.tabela-fig tr').length };
  });
  const larg = document.documentElement.clientWidth;
  const excesso = [...document.querySelectorAll('body *')].filter(e => {
    if (e.closest('.tabela-rolagem,.rolagem,.dag-rolagem,.abas,.plot,svg')) return false;
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.right > larg + 1;
  }).slice(0, 8).map(e => e.tagName + '.' + e.className);
  return { figs, scrollLargura: document.documentElement.scrollWidth, larg, excesso, tabelas: [...p.querySelectorAll('[data-tabela]')].map(t => t.querySelectorAll('tr').length) };
})()`;

const PREPARAR_ZOOM = (id) => `(() => {
  const g = document.querySelector('[data-fig="${id}"] .plot');
  g.scrollIntoView({ block: 'center' });
  const r = g.querySelector('.nsewdrag').getBoundingClientRect();
  return { x: r.x, y: r.y, w: r.width, h: r.height, faixa: [...g._fullLayout.xaxis.range].map(Number) };
})()`;

const PONTOS_HOVER = (id) => `(() => {
  const g = document.querySelector('[data-fig="${id}"] .plot');
  const lista = [];
  g.data.forEach((t, c) => {
    if (t.hoverinfo === 'skip') return;
    if (t.type === 'heatmap') {
      [[0, 0], [t.z.length - 1, t.z[0].length - 1]].forEach(([i, j]) => lista.push({ xval: j, yval: i }));
      return;
    }
    const validos = t.x.map((v, i) => (v !== null && t.y[i] !== null ? i : -1)).filter(i => i >= 0);
    [...new Set([validos[0], validos[Math.floor(validos.length / 2)], validos[validos.length - 1]])].forEach(i => lista.push({ curveNumber: c, pointNumber: i }));
  });
  return lista;
})()`;

const LER_HOVER = (id, ponto) => `new Promise(ok => {
  const g = document.querySelector('[data-fig="${id}"] .plot');
  Plotly.Fx.loneUnhover(g._fullLayout._hoverlayer);
  setTimeout(() => {
    const p = ${JSON.stringify(ponto)};
    Plotly.Fx.hover(g, p.xval === undefined ? [p] : p);
    setTimeout(() => ok([...g.querySelectorAll('.hoverlayer .hovertext')].map(h => h.textContent).join(' | ')), 90);
  }, 70);
})`;

async function arrastar(s, x0, y0, x1, y1) {
  const mouse = (type, x, y, extra = {}) => s.enviar("Input.dispatchMouseEvent", { type, x, y, ...extra });
  await mouse("mouseMoved", x0, y0);
  await mouse("mousePressed", x0, y0, { button: "left", buttons: 1, clickCount: 1 });
  await mouse("mouseMoved", (x0 + x1) / 2, (y0 + y1) / 2, { button: "left", buttons: 1 });
  await mouse("mouseMoved", x1, y1, { button: "left", buttons: 1 });
  await mouse("mouseReleased", x1, y1, { button: "left", clickCount: 1 });
  await mouse("mouseMoved", x1 + 3, y1 + 3);
}

async function testarInteracao(s, aba, r) {
  const ids = await s.avaliar(`[...document.querySelectorAll('#painel-${aba} [data-fig]')].map(f => f.dataset.fig)`);
  for (const id of ids) {
    console.error(`  interação ${id}`);
    const item = { id, hovers: 0, hoversVazios: [], zoom: false, restaurado: false, botoes: 0, png: false };
    for (const ponto of await s.avaliar(PONTOS_HOVER(id))) {
      const texto = await s.avaliar(LER_HOVER(id, ponto));
      if (texto && !/undefined|NaN|null/.test(texto)) item.hovers++;
      else item.hoversVazios.push({ ponto, texto });
    }
    await s.avaliar(`Plotly.Fx.loneUnhover(document.querySelector('[data-fig="${id}"] .plot')._fullLayout._hoverlayer)`);
    const antes = await s.avaliar(PREPARAR_ZOOM(id));
    await pausa(120);
    await arrastar(s, antes.x + antes.w * 0.3, antes.y + antes.h * 0.3, antes.x + antes.w * 0.7, antes.y + antes.h * 0.7);
    await pausa(250);
    const depois = await s.avaliar(`[...document.querySelector('[data-fig="${id}"] .plot')._fullLayout.xaxis.range].map(Number)`);
    item.zoom = Math.abs(depois[1] - depois[0]) < Math.abs(antes.faixa[1] - antes.faixa[0]) * 0.9;
    item.botoes = await s.avaliar(`document.querySelectorAll('[data-fig="${id}"] .modebar-btn').length`);
    await s.avaliar(`(() => { const g = document.querySelector('[data-fig="${id}"] .plot'); return Plotly.relayout(g, { 'xaxis.range': ${JSON.stringify(antes.faixa)} }).then(() => true); })()`);
    const final = await s.avaliar(`[...document.querySelector('[data-fig="${id}"] .plot')._fullLayout.xaxis.range].map(Number)`);
    item.restaurado = Math.abs(final[0] - antes.faixa[0]) < 1e-6 && Math.abs(final[1] - antes.faixa[1]) < 1e-6;
    item.png = String(await s.avaliar(`Plotly.toImage(document.querySelector('[data-fig="${id}"] .plot'), { format: 'png', width: 500, height: 280 }).then(u => u.slice(0, 22))`)).startsWith("data:image/png");
    r.interacao.push(item);
  }
}

async function verificar(nome, caminho, capturar) {
  const { proc, ws, perfil } = await abrirNavegador(caminho);
  const s = new Sessao(ws);
  const r = { navegador: nome, excecoes: [], consoleErros: [], requisicoes: [], abas: {}, filtros: [], textos: {}, exportacao: null, interacao: [] };
  const { targetId } = await s.enviar("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await s.enviar("Target.attachToTarget", { targetId, flatten: true });
  s.sessionId = sessionId;
  s.ouvintes.push((m) => {
    if (m.method === "Runtime.exceptionThrown") r.excecoes.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
    if (m.method === "Runtime.consoleAPICalled" && ["error", "warning"].includes(m.params.type)) r.consoleErros.push(m.params.args.map((a) => a.value || a.description).join(" "));
    if (m.method === "Log.entryAdded" && ["error", "warning"].includes(m.params.entry.level)) r.consoleErros.push(m.params.entry.text);
    if (m.method === "Network.requestWillBeSent") {
      const u = m.params.request.url;
      if (!/^(file:|data:|blob:)/.test(u)) r.requisicoes.push(u);
    }
  });
  for (const d of ["Page.enable", "Runtime.enable", "Network.enable", "Log.enable"]) await s.enviar(d);
  await s.enviar("Network.emulateNetworkConditions", { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0 });

  for (const [vp, m] of Object.entries(VIEWPORTS)) {
    await s.enviar("Emulation.setDeviceMetricsOverride", m);
    await s.enviar("Page.navigate", { url: pathToFileURL(HTML).href });
    await s.esperar("document.documentElement.dataset.painelPronto === '1'");
    r.abas[vp] = {};
    console.error(`${nome}: abas em ${vp}`);
    for (const aba of ABAS) {
      await s.avaliar(`document.querySelector('[data-aba="${aba}"]').click()`);
      await s.esperar(PLOTS_OK(aba));
      await pausa(450);
      r.abas[vp][aba] = await s.avaliar(SONDA(aba));
      if (capturar && (vp !== "tablet" || aba === "a")) {
        const { data } = await s.enviar("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
        const pasta = join(CAPTURAS, vp);
        mkdirSync(pasta, { recursive: true });
        writeFileSync(join(pasta, `aba-${aba}.png`), Buffer.from(data, "base64"));
      }
    }
  }

  await s.enviar("Emulation.setDeviceMetricsOverride", VIEWPORTS.desktop);
  await s.enviar("Page.navigate", { url: pathToFileURL(HTML).href });
  await s.esperar("document.documentElement.dataset.painelPronto === '1'");
  r.textos.a = await s.avaliar("document.getElementById('painel-a').innerText");
  console.error(`${nome}: filtros`);
  for (const aba of ABAS) {
    await s.avaliar(`document.querySelector('[data-aba="${aba}"]').click()`);
    await s.esperar(PLOTS_OK(aba));
    const chaves = await s.avaliar(`[...document.querySelectorAll('#painel-${aba} select[data-filtro]')].map(x => ({ k: x.dataset.filtro, v: [...x.options].filter(o => !o.disabled).map(o => o.value), a: x.value }))`);
    for (const { k, v, a } of chaves) {
      for (const val of [...v, a]) {
        await s.avaliar(`(() => { const x = document.querySelector('[data-filtro="${k}"]'); x.value = ${JSON.stringify(val)}; x.dispatchEvent(new Event('change')); })()`);
        await pausa(90);
        const sonda = await s.avaliar(SONDA(aba));
        r.filtros.push({ aba, filtro: k, valor: val, ok: sonda.figs.every((f) => f.tracos > 0 && f.svg) });
      }
    }
  }
  await s.enviar("Page.navigate", { url: pathToFileURL(HTML).href });
  await s.esperar("document.documentElement.dataset.painelPronto === '1'");
  for (const aba of ABAS) {
    await s.avaliar(`document.querySelector('[data-aba="${aba}"]').click()`);
    await s.esperar(PLOTS_OK(aba));
    await pausa(300);
    await testarInteracao(s, aba, r);
  }
  await s.avaliar(`document.querySelector('[data-aba="e"]').click()`);
  await s.esperar(PLOTS_OK("e"));
  r.exportacao = await s.avaliar(`Plotly.toImage(document.querySelector('[data-fig="e_difs"] .plot'), { format: 'png', width: 600, height: 300 }).then(u => u.slice(0, 22))`);
  r.textos.f = await s.avaliar(`(() => {
    const ini = document.querySelector('[data-filtro="f_ini"]'); ini.value = '2014'; ini.dispatchEvent(new Event('change'));
    const fim = document.querySelector('[data-filtro="f_fim"]'); fim.value = '2024'; fim.dispatchEvent(new Event('change'));
    document.querySelector('[data-aba="f"]').click();
    return new Promise(ok => setTimeout(() => ok(document.getElementById('kpis-periodo').innerText), 500));
  })()`);

  await s.enviar("Target.closeTarget", { targetId }, true).catch(() => {});
  ws.close();
  proc.kill();
  await pausa(400);
  try {
    rmSync(perfil, { recursive: true, force: true });
  } catch {
    // o navegador pode manter o perfil temporário em uso por alguns instantes
  }
  return r;
}

const relatorio = [];
for (const [nome, caminho] of Object.entries(NAVEGADORES)) {
  if (!existsSync(caminho)) {
    relatorio.push({ navegador: nome, ausente: true });
    continue;
  }
  relatorio.push(await verificar(nome, caminho, nome === "chrome"));
}

let falhas = 0;
const falhar = (m) => {
  falhas++;
  console.log("FALHA:", m);
};
for (const r of relatorio) {
  if (r.ausente) {
    falhar(`${r.navegador} ausente`);
    continue;
  }
  if (r.excecoes.length) falhar(`${r.navegador}: exceções ${JSON.stringify(r.excecoes.slice(0, 3))}`);
  if (r.consoleErros.length) falhar(`${r.navegador}: console ${JSON.stringify([...new Set(r.consoleErros)].slice(0, 5))}`);
  if (r.requisicoes.length) falhar(`${r.navegador}: requisições externas ${JSON.stringify(r.requisicoes.slice(0, 5))}`);
  if (!String(r.exportacao).startsWith("data:image/png")) falhar(`${r.navegador}: exportação PNG`);
  for (const esperado of ESPERADOS) if (!r.textos.a.includes(esperado)) falhar(`${r.navegador}: texto ausente ${esperado}`);
  if (!r.textos.f.includes("1.587.749")) falhar(`${r.navegador}: total do período: ${r.textos.f}`);
  for (const f of r.filtros) if (!f.ok) falhar(`${r.navegador}: filtro ${f.filtro}=${f.valor}`);
  if (r.interacao.length !== 28) falhar(`${r.navegador}: ${r.interacao.length} gráficos na interação`);
  for (const i of r.interacao) {
    if (!i.hovers || i.hoversVazios.length) falhar(`${r.navegador} ${i.id}: hover ${JSON.stringify(i.hoversVazios.slice(0, 2))}`);
    if (!i.zoom) falhar(`${r.navegador} ${i.id}: zoom`);
    if (!i.restaurado) falhar(`${r.navegador} ${i.id}: restauração de eixos`);
    if (!i.botoes) falhar(`${r.navegador} ${i.id}: barra de ferramentas`);
    if (!i.png) falhar(`${r.navegador} ${i.id}: exportação PNG`);
  }
  for (const [vp, abas] of Object.entries(r.abas)) {
    for (const [aba, sonda] of Object.entries(abas)) {
      if (sonda.scrollLargura > sonda.larg + 1) falhar(`${r.navegador} ${vp} aba ${aba}: rolagem horizontal ${sonda.scrollLargura}>${sonda.larg} ${sonda.excesso}`);
      for (const fig of sonda.figs) {
        if (!(fig.tracos > 0 && fig.pontos > 0 && fig.svg && fig.tabela > 1)) falhar(`${r.navegador} ${vp} ${fig.id}: ${JSON.stringify(fig)}`);
      }
      for (const linhas of sonda.tabelas) if (linhas < 2) falhar(`${r.navegador} ${vp} aba ${aba}: tabela vazia`);
    }
  }
}

const resumo = relatorio.map((r) =>
  r.ausente
    ? r
    : {
        navegador: r.navegador,
        excecoes: r.excecoes.length,
        consoleErros: [...new Set(r.consoleErros)],
        requisicoesExternas: r.requisicoes.length,
        filtrosTestados: r.filtros.length,
        filtrosFalhos: r.filtros.filter((f) => !f.ok).length,
        exportacaoPng: String(r.exportacao).startsWith("data:image/png"),
        interacao: { graficos: r.interacao.length, tooltipsLidos: r.interacao.reduce((s, i) => s + i.hovers, 0), zoom: r.interacao.filter((i) => i.zoom).length, restauracao: r.interacao.filter((i) => i.restaurado).length, png: r.interacao.filter((i) => i.png).length },
        graficosPorViewport: Object.fromEntries(Object.entries(r.abas).map(([v, a]) => [v, Object.values(a).reduce((s, x) => s + x.figs.length, 0)])),
      },
);
writeFileSync(join(AQUI, "relatorio_navegador.json"), JSON.stringify({ falhas, resumo }, null, 2) + "\n");
console.log(JSON.stringify({ falhas, resumo }, null, 2));
process.exit(falhas ? 1 : 0);
