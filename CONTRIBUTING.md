# Contributing to FRONDE

Thanks for your interest. FRONDE is a small, measurement-first project: the value is
in *honest numbers*, so the contribution bar is mostly about how results are produced,
not about code style.

## Ground rules for any performance claim

If your change touches a number in `BENCH.md`, the `README`, or `results/`, it must
follow the same protocol as the rest of the repo:

- **Bracket every comparison.** Run the reference config *before and after* the tested
  config and report **ratios**, never raw tok/s. Thermal drift is real (we have seen
  −11 % across a session); a run whose two reference brackets disagree by more than a
  few percent is invalid and must be replayed.
- **Fixed conditions.** temp 0, seed 42, ≥ 3 reps (median), power cap pinned, GPU
  monitored, and the model SHA256s verified before the run (`reproduce.sh` does this).
- **Clean GPU.** No other model resident; the harness refuses to run below the VRAM-free
  floor. Stop Ollama / other workloads first.
- **Capture the outputs.** An anomalous acceptance rate is a *measurement*, not a
  victory — it often means degeneration or chain-of-thought, not a real speedup. Attach
  the generated text when a result looks surprising.
- **Greedy = lossless.** Speculation must not change the emitted tokens. If output
  differs from the baseline at temp 0, that is a bug, not a feature.

## Workflow

1. Open an issue describing the change and, for perf changes, the hardware you measured on.
2. Keep PRs focused. Update `BENCH.md` (the permanent journal) with conditions + numbers.
3. `./reproduce.sh` must still print the invariant **PASS** verdict.
4. No secrets, tokens, or personal paths in commits.

## Scope

Reconstructed and validated on a single consumer GPU (RTX 5060, 8 GB). Contributions
that keep the "one command, one GPU, training-free" spirit are the most welcome.
