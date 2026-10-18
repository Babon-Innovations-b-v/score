// A library entry in 3D inside the Library explorer: its GLB (the web copy) with its own finish, or a surface's finish
// on a ball, under a neutral studio light (three.js RoomEnvironment), orbit only. The same three.js, loader and tone
// curve as the cockpit's place viewer (view3d.js); one view at a time, dropped when the next entry opens.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const BACKDROP = 0x1c2027;  // the cockpit's raised surface colour
let current = null;

function linear(values) { return new THREE.Color().setRGB(values[0], values[1], values[2], THREE.LinearSRGBColorSpace); }

// The studio: an even room light for reflections, one soft key light from above the camera's left, and a dim floor.
function studio(renderer) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(BACKDROP);
  const rooms = new THREE.PMREMGenerator(renderer);
  scene.environment = rooms.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.6;
  rooms.dispose();
  const key = new THREE.DirectionalLight(0xffffff, 1.0);
  key.position.set(-3, 5, 4);
  scene.add(key, new THREE.HemisphereLight(0xffffff, 0x3a3f47, 0.2));
  return scene;
}

function stage(holder) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.AgXToneMapping;  // the films' and the place viewer's tone curve
  holder.replaceChildren(renderer.domElement);
  const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 2000);
  const orbit = new OrbitControls(camera, renderer.domElement);
  orbit.enableDamping = true;
  return { holder, renderer, camera, orbit, scene: studio(renderer), running: true };
}

function fitSize(view) {
  const width = Math.max(view.holder.clientWidth, 50), height = Math.max(view.holder.clientHeight, 50);
  view.renderer.setSize(width, height, false);
  view.camera.aspect = width / height;
  view.camera.updateProjectionMatrix();
}

// Look at the whole thing from the front, a little above and to one side, as a product shot does.
function frame(view, object) {
  const box = new THREE.Box3().setFromObject(object);
  const middle = box.getCenter(new THREE.Vector3());
  const radius = Math.max(box.getSize(new THREE.Vector3()).length() / 2, 0.01);
  const distance = radius / Math.sin(THREE.MathUtils.degToRad(view.camera.fov / 2)) * 1.1;
  const toward = new THREE.Vector3(0.55, 0.38, 1).normalize();
  view.camera.position.copy(middle).addScaledVector(toward, distance);
  view.camera.near = distance / 200;
  view.camera.far = distance * 20;
  view.camera.updateProjectionMatrix();
  view.orbit.target.copy(middle);
  view.orbit.update();
  return box;
}

function floorUnder(view, box) {
  const size = box.getSize(new THREE.Vector3());
  const floor = new THREE.Mesh(new THREE.CircleGeometry(Math.max(size.x, size.z) * 0.8 + 0.01, 64),
                               new THREE.MeshStandardMaterial({ color: 0x23272e, roughness: 1 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.set((box.min.x + box.max.x) / 2, box.min.y - size.y * 0.002, (box.min.z + box.max.z) / 2);
  view.scene.add(floor);
}

function run(view) {
  const resized = new ResizeObserver(() => fitSize(view));
  resized.observe(view.holder);
  view.resized = resized;
  fitSize(view);
  const tick = () => {
    if (!view.running) return;
    view.orbit.update();
    view.renderer.render(view.scene, view.camera);
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function freeMaterial(material) {
  for (const value of Object.values(material)) if (value && value.isTexture) value.dispose();
  material.dispose();
}

// Drop the view on screen: its loop, its GPU memory, its canvas.
export function close() {
  if (!current) return;
  const view = current;
  current = null;
  view.running = false;
  view.resized?.disconnect();
  view.orbit.dispose();
  view.scene.traverse((node) => {
    if (!node.isMesh) return;
    node.geometry.dispose();
    for (const material of [node.material].flat()) freeMaterial(material);
  });
  view.scene.environment?.dispose();
  view.renderer.dispose();
  view.renderer.forceContextLoss();
  view.renderer.domElement.remove();
}

function sizeWords(box) {
  const size = box.getSize(new THREE.Vector3());
  return `${size.x.toFixed(2)} x ${size.y.toFixed(2)} x ${size.z.toFixed(2)} m`;
}

function triangles(object) {
  let counted = 0;
  object.traverse((node) => {
    if (!node.isMesh) return;
    counted += (node.geometry.index ? node.geometry.index.count : node.geometry.attributes.position.count) / 3;
  });
  return Math.round(counted);
}

// A model's GLB in the studio; resolves to {size, triangles} in words once it stands framed.
export async function showModel(holder, url) {
  close();
  const view = current = stage(holder);
  run(view);
  const loaded = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync(url);
  if (current !== view) return null;  // another entry was opened meanwhile
  view.scene.add(loaded.scene);
  const box = frame(view, loaded.scene);
  floorUnder(view, box);
  return { size: sizeWords(box), triangles: triangles(loaded.scene) };
}

// A surface's finish (colour, metallic, roughness, glow, opacity) on a ball, or its print on a card.
export async function showFinish(holder, finish, printUrl) {
  close();
  const view = current = stage(holder);
  run(view);
  const material = new THREE.MeshStandardMaterial({
    color: linear(finish.colour || [0.5, 0.5, 0.5]), metalness: finish.metallic ?? 0, roughness: finish.roughness ?? 0.5,
  });
  if (finish.glow) { material.emissive = linear(finish.glow); material.emissiveIntensity = 1; }
  if (finish.opacity !== undefined && finish.opacity < 1) { material.transparent = true; material.opacity = finish.opacity; }
  const printed = printUrl ? await new THREE.TextureLoader().loadAsync(printUrl).catch(() => null) : null;
  if (current !== view) return null;
  if (printed) {
    printed.colorSpace = THREE.SRGBColorSpace;
    material.map = printed;
    material.color.set(0xffffff);
    material.side = THREE.DoubleSide;
  }
  const shape = printed ? printCard(printed) : new THREE.SphereGeometry(0.5, 96, 64);
  const shown = new THREE.Mesh(shape, material);
  shown.position.y = printed ? 0.5 : 0;
  view.scene.add(shown);
  floorUnder(view, frame(view, shown));
  return { size: printed ? "its print on a card 1 m tall" : "a ball 1 m across", triangles: null };
}

// A print stands as a card 1 m tall at its picture's own proportions.
function printCard(printed) {
  const picture = printed.image;
  return new THREE.PlaneGeometry(picture.width / Math.max(picture.height, 1), 1);
}
