// A place's 3D web copy (score/dashboard/web3d/convert.py): the light preview first, the whole copy once loaded;
// orbit and walk, a toggle per OpenUSD layer, a person 1.8 m tall, a measuring tool, and a click names the part,
// its surface, its layer and the step that made that layer.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { PointerLockControls } from "three/addons/controls/PointerLockControls.js";
import { computeBoundsTree, acceleratedRaycast } from "three-mesh-bvh";

THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;

const given = JSON.parse(document.getElementById("view3d-data").textContent);
const place = given.place;
const EYE = 1.6, STEP_UP = 0.6, PERSON = 1.8, CLICK_SLOP = 5, NO_LAYER = "not named in the copy";
const $ = (id) => document.getElementById(id);
const say = (text) => { $("status").textContent = text; };

const holder = $("stage");
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.AgXToneMapping;  // the films' tone curve
holder.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, 1, 0.05, 5000);
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.enableDamping = true;
const walk = new PointerLockControls(camera, renderer.domElement);
const raycaster = new THREE.Raycaster();
const hidden = new Set();
let sidecar = null, model = null, move = "orbit", tool = "name", ready = false;

function linear(values) { return new THREE.Color().setRGB(values[0], values[1], values[2], THREE.LinearSRGBColorSpace); }

function resize() {
  const width = Math.max(holder.clientWidth, 100), height = Math.max(holder.clientHeight, 100);
  renderer.setSize(width, height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

// The scene record keeps a camera's fov across the picture; three.js keeps it up and down.
function setAcross(degrees) {
  camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(degrees) / 2) / camera.aspect));
  camera.updateProjectionMatrix();
}

function aimAt(eye, aim, fov) {
  camera.position.set(...eye);
  camera.lookAt(...aim);
  orbit.target.set(...aim);
  if (fov) setAcross(fov);
}

function addLight(entry) {
  const at = new THREE.Vector3(...entry.at), toward = new THREE.Vector3(...entry.toward);
  let made;
  if (entry.type === "directional") {
    made = new THREE.DirectionalLight(linear(entry.colour), entry.intensity);
    made.position.copy(at).addScaledVector(toward, -100);
    made.target.position.copy(at);
  } else if (entry.type === "spot") {
    made = new THREE.SpotLight(linear(entry.colour), entry.intensity, 0, entry.angle, Math.min(entry.penumbra, 1), 2);
    made.position.copy(at);
    made.target.position.copy(at).add(toward);
  } else {
    made = new THREE.PointLight(linear(entry.colour), entry.intensity, 0, 2);
    made.position.copy(at);
  }
  scene.add(made);
  if (made.target) scene.add(made.target);
}

// --- parts and layers ---------------------------------------------------------------------------------------

// GLTFLoader's node names: spaces as underscores, and [ ] . : / dropped (three.js PropertyBinding.sanitizeNodeName).
const loaderName = (name) => name.replace(/\s/g, "_").replace(/[[\].:/]/g, "");

function partsByName() {
  const found = new Map();
  for (const object of sidecar.objects) found.set(loaderName(object.name), object);
  return found;
}

// Each mesh's part: the nearest node up its parents that the sidecar names (a repeated name gets "_<n>" added).
function markParts(root) {
  const named = partsByName();
  root.traverse((node) => {
    const own = named.get(node.name) || named.get(node.name.replace(/_\d+$/, ""));
    if (own) node.userData.part = own;
  });
  root.traverse((node) => {
    if (!node.isMesh) return;
    let up = node;
    while (up && !up.userData.part) up = up.parent;
    node.userData.part = up ? up.userData.part : { name: null, layer: NO_LAYER };
  });
}

function showLayers() {
  if (!model) return;
  model.traverse((node) => { if (node.isMesh) node.visible = !hidden.has(node.userData.part.layer); });
}

function layerCounts() {
  const counts = new Map();
  model.traverse((node) => {
    if (!node.isMesh) return;
    const layer = node.userData.part.layer;
    counts.set(layer, (counts.get(layer) || 0) + 1);
  });
  return counts;
}

function layerList() {
  const counts = layerCounts();
  const order = [...given.order.filter((name) => counts.has(name)),
                 ...[...counts.keys()].filter((name) => !given.order.includes(name)).sort()];
  const holderList = $("layers");
  holderList.classList.remove("soft");
  holderList.replaceChildren(...order.map((name) => {
    const row = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = !hidden.has(name);
    box.onchange = () => { if (box.checked) hidden.delete(name); else hidden.add(name); showLayers(); };
    row.append(box, ` ${name} `);
    const count = document.createElement("span");
    count.className = "soft";
    count.textContent = `(${counts.get(name)} meshes)`;
    row.append(count);
    const maker = given.layers[name];
    if (maker) {
      const link = document.createElement("a");
      link.href = maker.url;
      link.textContent = ` made by ${maker.label}`;
      row.append(link);
    }
    return row;
  }));
}

// --- the person and the measure -------------------------------------------------------------------------------

function personFigure() {
  const figure = new THREE.Group();
  const stuff = new THREE.MeshStandardMaterial({ color: 0xe0782a, roughness: 0.6 });
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.18, 1.06, 6, 16), stuff);
  body.position.y = 0.18 + 1.06 / 2;  // the capsule's foot on the floor
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.12, 20, 14), stuff);
  head.position.y = PERSON - 0.12;  // its crown at 1.8 m
  figure.add(body, head);
  figure.userData.helper = true;
  return figure;
}
const person = personFigure();
scene.add(person);

const measure = { points: [], marks: new THREE.Group(), line: null };
scene.add(measure.marks);

function measureMark(point) {
  const mark = new THREE.Mesh(new THREE.SphereGeometry(0.04, 12, 8), new THREE.MeshBasicMaterial({ color: 0xffd400 }));
  mark.position.copy(point);
  measure.marks.add(mark);
}

function measureClear() {
  measure.points = [];
  measure.marks.clear();
  $("measure-label").hidden = true;
}

function measureAdd(point) {
  if (measure.points.length === 2) measureClear();
  measure.points.push(point.clone());
  measureMark(point);
  if (measure.points.length < 2) { $("picked").textContent = "Click the second point."; return; }
  const [from, to] = measure.points;
  const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([from, to]),
                              new THREE.LineBasicMaterial({ color: 0xffd400, depthTest: false }));
  line.renderOrder = 10;
  measure.marks.add(line);
  const across = Math.hypot(to.x - from.x, to.z - from.z), up = Math.abs(to.y - from.y);
  const words = `${from.distanceTo(to).toFixed(2)} m`;
  $("picked").textContent = `${words} apart: ${across.toFixed(2)} m across the floor, ${up.toFixed(2)} m up or down.`;
  $("measure-label").textContent = words;
}

function measureLabel() {
  const label = $("measure-label");
  if (measure.points.length < 2) return;
  const middle = measure.points[0].clone().add(measure.points[1]).multiplyScalar(0.5).project(camera);
  label.hidden = middle.z > 1;
  label.style.left = `${(middle.x + 1) / 2 * holder.clientWidth}px`;
  label.style.top = `${(1 - middle.y) / 2 * holder.clientHeight}px`;
}

// --- picking --------------------------------------------------------------------------------------------------

function shown(node) {
  for (let up = node; up; up = up.parent) if (!up.visible) return false;
  return true;
}

function hitAt(screen) {
  raycaster.setFromCamera(screen, camera);
  raycaster.far = Infinity;
  return raycaster.intersectObject(model, true).find((hit) => shown(hit.object)) || null;
}

function surfaceOf(hit) {
  const material = Array.isArray(hit.object.material) ? hit.object.material[hit.face?.materialIndex ?? 0]
    : hit.object.material;
  return material?.name || "unnamed surface";
}

function namePart(hit) {
  const part = hit.object.userData.part;
  const maker = given.layers[part.layer];
  const rows = [["Part", part.name || "not named in the copy"], ["Surface", surfaceOf(hit)], ["Layer", part.layer]];
  const box = document.createElement("div");
  for (const [name, value] of rows) {
    const row = document.createElement("div");
    row.innerHTML = "<b></b> ";
    row.firstChild.textContent = name;
    row.append(value);
    box.append(row);
  }
  const made = document.createElement("div");
  made.innerHTML = "<b>Made by</b> ";
  if (maker) {
    const link = document.createElement("a");
    link.href = maker.url;
    link.textContent = maker.label;
    made.append(link);
  } else {
    made.append("no step: the owner's own edits, or not known");
  }
  box.append(made);
  $("picked").replaceChildren(box);
}

function picked(screen) {
  if (!ready) return;
  const hit = hitAt(screen);
  if (!hit) { $("picked").textContent = "Nothing there."; return; }
  if (tool === "measure") measureAdd(hit.point);
  else if (tool === "person") { person.position.copy(hit.point); $("person").checked = person.visible = true; }
  else namePart(hit);
}

const pressed = { x: 0, y: 0 };
renderer.domElement.addEventListener("pointerdown", (event) => { pressed.x = event.clientX; pressed.y = event.clientY; });
renderer.domElement.addEventListener("pointerup", (event) => {
  if (move === "walk") {
    if (!walk.isLocked) walk.lock();
    else picked(new THREE.Vector2(0, 0));
    return;
  }
  if (Math.hypot(event.clientX - pressed.x, event.clientY - pressed.y) > CLICK_SLOP) return;  // a drag, not a click
  const rect = renderer.domElement.getBoundingClientRect();
  picked(new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1,
                           -(event.clientY - rect.top) / rect.height * 2 + 1));
});

// --- walking --------------------------------------------------------------------------------------------------

const keys = new Set();
document.addEventListener("keydown", (event) => keys.add(event.code));
document.addEventListener("keyup", (event) => keys.delete(event.code));

function floorUnder(position) {
  raycaster.set(new THREE.Vector3(position.x, position.y - EYE + STEP_UP, position.z), new THREE.Vector3(0, -1, 0));
  raycaster.far = 50;
  const hit = raycaster.intersectObject(model, true).find((found) => shown(found.object));
  return hit ? hit.point.y : null;
}

function walkStep(seconds) {
  const speed = 3 * (keys.has("ShiftLeft") || keys.has("ShiftRight") ? 3 : 1) * seconds;
  walk.moveForward(((keys.has("KeyW") ? 1 : 0) - (keys.has("KeyS") ? 1 : 0)) * speed);
  walk.moveRight(((keys.has("KeyD") ? 1 : 0) - (keys.has("KeyA") ? 1 : 0)) * speed);
  if (!$("hold").checked) {
    camera.position.y += ((keys.has("KeyE") ? 1 : 0) - (keys.has("KeyQ") ? 1 : 0)) * speed;
    return;
  }
  const floor = ready ? floorUnder(camera.position) : null;
  if (floor !== null) camera.position.y = floor + EYE;
}

function setMove(chosen) {
  move = chosen;
  orbit.enabled = move === "orbit";
  if (move === "orbit") {
    walk.unlock();
    orbit.target.copy(camera.position).addScaledVector(camera.getWorldDirection(new THREE.Vector3()), 5);
  }
}

document.querySelectorAll("input[name=move]").forEach((input) => { input.onchange = () => setMove(input.value); });
document.querySelectorAll("input[name=tool]").forEach((input) => {
  input.onchange = () => {
    tool = input.value;
    if (tool !== "measure") measureClear();
    $("picked").textContent = { name: "Click a surface.", measure: "Click the first point.",
                                person: "Click the floor where the person stands." }[tool];
  };
});
$("person").onchange = () => { person.visible = $("person").checked; };

let last = performance.now();
function frame(now) {
  const seconds = Math.min((now - last) / 1000, 0.1);
  last = now;
  if (move === "walk" && walk.isLocked) walkStep(seconds); else orbit.update();
  measureLabel();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

// --- loading --------------------------------------------------------------------------------------------------

function viewButtons() {
  $("views").replaceChildren(...(sidecar.cameras || []).map((view) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = view.name;
    button.onclick = () => { if (move === "walk") document.querySelector("input[value=orbit]").click(); aimAt(view.eye, view.aim, view.fov); };
    return button;
  }));
}

function standPerson() {
  raycaster.set(orbit.target.clone().add(new THREE.Vector3(0, 20, 0)), new THREE.Vector3(0, -1, 0));
  raycaster.far = 100;
  const hit = raycaster.intersectObject(model, true)[0];
  person.position.copy(hit ? hit.point : orbit.target);
}

// With no camera in the scene record: look at the whole place from above one corner.
function frameModel() {
  const box = new THREE.Box3().setFromObject(model);
  const middle = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
  aimAt([middle.x + size * 0.45, middle.y + size * 0.35, middle.z + size * 0.45], middle.toArray(), 75);
}

function swapIn(loaded) {
  if (model) {
    scene.remove(model);
    model.traverse((node) => { if (node.isMesh) node.geometry.dispose(); });  // the preview, replaced
  }
  model = loaded;
  markParts(model);
  showLayers();
  scene.add(model);
  layerList();
}

async function open() {
  const answer = await fetch(`/web/${place}/${place}.json`, { credentials: "same-origin" });
  if (!answer.ok) throw new Error(`the copy's facts: ${answer.status}`);
  sidecar = await answer.json();
  resize();
  window.addEventListener("resize", resize);
  const sky = sidecar.sky || { background: [0.05, 0.05, 0.05], ambient: [0.5, 0.5, 0.5], exposure: 1 };  // an older copy
  scene.background = linear(sky.background);
  renderer.toneMappingExposure = sky.exposure;
  scene.add(new THREE.AmbientLight(linear(sky.ambient), 1));
  (sidecar.lights || []).forEach(addLight);
  viewButtons();
  const first = (sidecar.cameras || [])[0];
  if (first) aimAt(first.eye, first.aim, first.fov);
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  requestAnimationFrame(frame);
  const preview = await loader.loadAsync(`/web/${place}/${place}-light.glb`).catch(() => null);
  if (preview) {
    swapIn(preview.scene);
    if (!first) frameModel();
    ready = true;
    standPerson();
    say(`Preview shown; the whole copy (${(sidecar.bytes / 1e6).toFixed(1)} MB) is loading...`);
  }
  const whole = await loader.loadAsync(`/web/${place}/${place}.glb`);
  swapIn(whole.scene);
  if (!first && !preview) frameModel();
  ready = true;
  if (!preview) standPerson();
  say(`${sidecar.triangles.toLocaleString()} triangles.`);
  setTimeout(() => model.traverse((node) => { if (node.isMesh) node.geometry.computeBoundsTree(); }), 0);
}

open().catch((error) => { say(`Could not open the 3D copy: ${error.message}`); console.error(error); });
