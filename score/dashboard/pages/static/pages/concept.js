// The concept review page (pages/concepts.py): drag on the picture to mark an area, a note for each. Its one draw
// button posts the price it shows (the owner's spend yes for that one call): with no mark and no note it is Draw fresh
// (a new first draw from the place's own wording: no base), else Redraw with notes (the marks, the note and the shown
// draw as its base); then it asks the page's state until the draw is answered and shows it. A first draw sends the
// wording box's text when he edited it (it becomes the place's own wording); "back to generated" drops it. Pick and
// Unlock post the shown draw (or none).
(() => {
  const page = document.getElementById("concept");
  if (!page) return;
  const place = page.dataset.place;
  const layer = document.getElementById("concept-marks");
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
  const share = (event) => {
    const box = layer.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (event.clientX - box.left) / box.width)),
            Math.min(1, Math.max(0, (event.clientY - box.top) / box.height))];
  };
  const place_box = (mark) => {
    Object.assign(mark.box.style, { left: `${mark.x * 100}%`, top: `${mark.y * 100}%`,
                                    width: `${mark.w * 100}%`, height: `${mark.h * 100}%` });
  };
  const plain = () => !marks.length && !note.value.trim();  // nothing asked of the shown draw: draw fresh
  const named = () => (!page.dataset.base ? "Draw concept" : plain() ? "Draw fresh" : "Redraw with notes");
  const relabel = () => { if (draw && !draw.disabled) draw.querySelector('[data-slot="label"]').textContent = named(); };
  const renumber = () => {
    marks.forEach((mark, index) => {
      mark.box.dataset.n = index + 1;
      mark.row.querySelector("b").textContent = index + 1;
    });
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
  if (layer && "marking" in page.dataset) {
    let drawing = null;
    layer.addEventListener("pointerdown", (event) => {
      const [x, y] = share(event);
      drawing = { from: [x, y], x, y, w: 0, h: 0, box: document.createElement("div") };
      drawing.box.className = "concept-mark";
      layer.append(drawing.box);
      layer.setPointerCapture(event.pointerId);
    });
    layer.addEventListener("pointermove", (event) => {
      if (!drawing) return;
      const [x, y] = share(event);
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
    draw.addEventListener("click", async () => {
      draw.disabled = true;
      const body = plain()
        ? { marks: [], note: "", base: null, euros: Number(page.dataset.euros) }
        : {
          marks: marks.map((mark) => ({ x: mark.x, y: mark.y, w: mark.w, h: mark.h,
                                        note: mark.row.querySelector("input").value })),
          note: note.value, base: page.dataset.base || null, euros: Number(page.dataset.euros),
        };
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
