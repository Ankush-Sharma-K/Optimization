"""
crossover.py -- Day 9: crossover operators for the kolamNet GA.

Operates on CHROMOSOMES (flat List[int]) -- see context.md. Every operator takes
two parent chromosomes and returns two child chromosomes (new lists; parents are
never modified). Because each gene is a tile orientation at one grid cell, any
mix of parent genes is a valid genome, so no repair step is needed.

Main entry point:
    crossover(parent1, parent2, method="block", crossover_rate=0.9, rng=None)
        -> (child1, child2)
    crossover_pairs(parents, ...) -> List[chromosome]   (pairs up a parent pool)
"""
import math
import random
from typing import List, Optional, Tuple

Chromosome = List[int]

CROSSOVER_RATE = 0.9  # default probability that a pair is actually recombined
CROSSOVER_METHODS = ("single_point", "two_point", "uniform", "block")


def _check(p1: Chromosome, p2: Chromosome) -> None:
    if len(p1) != len(p2):
        raise ValueError(f"parent length mismatch: {len(p1)} vs {len(p2)}")
    if len(p1) < 2:
        raise ValueError("chromosome too short to recombine")


def side_length(chromosome: Chromosome) -> int:
    """Cell-grid side of a square genome (len = side**2, i.e. grid.n - 1)."""
    s = math.isqrt(len(chromosome))
    if s * s != len(chromosome):
        raise ValueError(f"length {len(chromosome)} is not a perfect square; pass shape=(rows, cols)")
    return s


def single_point_crossover(p1, p2, rng=None) -> Tuple[Chromosome, Chromosome]:
    """Swap the tails after one cut. In row-major order this splits the pattern
    into a top band and a bottom band."""
    _check(p1, p2)
    rng = rng or random.Random()
    cut = rng.randint(1, len(p1) - 1)
    return p1[:cut] + p2[cut:], p2[:cut] + p1[cut:]


def two_point_crossover(p1, p2, rng=None) -> Tuple[Chromosome, Chromosome]:
    """Swap the segment between two cuts (a run of whole/partial rows)."""
    _check(p1, p2)
    rng = rng or random.Random()
    a, b = sorted(rng.sample(range(1, len(p1)), 2)) if len(p1) > 2 else (1, 1)
    return p1[:a] + p2[a:b] + p1[b:], p2[:a] + p1[a:b] + p2[b:]


def uniform_crossover(p1, p2, rng=None, swap_prob: float = 0.5) -> Tuple[Chromosome, Chromosome]:
    """Swap each gene independently. Maximally disruptive to spatial structure."""
    _check(p1, p2)
    rng = rng or random.Random()
    c1, c2 = list(p1), list(p2)
    for i in range(len(p1)):
        if rng.random() < swap_prob:
            c1[i], c2[i] = c2[i], c1[i]
    return c1, c2


def block_crossover(p1, p2, rng=None, shape: Optional[Tuple[int, int]] = None) -> Tuple[Chromosome, Chromosome]:
    """Swap a random rectangular patch of the 2D tile grid.

    Kolam structure is local (loops form where neighbouring tiles match), so
    this transplants a compact patch -- possibly in the interior or a corner --
    as one unit. Row-major cuts (single/two-point) can only move whole bands and
    always keep the first genes with parent 1. Measured seam count (neighbouring
    cells from different parents) on a 5x5 grid: single-point ~5.0, block ~6.7,
    two-point ~8.6, uniform ~20 -- so block is NOT lower-disruption than
    single-point; which is better for fitness is a Day 12 experiment.
    `shape` defaults to a square side x side grid inferred from the length.
    """
    _check(p1, p2)
    rng = rng or random.Random()
    rows, cols = shape if shape else (side_length(p1),) * 2
    if rows * cols != len(p1):
        raise ValueError(f"shape {shape} does not match chromosome length {len(p1)}")
    r0, r1 = sorted((rng.randrange(rows), rng.randrange(rows)))
    c0, c1 = sorted((rng.randrange(cols), rng.randrange(cols)))
    ch1, ch2 = list(p1), list(p2)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            k = r * cols + c
            ch1[k], ch2[k] = p2[k], p1[k]
    return ch1, ch2


_OPERATORS = {
    "single_point": single_point_crossover,
    "two_point": two_point_crossover,
    "uniform": uniform_crossover,
    "block": block_crossover,
}


def crossover(
    parent1: Chromosome,
    parent2: Chromosome,
    method: str = "block",
    crossover_rate: float = CROSSOVER_RATE,
    rng: Optional[random.Random] = None,
    **kwargs,
) -> Tuple[Chromosome, Chromosome]:
    """Recombine two parents into two children.

    With probability (1 - crossover_rate) the children are plain copies of the
    parents. `kwargs` pass through to the operator (e.g. shape= for "block").
    """
    if method not in _OPERATORS:
        raise ValueError(f"unknown method {method!r}; choose from {CROSSOVER_METHODS}")
    _check(parent1, parent2)
    rng = rng or random.Random()
    if rng.random() >= crossover_rate:
        return list(parent1), list(parent2)
    return _OPERATORS[method](parent1, parent2, rng=rng, **kwargs)


def crossover_pairs(
    parents: List[Chromosome],
    method: str = "block",
    crossover_rate: float = CROSSOVER_RATE,
    rng: Optional[random.Random] = None,
    **kwargs,
) -> List[Chromosome]:
    """Pair parents consecutively (0&1, 2&3, ...) and return all children, in
    order. Output length equals input length (an odd last parent is copied).
    Feed it the output of selection.select() -- already shuffled by sampling."""
    rng = rng or random.Random()
    children: List[Chromosome] = []
    for i in range(0, len(parents) - 1, 2):
        children.extend(crossover(parents[i], parents[i + 1], method, crossover_rate, rng, **kwargs))
    if len(parents) % 2:
        children.append(list(parents[-1]))
    return children
