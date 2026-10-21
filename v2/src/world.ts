// Världsdata för v2: meta.json + höjdkarta (1 m, rå LiDAR) ur tools/build_v2.py.
// Projektionen är exakt v1:s (lat/lon-linjär, meter, z positiv = söder) — se ARKITEKTUR.md.
import * as THREE from 'three';

export interface Meta {
  version: number;
  x0: number; x1: number; z0: number; z1: number;   // väst, öst, syd (z+), norr (z−)
  exag: number;
  height: { file: string; w: number; h: number; offsetM: number; scale: number };
  classmap: { file: string; w: number; h: number };
  ortho: Record<string, { w: number; h: number }>;
  attribution: string[];
}

export const DATA_URL = `${import.meta.env.BASE_URL}data/`;

// v1:s spawn (högsta gröna fläcken): data.js "spawn":[447.2,53.0]
export const SPAWN: [number, number] = [447.2, 53.0];

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`kunde inte ladda ${url}`));
    img.src = url;
  });
}

export class World {
  meta: Meta;
  /** rå höjd (m ö.h., FÖRE överdrift) i 1 m-grid, rad 0 = norr (z1) */
  raw: Float32Array;
  w: number; h: number;
  readonly exag: number;
  private readonly sx: number; private readonly sz: number;   // grid-celler per meter

  private constructor(meta: Meta, raw: Float32Array) {
    this.meta = meta; this.raw = raw;
    this.w = meta.height.w; this.h = meta.height.h;
    this.exag = meta.exag;
    this.sx = (this.w - 1) / (meta.x1 - meta.x0);
    this.sz = (this.h - 1) / (meta.z0 - meta.z1);
  }

  static async load(progress: (s: string) => void = () => {}): Promise<World> {
    progress('laddar meta.json …');
    const meta = (await (await fetch(`${DATA_URL}meta.json`)).json()) as Meta;
    progress(`laddar höjdkarta ${meta.height.w}×${meta.height.h} …`);
    const img = await loadImage(`${DATA_URL}${meta.height.file}`);
    const { w, h, offsetM, scale } = meta.height;
    if (img.width !== w || img.height !== h) throw new Error(`height.png är ${img.width}×${img.height}, meta säger ${w}×${h}`);
    const cv = document.createElement('canvas');
    cv.width = w; cv.height = h;
    const ctx = cv.getContext('2d', { willReadFrequently: true })!;
    ctx.drawImage(img, 0, 0);
    const px = ctx.getImageData(0, 0, w, h).data;
    const raw = new Float32Array(w * h);
    let lo = Infinity, hi = -Infinity;
    for (let i = 0, j = 0; i < raw.length; i++, j += 4) {
      const v = (px[j] * 256 + px[j + 1]) / scale - offsetM;
      raw[i] = v;
      if (v < lo) lo = v; if (v > hi) hi = v;
    }
    progress(`höjdkarta ${lo.toFixed(1)}–${hi.toFixed(1)} m`);
    return new World(meta, raw);
  }

  /** rå LiDAR-höjd (m ö.h.) bilinjärt — motsvarar v1:s origHeightAt/EXAG */
  rawAt(x: number, z: number): number {
    const m = this.meta;
    const fx = (x - m.x0) * this.sx, fz = (z - m.z1) * this.sz;
    const c = Math.max(0, Math.min(this.w - 2, Math.floor(fx)));
    const r = Math.max(0, Math.min(this.h - 2, Math.floor(fz)));
    const tx = Math.min(1, Math.max(0, fx - c)), tz = Math.min(1, Math.max(0, fz - r));
    const a = this.raw, i = r * this.w + c;
    return (a[i] * (1 - tx) + a[i + 1] * tx) * (1 - tz) + (a[i + this.w] * (1 - tx) + a[i + this.w + 1] * tx) * tz;
  }

  /** spelhöjd = rå × EXAG (1,2) — samma som v1:s heightAt före åfåre-nedskärningen */
  heightAt(x: number, z: number): number { return this.rawAt(x, z) * this.exag; }

  /** ytnormal ur höjdfältet (centrala differenser 1 m, med överdrift) */
  normalAt(x: number, z: number, out: THREE.Vector3): THREE.Vector3 {
    const dx = this.heightAt(x + 1, z) - this.heightAt(x - 1, z);
    const dz = this.heightAt(x, z + 1) - this.heightAt(x, z - 1);
    return out.set(-dx * 0.5, 1, -dz * 0.5).normalize();
  }

  inside(x: number, z: number, margin = 0): boolean {
    const m = this.meta;
    return x >= m.x0 + margin && x <= m.x1 - margin && z >= m.z1 + margin && z <= m.z0 - margin;
  }
}
