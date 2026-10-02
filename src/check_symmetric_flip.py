import random
from grid import PulliGrid
from genome import KolamGenome
from fitness import symmetry_score
from mutation import mutate

grid = PulliGrid(n=6, grid_type="square")
R = C = 5                      # cell grid = n - 1
rng = random.Random(0)

# Build a symmetric parent: each 4-cell orbit gets (v, 1-v, 1-v, v)
parent = [0] * (R * C)
for i in range(3):
    for j in range(3):
        v = rng.randint(0, 1)
        parent[i*C + j] = v
        parent[i*C + (C-1-j)] = 1 - v
        parent[(R-1-i)*C + j] = 1 - v
        parent[(R-1-i)*C + (C-1-j)] = v

def score(chrom):
    g = KolamGenome(grid)
    out = g.from_chromosome(chrom)
    return symmetry_score(out if isinstance(out, KolamGenome) else g)

base = score(parent)
sym = [score(mutate(parent, 0.3, "symmetric_flip", rng)) for _ in range(500)]
plain = [score(mutate(parent, 0.1, "flip", rng)) for _ in range(500)]

print("parent score:            ", round(base, 4))
print("symmetric_flip min/max:  ", round(min(sym), 4), round(max(sym), 4))
print("plain flip mean:         ", round(sum(plain) / len(plain), 4))
print("PASS" if all(abs(s - base) < 1e-9 for s in sym) else "FAIL")