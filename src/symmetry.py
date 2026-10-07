"""
symmetry.py -- Day 12.6: symmetric-by-construction patterns.

Instead of hoping the GA discovers symmetry, a "repair" step copies a free
region of the chromosome onto the rest of the grid, so every genome is
symmetric no matter what crossover or mutation did. The GA then only has to
search the free region (a quarter of the grid for "mirror", half for "rot180").

Modes (consistent with fitness.symmetry_score):
  "mirror"  left-right AND top-bottom mirror (hence also 180-degree rotation).
            Under a mirror a tile flips ARC_A <-> ARC_B, as in symmetry_score.
            Free region = top-left quadrant.
  "rot180"  180-degree rotation only (tile identity unchanged).
            Free region = first half of the cells in reading order.

Odd-size caveat: with an odd number of tile rows/columns (grid_n even, e.g. 12
-> 11 x 11 tiles) the middle row/column lies ON the mirror axis, and a tile
can never equal its own flip, so "mirror" cannot reach a perfect score there.
With an even number of tile rows/columns (grid_n odd, e.g. 13 -> 12 x 12) it can.

Chromosomes are flat lists of 0/1 (0 = ARC_A, 1 = ARC_B), row by row.
"""
from functools import lru_cache
from typing import List, Optional, Tuple

from genome import KolamGenome

SYMMETRY_MODES = ("mirror", "rot180")


@lru_cache(maxsize=None)
def symmetry_map(rows: int, cols: int, mode: str) -> Tuple[Tuple[Tuple[int, int], ...], int]:
    """Returns (map, n_free). map[idx] = (representative_idx, flip) for every
    cell; n_free = number of cells that are their own representative."""
    if mode not in SYMMETRY_MODES:
        raise ValueError(f"unknown symmetry mode {mode!r}; choose from {SYMMETRY_MODES}")
    out = []
    for i in range(rows):
        for j in range(cols):
            if mode == "mirror":
                ii, jj = min(i, rows - 1 - i), min(j, cols - 1 - j)
                rep = ii * cols + jj
                flip = ((i != ii) + (j != jj)) % 2
            else:  # rot180
                idx = i * cols + j
                rep = min(idx, rows * cols - 1 - idx)
                flip = 0
            out.append((rep, flip))
    n_free = sum(1 for idx, (rep, _) in enumerate(out) if rep == idx)
    return tuple(out), n_free


def n_free_cells(rows: int, cols: int, mode: Optional[str]) -> int:
    return rows * cols if mode is None else symmetry_map(rows, cols, mode)[1]


def symmetrize_chromosome(chromosome: List[int], rows: int, cols: int, mode: Optional[str]) -> List[int]:
    """Returns a new, symmetric chromosome built from the free cells of the input."""
    if mode is None:
        return list(chromosome)
    mapping, _ = symmetry_map(rows, cols, mode)
    return [chromosome[rep] ^ flip for rep, flip in mapping]


def symmetrize_genome(genome: KolamGenome, mode: Optional[str]) -> KolamGenome:
    g = genome.copy()
    g.from_chromosome(symmetrize_chromosome(g.to_chromosome(), g.rows, g.cols, mode))
    return g
