#!/usr/bin/env python3
"""FRONDE — verdict PASS/FAIL sur les invariants du router.

Invariant 1 : le router est ≥ référence (ratio ≥ 1.0, tolérance mesure −2 %)
              sur les 5 contenus de génération.
Invariant 2 : le router atteint ≥ 90 % du champion statique (meilleure config
              fixe) sur code / math / JSON.

Entrée : le JSON de bench_runner.py, où la politique du router par contenu est
rejouée hors-ligne : pour chaque prompt, le mode que le router aurait choisi
(classify_static → edit ; sinon le meilleur entre agressif sondé et safe).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fronde_router import Router  # noqa: E402

GEN_PROMPTS = ["gen_code_python", "gen_prose_fr", "gen_prose_en", "gen_math", "gen_json"]
CHAMPION_PROMPTS = ["gen_code_python", "gen_math", "gen_json"]
TOL = 0.98          # tolérance de mesure sur l'invariant 1
CHAMPION_FRAC = 0.90

ROUTER_MODE_CONFIG = {"safe": "ngram-simple", "aggressive": "draft", "edit": "ngram-mod"}


def main(path: str) -> int:
    rows = json.loads(Path(path).read_text())
    by_prompt: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        if not r.get("valid"):
            continue
        ratio = r.get("ratio", 1.0 if r["config"] == "baseline" else None)
        if ratio is not None:
            by_prompt[r["prompt"]][r["config"]] = ratio

    ok = True
    print(f"{'prompt':24} {'router→mode':18} {'ratio':>7} {'champion':>9}  verdict")
    for p in GEN_PROMPTS:
        cfgs = by_prompt.get(p, {})
        if not cfgs:
            print(f"{p:24} DONNÉES MANQUANTES → FAIL"); ok = False; continue
        text = (Path(__file__).resolve().parent.parent / "prompts" / f"{p}.txt").read_text()
        static_mode = Router.classify_static(text)
        if static_mode:
            router_cfg = ROUTER_MODE_CONFIG[static_mode]
        else:
            # la sonde choisit l'agressif seulement s'il bat le plancher ; hors-ligne,
            # on modélise : max(draft, ngram-simple) si draft gagne ≥10 %, sinon safe
            draft = cfgs.get("draft", 0)
            safe = cfgs.get("ngram-simple", 0)
            router_cfg = "draft" if draft >= 1.10 * safe else "ngram-simple"
        router_ratio = cfgs.get(router_cfg, 0)
        champion = max(v for k, v in cfgs.items() if k != "baseline")

        inv1 = router_ratio >= TOL
        inv2 = (p not in CHAMPION_PROMPTS) or (router_ratio >= CHAMPION_FRAC * champion)
        verdict = "PASS" if (inv1 and inv2) else "FAIL"
        ok &= (inv1 and inv2)
        print(f"{p:24} {router_cfg:18} {router_ratio:7.3f} {champion:9.3f}  {verdict}")

    print(f"\n== VERDICT GLOBAL : {'PASS' if ok else 'FAIL'} ==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
