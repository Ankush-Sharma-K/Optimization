"""
ga.py -- Day 11: the GA main loop for kolamNet.

Wires the earlier pieces together:
    Population.initialize -> evaluate_population (fitness) -> elitism
    -> select -> crossover_pairs -> mutate_all -> Population.replace   (repeat)

Main entry point:
    run_ga(grid, reference_transforms=None, config=None, callback=None) -> GAResult

Operators work on chromosomes (flat List[int]); genomes are rebuilt only when
the new generation is handed back to Population.replace().
"""
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from genome import KolamGenome
from population import Population
from selection import select, elite_indices, evaluate_population
from crossover import crossover_pairs
from mutation import mutate_all
from symmetry import symmetrize_chromosome, n_free_cells

Chromosome = List[int]


@dataclass
class GAConfig:
    population_size: int = 50
    generations: int = 100
    elite_count: int = 2                   # best members copied unchanged each generation
    selection_method: str = "tournament"
    tournament_size: int = 3
    crossover_method: str = "block"
    crossover_rate: float = 0.9
    mutation_method: str = "flip"
    mutation_rate: Optional[float] = None  # None -> 1/len(chromosome)
    sample_size: Optional[int] = None      # score vs a random subset of this many references per generation
    patience: Optional[int] = None         # stop early after this many generations without a new best
    seed: Optional[int] = None
    symmetry_mode: Optional[str] = None    # None | "mirror" | "rot180": force symmetric genomes (see symmetry.py)
    fitness_kwargs: Dict = field(default_factory=dict)  # e.g. {"symmetry_weight": 0.5, ...}


@dataclass
class GAResult:
    best_chromosome: Chromosome
    best_genome: KolamGenome
    best_fitness: float                    # scored against ALL references (see note in run_ga)
    history: List[Dict]                    # one dict per generation, gen 0 = initial population
    population: Population                 # final generation
    config: GAConfig
    elapsed_s: float


def _genome_from_chromosome(grid, chromosome: Chromosome) -> KolamGenome:
    g = KolamGenome(grid)
    out = g.from_chromosome(chromosome)
    return out if isinstance(out, KolamGenome) else g  # works whether from_chromosome mutates or returns


def _reference_subset(reference_transforms, sample_size, rng):
    if reference_transforms is None or sample_size is None or sample_size >= len(reference_transforms):
        return reference_transforms
    return rng.sample(list(reference_transforms), sample_size)


def _stats(gen: int, chroms: List[Chromosome], fit: List[float]) -> Dict:
    best_i = max(range(len(fit)), key=lambda i: fit[i])
    return {
        "generation": gen,
        "best": fit[best_i],
        "mean": sum(fit) / len(fit),
        "worst": min(fit),
        "diversity": len({tuple(c) for c in chroms}) / len(chroms),  # fraction of unique chromosomes
        "best_chromosome": list(chroms[best_i]),
    }


def run_ga(
    grid,
    reference_transforms=None,
    config: Optional[GAConfig] = None,
    callback: Optional[Callable[[Dict], None]] = None,
) -> GAResult:
    """Evolve a population of Kolam genomes on `grid`.

    reference_transforms: output of similarity.precompute_reference_transforms(),
        computed ONCE by the caller. None -> similarity term is skipped.
    callback(stats_dict): called after every generation (incl. gen 0) -- the hook
        the Streamlit app will use for live progress.

    Note on sample_size: each generation is scored against a fresh random subset
    of references, so fitness values are only comparable *within* a generation
    and best-so-far curves are noisy. The final population is therefore re-scored
    against ALL references before the best member is chosen. With
    sample_size=None scoring is deterministic and, thanks to elitism, the best
    fitness never decreases.
    """
    cfg = config or GAConfig()
    if cfg.population_size < 2:
        raise ValueError("population_size must be >= 2")
    if not 0 <= cfg.elite_count < cfg.population_size:
        raise ValueError("elite_count must be in [0, population_size - 1]")
    if cfg.sample_size is not None and cfg.sample_size < 1:
        raise ValueError("sample_size must be >= 1")

    t0 = time.time()
    rng = random.Random(cfg.seed)
    pop = Population(grid, cfg.population_size, seed=cfg.seed).initialize()

    # Symmetric-by-construction: repair every chromosome so it is symmetric.
    mode = cfg.symmetry_mode
    rows, cols = pop.genomes[0].rows, pop.genomes[0].cols
    chrom_len = rows * cols
    mutation_rate = cfg.mutation_rate
    if mode:
        pop.replace([_genome_from_chromosome(grid, symmetrize_chromosome(c, rows, cols, mode))
                     for c in pop.chromosomes()])
        # Only the free cells survive the repair, so scale the per-gene mutation
        # rate up to keep the expected number of effective flips per child unchanged.
        base_rate = mutation_rate if mutation_rate is not None else 1.0 / chrom_len
        mutation_rate = min(1.0, base_rate * chrom_len / n_free_cells(rows, cols, mode))

    refs = _reference_subset(reference_transforms, cfg.sample_size, rng)
    fit = evaluate_population(pop, refs, **cfg.fitness_kwargs)
    history = [_stats(0, pop.chromosomes(), fit)]
    if callback:
        callback(history[-1])

    best_so_far, stale = history[0]["best"], 0
    n_children = cfg.population_size - cfg.elite_count
    n_parents = n_children + (n_children % 2)  # crossover_pairs works on pairs

    for gen in range(1, cfg.generations + 1):
        chroms = pop.chromosomes()
        elites = [list(chroms[i]) for i in elite_indices(fit, cfg.elite_count)]

        parents = select(chroms, fit, n_parents, cfg.selection_method, cfg.tournament_size, rng)
        children = crossover_pairs(parents, cfg.crossover_method, cfg.crossover_rate, rng)
        children = mutate_all(children, mutation_rate, cfg.mutation_method, rng)[:n_children]
        if mode:
            children = [symmetrize_chromosome(c, rows, cols, mode) for c in children]

        pop.replace([_genome_from_chromosome(grid, c) for c in elites + children])

        refs = _reference_subset(reference_transforms, cfg.sample_size, rng)
        fit = evaluate_population(pop, refs, **cfg.fitness_kwargs)
        history.append(_stats(gen, pop.chromosomes(), fit))
        if callback:
            callback(history[-1])

        if history[-1]["best"] > best_so_far + 1e-12:
            best_so_far, stale = history[-1]["best"], 0
        else:
            stale += 1
        if cfg.patience is not None and stale >= cfg.patience:
            break

    if cfg.sample_size is not None and reference_transforms is not None:
        fit = evaluate_population(pop, reference_transforms, **cfg.fitness_kwargs)  # final: full references
    best_i = max(range(len(fit)), key=lambda i: fit[i])
    best_chrom = list(pop.chromosomes()[best_i])
    return GAResult(
        best_chromosome=best_chrom,
        best_genome=_genome_from_chromosome(grid, best_chrom),
        best_fitness=fit[best_i],
        history=history,
        population=pop,
        config=cfg,
        elapsed_s=time.time() - t0,
    )
