// A place's 3D web copy (score/dashboard/web3d/convert.py): the light preview first, then the places it shows, then
// the whole copy; lit as the films are (its lamps, its sky's ambient, its haze, what its surfaces mirror from a
// probe at the camera, AgX at the film's exposure); orbit and walk, a toggle per OpenUSD layer (its meshes, lamps,
// effects as points, motion), a person 1.8 m tall, a measuring tool, and a click names the part, its surface, its
// layer and the step that made that layer.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { PointerLockControls } from "three/addons/controls/PointerLockControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { Pass } from "three/addons/postprocessing/Pass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { computeBoundsTree, acceleratedRaycast } from "three-mesh-bvh";
import { MeshoptSimplifier } from "meshoptimizer/meshopt_simplifier.module.js";

THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;

const given = JSON.parse(document.getElementById("view3d-data").textContent);
const place = given.place;
const base = given.base || `/web/${place}/`;  // the current copy, or a basket item's free after
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
// The probe: a cube picture of the lit place from the camera, what its surfaces mirror, made again once the camera
// rests REPROBE_METRES from where it was made.
const PROBE_SIDE = 128, REPROBE_METRES = 4, REST_FRAMES = 20;
// Lamps that cast shadows at once (the place's own first, then the brightest where the probe is), each map drawn
// once a probe; with the pictures a surface reads, eight maps stay within the sixteen a graphics card samples.
const SHADOW_LAMPS = 8, SHADOW_SIDE = 1024, SUN_SHADOW_METRES = 60;
// A point lamp's shadow is six maps side by side (three.js lays them 4 by 2): at 1024 each a 4096 x 2048 picture.
const POINT_SHADOW_SIDE = 512;
// The orbit turns about a point this far ahead of the camera at most (a film's aim may be a city 260 m off).
const ORBIT_REACH = 6;
// The films' glow: what is brighter than the place's glow threshold blooms (Blender's glare at strength 1; three.js's
// bloom normalises its own way, so its strength and spread are set by eye against the stills).
const BLOOM_STRENGTH = 0.6, BLOOM_RADIUS = 0.5;
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
renderer.domElement.addEventListener("webglcontextlost", () => {
  say("The browser's graphics dropped this view (more than it could hold at once): reload the page to try again.");
});
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
// Where a lamp's light reaches. In the films a lamp the game casts no shadow for lights every surface through any
// wall (the square's floodlights light the flat), and one that casts lights what it sees. Here only SHADOW_LAMPS cast
// at once, so a lamp that should cast and has no shadow lights only the place it belongs to: unlinked, the camps'
// lamps lit the campgrounds' ground outside through their walls (2026-10-18). three.js links lights to surfaces by
// the camera's layers, so a frame is drawn in two passes over one depth: the shown places, then the place's own.
const OWN_MESHES = 0, SHOWN_MESHES = 1, OWN_LAMPS = 2, SHOWN_LAMPS = 3;
const SHOWN_PASS = (1 << SHOWN_MESHES) | (1 << SHOWN_LAMPS), OWN_PASS = (1 << OWN_MESHES) | (1 << OWN_LAMPS);

// The scene drawn by `draw` through `views` (a camera, or a cube camera's six) in the two passes; shadows due are
// drawn first, once, from every surface (through the first view, unlit, a picture the passes then draw over).
const unlit = new THREE.MeshBasicMaterial();

function drawSplit(views, draw) {
  const kept = views.map((view) => view.layers.mask), clearing = renderer.autoClear;
  if (renderer.shadowMap.needsUpdate) {
    views[0].layers.enableAll();
    scene.overrideMaterial = unlit;
    renderer.render(scene, views[0]);
    scene.overrideMaterial = null;
    renderer.shadowMap.needsUpdate = false;
  }
  views.forEach((view) => { view.layers.mask = SHOWN_PASS; });
  draw();
  const sky = scene.background;
  scene.background = null;  // a colour background clears the picture whatever autoClear says
  renderer.autoClear = false;
  views.forEach((view) => { view.layers.mask = OWN_PASS; });
  draw();
  renderer.autoClear = clearing;
  scene.background = sky;
  views.forEach((view, number) => { view.layers.mask = kept[number]; });
}

class SplitPass extends Pass {
  constructor() { super(); this.needsSwap = false; }
  render(drawer, writeBuffer, readBuffer) {
    drawer.setRenderTarget(this.renderToScreen ? null : readBuffer);
    drawSplit([camera], () => drawer.render(scene, camera));
  }
}

const composer = new EffectComposer(renderer);
composer.addPass(new SplitPass());
const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), BLOOM_STRENGTH, BLOOM_RADIUS, 1);
bloom.enabled = false;
composer.addPass(bloom);
composer.addPass(new OutputPass());  // AgX and the exposure, then sRGB
const ambient = new THREE.AmbientLight(0xffffff, 1);
ambient.layers.set(OWN_LAMPS);
ambient.layers.enable(SHOWN_LAMPS);
scene.add(ambient);
raycaster.layers.enableAll();
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
  made.userData.own = !(entry.layer || "").startsWith("place ");
  linkLamp(made);
  return shadowed(made, made.isPointLight ? POINT_SHADOW_SIDE : SHADOW_SIDE);
}

function addLamps(entries) {
  for (const entry of entries) {
    const made = lampOf(entry);
    lamps.push(made);
    scene.add(made);
    if (made.target) scene.add(made.target);
  }
  chooseLamps(camera.position);
}

// The lamps drawn at once, of each kind, the place's own and the shown places' apart: those of the shown layers that
// light `at` most. three.js works out every drawn lamp for every pixel, and the hub and the hangar hold 110 with the
// places they show (their shader ran out of room in the browser, 2026-10-18); a lamp past these lights nothing until
// the probe moves near it. The count of each kind stays the same, so no surface's shader is made again.
const LAMPS_AT_ONCE = { point: 12, spot: 6, directional: 4 };

function chooseLamps(at) {
  for (const [kind, most] of Object.entries(LAMPS_AT_ONCE)) {
    for (const own of [true, false]) {
      const these = lamps.filter((made) => made.userData.entry.type === kind && made.userData.own === own);
      const kept = new Set(these.filter(lampShown).sort((one, other) => reach(other, at) - reach(one, at))
        .slice(0, most));
      these.forEach((made) => { made.visible = kept.has(made); });
    }
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

// The surfaces a lamp lights (the layers it is on): every one for a sun, a lamp the game casts no shadow for and one
// casting here, else its own place's alone.
function linkLamp(made) {
  const everywhere = made.isDirectionalLight || made.userData.entry.shadows === false || made.castShadow;
  made.layers.mask = everywhere ? (1 << OWN_LAMPS) | (1 << SHOWN_LAMPS)
    : 1 << (made.userData.own ? OWN_LAMPS : SHOWN_LAMPS);
}

// The sun follows the probe: its shadow box centred there. The SHADOW_LAMPS lamps that light the probe's point most
// cast shadows, the place's own first.
function placeShadows(at) {
  const shown = lamps.filter((made) => made.visible && made.userData.entry.shadows !== false);
  const first = (one, other) => (other.userData.own - one.userData.own) || (reach(other, at) - reach(one, at));
  const casting = new Set(shown.sort(first).slice(0, SHADOW_LAMPS));
  for (const made of lamps) {
    made.castShadow = casting.has(made);
    linkLamp(made);
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
const probe = { light: null, at: null, sky: new THREE.Color(), ambient: new THREE.Color(), still: 0,
                last: new THREE.Vector3() };
// The probe gives what a surface mirrors, never its diffuse light: that is the sky's ambient (thinned in a haze) and
// the lamps. As diffuse light too (bounced three times from the eye's spot) it lit every wall alike, the flat's
// 1.7 times as bright as its film, the hub's half (2026-10-18).
const IBL_DIFFUSE = /iblIrradiance\s*\+=\s*getIBLIrradiance\(\s*geometryNormal\s*\)\s*;/;
THREE.ShaderChunk.lights_fragment_maps = THREE.ShaderChunk.lights_fragment_maps.replace(IBL_DIFFUSE, "");

// The place drawn into a cube from `at` against its sky's own radiance (the dome the films light with), lamps,
// shadows, haze and the far city's simplified towers chosen for that spot first.
function probeAt(at) {
  const helpers = [person, measure.marks, effects, changeMarks];
  const were = helpers.map((helper) => helper.visible);
  helpers.forEach((helper) => { helper.visible = false; });
  chooseLamps(at);
  splitLevels(at);
  placeShadows(at);
  hazeAt(at);
  const seen = scene.background;
  scene.background = probe.sky;
  probeCamera.position.copy(at);
  drawSplit(probeCamera.children, () => probeCamera.update(renderer, scene));
  const made = pmrem.fromCubemap(probeTarget.texture);
  if (probe.light) probe.light.dispose();
  probe.light = made;
  scene.environment = made.texture;
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

// The films' haze: a body of fog (the sidecar's `hazes`) that thins what lies behind it exponentially, its density a
// metre, worked out only to its reach from the eye, that thins the lamps' and the sun's light on its way through it
// and scatters that light (never the sky's: usd_views.py). three.js's linear Fog carries it: its near is the
// density, its far the reach.
const HAZE_SAMPLES = 4;  // the haze's own light is the lamps' averaged over a grid this many a side round the eye
const HAZE_AROUND = 30;  // metres round the eye that grid reaches at most
const FOG_LINEAR = /float fogFactor = smoothstep\(\s*fogNear\s*,\s*fogFar\s*,\s*vFogDepth\s*\)\s*;/;
const hazeReady = FOG_LINEAR.test(THREE.ShaderChunk.fog_fragment);
THREE.ShaderChunk.fog_fragment = THREE.ShaderChunk.fog_fragment.replace(FOG_LINEAR,
  "float fogFactor = 1.0 - exp( - fogNear * ( fogFar > 0.0 ? min( vFogDepth, fogFar ) : vFogDepth ) );");

// How much of a lamp's light the haze lets through to `at`: exp(-density x its way through the haze within the
// reach), a lamp's way from where it stands, the sun's from the haze's top.
function hazeThrough(made, haze, at) {
  const reach = haze.reach || Infinity;
  const up = made.isDirectionalLight ? -made.userData.toward.y : 0;
  const way = !made.isDirectionalLight ? made.position.distanceTo(at)
    : up > 0.01 ? Math.max(haze.high[1] - at.y, 0) / up : reach;
  return Math.exp(-haze.density * Math.min(way, reach));
}

// The light the haze scatters back (linear radiance, isotropic): its colour times the lamps' and the sun's
// irradiance from every side, thinned on their way, averaged over a grid round the eye inside its box, over 4 pi.
function hazeLight(haze, eye) {
  const low = [0, 1, 2].map((axis) => Math.max(haze.low[axis], eye.getComponent(axis) - HAZE_AROUND));
  const high = [0, 1, 2].map((axis) => Math.min(haze.high[axis], eye.getComponent(axis) + HAZE_AROUND));
  const at = new THREE.Vector3(), lit = new THREE.Color(0, 0, 0);
  const shining = lamps.filter((made) => made.visible);
  for (let step = 0; step < HAZE_SAMPLES ** 3; step++) {
    const cell = [step % HAZE_SAMPLES, Math.floor(step / HAZE_SAMPLES) % HAZE_SAMPLES,
                  Math.floor(step / HAZE_SAMPLES ** 2)].map((number) => (number + 0.5) / HAZE_SAMPLES);
    at.set(...[0, 1, 2].map((axis) => low[axis] + (high[axis] - low[axis]) * cell[axis]));
    for (const made of shining) {
      const away = made.isDirectionalLight ? 1 : Math.max(made.position.distanceToSquared(at), 0.25);
      const strength = made.userData.entry.intensity * hazeThrough(made, haze, at) / away;
      lit.add(made.color.clone().multiplyScalar(strength));
    }
  }
  const scale = 1 / (HAZE_SAMPLES ** 3 * 4 * Math.PI);
  return linear(haze.colour).multiply(lit.multiplyScalar(scale));
}

// The haze the eye stands in (the box holding `at`), or none: the fog it lays, every lamp thinned by it, and the
// sky's ambient thinned on its way down through it (a slab's mean way from the sky is twice its depth) and made up
// by the haze's own light from every side.
function hazeAt(at) {
  const holds = (haze) => [0, 1, 2].every((axis) => haze.low[axis] <= at.getComponent(axis)
                                                   && at.getComponent(axis) <= haze.high[axis]);
  const inside = hazeReady ? (sidecar.hazes || []).find(holds) : null;
  for (const made of lamps) {
    made.intensity = made.userData.entry.intensity * (inside ? hazeThrough(made, inside, at) : 1);
  }
  ambient.color.copy(probe.ambient);
  scene.fog = null;
  if (!inside) return;
  const glow = hazeLight(inside, at);
  const depth = Math.min(Math.max(inside.high[1] - at.y, 0), inside.reach || Infinity);
  const through = Math.exp(-2 * inside.density * depth);
  ambient.color.multiplyScalar(through).add(glow.clone().multiplyScalar(Math.PI * (1 - through)));
  scene.fog = new THREE.Fog(glow, inside.density, inside.reach);
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

// A point instancer's prototype (the far city's towers): each of its meshes drawn once a place it stands, whole near
// the eye and simplified (meshoptimizer's simplifier) past LOD_METRES: the far city's 2,167 towers hold about 25,000
// triangles each, 55 million drawn whole every frame and every probe face (2026-10-18).
const LOD_METRES = 400, FAR_SHARE = 0.02, FAR_ERROR = 0.02;
const levels = [];  // {near, far, placed, centres}: each prototype mesh's two instanced meshes and its instances

function simplified(geometry) {
  const count = geometry.attributes.position.count;
  const corners = geometry.index ? Uint32Array.from(geometry.index.array)
    : Uint32Array.from({ length: count }, (unused, index) => index);
  const target = Math.max(3, Math.floor(corners.length * FAR_SHARE / 3) * 3);
  const [kept] = MeshoptSimplifier.simplify(corners, plainValues(geometry.attributes.position), 3, target, FAR_ERROR);
  const far = new THREE.BufferGeometry();
  for (const [name, values] of Object.entries(geometry.attributes)) far.setAttribute(name, values);
  far.setIndex(new THREE.BufferAttribute(kept, 1));
  return far;
}

function instancedOf(mesh, geometry, count) {
  const made = new THREE.InstancedMesh(geometry, mesh.material, count);
  made.layers.mask = mesh.layers.mask;
  made.applyMatrix4(mesh.matrix);
  made.name = mesh.name;
  made.userData.part = mesh.userData.part;
  return made;
}

// The prototype mesh as its near and far instanced meshes in its parent, every instance near until the first probe.
function instanced(mesh, matrices) {
  mesh.updateWorldMatrix(true, false);
  const into = mesh.matrixWorld.clone().invert(), out = mesh.matrixWorld;
  const placed = matrices.map((numbers) => new THREE.Matrix4().fromArray(numbers).premultiply(into).multiply(out));
  const near = instancedOf(mesh, mesh.geometry, placed.length);
  const far = instancedOf(mesh, simplified(mesh.geometry), placed.length);
  mesh.parent.add(near, far);
  near.updateMatrixWorld(true);
  mesh.geometry.computeBoundingSphere();
  const centres = placed.map((matrix) => mesh.geometry.boundingSphere.center.clone().applyMatrix4(matrix)
    .applyMatrix4(near.matrixWorld));
  levels.push({ near, far, placed, centres });
  splitLevels(camera.position);
}

// Each instance whole within LOD_METRES of `at`, simplified past it.
function splitLevels(at) {
  for (const { near, far, placed, centres } of levels) {
    let close = 0, away = 0;
    placed.forEach((matrix, number) => {
      if (centres[number].distanceTo(at) < LOD_METRES) near.setMatrixAt(close++, matrix);
      else far.setMatrixAt(away++, matrix);
    });
    [[near, close], [far, away]].forEach(([made, count]) => {
      made.count = count;
      made.instanceMatrix.needsUpdate = true;
      made.computeBoundingSphere();
    });
  }
}

function placeInstances(nodes) {
  for (const instancer of sidecar.instancers || []) {
    for (const prototype of instancer.prototypes) {
      for (const name of prototype.objects) {
        for (const node of nodes.get(name) || []) {
          const meshes = [];
          node.traverse((found) => { if (found.isMesh && !found.isInstancedMesh && found.parent) meshes.push(found); });
          meshes.forEach((mesh) => { instanced(mesh, prototype.matrices); mesh.removeFromParent(); });
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
    made.layers.mask = meshes[0].layers.mask;
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
  chooseLamps(probe.at || camera.position);
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
  const puff = entry.look === "puff";
  const colour = puff ? linear(entry.colour).multiplyScalar(lightOn(geometry) / Math.PI) : linear(entry.colour);
  const material = new THREE.PointsMaterial({ color: colour, size: entry.size, map: sprite, transparent: true,
                                              opacity: entry.opacity, depthWrite: false });
  if (puff && entry.near_fade && entry.near_fade[1] > 0) fadedNear(material, entry.near_fade);
  const points = new THREE.Points(geometry, material);
  points.userData.layer = entry.layer;
  points.name = entry.name;
  return points;
}

// The light falling on an effect's middle (irradiance from every side, linear): the sky's ambient, the lamps and
// half the sun's, as the films light a puff.
function lightOn(geometry) {
  geometry.computeBoundingSphere();
  const middle = geometry.boundingSphere.center;
  const lamplight = lamps.reduce((sum, made) => sum + made.userData.entry.intensity * (made.isDirectionalLight ? 0.5
    : 1 / Math.max(made.position.distanceToSquared(middle), 0.25)), 0);
  return lamplight + (ambient.color.r + ambient.color.g + ambient.color.b) / 3;
}

// A puff gone within near_fade metres of the eye (smoothly from the first to the second), as the films draw it.
function fadedNear(material, [from, to]) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.fadeFrom = { value: from };
    shader.uniforms.fadeTo = { value: to };
    shader.vertexShader = shader.vertexShader.replace("void main() {", "varying float eyeDepth;\nvoid main() {")
      .replace("#include <fog_vertex>", "#include <fog_vertex>\n  eyeDepth = - mvPosition.z;");
    shader.fragmentShader = shader.fragmentShader
      .replace("void main() {", "uniform float fadeFrom;\nuniform float fadeTo;\nvarying float eyeDepth;\n"
                                  + "void main() {")
      .replace("#include <premultiplied_alpha_fragment>",
               "gl_FragColor.a *= smoothstep( fadeFrom, fadeTo, eyeDepth );\n#include <premultiplied_alpha_fragment>");
  };
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

// A link's moment (#...&t=<time code>, a film frame's): the movers held there; else they play from the start.
const linkedTime = () => Number((location.hash.match(/[#&]t=([-0-9.e]+)/) || [])[1] ?? NaN);
let heldAt = linkedTime();

function playMovers(seconds) {
  if (!sidecar || !sidecar.motion || hidden.has("motion")) return;
  const { start, end, codes_per_second: rate } = sidecar.motion;
  const code = Number.isFinite(heldAt) ? heldAt : start + (seconds * rate) % Math.max(end - start, 1);
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
person.visible = $("person").checked;  // off in a place's viewer: the films show no such figure
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

// --- a basket item's changes ---------------------------------------------------------------------------------
// What a basket item changes, outlined over the place (given.marks: boxes from the two stages' difference, in the
// stage's own metres), drawn through walls and left out of the probe; the first look aims at them.
const MARK_COLOURS = { added: 0x4fd18b, moved: 0xf2c14e, reshaped: 0xf2c14e, refinished: 0x8ab4ff, lamp: 0xffd400,
                       removed: 0xff7b72, missing: 0xff3b30, gate: 0xff9f0a };
const changeMarks = new THREE.Group();
scene.add(changeMarks);

function markChanges(marks) {
  for (const mark of marks) {
    const framed = given.hole && mark.id === given.hole;
    // a line is one pixel wide in WebGL, so the framed hole is drawn thicker as nested outlines, white
    for (const grow of framed ? [0.03, 0.05, 0.07, 0.09] : [0.03]) {
      const box = new THREE.Box3(new THREE.Vector3(...mark.low), new THREE.Vector3(...mark.high)).expandByScalar(grow);
      const outline = new THREE.Box3Helper(box, framed ? 0xffffff : MARK_COLOURS[mark.kind] || 0xffffff);
      outline.material.depthTest = false;
      outline.renderOrder = 10;
      changeMarks.add(outline);
    }
  }
  $("to-changes").hidden = !marks.length;
}

// A hole given by the page (`?hole=<id>`): looked at from above one corner, at a distance its size asks for.
function holeView() {
  const mark = (given.marks || []).find((each) => given.hole && each.id === given.hole);
  if (!mark) return null;
  const box = new THREE.Box3(new THREE.Vector3(...mark.low), new THREE.Vector3(...mark.high));
  const middle = box.getCenter(new THREE.Vector3()), reach = Math.max(box.getSize(new THREE.Vector3()).length(), 1) * 1.6;
  return { eye: [middle.x + reach, middle.y + reach * 0.7, middle.z + reach], aim: middle.toArray(), fov: 60 };
}

// No web copy yet (given.holes_only): only the holes' boxes, over a ground grid a metre a square, so a hole can be
// framed today; the place itself is not drawn.
const GRID_METRES = 200;
function openHolesOnly() {
  resize();
  window.addEventListener("resize", resize);
  lightTheSky({ background: [0.05, 0.05, 0.05], ambient: [0.5, 0.5, 0.5], exposure: 1 });
  scene.add(new THREE.GridHelper(GRID_METRES, GRID_METRES, 0x555555, 0x2a2a2a));
  markChanges(given.marks || []);
  const all = new THREE.Box3();
  for (const outline of changeMarks.children) all.union(outline.box);
  const middle = all.getCenter(new THREE.Vector3()), reach = Math.max(all.getSize(new THREE.Vector3()).length(), 2);
  const first = holeView() || { eye: [middle.x + reach * 0.6, middle.y + reach * 0.5, middle.z + reach * 0.6],
                                aim: middle.toArray(), fov: 60 };
  aimAt(first.eye, first.aim, first.fov);
  say("No 3D web copy of this place yet: only its holes are drawn.");
  requestAnimationFrame(frame);
}

// From `from` (a camera), looking at the middle of what changes; `from` itself when nothing is outlined.
function lookingAtChanges(from) {
  if (!changeMarks.children.length || !from) return from;
  const box = new THREE.Box3();
  for (const outline of changeMarks.children) box.union(outline.box);
  return { eye: from.eye, aim: box.getCenter(new THREE.Vector3()).toArray(), fov: from.fov };
}

$("to-changes").onclick = () => goTo(lookingAtChanges({ eye: camera.position.toArray(), aim: null, fov: null }));

// --- loading --------------------------------------------------------------------------------------------------

function goTo(view) {
  if (move === "walk") document.querySelector("input[value=orbit]").click();
  aimAt(view.eye, view.aim, view.fov);
  if (ready) probeAt(camera.position);
}

function viewButtons() {
  $("views").replaceChildren(...(sidecar.cameras || []).map((view) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = view.name;
    button.onclick = () => goTo(view);
    return button;
  }));
}

// A link to one view: #view=<eye x,y,z>,<aim x,y,z>,<fov across> opens there, and a new one moves there.
function linkedView() {
  const numbers = (location.hash.match(/view=([-0-9.,e]+)/) || [])[1]?.split(",").map(Number);
  return numbers && numbers.length === 7 && numbers.every(Number.isFinite)
    ? { eye: numbers.slice(0, 3), aim: numbers.slice(3, 6), fov: numbers[6] } : null;
}
window.addEventListener("hashchange", () => {
  heldAt = linkedTime();
  const view = linkedView();
  if (view) goTo(view);
});

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

// A shown place is seen from its seat, not up close: its pictures are drawn at most SHOWN_PICTURE px a side. At their
// copies' full size the ten places the hub and the hangar show held about 4 GB of graphics memory (2026-10-18).
const SHOWN_PICTURE = 512;
const PICTURE_SLOTS = ["map", "normalMap", "roughnessMap", "metalnessMap", "emissiveMap"];

function smallerPictures(root) {
  const done = new Set();
  root.traverse((node) => {
    for (const material of node.isMesh ? [node.material].flat() : []) {
      for (const texture of PICTURE_SLOTS.map((slot) => material[slot])) {
        const image = texture && texture.image;
        if (!image || done.has(texture) || Math.max(image.width, image.height) <= SHOWN_PICTURE) continue;
        done.add(texture);
        const scale = SHOWN_PICTURE / Math.max(image.width, image.height);
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(image.width * scale);
        canvas.height = Math.round(image.height * scale);
        canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
        if (image.close) image.close();
        texture.image = canvas;
        texture.needsUpdate = true;
      }
    }
  });
}

// A surface drawn as nothing (a haze body's shell: fully see-through, no picture) still hides what is drawn after it
// in the depth buffer and fills the probe from inside: left out.
function dropUnseen(root) {
  const gone = [];
  root.traverse((node) => {
    const material = node.isMesh && !Array.isArray(node.material) ? node.material : null;
    if (material && material.transparent && material.opacity === 0 && !material.map) gone.push(node);
  });
  gone.forEach((node) => node.removeFromParent());
}

// Every surface takes shadows; a see-through one (glass, a lamp's shade or bowl) casts none, as light passes it in
// the films: the flat's ceiling lamp sits in its fan's glass bowl.
function castsAndTakes(root) {
  root.traverse((node) => {
    if (!node.isMesh) return;
    node.receiveShadow = true;
    node.castShadow = ![node.material].flat().some((material) => material.transparent && material.opacity < 1);
  });
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
    smallerPictures(loaded);
    loaded.matrixAutoUpdate = false;
    loaded.matrix.fromArray(shows.seat);
    loaded.userData.nodes = markParts(loaded, `Places/${shows.place}/`, `place ${shows.place}`);
  } else {
    loaded.userData.nodes = markParts(loaded);
  }
  dropUnseen(loaded);
  loaded.traverse((node) => node.layers.set(kind === "own" ? OWN_MESHES : SHOWN_MESHES));
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
  probe.ambient.copy(ambient.color);
  probe.sky = linear(sky.ambient.map((value) => value / Math.PI));  // the dome's radiance: three.js's ambient over pi
}

async function loadInto(loader, kind, url, shows = null) {
  const loaded = await loader.loadAsync(url).catch(() => null);
  if (loaded) swapIn(kind, loaded.scene, shows);
  return loaded;
}

// Every shown place's copy onto its seat (the copy of the place it stands for: a tube seated again loads the
// tube's), each its preview (`-light`) or its whole.
async function loadShown(loader, ending) {
  const shown = (sidecar.shows || []).filter((shows) => shows.copy);
  await Promise.all(shown.map((shows) => {
    const name = shows.of || shows.place;
    return loadInto(loader, `place:${shows.place}`, `${others}${name}/${name}${ending}.glb`, shows);
  }));
}

function firstLook(first) {
  if (!first) frameModel();
  begun = performance.now();
  ready = true;
  standPerson();
  probeAt(camera.position);
}

async function open() {
  await MeshoptSimplifier.ready;
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
  markChanges(given.marks || []);
  // a breakdown link: the film's camera; a basket item: the first camera turned to what it changes
  const first = holeView() || linkedView() || given.at || lookingAtChanges((sidecar.cameras || [])[0]);
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

if (given.holes_only) openHolesOnly();
else open().catch((error) => { say(`Could not open the 3D copy: ${error.message}`); console.error(error); });
