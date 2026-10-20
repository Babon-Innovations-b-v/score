// The plan review page (pages/plans.py): the plan drawn top down in metres as an SVG laid out like the picture the
// prompt model is sent (score/review/plans.drawn: 40 px margins on a 900 px side), so a mark's share of it is the same
// area there. Drag an item, a zone or an inside place to move it, its corner to resize it, a door along its wall, a
// standing spot; drag on the floor or on the concept to mark an area, a note each. Keep posts the plan as he left it;
// Correct with notes posts the marks and notes at the price shown (his spend yes). The pick is the approval: no
// Approve here (owner, 2026-10-21).
(() => {
  const page = document.getElementById("plan");
  if (!page) return;
  const place = page.dataset.place;
  const plan = JSON.parse(document.getElementById("plan-data").textContent);
  const svg = document.getElementById("plan-drawing");
  const editing = "marking" in page.dataset;
  const said = document.getElementById("concept-said");
  const notes = document.getElementById("concept-notes");
  const note = document.getElementById("concept-note");
  const SVG = "http://www.w3.org/2000/svg";
  const WALLS = "ON THE WALLS AND CEILING";
  const SIDES = ["N", "S", "E", "W"];
  const ASK_EVERY = 1500;
  const wide = Math.max(plan.w, 0.5);
  const deep = Math.max(plan.d, 0.5);
  const margin = (40 * Math.max(wide, deep)) / 820;  // plans.drawn's 40 px at its scale
  const round = (value) => Math.round(value * 100) / 100;
  plan.holds = plan.holds || [];
  plan.people = plan.people || [];

  svg.setAttribute("viewBox", `${-margin} ${-margin} ${wide + 2 * margin} ${deep + 2 * margin}`);
  // the drawing as wide as its stage, no taller than most of the window: the marks' layer is exactly its box
  const canvas = document.getElementById("plan-canvas");
  const fitted = () => {
    const ratio = (wide + 2 * margin) / (deep + 2 * margin);
    canvas.style.width = `${Math.min(canvas.parentElement.clientWidth, window.innerHeight * 0.78 * ratio)}px`;
  };
  fitted();
  window.addEventListener("resize", fitted);
  const shape = (name, attributes, parent = svg) => {
    const found = document.createElementNS(SVG, name);
    for (const [key, value] of Object.entries(attributes)) found.setAttribute(key, value);
    parent.append(found);
    return found;
  };
  const label = (words, x, y, size, kind, parent = svg) => {
    const found = shape("text", { x, y, "font-size": size, class: `plan-label ${kind}` }, parent);
    found.textContent = words;
    return found;
  };
  const at = (event) => {
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    return point.matrixTransform(svg.getScreenCTM().inverse());
  };

  // --- dragging: a move or a resize of one thing, the plan changed in place -------------------------------------
  let dragging = null;
  const draggable = (element, start, move) => {
    if (!editing) return;
    element.classList.add("plan-drag");
    element.addEventListener("pointerdown", (event) => {
      event.stopPropagation();
      dragging = { from: at(event), was: start(), move };
      svg.setPointerCapture(event.pointerId);
    });
  };
  svg.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    const point = at(event);
    dragging.move(dragging.was, round(point.x - dragging.from.x), round(point.y - dragging.from.y));
    draw();
  });
  svg.addEventListener("pointerup", () => { dragging = null; });

  // one box: `rect()` its [x, y, w, h]; `moved(x, y)` and `sized(w, h)` change the thing it draws
  const box = (rect, moved, sized, kind, words, tip) => {
    const [x, y, w, h] = rect();
    const group = shape("g", { class: `plan-${kind}` });
    shape("rect", { x, y, width: w, height: h }, group);
    const size = Math.max(Math.min(w / 8, h / 3, 0.6), Math.max(wide, deep) / 90);
    label(words, x + size * 0.3, y + size * 1.1, size, kind, group);
    shape("title", {}, group).textContent = tip;
    const corner = shape("rect", { x: x + w - size * 0.6, y: y + h - size * 0.6, width: size * 0.6,
                                   height: size * 0.6, class: "plan-corner" }, group);
    draggable(group, rect, (was, dx, dy) => moved(round(was[0] + dx), round(was[1] + dy)));
    draggable(corner, rect, (was, dx, dy) => sized(Math.max(0.1, round(was[2] + dx)), Math.max(0.1, round(was[3] + dy))));
  };
  const item_box = (item) => box(() => item.slice(1, 5), (x, y) => item.splice(1, 2, x, y),
                                 (w, h) => item.splice(3, 2, w, h), item[6] === "zone" ? "zone" : "item",
                                 item[0].toLowerCase(), `${item[0]}: ${(plan.rows[item[0]] || []).join(", ") || "no row"}`);
  const hold_box = (hold) => box(() => [hold.x, hold.y, hold.w, hold.d], (x, y) => Object.assign(hold, { x, y }),
                                 (w, d) => Object.assign(hold, { w, d }), "hold", hold.place, `inside place ${hold.place}`);

  const door_line = (door, index) => {
    if (!SIDES.includes(door[0])) return;
    const half = Number(door[2]) / 2;
    const [x, y] = { N: [door[1], 0], S: [door[1], deep], W: [0, door[1]], E: [wide, door[1]] }[door[0]];
    const across = door[0] === "N" || door[0] === "S";
    const group = shape("g", { class: "plan-door" });
    shape("line", across ? { x1: x - half, y1: y, x2: x + half, y2: y } : { x1: x, y1: y - half, x2: x, y2: y + half },
          group);
    const lead = (plan.leads || {})[door[0]] || {};
    label(`to ${lead.to || "?"}`, x + 0.1, y + (door[0] === "N" ? margin * 0.5 : -margin * 0.15), margin * 0.35,
          "door", group);
    shape("title", {}, group).textContent = `${door[3]}: ${lead.why || ""}`;
    draggable(group, () => door.slice(), (was, dx, dy) => {
      plan.doors[index][1] = round(Math.min(across ? wide : deep, Math.max(0, was[1] + (across ? dx : dy))));
    });
  };

  const spot = (where) => {
    const dot = shape("circle", { cx: where[0], cy: where[1], r: Math.max(wide, deep) / 90, class: "plan-spot" });
    shape("title", {}, dot).textContent = "a standing spot";
    draggable(dot, () => where.slice(), (was, dx, dy) => where.splice(0, 2, round(was[0] + dx), round(was[1] + dy)));
  };

  const numbers = document.getElementById("plan-numbers");
  const draw = () => {
    svg.replaceChildren();
    shape("rect", { x: 0, y: 0, width: wide, height: deep, class: "plan-floor" });
    plan.items.filter((item) => item[0] !== WALLS).forEach(item_box);
    plan.holds.forEach(hold_box);  // over the items: the hangar's rooms over its ship
    plan.doors.forEach(door_line);
    plan.people.forEach(spot);
    label("N", -margin * 0.8, -margin * 0.3, margin * 0.6, "north");
    const zones = plan.items.filter((item) => item[6] === "zone").length;
    numbers.textContent = `${plan.items.length - zones} items · ${zones} clear · ${plan.doors.length} doors · ` +
      `${plan.people.length} spots · ${plan.holds.length} places`;
  };

  // --- the inside places: a list beside the drawing -------------------------------------------------------------
  const places = document.getElementById("plan-places");
  // each inside place: its name, the row of this place it stands in (none: this place's own walls), remove
  const ids = [...new Set(Object.values(plan.rows || {}).flat())].sort();
  const listed = () => {
    places.replaceChildren();
    plan.holds.forEach((hold, index) => {
      const row = document.createElement("li");
      if (!editing) {
        row.innerHTML = '<span data-v></span><small class="soft" data-v></small>';
        row.querySelector("span").textContent = hold.place;
        row.querySelector("small").textContent = hold.row || "walls";
        places.append(row);
        return;
      }
      row.innerHTML = '<input type="text" title="its name"><select title="the row of this place it stands in">' +
        '</select><button type="button" class="concept-drop" title="remove this place" aria-label="remove">&times;' +
        "</button>";
      const input = row.querySelector("input");
      input.value = hold.place;
      input.addEventListener("change", () => {
        hold.place = input.value.trim().toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "") || hold.place;
        input.value = hold.place;
        draw();
      });
      const select = row.querySelector("select");
      for (const id of ["", ...ids]) select.append(new Option(id || "walls", id, false, (hold.row || "") === id));
      select.addEventListener("change", () => { hold.row = select.value || null; });
      row.querySelector("button").addEventListener("click", () => { plan.holds.splice(index, 1); listed(); draw(); });
      places.append(row);
    });
  };
  const add = document.getElementById("plan-add");
  if (add) {
    add.addEventListener("click", () => {
      const side = Math.max(1, Math.min(wide, deep) / 4);
      plan.holds.push({ place: `place_${plan.holds.length + 1}`, row: null, x: round(margin), y: round(margin),
                        w: round(side), d: round(side) });
      listed();
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
    for (const layer of page.querySelectorAll(".plan-concept .concept-marks")) marking(layer, layer, layer.dataset.on);
  }
  const sent = (mark) => ({ x: mark.x, y: mark.y, w: mark.w, h: mark.h, note: mark.row.querySelector("input").value,
                            ...(mark.on ? { on: mark.on } : {}) });

  // --- the clicks -------------------------------------------------------------------------------------------------
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
  const tell = (tone, words) => {
    said.className = `dot tone-${tone}`;
    said.title = words;
    said.hidden = false;
  };
  const busy = document.getElementById("plan-busy");
  const buttons = [...page.querySelectorAll(".concept-side button")];
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
  const click = (id, path, body, slow) => {
    const button = document.getElementById(id);
    if (!button) return;
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const found = await post(path, body());
        tell("done", found.said);
        if (slow) waiting(); else setTimeout(() => location.reload(), 600);
      } catch (error) {
        tell("bad", error.message);
        console.error(`plan ${path} refused`, error);
        button.disabled = false;
      }
    });
  };
  click("plan-keep", "keep", () => ({ plan }), false);
  click("plan-revise", "revise", () => ({ marks: marks.filter((mark) => !mark.on).map(sent),
                                          context_marks: marks.filter((mark) => mark.on).map(sent),
                                          note: note.value, euros: Number(page.dataset.euros) }), true);
  if (page.dataset.pending) waiting();
  listed();
  draw();
})();
