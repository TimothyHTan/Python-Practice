// The 3D gem under the problem list is a shell with a pearl inside. Clicking it opens the helper chat:
// the shell turns to face you, its top swings open on a hinge and the pearl rises (the chat grows out of it).
// It also flashes mint/coral on pass/fail, and the pearl glows blue while the helper is thinking.
import * as THREE from 'three';
import { frameLoop, damp } from './frameloop.js?v=6';

const host = document.getElementById('badge');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
host.append(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 20);
camera.position.z = 4.4;

const matcap = new THREE.TextureLoader().load('assets/textures/matcap-porcelain-white.jpg');
matcap.colorSpace = THREE.SRGBColorSpace;
const IDLE = new THREE.Color(0xffd43b);
const shellMat = new THREE.MeshMatcapMaterial({ matcap, color: IDLE.clone(), side: THREE.DoubleSide });
const edgeMat = new THREE.LineBasicMaterial({ color: 0x13213c });

// Split an icosahedron into a top and a bottom half by face height; each half hangs on a hinge at the back.
const HINGE = new THREE.Vector3(0, 0, -0.85);
function half(top) {
  const src = new THREE.IcosahedronGeometry(1, 0).toNonIndexed().getAttribute('position');
  const keep = [];
  for (let i = 0; i < src.count; i += 3) {
    const cy = (src.getY(i) + src.getY(i + 1) + src.getY(i + 2)) / 3;
    if ((cy >= 0) === top) for (let k = 0; k < 3; k++) keep.push(src.getX(i + k), src.getY(i + k) - HINGE.y, src.getZ(i + k) - HINGE.z);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(keep, 3));
  geo.computeVertexNormals();
  const mesh = new THREE.Mesh(geo, shellMat);
  mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo), edgeMat));
  const hinge = new THREE.Group();
  hinge.position.copy(HINGE);
  hinge.add(mesh);
  return hinge;
}
const topHalf = half(true);
const bottomHalf = half(false);

// The pearl: pearly matcap plus a soft glow sprite behind it.
const PEARL = new THREE.Color(1.55, 1.5, 1.42); // above 1 so the grey matcap reads as a bright pearl
const THINK = new THREE.Color(0x8fb8ff);
const pearlMat = new THREE.MeshMatcapMaterial({ matcap, color: PEARL.clone() });
const pearl = new THREE.Mesh(new THREE.SphereGeometry(0.42, 48, 32), pearlMat);
const glowTex = (() => {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.35, 'rgba(255,240,215,0.55)');
  grad.addColorStop(1, 'rgba(255,240,215,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
})();
const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0 }));
glow.scale.setScalar(2.4);
pearl.add(glow);
pearl.scale.setScalar(0.001);

const spinner = new THREE.Group(); // spins while closed; turns to face you to open
spinner.add(topHalf, bottomHalf, pearl);
const pivot = new THREE.Group(); // leans toward the pointer
pivot.add(spinner);
scene.add(pivot);

let spin = 0;
let thinking = false;
let flashTimer = 0;
let openTarget = 0; // 0 closed, 1 open
let openness = 0;   // eased toward openTarget
let windUp = 0;     // extra twist while the shell shuts
const lean = { x: 0, y: 0 };
const facing = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.42, 0, 0)); // tilted so you see inside

export function flash(pass) {
  clearTimeout(flashTimer);
  shellMat.color.set(pass ? 0x3ddc97 : 0xff6b6b);
  spin = reduceMotion ? 0 : 1;
  flashTimer = setTimeout(() => shellMat.color.copy(IDLE), 2500);
}

export const setThinking = (on) => { thinking = on; };

const wait = (ms) => new Promise((r) => setTimeout(r, reduceMotion ? 0 : ms));

// Opens the shell; resolves once the pearl is out, so the chat can grow from it.
export async function openShell() {
  openTarget = 1;
  spin = 0;
  if (reduceMotion) openness = 1;
  await wait(280); // the pearl shows for a moment, then the chat grows out of it
}

// Closes the shell with a winding spin.
export function closeShell() {
  openTarget = 0;
  windUp = reduceMotion ? 0 : 1;
  if (reduceMotion) openness = 0;
}

// Where the pearl is on screen (the chat grows out of / unwinds into this point).
export function pearlPoint() {
  const p = new THREE.Vector3();
  pearl.getWorldPosition(p).project(camera);
  const r = host.getBoundingClientRect();
  return { x: r.left + (p.x + 1) / 2 * r.width, y: r.top + (1 - p.y) / 2 * r.height };
}

host.addEventListener('pointermove', (e) => {
  const r = host.getBoundingClientRect();
  lean.x = ((e.clientY - r.top) / r.height - 0.5) * 0.6;
  lean.y = ((e.clientX - r.left) / r.width - 0.5) * 0.6;
});
host.addEventListener('pointerleave', () => { lean.x = 0; lean.y = 0; });

new ResizeObserver(() => {
  const w = host.clientWidth, h = host.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}).observe(host);

const ease = (t) => t * t * (3 - 2 * t);
// Full frame rate only while opening/closing, flashing, thinking or leaning; the idle spin runs at ~30 fps.
const moving = () => thinking || spin > 0.02 || windUp > 0.02 || Math.abs(openTarget - openness) > 0.003
  || spinner.quaternion.angleTo(facing) > 0.01 && openTarget > 0
  || Math.abs(lean.x - pivot.rotation.x) + Math.abs(lean.y - pivot.rotation.y) > 0.002;
frameLoop(renderer, host, (t, f) => {
  const time = t / 1000;
  if (!reduceMotion) {
    openness += (openTarget - openness) * damp(openTarget ? 0.17 : 0.13, f);
    if (openTarget || openness > 0.02) {
      spinner.quaternion.slerp(facing, damp(0.14, f)); // turn to face you before/while opening
    } else {
      spinner.rotation.y += (0.004 + spin * 0.15 + windUp * 0.35) * f;
      spinner.rotation.x += (0.002 + spin * 0.05) * f;
    }
    spin *= 0.96 ** f;
    windUp *= 0.94 ** f;
    pivot.rotation.x += (lean.x - pivot.rotation.x) * damp(0.08, f);
    pivot.rotation.y += (lean.y - pivot.rotation.y) * damp(0.08, f);
  }
  const o = ease(Math.min(1, Math.max(0, openness)));
  topHalf.rotation.x = -1.25 * o;       // lid swings up and back
  bottomHalf.rotation.x = 0.28 * o;     // base dips a little
  const p = ease(Math.min(1, Math.max(0, (openness - 0.25) / 0.75)));
  pearl.scale.setScalar(Math.max(0.001, p * (thinking ? 1 + Math.sin(time * 6) * 0.06 : 1)));
  pearl.position.y = 0.12 * p;
  glow.material.opacity = p * (thinking ? 0.75 + Math.sin(time * 4) * 0.25 : 0.65);
  const tint = thinking ? 0.5 + Math.sin(time * 3) * 0.4 : 0;
  pearlMat.color.lerpColors(PEARL, THINK, tint);
  glow.material.color.lerpColors(PEARL, THINK, tint);
  renderer.render(scene, camera);
}, moving);
