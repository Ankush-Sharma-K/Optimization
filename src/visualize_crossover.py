"""Sanity check for Day 9 crossover (not core pipeline).

For each method, shows parent 1, parent 2 and the two children rendered as
Kolam curves. Run from src/:  python visualize_crossover.py
"""
import os
import random
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from grid import PulliGrid
from genome import KolamGenome
from renderer import render_genome
from crossover import crossover, CROSSOVER_METHODS

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")


def _genome(grid, chromosome):
    g = KolamGenome(grid)
    g.from_chromosome(chromosome)
    return g


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    grid = PulliGrid(n=6, grid_type="square")
    rng = random.Random(3)
    g1, g2 = KolamGenome(grid), KolamGenome(grid)
    g1.randomize(random.Random(1)); g2.randomize(random.Random(7))
    p1, p2 = g1.to_chromosome(), g2.to_chromosome()

    fig, axes = plt.subplots(len(CROSSOVER_METHODS), 4, figsize=(13, 3.3 * len(CROSSOVER_METHODS)))
    for row, method in enumerate(CROSSOVER_METHODS):
        c1, c2 = crossover(p1, p2, method, crossover_rate=1.0, rng=rng)
        for col, (ch, title) in enumerate([(p1, "parent 1"), (p2, "parent 2"), (c1, "child 1"), (c2, "child 2")]):
            ax = axes[row][col]
            render_genome(_genome(grid, ch), ax=ax, show_dots=False)
            ax.set_title(f"{method}: {title}" if col == 0 else title, fontsize=9)
            ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "day9_crossover_comparison.png"), dpi=120)
    print("saved day9_crossover_comparison.png")
