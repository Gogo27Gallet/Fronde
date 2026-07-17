# Show HN

**Title:** Show HN: Adaptive speculative decoding on a $300 GPU

**URL:** https://github.com/Gogo27Gallet/Fronde

---

**Author comment (~250 words):**

I lost a Windows research campaign to a reformat and rebuilt it on Linux to re-check every number, cold-first.

Short version: on an RTX 5060 (8 GB, 145 W cap) running Qwen3-8B-Q4_K_M, plain decoding already hits 80.1 tok/s — 90% of the 89 tok/s memory-bandwidth ceiling, using under 1% of the GPU's compute. Prompt processing runs 37.8× faster than generation. So the whole game is producing several tokens per read of the weights.

Three things I'd like reviewed:

- A stock 0.6B draft gives 1.56× / 1.97× / 1.92× on code / math / JSON, and the worst case across every content type is 0.99×. The −33% prose regression I saw on Windows turned out to be a WDDM/VRAM-spill artifact; it's gone on Linux.
- Prompt-copy n-gram (no second model) is where edits pay: 5.26× cold on a JSON edit, up to ~9× on a near-pure copy, and 3.92× wall-clock on a 5-step agent loop — emitting the exact same tokens as baseline (greedy = lossless).
- Two honest negatives: Qwen3's default "thinking" silently killed edit speedups (5.3× → 1.03×) until I set `--reasoning off`; and EAGLE-3 collapsed on my Q4 target (its own model card only claims ~1.7×).

The router *measures* a short probe instead of predicting, so it can conservatively route novel code to the safe floor (documented as the cold-probe caveat). Not a new category — see SpecRouter, MetaSD, EfficientEdit's 13× — just the training-free, single-GPU, one-command-repro corner of it.

reproduce or break it — looking for RTX 30/40/50 owners: https://github.com/Gogo27Gallet/Fronde
