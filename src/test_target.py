"""Tests for imitating an uploaded Kolam picture. Run from src/:  python test_target.py"""
import io, json, sys, random
import numpy as np
from PIL import Image
import app_core as ac
from grid import PulliGrid
from genome import KolamGenome
from population import Population
from similarity import (genome_to_skeleton, genome_to_skeleton_fast, overlap_score, prepare_target)
from scipy.ndimage import distance_transform_edt

fails = 0
def check(name, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + name); fails += 0 if cond else 1

def dt_of(sk): return distance_transform_edt(~sk)
pop = Population(PulliGrid(n=13), 5, seed=3).initialize().genomes

# 1. the fast renderer agrees with the matplotlib one
f1s = [overlap_score(genome_to_skeleton_fast(g), genome_to_skeleton(g), dt_of(genome_to_skeleton(g)), 2.0) for g in pop]
check(f"fast renderer matches matplotlib render (F1 at 2 px: min {min(f1s):.3f})", min(f1s) >= 0.97)

# 2. an uploaded picture is lined up with the pattern area, whatever margins/size it has
target_genome = pop[0]
png = ac.render_png(target_genome, size_inches=6, dpi=100)               # different size/margins from the internal render
gray = np.array(Image.open(io.BytesIO(png)).convert("L"))
tsk = prepare_target(gray, grid_n=13)
tol = ac.auto_tolerance(13)
sc = overlap_score(genome_to_skeleton_fast(target_genome), tsk, dt_of(tsk), tol)
check(f"prepared target lines up with the genome that drew it (F1 {sc:.3f} at {tol} px)", sc >= 0.95)
other = overlap_score(genome_to_skeleton_fast(pop[1]), tsk, dt_of(tsk), tol)
check(f"a different pattern scores clearly lower (F1 {other:.3f})", other < sc - 0.12)
check("auto tolerance shrinks as the grid grows", ac.auto_tolerance(10) > ac.auto_tolerance(13) > ac.auto_tolerance(16) >= 1.0)
inv = prepare_target(255 - gray, grid_n=13)
check("light-on-dark pictures work too", overlap_score(inv, tsk, dt_of(tsk), 2.0) > 0.95)
for name, arr in (("blank image", np.full((50, 50), 255, np.uint8)), ("tiny speck", np.where(np.arange(2500).reshape(50, 50) == 5, 0, 255).astype(np.uint8))):
    try:
        prepare_target(arr, 13); check(f"prepare_target rejects a {name}", False)
    except ValueError:
        check(f"prepare_target rejects a {name}", True)
try:
    ac.load_target(b"this is not an image", 13); check("unreadable file rejected", False)
except ValueError as e:
    check("unreadable file rejected with a clear message", "Could not read" in str(e))

# 3. end to end: the GA recovers a known pattern from its picture
refs = ac.load_references()
base = dict(grid_n=13, symmetry_mode=None, population_size=30, generations=60, seed=5, target_image=png)
r = ac.run_evolution(refs, ac.RunSettings(**base, target_weight=1.0))
acc = np.mean([a == b for a, b in zip(r.chromosome, target_genome.to_chromosome())])
print(f"   pure imitation: score {r.target_score:.3f} (random patterns {r.target_baseline:.3f}), {acc:.0%} of tiles recovered, {r.elapsed_s:.0f}s")
check("imitation score far above random patterns", r.target_score >= 0.9 and r.target_baseline < r.target_score - 0.1)
check("most tiles of the hidden pattern recovered", acc >= 0.9)
check("result carries the target lines and an overlay picture", r.target_skeleton is not None and
      Image.open(io.BytesIO(ac.overlay_png(r))).format == "PNG")
r2 = ac.run_evolution(refs, ac.RunSettings(**base, target_weight=0.6))
print(f"   balanced (0.6): score {r2.target_score:.3f}, symmetry {r2.symmetry:.2f}, loop {r2.loop_closure:.2f}")
check("balanced mode still improves on random", r2.target_score > r2.target_baseline + 0.04)
check("same seed repeats", ac.run_evolution(refs, ac.RunSettings(**base, target_weight=1.0)).chromosome == r.chromosome)
check("closest-real-Kolam match still reported from the dataset", r.match_name is not None and r.d_min > 0)

# 4. summary / validation / non-imitation runs
check("summary is JSON-able even with image bytes", json.loads(json.dumps(ac.result_summary(r)))["settings"]["target_image"] is True)
for bad in (dict(target_weight=0.0), dict(target_weight=1.5), dict(target_tolerance=0)):
    try:
        ac.validate_settings(ac.RunSettings(target_image=b"x", **bad)); check(f"validate rejects {bad}", False)
    except ValueError:
        check(f"validate rejects {bad}", True)
try:
    ac.run_evolution(refs, ac.RunSettings(target_image=b"garbage")); check("run with unreadable image raises ValueError", False)
except ValueError:
    check("run with unreadable image raises ValueError", True)
plain = ac.run_evolution(refs, ac.RunSettings(grid_n=13, population_size=6, generations=1, sample_size=8))
check("normal runs have no target fields", plain.target_score is None and plain.target_skeleton is None and ac.overlay_png(plain) is None)
print("\nALL PASSED" if fails == 0 else f"\n{fails} FAILED"); sys.exit(1 if fails else 0)
