"""Sanity check for Day 10 mutation (not core pipeline).

Row 1: one parent genome and mutants at increasing flip rates.
Row 2: one mutant per method (flip / block_flip / symmetric_flip), with the
changed cells listed in the title. Run from src/:  python visualize_mutation.py
"""
import os
import random
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from grid import PulliGrid
from genome import KolamGenome
from renderer import render_genome
from mutation import mutate, MUTATION_METHODS

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")


def _genome(grid, chromosome):
    g = KolamGenome(grid)
    g.from_chromosome(chromosome)
    return g


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    grid = PulliGrid(n=6, grid_type="square")
    rng = random.Random(4)
    g = KolamGenome(grid)
    g.randomize(random.Random(1))
    parent = g.to_chromosome()

    fig, axes = plt.subplots(2, 4, figsize=(13, 6.8))
    panels = [(parent, "parent")] + [
        (mutate(parent, r, "flip", rng), f"flip, rate={r}") for r in (0.04, 0.15, 0.4)
    ]
    for ax, (ch, title) in zip(axes[0], panels):
        render_genome(_genome(grid, ch), ax=ax, show_dots=False)
        ax.set_title(title + ("" if title == "parent" else f"  ({sum(a != b for a, b in zip(parent, ch))} changed)"), fontsize=9)
        ax.axis("off")
    for ax, method in zip(axes[1], MUTATION_METHODS):
        ch = mutate(parent, 0.15, method, rng)
        render_genome(_genome(grid, ch), ax=ax, show_dots=False)
        ax.set_title(f"{method}, rate=0.15  ({sum(a != b for a, b in zip(parent, ch))} changed)", fontsize=9)
        ax.axis("off")
    axes[1][3].axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "day10_mutation_comparison.png"), dpi=120)
    print("saved day10_mutation_comparison.png")
