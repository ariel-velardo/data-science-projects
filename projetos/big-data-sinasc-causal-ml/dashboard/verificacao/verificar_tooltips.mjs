// Regressão dos textos completos de forest(), em navegadores reais e offline.
// Uso: node dashboard/verificacao/verificar_tooltips.mjs [caminho-do-HTML]
// Node >= 22; Chrome e Edge instalados. Nenhuma dependência adicional.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const html = process.argv[2] || fileURLToPath(new URL("../dist/sinasc_dashboard_ipt.html", import.meta.url));
const navegadores = {
  chrome: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  edge: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
};
const esperados = {
  a_difs: [
    "Ajustada (ATO)-1,74 p.p.IC 95%: −2,36 a −1,12 p.p.",
    "Bruta-2,00 p.p.IC 95%: −2,61 a −1,37 p.p.",
  ],
  e_difs: [
    "Diferença ajustada (ATO)-1,74 p.p.IC 95%: −2,36 a −1,12 p.p.",
    "Diferença bruta-2,00 p.p.IC 95%: −2,61 a −1,37 p.p.",
  ],
  e_incerteza: [
    "IC normal (conferência)-1,74 p.p.IC 95%: −2,37 a −1,11 p.p.",
    "IC por percentis-1,74 p.p.IC 95%: −2,36 a −1,12 p.p.",
  ],
  e_sens: [
    "Com situação conjugal, sem IC-1,63 p.p.IC 95%: sem intervalo de confiança",
    "Principal, com IC 95%-1,74 p.p.IC 95%: −2,36 a −1,12 p.p.",
  ],
};
const pausa = (ms) => new Promise((ok) => setTimeout(ok, ms));

async function verificar(nome, executavel) {
  // Perfil isolado no TEMP, preservado para diagnóstico; nunca usa o perfil pessoal.
  const perfil = mkdtempSync(join(tmpdir(), "sinasc-tooltip-"));
  const proc = spawn(executavel, ["--headless=new", "--remote-debugging-port=0",
    "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--user-data-dir=${perfil}`, "about:blank"], { stdio: ["ignore", "ignore", "pipe"], windowsHide: true });
  let ws;
  try {
    const url = await new Promise((ok, erro) => {
      let buffer = "";
      const limite = setTimeout(() => erro(new Error("Navegador não iniciou")), 30000);
      proc.once("error", (e) => { clearTimeout(limite); erro(e); });
      proc.stderr.on("data", (d) => {
        buffer += d;
        const m = buffer.match(/ws:\/\/\S+/);
        if (m) { clearTimeout(limite); ok(m[0]); }
      });
    });
    ws = new WebSocket(url);
    await new Promise((ok, erro) => { ws.addEventListener("open", ok); ws.addEventListener("error", erro); });
    let sequencia = 0, sessionId;
    const pendentes = new Map(), erros = [], rede = [], tooltips = [];
    ws.addEventListener("message", (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && pendentes.has(m.id)) {
        pendentes.get(m.id)(m);
        pendentes.delete(m.id);
      }
      if (m.method === "Runtime.exceptionThrown") erros.push(m.params.exceptionDetails);
      if (m.method === "Runtime.consoleAPICalled" && ["error", "assert"].includes(m.params.type)) erros.push(m.params);
      if (m.method === "Network.requestWillBeSent" && /^https?:/.test(m.params.request.url)) rede.push(m.params.request.url);
    });
    const enviar = (method, params = {}, global = false) => new Promise((ok, erro) => {
      const id = ++sequencia;
      const limite = setTimeout(() => { pendentes.delete(id); erro(new Error(`Tempo esgotado: ${method}`)); }, 30000);
      pendentes.set(id, (m) => { clearTimeout(limite); m.error ? erro(new Error(JSON.stringify(m.error))) : ok(m.result); });
      ws.send(JSON.stringify({ id, method, params, ...(sessionId && !global ? { sessionId } : {}) }));
    });
    const avaliar = async (expression) => {
      const r = await enviar("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      assert.equal(r.exceptionDetails, undefined, JSON.stringify(r.exceptionDetails));
      return r.result.value;
    };
    const esperar = async (expression) => {
      for (let i = 0; i < 100; i++) { if (await avaliar(expression)) return; await pausa(100); }
      throw new Error(`Não ficou pronto: ${expression}`);
    };
    const { targetId } = await enviar("Target.createTarget", { url: "about:blank" }, true);
    ({ sessionId } = await enviar("Target.attachToTarget", { targetId, flatten: true }, true));
    for (const method of ["Page.enable", "Runtime.enable", "Network.enable"]) await enviar(method);
    await enviar("Network.emulateNetworkConditions", { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0 });
    await enviar("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await enviar("Page.navigate", { url: pathToFileURL(html).href });
    await esperar("document.documentElement.dataset.painelPronto === '1'");
    assert.equal(await avaliar("navigator.onLine"), false);
    for (const [id, textos] of Object.entries(esperados)) {
      await avaliar(`document.querySelector('[data-aba="${id[0]}"]').click()`);
      await esperar(`document.querySelectorAll('[data-fig="${id}"] .scatterlayer .trace .point').length === 2`);
      for (const [indice, esperado] of textos.entries()) {
        const ponto = await avaliar(`(() => {
          const g = document.querySelector('[data-fig="${id}"] .plot');
          g.scrollIntoView({block: 'center', behavior: 'instant'});
          const r = g.querySelectorAll('.scatterlayer .trace .point')[${indice}].getBoundingClientRect();
          return {x: r.x + r.width / 2, y: r.y + r.height / 2};
        })()`);
        await enviar("Input.dispatchMouseEvent", { type: "mouseMoved", x: 0, y: 0 });
        await enviar("Input.dispatchMouseEvent", { type: "mouseMoved", ...ponto });
        await esperar(`!!document.querySelector('[data-fig="${id}"] .hoverlayer .hovertext')`);
        const texto = await avaliar(`document.querySelector('[data-fig="${id}"] .hoverlayer .hovertext').textContent`);
        tooltips.push({ grafico: id, ponto: indice, texto });
        assert.equal(texto, esperado, `${nome}: ${id}, ponto ${indice}`);
      }
    }
    assert.deepEqual(erros, [], "Erros JavaScript");
    assert.deepEqual(rede, [], "Requisições externas");
    console.log(JSON.stringify({ navegador: nome, html, offline: true, erros, rede, tooltips }, null, 2));
  } finally {
    ws?.close();
    proc.kill();
  }
}

for (const [nome, executavel] of Object.entries(navegadores)) await verificar(nome, executavel);
