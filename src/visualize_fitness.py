"""
Day 5 sanity check -- scores every genome in a population and renders the
best vs. worst scoring one side by side, to confirm the fitness function
is actually discriminating between genomes (not returning near-identical
scores for everything).
"""
import os
import matplotlib.pyplot as plt

from grid import PulliGrid
from population import Population
from fitness import fitness, symmetry_score, loop_closure_score
from renderer import render_genome

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

if __name__ == "__main__":
    g = PulliGrid(n=6, grid_type="square")
    pop = Population(grid=g, size=20, seed=42).initialize()

    scored = [(genome, fitness(genome)) for genome in pop]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    print("Fitness scores (sorted, best first):")
    for idx, (genome, score) in enumerate(scored):
        print(f"  #{idx:02d}  fitness={score:.3f}  "
              f"symmetry={symmetry_score(genome):.3f}  "
              f"loop_closure={loop_closure_score(genome):.3f}")

    best_genome, best_score = scored[0]
    worst_genome, worst_score = scored[-1]

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))
    render_genome(best_genome, ax=axes[0])
    axes[0].set_title(f"Best (fitness={best_score:.3f})")
    render_genome(worst_genome, ax=axes[1])
    axes[1].set_title(f"Worst (fitness={worst_score:.3f})")

    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, "day5_fitness_best_vs_worst.png")
    plt.savefig(save_path, dpi=150)
    print("\nSaved to:", os.path.abspath(save_path))
