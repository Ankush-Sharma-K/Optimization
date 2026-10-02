"""
mutation.py -- Day 10: mutation operators for the kolamNet GA.

Operates on CHROMOSOMES (flat List[int] of tile orientations 0/1) -- see
context.md. Every operator returns a NEW list; the input is never modified.
Since each gene is a binary tile orientation, mutating a gene = flipping it
(0 <-> 1), and every result is still a valid genome.

Main entry point:
    mutate(chromosome, mutation_rate=None, method="flip", rng=None, **kwargs)
    mutate_all(chromosomes, ...) -> List[chromosome]
"""
import math
import random
from typing import List, Optional, Tuple

Chromosome = List[int]

MUTATION_METHODS = ("flip", "block_flip", "symmetric_flip")


def default_mutation_rate(chromosome: Chromosome) -> float:
    """1 / length: on average ~1 gene flips per chromosome (a standard starting
    point for binary GAs). A Day 12 tuning candidate."""
    return 1.0 / len(chromosome)


def _shape(chromosome: Chromosome, shape: Optional[Tuple[int, int]]) -> Tuple[int, int]:
    if shape:
        rows, cols = shape
    else:
        rows = cols = math.isqrt(len(chromosome))
    if rows * cols != len(chromosome):
        raise ValueError(f"cannot view length {len(chromosome)} as a {rows}x{cols} grid; pass shape=(rows, cols)")
    return rows, cols


def flip_mutation(chromosome, rate, rng) -> Chromosome:
    """Flip each gene independently with probability `rate`."""
    return [1 - g if rng.random() < rate else g for g in chromosome]


def block_flip_mutation(chromosome, rate, rng, shape=None, max_side: int = 2) -> Chromosome:
    """With probability `rate * len(chromosome)` (capped at 1) flip one random
    rectangle of up to max_side x max_side cells. Makes a coherent local change
    (e.g. re-routes a loop) that single flips rarely produce."""
    rows, cols = _shape(chromosome, shape)
    out = list(chromosome)
    if rng.random() >= min(1.0, rate * len(chromosome)):
        return out
    h, w = rng.randint(1, min(max_side, rows)), rng.randint(1, min(max_side, cols))
    r0, c0 = rng.randrange(rows - h + 1), rng.randrange(cols - w + 1)
    for r in range(r0, r0 + h):
        for c in range(c0, c0 + w):
            out[r * cols + c] = 1 - out[r * cols + c]
    return out


def symmetric_flip_mutation(chromosome, rate, rng, shape=None) -> Chromosome:
    """Symmetry-preserving mutation: each *orbit* of 4 mirror/rotation-related
    cells {(i,j), (i,C-1-j), (R-1-i,j), (R-1-i,C-1-j)} is flipped together with
    probability `rate` (rate is per orbit-representative cell).

    The horizontal-mirror, vertical-mirror and 180-degree relations between
    these cells are each a pairwise "equal" / "opposite" relation (mirrors swap
    ARC_A<->ARC_B, 180-degree keeps identity). Flipping both cells of any pair
    leaves that relation unchanged, so symmetry_score is exactly preserved.
    Useful once the population is symmetric and plain flips would break it.
    """
    rows, cols = _shape(chromosome, shape)
    out = list(chromosome)
    seen = set()
    for i in range(rows):
        for j in range(cols):
            orbit = frozenset({(i, j), (i, cols - 1 - j), (rows - 1 - i, j), (rows - 1 - i, cols - 1 - j)})
            if orbit in seen:
                continue
            seen.add(orbit)
            if rng.random() < rate:
                for (r, c) in orbit:
                    out[r * cols + c] = 1 - out[r * cols + c]
    return out


_OPERATORS = {
    "flip": flip_mutation,
    "block_flip": block_flip_mutation,
    "symmetric_flip": symmetric_flip_mutation,
}


def mutate(
    chromosome: Chromosome,
    mutation_rate: Optional[float] = None,
    method: str = "flip",
    rng: Optional[random.Random] = None,
    **kwargs,
) -> Chromosome:
    """Return a mutated copy of `chromosome`.

    mutation_rate=None -> 1/len(chromosome). kwargs pass to the operator
    (e.g. shape=, max_side= for block_flip).
    """
    if method not in _OPERATORS:
        raise ValueError(f"unknown method {method!r}; choose from {MUTATION_METHODS}")
    if len(chromosome) == 0:
        raise ValueError("cannot mutate an empty chromosome")
    if any(g not in (0, 1) for g in chromosome):
        raise ValueError("chromosome genes must be 0 or 1")
    rate = default_mutation_rate(chromosome) if mutation_rate is None else mutation_rate
    if not 0.0 <= rate <= 1.0:
        raise ValueError(f"mutation_rate must be in [0, 1], got {rate}")
    return _OPERATORS[method](chromosome, rate, rng or random.Random(), **kwargs)


def mutate_all(
    chromosomes: List[Chromosome],
    mutation_rate: Optional[float] = None,
    method: str = "flip",
    rng: Optional[random.Random] = None,
    **kwargs,
) -> List[Chromosome]:
    """Mutate every chromosome in a list (e.g. the children from crossover_pairs)."""
    rng = rng or random.Random()
    return [mutate(c, mutation_rate, method, rng, **kwargs) for c in chromosomes]
