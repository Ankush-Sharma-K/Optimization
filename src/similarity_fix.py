"""
Day 12.5 -- Why the similarity term is flat, and a fix to test.

PART 1  Diagnostics (cheap, ~1-2 min):
  * For random genomes on the tuned grid: how much does each distance variant
    differ BETWEEN genomes?  (coefficient of variation, in %)
  * Grid-size sweep: how does the distance to the references change with the
    grid size?  (Day 12 hint: grid size moved similarity far more than
    anything the GA did.)
PART 2  A/B test of GA runs, judged by neutral measures on ALL references:
  * d_min  = raw best-match Chamfer distance in pixels (lower = more similar)
  * d_k5   = mean distance to the 5 nearest references
  * structural = (symmetry + loop closure) / 2, to catch a trade-off
  Variants: baseline (Day 12 setting) | calib_k1 | calib_k5 | calib_k5_w50

Outputs (in outputs/): day12b_diagnostic.png, day12b_results.csv (resumable),
day12b_genomes.png, day12b_summary.json

Usage (from src/):
  python similarity_fix.py --quick            # smoke test
  python similarity_fix.py --workers 3        # full run
  python similarity_fix.py --diagnose-only    # Part 1 only
  python similarity_fix.py --grid-n 12 --workers 3   # A/B at another grid size
"""
import argparse
import csv
import json
import math
import os
import time

import numpy as np

from grid import PulliGrid
from genome import KolamGenome
from fitness import symmetry_score, loop_closure_score
from ga import run_ga
from population import Population
from dataset import load_processed_dataset
from similarity import (precompute_reference_transforms, distance_matrix,
                        similarity_distance, calibrate_similarity, _knn_mean)
from experiments import Progress, tuned_config, PROCESSED_DIR, OUTPUT_DIR, BEST_CONFIG_JSON

AB_CSV = os.path.join(OUTPUT_DIR, "day12b_results.csv")
SUMMARY_JSON = os.path.join(OUTPUT_DIR, "day12b_summary.json")
FIELDS = ["variant", "seed", "grid_n", "generations", "d_min", "d_k5", "symmetry", "loop",
          "structural", "own_fitness", "elapsed_s", "chromosome"]


# --------------------------------------------------------------------------
# Part 1: diagnostics
# --------------------------------------------------------------------------
def diagnose(ref, grid_n, grids, n_genomes=30, seed=0, out_png=None):
    pop = Population(PulliGrid(n=grid_n), n_genomes, seed=seed).initialize()
    D = distance_matrix(pop.genomes, ref)
    variants = {
        "min (current)": D.min(axis=1),
        "mean of 5 nearest": _knn_mean(D, 5),
        "mean of 20 nearest": _knn_mean(D, 20),
        "mean over all refs": D.mean(axis=1),
    }
    print(f"\n=== Part 1a: spread between {n_genomes} random genomes, grid {grid_n} ===")
    print(f"{'distance variant':>20} {'mean px':>8} {'std px':>8} {'CV %':>6}")
    cv = {}
    for name, d in variants.items():
        cv[name] = 100 * d.std() / d.mean()
        print(f"{name:>20} {d.mean():>8.3f} {d.std():>8.4f} {cv[name]:>6.2f}")
    print(f"distinct best-matching references: {len(set(D.argmin(axis=1)))} of {D.shape[1]}")

    print(f"\n=== Part 1b: grid-size sweep (random genomes, 20 per size) ===")
    print(f"{'grid':>5} {'d_min px':>9} {'std px':>8} {'sec/genome':>11}")
    sweep = []
    for n in grids:
        p = Population(PulliGrid(n=n), 20, seed=seed).initialize()
        t0 = time.time()
        d = distance_matrix(p.genomes, ref).min(axis=1)
        sweep.append((n, float(d.mean()), float(d.std()), (time.time() - t0) / 20))
        print(f"{n:>5} {sweep[-1][1]:>9.3f} {sweep[-1][2]:>8.4f} {sweep[-1][3]:>11.3f}")
    grid_effect = abs(sweep[0][1] - sweep[-1][1])
    within = max(s[2] for s in sweep)
    print(f"\nChanging the grid from {sweep[0][0]} to {sweep[-1][0]} moves the distance by "
          f"{grid_effect:.2f} px; changing the pattern at a fixed grid moves it by only "
          f"~{within:.3f} px (std).")
    if grid_effect > 20 * within:
        print("=> The distance mostly measures dot DENSITY (grid size), not pattern shape: "
              "every Truchet tiling covers the canvas almost identically.")

    if out_png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8))
        a.bar(range(len(cv)), list(cv.values()), color="#8B2E2E")
        a.set_xticks(range(len(cv)))
        a.set_xticklabels(list(cv), rotation=20, fontsize=8)
        a.set_ylabel("spread between random genomes (CV %)")
        a.set_title(f"Pattern-to-pattern variation, grid {grid_n}", fontsize=9)
        xs = [s[0] for s in sweep]
        b.errorbar(xs, [s[1] for s in sweep], yerr=[s[2] for s in sweep], marker="o", color="#4a6fa5")
        b.set_xlabel("grid size n")
        b.set_ylabel("best-match distance (px)")
        b.set_title("Distance vs grid size", fontsize=9)
        fig.tight_layout()
        fig.savefig(out_png, dpi=130)
        plt.close(fig)
    return {"cv_percent": cv, "sweep": sweep}


# --------------------------------------------------------------------------
# Part 2: A/B runs
# --------------------------------------------------------------------------
_REF = None


def _init_worker(processed_dir):
    global _REF
    _REF = precompute_reference_transforms(load_processed_dataset(processed_dir))


def run_variant(variant, seed, fitness_kwargs, args, ref):
    grid_n, cfg = tuned_config(grid_n=args.grid_n, generations=args.generations, population_size=args.pop,
                               sample_size=args.sample, seed=seed,
                               fitness_kwargs=fitness_kwargs)
    t0 = time.time()
    res = run_ga(PulliGrid(n=grid_n), ref, cfg)
    g = res.best_genome
    sym, loop = symmetry_score(g), loop_closure_score(g)
    return {"variant": variant, "seed": seed, "grid_n": grid_n, "generations": args.generations,
            "d_min": similarity_distance(g, ref, k=1), "d_k5": similarity_distance(g, ref, k=5),
            "symmetry": sym, "loop": loop, "structural": (sym + loop) / 2,
            "own_fitness": res.best_fitness, "elapsed_s": round(time.time() - t0, 1),
            "chromosome": json.dumps(g.to_chromosome())}


def _worker_task(task):
    variant, seed, fk, args = task
    return run_variant(variant, seed, fk, args, _REF)


def load_rows():
    if not os.path.exists(AB_CSV):
        return []
    with open(AB_CSV, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("d_min", "d_k5", "symmetry", "loop", "structural", "own_fitness", "elapsed_s"):
            r[k] = float(r[k])
        r["seed"], r["grid_n"], r["generations"] = int(r["seed"]), int(r["grid_n"]), int(r["generations"])
    return rows


def append_row(row):
    new = not os.path.exists(AB_CSV)
    with open(AB_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def _stat(rows, field):
    v = np.array([r[field] for r in rows])
    se = v.std(ddof=1) / math.sqrt(len(v)) if len(v) > 1 else float("nan")
    return float(v.mean()), float(se)


def summarize(rows, order, generations, grid_n):
    rows = [r for r in rows if r["generations"] == generations and r["grid_n"] == grid_n]
    by = {v: [r for r in rows if r["variant"] == v] for v in order}
    print(f"\n=== Part 2: A/B results (grid {grid_n}, {generations} generations) ===")
    print(f"{'variant':>13} {'n':>2} {'d_min px':>14} {'d_k5 px':>14} {'structural':>14}")
    out = {}
    for v in order:
        if not by[v]:
            continue
        dm, dme = _stat(by[v], "d_min")
        d5, d5e = _stat(by[v], "d_k5")
        st, ste = _stat(by[v], "structural")
        out[v] = {"n": len(by[v]), "d_min": dm, "d_min_se": dme, "d_k5": d5, "structural": st,
                  "structural_se": ste}
        print(f"{v:>13} {len(by[v]):>2} {dm:>8.3f}+-{dme:<5.3f} {d5:>8.3f}+-{d5e:<5.3f} "
              f"{st:>8.3f}+-{ste:<5.3f}")
    base = out.get("baseline")
    verdicts = {}
    if base:
        print("\nVerdict vs baseline (distance: lower is better):")
        for v, s in out.items():
            if v == "baseline":
                continue
            gain = base["d_min"] - s["d_min"]
            se = math.sqrt(np.nan_to_num(base["d_min_se"]) ** 2 + np.nan_to_num(s["d_min_se"]) ** 2)
            lost = base["structural"] - s["structural"]
            if se > 0 and gain > 2 * se:
                d = "closer to the references (>2 s.e.)"
            elif se > 0 and gain > se:
                d = "slightly closer (1-2 s.e.)"
            else:
                d = "no real change in similarity"
            note = f"; structure dropped by {lost:.3f}" if lost > 0.03 else ""
            verdicts[v] = {"similarity_gain_px": gain, "verdict": d, "structure_lost": lost}
            print(f"  {v:>13}: d_min {gain:+.3f} px -> {d}{note}")
    return out, verdicts


def plot_genomes(rows, order, generations, grid_n, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from renderer import render_genome
    rows = [r for r in rows if r["generations"] == generations and r["grid_n"] == grid_n]
    seeds = sorted({r["seed"] for r in rows})[:3]
    order = [v for v in order if any(r["variant"] == v for r in rows)]
    if not order or not seeds:
        return
    fig, axes = plt.subplots(len(order), len(seeds), figsize=(3.2 * len(seeds), 3.2 * len(order)),
                             squeeze=False)
    for i, v in enumerate(order):
        for j, s in enumerate(seeds):
            ax = axes[i][j]
            ax.axis("off")
            m = [r for r in rows if r["variant"] == v and r["seed"] == s]
            if not m:
                continue
            g = KolamGenome(PulliGrid(n=grid_n))
            g.from_chromosome(json.loads(m[0]["chromosome"]))
            render_genome(g, ax=ax, show_dots=False)
            ax.set_title(f"{v} | seed {s}\nd_min {m[0]['d_min']:.2f}px  struct {m[0]['structural']:.2f}",
                         fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="2 seeds, 12 gens, pop 16, sample 25")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--generations", type=int, default=30)
    ap.add_argument("--pop", type=int, default=30)
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--grid-n", type=int, default=None,
                    help="grid size for the diagnostic and A/B runs (default: from day12_best_config.json)")
    ap.add_argument("--variants", nargs="*", default=None,
                    help="run only these variants (baseline calib_k1 calib_k5 calib_k5_w50); "
                         "e.g. --variants baseline --seeds 1 is a single GA run")
    ap.add_argument("--diagnose-only", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    args = ap.parse_args()
    if args.quick:
        args.seeds, args.generations, args.pop, args.sample = 2, 12, 16, 25

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.exists(BEST_CONFIG_JSON):
        raise SystemExit(f"{BEST_CONFIG_JSON} not found -- run experiments.py (Day 12) first.")
    ref = precompute_reference_transforms(load_processed_dataset(PROCESSED_DIR))
    print(f"Loaded {len(ref)} reference skeletons.")
    grid_n, _ = tuned_config(grid_n=args.grid_n)

    grids = (6, 10) if args.quick else (6, 8, 10, 12, 14, 16)
    diag = diagnose(ref, grid_n, grids, out_png=os.path.join(OUTPUT_DIR, "day12b_diagnostic.png"))
    if args.diagnose_only:
        return

    # calibration is measured on the same grid + reference sample size the GA will use
    cal1 = calibrate_similarity(PulliGrid(n=grid_n), ref, k=1, sample_size=args.sample)
    cal5 = calibrate_similarity(PulliGrid(n=grid_n), ref, k=5, sample_size=args.sample)
    print(f"\nCalibration (random genomes, grid {grid_n}): k=1 mu={cal1['mu']:.3f}px sigma={cal1['sigma']:.4f}px"
          f" | k=5 mu={cal5['mu']:.3f}px sigma={cal5['sigma']:.4f}px")
    variants = {
        "baseline": {},
        "calib_k1": {"similarity_k": 1, "similarity_calibration": cal1},
        "calib_k5": {"similarity_k": 5, "similarity_calibration": cal5},
        "calib_k5_w50": {"similarity_k": 5, "similarity_calibration": cal5,
                         "symmetry_weight": 0.25, "loop_weight": 0.25, "similarity_weight": 0.5},
    }
    if args.variants:
        variants = {v: fk for v, fk in variants.items() if v in args.variants}
    order = list(variants)

    if args.fresh and os.path.exists(AB_CSV):
        os.remove(AB_CSV)
    rows = load_rows()
    done = {(r["variant"], r["seed"], r["grid_n"], r["generations"]) for r in rows}
    tasks = [(v, s, fk, args) for v, fk in variants.items() for s in range(args.seeds)
             if (v, s, grid_n, args.generations) not in done]
    progress = Progress(len(variants) * args.seeds)
    progress.skip(len(variants) * args.seeds - len(tasks))
    print(f"\n{len(tasks)} GA runs to do (workers={args.workers}).")
    if tasks:
        if args.workers > 1:
            import multiprocessing as mp
            pool = mp.Pool(args.workers, initializer=_init_worker, initargs=(PROCESSED_DIR,))
            results = pool.imap_unordered(_worker_task, tasks)
        else:
            pool = None
            results = (run_variant(v, s, fk, a, ref) for v, s, fk, a in tasks)
        for row in results:
            append_row(row)
            rows.append(row)
            progress.tick(f"{row['variant']} seed={row['seed']} d_min={row['d_min']:.3f}px "
                          f"struct={row['structural']:.3f} ({row['elapsed_s']:.0f}s)")
        if pool:
            pool.close()
            pool.join()

    out, verdicts = summarize(rows, order, args.generations, grid_n)
    plot_genomes(rows, order, args.generations, grid_n, os.path.join(OUTPUT_DIR, "day12b_genomes.png"))
    with open(SUMMARY_JSON, "w") as f:
        json.dump({"grid_n": grid_n, "diagnostics": diag, "variants": out, "verdicts": verdicts,
                   "calibration": {"k1": cal1, "k5": cal5}}, f, indent=2)
    print(f"\nSaved {SUMMARY_JSON}")


if __name__ == "__main__":
    main()