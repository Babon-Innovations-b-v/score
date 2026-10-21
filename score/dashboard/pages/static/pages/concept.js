// The concept review page (pages/concepts.py): drag on the picture to mark an area, a note for each. Its one draw
// button posts the price it shows (the owner's spend yes for that one call): with no mark and no note it is Draw fresh
// (a new first draw from the place's own wording: no base), else Redraw with notes (the marks, the note and the shown
// draw as its base); then it asks the page's state until the draw is answered and shows it. A first draw sends the
// wording box's text when he edited it (it becomes the place's own wording); "back to generated" drops it. Pick and
// Unlock post the shown draw (or none). Discuss posts the note as a question with the marks (its own spend yes) and
// shows the answer in the thread above the note; an open thread makes the draw button Redraw with notes, which sends
// it along (score/review/discuss.py). The inventory panel's boxes: the second part below.
(() => {
  const page = document.getElementById("concept");
  if (!page) return;
  const place = page.dataset.place;
  // the draw's mark layer, and one on each picked concept it is drawn on (data-on: that place; its marks P1, P2...)
  const layers = [...page.querySelectorAll(".concept-marks")];
  const notes = document.getElementById("concept-notes");
  const draw = document.getElementById("concept-draw");
  const note = document.getElementById("concept-note");
  const said = document.getElementById("concept-said");
  const wording = document.getElementById("concept-wording");
  const marks = [];
  const ASK_EVERY = 1500;

  const cookie = (name) => (document.cookie.split("; ").find((part) => part.startsWith(name + "=")) || "").split("=")[1];
  const post = async (path, body) => {
    const answer = await fetch(`/concept/${place}/${path}/`, {
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

  // --- the marks: a box a drag, numbered, each with its note ---------------------------------------------------
  const share = (event, layer) => {
    const box = layer.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (event.clientX - box.left) / box.width)),
            Math.min(1, Math.max(0, (event.clientY - box.top) / box.height))];
  };
  const place_box = (mark) => {
    Object.assign(mark.box.style, { left: `${mark.x * 100}%`, top: `${mark.y * 100}%`,
                                    width: `${mark.w * 100}%`, height: `${mark.h * 100}%` });
  };
  const thread = document.getElementById("concept-thread");
  const talked = () => Boolean(thread && thread.querySelector("li[data-open]"));  // an open discussion goes with a redraw
  const plain = () => !marks.length && !note.value.trim() && !talked();  // nothing asked of the shown draw: draw fresh
  const named = () => (!page.dataset.base ? "Draw concept" : plain() ? "Draw fresh" : "Redraw with notes");
  // a Redraw with notes is two calls (the prompt model corrects the prompt, then the draw): its own price
  const euros = () => Number(!page.dataset.base || plain() ? page.dataset.euros : page.dataset.redrawEuros);
  const relabel = () => {
    if (!draw || draw.disabled) return;
    draw.querySelector('[data-slot="label"]').textContent = named();
    const price = draw.querySelector('[data-slot="price"]');
    const shown = !page.dataset.base || plain() ? page.dataset.euros : page.dataset.redrawEuros;
    if (price && shown) price.textContent = `EUR ${Number(shown).toFixed(2)}`;
  };
  const renumber = () => {
    for (const [prefix, own] of [["", marks.filter((mark) => !mark.on)], ["P", marks.filter((mark) => mark.on)]]) {
      own.forEach((mark, index) => {
        mark.box.dataset.n = `${prefix}${index + 1}`;
        mark.row.querySelector("b").textContent = `${prefix}${index + 1}`;
      });
    }
    relabel();
  };
  const dropped = (mark) => {
    marks.splice(marks.indexOf(mark), 1);
    mark.box.remove();
    mark.row.remove();
    renumber();
  };
  const noted = (mark) => {
    mark.row = document.createElement("li");
    mark.row.innerHTML = '<b data-v></b><input type="text" placeholder="what to change here">' +
      '<button type="button" class="concept-drop" title="remove this mark" aria-label="remove">&times;</button>';
    mark.row.querySelector("button").addEventListener("click", () => dropped(mark));
    notes.append(mark.row);
    renumber();
    mark.row.querySelector("input").focus();
  };
  for (const layer of "marking" in page.dataset ? layers : []) {
    let drawing = null;
    layer.addEventListener("pointerdown", (event) => {
      const [x, y] = share(event, layer);
      drawing = { from: [x, y], x, y, w: 0, h: 0, on: layer.dataset.on || null, box: document.createElement("div") };
      drawing.box.className = "concept-mark";
      layer.append(drawing.box);
      layer.setPointerCapture(event.pointerId);
    });
    layer.addEventListener("pointermove", (event) => {
      if (!drawing) return;
      const [x, y] = share(event, layer);
      Object.assign(drawing, { x: Math.min(x, drawing.from[0]), y: Math.min(y, drawing.from[1]),
                               w: Math.abs(x - drawing.from[0]), h: Math.abs(y - drawing.from[1]) });
      place_box(drawing);
    });
    layer.addEventListener("pointerup", () => {
      const mark = drawing;
      drawing = null;
      if (!mark) return;
      if (mark.w < 0.01 || mark.h < 0.01) { mark.box.remove(); return; }
      marks.push(mark);
      noted(mark);
    });
  }

  // the marks as a redraw or a Discuss sends them: the draw's, and the picked concepts' (context_marks)
  const marked = () => ({
    marks: marks.filter((mark) => !mark.on).map((mark) => ({ x: mark.x, y: mark.y, w: mark.w, h: mark.h,
                                                              note: mark.row.querySelector("input").value })),
    context_marks: marks.filter((mark) => mark.on).map((mark) => ({
      on: mark.on, x: mark.x, y: mark.y, w: mark.w, h: mark.h, note: mark.row.querySelector("input").value })),
  });

  // --- Discuss: the note as a question to the prompt model, its answer in the thread above the note -------------
  const discuss = document.getElementById("concept-discuss");
  const shown_thread = (entries) => {
    thread.replaceChildren(...entries.map((entry) => {
      const row = document.createElement("li");
      const asked = document.createElement("b");
      const answer = document.createElement("p");
      asked.dataset.v = answer.dataset.v = "";
      asked.textContent = entry.question;
      answer.textContent = entry.answer;
      if (entry.closed) { row.className = "closed"; row.title = "closed: a draw was made after it"; }
      else row.dataset.open = "";
      row.append(asked, answer);
      return row;
    }));
    thread.hidden = !entries.length;
  };
  const answered = () => {
    const label = discuss.querySelector('[data-slot="label"]');
    discuss.disabled = true;
    const started = Date.now();
    const tick = () => { label.textContent = `asking ${Math.round((Date.now() - started) / 1000)} s`; };
    tick();
    const clock = setInterval(tick, 1000);
    const ask = async () => {
      const found = await fetch(`/concept/${place}/state/?draw=${page.dataset.base}`, { credentials: "same-origin" })
        .then((answer) => answer.json()).catch(() => null);
      if (!found || found.discussing) { setTimeout(ask, ASK_EVERY); return; }
      clearInterval(clock);
      label.textContent = "Discuss";
      discuss.disabled = false;
      if (found.discuss_refused) {
        tell("bad", found.discuss_refused);
        console.error("concept discuss refused", found.discuss_refused);
        return;
      }
      shown_thread(found.thread);
      note.value = "";
      relabel();
    };
    setTimeout(ask, ASK_EVERY);
  };
  if (discuss) {
    if ("discussing" in page.dataset) answered();
    discuss.addEventListener("click", async () => {
      if (!note.value.trim()) { tell("bad", "write your question in the note first"); note.focus(); return; }
      discuss.disabled = true;
      try {
        await post("discuss", { ...marked(), question: note.value, base: page.dataset.base,
                                euros: Number(discuss.dataset.euros) });
        said.hidden = true;
        answered();
      } catch (error) {
        tell("bad", error.message);
        console.error("concept discuss refused", error);
        discuss.disabled = false;
      }
    });
  }

  // --- draw, then ask until it is answered ----------------------------------------------------------------------
  const busy = document.getElementById("concept-busy");
  const waiting = (since) => {
    draw.disabled = true;
    busy.hidden = false;
    const label = draw.querySelector('[data-slot="label"]');
    const started = since ? Date.parse(since) : Date.now();
    const tick = () => { label.textContent = `drawing ${Math.round((Date.now() - started) / 1000)} s`; };
    tick();
    const clock = setInterval(tick, 1000);
    const ask = async () => {
      const found = await fetch(`/concept/${place}/state/`, { credentials: "same-origin" }).then((answer) => answer.json())
        .catch(() => null);
      if (!found || found.pending) { setTimeout(ask, ASK_EVERY); return; }
      clearInterval(clock);
      if (found.refused) {
        busy.hidden = true;
        tell("bad", found.refused);
        console.error("concept draw refused", found.refused);
        draw.disabled = false;
        relabel();
        return;
      }
      location.replace(`?draw=${found.newest}`);  // the answered draw in this step's place: no extra back step
    };
    setTimeout(ask, ASK_EVERY);
  };
  if (draw) {
    if (page.dataset.pending) waiting(page.dataset.pending);
    if (note) note.addEventListener("input", relabel);
    relabel();  // an open discussion makes it a Redraw with notes from the start
    draw.addEventListener("click", async () => {
      draw.disabled = true;
      const body = plain()
        ? { marks: [], note: "", base: null, euros: euros() }
        : { ...marked(), note: note.value, base: page.dataset.base || null, euros: euros() };
      // a first draw sends the wording box when he edited it; untouched, the store's machine words it as it is now
      if (!body.base && wording && wording.value.trim() !== wording.defaultValue.trim()) body.wording = wording.value.trim();
      try {
        await post("draw", body);
        said.hidden = true;
        waiting(null);
      } catch (error) {
        tell("bad", error.message);
        console.error("concept draw refused", error);
        draw.disabled = false;
      }
    });
  }

  // --- back to the generated wording ---------------------------------------------------------------------------
  const generated = document.getElementById("concept-generated");
  if (generated) {
    generated.addEventListener("click", async () => {
      generated.disabled = true;
      try {
        await post("generated", {});
        location.reload();
      } catch (error) {
        tell("bad", error.message);
        console.error("back to generated refused", error);
        generated.disabled = false;
      }
    });
  }

  // --- pick and unlock -----------------------------------------------------------------------------------------
  const pick = document.getElementById("concept-pick");
  if (pick) {
    pick.addEventListener("click", async () => {
      pick.disabled = true;
      try {
        const found = await post("pick", { sha: pick.dataset.sha || null });
        tell("done", found.said);
        setTimeout(() => location.reload(), 600);
      } catch (error) {
        tell("bad", error.message);
        console.error("concept pick refused", error);
        pick.disabled = false;
      }
    });
  }
})();

// The inventory panel: the reading's boxes on the picked concept, its rows beside them. One row is shown at a time,
// its boxes lit and every other dimmed: the row hovered in the list, else the row held, else the smallest box under
// the pointer on the picture (boxes stack: the smallest is the one meant). A click on the picture holds that row;
// clicking again at the same spot steps through every box stacked there, a bare spot lets go; a click on a row or a
// gap holds it too. "one at a time" hides the others, the kind buttons keep one kind's rows, "skipped" draws what the
// agreement left out, faint. Each row's number sits inside a corner of its first box, moved where it would cover
// another.
(() => {
  const stage = document.getElementById("inventory-stage");
  if (!stage) return;
  const layer = stage.querySelector(".concept-boxes");
  const boxes = [...layer.querySelectorAll(".concept-box")];
  const rows = [...document.querySelectorAll("#concept-reading li[data-row]")];
  const told = stage.title;
  const state = { list: null, held: null, hover: null, kind: "", stack: null };
  const key = (element) => (element.dataset.row ? `r${element.dataset.row}` : `s${element.dataset.skip}`);
  const seen = (box) => !box.classList.contains("off") && (!box.classList.contains("skipped") || layer.classList.contains("skipped-shown"));

  const shown = () => {
    const wanted = state.list || state.held || state.hover;
    layer.classList.toggle("focusing", Boolean(wanted));
    for (const box of boxes) box.classList.toggle("lit", key(box) === wanted);
    for (const row of rows) {
      row.classList.toggle("lit", key(row) === wanted);
      row.classList.toggle("held", key(row) === state.held);
    }
    const lit = boxes.find((box) => key(box) === wanted);
    stage.title = lit ? lit.dataset.tip : told;
  };
  // every box seen under the pointer, smallest first
  const under = (event) => boxes.filter(seen).map((box) => [box, box.getBoundingClientRect()])
    .filter(([, rect]) => event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom)
    .sort((one, other) => one[1].width * one[1].height - other[1].width * other[1].height).map(([box]) => box);
  stage.addEventListener("pointermove", (event) => {
    const [smallest] = under(event);
    state.hover = smallest ? key(smallest) : null;
    shown();
  });
  stage.addEventListener("pointerleave", () => { state.hover = null; shown(); });
  stage.addEventListener("click", (event) => {
    const found = under(event);
    const again = state.stack && Math.hypot(event.clientX - state.stack.x, event.clientY - state.stack.y) < 6;
    const index = again && found.length ? (state.stack.index + 1) % found.length : 0;
    state.stack = found.length ? { x: event.clientX, y: event.clientY, index } : null;
    state.held = found.length ? key(found[index]) : null;
    shown();
  });
  for (const row of document.querySelectorAll("#concept-reading li[data-row]")) {
    row.addEventListener("mouseenter", () => { state.list = key(row); shown(); });
    row.addEventListener("mouseleave", () => { state.list = null; shown(); });
    row.addEventListener("click", () => { state.held = state.held === key(row) ? null : key(row); state.stack = null; shown(); });
  }

  // each row's number inside a corner of its first box: the first corner free of the numbers placed, else moved down
  const numbers = () => {
    const placed = [];
    const labels = boxes.filter((box) => seen(box) && box.querySelector("b"))
      .sort((one, other) => one.offsetWidth * one.offsetHeight - other.offsetWidth * other.offsetHeight);
    for (const box of labels) {
      const tag = box.querySelector("b");
      const [wide, tall, bw, bh] = [tag.offsetWidth, tag.offsetHeight, box.offsetWidth, box.offsetHeight];
      const corners = [[0, 0], [bw - wide, 0], [0, bh - tall], [bw - wide, bh - tall]];
      for (let step = 1; step * tall < bh; step += 1) corners.push([0, step * tall]);
      const free = ([x, y]) => !placed.some((other) => x + box.offsetLeft < other[0] + other[2] && other[0] < x + box.offsetLeft + wide &&
                                                      y + box.offsetTop < other[1] + other[3] && other[1] < y + box.offsetTop + tall);
      const [x, y] = corners.find(free) || [0, 0];
      Object.assign(tag.style, { left: `${Math.max(0, x)}px`, top: `${Math.max(0, y)}px` });
      placed.push([x + box.offsetLeft, y + box.offsetTop, wide, tall]);
    }
  };
  new ResizeObserver(numbers).observe(stage);

  // the kind buttons, one at a time, skipped
  const kinds = [...document.querySelectorAll("#inventory-tools [data-kind]")];
  for (const button of kinds) {
    button.addEventListener("click", () => {
      state.kind = button.dataset.kind;
      for (const other of kinds) other.setAttribute("aria-pressed", String(other === button));
      for (const element of [...boxes, ...rows]) {
        element.classList.toggle("off", Boolean(state.kind) && element.dataset.kind !== undefined && element.dataset.kind !== state.kind);
      }
      numbers();
      shown();
    });
  }
  const toggle = (id, name) => {
    const button = document.getElementById(id);
    if (!button) return;
    button.addEventListener("click", () => {
      button.setAttribute("aria-pressed", String(layer.classList.toggle(name)));
      numbers();
    });
  };
  toggle("concept-boxes-quiet", "quiet");
  toggle("concept-skipped-shown", "skipped-shown");
})();
