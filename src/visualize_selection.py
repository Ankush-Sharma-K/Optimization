"""Sanity check for Day 8 selection (not core pipeline).

Scores a real population with the full 3-term fitness, then shows how each
selection method / tournament size shifts the average fitness of the chosen
parents, and renders the top-ranked genomes. Run from src/:  python visualize_selection.py
"""
import os
import random
import statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from grid import PulliGrid
from population import Population
from renderer import render_genome
from dataset import load_processed_dataset
from similarity import precompute_reference_transforms
from selection import select_indices, elite_indices, evaluate_population

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
PROCESSED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "processed")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ref = precompute_reference_transforms(load_processed_dataset(PROCESSED_DIR))
    pop = Population(PulliGrid(n=6, grid_type="square"), size=20, seed=0).initialize()
    fit = evaluate_population(pop, ref)
    print(f"population mean {st.mean(fit):.3f}  best {max(fit):.3f}  worst {min(fit):.3f}")

    configs = [("tournament", 2), ("tournament", 3), ("tournament", 5), ("roulette", 0), ("rank", 0)]
    labels, means = [], []
    for method, k in configs:
        idx = select_indices(fit, 5000, method, tournament_size=max(k, 1), rng=random.Random(1))
        labels.append(f"{method}\nk={k}" if method == "tournament" else method)
        means.append(st.mean(fit[i] for i in idx))
        print(f"{method:10s} k={k}: mean fitness of selected parents = {means[-1]:.4f}")

    top = elite_indices(fit, 3)
    fig = plt.figure(figsize=(12, 7))
    ax = fig.add_subplot(2, 1, 1)
    ax.bar(labels, means, color="#8B2E2E")
    ax.axhline(st.mean(fit), color="k", ls="--", label="population mean")
    ax.set_ylim(min(fit), max(fit)); ax.set_ylabel("mean fitness of parents"); ax.legend()
    ax.set_title("Selection pressure by method")
    for r, i in enumerate(top):
        a = fig.add_subplot(2, 3, 4 + r)
        render_genome(pop[i], ax=a, show_dots=False)
        a.set_title(f"rank {r+1}: fitness {fit[i]:.3f}"); a.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "day8_selection_pressure.png"), dpi=130)
    print("saved day8_selection_pressure.png")
