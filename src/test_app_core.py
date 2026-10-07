"""Tests for app_core.py. Run from src/:  python test_app_core.py   (add --quick for tiny GA settings)"""
import io, os, sys, tempfile, json
import numpy as np
from PIL import Image
import app_core as ac
from symmetry import symmetrize_chromosome
from fitness import symmetry_score

QUICK = "--quick" in sys.argv
ok = 0
def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name); ok += 0 if cond else 1

# --- settings / validation / eta (no data needed)
check("eta none before first step", ac.eta_seconds(5, 0, 10) is None)
check("eta basic", abs(ac.eta_seconds(10, 5, 15) - 20) < 1e-9)
check("eta never negative", ac.eta_seconds(10, 20, 15) == 0.0)
for bad in (dict(grid_n=3), dict(grid_n=40), dict(population_size=2), dict(generations=0),
            dict(sample_size=0), dict(symmetry_mode="diagonal")):
    try:
        ac.validate_settings(ac.RunSettings(**bad)); check(f"validate rejects {bad}", False)
    except ValueError:
        check(f"validate rejects {bad}", True)
check("validate accepts defaults", ac.validate_settings(ac.RunSettings()) is None)

# --- config: from the Day 12 file, and the fallback when the file is missing
cfg = ac.make_ga_config(ac.RunSettings(grid_n=13))
check("cfg mutation rate = 1/144", abs(cfg.mutation_rate - 1 / 144) < 1e-12)
check("cfg symmetry mirror", cfg.symmetry_mode == "mirror")
cfg2 = ac.make_ga_config(ac.RunSettings(grid_n=10, symmetry_mode=None), config_path="/nonexistent.json")
check("fallback ops used", cfg2.crossover_method == "block" and cfg2.tournament_size == 3 and cfg2.symmetry_mode is None)
check("fallback fitness weights", abs(cfg2.fitness_kwargs["loop_weight"] - 1 / 3) < 1e-12)
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "c.json"); json.dump({"overrides": {"tournament_size": 5, "elite_count": 4, "rate_mult": 2}}, open(p, "w"))
    c3 = ac.make_ga_config(ac.RunSettings(grid_n=11), config_path=p)
    check("custom config read", c3.tournament_size == 5 and c3.elite_count == 4 and abs(c3.mutation_rate - 2 / 100) < 1e-12)
    open(p, "w").write("not json")
    c4 = ac.make_ga_config(ac.RunSettings(), config_path=p)
    check("corrupt config falls back", c4.tournament_size == 3)

# --- missing data gives a clear error
for bad in ("/no/such/dir", tempfile.mkdtemp()):
    try:
        ac.load_references(bad); check("missing data raises", False)
    except FileNotFoundError as e:
        check("missing data raises FileNotFoundError", "reference" in str(e).lower() or "No reference" in str(e))

# --- full run on the available dataset
refs = ac.load_references()
check("references loaded", len(refs) > 0 and len(refs[0]) == 3)
s = ac.RunSettings(grid_n=13, symmetry_mode="mirror", population_size=6 if QUICK else 8,
                   generations=2 if QUICK else 3, sample_size=8, seed=1)
calls = []
r = ac.run_evolution(refs, s, on_progress=lambda d, t, st, el: calls.append((d, t, st["generation"])))
check("progress called every generation", len(calls) == s.generations + 1 and calls[-1][0] == calls[-1][1])
check("history has curves", len(r.history) == s.generations + 1 and {"best", "mean", "diversity"} <= set(r.history[0]))
check("genome is symmetric (mirror, grid 13)", abs(symmetry_score(r.genome) - 1.0) < 1e-9)
check("chromosome length 144", len(r.chromosome) == 144)
check("match found", r.match_name is not None and r.match_skeleton is not None and r.d_min > 0)
check("metrics in range", 0 <= r.symmetry <= 1 and 0 <= r.loop_closure <= 1 and 0 <= r.best_fitness <= 1)
r2 = ac.run_evolution(refs, s)
check("same seed -> same result", r2.chromosome == r.chromosome)
sm = ac.result_summary(r)
check("summary is JSON-serialisable", json.loads(json.dumps(sm))["settings"]["grid_n"] == 13)

# --- pictures
png = ac.render_png(r.genome)
im = Image.open(io.BytesIO(png)); check("render_png is a PNG image", im.format == "PNG" and im.size[0] > 100)
sp = ac.skeleton_png(r.match_skeleton)
im2 = Image.open(io.BytesIO(sp)); check("skeleton_png is a PNG image", im2.format == "PNG" and im2.mode == "L")
check("render_png leaves no open figures", __import__("matplotlib.pyplot").pyplot.get_fignums() == [])

# --- sample_size larger than the dataset is clamped, other modes run
s3 = ac.RunSettings(grid_n=10, symmetry_mode=None, population_size=6, generations=1, sample_size=9999, seed=2)
r3 = ac.run_evolution(refs, s3); check("sample_size clamped, no-symmetry run works", len(r3.history) == 2)
s4 = ac.RunSettings(grid_n=13, symmetry_mode="rot180", population_size=6, generations=1, sample_size=8)
r4 = ac.run_evolution(refs, s4); check("rot180 run works", len(r4.history) == 2)

print("\nALL PASSED" if ok == 0 else f"\n{ok} FAILED"); sys.exit(1 if ok else 0)
