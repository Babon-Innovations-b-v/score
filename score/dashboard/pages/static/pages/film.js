// The FILM page (score/dashboard/films): the film script's editor and its free preview, a cockpit like the design
// page (one screen: the player and the storyboard as panels, the chosen segment's editor, the cost and the lock in
// the rail). The editor keeps the script as the JSON it is saved as, saved on its own after every change; the preview
// plays it on the places' 3D web copies (/web/<place>/), their accepted films, the pictures their steps made and the
// rendered free preview's takes, with three.js for the walk-throughs, orbits, exploded views, isolates, layer focus
// and layer splits. Nothing here is rendered on a paid machine.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { token as designToken } from "./tokens.js";  // token() here is the CSRF token

const given = JSON.parse(document.getElementById("film-data").textContent);
const doc = given.script;
const $ = (id) => document.getElementById(id);
const WIDTH = 960, HEIGHT = 540;
const GHOST = 0.1, WALK_SPEED = 0.6, CAPTION_IN = 0.4, SAVE_AFTER = 700;
const STEP_ORDER = [...Object.keys(given.steps), "place"];
let selected = 0, dirty = false, answer = given.answer;

function element(tag, className, text) {
  const made = document.createElement(tag);
  if (className) made.className = className;
  if (text !== undefined) made.textContent = text;
  return made;
}

const eased = (share) => 0.5 - 0.5 * Math.cos(Math.PI * Math.min(1, Math.max(0, share)));
const clamp01 = (value) => Math.min(1, Math.max(0, value));

function clockWords(seconds) {
  const whole = Math.max(0, seconds);
  return `${Math.floor(whole / 60)}:${(whole % 60).toFixed(1).padStart(4, "0")}`;
}

// --- the script's clock (score/dashboard/films/script.py timeline, the same rules) ------------------------------

function defaultSeconds(cut) {
  const own = (doc.defaults || {})[cut];
  return Number(own !== undefined ? own : given.cuts[cut].seconds);
}

function secondsOf(segment) {
  return segment.seconds !== undefined && segment.seconds !== null ? Number(segment.seconds) : defaultSeconds(segment.cut);
}

function overlapOf(index, segment) {
  return index > 0 && ["cross-fade", "push"].includes(segment.transition) ? given.transition_seconds : 0;
}

function timeline() {
  const found = [];
  let clock = 0;
  doc.segments.forEach((segment, index) => {
    const start = Math.max(0, clock - overlapOf(index, segment));
    const length = secondsOf(segment);
    found.push({ start, length, end: start + length });
    clock = start + length;
  });
  return found;
}

const totalSeconds = () => timeline().reduce((most, slot) => Math.max(most, slot.end), 0);

// --- the storyboard ---------------------------------------------------------------------------------------------

function placeOf(segment) { return (segment.shows || {}).place; }
function mediaOf(place) { return given.places[place] || null; }
const placeName = (place) => (mediaOf(place) ? mediaOf(place).words : (given.shells || {})[place] || place);

// What a segment shows, in a few words: its scene, its page's section, its card's words.
function segmentWords(segment) {
  const shows = segment.shows || {};
  const where = shows.place ? placeName(shows.place) : null;
  if (segment.cut === "title" || segment.cut === "text") return segment.text || given.cuts[segment.cut].label;
  if (segment.cut === "screen-take") {
    const first = (segment.captions || [])[0];
    return first ? first.line.replace(/^\d+\s*·\s*/, "") : shows.page || "a page";
  }
  if (segment.cut === "setting-animation") return "the physics";
  if (segment.cut === "scale-zoom") return `down to ${where || "a scene"}`;
  if (!where) return "choose a scene";
  if (segment.cut === "step-card") return `${where}: ${given.steps[shows.step] || "a step"}`;
  if (segment.cut === "layer-focus") return `${where}: ${shows.layer || "a layer"}`;
  if (segment.cut === "isolate") return `${where}: ${(shows.part || "a part").split("/").pop()}`;
  return where;
}

// The rendered free preview's take of a segment: the preview's segment that is this very one (any place in it).
function previewIndex(segment) {
  const preview = given.preview;
  if (!preview) return -1;
  const wanted = stable(segment);
  return preview.script.segments.findIndex((then) => stable(then) === wanted);
}

// Thumbnails: a frame from the middle of each segment's take in the rendered preview, else the scene's hero picture.
const thumbs = new Map();
let thumbVideo = null, thumbQueue = Promise.resolve();
function thumbOf(segment) {
  const index = previewIndex(segment);
  if (index < 0) { const media = mediaOf(placeOf(segment)); return Promise.resolve(media && media.hero ? media.hero.thumb : null); }
  if (!thumbs.has(index)) {
    thumbs.set(index, thumbQueue = thumbQueue.then(() => new Promise((resolve) => {
      thumbVideo = thumbVideo || Object.assign(element("video"), { muted: true, preload: "metadata", src: given.preview.url });
      const slot = given.preview.segments[index];
      const grab = () => {
        const canvas = element("canvas");
        canvas.width = 320;
        canvas.height = 180;
        canvas.getContext("2d").drawImage(thumbVideo, 0, 0, 320, 180);
        resolve(canvas.toDataURL("image/jpeg", 0.8));
      };
      thumbVideo.addEventListener("seeked", grab, { once: true });
      thumbVideo.addEventListener("error", () => resolve(null), { once: true });
      thumbVideo.currentTime = slot.start + Math.min(slot.seconds * 0.5, 3);
    })));
  }
  return thumbs.get(index);
}

// A segment's faults the page can tell at once (the server's check says the rest when it saves).
function wants(segment) {
  const cut = given.cuts[segment.cut], shows = segment.shows || {};
  return cut.needs.filter((need) => need !== "world" && !shows[need]).map((need) => `choose its ${need === "place" ? "scene" : need}`);
}

function drawTimeline() {
  const holder = $("timeline");
  const slots = timeline(), editable = given.can_save && !given.locked;
  $("board-count").textContent = `${doc.segments.length} segments`;
  holder.replaceChildren(...doc.segments.map((segment, index) => {
    const card = element("button", "film-card" + (index === selected ? " on" : "") + (index === player.highlighted ? " playing" : ""));
    card.type = "button";
    card.dataset.cut = segment.cut;
    card.draggable = editable;
    const frame = element("span", "film-card-pic");
    frame.append(element("span", "film-card-num", String(index + 1)), element("span", "film-card-len", `${slots[index].length.toFixed(1).replace(/\.0$/, "")} s`));
    thumbOf(segment).then((url) => { if (url) frame.style.backgroundImage = `url("${url}")`; });
    const missing = wants(segment);
    if (missing.length) { card.classList.add("wants"); card.title = missing.join(", "); }
    else if (segment.waiting) card.title = `stands in until made: ${segment.waiting}`;
    card.append(frame, element("b", "film-card-cut", given.cuts[segment.cut].label), element("span", "film-card-scene", segmentWords(segment)));
    card.onclick = () => choose(index);
    if (editable) {
      card.ondragstart = (event) => { event.dataTransfer.setData("text/plain", String(index)); card.classList.add("dragged"); };
      card.ondragend = () => card.classList.remove("dragged");
      card.ondragover = (event) => { event.preventDefault(); card.classList.add("over"); };
      card.ondragleave = () => card.classList.remove("over");
      card.ondrop = (event) => { event.preventDefault(); moveSegment(Number(event.dataTransfer.getData("text/plain")), index); };
    }
    return card;
  }));
  holder.querySelector(".film-card.on")?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function choose(index) {
  selected = index;
  drawTimeline();
  drawInspector();
  player.seek(timeline()[index].start + given.transition_seconds);
}

function changed() {
  dirty = true;
  drawTimeline();
  drawLength();
  player.reset();
  if (given.can_save && !given.locked) saveSoon(); else compileSoon();
}

function drawLength() {
  const total = totalSeconds(), target = Number(doc.target_seconds || 0);
  const box = $("length");
  box.replaceChildren(element("b", "", clockWords(total)));
  box.title = target ? `the film's length against its target of ${clockWords(target)}` : "the film's length";
  if (!target) return;
  box.append(element("span", "soft", ` of ${clockWords(target)}`));
  const meter = element("span", "film-meter" + (total > target + 1e-6 ? " over" : ""));
  const fill = element("i");
  fill.style.width = `${Math.min(100, 100 * total / target)}%`;
  meter.append(fill);
  box.append(meter);
  if (total > target + 1e-6) box.append(element("span", "small bad", `${(total - target).toFixed(1)} s over`));
}

function moveSegment(from, to) {
  if (from === to || Number.isNaN(from)) return;
  const [moved] = doc.segments.splice(from, 1);
  doc.segments.splice(to, 0, moved);
  selected = to;
  changed();
  drawInspector();
}

// --- the segment editor (the rail) ------------------------------------------------------------------------------

function field(label, control) {
  const row = element("label", "film-field");
  row.append(element("span", "", label), control);
  return row;
}

function choice(options, value, onPick) {
  const select = element("select");
  for (const [key, words] of options) {
    const option = element("option", "", words);
    option.value = key;
    option.selected = key === value;
    select.append(option);
  }
  select.onchange = () => onPick(select.value);
  return select;
}

function textInput(value, onType, placeholder) {
  const input = element("input");
  input.type = "text";
  input.value = value || "";
  if (placeholder) input.placeholder = placeholder;
  input.oninput = () => onType(input.value);
  return input;
}

function placeOptions(cut) {
  const scenes = Object.values(given.places).map((media) => [media.place, media.words + (media.web3d || cut !== "walk-through" ? "" : " (no 3D copy)")]);
  const shells = cut === "scale-zoom" ? Object.entries(given.shells || {}) : [];
  return [...shells, ...scenes].sort((one, other) => one[1].localeCompare(other[1]));
}

async function sidecarOf(place) {
  if (!place || !mediaOf(place) || !mediaOf(place).web3d) return null;
  sidecarOf.cache = sidecarOf.cache || {};
  if (!sidecarOf.cache[place]) {
    sidecarOf.cache[place] = fetch(`/web/${place}/${place}.json`, { credentials: "same-origin" })
      .then((reply) => (reply.ok ? reply.json() : null)).catch(() => null);
  }
  return sidecarOf.cache[place];
}

function setShows(segment, key, value) {
  segment.shows = segment.shows || {};
  if (value) segment.shows[key] = value; else delete segment.shows[key];
  changed();
}

async function cameraField(segment) {
  const sidecar = await sidecarOf(placeOf(segment));
  const views = (sidecar && sidecar.cameras) || [];
  if (!views.length) return null;
  return field("Camera", choice([["", "the film's own start"], ...views.map((view) => [view.name, view.name])], segment.camera || "", (value) => {
    if (value) segment.camera = value; else delete segment.camera;
    changed();
  }));
}

async function partField(segment) {
  const sidecar = await sidecarOf(placeOf(segment));
  const names = ((sidecar && sidecar.objects) || []).map((part) => part.name).sort();
  const list = element("datalist");
  list.id = "film-parts";
  list.append(...names.map((name) => { const option = element("option"); option.value = name; return option; }));
  const input = textInput(segment.shows.part, (value) => setShows(segment, "part", value), "Objects/...");
  input.setAttribute("list", "film-parts");
  const row = field("Part", input);
  row.append(list);
  return row;
}

function layerField(segment) {
  const media = mediaOf(placeOf(segment));
  const layers = (media && media.layers) || [];
  return field("Layer", choice([["", "choose a layer"], ...layers.map((name) => [name, name])], segment.shows.layer || "",
                               (value) => setShows(segment, "layer", value)));
}

function stepField(segment) {
  return field("Step", choice([["", "choose a step"], ...Object.entries(given.steps)], segment.shows.step || "",
                              (value) => { setShows(segment, "step", value); loadPictures(placeOf(segment)); }));
}

function filmField(segment) {
  const media = mediaOf(placeOf(segment));
  const extras = Object.keys((media && media.extras) || {});
  if (!extras.length) return null;
  return field("Film", choice([["", "the scene's own"], ...extras.map((name) => [name, name])], segment.shows.film || "",
                              (value) => setShows(segment, "film", value)));
}

// A scale zoom's legs keep their shares of its length (the script check holds them equal to it).
function setLength(segment, value) {
  if (segment.legs && segment.legs.length) {
    const was = segment.legs.reduce((sum, leg) => sum + leg.seconds, 0) || value;
    segment.legs.forEach((leg) => { leg.seconds = Math.round(leg.seconds * value / was * 100) / 100; });
    const drift = value - segment.legs.reduce((sum, leg) => sum + leg.seconds, 0);
    segment.legs[segment.legs.length - 1].seconds = Math.round((segment.legs[segment.legs.length - 1].seconds + drift) * 100) / 100;
  }
  segment.seconds = value;
}

function lengthField(segment) {
  const input = element("input");
  input.type = "number";
  input.min = "0.5";
  input.max = "60";
  input.step = "0.5";
  input.value = String(secondsOf(segment));
  input.onchange = () => {
    const value = Number(input.value);
    if (value >= 0.5 && value <= 60) { setLength(segment, value); changed(); }
  };
  return field("Length, seconds", input);
}

// The words on screen: a card's title and line; a recorded cut's timed captions; any other cut's caption.
function wordFields(segment) {
  if (segment.captions && segment.captions.length) {
    const box = element("div", "film-captions");
    box.append(element("span", "film-field-label", "Words on screen"));
    segment.captions.forEach((caption) => {
      const pair = element("div", "film-caption-pair");
      pair.title = `on screen from ${caption.from} s to ${caption.to} s`;
      pair.append(textInput(caption.line, (value) => { caption.line = value; changed(); }, "small line"),
                  textInput(caption.text, (value) => { caption.text = value; changed(); }, "words"));
      box.append(pair);
    });
    return [box];
  }
  const card = segment.cut === "title" || segment.cut === "text";
  return [field(card ? "Words" : "Words on screen", textInput(segment.text, (value) => { segment.text = value || undefined; changed(); })),
          field(card ? "Second line" : "Small line above", textInput(segment.line, (value) => { segment.line = value || undefined; changed(); }))];
}

function segmentButtons(segment) {
  const row = element("div", "film-buttons");
  const actions = [["Earlier", "move it one earlier", () => moveSegment(selected, Math.max(0, selected - 1))],
                   ["Later", "move it one later", () => moveSegment(selected, Math.min(doc.segments.length - 1, selected + 1))],
                   ["Copy", "a copy after it", () => { doc.segments.splice(selected + 1, 0, JSON.parse(JSON.stringify(segment))); selected += 1; changed(); drawInspector(); }],
                   ["Remove", "take it out of the film", () => { doc.segments.splice(selected, 1); selected = Math.max(0, Math.min(selected, doc.segments.length - 1)); changed(); drawInspector(); }]];
  for (const [words, tip, act] of actions) {
    const button = element("button", words === "Remove" ? "tool danger" : "tool", words);
    button.type = "button";
    button.title = tip;
    button.onclick = act;
    row.append(button);
  }
  return row;
}

async function drawInspector() {
  const box = $("inspector");
  const segment = doc.segments[selected];
  if (!segment) { box.replaceChildren(element("p", "soft small", "No segment yet: add one from the storyboard.")); return; }
  segment.shows = segment.shows || {};
  const cut = given.cuts[segment.cut];
  const head = element("div", "film-inspector-head");
  head.append(element("span", "num-label", `segment ${selected + 1} of ${doc.segments.length}`));
  const name = element("h2", "film-cut-name", cut.label);
  name.title = cut.words;
  const parts = [head, name];
  if (segment.cut === "setting-animation" || segment.cut === "title" || segment.cut === "text") { /* no scene */ }
  else if (cut.needs.includes("place")) {
    const options = placeOptions(segment.cut);
    parts.push(field("Scene", choice(placeOf(segment) ? options : [["", "choose a scene"], ...options], placeOf(segment) || "",
                                     (value) => { setShows(segment, "place", value); loadPictures(value); drawInspector(); })));
  }
  if (cut.needs.includes("layer")) parts.push(layerField(segment));
  if (cut.needs.includes("part")) parts.push(await partField(segment));
  if (cut.needs.includes("step")) parts.push(stepField(segment));
  if (segment.cut === "walk-through") { const extra = filmField(segment); if (extra) parts.push(extra); }
  if (cut.needs.includes("page")) {
    const page = field("Page", textInput(segment.shows.page, (value) => { setShows(segment, "page", value); }));
    page.title = `${(segment.take || []).length} recorded steps on this page: the cursor, its clicks and highlights`;
    parts.push(page);
  }
  if (["walk-through", "orbit", "hero-still", "isolate"].includes(segment.cut)) { const camera = await cameraField(segment); if (camera) parts.push(camera); }
  const timing = element("div", "film-field-row");
  timing.append(lengthField(segment),
                field("Transition", choice(Object.entries(given.transitions), segment.transition || "cut",
                                           (value) => { segment.transition = value; changed(); })));
  parts.push(timing, ...wordFields(segment),
             field("Sound", choice(Object.entries(given.sounds), segment.sound || "bed", (value) => { segment.sound = value; changed(); })));
  if (segment.waiting) {
    const note = element("p", "small review", "stands in until made");
    note.title = segment.waiting;
    parts.push(note);
  }
  const fields = element("fieldset", "film-fields");
  fields.disabled = !given.can_save || given.locked;
  fields.append(...parts.slice(2));
  if (!fields.disabled) fields.append(segmentButtons(segment));
  if (doc.segments[selected] === segment) box.replaceChildren(head, name, fields);
}

// --- Add segment: the cut types in plain words, grouped --------------------------------------------------------------

// The scene a new segment shows: the chosen segment's, else the first the film shows, else the first there is.
function nearPlace(cut) {
  if (cut === "scale-zoom") {
    const zoom = doc.segments.find((segment) => segment.cut === "scale-zoom");
    return (zoom && placeOf(zoom)) || Object.keys(given.shells || {})[0] || Object.keys(given.places)[0];
  }
  const shown = [doc.segments[selected], ...doc.segments].map((segment) => segment && placeOf(segment))
    .find((place) => place && mediaOf(place));
  return shown || Object.keys(given.places)[0];
}

function added(key) {
  const entry = given.cuts[key];
  const made = { cut: key, shows: { world: doc.world }, transition: entry.transition, sound: entry.sound, seconds: entry.seconds };
  if (entry.needs.includes("place")) made.shows = { place: nearPlace(key) };
  if (entry.needs.includes("page")) made.shows = { page: `/environments/${doc.world}/` };
  if (key === "scale-zoom") made.legs = given.legs.map((layer) => ({ layer, seconds: entry.seconds / given.legs.length }));
  if (key === "title") made.text = doc.title;
  return made;
}

function drawAdd() {
  const menu = $("add");
  if (!menu) return;
  menu.replaceChildren(...given.groups.map((group) => {
    const box = element("div", "film-add-group");
    box.append(element("span", "num-label", group));
    for (const [key, entry] of Object.entries(given.cuts).filter(([, entry]) => entry.group === group)) {
      const button = element("button", "film-add-cut");
      button.type = "button";
      button.append(element("b", "", entry.label), element("span", "soft small", entry.words));
      button.onclick = () => {
        doc.segments.splice(selected + 1, 0, added(key));
        selected = Math.min(selected + 1, doc.segments.length - 1);
        $("add-menu").open = false;
        changed();
        drawInspector();
      };
      box.append(button);
    }
    return box;
  }));
  $("add-menu").hidden = given.locked;
}

// --- the cost: one line, its detail folded ------------------------------------------------------------------------

const HOW_WORDS = { free: "free", reuse: "free, reuses what exists", basket: "a scene film the basket can buy", new: "to render" };

function euros(value) { return value === null || value === undefined ? "not measured yet" : `EUR ${value.toFixed(2)}`; }

function moneyBar() {
  const box = element("div", "money");
  if (!answer.bar) { box.append(element("div", "soft small", "no reading of this month's spend")); return box; }
  const bar = element("div", "bar");
  const names = { spent: "spent this month", reserved: "in flight", likely: "this film's frames" };
  for (const part of answer.bar) {
    if (part.name === "high") continue;
    const piece = element("span", part.name);
    piece.style.width = `${part.share}%`;
    piece.title = `${names[part.name]}: EUR ${part.euros}`;
    bar.append(piece);
  }
  bar.title = `against the stop, EUR ${Number(answer.ceiling).toFixed(0)}`;
  box.append(bar);
  return box;
}

function drawRender() {
  const totals = answer.totals, items = answer.items;
  const paid = items.filter((entry) => entry.how === "new" || entry.how === "basket").length;
  const free = items.length - paid;
  const line = element("div", "film-cost-line");
  line.append(element("span", "num-label", "render"),
              element("b", "", `${totals.unmeasured.length ? "at least " : ""}EUR ${totals.euros.toFixed(2)}`),
              element("span", "soft small", `${paid} to render, ${free} free`));
  line.title = "the preview is free; rendering is paid and goes through Buy";
  const more = element("details", "film-cost-more");
  more.append(element("summary", "small soft", "detail"));
  const list = element("ul", "film-cost-items");
  for (const entry of items) {
    const row = element("li", entry.how === "new" || entry.how === "basket" ? "film-paid" : "");
    row.append(element("span", "", `${entry.segment}. ${given.cuts[entry.cut].label}`),
               element("span", "soft", entry.frames ? euros(entry.euros) : HOW_WORDS[entry.how]));
    row.title = entry.words + (entry.frames ? `, ${entry.frames} frames` : "");
    row.onclick = () => choose(entry.segment - 1);
    list.append(row);
  }
  const basis = element("p", "small faint", totals.unmeasured.length ? `not measured yet: ${totals.unmeasured.join(", ")}` : "priced from measured frames");
  basis.title = Object.entries(given.measured).map(([kind, found]) => `a ${kind} frame: ${found.from}`).join("\n");
  more.append(list, basis, moneyBar());
  if (totals.basket.length) {
    const ids = element("details", "ids");
    ids.append(element("summary", "", "rows"), element("p", "small", totals.basket.join(", ")));
    more.append(ids);
    const form = $("basket-form");
    if (form) { form.hidden = false; more.append(form); }
  }
  $("render").replaceChildren(line, more);
}

function token() {
  return document.querySelector("#token input[name=csrfmiddlewaretoken]").value;
}

async function post(url) {
  const reply = await fetch(url, { method: "POST", credentials: "same-origin", body: JSON.stringify(doc),
                                   headers: { "Content-Type": "application/json", "X-CSRFToken": token() } });
  return { ok: reply.ok, body: await reply.json() };
}

let compileTimer = null;
function compileSoon() {
  clearTimeout(compileTimer);
  compileTimer = setTimeout(async () => {
    const reply = await post(given.urls.compile);
    if (!reply.ok) { $("said").textContent = (reply.body.faults || []).join("; "); return; }
    $("said").textContent = "";
    answer = reply.body;
    drawRender();
  }, 400);
}

// Autosave, as the plan saves: a moment after the last change, the script as the editor shows it.
let saveTimer = null;
function saveSoon() {
  clearTimeout(saveTimer);
  $("saved").textContent = "saving";
  saveTimer = setTimeout(save, SAVE_AFTER);
}

async function save() {
  const reply = await post(given.urls.save);
  if (!reply.ok) {
    $("saved").textContent = "not saved";
    $("said").textContent = (reply.body.faults || ["not saved"]).join("; ");
    return;
  }
  dirty = false;
  answer = reply.body;
  $("saved").textContent = "saved";
  $("said").textContent = "";
  drawRender();
}

// His Lock posts the script as the editor shows it (also saved as his); Unlock posts nothing. Locked, nothing saves.
async function lockOrUnlock() {
  clearTimeout(saveTimer);
  const reply = await fetch(given.urls.lock, { method: "POST", credentials: "same-origin",
                                               body: JSON.stringify(given.locked ? {} : doc),
                                               headers: { "Content-Type": "application/json", "X-CSRFToken": token() } });
  const body = await reply.json();
  if (!reply.ok) { $("said").textContent = (body.faults || ["refused"]).join("; "); return; }
  given.locked = body.locked;
  dirty = false;
  $("lock").textContent = given.locked ? "Unlock" : "Lock";
  $("lock").className = given.locked ? "button" : "primary";
  $("lock-state").textContent = given.locked ? "locked" : "not locked";
  $("lock-state").className = `status ${given.locked ? "done" : "review"}`;
  $("saved").textContent = given.locked ? "" : "saved";
  $("said").textContent = "";
  drawTimeline();
  drawInspector();
  drawAdd();
}

async function loadPictures(place) {
  if (!place || given.pictures[place]) return;
  const reply = await fetch(`${given.urls.pictures}${place}/`, { credentials: "same-origin" });
  if (reply.ok) given.pictures[place] = await reply.json();
}

window.addEventListener("beforeunload", (event) => { if (dirty && given.can_save && !given.locked) event.preventDefault(); });

// --- the preview: places in 3D ------------------------------------------------------------------------------------

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(WIDTH, HEIGHT, false);
renderer.toneMapping = THREE.AgXToneMapping;  // the films' tone curve
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, WIDTH / HEIGHT, 0.05, 5000);
const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const places = new Map();
let shownPlace = null;

function linear(values) { return new THREE.Color().setRGB(values[0], values[1], values[2], THREE.LinearSRGBColorSpace); }

// GLTFLoader's node names: spaces as underscores, and [ ] . : / dropped (as the 3D viewer, view3d.js).
const loaderName = (name) => name.replace(/\s/g, "_").replace(/[[\].:/]/g, "");

function lightsOf(sidecar) {
  const group = new THREE.Group();
  const sky = sidecar.sky || { background: [0.05, 0.05, 0.05], ambient: [0.5, 0.5, 0.5], exposure: 1 };
  group.add(new THREE.AmbientLight(linear(sky.ambient), 1));
  for (const entry of sidecar.lights || []) {
    const at = new THREE.Vector3(...entry.at), toward = new THREE.Vector3(...entry.toward);
    let made;
    if (entry.type === "directional") {
      made = new THREE.DirectionalLight(linear(entry.colour), entry.intensity);
      made.position.copy(at).addScaledVector(toward, -100);
      made.target.position.copy(at);
    } else if (entry.type === "spot") {
      made = new THREE.SpotLight(linear(entry.colour), entry.intensity, 0, entry.angle, Math.min(entry.penumbra, 1), 2);
      made.position.copy(at);
      made.target.position.copy(at).add(toward);
    } else {
      made = new THREE.PointLight(linear(entry.colour), entry.intensity, 0, 2);
      made.position.copy(at);
    }
    group.add(made);
    if (made.target) group.add(made.target);
  }
  return group;
}

// The backdrop round a place (its sky and haze, the far ground and the sky ball, the places it shows): left standing
// on a walk-through, left out of every other view of the place. The near ground stays (the ground layer), but no
// ground outside counts in the place's size.
const SCENERY = /^(Sky|Places)\/|^Outside\/(far|ball)$/;
const OUTSIDE = /^Outside\//;
// A room's shell (its walls and slabs in one piece): see-through once the room is split apart, so its parts show.
const SHELL = /^Structure\//;

// Each part the sidecar names: its node, its meshes, its box and layer; every mesh with its own material copy so it
// can be ghosted alone.
function partsOf(root, sidecar) {
  const named = new Map(sidecar.objects.map((part) => [loaderName(part.name), part]));
  const parts = [];
  root.updateMatrixWorld(true);
  root.traverse((node) => {
    const own = named.get(node.name) || named.get(node.name.replace(/_\d+$/, ""));
    if (!own || node.userData.part) return;
    node.userData.part = own;
    const meshes = [];
    node.traverse((child) => {
      if (!child.isMesh) return;
      child.material = Array.isArray(child.material) ? child.material.map((one) => one.clone()) : child.material.clone();
      meshes.push(child);
    });
    const box = new THREE.Box3().setFromObject(node);
    parts.push({ node, meshes, layer: own.layer, name: own.name, box, scenery: SCENERY.test(own.name), centre: box.getCenter(new THREE.Vector3()),
                 home: node.position.clone(), toLocal: new THREE.Matrix3().setFromMatrix4(node.parent.matrixWorld.clone().invert()) });
  });
  return parts;
}

async function loadPlace(place) {
  const whole = $("whole").checked;
  const key = `${place}:${whole ? "whole" : "light"}`;
  if (!places.has(key)) {
    places.set(key, (async () => {
      const sidecar = await sidecarOf(place);
      if (!sidecar) throw new Error(`${place} has no 3D copy`);
      const loaded = await loader.loadAsync(`/web/${place}/${place}${whole ? "" : "-light"}.glb`);
      const root = loaded.scene;
      const parts = partsOf(root, sidecar);
      const box = new THREE.Box3();
      for (const part of parts) if (!part.scenery && !OUTSIDE.test(part.name)) box.union(part.box);
      if (box.isEmpty()) box.setFromObject(root);
      return { place, sidecar, root, parts, box, centre: box.getCenter(new THREE.Vector3()),
               size: box.getSize(new THREE.Vector3()), lights: lightsOf(sidecar), markers: new THREE.Group() };
    })());
  }
  return places.get(key);
}

function showPlace(loaded) {
  if (shownPlace === loaded) return;
  if (shownPlace) scene.remove(shownPlace.root, shownPlace.lights, shownPlace.markers);
  shownPlace = loaded;
  scene.add(loaded.root, loaded.lights, loaded.markers);
  const sky = loaded.sidecar.sky || { background: [0.05, 0.05, 0.05], exposure: 1 };
  scene.background = linear(sky.background);
  renderer.toneMappingExposure = sky.exposure;
}

function setOpacity(part, opacity) {
  for (const mesh of part.meshes) {
    mesh.visible = opacity > 0.01;
    for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
      material.transparent = opacity < 0.999;
      material.opacity = opacity;
      material.depthWrite = opacity >= 0.999;
    }
  }
}

function moveBy(part, world) {
  part.node.position.copy(part.home).add(world.clone().applyMatrix3(part.toLocal));
}

function homeAll(loaded) {
  for (const part of loaded.parts) { part.node.position.copy(part.home); setOpacity(part, 1); }
  loaded.markers.clear();
}

// Overhead parts (the roof, the ceiling and what hangs from it): their bottom above OVERHEAD of the place's height.
const OVERHEAD = 0.72;
const overhead = (loaded, part) => part.box.min.y > loaded.box.min.y + OVERHEAD * loaded.size.y && loaded.size.y > 1;

function setAcross(degrees) {
  camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(degrees) / 2) / camera.aspect));
  camera.updateProjectionMatrix();
}

function recordCamera(loaded, name) {
  const views = loaded.sidecar.cameras || [];
  return views.find((view) => view.name === name) || views[0] || null;
}

// The camera on a circle round `middle`, `elevation` radians up, just far enough to hold a box of size `extent`.
function fitPose(middle, extent, angle, elevation) {
  setAcross(55);
  const upDown = THREE.MathUtils.degToRad(camera.fov) / 2;
  const across = Math.atan(Math.tan(upDown) * camera.aspect);
  const distance = (extent.length() / 2) / Math.sin(Math.min(upDown, across)) * 0.95;
  const flat = Math.cos(elevation) * distance;
  camera.position.set(middle.x + Math.cos(angle) * flat, middle.y + Math.sin(elevation) * distance, middle.z + Math.sin(angle) * flat);
  camera.lookAt(middle);
}

function orbitPose(loaded, angle, lift, reach) {
  fitPose(loaded.centre, loaded.size.clone().multiplyScalar(reach), angle, 0.35 + 0.3 * lift);
}

function walkPose(loaded, segment, share, seconds) {
  const view = recordCamera(loaded, segment.camera);
  if (!view) { orbitPose(loaded, share * 0.6, 0.2, 0.9); return; }
  const eye = new THREE.Vector3(...view.eye), aim = new THREE.Vector3(...view.aim);
  const ahead = aim.clone().sub(eye).setY(0);
  const room = ahead.length();
  ahead.normalize();
  const travel = Math.min(WALK_SPEED * seconds, room * 0.6) * eased(share);
  camera.position.copy(eye).addScaledVector(ahead, travel);
  camera.lookAt(aim.clone().addScaledVector(ahead, travel));
  setAcross(view.fov || 75);
}

// An exploded view: every part pushed out from the room's middle and lifted by its height, overhead parts most.
function explode(loaded, share) {
  const spread = 0.9 * eased(share / 0.65);
  for (const part of loaded.parts) {
    if (part.scenery) continue;
    const away = part.centre.clone().sub(loaded.centre);
    const lift = (part.centre.y - loaded.box.min.y) * 0.9 + (overhead(loaded, part) ? loaded.size.y * 1.4 : 0);
    moveBy(part, new THREE.Vector3(away.x * spread, lift * spread, away.z * spread));
    if (SHELL.test(part.name)) setOpacity(part, 1 - 0.7 * eased(share / 0.5));
  }
  const grown = loaded.size.clone().multiply(new THREE.Vector3(1 + spread, 1 + 2.2 * spread, 1 + spread));
  const middle = loaded.centre.clone().setY(loaded.box.min.y + grown.y / 2);
  fitPose(middle, grown, 0.5 + share * 0.7, 0.5);
}

function isolate(loaded, segment, share) {
  const chosen = loaded.parts.filter((part) => part.name === segment.shows.part);
  if (!chosen.length) { orbitPose(loaded, share, 0.3, 1.0); return `no part ${segment.shows.part} in the copy`; }
  const box = new THREE.Box3();
  chosen.forEach((part) => box.union(part.box));
  const middle = box.getCenter(new THREE.Vector3()), size = Math.max(box.getSize(new THREE.Vector3()).length(), 0.3);
  const fade = 1 - clamp01((share - 0.15) / 0.4);
  for (const part of loaded.parts) if (!chosen.includes(part) && !part.scenery) setOpacity(part, fade);
  const view = recordCamera(loaded, segment.camera);
  const start = view ? new THREE.Vector3(...view.eye) : loaded.centre.clone().add(new THREE.Vector3(loaded.size.x, loaded.size.y, loaded.size.z));
  const angle = Math.atan2(start.z - middle.z, start.x - middle.x) + 0.6 * share;
  const close = middle.clone().add(new THREE.Vector3(Math.cos(angle) * size * 1.6, size * 0.6, Math.sin(angle) * size * 1.6));
  camera.position.copy(start).lerp(close, eased(share / 0.6));
  camera.lookAt(middle);
  setAcross(50);
  return null;
}

function lightMarkers(loaded, lift) {
  loaded.markers.clear();
  for (const entry of loaded.sidecar.lights || []) {
    if (entry.type === "directional") continue;
    const ball = new THREE.Mesh(new THREE.SphereGeometry(Math.max(loaded.size.length() * 0.006, 0.06), 12, 8),
                                new THREE.MeshBasicMaterial({ color: linear(entry.colour) }));
    ball.position.set(entry.at[0], entry.at[1] + lift, entry.at[2]);
    loaded.markers.add(ball);
  }
}

function layerFocus(loaded, segment, share) {
  const layer = segment.shows.layer;
  const ghost = 1 - (1 - GHOST) * eased(share / 0.35);
  let held = 0;
  for (const part of loaded.parts) {
    if (part.scenery) continue;
    if (part.layer === layer) held += 1; else setOpacity(part, ghost);
  }
  if (layer === "light") lightMarkers(loaded, 0);
  orbitPose(loaded, 0.8 + share * 0.5, 0.6, 1.1);
  if (held || layer === "light") return null;
  return `${layer}: no geometry of its own in the 3D copy`;
}

// The layer stack lifted apart: each OpenUSD layer the stage holds on its own plate, bottom up.
function layerSplit(loaded, share, labels) {
  const media = mediaOf(loaded.place);
  const held = (name) => loaded.parts.some((part) => part.layer === name && !part.scenery) ||
    (name === "light" && (loaded.sidecar.lights || []).some((entry) => entry.type !== "directional"));
  const named = given.stack.filter((name) => (media.layers || []).includes(name));
  const present = named.filter(held);
  const gap = Math.max(loaded.size.y, 2) * 1.15 * eased(share / 0.6);
  const level = new Map(present.map((name, index) => [name, index]));
  for (const part of loaded.parts) {
    if (part.scenery) continue;
    const index = level.has(part.layer) ? level.get(part.layer) : 0;
    moveBy(part, new THREE.Vector3(0, index * gap, 0));
    if (overhead(loaded, part)) setOpacity(part, 1 - eased(share / 0.3));
  }
  if (level.has("light")) lightMarkers(loaded, level.get("light") * gap);
  const plateShape = new THREE.BoxGeometry(loaded.size.x * 1.08, 0.04, loaded.size.z * 1.08);
  present.forEach((name, index) => {
    const plate = new THREE.Mesh(plateShape, new THREE.MeshBasicMaterial({ color: designToken("--film-plate"), transparent: true, opacity: 0.14, depthWrite: false }));
    plate.position.set(loaded.centre.x, loaded.box.min.y - 0.05 + index * gap, loaded.centre.z);
    loaded.markers.add(plate);
    const count = loaded.parts.filter((part) => part.layer === name && !part.scenery).length;
    labels.push({ at: new THREE.Vector3(loaded.box.min.x - loaded.size.x * 0.06, plate.position.y, loaded.box.max.z),
                  words: `${name}  ${count ? `${count} part${count === 1 ? "" : "s"}` : "lamps"}` });
  });
  const height = loaded.size.y + gap * Math.max(present.length - 1, 0);
  const extent = new THREE.Vector3(loaded.size.x * 1.3, height, loaded.size.z * 1.3);
  fitPose(loaded.centre.clone().setY(loaded.box.min.y + height * 0.4), extent, 0.7 + share * 0.5, 0.3);
  const bare = named.filter((name) => !held(name));
  return bare.length ? `also in the stage, no geometry in the 3D copy: ${bare.join(", ")}` : null;
}

function orbitCut(loaded, share) {
  for (const part of loaded.parts) if (overhead(loaded, part)) setOpacity(part, 0);
  orbitPose(loaded, 0.3 + share * Math.PI / 2, 0.7, 1.05);
}

// Draw one 3D frame of a segment at `share` of it; the labels to write over it and a note when it shows less.
function draw3d(loaded, segment, share, seconds) {
  showPlace(loaded);
  homeAll(loaded);
  if (!["walk-through", "hero-still"].includes(segment.cut)) for (const part of loaded.parts) if (part.scenery) setOpacity(part, 0);
  const labels = [];
  let note = null;
  if (segment.cut === "exploded") explode(loaded, share);
  else if (segment.cut === "isolate") note = isolate(loaded, segment, share);
  else if (segment.cut === "layer-focus") note = layerFocus(loaded, segment, share);
  else if (segment.cut === "layer-split") note = layerSplit(loaded, share, labels);
  else if (segment.cut === "orbit") orbitCut(loaded, share);
  else if (segment.cut === "hero-still") walkPose(loaded, segment, 0, 0);
  else walkPose(loaded, segment, share, seconds);
  renderer.render(scene, camera);
  return { labels: labels.map((label) => ({ ...label, screen: label.at.clone().project(camera) })), note };
}

// --- the preview: shots -------------------------------------------------------------------------------------------

// What a segment is played from: "film" (an accepted film's shot), "three" (the 3D copy), "picture", "card" or
// "words"; with the reason when it falls back.
function sourceOf(segment) {
  const media = mediaOf(placeOf(segment));
  const seconds = secondsOf(segment);
  if (segment.cut === "title" || segment.cut === "text") return { kind: "words" };
  if (given.recorded.includes(segment.cut)) return renderedOf(segment);
  if (segment.cut === "step-card") return { kind: "card" };
  if (segment.cut === "before-after") return { kind: "before-after" };
  if (!media) return { kind: "words", note: "no scene chosen" };
  if (segment.cut === "walk-through") {
    const film = segment.shows.film ? (media.extras || {})[segment.shows.film] : media.film && media.film.url;
    if (film && !segment.camera && seconds <= given.film_shot_seconds + 1e-6) return { kind: "film", url: film };
    if (media.web3d) return { kind: "three", note: film ? "longer than the film: the 3D copy stands in" : null };
    if (film) return { kind: "film", url: film, note: "longer than the film's shot" };
    return { kind: "words", note: "no film and no 3D copy yet" };
  }
  if (segment.cut === "hero-still" && media.hero && !segment.camera) return { kind: "picture", url: media.hero.url };
  if (media.web3d) return { kind: "three" };
  if (media.hero) return { kind: "picture", url: media.hero.url, note: "no 3D copy: its picture stands in" };
  return { kind: "words", note: "nothing to show yet" };
}

// A recorded segment plays from the rendered preview when the preview holds this very segment (wherever it stood).
function renderedOf(segment) {
  const index = previewIndex(segment);
  if (index >= 0) return { kind: "film", url: given.preview.url, from: given.preview.segments[index].start };
  return { kind: "words", note: "not in the rendered preview yet" };
}

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function captionOf(segment) {
  const box = element("div", "film-caption");
  if (segment.line) box.append(element("small", "", segment.line));
  if (segment.text) box.append(element("span", "", segment.text));
  return segment.text || segment.line ? box : null;
}

function noteOf(words) { return words ? element("div", "film-note", words) : null; }

function chainBar(step, share) {
  const bar = element("div", "film-chain");
  const at = STEP_ORDER.indexOf(step);
  STEP_ORDER.forEach((name, index) => {
    const cell = element("span", index === at ? "on" : index < at ? "done" : "");
    cell.append(element("b", "", `${index + 1}  ${given.steps[name] || "Scene"}`));
    const track = element("i");
    const fill = element("u");
    fill.style.width = `${index < at ? 100 : index === at ? 100 * share : 0}%`;
    track.append(fill);
    cell.append(track);
    bar.append(cell);
  });
  return bar;
}

class Shot {
  constructor(index, segment) {
    this.index = index;
    this.segment = segment;
    this.source = sourceOf(segment);
    this.box = element("div", `film-shot ${this.source.kind}`);
    this.ready = false;
    this.failed = null;
    this.layerWords = null;
  }

  async prepare() {
    const kind = this.source.kind;
    try {
      if (kind === "three") await this.prepareThree();
      else if (kind === "film") await this.prepareFilm();
      else if (kind === "picture") this.preparePicture(this.source.url);
      else if (kind === "before-after") await this.prepareBeforeAfter();
      else if (kind === "card") await this.prepareCard();
      else this.prepareWords();
    } catch (error) {
      this.failed = error.message;
      this.prepareWords();
    }
    const caption = kind === "words" || kind === "card" ? null : captionOf(this.segment);
    this.caption = caption;
    if (caption) this.box.append(caption);
    const note = noteOf(this.failed || this.source.note);
    if (note) this.box.append(note);
    this.ready = true;
  }

  async prepareThree() {
    this.loaded = await loadPlace(placeOf(this.segment));
    this.canvas = element("canvas");
    this.canvas.width = WIDTH;
    this.canvas.height = HEIGHT;
    this.box.append(this.canvas);
  }

  prepareFilm() {
    this.video = element("video");
    this.video.src = this.source.url;
    this.video.preload = "auto";
    this.video.playsInline = true;
    this.video.muted = true;
    this.box.append(this.video);
    return new Promise((resolve, reject) => {
      this.video.addEventListener("loadeddata", resolve, { once: true });
      this.video.addEventListener("error", () => reject(new Error("the film did not load")), { once: true });
    });
  }

  preparePicture(url) {
    this.picture = element("img");
    this.picture.src = url;
    this.picture.alt = "";
    this.box.append(this.picture);
  }

  async prepareBeforeAfter() {
    const place = placeOf(this.segment);
    await loadPictures(place);
    const concept = ((given.pictures[place] || {}).concept || [])[0];
    const media = mediaOf(place);
    if (!concept || !media || !media.hero) throw new Error("needs the scene's concept and its film");
    const before = element("img", "before"), after = element("img", "after");
    before.src = concept.url;
    after.src = media.hero.url;
    this.after = after;
    this.box.append(before, after, element("span", "film-tag left", "Concept"), element("span", "film-tag right", "Result"));
  }

  async prepareCard() {
    const place = placeOf(this.segment);
    await loadPictures(place);
    const step = this.segment.shows.step;
    const pictures = ((given.pictures[place] || {})[step] || []);
    const board = element("div", `film-board n${Math.min(pictures.length, 6)}`);
    for (const picture of pictures) {
      const image = element("img");
      image.src = picture.url;
      image.alt = "";
      board.append(image);
    }
    if (!pictures.length) board.append(element("div", "pic empty", `no ${given.steps[step] || "step"} pictures at ${place || "this place"}`));
    this.board = board;
    this.bar = chainBar(step, 0);
    const words = element("div", "film-card-words");
    words.append(element("h3", "", this.segment.text || given.steps[step] || "Step"));
    if (this.segment.line) words.append(element("p", "", this.segment.line));
    this.box.append(this.bar, words, board);
  }

  // A card's words; any other cut standing in as words (not made yet) says what it is and what it shows.
  prepareWords() {
    const card = ["title", "text"].includes(this.segment.cut);
    const words = element("div", `film-words ${this.segment.cut}`);
    words.append(element("h3", "", this.segment.text || (card ? doc.title || "" : given.cuts[this.segment.cut].label)), element("i", "rule"));
    const line = this.segment.line || (card ? "" : segmentWords(this.segment));
    if (line) words.append(element("p", "", line));
    this.box.append(words);
    this.words = words;
  }

  // A card's words come in on its clock: the title rises in as its letters close up, the rule draws out under it, the
  // line follows; all of it closes in slowly and fades before the card ends.
  drawWords(local, seconds) {
    const [title, rule, line] = [this.words.querySelector("h3"), this.words.querySelector(".rule"), this.words.querySelector("p")];
    const out = eased((seconds - local) / 0.6), rising = eased((local - 0.15) / 0.8);
    Object.assign(title.style, { opacity: String(Math.min(rising, out)), transform: `translateY(${(1 - rising) * 14}px)`,
      letterSpacing: `${0.09 - 0.1 * eased(local / 1.8)}em` });
    rule.style.transform = `scaleX(${eased((local - 0.55) / 0.8)})`;
    rule.style.opacity = String(out);
    if (line) {
      const shown = eased((local - 0.8) / 0.7);
      Object.assign(line.style, { opacity: String(Math.min(shown, out)), transform: `translateY(${(1 - shown) * 10}px)` });
    }
    this.words.style.transform = `scale(${1 + 0.025 * local / seconds})`;
  }

  // Show the shot at `local` seconds into its segment.
  draw(local, playing) {
    const seconds = secondsOf(this.segment), share = clamp01(local / seconds);
    if (this.caption) this.caption.style.opacity = String(Math.min(clamp01((local - CAPTION_IN) / 0.5), clamp01((seconds - local) / 0.5)));
    if (this.words) this.drawWords(local, seconds);
    if (this.loaded) this.drawThree(share, seconds);
    if (this.video) this.drawFilm(local, playing);
    if (this.picture) this.picture.style.transform = `scale(${1 + 0.06 * eased(share)})`;
    if (this.after) this.after.style.clipPath = `inset(0 0 0 ${100 * (1 - eased((share - 0.2) / 0.6))}%)`;
    if (this.board) {
      this.bar.replaceWith(this.bar = chainBar(this.segment.shows.step, share));
      this.board.style.transform = `translateX(${(1 - eased(share / 0.25)) * 6}%) scale(${1 + 0.03 * share})`;
    }
  }

  drawThree(share, seconds) {
    const drawn = draw3d(this.loaded, this.segment, share, seconds);
    const pen = this.canvas.getContext("2d");
    pen.drawImage(renderer.domElement, 0, 0, WIDTH, HEIGHT);
    pen.font = "600 17px Inter, system-ui, sans-serif";
    for (const label of drawn.labels) {
      if (label.screen.z > 1) continue;
      const x = (label.screen.x + 1) / 2 * WIDTH, y = (1 - label.screen.y) / 2 * HEIGHT;
      const width = pen.measureText(label.words).width + 16;
      pen.fillStyle = designToken("--color-scrim");
      pen.fillRect(x - width, y - 14, width, 26);
      pen.fillStyle = designToken("--color-text-body");
      pen.fillText(label.words, x - width + 8, y + 5);
    }
    if (drawn.note !== this.layerWords) {
      this.layerWords = drawn.note;
      this.box.querySelector(".film-note.live")?.remove();
      if (drawn.note) { const live = noteOf(drawn.note); live.classList.add("live"); this.box.append(live); }
    }
  }

  drawFilm(local, playing) {
    const wanted = Math.min((this.source.from ?? given.film_shot_from) + local, Math.max(0, (this.video.duration || 99) - 0.05));
    this.video.muted = !($("sound").checked && this.segment.sound === "place");
    if (playing) {
      if (this.video.paused) this.video.play().catch(() => {});
      if (Math.abs(this.video.currentTime - wanted) > 0.25) this.video.currentTime = wanted;
    } else {
      if (!this.video.paused) this.video.pause();
      if (Math.abs(this.video.currentTime - wanted) > 0.04) this.video.currentTime = wanted;
    }
  }

  stop() { if (this.video) this.video.pause(); }
}

// --- the preview: the player ----------------------------------------------------------------------------------------

const player = {
  clock: 0, playing: false, last: 0, shots: new Map(),

  reset() {
    for (const shot of this.shots.values()) { shot.stop(); shot.box.remove(); }
    this.shots.clear();
    this.clock = Math.min(this.clock, totalSeconds());
    this.paint();
  },

  shot(index) {
    if (!this.shots.has(index)) {
      const made = new Shot(index, doc.segments[index]);
      this.shots.set(index, made);
      made.prepare().then(() => this.paint());
    }
    return this.shots.get(index);
  },

  seek(seconds) {
    this.clock = Math.max(0, Math.min(seconds, totalSeconds()));
    this.paint();
  },

  toggle() {
    if (!this.playing && this.clock >= totalSeconds() - 0.01) this.clock = 0;
    this.playing = !this.playing;
    $("play").textContent = this.playing ? "Pause" : "Play";
    this.last = performance.now();
    if (this.playing) requestAnimationFrame((now) => this.tick(now));
    else this.paint();
  },

  tick(now) {
    if (!this.playing) return;
    const active = this.activeAt(this.clock);
    const waiting = active.some((index) => !this.shot(index).ready);
    if (!waiting) this.clock += Math.min((now - this.last) / 1000, 0.1);
    this.last = now;
    if (this.clock >= totalSeconds()) { this.clock = totalSeconds(); this.toggle(); return; }
    this.paint();
    requestAnimationFrame((later) => this.tick(later));
  },

  activeAt(clock) {
    const slots = timeline();
    const found = slots.map((slot, index) => index).filter((index) => slots[index].start <= clock && clock < slots[index].end);
    if (!found.length && slots.length) found.push(slots.length - 1);
    return found;
  },

  // Each active shot's opacity and offset from its transition, and the black of a fade through black.
  paint() {
    const slots = timeline(), active = this.activeAt(this.clock), half = given.transition_seconds / 2;
    const holder = $("shots");
    let black = 0;
    for (const index of active) for (const ahead of [index + 1, index + 2]) if (ahead < doc.segments.length) this.shot(ahead);
    for (const [index, shot] of this.shots) {
      if (!active.includes(index)) { shot.stop(); shot.box.remove(); }
    }
    for (const index of active) {
      const shot = this.shot(index), slot = slots[index], local = this.clock - slot.start;
      if (shot.box.parentNode !== holder) holder.append(shot.box);
      shot.box.style.zIndex = String(index);
      const transition = doc.segments[index].transition || "cut";
      const entering = clamp01(local / given.transition_seconds);
      shot.box.style.opacity = transition === "cross-fade" && index > 0 ? String(entering) : "1";
      shot.box.style.transform = transition === "push" && index > 0 ? `translateX(${(1 - eased(entering)) * 100}%)` : "";
      const next = doc.segments[index + 1];
      if (next && next.transition === "push" && active.includes(index + 1)) {
        shot.box.style.transform = `translateX(${-eased(clamp01((this.clock - slots[index + 1].start) / given.transition_seconds)) * 100}%)`;
      }
      if (transition === "fade-through-black" && local < half) black = Math.max(black, 1 - local / half);
      if (next && next.transition === "fade-through-black" && slot.end - this.clock < half) black = Math.max(black, 1 - (slot.end - this.clock) / half);
      if (shot.ready) shot.draw(local, this.playing);
    }
    $("black").style.opacity = String(black);
    const waiting = active.filter((index) => !this.shot(index).ready);
    $("wait").hidden = !waiting.length;
    $("wait").textContent = waiting.length ? `Loading ${segmentWords(doc.segments[waiting[0]])}...` : "";
    $("clock").textContent = `${clockWords(this.clock)} / ${clockWords(totalSeconds())}`;
    $("scrub").max = String(totalSeconds());
    $("scrub").value = String(this.clock);
    const shown = active[active.length - 1];
    if (shown !== undefined && shown !== this.highlighted) {
      this.highlighted = shown;
      document.querySelectorAll(".film-card").forEach((card, index) => card.classList.toggle("playing", index === shown));
    }
  },
};

$("play").onclick = () => player.toggle();
$("scrub").oninput = () => player.seek(Number($("scrub").value));
$("whole").onchange = () => { places.clear(); player.reset(); };
if ($("lock")) $("lock").onclick = lockOrUnlock;
window.filmPlayer = player;  // the page's own handle, for a headless look at a given moment

// The rendered free preview in place of the live player, with its own controls and sound.
function showRendered(on) {
  if (on && player.playing) player.toggle();
  $("rendered").hidden = !on;
  if (!on) $("rendered").pause();
  $("show-live").setAttribute("aria-pressed", String(!on));
  $("show-rendered").setAttribute("aria-pressed", String(on));
  document.querySelector(".film-transport").classList.toggle("off", on);
}
if ($("rendered")) {
  $("show-live").onclick = () => showRendered(false);
  $("show-rendered").onclick = () => showRendered(true);
}

drawLength();
drawTimeline();
drawInspector();
drawAdd();
drawRender();
if (given.can_save) $("saved").textContent = given.locked ? "" : given.origin === "saved" ? "saved" : "saves as you change it";
player.seek(given.transition_seconds);  // past a first fade through black, so the first frame shows
