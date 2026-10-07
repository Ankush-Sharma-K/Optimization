"""
Day 12.6 -- Does building symmetry in (symmetry.py) help?

Compares, at the tuned settings, three ways of running the GA:
  none     the Day 12 GA (symmetry is only rewarded by the fitness)
  rot180   every genome forced to 180-degree rotational symmetry
  mirror   every genome forced to left-right + top-bottom mirror symmetry

All runs are judged the same way, on ALL references:
  symmetry, loop closure, d_min (px, similarity to references; lower = closer),
  yardstick = default fitness().
NOTE: the yardstick contains the symmetry term, so forced symmetry raises it
mechanically. Read loop closure and d_min separately: they show whether
anything was LOST by forcing symmetry.

Parity note: grids with odd n (e.g. 13 -> 12x12 tiles) can reach symmetry 1.0
under "mirror"; even n (e.g. 12 -> 11x11 tiles) tops out at ~0.88.

Outputs (outputs/): day12c_results.csv (resumable), day12c_genomes.png,
day12c_summary.json

Usage (from src/):
  python symmetry_experiment.py --quick
  python symmetry_experiment.py --grids 13 --seeds 2 --workers 3
  python symmetry_experiment.py --grids 12 13 --workers 3
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
from fitness import fitness, symmetry_score, loop_closure_score
from ga import run_ga
from dataset import load_processed_dataset
from similarity import precompute_reference_transforms, similarity_distance
from experiments import Progress, tuned_config, PROCESSED_DIR, OUTPUT_DIR, BEST_CONFIG_JSON

CSV_PATH = os.path.join(OUTPUT_DIR, "day12c_results.csv")
SUMMARY_JSON = os.path.join(OUTPUT_DIR, "day12c_summary.json")
VARIANTS = {"none": None, "rot180": "rot180", "mirror": "mirror"}
FIELDS = ["variant", "grid_n", "seed", "generations", "symmetry", "loop", "d_min", "yardstick",
          "own_fitness", "elapsed_s", "chromosome"]
_REF = None


def _init_worker(processed_dir):
    global _REF
    _REF = precompute_reference_transforms(load_processed_dataset(processed_dir))


def run_one(variant, grid_n, seed, args, ref):
    gn, cfg = tuned_config(grid_n=grid_n, generations=args.generations, population_size=args.pop,
                           sample_size=args.sample, seed=seed, symmetry_mode=VARIANTS[variant])
    t0 = time.time()
    res = run_ga(PulliGrid(n=gn), ref, cfg)
    g = res.best_genome
    return {"variant": variant, "grid_n": gn, "seed": seed, "generations": args.generations,
            "symmetry": symmetry_score(g), "loop": loop_closure_score(g),
            "d_min": similarity_distance(g, ref, k=1),
            "yardstick": fitness(g, reference_transforms=ref),
            "own_fitness": res.best_fitness, "elapsed_s": round(time.time() - t0, 1),
            "chromosome": json.dumps(g.to_chromosome())}


def _worker_task(task):
    return run_one(*task, _REF)


def load_rows():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("symmetry", "loop", "d_min", "yardstick", "own_fitness", "elapsed_s"):
            r[k] = float(r[k])
        for k in ("grid_n", "seed", "generations"):
            r[k] = int(r[k])
    return rows


def append_row(row):
    new = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def _ms(rows, field):
    v = np.array([r[field] for r in rows])
    se = v.std(ddof=1) / math.sqrt(len(v)) if len(v) > 1 else float("nan")
    return v.mean(), se


def summarize(rows, grids, generations):
    out = {}
    for gn in grids:
        print(f"\n=== grid {gn} ({gn - 1}x{gn - 1} tiles), {generations} generations ===")
        print(f"{'variant':>8} {'n':>2} {'symmetry':>13} {'loop':>13} {'d_min px':>13} {'yardstick':>13} {'sec':>6}")
        for v in VARIANTS:
            rs = [r for r in rows if r["variant"] == v and r["grid_n"] == gn and r["generations"] == generations]
            if not rs:
                continue
            cells = []
            rec = {"n": len(rs)}
            for f in ("symmetry", "loop", "d_min", "yardstick"):
                m, se = _ms(rs, f)
                cells.append(f"{m:.3f}+-{np.nan_to_num(se):.3f}")
                rec[f], rec[f + "_se"] = float(m), float(np.nan_to_num(se))
            rec["sec"] = float(np.mean([r["elapsed_s"] for r in rs]))
            out[f"{v}@{gn}"] = rec
            print(f"{v:>8} {len(rs):>2} {cells[0]:>13} {cells[1]:>13} {cells[2]:>13} {cells[3]:>13} {rec['sec']:>6.0f}")
        base = out.get(f"none@{gn}")
        if base:
            for v in ("rot180", "mirror"):
                s = out.get(f"{v}@{gn}")
                if s:
                    print(f"  {v} vs none: symmetry {s['symmetry'] - base['symmetry']:+.3f}, "
                          f"loop {s['loop'] - base['loop']:+.3f}, d_min {s['d_min'] - base['d_min']:+.3f} px, "
                          f"yardstick {s['yardstick'] - base['yardstick']:+.3f}")
    return out


def plot_genomes(rows, grids, generations, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from renderer import render_genome
    cols = []
    for gn in grids:
        seeds = sorted({r["seed"] for r in rows if r["grid_n"] == gn and r["generations"] == generations})[:2]
        cols += [(gn, s) for s in seeds]
    if not cols:
        return
    fig, axes = plt.subplots(len(VARIANTS), len(cols), figsize=(3.2 * len(cols), 3.3 * len(VARIANTS)),
                             squeeze=False)
    for i, v in enumerate(VARIANTS):
        for j, (gn, s) in enumerate(cols):
            ax = axes[i][j]
            ax.axis("off")
            m = [r for r in rows if r["variant"] == v and r["grid_n"] == gn and r["seed"] == s
                 and r["generations"] == generations]
            if not m:
                continue
            g = KolamGenome(PulliGrid(n=gn))
            g.from_chromosome(json.loads(m[0]["chromosome"]))
            render_genome(g, ax=ax, show_dots=False)
            ax.set_title(f"{v} | grid {gn} seed {s}\nsym {m[0]['symmetry']:.2f} loop {m[0]['loop']:.2f}",
                         fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="1 seed, 12 gens, pop 16, sample 25, grid 13")
    ap.add_argument("--grids", type=int, nargs="*", default=[13])
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--generations", type=int, default=30)
    ap.add_argument("--pop", type=int, default=30)
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--variants", nargs="*", default=None, help="subset of: none rot180 mirror")
    ap.add_argument("--fresh", action="store_true")
    args = ap.parse_args()
    if args.quick:
        args.seeds, args.generations, args.pop, args.sample, args.grids = 1, 12, 16, 25, [13]
    if not os.path.exists(BEST_CONFIG_JSON):
        raise SystemExit(f"{BEST_CONFIG_JSON} not found -- run experiments.py (Day 12) first.")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if args.variants:
        for v in list(VARIANTS):
            if v not in args.variants:
                VARIANTS.pop(v)

    ref = precompute_reference_transforms(load_processed_dataset(PROCESSED_DIR))
    print(f"Loaded {len(ref)} reference skeletons.")
    if args.fresh and os.path.exists(CSV_PATH):
        os.remove(CSV_PATH)
    rows = load_rows()
    done = {(r["variant"], r["grid_n"], r["seed"], r["generations"]) for r in rows}
    tasks = [(v, gn, s, args) for gn in args.grids for v in VARIANTS for s in range(args.seeds)
             if (v, gn, s, args.generations) not in done]
    total = len(args.grids) * len(VARIANTS) * args.seeds
    progress = Progress(total)
    progress.skip(total - len(tasks))
    print(f"{len(tasks)} GA runs to do (workers={args.workers}).")
    if tasks:
        pool = None
        if args.workers > 1:
            import multiprocessing as mp
            pool = mp.Pool(args.workers, initializer=_init_worker, initargs=(PROCESSED_DIR,))
            results = pool.imap_unordered(_worker_task, tasks)
        else:
            results = (run_one(*t, ref) for t in tasks)
        for row in results:
            append_row(row)
            rows.append(row)
            progress.tick(f"{row['variant']} grid={row['grid_n']} seed={row['seed']} "
                          f"sym={row['symmetry']:.2f} loop={row['loop']:.2f} d_min={row['d_min']:.2f}px "
                          f"({row['elapsed_s']:.0f}s)")
        if pool:
            pool.close()
            pool.join()

    out = summarize(rows, args.grids, args.generations)
    plot_genomes(rows, args.grids, args.generations, os.path.join(OUTPUT_DIR, "day12c_genomes.png"))
    with open(SUMMARY_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved {SUMMARY_JSON} and day12c_genomes.png")


if __name__ == "__main__":
    main()
