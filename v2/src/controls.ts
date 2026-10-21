// FPS-styrning: mus (pointer lock) + WASD/piltangenter på dator; på telefon vänster halva =
// rörelsespak, höger halva = titta. Samma känsla som v1 (yaw/pitch i radianer).
import * as THREE from 'three';

export class FpsControls {
  yaw = Math.PI;      // 0 = norr (−z); π = tittar söderut
  pitch = -0.05;
  /** önskad rörelse i kamerans plan: x = höger, y = fram (−1..1) */
  move = new THREE.Vector2();
  sprint = false;
  private keys = new Set<string>();
  private moveTouch: { id: number; x0: number; y0: number } | null = null;
  private lookTouch: { id: number; x: number; y: number } | null = null;
  readonly isTouch = matchMedia('(pointer: coarse)').matches;

  constructor(private readonly dom: HTMLElement) {
    addEventListener('keydown', (e) => { this.keys.add(e.code); if (e.code === 'Space') e.preventDefault(); });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());
    dom.addEventListener('mousemove', (e) => {
      if (document.pointerLockElement !== dom) return;
      this.look(-e.movementX * 0.0022, -e.movementY * 0.0022);
    });
    dom.addEventListener('touchstart', (e) => {
      for (const t of Array.from(e.changedTouches)) {
        if (t.clientX < innerWidth / 2 && !this.moveTouch) this.moveTouch = { id: t.identifier, x0: t.clientX, y0: t.clientY };
        else if (!this.lookTouch) this.lookTouch = { id: t.identifier, x: t.clientX, y: t.clientY };
      }
      e.preventDefault();
    }, { passive: false });
    dom.addEventListener('touchmove', (e) => {
      for (const t of Array.from(e.changedTouches)) {
        if (this.moveTouch && t.identifier === this.moveTouch.id) {
          const dx = (t.clientX - this.moveTouch.x0) / 55, dy = (t.clientY - this.moveTouch.y0) / 55;
          const len = Math.hypot(dx, dy);
          const k = len > 1 ? 1 / len : 1;
          this.move.set(dx * k, -dy * k);
          this.sprint = len > 1.35;
        } else if (this.lookTouch && t.identifier === this.lookTouch.id) {
          this.look(-(t.clientX - this.lookTouch.x) * 0.0045, -(t.clientY - this.lookTouch.y) * 0.0045);
          this.lookTouch.x = t.clientX; this.lookTouch.y = t.clientY;
        }
      }
      e.preventDefault();
    }, { passive: false });
    const end = (e: TouchEvent) => {
      for (const t of Array.from(e.changedTouches)) {
        if (this.moveTouch && t.identifier === this.moveTouch.id) { this.moveTouch = null; this.move.set(0, 0); this.sprint = false; }
        if (this.lookTouch && t.identifier === this.lookTouch.id) this.lookTouch = null;
      }
    };
    dom.addEventListener('touchend', end);
    dom.addEventListener('touchcancel', end);
  }

  lock(): void { if (!this.isTouch) this.dom.requestPointerLock?.(); }

  look(dyaw: number, dpitch: number): void {
    this.yaw += dyaw;
    this.pitch = Math.max(-1.45, Math.min(1.45, this.pitch + dpitch));
  }

  /** uppdatera rörelsevektorn från tangentbordet (touch skriver direkt i `move`) */
  poll(): void {
    if (this.moveTouch) return;
    const k = this.keys;
    const x = (k.has('KeyD') || k.has('ArrowRight') ? 1 : 0) - (k.has('KeyA') || k.has('ArrowLeft') ? 1 : 0);
    const y = (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0) - (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0);
    const len = Math.hypot(x, y) || 1;
    this.move.set(x / len, y / len);
    this.sprint = k.has('ShiftLeft') || k.has('ShiftRight');
  }

  applyTo(camera: THREE.Camera): void { camera.rotation.set(this.pitch, this.yaw, 0, 'YXZ'); }

  /** rörelseriktning i världen (horisontell), ur yaw + move */
  worldMove(out: THREE.Vector3): THREE.Vector3 {
    const fx = -Math.sin(this.yaw), fz = -Math.cos(this.yaw);   // fram
    const rx = Math.cos(this.yaw), rz = -Math.sin(this.yaw);    // höger
    return out.set(fx * this.move.y + rx * this.move.x, 0, fz * this.move.y + rz * this.move.x);
  }
}
