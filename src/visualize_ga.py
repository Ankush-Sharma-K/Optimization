"""Sanity check for Day 11 GA loop (not core pipeline).

Runs a small GA against the real cached dataset, then plots best/mean/worst
fitness per generation, population diversity, and the best genome of generation
0 vs the final best. Run from src/:  python visualize_ga.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from grid import PulliGrid
from dataset import load_processed_dataset
from similarity import precompute_reference_transforms
from renderer import render_genome
from ga import run_ga, GAConfig, _genome_from_chromosome

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_HERE, "..", "outputs")
PROCESSED_DIR = os.path.join(_HERE, "..", "data", "processed")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    grid = PulliGrid(n=6, grid_type="square")
    ref = precompute_reference_transforms(load_processed_dataset(PROCESSED_DIR))

    cfg = GAConfig(population_size=30, generations=30, sample_size=100, seed=0)
    result = run_ga(grid, ref, cfg, callback=lambda s: print(
        f"gen {s['generation']:3d}  best {s['best']:.3f}  mean {s['mean']:.3f}  diversity {s['diversity']:.2f}"))
    print(f"done in {result.elapsed_s:.1f}s -- final best fitness (all references): {result.best_fitness:.3f}")

    h = result.history
    gens = [s["generation"] for s in h]
    fig = plt.figure(figsize=(12, 7))
    ax = fig.add_subplot(2, 2, 1)
    ax.plot(gens, [s["best"] for s in h], label="best")
    ax.plot(gens, [s["mean"] for s in h], label="mean")
    ax.plot(gens, [s["worst"] for s in h], label="worst")
    ax.set_xlabel("generation"); ax.set_ylabel("fitness (sampled refs)"); ax.legend()
    ax.set_title("Fitness per generation")
    ax = fig.add_subplot(2, 2, 2)
    ax.plot(gens, [s["diversity"] for s in h], color="#8B2E2E")
    ax.set_ylim(0, 1.05); ax.set_xlabel("generation"); ax.set_ylabel("unique chromosomes / size")
    ax.set_title("Population diversity")
    for k, (chrom, title) in enumerate([(h[0]["best_chromosome"], "best of generation 0"),
                                        (result.best_chromosome, f"final best ({result.best_fitness:.3f})")]):
        a = fig.add_subplot(2, 4, 5 + 2 * k)
        render_genome(_genome_from_chromosome(grid, chrom), ax=a, show_dots=False)
        a.set_title(title, fontsize=9); a.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "day11_ga_run.png"), dpi=120)
    print("saved day11_ga_run.png")
