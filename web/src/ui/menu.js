// The start screen, over the live demo: the two modes, and which version to play against.
import { trainedAgainst } from "../ai/versions.js";

const percent = (x) => `${Math.round(Number(x) * 100)}%`;

export class Menu {
  /** onPlay({ mode: "ai" | "pvp", version }) runs when a mode is picked. */
  constructor(onPlay) {
    this.el = document.getElementById("menu");
    this.select = document.getElementById("version");
    this.aiButton = document.getElementById("play-ai");
    this.info = document.getElementById("version-info");
    this.status = document.getElementById("status");
    this.versions = [];
    this.aiButton.addEventListener("click", () => this.aiButton.disabled || onPlay({ mode: "ai", version: this.version }));
    document.getElementById("play-pvp").addEventListener("click", () => onPlay({ mode: "pvp", version: null }));
  }

  get version() {
    return this.select.value;
  }

  setVersions(versions) {
    this.versions = versions;
    this.select.innerHTML = versions.map((v, k) => `<option value="${v.version}">${v.version}${k ? "" : " · newest"}</option>`).join("");
  }

  /** policies: the Policies, to know if the picked version is loaded. */
  update(policies) {
    const v = this.versions.find((x) => x.version === this.version);
    this.info.textContent = v
      ? `Trained against ${trainedAgainst(v.opponents)}. When frozen it won ${percent(v.win_rate)} of its rounds.`
      : "";
    const ready = v && policies.ready.has(v.version), failed = v && policies.failed.has(v.version);
    this.aiButton.disabled = !ready;
    this.aiButton.textContent = ready ? "Play" : failed ? "Couldn't load it" : "Loading the AI…";
    this.status.textContent = failed ? `${v.version} didn't load. Pick it again to retry, or play 2 players.` : "";
  }

  /** No AI at all (the versions didn't load): only 2 players is left. */
  disableAi(message) {
    this.aiButton.disabled = true;
    this.aiButton.textContent = "Unavailable";
    this.select.disabled = true;
    this.status.textContent = message;
  }
}
