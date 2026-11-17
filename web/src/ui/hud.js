// The text around the map, like the desktop game's (tank_game/renderer.py): the score in the bar, the time until
// the survivor gets the point, and big text in the middle of the map (the countdown, each round's result).
import { FPS, ROUND_END_DELAY } from "../game/config.js";

export class Hud {
  constructor({ score, notice, banner }) {
    Object.assign(this, { scoreEl: score, noticeEl: notice, bannerEl: banner });
  }

  /** names: [Red's, Blue's]; quiet: no banner (the menu's demo). */
  update(match, names, quiet) {
    const game = match.game, [red, blue] = match.score;
    // Blue first, like the desktop game's bar
    this.set(this.scoreEl, "score", `<b class="blue">${names[1]}</b> ${blue}&nbsp; - &nbsp;${red} <b class="red">${names[0]}</b>`, true);

    const alive = game.tanks.flatMap((t, i) => (t.alive ? [i] : []));
    const pointFor = !quiet && game.endTimer !== null && !game.done && alive.length;
    this.set(this.noticeEl, pointFor ? `notice ${alive[0] ? "blue" : "red"}` : "notice",
      pointFor ? `Point for ${names[alive[0]]} in ${Math.max(0, ROUND_END_DELAY - game.endTimer).toFixed(1)}s` : "");

    let text = "", kind = "banner";
    if (quiet) {
      text = "";
    } else if (match.phase === "countdown") {
      text = match.round === 1 ? String(Math.ceil(match.timer)) : `Round ${match.round}`;
      kind = match.round === 1 ? "banner count" : "banner";
    } else if (match.phase === "playing" && match.roundTick < FPS / 2) {
      text = "Go!";
    } else if (match.phase === "roundOver") {
      const w = game.winner;
      text = w === null ? "Draw" : names[w] === "You" ? "You win" : `${names[w]} wins`;
    }
    if (this.set(this.bannerEl, kind, text)) { // a new message: replay its pop
      void this.bannerEl.offsetWidth;
      this.bannerEl.classList.add("pop");
    }
  }

  /** Change an element only when its content changes. Returns whether it did. */
  set(el, className, content, html = false) {
    if ((html ? el.innerHTML : el.textContent) === content && el.dataset.kind === className) return false;
    el[html ? "innerHTML" : "textContent"] = content;
    el.className = className;
    el.dataset.kind = className;
    return true;
  }
}
