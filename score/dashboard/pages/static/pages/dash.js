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
