// The pages' live parts: a fold that refreshes itself from the server every few seconds (data-refresh="URL"), and
// a frame scrubber under each film that says its frames a second (data-fps).
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
