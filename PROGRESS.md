# kolamNet — Progress Report

**Project:** Genetic Algorithm for Generative Kolam Pattern Recreation
**Plan:** 15-day phased build, deployed as a Streamlit web app
**Fitness approach:** dataset-driven similarity (user has a reference Kolam image dataset) + symmetry/loop-closure scoring

## Overall Plan

| Phase | Days | Focus |
|---|---|---|
| 1 — Representation & Rendering | 1–3 | Pulli grid, genome encoding, image renderer |
| 2 — Population & Fitness | 4–7 | Init population, symmetry fitness, dataset preprocessing, similarity fitness |
| 3 — Evolution Engine | 8–11 | Selection, crossover, mutation, main GA loop |
| 4 — App & Deployment | 12–15 | Experiments/tuning, Streamlit UI, deployment, polish |

**Status: Phase 1, Day 1 of 15 complete.**

---

## Day 1 — Project Scaffold + Pulli Grid Representation

**Goal:** Build the dot-grid scaffold every Kolam genome will be drawn on.

**What was built:**
- `src/grid.py` — `PulliGrid` class supporting two grid types:
  - `"square"` — standard n×n lattice
  - `"diamond"` — classic rhombus pulli arrangement (rows grow 1→n→1), the traditional layout for most South Indian Kolams
- Each grid exposes:
  - `.points` — flat list of (x, y) dot coordinates
  - `.center` — centroid, used as the pivot for symmetry transforms
  - `.symmetry_axes(kind, order)` — returns rotation/reflection transform functions (4-fold, 8-fold rotational, or reflective). This is pre-built now because Phase 2's symmetry fitness function and later symmetric genome generation both need it.
  - `.nearest_point(x, y)` — snaps arbitrary coordinates to the nearest dot (useful later for mutation operators that need to stay grid-aligned)
- `src/visualize_grid.py` — sanity-check plot confirming dot placement is correct for both grid types

**Verified:** Rendered both grid types at n=6; square forms a clean lattice, diamond forms the correct rhombus shape (1,2,3,4,5,6,5,4,3,2,1 row pattern). Output saved as `outputs/day1_grid_sanity_check.png`.

**Why this matters for later phases:** The genome (Day 2) will encode a Kolam as a sequence of moves/loops *relative to this grid* — so the grid needs correct geometry and symmetry-transform support before anything else is built. Getting the diamond grid's centering right also matters for accurate reflective/rotational symmetry fitness in Phase 2.

**Decisions made:**
- Stack: Streamlit (for app + deployment)
- Fitness: will use your reference Kolam dataset for similarity scoring, in addition to symmetry/loop-closure rules
- Default grid type for early testing: diamond (most representative of traditional Kolams); square will remain supported as an option

**Next (Day 2):** Design the genome encoding — how a sequence of curve segments around the pulli grid gets represented as a chromosome (genes), so it can later be mutated and crossed over.

**Files:**
```
kolamnet/
├── requirements.txt
├── PROGRESS.md
├── src/
│   ├── grid.py
│   └── visualize_grid.py
├── data/            (empty — for your reference Kolam dataset, Day 6)
└── outputs/
    └── day1_grid_sanity_check.png
```
