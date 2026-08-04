/* Temporary diagnostic: drive headless Chrome via CDP to inspect the landing page
   storytelling visualization at various scroll positions and report computed styles. */
import { spawn } from "node:child_process";
import fs from "node:fs";

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9333;
const OUT = "C:/Users/NAVEEN~1/AppData/Local/Temp/cdp_out";

fs.mkdirSync(OUT, { recursive: true });

const chrome = spawn(CHROME, [
  "--headless=new",
  "--disable-gpu",
  "--remote-debugging-port=" + PORT,
  "--window-size=1440,900",
  "--user-data-dir=" + OUT + "/profile",
  "about:blank",
]);

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
  await send("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
  });

  await send("Page.navigate", { url: "http://localhost:3000" });
  await sleep(6000);

  // Wait for hydration
  await evaluate("new Promise(r => setTimeout(r, 2500))");

  // Find the storytelling section and scroll it into view step by step
  const info = await evaluate(`(() => {
    const section = document.getElementById('solutions');
    if (!section) return { error: 'no solutions section' };
    const box = section.querySelector('[class*="aspect-[4/3]"]');
    if (!box) return { error: 'no visualization box', sectionExists: true };
    const nodes = [...box.querySelectorAll('div')].filter(d => d.textContent.trim() === 'Gmail' || d.textContent.trim() === 'AI' || d.textContent.trim() === 'Drive' || d.textContent.trim() === 'Slack');
    const cs = getComputedStyle(box);
    return {
      boxRect: box.getBoundingClientRect().toJSON(),
      boxDisplay: cs.display,
      boxVisibility: cs.visibility,
      boxOpacity: cs.opacity,
      boxOverflow: cs.overflow,
      nodeCount: nodes.length,
      nodeInfo: nodes.map(n => {
        const s = getComputedStyle(n.closest('[class*="absolute"]'));
        return { text: n.textContent.trim(), opacity: s.opacity, display: s.display, visibility: s.visibility, transform: s.transform };
      }),
      childCount: box.children.length,
    };
  })()`);
  console.log("INITIAL (top of page):");
  console.log(JSON.stringify(info, null, 2));

  // Scroll in increments and report active step + visualization state
  const results = [];
  const totalH = await evaluate(`document.documentElement.scrollHeight`);
  console.log("TOTAL PAGE HEIGHT:", totalH);
  for (let i = 0; i <= 10; i++) {
    const y = Math.round(totalH * (i / 10));
    await evaluate(`(function(){document.documentElement.style.scrollBehavior='auto';document.body.style.scrollBehavior='auto';window.scrollTo({top:${y},behavior:'instant'});document.documentElement.scrollTop=${y};document.body.scrollTop=${y};return window.scrollY;})()`);
    await evaluate("new Promise(r => setTimeout(r, 700))");
    const r = await evaluate(`(() => {
      const section = document.getElementById('solutions');
      const box = section ? section.querySelector('[class*="aspect-[4/3]"]') : null;
      const all = [...(section ? section.querySelectorAll('[class*="absolute inset-0"][class*="flex flex-col justify-center"]') : [])];
      const active = all.findIndex(el => getComputedStyle(el).opacity === '1');
      let nodeInfo = [];
      if (box) {
        const spans = [...box.querySelectorAll('span')].filter(s => ['Gmail','AI','Drive','Slack'].includes(s.textContent.trim()));
        nodeInfo = spans.map(s => {
          const wrap = s.closest('[class*="-translate-x-1/2"]');
          return { text: s.textContent.trim(), opacity: getComputedStyle(wrap).opacity, top: getComputedStyle(wrap).top };
        });
      }
      return {
        scrollY: window.scrollY,
        activeStep: active,
        boxExists: !!box,
        visibleNodes: nodeInfo.filter(n => parseFloat(n.opacity) > 0.5).map(n => n.text),
        nodeOps: nodeInfo.map(n => n.text + ':' + n.opacity),
      };
    })()`);
    results.push(r);
  }

  console.log("SCROLL STEPS:");
  console.log(JSON.stringify(results, null, 2));

  const secInfo = await evaluate(`(() => {
    const s = document.getElementById('solutions');
    const r = s.getBoundingClientRect();
    return { top: r.top + window.scrollY, height: r.height, viewport: window.innerHeight };
  })()`);
  console.log("SECTION:", JSON.stringify(secInfo));

  const out = [];
  for (let st = 0; st <= 5; st++) {
    const target = Math.round(secInfo.top + (st / 5) * 0.96 * (secInfo.height - secInfo.viewport));
    await evaluate(`(function(){document.documentElement.style.scrollBehavior='auto';document.body.style.scrollBehavior='auto';window.scrollTo({top:${target},behavior:'instant'});document.documentElement.scrollTop=${target};document.body.scrollTop=${target};return true;})()`);
    await evaluate("new Promise(r => setTimeout(r, 900))");
    const r = await evaluate(`(() => {
      const s = document.getElementById('solutions');
      // All 6 step containers (absolute inset-0 with aria-hidden)
      const stepEls = [...s.querySelectorAll('[aria-hidden]')].filter(el => el.className && String(el.className).includes('absolute inset-0'));
      const stepsState = stepEls.map(el => ({
        aria: el.getAttribute('aria-hidden'),
        opacity: getComputedStyle(el).opacity,
        title: (el.querySelector('h3') ? el.querySelector('h3').getAttribute('aria-label') : ''),
      }));
      const box = s.querySelector('[class*="aspect-[4/3]"]');
      const nodeOps = [];
      const nodeTops = [];
      if (box) {
        const spans = [...box.querySelectorAll('span')].filter(x => ['Gmail','AI','Drive','Slack'].includes(x.textContent.trim()));
        for (const sp of spans) {
          const wrap = sp.closest('[class*="-translate-x-1/2"]');
          nodeOps.push(sp.textContent.trim() + '=' + getComputedStyle(wrap).opacity);
          nodeTops.push(sp.textContent.trim() + '@' + getComputedStyle(wrap).top);
        }
      }
      return {
        scrollY: Math.round(window.scrollY),
        target: ${target},
        stepsState,
        nodeOps,
        nodeTops,
      };
    })()`);
    out.push(r);
  }
  console.log("PER-STEP DATA:");
  console.log(JSON.stringify(out, null, 2));

  chrome.kill();
  process.exit(0);
}

main().catch((e) => {
  console.error("FAILED:", e.message);
  try { chrome.kill(); } catch {}
  process.exit(1);
});
