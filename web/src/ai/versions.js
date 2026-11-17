// The trained versions: their list (models/versions.csv, written by train.py) and their networks, each loaded once.
import { loadPolicy } from "./policy.js";

/** Every version, newest first: { version, opponents, win_rate, self_kill_rate, ... }. Odd rows are skipped. */
export async function loadVersions() {
  const response = await fetch("models/versions.csv");
  if (!response.ok) throw new Error(`models/versions.csv: ${response.status}`);
  const [header, ...rows] = (await response.text()).trim().split(/\r?\n/);
  const keys = header.split(",");
  return rows.map((row) => Object.fromEntries(row.split(",").map((v, k) => [keys[k], v])))
    .filter((v) => /^v\d+$/.test(v.version) && /^[v\d ]+$/.test(v.opponents))
    .reverse();
}

/** "v001 v002 v003" -> "v001–v003". */
export function trainedAgainst(opponents) {
  const names = opponents.split(" ");
  if (names[0] === "v0") return "a tank that stands still";
  return names.length > 1 ? `${names[0]}–${names.at(-1)}` : names[0];
}

/** The ONNX sessions, loaded on first use. onChange runs whenever one finishes loading or fails. */
export class Policies {
  constructor(onChange) {
    this.onChange = onChange;
    this.loading = new Map(); // version -> Promise of its session
    this.ready = new Set();
    this.failed = new Set();
  }

  get(version) {
    if (!this.loading.has(version)) {
      this.failed.delete(version);
      const loading = loadPolicy(`models/${version}.onnx`);
      this.loading.set(version, loading);
      loading.then(() => this.ready.add(version), (error) => {
        console.error(error);
        this.failed.add(version);
        this.loading.delete(version); // asking again retries
      }).finally(() => this.onChange());
    }
    return this.loading.get(version);
  }
}
