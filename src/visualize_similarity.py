"""
Day 7 sanity check -- renders a genome, finds its best-matching real Kolam
via similarity_score/best_match, and shows them side by side to visually
confirm the Chamfer-distance metric is picking a sensible match (not a
random one).
"""
import os
import random
import matplotlib.pyplot as plt

from grid import PulliGrid
from genome import KolamGenome
from renderer import render_genome
from dataset import load_processed_dataset, load_image_grayscale
from similarity import precompute_reference_transforms, similarity_score, best_match

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "processed")

if __name__ == "__main__":
    g = PulliGrid(n=6, grid_type="square")
    genome = KolamGenome(g)
    genome.randomize(random.Random(1))

    dataset = load_processed_dataset(PROCESSED_DIR)
    reference_transforms = precompute_reference_transforms(dataset)

    score = similarity_score(genome, reference_transforms)
    match_name, distance = best_match(genome, reference_transforms)

    # load the original (unprocessed) real image for a fair visual comparison
    real_path = os.path.join(RAW_DIR, os.path.splitext(match_name)[0] + ".jpg")
    real_image = load_image_grayscale(real_path)

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    render_genome(genome, ax=axes[0])
    axes[0].set_title(f"Genome (seed=1)\nsimilarity={score:.3f}")

    axes[1].imshow(real_image, cmap="gray")
    axes[1].set_title(f"Best match:\n{match_name} (dist={distance:.2f})")
    axes[1].axis("off")

    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, "day7_similarity_best_match.png")
    plt.savefig(save_path, dpi=150)
    print("Saved to:", os.path.abspath(save_path))
