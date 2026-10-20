// The concept review page (pages/concepts.py): drag on the picture to mark an area, a note for each; Draw or Redraw
// posts the marks, the note and the price the button shows (the owner's spend yes for that one call), then asks the
// page's state until the draw is answered and shows it; Pick and Unlock post the shown draw (or none).
(() => {
  const page = document.getElementById("concept");
  if (!page) return;
  const place = page.dataset.place;
  const layer = document.getElementById("concept-marks");
  const notes = document.getElementById("concept-notes");
  const draw = document.getElementById("concept-draw");
  const said = document.getElementById("concept-said");
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
  const renumber = () => marks.forEach((mark, index) => {
    mark.box.dataset.n = index + 1;
    mark.row.querySelector("b").textContent = index + 1;
  });
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
  const waiting = (since) => {
    draw.disabled = true;
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
        tell("bad", found.refused);
        console.error("concept draw refused", found.refused);
        label.textContent = page.dataset.base ? "Redraw" : "Draw concept";
        draw.disabled = false;
        return;
      }
      location.search = `?draw=${found.newest}`;
    };
    setTimeout(ask, ASK_EVERY);
  };
  if (draw) {
    if (page.dataset.pending) waiting(page.dataset.pending);
    draw.addEventListener("click", async () => {
      draw.disabled = true;
      const body = {
        marks: marks.map((mark) => ({ x: mark.x, y: mark.y, w: mark.w, h: mark.h,
                                      note: mark.row.querySelector("input").value })),
        note: document.getElementById("concept-note").value, base: page.dataset.base || null,
        euros: Number(page.dataset.euros),
      };
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
