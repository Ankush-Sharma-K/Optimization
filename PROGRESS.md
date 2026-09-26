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

**Status: Phase 1, Day 3 of 15 complete — Phase 1 finished.**

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

---

## Day 3 — Arc Renderer (Phase 1 complete)

**Goal:** Replace Day 2's straight-diagonal placeholder with the actual
quarter-circle arcs, so genomes render as real Kolam-style curves.

**Concept:** Each cell's two arcs have radius = half the cell's side length,
each centered on one corner and connecting the midpoints of that corner's
two adjacent edges. Because every arc ends exactly at an edge midpoint —
and every edge midpoint is shared with the neighboring cell — adjacent
tiles' arcs always meet up perfectly. That's the mechanism that turns a
grid of independent tiles into one continuous, looping curve instead of a
pile of disconnected quarter-circles.

**What was built:**
- `src/renderer.py`
  - `_cell_arcs(tl, tr, bl, br, tile)` — internal helper computing the
    `(center, theta1, theta2)` pair for each of a cell's 2 arcs, based on
    `TileType` (angles derived from the corner geometry: `ARC_A` hugs
    top-left + bottom-right corners, `ARC_B` hugs top-right + bottom-left)
  - `render_genome(genome, ax=None, show_dots=True, line_color=..., ...)` —
    the main renderer. Draws every cell's arcs onto a matplotlib `Axes`
    using `matplotlib.patches.Arc`, sets axis limits explicitly from
    `grid.bounding_box()` (so it renders correctly even with dots hidden),
    and returns the `Axes` so callers can further customize/save it.

**Verified:** Rendered the same seed=1 and seed=7 genomes from Day 2 for a
direct before/after comparison. Output
(`day3_render_comparison.png`) shows smooth, continuous looping curves that
never touch the dots — including fully closed loops forming naturally
around isolated dots where two matching tiles meet — which is the defining
visual signature of a real Kolam.

**Why this matters for later phases:** `render_genome()` is now the single
reusable entry point Phase 2's fitness functions and Phase 4's Streamlit
app will both call whenever a genome needs to become a visible/scorable
image. Because it just takes a `KolamGenome` and returns a matplotlib
`Axes`, it can be reused unmodified for single-pattern previews, side by
side comparisons, and later for exporting the final "best" pattern in the
app.

**Phase 1 (Representation & Rendering) is now complete.** We have: a
correct dot grid, a mutation/crossover-ready genome encoding, and a
renderer that turns any genome into an actual Kolam image.

**Next (Day 4, start of Phase 2):** Build the population initializer — a
`Population` class holding many random `KolamGenome` instances, ready for
fitness scoring and evolution.

**Files added:**
```
src/
└── renderer.py
outputs/
└── day3_render_comparison.png
```

---

## Day 4 — Population Initializer (start of Phase 2)

**Goal:** Move from a single `KolamGenome` to a whole population of them,
ready for fitness scoring and evolution.

**Concept:** A GA needs many candidate solutions competing at once, not
just one. This day is intentionally small in scope — it's about creating
and structurally validating a batch of random genomes, not about scoring or
evolving them yet (that starts Day 5). "Structural validity" here just
means the tile grid is well-formed (right dimensions, real `TileType`
values) — since every combination of Truchet tiles is a renderable pattern,
there's no such thing as an illegal genome at this stage. Loop-closure and
aesthetic quality checks come later, as fitness functions (Day 5 onward),
not as validity checks here.

**What was built:**
- `src/population.py`
  - `validate_genome(genome)` — structural validity check (dimensions +
    valid tile values); mainly guards against bugs, not bad patterns
  - `Population` class — `Population(grid, size, seed=None)`
    - `.initialize()` — fills `.genomes` with `size` random, validated
      `KolamGenome` instances (each genome seeded from the population's own
      RNG, so runs are reproducible)
    - `.chromosomes()` — returns the flat-list view of every genome, i.e.
      what Phase 3's selection/crossover/mutation operators will actually
      consume
    - `.replace(new_genomes)` — swaps in a new generation; reserved for the
      main GA loop (Day 11)
    - supports `len()`, iteration, and indexing directly over its genomes
- `src/visualize_population.py` — renders several genomes from a
  population side by side, **reusing Day 3's `render_genome()`** exactly as
  planned, to visually confirm the population is actually diverse rather
  than accidentally near-identical

**Verified:** Initialized a population of 8 — all 8 passed structural
validation, and all 8 produced unique chromosomes. Visual check
(`day4_population_preview.png`) of 6 rendered genomes confirms real pattern
diversity: different loop shapes, different closed-loop counts, no visual
duplicates.

**Why this matters for later phases:** `Population.chromosomes()` is the
exact interface Phase 3's operators should consume — they work on flat
integer lists, not on `KolamGenome` objects directly, keeping the
evolutionary logic decoupled from geometry. `.replace()` exists now so the
Day 11 main GA loop doesn't need to modify this class later.

**Next (Day 5):** Build the first fitness function — symmetry and
loop-closure scoring — so genomes in a population can actually be ranked
against each other.

**Files added:**
```
src/
├── population.py
└── visualize_population.py
outputs/
└── day4_population_preview.png
```

---

## Day 5 — Fitness v1: Symmetry & Loop-Closure Scoring

**Goal:** Give genomes an actual quality score so they can be ranked —
the first ingredient evolution needs.

**Concept:** Two structural signals real Kolams are judged by:
- **Symmetry** — does the tile pattern match itself under reflection/rotation?
- **Loop closure** — how much of the curve forms closed loops vs. open
  strands dead-ending at the boundary?

Both are computed directly from the tile grid / graph structure — no
rendering needed, which keeps scoring fast for when the GA loop (Day 11)
calls it constantly.

**What was built:**
- `src/fitness.py`
  - `symmetry_score(genome)` — averages 3 checks: horizontal reflection,
    vertical reflection, 180° rotation. Under a mirror, `ARC_A`/`ARC_B`
    flips identity (the two arcs swap which corners they hug); under 180°
    rotation identity is unchanged. (90° rotational symmetry needs a
    corner-permutation model not yet built — noted as a follow-up.)
  - `loop_closure_score(genome)` — builds a graph where nodes are cell-edge
    midpoints and edges are individual arcs, via `_edge_midpoint_graph()`.
    Finds connected components; a component is a "closed loop" if every
    node in it has degree 2. Score = fraction of total arcs belonging to
    closed-loop components. Boundary midpoints always have degree 1 by
    construction (structural property of the 2-tile encoding), so 1.0
    isn't reachable for any genome — the score is still meaningful for
    *comparing* genomes, since it rewards more interior closed loops over
    long open strands.
  - `fitness(genome, symmetry_weight=0.5, loop_weight=0.5)` — combined,
    weighted score. Weights are a starting point, expected to be retuned
    once dataset-similarity (Day 7) joins them.
- `src/visualize_fitness.py` — scores a 20-genome population, sorts by
  fitness, and renders best vs. worst side by side.

**Verified:** Scores across the 20-genome population ranged from 0.220 to
0.540 — a real, discriminating spread (not flat/uniform). Visual check
(`day5_fitness_best_vs_worst.png`) shows the best-scoring genome forming
more balanced, closed loop shapes than the worst.

**Why this matters for later phases:** `fitness()` is now the scoring
interface Phase 3's selection (Day 8) will call directly on each
`Population` member. Its weighted-sum structure is designed to extend
cleanly — Day 7's similarity score just becomes a third weighted term.

**Next (Day 6):** Build the dataset pipeline — preprocess your reference
Kolam images (threshold/skeletonize) so Day 7 can score genomes by
similarity to them.

**Files added:**
```
src/
├── fitness.py
└── visualize_fitness.py
outputs/
└── day5_fitness_best_vs_worst.png
```

---

## Day 6 — Dataset Preprocessing

**Goal:** Prepare reference Kolam images so Day 7 can compare rendered
genomes against real patterns on equal footing.

**Concept:** Real Kolam photos/scans vary in line thickness, background
color, and lighting — but what should actually be compared is the *shape*
of the loops, not how thick a chalk line was. So every image (real ones and
later, rendered genomes) goes through the same pipeline: resize to a fixed
canvas → threshold to binary (using Otsu's method, which finds the cutoff
automatically rather than a fixed brightness value, since real photos vary
a lot) → skeletonize (reduce the curve to a clean 1-pixel-wide line).

**What was built:**
- `src/dataset.py`
  - `IMAGE_SIZE = 256` — the fixed canvas size both dataset images and
    Day 7's rendered genomes will be resized to for fair comparison
  - `load_image_grayscale(path)` — loads any image file as grayscale
  - `preprocess_image(image, size=IMAGE_SIZE)` — resize → threshold →
    skeletonize; returns a boolean array (`True` = curve pixel)
  - `load_dataset(data_dir, size=IMAGE_SIZE, extensions=...)` — loads and
    preprocesses every image in a folder, returns `[(filename, skeleton), ...]`.
    Meant to be called once per GA run (Day 7/11), not per-generation —
    preprocessing is the slow part.
- `src/visualize_dataset.py` — shows resized/thresholded/skeletonized
  stages side by side

**Verified:** No real dataset is in `data/` yet, so the pipeline was tested
on a synthetic image (a rendered genome, saved and re-loaded as if it were
a real photo) — confirms the full pipeline runs end-to-end. Visual check
(`day6_preprocessing_stages.png`) shows a clean binary extraction and a
faithful thin skeleton preserving the original curve shape.

**Important note:** `preprocess_image()` currently assumes the curve is
*darker* than the background (dark ink/lines on a lighter surface). Once
your real dataset is dropped into `data/`, this assumption needs checking —
if your images are the opposite (e.g. white/light chalk lines on a dark
floor), the `binary = arr < thresh` line needs to flip to `arr > thresh`.
This is flagged in the code comments too.

**Why this matters for later phases:** Day 7's similarity scoring can now
call `load_dataset()` once at startup, then compare each generation's
rendered-and-preprocessed genomes against the same fixed set of reference
skeletons — no need to reprocess the dataset every generation.

**Next (Day 7):** Build the actual similarity metric — compare a rendered
genome's skeleton against the dataset's skeletons (e.g. via pixel overlap
or shape-based distance) and turn that into a third fitness term.

**Files added:**
```
src/
├── dataset.py
└── visualize_dataset.py
data/         <- put your real reference Kolam images here (Day 12 onward
                 will use them for real; for now, dataset.py works on any
                 images placed here, real or synthetic)
outputs/
├── day6_preprocessing_stages.png
└── _synthetic_test_image.png  (test artifact, not a deliverable)
```

---

## Day 7 — Similarity Fitness (dataset-based)

**Goal:** Compare a rendered genome against the real reference dataset, so
genomes are rewarded for actually resembling real Kolams — not just for
being symmetric/closed (Day 5's scores don't know what a real Kolam looks
like).

**Concept:** Pipeline is: render the genome (`renderer.py`) → preprocess it
through the *exact same* resize→threshold→skeletonize pipeline as the
dataset (`dataset.py`, Day 6) → compare the resulting skeleton against
reference skeletons using **Chamfer distance** (how far each curve pixel in
one image is from the nearest curve pixel in the other, averaged both
directions) → take the **best** match, not the average, since a genome only
needs to resemble one real design well.

**What was built:**
- `src/similarity.py`
  - `genome_to_skeleton(genome, size=IMAGE_SIZE)` — renders a genome
    in-memory (no disk I/O) and runs it through `dataset.preprocess_image`
  - `precompute_reference_transforms(dataset)` — precomputes each
    reference's distance transform **once per GA run**, not per genome
    (critical: this took per-genome scoring from ~8.5s down to ~0.35s
    against all 600 references)
  - `_chamfer_distance(...)` — symmetric Chamfer distance between two
    skeletons using precomputed transforms
  - `similarity_score(genome, reference_transforms)` — best-match score,
    mapped to `[0, 1]` via `exp(-distance / scale)`
  - `best_match(genome, reference_transforms)` — like above, but also
    returns *which* reference matched best (for sanity checks now, and the
    "closest real Kolam" display in the app, Day 13)
- `src/visualize_similarity.py` — renders a genome next to its best-matching
  real Kolam image, for a visual sanity check
- `fitness.py` updated: `fitness()` now takes an optional
  `reference_transforms` argument and adds `similarity_weight * similarity_score(...)`
  as a third term. **When no dataset is passed, it falls back to the exact
  Day 5 two-term behavior** (weights renormalized) — confirmed this keeps
  every earlier script (Days 4–5) working unchanged.

**Bug found and fixed during testing:** the first version used
`(d_ab + d_ba) / 2` (plain average) for Chamfer distance. This let very
*dense* reference images (fractals covering ~20% of the canvas) win "best
match" purely because genome pixels are trivially close to *some* reference
pixel — while the harder reverse direction (reference pixels needing to be
near the much sparser genome curve) was actually worse than a real match.
Verified this numerically (dense reference: d_ab=1.82 vs d_ba=7.70 — a huge
asymmetry) and fixed it by switching to **`max(d_ab, d_ba)`**, which
requires both directions to be genuinely close before a match scores well.
Re-verified: the best match is now a comparably-scaled reference image, not
the densest one in the dataset by coincidence.

**Verified:** Ran `similarity_score` + `best_match` against all 600 cached
reference skeletons (`data/processed`). Combined `fitness()` (all 3 terms)
tested on a 10-genome population: scores ranged 0.394–0.519, still
discriminating. Visual check (`day7_similarity_best_match.png`) confirms
the fixed metric picks a sensible (not density-biased) match.

**Known limitation (flagged for Day 12, not fixed now):** our genomes (5×5
Truchet cells) are much simpler than the dataset's intricate fractal
Kolams, so even the "best" match is still a loose one — this is a genuine
scale/complexity mismatch, not a bug. Options to revisit at Day 12 tuning:
increase grid resolution (larger `n`), or accept the current scale and
focus similarity scoring on smaller reference crops.

**Performance note for Day 11:** per-genome scoring against all 600
references takes ~0.19–0.35s. For a population of 50 over 100 generations
that's noticeable (~15–30 min total) — worth adding a `sample_size`
parameter to `similarity_score` (score against a random subset of
references per call) if Day 11/12 tuning needs it faster.

**Next (Day 8):** Build the selection operator — tournament or
roulette-wheel selection, using `Population.chromosomes()` and `fitness()`
to decide which genomes reproduce.

**Files added:**
```
src/
├── similarity.py
└── visualize_similarity.py
outputs/
└── day7_similarity_best_match.png
```

---

## Dataset Received (real Kolam images)

User's real reference dataset arrived: 600 images across 3 fractal Kolam
designs (`kolam19`: 400 images, `kolam29`: 100, `kolam109`: 100), plus 3 CSV
files containing the underlying curve-generation coordinates for each
design. Images are clean computer-generated fractal Kolams (gray curve on
white background, diamond-oriented, 500x500 JPEGs).

**Verified:** ran the existing Day 6 pipeline (`load_image_grayscale` +
`preprocess_image`) directly on a real sample image, no code changes
needed — the dark-curve-on-light-background assumption already matched.
Produced a clean, faithful skeleton (`day6_real_dataset_test.png`).

**Action for user:** copy the 3 image folders (or a representative subset)
into `data/`. CSVs are not used by the current image-based pipeline; noted
as a possible future enhancement (direct coordinate-based comparison)
rather than something needed now.

**Note for Day 12:** dataset is imbalanced (400 vs 100 vs 100) and likely
contains many near-duplicate variants per design — worth subsampling for
speed when tuning, rather than necessarily using all 600 images.

---

## Dataset Wired to Your Actual Folder Structure

Updated `dataset.py` to match your exact local layout:
```
data/raw/kolam19/*.jpg    (400 images)
data/raw/kolam29/*.jpg    (100 images)
data/raw/kolam109/*.jpg   (100 images)
data/processed/           (cached preprocessed skeletons -- new)
```

**What changed:**
- `load_dataset()` already walked subfolders recursively (no change needed
  there) -- confirmed it returns `(relative_path, skeleton)` pairs like
  `"kolam19/kolam19-0.jpg"`, so the design name travels with each entry.
- **New:** `save_processed_dataset(dataset, processed_root)` -- caches every
  skeleton as a PNG under `data/processed/`, mirroring the `raw/` subfolder
  structure exactly.
- **New:** `load_processed_dataset(processed_root)` -- reloads cached
  skeletons directly, skipping threshold+skeletonize entirely.

**Verified end-to-end on the real 600-image dataset** (mirrored locally to
match your exact folder layout):
- Preprocessing all 600 raw images: **5.7s**
- Saving the cache to `data/processed/`: **1.3s**
- Reloading 600 skeletons from cache: **0.2s** (a ~28x speedup over
  reprocessing)
- Cache round-trip confirmed pixel-identical to the freshly-processed
  version, and all 600 filenames accounted for in the cache.

**Why this matters for later phases:** Day 7's similarity scoring, and
especially Day 11's GA loop (which restarts often during testing/tuning),
should call `load_processed_dataset("data/processed")` after the first run
rather than `load_dataset("data/raw")` every time -- this turns a ~6 second
startup cost into ~0.2 seconds after the first run.

**Files updated:**
```
src/
└── dataset.py   (added save_processed_dataset, load_processed_dataset)
```