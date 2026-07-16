#!/usr/bin/env python3
"""FRONDE — graphes matplotlib depuis les JSON de bench_runner.py.

Produit dans results/ :
  speed_by_content.png  — tok/s par contenu × config (barres groupées)
  ratio_by_content.png  — ratio vs référence (la ligne 1.0 = jamais perdant)
  gpu_session.png       — VRAM / watts / temp de la session (si CSV présent)
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = Path(__file__).resolve().parent.parent / "results"

# Palette catégorielle validée (dataviz reference instance, light mode) —
# la couleur suit la config, jamais son rang.
CONFIG_COLORS = {
    "baseline": "#2a78d6",
    "draft": "#008300",
    "ngram-simple": "#e87ba4",
    "ngram-mod": "#eda100",
    "draft-n8-p0.45": "#1baf7a",
    "draft-n8-p0.75": "#eb6834",
    "draft-n12-p0.75": "#4a3aa7",
}
INK, INK2 = "#1a1a19", "#6b6a60"

plt.rcParams.update({
    "axes.edgecolor": "#d9d8ce", "axes.linewidth": 0.8,
    "axes.grid": True, "grid.color": "#eceae2", "grid.linewidth": 0.6,
    "axes.axisbelow": True, "text.color": INK,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "font.size": 9,
})


def load(path: Path):
    rows = json.loads(path.read_text())
    speed, ratio = defaultdict(dict), defaultdict(dict)
    for r in rows:
        if not r.get("valid"):
            continue
        speed[r["prompt"]][r["config"]] = r["test_tok_s"]
        if "ratio" in r:
            ratio[r["prompt"]][r["config"]] = r["ratio"]
    return speed, ratio


def grouped_bars(data: dict, title: str, ylabel: str, out: Path, hline=None):
    prompts = list(data)
    # ordre fixe des configs (jamais recyclé), pas d'ordre alphabétique
    configs = [c for c in CONFIG_COLORS if any(c in v for v in data.values())]
    w = 0.72 / max(1, len(configs))
    fig, ax = plt.subplots(figsize=(11, 4.6))
    for j, cfg in enumerate(configs):
        xs = [i + j * w for i in range(len(prompts))]
        ys = [data[p].get(cfg, 0) for p in prompts]
        bars = ax.bar(xs, ys, width=w * 0.92, label=cfg,
                      color=CONFIG_COLORS[cfg], edgecolor="white", linewidth=1)
        # labels directs sélectifs : uniquement les valeurs saillantes (>1.5× / >120 t/s)
        thr = 1.5 if hline is not None else 120
        for b, y in zip(bars, ys):
            if y > thr:
                ax.annotate(f"{y:.2g}", (b.get_x() + b.get_width() / 2, y),
                            ha="center", va="bottom", fontsize=7.5, color=INK)
    if hline is not None:
        ax.axhline(hline, color=INK2, lw=1, ls="--", alpha=0.8)
    ax.set_xticks([i + 0.36 - w / 2 for i in range(len(prompts))])
    ax.set_xticklabels(prompts, rotation=18, ha="right", fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.legend(fontsize=8, frameon=False, ncols=len(configs))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"→ {out}")


def gpu_plot(csv: Path, out: Path):
    import csv as _csv
    ts, vram, watts, temp = [], [], [], []
    with open(csv) as f:
        for row in _csv.DictReader(f):
            ts.append(float(row["ts"]))
            vram.append(float(row["vram_used_mib"]))
            watts.append(float(row["power_w"]))
            temp.append(float(row["temp_c"]))
    t0 = ts[0]
    x = [(t - t0) / 60 for t in ts]
    fig, axes = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
    for ax, y, lab in zip(axes, [vram, watts, temp], ["VRAM (MiB)", "Puissance (W)", "Temp (°C)"]):
        ax.plot(x, y, lw=0.8)
        ax.set_ylabel(lab)
    axes[1].axhline(145, color="red", lw=1, ls="--", alpha=0.6)
    axes[-1].set_xlabel("minutes")
    fig.suptitle("Session GPU (leçons 1–3 : dérive, watts, VRAM)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"→ {out}")


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS / "reproduce.json"
    speed, ratio = load(src)
    grouped_bars(speed, "Vitesse par contenu × config", "tok/s",
                 RESULTS / "speed_by_content.png")
    grouped_bars(ratio, "Ratio vs référence (bracketé) — 1.0 = jamais perdant",
                 "ratio", RESULTS / "ratio_by_content.png", hline=1.0)
    gpu_csv = src.with_suffix(".gpu.csv")
    if gpu_csv.exists():
        gpu_plot(gpu_csv, RESULTS / "gpu_session.png")
