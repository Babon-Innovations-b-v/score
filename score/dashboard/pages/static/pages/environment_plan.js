// The environment's plan page (pages/environment_plan.py). Each ground's map in true metres (x east, y south, north
// up): its ground with a grid, each top scene's own plan drawn at its site exactly as its plan page draws it
// (plan.js planSheet, read-only), its name over it, the true distances between sites, a north arrow and a scale bar;
// design.js then fits and zooms it. Before dash.js posts Keep (form[data-plan]), its body gets each site's scene time
// as the rail holds it, grouped by its ground (where it stands is the environment concept's setting, its size its
// plan's).
(() => {
  const SVG = "http://www.w3.org/2000/svg";
  const STEPS = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000];
  const data = JSON.parse(document.getElementById("ep-data").textContent);
  const shape = (name, attributes, parent) => {
    const found = document.createElementNS(SVG, name);
    for (const [key, value] of Object.entries(attributes)) found.setAttribute(key, value);
    parent.append(found);
    return found;
  };
  const label = (words, x, y, size, kind, parent) => {
    const found = shape("text", { x, y, "font-size": size, class: kind, "text-anchor": "middle" }, parent);
    found.textContent = words;
    return found;
  };
  // a site's box on the map: its footprint where it stands, else 10 m round its spot
  const box_of = (site) => {
    const points = (site.footprint || [[-10, -10], [10, 10]]).map(([x, y]) => [site.at[0] + x, site.at[1] + y]);
    const xs = points.map((point) => point[0]);
    const ys = points.map((point) => point[1]);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  };
  const step_for = (span, lines) => STEPS.find((step) => span / step <= lines) || STEPS[STEPS.length - 1];

  const site_drawn = (site, map, unit) => {
    const plan = data.plans[site.place];
    if (plan && plan.w) {
      const sheet = shape("svg", { "data-site": site.place, "data-place": site.place, class: "ep-site-plan" }, map);
      window.planSheet(sheet, structuredClone(plan), data.names, sheet, null);
      const view = sheet.viewBox.baseVal;  // the plan's own sheet: its outline from 0, 0 plus its margin
      Object.entries({ x: site.at[0] - plan.w / 2 + view.x, y: site.at[1] - plan.d / 2 + view.y,
                       width: view.width, height: view.height }).forEach(([key, value]) => sheet.setAttribute(key, value));
    } else {
      shape("circle", { cx: site.at[0], cy: site.at[1], r: unit * 0.6, class: "ep-unplanned", "data-site": site.place }, map);
    }
  };
  // its name over it, linked to its plan; drawn over every sheet, so a site under another still says where it is
  const site_named = (site, map, unit) => {
    const [left, top, right] = box_of(site);
    const link = shape("a", { href: `/concept/${site.place}/#plan-part` }, map);
    label(site.name, (left + right) / 2, top - unit * 0.9, unit * 1.5, "ep-name", link);
    shape("title", {}, link).textContent = `${site.name}: ${site.size ? site.size.join(" x ") + " m, its own plan" : "no plan yet"}`;
  };

  const north = (map, x, y, size) => {
    const group = shape("g", { class: "plan-north" }, map);
    shape("polygon", { points: `${x},${y - size / 2} ${x + size * 0.28},${y + size / 2} ${x},${y + size * 0.25}`, class: "fill" }, group);
    shape("polygon", { points: `${x},${y - size / 2} ${x - size * 0.28},${y + size / 2} ${x},${y + size * 0.25}` }, group);
    label("N", x, y - size * 0.62, size * 0.45, "plan-label north", group);
  };

  const scale_bar = (map, x, y, length, unit) => {
    const group = shape("g", { class: "plan-scale" }, map);
    for (let part = 0; part < 4; part += 1) {
      shape("rect", { x: x + (length / 4) * part, y: y - unit * 0.3, width: length / 4, height: unit * 0.3,
                      class: part % 2 ? "" : "fill" }, group);
    }
    label("0", x, y + unit, unit * 0.9, "plan-label dim", group);
    label(`${length} m`, x + length, y + unit, unit * 0.9, "plan-label dim", group);
  };

  for (const world of data.maps) {
    const map = document.querySelector(`svg[data-map="${world.on}"]`);
    if (!map) continue;
    const boxes = world.sites.map(box_of);
    const left = Math.min(...boxes.map((found) => found[0]));
    const top = Math.min(...boxes.map((found) => found[1]));
    const wide = Math.max(...boxes.map((found) => found[2])) - left;
    const deep = Math.max(...boxes.map((found) => found[3])) - top;
    const span = Math.max(wide, deep, 20);
    const unit = span / 55;  // the labels' size in metres
    const pad = span * 0.08 + unit * 3;
    const [x0, y0, x1, y1] = [left - pad, top - pad, left + wide + pad, top + deep + pad];
    map.setAttribute("viewBox", `${x0} ${y0} ${x1 - x0} ${y1 - y0}`);
    shape("rect", { x: x0, y: y0, width: x1 - x0, height: y1 - y0, class: "ep-ground" }, map);
    const grid = step_for(span, 12);
    const lines = shape("g", { class: "ep-grid" }, map);
    for (let x = Math.ceil(x0 / grid) * grid; x < x1; x += grid) shape("line", { x1: x, y1: y0, x2: x, y2: y1 }, lines);
    for (let y = Math.ceil(y0 / grid) * grid; y < y1; y += grid) shape("line", { x1: x0, y1: y, x2: x1, y2: y }, lines);
    const middles = Object.fromEntries(world.sites.map((site) => [site.place, site.at]));
    const area = (site) => { const [west, north_edge, east, south] = box_of(site); return (east - west) * (south - north_edge); };
    // the largest first, so a smaller site that stands on it shows over it (the gaps name the overlap)
    [...world.sites].sort((one, two) => area(two) - area(one)).forEach((site) => site_drawn(site, map, unit));
    for (const found of world.distances) {  // over the plans, faint: where two sites stand, and how far apart
      const [from, to] = [middles[found.from], middles[found.to]];
      shape("line", { x1: from[0], y1: from[1], x2: to[0], y2: to[1], class: "ep-apart" }, map);
      label(`${Math.round(found.metres)} m`, (from[0] + to[0]) / 2, (from[1] + to[1]) / 2 + unit * 0.35, unit * 1.1,
            "ep-metres", map);
    }
    for (const site of world.sites) site_named(site, map, unit);
    north(map, x1 - unit * 2, y0 + unit * 2.6, unit * 2.4);
    scale_bar(map, x0 + unit * 1.5, y1 - unit * 1.8, STEPS.filter((step) => step <= span / 4).pop() || 1, unit);
  }

  document.addEventListener("submit", (event) => {
    const form = event.target.closest?.("form[data-plan]");
    if (!form) return;
    const field = (row, name) => row.querySelector(`[data-f="${name}"]`)?.value.trim() ?? "";
    const plan = {
      maps: [...document.querySelectorAll("[data-plan-fields] [data-on]")].map((card) => ({
        on: card.dataset.on,
        sites: [...card.querySelectorAll('[data-row="site"]')].map((row) => ({
          place: row.dataset.place, ...(field(row, "time") ? { time: field(row, "time") } : {}),
        })),
      })),
    };
    form.dataset.body = JSON.stringify({ ...JSON.parse(form.dataset.body), plan });
  }, true);  // capture: before dash.js's own submit listener posts it
})();
