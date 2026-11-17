// The keyboard: which keys are held, and the keys that drive each tank.
// Keys are read by event.code, the physical key, so WASD stays in place on any keyboard layout.

export const BLUE_KEYS = [["KeyW"], ["KeyS"], ["KeyA"], ["KeyD"], ["Space"]]; // forward, back, left, right, shoot
export const RED_KEYS = [["ArrowUp"], ["ArrowDown"], ["ArrowLeft"], ["ArrowRight"], ["Enter", "NumpadEnter"]];
export const SOLO_KEYS = BLUE_KEYS.map((codes, k) => [...codes, ...RED_KEYS[k]]); // against the AI, either set
export const GAME_KEYS = new Set(SOLO_KEYS.flat()); // while playing they must not scroll the page or press a button

export class Keyboard {
  constructor(target = window) {
    this.held = new Set();
    target.addEventListener("keydown", (e) => this.held.add(e.code));
    target.addEventListener("keyup", (e) => this.held.delete(e.code));
    target.addEventListener("blur", () => this.held.clear()); // no key stays stuck after switching windows
  }

  /** A driver for Match: the buttons of keyset that are held right now. */
  driver(keyset) {
    return () => keyset.map((codes) => codes.some((c) => this.held.has(c)));
  }

  clear() {
    this.held.clear();
  }
}
