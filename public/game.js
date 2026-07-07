import * as THREE from './three.module.js';

const D = window.KVARNBYN_DATA;
const T = D.terrain;

// ---------- helpers ----------
function lerp(a, b, t) { return a + (b - a) * t; }

// vertical exaggeration — makes the real slopes feel as steep as they do on a bike
const EXAG = 1.5;

function bilinear(arr, x, z) {
  const fx = (x - T.x0) / (T.x1 - T.x0) * (T.cols - 1);
  const fz = (z - T.z0) / (T.z1 - T.z0) * (T.rows - 1);
  const c = Math.max(0, Math.min(T.cols - 2, Math.floor(fx)));
  const r = Math.max(0, Math.min(T.rows - 2, Math.floor(fz)));
  const tx = Math.min(1, Math.max(0, fx - c)), tz = Math.min(1, Math.max(0, fz - r));
  const E = (rr, cc) => arr[rr * T.cols + cc];
  return ((E(r, c) * (1 - tx) + E(r, c + 1) * tx) * (1 - tz) +
          (E(r + 1, c) * (1 - tx) + E(r + 1, c + 1) * tx) * tz) * EXAG;
}

// urspungsterrängen (före åfåre-nedskärningen) — broar/vägar/vattenyta refererar hit
const origElev = Float64Array.from(T.elev);
function heightAt(x, z) { return bilinear(T.elev, x, z); }
function origHeightAt(x, z) { return bilinear(origElev, x, z); }

function inBounds(x, z, m = 0) {
  return x >= T.x0 - m && x <= T.x1 + m && z >= T.z1 - m && z <= T.z0 + m;
}

// Sutherland–Hodgman clip of a polygon to the map rectangle
function clipPolyToMap(poly) {
  const edges = [
    p => p[0] >= T.x0, p => p[0] <= T.x1,
    p => p[1] >= T.z1, p => p[1] <= T.z0
  ];
  const inter = [
    (a, b) => { const t = (T.x0 - a[0]) / (b[0] - a[0]); return [T.x0, a[1] + t * (b[1] - a[1])]; },
    (a, b) => { const t = (T.x1 - a[0]) / (b[0] - a[0]); return [T.x1, a[1] + t * (b[1] - a[1])]; },
    (a, b) => { const t = (T.z1 - a[1]) / (b[1] - a[1]); return [a[0] + t * (b[0] - a[0]), T.z1]; },
    (a, b) => { const t = (T.z0 - a[1]) / (b[1] - a[1]); return [a[0] + t * (b[0] - a[0]), T.z0]; }
  ];
  let out = poly;
  for (let e = 0; e < 4; e++) {
    const inp = out; out = [];
    for (let i = 0; i < inp.length; i++) {
      const cur = inp[i], prev = inp[(i + inp.length - 1) % inp.length];
      const cIn = edges[e](cur), pIn = edges[e](prev);
      if (cIn) { if (!pIn) out.push(inter[e](prev, cur)); out.push(cur); }
      else if (pIn) out.push(inter[e](prev, cur));
    }
    if (out.length < 3) return null;
  }
  return out;
}

function pointInPoly(x, z, poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const xi = poly[i][0], zi = poly[i][1], xj = poly[j][0], zj = poly[j][1];
    if (((zi > z) !== (zj > z)) && (x < (xj - xi) * (z - zi) / (zj - zi) + xi)) inside = !inside;
  }
  return inside;
}

function mergeGeoms(geoms) {
  let vCount = 0;
  for (const g of geoms) vCount += g.attributes.position.count;
  const hasUV = geoms.length > 0 && geoms.every(g => g.attributes.uv);
  const pos = new Float32Array(vCount * 3), nor = new Float32Array(vCount * 3), col = new Float32Array(vCount * 3);
  const uv = hasUV ? new Float32Array(vCount * 2) : null;
  let o = 0;
  for (const g of geoms) {
    pos.set(g.attributes.position.array, o * 3);
    nor.set(g.attributes.normal.array, o * 3);
    col.set(g.attributes.color.array, o * 3);
    if (uv) uv.set(g.attributes.uv.array, o * 2);
    o += g.attributes.position.count;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  out.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  out.setAttribute('color', new THREE.BufferAttribute(col, 3));
  if (uv) out.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  return out;
}

function paintGeom(g, color) {
  const n = g.attributes.position.count;
  const col = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { col[i * 3] = color.r; col[i * 3 + 1] = color.g; col[i * 3 + 2] = color.b; }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
}

// ---------- renderer / scene ----------
const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xb8d0e8);
scene.fog = new THREE.FogExp2(0xb8d0e8, 0.00065);

const camera = new THREE.PerspectiveCamera(72, innerWidth / innerHeight, 0.1, 3000);
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

scene.add(new THREE.HemisphereLight(0xe8eef5, 0x77776a, 0.55));
const sun = new THREE.DirectionalLight(0xfff4dd, 0.85);
sun.position.set(300, 500, 200);
scene.add(sun);

// ---------- forsen: skär ner åfåran i terrängen ----------
const CELL = 24; // spatial hash-cellstorlek (delas av alla hashar)
const riverSegs = []; // {ax,az,bx,bz,fx,fz (strömriktning), steep, minX..maxZ}
const riverHash = new Map();
{
  for (const w of D.water) {
    if (w.poly) continue;
    for (let i = 0; i < w.p.length - 1; i++) {
      const [ax, az] = w.p[i], [bx, bz] = w.p[i + 1];
      if (!inBounds(ax, az, 10) || !inBounds(bx, bz, 10)) continue;
      const len = Math.hypot(bx - ax, bz - az); if (len < 0.5) continue;
      const ya = origHeightAt(ax, az), yb = origHeightAt(bx, bz);
      const f = yb < ya ? [(bx - ax) / len, (bz - az) / len] : [(ax - bx) / len, (az - bz) / len];
      riverSegs.push({ ax, az, bx, bz, fx: f[0], fz: f[1], steep: Math.abs(ya - yb) / len > 0.09,
        minX: Math.min(ax, bx), maxX: Math.max(ax, bx), minZ: Math.min(az, bz), maxZ: Math.max(az, bz) });
    }
  }
  const CARVE_W = 9, DEPTH_RAW = 3.0 / EXAG; // ~3 m djup fåra i världskoordinater
  const lower = new Float64Array(T.elev.length);
  const zToRow = z => (z - T.z0) / (T.z1 - T.z0) * (T.rows - 1);
  const xToCol = x => (x - T.x0) / (T.x1 - T.x0) * (T.cols - 1);
  for (const s of riverSegs) {
    const r1 = Math.max(0, Math.floor(Math.min(zToRow(s.minZ - CARVE_W), zToRow(s.maxZ + CARVE_W))));
    const r2 = Math.min(T.rows - 1, Math.ceil(Math.max(zToRow(s.minZ - CARVE_W), zToRow(s.maxZ + CARVE_W))));
    const c1 = Math.max(0, Math.floor(xToCol(s.minX - CARVE_W)));
    const c2 = Math.min(T.cols - 1, Math.ceil(xToCol(s.maxX + CARVE_W)));
    const abx = s.bx - s.ax, abz = s.bz - s.az, ab2 = abx * abx + abz * abz || 1;
    for (let r = r1; r <= r2; r++) {
      const z = lerp(T.z0, T.z1, r / (T.rows - 1));
      for (let c = c1; c <= c2; c++) {
        const x = lerp(T.x0, T.x1, c / (T.cols - 1));
        const t = Math.max(0, Math.min(1, ((x - s.ax) * abx + (z - s.az) * abz) / ab2));
        const d = Math.hypot(x - (s.ax + abx * t), z - (s.az + abz * t));
        if (d < CARVE_W) {
          const u = 1 - d / CARVE_W, f = u * u * (3 - 2 * u); // smoothstep-falloff
          const i = r * T.cols + c;
          if (DEPTH_RAW * f > lower[i]) lower[i] = DEPTH_RAW * f;
        }
      }
    }
  }
  // hash för närhets-frågor (ström, simning, ljud)
  riverSegs.forEach((s, idx) => {
    for (let cx = Math.floor((s.minX - CARVE_W) / CELL); cx <= Math.floor((s.maxX + CARVE_W) / CELL); cx++)
      for (let cz = Math.floor((s.minZ - CARVE_W) / CELL); cz <= Math.floor((s.maxZ + CARVE_W) / CELL); cz++) {
        const k = cx + ':' + cz;
        if (!riverHash.has(k)) riverHash.set(k, []);
        riverHash.get(k).push(idx);
      }
  });
  for (let i = 0; i < T.elev.length; i++) T.elev[i] -= lower[i];
}

function nearestRiver(x, z) {
  const cx = Math.floor(x / CELL), cz = Math.floor(z / CELL);
  let best = null, bd = Infinity;
  for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) {
    const arr = riverHash.get((cx + dx) + ':' + (cz + dz));
    if (!arr) continue;
    for (const i of arr) {
      const s = riverSegs[i];
      const abx = s.bx - s.ax, abz = s.bz - s.az;
      const t = Math.max(0, Math.min(1, ((x - s.ax) * abx + (z - s.az) * abz) / (abx * abx + abz * abz || 1)));
      const d = Math.hypot(x - (s.ax + abx * t), z - (s.az + abz * t));
      if (d < bd) { bd = d; best = s; }
    }
  }
  return best ? { d: bd, seg: best } : null;
}

// ---------- terrain (draped with satellite orthophoto) ----------
const orthoTex = new THREE.TextureLoader().load('ortho.jpg?v=3');
orthoTex.colorSpace = THREE.SRGBColorSpace;
orthoTex.anisotropy = 8;

const terrainGeom = new THREE.BufferGeometry();
{
  const pos = new Float32Array(T.rows * T.cols * 3);
  const uv = new Float32Array(T.rows * T.cols * 2);
  for (let r = 0; r < T.rows; r++) {
    for (let c = 0; c < T.cols; c++) {
      const i = r * T.cols + c;
      const x = lerp(T.x0, T.x1, c / (T.cols - 1));
      const z = lerp(T.z0, T.z1, r / (T.rows - 1));
      pos[i * 3] = x; pos[i * 3 + 1] = T.elev[i] * EXAG; pos[i * 3 + 2] = z;
      uv[i * 2] = (x - T.x0) / (T.x1 - T.x0);
      uv[i * 2 + 1] = (z - T.z0) / (T.z1 - T.z0); // z0=south → v=0 at south
    }
  }
  const idx = [];
  for (let r = 0; r < T.rows - 1; r++) for (let c = 0; c < T.cols - 1; c++) {
    const a = r * T.cols + c, b = a + 1, cI = a + T.cols, dI = cI + 1;
    idx.push(a, b, cI, b, dI, cI); // CCW seen from above (+Y normals)
  }
  terrainGeom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  terrainGeom.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  terrainGeom.setIndex(idx);
  terrainGeom.computeVertexNormals();
}
// Basic material: the aerial photo has real-world lighting baked in already
const terrainMesh = new THREE.Mesh(terrainGeom, new THREE.MeshBasicMaterial({ map: orthoTex }));
scene.add(terrainMesh);

// ---------- roads (draped ribbons) ----------
function ribbonGeom(pts, w, lift, color, opts = {}) {
  const hFn = opts.heightFn || heightAt;
  const positions = [], colors = [], normals = [], uvs = [];
  let vAcc = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const [x1, z1] = pts[i], [x2, z2] = pts[i + 1];
    if (!inBounds(x1, z1, 15) || !inBounds(x2, z2, 15)) continue;
    let dx = x2 - x1, dz = z2 - z1;
    const len = Math.hypot(dx, dz); if (len < 0.01) continue;
    dx /= len; dz /= len;
    const px = -dz * w / 2, pz = dx * w / 2;
    const y11 = hFn(x1 - px, z1 - pz) + lift, y12 = hFn(x1 + px, z1 + pz) + lift;
    const y21 = hFn(x2 - px, z2 - pz) + lift, y22 = hFn(x2 + px, z2 + pz) + lift;
    const v0 = vAcc / 6, v1 = (vAcc + len) / 6;
    vAcc += len;
    const quad = [
      [x1 - px, y11, z1 - pz, 0, v0], [x1 + px, y12, z1 + pz, 1, v0], [x2 - px, y21, z2 - pz, 0, v1],
      [x1 + px, y12, z1 + pz, 1, v0], [x2 + px, y22, z2 + pz, 1, v1], [x2 - px, y21, z2 - pz, 0, v1]
    ];
    const segCol = (opts.colorFn ? opts.colorFn(i) : color);
    for (const v of quad) {
      positions.push(v[0], v[1], v[2]); normals.push(0, 1, 0);
      colors.push(segCol.r, segCol.g, segCol.b); uvs.push(v[3], v[4]);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3));
  g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(normals), 3));
  g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(colors), 3));
  if (opts.uv) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(uvs), 2));
  return g;
}
// roadSegs: gångbara däck (broar över åfåran) + snabbare rörelse på väg än i terräng
const roadSegs = [];
const roadHash = new Map();
{
  const geoms = [], shoulderGeoms = [], dashGeoms = [];
  const cRoad = new THREE.Color(0x33363a), cFoot = new THREE.Color(0x8a8072), cSteps = new THREE.Color(0x9d8c72),
        cShoulder = new THREE.Color(0xa6aab0), cDash = new THREE.Color(0xd8d8d0);
  const hOpts = { heightFn: origHeightAt };
  for (const rd of D.roads) {
    let color = cRoad, lift = 0.16;
    const soft = rd.k === 'footway' || rd.k === 'path' || rd.k === 'cycleway' || rd.k === 'track';
    if (soft) { color = cFoot; lift = 0.13; }
    else if (rd.k === 'steps') { color = cSteps; lift = 0.22; }
    geoms.push(ribbonGeom(rd.p, rd.w, lift, color, hOpts));
    if (!soft && rd.k !== 'steps') {
      // ljus vägren gör gatan tydlig mot gräset
      shoulderGeoms.push(ribbonGeom(rd.p, rd.w + 0.9, lift - 0.03, cShoulder, hOpts));
      // mittlinje (streckad) på de större gatorna
      if (rd.w >= 7) {
        let acc = 0;
        for (let i = 0; i < rd.p.length - 1; i++) {
          const [x1, z1] = rd.p[i], [x2, z2] = rd.p[i + 1];
          const len = Math.hypot(x2 - x1, z2 - z1); if (len < 0.5) continue;
          const dx = (x2 - x1) / len, dz = (z2 - z1) / len;
          let s = 0;
          while (s < len) {
            const phase = (acc + s) % 9;
            const dashLeft = phase < 3 ? Math.min(3 - phase, len - s) : 0;
            if (dashLeft > 0.3) {
              dashGeoms.push(ribbonGeom(
                [[x1 + dx * s, z1 + dz * s], [x1 + dx * (s + dashLeft), z1 + dz * (s + dashLeft)]],
                0.2, lift + 0.02, cDash, hOpts));
            }
            s += dashLeft > 0 ? dashLeft : Math.min(9 - phase, len - s);
          }
          acc += len;
        }
      }
    }
    // gångbara däck-segment (för broar och vägkänning)
    for (let i = 0; i < rd.p.length - 1; i++) {
      const [ax, az] = rd.p[i], [bx, bz] = rd.p[i + 1];
      if (!inBounds(ax, az, 15) || !inBounds(bx, bz, 15)) continue;
      if (Math.hypot(bx - ax, bz - az) < 0.3) continue;
      const seg = { ax, az, bx, bz, hw: rd.w / 2, ya: origHeightAt(ax, az) + 0.16, yb: origHeightAt(bx, bz) + 0.16 };
      const idx = roadSegs.length;
      roadSegs.push(seg);
      for (let cx = Math.floor((Math.min(ax, bx) - 6) / CELL); cx <= Math.floor((Math.max(ax, bx) + 6) / CELL); cx++)
        for (let cz = Math.floor((Math.min(az, bz) - 6) / CELL); cz <= Math.floor((Math.max(az, bz) + 6) / CELL); cz++) {
          const k = cx + ':' + cz;
          if (!roadHash.has(k)) roadHash.set(k, []);
          roadHash.get(k).push(idx);
        }
    }
  }
  const mSh = new THREE.Mesh(mergeGeoms(shoulderGeoms), new THREE.MeshLambertMaterial({ vertexColors: true, transparent: true, opacity: 0.5, depthWrite: false }));
  mSh.renderOrder = 1;
  scene.add(mSh);
  const m = new THREE.Mesh(mergeGeoms(geoms), new THREE.MeshLambertMaterial({ vertexColors: true, transparent: true, opacity: 0.55, depthWrite: false }));
  m.renderOrder = 2;
  scene.add(m);
  const mDash = new THREE.Mesh(mergeGeoms(dashGeoms), new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.6, depthWrite: false }));
  mDash.renderOrder = 3;
  scene.add(mDash);
}

// mark-info: carved terräng + ev. vägdäck ovanpå (broar!) + är vi på väg?
function groundInfoAt(x, z) {
  let y = heightAt(x, z), road = false;
  const cx = Math.floor(x / CELL), cz = Math.floor(z / CELL);
  const arr = roadHash.get(cx + ':' + cz);
  if (arr) {
    for (const i of arr) {
      const s = roadSegs[i];
      const abx = s.bx - s.ax, abz = s.bz - s.az;
      const t = Math.max(0, Math.min(1, ((x - s.ax) * abx + (z - s.az) * abz) / (abx * abx + abz * abz || 1)));
      const d = Math.hypot(x - (s.ax + abx * t), z - (s.az + abz * t));
      if (d < s.hw + 0.5) {
        road = true;
        const dy = s.ya + (s.yb - s.ya) * t;
        if (dy > y + 0.25) y = dy; // vägen ligger som ett däck över fåran
      }
    }
  }
  return { y, road };
}

// ---------- water ----------
// strömmande vatten-textur (offset animeras i renderloopen → flöde)
const waterTex = (() => {
  const cv = document.createElement('canvas'); cv.width = 64; cv.height = 256;
  const c = cv.getContext('2d');
  c.fillStyle = '#4a7899'; c.fillRect(0, 0, 64, 256);
  for (let i = 0; i < 46; i++) { // långsträckta strömlinjer
    c.fillStyle = 'rgba(150,190,215,' + (0.10 + Math.random() * 0.16) + ')';
    const x = Math.random() * 64, y = Math.random() * 256;
    c.fillRect(x, y, 1.5 + Math.random() * 2.5, 14 + Math.random() * 42);
  }
  for (let i = 0; i < 26; i++) { // skumfläckar
    c.fillStyle = 'rgba(235,244,250,' + (0.12 + Math.random() * 0.25) + ')';
    c.beginPath(); c.arc(Math.random() * 64, Math.random() * 256, 1 + Math.random() * 2.6, 0, 7); c.fill();
  }
  const tex = new THREE.CanvasTexture(cv);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
})();

{
  const cCalm = new THREE.Color(0.62, 0.78, 0.88), cFoam = new THREE.Color(1, 1, 1);
  const surfFn = (x, z) => origHeightAt(x, z) - 1.5; // vattenytan ~1,5 m under strandkanten
  const ribbonGeoms = [];
  for (const w of D.water) {
    if (w.poly) continue;
    const pts = w.p.filter(p => inBounds(p[0], p[1], 10));
    if (pts.length < 2) continue;
    const colorFn = (i) => {
      const [x1, z1] = pts[i], [x2, z2] = pts[Math.min(i + 1, pts.length - 1)];
      const len = Math.hypot(x2 - x1, z2 - z1) || 1;
      return Math.abs(origHeightAt(x2, z2) - origHeightAt(x1, z1)) / len > 0.09 ? cFoam : cCalm;
    };
    ribbonGeoms.push(ribbonGeom(pts, 9, 0, cCalm, { heightFn: surfFn, uv: true, colorFn }));
  }
  if (ribbonGeoms.length) {
    const m = new THREE.Mesh(mergeGeoms(ribbonGeoms),
      new THREE.MeshBasicMaterial({ map: waterTex, vertexColors: true, transparent: true, opacity: 0.88, depthWrite: false }));
    m.renderOrder = 2;
    scene.add(m);
  }
  // sjöar och dammar (slutna polygoner) — stilla ytor
  const polyGeoms = [];
  const cW = new THREE.Color(0x3d6a8f);
  for (const w of D.water) {
    if (!w.poly) continue;
    const clipped = clipPolyToMap(w.p);
    if (!clipped) continue;
    const shape = new THREE.Shape(clipped.map(p => new THREE.Vector2(p[0], -p[1])));
    let geo; try { geo = new THREE.ShapeGeometry(shape); } catch (e) { continue; }
    geo.rotateX(-Math.PI / 2);
    const pa = geo.attributes.position.array;
    for (let i = 0; i < pa.length; i += 3) pa[i + 1] = heightAt(pa[i], pa[i + 2]) + 0.15;
    geo.computeVertexNormals(); paintGeom(geo, cW); polyGeoms.push(geo);
  }
  if (polyGeoms.length) scene.add(new THREE.Mesh(mergeGeoms(polyGeoms), new THREE.MeshLambertMaterial({ vertexColors: true, transparent: true, opacity: 0.75 })));
}

// ---------- buildings: windowed walls + real roof colors from the orthophoto ----------
const bldPolys = []; // {poly, minX,maxX,minZ,maxZ, topY}
let buildingMesh, roofMesh;

// procedural facade textures: one tile = 3 m × 3 m of wall with a window
function makeFacadeTex(style) {
  const cv = document.createElement('canvas'); cv.width = 128; cv.height = 128;
  const c = cv.getContext('2d');
  c.fillStyle = '#f1eee6'; c.fillRect(0, 0, 128, 128);
  if (style === 'wood') {
    // vertical plank panelling, ~0.35 m per plank
    for (let x = 0; x < 128; x += 15) {
      c.fillStyle = 'rgba(0,0,0,0.10)'; c.fillRect(x, 0, 2, 128);
      c.fillStyle = 'rgba(255,255,255,0.10)'; c.fillRect(x + 2, 0, 2, 128);
    }
    for (let i = 0; i < 120; i++) { // wood grain
      c.fillStyle = 'rgba(90,70,40,' + (Math.random() * 0.04) + ')';
      c.fillRect(Math.random() * 128, Math.random() * 128, 2, 6 + Math.random() * 10);
    }
  } else {
    for (let i = 0; i < 350; i++) { // plaster grain
      c.fillStyle = 'rgba(0,0,0,' + (Math.random() * 0.035) + ')';
      c.fillRect(Math.random() * 128, Math.random() * 128, 2, 2);
    }
  }
  c.fillStyle = '#c9c4b8'; c.fillRect(38, 34, 52, 66);      // frame
  c.fillStyle = '#2e3a44'; c.fillRect(42, 38, 44, 58);      // glass
  c.fillStyle = 'rgba(180,200,215,0.5)'; c.fillRect(44, 40, 18, 24); // sky reflection
  c.fillStyle = '#c9c4b8'; c.fillRect(62, 38, 4, 58); c.fillRect(42, 64, 44, 4); // mullions
  c.fillStyle = 'rgba(0,0,0,0.16)'; c.fillRect(38, 98, 52, 5); // sill shadow
  const tex = new THREE.CanvasTexture(cv);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}
const facadeTexWood = makeFacadeTex('wood');
const facadeTexPlaster = makeFacadeTex('plaster');

// white wood/plaster palette — Kvarnbyn per Joels minne
const WHITES = [0xf7f4ec, 0xf2efe6, 0xefe9db, 0xf5f2ea, 0xece7d8, 0xf2f1ea, 0xe9e6da];
const ACCENTS = [0xf0e3b4, 0xe4dcc6, 0xdcdcd2]; // pale yellow / sand / light grey
function wallColorFor(b) {
  if (b.t === 'garage' || b.t === 'garages' || b.t === 'shed' || b.t === 'carport')
    return new THREE.Color(0x9a958a);
  const seed = Math.abs(Math.sin(b.p[0][0] * 13.7 + b.p[0][1] * 7.3));
  if (seed < 0.85) return new THREE.Color(WHITES[Math.floor(seed * 100) % WHITES.length]);
  return new THREE.Color(ACCENTS[Math.floor(seed * 100) % ACCENTS.length]);
}

// oriented minimum-area bounding rectangle (rotating calipers over the convex hull)
function minAreaRect(poly) {
  const pts = poly.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower = [];
  for (const p of pts) { while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop(); lower.push(p); }
  const upper = [];
  for (let i = pts.length - 1; i >= 0; i--) { const p = pts[i]; while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop(); upper.push(p); }
  const hull = lower.slice(0, -1).concat(upper.slice(0, -1));
  if (hull.length < 3) return null;
  let best = null;
  for (let i = 0; i < hull.length; i++) {
    const a = hull[i], b = hull[(i + 1) % hull.length];
    const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
    const c = Math.cos(ang), s = Math.sin(ang);
    let minU = 1e12, maxU = -1e12, minV = 1e12, maxV = -1e12;
    for (const p of hull) {
      const u = p[0] * c + p[1] * s, v = -p[0] * s + p[1] * c;
      if (u < minU) minU = u; if (u > maxU) maxU = u;
      if (v < minV) minV = v; if (v > maxV) maxV = v;
    }
    const area = (maxU - minU) * (maxV - minV);
    if (!best || area < best.area) {
      best = { area, corners: [
        [minU * c - minV * s, minU * s + minV * c],
        [maxU * c - minV * s, maxU * s + minV * c],
        [maxU * c - maxV * s, maxU * s + maxV * c],
        [minU * c - maxV * s, minU * s + maxV * c]] };
    }
  }
  return best;
}

{
  const wallGeomsWood = [], wallGeomsPlaster = [], roofGeoms = [];
  for (const b of D.buildings) {
    let poly = b.p.slice();
    // drop duplicate consecutive points
    poly = poly.filter((p, i) => {
      const q = poly[(i + poly.length - 1) % poly.length];
      return i === 0 || Math.hypot(p[0] - q[0], p[1] - q[1]) > 0.3;
    });
    if (poly.length < 3) continue;
    if (!poly.some(p => inBounds(p[0], p[1], 5))) continue; // fully outside the map
    let rawArea = 0;
    for (let i = 0; i < poly.length; i++) {
      const p = poly[i], q = poly[(i + 1) % poly.length];
      rawArea += (p[0] * q[1] - q[0] * p[1]) / 2;
    }
    rawArea = Math.abs(rawArea);
    // Kvarnbyhusen är i grunden rektanglar — snappa nästan-rektangulära fotavtryck
    const rect = minAreaRect(poly);
    if (rect && rawArea / rect.area >= 0.68) poly = rect.corners;
    let minY = Infinity, minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity, area = 0;
    for (let i = 0; i < poly.length; i++) {
      const p = poly[i], q = poly[(i + 1) % poly.length];
      minY = Math.min(minY, heightAt(p[0], p[1]));
      minX = Math.min(minX, p[0]); maxX = Math.max(maxX, p[0]);
      minZ = Math.min(minZ, p[1]); maxZ = Math.max(maxZ, p[1]);
      area += (p[0] * q[1] - q[0] * p[1]) / 2;
    }
    area = Math.abs(area);
    const h = b.h * 1.2; // slight boost to match the exaggerated terrain
    const base = minY - 2, eave = minY + h;
    const roofCol = new THREE.Color('#' + (b.c || '9a8f80'));
    const wallCol = wallColorFor(b);
    const isWood = area < 350 && h < 10; // småhus: träpanel, större: puts
    const wallGeoms = isWood ? wallGeomsWood : wallGeomsPlaster;

    // --- walls ---
    const wPos = [], wNor = [], wCol = [], wUV = [];
    const isSmall = area < 45 || h < 4;
    for (let i = 0; i < poly.length; i++) {
      const p = poly[i], q = poly[(i + 1) % poly.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (len < 0.2) continue;
      const nx = (q[1] - p[1]) / len, nz = -(q[0] - p[0]) / len;
      const uMax = isSmall ? 0.28 : len / 3.2, vMax = isSmall ? 0.28 : h / 3.1;
      const quad = [
        [p[0], base, p[1], 0, 0], [q[0], base, q[1], uMax, 0], [q[0], eave, q[1], uMax, vMax],
        [p[0], base, p[1], 0, 0], [q[0], eave, q[1], uMax, vMax], [p[0], eave, p[1], 0, vMax]
      ];
      for (const v of quad) {
        wPos.push(v[0], v[1], v[2]); wNor.push(nx, 0, nz);
        wCol.push(wallCol.r, wallCol.g, wallCol.b); wUV.push(v[3], v[4]);
      }
    }

    // --- roof ---
    const rPos = [], rNor = [], rCol = [];
    const gabled = poly.length === 4 && area < 800 && h < 15;
    if (gabled) {
      // ridge along the longer opposite-edge pair
      const e0 = Math.hypot(poly[1][0] - poly[0][0], poly[1][1] - poly[0][1]);
      const e1 = Math.hypot(poly[2][0] - poly[1][0], poly[2][1] - poly[1][1]);
      const o = e0 >= e1 ? 0 : 1; // long edges: (o→o+1) and (o+2→o+3)
      const A = poly[o], B = poly[(o + 1) % 4], C = poly[(o + 2) % 4], E = poly[(o + 3) % 4];
      const shortLen = Math.min(Math.hypot(C[0] - B[0], C[1] - B[1]), Math.hypot(A[0] - E[0], A[1] - E[1]));
      const rise = Math.min(3.8, Math.max(1.6, shortLen * 0.32));
      const R1 = [(B[0] + C[0]) / 2, (B[1] + C[1]) / 2, eave + rise]; // over edge B-C
      const R2 = [(A[0] + E[0]) / 2, (A[1] + E[1]) / 2, eave + rise]; // over edge E-A
      const slope = [
        [A, B, R1, R2], // side 1: quad A,B,R1,R2
        [C, E, R2, R1]  // side 2
      ];
      for (const [P1, P2, T1, T2] of slope) {
        const tri = [
          [P1[0], eave, P1[1]], [P2[0], eave, P2[1]], [T1[0], T1[2], T1[1]],
          [P1[0], eave, P1[1]], [T1[0], T1[2], T1[1]], [T2[0], T2[2], T2[1]]
        ];
        const ux = tri[1][0] - tri[0][0], uy = tri[1][1] - tri[0][1], uz = tri[1][2] - tri[0][2];
        const vx = tri[2][0] - tri[0][0], vy = tri[2][1] - tri[0][1], vz = tri[2][2] - tri[0][2];
        let cx = uy * vz - uz * vy, cy = uz * vx - ux * vz, cz = ux * vy - uy * vx;
        const cl = Math.hypot(cx, cy, cz) || 1; cx /= cl; cy /= cl; cz /= cl;
        if (cy < 0) { cx = -cx; cy = -cy; cz = -cz; }
        for (const v of tri) { rPos.push(v[0], v[1], v[2]); rNor.push(cx, cy, cz); rCol.push(roofCol.r, roofCol.g, roofCol.b); }
      }
      // gable triangles (wall colour)
      for (const [Pa, Pb, R] of [[B, C, R1], [E, A, R2]]) {
        wPos.push(Pa[0], eave, Pa[1], Pb[0], eave, Pb[1], R[0], R[2], R[1]);
        const gnx = (Pb[1] - Pa[1]), gnz = -(Pb[0] - Pa[0]);
        const gl = Math.hypot(gnx, gnz) || 1;
        for (let k = 0; k < 3; k++) { wNor.push(gnx / gl, 0, gnz / gl); wCol.push(wallCol.r, wallCol.g, wallCol.b); wUV.push(0.28, 0.28); }
      }
    } else {
      // flat roof: triangulate footprint
      const v2 = poly.map(p => new THREE.Vector2(p[0], p[1]));
      let tris;
      try { tris = THREE.ShapeUtils.triangulateShape(v2, []); } catch (e) { tris = []; }
      for (const t of tris) {
        for (const vi of [t[0], t[2], t[1]]) {
          rPos.push(poly[vi][0], eave, poly[vi][1]);
          rNor.push(0, 1, 0);
          rCol.push(roofCol.r, roofCol.g, roofCol.b);
        }
      }
    }

    const wg = new THREE.BufferGeometry();
    wg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(wPos), 3));
    wg.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(wNor), 3));
    wg.setAttribute('color', new THREE.BufferAttribute(new Float32Array(wCol), 3));
    wg.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(wUV), 2));
    wallGeoms.push(wg);
    const rg = new THREE.BufferGeometry();
    rg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(rPos), 3));
    rg.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(rNor), 3));
    rg.setAttribute('color', new THREE.BufferAttribute(new Float32Array(rCol), 3));
    roofGeoms.push(rg);

    bldPolys.push({ poly, minX: minX - 1, maxX: maxX + 1, minZ: minZ - 1, maxZ: maxZ + 1, topY: eave });
  }

  function mergeWithUV(geoms) {
    let n = 0;
    for (const g of geoms) n += g.attributes.position.count;
    const pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), col = new Float32Array(n * 3), uv = new Float32Array(n * 2);
    let o = 0;
    for (const g of geoms) {
      pos.set(g.attributes.position.array, o * 3);
      nor.set(g.attributes.normal.array, o * 3);
      col.set(g.attributes.color.array, o * 3);
      if (g.attributes.uv) uv.set(g.attributes.uv.array, o * 2);
      o += g.attributes.position.count;
    }
    const out = new THREE.BufferGeometry();
    out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    out.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    out.setAttribute('color', new THREE.BufferAttribute(col, 3));
    out.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    return out;
  }

  buildingMesh = new THREE.Mesh(mergeWithUV(wallGeomsPlaster),
    new THREE.MeshLambertMaterial({ vertexColors: true, map: facadeTexPlaster, side: THREE.DoubleSide }));
  const buildingMeshWood = new THREE.Mesh(mergeWithUV(wallGeomsWood),
    new THREE.MeshLambertMaterial({ vertexColors: true, map: facadeTexWood, side: THREE.DoubleSide }));
  roofMesh = new THREE.Mesh(mergeGeoms(roofGeoms),
    new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide }));
  scene.add(buildingMesh);
  scene.add(buildingMeshWood);
  scene.add(roofMesh);
}

// spatial hash for building collision
const bldHash = new Map();
bldPolys.forEach((b, i) => {
  for (let cx = Math.floor(b.minX / CELL); cx <= Math.floor(b.maxX / CELL); cx++)
    for (let cz = Math.floor(b.minZ / CELL); cz <= Math.floor(b.maxZ / CELL); cz++) {
      const k = cx + ':' + cz;
      if (!bldHash.has(k)) bldHash.set(k, []);
      bldHash.get(k).push(i);
    }
});

function collideBuildings(pos, radius) {
  const k = Math.floor(pos.x / CELL) + ':' + Math.floor(pos.z / CELL);
  const near = new Set();
  for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) {
    const kk = (Math.floor(pos.x / CELL) + dx) + ':' + (Math.floor(pos.z / CELL) + dz);
    const arr = bldHash.get(kk); if (arr) arr.forEach(i => near.add(i));
  }
  for (const i of near) {
    const b = bldPolys[i];
    if (pos.x < b.minX - radius || pos.x > b.maxX + radius || pos.z < b.minZ - radius || pos.z > b.maxZ + radius) continue;
    const poly = b.poly;
    const inside = pointInPoly(pos.x, pos.z, poly);
    // push out from nearest edge
    let bestD = Infinity, bestNX = 0, bestNZ = 0, bestPX = 0, bestPZ = 0;
    for (let j = 0, l = poly.length - 1; j < poly.length; l = j++) {
      const ax = poly[l][0], az = poly[l][1], bx = poly[j][0], bz = poly[j][1];
      const abx = bx - ax, abz = bz - az;
      const t = Math.max(0, Math.min(1, ((pos.x - ax) * abx + (pos.z - az) * abz) / (abx * abx + abz * abz || 1)));
      const px = ax + abx * t, pz = az + abz * t;
      const d = Math.hypot(pos.x - px, pos.z - pz);
      if (d < bestD) { bestD = d; bestPX = px; bestPZ = pz; }
    }
    if (inside) {
      const d = Math.max(bestD, 0.001);
      pos.x += (bestPX - pos.x) / d * (bestD + radius);
      pos.z += (bestPZ - pos.z) / d * (bestD + radius);
    } else if (bestD < radius) {
      const d = Math.max(bestD, 0.001);
      pos.x += (pos.x - bestPX) / d * (radius - bestD);
      pos.z += (pos.z - bestPZ) / d * (radius - bestD);
    }
  }
}

// ---------- sandbags ----------
const sandbagObstacles = []; // {x,z,r,top}
let sandbagMesh;
{
  const geoms = [];
  const cBag = new THREE.Color(0xb3a173), cBag2 = new THREE.Color(0xa08e62);
  const entry = D.enemyEntry;
  function barricade(cx, cz, faceX, faceZ) {
    // wall of sandbags perpendicular to facing dir
    const y0 = heightAt(cx, cz);
    const ang = Math.atan2(faceX, faceZ);
    const perpX = Math.cos(ang), perpZ = -Math.sin(ang);
    for (let i = -2; i <= 2; i++) {
      for (let layer = 0; layer < 2; layer++) {
        const n = layer === 0 ? 1 : 0; // top layer offset
        const bx = cx + perpX * i * 0.95 + (layer ? perpX * 0.4 : 0);
        const bz = cz + perpZ * i * 0.95 + (layer ? perpZ * 0.4 : 0);
        const g = new THREE.BoxGeometry(0.95, 0.42, 0.55);
        g.rotateY(ang + (Math.random() - 0.5) * 0.15);
        g.translate(bx, heightAt(bx, bz) + 0.21 + layer * 0.42, bz);
        paintGeom(g, (i + layer) % 2 ? cBag : cBag2);
        geoms.push(g);
      }
    }
    sandbagObstacles.push({ x: cx, z: cz, r: 2.4, top: y0 + 0.9, fx: faceX, fz: faceZ });
  }
  // ring of barricades around each cap, facing enemy entry
  for (const cap of D.caps) {
    const dirX = entry[0] - cap.pos[0], dirZ = entry[1] - cap.pos[1];
    const dl = Math.hypot(dirX, dirZ);
    const fx = dirX / dl, fz = dirZ / dl;
    const baseAng = Math.atan2(fx, fz);
    for (const off of [-0.7, 0, 0.7]) {
      const a = baseAng + off;
      const bx = cap.pos[0] + Math.sin(a) * (cap.r - 4);
      const bz = cap.pos[1] + Math.cos(a) * (cap.r - 4);
      barricade(bx, bz, Math.sin(a), Math.cos(a));
    }
  }
  // extra barricades along the defence route between caps and spawn
  const route = [[150, -80], [250, -40], [180, -140], [320, -60], [380, 0], [120, -20]];
  for (const [bx, bz] of route) {
    const dirX = entry[0] - bx, dirZ = entry[1] - bz;
    const dl = Math.hypot(dirX, dirZ) || 1;
    barricade(bx, bz, dirX / dl, dirZ / dl);
  }
  sandbagMesh = new THREE.Mesh(mergeGeoms(geoms), new THREE.MeshLambertMaterial({ vertexColors: true }));
  scene.add(sandbagMesh);
}

function collideObstacles(pos, radius, footY) {
  const ccx = Math.floor(pos.x / CELL), ccz = Math.floor(pos.z / CELL);
  const seen = new Set();
  for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) {
    const arr = obstHash.get((ccx + dx) + ':' + (ccz + dz));
    if (!arr) continue;
    for (const i of arr) {
      if (seen.has(i)) continue; seen.add(i);
      const o = sandbagObstacles[i];
      if (footY > o.top - 0.25) continue; // can stand on / jump over
      const d = Math.hypot(pos.x - o.x, pos.z - o.z);
      if (d < o.r + radius && d > 0.001) {
        const push = (o.r + radius - d);
        pos.x += (pos.x - o.x) / d * push;
        pos.z += (pos.z - o.z) / d * push;
      }
    }
  }
}

// ---------- murar, staket & stödmurar ----------
const wallSegs = [];
const wallHash = new Map();
{
  const KIND = {
    wall:           { h: 1.5, c: 0x9d9789, jump: false },
    city_wall:      { h: 2.5, c: 0x8d887c, jump: false },
    retaining_wall: { h: 2.2, c: 0x8f8a7e, jump: false },
    fence:          { h: 1.1, c: 0x74695a, jump: true },
    guard_rail:     { h: 0.8, c: 0xb0b4b8, jump: true },
    hedge:          { h: 1.7, c: 0x4c6b3c, jump: false },
    cliff:          { h: 3.0, c: 0x77726a, jump: false },
    stodmur:        { h: 0, c: 0x8f8a7e, jump: false }  // höjd sätts per segment
  };
  const pos = [], nor = [], col = [];
  function addSeg(ax, az, bx, bz, hgt, kind) {
    const k = KIND[kind];
    const len = Math.hypot(bx - ax, bz - az); if (len < 0.4) return;
    const y1 = groundInfoAt(ax, az).y, y2 = groundInfoAt(bx, bz).y;
    const base = Math.min(y1, y2) - 0.6;
    const top1 = y1 + hgt, top2 = y2 + hgt;
    const nx = (bz - az) / len, nz = -(bx - ax) / len;
    const c = new THREE.Color(k.c);
    const quad = [
      [ax, base, az], [bx, base, bz], [bx, top2, bz],
      [ax, base, az], [bx, top2, bz], [ax, top1, az]
    ];
    for (const v of quad) { pos.push(...v); nor.push(nx, 0, nz); col.push(c.r, c.g, c.b); }
    const seg = { ax, az, bx, bz, top: Math.max(top1, top2), jump: k.jump,
                  minX: Math.min(ax, bx) - 1, maxX: Math.max(ax, bx) + 1,
                  minZ: Math.min(az, bz) - 1, maxZ: Math.max(az, bz) + 1 };
    const idx = wallSegs.length;
    wallSegs.push(seg);
    for (let cx = Math.floor(seg.minX / CELL); cx <= Math.floor(seg.maxX / CELL); cx++)
      for (let cz = Math.floor(seg.minZ / CELL); cz <= Math.floor(seg.maxZ / CELL); cz++) {
        const key = cx + ':' + cz;
        if (!wallHash.has(key)) wallHash.set(key, []);
        wallHash.get(key).push(idx);
      }
  }
  // kartlagda barriärer från OSM
  for (const w of (D.walls || [])) {
    const k = KIND[w.k] ? w.k : 'wall';
    for (let i = 0; i < w.p.length - 1; i++) {
      const [ax, az] = w.p[i], [bx, bz] = w.p[i + 1];
      if (!inBounds(ax, az, 5) || !inBounds(bx, bz, 5)) continue;
      addSeg(ax, az, bx, bz, KIND[k].h, k);
    }
  }
  // procedurella stödmurar: där terrängen reser sig brant alldeles intill gatukanten
  const roadKinds = new Set(['residential', 'living_street', 'tertiary', 'secondary', 'unclassified', 'service', 'pedestrian']);
  for (const rd of D.roads) {
    if (!roadKinds.has(rd.k)) continue;
    for (let i = 0; i < rd.p.length - 1; i++) {
      const [x1, z1] = rd.p[i], [x2, z2] = rd.p[i + 1];
      if (!inBounds(x1, z1) || !inBounds(x2, z2)) continue;
      const len = Math.hypot(x2 - x1, z2 - z1); if (len < 2) continue;
      const dx = (x2 - x1) / len, dz = (z2 - z1) / len;
      const px = -dz, pz = dx;
      const steps = Math.max(1, Math.floor(len / 7));
      for (let s = 0; s < steps; s++) {
        const t0 = s / steps, t1 = (s + 1) / steps;
        const mx = x1 + dx * len * (t0 + t1) / 2, mz = z1 + dz * len * (t0 + t1) / 2;
        const h0 = origHeightAt(mx, mz);
        for (const side of [1, -1]) {
          const off = rd.w / 2 + 2.0;
          const diff = heightAt(mx + px * off * side, mz + pz * off * side) - h0;
          const ex = rd.w / 2 + 0.6;
          if (diff > 1.15) {
            addSeg(x1 + dx * len * t0 + px * ex * side, z1 + dz * len * t0 + pz * ex * side,
                   x1 + dx * len * t1 + px * ex * side, z1 + dz * len * t1 + pz * ex * side,
                   Math.max(0.9, Math.min(diff * 0.55, 2.6)), 'stodmur');
          } else if (diff < -2.2) {
            // marken störtar ner intill vägen (t.ex. mot forsen) → räcke, hoppbart
            addSeg(x1 + dx * len * t0 + px * ex * side, z1 + dz * len * t0 + pz * ex * side,
                   x1 + dx * len * t1 + px * ex * side, z1 + dz * len * t1 + pz * ex * side,
                   1.0, 'guard_rail');
          }
        }
      }
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
  g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(nor), 3));
  g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(col), 3));
  scene.add(new THREE.Mesh(g, new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide })));
}

function collideWalls(pos3, radius, footY) {
  const ccx = Math.floor(pos3.x / CELL), ccz = Math.floor(pos3.z / CELL);
  const seen = new Set();
  for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) {
    const arr = wallHash.get((ccx + dx) + ':' + (ccz + dz));
    if (!arr) continue;
    for (const i of arr) {
      if (seen.has(i)) continue; seen.add(i);
      const s = wallSegs[i];
      if (footY > s.top - 0.25) continue; // hoppat över / står ovanpå
      const abx = s.bx - s.ax, abz = s.bz - s.az;
      const t = Math.max(0, Math.min(1, ((pos3.x - s.ax) * abx + (pos3.z - s.az) * abz) / (abx * abx + abz * abz || 1)));
      const qx = s.ax + abx * t, qz = s.az + abz * t;
      const d = Math.hypot(pos3.x - qx, pos3.z - qz);
      if (d < radius + 0.25 && d > 0.001) {
        const push = radius + 0.25 - d;
        pos3.x += (pos3.x - qx) / d * push;
        pos3.z += (pos3.z - qz) / d * push;
      }
    }
  }
}

// ---------- gatlyktor & parkerade bilar ----------
function insideAnyBuilding(x, z) {
  const arr = bldHash.get(Math.floor(x / CELL) + ':' + Math.floor(z / CELL));
  if (!arr) return false;
  for (const i of arr) {
    const b = bldPolys[i];
    if (x >= b.minX && x <= b.maxX && z >= b.minZ && z <= b.maxZ && pointInPoly(x, z, b.poly)) return true;
  }
  return false;
}
{
  const lampKinds = new Set(['residential', 'living_street', 'tertiary', 'secondary', 'pedestrian']);
  const carKinds = new Set(['residential', 'living_street', 'service']);
  const lamps = [], cars = [];
  for (const rd of D.roads) {
    const doLamp = lampKinds.has(rd.k), doCar = carKinds.has(rd.k);
    if (!doLamp && !doCar) continue;
    let accL = Math.random() * 20, accC = Math.random() * 30, sideL = 1;
    for (let i = 0; i < rd.p.length - 1; i++) {
      const [x1, z1] = rd.p[i], [x2, z2] = rd.p[i + 1];
      const len = Math.hypot(x2 - x1, z2 - z1); if (len < 0.5) continue;
      const dx = (x2 - x1) / len, dz = (z2 - z1) / len, px = -dz, pz = dx;
      for (let s = 2; s < len; s += 4) {
        const cxp = x1 + dx * s, czp = z1 + dz * s;
        accL += 4; accC += 4;
        if (doLamp && accL > 27) {
          accL = 0; sideL = -sideL;
          const lx = cxp + px * (rd.w / 2 + 0.8) * sideL, lz = czp + pz * (rd.w / 2 + 0.8) * sideL;
          if (inBounds(lx, lz) && !insideAnyBuilding(lx, lz)) lamps.push([lx, lz]);
        }
        if (doCar && accC > 36 && Math.random() < 0.55) {
          accC = 0;
          const side = Math.random() < 0.5 ? 1 : -1;
          const cx2 = cxp + px * (rd.w / 2 - 0.95) * side, cz2 = czp + pz * (rd.w / 2 - 0.95) * side;
          const nr = nearestRiver(cx2, cz2);
          const perpSlope = Math.abs(heightAt(cx2 + px * 2, cz2 + pz * 2) - heightAt(cx2, cz2)) / 2;
          if (inBounds(cx2, cz2) && !insideAnyBuilding(cx2, cz2) && (!nr || nr.d > 10) && perpSlope < 0.3)
            cars.push({ x: cx2, z: cz2, ang: Math.atan2(dx, dz) });
        }
      }
    }
  }
  // lyktstolpar (instansierade)
  const poleG = new THREE.CylinderGeometry(0.06, 0.09, 4.4, 6);
  const headG = new THREE.SphereGeometry(0.17, 8, 6);
  const poleM = new THREE.MeshLambertMaterial({ color: 0x3a3f45 });
  const headM = new THREE.MeshBasicMaterial({ color: 0xffe9b0 });
  const poles = new THREE.InstancedMesh(poleG, poleM, lamps.length);
  const heads = new THREE.InstancedMesh(headG, headM, lamps.length);
  const mat = new THREE.Matrix4();
  lamps.forEach(([lx, lz], i) => {
    const y = groundInfoAt(lx, lz).y;
    mat.makeTranslation(lx, y + 2.2, lz); poles.setMatrixAt(i, mat);
    mat.makeTranslation(lx, y + 4.5, lz); heads.setMatrixAt(i, mat);
    sandbagObstacles.push({ x: lx, z: lz, r: 0.28, top: y + 4.4 });
  });
  scene.add(poles); scene.add(heads);
  // parkerade bilar (instansierade, slumpade kulörer) — funkar som cover
  const bodyG = new THREE.BoxGeometry(1.72, 0.62, 4.1);
  const cabG = new THREE.BoxGeometry(1.58, 0.52, 2.1);
  const bodyM = new THREE.MeshLambertMaterial();
  const cabM = new THREE.MeshLambertMaterial();
  const bodies = new THREE.InstancedMesh(bodyG, bodyM, cars.length);
  const cabs = new THREE.InstancedMesh(cabG, cabM, cars.length);
  const CAR_COLS = [0xc9cdd1, 0x2e3438, 0x8c2026, 0x2a4d7c, 0xdedbd2, 0x49544a, 0x7d7f83];
  const q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0), one = new THREE.Vector3(1, 1, 1);
  cars.forEach((c, i) => {
    const y = groundInfoAt(c.x, c.z).y;
    q.setFromAxisAngle(up, c.ang);
    mat.compose(new THREE.Vector3(c.x, y + 0.55, c.z), q, one); bodies.setMatrixAt(i, mat);
    mat.compose(new THREE.Vector3(c.x, y + 1.08, c.z - 0), q, one); cabs.setMatrixAt(i, mat);
    const col = new THREE.Color(CAR_COLS[i % CAR_COLS.length]);
    bodies.setColorAt(i, col); cabs.setColorAt(i, col.clone().multiplyScalar(0.8));
    sandbagObstacles.push({ x: c.x, z: c.z, r: 1.45, top: y + 1.45 });
  });
  if (bodies.instanceColor) bodies.instanceColor.needsUpdate = true;
  if (cabs.instanceColor) cabs.instanceColor.needsUpdate = true;
  scene.add(bodies); scene.add(cabs);
}

// hindren i spatial hash (kollision + kulblockering)
const obstHash = new Map();
for (let i = 0; i < sandbagObstacles.length; i++) {
  const o = sandbagObstacles[i];
  for (let cx = Math.floor((o.x - o.r - 1) / CELL); cx <= Math.floor((o.x + o.r + 1) / CELL); cx++)
    for (let cz = Math.floor((o.z - o.r - 1) / CELL); cz <= Math.floor((o.z + o.r + 1) / CELL); cz++) {
      const k = cx + ':' + cz;
      if (!obstHash.has(k)) obstHash.set(k, []);
      obstHash.get(k).push(i);
    }
}

// ---------- trees ----------
{
  const trunkG = new THREE.CylinderGeometry(0.18, 0.28, 2.2, 5);
  const crownG = new THREE.ConeGeometry(1.6, 3.6, 7);
  const trunkM = new THREE.MeshLambertMaterial({ color: 0x5a4632 });
  const crownM = new THREE.MeshLambertMaterial({ color: 0x3d5c33 });
  const N = 350;
  const trunks = new THREE.InstancedMesh(trunkG, trunkM, N);
  const crowns = new THREE.InstancedMesh(crownG, crownM, N);
  const mat = new THREE.Matrix4();
  let placed = 0, guard = 0;
  const polys = D.green.filter(g => g.p.length >= 3);
  while (placed < N && guard++ < 6000 && polys.length) {
    const g = polys[Math.floor(Math.random() * polys.length)];
    let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
    for (const p of g.p) { minX = Math.min(minX, p[0]); maxX = Math.max(maxX, p[0]); minZ = Math.min(minZ, p[1]); maxZ = Math.max(maxZ, p[1]); }
    const x = lerp(minX, maxX, Math.random()), z = lerp(minZ, maxZ, Math.random());
    if (!inBounds(x, z) || !pointInPoly(x, z, g.p)) continue;
    const y = heightAt(x, z);
    const s = 0.7 + Math.random() * 0.9;
    mat.makeScale(s, s, s); mat.setPosition(x, y + 1.1 * s, z);
    trunks.setMatrixAt(placed, mat);
    mat.makeScale(s, s, s); mat.setPosition(x, y + 2.2 * s + 1.6 * s, z);
    crowns.setMatrixAt(placed, mat);
    placed++;
  }
  trunks.count = placed; crowns.count = placed;
  scene.add(trunks); scene.add(crowns);
}

// ---------- capture point markers ----------
const capState = D.caps.map(c => ({
  ...c, owner: 'friendly', progress: 0, beam: null, label: null,
  y: heightAt(c.pos[0], c.pos[1])
}));
for (const cap of capState) {
  const beamG = new THREE.CylinderGeometry(cap.r * 0.35, cap.r * 0.35, 60, 16, 1, true);
  const beamM = new THREE.MeshBasicMaterial({ color: 0x4f9dff, transparent: true, opacity: 0.16, side: THREE.DoubleSide, depthWrite: false });
  cap.beam = new THREE.Mesh(beamG, beamM);
  cap.beam.position.set(cap.pos[0], cap.y + 30, cap.pos[1]);
  scene.add(cap.beam);
  // floating letter sprite
  const cv = document.createElement('canvas'); cv.width = 128; cv.height = 128;
  const cx = cv.getContext('2d');
  cx.font = 'bold 96px Arial'; cx.textAlign = 'center'; cx.textBaseline = 'middle';
  cx.fillStyle = '#fff'; cx.shadowColor = '#000'; cx.shadowBlur = 12;
  cx.fillText(cap.id, 64, 68);
  const tex = new THREE.CanvasTexture(cv);
  const spr = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  spr.scale.set(10, 10, 1);
  spr.position.set(cap.pos[0], cap.y + 26, cap.pos[1]);
  cap.label = spr;
  scene.add(spr);
}

// Swedish flag at spawn
{
  const px = D.spawn[0], pz = D.spawn[1], py = heightAt(px, pz);
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 9, 6), new THREE.MeshLambertMaterial({ color: 0xd8d8d8 }));
  pole.position.set(px + 3, py + 4.5, pz + 3);
  scene.add(pole);
  const cv = document.createElement('canvas'); cv.width = 160; cv.height = 100;
  const c2 = cv.getContext('2d');
  c2.fillStyle = '#006aa7'; c2.fillRect(0, 0, 160, 100);
  c2.fillStyle = '#fecc02'; c2.fillRect(50, 0, 20, 100); c2.fillRect(0, 40, 160, 20);
  const flag = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 2),
    new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(cv), side: THREE.DoubleSide }));
  flag.position.set(px + 3 + 1.7, py + 8, pz + 3);
  scene.add(flag);
}

// ---------- landmark labels ----------
const markSprites = [];
{
  function labelSprite(text, kind) {
    const pad = 8, fs = 44;
    const cv = document.createElement('canvas');
    const ctx = cv.getContext('2d');
    ctx.font = `bold ${fs}px "Helvetica Neue", Arial`;
    const tw = ctx.measureText(text).width;
    cv.width = Math.ceil(tw + pad * 4); cv.height = fs + pad * 3;
    const c = cv.getContext('2d');
    c.font = `bold ${fs}px "Helvetica Neue", Arial`;
    c.textBaseline = 'middle';
    c.fillStyle = kind === 'district' ? 'rgba(10,16,24,0.55)' : 'rgba(10,16,24,0.4)';
    c.beginPath(); c.roundRect(0, 0, cv.width, cv.height, 10); c.fill();
    c.fillStyle = kind === 'district' ? '#ffd76a' : (kind === 'bld' ? '#9fd4ff' : '#e8eef4');
    c.fillText(text, pad * 2, cv.height / 2 + 2);
    const tex = new THREE.CanvasTexture(cv);
    tex.colorSpace = THREE.SRGBColorSpace;
    const mat = new THREE.SpriteMaterial({ map: tex, sizeAttenuation: false, depthTest: false, transparent: true });
    const spr = new THREE.Sprite(mat);
    const s = kind === 'district' ? 0.036 : 0.026;
    spr.scale.set(s * cv.width / cv.height, s, 1);
    spr.renderOrder = 5;
    return spr;
  }
  for (const m of (D.marks || [])) {
    const spr = labelSprite(m.n, m.k);
    const y = heightAt(m.p[0], m.p[1]) + (m.k === 'bld' ? m.h * 1.2 : m.h);
    spr.position.set(m.p[0], y, m.p[1]);
    spr.userData = { kind: m.k };
    scene.add(spr);
    markSprites.push(spr);
  }
}

// ---------- road graph for enemy pathfinding ----------
const graph = { nodes: [], adj: [] };
{
  const keyMap = new Map();
  const K = p => Math.round(p[0] / 2) + ':' + Math.round(p[1] / 2);
  function nodeFor(p) {
    const k = K(p);
    if (keyMap.has(k)) return keyMap.get(k);
    const id = graph.nodes.length;
    graph.nodes.push([p[0], p[1]]);
    graph.adj.push([]);
    keyMap.set(k, id);
    return id;
  }
  for (const rd of D.roads) {
    if (rd.k === 'primary' || rd.k === 'secondary') continue; // enemies avoid the big highway
    let prev = null;
    for (const p of rd.p) {
      const id = nodeFor(p);
      if (prev !== null && prev !== id) {
        const a = graph.nodes[prev], b = graph.nodes[id];
        const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
        if (d < 120) { graph.adj[prev].push([id, d]); graph.adj[id].push([prev, d]); }
      }
      prev = id;
    }
  }
}
function nearestNode(x, z) {
  let best = 0, bd = Infinity;
  for (let i = 0; i < graph.nodes.length; i++) {
    const n = graph.nodes[i];
    const d = (n[0] - x) * (n[0] - x) + (n[1] - z) * (n[1] - z);
    if (d < bd) { bd = d; best = i; }
  }
  return best;
}
function findPath(fromId, toId) {
  // A*
  const open = [[0, fromId]];
  const gScore = new Map([[fromId, 0]]);
  const came = new Map();
  const h = i => {
    const a = graph.nodes[i], b = graph.nodes[toId];
    return Math.hypot(a[0] - b[0], a[1] - b[1]);
  };
  const closed = new Set();
  while (open.length) {
    let bi = 0;
    for (let i = 1; i < open.length; i++) if (open[i][0] < open[bi][0]) bi = i;
    const [, cur] = open.splice(bi, 1)[0];
    if (cur === toId) {
      const path = [cur];
      let c = cur;
      while (came.has(c)) { c = came.get(c); path.push(c); }
      return path.reverse().map(i => graph.nodes[i]);
    }
    if (closed.has(cur)) continue;
    closed.add(cur);
    for (const [nb, d] of graph.adj[cur]) {
      if (closed.has(nb)) continue;
      const g = gScore.get(cur) + d;
      if (g < (gScore.get(nb) ?? Infinity)) {
        gScore.set(nb, g);
        came.set(nb, cur);
        open.push([g + h(nb), nb]);
      }
    }
  }
  return null;
}

// ---------- audio ----------
let AC = null;
function audio() { if (!AC) AC = new (window.AudioContext || window.webkitAudioContext)(); return AC; }
function playShot(vol = 0.25, freq = 700) {
  const ac = audio();
  const dur = 0.12;
  const buf = ac.createBuffer(1, ac.sampleRate * dur, ac.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / d.length, 2.2);
  const src = ac.createBufferSource(); src.buffer = buf;
  const f = ac.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = freq;
  const g = ac.createGain(); g.gain.value = vol;
  src.connect(f); f.connect(g); g.connect(ac.destination);
  src.start();
}
let riverGainNode = null;
function startAmbient() {
  if (riverGainNode) return;
  const ac = audio();
  const dur = 2.5;
  const buf = ac.createBuffer(1, ac.sampleRate * dur, ac.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  const src = ac.createBufferSource(); src.buffer = buf; src.loop = true;
  const f = ac.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 850;
  riverGainNode = ac.createGain(); riverGainNode.gain.value = 0;
  src.connect(f); f.connect(riverGainNode); riverGainNode.connect(ac.destination);
  src.start();
}

function playTone(freq, dur, vol = 0.15, type = 'square') {
  const ac = audio();
  const o = ac.createOscillator(); o.type = type; o.frequency.value = freq;
  const g = ac.createGain(); g.gain.setValueAtTime(vol, ac.currentTime);
  g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + dur);
  o.connect(g); g.connect(ac.destination);
  o.start(); o.stop(ac.currentTime + dur);
}

// ---------- player ----------
const player = {
  pos: new THREE.Vector3(D.spawn[0], 0, D.spawn[1]),
  vel: new THREE.Vector3(),
  yaw: 0, pitch: 0,
  hp: 100, maxHp: 100,
  onGround: true,
  lastHurt: -99,
  dead: false, deadTimer: 0,
  mag: 30, magSize: 30, reloading: false, reloadT: 0,
  fireCooldown: 0
};
player.pos.y = heightAt(player.pos.x, player.pos.z);
{ // face toward cap C
  const c = D.caps[2].pos;
  player.yaw = Math.atan2(-(c[0] - player.pos.x), -(c[1] - player.pos.z));
}

const keys = {};
addEventListener('keydown', e => { keys[e.code] = true; if (e.code === 'KeyR') startReload(); });
addEventListener('keyup', e => { keys[e.code] = false; });

let locked = false, firing = false;
document.addEventListener('pointerlockchange', () => { locked = document.pointerLockElement === canvas; });
addEventListener('mousemove', e => {
  if (!locked) return;
  player.yaw -= e.movementX * 0.0022;
  player.pitch -= e.movementY * 0.0022;
  player.pitch = Math.max(-1.45, Math.min(1.45, player.pitch));
});
addEventListener('mousedown', e => { if (locked && e.button === 0) firing = true; });
addEventListener('mouseup', e => { if (e.button === 0) firing = false; });

// ---------- weapon viewmodel ----------
const gun = new THREE.Group();
{
  const mDark = new THREE.MeshLambertMaterial({ color: 0x2b2f33 });
  const mWood = new THREE.MeshLambertMaterial({ color: 0x5a4632 });
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.14, 0.55), mDark);
  const barrel = new THREE.Mesh(new THREE.BoxGeometry(0.045, 0.045, 0.5), mDark);
  barrel.position.set(0, 0.04, -0.5);
  const stock = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.12, 0.3), mWood);
  stock.position.set(0, -0.02, 0.38);
  const magMesh = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.18, 0.1), mDark);
  magMesh.position.set(0, -0.14, -0.08);
  gun.add(body, barrel, stock, magMesh);
  gun.scale.set(0.38, 0.38, 0.38);
  gun.position.set(0.26, -0.24, -0.45);
  camera.add(gun);
}
scene.add(camera);
let gunKick = 0;

const flash = new THREE.PointLight(0xffcc66, 0, 12);
scene.add(flash);

// tracers
const tracers = [];
const tracerMat = new THREE.LineBasicMaterial({ color: 0xffd27f, transparent: true });
function addTracer(from, to, color) {
  const g = new THREE.BufferGeometry().setFromPoints([from, to]);
  const mat = tracerMat.clone();
  if (color) mat.color.set(color);
  const line = new THREE.Line(g, mat);
  scene.add(line);
  tracers.push({ line, life: 0.09 });
}

// ---------- soldiers (enemies + allies) ----------
function makeSoldier(color, helmetColor) {
  const grp = new THREE.Group();
  const uniform = new THREE.MeshLambertMaterial({ color });
  const dark = new THREE.MeshLambertMaterial({ color: new THREE.Color(color).multiplyScalar(0.55) });
  const gear = new THREE.MeshLambertMaterial({ color: 0x26292c });
  const skin = new THREE.MeshLambertMaterial({ color: 0xc9a186 });
  const helm = new THREE.MeshLambertMaterial({ color: helmetColor });

  // torso: bål + stridsväst + bälte
  const torso = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.62, 0.28), uniform);
  torso.position.y = 1.12;
  const vest = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.42, 0.34), gear);
  vest.position.y = 1.18;
  const belt = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.09, 0.3), dark);
  belt.position.y = 0.83;
  const pack = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.42, 0.16), dark);
  pack.position.set(0, 1.16, 0.24);

  // huvud + hjälm med brätte
  const head = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.26, 0.24), skin);
  head.position.y = 1.58;
  const helmet = new THREE.Mesh(new THREE.SphereGeometry(0.19, 10, 6, 0, Math.PI * 2, 0, Math.PI * 0.6), helm);
  helmet.scale.set(1, 0.85, 1.1);
  helmet.position.y = 1.66;
  const brim = new THREE.Mesh(new THREE.CylinderGeometry(0.21, 0.22, 0.035, 10), helm);
  brim.position.y = 1.62;

  // ben med knä-antydan (animeras i update)
  const mkLeg = x => {
    const leg = new THREE.Group();
    const thigh = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.44, 0.18), uniform);
    thigh.position.y = -0.22;
    const shin = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.42, 0.15), dark);
    shin.position.y = -0.63;
    const boot = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.1, 0.26), gear);
    boot.position.set(0, -0.86, -0.04);
    leg.add(thigh, shin, boot);
    leg.position.set(x, 0.86, 0);
    return leg;
  };
  const legL = mkLeg(-0.13), legR = mkLeg(0.13);

  // armar som håller geväret framför kroppen (aim-grupp, vrids mot målet)
  const aim = new THREE.Group();
  aim.position.set(0, 1.34, 0);
  const armR = new THREE.Mesh(new THREE.BoxGeometry(0.13, 0.13, 0.5), uniform);
  armR.position.set(0.2, -0.05, -0.22);
  armR.rotation.y = 0.35;
  const armL = new THREE.Mesh(new THREE.BoxGeometry(0.13, 0.13, 0.44), uniform);
  armL.position.set(-0.12, -0.06, -0.3);
  armL.rotation.y = -0.5;
  const rifle = new THREE.Group();
  const rBody = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.12, 0.62), gear);
  const rBarrel = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.035, 0.42), gear);
  rBarrel.position.set(0, 0.035, -0.5);
  const rMag = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.16, 0.09), dark);
  rMag.position.set(0, -0.12, -0.06);
  const rStock = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.1, 0.2), dark);
  rStock.position.set(0, -0.02, 0.36);
  rifle.add(rBody, rBarrel, rMag, rStock);
  rifle.position.set(0.04, -0.1, -0.42);
  // mynningseld (tänds vid skott)
  const flashSpr = new THREE.Sprite(new THREE.SpriteMaterial({ color: 0xffd27f, transparent: true, opacity: 0 }));
  flashSpr.scale.set(0.5, 0.5, 1);
  flashSpr.position.set(0.04, -0.06, -1.16);
  aim.add(armR, armL, rifle, flashSpr);

  grp.add(torso, vest, belt, pack, head, helmet, brim, legL, legR, aim);
  grp.userData = { bodyMat: uniform, legL, legR, aim, flashSpr, flashT: 0 };
  return grp;
}

// benanimation + mynningseld — anropas varje frame för levande soldater
function animateSoldier(mesh, moving, dt, speedFactor = 1) {
  const u = mesh.userData;
  if (!u.legL) return;
  if (moving) {
    u.phase = (u.phase || 0) + dt * 7 * speedFactor;
    u.legL.rotation.x = Math.sin(u.phase) * 0.55;
    u.legR.rotation.x = -Math.sin(u.phase) * 0.55;
  } else {
    u.legL.rotation.x *= 0.8; u.legR.rotation.x *= 0.8;
  }
  if (u.flashT > 0) {
    u.flashT -= dt;
    u.flashSpr.material.opacity = Math.max(0, u.flashT / 0.06);
  }
}
function soldierMuzzle(mesh) {
  const u = mesh.userData;
  if (u.flashSpr) { u.flashT = 0.06; u.flashSpr.material.opacity = 1; u.flashSpr.material.rotation = Math.random() * 6.28; }
}
// vrid överkroppen/vapnet mot ett mål i höjdled
function soldierAimAt(mesh, fromPos, target) {
  const u = mesh.userData;
  if (!u.aim) return;
  const d = Math.hypot(target.x - fromPos.x, target.z - fromPos.z) || 1;
  u.aim.rotation.x = Math.max(-0.7, Math.min(0.7, Math.atan2(target.y - (fromPos.y + 1.34), d)));
}

const enemies = [];
const allies = [];

// förstärkningar väller in från tre håll — Forsebron, söderifrån och österifrån
const ENTRY_POINTS = [D.enemyEntry, [-100, 350], [850, 300]].map(p => {
  const n = graph.nodes[nearestNode(p[0], p[1])];
  return [n[0], n[1]];
});

// slumpad vägnod, minst `minDist` från spelarens bas
function randomOccupationPos(minDist) {
  for (let tries = 0; tries < 60; tries++) {
    const n = graph.nodes[Math.floor(Math.random() * graph.nodes.length)];
    if (!inBounds(n[0], n[1], -30)) continue;
    if (Math.hypot(n[0] - D.spawn[0], n[1] - D.spawn[1]) < minDist) continue;
    return [n[0] + (Math.random() - 0.5) * 10, n[1] + (Math.random() - 0.5) * 10];
  }
  return [D.enemyEntry[0], D.enemyEntry[1]];
}

function spawnEnemy(at) {
  const e = at || ENTRY_POINTS[Math.floor(Math.random() * ENTRY_POINTS.length)];
  const jx = (Math.random() - 0.5) * 24, jz = (Math.random() - 0.5) * 24;
  const mesh = makeSoldier(0x6e2f2a, 0x3a3f35);
  const pos = new THREE.Vector3(e[0] + jx, 0, e[1] + jz);
  pos.y = heightAt(pos.x, pos.z);
  mesh.position.copy(pos);
  scene.add(mesh);
  const en = {
    mesh, pos, hp: 100, dead: false, deadT: 0,
    path: null, pathI: 0, target: null,
    speed: 2.6 + Math.random() * 0.9,
    losT: Math.random(), canSee: false, fireT: 1 + Math.random() * 2,
    wobble: Math.random() * 10, lateral: (Math.random() - 0.5) * 3
  };
  enemies.push(en);
  return en;
}

function spawnAlly(x, z) {
  const mesh = makeSoldier(0x2f4a6e, 0x27313d);
  const pos = new THREE.Vector3(x, heightAt(x, z), z);
  mesh.position.copy(pos);
  scene.add(mesh);
  const al = { mesh, pos, hp: 100, dead: false, deadT: 0, fireT: Math.random() * 2,
               path: null, pathI: 0, target: null, speed: 2.7 + Math.random() * 0.6,
               holdX: (Math.random() - 0.5) * 10, holdZ: (Math.random() - 0.5) * 10, stuckT: 0 };
  allies.push(al);
  return al;
}
// försvarsstyrkan grupperar vid B och C — A är redan förlorat när uppdraget börjar
for (const cap of [capState[1], capState[2]]) {
  spawnAlly(cap.pos[0] + 4, cap.pos[1] + 4);
  spawnAlly(cap.pos[0] - 4, cap.pos[1] - 3);
  spawnAlly(cap.pos[0] + 6, cap.pos[1] - 5);
}

// ---------- fast analytic raycast (terrain + buildings + sandbags) ----------
function pointBlocked(x, y, z) {
  if (y < heightAt(x, z) - 0.2) return true;
  const cx = Math.floor(x / CELL), cz = Math.floor(z / CELL);
  const arr = bldHash.get(cx + ':' + cz);
  if (arr) {
    for (const i of arr) {
      const b = bldPolys[i];
      if (x < b.minX || x > b.maxX || z < b.minZ || z > b.maxZ) continue;
      if (y < b.topY && pointInPoly(x, z, b.poly)) return true;
    }
  }
  const oArr = obstHash.get(cx + ':' + cz);
  if (oArr) {
    for (const i of oArr) {
      const o = sandbagObstacles[i];
      if (y < o.top && Math.hypot(x - o.x, z - o.z) < o.r * 0.7) return true;
    }
  }
  const wArr = wallHash.get(cx + ':' + cz);
  if (wArr) {
    for (const i of wArr) {
      const s = wallSegs[i];
      if (y > s.top) continue;
      const abx = s.bx - s.ax, abz = s.bz - s.az;
      const t = Math.max(0, Math.min(1, ((x - s.ax) * abx + (z - s.az) * abz) / (abx * abx + abz * abz || 1)));
      if (Math.hypot(x - (s.ax + abx * t), z - (s.az + abz * t)) < 0.35) return true;
    }
  }
  return false;
}

// returns { distance } of first blocked point, or null
function raycastWorld(origin, dir, maxDist) {
  const step = 0.8;
  for (let t = step; t <= maxDist; t += step) {
    const x = origin.x + dir.x * t, y = origin.y + dir.y * t, z = origin.z + dir.z * t;
    if (pointBlocked(x, y, z)) return { distance: t };
  }
  return null;
}

function hasLOS(from, to) {
  const dir = to.clone().sub(from);
  const dist = dir.length();
  dir.normalize();
  return !raycastWorld(from, dir, dist - 0.8);
}

// ---------- game state ----------
const game = {
  started: false, over: false,
  wave: 0, maxWave: 8,
  kills: 0,
  toSpawn: 0, spawnT: 0, betweenT: 4,
  msgT: 0
};

const feedEl = document.getElementById('feed');
function msg(text) {
  const d = document.createElement('div');
  d.textContent = text;
  feedEl.appendChild(d);
  while (feedEl.children.length > 5) feedEl.removeChild(feedEl.firstChild);
  setTimeout(() => { if (d.parentNode) d.parentNode.removeChild(d); }, 6000);
}

// caps HUD
const capsEl = document.getElementById('caps');
const capPills = capState.map(cap => {
  const d = document.createElement('div');
  d.className = 'cap friendly';
  d.innerHTML = `<b>${cap.id}</b>${cap.name}<div class="bar"><i></i></div>`;
  capsEl.appendChild(d);
  return d;
});

// ---------- startläge: invasionen är redan igång ----------
{
  const A = capState[0], B = capState[1], C = capState[2];
  A.owner = 'enemy'; A.progress = 1;
  A.beam.material.color.set(0xff4444);
  game.wave = 1; game.toSpawn = 5; game.spawnT = 3; game.betweenT = 9;
  document.getElementById('wavenum').textContent = 'Våg 1/8';
  // förtruppen är redan på väg uppför backarna mot B och C
  // ockupationen: fienden håller hela kartan utom området närmast basen
  for (let i = 0; i < 18; i++) {
    const p = randomOccupationPos(170);
    const en = spawnEnemy(p);
    en.pos.y = groundInfoAt(en.pos.x, en.pos.z).y;
    en.mesh.position.copy(en.pos);
  }
  // ...plus förtrupp på väg upp och två infiltratörer nära basen — omedelbar kontakt
  for (const [from, to, n, tBase, tSpan] of [[A.pos, B.pos, 3, 0.25, 0.6], [B.pos, C.pos, 3, 0.15, 0.45], [C.pos, D.spawn, 2, 0.3, 0.25]]) {
    for (let i = 0; i < n; i++) {
      const t = tBase + tSpan * (i / n) + Math.random() * 0.08;
      const en = spawnEnemy([lerp(from[0], to[0], t) + (Math.random() - 0.5) * 16,
                             lerp(from[1], to[1], t) + (Math.random() - 0.5) * 16]);
      en.pos.y = groundInfoAt(en.pos.x, en.pos.z).y;
      en.mesh.position.copy(en.pos);
    }
  }
}

function startReload() {
  if (player.reloading || player.mag === player.magSize || player.dead) return;
  player.reloading = true; player.reloadT = 1.7;
  document.getElementById('reloadmsg').style.display = 'block';
}

// current cap the enemies push toward: lowest index not enemy-owned
function frontlineCap() {
  for (const c of capState) if (c.owner !== 'enemy') return c;
  return null;
}

// ---------- shooting ----------
function playerShoot() {
  if (player.mag <= 0) { startReload(); return; }
  if (player.reloading || player.dead) return;
  player.mag--;
  player.fireCooldown = 0.11;
  gunKick = 1;
  playShot(0.3, 900);
  flash.intensity = 3;
  flash.position.copy(camera.position).add(new THREE.Vector3(Math.sin(player.yaw + 0.3), -0.1, Math.cos(player.yaw + 0.3)).multiplyScalar(-1));

  const dir = new THREE.Vector3(0, 0, -1).applyEuler(new THREE.Euler(player.pitch, player.yaw, 0, 'YXZ'));
  // small spread
  dir.x += (Math.random() - 0.5) * 0.012;
  dir.y += (Math.random() - 0.5) * 0.012;
  dir.normalize();
  const origin = camera.position.clone();

  const worldHit = raycastWorld(origin, dir, 400);
  const worldDist = worldHit ? worldHit.distance : 400;

  // sphere test vs enemies
  let best = null, bestDist = worldDist;
  for (const en of enemies) {
    if (en.dead) continue;
    const center = en.pos.clone(); center.y += 1.0;
    const oc = center.sub(origin);
    const tProj = oc.dot(dir);
    if (tProj < 0 || tProj > bestDist) continue;
    const closest = origin.clone().add(dir.clone().multiplyScalar(tProj));
    const centerW = en.pos.clone(); centerW.y += 1.0;
    const dd = closest.distanceTo(centerW);
    if (dd < 0.65) {
      const hitY = closest.y - en.pos.y;
      if (tProj < bestDist) { best = { en, dist: tProj, head: hitY > 1.45 }; bestDist = tProj; }
    }
  }

  const end = origin.clone().add(dir.clone().multiplyScalar(bestDist));
  const muzzle = origin.clone().add(dir.clone().multiplyScalar(1.2)).add(new THREE.Vector3(0, -0.15, 0));
  addTracer(muzzle, end);

  if (best) {
    const dmg = best.head ? 100 : 40;
    damageEnemy(best.en, dmg);
    const hm = document.getElementById('hitmarker');
    hm.style.opacity = 1;
    setTimeout(() => hm.style.opacity = 0, 90);
    playTone(1200, 0.05, 0.1, 'sine');
  }
  document.getElementById('mag').textContent = player.mag;
}

function damageEnemy(en, dmg) {
  if (en.dead) return;
  en.hp -= dmg;
  en.mesh.userData.bodyMat.emissive = new THREE.Color(0x662222);
  setTimeout(() => { en.mesh.userData.bodyMat.emissive = new THREE.Color(0x000000); }, 80);
  if (en.hp <= 0) {
    en.dead = true; en.deadT = 0;
    game.kills++;
    document.getElementById('kills').textContent = game.kills + ' fiender nedkämpade';
  }
}

function damagePlayer(dmg) {
  if (player.dead || game.over) return;
  player.hp -= dmg;
  player.lastHurt = clock.elapsedTime;
  playTone(160, 0.15, 0.2, 'sawtooth');
  if (player.hp <= 0) {
    player.hp = 0; player.dead = true; player.deadTimer = 5;
    msg('Du stupade! Återuppstår vid basen om 5 s…');
  }
}

// ---------- enemy update ----------
function updateEnemy(en, dt) {
  if (en.dead) {
    en.deadT += dt;
    en.mesh.rotation.x = Math.min(Math.PI / 2, en.deadT * 4);
    if (en.deadT > 3) {
      scene.remove(en.mesh);
      enemies.splice(enemies.indexOf(en), 1);
    }
    return;
  }

  // anfall närmaste punkt som inte redan är vår — ingen vänder om i onödan
  let targetCap = null, tcd = Infinity;
  for (const c of capState) {
    if (c.owner === 'enemy') continue;
    const dc = Math.hypot(en.pos.x - c.pos[0], en.pos.z - c.pos[1]);
    if (dc < tcd) { tcd = dc; targetCap = c; }
  }
  if (!targetCap) targetCap = capState[capState.length - 1];

  // (re)path if needed
  if (!en.path || en.target !== targetCap.id) {
    en.target = targetCap.id;
    const from = nearestNode(en.pos.x, en.pos.z);
    const to = nearestNode(targetCap.pos[0], targetCap.pos[1]);
    en.path = findPath(from, to) || [[targetCap.pos[0], targetCap.pos[1]]];
    en.pathI = 0;
  }

  const distToPlayer = en.pos.distanceTo(player.pos);

  // LOS check (throttled)
  en.losT -= dt;
  if (en.losT <= 0) {
    en.losT = 0.4 + Math.random() * 0.3;
    en.canSee = false;
    if (!player.dead && distToPlayer < 75) {
      const from = en.pos.clone(); from.y += 1.55;
      const to = player.pos.clone(); to.y += 1.5;
      en.canSee = hasLOS(from, to);
    }
  }

  const inCapZone = Math.hypot(en.pos.x - targetCap.pos[0], en.pos.z - targetCap.pos[1]) < targetCap.r;
  const engaging = en.canSee && distToPlayer < 70;
  const preX = en.pos.x, preZ = en.pos.z;

  // eld under framryckning — de stannar bara i närstrid
  if (engaging) {
    en.mesh.lookAt(player.pos.x, en.pos.y + 1.5, player.pos.z);
    en.fireT -= dt;
    if (en.fireT <= 0) {
      en.fireT = 0.75 + Math.random() * 0.6;
      const from = en.pos.clone(); from.y += 1.5;
      const to = player.pos.clone(); to.y += 1.4;
      addTracer(from, to.clone().add(new THREE.Vector3((Math.random() - .5) * 2, (Math.random() - .5) * 2, (Math.random() - .5) * 2)), 0xff6644);
      playShot(0.12, 500);
      soldierMuzzle(en.mesh);
      soldierAimAt(en.mesh, en.pos, { x: player.pos.x, y: player.pos.y + 1.4, z: player.pos.z });
      const moving = !inCapZone && distToPlayer > 22;
      const hitChance = Math.max(0.07, (0.42 - distToPlayer / 150) * (moving ? 0.65 : 1));
      if (Math.random() < hitChance) damagePlayer(6 + Math.random() * 5);
    }
  }

  if (!inCapZone && en.path) {
    // avancera mot målet — även under beskjutning (långsammare), strafe:a i närkontakt
    let speedMul = 1;
    if (engaging) speedMul = distToPlayer < 22 ? 0 : 0.65;
    if (speedMul === 0) {
      // sidledsrörelse i eldstrid — stå aldrig blick stilla
      const pdx = player.pos.x - en.pos.x, pdz = player.pos.z - en.pos.z;
      const pd = Math.hypot(pdx, pdz) || 1;
      const s = Math.sin(clock.elapsedTime * 1.7 + en.wobble * 3) * 1.6 * dt;
      en.pos.x += (-pdz / pd) * s;
      en.pos.z += (pdx / pd) * s;
    }
    if (speedMul > 0) {
      let wp = en.path[Math.min(en.pathI, en.path.length - 1)];
      let dx = wp[0] + en.lateral - en.pos.x, dz = wp[1] + en.lateral * 0.5 - en.pos.z;
      let d = Math.hypot(dx, dz);
      if (d < 3 && en.pathI < en.path.length - 1) { en.pathI++; wp = en.path[en.pathI]; dx = wp[0] - en.pos.x; dz = wp[1] - en.pos.z; d = Math.hypot(dx, dz); }
      if (d > 0.1) {
        let sp = en.speed * speedMul;
        const nrE = nearestRiver(en.pos.x, en.pos.z);
        if (nrE && nrE.d < 4.6 && en.pos.y < origHeightAt(en.pos.x, en.pos.z) - 1.1) sp *= 0.4; // vadar
        en.pos.x += dx / d * sp * dt;
        en.pos.z += dz / d * sp * dt;
        if (!engaging) en.mesh.rotation.y = Math.atan2(dx, dz);
        // fastna-detektor: kommer vi ingenstans → hoppa waypoint / räkna om vägen
        en.stuckT = (en.stuckT || 0) + dt;
        if (en.stuckT > 1.6) {
          const moved = Math.hypot(en.pos.x - (en.lastX ?? en.pos.x), en.pos.z - (en.lastZ ?? en.pos.z));
          if (moved < 1.2) {
            if (en.pathI < en.path.length - 1) en.pathI++;
            else en.path = null; // tvinga ompathning
            en.lateral = (Math.random() - 0.5) * 4;
          }
          en.stuckT = 0; en.lastX = en.pos.x; en.lastZ = en.pos.z;
        }
      }
    }
  } else if (inCapZone && !engaging) {
    // säkra zonen, skjut löst mot försvarare
    en.fireT -= dt;
    if (en.fireT <= 0) { en.fireT = 1.5; playShot(0.06, 400); }
  }

  collideBuildings(en.pos, 0.45);
  collideObstacles(en.pos, 0.45, en.pos.y);
  collideWalls(en.pos, 0.45, en.pos.y);
  en.pos.y = groundInfoAt(en.pos.x, en.pos.z).y;
  en.wobble += dt * 8;
  en.mesh.position.copy(en.pos);
  animateSoldier(en.mesh, Math.hypot(en.pos.x - preX, en.pos.z - preZ) > 0.15 * dt, dt, en.speed / 3);

  // enemies can hurt nearby allies
  for (const al of allies) {
    if (al.dead) continue;
    if (en.pos.distanceTo(al.pos) < 28 && Math.random() < dt * 0.06) {
      al.hp -= 25;
      if (al.hp <= 0) { al.dead = true; al.deadT = 0; msg('En försvarare stupade vid ' + (frontlineCap()?.name || 'fronten')); }
    }
  }
}

function updateAlly(al, dt) {
  if (al.dead) {
    al.deadT += dt;
    al.mesh.rotation.x = Math.min(Math.PI / 2, al.deadT * 4);
    if (al.deadT > 4) al.mesh.visible = false;
    return;
  }

  // närmsta levande fiende
  let best = null, bd = 55;
  for (const en of enemies) {
    if (en.dead) continue;
    const d = al.pos.distanceTo(en.pos);
    if (d < bd) { bd = d; best = en; }
  }

  al.fireT -= dt;
  if (best && al.fireT <= 0) {
    al.fireT = 0.95 + Math.random() * 0.5;
    al.mesh.lookAt(best.pos.x, al.pos.y + 1.5, best.pos.z);
    const from = al.pos.clone(); from.y += 1.5;
    const to = best.pos.clone(); to.y += 1.2;
    if (hasLOS(from, to)) {
      addTracer(from, to, 0x88bbff);
      playShot(0.07, 700);
      soldierMuzzle(al.mesh);
      soldierAimAt(al.mesh, al.pos, { x: best.pos.x, y: best.pos.y + 1.2, z: best.pos.z });
      if (Math.random() < 0.5) damageEnemy(best, 34);
    }
  }

  // försvara närmaste egna punkt — men förstärk hotade punkter i närheten
  let fc = null, fcd = Infinity;
  for (const c of capState) {
    if (c.owner === 'enemy') continue;
    let dc = Math.hypot(al.pos.x - c.pos[0], al.pos.z - c.pos[1]);
    if (c.progress > 0.1) dc -= 100; // punkt under attack → dit!
    if (dc < fcd) { fcd = dc; fc = c; }
  }
  if (!fc) fc = capState[capState.length - 1];
  const holdAt = [fc.pos[0] + al.holdX, fc.pos[1] + al.holdZ];
  const distHold = Math.hypot(al.pos.x - holdAt[0], al.pos.z - holdAt[1]);
  if (distHold > 6 && !(best && bd < 18)) {
    if (!al.path || al.target !== fc.id) {
      al.target = fc.id;
      al.path = findPath(nearestNode(al.pos.x, al.pos.z), nearestNode(fc.pos[0], fc.pos[1])) || [holdAt];
      al.pathI = 0;
    }
    let wp = al.path[Math.min(al.pathI, al.path.length - 1)];
    let dx = wp[0] - al.pos.x, dz = wp[1] - al.pos.z;
    let d = Math.hypot(dx, dz);
    if (d < 3 && al.pathI < al.path.length - 1) { al.pathI++; wp = al.path[al.pathI]; dx = wp[0] - al.pos.x; dz = wp[1] - al.pos.z; d = Math.hypot(dx, dz); }
    if (d > 0.1) {
      al.pos.x += dx / d * al.speed * dt;
      al.pos.z += dz / d * al.speed * dt;
      if (!best) al.mesh.rotation.y = Math.atan2(dx, dz);
      al.stuckT += dt;
      if (al.stuckT > 1.8) {
        const moved = Math.hypot(al.pos.x - (al.lastX ?? al.pos.x), al.pos.z - (al.lastZ ?? al.pos.z));
        if (moved < 1.0) { if (al.pathI < al.path.length - 1) al.pathI++; else al.path = null; }
        al.stuckT = 0; al.lastX = al.pos.x; al.lastZ = al.pos.z;
      }
    }
    collideBuildings(al.pos, 0.45);
    collideObstacles(al.pos, 0.45, al.pos.y);
    collideWalls(al.pos, 0.45, al.pos.y);
    al.pos.y = groundInfoAt(al.pos.x, al.pos.z).y;
    al.mesh.position.copy(al.pos);
    animateSoldier(al.mesh, d > 0.1, dt, 0.95);
    return;
  }
  animateSoldier(al.mesh, false, dt);
}

// ---------- capture logic ----------
function updateCaps(dt) {
  for (let i = 0; i < capState.length; i++) {
    const cap = capState[i];
    let eCount = 0;
    for (const en of enemies) {
      if (!en.dead && Math.hypot(en.pos.x - cap.pos[0], en.pos.z - cap.pos[1]) < cap.r) eCount++;
    }
    let fCount = 0;
    if (!player.dead && Math.hypot(player.pos.x - cap.pos[0], player.pos.z - cap.pos[1]) < cap.r) fCount++;
    for (const al of allies) {
      if (!al.dead && Math.hypot(al.pos.x - cap.pos[0], al.pos.z - cap.pos[1]) < cap.r) fCount++;
    }

    let cls = cap.owner;
    if (eCount > 0 && fCount === 0) {
      if (cap.owner !== 'enemy') {
        cap.progress += dt * 0.07 * Math.min(eCount, 3);
        cls = 'contested';
        if (cap.progress >= 1) {
          cap.owner = 'enemy'; cap.progress = 1;
          cap.beam.material.color.set(0xff4444);
          msg('⚠ Fienden har tagit ' + cap.name + '!');
          playTone(220, 0.5, 0.2, 'sawtooth');
          if (cap.id === 'C') { endGame(false); }
        }
      }
    } else if (fCount > 0 && eCount === 0) {
      if (cap.owner === 'enemy' || cap.progress > 0) {
        cap.progress -= dt * 0.1 * Math.min(fCount, 3);
        if (cap.owner === 'enemy') cls = 'contested';
        if (cap.progress <= 0) {
          cap.progress = 0;
          if (cap.owner === 'enemy') {
            cap.owner = 'friendly';
            cap.beam.material.color.set(0x4f9dff);
            msg('✔ ' + cap.name + ' återtaget! Frontlinjen flyttas ner.');
            playTone(660, 0.3, 0.15, 'sine');
          }
        }
      }
    } else if (eCount > 0 && fCount > 0) {
      cls = 'contested';
    }

    // HUD pill
    const pill = capPills[i];
    pill.className = 'cap ' + (cls === 'contested' ? 'contested' : cap.owner);
    const bar = pill.querySelector('.bar i');
    bar.style.width = (cap.progress * 100) + '%';
    bar.style.background = cap.owner === 'enemy' ? '#ff5a5a' : '#ffb14f';
    // beam pulse when contested
    cap.beam.material.opacity = cls === 'contested' ? 0.3 + Math.sin(clock.elapsedTime * 8) * 0.12 : 0.16;
  }
}

// ---------- waves ----------
function updateWaves(dt) {
  if (game.over) return;
  const alive = enemies.filter(e => !e.dead).length;
  if (game.toSpawn > 0) {
    game.spawnT -= dt;
    if (game.spawnT <= 0) {
      game.spawnT = 1.2;
      spawnEnemy();
      game.toSpawn--;
    }
  } else if (alive === 0) {
    game.betweenT -= dt;
    if (game.betweenT <= 0) {
      if (game.wave >= game.maxWave) { endGame(true); return; }
      game.wave++;
      game.toSpawn = 6 + game.wave * 2;
      game.spawnT = 0.5;
      game.betweenT = 9;
      document.getElementById('wavenum').textContent = 'Våg ' + game.wave + '/' + game.maxWave;
      msg('🔴 Våg ' + game.wave + ' — fienden rycker fram från flera håll!');
      playTone(440, 0.2, 0.15); setTimeout(() => playTone(550, 0.25, 0.15), 220);
      // stupade försvarare ersätts av förstärkningar från basen — de springer ner till fronten
      let reinforced = false;
      for (const al of allies) {
        if (al.dead) {
          al.dead = false; al.hp = 100; al.mesh.visible = true; al.mesh.rotation.x = 0;
          al.pos.set(D.spawn[0] + (Math.random() - 0.5) * 12, 0, D.spawn[1] + (Math.random() - 0.5) * 12);
          al.pos.y = groundInfoAt(al.pos.x, al.pos.z).y;
          al.mesh.position.copy(al.pos);
          al.path = null; al.target = null;
          reinforced = true;
        }
      }
      if (reinforced) msg('🔵 Förstärkning ansluter från Görjelycksgatan!');
    }
  }
}

function endGame(victory) {
  if (game.over) return;
  game.over = true;
  document.exitPointerLock();
  const ov = document.getElementById('overlay');
  ov.classList.remove('hidden');
  document.getElementById('title').textContent = victory ? 'KVARNBYN ÄR RÄDDAT!' : 'KVARNBYN HAR FALLIT';
  document.getElementById('title').style.color = victory ? '#7fd77f' : '#ff5a5a';
  ov.querySelector('h2').textContent = game.kills + ' fiender nedkämpade · ' + (victory ? 'Alla 8 vågor avvärjda. Görjelycksgatan sover tryggt inatt.' : 'Royens trappor föll. Ladda om sidan för revansch.');
  ov.querySelector('.panel').style.display = 'none';
  document.getElementById('gobtn').textContent = 'SPELA IGEN';
  document.getElementById('gobtn').onclick = () => location.reload();
}

// ---------- minimap ----------
const mmCanvas = document.getElementById('mm');
const mmCtx = mmCanvas.getContext('2d');
const mapCanvas = document.createElement('canvas');
{
  const SCALE = 1; // px per meter
  const w = Math.ceil(T.x1 - T.x0), h = Math.ceil(T.z0 - T.z1);
  mapCanvas.width = w; mapCanvas.height = h;
  const mc = mapCanvas.getContext('2d');
  mc.fillStyle = '#1c2620'; mc.fillRect(0, 0, w, h);
  const mapImg = new Image();
  mapImg.onload = () => {
    mc.drawImage(mapImg, 0, 0, w, h);
    // thin road overlay for readability
    mc.strokeStyle = 'rgba(255,255,255,0.35)'; mc.lineWidth = 1;
    for (const rd of D.roads) {
      if (rd.k === 'footway' || rd.k === 'path' || rd.k === 'steps') continue;
      mc.beginPath();
      rd.p.forEach((p, i) => { i ? mc.lineTo(p[0] - T.x0, p[1] - T.z1) : mc.moveTo(p[0] - T.x0, p[1] - T.z1); });
      mc.stroke();
    }
  };
  mapImg.src = 'ortho.jpg?v=3';
}
function drawMinimap() {
  const S = 1, R = 140; // map scale px/m, view radius px (=140 m radius)
  const ctx = mmCtx;
  const k = 220 / R; // map px → screen px
  ctx.clearRect(0, 0, 440, 440);
  const px = (player.pos.x - T.x0) * S, pz = (player.pos.z - T.z1) * S;
  ctx.save();
  ctx.beginPath(); ctx.arc(220, 220, 218, 0, Math.PI * 2); ctx.clip();
  ctx.drawImage(mapCanvas, px - R, pz - R, R * 2, R * 2, 0, 0, 440, 440);
  // caps
  for (const cap of capState) {
    const cx = 220 + ((cap.pos[0] - T.x0) * S - px) * k, cy = 220 + ((cap.pos[1] - T.z1) * S - pz) * k;
    ctx.fillStyle = cap.owner === 'enemy' ? '#ff5a5a' : '#4f9dff';
    ctx.beginPath(); ctx.arc(cx, cy, 9, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.font = 'bold 11px Arial'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(cap.id, cx, cy);
  }
  // enemies
  ctx.fillStyle = '#ff5a5a';
  for (const en of enemies) {
    if (en.dead) continue;
    const ex = 220 + ((en.pos.x - T.x0) * S - px) * k, ey = 220 + ((en.pos.z - T.z1) * S - pz) * k;
    if (Math.hypot(ex - 220, ey - 220) < 215) { ctx.beginPath(); ctx.arc(ex, ey, 3.5, 0, Math.PI * 2); ctx.fill(); }
  }
  // allies
  ctx.fillStyle = '#6db2ff';
  for (const al of allies) {
    if (al.dead) continue;
    const ex = 220 + ((al.pos.x - T.x0) * S - px) * k, ey = 220 + ((al.pos.z - T.z1) * S - pz) * k;
    if (Math.hypot(ex - 220, ey - 220) < 215) { ctx.beginPath(); ctx.arc(ex, ey, 3.5, 0, Math.PI * 2); ctx.fill(); }
  }
  // player arrow
  ctx.save();
  ctx.translate(220, 220);
  ctx.rotate(-player.yaw + Math.PI);
  ctx.fillStyle = '#ffd76a';
  ctx.beginPath(); ctx.moveTo(0, -8); ctx.lineTo(5, 6); ctx.lineTo(-5, 6); ctx.closePath(); ctx.fill();
  ctx.restore();
  ctx.restore();
}

// ---------- player update ----------
function updatePlayer(dt) {
  if (player.dead) {
    player.deadTimer -= dt;
    player.pitch = Math.max(player.pitch - dt, -1.2);
    if (player.deadTimer <= 0) {
      player.dead = false; player.hp = player.maxHp;
      player.pos.set(D.spawn[0], heightAt(D.spawn[0], D.spawn[1]), D.spawn[1]);
      player.vel.set(0, 0, 0);
      player.mag = player.magSize;
      const c = D.caps[2].pos;
      player.yaw = Math.atan2(-(c[0] - player.pos.x), -(c[1] - player.pos.z));
      player.pitch = 0;
      msg('Tillbaka i striden — försvara punkterna!');
    }
    return;
  }

  const gInfo = groundInfoAt(player.pos.x, player.pos.z);
  // i forsen? (nära å-segment och nere i den nedskurna fåran)
  const nr = nearestRiver(player.pos.x, player.pos.z);
  player.inWater = !!(nr && nr.d < 4.6 && player.pos.y < origHeightAt(player.pos.x, player.pos.z) - 1.1);

  let speed = (keys['ShiftLeft'] || keys['ShiftRight']) ? 8.2 : 5.2;
  if (player.inWater) speed *= 0.35;          // vada i strömmen
  else if (!gInfo.road) speed *= 0.8;         // gräs/terräng är segare än asfalt
  let mx = 0, mz = 0;
  if (keys['KeyW']) mz -= 1;
  if (keys['KeyS']) mz += 1;
  if (keys['KeyA']) mx -= 1;
  if (keys['KeyD']) mx += 1;
  const ml = Math.hypot(mx, mz);
  if (ml > 0) { mx /= ml; mz /= ml; }
  // forward = -Z in camera space rotated by yaw
  const fwdX = -Math.sin(player.yaw), fwdZ = -Math.cos(player.yaw);
  const rightX = Math.cos(player.yaw), rightZ = -Math.sin(player.yaw);
  let vx = (rightX * mx - fwdX * mz) * speed;
  let vz = (rightZ * mx - fwdZ * mz) * speed;

  const groundY = gInfo.y;
  if (player.onGround && keys['Space']) { player.vel.y = 5.2; player.onGround = false; }
  player.vel.y -= 14 * dt;
  player.pos.y += player.vel.y * dt;
  if (player.pos.y <= groundY && player.vel.y <= 0) {
    if (player.vel.y < -11) damagePlayer(Math.min(45, (-player.vel.y - 11) * 8)); // fallskada
    player.pos.y = groundY; player.vel.y = 0; player.onGround = true;
  }

  // axelvis förflyttning med branthetsspärr — branta sluttningar går inte att klättra,
  // halvbranta blir tunga (gatorna toppar på ~0.23 i lutningsdatan, bergssidorna ~0.5)
  // branthetsspärr med 1,6 m lookahead (per-frame-steg är för brusiga att mäta på).
  // Vägar/trappor är alltid gångbara, och i/vid åfåran får man alltid kravla.
  const nearCarve = nr && nr.d < 11;
  const tryMove = (dx, dz) => {
    let d = Math.hypot(dx, dz); if (d < 1e-7) return;
    if (player.onGround && !player.inWater && !nearCarve) {
      const ux = dx / d, uz = dz / d;
      const tx = player.pos.x + ux * 1.6, tz = player.pos.z + uz * 1.6;
      if (!groundInfoAt(tx, tz).road && !gInfo.road) {
        const grade = (heightAt(tx, tz) - heightAt(player.pos.x, player.pos.z)) / 1.6;
        if (grade > 0.38) return;               // spärr — ta gatan eller trappan
        if (grade > 0.26) { dx *= 0.5; dz *= 0.5; } // tung klättring
      }
    }
    player.pos.x += dx; player.pos.z += dz;
  };
  tryMove(vx * dt, 0);
  tryMove(0, vz * dt);
  // strömmen i forsen drar dig med nedströms
  if (player.inWater && nr) {
    player.pos.x += nr.seg.fx * 2.4 * dt;
    player.pos.z += nr.seg.fz * 2.4 * dt;
    if (!player.wetMsg) { player.wetMsg = true; msg('🌊 Du hamnade i forsen! Strömmen drar dig — kravla upp mot kanten!'); }
    if (nr.seg.steep) { // vitvattnet sliter
      player.waterDmg = (player.waterDmg || 0) + 4 * dt;
      if (player.waterDmg > 5) { player.waterDmg = 0; damagePlayer(5); }
    }
  } else player.wetMsg = false;
  collideBuildings(player.pos, 0.5);
  collideObstacles(player.pos, 0.5, player.pos.y);
  collideWalls(player.pos, 0.5, player.pos.y);
  // keep inside map
  player.pos.x = Math.max(T.x0 + 5, Math.min(T.x1 - 5, player.pos.x));
  player.pos.z = Math.max(T.z1 + 5, Math.min(T.z0 - 5, player.pos.z));
  if (player.onGround) {
    const gy = groundInfoAt(player.pos.x, player.pos.z).y;
    if (player.pos.y - gy > 0.55) player.onGround = false; // gick över en kant → fall
    else player.pos.y = gy;
  }

  // firing
  player.fireCooldown -= dt;
  if (firing && player.fireCooldown <= 0) playerShoot();

  // reload
  if (player.reloading) {
    player.reloadT -= dt;
    if (player.reloadT <= 0) {
      player.reloading = false;
      player.mag = player.magSize;
      document.getElementById('mag').textContent = player.mag;
      document.getElementById('reloadmsg').style.display = 'none';
      playTone(500, 0.08, 0.1, 'sine');
    }
  }

  // hp regen
  if (clock.elapsedTime - player.lastHurt > 6 && player.hp < player.maxHp) {
    player.hp = Math.min(player.maxHp, player.hp + 8 * dt);
  }

  // camera
  const bobbing = ml > 0 && player.onGround ? Math.sin(clock.elapsedTime * 10) * 0.04 : 0;
  camera.position.set(player.pos.x, player.pos.y + 1.7 + bobbing, player.pos.z);
  camera.rotation.set(player.pitch, player.yaw, 0, 'YXZ');

  // gun kick + sway
  gunKick = Math.max(0, gunKick - dt * 8);
  gun.position.z = -0.5 + gunKick * 0.06;
  gun.rotation.x = gunKick * 0.08;
  gun.position.y = -0.22 + bobbing * 0.5;
}

// ---------- HUD update ----------
function updateHUD() {
  document.getElementById('hpfill').style.width = player.hp + '%';
  document.getElementById('hpfill').style.background = player.hp > 50
    ? 'linear-gradient(90deg,#3fae5a,#7fd77f)'
    : 'linear-gradient(90deg,#c0392b,#e67e22)';
  const hurt = Math.max(0, 1 - (clock.elapsedTime - player.lastHurt) * 1.5);
  document.getElementById('vignette').style.opacity = player.dead ? 0.85 : hurt * 0.8 + (1 - player.hp / 100) * 0.25;
}

// ---------- main loop ----------
const clock = new THREE.Clock();
let mmT = 0;

function frame(dt) {
  if (game.started && !game.over) {
    updatePlayer(dt);
    for (let i = enemies.length - 1; i >= 0; i--) updateEnemy(enemies[i], dt);
    for (const al of allies) updateAlly(al, dt);
    updateCaps(dt);
    updateWaves(dt);
    updateHUD();
    mmT -= dt;
    if (mmT <= 0) {
      mmT = 0.08;
      drawMinimap();
      // fade nearby-only labels; districts stay visible far away
      for (const spr of markSprites) {
        const d = Math.hypot(spr.position.x - player.pos.x, spr.position.z - player.pos.z);
        const far = spr.userData.kind === 'district' ? 1600 : 500;
        spr.material.opacity = Math.max(0, Math.min(1, (far - d) / 150));
      }
      // forsens brus stiger när man närmar sig
      if (riverGainNode) {
        const nrA = nearestRiver(player.pos.x, player.pos.z);
        const dd = nrA ? nrA.d : 999;
        riverGainNode.gain.value = Math.min(0.4, Math.max(0, 0.16 * (1 - dd / 60)) * (player.inWater ? 2.5 : 1));
      }
    }
  }

  // tracers fade
  for (let i = tracers.length - 1; i >= 0; i--) {
    tracers[i].life -= dt;
    tracers[i].line.material.opacity = Math.max(0, tracers[i].life / 0.09);
    if (tracers[i].life <= 0) { scene.remove(tracers[i].line); tracers.splice(i, 1); }
  }
  flash.intensity = Math.max(0, flash.intensity - dt * 40);
  waterTex.offset.y = (waterTex.offset.y - dt * 0.55) % 1; // forsen strömmar

  renderer.render(scene, camera);
}

function animate() {
  requestAnimationFrame(animate);
  frame(Math.min(0.05, clock.getDelta()));
}
animate();

// debug hooks (used by automated playtesting; harmless in normal play)
window.__frame = (dt) => { clock.elapsedTime += dt; frame(dt); };
window.__game = { game, player, enemies, allies, capState, spawnEnemy, D, heightAt, scene, terrainMesh, orthoTex, renderer, camera, wallSegs };
window.__keys = keys;
window.__fire = () => playerShoot();
window.__look = (yaw, pitch) => { player.yaw = yaw; player.pitch = pitch; };

// ---------- start ----------
const overlay = document.getElementById('overlay');
overlay.addEventListener('click', () => {
  if (game.over) return;
  overlay.classList.add('hidden');
  audio();
  startAmbient();
  canvas.requestPointerLock();
  if (!game.started) {
    game.started = true;
    msg('⚠ Gamla Torget har fallit — fienden är på väg uppför backarna. Mota ner dem!');
  }
});
canvas.addEventListener('click', () => {
  if (game.started && !game.over && !locked) canvas.requestPointerLock();
});
