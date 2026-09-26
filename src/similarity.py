"""
kolamNet — Similarity Fitness (Day 7)
========================================
Compares a rendered genome against the reference dataset, so genomes can be
rewarded for actually resembling real Kolams -- not just for being
symmetric/closed (Day 5's structural scores don't know what a real Kolam
looks like at all).

Pipeline: render the genome (renderer.py) -> preprocess it through the
*exact same* resize->threshold->skeletonize pipeline as the dataset
(dataset.py, Day 6) -> compare the resulting skeleton against every dataset
skeleton using Chamfer distance -> take the best (nearest-neighbor) match.

Chamfer distance is used instead of raw pixel overlap because two skeletons
of the "same" shape are very unlikely to align pixel-for-pixel (slightly
different curve position/scale/orientation) -- Chamfer distance measures
how far each curve pixel in one image is from the *nearest* curve pixel in
the other, which tolerates that kind of small misalignment.

The *best* match (not the average) is used deliberately: the goal is
resembling at least one real Kolam well, not looking like a blurry average
of all of them.

PERFORMANCE NOTE: a reference image's distance transform never changes
across genome evaluations, only the genome side does. So the reference
side is precomputed ONCE (precompute_reference_transforms, call it right
after load_processed_dataset) and reused for every genome afterward --
computing it fresh per-genome (an earlier version of this file did this)
made a single genome's score take ~8.5s against 600 references; with
precomputation it's ~15ms.
"""

import io
from typing import List, Tuple

import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import distance_transform_edt
from PIL import Image

from genome import KolamGenome
from renderer import render_genome
from dataset import preprocess_image, IMAGE_SIZE

ReferenceTransforms = List[Tuple[str, np.ndarray, np.ndarray]]  # (name, skeleton, distance_transform)


def genome_to_skeleton(genome: KolamGenome, size: int = IMAGE_SIZE) -> np.ndarray:
    """Renders a genome and pushes it through the same preprocessing
    pipeline dataset images go through (dataset.preprocess_image), so both
    sides of the similarity comparison are on equal footing. Rendered
    in-memory (no disk I/O) since this gets called for every genome, every
    generation, once the GA loop (Day 11) is running."""
    fig, ax = plt.subplots(figsize=(4, 4))
    render_genome(genome, ax=ax, show_dots=False)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    gray = np.array(Image.open(buf).convert("L"))
    return preprocess_image(gray, size=size)


def precompute_reference_transforms(dataset: List[Tuple[str, np.ndarray]]) -> ReferenceTransforms:
    """Precomputes each dataset skeleton's distance transform once. Call
    this ONCE at the start of a GA run (right after load_processed_dataset),
    never per-genome -- this is the fix for the performance note above."""
    return [(name, skeleton, distance_transform_edt(~skeleton)) for name, skeleton in dataset]


def _chamfer_distance(genome_skeleton: np.ndarray, genome_dt: np.ndarray,
                       ref_skeleton: np.ndarray, ref_dt: np.ndarray) -> float:
    """Symmetric Chamfer distance using precomputed distance transforms for
    both sides. Returns a large fallback value if either skeleton is empty.

    Uses max(d_ab, d_ba) rather than their average. This was a deliberate
    fix made during Day 7 testing: with the *average*, a very dense
    reference image (a fractal covering a large fraction of the canvas)
    could win a "best match" purely because genome pixels are trivially
    close to SOME reference pixel (d_ab collapses), even while the reverse
    direction (d_ba: reference pixels needing to be near the much sparser
    genome curve) is actually worse than a real match would be. Taking the
    max forces both directions to be genuinely close before a match scores
    well, removing that density bias.
    """
    if genome_skeleton.sum() == 0 or ref_skeleton.sum() == 0:
        return 1e6
    d_ab = ref_dt[genome_skeleton].mean()
    d_ba = genome_dt[ref_skeleton].mean()
    return max(d_ab, d_ba)


def similarity_score(genome: KolamGenome, reference_transforms: ReferenceTransforms,
                      size: int = IMAGE_SIZE, scale: float = 20.0) -> float:
    """Renders + preprocesses the genome, compares it against every
    precomputed reference (via precompute_reference_transforms) using
    Chamfer distance, and returns the best match mapped to a [0, 1] score
    via exp(-distance / scale).

    `scale` controls how quickly the score falls off with distance (in
    pixels, on the `size` x `size` canvas) -- this is a starting value,
    expected to be retuned once real runs (Day 12) show what a
    "meaningfully similar" distance actually looks like in practice.
    """
    genome_skeleton = genome_to_skeleton(genome, size=size)
    if genome_skeleton.sum() == 0:
        return 0.0
    genome_dt = distance_transform_edt(~genome_skeleton)

    best_distance = min(
        _chamfer_distance(genome_skeleton, genome_dt, ref_skeleton, ref_dt)
        for _name, ref_skeleton, ref_dt in reference_transforms
    )
    return float(np.exp(-best_distance / scale))


def best_match(genome: KolamGenome, reference_transforms: ReferenceTransforms,
                size: int = IMAGE_SIZE) -> Tuple[str, float]:
    """Like similarity_score, but also returns *which* dataset entry was the
    best match -- useful for visual sanity checks (Day 7) and later for
    showing the user 'closest real Kolam' in the app (Day 13)."""
    genome_skeleton = genome_to_skeleton(genome, size=size)
    genome_dt = distance_transform_edt(~genome_skeleton)

    distances = [
        (name, _chamfer_distance(genome_skeleton, genome_dt, ref_skeleton, ref_dt))
        for name, ref_skeleton, ref_dt in reference_transforms
    ]
    name, distance = min(distances, key=lambda pair: pair[1])
    return name, distance


if __name__ == "__main__":
    import random
    import time
    from grid import PulliGrid
    from dataset import load_processed_dataset

    g = PulliGrid(n=6, grid_type="square")
    genome = KolamGenome(g)
    genome.randomize(random.Random(1))

    dataset = load_processed_dataset("./data/processed")
    print(f"Loaded {len(dataset)} cached reference skeletons")

    t0 = time.time()
    reference_transforms = precompute_reference_transforms(dataset)
    t1 = time.time()
    print(f"Precomputed reference transforms in {t1-t0:.2f}s (one-time cost)")

    score = similarity_score(genome, reference_transforms)
    name, dist = best_match(genome, reference_transforms)
    t2 = time.time()
    print(f"similarity_score: {score:.4f}")
    print(f"best match: {name}  (chamfer distance={dist:.2f})")
    print(f"Per-genome scoring time: {t2-t1:.3f}s")