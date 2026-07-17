# X / Twitter thread

Each tweet ≤ 280 chars. Cold-first throughout.

---

**1/**
I lost a Windows speculative-decoding campaign to a reformat, rebuilt it on Linux, and re-checked every number cold-first.

On a $300 RTX 5060 (8GB), plain decoding is already 80.1 tok/s = 90% of the memory ceiling. The whole game: >1 token per weight read. 🧵

**2/**
Generation is memory-bound. On this card prompt processing runs 37.8× faster than decoding, using <1% of the compute. All that idle silicon is the entire opportunity.

**3/**
Stock 0.6B draft: 1.56× / 1.97× / 1.92× on code / math / JSON. Worst case across every content type: 0.99×.

That −33% prose regression I had on Windows? A WDDM/VRAM-spill artifact. Gone on Linux.

**4/**
Edits are the goldmine, training-free (prompt-copy n-gram, no 2nd model). Cold-first: 5.26× on a JSON edit, ~9× on a near-pure copy. Warm 5-edit agent loop: 3.92× wall-clock, ~285 tok/s sustained (peaks ~887). Same tokens as baseline — greedy is lossless.

**5/**
Negative #1: Qwen3 "thinks" by default. Chain-of-thought is prose, not copy — it cut edits from 5.3× to 1.03×.

Fix: --reasoning off. If your edit acceptance cratered, check this first.

**6/**
Negative #2: EAGLE-3 collapsed on my Q4 target (58% accept on code → 14.8% on prose), beaten by the plain 0.6B. Eliminated quantization/conversion/coverage/chat-format by test. Model card only claims ~1.7×. Expectations wrong, not the head.

**7/**
The router measures a 48-token probe instead of predicting. Honest caveat: on 48 tokens a draft hasn't amortized, so novel code can get routed to the safe floor. "Never below baseline" is the router invariant (reproduce.sh PASS), not a universal promise.

**8/**
Not a new category: SpecRouter (routing), MetaSD (bandit drafters), EfficientEdit (edit-oriented, up to 13×). My corner: training-free, lossless, one consumer GPU, routing by measurement, one-command repro.

**9/**
reproduce or break it — looking for RTX 30/40/50 owners 👇
https://github.com/Gogo27Gallet/Fronde
