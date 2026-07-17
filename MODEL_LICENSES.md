# Model Licenses

This repository contains **no model weights**. The `models/` directory is
git-ignored; `reproduce.sh` downloads the GGUF files from Hugging Face and verifies
their SHA256 before any benchmark. The models used are governed by their own licenses,
summarized here for convenience — the upstream `LICENSE` file is authoritative.

## Qwen3 (target and draft models)

Both models are published by the **Qwen team, Alibaba Cloud**, and released under the
**Apache License 2.0**.

| Model | Role | Repository | License |
|---|---|---|---|
| Qwen3-8B (Q4_K_M GGUF) | target | [`Qwen/Qwen3-8B-GGUF`](https://huggingface.co/Qwen/Qwen3-8B-GGUF) | Apache-2.0 |
| Qwen3-0.6B (Q8_0 GGUF) | draft | [`Qwen/Qwen3-0.6B-GGUF`](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF) | Apache-2.0 |

License texts:
- <https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE>
- <https://huggingface.co/Qwen/Qwen3-0.6B/blob/main/LICENSE>

Apache-2.0 permits commercial and private use, modification, and redistribution,
subject to attribution and the terms in the license. FRONDE does not modify the model
weights; it only runs inference over them and reports throughput measurements.

> Verify the exact license on the model card at download time — upstream terms can
> change, and the `LICENSE` file in each Hugging Face repository is the source of truth.
