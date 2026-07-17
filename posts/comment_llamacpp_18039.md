# Comment for llama.cpp PR #18039 (EAGLE3 speculative decoding support)

Context: this is a constructive negative data point to share on the EAGLE3 PR thread,
not a criticism of the work. Cold-first, honest, with a link back.

---

Thanks for landing EAGLE3 support. Trying it gave me a clean negative data point on a consumer 8 GB card that might help others calibrate expectations, so I wanted to share it here.

Setup: RTX 5060 (8 GB), Qwen3-8B as a **Q4_K_M** target, AngelSlim EAGLE-3 head, llama.cpp b10034, greedy, `--reasoning off`.

On my Q4 target the head didn't hold up. Acceptance ran ~58% on Python code but fell to ~14.8% on French prose, and across my content battery a plain stock **0.6B draft beat it everywhere**. Before blaming the head I tried to eliminate the usual suspects one at a time — heavy quantization of the target, the head conversion, d2t vocabulary coverage, and chat formatting — and none of them explained the drop. The head's own model card only advertises ~1.7×, so this reads as my expectations being off rather than a bug in the PR.

Two things that might be worth a line in the docs for Q4-target users: (1) sensitivity to how heavily the target is quantized, and (2) how large the content dependence is (structured code vs prose). I'm happy to share raw acceptance-by-content numbers if useful.

Full protocol and numbers (with a training-free 0.6B-draft / prompt-copy n-gram baseline for comparison) are here: https://github.com/Gogo27Gallet/Fronde — and if anyone has EAGLE-3 working well on a **Q4** target, I'd genuinely like to be proven wrong. Reproduce or break it.
