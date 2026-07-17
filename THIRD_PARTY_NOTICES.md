# Third-Party Notices

FRONDE is distributed under the MIT License (see `LICENSE`). It **builds on** and, at
runtime, **invokes** third-party software that is not redistributed in this repository
(it is fetched by `reproduce.sh`). Their licenses and notices are reproduced below.

---

## llama.cpp

- Project: <https://github.com/ggml-org/llama.cpp>
- Used as: the inference engine (`llama-cli`, `llama-server`, `llama-bench`) and its
  `ggml` library. Pinned in this project at tag `b10034` (commit `505b1ed1…`).
- License: **MIT**

```
MIT License

Copyright (c) 2023-2024 The ggml authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Python packages (runtime tooling)

Used by the harness / demo, installed from PyPI, not redistributed here:

- **rich** — MIT License — <https://github.com/Textualize/rich>
- **matplotlib** — Matplotlib License (BSD-style, PSF-based) — <https://matplotlib.org/stable/project/license.html>

## NVIDIA CUDA Toolkit

- Used only as the build toolchain (`nvcc`, CUDA runtime/libraries) to compile
  llama.cpp for `sm_120`. Governed by the **NVIDIA CUDA Toolkit EULA**; not
  redistributed by this project.

---

Model weights (Qwen3) have their own terms — see `MODEL_LICENSES.md`.
