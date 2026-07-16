#!/usr/bin/env python3
"""FRONDE — bench agent-loop : 5 éditions successives du même fichier.

Simule une boucle d'agent : chaque tour renvoie le fichier complet modifié,
qui devient l'entrée du tour suivant (sortie ≈ copie du prompt → gisement
ngram-mod). Mesure : tok/s par tour + wall-clock total, comparé à la même
boucle en baseline.  Réf Windows : 3,8× wall-clock, 260 tok/s soutenus.

Usage : python3 agent_loop.py [--mode ngram-mod|baseline] --out results/agent_loop_<mode>.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.bench_runner import ENV, LLAMA_CLI, MODEL_8B, TIMING_RE  # noqa: E402

SEED_FILE = (ROOT / "prompts" / "edit_rename_typehints.txt").read_text()
CODE_RE = re.compile(r"```(?:python)?\n(.*?)```", re.S)

EDITS = [
    "Rename every occurrence of the variable/parameter `data` to `records` and add full type hints to every function signature.",
    "Add a module-level docstring and convert all f-strings in `__main__` to explicit str.format calls.",
    "Add a `--verbose` handling: import logging, create `log = logging.getLogger(__name__)`, and add one log.debug call at the start of each function.",
    "Rename `pipeline` to `run_pipeline` (including the call site) and make `top_n` default to n=10.",
    "Add `from __future__ import annotations` at the top and change all Dict/List style hints to builtin generics.",
]


def extract_code(text: str, fallback: str) -> str:
    blocks = CODE_RE.findall(text)
    return blocks[-1] if blocks else fallback


def run_turn(code: str, instruction: str, mode_args: list[str]) -> tuple[str, float, float]:
    prompt = (f"Here is a complete Python file. {instruction} "
              f"Do not change anything else. Return the COMPLETE modified file "
              f"in a single ```python code block.\n\n```python\n{code}\n```\n")
    cmd = [str(LLAMA_CLI), "-m", str(MODEL_8B), "-ngl", "99", "-c", "4096",
           "--reasoning", "off", "--temp", "0", "--seed", "42", "-n", "1536",
           "-st", "-no-cnv", "--no-display-prompt", "-p", prompt, *mode_args]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800,
                          stdin=subprocess.DEVNULL, env=ENV)
    wall = time.time() - t0
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-1500:])
    m = TIMING_RE.findall(proc.stderr + proc.stdout)
    return proc.stdout, float(m[-1]) if m else 0.0, wall


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["baseline", "ngram-mod"], default="ngram-mod")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    mode_args = [] if args.mode == "baseline" else ["--spec-type", "ngram-mod"]
    code = CODE_RE.findall(SEED_FILE)[-1]
    turns, t_start = [], time.time()
    for i, instr in enumerate(EDITS, 1):
        out, tok_s, wall = run_turn(code, instr, mode_args)
        code = extract_code(out, code)
        turns.append({"turn": i, "tok_s": tok_s, "wall_s": round(wall, 2),
                      "code_chars": len(code), "output": out})
        print(f"  tour {i}: {tok_s:.1f} tok/s, {wall:.1f}s", file=sys.stderr)
    total = time.time() - t_start
    Path(args.out).write_text(json.dumps(
        {"mode": args.mode, "wall_total_s": round(total, 2), "turns": turns},
        indent=1, ensure_ascii=False))
    print(f"{args.mode}: {total:.1f}s total", file=sys.stderr)


if __name__ == "__main__":
    main()
