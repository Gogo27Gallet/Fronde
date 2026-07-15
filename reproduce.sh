#!/usr/bin/env bash
# FRONDE — reproduction one-shot : vérif SHA → build → benchs → verdict invariants.
# Usage : ./reproduce.sh          (tout)
#         ./reproduce.sh --quick  (saute le build si binaires présents)
set -euo pipefail
cd "$(dirname "$0")"

LLAMA_TAG="b10034"
LLAMA_COMMIT="505b1ed15ca80e2a19f12ff4ac365e40fb374053"

echo "=== [1/5] Modèles (téléchargement + SHA256) ==="
bash scripts/download_models.sh

echo "=== [2/5] llama.cpp ${LLAMA_TAG} (${LLAMA_COMMIT:0:8}) ==="
if [ ! -d llama.cpp ]; then
  git clone https://github.com/ggml-org/llama.cpp.git
fi
git -C llama.cpp checkout -q "$LLAMA_COMMIT"
if [ ! -x llama.cpp/build/bin/llama-cli ] || [ "${1:-}" != "--quick" ]; then
  cmake -S llama.cpp -B llama.cpp/build -DGGML_CUDA=ON \
        -DCMAKE_CUDA_ARCHITECTURES=120 -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
  cmake --build llama.cpp/build --target llama-cli llama-server llama-bench -j "$(nproc)"
fi

echo "=== [3/5] GPU propre + power cap 145 W ==="
python3 scripts/gpu_monitor.py --check /dev/null

echo "=== [4/5] Benchs (protocole bracketé, temp 0, seed 42, 3 reps) ==="
mkdir -p results
python3 scripts/bench_runner.py \
  --configs baseline draft ngram-simple ngram-mod \
  --prompts gen_code_python gen_prose_fr gen_prose_en gen_math gen_json \
            edit_rename_typehints edit_bugfix_offbyone edit_json \
  --out results/reproduce.json

echo "=== [5/5] Invariants FRONDE-Router ==="
python3 scripts/check_invariants.py results/reproduce.json
