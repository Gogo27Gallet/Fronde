#!/usr/bin/env python3
"""FRONDE — moniteur GPU 1 Hz (leçons 1/2/3 : dérive thermique, watts, VRAM).

Écrit un CSV : timestamp, vram_used_mib, vram_free_mib, power_w, temp_c, util_pct.
Usage :
    python3 gpu_monitor.py out.csv            # jusqu'à Ctrl-C / SIGTERM
    python3 gpu_monitor.py out.csv --check    # one-shot : vérifie GPU propre, exit 0/1
"""
import signal
import subprocess
import sys
import time

QUERY = "memory.used,memory.free,power.draw,temperature.gpu,utilization.gpu,power.limit"
# Leçon 3 : ce qui compte = VRAM LIBRE ≥ modèle (5 Go) + KV + marge, sinon spill silencieux.
# Le bureau (gnome-shell/remote-desktop/navigateur) prend ~500 MiB incompressibles ici.
CLEAN_VRAM_MIN_FREE_MIB = 6800
EXPECTED_POWER_CAP_W = 145.0  # la réf est pinée à 145 W (leçon 2)


def sample():
    out = subprocess.check_output(
        ["nvidia-smi", f"--query-gpu={QUERY}", "--format=csv,noheader,nounits"],
        text=True,
    ).strip()
    used, free, power, temp, util, cap = [float(x) for x in out.split(", ")]
    return used, free, power, temp, util, cap


def check_clean() -> int:
    used, free, power, temp, util, cap = sample()
    ok = True
    if free < CLEAN_VRAM_MIN_FREE_MIB:
        print(f"KO: VRAM libre {free:.0f} MiB < {CLEAN_VRAM_MIN_FREE_MIB} MiB — risque de spill silencieux (leçon 3)")
        ok = False
    if abs(cap - EXPECTED_POWER_CAP_W) > 1:
        print(f"KO: power cap {cap:.0f} W ≠ {EXPECTED_POWER_CAP_W:.0f} W attendu")
        ok = False
    if ok:
        print(f"OK: VRAM libre {free:.0f} MiB, cap {cap:.0f} W, temp {temp:.0f} °C")
    return 0 if ok else 1


def monitor(path: str) -> None:
    stop = False

    def _stop(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    with open(path, "w") as f:
        f.write("ts,vram_used_mib,vram_free_mib,power_w,temp_c,util_pct\n")
        while not stop:
            t0 = time.time()
            used, free, power, temp, util, _ = sample()
            f.write(f"{t0:.1f},{used:.0f},{free:.0f},{power:.1f},{temp:.0f},{util:.0f}\n")
            f.flush()
            time.sleep(max(0.0, 1.0 - (time.time() - t0)))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if "--check" in sys.argv:
        sys.exit(check_clean())
    monitor(sys.argv[1])
