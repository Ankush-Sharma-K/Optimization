# kolamNet — Days 1–2 Summary

**Phase:** 1 — Representation & Rendering
**Covers:** Pulli (dot) grid representation (Day 1) + Genome encoding (Day 2)

---

## Day 1 — Pulli Grid Representation

### Conceptual Overview

Every Kolam is drawn *around* a grid of dots called **pulli** — the curve never
touches the dots directly, it loops and weaves between and around them. The
pattern's symmetry (4-fold, 8-fold rotational, or mirror symmetry) is defined
relative to this grid.

Since the genetic algorithm will eventually evolve *how a curve moves through
this grid*, the grid had to be built first and be geometrically correct —
genome encoding, mutation, and symmetry-based fitness all depend on it.

Two classic pulli layouts were implemented:
- **Square grid** — plain n×n lattice of dots
- **Diamond grid** — the traditional rhombus shape used in most real Kolams,
  where each row grows by one dot until the middle row, then shrinks back
  down (1, 2, 3, ..., n, ..., 3, 2, 1)

Both were built since it's not yet known which will work better once fitness
scoring is in place.

### What Was Built

**`PulliGrid` class (`src/grid.py`)**
- Python `dataclass` taking size `n`, `grid_type` (`"square"` / `"diamond"`),
  and dot `spacing`; builds the list of (x, y) dot coordinates.
- `_build_square()` / `_build_diamond()` — construction methods. The diamond
  builder computes row lengths as `1..n..1` and centers each row so the
  result is a proper rhombus.
- `.center` — centroid of all points; used as the pivot for symmetry
  transforms.
- `.symmetry_axes(kind, order)` — returns transform functions for
  `"rotational"` (n-fold rotation matrices around the centroid) or
  `"reflective"` (horizontal/vertical mirror) symmetry. Will drive
  symmetry-based fitness scoring in Phase 2.
- `.nearest_point(x, y)` — snaps arbitrary coordinates to the closest grid
  dot; will keep future mutation operators grid-aligned.

**`visualize_grid.py`**
- Sanity-check script (not part of the final pipeline) — plots both grid
  types side by side with centroid marked. Confirmed both grids are
  geometrically correct.

**Debugging note**
- The original save path (`../outputs/...`) was relative to the *working
  directory*, which caused a `FileNotFoundError` depending on where the
  script was launched from. Fixed by anchoring the output path to the
  script's own file location via `os.path.dirname(os.path.abspath(__file__))`
  — this pattern was reused in every script written afterward to avoid the
  same issue.

---

## Day 2 — Genome Encoding (Truchet-Tile Representation)

### Conceptual Overview

Day 1 gave us the dots. Day 2 answers the actual question a GA needs
answered: **how do we represent a Kolam pattern itself as something that can
be mutated and crossed over?**

Traditional Kolam curves are built one small square "cell" at a time — every
2×2 block of neighboring pulli dots forms one cell, and that cell contains
two quarter-circle arcs in one of two possible orientations. This is exactly
the classic **Truchet tile** idea. Line enough oriented tiles up next to each
other and the individual arcs chain together into the continuous, looping
curves that make a Kolam.

This makes for a very GA-friendly genome:
- **one gene = one tile's orientation** (0 or 1)
- **mutation** = flip a single tile
- **crossover** = swap a block of tiles between two parent genomes
- the tile grid maps 1:1 onto the arc renderer being built next (Day 3) — no
  extra translation layer needed between "genome" and "drawable pattern"

Currently implemented for **square grids only**. Diamond-grid cells aren't
uniform 2×2 blocks (row lengths change), so tiling rules for that layout are
deferred until the square-grid pipeline (encoding → rendering → fitness) is
proven end-to-end.

### Logical Design

- The genome is stored internally as a 2D grid of tile types (`rows × cols`,
  where `rows = cols = n - 1` for an `n`-dot square `PulliGrid`) — this
  mirrors the grid's own geometry so every gene has an obvious, direct
  mapping to a physical cell.
- For GA operators (selection, crossover, mutation — Phase 3), the 2D grid
  is flattened into a plain 1D list of integers via `to_chromosome()`, and
  rebuilt via `from_chromosome()`. Keeping these two representations
  separate means the geometric logic (grid.py, genome.py) stays clean, while
  the evolutionary operators can work on a simple flat array without caring
  about geometry at all.
- `cell_corners(i, j)` pulls the four bounding dot coordinates for any cell
  straight from the `PulliGrid`, so the genome and the grid can never drift
  out of sync with each other.

### What Was Built

**`src/genome.py` — `KolamGenome` class**
- `TileType` enum: `ARC_A` (top-left↔bottom-right) / `ARC_B`
  (top-right↔bottom-left)
- `.randomize(rng)` — fills the tile grid randomly; accepts a seeded
  `random.Random` for reproducible tests
- `.to_chromosome()` / `.from_chromosome()` — the flatten/rebuild pair
  described above
- `.cell_corners(i, j)` — geometry lookup tying genome cells to grid dots
- `.as_symbol_grid()` — quick `\` / `/` text preview for fast debugging
  without rendering anything

**`src/visualize_genome.py`**
- Draws a straight diagonal per tile (not the final curved arcs — that's
  Day 3) purely to confirm each gene maps to the correct grid cell with the
  correct orientation before the real renderer is built.

### Verified

- A 6×6 dot grid produces exactly 25 genes (5×5 cells), confirmed via the
  printed chromosome and symbol-grid output.
- The visual sanity check (`day2_genome_sanity_check.png`) rendered two
  different random seeds side by side, producing distinct but correctly
  grid-aligned diagonal patterns — already visibly forming the zigzag/diamond
  chains characteristic of Truchet mazes, and by extension, Kolam-style
  curves.

### Why This Matters for Later Phases

Because the genome already maps 1:1 onto real grid geometry, Day 3 only
needs to swap each straight diagonal placeholder for the correct pair of
curved arcs — no restructuring of the genome itself is needed. It also means
Phase 3's crossover/mutation operators can operate on a plain flat list of
0s and 1s without needing any awareness of geometry.

---

## Files Produced So Far

```
OT Project/
├── requirements.txt
├── PROGRESS.md
├── src/
│   ├── grid.py
│   ├── visualize_grid.py
│   ├── genome.py
│   └── visualize_genome.py
├── data/       (empty — reference Kolam dataset goes here, Day 6)
└── outputs/
    ├── day1_grid_sanity_check.png
    └── day2_genome_sanity_check.png
```

---

## Next Up: Day 3

Build the actual Kolam renderer — replace each tile's straight-diagonal
placeholder with proper quarter-circle arcs, so genomes render as real
Kolam-style curves instead of the Truchet-maze preview.