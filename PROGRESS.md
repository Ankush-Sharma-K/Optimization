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

**Status: Phase 3 complete — Day 11 of 15 complete (working GA loop).**

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

### Day 12 — Real results (81 runs, 3 seeds each, ~3.3 h of compute in total)

Yardstick = default `fitness()` on all 600 references (mean over seeds, s.e. in brackets).

| Experiment | Settings (yardstick) | Verdict |
|---|---|---|
| crossover | single_point .643, two_point .652, uniform .643, **block .649** | all within noise; default kept |
| mutation | **flip .649**, block_flip .655, symmetric_flip .628 | within noise; default kept |
| tournament | 2 .649, **3 .649**, 5 .649 | no difference |
| elite | 0 .652, **2 .649**, 4 .640 | within noise (4 is lowest) |
| mut_rate | 0.5x .637, **1x .649**, 2x .655 | within noise (2x slightly ahead) |
| scale | 5/10/20/40/80 all **.6489** | no effect (see finding 1) |
| weights | equal / sim-heavy / struct-heavy all **.6489** | no effect (see finding 1) |
| grid | 6 -> .649 (.006), 8 -> .710 (.025), **10 -> .716 (.015)** | **only clear win**: 10 beats 6 by ~4 s.e.; 8 vs 10 within noise |

**Tuned config (`outputs/day12_best_config.json`):** grid_n 10, block crossover, flip
mutation, tournament 3, elite 2, mutation rate 1x (1/chromosome length), similarity_scale 20,
equal weights, population 30, generations 30, sample_size 50.

**Findings**
1. **The similarity term does not steer the GA.** In all 72 non-grid runs the final similarity
   was 0.739-0.744 (distance ~6 px); changing `scale` or the weights left the final genome
   *identical* for every seed (only `own_fitness` shifted). So evolution is effectively optimising
   symmetry + loop closure; matching the real Kolams is not being optimised at this grid size.
   Likely cause (hypothesis, not yet tested): the distance is the minimum over 600 references and
   barely differs between genomes, so it gives almost no gradient.
2. **Bigger grid helps**: 10x10 raised similarity to ~0.79 and loop closure, but each run costs
   ~2x a grid-6 run (~340 s vs ~155 s per run in this experiment run).
3. **Most operator choices are statistically indistinguishable with 3 seeds.** Defaults are fine.
4. Runs are deterministic per seed (repeated default runs gave identical numbers).
5. Seed-to-seed spread is large (e.g. symmetry 0.55 vs 0.76 at grid 6): the GA converges to
   different structure/loop trade-offs, so conclusions need more seeds to separate close settings.

**Open item for later:** make similarity informative (e.g. average of the k nearest references,
or rank-normalise it within the population). Not done; Day 13 uses the tuned config as is.

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

---

## Day 8 — Selection Operator (start of Phase 3)

**Goal:** Decide which genomes get to reproduce, using `fitness()` scores.

**Concept:** Selection is what turns fitness numbers into evolutionary
pressure: fitter chromosomes get picked as parents more often, but not
exclusively (weaker ones still occasionally survive, which preserves
diversity). Three methods were implemented behind one `method=` switch:
- **Tournament** (default) — draw `k` random contenders, the fittest wins.
  `k` directly controls selection pressure.
- **Roulette-wheel** — probability proportional to fitness (shifted so the
  worst member sits at ~0).
- **Rank** — probability proportional to rank, so it ignores fitness scale.

**What was built:**
- `src/selection.py` — `select()` (main entry point, returns parent
  *chromosomes*, copied), `select_indices()`, `elite_indices()` (for
  elitism on Day 11), `evaluate_population()` (Population → list of
  fitness values via `fitness()`), plus module constants
  `TOURNAMENT_SIZE = 3` and `SELECTION_METHODS`.
- `src/visualize_selection.py` — sanity script: scores a real population
  and plots mean parent fitness per method, plus the top-3 genomes.

**Why tournament is the default:** `fitness()` values are bunched in a
narrow band (~0.39–0.52). Roulette-wheel depends on *absolute* fitness
differences, so with bunched scores it is nearly random. Tested on a
50-member synthetic population with a similarly narrow range (pop mean
0.4547): roulette's selected parents averaged 0.4583, rank 0.4610, while
tournament gave 0.4613 / 0.4645 / 0.4680 for k = 2 / 3 / 5. Tournament is
also cheaper and its pressure is a single tunable knob — `tournament_size`
is a Day 12 tuning candidate.

**Design choices:**
- Selection takes a `Population` *or* a plain list of chromosomes, and
  returns copies, so crossover/mutation can never mutate the parent pool.
- Sampling is with replacement; contenders within one tournament are
  distinct. A seeded `random.Random` gives reproducible runs.
- Edge cases handled: all-equal / all-zero fitness falls back to uniform
  choice; tournament size is clamped to population size; length mismatch
  between chromosomes and fitnesses raises `ValueError`.

**Verified:** `selection.py` tested standalone on synthetic chromosomes
(selection pressure ordering, seeded reproducibility, copy-safety, edge
cases). `visualize_selection.py` still needs a first run on your machine
against the real 600-image cache.

**Next (Day 9):** Crossover — combine two selected parent chromosomes
into children (single-point / two-point / 2D block-swap).

**Files added:**
```
src/
├── selection.py
└── visualize_selection.py
outputs/
└── day8_selection_pressure.png   (generated when you run the script)
```

---

## Day 9 — Crossover Operators

**Goal:** Combine two selected parent chromosomes into children so good
traits can be recombined.

**Concept:** Each gene is one tile orientation at one grid cell, so *any*
mix of parent genes is still a valid, renderable genome — crossover needs
no repair step. Four operators were built behind one `method=` switch:
- **single_point** — swap the tails after one cut (top band / bottom band
  in row-major order)
- **two_point** — swap the segment between two cuts
- **uniform** — swap each gene independently
- **block** (default) — swap a random rectangular patch of the 2D tile
  grid, reshaping the flat chromosome using its square side length

**What was built:**
- `src/crossover.py` — `crossover()` (main entry point; applies
  `crossover_rate`, default 0.9, otherwise returns copies),
  `crossover_pairs()` (pairs up a parent pool from `select()`, for the
  Day 11 loop), the four operators, `side_length()`, constants
  `CROSSOVER_RATE`, `CROSSOVER_METHODS`.
- `src/visualize_crossover.py` — renders parents + both children for every
  method, for a visual check.

**Measured, on a 5×5 cell grid (all-0 parent × all-1 parent, 3000 trials):**
every operator conserves genes (child1 + child2 reproduce the parents'
genes at each position). Mean "seams" (neighbouring cells that came from
different parents) were: single_point 4.98, block 6.68, two_point 8.61,
uniform 20.0. So uniform is by far the most disruptive to spatial
structure, which matters because loops form where neighbouring tiles
match. Block is *not* lower-disruption than single-point — its advantage
is that it can transplant a compact patch from anywhere (interior or
corner) as one unit, whereas row-major cuts only move whole bands and
always keep the first genes with parent 1. Whether that helps fitness is
untested, so the default is a reasoned choice and the method comparison is
a **Day 12 experiment**.

**Design choices:** children are always new lists (parents never
modified); length mismatch, unknown method, and non-square length without
`shape=` raise `ValueError`; `block_crossover` accepts `shape=(rows, cols)`
for future non-square genomes.

**Verified:** `crossover.py` tested standalone (gene conservation, rate 0
→ copies, parents untouched, odd-length pairing, error cases).
`visualize_crossover.py` has not been run against your real modules yet.

**Next (Day 10):** Mutation — flip individual tile genes with a small
per-gene probability.

**Files added:**
```
src/
├── crossover.py
└── visualize_crossover.py
outputs/
└── day9_crossover_comparison.png   (generated when you run the script)
```

---

## Day 10 — Mutation Operators

**Goal:** Add small random changes to children so evolution can discover
patterns neither parent contained.

**Concept:** Each gene is a binary tile orientation, so mutating a gene
means flipping it (0 ↔ 1) — every result is still a valid, renderable
genome. Three operators behind one `method=` switch:
- **flip** (default) — each gene flips independently with probability `rate`
- **block_flip** — with probability `rate × length`, flip one random
  rectangle of up to 2×2 cells: a coherent local change (e.g. re-routing a
  loop) that single flips rarely make
- **symmetric_flip** — flips whole 4-cell mirror/rotation orbits together.
  Mirrors swap ARC_A↔ARC_B and 180° rotation keeps identity, so each
  relation between two cells is "equal" or "opposite"; flipping both cells
  keeps it intact, so `symmetry_score` is preserved exactly. Plain flips
  tend to break symmetry that selection has built up.

**What was built:**
- `src/mutation.py` — `mutate()` (main entry point; default rate
  `1/len(chromosome)`, i.e. ~1 flipped gene per chromosome), `mutate_all()`,
  the three operators, `default_mutation_rate()`, `MUTATION_METHODS`.
  Returns new lists; validates genes ∈ {0,1} and rate ∈ [0,1].
- `src/visualize_mutation.py` — parent vs mutants at increasing rates, and
  one mutant per method.

**Measured (25-gene chromosome, 4000 trials each):** at the default rate,
average genes changed — flip 0.99, symmetric_flip 0.96, block_flip 2.26
(each event flips 1–4 cells). flip at rate 0.2 changed 5.02 genes (expected
5). `block_flip` changes were always a contiguous rectangle ≤ 2×2.
Symmetry check on a symmetric parent (score 0.76 — below 1.0 because
centre-row/column cells of an odd-sized grid are their own mirror image):
`symmetric_flip` kept it at exactly 0.76 across 2000 mutants; plain `flip`
at rate 0.1 dropped the mean to 0.646. *Confirmed on the real code:* running the real `symmetry_score()` on a symmetric parent gave 0.76 before and 0.76 (min and max over 500 `symmetric_flip` mutants) after; plain `flip` averaged 0.6443 → PASS.

**Design choices:** `nearest_point()` (reserved on Day 1 for mutation) is
not needed — tile flips can't leave the grid. Default method is plain
`flip`; whether `symmetric_flip` or `block_flip` helps is a Day 12
experiment, not a conclusion.

**Verified:** `mutation.py` tested standalone (rate 0 → copy, rate 1 → all
flipped, input untouched, expected flip counts, rectangle contiguity,
symmetry preservation, error cases). `visualize_mutation.py` not yet run
against your real modules.

**Phase 3 operators complete:** `select()`, `crossover()`, `mutate()`.

**Next (Day 11):** GA main loop (`ga.py`) tying everything together.

**Files added:**
```
src/
├── mutation.py
└── visualize_mutation.py
outputs/
└── day10_mutation_comparison.png   (generated when you run the script)
```

---

## Day 11 — GA Main Loop (Phase 3 complete)

**Goal:** Tie population, fitness, selection, crossover and mutation into
one evolutionary loop.

**Each generation:** score the population → copy the top `elite_count`
unchanged → `select()` parents → `crossover_pairs()` → `mutate_all()` →
trim to size → `Population.replace()` → re-score. Elites skip crossover and
mutation, so the best fitness can't be lost.

**What was built:**
- `src/ga.py`
  - `GAConfig` — every hyper-parameter in one dataclass (defaults: pop 50,
    100 generations, 2 elites, tournament k=3, block crossover @ 0.9,
    flip mutation @ 1/len, no sampling, no early stop).
  - `run_ga(grid, reference_transforms=None, config=None, callback=None)` →
    `GAResult` (`best_chromosome`, `best_genome`, `best_fitness`, `history`,
    final `population`, `elapsed_s`).
  - Per-generation `history` records best / mean / worst fitness,
    `diversity` (unique chromosomes ÷ size, to spot premature convergence)
    and the generation's best chromosome (so the app can animate evolution).
  - `callback(stats)` after every generation — hook for Streamlit live
    progress on Day 13.
  - `patience` — optional early stop after N generations without a new best.
- `src/visualize_ga.py` — runs a 30×30 GA on the real cached dataset and
  plots fitness curves, diversity, and best-of-gen-0 vs final best.

**`sample_size` — a change from what I said on Day 7/10:** I planned to add
it to `similarity_score()`. Instead it lives in `GAConfig`: each generation
the loop scores against a fresh random subset of the references, so
`similarity.py` needs no edits (I didn't have its source in hand). Because
subsets differ per generation, fitness is comparable only *within* a
generation, so the final population is re-scored against **all** references
before the best is picked. With `sample_size=None` scoring is deterministic
and best fitness is monotone non-decreasing.

**Tested — on stand-in modules, not your real ones.** I didn't have your
`grid/genome/population/fitness` source, so I tested the loop wiring with
small stubs built from the documented interfaces (stub fitness = fake
symmetry + fake loop + fake similarity to 40 random reference chromosomes).
This checks the *loop*, not real Kolam quality. Results: best 0.673 → 0.782
and mean 0.539 → 0.716 over 40 generations; best never decreased;
diversity fell 1.00 → 0.77; same seed reproduces exactly, different seed
differs; sampling mode, no-reference mode, odd population size, early
stopping and invalid-config errors all behave; with `elite_count=0` the best
*does* sometimes drop, confirming elitism is doing its job.

**To do on your machine:** run `python visualize_ga.py` from `src/`. Two
assumptions to confirm: `KolamGenome(grid)` builds a default tile grid
(then `from_chromosome` fills it), and `Population.replace()` accepts a list
of `KolamGenome`. `_genome_from_chromosome` handles `from_chromosome`
either mutating in place or returning a genome. Please also note the
runtime printed (30 × 30 with 100 sampled references) — it informs Day 12.

**Phase 3 (Evolution Engine) is complete.**

**Next (Day 12):** experiments and tuning with `run_ga()`.

**Files added:**
```
src/
├── ga.py
└── visualize_ga.py
outputs/
└── day11_ga_run.png   (generated when you run the script)
```

---

## Day 12 — Experiments & Tuning (COMPLETE)

**Goal:** Pick the GA defaults for the app with evidence, not guesses.

**What was built:**
- `src/experiments.py` — one-factor-at-a-time (greedy) tuning over several seeds.
  Order: crossover method → mutation method → tournament size → elite count →
  mutation-rate multiplier → similarity `scale` → fitness weights → grid size.
  After each experiment the winner is locked into a running base config, so
  later experiments are tested on top of earlier winners. `population` size is
  optional (`--only population`), since a bigger population just costs more evaluations.
- **Common yardstick:** weights/scale change what `run_ga` optimises, so its own
  `best_fitness` is not comparable across settings. Each run's final best genome
  is re-scored with the *default* `fitness()` against ALL references; that number
  ranks settings.
- **Noise guard:** a challenger replaces the incumbent only if it beats it by more
  than the combined standard error across seeds; otherwise the default is kept.
- Results go to `outputs/day12_results.csv` (resumable: re-running skips finished
  runs), plus `day12_experiments.png`, `day12_scale_analysis.png`,
  `day12_best_config.json`. `tuned_config()` rebuilds the chosen `(grid_n, GAConfig)`.
- **One edit to existing code:** `fitness()` gained `similarity_scale=20.0`
  (passed to `similarity_score(scale=...)`) so scale can be tuned via `fitness_kwargs`.
  Default behaviour is unchanged.

**Tested:** plumbing on a synthetic set first, then the full run on the real dataset (results below).

**To do on your machine:** run `python visualize_ga.py` from `src/`. Two
assumptions to confirm: `KolamGenome(grid)` builds a default tile grid
(then `from_chromosome` fills it), and `Population.replace()` accepts a list
of `KolamGenome`. `_genome_from_chromosome` handles `from_chromosome`
either mutating in place or returning a genome. Please also note the
runtime printed (30 × 30 with 100 sampled references) — it informs Day 12.

**Phase 3 (Evolution Engine) is complete.**

**Next (Day 12):** experiments and tuning with `run_ga()`.

**Files added:**
```
src/
├── ga.py
└── visualize_ga.py
outputs/
└── day11_ga_run.png   (generated when you run the script)
```

---

## Day 12 — Experiments & Tuning (COMPLETE)

**Goal:** Pick the GA defaults for the app with evidence, not guesses.

**What was built:**
- `src/experiments.py` — one-factor-at-a-time (greedy) tuning over several seeds.
  Order: crossover method → mutation method → tournament size → elite count →
  mutation-rate multiplier → similarity `scale` → fitness weights → grid size.
  After each experiment the winner is locked into a running base config, so
  later experiments are tested on top of earlier winners. `population` size is
  optional (`--only population`), since a bigger population just costs more evaluations.
- **Common yardstick:** weights/scale change what `run_ga` optimises, so its own
  `best_fitness` is not comparable across settings. Each run's final best genome
  is re-scored with the *default* `fitness()` against ALL references; that number
  ranks settings.
- **Noise guard:** a challenger replaces the incumbent only if it beats it by more
  than the combined standard error across seeds; otherwise the default is kept.
- Results go to `outputs/day12_results.csv` (resumable: re-running skips finished
  runs), plus `day12_experiments.png`, `day12_scale_analysis.png`,
  `day12_best_config.json`. `tuned_config()` rebuilds the chosen `(grid_n, GAConfig)`.
- **One edit to existing code:** `fitness()` gained `similarity_scale=20.0`
  (passed to `similarity_score(scale=...)`) so scale can be tuned via `fitness_kwargs`.
  Default behaviour is unchanged.

**Tested:** against the real source files you uploaded, but on a *synthetic*
reference set (30 skeletons rendered from random 14x14 genomes) with tiny
settings — this checks the plumbing (runs, CSV resume, winner logic, plots, JSON,
`tuned_config`), not Kolam quality. No real tuning conclusions exist yet.

**To do on your machine (from `src/`):**
```
python experiments.py --quick                   # smoke test
python experiments.py --workers 3               # full run, resumable
python experiments.py --scale-only              # only the similarity-scale table
```
Rough cost: ~27 settings x 3 seeds = 81 runs; at your Day 11 speed (~70 s for
30x30) that is ~95 min serial, roughly 1/workers of that in parallel.

**Next:** Day 13 (Streamlit app) using `tuned_config()`.

**Files added:**
```
src/
└── experiments.py
outputs/
├── day12_results.csv / day12_experiments.png / day12_scale_analysis.png
└── day12_best_config.json            (generated when you run the script)
```

---

## Day 12.5 — Fixing the flat similarity term (COMPLETE)

**Why:** Day 12 showed final similarity stuck at ~0.74 in every run, and `scale`/weights changed nothing.

**Diagnosis (tested on a stand-in reference set; to be confirmed on the real data):**
- The Chamfer distance of random genomes varies by only ~0.02 px (about 0.25 %) between patterns
  on the same grid, while changing the grid size moved it by several px. The metric mostly measures
  dot density (how much of the canvas the curves cover), not shape.
- Reason: every tile is one of two arc orientations and every cell draws arcs, so all genomes cover
  the canvas almost identically. A pixel-distance score therefore cannot tell Truchet tilings apart.

**What was built (backward compatible; defaults reproduce the old scores exactly):**
- `similarity.py`: `distances_to_refs`, `similarity_distance(k)`, `distance_matrix`,
  `calibrate_similarity(grid, refs, k, sample_size)` -> `{mu, sigma, k}`; `similarity_score` gained
  `k` (mean of k nearest references) and `calibration` (logistic score centred on the average random genome).
- `fitness.py`: `fitness()` gained `similarity_k` and `similarity_calibration`.
- `similarity_fix.py`: Part 1 diagnostics (spread per distance variant + grid-size sweep 6..16),
  Part 2 A/B GA runs (baseline / calib_k1 / calib_k5 / calib_k5_w50) judged by neutral measures on all
  references (raw d_min in px, d_k5, structural = mean of symmetry and loop closure), with a progress
  bar, `--workers`, resumable CSV, and a genome image grid.
- On the stand-in data the calibrated score's spread across random genomes rose from ~0.0006 to ~0.19,
  so selection can now see differences.

**Expected outcome (be realistic):** because pattern-to-pattern variation is tiny, the A/B will likely
show only a small d_min gain (hundredths of a pixel) at best. The big lever is probably grid density.

**To run (from `src/`):** `python similarity_fix.py --quick`, then `python similarity_fix.py --workers 3`
(12 GA runs at the tuned grid), or `--diagnose-only` (about 2 min).

**Next:** Day 13 (Streamlit app).

### Day 12.5 — Part 1 grid sweep, REAL data (20 random genomes per grid)

| grid | d_min px | std px | sec/genome |
|---|---|---|---|
| 6 | 5.994 | 0.0246 | 0.251 |
| 8 | 4.802 | 0.0116 | 0.284 |
| 10 | 4.622 | 0.0203 | 0.320 |
| 12 | 3.898 | 0.0087 | 0.356 |
| 14 | 3.841 | 0.0187 | 0.413 |
| 16 | 4.119 | 0.0087 | 0.474 |

Reading: on real data the diagnosis holds. Changing the grid from 6 to 16 moves the distance by ~1.9 px,
while different patterns on one grid differ by only ~0.01-0.02 px. The distance is lowest at grids 12-14
(12 is within 0.06 px of 14 and cheaper); it gets worse at 16, so there is an optimum density. Grid 12 and
14 were never run through the GA (Day 12 tested 6/8/10), so their GA behaviour is untested.
`similarity_fix.py` now accepts `--grid-n` (and `tuned_config(grid_n=...)` rescales the mutation rate).

### Day 12.5 — Decision (A/B skipped as too slow)

The 12-run A/B was too slow to run. Decision from the evidence already collected:
- **Grid 10 -> 12** (distance 4.62 -> 3.90 px on real data; 14 is only 0.06 px better and slower). Updated
  `day12_best_config.json` carries `grid_n: 12`; mutation rate rescales automatically (1x / chromosome length).
- **Calibrated / k-nearest similarity stays OFF by default.** Pattern-to-pattern spread is ~0.01-0.02 px, so it
  can only reward noise-level differences; it is available in the code but untested in the GA, so it is not used.
- Optional cheap check: `python similarity_fix.py --grid-n 12 --variants baseline --seeds 1` (one GA run).
- Not verified: GA behaviour at grid 12 (Day 12 only tested 6/8/10).

### Day 12.5 — Final check: one GA run at grid 12, REAL data

`python similarity_fix.py --grid-n 12 --variants baseline --seeds 1` (tuned settings, 30 pop x 30 gens):
- Run time **176 s** (a full 12-run comparison would therefore be ~35 min, not hours).
- Final best genome: **d_min 3.893 px**, d_k5 3.903 px, structural (mean of symmetry and loop closure) **0.657**.
- Random genomes at grid 12 average 3.898 px (std 0.009), so the GA's result is *inside the random range*:
  the GA did not make the genome more similar to the references than a random one, confirming that
  evolution is steering symmetry/loop closure only. The better similarity comes from the grid size.
- Overall fitness estimate ~0.71 (similarity score exp(-3.893/20) = 0.823), the same as grid 10's 0.716 +- 0.015
  from Day 12; the smaller distance is offset by slightly lower structure (0.657 vs 0.677). One seed, so
  grid 12 vs 10 is not statistically separated.
- Diagnostics on real data (CV between random genomes, grid 12): min 0.21 %, 5-nearest 0.15 %, 20-nearest 0.13 %,
  all-refs 0.21 % -- no distance variant separates patterns.
- Calibration at grid 12 (50 sampled refs): k=1 mu 3.918 px sigma 0.0066 px; k=5 mu 3.942 px sigma 0.0051 px.

**Conclusion:** grid 12 works (runs normally, sensible structure). Defaults for the app: grid 12 (selectable
6-14), tuned operators from Day 12, calibrated similarity OFF. The A/B of the calibrated variants was not run;
the code remains available. Report-worthy finding: with a two-orientation Truchet encoding, pixel-based similarity
to the fractal Kolam dataset can only be improved through dot density, not pattern shape.

---

## Day 12.6 — Symmetric-by-construction patterns (COMPLETE)

**Why:** the evolved grid-12 pattern had no visible symmetry (score ~0.66) and open strands; real Kolams are symmetric.

**What was built:**
- `src/symmetry.py` — a repair step that copies a free region of the chromosome onto the rest of the grid.
  Modes: `"mirror"` (left-right + top-bottom + 180 deg; free region = top-left quadrant, tiles flip ARC_A<->ARC_B
  under a mirror, exactly as `symmetry_score` assumes) and `"rot180"` (free region = half the cells).
- `src/ga.py` — `GAConfig.symmetry_mode` (default `None` = Day 11 behaviour unchanged). When set, the initial
  population and every child are repaired; the per-gene mutation rate is scaled up so the expected number of
  effective flips per child stays the same.
- `src/symmetry_experiment.py` — compares none / rot180 / mirror at the tuned settings (progress bar, `--workers`,
  resumable CSV, genome image grid), judged by symmetry, loop closure, d_min and the default fitness on all references.

**Tested (stand-in data only):** repair is idempotent; mirror symmetry score is exactly 1.000 at even tile counts
(grid 11, 13) and 0.884 at 11x11 tiles (grid 12); rot180 reaches ~0.61-0.67 from the repair alone; every member of the
final population stays symmetric; the picture for `mirror` is visibly mirror-symmetric on both axes.

**Parity caveat:** with an odd tile count (grid 12 -> 11x11) the middle row/column sits on the mirror axis and a
tile can never equal its own flip, so symmetry tops out at 1 - (4N-2)/(3N^2) = 0.884. Grid 13 (12x12 tiles) can reach 1.0.
Distance to references at grid 13 has not been measured (grids 12 and 14 gave 3.90 and 3.84 px).

**Caution:** forcing symmetry raises the default fitness mechanically (symmetry term ~0.65 -> 1.0), so compare loop
closure and d_min separately, not the fitness.

**To run (from `src/`):** `python symmetry_experiment.py --quick`, then
`python symmetry_experiment.py --grids 13 --seeds 2 --workers 3` (6 GA runs; ~3 min each at grid 12, so roughly 20-40 min).
**Next:** Day 13 (Streamlit app).

### Day 12.6 — Results, REAL data (grid 13 = 12x12 tiles, 2 seeds, 30 generations; mean +- s.e.)

| variant | symmetry | loop closure | d_min px | fitness (yardstick) |
|---|---|---|---|---|
| none | 0.743 +- 0.025 | 0.694 +- 0.056 | 3.720 +- 0.003 | 0.756 +- 0.027 |
| rot180 | 0.972 +- 0.009 | 0.757 +- 0.035 | 3.721 +- 0.021 | 0.853 +- 0.015 |
| **mirror** | **1.000** | **0.847** (both seeds) | 3.714 +- 0.002 | **0.893** |

- **Mirror** reaches perfect symmetry and the highest loop closure; its 0.847 beats every none (0.64, 0.75) and
  rot180 (0.72, 0.79) run. rot180 is in between. Only 2 seeds, so treat as strong but not statistically proven.
- **Similarity is unchanged** (3.71-3.72 px for all three): symmetry neither helps nor hurts it, as expected.
- **Fitness is partly mechanical**: of mirror's +0.137 over none, ~+0.086 is the symmetry term (+0.257 / 3);
  ~+0.051 is loop closure; similarity contributes ~0. The loop-closure gain is the real improvement.
- **The two mirror seeds found different patterns (52 of 144 tiles differ) with identical scores (0.8926)**: a quality
  plateau with many equally good designs, so the app can offer variety by changing the seed.
- **Grid 13 is the best distance seen so far**: 3.72 px vs 3.89 (grid 12) and 3.84 (grid 14), measured on random genomes
  in Day 12.5 for even grids only; odd grids 11 and 15 were never measured.
- **Run times (274-1140 s) are not interpretable**: they varied 4x between identical-cost runs, so the machine was
  loaded (parallel jobs). Do not conclude anything about speed from them.
- Remaining flaw: loop closure 0.85, not 1.0 (the boundary leaves open strands, a property of the encoding), and the
  patterns are still Truchet-like (no dots, ring loops).

**Decision:** app default = grid 13, `symmetry_mode="mirror"`; the app should also offer none / rot180 and grid
selection for comparison. New `day12_best_config.json` carries `grid_n: 13` and `"symmetry_mode": "mirror"`
(`tuned_config(symmetry_mode=None)` turns it off). Not tested: whether fewer generations suffice for mirror (only 36
free cells), so Day 13 should show the best-fitness curve.

### Safety change to `experiments.py`

`experiments.py` can no longer overwrite `day12_best_config.json` (the file the app and scripts read). By default it writes
its result to `outputs/day12_experiments_config.json` and prints that the real config was NOT modified. Only with
`--write-config` does it also write `day12_best_config.json`, and it first copies the existing file to
`day12_best_config.json.bak-<date-time>`. Tested: without the flag the config's checksum is unchanged; with the flag a
backup is created. Day 12 itself is finished and does not need to be re-run.

---

## Day 13 — Streamlit app (IN PROGRESS, split into 3 phases to keep each step small)

| Phase | Content | Status |
|---|---|---|
| 13a | `app_core.py` (all logic, no Streamlit) + `test_app_core.py` | DONE (32 checks pass on real data) |
| 13b | `app.py`: sidebar controls, Run button, live progress bar + ETA + fitness curve, result image, metrics, PNG/JSON download | CODE READY (your first `streamlit run app.py` pending) |
| 13c | "Closest real Kolam" panel, seed gallery for variety, error messages, session state, final polish | after 13b |

### 13a — app_core.py
- `RunSettings` (grid_n 13, symmetry_mode "mirror", pop 30, gens 30, sample 50, seed 0), `validate_settings`,
  `make_ga_config` (reads the Day 12 operators from `day12_best_config.json`; built-in fallback if the file is missing),
  `run_evolution(refs, settings, on_progress)` -> `EvolutionResult` (best genome, metrics, curve history, closest reference
  name + skeleton), `render_png`, `skeleton_png`, `eta_seconds`, `result_summary`.
- Paths can be overridden with `KOLAM_PROCESSED_DIR` and `KOLAM_CONFIG_PATH` (for Day 14 deployment).
- Tested: 32 checks pass on stand-in data (validation, config + fallback + corrupt file, progress callbacks, symmetric result,
  determinism per seed, PNG output, clamped sample size, all symmetry modes). The Streamlit screen itself is NOT yet built or tested.
- Closest-Kolam panel will draw the reference *skeleton* from memory, so it works even without the raw images.

### 13b — app.py (code ready)
- Sidebar: symmetry mode, grid size (6-16, default 13) with a note when an even grid makes perfect mirror symmetry impossible,
  seed, and an "Advanced" box (population, generations, references per generation). **Evolve a Kolam** button.
- During the run: progress bar with generation number, best fitness and time left, plus a live fitness chart.
- Result (kept in `session_state`, so clicking a download button does not lose it): the evolved Kolam, four metrics (fitness,
  symmetry, loop closure, distance to closest real Kolam), PNG and JSON downloads, final fitness curve, "About" box with the limits.
- Friendly `st.error` messages for missing reference data, invalid settings and failed runs.
- `app_core.py` now forces matplotlib's off-screen "Agg" backend at import (Streamlit runs scripts in a worker thread).
- Tested with a fake `streamlit` module (`test_app_ui.py`, 18 checks): first visit, a full run, rerun keeps the result, even-grid hint,
  missing data. NOT tested: how the page actually looks, and Streamlit version differences (use Streamlit 1.30 or newer).
- Not yet in the app: "closest real Kolam" picture and seed gallery (Phase 13c).
