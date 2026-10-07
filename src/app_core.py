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
from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from grid import PulliGrid
from ga import GAConfig, run_ga
from fitness import symmetry_score, loop_closure_score
from similarity import precompute_reference_transforms, best_match
from dataset import load_processed_dataset
from symmetry import SYMMETRY_MODES

_HERE = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DIR = os.environ.get("KOLAM_PROCESSED_DIR", os.path.join(_HERE, "..", "data", "processed"))
CONFIG_PATH = os.environ.get("KOLAM_CONFIG_PATH", os.path.join(_HERE, "..", "outputs", "day12_best_config.json"))

# Used when the Day 12 config file is missing (e.g. on a fresh deployment).
FALLBACK_OPERATORS = {"crossover_method": "block", "mutation_method": "flip",
                      "tournament_size": 3, "elite_count": 2, "rate_mult": 1.0}
DEFAULT_FITNESS_KWARGS = {"symmetry_weight": 1 / 3, "loop_weight": 1 / 3, "similarity_weight": 1 / 3}

GRID_RANGE = (6, 16)
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


@dataclass
class EvolutionResult:
    settings: RunSettings
    genome: object                            # KolamGenome
    chromosome: List[int]
    best_fitness: float                       # vs ALL references
    symmetry: float
    loop_closure: float
    d_min: float                              # px to the closest reference (lower = more similar)
    match_name: Optional[str]                 # e.g. "kolam19/kolam19-0.jpg"
    match_skeleton: Optional[np.ndarray]      # skeleton of that reference (bool array)
    history: List[Dict] = field(default_factory=list)   # per generation: generation, best, mean, diversity
    elapsed_s: float = 0.0


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
        symmetry_mode=s.symmetry_mode, fitness_kwargs=ops["fitness_kwargs"])


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
    # keep the sample size sensible when the dataset is small
    cfg.sample_size = min(cfg.sample_size, len(refs))
    total = settings.generations + 1          # generation 0 .. generations
    t0 = time.time()
    history: List[Dict] = []

    def cb(stats):
        history.append({k: stats[k] for k in ("generation", "best", "mean", "diversity")})
        if on_progress:
            on_progress(len(history), total, history[-1], time.time() - t0)

    res = run_ga(PulliGrid(n=settings.grid_n), refs, cfg, callback=cb)
    g = res.best_genome
    name, d_min = best_match(g, refs)
    skeleton = next((sk for n, sk, _dt in refs if n == name), None)
    return EvolutionResult(
        settings=settings, genome=g, chromosome=g.to_chromosome(), best_fitness=float(res.best_fitness),
        symmetry=float(symmetry_score(g)), loop_closure=float(loop_closure_score(g)),
        d_min=float(d_min), match_name=name, match_skeleton=skeleton, history=history,
        elapsed_s=time.time() - t0)


# --------------------------------------------------------------------------
# Pictures
# --------------------------------------------------------------------------
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


def result_summary(r: EvolutionResult) -> Dict:
    """Plain dict for display / JSON download (no big arrays)."""
    return {"settings": asdict(r.settings), "best_fitness": r.best_fitness, "symmetry": r.symmetry,
            "loop_closure": r.loop_closure, "d_min_px": r.d_min, "closest_reference": r.match_name,
            "seconds": round(r.elapsed_s, 1), "chromosome": r.chromosome}
