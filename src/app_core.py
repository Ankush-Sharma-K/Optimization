"""
app_core.py -- Day 13, Phase 13a: all the logic behind the Streamlit app.

No Streamlit code lives here, so everything in this file can be tested from the
command line. app.py (Phase 13b/13c) only draws buttons and pictures and calls
these functions.

Main entry points
    load_references(processed_dir)          -> reference transforms (list of (name, skeleton, dt))
    RunSettings(...)                         -> what the user chose in the sidebar
    validate_settings(settings)              -> raises ValueError with a friendly message
    run_evolution(refs, settings, on_progress=None) -> EvolutionResult
    render_png(genome) / skeleton_png(skel)  -> PNG bytes for st.image / st.download_button
    eta_seconds(elapsed, done, total)        -> time left, for the progress display

Paths can be overridden with the environment variables KOLAM_PROCESSED_DIR and
KOLAM_CONFIG_PATH (useful for deployment, Day 14).
"""
import io
import json
import os
import time

import matplotlib
matplotlib.use("Agg")   # off-screen drawing; must be set before pyplot is first used (Streamlit runs in a worker thread)
from dataclasses import dataclass, field, asdict, replace as dc_replace
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from grid import PulliGrid
from ga import GAConfig, run_ga
from fitness import fitness, symmetry_score, loop_closure_score
from similarity import (precompute_reference_transforms, best_match, prepare_target, overlap_score,
                        genome_to_skeleton_fast, overlap_png_array)
from dataset import load_processed_dataset
from symmetry import SYMMETRY_MODES, symmetrize_chromosome

_HERE = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DIR = os.environ.get("KOLAM_PROCESSED_DIR", os.path.join(_HERE, "..", "data", "processed"))
CONFIG_PATH = os.environ.get("KOLAM_CONFIG_PATH", os.path.join(_HERE, "..", "outputs", "day12_best_config.json"))

# Used when the Day 12 config file is missing (e.g. on a fresh deployment).
FALLBACK_OPERATORS = {"crossover_method": "block", "mutation_method": "flip",
                      "tournament_size": 3, "elite_count": 2, "rate_mult": 1.0}
DEFAULT_FITNESS_KWARGS = {"symmetry_weight": 1 / 3, "loop_weight": 1 / 3, "similarity_weight": 1 / 3}
# Fast mode: rendering each pattern to compare it with the real Kolams is ~95% of the run time, and on Day 12
# the similarity term never changed which pattern won (all candidates are ~equally far from the references).
# So fast mode evolves on symmetry + loop closure only; similarity is measured once at the end.
FAST_FITNESS_KWARGS = {"symmetry_weight": 0.5, "loop_weight": 0.5, "similarity_weight": 0.0}

GRID_RANGE = (6, 16)
# "How much may the GA change my pattern?"  label -> (start_fraction, start_spread)
FREEDOM_CHOICES = {"Stay close to my pattern": (1.0, 0.02),
                   "Balanced": (0.5, 0.05),
                   "Explore freely": (0.2, 0.15)}
SYMMETRY_CHOICES = {"Mirror (left-right + top-bottom)": "mirror",
                    "Rotation (180 degrees)": "rot180",
                    "None (let the GA find it)": None}


@dataclass
class RunSettings:
    grid_n: int = 13                          # dots per side; tiles per side = grid_n - 1
    symmetry_mode: Optional[str] = "mirror"   # None | "rot180" | "mirror"
    population_size: int = 30
    generations: int = 30
    sample_size: int = 50                     # references sampled per generation
    seed: int = 0
    start_pattern: Optional[List[int]] = None   # flat 0/1 tile list (length (grid_n-1)**2) to evolve from
    start_fraction: float = 0.5                 # share of the population that starts from it
    start_spread: float = 0.05                  # how much the starting copies differ from it
    fast_mode: bool = True                      # True: skip the slow image comparison while evolving
    target_image: Optional[bytes] = None        # an uploaded picture of a Kolam to imitate (file bytes)
    target_weight: float = 0.6                  # how much matching that picture counts in the score (0-1)
    target_tolerance: Optional[float] = None    # pixels of slack when comparing lines; None = automatic (0.1 tile)


@dataclass
class EvolutionResult:
    settings: RunSettings
    genome: object                            # KolamGenome
    chromosome: List[int]
    best_fitness: float                       # full formula (symmetry, loops, similarity) vs ALL references
    symmetry: float
    loop_closure: float
    d_min: float                              # px to the closest reference (lower = more similar)
    match_name: Optional[str]                 # e.g. "kolam19/kolam19-0.jpg"
    match_skeleton: Optional[np.ndarray]      # skeleton of that reference (bool array)
    history: List[Dict] = field(default_factory=list)   # per generation: generation, best, mean, diversity
    elapsed_s: float = 0.0
    target_skeleton: Optional[np.ndarray] = None  # prepared target lines (imitation mode only)
    target_score: Optional[float] = None          # overlap F1 with the target, 0-1 (imitation mode only)
    target_baseline: Optional[float] = None       # average F1 of random patterns, for comparison


# --------------------------------------------------------------------------
# Data + settings
# --------------------------------------------------------------------------
def load_references(processed_dir: str = PROCESSED_DIR):
    """Loads the cached skeleton PNGs and precomputes distance transforms.
    Raises FileNotFoundError with a clear message when nothing is found."""
    if not os.path.isdir(processed_dir):
        raise FileNotFoundError(f"Reference folder not found: {processed_dir}")
    dataset = load_processed_dataset(processed_dir)
    if not dataset:
        raise FileNotFoundError(f"No reference skeleton PNGs found in {processed_dir}")
    return precompute_reference_transforms(dataset)


def validate_settings(s: RunSettings):
    lo, hi = GRID_RANGE
    if not (lo <= s.grid_n <= hi):
        raise ValueError(f"Grid size must be between {lo} and {hi}.")
    if s.symmetry_mode is not None and s.symmetry_mode not in SYMMETRY_MODES:
        raise ValueError(f"Unknown symmetry mode: {s.symmetry_mode!r}.")
    if s.population_size < 6:
        raise ValueError("Population must be at least 6.")
    if s.generations < 1:
        raise ValueError("Generations must be at least 1.")
    if s.sample_size < 1:
        raise ValueError("Reference sample size must be at least 1.")
    if s.target_image is not None:
        if not 0.0 < s.target_weight <= 1.0:
            raise ValueError("The picture weight must be above 0 and at most 1.")
        if s.target_tolerance is not None and s.target_tolerance < 1:
            raise ValueError("Line tolerance must be at least 1 pixel.")
    if s.start_pattern is not None:
        need = (s.grid_n - 1) ** 2
        if len(s.start_pattern) != need:
            raise ValueError(f"Your starting pattern has {len(s.start_pattern)} tiles, but a grid of "
                             f"{s.grid_n} dots needs {need} ({s.grid_n - 1} x {s.grid_n - 1}).")
        if any(g not in (0, 1) for g in s.start_pattern):
            raise ValueError("A starting pattern may only contain 0 and 1.")
        if not (0.0 <= s.start_fraction <= 1.0 and 0.0 <= s.start_spread <= 1.0):
            raise ValueError("Starting-pattern fraction and spread must be between 0 and 1.")


def _operators(config_path: str) -> Dict:
    """Operator settings tuned on Day 12, or the built-in fallback."""
    ops = dict(FALLBACK_OPERATORS)
    fitness_kwargs = dict(DEFAULT_FITNESS_KWARGS)
    try:
        with open(config_path) as f:
            ov = json.load(f).get("overrides", {})
        for k in FALLBACK_OPERATORS:
            if k in ov:
                ops[k] = ov[k]
        fitness_kwargs.update(ov.get("fitness_kwargs", {}))
    except (OSError, ValueError):
        pass
    ops["fitness_kwargs"] = fitness_kwargs
    return ops


def load_target(image_bytes: bytes, grid_n: int):
    """Uploaded picture bytes -> (skeleton, reference-transform list with one entry). Raises ValueError."""
    from PIL import Image, UnidentifiedImageError
    try:
        gray = np.array(Image.open(io.BytesIO(image_bytes)).convert("L"))
    except (UnidentifiedImageError, OSError):
        raise ValueError("Could not read the image. Please upload a PNG or JPG picture.")
    skeleton = prepare_target(gray, grid_n)
    return skeleton, precompute_reference_transforms([("uploaded image", skeleton)])


def auto_tolerance(grid_n: int, size: int = 256) -> float:
    """Pixels of slack for comparing lines: 0.1 of a tile. Measured on Day 13: with more slack the two tile types
    (whose arcs are only ~0.25 tile apart) look identical, so every pattern would score about the same."""
    return max(1.0, round(0.10 * 0.77 * size / grid_n, 1))


def _tolerance(s: RunSettings) -> float:
    return float(s.target_tolerance) if s.target_tolerance is not None else auto_tolerance(s.grid_n)


def target_fitness_kwargs(s: RunSettings) -> Dict:
    """Imitation mode: symmetry and loops share what the picture does not take; similarity = overlap with the picture."""
    rest = (1.0 - s.target_weight) / 2.0
    return {"symmetry_weight": rest, "loop_weight": rest, "similarity_weight": s.target_weight,
            "similarity_mode": "overlap", "similarity_tolerance": _tolerance(s),
            "similarity_fast_render": True}


def make_ga_config(s: RunSettings, config_path: str = CONFIG_PATH) -> GAConfig:
    """GAConfig from the user's settings + the Day 12 tuned operators.
    The mutation rate is 'rate_mult / number of tiles', as tuned on Day 12."""
    validate_settings(s)
    ops = _operators(config_path)
    n_tiles = (s.grid_n - 1) ** 2
    return GAConfig(
        population_size=s.population_size, generations=s.generations,
        elite_count=min(int(ops["elite_count"]), s.population_size - 1),
        tournament_size=int(ops["tournament_size"]),
        crossover_method=ops["crossover_method"], mutation_method=ops["mutation_method"],
        mutation_rate=float(ops["rate_mult"]) / n_tiles,
        sample_size=min(s.sample_size, 10 ** 9), seed=s.seed,
        symmetry_mode=s.symmetry_mode,
        fitness_kwargs=(target_fitness_kwargs(s) if s.target_image is not None
                        else dict(FAST_FITNESS_KWARGS) if s.fast_mode else ops["fitness_kwargs"]),
        initial_chromosome=None if s.start_pattern is None else [int(g) for g in s.start_pattern],
        initial_fraction=s.start_fraction, initial_spread=s.start_spread)


# --------------------------------------------------------------------------
# Running the GA
# --------------------------------------------------------------------------
def eta_seconds(elapsed: float, done: int, total: int) -> Optional[float]:
    """Seconds left, from the average time per finished step; None until one step is done."""
    if done <= 0 or total <= 0:
        return None
    return max(0.0, elapsed / done * (total - done))


def run_evolution(refs, settings: RunSettings,
                  on_progress: Optional[Callable[[int, int, Dict, float], None]] = None,
                  config_path: str = CONFIG_PATH) -> EvolutionResult:
    """Runs the GA and returns everything the app needs to show.

    on_progress(done_generations, total_generations, stats, elapsed_s) is called
    after every generation (generation 0 counts as done=1 of total+1)."""
    cfg = make_ga_config(settings, config_path)
    target_skeleton, ga_refs = None, refs
    if settings.target_image is not None:      # imitation: the GA compares against the uploaded picture only
        target_skeleton, ga_refs = load_target(settings.target_image, settings.grid_n)
    # keep the sample size sensible when the dataset is small
    cfg.sample_size = min(cfg.sample_size, len(ga_refs))
    total = settings.generations + 1          # generation 0 .. generations
    t0 = time.time()
    history: List[Dict] = []

    def cb(stats):
        history.append({k: stats[k] for k in ("generation", "best", "mean", "diversity")})
        if on_progress:
            on_progress(len(history), total, history[-1], time.time() - t0)

    res = run_ga(PulliGrid(n=settings.grid_n), ga_refs, cfg, callback=cb)
    g = res.best_genome
    name, d_min = best_match(g, refs)
    # one full-formula score against ALL references, so the number is comparable between modes
    final_fitness = fitness(g, refs, **_operators(config_path)["fitness_kwargs"])
    skeleton = next((sk for n, sk, _dt in refs if n == name), None)
    target_score = target_baseline = None
    if target_skeleton is not None:
        t_dt = ga_refs[0][2]
        target_score = float(overlap_score(genome_to_skeleton_fast(g), target_skeleton, t_dt, _tolerance(settings)))
        from population import Population
        rand = Population(PulliGrid(n=settings.grid_n), 20, seed=12345).initialize().genomes
        target_baseline = float(np.mean([overlap_score(genome_to_skeleton_fast(x), target_skeleton, t_dt,
                                                       _tolerance(settings)) for x in rand]))
    return EvolutionResult(
        settings=settings, genome=g, chromosome=g.to_chromosome(), best_fitness=float(final_fitness),
        symmetry=float(symmetry_score(g)), loop_closure=float(loop_closure_score(g)),
        d_min=float(d_min), match_name=name, match_skeleton=skeleton, history=history,
        elapsed_s=time.time() - t0, target_skeleton=target_skeleton, target_score=target_score,
        target_baseline=target_baseline)


def run_variants(refs, settings: RunSettings, n: int = 6,
                 on_progress: Optional[Callable[[int, int, "EvolutionResult"], None]] = None,
                 config_path: str = CONFIG_PATH) -> List["EvolutionResult"]:
    """Runs the same settings with n consecutive seeds (settings.seed, seed+1, ...) so the user can compare
    different patterns of similar quality. Fast mode only: with the slow picture comparison this would
    take far too long. on_progress(done, n, result) is called after each variant."""
    if not settings.fast_mode:
        raise ValueError("Variants need fast mode (otherwise it would take hours).")
    if not 1 <= n <= 12:
        raise ValueError("Choose between 1 and 12 variants.")
    out = []
    for i in range(n):
        out.append(run_evolution(refs, dc_replace(settings, seed=settings.seed + i), config_path=config_path))
        if on_progress:
            on_progress(i + 1, n, out[-1])
    return out


def match_png(result: "EvolutionResult") -> Optional[bytes]:
    """PNG of the closest real Kolam's skeleton (None if unknown)."""
    return skeleton_png(result.match_skeleton) if result.match_skeleton is not None else None


# --------------------------------------------------------------------------
# Starting patterns (the user's own Kolam to evolve)
# --------------------------------------------------------------------------
def pattern_to_rows(pattern: List[int], grid_n: int) -> List[List[int]]:
    """Flat tile list -> list of rows (what a table editor shows)."""
    n = grid_n - 1
    if len(pattern) != n * n:
        raise ValueError(f"Expected {n * n} tiles for grid {grid_n}, got {len(pattern)}.")
    return [[int(v) for v in pattern[i * n:(i + 1) * n]] for i in range(n)]


def rows_to_pattern(rows) -> List[int]:
    """List of rows (0/1 or False/True) -> flat tile list."""
    return [int(bool(v)) for row in rows for v in row]


def random_pattern(grid_n: int, seed: int = 0) -> List[int]:
    import random
    rng = random.Random(seed)
    return [rng.randint(0, 1) for _ in range((grid_n - 1) ** 2)]


def effective_start_pattern(pattern: List[int], grid_n: int, symmetry_mode: Optional[str]) -> List[int]:
    """The pattern the GA will really start from: with a symmetry mode on, it is rebuilt from the
    free part of the grid (top-left quarter for mirror), so it can differ from what was drawn."""
    n = grid_n - 1
    return symmetrize_chromosome(list(pattern), n, n, symmetry_mode)


# --------------------------------------------------------------------------
# Pictures
# --------------------------------------------------------------------------
def render_pattern_png(pattern: List[int], grid_n: int, show_dots: bool = False, **kw) -> bytes:
    """PNG bytes of a flat tile pattern (for previewing a starting pattern)."""
    from genome import KolamGenome
    g = KolamGenome(PulliGrid(n=grid_n))
    g.from_chromosome(list(pattern))
    return render_png(g, show_dots=show_dots, **kw)

def render_png(genome, show_dots: bool = False, size_inches: float = 5.0, dpi: int = 150) -> bytes:
    """PNG bytes of the evolved Kolam (matplotlib, off-screen)."""
    import matplotlib.pyplot as plt
    from renderer import render_genome
    fig, ax = plt.subplots(figsize=(size_inches, size_inches))
    try:
        render_genome(genome, ax=ax, show_dots=show_dots)
        ax.axis("off")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
        return buf.getvalue()
    finally:
        plt.close(fig)


def skeleton_png(skeleton: np.ndarray) -> bytes:
    """PNG bytes of a reference skeleton (dark line on white)."""
    from PIL import Image
    img = Image.fromarray(np.where(np.asarray(skeleton, dtype=bool), 0, 255).astype(np.uint8), mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def overlay_png(result: "EvolutionResult") -> Optional[bytes]:
    """PNG: the uploaded target (grey) with the evolved pattern drawn over it (red) -- imitation mode only."""
    if result.target_skeleton is None:
        return None
    from PIL import Image
    img = Image.fromarray(overlap_png_array(genome_to_skeleton_fast(result.genome), result.target_skeleton))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def result_summary(r: EvolutionResult) -> Dict:
    """Plain dict for display / JSON download (no big arrays)."""
    st = asdict(r.settings)
    st["target_image"] = r.settings.target_image is not None      # bytes are not JSON-serialisable
    return {"settings": st, "target_score": r.target_score, "target_baseline": r.target_baseline, "best_fitness": r.best_fitness, "symmetry": r.symmetry,
            "loop_closure": r.loop_closure, "d_min_px": r.d_min, "closest_reference": r.match_name,
            "seconds": round(r.elapsed_s, 1), "chromosome": r.chromosome}
