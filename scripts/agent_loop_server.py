#!/usr/bin/env python3
"""FRONDE — agent-loop sur serveur chaud (le modèle reste chargé, comme un vrai agent).

5 éditions successives du même fichier via llama-server ; le fichier renvoyé au
tour N devient l'entrée du tour N+1. Compare wall-clock et tok/s soutenus entre
--mode edit (ngram-mod) et --mode baseline. Réf Windows : 3,8× wall, 260 tok/s.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fronde_router import MODES, Router  # noqa: E402

from scripts.agent_loop import CODE_RE, EDITS, SEED_FILE, extract_code  # noqa: E402

MODES["baseline"] = []  # mode sans spéculation pour la comparaison


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["baseline", "edit"], default="edit")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    router = Router()
    code = CODE_RE.findall(SEED_FILE)[-1]
    turns = []
    try:
        router._start_server(args.mode)
        t0 = time.time()
        for i, instr in enumerate(EDITS, 1):
            # amorce du fence de sortie + stop au fence fermant (protocole "stop au fence")
            prompt = (f"Here is a complete Python file. {instr} "
                      f"Do not change anything else. Return the COMPLETE modified file.\n\n"
                      f"```python\n{code}\n```\n\nModified file:\n```python\n")
            text, tok_s, n = router._complete(prompt, 2048, stop=["```"])
            code = text.rstrip().removesuffix("```").rstrip() or code
            turns.append({"turn": i, "tok_s": tok_s, "n_tokens": n,
                          "code_chars": len(code), "output": text})
            print(f"  tour {i}: {tok_s:.1f} tok/s ({n} tokens)", file=sys.stderr)
        wall = time.time() - t0
    finally:
        router.stop()
    tot_tok = sum(t["n_tokens"] for t in turns)
    Path(args.out).write_text(json.dumps(
        {"mode": args.mode, "wall_total_s": round(wall, 2),
         "tokens_total": tot_tok, "sustained_tok_s": round(tot_tok / wall, 1),
         "turns": turns}, indent=1, ensure_ascii=False))
    print(f"{args.mode}: {wall:.1f}s, {tot_tok} tokens, {tot_tok/wall:.1f} tok/s soutenus",
          file=sys.stderr)


if __name__ == "__main__":
    main()
