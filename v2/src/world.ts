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

const MB = (n: number) => (n / 1048576).toFixed(1);

/** hämta en fil med förlopp i MB (så ett långsamt mobilnät syns i statusraden) */
export async function fetchBlob(url: string, label: string, progress: (s: string) => void): Promise<Blob> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${label}: HTTP ${res.status}`);
  const total = Number(res.headers.get('content-length') || 0);
  if (!res.body) { progress(`laddar ${label} …`); return res.blob(); }
  const reader = res.body.getReader();
  const chunks: Uint8Array[] = [];
  let got = 0, lastShown = -1;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); got += value.length;
    const shown = Math.floor(got / 262144);
    if (shown !== lastShown) { lastShown = shown; progress(`laddar ${label} ${MB(got)}${total ? ` / ${MB(total)}` : ''} MB`); }
  }
  return new Blob(chunks as BlobPart[]);
}

/** bild via fetch (förlopp) + <img> (fungerar i alla mobilwebbläsare) */
export async function loadImage(url: string, label: string, progress: (s: string) => void): Promise<HTMLImageElement> {
  const blob = await fetchBlob(url, label, progress);
  progress(`avkodar ${label} …`);
  const objUrl = URL.createObjectURL(blob);
  try {
    return await new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error(`${label}: kunde inte avkoda bilden (${MB(blob.size)} MB)`));
      img.src = objUrl;
    });
  } finally {
    // objekt-URL:en frigörs först när bilden är använd — anroparen behåller img
  }
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
    const metaRes = await fetch(`${DATA_URL}meta.json`);
    if (!metaRes.ok) throw new Error(`meta.json: HTTP ${metaRes.status}`);
    const meta = (await metaRes.json()) as Meta;
    const img = await loadImage(`${DATA_URL}${meta.height.file}`, 'höjdkarta', progress);
    const { w, h, offsetM, scale } = meta.height;
    progress(`läser höjdkarta ${w}×${h} …`);
    await new Promise((r) => setTimeout(r, 0));   // låt statusraden ritas innan den tunga loopen
    if (img.width !== w || img.height !== h) throw new Error(`height.png är ${img.width}×${img.height}, meta säger ${w}×${h}`);
    const cv = document.createElement('canvas');
    cv.width = w; cv.height = h;
    const ctx = cv.getContext('2d', { willReadFrequently: true });
    if (!ctx) throw new Error(`canvas ${w}×${h} gick inte att skapa (minne?)`);
    ctx.drawImage(img, 0, 0);
    const px = ctx.getImageData(0, 0, w, h).data;
    URL.revokeObjectURL(img.src);
    cv.width = cv.height = 1;   // släpp canvasminnet (28 MB) direkt
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
