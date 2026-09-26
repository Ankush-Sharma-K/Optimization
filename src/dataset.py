"""
kolamNet — Dataset Preprocessing
===================================
Prepares your reference Kolam images so Day 7's similarity fitness can
compare a rendered genome against real patterns on equal footing.

Pipeline per image:
  load (grayscale) -> resize to a fixed canvas -> threshold (binary) ->
  skeletonize (reduce the curve to a 1-pixel-wide skeleton)

Skeletonizing matters because Kolam curves in photographs/scans vary in
line thickness, but the underlying *shape* of the loops is what should be
compared -- not how thick someone's chalk line was. Rendered genomes (via
renderer.py) will go through this same resize+threshold+skeletonize
pipeline in Day 7, so both sides of the similarity comparison are on equal
footing.
"""

import os
from typing import List, Tuple

import numpy as np
from PIL import Image
from skimage.filters import threshold_otsu
from skimage.morphology import skeletonize

IMAGE_SIZE = 256  # fixed canvas both dataset images and rendered genomes resize to


def load_image_grayscale(path: str) -> np.ndarray:
    """Loads any image file as a grayscale numpy array (0-255)."""
    img = Image.open(path).convert("L")
    return np.array(img)


def preprocess_image(image: np.ndarray, size: int = IMAGE_SIZE) -> np.ndarray:
    """Resize -> threshold -> skeletonize. Returns a boolean 2D array
    (True = curve pixel), size x size."""
    img = Image.fromarray(image).resize((size, size), Image.LANCZOS)
    arr = np.array(img).astype(np.float64) / 255.0

    # Otsu's method picks a threshold automatically rather than a fixed
    # cutoff, since scans/photos of real Kolams vary a lot in
    # brightness/contrast.
    try:
        thresh = threshold_otsu(arr)
    except ValueError:
        # Happens if the image is blank/uniform -- fall back to a fixed cutoff.
        thresh = 0.5

    # Assumption: curve = darker pixels than the background (dark ink/lines
    # on a lighter surface). Revisit this if real dataset images turn out
    # to be the opposite (e.g. white chalk on a dark floor) -- Day 12 tuning.
    binary = arr < thresh

    skeleton = skeletonize(binary)
    return skeleton


def load_dataset(data_dir: str, size: int = IMAGE_SIZE,
                  extensions: Tuple[str, ...] = (".png", ".jpg", ".jpeg", ".bmp")
                  ) -> List[Tuple[str, np.ndarray]]:
    """Loads every image under data_dir -- including subfolders (e.g. a
    data/raw/kolam19/, data/raw/kolam29/, data/raw/kolam109/ layout, one
    subfolder per Kolam design) -- preprocesses each one, and returns a
    list of (relative_path, skeleton) pairs. relative_path includes the
    subfolder (e.g. "kolam19/kolam19-0.jpg") so callers can still tell
    which design each skeleton came from if that ever matters later.

    Call this once at the start of a GA run (Day 7 / Day 11) rather than
    per-generation -- preprocessing is the slow part; scoring similarity
    against an already-preprocessed skeleton is cheap.
    """
    paths = []
    for root, _dirs, files in os.walk(data_dir):
        for fname in files:
            if fname.lower().endswith(extensions):
                paths.append(os.path.join(root, fname))
    paths.sort()

    dataset = []
    for path in paths:
        gray = load_image_grayscale(path)
        skeleton = preprocess_image(gray, size=size)
        rel_name = os.path.relpath(path, data_dir)
        dataset.append((rel_name, skeleton))
    return dataset


# -- Caching preprocessed output -----------------------------------------
# Your dataset layout (as provided):
#   data/raw/kolam19/*.jpg   (400 images)
#   data/raw/kolam29/*.jpg   (100 images)
#   data/raw/kolam109/*.jpg  (100 images)
# Preprocessing 600 images is the slow part of this pipeline, so
# save_processed_dataset() caches every skeleton to data/processed/ once,
# mirroring the raw/ subfolder structure. Later runs (Day 7 onward) should
# call load_processed_dataset() instead of re-running load_dataset() from
# scratch on the raw images.

def save_processed_dataset(dataset: List[Tuple[str, np.ndarray]], processed_root: str):
    """Saves each (relative_path, skeleton) pair from load_dataset() as a
    PNG under processed_root, preserving the same subfolder structure
    (e.g. kolam19/kolam19-0.jpg -> processed_root/kolam19/kolam19-0.png)."""
    os.makedirs(processed_root, exist_ok=True)
    for rel_name, skeleton in dataset:
        out_path = os.path.join(processed_root, os.path.splitext(rel_name)[0] + ".png")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        # skeleton is boolean (True = curve) -> save as a standard 0/255 PNG
        Image.fromarray((skeleton * 255).astype(np.uint8)).save(out_path)


def load_processed_dataset(processed_root: str) -> List[Tuple[str, np.ndarray]]:
    """Loads already-cached skeletons back from processed_root (produced by
    save_processed_dataset), skipping threshold+skeletonize entirely. Use
    this in Day 7 / Day 11 once the cache exists, instead of load_dataset()
    on the raw images."""
    dataset = []
    for root, _dirs, files in os.walk(processed_root):
        for fname in sorted(files):
            if fname.lower().endswith(".png"):
                path = os.path.join(root, fname)
                arr = np.array(Image.open(path).convert("L"))
                skeleton = arr > 127
                rel_name = os.path.relpath(path, processed_root)
                dataset.append((rel_name, skeleton))
    return dataset


if __name__ == "__main__":
    # If a real dataset exists at data/raw, use it (and cache the result to
    # data/processed). Otherwise fall back to the Day 6 synthetic test image
    # -- this keeps the script useful before AND after real data is added,
    # without needing to remember which mode to run manually.
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
    RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
    PROCESSED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "processed")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    has_real_data = os.path.isdir(RAW_DIR) and any(
        fname.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
        for _root, _dirs, files in os.walk(RAW_DIR)
        for fname in files
    )

    if has_real_data:
        print(f"Found real dataset at {os.path.abspath(RAW_DIR)} -- using it.")
        dataset = load_dataset(RAW_DIR)
        print(f"Loaded + preprocessed {len(dataset)} real images.")
        save_processed_dataset(dataset, PROCESSED_DIR)
        print(f"Cached processed skeletons to {os.path.abspath(PROCESSED_DIR)}")
        sample_name, sample_skeleton = dataset[0]
        print(f"Sample: {sample_name}  shape={sample_skeleton.shape}  "
              f"curve_pixels={int(sample_skeleton.sum())}")
    else:
        print(f"No real dataset found at {os.path.abspath(RAW_DIR)} -- "
              f"running the Day 6 synthetic pipeline test instead.")
        import random
        import matplotlib.pyplot as plt
        from grid import PulliGrid
        from genome import KolamGenome
        from renderer import render_genome

        g = PulliGrid(n=6, grid_type="square")
        genome = KolamGenome(g)
        genome.randomize(random.Random(3))

        fig, ax = plt.subplots(figsize=(4, 4))
        render_genome(genome, ax=ax, show_dots=False)
        synthetic_path = os.path.join(OUTPUT_DIR, "_synthetic_test_image.png")
        plt.savefig(synthetic_path, dpi=150)
        plt.close(fig)

        gray = load_image_grayscale(synthetic_path)
        skeleton = preprocess_image(gray)

        print(f"Loaded synthetic test image: shape={gray.shape}")
        print(f"Skeleton: shape={skeleton.shape}, curve pixels={int(skeleton.sum())}")