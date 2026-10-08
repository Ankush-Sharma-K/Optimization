# kolamNet — Context Reference

Keep this alongside `PROGRESS.md`. `PROGRESS.md` tells you *what happened
each day*; this file tells you *what everything is currently called* and
*what the project is trying to do*, so new code never accidentally reuses a
name that already means something else.

Update this file whenever a new class/function/module-level variable is
added — treat it as the single source of truth for naming.

---

## 1. Project Aim

Build a **Genetic Algorithm that generatively recreates Kolam patterns**,
deployed as a working Streamlit web app.

- **Input:** a reference dataset of real Kolam images (user-supplied)
- **Representation:** each candidate Kolam is encoded as a genome (Truchet-tile
  grid — see below) built on top of a pulli dot grid
- **Evolution:** a population of genomes is evolved generation over
  generation using selection, crossover, and mutation
- **Fitness:** candidates are scored on (a) symmetry / loop-closure
  correctness and (b) similarity to the reference dataset
- **Output:** a deployed app where a user can run the GA and watch/download
  the evolved Kolam pattern

---

## 2. Pipeline / Phase Map

| Phase | Module (planned) | Status |
|---|---|---|
| Grid representation | `grid.py` | ✅ Done (Day 1) |
| Genome encoding | `genome.py` | ✅ Done (Day 2) |
| Arc renderer | `renderer.py` | ✅ Done (Day 3) — **Phase 1 complete** |
| Population init | `population.py` | ✅ Done (Day 4) — **start of Phase 2** |
| Symmetry fitness | `fitness.py` | ✅ Done (Day 5) |
| Dataset preprocessing | `dataset.py` | ✅ Done (Day 6) |
| Similarity fitness | `similarity.py` | ✅ Done (Day 7) — **Phase 2 fitness complete** |
| Selection | `selection.py` | ✅ Done (Day 8) — **start of Phase 3** |
| Crossover | `crossover.py` | ✅ Done (Day 9) |
| Mutation | `mutation.py` | ✅ Done (Day 10) — **all three GA operators complete** |
| GA main loop | `ga.py` | ✅ Done (Day 11) — **Phase 3 complete** |
| Experiments/tuning | `experiments.py` | ✅ Done (Day 12) — tuned config in `outputs/day12_best_config.json` |
| Streamlit app | `app_core.py` + `app.py` | 🟡 Day 13 in progress: 13a core done; 13b `app.py` written (needs first real `streamlit run`); 13c panels pending |
| Deployment config | `Dockerfile` / `requirements.txt` | ⏳ Pending (Day 14) |
| Polish/testing | — | ⏳ Pending (Day 15) |

---

## 3. Symbol Registry (everything defined so far)

### `src/grid.py`

| Name | Kind | Signature / Notes |
|---|---|---|
| `PulliGrid` | class (dataclass) | `PulliGrid(n: int = 5, grid_type: str = "square", spacing: float = 1.0)` |
| `PulliGrid.n` | attribute | grid size parameter |
| `PulliGrid.grid_type` | attribute | `"square"` or `"diamond"` |
| `PulliGrid.spacing` | attribute | distance between adjacent dots |
| `PulliGrid.points` | attribute | flat `List[Tuple[float, float]]` of all dot coords |
| `PulliGrid.rows` | attribute | `List[List[Tuple[float, float]]]` — dots grouped by row (used by `genome.py` for cell lookups — **do not repurpose this name**) |
| `PulliGrid.center` | property | centroid `(x, y)` of all points |
| `PulliGrid._build_square()` | method | internal — builds n×n lattice |
| `PulliGrid._build_diamond()` | method | internal — builds rhombus layout |
| `PulliGrid.bounding_box()` | method | returns `(min_x, min_y, max_x, max_y)` |
| `PulliGrid.symmetry_axes(kind, order)` | method | `kind: "rotational" \| "reflective"`, returns list of transform functions — reserved for `fitness_symmetry.py` (Day 5) |
| `PulliGrid.nearest_point(x, y)` | method | snaps arbitrary coords to nearest dot — reserved for `mutation.py` (Day 10) |

### `src/genome.py`

| Name | Kind | Signature / Notes |
|---|---|---|
| `TileType` | class (IntEnum) | `ARC_A = 0`, `ARC_B = 1` |
| `KolamGenome` | class (dataclass) | `KolamGenome(grid: PulliGrid)` — **square grids only for now** |
| `KolamGenome.grid` | attribute | the `PulliGrid` this genome is built on |
| `KolamGenome.rows` / `.cols` | attribute | `= grid.n - 1` each (cell grid dimensions — **note: distinct from `PulliGrid.rows`, which is the dot grid, not the cell grid**) |
| `KolamGenome.tiles` | attribute | `List[List[TileType]]` — the actual genome data |
| `KolamGenome.randomize(rng)` | method | fills `tiles` randomly; accepts seeded `random.Random` |
| `KolamGenome.to_chromosome()` | method | flattens `tiles` → `List[int]` (**this is "the chromosome" — the name GA operators in Phase 3 should use**) |
| `KolamGenome.from_chromosome(chromosome)` | method | rebuilds `tiles` from a flat `List[int]` |
| `KolamGenome.get_tile(i, j)` / `.set_tile(i, j, t)` | methods | single-cell accessors |
| `KolamGenome.copy()` | method | deep-ish copy (new `tiles` list) |
| `KolamGenome.cell_corners(i, j)` | method | returns `(tl, tr, bl, br)` dot coords for cell `(i, j)` |
| `KolamGenome.as_symbol_grid()` | method | text preview (`\` / `/`) |

### `src/visualize_grid.py` (sanity-check script, not core pipeline)

| Name | Kind | Notes |
|---|---|---|
| `plot_grid(grid, ax, title)` | function | draws dots + centroid marker on a given matplotlib axis |

### `src/visualize_genome.py` (sanity-check script, not core pipeline)

| Name | Kind | Notes |
|---|---|---|
| `OUTPUT_DIR` | module constant | `os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")` — **reuse this exact pattern in every future script that saves output**, don't invent a new relative path style |
| `plot_genome_preview(genome, ax, title)` | function | draws diagonal-per-tile preview on a given matplotlib axis |

### `src/renderer.py` (core pipeline — first module later phases will call directly)

| Name | Kind | Signature / Notes |
|---|---|---|
| `OUTPUT_DIR` | module constant | same path pattern as above |
| `_cell_arcs(tl, tr, bl, br, tile)` | function (internal) | returns `[(center, theta1, theta2), (center, theta1, theta2)]` — the 2 arcs for one cell |
| `render_genome(genome, ax=None, show_dots=True, line_color="#8B2E2E", line_width=2.2, dot_color="#cccccc")` | function | **the main renderer** — draws a `KolamGenome` as curved arcs on a matplotlib `Axes` and returns that `Axes`. This is the function Phase 2 (fitness) and Phase 4 (Streamlit app) should both call whenever a genome needs to become an image — don't write a second renderer elsewhere. |

### `src/population.py`

| Name | Kind | Signature / Notes |
|---|---|---|
| `validate_genome(genome)` | function | structural validity check only (dimensions + valid `TileType` values) — **not** a quality/aesthetic check; that's `fitness_*.py`'s job |
| `Population` | class (dataclass) | `Population(grid: PulliGrid, size: int, seed: Optional[int] = None)` — square grids only, matching `KolamGenome` |
| `Population.grid` / `.size` / `.seed` | attributes | as passed to constructor |
| `Population.genomes` | attribute | `List[KolamGenome]` — the actual population data |
| `Population._rng` | attribute (internal) | seeded `random.Random`, used to seed each genome's own randomization |
| `Population.initialize()` | method | fills `.genomes` with `size` random, validated genomes; returns `self` |
| `Population.chromosomes()` | method | returns `List[List[int]]` — **the interface Phase 3's selection/crossover/mutation operators should consume**, not `.genomes` directly |
| `Population.replace(new_genomes)` | method | swaps in a new generation — reserved for the Day 11 main GA loop |
| `Population.__len__` / `__iter__` / `__getitem__` | dunder methods | population behaves like a sequence of genomes directly |

### `src/visualize_population.py` (sanity-check script, not core pipeline)

No new module-level names beyond `OUTPUT_DIR` (same pattern as other
sanity-check scripts). Reuses `render_genome()` from `renderer.py` directly
— intentionally does not define its own rendering logic.

### `src/fitness.py`

| Name | Kind | Signature / Notes |
|---|---|---|
| `symmetry_score(genome)` | function | returns `float` in `[0, 1]` — averages horizontal-reflection, vertical-reflection, and 180°-rotation match fractions |
| `loop_closure_score(genome)` | function | returns `float` in `[0, 1]` — fraction of curve (by arc count) in fully closed-loop graph components; **note: 1.0 is structurally unreachable**, this is a comparative score only |
| `fitness(genome, reference_transforms=None, symmetry_weight=1/3, loop_weight=1/3, similarity_weight=1/3, similarity_scale=20.0, similarity_k=1, similarity_calibration=None)` | function | **the main scoring entry point** — weighted sum of symmetry, loop-closure, and (if `reference_transforms` given) similarity. Falls back to the Day 5 two-term score (weights renormalized) when `reference_transforms` is `None` — this is what Phase 3's `select()` (Day 8) should call, always passing the precomputed `reference_transforms` from `similarity.precompute_reference_transforms()`. |
| `_flipped(t)` | function (internal) | `ARC_A ↔ ARC_B` |
| `_mid(p, q)` / `_key(p)` | functions (internal) | geometry helpers for the loop-closure graph |
| `_edge_midpoint_graph(genome)` | function (internal) | builds `{midpoint: [connected midpoints]}` adjacency map from every cell's arcs |

### `src/visualize_fitness.py` (sanity-check script, not core pipeline)

No new module-level names beyond `OUTPUT_DIR`. Reuses `Population`,
`fitness()`, `symmetry_score()`, `loop_closure_score()`, and
`render_genome()` directly.

### `src/similarity.py`

| Name | Kind | Signature / Notes |
|---|---|---|
| `ReferenceTransforms` | type alias | `List[Tuple[str, np.ndarray, np.ndarray]]` — `(name, skeleton, distance_transform)` triples |
| `genome_to_skeleton(genome, size=IMAGE_SIZE)` | function | renders a genome in-memory (no disk I/O) and preprocesses it via `dataset.preprocess_image` |
| `precompute_reference_transforms(dataset)` | function | precomputes distance transforms for every reference skeleton — **call once per GA run**, never per-genome (this is the ~8.5s → ~0.35s optimization) |
| `_chamfer_distance(genome_skeleton, genome_dt, ref_skeleton, ref_dt)` | function (internal) | returns `max(d_ab, d_ba)` — **not the average**; see Day 7 bug-fix note in PROGRESS.md re: dense-reference bias |
| `similarity_score(genome, reference_transforms, size=IMAGE_SIZE, scale=20.0)` | function | best-match similarity in `[0, 1]`, via `exp(-distance / scale)`. `scale` is a starting value, expected to be retuned at Day 12. |
| `best_match(genome, reference_transforms, size=IMAGE_SIZE)` | function | like `similarity_score` but also returns which reference matched — reserved for the "closest real Kolam" display in the app (Day 13) |

### `src/visualize_similarity.py` (sanity-check script, not core pipeline)

No new reusable names. Reuses `render_genome`, `load_processed_dataset`,
`load_image_grayscale`, `precompute_reference_transforms`,
`similarity_score`, `best_match` directly.

### `src/dataset.py`

| Name | Kind | Signature / Notes |
|---|---|---|
| `IMAGE_SIZE` | module constant | `= 256` — fixed canvas size for both dataset images and rendered genomes; **reuse this exact constant in `renderer.py`-based rendering for Day 7's similarity comparison, don't hardcode a different size there** |
| `load_image_grayscale(path)` | function | loads any image file as a grayscale `np.ndarray` |
| `preprocess_image(image, size=IMAGE_SIZE)` | function | resize → Otsu threshold → skeletonize; returns boolean 2D array (`True` = curve pixel). **Assumes dark curve on light background** — flip `<` to `>` in the `binary = ...` line if real dataset images are the opposite |
| `load_dataset(data_dir, size=IMAGE_SIZE, extensions=(".png",".jpg",".jpeg",".bmp"))` | function | loads + preprocesses every image under `data_dir`, **recursively** (walks subfolders, e.g. `data/raw/kolam19/`, `data/raw/kolam29/`, `data/raw/kolam109/`). Returns `List[Tuple[str, np.ndarray]]` of `(relative_path, skeleton)` pairs — `relative_path` includes the subfolder, e.g. `"kolam19/kolam19-0.jpg"`. Call once per GA run, not per-generation. |
| `save_processed_dataset(dataset, processed_root)` | function | caches every `(relative_path, skeleton)` pair from `load_dataset()` as a PNG under `processed_root`, mirroring the raw subfolder structure exactly (e.g. `kolam19/kolam19-0.jpg` → `processed_root/kolam19/kolam19-0.png`) |
| `load_processed_dataset(processed_root)` | function | reloads cached skeletons saved by `save_processed_dataset()`, skipping threshold+skeletonize entirely. **Use this (not `load_dataset`) in Day 7/11 once the cache exists** — confirmed ~28x faster (0.2s vs 5.7s for 600 images) |

### `src/visualize_dataset.py` (sanity-check script, not core pipeline)

No new reusable names — imports `load_image_grayscale`, `preprocess_image`,
`IMAGE_SIZE` from `dataset.py` directly.

### `src/selection.py`

| Name | Kind | Signature / Notes |
|---|---|---|
| `TOURNAMENT_SIZE` | module constant | `= 3` — default tournament size |
| `SELECTION_METHODS` | module constant | `("tournament", "roulette", "rank")` |
| `select(population, fitnesses, n, method="tournament", tournament_size=TOURNAMENT_SIZE, rng=None)` | function | **the main selection entry point.** `population` = a `Population` *or* a list of chromosomes; `fitnesses[i]` aligns with member `i`. Returns `n` parent **chromosomes** (copies, sampled with replacement) |
| `select_indices(fitnesses, n, method, tournament_size, rng)` | function | same, but returns indices — useful for tracking parents |
| `elite_indices(fitnesses, k)` | function | top-k indices, best first — for elitism in the Day 11 loop |
| `evaluate_population(population, reference_transforms=None, **fitness_kwargs)` | function | `Population` → `List[float]` via `fitness.fitness()`; lazy-imports `fitness`. **Always pass `reference_transforms`** |
| `_as_chromosomes`, `_tournament_indices`, `_roulette_indices`, `_rank_indices`, `_weighted_indices` | functions (internal) | method implementations / helpers |

### `src/visualize_selection.py` (sanity-check script, not core pipeline)

No new reusable names beyond `OUTPUT_DIR` / `PROCESSED_DIR` (path pattern as other scripts).

### `src/crossover.py`

| Name | Kind | Signature / Notes |
|---|---|---|
| `Chromosome` | type alias | `List[int]` |
| `CROSSOVER_RATE` | module constant | `= 0.9` — default probability a pair is recombined |
| `CROSSOVER_METHODS` | module constant | `("single_point", "two_point", "uniform", "block")` |
| `crossover(parent1, parent2, method="block", crossover_rate=CROSSOVER_RATE, rng=None, **kwargs)` | function | **the main crossover entry point.** Two parent chromosomes → `(child1, child2)`, new lists. With prob. `1 - crossover_rate` returns plain copies. `kwargs` go to the operator (e.g. `shape=` for block) |
| `crossover_pairs(parents, method, crossover_rate, rng, **kwargs)` | function | pairs `parents` consecutively (0&1, 2&3…), returns children in order; same length as input (odd last parent copied). Feed it `selection.select()` output |
| `single_point_crossover` / `two_point_crossover` / `uniform_crossover(p1, p2, rng, swap_prob=0.5)` / `block_crossover(p1, p2, rng, shape=None)` | functions | the four operators; `block` swaps a random rectangle of the 2D tile grid, shape inferred as square from length |
| `side_length(chromosome)` | function | cell-grid side of a square genome (`grid.n - 1`); raises if length isn't a perfect square |
| `_check(p1, p2)` / `_OPERATORS` | internal | length validation / method-name → function map |

### `src/visualize_crossover.py` (sanity-check script, not core pipeline)

No new reusable names beyond `OUTPUT_DIR`. Defines a tiny private helper `_genome(grid, chromosome)`.

### `src/mutation.py`

| Name | Kind | Signature / Notes |
|---|---|---|
| `Chromosome` | type alias | `List[int]` (same alias as in `crossover.py`) |
| `MUTATION_METHODS` | module constant | `("flip", "block_flip", "symmetric_flip")` |
| `mutate(chromosome, mutation_rate=None, method="flip", rng=None, **kwargs)` | function | **the main mutation entry point.** Returns a *new* mutated chromosome; input untouched. `mutation_rate=None` → `1/len(chromosome)`. Validates genes ∈ {0,1} and rate ∈ [0,1] |
| `mutate_all(chromosomes, mutation_rate, method, rng, **kwargs)` | function | mutates every chromosome in a list (e.g. output of `crossover_pairs`) |
| `default_mutation_rate(chromosome)` | function | `1 / len(chromosome)` |
| `flip_mutation(chromosome, rate, rng)` | function | per-gene independent flip |
| `block_flip_mutation(chromosome, rate, rng, shape=None, max_side=2)` | function | with prob. `rate * len` flips one random ≤`max_side`×`max_side` rectangle |
| `symmetric_flip_mutation(chromosome, rate, rng, shape=None)` | function | flips whole 4-cell mirror/rotation orbits together → `symmetry_score` exactly preserved |
| `_shape(chromosome, shape)` / `_OPERATORS` | internal | grid-shape inference / method map |

### `src/visualize_mutation.py` (sanity-check script, not core pipeline)

No new reusable names beyond `OUTPUT_DIR`; private helper `_genome(grid, chromosome)` (same as in `visualize_crossover.py`).

### `src/ga.py`

| Name | Kind | Signature / Notes |
|---|---|---|
| `GAConfig` | class (dataclass) | all GA hyper-parameters, with defaults: `population_size=50`, `generations=100`, `elite_count=2`, `selection_method="tournament"`, `tournament_size=3`, `crossover_method="block"`, `crossover_rate=0.9`, `mutation_method="flip"`, `mutation_rate=None` (→ 1/len), `sample_size=None`, `patience=None`, `seed=None`, `fitness_kwargs={}` (weights passed to `fitness()`) |
| `GAResult` | class (dataclass) | `best_chromosome`, `best_genome` (`KolamGenome`), `best_fitness` (scored vs ALL references), `history`, `population` (final), `config`, `elapsed_s` |
| `run_ga(grid, reference_transforms=None, config=None, callback=None)` | function | **the main GA entry point.** `callback(stats_dict)` fires after every generation incl. gen 0 — the hook for Streamlit live progress (Day 13) |
| history entry | dict | `{"generation", "best", "mean", "worst", "diversity", "best_chromosome"}`; `diversity` = unique chromosomes / population size |
| `_genome_from_chromosome(grid, chromosome)` | function (internal, but imported by `visualize_ga.py`) | builds a `KolamGenome` from a flat chromosome; works whether `from_chromosome` mutates in place or returns a genome |
| `_reference_subset(reference_transforms, sample_size, rng)` / `_stats(gen, chroms, fit)` | functions (internal) | per-generation reference sampling / history record |

**`sample_size` lives in `GAConfig`, not in `similarity_score()`** (this
replaces the earlier idea of adding a `sample_size` param to `similarity.py`):
`ga.py` samples a subset of `reference_transforms` each generation and passes
that to `fitness()`, so `similarity.py` is unchanged.

### `src/visualize_ga.py` (sanity-check script, not core pipeline)

No new reusable names beyond `OUTPUT_DIR` / `PROCESSED_DIR` (plus private `_HERE`).

### `src/experiments.py`

| Name | Kind | Signature / Notes |
|---|---|---|
| `DEFAULT_GRID_N` | module constant | `= 6` (matches `visualize_ga.py`) |
| `SCALE_CANDIDATES` | module constant | `(5, 10, 20, 40, 80)` similarity-scale values tested |
| `OPTIONAL` | module constant | experiments skipped unless named in `--only` (`{"population"}`) |
| `RESULTS_CSV` / `BEST_CONFIG_JSON` | module constants | `outputs/day12_results.csv` / `outputs/day12_best_config.json` |
| `build_experiments()` | function | `{name: (default_label, [(label, overrides)])}`; override keys = any `GAConfig` field plus `grid_n`, `rate_mult`, `fitness_kwargs` |
| `build_run(base, overrides, args)` | function | → `(PulliGrid, GAConfig)` |
| `run_one(experiment, label, overrides, seed, base, args, ref)` | function | one GA run → result row dict; `yardstick` = default `fitness()` on ALL refs |
| `summarize` / `pick_winner` / `print_table` | functions | per-setting mean ± s.e.; challenger must beat incumbent by > 1 s.e. combined |
| `scale_analysis(grid, ref, ...)` / `plot_scale` | functions | how well each similarity `scale` separates random genomes |
| `tuned_config(path=BEST_CONFIG_JSON, **overrides)` | function | → `(grid_n, GAConfig)` from the Day 12 result — **what the Day 13 app should call** |
| `load_rows` / `append_row` / `_init_worker` / `_worker_task` | functions | resumable CSV store / multiprocessing helpers |

CLI: `--quick`, `--seeds`, `--generations`, `--pop`, `--sample`, `--grid-n`, `--only`, `--fresh`, `--scale-only`, `--workers`.

### Day 12.5 additions

| Name | File | Notes |
|---|---|---|
| `distances_to_refs(genome_skeleton, reference_transforms)` | `similarity.py` | Chamfer distance to every reference (array) |
| `similarity_distance(genome, refs, size, k=1)` | `similarity.py` | raw px distance, mean of k nearest refs |
| `distance_matrix(genomes, refs, size)` | `similarity.py` | (n_genomes, n_refs); renders each genome once |
| `calibrate_similarity(grid, refs, k, n_genomes, sample_size, n_subsets, seed)` | `similarity.py` | -> `{"mu","sigma","k"}` from random genomes |
| `similarity_score(..., k=1, calibration=None)` | `similarity.py` | default = old `exp(-d/scale)`; with calibration = logistic |
| `diagnose`, `run_variant`, `summarize`, `plot_genomes` | `similarity_fix.py` | Part 1 diagnostics / Part 2 A/B |
| outputs | `outputs/` | `day12b_diagnostic.png`, `day12b_results.csv`, `day12b_genomes.png`, `day12b_summary.json` |

### Day 12.6 additions

| Name | File | Notes |
|---|---|---|
| `SYMMETRY_MODES` | `symmetry.py` | `("mirror", "rot180")` |
| `symmetry_map(rows, cols, mode)` | `symmetry.py` | cached; -> `(tuple of (rep_idx, flip), n_free)` |
| `n_free_cells(rows, cols, mode)` | `symmetry.py` | free cells the GA actually searches (`None` -> all) |
| `symmetrize_chromosome(chrom, rows, cols, mode)` | `symmetry.py` | new symmetric chromosome from the free cells |
| `symmetrize_genome(genome, mode)` | `symmetry.py` | copy of the genome made symmetric |
| `GAConfig.symmetry_mode` | `ga.py` | `None` (default) / `"mirror"` / `"rot180"` |
| `run_one`, `summarize`, `plot_genomes` | `symmetry_experiment.py` | none vs rot180 vs mirror comparison; outputs `day12c_*` |

### Day 13a additions (`src/app_core.py`, tests in `src/test_app_core.py`)

| Name | Kind | Notes |
|---|---|---|
| `RunSettings` | dataclass | `grid_n=13, symmetry_mode="mirror", population_size=30, generations=30, sample_size=50, seed=0` |
| `EvolutionResult` | dataclass | `genome, chromosome, best_fitness, symmetry, loop_closure, d_min, match_name, match_skeleton, history, elapsed_s` |
| `load_references(processed_dir)` | function | -> reference transforms; raises `FileNotFoundError` with a clear message |
| `validate_settings(s)` | function | raises `ValueError` (grid 6-16, pop >= 6, gens >= 1, ...) |
| `make_ga_config(s, config_path)` | function | tuned operators from the Day 12 JSON, fallback if missing |
| `run_evolution(refs, s, on_progress, config_path)` | function | `on_progress(done, total, stats, elapsed)` per generation |
| `render_png(genome, show_dots)` / `skeleton_png(skel)` | functions | PNG bytes |
| `eta_seconds(elapsed, done, total)` / `result_summary(r)` | functions | ETA / JSON-able dict |
| `SYMMETRY_CHOICES` | dict | UI label -> mode (`"mirror"`, `"rot180"`, `None`) |
| `PROCESSED_DIR`, `CONFIG_PATH` | constants | overridable via `KOLAM_PROCESSED_DIR`, `KOLAM_CONFIG_PATH` |

### Day 13c additions

| Name | File | Notes |
|---|---|---|
| `GAConfig.initial_chromosome / initial_fraction / initial_spread` | `ga.py` | start from a user pattern (default `None`) |
| `apply_initial_seed(chromosomes, seed, fraction, spread, rng)` | `ga.py` | first member exact copy, others flipped with prob. `spread` |
| `RunSettings.start_pattern / start_fraction / start_spread` | `app_core.py` | validated in `validate_settings` |
| `FREEDOM_CHOICES` | `app_core.py` | label -> (fraction, spread) |
| `pattern_to_rows`, `rows_to_pattern`, `random_pattern`, `effective_start_pattern`, `render_pattern_png` | `app_core.py` | editor helpers / preview |
| tests | `test_seeding.py`, `test_app_ui.py` | 30 and 29 checks |

### Fast mode additions

| Name | File | Notes |
|---|---|---|
| `fitness(..., similarity_weight=0)` | `fitness.py` | skips similarity (and rendering) when the weight is 0 |
| `RunSettings.fast_mode` | `app_core.py` | default True; evolve on symmetry + loop closure only |
| `FAST_FITNESS_KWARGS` | `app_core.py` | `{symmetry 0.5, loop 0.5, similarity 0.0}` |
| `EvolutionResult.best_fitness` | `app_core.py` | now always the full formula vs ALL references |

### Day 13c-5 additions

| Name | File | Notes |
|---|---|---|
| `run_variants(refs, settings, n=6, on_progress)` | `app_core.py` | n consecutive seeds, fast mode only, n in 1..12 |
| `match_png(result)` | `app_core.py` | PNG of the closest reference's skeleton |
| `build_settings()`, `show_result(...)` | `app.py` | helpers shared by the Evolve / Variants buttons |

### Day 13c-3 additions

| Name | File | Notes |
|---|---|---|
| `genome_to_skeleton_fast(genome, size, line_width)` | `similarity.py` | PIL drawing, ~150x faster than `genome_to_skeleton` |
| `overlap_score(genome_sk, ref_sk, ref_dt, tolerance)` | `similarity.py` | F1 of line pixels within tolerance |
| `prepare_target(gray, grid_n, size)` | `similarity.py` | uploaded picture -> aligned skeleton; raises `ValueError` |
| `overlap_png_array(genome_sk, target_sk)` | `similarity.py` | RGB overlay array |
| `similarity_score(..., mode="overlap", tolerance, fast_render)` | `similarity.py` | `mode` is `"chamfer"` (default) or `"overlap"` |
| `fitness(..., similarity_mode, similarity_tolerance, similarity_fast_render)` | `fitness.py` | passed through to `similarity_score` |
| `RunSettings.target_image / target_weight / target_tolerance` | `app_core.py` | imitation mode when `target_image` is set |
| `load_target`, `auto_tolerance`, `target_fitness_kwargs`, `overlay_png` | `app_core.py` | helpers |
| `EvolutionResult.target_skeleton / target_score / target_baseline` | `app_core.py` | imitation results |

---

## 4. Naming Conventions (keep consistent going forward)

- **Classes:** `PascalCase` (`PulliGrid`, `KolamGenome`, `TileType`)
- **Functions/methods/variables:** `snake_case` (`to_chromosome`, `cell_corners`)
- **Module-level constants:** `UPPER_SNAKE_CASE` (`OUTPUT_DIR`)
- **"Chromosome"** always refers specifically to the *flat* `List[int]` form
  (`to_chromosome()` / `from_chromosome()`), never the 2D `tiles` grid —
  keep this distinction when Phase 3 (`selection.py`, `crossover.py`,
  `mutation.py`) is built, since those operators work on chromosomes, not
  genomes directly.
- **`grid` vs `genome`** — a recurring source of possible confusion:
  `PulliGrid` = the dots. `KolamGenome` = the tile pattern drawn on top of
  the dots. A `KolamGenome` *has* a `PulliGrid` (`genome.grid`), not the
  other way around.
- **Reserved names for upcoming phases** (don't reuse elsewhere):
  - `fitness_similarity_score()` — planned dataset-similarity scoring
    function (Day 7); will likely be added as a 3rd weighted term inside
    `fitness()` in `fitness.py`, not a separate top-level scorer
  - `select()`, `crossover()` and `mutate()` all exist now — see registry.
    (`PulliGrid.nearest_point()` was reserved for mutation but is not needed:
    genes are tile flips, so mutation never leaves the grid.), each expected to take/return chromosomes (flat lists),
    consistent with the "chromosome" convention above. **Note:** these
    should consume `Population.chromosomes()`, not `Population.genomes`
    directly.

---

## 5. Currently Pending / Next Step

**13c-4 (next):** `app.py` UI for imitation: image upload, preview of the prepared target, "Imitate this image" mode (no symmetry by default,
about 60 generations, picture-strictness slider), overlay picture and the score vs random baseline.
Then **Day 14** deployment, **Day 15** polish/testing/report. Still to check in the real app: 13c-5 was confirmed working; imitation not yet tried on real Kolam pictures.

**Known limitations:** (1) genomes are far simpler than the dataset's fractal Kolams (Truchet-like, no dots);
(2) pixel-distance similarity to the *dataset* mostly measures dot density, not shape; imitation follows rough line positions only;
(3) loop closure tops out near 0.85 (border strands); (4) in fast mode the dataset only supplies the closest-Kolam match and distance.
