"""
Day 12 -- Experiments & tuning for kolamNet.

Compares GA settings one factor at a time (greedy, in a fixed order), over
several seeds, and writes:
  outputs/day12_results.csv        every single run (resumable)
  outputs/day12_experiments.png    mean +/- s.e. per setting, per experiment
  outputs/day12_scale_analysis.png / printed table for similarity `scale`
  outputs/day12_best_config.json   the tuned defaults for the Streamlit app

IMPORTANT DESIGN POINT -- a common yardstick:
  Settings such as fitness weights change what `run_ga` optimises, so the GA's
  own `best_fitness` is NOT comparable across settings. Every run's final best
  genome is therefore re-scored with the *default* `fitness()` against ALL
  references. That number (`yardstick`) is what settings are ranked by.

Usage (from src/):
  python experiments.py --quick                  # smoke test, a few minutes
  python experiments.py                          # full run (resumable)
  python experiments.py --only crossover mutation
  python experiments.py --scale-only             # just the similarity-scale analysis
"""
import argparse
import csv
import inspect
import json
import math
import os
import random
import time
from typing import Dict, List, Tuple

import numpy as np

from grid import PulliGrid
from population import Population
from ga import GAConfig, run_ga
from fitness import fitness, symmetry_score, loop_closure_score
from similarity import precompute_reference_transforms, similarity_score
from dataset import load_processed_dataset
from crossover import CROSSOVER_METHODS
from mutation import MUTATION_METHODS

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_HERE, "..", "outputs")
PROCESSED_DIR = os.path.join(_HERE, "..", "data", "processed")
RESULTS_CSV = os.path.join(OUTPUT_DIR, "day12_results.csv")
BEST_CONFIG_JSON = os.path.join(OUTPUT_DIR, "day12_best_config.json")

DEFAULT_GRID_N = 6   # matches visualize_ga.py (6x6 dots -> 5x5 cells)
SCALE_CANDIDATES = (5.0, 10.0, 20.0, 40.0, 80.0)
CSV_FIELDS = ["experiment", "label", "base", "seed", "yardstick", "own_fitness",
              "symmetry", "loop", "similarity", "elapsed_s",
              "gen_of_best", "final_diversity"]

# --------------------------------------------------------------------------
# Experiment definitions.  Each experiment = (default_label, [(label, overrides)])
# Override keys: any GAConfig field, plus the special keys
#   "grid_n"        -> PulliGrid(n=...)
#   "rate_mult"     -> mutation_rate = rate_mult / chromosome_length
#   "fitness_kwargs"-> merged into GAConfig.fitness_kwargs
# The first listed label is NOT special; `default_label` marks the incumbent.
# --------------------------------------------------------------------------
def _weights(s, l, m):
    return {"fitness_kwargs": {"symmetry_weight": s, "loop_weight": l,
                               "similarity_weight": m}}


def build_experiments() -> Dict[str, Tuple[str, List[Tuple[str, dict]]]]:
    exps = {
        "crossover": ("block", [(m, {"crossover_method": m}) for m in CROSSOVER_METHODS]),
        "mutation": ("flip", [(m, {"mutation_method": m}) for m in MUTATION_METHODS]),
        "tournament": ("3", [(str(k), {"tournament_size": k}) for k in (2, 3, 5)]),
        "elite": ("2", [(str(k), {"elite_count": k}) for k in (0, 2, 4)]),
        "mut_rate": ("1x", [(f"{m:g}x", {"rate_mult": m}) for m in (0.5, 1, 2)]),
        "population": ("30", [(str(p), {"population_size": p}) for p in (20, 30, 50)]),  # optional: only with --only population
        "scale": None,  # placeholder to fix ordering; replaced below
        "weights": ("equal", [
            ("equal", _weights(1 / 3, 1 / 3, 1 / 3)),
            ("sim-heavy", _weights(0.2, 0.2, 0.6)),
            ("struct-heavy", _weights(0.4, 0.4, 0.2)),
        ]),
        "grid": ("6", [(str(n), {"grid_n": n}) for n in (6, 8, 10)]),
    }
    # The similarity `scale` can only be tuned inside the GA if fitness() accepts it.
    if "similarity_scale" not in inspect.signature(fitness).parameters:
        exps.pop("scale")
    else:
        exps["scale"] = ("20", [(f"{s:g}", {"fitness_kwargs": {"similarity_scale": s}})
                                for s in SCALE_CANDIDATES])
    return exps


# --------------------------------------------------------------------------
# Building + running one configuration
# --------------------------------------------------------------------------
def build_run(base: dict, overrides: dict, args) -> Tuple[PulliGrid, GAConfig]:
    o = {**base, **overrides}
    fk = {**base.get("fitness_kwargs", {}), **overrides.get("fitness_kwargs", {})}
    o.pop("fitness_kwargs", None)
    grid_n = o.pop("grid_n", args.grid_n)
    rate_mult = o.pop("rate_mult", None)

    kw = dict(population_size=args.pop, generations=args.generations,
              sample_size=args.sample, elite_count=2)
    kw.update(o)
    if rate_mult is not None:
        kw["mutation_rate"] = rate_mult / float((grid_n - 1) ** 2)
    kw["fitness_kwargs"] = fk
    return PulliGrid(n=grid_n), GAConfig(**kw)


_WORKER_REF = None


def _init_worker(processed_dir):
    """Each worker process loads the reference transforms once."""
    global _WORKER_REF
    _WORKER_REF = precompute_reference_transforms(load_processed_dataset(processed_dir))


def _worker_task(task):
    experiment, label, overrides, seed, base, args = task
    return run_one(experiment, label, overrides, seed, base, args, _WORKER_REF)


class Progress:
    """Run-level progress bar with elapsed time and ETA (wall clock, so it is
    correct with --workers too). Runs already saved in the CSV count as done
    but are not used to estimate speed."""

    def __init__(self, total, width=24):
        self.total, self.width = total, width
        self.done = self.ran = 0
        self.t0 = time.time()

    @staticmethod
    def _fmt(sec):
        sec = int(max(sec, 0))
        h, r = divmod(sec, 3600)
        m, s = divmod(r, 60)
        return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"

    def skip(self, n):
        self.done += n

    def line(self, msg=""):
        frac = self.done / self.total if self.total else 1.0
        filled = int(self.width * frac)
        bar = "#" * filled + "-" * (self.width - filled)
        elapsed = time.time() - self.t0
        eta = (elapsed / self.ran) * (self.total - self.done) if self.ran else None
        eta_s = self._fmt(eta) if eta is not None else "..."
        return (f"[{bar}] {self.done}/{self.total} ({100 * frac:3.0f}%) "
                f"elapsed {self._fmt(elapsed)} | ETA ~{eta_s} | {msg}")

    def tick(self, msg=""):
        self.done += 1
        self.ran += 1
        print(self.line(msg), flush=True)


OPTIONAL = {"population"}   # only run when asked for with --only


def run_one(experiment, label, overrides, seed, base, args, ref, verbose=False) -> dict:
    grid, cfg = build_run(base, overrides, args)
    cfg.seed = seed
    t0 = time.time()
    cb = None
    if verbose:   # serial mode only: show life signs inside a long run
        def cb(st, total=cfg.generations):
            if st["generation"] % 5 == 0:
                print(f"      {experiment}={label} seed={seed}: generation "
                      f"{st['generation']}/{total}", flush=True)
    res = run_ga(grid, ref, cfg, callback=cb)
    elapsed = time.time() - t0
    g = res.best_genome
    hist_best = [h["best"] for h in res.history]
    return {
        "experiment": experiment, "label": label,
        "base": json.dumps(base, sort_keys=True), "seed": seed,
        "yardstick": fitness(g, reference_transforms=ref),   # default weights, ALL refs
        "own_fitness": res.best_fitness,
        "symmetry": symmetry_score(g), "loop": loop_closure_score(g),
        "similarity": similarity_score(g, ref),
        "elapsed_s": round(elapsed, 2),
        "gen_of_best": int(np.argmax(hist_best)),
        "final_diversity": res.history[-1]["diversity"],
    }


# --------------------------------------------------------------------------
# Results store (CSV, resumable)
# --------------------------------------------------------------------------
def load_rows(path=RESULTS_CSV) -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("yardstick", "own_fitness", "symmetry", "loop", "similarity",
                  "elapsed_s", "final_diversity"):
            r[k] = float(r[k])
        r["seed"] = int(r["seed"])
        r["gen_of_best"] = int(r["gen_of_best"])
    return rows


def append_row(row: dict, path=RESULTS_CSV):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def _key(r):
    return (r["experiment"], r["label"], r["base"], int(r["seed"]))


# --------------------------------------------------------------------------
# Summaries
# --------------------------------------------------------------------------
def summarize(rows, experiment, base) -> Dict[str, dict]:
    """label -> stats for runs of `experiment` under exactly this `base`."""
    bj = json.dumps(base, sort_keys=True)
    by = {}
    for r in rows:
        if r["experiment"] == experiment and r["base"] == bj:
            by.setdefault(r["label"], []).append(r)
    out = {}
    for label, rs in by.items():
        y = np.array([r["yardstick"] for r in rs])
        n = len(y)
        out[label] = {
            "n": n, "mean": float(y.mean()),
            "se": float(y.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan"),
            "symmetry": float(np.mean([r["symmetry"] for r in rs])),
            "loop": float(np.mean([r["loop"] for r in rs])),
            "similarity": float(np.mean([r["similarity"] for r in rs])),
            "time": float(np.mean([r["elapsed_s"] for r in rs])),
            "gen_of_best": float(np.mean([r["gen_of_best"] for r in rs])),
            "diversity": float(np.mean([r["final_diversity"] for r in rs])),
        }
    return out


def pick_winner(stats: Dict[str, dict], default_label: str):
    """Return (label, verdict). A challenger replaces the default only if it
    beats it by more than the combined standard error."""
    best = max(stats, key=lambda k: stats[k]["mean"])
    if best == default_label or default_label not in stats:
        return best, "default kept" if best == default_label else "no default run"
    diff = stats[best]["mean"] - stats[default_label]["mean"]
    se = math.sqrt(np.nan_to_num(stats[best]["se"]) ** 2 +
                   np.nan_to_num(stats[default_label]["se"]) ** 2)
    if se > 0 and diff > 2 * se:
        return best, f"clear win (+{diff:.4f}, >2 s.e.)"
    if se > 0 and diff > se:
        return best, f"marginal win (+{diff:.4f}, 1-2 s.e.)"
    return default_label, f"within noise (best +{diff:.4f} vs s.e. {se:.4f}); default kept"


def print_table(experiment, stats, default_label):
    print(f"\n=== {experiment}  (yardstick = default fitness on all refs) ===")
    print(f"{'setting':>14} {'n':>2} {'mean':>7} {'s.e.':>7} {'sym':>6} {'loop':>6} "
          f"{'sim':>6} {'gen*':>5} {'div':>5} {'sec':>6}")
    for label, s in sorted(stats.items(), key=lambda kv: -kv[1]["mean"]):
        tag = " <- default" if label == default_label else ""
        print(f"{label:>14} {s['n']:>2} {s['mean']:>7.4f} {s['se']:>7.4f} "
              f"{s['symmetry']:>6.3f} {s['loop']:>6.3f} {s['similarity']:>6.3f} "
              f"{s['gen_of_best']:>5.1f} {s['diversity']:>5.2f} {s['time']:>6.1f}{tag}")


# --------------------------------------------------------------------------
# Similarity-scale analysis (works even without a fitness() edit)
# --------------------------------------------------------------------------
def scale_analysis(grid, ref, n_random=40, seed=0, scales=SCALE_CANDIDATES):
    """exp(-d/scale) with the Chamfer distance d recovered from the scale-20
    score. Reports how well each candidate scale separates random genomes."""
    pop = Population(grid, n_random, seed=seed).initialize()
    s20 = np.array([similarity_score(g, ref, scale=20.0) for g in pop])
    d = -20.0 * np.log(np.clip(s20, 1e-12, 1.0))
    print(f"\n=== similarity scale analysis ({n_random} random genomes, n={grid.n}) ===")
    print(f"Chamfer distance d: min {d.min():.1f}  median {np.median(d):.1f}  max {d.max():.1f}")
    print(f"{'scale':>6} {'mean':>7} {'std':>7} {'min':>7} {'max':>7}")
    rows = []
    for s in scales:
        v = np.exp(-d / s)
        rows.append((s, float(v.mean()), float(v.std()), float(v.min()), float(v.max())))
        print(f"{s:>6g} {v.mean():>7.3f} {v.std():>7.3f} {v.min():>7.3f} {v.max():>7.3f}")
    best = max(rows, key=lambda r: r[2])[0]
    print(f"Largest spread (std) at scale = {best:g}.  Heuristic: pick the scale where "
          f"scores spread widely without saturating near 0 or 1.")
    return d, rows


def plot_scale(d, rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 4))
    grid_d = np.linspace(0, max(d.max() * 1.2, 1), 200)
    for s, *_ in rows:
        ax.plot(grid_d, np.exp(-grid_d / s), label=f"scale {s:g}")
    ax.scatter(d, np.zeros_like(d), marker="|", color="k", s=200, label="random genomes")
    ax.set_xlabel("Chamfer distance to best reference")
    ax.set_ylabel("similarity score")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------
# Plot of all experiments
# --------------------------------------------------------------------------
def plot_experiments(all_stats: Dict[str, Tuple[dict, str, str]], path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = list(all_stats)
    if not names:
        return
    cols = min(3, len(names))
    rows_ = math.ceil(len(names) / cols)
    fig, axes = plt.subplots(rows_, cols, figsize=(4.6 * cols, 3.4 * rows_), squeeze=False)
    for ax, name in zip(axes.flat, names):
        stats, default_label, winner = all_stats[name]
        labels = list(stats)
        means = [stats[k]["mean"] for k in labels]
        ses = [np.nan_to_num(stats[k]["se"]) for k in labels]
        colors = ["#8B2E2E" if k == winner else ("#999999" if k != default_label else "#4a6fa5")
                  for k in labels]
        ax.bar(range(len(labels)), means, yerr=ses, color=colors, capsize=3)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=8, rotation=20)
        lo = min(m - e for m, e in zip(means, ses))
        hi = max(m + e for m, e in zip(means, ses))
        pad = max((hi - lo) * 0.3, 0.005)
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_title(f"{name}  (blue=default, red=chosen)", fontsize=9)
        ax.set_ylabel("yardstick fitness")
    for ax in list(axes.flat)[len(names):]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------
# Tuned config for the app
# --------------------------------------------------------------------------
def tuned_config(path=BEST_CONFIG_JSON, **overrides):
    """Return (grid_n, GAConfig) built from the Day 12 result file.
    Extra keyword args override GAConfig fields (e.g. generations=40)."""
    with open(path) as f:
        spec = json.load(f)
    ns = argparse.Namespace(pop=spec["population_size"], generations=spec["generations"],
                            sample=spec["sample_size"], grid_n=spec["grid_n"])
    grid, cfg = build_run(spec["overrides"], {}, ns)
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return grid.n, cfg


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="2 seeds, 15 gens, pop 20, 30 refs/gen")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--generations", type=int, default=30)
    ap.add_argument("--pop", type=int, default=30)
    ap.add_argument("--sample", type=int, default=50, help="references sampled per generation")
    ap.add_argument("--grid-n", type=int, default=DEFAULT_GRID_N)
    ap.add_argument("--only", nargs="*", help="run only these experiments")
    ap.add_argument("--fresh", action="store_true", help="ignore/overwrite saved results")
    ap.add_argument("--scale-only", action="store_true")
    ap.add_argument("--workers", type=int, default=1,
                    help="parallel processes (try cpu_count-1); results are identical to --workers 1")
    args = ap.parse_args()
    if args.quick:
        args.seeds, args.generations, args.pop, args.sample = 2, 15, 20, 30

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dataset = load_processed_dataset(PROCESSED_DIR)
    if not dataset:
        raise SystemExit(f"No cached skeletons in {PROCESSED_DIR} -- run the Day 6 caching first.")
    ref = precompute_reference_transforms(dataset)
    print(f"Loaded {len(ref)} reference skeletons.")

    d, srows = scale_analysis(PulliGrid(n=args.grid_n), ref)
    plot_scale(d, srows, os.path.join(OUTPUT_DIR, "day12_scale_analysis.png"))
    if args.scale_only:
        return

    if args.fresh and os.path.exists(RESULTS_CSV):
        os.remove(RESULTS_CSV)
    rows = load_rows()
    done = {_key(r) for r in rows}

    exps = build_experiments()
    if "scale" not in exps:
        print("\nNote: fitness() has no `similarity_scale` argument, so scale is analysed "
              "above but not tuned inside the GA (see Day 12 notes for the 1-line patch).")
    names = [n for n in exps if (n in args.only if args.only else n not in OPTIONAL)]
    pool = None
    if args.workers > 1:
        import multiprocessing as mp
        pool = mp.Pool(args.workers, initializer=_init_worker, initargs=(PROCESSED_DIR,))
    seeds = list(range(args.seeds))

    progress = Progress(sum(len(exps[n][1]) * len(seeds) for n in names))
    print(f"\nTotal: {progress.total} runs planned "
          f"(workers={args.workers}). Progress lines show elapsed time and ETA.")
    base: dict = {}
    all_stats = {}
    for name in names:
        default_label, settings = exps[name]
        print(f"\n##### {name}  (base so far: {base or 'GAConfig defaults'})")
        tasks = []
        for label, ov in settings:
            for seed in seeds:
                probe = {"experiment": name, "label": label,
                         "base": json.dumps(base, sort_keys=True), "seed": seed}
                if _key(probe) not in done:
                    tasks.append((name, label, ov, seed, dict(base), args))
        progress.skip(len(settings) * len(seeds) - len(tasks))   # already saved
        results = (pool.imap_unordered(_worker_task, tasks) if pool
                   else (run_one(*t[:6], ref, verbose=True) for t in tasks))
        for row in results:
            append_row(row)
            rows.append(row)
            done.add(_key(row))
            progress.tick(f"{row['experiment']}={row['label']} seed={row['seed']} "
                          f"yardstick={row['yardstick']:.4f} ({row['elapsed_s']:.0f}s)")
        stats = summarize(rows, name, base)
        winner, verdict = pick_winner(stats, default_label)
        print_table(name, stats, default_label)
        print(f"--> {name}: choose '{winner}'  [{verdict}]")
        all_stats[name] = (stats, default_label, winner)
        win_ov = dict(dict(settings)[winner])
        if "fitness_kwargs" in win_ov:
            win_ov["fitness_kwargs"] = {**base.get("fitness_kwargs", {}), **win_ov["fitness_kwargs"]}
        base = {**base, **win_ov}

    if pool:
        pool.close()
        pool.join()
    plot_experiments(all_stats, os.path.join(OUTPUT_DIR, "day12_experiments.png"))
    spec = {"overrides": base, "population_size": args.pop, "generations": args.generations,
            "sample_size": args.sample, "grid_n": base.get("grid_n", args.grid_n),
            "note": "Chosen greedily one factor at a time; see day12_results.csv"}
    with open(BEST_CONFIG_JSON, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"\nSaved {BEST_CONFIG_JSON}\n{json.dumps(spec, indent=2)}")


if __name__ == "__main__":
    main()