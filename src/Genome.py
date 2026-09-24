"""
kolamNet — Genome Encoding
============================
Represents a Kolam pattern as a chromosome the GA can mutate and cross over.

Encoding scheme (Truchet-tile based):
--------------------------------------
Between every 2x2 block of neighboring pulli dots there is a square "cell".
Each cell holds two quarter-circle arcs, and there are exactly two ways to
orient them:

    ARC_A ('\\')            ARC_B ('/')
    o---o                   o---o
    | ⌒ |                   | ⌒ |     (each arc connects two adjacent
    | ⌄ |                   | ⌄ |      corners of the cell, diagonally
    o---o                   o---o      opposite orientation)

Line enough oriented tiles up next to each other and the individual arcs
chain together into the continuous looping curves that make a Kolam. This
is why the genome is simply a grid of 0/1 values, one per cell:

  - one gene = one tile's orientation
  - mutation = flip a single tile
  - crossover = swap a block of tiles between two parent genomes
  - the tile grid maps 1:1 onto the arc renderer we'll build next (Day 3)

Currently implemented for square grids. Diamond-grid cells are irregular
(the "cell" between rows of different lengths isn't a clean 2x2 block), so
that support will be layered in once tile-connectivity rules are settled.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional
import random

from grid import PulliGrid


class TileType(IntEnum):
    ARC_A = 0   # arcs connect the top-left <-> bottom-right corners
    ARC_B = 1   # arcs connect the top-right <-> bottom-left corners


@dataclass
class KolamGenome:
    grid: PulliGrid
    rows: int = field(init=False)
    cols: int = field(init=False)
    tiles: List[List[int]] = field(default_factory=list, init=False)

    def __post_init__(self):
        if self.grid.grid_type != "square":
            raise NotImplementedError(
                "KolamGenome currently supports square grids only; "
                "diamond-grid tiling is planned for a later day."
            )
        # n dots per side -> (n - 1) cells per side
        self.rows = self.grid.n - 1
        self.cols = self.grid.n - 1
        self.tiles = [[TileType.ARC_A for _ in range(self.cols)] for _ in range(self.rows)]

    # -- construction / randomization -------------------------------------

    def randomize(self, rng: Optional[random.Random] = None):
        rng = rng or random.Random()
        for i in range(self.rows):
            for j in range(self.cols):
                self.tiles[i][j] = TileType(rng.randint(0, 1))
        return self

    # -- chromosome <-> tile grid conversion (what the GA operators use) --

    def to_chromosome(self) -> List[int]:
        """Flatten the tile grid into a 1D list — this is the actual
        'chromosome' that selection/crossover/mutation will operate on."""
        return [int(t) for row in self.tiles for t in row]

    def from_chromosome(self, chromosome: List[int]):
        expected = self.rows * self.cols
        if len(chromosome) != expected:
            raise ValueError(f"Expected chromosome of length {expected}, got {len(chromosome)}")
        idx = 0
        for i in range(self.rows):
            for j in range(self.cols):
                self.tiles[i][j] = TileType(chromosome[idx])
                idx += 1
        return self

    # -- basic accessors ----------------------------------------------------

    def get_tile(self, i: int, j: int) -> TileType:
        return self.tiles[i][j]

    def set_tile(self, i: int, j: int, t: TileType):
        self.tiles[i][j] = t

    def copy(self) -> "KolamGenome":
        clone = KolamGenome(self.grid)
        clone.tiles = [row[:] for row in self.tiles]
        return clone

    def cell_corners(self, i: int, j: int):
        """Returns the 4 dot coordinates (TL, TR, BL, BR) bounding cell (i, j),
        pulled straight from the PulliGrid this genome is built on."""
        tl = self.grid.rows[i][j]
        tr = self.grid.rows[i][j + 1]
        bl = self.grid.rows[i + 1][j]
        br = self.grid.rows[i + 1][j + 1]
        return tl, tr, bl, br

    def as_symbol_grid(self) -> str:
        """Quick text preview: '\\' / '/' per cell, no rendering needed."""
        symbol_map = {TileType.ARC_A: "\\", TileType.ARC_B: "/"}
        return "\n".join(" ".join(symbol_map[t] for t in row) for row in self.tiles)

    def __len__(self):
        return self.rows * self.cols


if __name__ == "__main__":
    g = PulliGrid(n=6, grid_type="square")
    genome = KolamGenome(g)
    genome.randomize(random.Random(42))

    print(f"Chromosome length: {len(genome)} genes ({genome.rows}x{genome.cols} cells)")
    print(f"Chromosome (flat): {genome.to_chromosome()}")
    print("\nTile preview:")
    print(genome.as_symbol_grid())