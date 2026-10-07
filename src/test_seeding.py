"""Tests for the 'start from my own pattern' feature. Run from src/:  python test_seeding.py"""
import io, random, sys
from PIL import Image
import app_core as ac
from ga import apply_initial_seed, GAConfig, run_ga
from grid import PulliGrid

fails = 0
def check(name, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + name); fails += 0 if cond else 1

# --- apply_initial_seed
rng = random.Random(0); L = 144
pop = [[rng.randint(0, 1) for _ in range(L)] for _ in range(20)]
seed = [i % 2 for i in range(L)]
pop_before = [list(c) for c in pop]
out = apply_initial_seed(pop, seed, 0.5, 0.05, random.Random(1))
check("size unchanged", len(out) == 20 and all(len(c) == L for c in out))
check("first member is an exact copy", out[0] == seed)
dist = [sum(a != b for a, b in zip(c, seed)) for c in out]
check("10 members started from seed (exact + 9 perturbed)", sum(d < 30 for d in dist) == 10)
check("perturbation near spread*L (~7 flips)", all(0 <= d <= 20 for d in dist[1:10]) and 2 <= sum(dist[1:10]) / 9 <= 13)
check("the other members untouched", out[10:] == pop[10:])
check("spread 0 gives exact copies", all(c == seed for c in apply_initial_seed(pop, seed, 1.0, 0.0, random.Random(2))))
check("input list not modified", pop == pop_before)
for bad in (dict(seed=[0] * 10), dict(seed=[2] * L), dict(fraction=1.5), dict(spread=-0.1)):
    try:
        apply_initial_seed(pop, bad.get("seed", seed), bad.get("fraction", 0.5), bad.get("spread", 0.05), random.Random(0))
        check(f"rejects {list(bad)}", False)
    except ValueError:
        check(f"rejects {list(bad)}", True)

# --- settings validation + helpers
good = ac.random_pattern(13, seed=3)
check("random_pattern length", len(good) == 144 and set(good) <= {0, 1})
check("rows round-trip", ac.rows_to_pattern(ac.pattern_to_rows(good, 13)) == good)
check("rows_to_pattern accepts booleans", ac.rows_to_pattern([[True, False], [False, True]]) == [1, 0, 0, 1])
for bad in (dict(start_pattern=[0] * 5), dict(start_pattern=[3] * 144), dict(start_pattern=good, start_fraction=2.0)):
    try:
        ac.validate_settings(ac.RunSettings(**bad)); check(f"validate rejects {list(bad)}", False)
    except ValueError as e:
        check(f"validate rejects {list(bad)}", True)
try:
    ac.validate_settings(ac.RunSettings(grid_n=10, start_pattern=good)); check("grid mismatch rejected", False)
except ValueError as e:
    check("grid mismatch rejected with a clear message", "needs 81" in str(e))
check("valid start pattern accepted", ac.validate_settings(ac.RunSettings(start_pattern=good)) is None)
cfg = ac.make_ga_config(ac.RunSettings(start_pattern=good, start_fraction=0.3, start_spread=0.1))
check("config carries the pattern", cfg.initial_chromosome == good and cfg.initial_fraction == 0.3 and cfg.initial_spread == 0.1)
check("no pattern -> config unchanged", ac.make_ga_config(ac.RunSettings()).initial_chromosome is None)
check("freedom choices valid", all(0 <= f <= 1 and 0 <= sp <= 1 for f, sp in ac.FREEDOM_CHOICES.values()))

eff = ac.effective_start_pattern(good, 13, "mirror")
from fitness import symmetry_score
from genome import KolamGenome
g = KolamGenome(PulliGrid(n=13)); g.from_chromosome(eff)
check("effective pattern is symmetric under mirror", abs(symmetry_score(g) - 1.0) < 1e-9)
check("effective pattern unchanged when no symmetry", ac.effective_start_pattern(good, 13, None) == good)
check("preview PNG", Image.open(io.BytesIO(ac.render_pattern_png(good, 13))).format == "PNG")

# --- end to end: GA stays near the pattern it started from
refs = ac.load_references()
L = 144
pat = [(i // 12 + i % 12) % 2 for i in range(L)]          # a regular checkerboard of tile types
base = dict(grid_n=13, symmetry_mode=None, population_size=8, generations=2, sample_size=8, seed=4)
r_seed = ac.run_evolution(refs, ac.RunSettings(**base, start_pattern=pat, start_fraction=1.0, start_spread=0.0))
r_rand = ac.run_evolution(refs, ac.RunSettings(**base))
d_seed = sum(a != b for a, b in zip(r_seed.chromosome, pat)); d_rand = sum(a != b for a, b in zip(r_rand.chromosome, pat))
print(f"   distance from start pattern: seeded run {d_seed} tiles, random run {d_rand} tiles")
check("seeded run stays close to the pattern (<= 25 of 144 tiles changed)", d_seed <= 25)
check("random run is far from it", d_rand > 40)
check("same seed + pattern is repeatable", ac.run_evolution(refs, ac.RunSettings(**base, start_pattern=pat, start_fraction=1.0,
      start_spread=0.0)).chromosome == r_seed.chromosome)
r_m = ac.run_evolution(refs, ac.RunSettings(**{**base, "symmetry_mode": "mirror"}, start_pattern=pat))
check("works together with mirror symmetry", abs(r_m.symmetry - 1.0) < 1e-9)
print("\nALL PASSED" if fails == 0 else f"\n{fails} FAILED"); sys.exit(1 if fails else 0)
