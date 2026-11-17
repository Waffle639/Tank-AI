// A trained version (models/vNNN.onnx, made by rl/export.py) run with ONNX Runtime Web.
// In the browser "onnxruntime-web" comes from the import map in index.html; in Node (the tests) from node_modules.
import * as ort from "onnxruntime-web";
import { OBS_SIZE, observe } from "./observation.js";

export const FRAME_SKIP = 4; // game ticks per decision (15 decisions/s), as in training (rl/env.py)

// Several threads need cross-origin isolation headers, which GitHub Pages can't send. One is plenty for 85k weights.
ort.env.wasm.numThreads = 1;

/** source: the .onnx file's URL, or its bytes. */
export function loadPolicy(source) {
  return ort.InferenceSession.create(source);
}

/**
 * One pass through the network: { inputs, hidden, probs }. inputs: the 70 numbers it sees, hidden: each hidden
 * layer's activations (256 each), probs: the chance of pressing each of the 5 buttons.
 */
export async function think(session, inputs) {
  const out = await session.run({ obs: new ort.Tensor("float32", Float32Array.from(inputs), [1, OBS_SIZE]) });
  const hidden = Object.keys(out).filter((k) => k.startsWith("hidden")).sort().map((k) => out[k].data);
  return { inputs, hidden, probs: Array.from(out.probs.data) };
}

/**
 * A tank driven by the policy, for Match: it decides every FRAME_SKIP ticks and holds its buttons in between,
 * like in training. Each button is pressed with the chance the network gives, like SB3's predict.
 * driver.thought is its last decision ({ inputs, hidden, probs, buttons }), for the brain panel.
 */
export function aiDriver(session, i, random = Math.random) {
  const driver = async (game, tick) => {
    if (tick % FRAME_SKIP === 0) {
      const thought = await think(session, observe(game, i));
      driver.thought = { ...thought, buttons: thought.probs.map((p) => random() < p) };
    }
    return driver.thought.buttons;
  };
  driver.thought = null;
  return driver;
}
