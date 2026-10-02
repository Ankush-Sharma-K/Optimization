"""
selection.py -- Day 8: selection operators for the kolamNet GA.

Operates on CHROMOSOMES (flat List[int]) and a parallel list of fitness
values, never on KolamGenome objects directly -- see context.md naming
convention. Selection is geometry-agnostic by design.

Main entry point:
    select(population, fitnesses, n, method="tournament", ...) -> List[chromosome]

Supporting pieces:
    select_indices(...)       same as select() but returns indices
    elite_indices(...)        top-k indices, for elitism in the Day 11 loop
    evaluate_population(...)  Population -> List[float] via fitness.fitness()
"""
import random
from typing import List, Optional, Sequence

TOURNAMENT_SIZE = 3  # module constant: default selection pressure
SELECTION_METHODS = ("tournament", "roulette", "rank")


def _as_chromosomes(population) -> List[List[int]]:
    """Accept a Population (anything with .chromosomes()) or a list of chromosomes."""
    if hasattr(population, "chromosomes"):
        return population.chromosomes()
    return [list(c) for c in population]


def _tournament_indices(fitnesses, n, k, rng):
    m = len(fitnesses)
    k = max(1, min(k, m))
    picks = []
    for _ in range(n):
        contenders = rng.sample(range(m), k)  # distinct contenders per tournament
        picks.append(max(contenders, key=lambda i: fitnesses[i]))
    return picks


def _weighted_indices(weights, n, rng):
    total = sum(weights)
    if total <= 0:  # all weights zero -> uniform
        return [rng.randrange(len(weights)) for _ in range(n)]
    return rng.choices(range(len(weights)), weights=weights, k=n)


def _roulette_indices(fitnesses, n, rng):
    # Shift so the worst individual has weight 0 would kill it entirely and
    # break when all are equal; shift to min=0 then add a tiny floor instead.
    lo = min(fitnesses)
    weights = [f - lo for f in fitnesses]
    if sum(weights) > 0:
        floor = 1e-6 * max(weights)
        weights = [w + floor for w in weights]
    return _weighted_indices(weights, n, rng)


def _rank_indices(fitnesses, n, rng):
    # Weight = rank (worst=1 ... best=m). Insensitive to the *scale* of fitness,
    # which matters because our 3-term fitness values are bunched (~0.39-0.52).
    order = sorted(range(len(fitnesses)), key=lambda i: fitnesses[i])
    weights = [0.0] * len(fitnesses)
    for rank, i in enumerate(order, start=1):
        weights[i] = float(rank)
    return _weighted_indices(weights, n, rng)


def select_indices(
    fitnesses: Sequence[float],
    n: int,
    method: str = "tournament",
    tournament_size: int = TOURNAMENT_SIZE,
    rng: Optional[random.Random] = None,
) -> List[int]:
    """Pick n parent indices (with replacement) according to `method`."""
    if len(fitnesses) == 0:
        raise ValueError("cannot select from an empty population")
    if method not in SELECTION_METHODS:
        raise ValueError(f"unknown method {method!r}; choose from {SELECTION_METHODS}")
    rng = rng or random.Random()
    if method == "tournament":
        return _tournament_indices(fitnesses, n, tournament_size, rng)
    if method == "roulette":
        return _roulette_indices(fitnesses, n, rng)
    return _rank_indices(fitnesses, n, rng)


def select(
    population,
    fitnesses: Sequence[float],
    n: int,
    method: str = "tournament",
    tournament_size: int = TOURNAMENT_SIZE,
    rng: Optional[random.Random] = None,
) -> List[List[int]]:
    """Select n parent chromosomes (copies, with replacement).

    `population` may be a Population or a list of chromosomes;
    `fitnesses[i]` must be the fitness of the i-th member.
    """
    chroms = _as_chromosomes(population)
    if len(chroms) != len(fitnesses):
        raise ValueError(f"{len(chroms)} chromosomes but {len(fitnesses)} fitnesses")
    idx = select_indices(fitnesses, n, method, tournament_size, rng)
    return [list(chroms[i]) for i in idx]  # copies: crossover/mutation can't corrupt the pool


def elite_indices(fitnesses: Sequence[float], k: int) -> List[int]:
    """Indices of the k fittest members, best first (for elitism)."""
    k = max(0, min(k, len(fitnesses)))
    return sorted(range(len(fitnesses)), key=lambda i: fitnesses[i], reverse=True)[:k]


def evaluate_population(population, reference_transforms=None, **fitness_kwargs) -> List[float]:
    """Score every genome with fitness.fitness(); returns a list aligned with population order.

    Always pass reference_transforms (from similarity.precompute_reference_transforms,
    computed ONCE per run) so the similarity term is included.
    """
    from fitness import fitness  # lazy: keeps this module importable without the dataset stack
    return [fitness(g, reference_transforms=reference_transforms, **fitness_kwargs)
            for g in population.genomes]
