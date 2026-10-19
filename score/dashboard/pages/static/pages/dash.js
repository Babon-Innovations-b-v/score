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
