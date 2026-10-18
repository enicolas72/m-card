// Rendu 3D temps réel de l'appareil : pièces STL exportées depuis
// enclosure/mcard.scad (position assemblée, cf. build/parts.scad), écran LCD
// émulé en texture, carte M-Card qui glisse dans la fente.
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

// cotes reprises de mcard.scad
const BOX_H = 48, LIP = 10, CONSOLE_RUN = 57, SLOT_DEPTH = 28, LID_T = 4;
const ALPHA = Math.atan((BOX_H - LIP) / CONSOLE_RUN);
const CARD_W = 54, CARD_H = 86.6, CARD_T = 0.8;
const CARD_SEATED_Z = BOX_H - SLOT_DEPTH + CARD_H / 2 + 0.5;

function b64ToBuffer(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out.buffer;
}

const ease = {
  inCubic: (t) => t * t * t,
  outBack: (t) => { const c = 1.25; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); },
};

export function createDeviceScene(container, { stl, cards, lcd }) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.7;

  const camera = new THREE.PerspectiveCamera(30, 1, 10, 4000);
  camera.position.set(-170, 230, 430);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 52, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.enableZoom = false;
  controls.enablePan = false;
  controls.minPolarAngle = 0.35;
  controls.maxPolarAngle = 1.45;
  controls.update();

  // lumières : clé chaude, contre-jour froid (rappel de l'écran bleu)
  const key = new THREE.DirectionalLight(0xfff1e0, 2.4);
  key.position.set(-160, 320, 260);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, { left: -260, right: 260, top: 260, bottom: -260, near: 10, far: 1200 });
  key.shadow.radius = 6;
  key.shadow.bias = -0.0004;
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x8fa8ff, 1.6);
  rim.position.set(260, 160, -260);
  scene.add(rim);
  const glow = new THREE.PointLight(0x3355ff, 900, 180, 2);
  scene.add(glow);

  // sol : ne reçoit que l'ombre (fond de page visible au travers)
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(2000, 2000),
    new THREE.ShadowMaterial({ opacity: 0.38 }));
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -LID_T;
  ground.receiveShadow = true;
  scene.add(ground);

  // repère OpenSCAD (Z en haut, façade vers -Y) → three (Y en haut, façade vers +Z)
  const device = new THREE.Group();
  device.rotation.x = -Math.PI / 2;
  scene.add(device);

  const pla = (color, roughness = 0.68) =>
    new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.0 });
  const lcdTexture = new THREE.CanvasTexture(lcd.canvas);
  lcdTexture.colorSpace = THREE.SRGBColorSpace;
  lcdTexture.anisotropy = 8;
  const materials = {
    shell: pla(0x121215),
    faceplate: pla(0x0f0f12, 0.6),
    icon_plate: new THREE.MeshStandardMaterial({ color: 0xe0a74a, roughness: 0.4, emissive: 0x6a4210, emissiveIntensity: 0.4 }),
    backrest: pla(0x131316),
    backrest_cover: pla(0x111114),
    lid: pla(0x0c0c0e),
    lcd_bezel: new THREE.MeshStandardMaterial({ color: 0x050507, roughness: 0.3 }),
    lcd_screen: new THREE.MeshBasicMaterial({ map: lcdTexture, toneMapped: false }),
    buttons: new THREE.MeshStandardMaterial({ color: 0xe8e8ec, metalness: 1.0, roughness: 0.22 }),
    screws: new THREE.MeshStandardMaterial({ color: 0xc9c9ce, metalness: 1.0, roughness: 0.32 }),
    usbc_body: pla(0x08080a, 0.45),
    usbc_metal: new THREE.MeshStandardMaterial({ color: 0xdadade, metalness: 1.0, roughness: 0.25 }),
    usbc_slot: new THREE.MeshBasicMaterial({ color: 0x020202 }),
  };
  lcd.onDraw = () => { lcdTexture.needsUpdate = true; };

  const loader = new STLLoader();
  for (const [name, b64] of Object.entries(stl)) {
    const geometry = loader.parse(b64ToBuffer(b64));
    if (name === 'lcd_screen') screenUVs(geometry);
    const mesh = new THREE.Mesh(geometry, materials[name]);
    mesh.castShadow = !name.startsWith('lcd');
    mesh.receiveShadow = true;
    device.add(mesh);
  }

  // UV de la dalle : projection dans le plan incliné de la façade
  function screenUVs(geometry) {
    const pos = geometry.attributes.position;
    const sDir = new THREE.Vector3(0, Math.cos(ALPHA), Math.sin(ALPHA));
    const p = new THREE.Vector3();
    let minX = Infinity, maxX = -Infinity, minS = Infinity, maxS = -Infinity;
    for (let i = 0; i < pos.count; i++) {
      p.fromBufferAttribute(pos, i);
      const s = p.dot(sDir);
      minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
      minS = Math.min(minS, s); maxS = Math.max(maxS, s);
    }
    const uv = new Float32Array(pos.count * 2);
    for (let i = 0; i < pos.count; i++) {
      p.fromBufferAttribute(pos, i);
      uv[2 * i] = (p.x - minX) / (maxX - minX);
      uv[2 * i + 1] = (p.dot(sDir) - minS) / (maxS - minS);
    }
    geometry.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    // la lumière bleue émane du centre de l'écran, 30 mm devant (le long
    // de la normale de façade) ; repère scad (x, y, z) → three (x, z, -y)
    geometry.computeBoundingBox();
    const c = geometry.boundingBox.getCenter(new THREE.Vector3())
      .addScaledVector(new THREE.Vector3(0, -Math.sin(ALPHA), Math.cos(ALPHA)), 30);
    glow.position.set(c.x, c.z, -c.y);
  }

  // carte M-Card : recto = jaquette, verso brun du logo
  const texLoader = new THREE.TextureLoader();
  const cardTextures = cards.map((url) => {
    const t = texLoader.load(url);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 8;
    return t;
  });
  const cardFront = new THREE.MeshStandardMaterial({ map: cardTextures[0], roughness: 0.35 });
  const cardBack = new THREE.MeshStandardMaterial({ color: 0x352727, roughness: 0.5 });
  const cardEdge = new THREE.MeshStandardMaterial({ color: 0xf2efe9, roughness: 0.6 });
  const card = new THREE.Mesh(new THREE.BoxGeometry(CARD_W, CARD_H, CARD_T),
    [cardEdge, cardEdge, cardEdge, cardEdge, cardFront, cardBack]);
  card.castShadow = true;
  card.rotation.x = Math.PI / 2 - 0.035;   // debout dans la fente, très légèrement penchée
  card.position.set(0, 0, CARD_SEATED_Z);
  device.add(card);

  // ---- animation de changement de carte -----------------------------
  let swap = null;   // { start, next, onSeated }
  const LIFT = 130, OUT_MS = 520, IN_MS = 900;
  function showCard(index, onSeated) {
    swap = { start: performance.now(), next: index, onSeated, swapped: false };
  }
  function animateCard(now) {
    if (!swap) return;
    const t = now - swap.start;
    if (t < OUT_MS) {
      card.position.z = CARD_SEATED_Z + LIFT * ease.inCubic(t / OUT_MS);
    } else {
      if (!swap.swapped) {
        cardFront.map = cardTextures[swap.next];
        cardFront.needsUpdate = true;
        swap.swapped = true;
      }
      const k = Math.min(1, (t - OUT_MS) / IN_MS);
      card.position.z = CARD_SEATED_Z + LIFT * (1 - ease.outBack(k));
      if (k >= 1) {
        const cb = swap.onSeated;
        swap = null;
        if (cb) cb();
      }
    }
  }

  // ---- balancement automatique tant que l'utilisateur ne touche à rien
  let lastInteraction = -1e9;
  controls.addEventListener('start', () => { lastInteraction = performance.now(); });
  controls.addEventListener('end', () => { lastInteraction = performance.now(); });
  const sph = new THREE.Spherical();
  const offset = new THREE.Vector3();

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    // recule la caméra sur écran étroit pour garder l'appareil entier
    camera.zoom = Math.min(1, (w / h) / 1.25 + 0.15);
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(container);
  resize();

  let running = false;
  const t0 = performance.now();
  function frame(now) {
    if (!running) return;
    animateCard(now);
    if (now - lastInteraction > 3500) {
      offset.copy(camera.position).sub(controls.target);
      sph.setFromVector3(offset);
      const tt = (now - t0) / 1000;
      const targetTheta = -0.38 + Math.sin(tt * 0.22) * 0.42;
      const targetPhi = 1.05 + Math.sin(tt * 0.15) * 0.08;
      sph.theta += (targetTheta - sph.theta) * 0.012;
      sph.phi += (targetPhi - sph.phi) * 0.012;
      offset.setFromSpherical(sph);
      camera.position.copy(controls.target).add(offset);
    }
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  // ne rend que lorsque visible
  new IntersectionObserver(([e]) => {
    const was = running;
    running = e.isIntersecting;
    if (running && !was) requestAnimationFrame(frame);
  }).observe(container);

  return { showCard };
}
