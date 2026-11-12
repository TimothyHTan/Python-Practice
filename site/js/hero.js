// Home hero: "Hello, world!" drops letter by letter into a vertical column, like problem 1's output.
import * as THREE from 'three';
import { frameLoop } from './frameloop.js?v=6';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { FontLoader } from 'three/addons/loaders/FontLoader.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';

const host = document.querySelector('.hero-canvas');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
host.prepend(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 200);
camera.position.set(11, 2, 40);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableZoom = false;
controls.enablePan = false;
controls.enableDamping = true;
controls.autoRotate = !reduceMotion;
controls.autoRotateSpeed = 0.5;

const floor = new THREE.GridHelper(40, 40, 0x2a3f68, 0x1c2d4f);
floor.position.y = -11;
scene.add(floor);

const matcap = new THREE.TextureLoader().load('assets/textures/matcap-porcelain-white.jpg');
matcap.colorSpace = THREE.SRGBColorSpace;
const letterMat = new THREE.MeshMatcapMaterial({ matcap, color: 0xffd43b });
const punctMat = new THREE.MeshMatcapMaterial({ matcap, color: 0x4c8df6 });

const TEXT = 'Hello, world!';
const LINE = 1.5;
const letters = [];

new FontLoader().load('assets/fonts/helvetiker_bold.typeface.json', (font) => {
  [...TEXT].forEach((ch, i) => {
    if (ch === ' ') return; // print(' ') is a blank line: keep the gap, no mesh
    const geo = new TextGeometry(ch, {
      font, size: 1.15, depth: 0.4, curveSegments: 6,
      bevelEnabled: true, bevelThickness: 0.05, bevelSize: 0.03, bevelSegments: 3,
    });
    geo.center();
    const mesh = new THREE.Mesh(geo, /[a-z]/i.test(ch) ? letterMat : punctMat);
    const target = ((TEXT.length - 1) / 2 - i) * LINE;
    mesh.userData = { target, start: target + 16 + i * 0.6, delay: 0.3 + i * 0.13 };
    mesh.position.y = reduceMotion ? target : mesh.userData.start;
    scene.add(mesh);
    letters.push(mesh);
  });
  startedAt = performance.now();
});

function easeOutBounce(x) {
  const n = 7.5625, d = 2.75;
  if (x < 1 / d) return n * x * x;
  if (x < 2 / d) return n * (x -= 1.5 / d) * x + 0.75;
  if (x < 2.5 / d) return n * (x -= 2.25 / d) * x + 0.9375;
  return n * (x -= 2.625 / d) * x + 0.984375;
}

let startedAt = null;

function resize() {
  const { clientWidth: w, clientHeight: h } = host;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(host);

// Full frame rate while the letters fall and while you drag (plus the damping after); ~30 fps for the slow orbit.
let dragUntil = 0;
controls.addEventListener('start', () => { dragUntil = Infinity; });
controls.addEventListener('end', () => { dragUntil = performance.now() + 1500; });
const DROP_MS = 1000 * (0.3 + TEXT.length * 0.13 + 1);
const moving = () => performance.now() < dragUntil || (startedAt !== null && performance.now() - startedAt < DROP_MS);
let lastDraw = performance.now();
frameLoop(renderer, host, () => {
  const now = performance.now();
  const dt = Math.min(now - lastDraw, 100) / 1000;
  lastDraw = now;
  if (!reduceMotion && startedAt !== null) {
    const t = (performance.now() - startedAt) / 1000;
    for (const m of letters) {
      const { start, target, delay } = m.userData;
      const k = Math.min(Math.max((t - delay) / 0.9, 0), 1);
      m.position.y = start + (target - start) * easeOutBounce(k);
      m.rotation.y = (1 - k) * Math.PI;
    }
  }
  controls.update(dt);
  renderer.render(scene, camera);
}, moving);
