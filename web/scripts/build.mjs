// Builds the static site in web/dist/ (what GitHub Pages serves): src/ as it is (no bundler), the AI's runtime
// and the trained versions. `npm run build`, or `npm start` to build and serve it.
import { cpSync, existsSync, readFileSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";

const web = (path) => fileURLToPath(new URL(`../${path}`, import.meta.url)); // paths from web/, whatever the cwd
const MODELS = web("../models");
const OUT = web("dist");

rmSync(OUT, { recursive: true, force: true });
cpSync(web("src"), OUT, { recursive: true });

// ONNX Runtime Web: the module (with its JS glue inside) and the WebAssembly it loads from next to itself.
// Its MIT license and third-party notices are in src/licenses/.
for (const file of ["ort.wasm.bundle.min.mjs", "ort-wasm-simd-threaded.wasm"]) {
  cpSync(web(`node_modules/onnxruntime-web/dist/${file}`), `${OUT}/vendor/${file}`);
}

// Every version the menu lists needs its .onnx (rl/export.py; train.py exports each new version)
cpSync(`${MODELS}/versions.csv`, `${OUT}/models/versions.csv`);
const versions = readFileSync(`${MODELS}/versions.csv`, "utf8").trim().split(/\r?\n/).slice(1).map((row) => row.split(",")[0]);
for (const version of versions) {
  if (!existsSync(`${MODELS}/${version}.onnx`)) throw new Error(`models/${version}.onnx is missing: run \`python -m rl.export\``);
  cpSync(`${MODELS}/${version}.onnx`, `${OUT}/models/${version}.onnx`);
}
console.log(`built web/dist/ with ${versions.length} versions (${versions[0]}–${versions.at(-1)})`);
