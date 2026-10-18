// The Library explorer: the tree of kinds and categories on the left, the chosen folder's entries beside it, the
// chosen entry on the right with its 3D view first (libview.js), all from /api/library (api/library_api.py) without
// a page load. On a phone one pane shows at a time. The owner ticks entries to lock, withdraw or refine them.
const $ = (id) => document.getElementById(id);
const explorer = $("lib-explorer");
const first = JSON.parse($("lib-first").textContent);
const SHOWN_MAX = 400;  // tiles drawn at once; a search or a filter narrows the rest
const BANDS = [["", "Every score"], ["low", "Below 50"], ["mid", "50 to 79"], ["high", "80 and up"], ["none", "Not scored"]];
const KEPT_OPEN = "library-open-folders";

const view = { node: first.node, entry: first.entry, place: first.place, q: first.q, state: "", band: "", sort: "name" };
const picked = new Map();  // address -> its row, the owner's choice
let tree = [], owner = false, parents = new Map(), labels = new Map(), opened = keptOpen(), shownRows = [];

// --- small helpers ---------------------------------------------------------------------------------------------

function make(tag, attributes = {}, ...children) {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (value === null || value === undefined || value === false) continue;
    if (name === "class") element.className = value;
    else if (name.startsWith("on")) element.addEventListener(name.slice(2), value);
    else element.setAttribute(name, value === true ? "" : value);
  }
  element.append(...children.flat().filter((child) => child !== null && child !== undefined && child !== false));
  return element;
}

function cookie(name) {
  const found = document.cookie.split("; ").find((part) => part.startsWith(name + "="));
  return found ? decodeURIComponent(found.slice(name.length + 1)) : "";
}

async function getJson(url) {
  const answer = await fetch(url, { credentials: "same-origin" });
  if (!answer.ok) throw new Error(`${answer.status} ${(await answer.json().catch(() => ({}))).detail || ""}`.trim());
  return answer.json();
}

async function postJson(url, body) {
  const answer = await fetch(url, {
    method: "POST", credentials: "same-origin", body: JSON.stringify(body),
    headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
  });
  const found = await answer.json().catch(() => ({}));
  if (!answer.ok) throw new Error(found.detail || String(answer.status));
  return found;
}

function keptOpen() {
  try { return new Set(JSON.parse(localStorage.getItem(KEPT_OPEN) || "[]")); } catch { return new Set(); }
}

function keepOpen() {
  try { localStorage.setItem(KEPT_OPEN, JSON.stringify([...opened])); } catch { /* a private window keeps none */ }
}

function scoreBadge(score, big = false) {
  if (score === null || score === undefined) return null;
  const band = score >= 80 ? "high" : score >= 50 ? "mid" : "low";
  return make("b", { class: `score-badge ${band}${big ? " big" : ""}`, title: `quality score ${score} of 100` }, String(score));
}

function stateMark(state) {
  return make("i", { class: `mark ${state === "locked" ? "accepted" : state === "draft" ? "waiting" : "not-run"}`, title: state });
}

function remember() {
  const query = new URLSearchParams();
  for (const name of ["node", "entry", "place", "q"]) if (view[name]) query.set(name, view[name]);
  history.replaceState(null, "", `${location.pathname}${query.size ? "?" + query : ""}`);
}

// On a phone one pane shows at a time: the newly shown one starts at its top.
function showPane(name) {
  explorer.dataset.pane = name;
  if (window.matchMedia("(max-width: 700px)").matches && explorer.getBoundingClientRect().top < 0) explorer.scrollIntoView();
}

// --- the tree --------------------------------------------------------------------------------------------------

function index(nodes, parent) {
  for (const node of nodes) {
    parents.set(node.id, parent);
    labels.set(node.id, node.label);
    index(node.children, node.id);
  }
}

function pathTo(id) {
  const found = [];
  for (let at = id; at; at = parents.get(at)) found.unshift(at);
  return found;
}

function treeItem(node) {
  const hasChildren = node.children.length > 0, isOpen = opened.has(node.id);
  const item = make("li", { role: "treeitem", "aria-expanded": hasChildren ? String(isOpen) : null,
                            "aria-selected": String(view.node === node.id && !view.q) });
  const caret = hasChildren
    ? make("button", { type: "button", class: "caret", "aria-label": isOpen ? "close" : "open",
                       onclick: () => toggle(node.id) }, isOpen ? "▾" : "▸")
    : make("span", { class: "caret" });
  const name = make("button", { type: "button", class: "folder", onclick: () => chooseFolder(node.id) },
                    make("span", { class: "folder-name" }, node.label), make("span", { class: "count" }, String(node.count)));
  item.append(make("div", { class: "tree-row" }, caret, name));
  if (hasChildren && isOpen) item.append(make("ul", { role: "group" }, node.children.map(treeItem)));
  return item;
}

function drawTree() {
  $("lib-tree").replaceChildren(make("ul", { class: "tree-top" }, tree.map(treeItem)));
}

function toggle(id) {
  if (opened.has(id)) opened.delete(id); else opened.add(id);
  keepOpen();
  drawTree();
}

function chooseFolder(id) {
  for (const up of pathTo(id)) opened.add(up);
  keepOpen();
  view.node = id;
  view.q = "";
  $("lib-search").value = "";
  drawTree();
  showPane("list");
  loadList();
}

// --- a folder's entries ----------------------------------------------------------------------------------------

function drawWhere(found) {
  const where = view.q ? [make("span", {}, `"${view.q}" in the whole library`)]
    : view.node ? pathTo(view.node).map((id, rank, all) => rank < all.length - 1
      ? make("button", { type: "button", class: "crumb", onclick: () => chooseFolder(id) }, labels.get(id))
      : make("b", {}, labels.get(id)))
    : [make("span", {}, view.place ? `Everything from ${view.place.replace(/_/g, " ")}` : "Everything")];
  $("lib-where").replaceChildren(make("div", { class: "crumbs-line" }, where),
                                 make("span", { class: "soft small" }, `${found.count} entr${found.count === 1 ? "y" : "ies"}`));
}

function drawBands(found) {
  $("lib-bands").replaceChildren(...BANDS.map(([band, words]) => {
    const count = band ? found.bands[band] : Object.values(found.bands).reduce((sum, each) => sum + each, 0);
    return make("button", { type: "button", class: `band ${band || "every"}${view.band === band ? " on" : ""}`,
                            disabled: band && !count && view.band !== band,
                            onclick: () => { view.band = band; loadList(); } }, words, make("span", { class: "count" }, String(count)));
  }));
}

function tile(row) {
  const thumb = row.thumb ? make("img", { class: "pic", src: row.thumb, alt: row.title, loading: "lazy", "data-name": row.title })
    : make("div", { class: "pic empty" }, make("span", {}, row.title));
  const three = row.has3d ? make("span", { class: "pill three" }, "3D") : row.waits3d ? make("span", { class: "pill waits" }, "3D soon") : null;
  const card = make("div", { class: `lib-card ${row.state}${view.entry === row.address ? " here" : ""}${picked.has(row.address) ? " chosen" : ""}`,
                             "data-address": row.address },
    make("button", { type: "button", class: "card-open", onclick: () => openEntry(row.address), "aria-label": row.title },
      make("div", { class: "frame" }, thumb, make("div", { class: "card-marks" }, scoreBadge(row.score), three)),
      make("div", { class: "card-foot" }, stateMark(row.state), make("span", { class: "card-name" }, row.title)),
      row.place ? make("div", { class: "card-place" }, `from ${row.place.replace(/_/g, " ")}`) : null),
    row.asked ? make("span", { class: "corner" }, `${row.asked} asked`) : null);
  if (owner && row.state !== "withdrawn") {
    const box = make("input", { type: "checkbox", "aria-label": `choose ${row.title}`, onchange: (event) => pick(row, event.target.checked) });
    box.checked = picked.has(row.address);
    card.append(make("label", { class: "pick", title: "choose" }, box));
  }
  return card;
}

function drawGrid(found) {
  shownRows = found.entries;
  const drawn = found.entries.slice(0, SHOWN_MAX).map(tile);
  const more = found.entries.length > SHOWN_MAX
    ? make("p", { class: "soft small lib-more" }, `The first ${SHOWN_MAX} of ${found.entries.length}: search or filter to narrow.`) : null;
  $("lib-grid").replaceChildren(...(drawn.length ? drawn : [make("p", { class: "soft lib-hint" }, "Nothing matches.")]), ...(more ? [more] : []));
}

async function loadList() {
  remember();
  if (!view.node && !view.q && !view.place) return;
  const query = new URLSearchParams({ node: view.q ? "" : view.node, q: view.q, place: view.place, state: view.state,
                                      band: view.band, sort: view.sort });
  try {
    const found = await getJson(`/api/library/list?${query}`);
    drawWhere(found);
    drawBands(found);
    drawGrid(found);
  } catch (error) {
    $("lib-grid").replaceChildren(make("p", { class: "notice" }, `Could not read this folder: ${error.message}`));
  }
}

// --- the owner's choice ----------------------------------------------------------------------------------------

function pick(row, chosen) {
  if (chosen) picked.set(row.address, row); else picked.delete(row.address);
  document.querySelector(`.lib-card[data-address="${CSS.escape(row.address)}"]`)?.classList.toggle("chosen", chosen);
  drawBar();
}

function sharedOptions() {
  const options = new Map();
  for (const row of picked.values()) for (const option of row.refine) options.set(option.id, option.label);
  return [...options];
}

function drawBar() {
  const bar = $("lib-bar"), rows = [...picked.values()];
  bar.hidden = rows.length === 0;
  bar.querySelector("[data-picked]").textContent = String(rows.length);
  bar.querySelector('[data-act="lock"]').disabled = !rows.every((row) => row.state === "draft");
  bar.querySelector('[data-act="withdraw"]').disabled = !rows.every((row) => row.state === "locked");
  $("lib-refine-option").replaceChildren(make("option", { value: "" }, "Refine as each one's scoring suggests"),
    ...sharedOptions().map(([id, label]) => make("option", { value: id }, `Refine: ${label}`)));
}

async function act(what) {
  const said = $("lib-said"), addresses = [...picked.keys()];
  if (what === "unpick") { picked.clear(); drawBar(); loadList(); return; }
  try {
    const answer = what === "refine"
      ? await postJson("/api/library/refine", { addresses, option: $("lib-refine-option").value })
      : await postJson("/api/library/ask", { action: what, addresses });
    said.textContent = answer.said;
    if (what === "refine") basketCount(answer.in_basket);
    else { picked.clear(); drawBar(); loadList(); }
  } catch (error) {
    said.textContent = `not done: ${error.message}`;
  }
}

function basketCount(count) {
  const link = document.querySelector('header.top nav a[href="/basket/"]');
  if (!link) return;
  link.querySelector(".count")?.remove();
  if (count) link.append(make("span", { class: "count" }, String(count)));
}

for (const button of $("lib-bar").querySelectorAll("[data-act]")) button.addEventListener("click", () => act(button.dataset.act));

// --- one entry -------------------------------------------------------------------------------------------------

function factRows(entry) {
  const link = (found) => found.url ? make("a", { href: found.url }, found.label) : make("span", {}, found.label);
  const rows = [];
  if (entry.world) rows.push(["World", entry.world]);
  if (entry.place) rows.push(["Place", link(entry.place)]);
  if (entry.step) rows.push(["Step", link(entry.step)]);
  if (entry.source) rows.push(["Read from", entry.source]);
  if (entry.seen_in.length > 1) rows.push(["Used in", entry.seen_in.flatMap((found, rank) => [rank ? ", " : "", link(found)])]);
  return make("dl", { class: "facts" }, rows.flatMap(([name, value]) => [make("dt", {}, name), make("dd", {}, value)]));
}

function mediaTabs(entry, stage, picture) {
  const has3d = entry.three_d !== null;
  if (!has3d || !entry.picture) return null;
  const tabs = make("div", { class: "lib-tabs", role: "tablist" });
  const choose = (which) => {
    stage.hidden = which !== "3d";
    picture.hidden = which !== "picture";
    for (const button of tabs.children) button.classList.toggle("on", button.dataset.tab === which);
  };
  tabs.append(make("button", { type: "button", class: "on", "data-tab": "3d", onclick: () => choose("3d") }, "3D"),
              make("button", { type: "button", "data-tab": "picture", onclick: () => choose("picture") }, "Picture"));
  return tabs;
}

function waitingCard(entry) {
  return make("div", { class: "lib-waiting" },
    entry.picture ? make("img", { src: entry.picture, alt: "" }) : null,
    make("div", { class: "lib-waiting-words" }, make("b", {}, "3D copy on its way"),
         make("span", {}, "Its web copy is being made; the picture shows it until then.")));
}

async function openThreeD(entry, stage, said) {
  const shown = entry.three_d;
  if (shown.waiting) { stage.replaceChildren(waitingCard(entry)); return; }
  if (shown.place) {
    stage.replaceChildren(make("div", { class: "lib-waiting" }, entry.picture ? make("img", { src: entry.picture, alt: "" }) : null,
      make("div", { class: "lib-waiting-words" }, make("a", { class: "button primary", href: shown.place }, "Open the place in 3D"))));
    return;
  }
  said.textContent = shown.model ? `Loading ${(shown.bytes / 1e6).toFixed(1)} MB...` : "";
  try {
    const viewer = await import("/static/pages/libview.js");
    const facts = shown.model ? await viewer.showModel(stage, shown.model) : await viewer.showFinish(stage, shown.finish, shown.print);
    if (!facts) return;
    const made = shown.model ? (shown.web_copy ? "its web copy" : "its own GLB") : "its own finish";
    said.textContent = [facts.size, facts.triangles ? `${facts.triangles.toLocaleString()} triangles` : null, made,
                        "drag to turn, wheel to come closer"].filter(Boolean).join("; ");
  } catch (error) {
    stage.replaceChildren(waitingCard(entry));
    said.textContent = `The 3D view could not open: ${error.message}`;
  }
}

function qualityPart(entry) {
  const quality = entry.quality;
  const parts = quality.parts.map((part) => make("div", { class: `part${part.score === null ? " unmeasured" : ""}`, title: part.how || null },
    make("span", { class: "part-name" }, part.name),
    make("span", { class: "part-bar" }, make("i", { style: `width:${Math.max(0, Math.min(100, part.score ?? 0))}%` })),
    make("span", { class: "part-score" }, part.score === null ? "not measured" : String(part.score))));
  const head = make("div", { class: "quality-head" }, scoreBadge(quality.score, true),
    make("span", { class: "soft small" }, quality.score === null ? "Not scored yet." : "Quality score of 100, from its kind's own scoring."));
  return make("section", { class: "lib-quality" }, make("h3", { class: "eyebrow" }, "Quality"), head, parts, refineChoice(entry));
}

function refineChoice(entry) {
  if (!owner || entry.state === "withdrawn") return null;
  const options = entry.quality.refine.map((option) => make("label", { class: "chip" },
    make("input", { type: "checkbox", value: option.id }), option.label));
  const said = make("output", { class: "small" });
  const add = async () => {
    const chosen = [...box.querySelectorAll("input:checked")].map((input) => input.value);
    try {
      let answer = null;
      for (const option of chosen.length ? chosen : [""]) answer = await postJson("/api/library/refine", { addresses: [entry.address], option });
      said.textContent = answer.said;
      basketCount(answer.in_basket);
    } catch (error) {
      said.textContent = `not added: ${error.message}`;
    }
  };
  const box = make("div", { class: "refine-choice" }, options.length ? make("div", { class: "chips" }, options) : null,
    make("button", { type: "button", onclick: add }, "Add to basket as a refine item"), said);
  return box;
}

function decideButton(entry) {
  if (!owner || entry.asked || entry.state === "withdrawn") return null;
  const action = entry.state === "draft" ? "lock" : "withdraw";
  const said = make("output", { class: "small" });
  const press = async () => {
    try {
      said.textContent = (await postJson("/api/library/ask", { action, addresses: [entry.address] })).said;
      openEntry(entry.address);
      loadList();
    } catch (error) {
      said.textContent = `not done: ${error.message}`;
    }
  };
  return make("div", { class: "lib-decide" },
    make("button", { type: "button", class: action === "lock" ? "primary" : "danger", onclick: press },
         action === "lock" ? "Lock: approve as final" : "Withdraw"), said);
}

function needs(entry) {
  if (!entry.requires.length) return null;
  return [make("h3", { class: "eyebrow" }, "Needs"), make("div", { class: "chips" }, entry.requires.map((need) => need.known
    ? make("button", { type: "button", class: "chip", onclick: () => openEntry(need.address) }, need.title)
    : make("span", { class: "chip missing" }, need.title)))];
}

function versions(entry) {
  if (entry.versions.length < 2) return null;
  return [make("h3", { class: "eyebrow" }, "Versions"), make("div", { class: "chips" }, entry.versions.map((other) =>
    make("button", { type: "button", class: `chip${other.address === entry.address ? " on" : ""}`, onclick: () => openEntry(other.address) },
         `v${other.version} ${other.state}`)))];
}

function idsFold(entry) {
  const tags = Object.entries(entry.ids.tags || {}).map(([name, values]) => `${name}: ${values.join(", ")}`).join("; ");
  return make("details", { class: "ids" }, make("summary", {}, "details"), make("div", { class: "fold-body" },
    make("p", {}, "Address ", make("code", {}, entry.address),
         entry.ids.node ? [", made by ", make("code", {}, entry.ids.node)] : null,
         entry.ids.commit ? [" at commit ", make("code", {}, entry.ids.commit.slice(0, 12))] : null, "."),
    tags ? make("p", {}, tags) : null));
}

function drawEntry(entry) {
  const stage = make("div", { class: "lib-stage" });
  const picture = make("figure", { class: "lib-picture", hidden: entry.three_d !== null && Boolean(entry.picture) },
    entry.picture ? make("a", { href: entry.picture, target: "_blank" }, make("img", { class: "pic", src: entry.picture, alt: entry.title }))
      : make("div", { class: "pic empty" }, make("span", {}, entry.title), make("small", {}, "no picture yet")));
  if (entry.three_d === null) stage.hidden = true;
  const said = make("p", { class: "small soft lib-said" });
  const full = entry.three_d && entry.three_d.full ? make("a", { class: "small", href: entry.three_d.full }, "Full screen, with measuring") : null;
  const takes = entry.takes.length ? make("div", { class: "takes" }, entry.takes.map((take) =>
    make("figure", { class: "take" }, make("audio", { controls: true, preload: "none", src: take.url }), make("figcaption", {}, take.name)))) : null;
  const parts = [
    make("div", { class: "lib-entry-head" },
      make("button", { type: "button", class: "quiet lib-back", onclick: () => showPane("list") }, "‹ Entries"),
      make("div", { class: "lib-entry-title" }, make("span", { class: "eyebrow" }, entry.kind_label),
           make("h2", {}, entry.title)),
      make("div", { class: "lib-entry-marks" }, scoreBadge(entry.quality.score),
           make("span", { class: `status ${entry.state === "locked" ? "done" : entry.state === "draft" ? "review" : "quiet"}` }, entry.state),
           entry.asked ? make("span", { class: "tag" }, `${entry.asked} asked, waiting for the library's machine`) : null)),
    mediaTabs(entry, stage, picture), stage, picture, make("div", { class: "lib-under-stage" }, said, full), takes,
    make("p", { class: "lib-sentence" }, entry.sentence),
    qualityPart(entry), decideButton(entry),
    make("h3", { class: "eyebrow" }, "Where it came from"), factRows(entry), needs(entry), versions(entry), idsFold(entry)];
  $("lib-entry").replaceChildren(...parts.flat().filter(Boolean));
  if (entry.three_d !== null) openThreeD(entry, stage, said);
}

async function openEntry(address) {
  view.entry = address;
  remember();
  for (const card of document.querySelectorAll(".lib-card")) card.classList.toggle("here", card.dataset.address === address);
  showPane("entry");
  try {
    drawEntry(await getJson(`/api/library/entry?address=${encodeURIComponent(address)}`));
  } catch (error) {
    $("lib-entry").replaceChildren(make("p", { class: "notice" }, `Could not open ${address}: ${error.message}`));
  }
}

// --- filters and the start -------------------------------------------------------------------------------------

function wireFilters(places, states) {
  $("lib-place").append(...places.map((place) => make("option", { value: place }, place.replace(/_/g, " "))));
  $("lib-state").append(...states.map((state) => make("option", { value: state }, state)));
  $("lib-place").value = view.place;
  $("lib-sort").onchange = () => { view.sort = $("lib-sort").value; loadList(); };
  $("lib-place").onchange = () => { view.place = $("lib-place").value; loadList(); };
  $("lib-state").onchange = () => { view.state = $("lib-state").value; loadList(); };
  let waiting = null;
  $("lib-search").value = view.q;
  $("lib-search").addEventListener("input", () => {
    clearTimeout(waiting);
    waiting = setTimeout(() => { view.q = $("lib-search").value.trim(); drawTree(); showPane("list"); loadList(); }, 250);
  });
  for (const button of document.querySelectorAll("[data-pane-to]")) button.addEventListener("click", () => showPane(button.dataset.paneTo));
}

async function start() {
  const found = await getJson("/api/library/tree");
  tree = found.tree;
  owner = found.owner;
  index(tree, null);
  if (!view.node && view.entry) view.node = view.entry.split("/")[0];
  if (view.node && !labels.has(view.node)) view.node = "";
  for (const up of pathTo(view.node)) if (up !== view.node) opened.add(up);
  wireFilters(found.places, found.states);
  drawTree();
  await loadList();
  if (view.entry) openEntry(view.entry);
  else if (view.node || view.q || view.place) showPane("list");
}

start().catch((error) => { $("lib-tree").replaceChildren(make("p", { class: "notice" }, `Could not read the library: ${error.message}`)); });
