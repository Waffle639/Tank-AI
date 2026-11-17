// A small static server for web/dist/, for `npm start` and the Playwright tests. The real site is on GitHub Pages.
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("../dist", import.meta.url));
const PORT = Number(process.env.PORT ?? 8000);
const TYPES = {
  ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".mjs": "text/javascript",
  ".wasm": "application/wasm", ".onnx": "application/octet-stream", ".csv": "text/csv",
  ".txt": "text/plain; charset=utf-8",
};

createServer(async (req, res) => {
  const path = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
  const file = resolve(join(ROOT, path.endsWith("/") ? `${path}index.html` : path));
  if (!file.startsWith(ROOT + sep)) { // no ../ out of dist/
    res.writeHead(403).end();
    return;
  }
  try {
    const body = await readFile(file);
    res.writeHead(200, { "Content-Type": TYPES[extname(file)] ?? "application/octet-stream" }).end(body);
  } catch (error) {
    if (error.code !== "ENOENT") console.error(`${path}: ${error.code} ${error.message}`);
    res.writeHead(error.code === "ENOENT" ? 404 : 500, { "Content-Type": "text/plain" }).end(error.code);
  }
}).listen(PORT, "127.0.0.1", () => console.log(`serving web/dist/ on http://127.0.0.1:${PORT}/`));
