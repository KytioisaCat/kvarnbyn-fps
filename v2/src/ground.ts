// Procedurella markdetaljtexturer (512 px ≈ 2,6 m), porterade från v1 (public/game.js) där
// receptet är kalibrerat: stora mjuka tonfläckar i flera skalor + finkorn + karaktärsinslag
// (strån, löv, stenar, sprickor). Inga nedladdningar — genereras på canvas vid start.
// Riktiga PBR-texturer (ambientCG, CC0) kan ersätta dessa när Joel har nät.
import * as THREE from 'three';

type Ctx = CanvasRenderingContext2D;

function groundCanvas(base: string, size = 512): [HTMLCanvasElement, Ctx] {
  const cv = document.createElement('canvas'); cv.width = cv.height = size;
  const c = cv.getContext('2d')!;
  c.fillStyle = base; c.fillRect(0, 0, size, size);
  return [cv, c];
}
// mjuka tonfläckar; fläckar som korsar kanten ritas wrappat så texturen förblir sömlös
function blotch(c: Ctx, n: number, rMin: number, rMax: number, colFn: () => string, aMax: number, size = 512) {
  for (let i = 0; i < n; i++) {
    const x = Math.random() * size, y = Math.random() * size;
    const r = rMin + Math.random() * (rMax - rMin);
    const col = colFn(), al = (0.35 + Math.random() * 0.65) * aMax;
    for (const ox of (x - r < 0 || x + r > size) ? [0, x < size / 2 ? size : -size] : [0])
      for (const oy of (y - r < 0 || y + r > size) ? [0, y < size / 2 ? size : -size] : [0]) {
        const g = c.createRadialGradient(x + ox, y + oy, 0, x + ox, y + oy, r);
        g.addColorStop(0, `rgba(${col},${al.toFixed(3)})`);
        g.addColorStop(1, `rgba(${col},0)`);
        c.fillStyle = g;
        c.fillRect(x + ox - r, y + oy - r, r * 2, r * 2);
      }
  }
}
function speckle(c: Ctx, n: number, vFn: () => string, aMax: number, sMax = 2, size = 512) {
  for (let i = 0; i < n; i++) {
    c.fillStyle = `rgba(${vFn()},${(0.25 + Math.random() * 0.75) * aMax})`;
    c.fillRect(Math.random() * size, Math.random() * size, 1 + Math.random() * (sMax - 1), 1 + Math.random() * (sMax - 1));
  }
}
function cracks(c: Ctx, n: number, style: string, size = 512) {
  for (let i = 0; i < n; i++) {
    c.strokeStyle = style; c.lineWidth = 1 + Math.random();
    let x = Math.random() * size, y = Math.random() * size;
    c.beginPath(); c.moveTo(x, y);
    for (let s = 0; s < 7; s++) { x += (Math.random() - 0.5) * 70; y += (Math.random() - 0.5) * 70; c.lineTo(x, y); }
    c.stroke();
  }
}
function toGroundTex(cv: HTMLCanvasElement, anisotropy: number): THREE.CanvasTexture {
  const t = new THREE.CanvasTexture(cv);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = anisotropy;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  return t;
}
const gray = (lo: number, hi: number) => { const v = (lo + Math.random() * (hi - lo)) | 0; return `${v},${v},${v}`; };

export interface GroundTextures {
  asphalt: THREE.Texture; grass: THREE.Texture; forest: THREE.Texture; rock: THREE.Texture; macro: THREE.Texture;
}

export function makeGroundTextures(anisotropy = 4): GroundTextures {
  const asphalt = (() => {
    const [cv, c] = groundCanvas('#a9abae');
    blotch(c, 24, 90, 210, () => gray(Math.random() < 0.5 ? 128 : 178, Math.random() < 0.5 ? 148 : 196), 0.30); // väderfläckar/lagningar
    blotch(c, 70, 22, 70, () => gray(132, 192), 0.22);
    speckle(c, 26000, () => gray(128, 205), 0.5, 2);   // ballastkorn
    speckle(c, 1200, () => gray(180, 215), 0.5, 2);    // ljusa stenar
    cracks(c, 6, 'rgba(52,52,54,0.35)');
    return toGroundTex(cv, anisotropy);
  })();
  const grass = (() => {
    const [cv, c] = groundCanvas('#83955e');
    blotch(c, 26, 80, 190, () => Math.random() < 0.45 ? '148,146,88' : '72,98,52', 0.32); // torrfläckar/frodigt
    blotch(c, 80, 18, 55, () => Math.random() < 0.5 ? '128,134,74' : '84,110,58', 0.25);
    for (let i = 0; i < 16000; i++) { // grässtrån
      const g = 122 + Math.random() * 84, r = g * (0.68 + Math.random() * 0.24), b = g * 0.46;
      c.strokeStyle = `rgba(${r | 0},${g | 0},${b | 0},${0.35 + Math.random() * 0.3})`;
      c.lineWidth = 1;
      const x = Math.random() * 512, y = Math.random() * 512;
      c.beginPath(); c.moveTo(x, y);
      c.lineTo(x + (Math.random() - 0.5) * 4, y - 3 - Math.random() * 5);
      c.stroke();
    }
    blotch(c, 16, 12, 34, () => '96,82,58', 0.30);    // jordfläckar
    for (let i = 0; i < 70; i++) { // vårblommor (maskros/vitsippa — fotot är vårtaget)
      c.fillStyle = Math.random() < 0.6 ? 'rgba(238,214,90,0.6)' : 'rgba(235,238,225,0.55)';
      c.beginPath(); c.arc(Math.random() * 512, Math.random() * 512, 1 + Math.random() * 1.4, 0, 7); c.fill();
    }
    return toGroundTex(cv, anisotropy);
  })();
  const forest = (() => {
    const [cv, c] = groundCanvas('#6b614c');
    blotch(c, 24, 70, 180, () => Math.random() < 0.5 ? '44,40,30' : '112,96,66', 0.35); // humus/barrmattor
    blotch(c, 60, 18, 60, () => '90,78,52', 0.25);
    for (let i = 0; i < 9000; i++) { // barr
      c.strokeStyle = `rgba(${96 + Math.random() * 60 | 0},${70 + Math.random() * 40 | 0},${34 + Math.random() * 20 | 0},${0.3 + Math.random() * 0.3})`;
      c.lineWidth = 1;
      const x = Math.random() * 512, y = Math.random() * 512, a = Math.random() * 6.28;
      c.beginPath(); c.moveTo(x, y); c.lineTo(x + Math.cos(a) * (4 + Math.random() * 6), y + Math.sin(a) * (4 + Math.random() * 6)); c.stroke();
    }
    for (let i = 0; i < 1100; i++) { // fjolårslöv
      const r = 120 + Math.random() * 70;
      c.fillStyle = `rgba(${r | 0},${r * (0.55 + Math.random() * 0.2) | 0},${r * 0.3 | 0},${0.3 + Math.random() * 0.3})`;
      c.beginPath();
      c.ellipse(Math.random() * 512, Math.random() * 512, 1.6 + Math.random() * 2.4, 1 + Math.random() * 1.6, Math.random() * 3.14, 0, 7);
      c.fill();
    }
    blotch(c, 22, 14, 45, () => '86,116,58', 0.30);   // mossa
    for (let i = 0; i < 70; i++) { // kvistar
      c.strokeStyle = 'rgba(58,46,32,0.5)'; c.lineWidth = 1 + Math.random();
      const x = Math.random() * 512, y = Math.random() * 512, a = Math.random() * 6.28;
      c.beginPath(); c.moveTo(x, y); c.lineTo(x + Math.cos(a) * (10 + Math.random() * 16), y + Math.sin(a) * (10 + Math.random() * 16)); c.stroke();
    }
    return toGroundTex(cv, anisotropy);
  })();
  const rock = (() => {
    const [cv, c] = groundCanvas('#a7a6a1');
    blotch(c, 20, 80, 200, () => gray(Math.random() < 0.5 ? 110 : 150, Math.random() < 0.5 ? 130 : 170), 0.30);
    speckle(c, 20000, () => gray(128, 208), 0.5, 3);  // granitkorn
    cracks(c, 9, 'rgba(48,48,46,0.5)');
    blotch(c, 26, 10, 40, () => '104,128,64', 0.30);  // mossa i skrevorna
    for (let i = 0; i < 320; i++) { // lav
      c.fillStyle = `rgba(${190 + Math.random() * 40 | 0},${190 + Math.random() * 40 | 0},${170 + Math.random() * 30 | 0},0.35)`;
      c.beginPath(); c.arc(Math.random() * 512, Math.random() * 512, 1 + Math.random() * 2.4, 0, 7); c.fill();
    }
    return toGroundTex(cv, anisotropy);
  })();
  // makrobrus: låg frekvens som moduleras in på ~45 m-skalan för att döda tiling-mönstret
  const macro = (() => {
    const [cv, c] = groundCanvas('#808080', 256);
    blotch(c, 46, 40, 120, () => gray(96, 164), 0.5, 256);
    blotch(c, 90, 12, 45, () => gray(104, 152), 0.35, 256);
    const t = toGroundTex(cv, anisotropy);
    t.colorSpace = THREE.NoColorSpace;
    return t;
  })();
  return { asphalt, grass, forest, rock, macro };
}
