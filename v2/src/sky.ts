// Dagsljus: procedurell himmel (three/addons Sky), sol som kaskadlös skuggkastare som följer
// spelaren, hemisfärljus + himlen som IBL (PMREM). Kvällsläge kommer i M4.
import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';

export class Daylight {
  readonly sky = new Sky();
  readonly sun = new THREE.DirectionalLight(0xfff1dc, 3.2);
  readonly hemi = new THREE.HemisphereLight(0xcfe0ff, 0x5a5440, 0.35);
  readonly dir = new THREE.Vector3(0, 1, 0);   // riktning MOT solen
  private envRT: THREE.WebGLRenderTarget | null = null;

  constructor(private readonly renderer: THREE.WebGLRenderer, private readonly scene: THREE.Scene, mobile: boolean) {
    this.sky.scale.setScalar(20000);
    const u = this.sky.material.uniforms;
    u.turbidity.value = 5; u.rayleigh.value = 1.6; u.mieCoefficient.value = 0.004; u.mieDirectionalG.value = 0.8;
    scene.add(this.sky, this.hemi, this.sun, this.sun.target);
    const s = this.sun.shadow;
    s.mapSize.set(mobile ? 2048 : 4096, mobile ? 2048 : 4096);
    const R = 110;
    s.camera.left = -R; s.camera.right = R; s.camera.top = R; s.camera.bottom = -R;
    s.camera.near = 1; s.camera.far = 900;
    s.bias = -0.0004; s.normalBias = 0.6;
    this.sun.castShadow = true;
    this.setSun(34, 222);   // eftermiddag i sydväst
  }

  /** elevation och kompass-azimut (0 = N, 90 = Ö, 180 = S, 270 = V) i grader */
  setSun(elevDeg: number, azDeg: number): void {
    const el = THREE.MathUtils.degToRad(elevDeg), az = THREE.MathUtils.degToRad(azDeg);
    this.dir.set(Math.cos(el) * Math.sin(az), Math.sin(el), -Math.cos(el) * Math.cos(az)).normalize();
    this.sky.material.uniforms.sunPosition.value.copy(this.dir);
    this.sun.intensity = 3.2 * Math.max(0.1, Math.sin(el)) ** 0.5;
    this.bakeEnvironment();
  }

  private bakeEnvironment(): void {
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const envScene = new THREE.Scene();
    const skyCopy = new Sky();
    skyCopy.scale.setScalar(20000);
    const src = this.sky.material.uniforms, dst = skyCopy.material.uniforms;
    for (const k of ['turbidity', 'rayleigh', 'mieCoefficient', 'mieDirectionalG'] as const) dst[k].value = src[k].value;
    dst.sunPosition.value.copy(this.dir);
    envScene.add(skyCopy);
    this.envRT?.dispose();
    this.envRT = pmrem.fromScene(envScene);
    this.scene.environment = this.envRT.texture;
    this.scene.environmentIntensity = 0.55;
    pmrem.dispose();
  }

  /** flytta skuggkameran med spelaren så upplösningen alltid läggs där man är */
  follow(target: THREE.Vector3): void {
    this.sun.target.position.copy(target);
    this.sun.position.copy(target).addScaledVector(this.dir, 400);
    this.sun.target.updateMatrixWorld();
  }
}
