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

**Status: Phase 1, Day 2 of 15 complete.**

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

---

## Day 2 — Genome Encoding (Truchet-Tile Representation)

**Goal:** Represent an actual Kolam pattern (not just the dot grid) as a
chromosome the GA can mutate and cross over.

**Concept:** Between every 2×2 block of neighboring pulli dots there's a
square "cell." Traditional Kolam curves are built from two quarter-circle
arcs per cell, in one of two possible orientations — the same idea as a
classic **Truchet tile**. Line enough oriented tiles up and the individual
arcs chain into continuous looping curves. This makes the genome design
simple: one gene per cell (0 or 1, the tile orientation), where mutation =
flip one tile, and crossover = swap a block of tiles between two parents.

**What was built:**
- `src/genome.py` — `KolamGenome` class (square grids for now; diamond-grid
  tiling is deferred until tile-connectivity rules are settled, since its
  cells aren't uniform 2×2 blocks)
  - `TileType` enum: `ARC_A` (top-left↔bottom-right) / `ARC_B`
    (top-right↔bottom-left)
  - `.randomize()` — fills the tile grid randomly (seedable, for
    reproducible tests)
  - `.to_chromosome()` / `.from_chromosome()` — flattens/rebuilds the 2D
    tile grid as a 1D list — this flat list is what selection, crossover,
    and mutation will actually operate on in Phase 3
  - `.cell_corners(i, j)` — pulls the 4 dot coordinates bounding a cell
    directly from the `PulliGrid`, so genome and grid stay in sync
  - `.as_symbol_grid()` — quick text preview (`\` / `/` per cell) for fast
    debugging without needing to render anything
- `src/visualize_genome.py` — draws a straight diagonal per tile (not the
  final curved arcs yet) purely to confirm each gene maps to the right grid
  cell with the right orientation, before building the real renderer

**Verified:** For a 6×6 dot grid → 25 genes (5×5 cells), confirmed via
printed chromosome + symbol grid. Visual sanity check
(`day2_genome_sanity_check.png`) shows two different random seeds producing
distinct, correctly-aligned diagonal patterns — already visibly forming the
zigzag/diamond chains characteristic of Truchet mazes and, by extension,
Kolam-style curves.

**Why this matters for later phases:** Because the genome already maps 1:1
onto real grid geometry, Day 3 only needs to replace each straight diagonal
with the correct curved arc pair — no restructuring of the genome itself.
It also means crossover/mutation (Phase 3) can operate on a plain flat list
of 0s and 1s without needing to know anything about geometry at all.

**Next (Day 3):** Build the actual Kolam renderer — replace each tile's
diagonal placeholder with proper quarter-circle arcs so genomes render as
real Kolam-style curves.

**Files added:**
```
src/
├── genome.py
└── visualize_genome.py
outputs/
└── day2_genome_sanity_check.png
```