#!/usr/bin/env python3
"""FRONDE-Router — dispatcher client au-dessus de llama-server.

Idée : la vitesse de chaque mode spéculatif dépend du contenu. Plutôt que de
prédire, on MESURE : une sonde de 48 tokens sur la config agressive classe le
prompt par vitesse observée, avec un plancher jamais-perdant (ngram-simple).

Politique :
  1. Classe EDIT (bloc code/JSON ≥ 800 caractères + verbe d'édition)
     → ngram-mod direct, sans sonde (le gisement copie-de-prompt est connu).
  2. Sinon : sonde 48 tokens sur la config agressive (draft n_max=12 p_min=0.45).
     Si la vitesse sondée bat le plancher d'au moins PROBE_MARGIN → agressif,
     sinon → SAFE (ngram-simple, ≥ réf sur tous contenus mesurés).
  3. Cache par hash de prompt (les re-soumissions sautent la sonde).
  4. Époques : les requêtes d'un batch sont regroupées par mode → un seul
     swap de config serveur par époque (le swap coûte un redémarrage).
  5. EMA anti-effondrement : si la vitesse réalisée d'un mode s'effondre sous
     EMA_COLLAPSE × son EMA, le mode est mis en quarantaine pour QUARANTINE_S
     et on retombe sur SAFE.

Invariants validés par reproduce.sh :
  - ≥ référence (baseline) sur les 5 contenus de la batterie ;
  - ≥ 90 % du champion statique sur code / math / JSON.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER_BIN = ROOT / "llama.cpp" / "build" / "bin" / "llama-server"
MODEL_8B = ROOT / "models" / "Qwen3-8B-Q4_K_M.gguf"
MODEL_06B = ROOT / "models" / "Qwen3-0.6B-Q8_0.gguf"
PORT = 8765

PROBE_TOKENS = 48
PROBE_MARGIN = 1.10      # l'agressif doit battre le plancher de 10 % sur la sonde
EDIT_MIN_BLOCK = 800     # caractères de bloc code/JSON pour la classe EDIT
EMA_ALPHA = 0.30
EMA_COLLAPSE = 0.50      # vitesse < 50 % de l'EMA du mode → quarantaine
QUARANTINE_S = 120.0

EDIT_VERBS = re.compile(
    r"\b(rename|refactor|fix|correct|modify|change|edit|update|patch|add|remove|"
    r"renomme|corrige|modifie|change|édite|ajoute|supprime|remplace)\b", re.I)
CODE_BLOCK = re.compile(r"```[a-z]*\n(.*?)```", re.S)

MODES: dict[str, list[str]] = {
    "safe":       ["--spec-type", "ngram-simple"],
    "aggressive": ["-md", str(MODEL_06B), "--spec-type", "draft-simple",
                   "--draft-max", "12", "--draft-p-min", "0.45"],
    "edit":       ["--spec-type", "ngram-mod"],
}


@dataclass
class Router:
    server: subprocess.Popen | None = None
    current_mode: str | None = None
    cache: dict[str, str] = field(default_factory=dict)          # prompt_hash → mode
    ema: dict[str, float] = field(default_factory=dict)          # mode → tok/s EMA
    quarantined: dict[str, float] = field(default_factory=dict)  # mode → t_fin
    log: list[dict] = field(default_factory=list)

    # ---------- serveur ----------

    def _start_server(self, mode: str) -> None:
        if self.current_mode == mode and self.server and self.server.poll() is None:
            return
        self.stop()
        cmd = [str(SERVER_BIN), "-m", str(MODEL_8B), "-ngl", "99",
               "--port", str(PORT), "--temp", "0", "--seed", "42",
               *MODES[mode]]
        self.server = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
                self.current_mode = mode
                return
            except Exception:
                if self.server.poll() is not None:
                    raise RuntimeError(f"llama-server mort au démarrage (mode {mode})")
                time.sleep(0.5)
        raise TimeoutError(f"llama-server injoignable (mode {mode})")

    def stop(self) -> None:
        if self.server and self.server.poll() is None:
            self.server.terminate()
            self.server.wait(timeout=30)
        self.server, self.current_mode = None, None

    def _complete(self, prompt: str, n_predict: int) -> tuple[str, float, int]:
        """→ (texte, tok/s, n_tokens) via /completion."""
        body = json.dumps({"prompt": prompt, "n_predict": n_predict,
                           "temperature": 0, "seed": 42, "cache_prompt": False}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/completion", body,
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=1800) as r:
            data = json.loads(r.read())
        timings = data.get("timings", {})
        tok_s = timings.get("predicted_per_second", 0.0)
        return data.get("content", ""), tok_s, timings.get("predicted_n", 0)

    # ---------- classification ----------

    @staticmethod
    def _hash(prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    @staticmethod
    def classify_static(prompt: str) -> str | None:
        """Classe EDIT sans sonde : gros bloc code/JSON + verbe d'édition."""
        blocks = CODE_BLOCK.findall(prompt)
        if blocks and max(len(b) for b in blocks) >= EDIT_MIN_BLOCK and EDIT_VERBS.search(prompt):
            return "edit"
        return None

    def _quarantine_ok(self, mode: str) -> bool:
        until = self.quarantined.get(mode, 0.0)
        return time.time() >= until

    def _probe(self, prompt: str) -> str:
        """Sonde PROBE_TOKENS sur l'agressif, compare au plancher SAFE."""
        if not self._quarantine_ok("aggressive"):
            return "safe"
        self._start_server("aggressive")
        _, spd_aggr, _ = self._complete(prompt, PROBE_TOKENS)
        floor = self.ema.get("safe")
        if floor is None:
            self._start_server("safe")
            _, floor, _ = self._complete(prompt, PROBE_TOKENS)
            self._update_ema("safe", floor)
        return "aggressive" if spd_aggr >= PROBE_MARGIN * floor else "safe"

    def _update_ema(self, mode: str, tok_s: float) -> None:
        prev = self.ema.get(mode)
        self.ema[mode] = tok_s if prev is None else EMA_ALPHA * tok_s + (1 - EMA_ALPHA) * prev

    # ---------- API ----------

    def route(self, prompt: str) -> str:
        h = self._hash(prompt)
        if h in self.cache:
            return self.cache[h]
        mode = self.classify_static(prompt) or self._probe(prompt)
        self.cache[h] = mode
        return mode

    def run_batch(self, prompts: list[str], n_predict: int = 768) -> list[dict]:
        """Époques : groupe par mode → un seul swap serveur par groupe."""
        routed = [(p, self.route(p)) for p in prompts]
        results: list[dict | None] = [None] * len(prompts)
        for mode in ("edit", "aggressive", "safe"):
            idx = [i for i, (_, m) in enumerate(routed) if m == mode]
            if not idx:
                continue
            self._start_server(mode)
            for i in idx:
                text, tok_s, n = self._complete(prompts[i], n_predict)
                # EMA anti-effondrement (leçon 4 : une anomalie se mesure, ne s'ignore pas)
                prev = self.ema.get(mode)
                if prev and tok_s < EMA_COLLAPSE * prev:
                    self.quarantined[mode] = time.time() + QUARANTINE_S
                self._update_ema(mode, tok_s)
                rec = {"i": i, "mode": mode, "tok_s": tok_s, "n": n, "text": text}
                results[i] = rec
                self.log.append({k: v for k, v in rec.items() if k != "text"})
        return results  # type: ignore[return-value]


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="FRONDE-Router")
    ap.add_argument("prompt_files", nargs="+", help="fichiers prompt à router/exécuter")
    ap.add_argument("-n", "--n-predict", type=int, default=768)
    ap.add_argument("--dry-run", action="store_true", help="classe sans exécuter")
    args = ap.parse_args()

    prompts = [Path(f).read_text() for f in args.prompt_files]
    router = Router()
    try:
        if args.dry_run:
            for f, p in zip(args.prompt_files, prompts):
                print(f"{f}: {router.classify_static(p) or 'probe-needed'}")
        else:
            for f, r in zip(args.prompt_files, router.run_batch(prompts, args.n_predict)):
                print(f"{f}: mode={r['mode']} {r['tok_s']:.1f} tok/s ({r['n']} tokens)")
    finally:
        router.stop()
