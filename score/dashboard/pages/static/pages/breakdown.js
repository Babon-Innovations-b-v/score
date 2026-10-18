// The place breakdown's live parts: a large picture the hosted export does not carry falls back to its thumbnail
// (data-fallback) before the page calls it missing, and a before and after slider wipes as it is dragged.

// Capture, and registered before dash.js: the fallback is tried first, and the "on its way" tile only after it.
document.addEventListener("error", (event) => {
  const image = event.target;
  if (!(image instanceof HTMLImageElement) || !image.dataset.fallback) return;
  if (image.getAttribute("src") === image.dataset.fallback) return;
  event.stopImmediatePropagation();
  image.src = image.dataset.fallback;
}, true);
for (const image of document.querySelectorAll("img[data-fallback]")) {
  if (image.complete && image.naturalWidth === 0 && image.getAttribute("src") !== image.dataset.fallback) {
    image.src = image.dataset.fallback;
  }
}

for (const wipe of document.querySelectorAll(".ba")) {
  const range = wipe.querySelector(".ba-range");
  range.addEventListener("input", () => wipe.style.setProperty("--cut", `${range.value}%`));
}
