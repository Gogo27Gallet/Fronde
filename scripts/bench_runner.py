#!/usr/bin/env python3
"""FRONDE — orchestrateur de bench bracketé.

Protocole (leçon 1) : pour chaque config testée sur chaque prompt :
    réf AVANT (baseline) → config → réf APRÈS (baseline)
On rapporte le RATIO config/moyenne(réfs). Si |réf_avant − réf_après| / moyenne > 5 %,
le run est invalidé et rejoué (une fois ; sinon marqué INVALID).

Conditions fixes : temp 0, seed 42, 3 reps (médiane), moniteur GPU 1 Hz,
GPU propre vérifié avant chaque session (gpu_monitor.py --check).
Les sorties générées sont TOUJOURS capturées (leçon 4).

Usage :
    python3 bench_runner.py --configs baseline draft ngram-simple ngram-mod \
                            --prompts gen_code_python gen_prose_fr ... \
                            --out results/session_01.json
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LLAMA_CLI = ROOT / "llama.cpp" / "build" / "bin" / "llama-cli"
MODEL_8B = ROOT / "models" / "Qwen3-8B-Q4_K_M.gguf"
MODEL_06B = ROOT / "models" / "Qwen3-0.6B-Q8_0.gguf"

BRACKET_TOL = 0.05
N_PREDICT_GEN = 768
N_PREDICT_EDIT = 1536
REPS = 3

# Configs nommées → arguments llama-cli supplémentaires
CONFIGS: dict[str, list[str]] = {
    "baseline": [],
    "draft": ["-md", str(MODEL_06B), "--spec-type", "draft-simple",
              "--draft-max", "12", "--draft-p-min", "0.45"],
    "ngram-simple": ["--spec-type", "ngram-simple"],
    "ngram-mod": ["--spec-type", "ngram-mod"],
}
# Grille draft de la Phase 4 (n_max × p_min)
for n_max in (8, 12):
    for p_min in ("0.45", "0.75"):
        CONFIGS[f"draft-n{n_max}-p{p_min}"] = [
            "-md", str(MODEL_06B), "--spec-type", "draft-simple",
            "--draft-max", str(n_max), "--draft-p-min", p_min,
        ]

TIMING_RE = re.compile(
    r"eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*(?:runs|tokens).*?([\d.]+)\s*tokens per second",
    re.S,
)


def run_once(prompt_text: str, extra_args: list[str], n_predict: int) -> dict:
    """Un run llama-cli, retourne {'tok_s', 'n_gen', 'output', 'stderr_tail'}."""
    cmd = [
        str(LLAMA_CLI), "-m", str(MODEL_8B),
        "-ngl", "99", "--temp", "0", "--seed", "42",
        "-n", str(n_predict), "-no-cnv", "--no-display-prompt",
        "-p", prompt_text,
        *extra_args,
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    wall = time.time() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"llama-cli rc={proc.returncode}\n{proc.stderr[-2000:]}")
    # le dernier bloc "eval time" du stderr = génération (pas le prompt eval)
    matches = [m for m in TIMING_RE.finditer(proc.stderr)
               if "prompt eval" not in proc.stderr[max(0, m.start() - 20):m.start()]]
    if not matches:
        raise RuntimeError(f"timings introuvables dans stderr:\n{proc.stderr[-2000:]}")
    ms, n_tok, tok_s = matches[-1].groups()
    return {
        "tok_s": float(tok_s),
        "n_gen": int(n_tok),
        "wall_s": round(wall, 2),
        "output": proc.stdout,
        "stderr_tail": proc.stderr[-3000:],
    }


def median_run(prompt_text: str, extra_args: list[str], n_predict: int, reps: int = REPS) -> dict:
    runs = [run_once(prompt_text, extra_args, n_predict) for _ in range(reps)]
    speeds = [r["tok_s"] for r in runs]
    med = statistics.median(speeds)
    chosen = min(runs, key=lambda r: abs(r["tok_s"] - med))
    return {"tok_s_median": med, "tok_s_all": speeds, "run": chosen}


def bracketed(prompt_name: str, prompt_text: str, config: str, n_predict: int) -> dict:
    """réf → config → réf ; retourne ratios + données brutes."""
    for attempt in (1, 2):
        ref_a = median_run(prompt_text, CONFIGS["baseline"], n_predict)
        test = median_run(prompt_text, CONFIGS[config], n_predict)
        ref_b = median_run(prompt_text, CONFIGS["baseline"], n_predict)
        ra, rb = ref_a["tok_s_median"], ref_b["tok_s_median"]
        drift = abs(ra - rb) / ((ra + rb) / 2)
        result = {
            "prompt": prompt_name, "config": config, "attempt": attempt,
            "ref_before": ra, "ref_after": rb, "drift": round(drift, 4),
            "test_tok_s": test["tok_s_median"],
            "ratio": round(test["tok_s_median"] / ((ra + rb) / 2), 4),
            "valid": drift <= BRACKET_TOL,
            "raw": {"ref_before": ref_a, "test": test, "ref_after": ref_b},
        }
        if result["valid"]:
            return result
        print(f"  !! drift {drift:.1%} > {BRACKET_TOL:.0%}, run rejoué", file=sys.stderr)
    result["valid"] = False
    return result


def gpu_clean_or_die() -> None:
    rc = subprocess.run([sys.executable, str(ROOT / "scripts" / "gpu_monitor.py"), "--check", "/dev/null"]).returncode
    if rc != 0:
        sys.exit("GPU pas propre — bench refusé (leçon 3).")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="+", required=True, choices=sorted(CONFIGS))
    ap.add_argument("--prompts", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=REPS)
    args = ap.parse_args()

    gpu_clean_or_die()
    global REPS
    REPS = args.reps

    mon_csv = Path(args.out).with_suffix(".gpu.csv")
    mon = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "gpu_monitor.py"), str(mon_csv)])
    results = []
    try:
        for prompt_name in args.prompts:
            text = (ROOT / "prompts" / f"{prompt_name}.txt").read_text()
            n_pred = N_PREDICT_EDIT if prompt_name.startswith("edit_") else N_PREDICT_GEN
            for config in args.configs:
                print(f"== {prompt_name} × {config}", file=sys.stderr)
                if config == "baseline":
                    r = median_run(text, CONFIGS["baseline"], n_pred)
                    results.append({"prompt": prompt_name, "config": "baseline",
                                    "test_tok_s": r["tok_s_median"], "raw": r, "valid": True})
                else:
                    results.append(bracketed(prompt_name, text, config, n_pred))
                Path(args.out).write_text(json.dumps(results, indent=1, ensure_ascii=False))
    finally:
        mon.terminate()
    print(f"OK — {len(results)} mesures → {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
