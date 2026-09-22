"""
Quick sanity-check renderer for PulliGrid.
Not the final Kolam renderer (that's Day 3) — just confirms the dot
placement and symmetry math look right before we build genomes on top.
"""
import matplotlib.pyplot as plt
from grid import PulliGrid
import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def plot_grid(grid: PulliGrid, ax, title: str):
    xs = [p[0] for p in grid.points]
    ys = [p[1] for p in grid.points]
    ax.scatter(xs, ys, s=40, color="#8B2E2E")
    cx, cy = grid.center
    ax.scatter([cx], [cy], s=80, color="#2E4E8B", marker="x")
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.axis("off")


if __name__ == "__main__":
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    g_sq = PulliGrid(n=6, grid_type="square")
    g_di = PulliGrid(n=6, grid_type="diamond")

    plot_grid(g_sq, axes[0], "Square grid (n=6)")
    plot_grid(g_di, axes[1], "Diamond grid (n=6)")

    plt.tight_layout()

    plt.savefig(os.path.join(OUTPUT_DIR, "day1_grid_sanity_check.png"), dpi=150)
    print("Saved outputs/day1_grid_sanity_check.png")
