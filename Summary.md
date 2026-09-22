# kolamNet — Day 1 Summary

**Phase:** 1 — Representation & Rendering
**Focus:** Pulli (dot) grid representation

---

## Conceptual Overview

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

---

## What Was Built

### `PulliGrid` class (`src/grid.py`)
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

### `visualize_grid.py`
- Sanity-check script (not part of the final pipeline) — plots both grid
  types side by side with centroid marked. Confirmed both grids are
  geometrically correct.

### Debugging note
- The original save path (`../outputs/...`) was relative to the *working
  directory*, which caused a `FileNotFoundError` depending on where the
  script was launched from. Fixed by anchoring the output path to the
  script's own file location via `os.path.dirname(os.path.abspath(__file__))`
  — this pattern should be reused in future scripts to avoid the same issue.

---

## Files Produced

```
OT Project/
├── requirements.txt
├── PROGRESS.md
├── src/
│   ├── grid.py
│   └── visualize_grid.py
├── data/       (empty — reference Kolam dataset goes here, Day 6)
└── outputs/
    └── day1_grid_sanity_check.png
```

---

## Next Up: Day 2

Design the genome encoding — how a sequence of curve segments around the
pulli grid gets represented as a chromosome, so it can later be mutated and
crossed over.
