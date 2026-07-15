#!/usr/bin/env bash
# FRONDE — téléchargement + vérification des modèles GGUF.
set -euo pipefail
cd "$(dirname "$0")/../models"

SHA_8B="d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785"
SIZE_8B=5027783488
SHA_06B="9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031"

fetch() { # url dest
  [ -f "$2" ] || { echo "↓ $2"; curl -L --fail -o "$2.part" "$1" && mv "$2.part" "$2"; }
}

fetch "https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf"   Qwen3-8B-Q4_K_M.gguf
fetch "https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q8_0.gguf" Qwen3-0.6B-Q8_0.gguf

echo "Vérification SHA256 + taille…"
actual_size=$(stat -c%s Qwen3-8B-Q4_K_M.gguf)
[ "$actual_size" = "$SIZE_8B" ] || { echo "FAIL: taille 8B $actual_size ≠ $SIZE_8B"; exit 1; }
echo "$SHA_8B  Qwen3-8B-Q4_K_M.gguf"    | sha256sum -c -
echo "$SHA_06B  Qwen3-0.6B-Q8_0.gguf"   | sha256sum -c -
echo "OK — modèles vérifiés."
