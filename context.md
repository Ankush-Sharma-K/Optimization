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
| Population init | `population.py` | ⏳ Pending (Day 4) |
| Symmetry fitness | `fitness_symmetry.py` | ⏳ Pending (Day 5) |
| Dataset preprocessing | `dataset.py` | ⏳ Pending (Day 6) |
| Similarity fitness | `fitness_similarity.py` | ⏳ Pending (Day 7) |
| Selection | `selection.py` | ⏳ Pending (Day 8) |
| Crossover | `crossover.py` | ⏳ Pending (Day 9) |
| Mutation | `mutation.py` | ⏳ Pending (Day 10) |
| GA main loop | `ga.py` | ⏳ Pending (Day 11) |
| Experiments/tuning | — | ⏳ Pending (Day 12) |
| Streamlit app | `app.py` | ⏳ Pending (Day 13) |
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
  - `Population` — planned class in `population.py` (Day 4), will hold a
    list of `KolamGenome` instances
  - `fitness_symmetry_score()`, `fitness_similarity_score()` — planned
    scoring functions (Days 5, 7)
  - `select()`, `crossover()`, `mutate()` — planned GA operator functions
    (Days 8–10), each expected to take/return chromosomes (flat lists),
    consistent with the "chromosome" convention above

---

## 5. Currently Pending / Next Step

**Day 4 — Population Initializer.** Build a `Population` class (in
`population.py`) that holds a list of many random `KolamGenome` instances,
ready to be scored and evolved starting Phase 2. Expected shape:
`Population(grid: PulliGrid, size: int)` with a method to generate `size`
randomized genomes — exact API to be confirmed and added to this registry
once written.