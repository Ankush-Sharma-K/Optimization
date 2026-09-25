# kolamNet — Days 1–4 Summary

**Phase:** 1 — Representation & Rendering (complete) → Phase 2 — Population & Fitness (in progress)
**Covers:** Pulli (dot) grid representation (Day 1) + Genome encoding (Day 2) + Arc renderer (Day 3) + Population initializer (Day 4)

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

## Day 3 — Arc Renderer (Phase 1 Complete)

### Conceptual Overview

Day 2 gave us a genome that maps 1:1 onto grid cells, but the visual preview
used straight diagonal lines — a placeholder, not an actual Kolam curve.
Day 3's job was to replace that placeholder with the real thing: proper
quarter-circle arcs, so a genome renders as an authentic-looking Kolam
pattern instead of a Truchet maze of straight lines.

Each cell's two arcs have a radius equal to half the cell's side length.
Each arc is centered on one corner of the cell and connects the midpoints
of that corner's two adjacent edges:

- **ARC_A** — one arc hugs the top-left corner (top-mid → left-mid), the
  other hugs the bottom-right corner (bottom-mid → right-mid)
- **ARC_B** — one arc hugs the top-right corner (top-mid → right-mid), the
  other hugs the bottom-left corner (bottom-mid → left-mid)

The key property that makes this work: every arc terminates *exactly* at an
edge midpoint, and every edge midpoint is shared with the neighboring cell.
So when two tiles sit next to each other, their arcs automatically meet up
at that shared point — with no gaps and no extra logic needed to "connect"
anything. This is precisely the mechanism that turns a grid of independent
tiles into one continuous, looping curve, which is the defining visual
signature of a real Kolam (the curve never touches a dot, and loops close
naturally wherever the tile pattern allows).

### Logical Design

- Arc angles are derived purely from corner geometry, not hardcoded per
  orientation — `_cell_arcs()` computes each arc's center and its
  `(theta1, theta2)` sweep directly from the cell's four corner coordinates
  and its `TileType`, keeping the renderer consistent with however
  `KolamGenome.cell_corners()` defines a cell.
- `render_genome()` deliberately takes a genome and returns a matplotlib
  `Axes` (rather than immediately saving a file) — this makes it reusable
  as the single rendering entry point for everything downstream: Phase 2's
  fitness functions will need to render a genome to score it against the
  reference dataset, and Phase 4's Streamlit app will need to render the
  live "best genome so far" during evolution. Both can call this same
  function unmodified.
- Axis limits are computed explicitly from `grid.bounding_box()` rather
  than relying on matplotlib's autoscaling — this keeps rendering correct
  even when dots are hidden (`show_dots=False`), which matters once this
  function is reused for a "clean" final output image with no debug dots.

### What Was Built

**`src/renderer.py`**
- `_cell_arcs(tl, tr, bl, br, tile)` — internal helper; returns the 2
  `(center, theta1, theta2)` arc definitions for a single cell
- `render_genome(genome, ax=None, show_dots=True, line_color="#8B2E2E", line_width=2.2, dot_color="#cccccc")`
  — the main renderer. Draws every cell's arcs onto a matplotlib `Axes`
  using `matplotlib.patches.Arc`, sets axis limits from the grid's bounding
  box, and returns the `Axes` for further customization or saving.

### Verified

Rendered the same seed=1 and seed=7 genomes used in the Day 2 sanity check,
for a direct before/after comparison. The output
(`day3_render_comparison.png`) shows smooth, continuous looping curves that
never touch the dots — including fully closed loops forming naturally
around isolated dots wherever two matching tiles happen to meet. This
confirms the arc-matching logic is geometrically correct.

### Why This Matters for Later Phases

`render_genome()` is now the single reusable rendering entry point the rest
of the project will build on — Phase 2's fitness scoring and Phase 4's
Streamlit app both need to turn a genome into an image, and neither should
need a second renderer.

**Phase 1 (Representation & Rendering) is now complete.**

---

## Files Produced So Far

```
OT Project/
├── requirements.txt
├── PROGRESS.md
├── context.md
├── Summary.md
├── src/
│   ├── grid.py
│   ├── visualize_grid.py
│   ├── genome.py
│   ├── visualize_genome.py
│   ├── renderer.py
│   ├── population.py
│   └── visualize_population.py
├── data/       (empty — reference Kolam dataset goes here, Day 6)
└── outputs/
    ├── day1_grid_sanity_check.png
    ├── day2_genome_sanity_check.png
    ├── day3_render_comparison.png
    └── day4_population_preview.png
```

---

## Day 4 — Population Initializer (Start of Phase 2)

### Conceptual Overview

Everything through Day 3 dealt with a single Kolam pattern at a time. A
genetic algorithm needs a whole **population** of candidate patterns
competing, being ranked, and producing offspring together. Day 4 is
deliberately narrow in scope: it's about creating and structurally
validating a batch of random genomes — not about scoring or evolving them
yet (that begins Day 5).

It's worth being precise about what "valid" means at this stage: because
every combination of Truchet tiles renders as *some* connected pattern,
there's no such thing as a geometrically illegal genome. "Structural
validity" here just means the tile grid is well-formed — correct
dimensions, real tile values — which mainly guards against bugs rather than
bad patterns. Judging whether a pattern is aesthetically good, symmetric,
or made of properly closed loops is a *fitness* question, not a *validity*
question, and that judgment starts on Day 5.

### Logical Design

- `Population` wraps a list of `KolamGenome` instances plus its own seeded
  random generator, so an entire population's randomness is reproducible
  from a single seed — not just each genome individually.
- `Population.chromosomes()` deliberately returns the flat-list form (not
  the `KolamGenome` objects themselves). This is the exact interface
  Phase 3's selection, crossover, and mutation operators are meant to
  consume, keeping evolutionary logic fully decoupled from grid geometry —
  those operators will never need to know what a "cell" or a "tile" is.
- `Population.replace()` was added now, even though nothing calls it yet,
  so the Day 11 main GA loop can swap in each new generation without
  needing to modify this class later.

### What Was Built

**`src/population.py`**
- `validate_genome(genome)` — structural validity check (correct
  dimensions, real `TileType` values only)
- `Population` class — `Population(grid, size, seed=None)`
  - `.initialize()` — fills `.genomes` with `size` random, validated
    genomes (each seeded from the population's own RNG)
  - `.chromosomes()` — flat-list view of every genome, for Phase 3's GA
    operators
  - `.replace(new_genomes)` — swaps in a new generation (reserved for
    Day 11)
  - behaves like a plain sequence: supports `len()`, iteration, indexing

**`src/visualize_population.py`**
- Renders several genomes from a population side by side, **reusing Day
  3's `render_genome()` directly** rather than writing new rendering logic
  — exactly the reuse pattern the renderer was designed for.

### Verified

Initialized a population of 8 genomes — all 8 passed structural
validation, and all 8 produced unique chromosomes (no accidental
duplicates from the RNG). The visual check (`day4_population_preview.png`)
rendered 6 of them side by side, confirming genuinely diverse patterns:
different loop shapes and different numbers of fully closed loops across
genomes, with no two looking alike.

### Why This Matters for Later Phases

`Population.chromosomes()` is the exact interface Phase 3's operators
should build against. Because fitness scoring, selection, crossover, and
mutation all need to operate over many genomes at once, having a single
object that already handles generation, validation, and reproducibility
means none of the later phases need to rebuild that logic.

---

## Next Up: Day 5

Build the first fitness function — symmetry and loop-closure scoring —
using the `PulliGrid.symmetry_axes()` helper already built on Day 1, so
genomes in a population can finally be ranked against each other.