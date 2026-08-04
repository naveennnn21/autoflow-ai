import { spawn } from "node:child_process";
import fs from "node:fs";

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9338;
const OUT = "C:/Users/NAVEEN~1/AppData/Local/Temp/cdp_rm";
fs.mkdirSync(OUT, { recursive: true });

const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--force-prefers-reduced-motion", "--remote-debugging-port=" + PORT, "--window-size=1440,900", "--user-data-dir=" + OUT + "/profile", "about:blank"]);
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
  throw new Error("no ws url");
}

async function main() {
  const ws = new WebSocket(await getWsUrl());
  await new Promise((r) => (ws.onopen = r));
  let id = 0;
  const pending = new Map();
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  };
  const send = (method, params = {}) => new Promise((res) => {
    const mid = ++id;
    pending.set(mid, res);
    ws.send(JSON.stringify({ id: mid, method, params }));
  });

  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  await send("Page.navigate", { url: "http://localhost:3000" });
  await sleep(5000);

  const evalJs = async (expr) => {
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true });
    return r.result?.result?.value;
  };

  const env = await evalJs(`JSON.stringify({ reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches, scrollY: scrollY, docH: document.documentElement.scrollHeight })`);
  console.log("ENV:", env);

  const rows = [];
  let y = 0;
  for (let i = 0; i < 60 && y < 12000; i++) {
    // real wheel events via CDP input
    await send("Input.dispatchMouseEvent", { type: "mouseWheel", x: 720, y: 450, deltaX: 0, deltaY: 330 });
    await sleep(350);
    y = await evalJs("scrollY");
    const row = await evalJs(`(() => {
      const steps = [...document.querySelectorAll('#solutions [class*=text-display]')];
      const labels = steps.map(s => s.textContent.trim());
      const box = document.querySelector('#solutions [class*=aspect]');
      const nodes = [...document.querySelectorAll('#solutions [class*=aspect] [class*=rounded-xl]')].slice(0,4).map(n => {
        const ic = n.querySelector('span');
        const nm = ic ? ic.textContent : '?';
        return nm + '=' + Math.round(getComputedStyle(n.parentElement).opacity * 100) / 100;
      });
      const bubble = box ? [...box.querySelectorAll('div')].find(d => d.textContent.includes('Route urgent')) : null;
      return JSON.stringify({
        scrollY,
        visSteps: steps.filter(s => getComputedStyle(s.parentElement).opacity > 0.5).map(s => s.textContent.trim()),
        bubble: bubble ? Math.round(getComputedStyle(bubble).opacity * 100) / 100 : null,
        nodes,
        boxH: box ? box.getBoundingClientRect().height : 0,
        boxTop: box ? box.getBoundingClientRect().top : 0,
        containerH: document.querySelector('#solutions > div > div') ? document.querySelector('#solutions [style*="height"]')?.getBoundingClientRect().height ?? 0 : 0,
      });
    })()`);
    rows.push(JSON.parse(row));
  }
  console.log("ROWS:", JSON.stringify(rows));
  await send("Page.captureScreenshot", { format: "png" }).then(async (r) => {
    fs.writeFileSync(OUT + "/final.png", Buffer.from(r.result.data, "base64"));
  });
  console.log("SHOT:", OUT + "/final.png");
  chrome.kill();
  process.exit(0);
}

main().catch((e) => { console.error(e.message); chrome.kill(); process.exit(1); });
