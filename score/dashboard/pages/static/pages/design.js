// The design page's cockpit (pages/concepts.py): its panels and their zoom views.
// Focus: a panel's enlarge button fills the screen with it, in place (its marks, hover and drags work the same); it is
// a history step of its own (#focus=<panel>, pushed), so back, Escape or the button shut it and a reload shows it.
// Zoom: a .zoom-view fits its .zoom-content (its svg's viewBox aspect) and zooms with the wheel at the pointer (in an
// enlarged panel, else with Ctrl), pans with Space+drag or the middle button (data-pan="free": any drag); "fit" and
// a resize put it back whole.
(() => {
  // --- the screen: on a desktop the cockpit fills the screen below where it starts (dash.css --design-top) ---------
  const design = document.querySelector(".design");
  const placed = () => design.style.setProperty("--design-top", `${design.getBoundingClientRect().top + window.scrollY}px`);
  placed();
  window.addEventListener("resize", placed);

  // --- focus --------------------------------------------------------------------------------------------------------
  const focused = () => {
    const wanted = /^#focus=([\w-]+)$/.exec(location.hash);
    for (const panel of document.querySelectorAll(".dpanel")) {
      const on = Boolean(wanted) && panel.id === wanted[1];
      panel.classList.toggle("focused", on);
      const button = panel.querySelector("[data-focus]");
      button.setAttribute("aria-pressed", String(on));
      button.innerHTML = on ? "&times;" : "&#x2922;";
    }
    document.body.classList.toggle("focusing", Boolean(wanted));
  };
  const shut = () => {
    if (history.state && history.state.focus) history.back();  // the step it pushed
    else { history.replaceState(null, "", location.pathname + location.search); focused(); }  // opened by a link
  };
  for (const button of document.querySelectorAll("[data-focus]")) {
    button.addEventListener("click", () => {
      const panel = button.closest(".dpanel");
      if (panel.classList.contains("focused")) { shut(); return; }
      history.pushState({ focus: panel.id }, "", `#focus=${panel.id}`);
      focused();
    });
  }
  window.addEventListener("popstate", focused);
  window.addEventListener("hashchange", focused);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && document.querySelector(".dpanel.focused") && !event.target.matches("input, textarea")) shut();
  });
  focused();

  // --- zoom and pan -------------------------------------------------------------------------------------------------
  let space = false;
  window.addEventListener("keydown", (event) => {
    if (event.code !== "Space" || !document.querySelector(".zoom-view:hover") || event.target.matches("input, textarea")) return;
    space = true;
    event.preventDefault();  // held over a zoom view: a pan, not a page scroll
  });
  window.addEventListener("keyup", (event) => { if (event.code === "Space") space = false; });
  const zoomable = (view) => {
    const content = view.querySelector(".zoom-content");
    const drawing = content.querySelector("svg");
    const at = { x: 0, y: 0, s: 1 };
    let size = [1, 1];  // the content's fitted width and height
    const shown = () => { content.style.transform = `translate(${at.x}px, ${at.y}px) scale(${at.s})`; };
    const fit = () => {
      const box = drawing.viewBox.baseVal;
      if (!box || !box.width || !box.height || !view.clientWidth) return;
      const ratio = box.width / box.height;
      view.style.aspectRatio = String(ratio);  // as tall as its drawing, no taller than its max-height
      const scale = Math.min(view.clientWidth / box.width, view.clientHeight / box.height);
      size = [box.width * scale, box.height * scale];
      content.style.width = `${size[0]}px`;
      Object.assign(at, { x: (view.clientWidth - size[0]) / 2, y: (view.clientHeight - size[1]) / 2, s: 1 });
      shown();
    };
    new ResizeObserver(fit).observe(view);
    new MutationObserver(() => { if (at.s === 1) fit(); }).observe(drawing, { attributes: true, attributeFilter: ["viewBox"] });
    view.addEventListener("wheel", (event) => {
      if (!view.closest(".focused") && !event.ctrlKey) return;  // the page scrolls past it
      event.preventDefault();
      const bounds = view.getBoundingClientRect();
      const [px, py] = [event.clientX - bounds.left, event.clientY - bounds.top];
      const scale = Math.min(40, Math.max(1, at.s * Math.exp(-event.deltaY / 400)));
      Object.assign(at, { x: px - ((px - at.x) * scale) / at.s, y: py - ((py - at.y) * scale) / at.s, s: scale });
      shown();
    }, { passive: false });
    let panning = null;
    view.addEventListener("pointerdown", (event) => {
      if (!(event.button === 1 || space || view.dataset.pan === "free")) return;
      event.preventDefault();
      event.stopPropagation();  // no mark, no drag of a thing
      panning = { from: [event.clientX, event.clientY], was: [at.x, at.y] };
      view.setPointerCapture(event.pointerId);
      view.classList.add("panning");
    }, true);
    view.addEventListener("pointermove", (event) => {
      if (!panning) return;
      event.stopPropagation();
      at.x = panning.was[0] + event.clientX - panning.from[0];
      at.y = panning.was[1] + event.clientY - panning.from[1];
      shown();
    }, true);
    const done = (event) => { if (panning) { event.stopPropagation(); panning = null; view.classList.remove("panning"); } };
    view.addEventListener("pointerup", done, true);
    view.addEventListener("pointercancel", done, true);
    return fit;
  };
  const fits = [...document.querySelectorAll(".zoom-view")].map(zoomable);
  for (const button of document.querySelectorAll("[data-fit]")) {
    button.addEventListener("click", () => fits.forEach((fit) => fit()));
  }
})();
