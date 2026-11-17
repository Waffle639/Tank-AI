# 1. The web demo runs in the browser: the game in JavaScript, the AI in ONNX

- Status: accepted
- Date: 2026-11-17

## Context

Playing against the AI meant cloning the repo and installing PyTorch and Stable-Baselines3. The goal is a public page where anyone can play against any trained version, or two people on one keyboard, with nothing to install.

The game is single-player against a small network: 85,253 parameters (~341 KB in float32) that take 70 numbers and give 5 button probabilities, 15 times a second. The game and the observation the network was trained on are Python (`tank_game/`, `rl/observation.py`).

## Options

| | Python in the browser (Pyodide) | JavaScript port + ONNX | Server (e.g. an Arduino UNO Q at home) |
|---|---|---|---|
| Pattern | research demo | single-player web product | online multiplayer |
| First load | Python runtime + numpy + pygame-ce, then Python starts | the page, then the ONNX runtime (14.8 MB of WebAssembly before compression) in the background | small |
| Input lag | none | none | a network round trip on every key |
| Running cost | none (static files) | none (static files) | a machine always on, a home connection, a few games at once |
| Copies of the game | one | two (Python and JS) | one |

## Decision

Port the game and the observation to JavaScript, export each trained version to ONNX (`rl/export.py`), run it with ONNX Runtime Web, and publish the static site on GitHub Pages from GitHub Actions.

A single-player game against a model this small doesn't need a server, and nobody should wait for a Python runtime before they can move. ONNX is the standard format for running a trained model outside the framework that trained it: the same file runs in the browser, in Python (`onnx.reference`) and on a server.

## Consequences

- **Two copies of the game.** The network only plays well if it gets exactly the numbers it saw in training, so the JS must match the Python. `python -m rl.fixtures` records states from real games (with every shot, bounce, wall push, death and round end it can find) and `npm test` (in `web/`) checks that the JS port computes the same observations, shot paths and next states, and that ONNX Runtime Web gives the same probabilities. `npm run test:e2e` plays the page in Chromium, Firefox and WebKit with Playwright. CI runs all of them before every deploy, so a change to the Python game that isn't ported can't go live.
- **The Python stays the reference.** Training, rewards and the desktop game don't change. A new version is exported to ONNX when `train.py` freezes it.
- **The network can be shown, not just run.** The ONNX file also outputs its hidden layers' activations (no extra weights), and the page draws them next to the map: one decision from the inside, 15 times a second.
- **The ONNX runtime is heavy for this network.** Its WebAssembly is a general runtime with every operator. It loads while the player is in the menu, and the 2-player mode doesn't wait for it. A custom ONNX Runtime build with only the 3 operators used (Gemm, Tanh, Sigmoid) would shrink it if it ever matters.
- **Online play is not covered.** Two people on two computers would need an authoritative server. That is where a home server like the UNO Q would make sense, as a later step.
