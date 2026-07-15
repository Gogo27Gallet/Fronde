# FRONDE — Turning idle silicon into tokens per second

*Speculative decoding, measured honestly, on a €300 GPU.*

## The wall

Generating one token means re-reading every weight. On an RTX 5060 (448 GB/s) running
Qwen3-8B-Q4_K_M (5.03 GB), the ceiling is 448 ÷ 5.03 ≈ **89 tok/s** — and the plain
baseline already hits **{{TG128}} tok/s** (tg128), i.e. ~{{PCT_CEILING}} % of it, while using
**less than 1 % of the GPU's compute**. Prompt processing runs at {{PP512}} tok/s: a
**{{RATIO}}× gap** between what the silicon can chew and what decoding feeds it.

The whole project is one idea: **produce several tokens per read of the weights.**

## What we measured

All numbers: llama.cpp {{LLAMA_TAG}}, temp 0, seed 42, 3 reps (median), power cap
pinned at 145 W, GPU monitored at 1 Hz. Every comparison is **bracketed** (baseline
before + after, ratios only — thermal drift is real: we measured −11 % over a session).

| Mode | Code | Prose (FR) | Edits |
|---|---|---|---|
| Baseline | 1.00× | 1.00× | 1.00× |
| Draft 0.6B (n_max=12, p_min=0.45) | {{DRAFT_CODE}} | {{DRAFT_PROSE}} | — |
| ngram-simple | {{NGS_CODE}} | {{NGS_PROSE}} | {{NGS_EDIT}} |
| ngram-mod | — | — | **{{NGM_EDIT}}×** (peaks >{{NGM_PEAK}} tok/s) |

Key findings:

1. **The draft model is a bet, not a win.** A 0.6B Q8_0 draft gives {{DRAFT_CODE_SPEED}} tok/s
   on code (66 % acceptance) but *loses* on prose — the draft costs ~2.6 ms/token even
   when it stays silent. The 0.6B alone runs at {{SPEED_06B}} tok/s vs ~700 theoretical:
   it is **kernel-launch-bound**, not bandwidth-bound (which is also why Q4 drafts lose to Q8).
2. **ngram-simple is the never-losing floor** — ≥ baseline on every content type we tested.
3. **Code editing is a goldmine.** When the output mostly copies the prompt, ngram-mod
   reaches a **{{NGM_EDIT}}× median speedup** ({{NGM_REPEAT}}× on repeated edits). The speedup
   tracks the copied fraction: {{NGM_LOW}}× when everything changes, {{NGM_HIGH}}× when little does.
   An agent loop of 5 successive edits sustains {{AGENT_SPEED}} tok/s ({{AGENT_X}}× wall-clock).
4. **What didn't work:** EAGLE-3 (AngelSlim head for Qwen3-8B) collapsed on a Q4 target
   (58 % acceptance on code → 14.8 % on French prose), beaten by the plain 0.6B draft
   everywhere. We eliminated quantization, conversion, d2t coverage and chat format as
   causes; the model card itself only claims ~1.7×. Our expectations were wrong, not the head.

## FRONDE-Router

A ~250-line client-side dispatcher over llama-server. It doesn't predict which mode
wins — it **measures**: a 48-token probe on the aggressive config, a prompt-hash cache,
epoch batching (one server swap per batch), a static EDIT class (big code/JSON block +
edit verb → ngram-mod, no probe), ngram-simple as the safety floor, and an EMA
collapse detector.

**Invariants** (checked by `reproduce.sh`, PASS/FAIL): ≥ baseline on all 5 content
types, and ≥ 90 % of the static champion on code/math/JSON.

## Reproduce

```bash
./reproduce.sh        # SHA-checks models, builds llama.cpp (CUDA, sm_120), runs the
                      # bracketed benchmark battery, prints the invariant verdict
./demo.py             # live demo: prose → code → JSON → edit, tok/s counter
```

Hardware: Ryzen 5 5500, RTX 5060 8 GB (145 W cap), 16 GB RAM, Ubuntu 26.04.
Models: Qwen3-8B-Q4_K_M (SHA256 `d98cdcbd…5745785`) + Qwen3-0.6B-Q8_0, from
`Qwen/Qwen3-*-GGUF`. llama.cpp pinned at `{{LLAMA_TAG}}` (`{{LLAMA_COMMIT}}`).

## Method notes (the hard-earned ones)

- **Bracket everything.** −11 % thermal drift per session will otherwise manufacture
  or hide your effect.
- **Log watts.** Speculative modes draw ~15 W less than baseline at the same cap —
  efficiency becomes speed whenever there is thermal headroom.
- **Watch VRAM.** Squatted VRAM means silent spill: half the speed, zero errors
  (Windows/WDDM; {{LINUX_SPILL_NOTE}}).
- **Capture outputs.** An exploding acceptance rate can measure degeneration
  (the model looping), not speed.

## License

MIT.
