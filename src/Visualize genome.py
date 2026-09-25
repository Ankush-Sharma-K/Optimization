"""
Day 2 sanity check — NOT the final Kolam renderer (that's Day 3).

This just draws a straight diagonal line per tile (instead of the curved
arcs) so we can visually confirm each gene in the chromosome maps onto the
correct cell of the grid, with correct orientation. Getting this mapping
right now means Day 3's arc renderer is a much smaller step.
"""
import os
import random
import matplotlib.pyplot as plt

from grid import PulliGrid
from genome import KolamGenome, TileType

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def plot_genome_preview(genome: KolamGenome, ax, title: str):
    # plot the underlying dots, faint
    xs = [p[0] for p in genome.grid.points]
    ys = [p[1] for p in genome.grid.points]
    ax.scatter(xs, ys, s=15, color="#cccccc", zorder=1)

    for i in range(genome.rows):
        for j in range(genome.cols):
            tl, tr, bl, br = genome.cell_corners(i, j)
            tile = genome.get_tile(i, j)
            if tile == TileType.ARC_A:
                x_vals, y_vals = [tl[0], br[0]], [tl[1], br[1]]
            else:
                x_vals, y_vals = [tr[0], bl[0]], [tr[1], bl[1]]
            ax.plot(x_vals, y_vals, color="#8B2E2E", linewidth=2, zorder=2)

    ax.set_title(title)
    ax.set_aspect("equal")
    ax.invert_yaxis()  # row 0 at top, matches grid indexing
    ax.axis("off")


if __name__ == "__main__":
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    g = PulliGrid(n=6, grid_type="square")

    genome_a = KolamGenome(g)
    genome_a.randomize(random.Random(1))
    plot_genome_preview(genome_a, axes[0], "Random genome (seed=1)")

    genome_b = KolamGenome(g)
    genome_b.randomize(random.Random(7))
    plot_genome_preview(genome_b, axes[1], "Random genome (seed=7)")

    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, "day2_genome_sanity_check.png")
    plt.savefig(save_path, dpi=150)
    print("Saved to:", os.path.abspath(save_path))