#!/usr/bin/env python3
"""FRONDE — démo live : 4 scènes (prose → code → JSON → edit), compteur tok/s en direct.

Le router choisit le mode par scène ; le panneau rich affiche le texte qui
s'écrit, la vitesse instantanée et le mode actif.
"""
import json
import time
import urllib.request
from pathlib import Path

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from fronde_router import MODES, PORT, Router

ROOT = Path(__file__).resolve().parent
SCENES = [
    ("Prose (FR)", "gen_prose_fr", 400),
    ("Code Python", "gen_code_python", 600),
    ("JSON", "gen_json", 600),
    ("Édition de code", "edit_rename_typehints", 1536),
]

console = Console()


def stream(prompt: str, n_predict: int, title: str, mode: str) -> tuple[float, int]:
    body = json.dumps({"prompt": prompt, "n_predict": n_predict, "temperature": 0,
                       "seed": 42, "stream": True, "cache_prompt": False}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/completion", body,
                                 {"Content-Type": "application/json"})
    text, n_tok, t0 = "", 0, time.time()
    with urllib.request.urlopen(req, timeout=1800) as r, Live(console=console, refresh_per_second=12) as live:
        for raw in r:
            raw = raw.decode().strip()
            if not raw.startswith("data: "):
                continue
            data = json.loads(raw[6:])
            text += data.get("content", "")
            n_tok += 1
            dt = max(1e-3, time.time() - t0)
            speed = n_tok / dt
            header = Text.assemble(
                (f" {title} ", "bold white on blue"), "  mode=",
                (mode, "bold magenta"), "  ",
                (f"{speed:6.1f} tok/s", "bold green"), f"  ({n_tok} tokens)")
            body_txt = Text(text[-1200:], overflow="ellipsis")
            live.update(Panel(Group(header, body_txt), border_style="blue"))
            if data.get("stop"):
                break
    return n_tok / max(1e-3, time.time() - t0), n_tok


def main() -> None:
    router = Router()
    console.rule("[bold]FRONDE — demo")
    summary = []
    try:
        for title, prompt_name, n_pred in SCENES:
            prompt = (ROOT / "prompts" / f"{prompt_name}.txt").read_text()
            mode = router.route(prompt)
            router._start_server(mode)
            speed, n = stream(prompt, n_pred, title, mode)
            summary.append((title, mode, speed, n))
    finally:
        router.stop()
    console.rule("[bold]Récap")
    for title, mode, speed, n in summary:
        console.print(f"  {title:18} mode={mode:10} [bold green]{speed:6.1f} tok/s[/] ({n} tokens)")


if __name__ == "__main__":
    main()
