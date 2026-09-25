"""
kolamNet — Population Initializer
====================================
Phase 2 starts here: instead of working with a single KolamGenome, the GA
needs a whole population of them to select from, cross over, and mutate.

This module is intentionally small right now -- it just creates and
structurally validates many random genomes. Selection (Day 8), crossover
(Day 9), and mutation (Day 10) will all operate on the chromosomes this
population produces; the main GA loop (Day 11) will call
Population.initialize() once at the start of a run and then repeatedly
replace its genomes generation over generation.
"""

import random
from dataclasses import dataclass, field
from typing import List, Optional

from grid import PulliGrid
from genome import KolamGenome, TileType


def validate_genome(genome: KolamGenome) -> bool:
    """Structural validity check: every cell holds a real TileType, and the
    tile grid's dimensions match the genome's own rows/cols. This does NOT
    check loop-closure or symmetry quality -- that's Phase 2's fitness
    functions' job (Day 5 onward). Every structurally valid genome is a
    renderable Kolam pattern; there are no illegal Truchet-tile
    combinations, so this mainly guards against bugs, not bad patterns."""
    if len(genome.tiles) != genome.rows:
        return False
    for row in genome.tiles:
        if len(row) != genome.cols:
            return False
        for tile in row:
            if tile not in (TileType.ARC_A, TileType.ARC_B):
                return False
    return True


@dataclass
class Population:
    grid: PulliGrid
    size: int
    seed: Optional[int] = None
    genomes: List[KolamGenome] = field(default_factory=list, init=False)

    def __post_init__(self):
        if self.grid.grid_type != "square":
            raise NotImplementedError(
                "Population currently supports square grids only, "
                "matching KolamGenome's current limitation."
            )
        self._rng = random.Random(self.seed)

    def initialize(self) -> "Population":
        """Fills self.genomes with self.size random, validated genomes."""
        self.genomes = []
        for _ in range(self.size):
            genome = KolamGenome(self.grid)
            genome.randomize(self._rng)
            assert validate_genome(genome), "Generated genome failed structural validation"
            self.genomes.append(genome)
        return self

    def chromosomes(self) -> List[List[int]]:
        """Flat chromosome view of every genome -- what Phase 3's GA
        operators (selection/crossover/mutation) will actually consume."""
        return [g.to_chromosome() for g in self.genomes]

    def replace(self, new_genomes: List[KolamGenome]):
        """Swaps in a new generation of genomes (used by the main GA loop, Day 11)."""
        if len(new_genomes) != self.size:
            raise ValueError(f"Expected {self.size} genomes, got {len(new_genomes)}")
        self.genomes = new_genomes

    def __len__(self):
        return len(self.genomes)

    def __iter__(self):
        return iter(self.genomes)

    def __getitem__(self, idx):
        return self.genomes[idx]


if __name__ == "__main__":
    g = PulliGrid(n=6, grid_type="square")
    pop = Population(grid=g, size=8, seed=42).initialize()

    print(f"Population size: {len(pop)}")
    print(f"All genomes structurally valid: {all(validate_genome(gen) for gen in pop)}")
    print(f"Chromosome length per genome: {len(pop.chromosomes()[0])}")

    # quick diversity sanity check -- chromosomes should differ across genomes
    unique_chromosomes = {tuple(c) for c in pop.chromosomes()}
    print(f"Unique chromosomes among {pop.size}: {len(unique_chromosomes)}")
