# FRONDE — Journal de bench (reconstruction Linux)

> Ce fichier est la mémoire du projet. Chaque étape, version, SHA, condition et décision y est consignée au fil de l'eau.

## Mission

Reconstruction sous Ubuntu de la campagne Windows (code/données perdus au reformatage).
Thèse : génération = memory-bound. Plafond théorique = 448 Go/s ÷ 5,03 Go ≈ **89 tok/s** ;
Windows l'atteignait à 85 % (76 tok/s) en utilisant <1 % du compute. Ratio pp/tg ≈ 38× = le gisement.
Objectif : plusieurs tokens par lecture des poids (spéculatif draft + ngram), routés par FRONDE-Router.

## Matériel / OS (vérifié 2026-07-15)

| Composant | Valeur |
|---|---|
| CPU | Ryzen 5 5500 |
| GPU | RTX 5060, 8151 MiB VRAM, 448 Go/s, power cap **145 W** (vérifié nvidia-smi) |
| Driver | 595.71.05 |
| RAM | 14 Gi |
| OS | Ubuntu 26.04 LTS (Resolute Raccoon), noyau 7.0.0-27-generic |
| Toolchain | gcc 15.2.0, cmake 4.2.3, git 2.53.0, Python 3.14.4 |

## Références Windows (à confronter — attendu : Linux ≥ Windows, pas de spill WDDM)

| Mesure | Windows |
|---|---|
| Baseline 8B Q4_K_M tg128 / pp512 | 76 tok/s / ~2900 tok/s (ratio 38×) |
| Draft 0.6B Q8_0 (n_max=12, p_min=0.45) — code | 97–112 tok/s (accept 66 %) |
| Idem — prose | ~50 tok/s (**−33 %**, coût draft ~2,6 ms/token même muet) |
| 0.6B seul | 378 tok/s vs ~700 théoriques → kernel-launch-bound |
| ngram-simple | ≥ réf partout (« jamais perdant ») |
| ngram-mod, batterie edit | 6,5× froid / 7,6× répété, pics >600 tok/s ; speedup ∝ fraction copiée (1,9×→8,4×) |
| Agent loop (5 éditions) | 3,8× wall-clock, 260 tok/s soutenus |
| EAGLE-3 (AngelSlim) | ÉCHEC sur cible Q4 (accept 58 % code → 14,8 % prose FR). **Ne pas re-tester.** |

## Leçons méthodo (non négociables)

1. **Bracketing** : dérive thermique −11 %/session → réf avant + réf après chaque comparatif, on compare des ratios, jamais des absolus. Réfs divergentes >5 % ⇒ run invalidé.
2. **Power cap** : réf pinée à 145 W ; les modes spéculatifs tirent ~15 W de moins → logger les watts par mode.
3. **VRAM squattée = spill silencieux ÷2** (bug WDDM Windows) → vérifier si présent sous Linux ; GPU propre avant chaque bench.
4. **Acceptation qui explose = suspecter une dégénérescence** → toujours capturer les sorties.

## Versions épinglées

| Composant | Version | Commit/SHA |
|---|---|---|
| CUDA toolkit | _(en cours)_ | |
| llama.cpp | tag **b10034** | `505b1ed15ca80e2a19f12ff4ac365e40fb374053` |
| Qwen3-8B-Q4_K_M | 5 027 783 488 o ✔ (= Windows), source Qwen/Qwen3-8B-GGUF | SHA256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` ✔ **vérifié 2026-07-15** |
| Qwen3-0.6B-Q8_0 | 511 791 104+ o, source Qwen/Qwen3-0.6B-GGUF | SHA256 `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031` |

## Journal

### 2026-07-15 — Phase 2 : environnement
- Structure `~/fronde` créée. Machine vérifiée (tableau ci-dessus).
- Décision utilisateur : CUDA via repo apt NVIDIA officiel, toolkit 13.x.
- llama.cpp épinglé au tag **b10034** (`505b1ed1`). Vérifié : `ngram-simple` et `ngram-mod` sont
  **upstream** (`--spec-type ngram-simple|ngram-mod`, réglages `--spec-ngram-simple-size-{n,m}`,
  `--spec-ngram-mod-n-{min,max,match}`) → rien à réimplémenter, mêmes noms que la campagne Windows.
- Qwen3-0.6B-Q8_0 téléchargé, SHA256 enregistré. 8B en cours.
- Batterie de prompts figée (5 gen + 3 edit) dans `prompts/`. `scripts/gpu_monitor.py` écrit.
- CUDA **13.1.1** installé (repo apt NVIDIA ubuntu2604, `cuda-toolkit-13-1`).
- **Incompatibilité CUDA 13.1 ↔ glibc Ubuntu 26.04** : la glibc déclare `rsqrt`/`rsqrtf` (C23,
  garde `IEC_60559_FUNCS_EXT_C23`, activée par `_GNU_SOURCE` que g++ définit toujours) avec
  `noexcept`, en conflit avec `crt/math_functions.h`. Correctif : ajout de `noexcept (true)` aux
  2 déclarations CUDA (l. 629/653), sauvegarde dans `math_functions.h.bak`. À retirer quand
  NVIDIA corrigera.
- Harnais : llama-cli b10034 exige `-st` + stdin fermé (sinon mode interactif) ; timings au format
  `[ Prompt: X t/s | Generation: Y t/s ]`, `LC_ALL=C` obligatoire (virgule décimale FR sinon).
- Check « GPU propre » recalibré : le bureau (gnome-shell + remote-desktop + Chrome) occupe
  ~544 MiB incompressibles → critère = **VRAM libre ≥ 6800 MiB** (modèle 5 Go + KV + marge),
  pas un seuil d'occupation.

### 2026-07-15 — Phase 4 : premiers chiffres Linux (build CUDA sm_120, b10034)

| Mesure | Windows | **Linux** | Écart |
|---|---|---|---|
| 8B Q4_K_M tg128 | 76 | **80,12 ± 0,08** | **+5,4 %** — 90 % du plafond théorique (89) ; pas de spill WDDM, prédiction confirmée |
| 8B Q4_K_M pp512 | ~2900 | **3031 ± 96** | +4,5 % ; ratio pp/tg = **37,8×** (le gisement annoncé ≈ 38×) |
| 0.6B Q8_0 tg128 | 378 | **406,85 ± 1,79** | +7,6 % ; toujours ~58 % du théorique (~700) → **kernel-launch-bound confirmé sous Linux** |
| 0.6B Q8_0 pp512 | — | 24 651 ± 3 312 | |
| ngram-simple, gen_json (smoke, 1 rep) | ≥ réf | ratio **1,010** (réfs 78,1/77,6, dérive 0,6 %) | plancher « jamais perdant » : premier point conforme |

- Batterie complète lancée (bracketé, 3 reps) : baseline/draft/ngram-simple/ngram-mod × 8 prompts,
  puis grille draft n_max{8,12}×p_min{0.45,0.75} × {code, prose FR} → `results/battery_*.json`.

### 2026-07-16 — DÉCOUVERTE : le mode thinking de Qwen3 tuait le gisement d'édition

- Batterie v1 : 38/38 mesures valides (dérive ≤ 2,6 %) MAIS éditions à 1,03–1,56× au lieu des
  6,5× Windows. **Leçon 4 appliquée** (inspecter les sorties) : le modèle partait en
  chain-of-thought (`[Start thinking]` — llama-cli b10034 applique le template chat même en
  single-turn, et Qwen3 pense par défaut) → la sortie n'était plus une copie du prompt → rien à
  accepter pour ngram-mod. La campagne Windows avait nécessairement le thinking désactivé.
- Correctif : `--reasoning off` partout (runner, router, agent-loop).
- Tuning ngram-mod sur edit_json (thinking off, baseline 77,2) :
  n_match=6 → 290,7 t/s ; **n_match=12 → 409,2 t/s (5,3×)** ; n_match=24 (défaut) → 276,4 t/s.
  → `--spec-ngram-mod-n-match 12` figé dans toutes les configs.
- Trouvailles v1 à confirmer en v2 : **la régression prose du draft a disparu sous Linux**
  (Windows −33 % → Linux 1,00) ; draft à **1,39× sur math** (108 t/s) ; bracketing vindiqué
  (fenêtre entière à 64 t/s pendant gen_prose_fr, réfs comprises → ratios restés honnêtes).
