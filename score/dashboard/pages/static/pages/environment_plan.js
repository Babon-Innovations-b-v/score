// The environment's plan page (pages/environment_plan.py): before dash.js posts Keep (form[data-plan]), its body gets
// each site's fields as the page holds them, grouped by its ground: its size and scene time (where it stands is the
// environment concept's setting).
const field = (row, name) => row.querySelector(`[data-f="${name}"]`)?.value.trim() ?? "";
const decimal = (text) => (text === "" ? null : Number(text.replace(",", ".")));

function plan() {
  return {
    maps: [...document.querySelectorAll("[data-plan-fields] [data-on]")].map((card) => ({
      on: card.dataset.on,
      sites: [...card.querySelectorAll('[data-row="site"]')].map((row) => ({
        place: row.dataset.place,
        size: field(row, "size").split(/\s*x\s*/).map(decimal),
        ...(field(row, "time") ? { time: field(row, "time") } : {}),
      })),
    })),
  };
}

document.addEventListener("submit", (event) => {
  const form = event.target.closest?.("form[data-plan]");
  if (!form) return;
  form.dataset.body = JSON.stringify({ ...JSON.parse(form.dataset.body), plan: plan() });
}, true);  // capture: before dash.js's own submit listener posts it
