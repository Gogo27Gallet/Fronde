# Security Policy

FRONDE is a research/benchmark project that runs local models through
[llama.cpp](https://github.com/ggml-org/llama.cpp). It ships no network service of its
own; the only listener is a **local** `llama-server` bound to `127.0.0.1` for the
router and demo.

## Reporting a vulnerability

Please report suspected vulnerabilities **privately**, not in a public issue:

- Open a private security advisory via GitHub:
  **Security → Advisories → Report a vulnerability** on this repository.

Include a description, affected file/commit, and a minimal reproduction. Expect an
initial acknowledgement within a reasonable delay for a solo-maintained project.

## Scope and expectations

- **In scope:** issues in this repository's own code (`fronde_router.py`, `scripts/`,
  `demo.py`, `reproduce.sh`) — e.g. command injection, unsafe file handling, or the
  local server being reachable off-loopback.
- **Out of scope:** vulnerabilities in upstream dependencies (report those to
  [llama.cpp](https://github.com/ggml-org/llama.cpp) directly), and model *content*
  behaviour (hallucination, unsafe generations) — this project makes no safety claims
  about the underlying models.

## Hardening notes

- The router and demo bind `llama-server` to loopback only. Do not expose it publicly
  without adding authentication and a reverse proxy.
- Model weights are downloaded by the user and SHA256-verified by `reproduce.sh`; do
  not run with unverified GGUF files.
