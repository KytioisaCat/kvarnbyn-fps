// Försvara Kvarnbyn v2 — startpunkt.
// Detta är ett tomt skal: bevisar att bygget, deployen till /v2/ och renderaren fungerar
// på Joels telefon. Själva motorn byggs ovanpå detta enligt KRAVSPEC.md och v2/PLAN.md.
import * as THREE from 'three';

const app = document.getElementById('app')!;
const overlay = document.getElementById('overlay')!;
const status = document.getElementById('status')!;

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x87a8c8);
const camera = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.1, 2000);
camera.position.set(0, 1.7, 5);

const sun = new THREE.DirectionalLight(0xfff2e0, 3);
sun.position.set(50, 80, 30);
scene.add(sun, new THREE.HemisphereLight(0xbfd8ff, 0x50452e, 1));

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(200, 200),
  new THREE.MeshStandardMaterial({ color: 0x4a6b3a, roughness: 1 })
);
ground.rotation.x = -Math.PI / 2;
scene.add(ground);

const hus = new THREE.Mesh(
  new THREE.BoxGeometry(8, 5, 6),
  new THREE.MeshStandardMaterial({ color: 0xf2efe6, roughness: 0.8 })
);
hus.position.set(0, 2.5, -10);
scene.add(hus);

const gl = renderer.getContext();
const dbg = gl.getExtension('WEBGL_debug_renderer_info');
const gpu = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : 'okänd';
status.textContent = `three r${THREE.REVISION} · ${gpu}`;

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

let running = false;
overlay.addEventListener('click', () => { overlay.style.display = 'none'; running = true; });

let t = 0;
function frame(dt: number) {
  t += dt;
  hus.rotation.y = t * 0.3;
  renderer.render(scene, camera);
}
let last = performance.now();
renderer.setAnimationLoop(() => {
  const now = performance.now();
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  if (running) frame(dt);
  else renderer.render(scene, camera);
});

// Debughookar (samma mönster som v1) så en headless-körning kan stega spelet utan rAF.
declare global { interface Window { __frame: (dt: number) => void; __v2: unknown } }
window.__frame = frame;
window.__v2 = { scene, camera, renderer };
