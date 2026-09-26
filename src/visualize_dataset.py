"""
Day 6 sanity check -- shows the original synthetic image, its thresholded
binary version, and its final skeleton side by side, to visually confirm
each preprocessing stage is doing what it should before real dataset
images are used.
"""
import os
import matplotlib.pyplot as plt

from dataset import load_image_grayscale, preprocess_image, IMAGE_SIZE
from skimage.filters import threshold_otsu
from PIL import Image
import numpy as np

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
SYNTHETIC_PATH = os.path.join(OUTPUT_DIR, "_synthetic_test_image.png")

if __name__ == "__main__":
    gray = load_image_grayscale(SYNTHETIC_PATH)

    resized = np.array(Image.fromarray(gray).resize((IMAGE_SIZE, IMAGE_SIZE), Image.LANCZOS))
    arr = resized.astype(np.float64) / 255.0
    binary = arr < threshold_otsu(arr)
    skeleton = preprocess_image(gray)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.5))
    axes[0].imshow(resized, cmap="gray")
    axes[0].set_title("Resized grayscale")
    axes[1].imshow(binary, cmap="gray")
    axes[1].set_title("Thresholded (binary)")
    axes[2].imshow(skeleton, cmap="gray")
    axes[2].set_title("Skeletonized")
    for ax in axes:
        ax.axis("off")

    plt.tight_layout()
    save_path = os.path.join(OUTPUT_DIR, "day6_preprocessing_stages.png")
    plt.savefig(save_path, dpi=150)
    print("Saved to:", os.path.abspath(save_path))
