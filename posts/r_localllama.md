# r/LocalLLaMA

**Title:** Adaptive speculative decoding on a $300 GPU (RTX 5060, 8 GB): up to ~9× on code edits, no material regression in my suite — reproduce or break it

---

I rebuilt a lost Windows research campaign on Linux and re-validated every number cold-first. Everything below is on an RTX 5060 (8 GB, 145 W cap), Ryzen 5 5500, Qwen3-8B-Q4_K_M as target and Qwen3-0.6B-Q8_0 as draft, llama.cpp b10034.

**The premise.** Token generation is memory-bound. On this card, plain decoding already runs at 80.1 tok/s, which is ~90% of the 448 GB/s ÷ 5.03 GB ≈ 89 tok/s ceiling, while using under 1% of the GPU's compute. Prompt processing is 37.8× faster than generation. There's a lot of idle silicon, and the only way to use it is to produce more than one token per read of the weights.

**Draft model (0.6B).** It's a bet that pays on structured content: 1.56× on Python code, 1.97× on step-by-step math, 1.92× on JSON. The important part for me is the worst case: 0.99× across every content type. On Windows I had a nasty −33% regression on prose; it turned out to be a WDDM/VRAM-spill artifact, not the method. On Linux with a clean VRAM budget it disappeared. The 0.6B alone runs ~407 tok/s vs ~700 theoretical, so it's kernel-launch-bound, not bandwidth-bound — which is also why a Q4 draft loses to Q8.

**Edits are the goldmine, and they're training-free.** Prompt-copy n-gram speculation (no second model at all) tracks the copied fraction of the output. Leading with the cold, first-encounter numbers: 5.26× on a JSON edit (~404 tok/s), 1.86× on a heavy rewrite, up to ~9× on a near-pure-copy bugfix. On a warm server doing 5 successive edits of the same file, it's 3.92× wall-clock and ~285 tok/s sustained, with peaks around 887 tok/s once the copy memory is hot. Both modes emit the exact same tokens as the baseline — greedy decoding, so speculation is lossless.

**Two negatives I want to keep honest.** First, Qwen3 "thinks" by default, and chain-of-thought is prose, not copy: one run with thinking on cut edits from 5.3× to 1.03×. Fix is `--reasoning off` everywhere; if your acceptance rate cratered on edits, check this first. Second, EAGLE-3 (AngelSlim head for Qwen3-8B) collapsed on my Q4 target — 58% acceptance on code down to 14.8% on French prose, beaten everywhere by the plain 0.6B draft. I eliminated quantization, conversion, d2t coverage and chat format as causes by testing each; the model card itself only claims ~1.7×. My expectations were wrong, not the head.

**The router measures, it doesn't predict.** A 48-token probe on the aggressive config decides the mode, with n-gram-simple as a never-below-baseline floor (that "never below baseline" is a router invariant, checked by reproduce.sh, verdict PASS — not a claim about every possible prompt). Being honest: because the probe is only 48 tokens, a draft hasn't amortized yet, so novel code can get conservatively routed to the safe floor instead of the draft. That's the documented cold-probe caveat; the demo warms the server before routing to match the battery protocol.

**Related work, because I didn't invent this category.** SpecRouter does adaptive multi-level routing across model chains; MetaSD does bandit selection across multiple trained drafters; EfficientEdit does edit-oriented speculative decoding with a trained draft and reports up to 13×. My corner is deliberately narrow: training-free, lossless, one consumer GPU, routing by measurement, and a one-command reproduction.

Everything is bracketed (reference before and after, ratios not absolutes) because thermal drift is real — I measured −11% over a session. Full protocol, raw JSON, graphs and a demo GIF are in the repo.

reproduce or break it — looking for RTX 30/40/50 owners: https://github.com/Gogo27Gallet/Fronde
