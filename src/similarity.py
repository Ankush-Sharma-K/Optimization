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


def distances_to_refs(genome_skeleton: np.ndarray, reference_transforms: ReferenceTransforms) -> np.ndarray:
    """Chamfer distance from one rendered genome skeleton to EVERY reference
    (one value per reference, in the order of `reference_transforms`)."""
    if genome_skeleton.sum() == 0:
        return np.full(len(reference_transforms), 1e6)
    genome_dt = distance_transform_edt(~genome_skeleton)
    return np.array([
        _chamfer_distance(genome_skeleton, genome_dt, ref_skeleton, ref_dt)
        for _name, ref_skeleton, ref_dt in reference_transforms
    ])


def _knn_mean(distances: np.ndarray, k: int) -> np.ndarray:
    """Mean of the k smallest distances along the last axis (k=1 -> plain minimum)."""
    k = max(1, min(int(k), distances.shape[-1]))
    return np.sort(distances, axis=-1)[..., :k].mean(axis=-1)


def similarity_distance(genome: KolamGenome, reference_transforms: ReferenceTransforms,
                         size: int = IMAGE_SIZE, k: int = 1) -> float:
    """Raw distance in pixels (lower = more similar): the mean of the k
    nearest references' Chamfer distances. k=1 is the original best-match
    distance; k>1 is smoother because it does not hinge on one reference."""
    d = distances_to_refs(genome_to_skeleton(genome, size=size), reference_transforms)
    return float(_knn_mean(d, k))


def distance_matrix(genomes, reference_transforms: ReferenceTransforms,
                    size: int = IMAGE_SIZE) -> np.ndarray:
    """(n_genomes, n_refs) matrix of Chamfer distances. Each genome is
    rendered only once, which makes diagnostics and calibration cheap."""
    return np.array([distances_to_refs(genome_to_skeleton(g, size=size), reference_transforms)
                     for g in genomes])


def calibrate_similarity(grid, reference_transforms: ReferenceTransforms, k: int = 1,
                          n_genomes: int = 30, sample_size=None, n_subsets: int = 5,
                          seed: int = 0, size: int = IMAGE_SIZE) -> dict:
    """Measures how random genomes on `grid` are spread in distance, so the
    score can be re-centred and re-scaled to that spread.

    Why: exp(-d/scale) with a fixed scale makes the score nearly constant when
    all genomes have almost the same distance (Day 12 finding: ~0.74 for every
    run), so selection cannot see differences. The returned {"mu", "sigma", "k"}
    is used by similarity_score(calibration=...) to map distance to a logistic
    score that is 0.5 at the average random genome and moves by about one
    "standard random spread" per unit of sigma.

    sample_size: pass the GA's per-generation reference sample size so the
    calibration matches what the GA actually sees (a min over fewer references
    is larger than a min over all of them).
    """
    import random as _random
    from population import Population
    pop = Population(grid, n_genomes, seed=seed).initialize()
    D = distance_matrix(pop.genomes, reference_transforms, size=size)
    R = D.shape[1]
    if sample_size is None or sample_size >= R:
        d = _knn_mean(D, k)
        mu, sigma = float(d.mean()), float(d.std())
    else:
        rng = _random.Random(seed)
        mus, sigmas = [], []
        for _ in range(n_subsets):
            idx = rng.sample(range(R), sample_size)
            d = _knn_mean(D[:, idx], k)
            mus.append(d.mean())
            sigmas.append(d.std())   # within-subset spread: that is what selection sees
        mu, sigma = float(np.mean(mus)), float(np.mean(sigmas))
    return {"mu": mu, "sigma": max(sigma, 1e-3), "k": int(k)}


def similarity_score(genome: KolamGenome, reference_transforms: ReferenceTransforms,
                      size: int = IMAGE_SIZE, scale: float = 20.0,
                      k: int = 1, calibration=None) -> float:
    """Renders + preprocesses the genome, compares it against every
    precomputed reference (via precompute_reference_transforms) using
    Chamfer distance, and maps the distance to a [0, 1] score.

    Default (k=1, calibration=None) is the original behaviour:
    exp(-best_distance / scale). With `calibration` (from
    calibrate_similarity) the score is logistic around the random-genome
    average distance, which keeps differences between genomes visible.
    `k` averages the k nearest references instead of using only the best one.
    """
    d = similarity_distance(genome, reference_transforms, size=size, k=k)
    if calibration is None:
        return float(np.exp(-d / scale))
    z = (d - calibration["mu"]) / calibration["sigma"]
    return float(1.0 / (1.0 + np.exp(np.clip(z, -50.0, 50.0))))


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