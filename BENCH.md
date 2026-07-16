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

### 2026-07-16 — Phase 4/5 FINAL : batterie v2 (thinking off, n_match=12), 38/38 valides

Conditions : b10034 CUDA sm_120, `-c 4096 --reasoning off`, temp 0, seed 42, 3 reps (médiane),
bracketé (dérive max observée 2,6 %), cap 145 W vérifié.

**Génération** (ratio vs réf bracketée ; réf ≈ 76–78 t/s)

| prompt | draft (n12 p0.45) | ngram-simple | ngram-mod |
|---|---|---|---|
| code Python | **1,56× (122 t/s)** | 1,01 | 1,00 |
| prose FR | 1,02 | 1,00 | 1,00 |
| prose EN | 0,99 | 1,00 | 1,01 |
| math | **1,97× (153 t/s)** | 0,99 | 0,98 |
| JSON | **1,92× (150 t/s)** | 1,03 | 1,03 |

**Éditions** (sortie ≈ copie du prompt)

| tâche | draft | ngram-simple | ngram-mod |
|---|---|---|---|
| rename+hints (grosse réécriture) | **2,76×** | 1,87 | 1,86 |
| bugfix off-by-one (copie quasi pure) | 2,80 | 9,27 | **9,16× (697 t/s)** |
| edit JSON (3 changements) | 2,62 | 5,24 | **5,26× (404 t/s)** |

**Grille draft** (code / prose FR) : n12-p0.45 = champion code (1,56) ; n8-p0.45 : 1,60/0,99–1,04 ;
n8-p0.75 : 1,52/1,04 ; n12-p0.75 : 1,52/1,05 → plus aucune config perdante sous Linux.

**Agent-loop serveur chaud** (5 éditions, stop au fence, 4169 tokens identiques dans les 2 modes
→ la spéculation ne change pas la sortie) : ngram-mod **14,6 s vs 57,3 s = 3,92×**,
**284,8 t/s soutenus**, pic 887 t/s. **Windows (3,8× / 260) battu.**
NB : la même boucle en llama-cli (rechargement modèle à chaque tour) ne donnait que 1,17× —
le serveur chaud fait partie du protocole.

**Écarts vs Windows, commentés** :
1. Baseline +5 % (80,1), pas de spill WDDM — prédit et confirmé.
2. La régression prose du draft (−33 % Windows) **n'existe pas** sous Linux/b10034 — le coût du
   draft muet (~2,6 ms/tok Windows) a été absorbé (scheduler draft amélioré + launch overhead moindre).
3. Le gisement d'édition dépend du thinking OFF (découverte du jour) et de n_match=12 ;
   médiane edits ngram 5,26× froid (Windows 6,5×, mix de tâches différent), pics 887 vs >600.
4. Draft partout ≥ 0,99 → sous Linux le draft est devenu quasi « jamais perdant » aussi,
   mais ngram-simple reste le plancher sûr (zéro dépendance au 2e modèle).

### 2026-07-16 — Phase 5 : FRONDE-Router validé

- Rejeu hors-ligne des invariants sur battery_main v2 : **PASS global**
  (5/5 contenus ≥ réf ; router = champion statique sur code/math/JSON).
- Live (sonde 48 tok + époques + classe EDIT) : prose→safe 78,6 t/s ;
  math→aggressive 119,2 t/s ; edit_json→edit 327,1 t/s. Comportement conforme.

### 2026-07-16 — Phase 6 : livrable

- Agent-loop llama-cli (rechargement/tour) : 1,17× seulement → protocole corrigé : serveur chaud
  + stop au fence (`agent_loop_server.py`) → **3,92×, 285 t/s soutenus, pic 887 t/s**.
- Graphes générés (`results/*.png`) : ratio par contenu (ligne 1,0 = jamais perdant),
  vitesses, session GPU. Palette catégorielle validée, couleur fixe par config.
- `demo.py` validé de bout en bout : prose→safe 77,9 ; code→safe 76,5 ; JSON→aggressive 136,9 ;
  edit→edit **236,2 t/s**. README final chiffré. Repo complet, commits locaux, aucun push.
