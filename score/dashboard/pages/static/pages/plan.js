// The plan review page (pages/plans.py): the plan drawn as an architect's floor plan in metres, an SVG laid out like
// the picture the prompt model is sent (score/review/plans.drawn: 40 px margins on a 900 px side), so a mark's share
// of it is the same area there: hatched walls with their thickness, doors with their swing, windows, stairs with the
// way up, floor levels (+0.00), terrain contours and spot heights, roofs overhead dashed, the items in their own
// shapes, the inside places in what holds them, dimension lines, a north arrow and a scale bar; under it a section
// A-A (score/review/plan_writing.py's schema). Hover a thing for its details. Drag an item, a zone or an inside place
// to move it (an inside place dropped on a building stands in it), its corner to resize it, a door along its wall, a
// standing spot; drag on the floor or on the concept to mark an area, a note each. The drop rule (owner, 2026-10-21):
// a box dropped fully inside a room is a thing in that room (no scene of its own, kept with the room); a room dropped
// on or resized over another is one shared room named from both; anywhere else a box is a child scene; each said with
// an undo. A gap's click lights it on the
// plan. Every edit saves on its own a moment later (his plan-edit request: the plan as he left it); removing an inside
// place right after renaming another merges them, said with an undo. Correct with notes and Make plan post at the
// price shown (his spend yes); Correct with no note typed sends his edits as the note. A refusal shows in red.
(() => {
  const page = document.getElementById("plan");
  if (!page) return;
  const place = page.dataset.place;
  const plan = JSON.parse(document.getElementById("plan-data").textContent);
  // an inside place is shown by its name (place.json `short`: "Cockpit and nav"); its id stays in the plan and the words
  // Correct sends
  const names = JSON.parse(document.getElementById("plan-names").textContent);
  const called = (id) => names[id] || id.replace(/_/g, " ");
  const title = (hold) => hold.name || called(hold.place);  // a shared room by the name made from both
  const svg = document.getElementById("plan-drawing");
  const cut = document.getElementById("plan-section");
  const editing = "marking" in page.dataset;
  const said = document.getElementById("plan-said");
  const notes = document.getElementById("plan-notes");
  const note = document.getElementById("plan-note");
  const SVG = "http://www.w3.org/2000/svg";
  const WALLS = "ON THE WALLS AND CEILING";
  const SIDES = ["N", "S", "E", "W"];
  const ASK_EVERY = 1500;
  const WALL = 0.3;  // metres: the thickness of a wall the plan draws round an outline that gives none
  const LOW = 0.5;  // metres: a thing standing higher than this is overhead, drawn dashed
  const wide = Math.max(plan.w, 0.5);
  const deep = Math.max(plan.d, 0.5);
  const longest = Math.max(wide, deep);
  const margin = (40 * longest) / 820;  // plans.drawn's 40 px at its scale
  const text = longest / 70;  // the labels' size in metres
  const round = (value) => Math.round(value * 100) / 100;
  const level = (value) => `${value < 0 ? "-" : "+"}${Math.abs(value).toFixed(2)}`;
  plan.holds = plan.holds || [];
  plan.people = plan.people || [];
  plan.shapes = plan.shapes || {};
  const outline = (plan.outline && plan.outline.length >= 3) ? plan.outline : [[0, 0], [wide, 0], [wide, deep], [0, deep]];
  const outdoor = plan.shell === "outdoor";
  // a wall's height when it gives none: the plan's words ("walls 15 m"), else 3 m
  const said_tall = Number((/walls?\D{0,12}?(\d+(?:\.\d+)?)\s*m\b/.exec(plan.height || "") || [])[1]) || 3;
  let lit = null;  // the gap shown: {names, at}

  // fitted to its panel, zoomed and panned by design.js: the marks' layer is exactly the drawing's box
  svg.setAttribute("viewBox", `${-margin} ${-margin} ${wide + 2 * margin} ${deep + 2 * margin}`);
  page.closest(".dpanel").classList.toggle("wide", wide > 1.25 * deep);  // a long plan takes the cockpit's whole width
  // the cockpit's plan column is as wide as the drawing at the height it gets (dash.css)
  page.closest(".design").style.setProperty("--plan-aspect", String((wide + 2 * margin) / (deep + 2 * margin)));

  // --- drawing helpers ----------------------------------------------------------------------------------------------
  const shape = (name, attributes, parent = svg) => {
    const found = document.createElementNS(SVG, name);
    for (const [key, value] of Object.entries(attributes)) found.setAttribute(key, value);
    parent.append(found);
    return found;
  };
  const label = (words, x, y, size, kind, parent = svg, anchor = "start") => {
    const found = shape("text", { x, y, "font-size": size, class: `plan-label ${kind}`, "text-anchor": anchor }, parent);
    found.textContent = words;
    return found;
  };
  const tip = (element, words) => { shape("title", {}, element).textContent = words; };
  const line = (from, to, kind, parent = svg) => shape("line", { x1: from[0], y1: from[1], x2: to[0], y2: to[1], class: kind }, parent);
  const joined = (points) => points.map((point) => `${point[0]},${point[1]}`).join(" ");
  const polygon = (points, kind, parent = svg) => shape("polygon", { points: joined(points), class: kind }, parent);
  const polyline = (points, kind, parent = svg) => shape("polyline", { points: joined(points), class: kind }, parent);
  const add = (a, b, scale = 1) => [a[0] + b[0] * scale, a[1] + b[1] * scale];
  const box = (points) => {
    const xs = points.map((point) => point[0]);
    const ys = points.map((point) => point[1]);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  };
  const middle = (points) => { const [x0, y0, x1, y1] = box(points); return [(x0 + x1) / 2, (y0 + y1) / 2]; };
  const inside = (point, points) => {
    let found = false;
    for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
      const [xi, yi] = points[i];
      const [xj, yj] = points[j];
      if ((yi > point[1]) !== (yj > point[1]) && point[0] < ((xj - xi) * (point[1] - yi)) / (yj - yi) + xi) found = !found;
    }
    return found;
  };
  const at = (event) => {
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    return point.matrixTransform(svg.getScreenCTM().inverse());
  };
  // an item's footprint in plan metres: its shape in 0..1 of its box (plan_checks.polygon_of)
  const footprint = (item) => {
    const [, x, y, w, d] = item;
    const found = plan.shapes[item[0]] || {};
    if (found.shape === "circle") {
      return Array.from({ length: 32 }, (_, i) => [x + w / 2 + (w / 2) * Math.cos((i * Math.PI) / 16),
                                                   y + d / 2 + (d / 2) * Math.sin((i * Math.PI) / 16)]);
    }
    if (found.shape === "polygon" && (found.points || []).length >= 3) return found.points.map(([u, v]) => [x + u * w, y + v * d]);
    return [[x, y], [x + w, y], [x + w, y + d], [x, y + d]];
  };

  // --- dragging: a move or a resize of one thing, the plan changed in place -------------------------------------
  // `what` says the edit in words (its line in what Correct sends when no note is typed)
  let dragging = null;
  const draggable = (element, start, move, done, what) => {
    if (!editing) return;
    element.classList.add("plan-drag");
    element.addEventListener("pointerdown", (event) => {
      event.stopPropagation();
      dragging = { from: at(event), was: start(), move, done, what, moved: false };
      svg.setPointerCapture(event.pointerId);
    });
  };
  svg.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    const point = at(event);
    dragging.move(dragging.was, round(point.x - dragging.from.x), round(point.y - dragging.from.y));
    dragging.moved = true;
    draw();
  });
  // `done` runs once the drag ends and may say what the drop made of it (a thing in a room, a shared room)
  svg.addEventListener("pointerup", () => {
    const said = dragging && dragging.moved && dragging.done ? dragging.done() : null;
    if (said !== null) { draw(); listed(); }
    if (dragging && dragging.moved) changed(said || dragging.what());
    dragging = null;
  });

  // --- the walls, their openings, the stairs ------------------------------------------------------------------------
  // the plan's walls, else (indoors) walls of WALL round its outline
  const walls = () => {
    if ((plan.walls || []).length || outdoor) return plan.walls || [];
    return outline.map((point, index) => ({ from: point, to: outline[(index + 1) % outline.length], thick: WALL }));
  };
  const wall_points = (wall) => {
    const half = (wall.thick || 0.2) / 2;
    if (wall.arc) {
      const { centre, radius, start, end } = wall.arc;
      const turns = Array.from({ length: 33 }, (_, i) => ((start + ((end - start) * i) / 32) * Math.PI) / 180);
      return [...turns.map((turn) => [centre[0] + (radius + half) * Math.cos(turn), centre[1] + (radius + half) * Math.sin(turn)]),
              ...turns.reverse().map((turn) => [centre[0] + (radius - half) * Math.cos(turn), centre[1] + (radius - half) * Math.sin(turn)])];
    }
    const [x1, y1] = wall.from;
    const [x2, y2] = wall.to;
    const length = Math.hypot(x2 - x1, y2 - y1) || 1;
    const across = [(-(y2 - y1) / length) * half, ((x2 - x1) / length) * half];
    return [add(wall.from, across), add(wall.to, across), add(wall.to, across, -1), add(wall.from, across, -1)];
  };
  // every opening: the plan's own, and each wall door of its doors (where it leads; draggable along its wall)
  const openings = () => {
    const own = plan.openings || [];
    const doors = plan.doors.map((door, index) => {
      if (!SIDES.includes(door[0])) return null;
      const spot = { N: [door[1], 0], S: [door[1], deep], W: [0, door[1]], E: [wide, door[1]] }[door[0]];
      const same = own.find((opening) => Math.hypot(opening.at[0] - spot[0], opening.at[1] - spot[1]) < 1.0);
      return { kind: "door", swing: "none", ...(same || {}), at: spot, wide: Number(door[2]),
               angle: door[0] === "N" || door[0] === "S" ? 0 : 90, to: ((plan.leads || {})[door[0]] || {}).to || (same || {}).to,
               words: door[3], door: index, same };
    }).filter(Boolean);
    return [...doors, ...own.filter((opening) => !doors.some((door) => door.same === opening))];
  };
  const thickness = (opening) => Math.max(WALL, ...walls().map((wall) => wall.thick || 0.2)) + 0.04;
  const draw_opening = (opening) => {
    const turn = ((opening.angle || 0) * Math.PI) / 180;
    const along = [Math.cos(turn), Math.sin(turn)];
    let across = [-Math.sin(turn), Math.cos(turn)];
    if (!inside(add(opening.at, across, 0.6), outline)) across = [-across[0], -across[1]];  // into the room
    const half = opening.wide / 2;
    const thick = thickness(opening);
    const ends = [add(opening.at, along, -half), add(opening.at, along, half)];
    const group = shape("g", { class: `plan-opening ${opening.kind}` });
    polygon([add(ends[0], across, -thick / 2), add(ends[1], across, -thick / 2), add(ends[1], across, thick / 2),
             add(ends[0], across, thick / 2)], "plan-gap", group);
    for (const end of ends) line(add(end, across, -thick / 2), add(end, across, thick / 2), "plan-jamb", group);
    const leaf = (hinge, other, length) => {
      const tip_at = add(hinge, across, length);
      line(hinge, tip_at, "plan-leaf", group);
      const from = Math.atan2(across[1], across[0]);
      let to = Math.atan2(other[1] - hinge[1], other[0] - hinge[0]);
      while (to - from > Math.PI) to -= 2 * Math.PI;
      while (to - from < -Math.PI) to += 2 * Math.PI;
      polyline(Array.from({ length: 13 }, (_, i) => {
        const angle = from + ((to - from) * i) / 12;
        return [hinge[0] + length * Math.cos(angle), hinge[1] + length * Math.sin(angle)];
      }), "plan-swing", group);
    };
    if (opening.kind === "window") {
      for (const offset of [-thick / 4, 0, thick / 4]) line(add(ends[0], across, offset), add(ends[1], across, offset), "plan-glass", group);
    } else if (opening.swing === "left") {
      leaf(ends[0], ends[1], opening.wide);
    } else if (opening.swing === "right") {
      leaf(ends[1], ends[0], opening.wide);
    } else if (opening.swing === "double") {
      leaf(ends[0], opening.at, half);
      leaf(ends[1], opening.at, half);
    } else if (opening.swing === "slide") {
      const offset = thick / 2 + 0.08;
      line(add(ends[0], across, offset), add(add(ends[1], along, half * 0.4), across, offset), "plan-leaf", group);
      line(add(opening.at, across, offset * 2.2), add(add(opening.at, along, half * 0.8), across, offset * 2.2), "plan-slide", group)
        .setAttribute("marker-end", "url(#plan-arrow)");
    } else if (opening.kind === "gate") {
      line(ends[0], ends[1], "plan-slide", group);
    }
    if (opening.to) label(`to ${opening.to}`, ...add(opening.at, across, -(thick / 2 + text * 1.1)), text * 0.85, "door", group, "middle");
    tip(group, `${opening.kind}${opening.to ? ` to ${opening.to}` : ""}, ${opening.wide} m wide` +
        `${opening.head ? `, ${opening.head} m high` : ""}${opening.sill ? `, sill ${level(opening.sill)}` : ""}` +
        `${opening.swing && opening.swing !== "none" ? `, ${opening.swing === "slide" ? "sliding" : `swings ${opening.swing}`}` : ""}` +
        `${opening.words ? `: ${opening.words}` : ""}`);
    if (opening.door !== undefined) {
      const door = plan.doors[opening.door];
      const across_wall = door[0] === "N" || door[0] === "S";
      draggable(group, () => door.slice(), (was, dx, dy) => {
        door[1] = round(Math.min(across_wall ? wide : deep, Math.max(0, was[1] + (across_wall ? dx : dy))));
      }, null, () => `moved the ${opening.kind}${opening.to ? ` to ${opening.to}` : ""} along its wall`);
    }
  };
  const draw_stair = (stair) => {
    const group = shape("g", { class: `plan-stair ${stair.kind}` });
    polygon(stair.points, "plan-stair-edge", group);
    const turn = ((stair.angle || 0) * Math.PI) / 180;
    const up = [Math.cos(turn), Math.sin(turn)];
    const side = [-Math.sin(turn), Math.cos(turn)];
    const along = stair.points.map((point) => point[0] * up[0] + point[1] * up[1]);
    const across = stair.points.map((point) => point[0] * side[0] + point[1] * side[1]);
    const [low, high, left, right] = [Math.min(...along), Math.max(...along), Math.min(...across), Math.max(...across)];
    const spot = (t, s) => [up[0] * t + side[0] * s, up[1] * t + side[1] * s];
    const steps = stair.steps || Math.max(2, Math.round(Math.abs(stair.to - stair.from) / 0.18));
    if (stair.kind !== "ramp") {
      for (let i = 1; i < steps; i += 1) line(spot(low + ((high - low) * i) / steps, left), spot(low + ((high - low) * i) / steps, right), "plan-tread", group);
    }
    const mid = (left + right) / 2;
    line(spot(low + (high - low) * 0.1, mid), spot(high - (high - low) * 0.08, mid), "plan-up", group).setAttribute("marker-end", "url(#plan-arrow)");
    label(stair.to >= stair.from ? "UP" : "DN", ...spot(low + (high - low) * 0.1, mid + text * 0.4), text * 0.75, "stair", group);
    tip(group, `${stair.kind}, ${level(stair.from)} to ${level(stair.to)}${stair.kind !== "ramp" ? `, ${steps} steps` : ""}`);
  };
  const level_mark = (height, point, words, parent = svg) => {
    const size = text * 0.7;
    polygon([[point[0] - size / 2, point[1] - size], [point[0] + size / 2, point[1] - size], [point[0], point[1]]], "plan-mark", parent);
    label(`${level(height)}${words ? ` ${words}` : ""}`, point[0] + size * 0.8, point[1] - size * 0.15, size * 1.2, "level", parent);
  };

  // --- items, zones, inside places ----------------------------------------------------------------------------------
  const lit_names = () => (lit ? lit.names : []);
  const corner = (rect, sized, group, size, name, done = null) => {
    const [x, y, w, h] = rect();
    const handle = shape("rect", { x: x + w - size * 0.6, y: y + h - size * 0.6, width: size * 0.6, height: size * 0.6,
                                   class: "plan-corner" }, group);
    draggable(handle, rect, (was, dx, dy) => sized(Math.max(0.1, round(was[2] + dx)), Math.max(0.1, round(was[3] + dy))),
              done, () => { const [, , cw, ch] = rect(); return `resized ${name()} to ${cw} x ${ch} m`; });
  };
  const rows_of = (name) => (plan.rows || {})[name] || [];
  const item_shape = (item) => {
    const [name, x, y, w, d, facing, kind] = item;
    const form = plan.shapes[name] || {};
    const over = (form.base || 0) >= LOW;
    const lights = lit_names().some((found) => found === name || rows_of(name).includes(found));
    const group = shape("g", { class: `plan-${kind === "zone" ? "zone" : "item"}${over ? " over" : ""}${lights ? " lit" : ""}` });
    if (form.shape === "circle") shape("ellipse", { cx: x + w / 2, cy: y + d / 2, rx: w / 2, ry: d / 2 }, group);
    else polygon(footprint(item), "", group);
    const size = Math.max(Math.min(w / 7, d / 2.2, text), longest / 140);
    const short = name.toLowerCase().split(/[(:,]/)[0].trim().slice(0, 28);
    const fits = Math.min(text, (w * 0.92) / (short.length * 0.56), d * 0.5);  // its label inside it, else none
    if (fits >= longest / 260 && kind === "zone") label(short, x + fits * 0.3, y + fits * 1.2, fits * 0.8, "zone", group);  // its corner: a zone holds things
    else if (fits >= longest / 260 && !over) label(short, x + w / 2, y + d / 2 + fits * 0.35, fits, "item", group, "middle");
    if (facing) {  // its front: a tick on that side
      const front = { N: [[x + w * 0.35, y], [x + w * 0.65, y]], S: [[x + w * 0.35, y + d], [x + w * 0.65, y + d]],
                      W: [[x, y + d * 0.35], [x, y + d * 0.65]], E: [[x + w, y + d * 0.35], [x + w, y + d * 0.65]] }[facing];
      line(front[0], front[1], "plan-front", group);
    }
    const holding = plan.holds.filter((hold) => hold.row && rows_of(name)[0] === hold.row).map((hold) => hold.place);
    tip(group, `${name.toLowerCase()}${rows_of(name).length ? ` (${rows_of(name).join(", ").replace(/_/g, " ")})` : ""}: ` +
        `${w} x ${d}${form.tall ? ` x ${form.tall}` : ""} m${form.base ? `, at ${level(form.base)}` : ""}` +
        `${facing ? `, facing ${facing}` : ""}${holding.length ? `; holds ${holding.join(", ")}` : ""}`);
    const rect = () => item.slice(1, 5);
    draggable(group, rect, (was, dx, dy) => item.splice(1, 2, round(was[0] + dx), round(was[1] + dy)), null,
              () => `moved ${short} to ${item[1]}, ${item[2]} m`);
    corner(rect, (cw, ch) => item.splice(3, 2, cw, ch), group, size, () => short);
  };
  // an inside place dropped on a building stands in it: the item under its middle (its row), else this place's floor
  const holder_under = (hold) => {
    const spot = [hold.x + hold.w / 2, hold.y + hold.d / 2];
    const under = plan.items.filter((item) => item[6] === "item" && item[0] !== WALLS && rows_of(item[0]).length &&
                                               inside(spot, footprint(item)))
      .sort((a, b) => a[3] * a[4] - b[3] * b[4])[0];
    return under ? rows_of(under[0])[0] : null;
  };
  const hold_shape = (hold) => {
    const group = shape("g", { class: `plan-hold${lit_names().includes(hold.place) ? " lit" : ""}` });
    shape("rect", { x: hold.x, y: hold.y, width: hold.w, height: hold.d }, group);
    const size = Math.max(Math.min(hold.w / 6, hold.d / 2.5, text * 1.2), longest / 140);
    label(title(hold), hold.x + size * 0.4, hold.y + size * 1.2, size, "hold", group);
    tip(group, `${title(hold)}: ${hold.w} x ${hold.d} m, ` +
        `${hold.row ? `inside the ${hold.row.replace(/_/g, " ")}` : "on this scene's own floor"}`);
    const rect = () => [hold.x, hold.y, hold.w, hold.d];
    draggable(group, rect, (was, dx, dy) => Object.assign(hold, { x: round(was[0] + dx), y: round(was[1] + dy) }),
              () => dropped(hold),
              () => `moved ${hold.place.replace(/_/g, " ")} to ${hold.x}, ${hold.y} m${hold.row ? `, inside the ${hold.row.replace(/_/g, " ")}` : ""}`);
    corner(rect, (w, d) => Object.assign(hold, { w, d }), group, size, () => title(hold), () => overlapped(hold, false));
    (hold.things || []).forEach((thing) => thing_shape(thing, hold));
  };
  // a thing in a room: its box at its spot in the room (its corner from the room's), its name in it
  const thing_shape = (thing, hold) => {
    const group = shape("g", { class: "plan-thing" });
    const rect = () => [hold.x + thing.x, hold.y + thing.y, thing.w, thing.d];
    shape("rect", { x: rect()[0], y: rect()[1], width: thing.w, height: thing.d }, group);
    const size = Math.max(Math.min(thing.w / 5, thing.d / 2, text), longest / 160);
    label(thing.name, rect()[0] + thing.w / 2, rect()[1] + thing.d / 2 + size * 0.35, size, "thing", group, "middle");
    tip(group, `${thing.name}: ${thing.w} x ${thing.d} m, in ${title(hold)}`);
    draggable(group, rect, (was, dx, dy) => Object.assign(thing, { x: round(was[0] + dx - hold.x), y: round(was[1] + dy - hold.y) }),
              () => thing_dropped(thing, hold), () => `moved ${thing.name} in ${hold.place.replace(/_/g, " ")}`);
    corner(rect, (w, d) => Object.assign(thing, { w, d }), group, size, () => thing.name);
  };
  const spot = (where) => {
    const dot = shape("circle", { cx: where[0], cy: where[1], r: longest / 110, class: "plan-spot" });
    tip(dot, "a standing spot");
    draggable(dot, () => where.slice(), (was, dx, dy) => where.splice(0, 2, round(was[0] + dx), round(was[1] + dy)), null,
              () => "moved a standing spot");
  };

  // --- the sheet: dimensions, north, scale, the cut -----------------------------------------------------------------
  const dimension = (from, to, offset, words, vertical) => {
    const group = shape("g", { class: "plan-dim" });
    const shift = vertical ? [offset, 0] : [0, offset];
    const a = add(from, shift);
    const b = add(to, shift);
    line(a, b, "plan-dim-line", group);
    for (const [end, base] of [[a, from], [b, to]]) {
      line(base, add(end, shift, 0.15), "plan-dim-ext", group);
      line(add(end, [-1, 1], text * 0.25), add(end, [1, -1], text * 0.25), "plan-dim-tick", group);
    }
    const words_at = add(middle([a, b]), vertical ? [-text * 0.35, 0] : [0, -text * 0.35]);
    const found = label(words, ...words_at, text * 0.9, "dim", group, "middle");
    if (vertical) found.setAttribute("transform", `rotate(-90 ${words_at[0]} ${words_at[1]})`);
  };
  const north = () => {
    const size = margin * 0.55;
    const centre = [wide + margin * 0.5, -margin * 0.45];
    const group = shape("g", { class: "plan-north" });
    polygon([[centre[0], centre[1] - size / 2], [centre[0] + size * 0.28, centre[1] + size / 2], [centre[0], centre[1] + size * 0.25]], "fill", group);
    polygon([[centre[0], centre[1] - size / 2], [centre[0] - size * 0.28, centre[1] + size / 2], [centre[0], centre[1] + size * 0.25]], "", group);
    label("N", centre[0], centre[1] - size * 0.6, size * 0.45, "north", group, "middle");
    tip(group, "north, up the page");
  };
  const scale_bar = () => {
    const length = [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500].filter((value) => value <= wide / 4).pop() || 0.5;
    const y = deep + margin * 0.45;
    const group = shape("g", { class: "plan-scale" });
    for (let i = 0; i < 4; i += 1) {
      shape("rect", { x: (length / 4) * i, y: y - text * 0.25, width: length / 4, height: text * 0.25, class: i % 2 ? "" : "fill" }, group);
    }
    label("0", 0, y + text * 0.9, text * 0.8, "dim", group, "middle");
    label(`${length} m`, length, y + text * 0.9, text * 0.8, "dim", group, "middle");
    tip(group, `scale: ${length} metres`);
  };
  const section_y = () => Math.min(deep, Math.max(0, (plan.section || {}).y ?? deep / 2));
  const cut_line = () => {
    const y = section_y();
    const group = shape("g", { class: "plan-cut" });
    line([-margin * 0.6, y], [wide + margin * 0.6, y], "plan-cut-line", group);
    for (const x of [-margin * 0.6, wide + margin * 0.6]) label("A", x, y - text * 0.4, text, "cut", group, "middle");
    tip(group, "where the section A-A below cuts the scene");
  };

  const defs = () => {
    const found = shape("defs", {});
    const hatch = shape("pattern", { id: "plan-hatch", patternUnits: "userSpaceOnUse", width: longest / 160,
                                     height: longest / 160, patternTransform: "rotate(45)" }, found);
    shape("rect", { width: longest / 160, height: longest / 160, class: "plan-hatch-ground" }, hatch);
    shape("line", { x1: 0, y1: 0, x2: 0, y2: longest / 160, class: "plan-hatch-line" }, hatch);
    const arrow = shape("marker", { id: "plan-arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6,
                                    orient: "auto-start-reverse" }, found);
    shape("path", { d: "M0,0 L10,5 L0,10 z", class: "plan-arrow-head" }, arrow);
  };

  // a thing drawn on the plan: no zone, not the walls-and-ceiling item, no shell or ground row, and no backdrop the
  // writer placed far wider than the place (a skyline)
  const structure = new Set(plan.structure || []);
  const drawn = (item) => item[0] !== WALLS && item[6] !== "zone" && !rows_of(item[0]).some((row) => structure.has(row)) &&
    !(item[3] > wide * 1.5 || item[4] > deep * 1.5);
  const numbers = document.getElementById("plan-numbers");
  const draw = () => {
    svg.replaceChildren();
    defs();
    polygon(outline, outdoor ? "plan-site" : "plan-floor");
    for (const area of plan.levels || []) {
      const group = shape("g", { class: "plan-level" });
      polygon(area.points, "", group);
      tip(group, `${area.name || "floor"} at ${level(area.height)}`);
    }
    const terrain = plan.terrain || {};
    for (const contour of terrain.contours || []) {
      const group = shape("g", { class: "plan-contour" });
      polyline(contour.points, "", group);
      const spot_at = contour.points[Math.floor(contour.points.length / 2)];
      label(level(contour.height), spot_at[0], spot_at[1] - text * 0.2, text * 0.7, "contour", group, "middle");
      tip(group, `ground at ${level(contour.height)}`);
    }
    for (const [x, y, height] of terrain.spots || []) {
      const group = shape("g", { class: "plan-spot-height" });
      line([x - text * 0.3, y - text * 0.3], [x + text * 0.3, y + text * 0.3], "", group);
      line([x - text * 0.3, y + text * 0.3], [x + text * 0.3, y - text * 0.3], "", group);
      label(level(height), x + text * 0.4, y - text * 0.3, text * 0.7, "contour", group);
      tip(group, `spot height ${level(height)}`);
    }
    (plan.stairs || []).forEach(draw_stair);
    plan.items.filter((item) => drawn(item) && !((plan.shapes[item[0]] || {}).base >= LOW)).forEach(item_shape);
    plan.items.filter((item) => item[6] === "zone").forEach(item_shape);
    plan.holds.forEach(hold_shape);  // over the items: the hangar's rooms in its ship
    for (const wall of walls()) {
      const found = polygon(wall_points(wall), "plan-wall");
      tip(found, `wall ${wall.thick || 0.2} m thick${wall.tall ? `, ${wall.tall} m high` : ""}`);
    }
    openings().forEach(draw_opening);
    plan.items.filter((item) => drawn(item) && (plan.shapes[item[0]] || {}).base >= LOW).forEach(item_shape);
    for (const roof of plan.roofs || []) {
      const group = shape("g", { class: `plan-roof ${roof.kind}` });
      polygon(roof.points, "", group);
      if (roof.kind === "dome") {
        const centre = middle(roof.points);
        polygon(roof.points.map((point) => add(centre, [point[0] - centre[0], point[1] - centre[1]], 0.5)), "", group);
      }
      tip(group, `${roof.kind} roof overhead, ${level(roof.eave)}${roof.top !== roof.eave ? ` to ${level(roof.top)}` : ""}`);
    }
    const marks = (plan.levels || []).length ? plan.levels : [{ height: 0, points: [[text * 2, text * 2]] }];
    for (const area of marks) level_mark(area.height, middle(area.points), "");
    plan.people.forEach(spot);
    dimension([0, 0], [wide, 0], -margin * 0.5, wide.toFixed(2), false);
    dimension([0, 0], [0, deep], -margin * 0.5, deep.toFixed(2), true);
    cut_line();
    north();
    scale_bar();
    if (lit && lit.at) shape("circle", { cx: lit.at[0], cy: lit.at[1], r: longest / 30, class: "plan-ring" });
    const things = plan.items.filter(drawn).length;
    numbers.textContent = `${round(wide)} x ${round(deep)} m, ${things} things`;
    section();
  };

  // --- the section A-A: what the cut crosses, heights true to scale -------------------------------------------------
  // the stretches [x0, x1] where a horizontal line at `y` runs inside `points`
  const spans = (points, y) => {
    const xs = [];
    points.forEach((point, index) => {
      const next = points[(index + 1) % points.length];
      if ((point[1] > y) !== (next[1] > y)) xs.push(point[0] + ((y - point[1]) * (next[0] - point[0])) / (next[1] - point[1]));
    });
    xs.sort((a, b) => a - b);
    return Array.from({ length: Math.floor(xs.length / 2) }, (_, i) => [xs[2 * i], xs[2 * i + 1]]);
  };
  // the ground's height at x along the cut: the spot heights and contours weighed by nearness, else +0.00
  const ground_at = (x, y) => {
    const terrain = plan.terrain || {};
    const known = [...(terrain.spots || []), ...(terrain.contours || []).flatMap((contour) => contour.points.map((point) => [...point, contour.height]))];
    if (!known.length) return 0;
    let weight = 0;
    let sum = 0;
    for (const [kx, ky, height] of known) {
      const far = (kx - x) ** 2 + (ky - y) ** 2;
      if (far < 1e-6) return height;
      weight += 1 / far;
      sum += height / far;
    }
    return sum / weight;
  };
  const section = () => {
    if (!cut) return;
    cut.replaceChildren();
    const y = section_y();
    const crossed = plan.items.filter(drawn)
      .map((item) => ({ item, form: plan.shapes[item[0]] || {}, spans: spans(footprint(item), y) }))
      .filter((found) => found.spans.length);
    const heights = [0, ...(plan.levels || []).map((area) => area.height), ...(plan.roofs || []).flatMap((roof) => [roof.eave, roof.top]),
                     ...walls().map((wall) => wall.tall || said_tall), ...crossed.map((found) => (found.form.base || 0) + (found.form.tall || 0))];
    const samples = Array.from({ length: 81 }, (_, i) => [(wide * i) / 80, ground_at((wide * i) / 80, y)]);
    const low = Math.min(...heights, ...samples.map((sample) => sample[1])) - Math.max(1, longest / 60);
    const high = Math.max(3, ...heights) + Math.max(1, longest / 60);
    cut.setAttribute("viewBox", `${-margin} ${-high} ${wide + 2 * margin} ${high - low}`);
    const up = (height) => -height;  // heights up the page
    const draw_cut = (name, attributes, parent = cut) => shape(name, attributes, parent);
    const ground = [...samples.map(([x, height]) => [x, up(height)]), [wide, up(low)], [0, up(low)]];
    draw_cut("polygon", { points: joined(ground), class: "plan-earth" });
    for (const area of plan.levels || []) {
      for (const [x0, x1] of spans(area.points, y)) {
        const slab = draw_cut("rect", { x: x0, y: up(area.height), width: x1 - x0, height: Math.max(0.15, longest / 300), class: "plan-slab" });
        tip(slab, `${area.name || "floor"} at ${level(area.height)}`);
      }
    }
    for (const wall of walls()) {
      const tall = wall.tall || said_tall;
      const thick = wall.thick || 0.2;
      let xs = [];
      if (wall.arc) {
        const { centre, radius, start, end } = wall.arc;
        const rest = radius ** 2 - (y - centre[1]) ** 2;
        if (rest >= 0) {
          xs = [centre[0] - Math.sqrt(rest), centre[0] + Math.sqrt(rest)].filter((x) => {
            let turn = (Math.atan2(y - centre[1], x - centre[0]) * 180) / Math.PI;
            while (turn < Math.min(start, end)) turn += 360;
            return turn <= Math.max(start, end);
          });
        }
      } else if ((wall.from[1] - y) * (wall.to[1] - y) <= 0 && wall.from[1] !== wall.to[1]) {
        xs = [wall.from[0] + ((y - wall.from[1]) * (wall.to[0] - wall.from[0])) / (wall.to[1] - wall.from[1])];
      }
      for (const x of xs) {
        const found = draw_cut("rect", { x: x - thick / 2, y: up(tall), width: thick, height: tall, class: "plan-wall" });
        tip(found, `wall ${thick} m thick, ${tall} m high`);
      }
    }
    for (const roof of plan.roofs || []) {
      const [rx0, ry0, rx1, ry1] = box(roof.points);
      const [cx, cy] = [(rx0 + rx1) / 2, (ry0 + ry1) / 2];
      for (const [x0, x1] of spans(roof.points, y)) {
        const points = Array.from({ length: 41 }, (_, i) => {
          const x = x0 + ((x1 - x0) * i) / 40;
          const across = (x - cx) / Math.max((rx1 - rx0) / 2, 0.01);
          const down = (y - cy) / Math.max((ry1 - ry0) / 2, 0.01);
          const rise = { dome: Math.sqrt(Math.max(0, 1 - across ** 2 - down ** 2)), vault: Math.sqrt(Math.max(0, 1 - across ** 2)),
                         pitched: 1 - Math.abs(across), shed: (x - x0) / Math.max(x1 - x0, 0.01) }[roof.kind] || 0;
          return [x, up(roof.eave + (roof.top - roof.eave) * rise)];
        });
        const found = draw_cut("polyline", { points: joined(points), class: "plan-roof-cut" });
        tip(found, `${roof.kind} roof, ${level(roof.eave)}${roof.top !== roof.eave ? ` to ${level(roof.top)}` : ""}`);
      }
    }
    for (const stair of plan.stairs || []) {
      for (const [x0, x1] of spans(stair.points, y)) {
        const east = Math.cos(((stair.angle || 0) * Math.PI) / 180) >= 0;
        const found = draw_cut("line", { x1: x0, y1: up(east ? stair.from : stair.to), x2: x1, y2: up(east ? stair.to : stair.from), class: "plan-stair-cut" });
        tip(found, `${stair.kind}, ${level(stair.from)} to ${level(stair.to)}`);
      }
    }
    for (const { item, form, spans: found } of crossed) {
      const base = form.base || 0;
      const tall = form.tall || 1;
      for (const [x0, x1] of found) {
        const group = draw_cut("g", { class: "plan-item-cut" });
        draw_cut("rect", { x: x0, y: up(base + tall), width: x1 - x0, height: tall }, group);
        tip(group, `${item[0].toLowerCase()}: ${tall} m high${base ? `, at ${level(base)}` : ""}`);
      }
    }
    // the floors' and roofs' levels, each far enough from the last to be read
    const marked = [...new Set([0, ...(plan.levels || []).map((area) => area.height),
                                ...(plan.roofs || []).flatMap((roof) => [roof.eave, roof.top])].map(round))]
      .sort((a, b) => a - b).filter((height, index, all) => index === 0 || height - all[index - 1] >= text * 1.4);
    for (const height of marked) {
      level_mark(height, [-margin * 0.85, up(height)], "", cut);
      draw_cut("line", { x1: -margin * 0.3, y1: up(height), x2: 0, y2: up(height), class: "plan-dim-ext" });
    }
    label("A-A", wide + margin * 0.05, up(high) + text * 1.2, text, "cut", cut);
  };

  // --- the inside places: their names beside the drawing --------------------------------------------------------
  const places = document.getElementById("plan-places");
  const listed = () => {
    places.replaceChildren();
    plan.holds.forEach((hold, index) => {
      const row = document.createElement("li");
      row.title = hold.row ? `inside the ${hold.row.replace(/_/g, " ")}` : "on this scene's own floor";
      if (!editing) {
        row.innerHTML = "<span data-v></span>";
        row.querySelector("span").textContent = title(hold);
        places.append(row);
        (hold.things || []).forEach((thing) => thing_row(thing, hold));
        return;
      }
      row.innerHTML = '<input type="text" title="its name"><button type="button" class="concept-drop" title="remove this scene" ' +
        'aria-label="remove">&times;</button>';
      const input = row.querySelector("input");
      input.value = title(hold);
      input.addEventListener("change", () => {
        const typed = input.value.trim();
        if (hold.name) {  // a shared room keeps its id: its name is his
          const was_name = hold.name;
          hold.name = typed || hold.name;
          input.value = title(hold);
          draw();
          if (hold.name !== was_name) changed(`renamed the shared room ${hold.place.replace(/_/g, " ")} to ${hold.name}`);
          return;
        }
        const was = hold.place;
        if (typed && typed !== called(was)) {
          hold.place = typed.toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "") || hold.place;
          names[hold.place] = typed;
        }
        input.value = called(hold.place);
        draw();
        if (hold.place === was) return;
        renamed = hold;
        changed(`renamed ${was.replace(/_/g, " ")} to ${hold.place.replace(/_/g, " ")}`);
      });
      row.querySelector("button").addEventListener("click", () => removed(index));
      places.append(row);
      (hold.things || []).forEach((thing) => thing_row(thing, hold));
    });
  };
  // a thing in a room: under its room, its name to change, x to take it out
  const thing_row = (thing, hold) => {
    const row = document.createElement("li");
    row.className = "plan-thing-row";
    row.title = `a thing in ${title(hold)}: no scene of its own`;
    if (!editing) {
      row.innerHTML = "<span data-v></span>";
      row.querySelector("span").textContent = thing.name;
      places.append(row);
      return;
    }
    row.innerHTML = '<input type="text" title="its name"><button type="button" class="concept-drop" title="take it out of the room" ' +
      'aria-label="remove">&times;</button>';
    const input = row.querySelector("input");
    input.value = thing.name;
    input.addEventListener("change", () => {
      const was = thing.name;
      thing.name = input.value.trim() || thing.name;
      input.value = thing.name;
      draw();
      if (thing.name !== was) changed(`renamed ${was} in ${hold.place.replace(/_/g, " ")} to ${thing.name}`);
    });
    row.querySelector("button").addEventListener("click", () => {
      hold.things.splice(hold.things.indexOf(thing), 1);
      if (!hold.things.length) delete hold.things;
      listed();
      draw();
      changed(`removed ${thing.name} from ${hold.place.replace(/_/g, " ")}`);
    });
    places.append(row);
  };
  const adding = document.getElementById("plan-add");
  if (adding) {
    adding.addEventListener("click", () => {
      const side = Math.max(1, Math.min(wide, deep) / 4);
      plan.holds.push({ place: free_id(`place_${plan.holds.length + 1}`), row: null, x: round(margin), y: round(margin),
                        w: round(side), d: round(side) });
      listed();
      draw();
      changed(`added ${plan.holds.at(-1).place.replace(/_/g, " ")}`);
    });
  }

  // --- the gaps: a click lights the thing on the plan ---------------------------------------------------------------
  for (const gap of document.querySelectorAll("[data-gap]")) {
    gap.addEventListener("click", () => {
      const was = gap.classList.contains("lit");
      for (const other of document.querySelectorAll("[data-gap]")) other.classList.remove("lit");
      lit = was ? null : { names: [gap.dataset.item, gap.dataset.with].filter(Boolean), at: gap.dataset.at ? JSON.parse(gap.dataset.at) : null };
      if (!was) gap.classList.add("lit");
      draw();
    });
  }

  // --- marks: on the plan's floor (1, 2, ...) and on the concept (P1, P2, ...), a note each ----------------------
  const marks = [];
  const share = (event, layer) => {
    const bounds = layer.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (event.clientX - bounds.left) / bounds.width)),
            Math.min(1, Math.max(0, (event.clientY - bounds.top) / bounds.height))];
  };
  const framed = (mark) => Object.assign(mark.box.style, { left: `${mark.x * 100}%`, top: `${mark.y * 100}%`,
                                                           width: `${mark.w * 100}%`, height: `${mark.h * 100}%` });
  const renumber = () => {
    for (const [prefix, own] of [["", marks.filter((mark) => !mark.on)], ["P", marks.filter((mark) => mark.on)]]) {
      own.forEach((mark, index) => {
        mark.box.dataset.n = `${prefix}${index + 1}`;
        mark.row.querySelector("b").textContent = `${prefix}${index + 1}`;
      });
    }
  };
  const noted = (mark) => {
    mark.row = document.createElement("li");
    mark.row.innerHTML = '<b data-v></b><input type="text" placeholder="what to change here">' +
      '<button type="button" class="concept-drop" title="remove this mark" aria-label="remove">&times;</button>';
    mark.row.querySelector("button").addEventListener("click", () => {
      marks.splice(marks.indexOf(mark), 1);
      mark.box.remove();
      mark.row.remove();
      renumber();
    });
    notes.append(mark.row);
    renumber();
    mark.row.querySelector("input").focus();
  };
  const marking = (start_on, layer, on) => {
    let open = null;
    start_on.addEventListener("pointerdown", (event) => {
      if (dragging) return;
      const [x, y] = share(event, layer);
      open = { from: [x, y], x, y, w: 0, h: 0, on, box: document.createElement("div") };
      open.box.className = "concept-mark";
      layer.append(open.box);
      start_on.setPointerCapture(event.pointerId);
    });
    start_on.addEventListener("pointermove", (event) => {
      if (!open) return;
      const [x, y] = share(event, layer);
      Object.assign(open, { x: Math.min(x, open.from[0]), y: Math.min(y, open.from[1]),
                            w: Math.abs(x - open.from[0]), h: Math.abs(y - open.from[1]) });
      framed(open);
    });
    start_on.addEventListener("pointerup", () => {
      const mark = open;
      open = null;
      if (!mark) return;
      if (mark.w < 0.01 || mark.h < 0.01) { mark.box.remove(); return; }
      marks.push(mark);
      noted(mark);
    });
  };
  if (editing) {
    marking(svg, document.getElementById("plan-marks"), null);
    for (const layer of document.querySelectorAll(".plan-concept .concept-marks")) marking(layer, layer, layer.dataset.on);
  }
  const sent = (mark) => ({ x: mark.x, y: mark.y, w: mark.w, h: mark.h, note: mark.row.querySelector("input").value,
                            ...(mark.on ? { on: mark.on } : {}) });

  // --- requests ---------------------------------------------------------------------------------------------------
  const cookie = (name) => (document.cookie.split("; ").find((part) => part.startsWith(name + "=")) || "").split("=")[1];
  const post = async (path, body) => {
    const answer = await fetch(`/plan/${place}/${path}/`, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
      body: JSON.stringify(body),
    });
    const found = await answer.json().catch(() => ({}));
    if (!answer.ok) throw new Error(String(found.detail || answer.status));
    return found;
  };
  // a refusal says why on the page, in red (owner, 2026-10-21: a refused Correct showed nothing)
  const told = document.getElementById("plan-told");
  const tell = (tone, words) => {
    said.className = `dot tone-${tone}`;
    said.title = words;
    said.hidden = false;
    if (told) told.textContent = tone === "bad" ? words : "";
  };
  const busy = document.getElementById("plan-busy");
  const buttons = [...document.querySelectorAll("#plan-rail button")];
  const waiting = () => {
    buttons.forEach((button) => { button.disabled = true; });
    busy.hidden = false;
    const ask = async () => {
      const found = await fetch(`/plan/${place}/state/`, { credentials: "same-origin" }).then((answer) => answer.json())
        .catch(() => null);
      if (!found || found.pending) { setTimeout(ask, ASK_EVERY); return; }
      location.reload();
    };
    setTimeout(ask, ASK_EVERY);
  };

  // --- his edits save on their own: each one his plan-edit request, a moment after the last change ---------------
  const SAVE_AFTER = 1200;  // ms
  const saved = document.getElementById("plan-saved");
  const edits = [];  // what he changed, in words: Correct sends them when no note is typed
  let timer = null;
  let saving = Promise.resolve();
  const shown_state = (words, tone) => {
    if (!saved) return;
    saved.textContent = words;
    saved.className = `plan-saved tone-${tone}`;
  };
  const save = () => {
    clearTimeout(timer);
    timer = null;
    shown_state("saving", "idle");
    saving = saving.then(() => post("keep", { plan })).then(() => shown_state("saved", "done"), (error) => {
      shown_state("not saved", "bad");
      tell("bad", error.message);
      console.error("plan edit refused", error);
    });
    return saving;
  };
  const changed = (words) => {
    if (!editing) return;
    if (edits.at(-1) !== words) edits.push(words);
    shown_state("unsaved", "idle");
    clearTimeout(timer);
    timer = setTimeout(save, SAVE_AFTER);
  };
  window.addEventListener("beforeunload", () => { if (timer) save(); });

  // removing an inside place right after renaming another is a merge: the renamed one holds both (owner, 2026-10-21:
  // "cockpit" renamed "cockpit and nav", then "navigation" removed); said, with an undo, never asked
  let renamed = null;
  const merged_note = document.getElementById("plan-merged");
  // said with an undo: `undo` puts the plan back, `back` says that in words
  const undoable = (words, undo, back) => {
    if (!merged_note) return;
    merged_note.hidden = false;
    merged_note.querySelector("[data-slot]").textContent = words;
    merged_note.querySelector("button").onclick = () => {
      undo();
      merged_note.hidden = true;
      listed();
      draw();
      changed(back);
    };
  };
  const removed = (index) => {
    const [gone] = plan.holds.splice(index, 1);
    const into = renamed && plan.holds.includes(renamed) ? renamed : null;
    const name = (hold) => hold.place.replace(/_/g, " ");
    listed();
    draw();
    changed(into ? `merged ${name(gone)} into ${name(into)}` : `removed ${name(gone)}`);
    if (into) undoable(`merged ${called(gone.place)} into ${title(into)}`, () => plan.holds.splice(index, 0, gone),
                       `kept ${name(gone)} apart from ${name(into)}`);
  };

  // --- the drop rule (owner, 2026-10-21): a box dropped fully inside a room is a thing in that room; two rooms that
  // overlap are one shared room named from both; anywhere else a box is a child scene of its own --------------------
  const OVERLAP = 0.05;  // metres two boxes must overlap each way to count
  const box_of = (hold) => [hold.x, hold.y, hold.w, hold.d];
  const within = (a, b) => a[0] >= b[0] && a[1] >= b[1] && a[0] + a[2] <= b[0] + b[2] && a[1] + a[3] <= b[1] + b[3];
  const crossing = (a, b) => Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0]) > OVERLAP &&
                             Math.min(a[1] + a[3], b[1] + b[3]) - Math.max(a[1], b[1]) > OVERLAP;
  const room_round = (box, but) => plan.holds.filter((hold) => hold !== but && within(box, box_of(hold)))
    .sort((a, b) => a.w * a.d - b.w * b.d)[0];
  const copied = (hold) => JSON.parse(JSON.stringify(hold));
  const put_back = (hold, was) => { for (const key of Object.keys(hold)) delete hold[key]; Object.assign(hold, was); };
  // a room dropped: into the room round it as a thing, else onto one it overlaps as a shared room, else on its own
  const dropped = (hold) => {
    const room = room_round(box_of(hold), hold);
    if (room) return into_room(hold, room);
    const merged = overlapped(hold);
    if (!merged) hold.row = holder_under(hold);
    return merged;
  };
  // a room dropped onto another it overlaps (kept: the one it landed on), or resized over one (kept: itself): the two one
  // shared room in the box round both, their things kept
  const overlapped = (hold, landed = true) => {
    const other = plan.holds.find((found) => found !== hold && crossing(box_of(hold), box_of(found)));
    if (!other) return "";
    const [kept, gone] = landed ? [other, hold] : [hold, other];
    const was = copied(kept);
    const at = plan.holds.indexOf(gone);
    const x0 = Math.min(kept.x, gone.x), y0 = Math.min(kept.y, gone.y);
    const x1 = Math.max(kept.x + kept.w, gone.x + gone.w), y1 = Math.max(kept.y + kept.d, gone.y + gone.d);
    const things = [kept, gone].flatMap((room) => (room.things || []).map((thing) => (
      { ...thing, x: round(thing.x + room.x - x0), y: round(thing.y + room.y - y0) })));
    const name = `${title(kept)} and ${title(gone).toLowerCase()}`;
    plan.holds.splice(at, 1);
    Object.assign(kept, { x: round(x0), y: round(y0), w: round(x1 - x0), d: round(y1 - y0), name });
    if (things.length) kept.things = things;
    undoable(`${title(was)} and ${title(gone)} are one room`, () => { put_back(kept, was); plan.holds.splice(at, 0, gone); },
             `kept ${gone.place.replace(/_/g, " ")} apart from ${kept.place.replace(/_/g, " ")}`);
    return `made ${kept.place.replace(/_/g, " ")} and ${gone.place.replace(/_/g, " ")} one shared room called ${name}`;
  };
  // a room dropped fully inside another: a thing in it, no scene of its own, its own things with it
  const into_room = (hold, room) => {
    const was = copied(room);
    const at = plan.holds.indexOf(hold);
    const thing = { name: title(hold).toLowerCase(), x: round(hold.x - room.x), y: round(hold.y - room.y), w: hold.w, d: hold.d };
    const carried = (hold.things || []).map((found) => ({ ...found, x: round(found.x + thing.x), y: round(found.y + thing.y) }));
    plan.holds.splice(at, 1);
    room.things = [...(room.things || []), thing, ...carried];
    undoable(`${thing.name} stands in ${title(room)}`, () => { put_back(room, was); plan.holds.splice(at, 0, hold); },
             `kept ${hold.place.replace(/_/g, " ")} a scene of its own`);
    return `put ${thing.name} in ${room.place.replace(/_/g, " ")}, ${thing.w} x ${thing.d} m at ${thing.x}, ${thing.y} m from its corner`;
  };
  const free_id = (name) => {
    const base = (/^[a-z]/i.test(name) ? "" : "place_") + name.toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 34);
    let found = base || "place";
    for (let count = 2; plan.holds.some((hold) => hold.place === found); count += 1) found = `${base}_${count}`;
    return found;
  };
  // a thing dropped: in the room round it (its own or another), else out on its own as a child scene again
  const thing_dropped = (thing, hold) => {
    const box = [hold.x + thing.x, hold.y + thing.y, thing.w, thing.d];
    const room = room_round(box, null);
    if (room === hold) return "";
    hold.things.splice(hold.things.indexOf(thing), 1);
    if (!hold.things.length) delete hold.things;
    if (room) {
      room.things = [...(room.things || []), { ...thing, x: round(box[0] - room.x), y: round(box[1] - room.y) }];
      return `moved ${thing.name} from ${hold.place.replace(/_/g, " ")} to ${room.place.replace(/_/g, " ")}`;
    }
    const scene = { place: free_id(thing.name), row: null, x: box[0], y: box[1], w: thing.w, d: thing.d };
    plan.holds.push(scene);
    names[scene.place] = thing.name;
    const merged = overlapped(scene);
    if (!merged) scene.row = holder_under(scene);
    return merged || `took ${thing.name} out of ${hold.place.replace(/_/g, " ")} as a scene of its own`;
  };

  // --- the clicks -------------------------------------------------------------------------------------------------
  const click = (id, path, body, slow) => {
    const button = document.getElementById(id);
    if (!button) return;
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const sent_body = await body();
        const found = await post(path, sent_body);
        tell("done", found.said);
        if (slow) waiting(); else setTimeout(() => location.reload(), 600);
      } catch (error) {
        tell("bad", error.message);
        console.error(`plan ${path} refused`, error);
        button.disabled = false;
      }
    });
  };
  // Correct with notes: his marks and note; with no note typed, the edits he made on this visit (saved first) are the
  // note, else the store's machine words his kept edits (score/review/plans.note_of) or refuses before any spend
  click("plan-revise", "revise", async () => {
    if (timer) await save();
    await saving;
    const own = marks.filter((mark) => !mark.on).map(sent);
    const context = marks.filter((mark) => mark.on).map(sent);
    const words = note.value.trim() || (edits.length ? `I changed the plan by hand: ${edits.join("; ")}. Keep these changes and fit the rest of the plan to them.` : "");
    return { marks: own, context_marks: context, note: words, euros: Number(page.dataset.euros) };
  }, true);
  click("plan-write", "write", () => ({ euros: Number(page.dataset.writeEuros) }), true);
  if (page.dataset.pending) waiting();
  listed();
  draw();
})();
