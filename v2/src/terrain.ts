// Terräng: rutor om 128 m i fem LOD-steg (1/2/4/8/16 m) ur 1 m-höjdfältet, med kjolar som
// döljer sprickor mellan LOD-nivåer. Normaler kommer ur höjdfältet (1 m) oavsett LOD-steg,
// så backarna ser lika ut på håll. Trianglar CCW sedda uppifrån (annars backface-cullas allt).
import * as THREE from 'three';
import { World } from './world';

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

/** Terrängmaterial: ortofotot som färg på håll; nära blandas klasskartan in som
 *  procedurell detalj (gräs/asfalt/skog/berg — tills riktiga PBR-texturer laddas ner). */
export function makeTerrainMaterial(world: World, ortho: THREE.Texture, classmap: THREE.Texture): THREE.MeshStandardMaterial {
  const m = world.meta;
  const mat = new THREE.MeshStandardMaterial({ map: ortho, roughness: 0.95, metalness: 0 });
  const uniforms = {
    uClass: { value: classmap },
    uBounds: { value: new THREE.Vector4(m.x0, m.z1, 1 / (m.x1 - m.x0), 1 / (m.z0 - m.z1)) },
  };
  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWPos;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
varying vec3 vWPos;
uniform sampler2D uClass;
uniform vec4 uBounds;
float kvHash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float kvNoise(vec2 p) {
  vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(kvHash(i), kvHash(i + vec2(1.0, 0.0)), f.x), mix(kvHash(i + vec2(0.0, 1.0)), kvHash(i + vec2(1.0, 1.0)), f.x), f.y);
}`)
      .replace('#include <map_fragment>', `#include <map_fragment>
vec2 kvUv = vec2((vWPos.x - uBounds.x) * uBounds.z, 1.0 - (vWPos.z - uBounds.y) * uBounds.w);
vec3 kvCls = texture2D(uClass, kvUv).rgb;                       // R asfalt, G gräs, B skog
float kvRock = clamp(1.0 - kvCls.r - kvCls.g - kvCls.b, 0.0, 1.0); // svart = berg
float kvNear = 1.0 - smoothstep(25.0, 180.0, length(vWPos - cameraPosition));
float n1 = kvNoise(vWPos.xz * 0.8), n2 = kvNoise(vWPos.xz * 6.0), n3 = kvNoise(vWPos.xz * 23.0);
vec3 kvTint = vec3(1.0);
kvTint = mix(kvTint, vec3(0.88, 1.06, 0.78), kvCls.g * 0.55);
kvTint = mix(kvTint, vec3(0.70, 0.84, 0.62), kvCls.b * 0.55);
kvTint = mix(kvTint, vec3(0.80, 0.80, 0.83), kvCls.r * 0.40);
kvTint = mix(kvTint, vec3(1.06, 1.02, 0.96), kvRock * 0.35);
float kvGrain = (n1 - 0.5) * (0.08 + 0.22 * kvCls.g + 0.18 * kvCls.b + 0.28 * kvRock)
              + (n2 - 0.5) * (0.05 + 0.14 * kvCls.g + 0.10 * kvCls.b + 0.12 * kvRock + 0.04 * kvCls.r)
              + (n3 - 0.5) * (0.03 + 0.06 * kvCls.g + 0.05 * kvRock + 0.05 * kvCls.r);
diffuseColor.rgb *= mix(vec3(1.0), kvTint * (1.0 + kvGrain), kvNear);`)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
roughnessFactor = mix(roughnessFactor, 0.72 + 0.26 * kvCls.g + 0.2 * kvCls.b + 0.1 * kvCls.r - 0.05 * kvRock, kvNear);`);
  };
  mat.customProgramCacheKey = () => 'kvarnbyn-terrain-v1';
  return mat;
}
