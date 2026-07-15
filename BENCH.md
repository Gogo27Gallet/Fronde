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
