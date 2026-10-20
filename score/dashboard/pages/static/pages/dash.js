// The pages' live parts: a fold that refreshes itself from the server every few seconds (data-refresh="URL"), a
// frame scrubber under each film that says its frames a second (data-fps), a board tile's film shown at its middle
// frame, and never a broken picture: a picture whose file is not there yet becomes a calm "on its way" tile.

function onItsWay(element) {
  const tile = document.createElement("div");
  tile.className = "pic empty";
  const name = document.createElement("span");
  name.textContent = element.dataset.name || element.getAttribute("alt") || "picture";
  const words = document.createElement("small");
  words.textContent = "picture on its way";
  tile.append(name, words);
  element.replaceWith(tile);
}

// Capture: an image's error does not bubble, and a lazy image can fail long after the page loaded.
document.addEventListener("error", (event) => {
  const element = event.target;
  if (element instanceof HTMLImageElement) onItsWay(element);
}, true);
for (const image of document.querySelectorAll("img")) {
  if (image.complete && image.naturalWidth === 0 && image.getAttribute("src")) onItsWay(image);
}

// A board tile's film over its still: shown only once it stands at its middle frame, so a film that cannot load
// leaves the still in view.
for (const video of document.querySelectorAll("video.middle")) {
  const middle = () => { if (Number.isFinite(video.duration)) video.currentTime = video.duration / 2; };
  video.addEventListener("loadedmetadata", middle, { once: true });
  if (video.readyState >= 1) middle();
  const shown = () => { if (video.readyState >= 2 && video.videoWidth > 0) video.classList.add("ready"); };
  video.addEventListener("seeked", shown);
  video.addEventListener("loadeddata", shown);
  video.addEventListener("error", () => video.remove(), { once: true });
  if (video.error) video.remove();
}
for (const element of document.querySelectorAll("[data-refresh]")) {
  const every = Number(element.dataset.every || 10) * 1000;
  setInterval(async () => {
    try {
      const answer = await fetch(element.dataset.refresh, { credentials: "same-origin" });
      if (answer.ok) element.innerHTML = await answer.text();
    } catch (error) {
      element.dataset.failed = String(error);
    }
  }, every);
}

function scrubber(video) {
  const fps = Number(video.dataset.fps);
  const bar = document.createElement("div");
  bar.className = "scrub";
  bar.innerHTML = '<button type="button" data-step="-1" title="one frame back (,)">&lsaquo; frame</button>' +
    '<input type="range" min="0" step="1" value="0" aria-label="frame">' +
    '<button type="button" data-step="1" title="one frame on (.)">frame &rsaquo;</button><output></output>';
  video.after(bar);
  const range = bar.querySelector("input"), shown = bar.querySelector("output");
  const frames = () => Math.max(0, Math.round(video.duration * fps) - 1);
  const frameNow = () => Math.min(frames(), Math.floor(video.currentTime * fps + 1e-3));
  const seek = (frame) => {
    video.pause();
    video.currentTime = (Math.max(0, Math.min(frames(), frame)) + 0.5) / fps;  // the middle of the frame
  };
  const show = () => {
    range.max = String(frames());
    range.value = String(frameNow());
    shown.textContent = `frame ${frameNow()} of ${frames()} at ${fps} fps (${video.currentTime.toFixed(2)} s)`;
  };
  range.addEventListener("input", () => seek(Number(range.value)));
  bar.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => seek(frameNow() + Number(button.dataset.step)));
  });
  video.addEventListener("keydown", (event) => {
    if (event.key === "," || event.key === ".") { event.preventDefault(); seek(frameNow() + (event.key === "." ? 1 : -1)); }
  });
  for (const name of ["loadedmetadata", "timeupdate", "seeked"]) video.addEventListener(name, show);
  if (video.readyState >= 1) show();
}

for (const video of document.querySelectorAll("video[data-fps]")) {
  if (Number(video.dataset.fps) > 0) scrubber(video);
}

// A strip picture (a plan drawing, a render) opens large over the page; a click or Esc closes it.
function openLarge(url, caption) {
  const box = document.createElement("div");
  box.className = "lightbox";
  box.setAttribute("role", "dialog");
  const image = document.createElement("img");
  image.src = url;
  image.alt = caption;
  const words = document.createElement("p");
  words.textContent = caption;
  box.append(image, words);
  const close = () => { box.remove(); document.removeEventListener("keydown", onKey); };
  const onKey = (event) => { if (event.key === "Escape") close(); };
  box.addEventListener("click", close);
  document.addEventListener("keydown", onKey);
  document.body.append(box);
}

for (const button of document.querySelectorAll("[data-full]")) {
  button.addEventListener("click", () => openLarge(button.dataset.full, button.dataset.caption || ""));
}

// A basket item's 3D view: the before and after switch loads the other side into the frame.
for (const button of document.querySelectorAll(".item-3d-bar [data-src]")) {
  button.addEventListener("click", () => {
    document.getElementById("item-3d").src = button.dataset.src;
    for (const other of document.querySelectorAll(".item-3d-bar [data-src]")) other.classList.toggle("on", other === button);
  });
}

// The owner's cost figures, his basket and his checkout go to the API as JSON, with the CSRF token from its cookie; the page then reads again.
function cookie(name) {
  const found = document.cookie.split("; ").find((part) => part.startsWith(name + "="));
  return found ? decodeURIComponent(found.slice(name.length + 1)) : "";
}

for (const form of document.querySelectorAll("form[data-post]")) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const said = form.querySelector("output");
    const body = Object.fromEntries(new FormData(form));
    if (event.submitter && event.submitter.name) body[event.submitter.name] = event.submitter.value;
    if ("euros" in body) body.euros = Number(body.euros);
    for (const name of ["in", "confirm"]) if (name in body) body[name] = body[name] === "yes";
    try {
      const answer = await fetch(form.dataset.post, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
        body: JSON.stringify(body),
      });
      const found = await answer.json().catch(() => ({}));
      said.textContent = answer.ok ? found.said : `not entered: ${found.detail || answer.status}`;
      if (answer.ok) setTimeout(() => location.reload(), 800);
    } catch (error) {
      said.textContent = `not entered: ${error}`;
    }
  });
}


// The side panel (templates/pages/c/panel.html): a click on [data-opens="<id>"] fills that panel's slots from the
// element's data-title, data-state, data-tone, data-price, data-action and data-action-label, and opens it.
function openPanel(opener) {
  const panel = document.getElementById(opener.dataset.opens);
  if (!panel) return;
  const slot = (name) => panel.querySelector(`[data-slot="${name}"]`);
  slot("title").textContent = opener.dataset.title || "";
  slot("state").textContent = opener.dataset.state || "";
  slot("tone").className = `dot tone-${opener.dataset.tone || "idle"}`;
  slot("price").textContent = opener.dataset.price || "";
  slot("price").classList.toggle("unknown", opener.dataset.price === "unknown");
  const picture = slot("picture");
  if (picture) {
    picture.hidden = !opener.dataset.picture;
    if (opener.dataset.picture) picture.src = opener.dataset.picture; else picture.removeAttribute("src");
  }
  const posts = Boolean(opener.dataset.body), action = slot("action"), post = slot("post");
  action.hidden = !opener.dataset.action || posts;
  action.href = opener.dataset.action || "#";
  action.textContent = opener.dataset.actionLabel || "";
  if (post) {
    post.hidden = !posts;
    Object.assign(post.dataset, { url: opener.dataset.action || "", body: opener.dataset.body || "" });
    slot("reason").hidden = !opener.dataset.reason;
    slot("reason").required = Boolean(opener.dataset.reason);
    slot("reason").value = "";
    slot("post-label").textContent = opener.dataset.actionLabel || "";
    slot("post-label").disabled = false;
    slot("said").hidden = true;
  }
  const view = document.querySelector("iframe[data-frames]");
  if (view && opener.dataset.gap) view.contentWindow.postMessage({ gap: opener.dataset.gap }, location.origin);
  panel.hidden = false;
}

// A yes form (form[data-yes]: the panel's one action, the Buy button) as the signed-in owner's request: data-body's
// JSON to data-url with the reason when asked and the CSRF token; a green dot when done (the page read again with
// data-reload), a red one when refused (the detail as hover text and in the log, never on the page).
document.addEventListener("submit", async (event) => {
  const post = event.target.closest?.("form[data-yes]");
  if (!post) return;
  event.preventDefault();
  const said = post.querySelector('[data-slot="said"]'), button = post.querySelector('[data-slot="post-label"]');
  const body = JSON.parse(post.dataset.body);
  const reason = post.querySelector('[data-slot="reason"]');
  if (reason && !reason.hidden) body.reason = reason.value;
  button.disabled = true;
  const label = button.innerHTML;
  if (post.dataset.busy) button.innerHTML = `<i class="spinner" aria-hidden="true"></i> ${post.dataset.busy}`;
  let detail = "";
  try {
    const answer = await fetch(post.dataset.url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
      body: JSON.stringify(body),
    });
    const found = await answer.json().catch(() => ({}));
    detail = answer.ok ? found.said : String(found.detail || answer.status);
    if (!answer.ok) throw new Error(detail);
    said.className = "dot tone-done";
    if ("reload" in post.dataset) setTimeout(() => location.reload(), 800);
  } catch (error) {
    console.error("panel action refused", post.dataset.url, error);
    said.className = "dot tone-bad";
    button.innerHTML = label;
    button.disabled = false;
  }
  said.title = detail;
  said.hidden = false;
});
document.addEventListener("click", (event) => {
  const opener = event.target.closest("[data-opens]");
  if (opener) { event.preventDefault(); openPanel(opener); return; }
  const close = event.target.closest("[data-panel-close]");
  if (close) close.closest(".side-panel").hidden = true;
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") for (const panel of document.querySelectorAll(".side-panel")) panel.hidden = true;
  if (event.key === "Enter" && event.target.matches?.("[data-opens]")) openPanel(event.target);
});

// A tree branch with data-children="URL" (templates/pages/c/tree.html) loads its children when it first opens: the
// URL answers [node] as JSON with the fields of c/tree.html; a failed load turns its dot red, the detail to the log.
function treeRow(node) {
  const row = document.createElement(node.href ? "a" : "span");
  row.className = "node-row";
  if (node.href) row.href = node.href;
  if (node.tip) row.title = node.tip;
  if (node.panel) {
    Object.assign(row.dataset, { opens: "panel", title: node.panel.title || "", state: node.panel.state || "",
      tone: node.panel.tone || "", price: node.panel.price || "", action: node.panel.action || "",
      actionLabel: node.panel.action_label || "", picture: node.panel.picture || "", gap: node.panel.gap || "",
      body: node.panel.body || "", reason: node.panel.reason ? "1" : "" });
    row.tabIndex = 0;
    row.setAttribute("role", "button");
  }
  const dot = document.createElement("i");
  dot.className = `dot tone-${node.tone || "idle"}`;
  const label = document.createElement("span");
  label.className = "node-label";
  label.textContent = node.label;
  row.append(dot);
  if (node.picture) {
    const thumb = document.createElement("img");
    Object.assign(thumb, { className: "node-thumb", src: node.picture, alt: "", loading: "lazy" });
    row.append(thumb);
  }
  row.append(label);
  if (node.count !== undefined && node.count !== null) {
    const count = document.createElement("span");
    count.className = "node-count";
    count.textContent = node.count;
    row.append(count);
  }
  return row;
}
function treeList(nodes) {
  const list = document.createElement("ul");
  list.className = "tree";
  for (const node of nodes) {
    const item = document.createElement("li");
    if (node.children?.length || node.children_url) {
      const branch = document.createElement("details");
      const summary = document.createElement("summary");
      summary.append(treeRow(node));
      branch.append(summary);
      if (node.children_url) branch.dataset.children = node.children_url;
      else branch.append(treeList(node.children));
      item.append(branch);
    } else {
      item.append(treeRow(node));
    }
    list.append(item);
  }
  return list;
}
document.addEventListener("toggle", async (event) => {
  const branch = event.target;
  if (!branch.open || !branch.dataset?.children || branch.dataset.loaded) return;
  branch.dataset.loaded = "1";
  try {
    const answer = await fetch(branch.dataset.children, { credentials: "same-origin" });
    if (!answer.ok) throw new Error(`${answer.status}`);
    branch.append(treeList(await answer.json()));
  } catch (error) {
    console.error("tree branch not loaded", branch.dataset.children, error);
    branch.querySelector("summary .dot").className = "dot tone-bad";
    delete branch.dataset.loaded;
  }
}, true);

// While a concept draw is on its way ([data-reread][data-drawing], the Environment) the page reads itself again
// every few seconds and swaps in what it gets, so each card shows its draw as it lands; it stops once none is.
const REREAD_EVERY = 3000;
function reread() {
  const live = document.querySelector("[data-reread][data-drawing]");
  if (!live) return;
  setTimeout(async () => {
    try {
      const answer = await fetch(location.href, { credentials: "same-origin" });
      const fresh = new DOMParser().parseFromString(await answer.text(), "text/html").querySelector("[data-reread]");
      if (!answer.ok || !fresh) throw new Error(`page read again: ${answer.status}`);
      live.replaceWith(fresh);
    } catch (error) {
      console.error("draws on their way: page not read again", error);
    }
    reread();
  }, REREAD_EVERY);
}
reread();
