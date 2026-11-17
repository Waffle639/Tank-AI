// Entry point: wires the pieces together and runs the loop.
//   screens: menu (a live AI-vs-AI demo behind the start screen) -> game <-> paused
//   loop: fixed 60 Hz game ticks like main.py, drawn on every animation frame
import { aiDriver } from "./ai/policy.js";
import { Policies, loadVersions } from "./ai/versions.js";
import { FPS, HEIGHT, WIDTH } from "./game/config.js";
import { Game } from "./game/game.js";
import { BLUE_KEYS, GAME_KEYS, Keyboard, RED_KEYS, SOLO_KEYS } from "./play/controls.js";
import { Match } from "./play/match.js";
import { Brain } from "./ui/brain.js";
import { Effects } from "./ui/effects.js";
import { Hud } from "./ui/hud.js";
import { Menu } from "./ui/menu.js";
import { draw } from "./ui/render.js";
import { Sound } from "./ui/sound.js";

const TICK_MS = 1000 / FPS;
const DEMO_ROUND = 60; // s before a demo round is cut, like TIME_LIMIT in rl/env.py: two AIs may never meet
const STILL = () => [false, false, false, false, false];

const $ = (id) => document.getElementById(id);
const stage = $("stage"), canvas = $("board"), ctx = canvas.getContext("2d");
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const keyboard = new Keyboard();
const sound = new Sound();
const hud = new Hud({ score: $("score"), notice: $("notice"), banner: $("banner") });
const brain = new Brain($("brain-canvas"));
const policies = new Policies(() => menu.update(policies));
const menu = new Menu((choice) => startGame(choice));

let screen = "menu"; // menu | game | paused
let aiView = false;

/**
 * A view is a match and what's needed to show it. brainOf: the tank whose network the brain panel shows
 * (null: no AI, no panel). labels: the text over each tank at the start of a round.
 */
function makeView({ drivers, names, labels, brainOf, demo = false, choice = null }) {
  const match = new Match(new Game(), drivers, demo ? DEMO_ROUND * FPS : Infinity);
  return { match, names, labels, brainOf, demo, choice, effects: new Effects(reducedMotion) };
}

let demo = makeView({ drivers: [STILL, STILL], names: ["", ""], labels: null, brainOf: 1, demo: true });
let view = demo;

// ---- Screens ----

async function startDemo(versions) {
  // The two newest versions play each other behind the start screen
  const [blue, red = blue] = versions.map((v) => v.version);
  const [redSession, blueSession] = await Promise.all([policies.get(red), policies.get(blue)]);
  demo = makeView({ drivers: [aiDriver(redSession, 0), aiDriver(blueSession, 1)], names: [red, blue],
    labels: [red, blue], brainOf: 1, demo: true });
  if (screen === "menu") show(demo);
}

async function startGame(choice) {
  sound.start(); // a click or a key press got us here, so the browser allows sound now
  const ai = choice.mode === "ai";
  show(makeView({
    choice,
    drivers: ai ? [aiDriver(await policies.get(choice.version), 0), keyboard.driver(SOLO_KEYS)]
      : [keyboard.driver(RED_KEYS), keyboard.driver(BLUE_KEYS)],
    names: ai ? [choice.version, "You"] : ["Red", "Blue"],
    labels: ai ? [choice.version, "YOU"] : ["ARROWS", "WASD"],
    brainOf: ai ? 0 : null,
  }));
  setScreen("game");
}

function show(next) {
  view = next;
  stage.dataset.brain = next.brainOf === null ? "off" : "on";
  $("brain-name").textContent = next.names[next.brainOf] ?? "";
  brain.resize();
}

function setScreen(next) {
  screen = next;
  stage.dataset.screen = next;
  $("menu").hidden = next !== "menu";
  $("pause").hidden = next !== "paused";
  if (next === "game") canvas.focus();
  if (next === "paused") $("resume").focus();
}

function togglePause() {
  if (screen === "game") setScreen("paused");
  else if (screen === "paused") setScreen("game");
}

function toMenu() {
  keyboard.clear();
  show(demo);
  setScreen("menu");
  menu.update(policies);
  $("play-ai").focus();
}

// ---- The loop ----

let last = performance.now(), acc = 0;

async function frame(now) {
  acc += Math.min(now - last, 250); // back from a hidden tab: catch up at most 1/4 s, don't fast-forward
  last = now;
  try {
    while (acc >= TICK_MS) {
      acc -= TICK_MS;
      if (screen !== "paused") await tick(view);
    }
    render(view);
  } catch (error) {
    console.error(error);
    if (!view.demo) toMenu();
    $("status").textContent = `Something went wrong: ${error.message}`;
  }
  requestAnimationFrame(frame);
}

async function tick(v) {
  const { match } = v;
  const count = Math.ceil(match.timer);
  const events = await match.tick();
  if (view !== v) return; // the player left while the AI was thinking
  v.effects.tick(events);
  if (v.demo) return;
  if (events.shots.length) sound.shot();
  if (events.deaths.length) sound.explosion();
  if (match.phase === "countdown" && match.round === 1 && Math.ceil(match.timer) !== count) sound.beep();
  if (events.phase === "playing") sound.beep(true);
  if (events.phase === "roundOver" && match.game.winner !== null) {
    sound.jingle(v.choice.mode !== "ai" || match.game.winner === 1);
  }
}

function render(v) {
  const { match } = v;
  const start = match.phase === "countdown" || (match.phase === "playing" && match.roundTick < FPS);
  draw(ctx, match.game, { debug: aiView, effects: v.effects, labels: v.demo || start ? v.labels : null });
  hud.update(match, v.names, v.demo);
  if (v.brainOf !== null) brain.show(match.drivers[v.brainOf].thought ?? null);
}

function fitCanvas() {
  const ratio = window.devicePixelRatio || 1; // sharp on high-density screens
  canvas.width = Math.round(WIDTH * ratio);
  canvas.height = Math.round(HEIGHT * ratio);
  ctx.setTransform(canvas.width / WIDTH, 0, 0, canvas.height / HEIGHT, 0, 0);
  brain.resize();
}

// ---- Buttons and keys ----

function setAiView(on) {
  aiView = on;
  $("eyes").setAttribute("aria-pressed", String(on));
  $("legend").hidden = !on;
}

function setMuted(muted) {
  sound.setMuted(muted);
  $("mute").setAttribute("aria-pressed", String(muted));
}

$("version").addEventListener("change", () => {
  policies.get(menu.version);
  menu.update(policies);
});
$("eyes").addEventListener("click", () => setAiView(!aiView));
$("mute").addEventListener("click", () => setMuted(!sound.muted));
$("pause-button").addEventListener("click", togglePause);
$("resume").addEventListener("click", togglePause);
$("restart").addEventListener("click", () => startGame(view.choice));
$("to-menu").addEventListener("click", toMenu);
for (const id of ["eyes", "mute"]) $(id).addEventListener("click", () => screen === "game" && canvas.focus()); // so Space shoots

window.addEventListener("keydown", (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey || e.repeat) {
    if (screen === "game" && GAME_KEYS.has(e.code)) e.preventDefault();
    return;
  }
  if (e.code === "F1") {
    e.preventDefault(); // not the browser's help
    setAiView(!aiView);
  } else if (e.code === "KeyM") {
    setMuted(!sound.muted);
  } else if (screen === "game") {
    if (GAME_KEYS.has(e.code)) e.preventDefault();
    if (e.code === "Escape" || e.code === "KeyP") togglePause();
  } else if (screen === "paused" && (e.code === "Escape" || e.code === "KeyP")) {
    e.preventDefault();
    togglePause();
  } else if (screen === "menu" && e.code === "Enter" && e.target.tagName !== "BUTTON" && e.target.tagName !== "SELECT") {
    $("play-ai").click(); // Enter anywhere on the start screen plays the AI
  }
});
window.addEventListener("keyup", (e) => screen === "game" && GAME_KEYS.has(e.code) && e.preventDefault());
window.addEventListener("blur", () => screen === "game" && setScreen("paused")); // switching windows pauses
document.addEventListener("visibilitychange", () => document.hidden && screen === "game" && setScreen("paused"));
window.addEventListener("resize", fitCanvas);

// Read-only state for the end-to-end tests (web/test/e2e)
window.tankAI = Object.freeze({
  snapshot: () => ({
    screen, aiView, muted: sound.muted, phase: view.match.phase, round: view.match.round, score: [...view.match.score],
    brain: view.brainOf === null ? null : view.match.drivers[view.brainOf].thought?.probs ?? null,
    tanks: view.match.game.tanks.map(({ x, y, angle, alive }) => ({ x, y, angle, alive })),
  }),
});

// ---- Start ----

show(demo);
fitCanvas();
requestAnimationFrame(frame);
loadVersions().then((versions) => {
  if (!versions.length) throw new Error("no versions in models/versions.csv");
  menu.setVersions(versions);
  menu.update(policies);
  return startDemo(versions);
}).catch((error) => {
  console.error(error);
  menu.disableAi("The AI couldn't load. You can still play 2 players.");
});
