import { spawn } from "node:child_process";
import fs from "node:fs";

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9336;
const OUT = "C:/Users/NAVEEN~1/AppData/Local/Temp/cdp_out4";
fs.mkdirSync(OUT, { recursive: true });

const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--remote-debugging-port=" + PORT, "--window-size=1440,900", "--user-data-dir=" + OUT + "/profile", "about:blank"]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getWsUrl() {
  for (let i = 0; i < 50; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const j = await res.json();
      const page = j.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(200);
  }
  throw new Error("CDP not ready");
}

let msgId = 0;
const pending = new Map();
let ws;
function send(method, params = {}) {
  const id = ++msgId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expr) {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result?.value;
}
async function scrollBy(dy) {
  await send("Input.dispatchMouseEvent", { type: "mouseWheel", x: 700, y: 450, deltaX: 0, deltaY: dy });
}

async function main() {
  const wsUrl = await getWsUrl();
  ws = new WebSocket(wsUrl);
  await new Promise((r) => (ws.onopen = r));
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) reject(new Error(JSON.stringify(m.error)));
      else resolve(m.result);
    }
  };
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: "http://localhost:3000" });
  await sleep(8000);

  const env = await evaluate(`({ reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches, scrollY: window.scrollY })`);
  console.log("ENV:", JSON.stringify(env));

  const rows = [];
  for (let i = 0; i < 40; i++) {
    await scrollBy(300);
    await sleep(400);
    const r = await evaluate(`(() => {
      const s = document.getElementById('solutions');
      const out = { scrollY: Math.round(window.scrollY) };
      if (s) {
        const stepDivs = [...s.querySelectorAll('div')].filter(d => {
          const c = String(d.className||'');
          return c.includes('absolute inset-0') && c.includes('flex flex-col justify-center') && d.querySelector('h3');
        });
        out.stepDivs = stepDivs.length;
        out.visibleStep = stepDivs.findIndex(d => parseFloat(getComputedStyle(d).opacity) > 0.5);
        out.stepLabels = stepDivs.map(d => (d.querySelector('h3 span') ? d.querySelector('h3 span').getAttribute('aria-label') : ''));
        out.stepOps = stepDivs.map(d => getComputedStyle(d).opacity.slice(0,4));
        const box = s.querySelector('[class*="aspect-[4/3]"]');
        if (box) {
          const spans = [...box.querySelectorAll('span')].filter(x => ['Gmail','AI','Drive','Slack'].includes(x.textContent.trim()));
          out.nodes = spans.map(sp => { const wrap = sp.closest('[class*="-translate-x-1/2"]'); return sp.textContent.trim() + '=' + getComputedStyle(wrap).opacity.slice(0,4); });
          const rr = box.getBoundingClientRect();
          out.boxRect = { top: Math.round(rr.top), height: Math.round(rr.height), width: Math.round(rr.width) };
        }
      }
      const cards = [...document.querySelectorAll('p')].filter(p => ['Gmail','AI Extract','Google Drive','Slack'].includes(p.textContent.trim()));
      out.demoCards = cards.length;
      return out;
    })()`);
    rows.push(r);
  }
  for (const r of rows) console.log(JSON.stringify(r));
  chrome.kill();
  process.exit(0);
}
main().catch((e) => { console.error("FAILED:", e.message); try { chrome.kill(); } catch {} process.exit(1); });
