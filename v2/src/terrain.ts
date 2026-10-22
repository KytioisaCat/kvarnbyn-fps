// Terräng: rutor om 128 m i fem LOD-steg (1/2/4/8/16 m) ur 1 m-höjdfältet, med kjolar som
// döljer sprickor mellan LOD-nivåer. Normaler kommer ur höjdfältet (1 m) oavsett LOD-steg,
// så backarna ser lika ut på håll. Trianglar CCW sedda uppifrån (annars backface-cullas allt).
import * as THREE from 'three';
import { World } from './world';
import type { GroundTextures } from './ground';

const TILE = 128;
const LOD_STEPS = [1, 2, 4, 8, 16];
const LOD_DIST = [150, 380, 850, 1600];   // horisontellt avstånd rutmitt→kamera; längre bort → nästa steg

export class Terrain {
  readonly group = new THREE.Group();
  private readonly cache = new Map<string, THREE.Mesh>();
  private readonly nx: number; private readonly nz: number;
  private lastCam = new THREE.Vector3(Infinity, 0, 0);
  stats = { tiles: 0, tris: 0 };

  constructor(private readonly world: World, readonly material: THREE.Material) {
    const m = world.meta;
    this.nx = Math.ceil((m.x1 - m.x0) / TILE);
    this.nz = Math.ceil((m.z0 - m.z1) / TILE);
    this.group.name = 'terrain';
  }

  /** välj LOD per ruta efter kameraposition; bygger geometrier lat (cachas) */
  update(cam: THREE.Vector3, force = false): void {
    if (!force && cam.distanceToSquared(this.lastCam) < 36) return;
    this.lastCam.copy(cam);
    const m = this.world.meta;
    const visible = new Set<string>();
    let tris = 0;
    for (let tz = 0; tz < this.nz; tz++) {
      for (let tx = 0; tx < this.nx; tx++) {
        const xs = m.x0 + tx * TILE, zs = m.z1 + tz * TILE;
        const xe = Math.min(m.x1, xs + TILE), ze = Math.min(m.z0, zs + TILE);
        const cx = (xs + xe) / 2, cz = (zs + ze) / 2;
        const d = Math.hypot(cam.x - cx, cam.z - cz);
        let lod = LOD_DIST.length;
        for (let i = 0; i < LOD_DIST.length; i++) if (d < LOD_DIST[i]) { lod = i; break; }
        const key = `${tx}_${tz}_${lod}`;
        let mesh = this.cache.get(key);
        if (!mesh) {
          mesh = this.buildTile(xs, zs, xe, ze, LOD_STEPS[lod]);
          mesh.name = key;
          this.cache.set(key, mesh);
          this.group.add(mesh);
        }
        mesh.visible = true;
        visible.add(key);
        tris += mesh.geometry.index!.count / 3;
      }
    }
    for (const [key, mesh] of this.cache) if (!visible.has(key)) mesh.visible = false;
    this.stats = { tiles: visible.size, tris };
  }

  private buildTile(xs: number, zs: number, xe: number, ze: number, step: number): THREE.Mesh {
    const w = this.world, m = w.meta;
    const n = Math.round(TILE / step) + 1;     // rutnät n×n …
    const N = n + 2;                           // … plus kjolring
    const skirt = step * 2 + 3;
    const pos = new Float32Array(N * N * 3), nor = new Float32Array(N * N * 3), uv = new Float32Array(N * N * 2);
    const tmp = new THREE.Vector3();
    const iw = 1 / (m.x1 - m.x0), ih = 1 / (m.z0 - m.z1);
    for (let j = 0; j < N; j++) {
      const gj = Math.min(n - 1, Math.max(0, j - 1));
      const z = Math.min(ze, zs + gj * step);
      for (let i = 0; i < N; i++) {
        const gi = Math.min(n - 1, Math.max(0, i - 1));
        const x = Math.min(xe, xs + gi * step);
        const edge = i === 0 || j === 0 || i === N - 1 || j === N - 1;
        const y = w.heightAt(x, z) - (edge ? skirt : 0);
        const k = j * N + i;
        pos[k * 3] = x; pos[k * 3 + 1] = y; pos[k * 3 + 2] = z;
        w.normalAt(x, z, tmp);
        nor[k * 3] = tmp.x; nor[k * 3 + 1] = tmp.y; nor[k * 3 + 2] = tmp.z;
        uv[k * 2] = (x - m.x0) * iw;
        uv[k * 2 + 1] = 1 - (z - m.z1) * ih;   // flipY: v=1 är bildens rad 0 = norr
      }
    }
    const idx = new Uint32Array((N - 1) * (N - 1) * 6);
    let q = 0;
    for (let j = 0; j < N - 1; j++) {
      for (let i = 0; i < N - 1; i++) {
        const a = j * N + i, b = a + 1, c = a + N, d = c + 1;
        idx[q++] = a; idx[q++] = c; idx[q++] = b;   // CCW uppifrån
        idx[q++] = b; idx[q++] = c; idx[q++] = d;
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    g.setIndex(new THREE.BufferAttribute(idx, 1));
    g.computeBoundingSphere();
    const mesh = new THREE.Mesh(g, this.material);
    mesh.receiveShadow = true;
    mesh.castShadow = step <= 2;   // bara fina rutor kastar skugga (backar skuggar varandra nära spelaren)
    mesh.frustumCulled = true;
    return mesh;
  }
}

/** Terrängmaterial: ortofotot som färg på håll (klasstonat — vårfotot är gråblekt); nära
 *  blandas v1:s procedurella detaljtexturer in per markklass, med fotot som ljus/makrofärg.
 *  Blandningsformeln är v1:s (public/game.js, kalibrerad), minus det bakade ljuset som här
 *  kommer från riktig belysning + skuggor. Branta ytor blir berg oavsett klass. */
export function makeTerrainMaterial(world: World, ortho: THREE.Texture, classmap: THREE.Texture, det: GroundTextures): THREE.MeshStandardMaterial {
  const m = world.meta;
  const mat = new THREE.MeshStandardMaterial({ map: ortho, roughness: 0.95, metalness: 0 });
  const uniforms = {
    uClass: { value: classmap },
    uBounds: { value: new THREE.Vector4(m.x0, m.z1, 1 / (m.x1 - m.x0), 1 / (m.z0 - m.z1)) },
    detA: { value: det.asphalt }, detG: { value: det.grass }, detF: { value: det.forest }, detR: { value: det.rock }, detN: { value: det.macro },
  };
  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWPos;\nvarying float vSlope;\nvarying vec3 vWNor;')
      .replace('#include <begin_vertex>', `#include <begin_vertex>
vWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
vWNor = normalize(mat3(modelMatrix) * normal);
vSlope = min(1.0, (1.0 - normal.y) * 2.2);`);
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
varying vec3 vWPos;
varying float vSlope;
varying vec3 vWNor;
uniform sampler2D uClass;
uniform vec4 uBounds;
uniform sampler2D detA, detG, detF, detR, detN;
vec4 kvW;   // klassvikter: asfalt, gräs, skog, berg`)
      .replace('#include <map_fragment>', `#include <map_fragment>
{
  vec2 kvUv = vec2((vWPos.x - uBounds.x) * uBounds.z, 1.0 - (vWPos.z - uBounds.y) * uBounds.w);
  vec3 sp = texture2D(uClass, kvUv).rgb;                        // R asfalt, G gräs, B skog
  float wRock = clamp(1.0 - sp.r - sp.g - sp.b, 0.0, 1.0);      // svart = berg
  wRock = max(wRock, smoothstep(0.55, 0.8, vSlope) * 0.85);     // branta ytor blir berg
  vec4 w = pow(vec4(sp.r, sp.g, sp.b, wRock), vec4(1.35));      // skärp klassgränserna
  w /= max(w.x + w.y + w.z + w.w, 1e-3);
  kvW = w;
  // färglägg fotot efter markklass även på håll (vårfotot är gråblekt)
  vec3 farTint = w.x * vec3(1.0, 1.0, 1.0) + w.y * vec3(0.98, 1.10, 0.86)
               + w.z * vec3(0.62, 0.94, 0.55) + w.w * vec3(1.10, 1.08, 1.02);
  vec3 photo = diffuseColor.rgb * farTint;
  float wNear = 1.0 - smoothstep(30.0, 110.0, length(vWPos - cameraPosition));
  diffuseColor.rgb = photo;
  // branta ytor (klippor, terrasser, stödmurar i LiDAR:n): fotot är taget uppifrån och smetas ut
  // på vertikala ytor — där används bergtexturen triplanärt på ALLA avstånd
  float steep = smoothstep(0.45, 0.75, vSlope);
  if (steep > 0.003) {
    vec3 an = abs(vWNor);
    vec2 uvS = (an.x > an.z) ? vWPos.zy / 2.6 : vWPos.xy / 2.6;
    vec3 rockSide = texture2D(detR, uvS).rgb * (0.82 + 0.36 * texture2D(detN, uvS / 17.0).r);
    float plS = dot(photo, vec3(0.299, 0.587, 0.114));
    vec3 rockLit = rockSide * (0.55 + 0.9 * mix(plS, 0.5, 0.6));
    diffuseColor.rgb = mix(diffuseColor.rgb, rockLit, steep);
    photo = diffuseColor.rgb;
  }
  if (wNear > 0.003) {
    vec2 duv = vWPos.xz / 2.6;                                    // 512 px ≈ 2,6 m
    vec3 d = vec3(0.0);
    if (w.x > 0.004) d += texture2D(detA, duv).rgb * w.x;
    if (w.y > 0.004) d += texture2D(detG, duv).rgb * w.y;
    if (w.z > 0.004) d += texture2D(detF, duv).rgb * w.z;
    if (w.w > 0.004) d += texture2D(detR, duv).rgb * w.w;
    d *= 0.82 + 0.36 * texture2D(detN, vWPos.xz / 45.0).r;       // makrobrus dödar tiling
    // fotot bidrar med ljus (solfläckar/skuggor) men bara 35 % färg
    float pl = dot(photo, vec3(0.299, 0.587, 0.114));
    vec3 near = d * (0.50 + 1.15 * mix(vec3(pl), photo, 0.35));
    diffuseColor.rgb = mix(photo, near, wNear);
  }
}`)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
roughnessFactor = 0.80 * kvW.x + 0.98 * kvW.y + 1.0 * kvW.z + 0.75 * kvW.w;`);
  };
  mat.customProgramCacheKey = () => 'kvarnbyn-terrain-v2';
  return mat;
}
