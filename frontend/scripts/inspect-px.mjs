import { spawn } from "node:child_process";
import fs from "node:fs";

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9340;
const OUT = "C:/Users/NAVEEN~1/AppData/Local/Temp/cdp_px";
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
  await send("Page.navigate", { url: "http://localhost:3000" });
  await sleep(5000);

  const evalJs = async (expr) => {
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true });
    if (r.result?.exceptionDetails) return "EXC: " + JSON.stringify(r.result.exceptionDetails).slice(0, 200);
    return r.result?.result?.value;
  };

  // wheel to step 02: section starts ~2250; step2 is ~scrollY 3100-3500
  for (let i = 0; i < 12; i++) {
    await send("Input.dispatchMouseEvent", { type: "mouseWheel", x: 720, y: 450, deltaX: 0, deltaY: 300 });
    await sleep(300);
  }
  await sleep(1200);

  const state = await evalJs(`(() => {
    const box = document.querySelector('#solutions [class*=aspect]');
    const labels = [...document.querySelectorAll('#solutions [class*=text-display]')].map(s => s.textContent.trim());
    const boxR = box.getBoundingClientRect();
    return JSON.stringify({ scrollY, labels, boxR: { top: boxR.top, left: boxR.left, w: boxR.width, h: boxR.height } });
  })()`);
  console.log("STATE:", state);

  // screenshot
  const shot = await send("Page.captureScreenshot", { format: "png" });
  const png = OUT + "/step02.png";
  fs.writeFileSync(png, Buffer.from(shot.result.data, "base64"));
  console.log("SHOT:", png);

  // pixel-sample the box region inside the page by drawing the data URL
  const analysis = await evalJs(`new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const box = document.querySelector('#solutions [class*=aspect]').getBoundingClientRect();
      const c = document.createElement('canvas');
      c.width = img.width; c.height = img.height;
      const ctx = c.getContext('2d');
      ctx.drawImage(img, 0, 0);
      const dpr = img.width / window.innerWidth;
      const x0 = Math.round((box.left + 4) * dpr), y0 = Math.round((box.top + 4) * dpr);
      const x1 = Math.round((box.right - 4) * dpr), y1 = Math.round((box.bottom - 4) * dpr);
      const data = ctx.getImageData(x0, y0, Math.max(1, x1 - x0), Math.max(1, y1 - y0)).data;
      const colors = {};
      for (let y = 0; y < y1 - y0; y += 6) {
        for (let x = 0; x < x1 - x0; x += 6) {
          const i = (y * (x1 - x0) + x) * 4;
          const key = data[i] + ',' + data[i+1] + ',' + data[i+2];
          colors[key] = (colors[key] || 0) + 1;
        }
      }
      const sorted = Object.entries(colors).sort((a, b) => b[1] - a[1]);
      resolve(JSON.stringify({ distinct: Object.keys(colors).length, top: sorted.slice(0, 8) }));
    };
    img.src = ${JSON.stringify(shot.result.data)};
  })`);
  console.log("PIXELS:", analysis);

  chrome.kill();
  process.exit(0);
}

main().catch((e) => { console.error(e.message); chrome.kill(); process.exit(1); });
