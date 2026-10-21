// The scenes films/preview draws in headless Chromium, frame by frame on the film's own clock (never the wall clock):
// the setting animation (the setting's bodies on their orbits, positions worked out by score/review/overhead.py per
// frame in setting.py) and the scale zoom (one camera path down through the layers: the setting, the world's globe,
// the site's blockout on its ground, the place from outside, its rooms), each layer its own view, dissolved into
// the next while both cameras keep moving, so the shot never cuts. window.filmScene.setup(data), then draw(seconds).
import * as THREE from "three";

const SPACE = 0x05060a;
const DISSOLVE = 0.9;
const EASE = 0.3;  // the share of a leg a move takes to rise from rest or fall to rest
let size = [1280, 720], views = [], legs = [], rate = 24;

const clamp01 = (value) => Math.max(0, Math.min(1, value));
const eased = (value) => { const share = clamp01(value); return share * share * (3 - 2 * share); };
const lerp = (from, to, share) => from + (to - from) * share;

// Progress along a leg, 0 at its start and 1 at its end, its speed a half sine wave rising from rest over EASE where
// `rests[0]` and falling to rest where `rests[1]`; a leg that does not rest at an end is at speed there and carries
// on past it, so the camera keeps moving through a dissolve instead of stopping and starting again.
function travel(share, rests) {
  const rise = rests[0] ? EASE : 0, fall = rests[1] ? EASE : 0, length = 1 - rise / 2 - fall / 2;
  const ramp = (time, ease) => (ease ? time / 2 - ease / (2 * Math.PI) * Math.sin(Math.PI * time / ease) : time);
  if (share <= 0) return rests[0] ? 0 : share / length;
  if (share >= 1) return rests[1] ? 1 : 1 + (share - 1) / length;
  if (share < rise) return ramp(share, rise) / length;
  if (1 - share < fall) return (length - ramp(1 - share, fall)) / length;
  return (share - rise / 2) / length;
}
const colour = (rgb) => new THREE.Color().setRGB(rgb[0], rgb[1], rgb[2], THREE.SRGBColorSpace);

// A fixed sequence of numbers (the same stars and ground every time).
function seeded(seed) {
  let state = seed >>> 0;
  return () => { state = (state * 1664525 + 1013904223) >>> 0; return state / 4294967296; };
}

function renderer() {
  const made = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  made.setPixelRatio(window.devicePixelRatio);
  made.setSize(size[0], size[1]);
  made.outputColorSpace = THREE.SRGBColorSpace;
  made.domElement.className = "view";
  document.getElementById("views").append(made.domElement);
  return made;
}

function stars(count, radius) {
  const random = seeded(7), points = [];
  for (let index = 0; index < count; index++) {
    const up = random() * 2 - 1, turn = random() * Math.PI * 2, across = Math.sqrt(1 - up * up);
    points.push(radius * across * Math.cos(turn), radius * up, radius * across * Math.sin(turn));
  }
  const geometry = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
  return new THREE.Points(geometry, new THREE.PointsMaterial({ color: 0xdfe4f2, size: 1.3, sizeAttenuation: false }));
}

function glow(rgb) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const pen = canvas.getContext("2d"), fill = pen.createRadialGradient(64, 64, 0, 64, 64, 64);
  const [red, green, blue] = rgb.map((value) => Math.round(255 * value));
  fill.addColorStop(0, `rgba(${red},${green},${blue},0.9)`);
  fill.addColorStop(0.25, `rgba(${red},${green},${blue},0.35)`);
  fill.addColorStop(1, `rgba(${red},${green},${blue},0)`);
  pen.fillStyle = fill;
  pen.fillRect(0, 0, 128, 128);
  return new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), depthWrite: false, blending: THREE.AdditiveBlending }));
}

// A surface's colour broken by soft noise, so a globe or the ground reads as ground and not as plastic.
function groundTexture(rgb, seed, repeat) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 512;
  const pen = canvas.getContext("2d"), random = seeded(seed), base = rgb.map((value) => 255 * value);
  pen.fillStyle = `rgb(${base.join(",")})`;
  pen.fillRect(0, 0, 512, 512);
  for (let index = 0; index < 900; index++) {
    const x = random() * 512, y = random() * 512, radius = 2 + 26 * random() ** 3, shade = (random() - 0.5) * 0.35;
    pen.fillStyle = `rgba(${shade > 0 ? 255 : 0},${shade > 0 ? 255 : 0},${shade > 0 ? 255 : 0},${Math.abs(shade) * 0.5})`;
    pen.beginPath(); pen.arc(x, y, radius, 0, Math.PI * 2); pen.fill();
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(repeat, repeat);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function label(words, kind = "") {
  const shown = document.createElement("div");
  shown.className = `label ${kind}`;
  shown.textContent = words;
  document.getElementById("labels").append(shown);
  return shown;
}

function placeLabel(shown, point, camera, opacity) {
  const projected = point.clone().project(camera);
  const visible = projected.z < 1 && Math.abs(projected.x) < 1.05 && Math.abs(projected.y) < 1.05;
  shown.style.opacity = String(visible ? opacity : 0);
  shown.style.left = `${(projected.x + 1) / 2 * size[0]}px`;
  shown.style.top = `${(1 - projected.y) / 2 * size[1]}px`;
}

// --- the setting: its bodies on their orbits ---------------------------------------------------------------------

function settingView(data) {
  const paint = renderer(), scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(36, size[0] / size[1], 0.01, 5000);
  scene.background = new THREE.Color(SPACE);
  scene.add(stars(2600, 2400), new THREE.AmbientLight(0xffffff, 0.12));
  const bodies = {}, orbits = [];
  for (const body of data.bodies) {
    const material = body.shines ? new THREE.MeshBasicMaterial({ color: colour(body.color) })
      : new THREE.MeshStandardMaterial({ color: colour(body.color), roughness: 0.9 });
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(body.size, 48, 32), material);
    scene.add(mesh);
    if (body.shines) {
      const halo = glow(body.color);
      halo.scale.setScalar(body.size * 7);
      mesh.add(halo);
      const light = new THREE.PointLight(0xffffff, 3.2, 0, 0);
      mesh.add(light);
    }
    bodies[body.key] = { mesh, label: label(body.name), size: body.size };
  }
  for (const orbit of data.orbits) {
    const geometry = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(orbit.points.flat(), 3));
    const line = new THREE.LineLoop(geometry, new THREE.LineBasicMaterial({ color: 0x8d8aa8, transparent: true, opacity: orbit.around ? 0.75 : 0.45 }));
    scene.add(line);
    orbits.push({ line, around: orbit.around });
  }
  const note = data.note ? label(data.note, "note") : null;

  function at(local) {
    const frame = Math.max(0, Math.min(data.track.length - 1, Math.round(local * rate)));
    for (const [key, where] of Object.entries(data.track[frame])) bodies[key].mesh.position.set(...where);
    for (const orbit of orbits) if (orbit.around) orbit.line.position.copy(bodies[orbit.around].mesh.position);
  }

  return {
    element: paint.domElement, labels: [...Object.values(bodies).map((body) => body.label), ...(note ? [note] : [])],
    draw(local, leg, opacity) {
      at(local);
      const view = leg.camera, share = local / leg.seconds;
      let turn = THREE.MathUtils.degToRad(view.start_deg + view.turn_deg_per_s * local);
      if (view.focus) {  // close in from the focus's sunlit side, a little round from the Sun, so it shows lit
        const focus = bodies[view.focus].mesh.position;
        const sunward = Math.atan2(-focus.z, -focus.x) + THREE.MathUtils.degToRad(view.end_turn_deg ?? 55);
        let gap = sunward - turn;
        gap = Math.atan2(Math.sin(gap), Math.cos(gap));
        turn += gap * eased(share * 1.1);
      }
      const tilt = THREE.MathUtils.degToRad(lerp(view.tilt_deg, view.end_tilt_deg ?? view.tilt_deg, eased(share)));
      let target = new THREE.Vector3(), distance = view.distance;
      if (view.focus) {
        const focus = bodies[view.focus].mesh.position, closing = eased(share * 1.08);
        target.lerpVectors(new THREE.Vector3(), focus, closing);
        distance = view.distance * Math.pow(view.end_distance / view.distance, Math.min(1.2, share) ** 1.6);
      }
      camera.position.set(target.x + distance * Math.cos(tilt) * Math.cos(turn), target.y + distance * Math.sin(tilt),
                          target.z + distance * Math.cos(tilt) * Math.sin(turn));
      camera.lookAt(target);
      paint.render(scene, camera);
      const labelled = view.focus ? clamp01(1 - share * 1.7) : 1;
      for (const body of Object.values(bodies)) {
        placeLabel(body.label, body.mesh.position.clone().add(new THREE.Vector3(0, -body.size * 1.6, 0)), camera, opacity * labelled);
      }
      if (note) note.style.opacity = String(opacity);
    },
  };
}

// --- the world: the globe the site stands on, turned so the site faces the camera -----------------------------------

function worldView(data) {
  const paint = renderer(), scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(36, size[0] / size[1], 0.0005, 100);
  scene.background = new THREE.Color(SPACE);
  scene.add(stars(2600, 60), new THREE.AmbientLight(0xffffff, 0.06));
  const sun = new THREE.DirectionalLight(0xffffff, 3.4);
  sun.position.set(...data.sun);  // the site's east, north and up are the scene's x, y and z here
  scene.add(sun);
  const turned = new THREE.Group(), spun = new THREE.Group();
  const globe = new THREE.Mesh(new THREE.SphereGeometry(1, 128, 96), new THREE.MeshStandardMaterial({
    color: 0xffffff, map: groundTexture(data.color, 3, 3), roughness: 1 }));
  spun.add(globe);
  spun.rotation.y = -THREE.MathUtils.degToRad(data.site.longitude);
  turned.add(spun);
  turned.rotation.x = THREE.MathUtils.degToRad(data.site.latitude);
  scene.add(turned);
  const marker = new THREE.Mesh(new THREE.RingGeometry(0.018, 0.026, 48), new THREE.MeshBasicMaterial({ color: 0xb99cff, transparent: true }));
  marker.position.set(0, 0, 1.001);
  scene.add(marker);
  const tag = label(data.site.name, "site");
  const name = label(data.name);
  return {
    element: paint.domElement, labels: [tag, name],
    draw(local, leg, opacity) {
      const share = local / leg.seconds, moved = travel(share, leg.rests);
      const distance = 1 + (leg.from_height - 1) * Math.pow((leg.to_height - 1) / (leg.from_height - 1), Math.max(0, Math.min(1.25, moved)) ** 1.3);
      const lean = moved * 0.35 * (distance - 1);
      camera.position.set(0, -lean, distance);
      camera.lookAt(0, 0, 1);
      turned.rotation.y = THREE.MathUtils.degToRad(12 * (1 - moved));
      marker.material.opacity = clamp01(1.2 - share);
      paint.render(scene, camera);
      placeLabel(tag, new THREE.Vector3(0, 0.05, 1.0), camera, opacity * clamp01(1.3 - share * 1.2));
      placeLabel(name, new THREE.Vector3(0, -1.12, 0), camera, opacity * clamp01(1 - share * 2.5));
    },
  };
}

// --- the site and the place from outside: the blockout on its ground ---------------------------------------------------

function footprint(points) {
  const shape = new THREE.Shape(points.map(([east, south]) => new THREE.Vector2(east, -south)));
  return shape;
}

// One block of the site's blockout: its walls to `tall`, then its roof (flat, dome, vault or pitched) rising `rise`.
function block(found, material) {
  const group = new THREE.Group();
  const walls = new THREE.Mesh(new THREE.ExtrudeGeometry(footprint(found.points), { depth: found.tall, bevelEnabled: false }), material);
  walls.rotation.x = -Math.PI / 2;
  walls.position.y = found.base;
  walls.castShadow = walls.receiveShadow = true;
  group.add(walls);
  const easts = found.points.map((point) => point[0]), souths = found.points.map((point) => point[1]);
  const middle = [(Math.min(...easts) + Math.max(...easts)) / 2, (Math.min(...souths) + Math.max(...souths)) / 2];
  const wide = Math.max(...easts) - Math.min(...easts), deep = Math.max(...souths) - Math.min(...souths);
  const top = found.base + found.tall;
  let roof = null;
  if (found.roof === "dome" && found.rise > 0) {
    roof = new THREE.Mesh(new THREE.SphereGeometry(0.5, 48, 16, 0, Math.PI * 2, 0, Math.PI / 2), material);
    roof.scale.set(wide, found.rise * 2, deep);
  } else if (found.roof === "vault" && found.rise > 0) {
    roof = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 1, 32, 1, false, 0, Math.PI), material);
    roof.rotation.z = Math.PI / 2;
    roof.rotation.y = wide >= deep ? 0 : Math.PI / 2;
    roof.scale.set(found.rise * 2, wide >= deep ? wide : deep, wide >= deep ? deep : wide);
  } else if (found.roof === "pitched" && found.rise > 0) {
    roof = new THREE.Mesh(new THREE.ConeGeometry(Math.SQRT1_2, 1, 4, 1), material);
    roof.rotation.y = Math.PI / 4;
    roof.scale.set(wide, found.rise, deep);
    roof.position.y = found.rise / 2;
  }
  if (roof) {
    roof.position.x = middle[0];
    roof.position.z = middle[1];
    roof.position.y += top;
    roof.castShadow = roof.receiveShadow = true;
    group.add(roof);
  }
  return { group, middle: new THREE.Vector3(middle[0], top, middle[1]), name: found.name, size: Math.max(wide, deep) };
}

function groundView(data) {
  const paint = renderer(), scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(42, size[0] / size[1], 0.5, 20000);
  paint.shadowMap.enabled = true;
  paint.shadowMap.type = THREE.PCFSoftShadowMap;
  scene.background = new THREE.Color(SPACE);
  scene.add(stars(2600, 9000), new THREE.HemisphereLight(0xc9d2e8, 0x2a2826, 0.25));
  const [east, north, up] = data.sun;
  const sun = new THREE.DirectionalLight(0xffffff, 3.2);
  sun.position.set(east * 400, up * 400, -north * 400);
  sun.castShadow = true;
  sun.shadow.mapSize.set(4096, 4096);
  Object.assign(sun.shadow.camera, { left: -220, right: 220, top: 220, bottom: -220, near: 1, far: 1200 });
  sun.shadow.bias = -0.0004;
  scene.add(sun, sun.target);
  const ground = new THREE.Mesh(new THREE.CircleGeometry(4000, 96), new THREE.MeshStandardMaterial({
    color: 0xffffff, map: groundTexture(data.ground_color, 11, 90), roughness: 1 }));
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);
  for (const world of data.sky) {  // a world in the sky: its true size and phase, lit by the same sun
    const away = 6000, across = Math.max(world.across, 0.25);
    const altitude = THREE.MathUtils.degToRad(world.altitude), azimuth = THREE.MathUtils.degToRad(world.azimuth);
    const globe = new THREE.Mesh(new THREE.SphereGeometry(away * Math.tan(THREE.MathUtils.degToRad(across) / 2), 48, 32),
      new THREE.MeshStandardMaterial({ color: colour(world.color), roughness: 1 }));
    globe.position.set(away * Math.cos(altitude) * Math.sin(azimuth), away * Math.sin(altitude), -away * Math.cos(altitude) * Math.cos(azimuth));
    scene.add(globe);
  }
  const material = new THREE.MeshStandardMaterial({ color: 0xbfc3c9, roughness: 0.85 });
  const blocks = [], others = [];
  for (const site of data.sites) {
    const group = new THREE.Group();
    group.position.set(site.at[0], 0, site.at[1]);
    for (const found of site.blocks) {
      const made = block(found, material);
      group.add(made.group);
      const named = site.blocks.filter((other) => other.name === found.name).length === 1;  // a row of tubes goes unnamed
      if (site.place === data.place && named) blocks.push({ ...made, middle: made.middle.add(group.position), label: label(found.name, "block") });
    }
    scene.add(group);
    if (site.place !== data.place) {
      const middle = site.blocks.flatMap((found) => found.points);
      const east = middle.reduce((sum, point) => sum + point[0], 0) / middle.length;
      const south = middle.reduce((sum, point) => sum + point[1], 0) / middle.length;
      others.push({ label: label(site.name, "site"), at: new THREE.Vector3(site.at[0] + east, 12, site.at[1] + south) });
    }
  }
  const centre = new THREE.Vector3(...data.centre);
  const into = blocks.find((found) => found.name === data.into);
  return {
    element: paint.domElement, labels: [...blocks.map((found) => found.label), ...others.map((other) => other.label)],
    draw(local, leg, opacity) {
      const share = local / leg.seconds, path = leg.camera, moved = travel(share, leg.rests);
      const turn = THREE.MathUtils.degToRad(lerp(path.from_deg, path.to_deg, moved));
      const tilt = THREE.MathUtils.degToRad(lerp(path.from_tilt, path.to_tilt, Math.min(1.1, moved)));
      const distance = path.from_distance * Math.pow(path.to_distance / path.from_distance, moved);
      let target = centre.clone();
      if (leg.layer === "place" && into && share > 0.72) {  // the camera goes on into the room the rooms start with
        const closing = Math.min(1 / 0.85, travel((share - 0.72) / 0.28, [true, false]));
        target = centre.clone().lerp(into.middle, closing);
        camera.position.lerpVectors(this.orbit(turn, tilt, distance), into.middle.clone().add(new THREE.Vector3(0, 2, 6)), closing * 0.85);
      } else {
        camera.position.copy(this.orbit(turn, tilt, distance));
      }
      camera.lookAt(target);
      paint.render(scene, camera);
      const labelled = leg.layer === "site" ? clamp01((share - 0.35) / 0.2) : clamp01(1 - share * 3);
      for (const found of blocks) placeLabel(found.label, found.middle.clone().add(new THREE.Vector3(0, 3, 0)), camera, opacity * labelled);
      for (const other of others) placeLabel(other.label, other.at, camera, opacity * (leg.layer === "site" ? labelled : 0));
    },
    orbit(turn, tilt, distance) {
      return new THREE.Vector3(centre.x + distance * Math.cos(tilt) * Math.sin(turn), centre.y + distance * Math.sin(tilt),
                               centre.z + distance * Math.cos(tilt) * Math.cos(turn));
    },
  };
}

// --- the rooms: what exists of each (its concept), slowly closing in, one into the next -----------------------------

function roomView(leg) {
  const holder = document.createElement("div");
  holder.className = "view rooms";
  document.getElementById("views").append(holder);
  const shown = leg.pictures.map((picture) => {
    const frame = document.createElement("div");
    frame.className = "room";
    const image = document.createElement("img");
    image.src = picture.url;
    const words = document.createElement("span");
    words.textContent = picture.name;
    frame.append(image, words);
    holder.append(frame);
    return frame;
  });
  return {
    element: holder, labels: [],
    draw(local, leg) {
      const each = leg.seconds / shown.length;
      shown.forEach((frame, index) => {
        const start = index * each, mine = local - start;
        const into = index === 0 ? 1 : clamp01((mine + DISSOLVE / 2) / DISSOLVE);
        const out = index === shown.length - 1 ? 1 : clamp01((each - mine + DISSOLVE / 2) / DISSOLVE);
        frame.style.opacity = String(Math.min(into, out));
        frame.querySelector("img").style.transform = `scale(${1.04 + 0.12 * clamp01((mine + DISSOLVE / 2) / (each + DISSOLVE))}) translateX(${(index % 2 ? 1 : -1) * 1.5 * clamp01(mine / each)}%)`;
      });
    },
  };
}

// --- the timeline: each leg's view, dissolved into the next ---------------------------------------------------------

function viewFor(leg) {
  if (leg.layer === "setting") return settingView(leg);
  if (leg.layer === "world") return worldView(leg);
  if (leg.layer === "room") return roomView(leg);
  return groundView(leg);
}

function setup(data) {
  size = data.size;
  rate = data.rate;
  legs = data.legs;
  views = [];
  let start = 0;
  legs.forEach((leg, index) => { leg.rests = [false, index === legs.length - 1]; });  // one move, resting only at its end
  for (const leg of legs) {
    leg.start = start;
    start += leg.seconds;
    const shared = leg.view && views.find((view) => view.key === leg.view);
    if (shared) { leg.shown = shared; continue; }
    leg.shown = { key: leg.view, ...viewFor(leg) };
    views.push(leg.shown);
  }
  document.getElementById("tag").textContent = "";
}

// How much of `leg` shows at `seconds`: dissolving in from the leg before (unless it carries on in the same view)
// and out into the next.
function opacityOf(index, seconds) {
  const leg = legs[index], before = legs[index - 1], after = legs[index + 1];
  const carries = (other) => other && other.shown === leg.shown;
  const into = !before || carries(before) ? (seconds >= leg.start ? 1 : 0) : clamp01((seconds - leg.start + DISSOLVE / 2) / DISSOLVE);
  const end = leg.start + leg.seconds;
  const out = !after || carries(after) ? (seconds < end ? 1 : 0) : clamp01((end - seconds + DISSOLVE / 2) / DISSOLVE);
  return Math.min(into, out);
}

function draw(seconds) {
  const shown = new Map();
  legs.forEach((leg, index) => {
    const opacity = opacityOf(index, seconds);
    if (opacity <= 0) return;
    const now = shown.get(leg.shown);
    if (!now || opacity > now.opacity) shown.set(leg.shown, { leg, opacity });
  });
  let tag = "";
  for (const view of views) {
    const found = shown.get(view);
    view.element.style.opacity = found ? String(found.opacity) : "0";
    for (const shownLabel of view.labels) if (!found) shownLabel.style.opacity = "0";
    if (!found) continue;
    view.element.style.zIndex = String(legs.indexOf(found.leg));
    view.draw(seconds - found.leg.start, found.leg, found.opacity);
    if (found.opacity > 0.5 && found.leg.tag) tag = found.leg.tag;
  }
  document.getElementById("tag").textContent = tag;
  document.getElementById("tag").hidden = !tag;
}

window.filmScene = { setup, draw };
