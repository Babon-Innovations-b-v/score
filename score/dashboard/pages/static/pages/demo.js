// An algorithm's own work on one real example (pages/library.py demo_of; its shape in
// score/stages/library/demo/CLAUDE.md): its steps played one after another on a plan, a side view or a raised
// relief, a path flown as a camera, a slider that shows the algorithm's output at another setting. Colours come from
// design tokens.
import { token } from "./tokens.js";

const given = JSON.parse(document.getElementById("demo-data").textContent);
const holder = document.getElementById("demo");
const canvas = document.createElement("canvas");
holder.prepend(canvas);
const pen = canvas.getContext("2d");
const tip = document.getElementById("demo-tip");
const stepList = document.getElementById("demo-steps");
const slider = document.getElementById("demo-slider");
const STEP_SECONDS = 1.6;  // how long one step takes to play in
const TONES = { ground: "--color-view-ground", base: "--color-view-grid", made: "--color-done",
  accent: "--color-view-pick", warn: "--color-bad", ghost: "--color-view-grid-fine",
  c1: "--color-mark-added", c2: "--color-mark-moved", c3: "--color-mark-refinished", c4: "--color-view-person",
  c5: "--color-mark-removed", c6: "--color-accent", c7: "--color-mark-framed", c8: "--color-mark-gate" };
const colour = (tone) => token(TONES[tone] || TONES.base);
const play = { step: 0, at: 0, running: true, choice: given.slider ? given.slider.at : 0, sliderFrom: null, turn: 0.6,
  flown: 0 };

// --- where a metre lands -------------------------------------------------------------------------------------------

let fit = null;
function resize() {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = holder.clientWidth * ratio;
  canvas.height = holder.clientHeight * ratio;
  canvas.style.width = `${holder.clientWidth}px`;
  canvas.style.height = `${holder.clientHeight}px`;
  pen.setTransform(ratio, 0, 0, ratio, 0, 0);
  if (given.view !== "relief") fit = fitted(given.bounds, holder.clientWidth, holder.clientHeight, !given.axes);
}

// The bounds into the canvas with a margin; the same scale both ways unless it is a chart with axes.
function fitted([left, bottom, right, top], width, height, equal) {
  const margin = given.axes ? 44 : 18;
  let across = (width - 2 * margin) / Math.max(right - left, 1e-6);
  let up = (height - 2 * margin) / Math.max(top - bottom, 1e-6);
  if (equal) across = up = Math.min(across, up);
  const spareX = width - (right - left) * across, spareY = height - (top - bottom) * up;
  return { across, up, x: (value) => spareX / 2 + (value - left) * across, y: (value) => height - spareY / 2 - (value - bottom) * up };
}
const at = ([x, y]) => [fit.x(x), fit.y(y)];

// --- the steps: which shapes show, and how far each has come in -------------------------------------------------------

function stepShapes(rank) {
  const shapes = given.steps[rank].shapes || [];
  const last = rank === given.steps.length - 1;
  return last && given.slider ? given.slider.shapes[play.choice] : shapes;
}

// [{shape, alpha, from (the shape it moves from, by id), share}] for everything showing now.
function showing() {
  const byId = new Map(), drawn = [];
  for (let rank = 0; rank <= play.step; rank += 1) {
    const share = rank < play.step ? 1 : Math.min(play.at / STEP_SECONDS, 1);
    if (rank === given.steps.length - 1 && given.slider && play.sliderFrom !== null) {
      for (const shape of given.slider.shapes[play.sliderFrom]) {  // a slider's move: its shapes go from the last setting's
        if (shape.id !== undefined) byId.set(shape.id, { shape });
      }
    }
    for (const shape of stepShapes(rank)) {
      const before = shape.id !== undefined ? byId.get(shape.id) : undefined;
      const item = { shape, share, from: before ? before.shape : null, alpha: before ? 1 : share };
      if (before && drawn.includes(before)) drawn.splice(drawn.indexOf(before), 1);
      if (shape.id !== undefined) byId.set(shape.id, item);
      drawn.push(item);
    }
  }
  return drawn;
}

const ease = (share) => share * share * (3 - 2 * share);
function moved(item) {
  const { shape, from, share } = item;
  if (!from || from.points.length !== shape.points.length) return shape.points;
  const done = ease(share);
  return shape.points.map((point, rank) => point.map((value, axis) => from.points[rank][axis] + (value - from.points[rank][axis]) * done));
}

// --- drawing one shape ---------------------------------------------------------------------------------------------------

function outline(points, close) {
  pen.beginPath();
  points.forEach((point, rank) => { const [x, y] = at(point); rank ? pen.lineTo(x, y) : pen.moveTo(x, y); });
  if (close) pen.closePath();
}

function drawArea(shape, points) {
  outline(points, true);
  pen.globalAlpha *= 0.55;
  pen.fillStyle = colour(shape.tone || "ground");
  pen.fill();
  pen.globalAlpha /= 0.55;
  pen.strokeStyle = colour(shape.tone || "ground");
  pen.lineWidth = 1;
  pen.stroke();
}

function drawLine(shape, points, share = 1) {
  const count = Math.max(2, Math.round(points.length * share));
  outline(points.slice(0, count), false);
  pen.strokeStyle = colour(shape.tone || "base");
  pen.lineWidth = shape.kind === "path" ? 2.5 : 1.5;
  pen.stroke();
}

function drawDots(shape, points) {
  pen.fillStyle = colour(shape.tone || "made");
  const radius = Math.max(((shape.r || 0) / 2) * fit.across, 1.5);
  for (const point of points) {
    const [x, y] = at(point);
    pen.beginPath();
    pen.arc(x, y, radius, 0, Math.PI * 2);
    pen.fill();
  }
}

function drawText(shape, points) {
  const [x, y] = at(points[0]);
  pen.fillStyle = colour(shape.tone || "accent");
  pen.font = "12px Poppins, system-ui, sans-serif";
  pen.textAlign = "center";
  pen.fillText(shape.label || "", x, y);
}

function drawRaster(shape) {
  const rows = shape.grid, tall = rows.length, wide = rows[0].length;
  const [x0, y0] = at(shape.points[0]), [x1, y1] = at(shape.points[1]);  // row 0's first cell's corner, the far one
  const cellX = (x1 - x0) / wide, cellY = (y1 - y0) / tall;
  const overlapX = Math.sign(cellX) * 0.6, overlapY = Math.sign(cellY) * 0.6;  // no hairline gaps between cells
  rows.forEach((row, rowRank) => row.forEach((value, columnRank) => {
    const rgb = Array.isArray(value) ? value : [value, value, value];
    pen.fillStyle = `rgb(${rgb.map((part) => Math.round(Math.min(Math.max(part, 0), 1) * 255)).join(",")})`;
    pen.fillRect(x0 + columnRank * cellX, y0 + rowRank * cellY, cellX + overlapX, cellY + overlapY);
  }));
}

// A path's marker: where it is along the path now, and with `look` a camera's view cone.
function drawFlier(shape, points) {
  const along = (play.flown % 1) * (points.length - 1);
  const rank = Math.floor(along), share = along - rank;
  const next = points[Math.min(rank + 1, points.length - 1)];
  const spot = points[rank].map((value, axis) => value + (next[axis] - value) * share);
  const [x, y] = at(spot);
  if (shape.look) {
    const [dx, dy] = shape.look[Math.min(rank, shape.look.length - 1)];
    const angle = Math.atan2(-dy, dx), reach = Math.min(holder.clientWidth, holder.clientHeight) / 6;
    pen.beginPath();
    pen.moveTo(x, y);
    pen.arc(x, y, reach, angle - 0.5, angle + 0.5);
    pen.closePath();
    pen.fillStyle = colour("accent");
    pen.globalAlpha = 0.25;
    pen.fill();
    pen.globalAlpha = 1;
  }
  pen.beginPath();
  pen.arc(x, y, 6, 0, Math.PI * 2);
  pen.fillStyle = colour("accent");
  pen.fill();
}

function drawShape(item) {
  const { shape } = item, points = moved(item);
  pen.globalAlpha = item.alpha;
  if (shape.kind === "area") drawArea(shape, points);
  else if (shape.kind === "line") drawLine(shape, points);
  else if (shape.kind === "path") { drawLine(shape, points, item.from ? 1 : item.share); if (item.share >= 1) drawFlier(shape, points); }
  else if (shape.kind === "dots") drawDots(shape, points);
  else if (shape.kind === "text") drawText(shape, points);
  else if (shape.kind === "raster") drawRaster(shape);
  pen.globalAlpha = 1;
}

function drawAxes() {
  if (!given.axes) return;
  const [left, bottom, right, top] = given.bounds;
  pen.strokeStyle = colour("base");
  pen.fillStyle = token("--color-text-light");
  pen.font = "11px Poppins, system-ui, sans-serif";
  pen.lineWidth = 1;
  outline([[left, bottom], [right, bottom]]); pen.stroke();
  outline([[left, bottom], [left, top]]); pen.stroke();
  pen.textAlign = "center";
  pen.fillText(given.axes.x || "", (fit.x(left) + fit.x(right)) / 2, fit.y(bottom) + 30);
  pen.fillText(String(round(left)), fit.x(left), fit.y(bottom) + 14);
  pen.fillText(String(round(right)), fit.x(right), fit.y(bottom) + 14);
  pen.save();
  pen.translate(fit.x(left) - 30, (fit.y(bottom) + fit.y(top)) / 2);
  pen.rotate(-Math.PI / 2);
  pen.fillText(given.axes.y || "", 0, 0);
  pen.restore();
  pen.textAlign = "right";
  pen.fillText(String(round(bottom)), fit.x(left) - 6, fit.y(bottom));
  pen.fillText(String(round(top)), fit.x(left) - 6, fit.y(top) + 4);
}
const round = (value) => Math.round(value * 10) / 10;

// A chart draws inside its axes only (a particle flying on past them is cut at the edge); restored after the shapes.
function clipToChart() {
  const [left, bottom, right, top] = given.bounds;
  pen.save();
  pen.beginPath();
  pen.rect(fit.x(left), fit.y(top), fit.x(right) - fit.x(left), fit.y(bottom) - fit.y(top));
  pen.clip();
}

// --- a relief: the heights raised in a turned, tilted view ------------------------------------------------------------------

function reliefHeights() {
  const steps = given.relief.steps;
  if (!steps || !steps.length) return { now: given.relief.heights, before: null };
  const rank = Math.min(play.step, steps.length - 1);
  return { now: steps[rank].heights, before: rank > 0 ? steps[rank - 1].heights : null };
}

function drawRelief() {
  const { now, before } = reliefHeights();
  const share = ease(Math.min(play.at / STEP_SECONDS, 1));
  const raise = play.step === 0 && !before ? share : 1;
  const [wide, deep] = given.relief.size, rows = now.length, columns = now[0].length;
  const height = (row, column) => {
    const target = now[row][column];
    const start = before ? before[row][column] : 0;
    return (before ? start + (target - start) * share : target * raise);
  };
  let low = Infinity, high = -Infinity;
  now.forEach((row) => row.forEach((value) => { low = Math.min(low, value); high = Math.max(high, value); }));
  const span = Math.max(high - low, 1e-6), reach = Math.max(wide, deep);
  const lift = given.relief.lift || Math.min(1, (0.25 * reach) / span);  // heights drawn at most a quarter of its width up
  const size = Math.min(holder.clientWidth, holder.clientHeight) / reach * 0.75;
  const cos = Math.cos(play.turn), sin = Math.sin(play.turn), tilt = 0.5;
  const project = (row, column) => {
    const x = (column / (columns - 1) - 0.5) * wide, z = (row / (rows - 1) - 0.5) * deep;
    const turnedX = x * cos - z * sin, turnedZ = x * sin + z * cos;
    return [holder.clientWidth / 2 + turnedX * size,
      holder.clientHeight * 0.58 + turnedZ * size * tilt - (height(row, column) - low) * lift * size];
  };
  const cells = [];
  for (let row = 0; row < rows - 1; row += 1) {
    for (let column = 0; column < columns - 1; column += 1) {
      const x = ((column + 0.5) / (columns - 1) - 0.5) * wide, z = ((row + 0.5) / (rows - 1) - 0.5) * deep;
      cells.push({ row, column, depth: x * sin + z * cos });
    }
  }
  cells.sort((one, other) => one.depth - other.depth);
  const lowColour = token("--color-view-ground"), highColour = token("--color-view-light");
  const cellWide = wide / (columns - 1), cellDeep = deep / (rows - 1);
  const sun = [-0.5, 0.8, -0.33];  // light from the north-west, above
  for (const { row, column } of cells) {
    const eastward = (height(row, column + 1) - height(row, column)) / cellWide;
    const southward = (height(row + 1, column) - height(row, column)) / cellDeep;
    const length = Math.hypot(eastward, 1, southward);
    const facing = (-eastward * sun[0] + sun[1] - southward * sun[2]) / length / Math.hypot(...sun);
    const shade = 0.45 + 0.55 * Math.max(0, facing);
    const level = (now[row][column] - low) / span;
    pen.fillStyle = mix(lowColour, highColour, 0.25 + 0.6 * level, shade);
    pen.beginPath();
    [[row, column], [row, column + 1], [row + 1, column + 1], [row + 1, column]].forEach(([r, c], rank) => {
      const [x, y] = project(r, c);
      rank ? pen.lineTo(x, y) : pen.moveTo(x, y);
    });
    pen.closePath();
    pen.fill();
  }
}

// Two token colours mixed at `share`, then darkened by `shade`.
function mix(one, other, share, shade) {
  const parts = (hex) => [1, 3, 5].map((start) => parseInt(hex.slice(start, start + 2), 16));
  const [first, second] = [parts(one), parts(other)];
  return `rgb(${first.map((value, rank) => Math.round((value + (second[rank] - value) * share) * shade)).join(",")})`;
}

// --- the loop, the controls, the hover text ---------------------------------------------------------------------------

function showSteps() {
  [...stepList.children].forEach((item, rank) => item.classList.toggle("on", rank <= play.step));
}

let last = performance.now();
function draw(now) {
  const seconds = Math.min((now - last) / 1000, 0.1);
  last = now;
  if (play.running) {
    play.at += seconds;
    play.flown += seconds / 12;
    if (play.at >= STEP_SECONDS && play.step < stepCount() - 1) { play.step += 1; play.at = 0; showSteps(); }
  }
  pen.fillStyle = token("--color-view-plinth");
  pen.fillRect(0, 0, holder.clientWidth, holder.clientHeight);
  if (given.view === "relief") drawRelief();
  else {
    drawAxes();
    if (given.axes) clipToChart(); else pen.save();
    const drawn = showing();  // words over everything else
    drawn.filter((item) => item.shape.kind !== "text").forEach(drawShape);
    drawn.filter((item) => item.shape.kind === "text").forEach(drawShape);
    pen.restore();
  }
  requestAnimationFrame(draw);
}
const stepCount = () => (given.view === "relief" && given.relief.steps ? given.relief.steps.length : given.steps.length);

function goTo(rank) {
  play.sliderFrom = null;
  play.step = rank;
  play.at = 0;
  play.running = true;
  showSteps();
}

function within(point, polygon) {
  let inside = false;
  for (let rank = 0, back = polygon.length - 1; rank < polygon.length; back = rank, rank += 1) {
    const [x1, y1] = polygon[rank], [x2, y2] = polygon[back];
    if ((y1 > point[1]) !== (y2 > point[1]) && point[0] < ((x2 - x1) * (point[1] - y1)) / (y2 - y1) + x1) inside = !inside;
  }
  return inside;
}

// The label of the top shape under the pointer, as hover text.
function hovered(event) {
  if (given.view === "relief" || !fit) return "";
  const box = canvas.getBoundingClientRect(), x = event.clientX - box.left, y = event.clientY - box.top;
  const metres = [(x - fit.x(0)) / fit.across, (fit.y(0) - y) / fit.up];
  const items = showing().reverse();
  for (const { shape } of items) {
    if (!shape.label) continue;
    if (shape.kind === "area" && within(metres, shape.points)) return shape.label;
    if (shape.kind === "dots" || shape.kind === "path" || shape.kind === "line") {
      const near = shape.points.some(([px, py]) => Math.hypot(fit.x(px) - x, fit.y(py) - y) < 8);
      if (near) return shape.label;
    }
  }
  return "";
}

canvas.addEventListener("pointermove", (event) => {
  if (dragging) { play.turn += (event.movementX || 0) * 0.01; return; }
  const said = hovered(event);
  tip.textContent = said;
  tip.hidden = !said;
});
let dragging = false;
canvas.addEventListener("pointerdown", () => { dragging = given.view === "relief"; });
window.addEventListener("pointerup", () => { dragging = false; });
stepList.addEventListener("click", (event) => {
  const item = event.target.closest("[data-step]");
  if (item) goTo(Number(item.dataset.step));
});
document.getElementById("demo-play").addEventListener("click", () => goTo(0));
if (slider) {
  slider.addEventListener("input", () => {
    play.sliderFrom = play.step === stepCount() - 1 ? play.choice : null;
    play.choice = Number(slider.value);
    document.getElementById("demo-value").textContent = `${given.slider.values[play.choice]} ${given.slider.unit || ""}`;
    play.step = stepCount() - 1;
    play.at = 0;
    showSteps();
  });
}

resize();
new ResizeObserver(resize).observe(holder);
showSteps();
holder.classList.add("loaded");
requestAnimationFrame(draw);
