"""
kolamNet — Pulli Grid Representation
=====================================
A Kolam is drawn around a grid of dots ("pulli"). Most traditional Kolams
use a square or diamond arrangement of dots, and the curve weaves around
them following symmetry rules (4-fold, 8-fold rotational, or reflective).

This module defines the PulliGrid: the scaffold that every genome (in later
phases) will be drawn on top of. Getting this right first matters because:
  - the genome's "genes" will reference grid coordinates / cell indices
  - symmetry-based fitness scoring depends on knowing the grid's symmetry
    axes ahead of time
  - the renderer needs real (x, y) pixel positions to draw on

Supported grid types (v1):
  - "square"  : standard square lattice of dots, size n x n
  - "diamond" : the classic rhombus/diamond pulli arrangement used in many
                South Indian Kolams (rows grow then shrink: 1,2,...,n,...,2,1)
"""

from dataclasses import dataclass, field
from typing import List, Tuple
import math


@dataclass
class PulliGrid:
    n: int = 5                 # base size parameter
    grid_type: str = "square"  # "square" or "diamond"
    spacing: float = 1.0       # distance between adjacent dots

    points: List[Tuple[float, float]] = field(default_factory=list, init=False)
    rows: List[List[Tuple[float, float]]] = field(default_factory=list, init=False)

    def __post_init__(self):
        if self.grid_type == "square":
            self._build_square()
        elif self.grid_type == "diamond":
            self._build_diamond()
        else:
            raise ValueError(f"Unknown grid_type: {self.grid_type}")

    def _build_square(self):
        self.rows = []
        for i in range(self.n):
            row = []
            for j in range(self.n):
                x = j * self.spacing
                y = i * self.spacing
                row.append((x, y))
            self.rows.append(row)
        self.points = [p for row in self.rows for p in row]

    def _build_diamond(self):
        # row lengths: 1, 2, ..., n, ..., 2, 1  (classic diamond pulli kolam)
        self.rows = []
        n = self.n
        row_lengths = list(range(1, n + 1)) + list(range(n - 1, 0, -1))
        total_rows = len(row_lengths)
        mid = (total_rows - 1) / 2

        for i, length in enumerate(row_lengths):
            row = []
            y = i * self.spacing
            # center each row horizontally
            x_start = -(length - 1) * self.spacing / 2
            for j in range(length):
                x = x_start + j * self.spacing
                row.append((x, y))
            self.rows.append(row)
        self.points = [p for row in self.rows for p in row]

    @property
    def center(self) -> Tuple[float, float]:
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def bounding_box(self):
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return (min(xs), min(ys), max(xs), max(ys))

    def symmetry_axes(self, kind: str = "rotational", order: int = 4):
        """
        Returns a list of transform functions (each maps (x, y) -> (x', y'))
        representing the symmetry group we'll use for symmetry-based fitness
        and for symmetric genome generation later.
        """
        cx, cy = self.center
        transforms = []

        if kind == "rotational":
            for k in range(order):
                theta = 2 * math.pi * k / order
                cos_t, sin_t = math.cos(theta), math.sin(theta)

                def make_rot(cos_t=cos_t, sin_t=sin_t, cx=cx, cy=cy):
                    def rot(p):
                        x, y = p[0] - cx, p[1] - cy
                        return (x * cos_t - y * sin_t + cx,
                                x * sin_t + y * cos_t + cy)
                    return rot
                transforms.append(make_rot())

        elif kind == "reflective":
            def reflect_v(p, cx=cx):
                return (2 * cx - p[0], p[1])

            def reflect_h(p, cy=cy):
                return (p[0], 2 * cy - p[1])

            transforms = [lambda p: p, reflect_v, reflect_h]

        else:
            raise ValueError(f"Unknown symmetry kind: {kind}")

        return transforms

    def nearest_point(self, x: float, y: float) -> Tuple[float, float]:
        return min(self.points, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)

    def __len__(self):
        return len(self.points)


if __name__ == "__main__":
    g_sq = PulliGrid(n=5, grid_type="square")
    g_di = PulliGrid(n=5, grid_type="diamond")
    print(f"Square grid: {len(g_sq)} points, center={g_sq.center}")
    print(f"Diamond grid: {len(g_di)} points, center={g_di.center}")
    print(f"Bounding box (diamond): {g_di.bounding_box()}")
