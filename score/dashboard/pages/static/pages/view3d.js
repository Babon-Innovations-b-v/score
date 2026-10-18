// A place's 3D web copy (score/dashboard/web3d/convert.py): the light preview first, then the places it shows, then
// the whole copy; lit as the films are (its lamps, its sky, light bounced off its own surfaces from a probe at the
// camera, AgX at the film's exposure); orbit and walk, a toggle per OpenUSD layer (its meshes, lamps, effects as
// points, motion), a person 1.8 m tall, a measuring tool, and a click names the part, its surface, its layer and the
// step that made that layer.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { PointerLockControls } from "three/addons/controls/PointerLockControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { computeBoundsTree, acceleratedRaycast } from "three-mesh-bvh";

THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;

const given = JSON.parse(document.getElementById("view3d-data").textContent);
const place = given.place;
const base = given.base || `/web/${place}/`;  // the current copy, or a proposed version's
// The hidden layers: none, or, from a breakdown's "show in 3D" (given.only), every layer but those named until its box
// is ticked.
class Hidden extends Set {
  constructor(only) { super(); this.only = only ? new Set(only) : null; this.chosen = new Set(); }
  has(name) { return this.only && !this.only.has(name) && !this.chosen.has(name) ? true : super.has(name); }
  add(name) { this.chosen.add(name); return super.add(name); }
  delete(name) { this.chosen.add(name); return super.delete(name); }
}
const others = given.others || "/web/";  // where the places it shows keep their own current copies
const EYE = 1.6, STEP_UP = 0.6, PERSON = 1.8, CLICK_SLOP = 5, NO_LAYER = "not named in the copy";
// The probe: a cube picture of the lit place from the camera, the light its surfaces bounce (BOUNCES times over),
// made again once the camera rests REPROBE_METRES from where it was made.
const PROBE_SIDE = 128, BOUNCES = 3, REPROBE_METRES = 4, REST_FRAMES = 20;
// Lamps that cast shadows at once (the brightest where the probe is), each map PROBE-fixed: drawn once a probe.
const SHADOW_LAMPS = 4, SHADOW_SIDE = 1024, SUN_SHADOW_METRES = 60;
// The orbit turns about a point this far ahead of the camera at most (a film's aim may be a city 260 m off).
const ORBIT_REACH = 6;
// The films' glow: what is brighter than the place's glow threshold blooms (Blender's glare at strength 1; three.js's
// bloom normalises its own way, so its strength and spread are set by eye against the stills).
const BLOOM_STRENGTH = 0.6, BLOOM_RADIUS = 0.5;
// An effect's points are each this much of its opacity: thousands overlap into one cloud.
const POINT_SHARE = 0.25;
const $ = (id) => document.getElementById(id);
const say = (text) => { $("status").textContent = text; };

const holder = $("stage");
const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.AgXToneMapping;  // the films' tone curve
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.shadowMap.autoUpdate = false;  // the place stands still: its shadows are drawn once a probe
holder.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, 1, 0.05, 20000);  // the far city's mountains stand about 5 km off
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.enableDamping = true;
const walk = new PointerLockControls(camera, renderer.domElement);
const raycaster = new THREE.Raycaster();
const hidden = new Hidden(given.only);
const model = new THREE.Group();  // the place's own copy (preview, then whole) and the places it shows
const copies = { own: null, around: null };
const lamps = [], effects = new THREE.Group();
scene.add(model, effects);
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), BLOOM_STRENGTH, BLOOM_RADIUS, 1);
bloom.enabled = false;
composer.addPass(bloom);
composer.addPass(new OutputPass());  // AgX and the exposure, then sRGB
const ambient = new THREE.AmbientLight(0xffffff, 1);
scene.add(ambient);
let sidecar = null, move = "orbit", tool = "name", ready = false;

function linear(values) { return new THREE.Color().setRGB(values[0], values[1], values[2], THREE.LinearSRGBColorSpace); }

function resize() {
  const width = Math.max(holder.clientWidth, 100), height = Math.max(holder.clientHeight, 100);
  renderer.setSize(width, height);
  composer.setSize(width, height);
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
  const ahead = new THREE.Vector3(...aim).sub(camera.position);
  orbit.target.copy(camera.position).addScaledVector(ahead.normalize(), Math.min(ORBIT_REACH, ahead.length() || 1));
  if (fov) setAcross(fov);
}

// --- light -----------------------------------------------------------------------------------------------------

function shadowed(made, side) {
  made.shadow.mapSize.set(side, side);
  made.shadow.bias = -0.0004;
  made.shadow.normalBias = 0.02;
  return made;
}

function lampOf(entry) {
  const at = new THREE.Vector3(...entry.at), toward = new THREE.Vector3(...entry.toward);
  let made;
  if (entry.type === "directional") {
    made = new THREE.DirectionalLight(linear(entry.colour), entry.intensity);
    made.userData.toward = toward;
    made.position.copy(at).addScaledVector(toward, -100);
    made.target.position.copy(at);
  } else if (entry.type === "spot") {
    made = new THREE.SpotLight(linear(entry.colour), entry.intensity, 0, entry.angle, Math.min(entry.penumbra, 1), 2);
    made.position.copy(at);
    made.target.position.copy(at).add(toward);
  } else {
    made = new THREE.PointLight(linear(entry.colour), entry.intensity, 0, 2);
    made.position.copy(at);
    made.shadow.camera.near = 0.05;
  }
  made.userData.entry = entry;
  return shadowed(made, SHADOW_SIDE);
}

function addLamps(entries) {
  for (const entry of entries) {
    const made = lampOf(entry);
    lamps.push(made);
    scene.add(made);
    if (made.target) scene.add(made.target);
  }
}

// A lamp shines while the light layer is on, and, for one of a place the scene shows, while that place is.
function lampShown(made) { return !hidden.has("light") && !shownPlaceHidden(made.userData.entry.layer); }

function shownPlaceHidden(layer) { return Boolean(layer) && layer.startsWith("place ") && hidden.has(layer); }

// How strongly a lamp lights the point `at` (a sun: everywhere alike).
function reach(made, at) {
  if (made.isDirectionalLight) return Infinity;
  return made.intensity / Math.max(made.position.distanceToSquared(at), 0.25);
}

// The sun follows the probe: its shadow box centred there. The SHADOW_LAMPS lamps that light the probe's point most
// cast shadows; the count stays the same, so no surface's shader is made again.
function placeShadows(at) {
  const shown = lamps.filter((made) => made.visible && made.userData.entry.shadows !== false);
  const casting = new Set(shown.sort((one, other) => reach(other, at) - reach(one, at)).slice(0, SHADOW_LAMPS));
  for (const made of lamps) {
    made.castShadow = casting.has(made);
    if (!made.isDirectionalLight) continue;
    made.target.position.copy(at);
    made.position.copy(at).addScaledVector(made.userData.toward, -200);
    Object.assign(made.shadow.camera, { left: -SUN_SHADOW_METRES, right: SUN_SHADOW_METRES, top: SUN_SHADOW_METRES,
                                        bottom: -SUN_SHADOW_METRES, near: 1, far: 400 });
    made.shadow.camera.updateProjectionMatrix();
    scene.add(made.target);
  }
  renderer.shadowMap.needsUpdate = true;
}

const probeTarget = new THREE.WebGLCubeRenderTarget(PROBE_SIDE, { type: THREE.HalfFloatType });
const probeCamera = new THREE.CubeCamera(0.05, 20000, probeTarget);
const pmrem = new THREE.PMREMGenerator(renderer);
const probe = { light: null, at: null, sky: new THREE.Color(), still: 0, last: new THREE.Vector3() };

// The light bounced to every surface: the place drawn into a cube from `at` against its sky's own radiance (the dome
// the films light with), BOUNCES times, each time lit by the last; the dome's flat ambient is then off.
function probeAt(at) {
  const helpers = [person, measure.marks, effects];
  const were = helpers.map((helper) => helper.visible);
  helpers.forEach((helper) => { helper.visible = false; });
  placeShadows(at);
  const seen = scene.background;
  scene.background = probe.sky;
  probeCamera.position.copy(at);
  for (let bounce = 0; bounce < BOUNCES; bounce++) {
    probeCamera.update(renderer, scene);
    const made = pmrem.fromCubemap(probeTarget.texture);
    if (probe.light) probe.light.dispose();
    probe.light = made;
    scene.environment = made.texture;
    ambient.intensity = 0;
  }
  scene.background = seen;
  helpers.forEach((helper, number) => { helper.visible = were[number]; });
  probe.at = at.clone();
}

// A probe again once the camera has rested REST_FRAMES frames REPROBE_METRES from the last.
function probeWhenResting() {
  if (!ready || !probe.at) return;
  probe.still = camera.position.distanceTo(probe.last) < 0.01 ? probe.still + 1 : 0;
  probe.last.copy(camera.position);
  if (probe.still === REST_FRAMES && camera.position.distanceTo(probe.at) > REPROBE_METRES) probeAt(camera.position);
}

// --- parts and layers ---------------------------------------------------------------------------------------

// GLTFLoader's node names: spaces as underscores, and [ ] . : / dropped (three.js PropertyBinding.sanitizeNodeName).
const loaderName = (name) => name.replace(/\s/g, "_").replace(/[[\].:/]/g, "");

function partsByName() {
  const found = new Map();
  for (const object of sidecar.objects) found.set(loaderName(object.name), object);
  return found;
}

// Each named node's part (a repeated name gets "_<n>" added), and each mesh's: the nearest node up its parents that
// the sidecar names. A shown place's own copy names its nodes from that place's root: `prefix` is its root's path
// here, and a node the sidecar does not name (a copy newer than the stage) is still that place's (`layer`).
// {part name: [its named nodes]}.
function markParts(root, prefix = "", layer = NO_LAYER) {
  const named = partsByName(), nodes = new Map(), key = loaderName(prefix);
  root.traverse((node) => {
    if (node === root) return;
    const own = named.get(key + node.name) || named.get(key + node.name.replace(/_\d+$/, ""));
    if (!own) return;
    node.userData.part = own;
    if (!nodes.has(own.name)) nodes.set(own.name, []);
    nodes.get(own.name).push(node);
  });
  root.traverse((node) => {
    if (!node.isMesh) return;
    let up = node;
    while (up && !up.userData.part) up = up.parent;
    node.userData.part = up ? up.userData.part : { name: null, layer };
  });
  return nodes;
}

// What of a shown place's own copy the showing stage leaves out (its ground, its sky, the far ring this place has
// too): each node whose name begins with one of `hidden` (paths from that place's root), as the loader names it.
function leaveOut(root, hidden) {
  const names = hidden.map(loaderName);
  const gone = [];
  root.traverse((node) => { if (node !== root && names.some((name) => node.name.startsWith(name))) gone.push(node); });
  gone.forEach((node) => node.removeFromParent());
}

// A point instancer's prototype (the far city's towers): each of its meshes drawn once a place it stands.
function instanced(mesh, matrices) {
  mesh.updateWorldMatrix(true, false);
  const into = mesh.matrixWorld.clone().invert(), out = mesh.matrixWorld;
  const made = new THREE.InstancedMesh(mesh.geometry, mesh.material, matrices.length);
  const each = new THREE.Matrix4();
  matrices.forEach((numbers, number) => {
    made.setMatrixAt(number, each.fromArray(numbers).premultiply(into).multiply(out));
  });
  made.applyMatrix4(mesh.matrix);
  made.name = mesh.name;
  made.userData.part = mesh.userData.part;
  return made;
}

function placeInstances(nodes) {
  for (const instancer of sidecar.instancers || []) {
    for (const prototype of instancer.prototypes) {
      for (const name of prototype.objects) {
        for (const node of nodes.get(name) || []) {
          const meshes = [];
          node.traverse((found) => { if (found.isMesh && !found.isInstancedMesh && found.parent) meshes.push(found); });
          meshes.forEach((mesh) => { mesh.parent.add(instanced(mesh, prototype.matrices)); mesh.removeFromParent(); });
        }
      }
    }
  }
}

// --- fewer draws ----------------------------------------------------------------------------------------------

// A copy keeps every object its own node (so a click names it and a layer hides it), thousands of them; drawn so,
// each frame and each probe is thousands of draws. The meshes that stand still are joined, per layer and surface,
// into one each; each joined mesh keeps which triangles came from which part, so a click still names it.

function attributeKey(geometry) {
  return Object.entries(geometry.attributes).map(([name, values]) => `${name}${values.itemSize}`).sort().join(",");
}

const COMPONENTS = ["getX", "getY", "getZ", "getW"];

// One attribute as plain floats (a quantized one read back to its values).
function plainValues(values) {
  const made = new Float32Array(values.count * values.itemSize);
  for (let index = 0; index < values.count; index++) {
    for (let component = 0; component < values.itemSize; component++) {
      made[index * values.itemSize + component] = values[COMPONENTS[component]](index);
    }
  }
  return made;
}

// The meshes' geometries, each moved by its matrix, as one geometry: {geometry, ranges: [first triangle, part]}.
function joined(meshes, into) {
  const pieces = meshes.map((mesh) => {
    const piece = new THREE.BufferGeometry();
    for (const [name, values] of Object.entries(mesh.geometry.attributes)) {
      piece.setAttribute(name, new THREE.BufferAttribute(plainValues(values), values.itemSize));
    }
    const count = mesh.geometry.attributes.position.count;
    piece.setIndex(new THREE.BufferAttribute(mesh.geometry.index ? Uint32Array.from(mesh.geometry.index.array)
                                             : Uint32Array.from({ length: count }, (unused, index) => index), 1));
    piece.applyMatrix4(new THREE.Matrix4().multiplyMatrices(into, mesh.matrixWorld));
    return piece;
  });
  const geometry = new THREE.BufferGeometry(), ranges = [];
  for (const name of Object.keys(pieces[0].attributes)) {
    const size = pieces[0].attributes[name].itemSize;
    const all = new Float32Array(pieces.reduce((sum, piece) => sum + piece.attributes[name].array.length, 0));
    let at = 0;
    for (const piece of pieces) { all.set(piece.attributes[name].array, at); at += piece.attributes[name].array.length; }
    geometry.setAttribute(name, new THREE.BufferAttribute(all, size));
  }
  const corners = new Uint32Array(pieces.reduce((sum, piece) => sum + piece.index.count, 0));
  let corner = 0, offset = 0;
  pieces.forEach((piece, number) => {
    ranges.push([corner / 3, meshes[number].userData.part]);
    for (const index of piece.index.array) corners[corner++] = index + offset;
    offset += piece.attributes.position.count;
    piece.dispose();
  });
  geometry.setIndex(new THREE.BufferAttribute(corners, 1));
  return { geometry, ranges };
}

// The nodes the motion moves and the instancers' prototypes, and all under them: never joined.
function keptApart(nodes) {
  const names = [...(sidecar.motion ? sidecar.motion.movers.flatMap((mover) => mover.objects) : []),
                 ...(sidecar.instancers || []).flatMap((each) => each.prototypes.flatMap((proto) => proto.objects))];
  const kept = new Set();
  for (const name of names) for (const node of nodes.get(name) || []) node.traverse((under) => kept.add(under));
  return kept;
}

function joinStill(root, nodes) {
  const kept = keptApart(nodes), groups = new Map();
  root.updateMatrixWorld(true);
  root.traverse((node) => {
    if (!node.isMesh || node.isInstancedMesh || kept.has(node) || Array.isArray(node.material)) return;
    const key = `${node.userData.part.layer}|${node.material.uuid}|${attributeKey(node.geometry)}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(node);
  });
  const into = root.matrixWorld.clone().invert();
  for (const meshes of groups.values()) {
    if (meshes.length < 2) continue;
    const { geometry, ranges } = joined(meshes, into);
    const made = new THREE.Mesh(geometry, meshes[0].material);
    made.name = meshes[0].material.name;
    made.userData.part = { name: null, layer: meshes[0].userData.part.layer };
    made.userData.ranges = ranges;
    root.add(made);
    meshes.forEach((mesh) => { mesh.removeFromParent(); mesh.geometry.dispose(); });
  }
}

// The part a click hit: a joined mesh's by the triangle, else the mesh's own.
function partOf(hit) {
  const ranges = hit.object.userData.ranges;
  if (!ranges || hit.faceIndex == null) return hit.object.userData.part;
  let low = 0, high = ranges.length - 1;
  while (low < high) {
    const middle = (low + high + 1) >> 1;
    if (ranges[middle][0] <= hit.faceIndex) low = middle; else high = middle - 1;
  }
  return ranges[low][1];
}

function showLayers() {
  model.traverse((node) => { if (node.isMesh) node.visible = !hidden.has(node.userData.part.layer); });
  lamps.forEach((made) => { made.visible = lampShown(made); });
  effects.children.forEach((points) => {
    points.visible = !hidden.has("effects") && !shownPlaceHidden(points.userData.layer);
  });
  if (hidden.has("motion")) restMovers();
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

// What each layer holds, in words: its meshes, and the lamps, effects, movers and sounds the stage's own layers
// carry. {layer: [words]}; a layer with nothing to show or switch gets none.
function layerHoldings() {
  const holds = new Map();
  const add = (layer, words) => { if (!holds.has(layer)) holds.set(layer, []); holds.get(layer).push(words); };
  for (const [layer, count] of layerCounts()) add(layer, `${count} meshes`);
  if (lamps.length) add("light", `${lamps.length} lamps`);
  if (effects.children.length) add("effects", `${effects.children.length} effects as points`);
  const movers = sidecar.motion ? sidecar.motion.movers.length : 0;
  if (movers) add("motion", `${movers} moving, played`);
  return holds;
}

function layerOrder(holds) {
  const named = [...given.order, ...(sidecar.stage_layers || [])];
  const known = [...new Set(named)];
  return [...known, ...[...holds.keys()].filter((name) => !known.includes(name)).sort()];
}

function layerRow(name, holds) {
  const row = document.createElement("label");
  const words = holds.get(name);
  if (words) {
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = !hidden.has(name);
    box.onchange = () => { if (box.checked) hidden.delete(name); else hidden.add(name); layersChanged(name); };
    row.append(box);
  }
  row.append(` ${name} `);
  const count = document.createElement("span");
  count.className = "soft";
  count.textContent = words ? `(${words.join(", ")})` : name === "sound" && sidecar.sounds
    ? `(${sidecar.sounds} sounds, heard in the films, not drawn)` : "(nothing to draw)";
  row.append(count);
  const maker = given.layers[name];
  if (maker) {
    const link = document.createElement("a");
    link.href = maker.url;
    link.textContent = ` made by ${maker.label}`;
    row.append(link);
  }
  return row;
}

function layerList() {
  const holds = layerHoldings();
  const holderList = $("layers");
  holderList.classList.remove("soft");
  holderList.replaceChildren(...layerOrder(holds).map((name) => layerRow(name, holds)));
}

// A layer switched: shown or hidden, and the light probed again where it was (a lamp or a wall gone changes it).
function layersChanged() {
  showLayers();
  if (probe.at) probeAt(probe.at);
}

// --- effects and motion ---------------------------------------------------------------------------------------

function spark() {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const draw = canvas.getContext("2d");
  const fade = draw.createRadialGradient(32, 32, 0, 32, 32, 32);
  fade.addColorStop(0, "rgba(255,255,255,1)");
  fade.addColorStop(1, "rgba(255,255,255,0)");
  draw.fillStyle = fade;
  draw.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(canvas);
}

// An effect's points (convert.py packs them as 16-bit steps across their box) as one soft, glowing cloud.
function effectPoints(entry, sprite) {
  const steps = new Uint16Array(Uint8Array.from(atob(entry.points.data), (char) => char.charCodeAt(0)).buffer);
  const placed = new Float32Array(steps.length);
  for (let number = 0; number < steps.length; number++) {
    const axis = number % 3;
    placed[number] = entry.points.low[axis] + steps[number] / 65535 * (entry.points.high[axis] - entry.points.low[axis]);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(placed, 3));
  const material = new THREE.PointsMaterial({ color: linear(entry.colour), size: entry.size, map: sprite,
                                              transparent: true, opacity: entry.opacity * POINT_SHARE,
                                              blending: THREE.AdditiveBlending, depthWrite: false });
  const points = new THREE.Points(geometry, material);
  points.userData.layer = entry.layer;
  points.name = entry.name;
  return points;
}

function addEffects(entries) {
  const sprite = spark();
  entries.forEach((entry) => effects.add(effectPoints(entry, sprite)));
}

const movers = [];  // {keys: [{code, at, turn, size}], nodes: [{node, rest}]}

function moverKeys(keys) {
  return keys.map(([code, numbers]) => {
    const key = { code, at: new THREE.Vector3(), turn: new THREE.Quaternion(), size: new THREE.Vector3() };
    new THREE.Matrix4().fromArray(numbers).decompose(key.at, key.turn, key.size);
    return key;
  });
}

// The movers' nodes in a copy just loaded, each with the matrix it stands at.
function findMovers(nodes) {
  movers.length = 0;
  for (const mover of sidecar.motion ? sidecar.motion.movers : []) {
    const found = mover.objects.flatMap((name) => nodes.get(name) || []);
    if (!found.length) continue;
    mover.decoded = mover.decoded || moverKeys(mover.keys);
    found.forEach((node) => { node.userData.rest = node.userData.rest || node.matrix.clone(); });
    movers.push({ keys: mover.decoded, nodes: found.map((node) => ({ node, rest: node.userData.rest })) });
  }
}

function keyAt(keys, code) {
  let low = 0, high = keys.length - 1;
  if (code <= keys[0].code) return [keys[0], keys[0], 0];
  if (code >= keys[high].code) return [keys[high], keys[high], 0];
  while (high - low > 1) {
    const middle = (low + high) >> 1;
    if (keys[middle].code <= code) low = middle; else high = middle;
  }
  return [keys[low], keys[high], (code - keys[low].code) / (keys[high].code - keys[low].code)];
}

const moved = { at: new THREE.Vector3(), turn: new THREE.Quaternion(), size: new THREE.Vector3(),
                matrix: new THREE.Matrix4() };

function moveTo(mover, code) {
  const [before, after, share] = keyAt(mover.keys, code);
  moved.at.lerpVectors(before.at, after.at, share);
  moved.turn.slerpQuaternions(before.turn, after.turn, share);
  moved.size.lerpVectors(before.size, after.size, share);
  moved.matrix.compose(moved.at, moved.turn, moved.size);
  for (const { node, rest } of mover.nodes) {
    node.matrixAutoUpdate = false;
    node.matrix.multiplyMatrices(moved.matrix, rest);
    node.matrixWorldNeedsUpdate = true;
  }
}

function playMovers(seconds) {
  if (!sidecar || !sidecar.motion || hidden.has("motion")) return;
  const { start, end, codes_per_second: rate } = sidecar.motion;
  const code = start + (seconds * rate) % Math.max(end - start, 1);
  movers.forEach((mover) => moveTo(mover, code));
}

function restMovers() {
  for (const mover of movers) {
    for (const { node, rest } of mover.nodes) { node.matrix.copy(rest); node.matrixWorldNeedsUpdate = true; }
  }
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
  const part = partOf(hit);
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
let begun = performance.now();  // the stage's first moment: reset when the place is first shown
function frame(now) {
  const seconds = Math.min((now - last) / 1000, 0.1);
  last = now;
  if (move === "walk" && walk.isLocked) walkStep(seconds); else orbit.update();
  playMovers((now - begun) / 1000);
  probeWhenResting();
  measureLabel();
  composer.render();
  requestAnimationFrame(frame);
}

// --- loading --------------------------------------------------------------------------------------------------

function viewButtons() {
  $("views").replaceChildren(...(sidecar.cameras || []).map((view) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = view.name;
    button.onclick = () => {
      if (move === "walk") document.querySelector("input[value=orbit]").click();
      aimAt(view.eye, view.aim, view.fov);
      if (ready) probeAt(camera.position);
    };
    return button;
  }));
}

function standPerson() {
  raycaster.set(orbit.target.clone().add(new THREE.Vector3(0, 20, 0)), new THREE.Vector3(0, -1, 0));
  raycaster.far = 100;
  const hit = raycaster.intersectObject(model, true)[0];
  person.position.copy(hit ? hit.point : orbit.target);
}

// With no camera in the scene record: look at the place itself (not its far ground ring, its sky or the places it
// shows) from above one corner.
function frameModel() {
  const box = new THREE.Box3();
  for (const object of sidecar.objects) {
    if (object.layer.startsWith("place ") || /^(Outside|Sky)/.test(object.name)) continue;
    box.union(new THREE.Box3(new THREE.Vector3(...object.low), new THREE.Vector3(...object.high)));
  }
  if (box.isEmpty()) box.setFromObject(model);
  const middle = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
  aimAt([middle.x + size * 0.45, middle.y + size * 0.35, middle.z + size * 0.45], middle.toArray(), 75);
}

function castsAndTakes(root) {
  root.traverse((node) => { if (node.isMesh) node.castShadow = node.receiveShadow = true; });
}

// A copy loaded into its slot (own: the preview, then the whole; around: the shown places with no copy of their own;
// place:<name>: a shown place's own copy on its seat), the one it replaces let go.
function swapIn(kind, loaded, shows = null) {
  if (copies[kind]) {
    model.remove(copies[kind]);
    copies[kind].traverse((node) => { if (node.isMesh) node.geometry.dispose(); });
  }
  if (shows) {
    leaveOut(loaded, shows.hidden);
    loaded.matrixAutoUpdate = false;
    loaded.matrix.fromArray(shows.seat);
    loaded.userData.nodes = markParts(loaded, `Places/${shows.place}/`, `place ${shows.place}`);
  } else {
    loaded.userData.nodes = markParts(loaded);
  }
  copies[kind] = loaded;
  model.add(loaded);
  model.updateMatrixWorld(true);
  const nodes = new Map(Object.values(copies).filter(Boolean).flatMap((copy) => [...copy.userData.nodes]));
  placeInstances(nodes);
  joinStill(loaded, nodes);
  findMovers(nodes);
  castsAndTakes(loaded);
  showLayers();
  layerList();
  renderer.shadowMap.needsUpdate = true;
}

// The films bloom what is brighter than the glow's threshold once the exposure is on it.
function glowing(glow, exposure) {
  if (!glow) return;
  bloom.threshold = glow.threshold / Math.max(exposure, 1e-3);
  bloom.enabled = true;
}

function lightTheSky(sky) {
  scene.background = linear(sky.background);
  renderer.toneMappingExposure = sky.exposure;
  ambient.color = linear(sky.ambient);
  probe.sky = linear(sky.ambient.map((value) => value / Math.PI));  // the dome's radiance: three.js's ambient over pi
}

async function loadInto(loader, kind, url, shows = null) {
  const loaded = await loader.loadAsync(url).catch(() => null);
  if (loaded) swapIn(kind, loaded.scene, shows);
  return loaded;
}

// Every shown place's own copy onto its seat, each its preview (`-light`) or its whole.
async function loadShown(loader, ending) {
  const shown = (sidecar.shows || []).filter((shows) => shows.copy);
  await Promise.all(shown.map((shows) => loadInto(loader, `place:${shows.place}`,
                                                  `${others}${shows.place}/${shows.place}${ending}.glb`, shows)));
}

function firstLook(first) {
  if (!first) frameModel();
  begun = performance.now();
  ready = true;
  standPerson();
  probeAt(camera.position);
}

async function open() {
  const answer = await fetch(`${base}${place}.json`, { credentials: "same-origin" });
  if (!answer.ok) throw new Error(`the copy's facts: ${answer.status}`);
  sidecar = await answer.json();
  resize();
  window.addEventListener("resize", resize);
  lightTheSky(sidecar.sky || { background: [0.05, 0.05, 0.05], ambient: [0.5, 0.5, 0.5], exposure: 1 });  // older
  glowing(sidecar.glow, renderer.toneMappingExposure);
  addLamps(sidecar.lights || []);
  addEffects(sidecar.effects || []);
  viewButtons();
  const first = given.at || (sidecar.cameras || [])[0];  // a breakdown link opens at the film's camera
  if (first) aimAt(first.eye, first.aim, first.fov);
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  requestAnimationFrame(frame);
  const preview = await loadInto(loader, "own", `${base}${place}-light.glb`);
  if (preview) {
    firstLook(first);
    say(`Preview shown; the whole copy (${(sidecar.bytes / 1e6).toFixed(1)} MB) is loading...`);
  }
  await loadShown(loader, "-light");
  if (sidecar.around_bytes) await loadInto(loader, "around", `${base}${place}-around.glb`);
  const whole = await loader.loadAsync(`${base}${place}.glb`);
  swapIn("own", whole.scene);
  if (!preview) firstLook(first);
  await loadShown(loader, "");
  probeAt(probe.at);
  say(`${sidecar.triangles.toLocaleString()} triangles.`);
  setTimeout(() => model.traverse((node) => { if (node.isMesh) node.geometry.computeBoundsTree(); }), 0);
}

open().catch((error) => { say(`Could not open the 3D copy: ${error.message}`); console.error(error); });
