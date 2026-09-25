"""
kolamNet — Fitness v1: Symmetry & Loop-Closure Scoring
==========================================================
First fitness function for ranking genomes within a Population. Combines
two structural quality signals real Kolams are judged by:

  1. Symmetry -- how closely the tile pattern matches itself under
     reflection/rotation (traditional Kolams are almost always symmetric)
  2. Loop closure -- how much of the drawn curve forms fully closed loops
     versus open strands that dead-end at the grid's outer boundary
     (traditional Kolams are drawn as one or more closed, unbroken loops)

Both scores are in [0, 1], where 1 is "perfect". Neither needs to render
anything -- both work directly off the genome's tile grid / grid geometry,
which keeps fitness evaluation fast (it'll be called constantly once the
GA loop, Day 11, is running).
"""

from collections import defaultdict
from typing import Dict, Tuple

from genome import KolamGenome, TileType


# -- Symmetry -----------------------------------------------------------

def _flipped(t: TileType) -> TileType:
    return TileType.ARC_B if t == TileType.ARC_A else TileType.ARC_A


def symmetry_score(genome: KolamGenome) -> float:
    """Averages 3 structural symmetry checks: horizontal reflection,
    vertical reflection, and 180-degree rotation.

    Under a horizontal or vertical mirror, a cell's ARC_A/ARC_B identity
    flips (the two arcs swap which pair of corners they hug); under a
    180-degree rotation the tile identity stays the same. This lets us
    score symmetry directly from the tile grid, no rendering needed.

    Note: 90-degree rotational symmetry needs a corner-permutation model
    that isn't implemented yet -- left as a follow-up refinement.
    """
    rows, cols = genome.rows, genome.cols
    tiles = genome.tiles
    total = rows * cols

    h_matches = sum(
        1 for i in range(rows) for j in range(cols)
        if tiles[i][j] == _flipped(tiles[i][cols - 1 - j])
    )
    v_matches = sum(
        1 for i in range(rows) for j in range(cols)
        if tiles[i][j] == _flipped(tiles[rows - 1 - i][j])
    )
    r_matches = sum(
        1 for i in range(rows) for j in range(cols)
        if tiles[i][j] == tiles[rows - 1 - i][cols - 1 - j]
    )

    return ((h_matches / total) + (v_matches / total) + (r_matches / total)) / 3


# -- Loop closure ---------------------------------------------------------

def _mid(p, q):
    return ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)


def _key(p, precision: int = 6):
    return (round(p[0], precision), round(p[1], precision))


def _edge_midpoint_graph(genome: KolamGenome) -> Dict[Tuple[float, float], list]:
    """Builds an adjacency map {midpoint: [connected midpoints]} from every
    cell's 2 arcs. Each arc is one edge between the two midpoints it joins.
    Interior midpoints are shared by 2 neighboring cells (so end up with
    degree 2 -- a clean pass-through); boundary midpoints belong to only
    1 cell (degree 1 -- a dangling curve end)."""
    adjacency = defaultdict(list)
    for i in range(genome.rows):
        for j in range(genome.cols):
            tl, tr, bl, br = genome.cell_corners(i, j)
            top, bottom = _mid(tl, tr), _mid(bl, br)
            left, right = _mid(tl, bl), _mid(tr, br)
            tile = genome.get_tile(i, j)
            pairs = [(top, left), (bottom, right)] if tile == TileType.ARC_A \
                else [(top, right), (bottom, left)]
            for a, b in pairs:
                adjacency[_key(a)].append(_key(b))
                adjacency[_key(b)].append(_key(a))
    return adjacency


def loop_closure_score(genome: KolamGenome) -> float:
    """Traces the arc-connectivity graph and measures what fraction of the
    total curve (by arc count) belongs to fully closed loops -- every node
    in that connected component has degree 2 -- versus open strands that
    dead-end at the grid boundary (some node in the component has degree 1).

    Because boundary midpoints always have degree 1 by construction (a
    structural property of this 2-tile encoding, not something a genome can
    avoid), a score of 1.0 isn't reachable for any genome on this grid --
    that's expected, and mirrors how real Kolams need a bounded/closed
    border treatment to avoid open ends, which this project hasn't added
    yet. The score is still meaningful for *comparing* genomes: it rewards
    patterns that curl into more interior closed loops rather than long
    open strands.
    """
    adjacency = _edge_midpoint_graph(genome)
    visited = set()
    closed_edges = 0
    total_edges = 0

    for start in adjacency:
        if start in visited:
            continue
        component = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            stack.extend(n for n in adjacency[node] if n not in component)
        visited |= component

        is_closed = all(len(adjacency[node]) == 2 for node in component)
        component_edges = sum(len(adjacency[node]) for node in component) // 2
        total_edges += component_edges
        if is_closed:
            closed_edges += component_edges

    return closed_edges / total_edges if total_edges else 0.0


# -- Combined fitness -----------------------------------------------------

def fitness(genome: KolamGenome, symmetry_weight: float = 0.5,
            loop_weight: float = 0.5) -> float:
    """Weighted combination of the two scores above. Weights are a starting
    point -- expect to retune these once dataset-similarity scoring (Day 7)
    is added alongside them."""
    return (symmetry_weight * symmetry_score(genome)
            + loop_weight * loop_closure_score(genome))


if __name__ == "__main__":
    import random
    from grid import PulliGrid

    g = PulliGrid(n=6, grid_type="square")
    genome = KolamGenome(g)
    genome.randomize(random.Random(1))

    print(f"symmetry_score: {symmetry_score(genome):.3f}")
    print(f"loop_closure_score: {loop_closure_score(genome):.3f}")
    print(f"fitness: {fitness(genome):.3f}")
