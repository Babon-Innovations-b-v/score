// A library item on its own (pages/library.py viewer_of): a model, kit or character's web copy turned and zoomed
// (its light copy first, its whole copy after when this cockpit holds it; a kit as its place lays it; a copy's
// clips played), a surface on a lit sphere and tile with its settings on sliders, an effect's emitter played from its
// settings with a time scrubber, a place's lamps over a neutral test scene, and a sky: its dome looked around in from
// inside, or a planet's backdrop as its globe. Colours come from design tokens.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { token } from "./tokens.js";

const given = JSON.parse(document.getElementById("item-data").textContent);
const holder = document.getElementById("item3d");
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.AgXToneMapping;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.localClippingEnabled = true;  // an inside kit cut open
holder.prepend(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(token("--color-view-plinth"));
const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 5000);
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.enableDamping = true;
orbit.autoRotate = given.mode !== "effect" && given.mode !== "surface";  // a surface's sphere spins on its own
orbit.addEventListener("start", () => { orbit.autoRotate = false; });
const studio = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
const clock = { playing: true, at: 0, length: 0, show: null };  // an effect's or a clip's time
const spinning = [];  // objects turned slowly about their own up axis (a surface's sphere)

function resize() {
  const { clientWidth: width, clientHeight: height } = holder;
  renderer.setSize(width, height, false);
  camera.aspect = width / Math.max(height, 1);
  camera.updateProjectionMatrix();
}

// Look at a box whole, from `toward` it (by default a little above one corner).
function frame(box, toward = new THREE.Vector3(0.7, 0.45, 0.9)) {
  if (box.isEmpty()) return box;
  const middle = box.getCenter(new THREE.Vector3()), reach = box.getSize(new THREE.Vector3()).length() || 1;
  camera.position.copy(middle).add(toward.clone().multiplyScalar(reach));
  camera.near = reach / 500;
  camera.far = reach * 50;
  camera.updateProjectionMatrix();
  orbit.target.copy(middle);
  orbit.update();
  return box;
}

// A number card the copy answers (pages/library.py numbers_of `fact`): its value shown once known.
function fill(fact, text) {
  const value = document.querySelector(`[data-fact="${fact}"] .num-value`);
  if (!value) return;
  value.classList.remove("unknown");
  value.removeAttribute("title");
  value.textContent = text;
}

function shown() { holder.classList.add("loaded"); }

// --- the clock: play or pause, a scrubber, the time -----------------------------------------------------------

const controls = document.getElementById("clock");
function startClock(length, show) {
  if (!controls || !(length > 0)) return;
  Object.assign(clock, { length, show, at: 0 });
  controls.hidden = false;
  const slider = controls.querySelector("[data-time]");
  slider.max = String(length);
  slider.addEventListener("input", () => { clock.at = Number(slider.value); clock.playing = false; showTime(); });
  controls.querySelector("[data-play]").addEventListener("click", () => { clock.playing = !clock.playing; showTime(); });
}

function showTime() {
  if (!clock.show) return;
  clock.show(clock.at);
  controls.querySelector("[data-time]").value = String(clock.at);
  controls.querySelector("[data-at]").textContent = `${clock.at.toFixed(1)} s`;
  controls.querySelector("[data-play]").innerHTML = clock.playing ? "&#10074;&#10074;" : "&#9654;";
}

// --- a web copy: a model, a character, a kit --------------------------------------------------------------------

// A kit as its place lays it (its copy is the place's base layer with only the kit's objects) and its kinds of piece
// listed beside it, one opened showing one piece of that kind alone. A node is named for its prim,
// ".../Objects/<piece>_<n>" (a glowing piece's glow half "<piece>_glow_<n>"); its kind is that name less the number.
// An inside place's kit is cut open above CUT of its height, so its room shows, not its roof.
const CUT = 0.7;
const kitList = document.getElementById("kit-pieces");
const cut = new THREE.Plane(new THREE.Vector3(0, -1, 0), 0);

// The glTF node name of a mesh's piece: its own, or its node's when the piece has several materials (a group).
function pieceName(object) {
  while (object.parent && !object.userData.name) object = object.parent;
  return (object.userData.name || "").replace(/_glow(_\d+)$/, "$1");
}

// The meshes of the place's own laid set: a place laying its kit again in places of its own (the tube's three
// others, "/tube/Places/<other>/Objects/...") shows its own set only, so one tube fills the view, not four small.
function ownSet(root) {
  const sets = new Map();
  root.traverse((object) => {
    if (!object.isMesh) return;
    const set = pieceName(object).replace(/\/[^/]*$/, "");
    if (!sets.has(set)) sets.set(set, []);
    sets.get(set).push(object);
  });
  const shortest = [...sets.keys()].sort((one, other) => one.length - other.length)[0];
  return { meshes: sets.get(shortest) || [], sets: sets.size };
}

// {kind: [[the meshes of one laid piece]]}, in the copy's order.
function kitKinds(meshes) {
  const pieces = new Map();
  meshes.forEach((object) => {
    const name = pieceName(object);
    if (!pieces.has(name)) pieces.set(name, []);
    pieces.get(name).push(object);
  });
  const kinds = new Map();
  for (const [name, meshes] of pieces) {
    const kind = name.split("/").pop().replace(/_\d+$/, "");
    if (!kinds.has(kind)) kinds.set(kind, []);
    kinds.get(kind).push(meshes);
  }
  return kinds;
}

function clipped(root, planes) {
  root.traverse((object) => {
    if (!object.isMesh) return;
    for (const material of [object.material].flat()) material.clippingPlanes = planes;
  });
}

// The whole kit (`kind` empty), or the first laid piece of `kind` alone, framed.
function showKit(root, own, kinds, kind) {
  const shown = new Set(kind ? kinds.get(kind)[0] : own);
  const box = new THREE.Box3();
  root.traverse((object) => {
    if (!object.isMesh) return;
    object.visible = shown.has(object);
    if (object.visible) box.expandByObject(object);
  });
  const opened = !kind && given.inside;
  cut.constant = box.min.y + (box.max.y - box.min.y) * CUT;
  clipped(root, opened ? [cut] : []);
  if (opened) box.max.y = cut.constant;
  // an open room seen from above, a thin piece from a little further, so all of it shows
  frame(box, opened ? new THREE.Vector3(0.55, 0.9, 0.75) : new THREE.Vector3(0.9, 0.55, 1.15));
  [...kitList.children].forEach((row) => row.classList.toggle("on", row.dataset.kind === kind));
}

function kitRow(kind, label, count) {
  const row = document.createElement("li");
  row.dataset.kind = kind;
  row.tabIndex = 0;
  row.title = kind ? "one alone" : "as its place lays it";
  row.append(Object.assign(document.createElement("span"), { textContent: label }), " ",
    Object.assign(document.createElement("span"), { textContent: `× ${count}`, className: "small" }));
  row.querySelectorAll("span").forEach((span) => span.setAttribute("data-v", ""));
  return row;
}

function listKit(root) {
  const own = ownSet(root), kinds = kitKinds(own.meshes);
  const total = [...kinds.values()].reduce((sum, laid) => sum + laid.length, 0);
  const whole = kitRow("", "whole kit", total);
  if (own.sets > 1) whole.title += `, one of the ${own.sets} sets it lays`;
  kitList.replaceChildren(whole,
    ...[...kinds].map(([kind, laid]) => kitRow(kind, kind.replaceAll("_", " "), laid.length)));
  const open = (event) => {
    const row = event.target.closest("[data-kind]");
    if (row && (event.type === "click" || event.key === "Enter")) showKit(root, own.meshes, kinds, row.dataset.kind);
  };
  kitList.onclick = open;
  kitList.onkeydown = open;
  showKit(root, own.meshes, kinds, "");
}

function playClips(root, clips) {
  fill("clips", String(clips.length));
  if (!clips.length) return null;
  const mixer = new THREE.AnimationMixer(root);
  clips.forEach((clip) => mixer.clipAction(clip).play());
  startClock(Math.max(...clips.map((clip) => clip.duration)), (at) => mixer.setTime(at));
  return mixer;
}

let current = null;
async function loadCopy(loader, url) {
  const loaded = await loader.loadAsync(url);
  if (current) scene.remove(current);
  scene.add(loaded.scene);
  current = loaded.scene;
  const box = frame(new THREE.Box3().setFromObject(current));
  const size = box.getSize(new THREE.Vector3());
  fill("size", `${size.x.toFixed(2)} × ${size.y.toFixed(2)} × ${size.z.toFixed(2)}`);
  playClips(loaded.scene, loaded.animations);
  if (given.mode === "kit") listKit(current);
  shown();
}

async function openCopy() {
  scene.environment = studio;
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  if (given.light) await loadCopy(loader, given.light);
  if (given.full) await loadCopy(loader, given.full);
}

// --- a surface: a sphere and a tile, its settings on sliders -------------------------------------------------------

const WEAR_SIDE = 256;

// A seeded value noise, three octaves, 0 to 1, over a square of `side` cells that tiles.
function noise(seed, side) {
  let state = seed * 2654435761 % 4294967296;
  const random = () => { state = (state * 1664525 + 1013904223) % 4294967296; return state / 4294967296; };
  const values = [];
  for (const cells of [8, 16, 32]) {
    const grid = Array.from({ length: cells * cells }, random);
    const at = (column, row) => grid[(row % cells) * cells + (column % cells)];
    values.push((x, y) => {
      const u = (x / side) * cells, v = (y / side) * cells, column = Math.floor(u), row = Math.floor(v);
      const across = u - column, down = v - row;
      const top = at(column, row) * (1 - across) + at(column + 1, row) * across;
      const bottom = at(column, row + 1) * (1 - across) + at(column + 1, row + 1) * across;
      return top * (1 - down) + bottom * down;
    });
  }
  return (x, y) => (values[0](x, y) * 4 + values[1](x, y) * 2 + values[2](x, y)) / 7;
}

// The colour and roughness pictures of a worn surface: worn patches darker and rougher, where the seed puts them.
function wornPictures(print, wear, seed, roughness) {
  const colour = document.createElement("canvas"), rough = document.createElement("canvas");
  colour.width = colour.height = rough.width = rough.height = WEAR_SIDE;
  const paint = colour.getContext("2d");
  if (print) paint.drawImage(print, 0, 0, WEAR_SIDE, WEAR_SIDE);
  else { paint.fillStyle = token("--color-view-light"); paint.fillRect(0, 0, WEAR_SIDE, WEAR_SIDE); }
  const pixels = paint.getImageData(0, 0, WEAR_SIDE, WEAR_SIDE), roughPixels = new ImageData(WEAR_SIDE, WEAR_SIDE);
  const field = noise(seed, WEAR_SIDE);
  for (let y = 0; y < WEAR_SIDE; y++) {
    for (let x = 0; x < WEAR_SIDE; x++) {
      const worn = THREE.MathUtils.smoothstep(field(x, y), 1 - wear, 1 - wear + 0.12) * Math.min(wear * 4, 1);
      const index = (y * WEAR_SIDE + x) * 4;
      for (let channel = 0; channel < 3; channel++) pixels.data[index + channel] *= 1 - 0.45 * worn;
      roughPixels.data[index + 1] = 255 * (roughness + (1 - roughness) * 0.8 * worn);
      roughPixels.data[index + 3] = 255;
    }
  }
  paint.putImageData(pixels, 0, 0);
  rough.getContext("2d").putImageData(roughPixels, 0, 0);
  const map = new THREE.CanvasTexture(colour), roughMap = new THREE.CanvasTexture(rough);
  map.colorSpace = THREE.SRGBColorSpace;
  return { map, roughMap };
}

async function openSurface() {
  scene.environment = studio;
  const finish = given.finish || {};
  const material = new THREE.MeshPhysicalMaterial({ metalness: finish.metallic ?? 0, roughness: 1,
    transparent: (finish.opacity ?? 1) < 1, opacity: finish.opacity ?? 1 });
  const own = finish.colour ? new THREE.Color().setRGB(...finish.colour, THREE.LinearSRGBColorSpace) : null;
  if (finish.glow) material.emissive.setRGB(...finish.glow, THREE.LinearSRGBColorSpace);
  const print = given.print ? (await new THREE.TextureLoader().loadAsync(given.print).catch(() => null))?.image : null;
  const form = document.getElementById("surface-controls");
  form.shine.value = String(1 - (finish.roughness ?? 0.5));
  form.metal.value = String(finish.metallic ?? 0);
  const update = () => {
    const chosen = form.token.value;
    material.color = chosen === given.token && own ? own.clone() : new THREE.Color(given.palette[chosen] || token("--color-view-light"));
    const pictures = wornPictures(print, Number(form.wear.value), Number(form.seed.value), 1 - Number(form.shine.value));
    material.metalness = Number(form.metal.value);
    material.map?.dispose();
    material.roughnessMap?.dispose();
    material.map = pictures.map;
    material.roughnessMap = pictures.roughMap;
    material.needsUpdate = true;
  };
  form.addEventListener("input", update);
  update();
  const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.5, 96, 64), material);
  const tile = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 0.04), material);  // a flat swatch facing the eye
  sphere.position.x = -0.6;
  tile.position.x = 0.6;
  const pair = new THREE.Group().add(sphere, tile);
  scene.add(pair);
  spinning.push(sphere);
  frame(new THREE.Box3().setFromObject(pair), new THREE.Vector3(0, 0.15, 1.1));
  shown();
}

// --- an effect: its emitter played from its settings ---------------------------------------------------------------

const MOST_CARDS = 20000;  // cards drawn at most; an emitter with more is drawn thinned

function curveAt(points, share) {
  if (!points || !points.length) return 1;
  const after = points.findIndex(([at]) => at >= share);
  if (after <= 0) return points[after === 0 ? 0 : points.length - 1][1];
  const [from, low] = points[after - 1], [to, high] = points[after];
  return low + ((high - low) * (share - from)) / Math.max(to - from, 1e-6);
}

// A soft round card: the light's colour, fading out to its edge.
function cardSprite() {
  const side = 64, light = new THREE.Color(token("--color-view-light")), pixels = new Uint8Array(side * side * 4);
  for (let y = 0; y < side; y++) {
    for (let x = 0; x < side; x++) {
      const out = Math.hypot(x - side / 2 + 0.5, y - side / 2 + 0.5) / (side / 2), index = (y * side + x) * 4;
      pixels.set([light.r * 255, light.g * 255, light.b * 255, 255 * Math.max(0, 1 - out) ** 2], index);
    }
  }
  const sprite = new THREE.DataTexture(pixels, side, side);
  sprite.needsUpdate = true;
  return sprite;
}

// Each card's start, heading and speed, the same every time (its seed).
function cards(settings, count) {
  let state = (settings.seed || 1) * 2654435761 % 4294967296;
  const random = () => { state = (state * 1664525 + 1013904223) % 4294967296; return state / 4294967296; };
  const [width, height, inner] = settings.emitter_size || [0, 0, 0];
  const heading = new THREE.Vector3(...(settings.direction || [0, 1, 0])).normalize();
  const spread = THREE.MathUtils.degToRad(settings.spread || 0);
  const [slow, fast] = settings.speed || [0, 0];
  return Array.from({ length: count }, () => {
    let start;
    if (settings.emitter === "ring") {
      const turn = random() * Math.PI * 2, radius = inner + (width - inner) * Math.sqrt(random());
      start = new THREE.Vector3(Math.cos(turn) * radius, (random() - 0.5) * height, Math.sin(turn) * radius);
    } else if (settings.emitter === "sphere") {
      start = new THREE.Vector3(random() - 0.5, random() - 0.5, random() - 0.5).normalize().multiplyScalar(width * Math.cbrt(random()));
    } else if (settings.emitter === "box") {
      start = new THREE.Vector3((random() - 0.5) * width * 2, (random() - 0.5) * height * 2, (random() - 0.5) * inner * 2);
    } else start = new THREE.Vector3();
    const tilt = spread * Math.sqrt(random()), around = random() * Math.PI * 2;
    const side = new THREE.Vector3(1, 0, 0).cross(heading).lengthSq() > 1e-6 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 0, 1);
    const off = side.cross(heading).normalize().applyAxisAngle(heading, around);
    const velocity = heading.clone().applyAxisAngle(off, tilt).multiplyScalar(slow + (fast - slow) * random());
    return { start, velocity, birth: random() };
  });
}

function openEffect() {
  const settings = given.settings;
  if (!settings) return;
  const life = settings.lifetime || 1, length = settings.loop || life;
  const count = Math.min(settings.count || 0, MOST_CARDS);
  const made = cards(settings, count);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(count * 3), 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(new Float32Array(count * 4), 4));
  const scale = settings.scale ? (settings.scale[0] + settings.scale[1]) / 2 : 1;
  const material = new THREE.PointsMaterial({ size: (settings.size || 0.1) * scale, map: cardSprite(), vertexColors: true,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });  // faint cards add up to a veil
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  scene.add(points);
  const colour = new THREE.Color().setRGB(...(settings.colour || [1, 1, 1]), THREE.LinearSRGBColorSpace)
    .multiplyScalar(settings.brightness ?? 1);
  const gravity = new THREE.Vector3(...(settings.gravity || [0, 0, 0])), wind = new THREE.Vector3(...(settings.wind || [0, 0, 0]));
  const place = new THREE.Vector3(), positions = geometry.attributes.position, colours = geometry.attributes.color;
  // A burst (`once`: from its first second for its second's length) lets each card out once; else they stream.
  const [burstFrom, burstFor] = settings.once || [0, 0];
  const damping = settings.damping ? (settings.damping[0] + settings.damping[1]) / 2 : 0;
  const ageOf = (card, at) => (burstFor > 0 ? at - burstFrom - card.birth * burstFor
    : (((at - card.birth * life * (1 - (settings.explosiveness || 0))) % life) + life) % life);
  const show = (at) => {
    made.forEach((card, rank) => {
      const age = ageOf(card, at);
      if (age < 0 || age >= life) { colours.setW(rank, 0); return; }
      const moved = damping > 0 ? (1 - Math.exp(-damping * age)) / damping : age;  // slowed by its damping
      place.copy(card.start).addScaledVector(card.velocity, moved).addScaledVector(gravity, 0.5 * age * age).addScaledVector(wind, age);
      place.applyAxisAngle(THREE.Object3D.DEFAULT_UP, (settings.spin || 0) * age);
      positions.setXYZ(rank, place.x, place.y, place.z);
      colours.setXYZW(rank, colour.r, colour.g, colour.b, (settings.opacity ?? 1) * curveAt(settings.opacity_over_life, age / life));
    });
    positions.needsUpdate = colours.needsUpdate = true;
  };
  show(burstFor > 0 ? burstFrom + burstFor / 2 + life / 4 : life / 2);
  geometry.computeBoundingBox();
  frame(geometry.boundingBox.clone());
  startClock(length, show);
  shown();
}

// --- a light: its lamps over a neutral test scene -----------------------------------------------------------------

function lampOf(lamp) {
  const colour = new THREE.Color().setRGB(...lamp.colour, THREE.LinearSRGBColorSpace);
  if (lamp.type === "dome") return new THREE.HemisphereLight(colour, token("--color-view-ground"), lamp.power * Math.PI);
  if (lamp.type === "sun") {
    const sun = new THREE.DirectionalLight(colour, lamp.power);
    sun.position.set(3, 5, 2);
    sun.castShadow = true;
    return sun;
  }
  const point = new THREE.PointLight(colour, lamp.power, 0, 2);
  point.position.set(1.2, 2.2, 1.2);
  if (lamp.spot) {  // a place's lamp where it stands, its rig's middle over the test scene, with a bulb to see it by
    point.position.set(lamp.spot[0] - rigMiddle.x, lamp.spot[1], lamp.spot[2] - rigMiddle.z);
    point.add(new THREE.Mesh(new THREE.SphereGeometry(0.08, 16, 8), new THREE.MeshBasicMaterial({ color: colour })));
  }
  point.castShadow = true;
  return point;
}

// The middle of a place's lamps across the floor, and how far they reach from it.
const rigMiddle = new THREE.Vector3();
let rigReach = 0;
function measureRig(lamps) {
  const spots = lamps.filter((lamp) => lamp.spot).map((lamp) => new THREE.Vector3(...lamp.spot));
  if (!spots.length) return;
  const box = new THREE.Box3().setFromPoints(spots);
  box.getCenter(rigMiddle);
  rigReach = Math.max(box.max.x - box.min.x, box.max.z - box.min.z);
}

function openLight() {
  renderer.shadowMap.enabled = true;
  measureRig(given.lamps || []);
  const neutral = new THREE.MeshStandardMaterial({ color: token("--color-view-light"), roughness: 0.55 });
  const side = Math.max(8, rigReach + 4);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(side, side), new THREE.MeshStandardMaterial({ color: token("--color-view-plinth"), roughness: 0.9 }));
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  const shapes = [new THREE.SphereGeometry(0.4, 64, 32), new THREE.BoxGeometry(0.7, 0.7, 0.7), new THREE.CylinderGeometry(0.3, 0.3, 1, 48)]
    .map((geometry, rank) => {
      const shape = new THREE.Mesh(geometry, neutral);
      shape.position.set((rank - 1) * 1.1, geometry.type === "CylinderGeometry" ? 0.5 : 0.4, 0);
      shape.castShadow = shape.receiveShadow = true;
      return shape;
    });
  const objects = new THREE.Group().add(...shapes);
  scene.add(floor, objects, ...(given.lamps || []).map(lampOf));
  frame(new THREE.Box3().setFromObject(rigReach ? floor : objects));
  shown();
}

// --- a sky: its picture as a dome round the viewer, looked around in; a planet's backdrop as its globe ---------------

async function openSky() {
  const picture = await new THREE.TextureLoader().loadAsync(given.picture);
  picture.colorSpace = THREE.SRGBColorSpace;
  if (given.sky === "dome") {
    const dome = new THREE.Mesh(new THREE.SphereGeometry(50, 64, 32), new THREE.MeshBasicMaterial({ map: picture, side: THREE.BackSide }));
    scene.add(dome);
    camera.position.set(0, 0, 0.01);  // inside it: dragging turns the view
    orbit.target.set(0, 0, 0);
    orbit.enableZoom = false;
    orbit.rotateSpeed = -0.35;
    orbit.autoRotateSpeed = 0.4;
  } else {
    const globe = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 48), new THREE.MeshBasicMaterial({ map: picture }));
    scene.add(globe);
    scene.background = new THREE.Color(token("--color-bg"));
    frame(new THREE.Box3().setFromObject(globe), new THREE.Vector3(0, 0.2, 1.2));
  }
  orbit.update();
  shown();
}

// --- the loop ------------------------------------------------------------------------------------------------------

let last = performance.now();
function draw(now) {
  const seconds = Math.min((now - last) / 1000, 0.1);
  last = now;
  if (clock.playing && clock.length > 0) { clock.at = (clock.at + seconds) % clock.length; showTime(); }
  spinning.forEach((object) => { object.rotation.y += seconds * 0.4; });
  orbit.update();
  renderer.render(scene, camera);
  requestAnimationFrame(draw);
}

const OPEN = { copy: openCopy, kit: openCopy, surface: openSurface, effect: openEffect, light: openLight, sky: openSky };
resize();
new ResizeObserver(resize).observe(holder);
requestAnimationFrame(draw);
Promise.resolve(OPEN[given.mode]()).catch((error) => { holder.classList.add("failed"); console.error(error); });
