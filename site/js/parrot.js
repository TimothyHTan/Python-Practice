// Animated parrot (from the three.js examples) flapping in the notes page corner.
import * as THREE from 'three';
import { frameLoop } from './frameloop.js?v=6';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const host = document.getElementById('parrot');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
host.append(renderer.domElement);

const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff, 0x4c8df6, 3));
const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 5000);

let mixer, bird, baseY = 0;
const timer = new THREE.Timer();

new GLTFLoader().load('assets/models/Parrot.glb', (gltf) => {
  bird = gltf.scene;
  bird.rotation.y = -Math.PI / 2.4;
  // Fit the camera to the model instead of guessing its units.
  const box = new THREE.Box3().setFromObject(bird, true); // precise: ignores morph-target extremes
  bird.position.sub(box.getCenter(new THREE.Vector3()));
  camera.position.set(0, 0, box.getSize(new THREE.Vector3()).length() * 1.9);
  baseY = bird.position.y;
  scene.add(bird);
  mixer = new THREE.AnimationMixer(bird);
  mixer.clipAction(gltf.animations[0]).setDuration(1.2).play();
  if (reduceMotion) mixer.update(0.3);
});

new ResizeObserver(() => {
  const w = host.clientWidth, h = host.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}).observe(host);

// ~30 fps is plenty for the flapping.
frameLoop(renderer, host, (time) => {
  timer.update(time);
  if (mixer && !reduceMotion) {
    mixer.update(timer.getDelta());
    bird.position.y = baseY + Math.sin(time / 600) * camera.position.z * 0.03;
  }
  renderer.render(scene, camera);
}, () => false);
