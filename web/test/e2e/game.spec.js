// The whole game in a real browser (Chromium, Firefox and WebKit): `npm run test:e2e`.
// Every test also fails on a console error, an uncaught exception or a request outside the site.
import { readFileSync } from "node:fs";

import { test as base, expect } from "@playwright/test";

const [HEADER, ...ROWS] = readFileSync("../models/versions.csv", "utf8").trim().split(/\r?\n/).map((r) => r.split(","));
const VERSIONS = ROWS.map((r) => Object.fromEntries(r.map((v, k) => [HEADER[k], v])));
const NEWEST = VERSIONS.at(-1);

const test = base.extend({
  page: async ({ page, baseURL }, use) => {
    const problems = [];
    page.on("console", (m) => m.type() === "error" && problems.push(`console error: ${m.text()}`));
    page.on("pageerror", (e) => problems.push(`uncaught: ${e.message}`));
    page.on("request", (r) => {
      if (!r.url().startsWith(baseURL) && !r.url().startsWith("data:")) problems.push(`request outside the site: ${r.url()}`);
    });
    await use(page);
    expect(problems).toEqual([]);
  },
});

const snapshot = (page) => page.evaluate(() => window.tankAI.snapshot());
/** A mode's card: clicking anywhere on it starts that mode. */
const card = (page, mode) => page.locator(`.mode.${mode}`);

async function openStart(page) {
  await page.goto("/");
  await page.keyboard.press("m"); // silent tests: nothing plays before the first game, so this comes first
  await expect(page.locator("#play-ai")).toBeEnabled({ timeout: 30_000 });
}

/** Click a mode's card, then wait for the round to start. */
async function start(page, mode) {
  await card(page, mode).click({ position: { x: 24, y: 24 } });
  await expect.poll(async () => (await snapshot(page)).screen).toBe("game");
  await expect.poll(async () => (await snapshot(page)).phase, { timeout: 10_000 }).toBe("playing");
}

async function hold(page, key, ms) {
  await page.keyboard.down(key);
  await page.waitForTimeout(ms);
  await page.keyboard.up(key);
}

test("start screen: the newest version is picked, and two AIs play live with the brain on screen", async ({ page }) => {
  await openStart(page);
  await expect(page.locator("#version option")).toHaveCount(VERSIONS.length);
  await expect(page.locator("#version")).toHaveValue(NEWEST.version);
  await expect(page.locator("#version-info")).toContainText(`${Math.round(NEWEST.win_rate * 100)}% of its rounds`);
  await expect(page.locator("#score")).toContainText(NEWEST.version);
  await expect(page.locator(".brain")).toBeVisible();

  const before = (await snapshot(page)).tanks;
  await expect.poll(async () => (await snapshot(page)).brain, { timeout: 15_000 }).not.toBeNull();
  await expect.poll(async () => JSON.stringify((await snapshot(page)).tanks), { timeout: 15_000 })
    .not.toBe(JSON.stringify(before));
});

test("vs AI: a countdown, then you drive Blue while the AI drives Red, its brain thinking on the side", async ({ page }) => {
  await openStart(page);
  await card(page, "ai").click({ position: { x: 24, y: 24 } });
  await expect(page.locator("#banner")).toHaveText(/^[123]$/); // a busy machine may already be past the 3
  await expect(page.locator("#score")).toHaveText(new RegExp(`^You 0\\s+-\\s+0 ${NEWEST.version}$`));
  await expect.poll(async () => (await snapshot(page)).phase, { timeout: 10_000 }).toBe("playing");
  await expect(page.locator(".brain")).toBeVisible();
  await expect.poll(async () => (await snapshot(page)).brain).not.toBeNull();

  const start = await snapshot(page);
  await hold(page, "a", 400);
  expect((await snapshot(page)).tanks[1].angle).not.toBe(start.tanks[1].angle);
  await expect.poll(async () => JSON.stringify((await snapshot(page)).tanks[0]), { timeout: 10_000 })
    .not.toBe(JSON.stringify(start.tanks[0]));
});

test("pause: Esc and leaving the window pause it, Restart starts over, Menu goes back", async ({ page }) => {
  await openStart(page);
  await start(page, "ai");
  await page.keyboard.press("Escape");
  const paused = page.getByRole("dialog", { name: "Paused" });
  await expect(paused).toBeVisible();
  const frozen = await snapshot(page);
  await page.waitForTimeout(500);
  expect((await snapshot(page)).tanks).toEqual(frozen.tanks);
  await page.keyboard.press("Escape");
  await expect(paused).toBeHidden();

  await page.evaluate(() => window.dispatchEvent(new Event("blur")));
  await expect(paused).toBeVisible();
  await page.getByRole("button", { name: "Restart" }).click();
  await expect(paused).toBeHidden();
  expect(await snapshot(page)).toMatchObject({ screen: "game", round: 1, score: [0, 0], phase: "countdown" });

  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Menu" }).click();
  await expect(page.locator("#menu")).toBeVisible();
  expect((await snapshot(page)).screen).toBe("menu");
});

test("F1 shows what the AI sees and M mutes, from the keyboard or the buttons", async ({ page }) => {
  await openStart(page);
  await page.keyboard.press("F1");
  await expect(page.getByRole("button", { name: /AI view/ })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#legend")).toBeVisible();
  await page.getByRole("button", { name: /AI view/ }).click();
  await expect(page.locator("#legend")).toBeHidden();
  expect((await snapshot(page)).muted).toBe(true); // openStart pressed M
  await expect(page.getByRole("button", { name: /Mute/ })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: /Mute/ }).click();
  expect((await snapshot(page)).muted).toBe(false);
  await page.keyboard.press("m");
  expect((await snapshot(page)).muted).toBe(true);
});

test("2 players: each tank answers to its own keys only, and there's no AI brain", async ({ page }) => {
  await openStart(page);
  await start(page, "pvp");
  await expect(page.locator("#score")).toHaveText(/^Blue 0\s+-\s+0 Red$/);
  await expect(page.locator(".brain")).toBeHidden();

  const start0 = await snapshot(page);
  await hold(page, "d", 300);
  const blueTurned = await snapshot(page);
  expect(blueTurned.tanks[1].angle).not.toBe(start0.tanks[1].angle);
  expect(blueTurned.tanks[0]).toEqual(start0.tanks[0]);
  await hold(page, "ArrowRight", 300);
  const redTurned = await snapshot(page);
  expect(redTurned.tanks[0].angle).not.toBe(blueTurned.tanks[0].angle);
  expect(redTurned.tanks[1]).toEqual(blueTurned.tanks[1]);
  expect(await page.evaluate(() => scrollY)).toBe(0); // the arrows didn't scroll the page
});

test("rounds go on like the desktop game: a result, then a new map and the next round", async ({ page }) => {
  test.setTimeout(120_000);
  await openStart(page);
  await start(page, "ai");
  // Spin and keep shooting: bullets fly everywhere, and someone gets hit soon
  await page.keyboard.down("a");
  await page.keyboard.down(" ");
  await expect.poll(async () => (await snapshot(page)).phase, { timeout: 90_000, intervals: [100] }).toBe("roundOver");
  await expect(page.locator("#banner")).toHaveText(new RegExp(`^(You win|${NEWEST.version} wins|Draw)$`));
  await page.keyboard.up("a");
  await page.keyboard.up(" ");
  await expect.poll(async () => (await snapshot(page)).round, { timeout: 5_000 }).toBe(2);
  const s = await snapshot(page);
  expect(s.score[0] + s.score[1]).toBeLessThanOrEqual(1);
});

test("keyboard only: Enter on the start screen plays the AI", async ({ page }) => {
  await openStart(page);
  await page.keyboard.press("Enter");
  await expect.poll(async () => (await snapshot(page)).screen).toBe("game");
  await expect(page.locator("#score")).toContainText("You");
});

test("footer: GitHub, and the privacy and license notes open and close, with the license files served", async ({ page, request }) => {
  await openStart(page);
  await expect(page.getByRole("link", { name: "Source code on GitHub" })).toHaveAttribute("href", "https://github.com/Waffle639/Tank-AI");
  await page.getByRole("button", { name: "Privacy" }).click();
  await expect(page.locator("#privacy")).toBeVisible();
  await expect(page.locator("#privacy")).toContainText("No accounts, cookies, analytics or forms");
  await page.keyboard.press("Escape");
  await expect(page.locator("#privacy")).toBeHidden();
  await page.getByRole("button", { name: "Licenses" }).click();
  await expect(page.locator("#licenses")).toBeVisible();
  for (const href of await page.locator("#licenses a[href^='licenses/']").evaluateAll((as) => as.map((a) => a.href))) {
    expect((await request.get(href)).status(), href).toBe(200);
  }
});

test("on a phone-sized screen the start screen goes under the map and nothing scrolls sideways", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openStart(page);
  const map = await page.locator("#board").boundingBox();
  const menu = await page.locator("#menu").boundingBox();
  expect(menu.y).toBeGreaterThanOrEqual(map.y + map.height - 1); // 1 px: browsers round layout differently
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
