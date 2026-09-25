"""
Day 4 sanity check -- renders a handful of genomes from a Population side
by side using Day 3's renderer, to visually confirm the population is
actually diverse (not accidentally generating near-identical patterns).
"""
import os
import matplotlib.pyplot as plt

from grid import PulliGrid
from population import Population, validate_genome
from renderer import render_genome

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

if __name__ == "__main__":
    g = PulliGrid(n=6, grid_type="square")
    pop = Population(grid=g, size=6, seed=42).initialize()

    assert all(validate_genome(gen) for gen in pop), "invalid genome in population"

    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    for genome, ax in zip(pop, axes.flat):
        render_genome(genome, ax=ax, line_width=1.6)

    fig.suptitle(f"Population preview (size={pop.size}, seed=42)")
    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, "day4_population_preview.png")
    plt.savefig(save_path, dpi=150)
    print("Saved to:", os.path.abspath(save_path))
