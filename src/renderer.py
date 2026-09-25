"""
kolamNet — Kolam Arc Renderer
================================
Turns a KolamGenome into an actual Kolam-style image, replacing Day 2's
straight-diagonal placeholder with proper quarter-circle arcs.

Each cell holds two quarter-circle arcs of radius = spacing/2, each centered
on one corner of the cell and connecting the midpoints of that corner's two
adjacent edges:

    ARC_A: one arc hugs the top-left corner    (top-mid -> left-mid)
           the other hugs the bottom-right corner (bottom-mid -> right-mid)
    ARC_B: one arc hugs the top-right corner   (top-mid -> right-mid)
           the other hugs the bottom-left corner  (bottom-mid -> left-mid)

Because every cell's arcs terminate exactly at its edge midpoints, and every
edge midpoint is shared with the neighboring cell, adjacent tiles' arcs
always meet up -- this is what makes the pattern chain into the continuous,
looping curves characteristic of real Kolams, instead of a disconnected
pile of quarter-circles.
"""

import os
import random
import matplotlib.pyplot as plt
from matplotlib.patches import Arc

from grid import PulliGrid
from genome import KolamGenome, TileType

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _cell_arcs(tl, tr, bl, br, tile: TileType):
    """Returns [(center, theta1, theta2), (center, theta1, theta2)] -- the
    two quarter-circle arcs for one cell, given its 4 corner coordinates."""
    if tile == TileType.ARC_A:
        return [
            (tl, 0, 90),     # top-mid -> left-mid, hugging the top-left corner
            (br, 180, 270),  # bottom-mid -> right-mid, hugging the bottom-right corner
        ]
    else:  # ARC_B
        return [
            (tr, 90, 180),   # top-mid -> right-mid, hugging the top-right corner
            (bl, 270, 360),  # bottom-mid -> left-mid, hugging the bottom-left corner
        ]


def render_genome(genome: KolamGenome, ax=None, show_dots: bool = True,
                   line_color: str = "#8B2E2E", line_width: float = 2.2,
                   dot_color: str = "#cccccc"):
    """Draws a KolamGenome as proper curved arcs on a matplotlib Axes.
    Returns the Axes used, so callers can further customize or save it."""
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))

    if show_dots:
        xs = [p[0] for p in genome.grid.points]
        ys = [p[1] for p in genome.grid.points]
        ax.scatter(xs, ys, s=15, color=dot_color, zorder=1)

    for i in range(genome.rows):
        for j in range(genome.cols):
            tl, tr, bl, br = genome.cell_corners(i, j)
            side = tr[0] - tl[0]  # cell side length (square cells assumed)
            tile = genome.get_tile(i, j)
            for center, theta1, theta2 in _cell_arcs(tl, tr, bl, br, tile):
                arc = Arc(center, width=side, height=side, angle=0,
                          theta1=theta1, theta2=theta2,
                          color=line_color, linewidth=line_width, zorder=2)
                ax.add_patch(arc)

    # Set limits explicitly (rather than relying on autoscale) so rendering
    # works correctly even if show_dots=False and no scatter data exists.
    min_x, min_y, max_x, max_y = genome.grid.bounding_box()
    pad = genome.grid.spacing * 0.5
    ax.set_xlim(min_x - pad, max_x + pad)
    ax.set_ylim(min_y - pad, max_y + pad)

    ax.set_aspect("equal")
    ax.invert_yaxis()  # row 0 at top, matches grid indexing (see visualize_genome.py)
    ax.axis("off")
    return ax


if __name__ == "__main__":
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))

    g = PulliGrid(n=6, grid_type="square")

    genome_a = KolamGenome(g)
    genome_a.randomize(random.Random(1))
    render_genome(genome_a, ax=axes[0])
    axes[0].set_title("Rendered Kolam (seed=1)")

    genome_b = KolamGenome(g)
    genome_b.randomize(random.Random(7))
    render_genome(genome_b, ax=axes[1])
    axes[1].set_title("Rendered Kolam (seed=7)")

    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, "day3_render_comparison.png")
    plt.savefig(save_path, dpi=150)
    print("Saved to:", os.path.abspath(save_path))
