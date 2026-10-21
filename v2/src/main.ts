// Försvara Kvarnbyn v2 — startpunkt. Delmål M1: terrängen (1 m-LiDAR, LOD, ortofoto + klass-
// detalj, himmel/sol/skuggor) med FPS-kamera. Kalibreringar från v1 (public/game.js):
// EXAG 1,2, ögonhöjd 1,7 m, gångfart 5,2 / sprint 8,2 m/s, spawn (447,53).
import * as THREE from 'three';
import { World, SPAWN, DATA_URL, loadImage } from './world';
import { Terrain, makeTerrainMaterial } from './terrain';
import { Daylight } from './sky';
import { FpsControls } from './controls';
import { makeGroundTextures } from './ground';
import { loadRoads } from './roads';

const app = document.getElementById('app')!;
const overlay = document.getElementById('overlay')!;
const status = document.getElementById('status')!;
const hud = document.getElementById('hud')!;
const say = (s: string) => { status.textContent = s; };

const isMobile = matchMedia('(pointer: coarse)').matches;
const renderer = new THREE.WebGLRenderer({ antialias: !isMobile, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, isMobile ? 1.5 : 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.55;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0xc3d2e4, 0.00042);
const camera = new THREE.PerspectiveCamera(72, innerWidth / innerHeight, 0.15, 6000);

const gl = renderer.getContext();
const dbg = gl.getExtension('WEBGL_debug_renderer_info');
const gpu = dbg ? String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)) : 'okänd GPU';
const maxTex = renderer.capabilities.maxTextureSize;

const player = {
  pos: new THREE.Vector3(SPAWN[0], 0, SPAWN[1]),
  eyeY: 1.7,
  walk: 5.2, sprint: 8.2,
};
const controls = new FpsControls(renderer.domElement);

let world: World | null = null;
let terrain: Terrain | null = null;
let daylight: Daylight | null = null;

async function init() {
  say(`three r${THREE.REVISION} · ${gpu}`);
  world = await World.load(say);
  // 8k-fotot (8,8 MB) bara på dator: telefonen får 4k (2,9 MB) — mätt nät och GPU-minne
  const orthoFile = !isMobile && maxTex >= 8192 ? 'ortho_8k.jpg' : 'ortho_4k.jpg';
  const orthoImg = await loadImage(`${DATA_URL}${orthoFile}`, 'ortofoto', say);
  const classImg = await loadImage(`${DATA_URL}${world.meta.classmap.file}`, 'klasskarta', say);
  const ortho = new THREE.Texture(orthoImg), classmap = new THREE.Texture(classImg);
  ortho.needsUpdate = classmap.needsUpdate = true;
  ortho.colorSpace = THREE.SRGBColorSpace;
  ortho.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  ortho.generateMipmaps = true;
  ortho.minFilter = THREE.LinearMipmapLinearFilter;
  classmap.colorSpace = THREE.NoColorSpace;
  classmap.minFilter = THREE.LinearFilter; classmap.magFilter = THREE.LinearFilter;
  classmap.generateMipmaps = false;

  say('ritar markdetaljer …');
  const ground = makeGroundTextures(Math.min(4, renderer.capabilities.getMaxAnisotropy()));
  terrain = new Terrain(world, makeTerrainMaterial(world, ortho, classmap, ground));
  scene.add(terrain.group);
  daylight = new Daylight(renderer, scene, isMobile);
  try { scene.add(await loadRoads(say)); } catch (e) { console.warn('inga vägar:', e); }

  player.pos.y = world.heightAt(player.pos.x, player.pos.z) + player.eyeY;
  camera.position.copy(player.pos);
  controls.applyTo(camera);
  say('bygger terräng …');
  terrain.update(player.pos, true);
  daylight.follow(player.pos);
  renderer.render(scene, camera);   // kompilera shaders före första riktiga bildrutan
  say(`klart · ${terrain.stats.tiles} rutor, ${(terrain.stats.tris / 1e6).toFixed(2)} M tri · ${gpu}`);
  overlay.classList.add('ready');
}

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

let running = false;
let fly = false;
overlay.addEventListener('click', () => {
  if (!overlay.classList.contains('ready')) return;
  overlay.style.display = 'none'; running = true; controls.lock();
});

const tmpMove = new THREE.Vector3();
let fpsAcc = 0, fpsN = 0, fpsShown = 0;
function frame(dt: number) {
  if (!world || !terrain || !daylight) return;
  controls.poll();
  controls.worldMove(tmpMove);
  const speed = controls.sprint ? player.sprint : player.walk;
  const nx = player.pos.x + tmpMove.x * speed * dt, nz = player.pos.z + tmpMove.z * speed * dt;
  if (world.inside(nx, nz, 4)) { player.pos.x = nx; player.pos.z = nz; }
  if (!fly) {
    const groundY = world.heightAt(player.pos.x, player.pos.z) + player.eyeY;
    player.pos.y += (groundY - player.pos.y) * Math.min(1, dt * 14);
  }
  camera.position.copy(player.pos);
  controls.applyTo(camera);
  terrain.update(player.pos);
  daylight.follow(player.pos);
  renderer.render(scene, camera);

  fpsAcc += dt; fpsN++;
  if (fpsAcc >= 0.5) { fpsShown = Math.round(fpsN / fpsAcc); fpsAcc = 0; fpsN = 0; }
  hud.textContent = `${fpsShown} fps · x ${player.pos.x.toFixed(0)} z ${player.pos.z.toFixed(0)} · ${(player.pos.y - player.eyeY).toFixed(1)} m ö.h. · ${terrain.stats.tiles} rutor ${(terrain.stats.tris / 1e6).toFixed(2)} M tri`;
}

let last = performance.now();
renderer.setAnimationLoop(() => {
  const now = performance.now();
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  if (running) frame(dt);
});

init().catch((e: unknown) => { say(`fel: ${e instanceof Error ? e.message : String(e)}`); console.error(e); });

// Debughookar (samma mönster som v1) så en headless-körning kan stega spelet utan rAF.
declare global {
  interface Window {
    __frame: (dt: number) => void;
    __look: (yaw: number, pitch: number) => void;
    __tp: (x: number, z: number) => void;
    __fly: (x: number, y: number, z: number) => void;
    __v2: Record<string, unknown>;
  }
}
window.__frame = (dt) => { running = true; frame(dt); };
window.__look = (yaw, pitch) => { controls.yaw = yaw; controls.pitch = pitch; };
window.__fly = (x, y, z) => { fly = true; player.pos.set(x, y, z); };
window.__tp = (x, z) => { fly = false; player.pos.x = x; player.pos.z = z; if (world) player.pos.y = world.heightAt(x, z) + player.eyeY; };
window.__v2 = { scene, camera, renderer, player, controls, get world() { return world; }, get terrain() { return terrain; }, get daylight() { return daylight; } };
