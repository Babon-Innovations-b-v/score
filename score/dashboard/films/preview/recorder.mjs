// The browser half of films/preview: each recorded segment drawn frame by frame in headless Chromium on its own
// clock (never the wall clock, so a take comes out the same every time), every frame saved as a JPEG. Run through
//   npx -y -p playwright@<pinned> node recorder.mjs <job.json>
// The job: {base, user, size [w, h], scale, rate, scene_js, segments: [{index, kind (take, scene, player), seconds,
// out, captions, pip, ...}]}. Signed in as the owner by the trusted proxy's header; every request that is not a GET is
// aborted and a click on a button that spends refuses the whole take (takes.py). Prints one JSON line a segment.
import { createRequire } from "node:module";
import { mkdirSync, readFileSync } from "node:fs";
import path from "node:path";

const bin = process.env.PATH.split(":").find((part) => part.includes("_npx") && part.endsWith(".bin"));
const { chromium } = createRequire(import.meta.url)(path.join(bin, "..", "playwright"));
const job = JSON.parse(readFileSync(process.argv[2], "utf8"));
const [WIDE, TALL] = job.size;
const SPEND = new RegExp(job.spend, "i");
const STILL = "*, *::before, *::after { transition: none !important; animation: none !important; caret-color: transparent !important; }" +
  " html { scrollbar-width: none; } ::-webkit-scrollbar { display: none; }";

const clamp01 = (value) => Math.max(0, Math.min(1, value));
// How far a screen take's page slowly closes in over the take (a held shot's drift; the page itself, never the words over it).
const DRIFT = 0.03;
const eased = (value) => { const share = clamp01(value); return share * share * (3 - 2 * share); };

// --- the overlay: caption, picture-in-picture, cursor and highlight boxes, drawn over any page ----------------------

function drawOverlay(state) {
  if (state.drift) {  // the page closes in about the middle of what shows; the overlay is outside the body, so it stays
    document.body.style.transformOrigin = `${window.scrollX + window.innerWidth / 2}px ${window.scrollY + window.innerHeight / 2}px`;
    document.body.style.transform = `scale(${state.drift})`;
  }
  let layer = document.getElementById("film-overlay");
  if (!layer) {
    layer = document.createElement("div");
    layer.id = "film-overlay";
    layer.innerHTML = `<style>
      #film-overlay { position: fixed; inset: 0; z-index: 2147483647; pointer-events: none; font-family: Poppins, system-ui, sans-serif; }
      #film-overlay .box { position: fixed; border: 3px solid #b99cff; border-radius: 10px; box-shadow: 0 0 0 9999px rgba(8, 9, 14, .28), 0 0 24px rgba(185, 156, 255, .55); }
      #film-overlay .box b { position: absolute; left: -3px; top: -34px; background: #b99cff; color: #120d1f; font-size: 15px; font-weight: 600; padding: 4px 10px; border-radius: 8px; white-space: nowrap; }
      #film-overlay .caption { position: fixed; left: 48px; bottom: 44px; max-width: 62%; background: rgba(10, 11, 16, .82); border-left: 4px solid #b99cff; border-radius: 10px; padding: 14px 22px; color: #f4f2fa; box-shadow: 0 10px 40px rgba(0, 0, 0, .45); }
      #film-overlay .caption small { display: block; font-size: 13px; letter-spacing: .14em; text-transform: uppercase; color: #b99cff; margin-bottom: 4px; font-weight: 600; }
      #film-overlay .caption span { font-size: 25px; font-weight: 600; line-height: 1.25; }
      #film-overlay .pip { position: fixed; width: 30%; border-radius: 12px; overflow: hidden; border: 3px solid rgba(244, 242, 250, .9); box-shadow: 0 14px 44px rgba(0, 0, 0, .55); background: #0a0b10; }
      #film-overlay .pip img { display: block; width: 100%; aspect-ratio: 16 / 9; object-fit: cover; }
      #film-overlay .pip i { position: absolute; left: 10px; top: 8px; font-style: normal; font-size: 12px; letter-spacing: .12em; text-transform: uppercase; font-weight: 600; color: #f4f2fa; background: rgba(10, 11, 16, .75); padding: 3px 9px; border-radius: 6px; }
      #film-overlay .cursor { position: fixed; width: 28px; height: 28px; margin: -3px 0 0 -4px; filter: drop-shadow(0 2px 4px rgba(0,0,0,.6)); }
      #film-overlay .ring { position: fixed; border: 3px solid #b99cff; border-radius: 50%; }
    </style><div class="boxes"></div><div class="ring" hidden></div><div class="pip" hidden><img alt=""><i></i></div>
    <div class="caption" hidden><small></small><span></span></div>
    <svg class="cursor" hidden viewBox="0 0 24 24"><path d="M3 2 L3 19 L8 14.5 L11.5 22 L14.5 20.6 L11 13.3 L17.5 13.3 Z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>`;
    document.documentElement.append(layer);
  }
  const zoom = String(state.k || 1);  // a take on a wider page: its words and corner picture kept at the film's size
  for (const kept of layer.querySelectorAll(".caption, .pip, .box b")) kept.style.zoom = zoom;
  const boxes = layer.querySelector(".boxes");
  boxes.replaceChildren();
  for (const box of state.boxes) {
    const found = document.querySelector(box.on);
    if (!found) continue;
    const rect = found.getBoundingClientRect(), pad = 6;
    const shown = document.createElement("div");
    shown.className = "box";
    Object.assign(shown.style, { left: `${rect.left - pad}px`, top: `${rect.top - pad}px`, width: `${rect.width + 2 * pad}px`,
      height: `${rect.height + 2 * pad}px`, opacity: String(box.alpha) });
    if (box.words) { const label = document.createElement("b"); label.textContent = box.words; shown.append(label); }
    boxes.append(shown);
  }
  const caption = layer.querySelector(".caption");
  caption.hidden = !state.caption;
  if (state.caption) {
    caption.querySelector("small").textContent = state.caption.line || "";
    caption.querySelector("small").hidden = !state.caption.line;
    caption.querySelector("span").textContent = state.caption.text || "";
    caption.style.opacity = String(state.caption.alpha);
    caption.style.transform = `translateY(${(1 - state.caption.alpha) * 12}px)`;
  }
  const pip = layer.querySelector(".pip");
  pip.hidden = !state.pip;
  if (state.pip) {
    const image = pip.querySelector("img");
    if (image.getAttribute("src") !== state.pip.url) image.src = state.pip.url;
    pip.querySelector("i").textContent = state.pip.label || "";
    const [vertical, horizontal] = state.pip.corner.split("-");
    Object.assign(pip.style, { top: vertical === "top" ? "32px" : "", bottom: vertical === "bottom" ? "32px" : "",
      left: horizontal === "left" ? "32px" : "", right: horizontal === "right" ? "32px" : "",
      opacity: String(state.pip.alpha), transform: `scale(${0.94 + 0.06 * state.pip.alpha})` });
  }
  const cursor = layer.querySelector(".cursor");
  cursor.style.display = state.cursor ? "" : "none";  // an svg has no `hidden` property
  if (state.cursor) Object.assign(cursor.style, { left: `${state.cursor.x}px`, top: `${state.cursor.y}px`,
    transform: `scale(${(state.k || 1) * (state.cursor.down ? 0.86 : 1)})`, transformOrigin: "4px 3px" });
  const ring = layer.querySelector(".ring");
  ring.hidden = !state.ring;
  if (state.ring) {
    const size = 16 + 46 * state.ring.share;
    Object.assign(ring.style, { left: `${state.ring.x - size / 2}px`, top: `${state.ring.y - size / 2}px`, width: `${size}px`,
      height: `${size}px`, opacity: String(1 - state.ring.share) });
  }
  const pictures = [...document.images, pip.querySelector("img")].filter((image) => image.src && !image.complete);
  return Promise.race([Promise.all(pictures.map((image) => new Promise((done) => {
    image.addEventListener("load", done, { once: true }); image.addEventListener("error", done, { once: true });
  }))), new Promise((done) => setTimeout(done, 8000))]).then(() => document.fonts.ready).then(() => true);
}

// What a segment's captions and picture-in-picture show at `local` seconds.
function wordsAt(segment, local) {
  const caption = (segment.captions || []).find((one) => one.from <= local && local < one.to);
  const fade = (one) => Math.min(clamp01((local - one.from) / 0.4), clamp01((one.to - local) / 0.4));
  const pip = segment.pip && segment.pip.from <= local && local < segment.pip.to ? segment.pip : null;
  return { caption: caption ? { ...caption, alpha: fade(caption) } : null,
           pip: pip ? { ...pip, alpha: fade(pip) } : null };
}

async function save(page, segment, frame) {
  await page.screenshot({ path: path.join(segment.out, `${String(frame).padStart(5, "0")}.jpg`), type: "jpeg", quality: 92 });
}

// --- a screen take ----------------------------------------------------------------------------------------------

// The element's box in the viewport, or a refusal when it is not on the page.
async function boxOf(page, selector, number) {
  const rect = await page.evaluate((on) => {
    const found = document.querySelector(on);
    if (!found) return null;
    const box = found.getBoundingClientRect();
    return { x: box.left, y: box.top, width: box.width, height: box.height };
  }, selector);
  if (!rect) throw new Error(`segment ${number}: no element ${selector} on the page`);
  return rect;
}

function pointIn(rect, share = [0.5, 0.5]) {
  return { x: rect.x + rect.width * share[0], y: rect.y + rect.height * share[1] };
}

// Refuse a click on a button that spends: one that posts a form, names a price or carries a spend word.
async function refusal(page, point) {
  return page.evaluate(({ x, y, spend }) => {
    const hit = document.elementFromPoint(x, y);
    if (!hit) return null;
    const target = hit.closest("button, a, input, select, summary, label, [role=button], [data-yes], [data-url]") || hit;
    const words = [target.innerText, target.value, target.title, target.getAttribute("aria-label")].filter(Boolean).join(" ");
    const form = target.closest("form");
    const posts = form && (form.getAttribute("method") || "").toLowerCase() === "post" &&
      (target.tagName === "BUTTON" || target.type === "submit");
    const yes = target.closest("[data-yes], form[data-yes]");
    if (posts || yes || (target.matches("button, input, [role=button]") && new RegExp(spend, "i").test(words))) {
      return `${target.tagName.toLowerCase()} "${words.trim().slice(0, 60)}"`;
    }
    return null;
  }, { ...point, spend: job.spend });
}

async function settle(page) {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.addStyleTag({ content: STILL }).catch(() => {});
}

async function take(context, segment) {
  const page = await context.newPage();
  const k = (segment.view || WIDE) / WIDE;  // `view`: the page's width in CSS pixels, its height the film's shape
  if (segment.view) await page.setViewportSize({ width: segment.view, height: Math.round(segment.view * TALL / WIDE) });
  await page.goto(job.base + segment.page, { waitUntil: "networkidle" });
  await settle(page);
  const frames = Math.round(segment.seconds * job.rate);
  const steps = (segment.take || []).map((step) => ({ ...step, started: false, done: false }));
  let cursor = { x: WIDE * k * 0.62, y: TALL * k * 0.7, down: false }, ring = null, shown = false;
  for (let frame = 0; frame < frames; frame++) {
    const local = frame / job.rate;
    const boxes = [];
    for (const step of steps) {
      if (local < step.at || step.done) continue;
      const share = step.over ? clamp01((local - step.at) / step.over) : 1;
      if (!step.started) {
        step.started = true;
        step.origin = { ...cursor };
        if (step.on && step.do !== "box") step.rect = await boxOf(page, step.on, segment.index);
        if (step.do === "scroll") {
          step.top = await page.evaluate(() => window.scrollY);
          step.bottom = step.on ? await page.evaluate((on) => {
            const box = document.querySelector(on).getBoundingClientRect();
            return Math.max(0, window.scrollY + box.top + box.height / 2 - window.innerHeight / 2);
          }, step.on) : step.y || 0;
        }
        if (step.do === "type") await page.evaluate((on) => document.querySelector(on).focus(), step.on);
        if (step.do === "drag") {
          const start = pointIn(step.rect, step.from);
          await page.mouse.move(start.x, start.y);
          await page.mouse.down();
          step.typedFrom = start;
        }
      }
      if (step.do === "move" || step.do === "hover") {
        const target = pointIn(step.rect, step.to);
        cursor = { x: step.origin.x + (target.x - step.origin.x) * eased(share), y: step.origin.y + (target.y - step.origin.y) * eased(share), down: false };
        await page.mouse.move(cursor.x, cursor.y);
      } else if (step.do === "click" && !step.done) {
        const target = pointIn(step.rect, step.to);
        const refused = await refusal(page, target);
        if (refused) throw new Error(`refused: segment ${segment.index} clicks ${refused}: a take never clicks a button that spends`);
        cursor = { ...target, down: true };
        ring = { ...target, at: local };
        await page.mouse.click(target.x, target.y);
        await settle(page);
      } else if (step.do === "drag") {
        const start = step.typedFrom, end = pointIn(step.rect, step.to);
        cursor = { x: start.x + (end.x - start.x) * eased(share), y: start.y + (end.y - start.y) * eased(share), down: share < 1 };
        await page.mouse.move(cursor.x, cursor.y);
        if (share >= 1 && !step.done) await page.mouse.up();
      } else if (step.do === "type") {
        const want = Math.round(share * step.text.length), typed = step.typed || 0;
        if (want > typed) await page.keyboard.type(step.text.slice(typed, want));
        step.typed = want;
      } else if (step.do === "scroll") {
        await page.evaluate((y) => window.scrollTo(0, y), step.top + (step.bottom - step.top) * eased(share));
      } else if (step.do === "goto" && !step.done) {
        await page.goto(job.base + step.page, { waitUntil: "networkidle" });
        await settle(page);
      } else if (step.do === "box") {
        const left = step.at + (step.for || 1.5) - local;
        if (left <= 0) { step.done = true; continue; }
        boxes.push({ on: step.on, words: step.words, alpha: Math.min(clamp01((local - step.at) / 0.3), clamp01(left / 0.3)) });
        continue;
      }
      if (share >= 1) step.done = true;
    }
    if (cursor.down && !steps.some((step) => step.do === "drag" && step.started && !step.done) && (!ring || local - ring.at > 0.15)) cursor.down = false;
    const ringShown = ring && local - ring.at < 0.5 ? { x: ring.x, y: ring.y, share: (local - ring.at) / 0.5 } : null;
    shown = shown || steps.some((step) => step.started && ["move", "hover", "click", "drag"].includes(step.do));
    await page.evaluate(drawOverlay, { ...wordsAt(segment, local), boxes, cursor: shown ? cursor : null, ring: ringShown, k,
      drift: 1 + DRIFT * local / segment.seconds });
    await save(page, segment, frame);
  }
  await page.close();
}

// --- a scene (the setting animation and the scale zoom, scene.js) and the editor's own player -------------------

async function scene(context, segment) {
  const page = await context.newPage();
  page.on("pageerror", (error) => console.error(`segment ${segment.index}: ${error.message}`));
  await page.route(`${job.base}/__film/**`, (route) => {
    const name = new URL(route.request().url()).pathname.split("/").pop();
    if (name === "scene.html") return route.fulfill({ contentType: "text/html", body: job.scene_html });
    return route.fulfill({ contentType: "text/javascript", body: readFileSync(job.scene_js) });
  });
  await page.goto(`${job.base}/__film/scene.html`, { waitUntil: "load" });
  await page.waitForFunction(() => window.filmScene !== undefined, null, { timeout: 60000 });
  await page.evaluate((data) => window.filmScene.setup(data), { ...segment.scene, size: job.size });
  const frames = Math.round(segment.seconds * job.rate);
  for (let frame = 0; frame < frames; frame++) {
    const local = frame / job.rate;
    await page.evaluate((at) => window.filmScene.draw(at), local);
    await page.evaluate(drawOverlay, { ...wordsAt(segment, local), boxes: [], cursor: null, ring: null });
    await save(page, segment, frame);
  }
  await page.close();
}

async function player(context, segment) {
  const page = await context.newPage();
  await page.goto(job.base + segment.page, { waitUntil: "networkidle" });
  // The stage over the whole viewport: its screen's size container (film.css) would hold a fixed child inside it.
  await page.addStyleTag({ content: `${STILL} .film-screen { container-type: normal !important; } #stage { position: fixed !important; inset: 0 !important; width: auto !important; z-index: 2147483000; border-radius: 0 !important; }` });
  const frames = Math.round(segment.seconds * job.rate);
  for (let frame = 0; frame < frames; frame++) {
    const local = frame / job.rate;
    await page.evaluate((at) => window.filmPlayer.seek(at), segment.start + local);
    await page.waitForFunction(() => document.getElementById("wait").hidden, null, { timeout: 120000 });
    await page.evaluate((at) => window.filmPlayer.seek(at), segment.start + local);
    await page.evaluate(drawOverlay, { ...wordsAt(segment, local), boxes: [], cursor: null, ring: null });
    await save(page, segment, frame);
  }
  await page.close();
}

const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const context = await browser.newContext({ viewport: { width: WIDE, height: TALL }, deviceScaleFactor: job.scale,
  extraHTTPHeaders: { "Remote-User": job.user } });
const refused = [];
await context.route("**/*", (route) => {
  const asked = route.request();
  if (asked.method() === "GET" || asked.method() === "HEAD") return route.fallback();
  refused.push(`${asked.method()} ${asked.url()}`);
  return route.abort();
});
const makers = { take, scene, player };
let failed = false;
for (const segment of job.segments) {
  mkdirSync(segment.out, { recursive: true });
  const before = refused.length;
  try {
    await makers[segment.kind](context, segment);
    if (refused.length > before) throw new Error(`refused: segment ${segment.index} sent ${refused.slice(before).join(", ")}`);
    console.log(JSON.stringify({ segment: segment.index, frames: Math.round(segment.seconds * job.rate), out: segment.out }));
  } catch (error) {
    console.log(JSON.stringify({ segment: segment.index, error: error.message }));
    failed = true;
    break;
  }
}
await browser.close();
process.exit(failed ? 1 : 0);
