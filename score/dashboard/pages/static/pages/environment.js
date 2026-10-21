// The environment concept page (pages/environment.py): before dash.js posts a yes form, its body gets what the page
// holds: the concept's fields (form[data-fields]: Save, Lock), the answer typed (form[data-answer]: Send) or the
// picture chosen with what it is for (form[data-upload]: Add, its bytes read as it is chosen).
const value = (root, name) => root.querySelector(`[data-f="${name}"]`)?.value ?? "";
const rows = (root, kind) => [...root.querySelectorAll(`[data-row="${kind}"]`)];
// a setting row: its whole row as kept (data-keep: the values it shows none of) with its fields as the page holds them;
// a field left empty clears that value, so a real body takes the reference table's again
const kept = (root, kind) => rows(root, kind).map((row) => {
  const found = JSON.parse(row.dataset.keep || "{}");
  for (const input of row.querySelectorAll("[data-f]")) {
    if (input.value.trim() === "") delete found[input.dataset.f];
    else found[input.dataset.f] = input.value.trim();
  }
  delete found.gravity;  // worked out again from its mass and radius
  return found;
}).filter((row) => Object.keys(row).length);

function concept() {
  const root = document.querySelector("[data-concept]");
  return {
    style: value(root, "style"),
    setting: {
      bodies: kept(root, "bodies"), lights: kept(root, "lights"), backdrops: kept(root, "backdrops"),
      plots: kept(root, "plots"), sites: kept(root, "sites"),
    },
    references: rows(root, "references").filter((row) => !row.querySelector('[data-f="drop"]')?.checked)
      .map((row) => ({ picture: row.dataset.picture, shows: value(row, "shows"), place: value(row, "place") })),
    places: rows(root, "places").map((row) => ({
      ...(row.dataset.place ? { place: row.dataset.place } : {}), name: value(row, "name"), holds: value(row, "holds"),
    })),
  };
}

const picked = new WeakMap();  // form: {name, data} of the picture chosen in it

document.addEventListener("change", (event) => {
  const form = event.target.closest?.("form[data-upload]");
  const file = event.target.files?.[0];
  if (!form || !file) return;
  const reader = new FileReader();
  reader.onload = () => picked.set(form, { name: file.name, data: String(reader.result).split(",", 2)[1] });
  reader.readAsDataURL(file);
});

document.addEventListener("submit", (event) => {
  const form = event.target.closest?.("form[data-yes]");
  if (!form) return;
  const body = JSON.parse(form.dataset.body);
  if ("fields" in form.dataset) body.concept = concept();
  if ("answer" in form.dataset) body.answer = value(form, "answer");
  if ("upload" in form.dataset) Object.assign(body, picked.get(form) || {}, { shows: value(form, "shows"), place: value(form, "place") });
  form.dataset.body = JSON.stringify(body);
}, true);  // capture: before dash.js's own submit listener posts it
