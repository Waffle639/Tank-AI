// End-to-end tests of the web game in the three browser engines: `npm run test:e2e`.
import { defineConfig, devices } from "@playwright/test";

const PORT = 4173;

export default defineConfig({
  testDir: "test/e2e",
  timeout: 60_000, // each page compiles ONNX Runtime's 14.8 MB of WebAssembly, slow with many browsers at once
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: { baseURL: `http://127.0.0.1:${PORT}/`, trace: "retain-on-failure", screenshot: "only-on-failure" },
  webServer: {
    command: "npm run build && node scripts/serve.mjs",
    env: { PORT: String(PORT) },
    url: `http://127.0.0.1:${PORT}/`,
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
});
