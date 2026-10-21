// The environment's plan page (pages/environment_plan.py): before dash.js posts Keep (form[data-plan]), its body gets
// each site's fields as the page holds them, grouped by world: its size, scene time, latitude and longitude.
const field = (row, name) => row.querySelector(`[data-f="${name}"]`)?.value.trim() ?? "";
const decimal = (text) => (text === "" ? null : Number(text.replace(",", ".")));

function plan() {
  return {
    maps: [...document.querySelectorAll("[data-plan-fields] [data-world]")].map((card) => ({
      world: card.dataset.world,
      sites: [...card.querySelectorAll('[data-row="site"]')].map((row) => ({
        place: row.dataset.place,
        size: field(row, "size").split(/\s*x\s*/).map(decimal),
        ...(field(row, "time") ? { time: field(row, "time") } : {}),
        latitude: decimal(field(row, "latitude")),
        longitude: decimal(field(row, "longitude")),
      })),
    })),
  };
}

document.addEventListener("submit", (event) => {
  const form = event.target.closest?.("form[data-plan]");
  if (!form) return;
  form.dataset.body = JSON.stringify({ ...JSON.parse(form.dataset.body), plan: plan() });
}, true);  // capture: before dash.js's own submit listener posts it
