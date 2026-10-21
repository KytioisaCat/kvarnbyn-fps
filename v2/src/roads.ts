// Vägmeshar från tools/v2model (roads.json + roads.bin): asfalt, kantsten, brodäck, betong,
// räcken, trappor. Varje triangel har egna vertex → plana normaler (skarpa kanter) gratis.
import * as THREE from 'three';
import { DATA_URL, fetchBlob } from './world';

interface RoadsMeta {
  materials: Record<string, { posOffset: number; posCount: number; idxOffset: number; idxCount: number }>;
}

const MATERIALS: Record<string, THREE.MeshStandardMaterial> = {
  asphalt: new THREE.MeshStandardMaterial({ color: 0x34363a, roughness: 0.93, metalness: 0 }),
  steps: new THREE.MeshStandardMaterial({ color: 0x8e8b86, roughness: 0.85 }),
  kerb: new THREE.MeshStandardMaterial({ color: 0xb3b0a8, roughness: 0.8 }),
  deck: new THREE.MeshStandardMaterial({ color: 0x3b3d41, roughness: 0.9 }),
  concrete: new THREE.MeshStandardMaterial({ color: 0x9d9a93, roughness: 0.85 }),
  rail: new THREE.MeshStandardMaterial({ color: 0x3a3e44, roughness: 0.45, metalness: 0.6, side: THREE.DoubleSide }),
};

export async function loadRoads(say: (s: string) => void): Promise<THREE.Group> {
  const meta = (await (await fetch(`${DATA_URL}roads.json`, { cache: 'no-cache' })).json()) as RoadsMeta;
  const blob = await fetchBlob(`${DATA_URL}roads.bin`, 'vägar', say);
  const buf = await blob.arrayBuffer();
  const group = new THREE.Group();
  group.name = 'roads';
  let tris = 0;
  for (const [name, m] of Object.entries(meta.materials)) {
    const pos = new Float32Array(buf, m.posOffset, m.posCount * 3);
    const idx = new Uint32Array(buf, m.idxOffset, m.idxCount);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setIndex(new THREE.BufferAttribute(idx, 1));
    g.computeVertexNormals();
    g.computeBoundingSphere();
    const mesh = new THREE.Mesh(g, MATERIALS[name] ?? MATERIALS.concrete);
    mesh.name = name;
    mesh.castShadow = name !== 'asphalt';
    mesh.receiveShadow = true;
    group.add(mesh);
    tris += m.idxCount / 3;
  }
  say(`vägar: ${(tris / 1000).toFixed(0)} k tri`);
  return group;
}
