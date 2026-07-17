#!/usr/bin/env python3
"""FRONDE — démo live : 4 scènes (prose FR → code → JSON → édition JSON),
compteur tok/s en direct.

Le router choisit le mode par scène ; le panneau rich affiche la classe
détectée, le mode actif, le texte qui s'écrit, la vitesse instantanée (verte
≥ 100 tok/s) et les watts / la température du GPU.

Préflight : refuse de tourner si le GPU n'est pas propre (> 1 Go occupé).
L'édition JSON est jouée en PREMIÈRE rencontre (mémoire ngram vierge) après un
warmup neutre ; --with-repeat rejoue la même édition, étiquetée "repeat", pour
montrer le gain quand la mémoire de copie est amorcée.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from fronde_router import Router, PORT

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts.gpu_monitor import sample as gpu_sample  # noqa: E402

# Préflight : le GPU doit être propre (aucun autre modèle chargé). > 1 Go = refus.
PREFLIGHT_MAX_USED_MIB = 1024
GREEN_TOK_S = 100.0  # seuil "c'est rapide" à l'écran

SCENES = [
    ("Prose (FR)", "gen_prose_fr", 400, False),
    ("Code Python", "gen_code_python", 600, False),
    ("JSON", "gen_json", 600, False),
    ("Édition JSON", "edit_json", 1536, True),  # dernière = édition (première rencontre)
]

console = Console()


def preflight() -> None:
    used, free, power, temp, util, cap = gpu_sample()
    if used > PREFLIGHT_MAX_USED_MIB:
        console.print(
            f"[bold red]Préflight KO[/] : {used:.0f} MiB déjà occupés sur le GPU "
            f"(> {PREFLIGHT_MAX_USED_MIB} MiB). Libère la VRAM (Ollama ? autre modèle ?) "
            f"avant la démo.")
        sys.exit(1)
    console.print(
        f"[green]Préflight OK[/] — GPU propre : {used:.0f} MiB occupés, "
        f"{free:.0f} MiB libres, cap {cap:.0f} W, {temp:.0f} °C.")


def _speed_style(speed: float) -> str:
    return "bold green" if speed >= GREEN_TOK_S else "bold yellow"


def stream(prompt: str, n_predict: int, title: str, detected: str, mode: str,
           label: str = "") -> tuple[float, int]:
    """Streame /completion en affichant classe, mode, tok/s (gros), watts, temp."""
    body = json.dumps({"prompt": prompt, "n_predict": n_predict, "temperature": 0,
                       "seed": 42, "stream": True, "cache_prompt": False}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/completion", body,
                                 {"Content-Type": "application/json"})
    text, n_tok, t0 = "", 0, time.time()
    watts = temp = 0.0
    last_gpu = 0.0
    chip = f" {title}{(' · ' + label) if label else ''} "
    with urllib.request.urlopen(req, timeout=1800) as r, \
            Live(console=console, refresh_per_second=12) as live:
        for raw in r:
            raw = raw.decode().strip()
            if not raw.startswith("data: "):
                continue
            data = json.loads(raw[6:])
            text += data.get("content", "")
            n_tok += 1
            now = time.time()
            speed = n_tok / max(1e-3, now - t0)
            if now - last_gpu >= 1.0:  # échantillon GPU ~1 Hz (pas à 12 Hz)
                used, free, watts, temp, util, cap = gpu_sample()
                last_gpu = now
            head1 = Text.assemble(
                (chip, "bold white on blue"), "   classe=",
                (detected, "bold cyan"), "   mode=", (mode, "bold magenta"))
            big = Text(f"  ▍ {speed:6.1f} tok/s", style=_speed_style(speed))
            big.append(f"   ({n_tok} tokens)", style="dim")
            head3 = Text.assemble(
                ("GPU  ", "dim"), (f"{watts:5.1f} W", "bold"), ("   ", ""),
                (f"{temp:4.0f} °C", "bold"))
            body_txt = Text(text[-1100:], overflow="ellipsis")
            live.update(Panel(Group(head1, big, head3, Text(""), body_txt),
                              border_style="blue"))
            if data.get("stop"):
                break
    return n_tok / max(1e-3, time.time() - t0), n_tok


def main() -> None:
    ap = argparse.ArgumentParser(description="FRONDE — démo live")
    ap.add_argument("--with-repeat", action="store_true",
                    help="rejoue l'édition JSON une 2e fois (mémoire ngram amorcée), "
                         "étiquetée 'repeat'")
    args = ap.parse_args()

    preflight()
    router = Router()
    console.rule("[bold]FRONDE — demo")
    summary: list[tuple[str, str, float, int]] = []
    try:
        for title, prompt_name, n_pred, is_edit in SCENES:
            prompt = (ROOT / "prompts" / f"{prompt_name}.txt").read_text()
            detected = "EDIT (statique)" if router.classify_static(prompt) else "probe"
            if not is_edit:
                # warmup neutre juste AVANT la sonde : la sonde de 48 tokens mesure
                # sinon les horloges GPU froides après le swap serveur et sous-évalue
                # l'agressif (contenu neutre → n'amorce aucune mémoire de copie).
                router._start_server("aggressive")
                router._complete("Bonjour, ceci est un échauffement neutre.", 32)
            mode = router.route(prompt)
            router._start_server(mode)
            if is_edit:
                # warmup neutre : réveille les horloges GPU sans amorcer la mémoire
                # ngram avec le contenu de l'édition → la mesure reste "1re rencontre".
                router._complete("Bonjour, ceci est un échauffement neutre.", 16)
            speed, n = stream(prompt, n_pred, title, detected, mode)
            summary.append((title, mode, speed, n))
            if is_edit and args.with_repeat:
                # même prompt, même serveur : la mémoire de copie est maintenant chaude.
                speed_r, n_r = stream(prompt, n_pred, title, detected, mode,
                                      label="repeat")
                summary.append((title + " (repeat)", mode, speed_r, n_r))
    finally:
        router.stop()
    console.rule("[bold]Récap")
    for title, mode, speed, n in summary:
        style = "bold green" if speed >= GREEN_TOK_S else "bold yellow"
        console.print(f"  {title:22} mode={mode:10} "
                      f"[{style}]{speed:6.1f} tok/s[/] ({n} tokens)")


if __name__ == "__main__":
    main()
