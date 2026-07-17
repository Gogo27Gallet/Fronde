# Feature request issue (llama.cpp)

Target: github.com/ggml-org/llama.cpp — a well-formed feature request motivated by
client-side speculative routing.

---

**Title:** server: per-request speculative-decoding parameters

**Body:**

### Motivation

`llama-server` fixes the speculative-decoding strategy at startup: the `--spec-type`
(draft / ngram-simple / ngram-mod), the draft model, and the n-gram/draft parameters
are all process-level. Switching strategy therefore means restarting the server, which
reloads the target model (5+ GB) and dominates end-to-end latency.

This matters as soon as you route *per prompt*. The best speculative mode depends on
content: a small draft wins on structured generation (I measure ~1.5–2× on code/math/
JSON), while training-free prompt-copy n-gram wins on edits (cold-first: ~5× on a JSON
edit, up to ~9× on a near-pure copy), and plain prose is best left at the safe floor.
A client that wants those wins on a mixed workload currently has to bounce the server
between modes — one 5 GB reload per switch — which erases the gains it is trying to
capture. (I work around this today with epoch batching, grouping same-mode requests to
amortize one restart per batch, but that's a scheduling hack, not a fix.)

### Proposal

Allow a request to *override* speculative parameters for that request only, falling
back to the server defaults when absent. On `/completion` (and the OpenAI-compatible
endpoints), accept optional fields such as:

```jsonc
{
  "prompt": "...",
  "speculative": {
    "type": "ngram-simple",   // draft | ngram-simple | ngram-mod | off
    "draft_n_max": 12,          // when type=draft
    "draft_p_min": 0.45,
    "ngram_mod_n_match": 12     // when type=ngram-mod
  }
}
```

### Constraints / scope

- The **draft model can't be hot-loaded per request** — it has to be resident. So the
  realistic scope is: toggle between *already-loaded* resources (draft on/off, n-gram
  variants, or no speculation) and tune the parameters that don't require new weights.
  Requesting `draft` when no `-md` model was loaded should error cleanly.
- Greedy correctness must be preserved: speculation should not change emitted tokens.
- Per-request overrides should be validated and clamped like the sampling params.

### Why it's worth it

It turns a warm server into something a per-prompt router can actually use without
paying a model reload, which is the difference between "nice benchmark" and "usable on
a single 8 GB GPU". Full motivation, measurements, and a ~250-line reference router
that currently restarts the server per epoch: https://github.com/Gogo27Gallet/Fronde

Happy to prototype the request-parsing side if there's appetite for the feature.
Reproduce or break it — especially RTX 30/40/50 owners.
