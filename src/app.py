"""
app.py -- kolamNet Streamlit app (Day 13, Phase 13b: controls, live progress, result, download).

Run from src/:   streamlit run app.py

All logic lives in app_core.py; this file only draws the screen.
Phase 13c-2 adds "start from your own pattern". Still to come: imitate an uploaded image,
the 'closest real Kolam' panel and a seed gallery.
"""
import json

import pandas as pd
import streamlit as st

import app_core as ac

st.set_page_config(page_title="kolamNet", page_icon="🪔", layout="wide")


def fmt_seconds(sec):
    if sec is None:
        return "estimating..."
    sec = int(round(sec))
    return f"{sec // 60}m {sec % 60:02d}s" if sec >= 60 else f"{sec}s"


@st.cache_resource(show_spinner="Loading reference Kolams...")
def get_refs():
    return ac.load_references()


# ---------------------------------------------------------------- header
st.title("kolamNet")
st.caption("A genetic algorithm that evolves Kolam-style patterns. Pick settings on the left, "
           "press **Evolve**, and watch the population improve generation by generation.")

try:
    refs = get_refs()
except FileNotFoundError as e:
    st.error(f"Could not load the reference Kolams. {e}")
    st.stop()

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Settings")
    sym_label = st.selectbox(
        "Symmetry", list(ac.SYMMETRY_CHOICES), index=0,
        help="Forcing symmetry guarantees a symmetric pattern and gave the best loop closure in our tests.")
    symmetry_mode = ac.SYMMETRY_CHOICES[sym_label]

    grid_n = st.slider("Grid size (dots per side)", ac.GRID_RANGE[0], ac.GRID_RANGE[1], 13,
                       help="Bigger grids give denser, more intricate patterns and run slower.")
    if symmetry_mode == "mirror" and (grid_n - 1) % 2 == 1:
        st.info("With this grid size the middle row and column sit on the mirror axis, so a perfect "
                "symmetry score is impossible. Odd grid sizes such as 13 can reach 1.0.")

    seed = st.number_input("Random seed", min_value=0, max_value=999999, value=0, step=1,
                           help="Different seeds give different patterns of similar quality.")

    st.subheader("Starting point")
    last = st.session_state.get("result")
    start_options = ["Random start", "Draw my own pattern"]
    if last is not None:
        start_options.append("Evolve my last result")
    start_mode = st.radio("Where should evolution begin?", start_options, index=0,
                          help="Random start explores freely. Otherwise the GA starts from a pattern you give it.")
    freedom_label = None
    if start_mode != "Random start":
        freedom_label = st.selectbox("How much may it change my pattern?", list(ac.FREEDOM_CHOICES), index=1,
                                     help="The GA still rewards symmetry and closed loops, so it will move away "
                                          "from your pattern to some degree.")
    if start_mode == "Evolve my last result" and last is not None and last.settings.grid_n != grid_n:
        st.warning(f"Your last result used a grid of {last.settings.grid_n}. Set the grid size to "
                   f"{last.settings.grid_n} to evolve it.")

    with st.expander("Advanced"):
        population_size = st.slider("Population size", 6, 100, 30)
        generations = st.slider("Generations", 5, 100, 30)
        sample_size = st.slider("References compared per generation", 10, 200, 50,
                                help="Only used when fast mode is off. Fewer = faster but noisier scoring.")
        fast_mode = st.checkbox("Fast mode (recommended)", value=True,
                                help="Skips the slow picture comparison with real Kolams while evolving. It never "
                                     "changed which pattern won in our tests, and the distance to the closest real "
                                     "Kolam is still measured at the end. Untick to compare during evolution "
                                     "(about 50 times slower).")

    run_clicked = st.button("Evolve a Kolam", type="primary")
    variants_clicked = st.button("Make 6 variants", disabled=not fast_mode,
                                 help="Runs six different random seeds with your settings and shows the results "
                                      "side by side (fast mode only).")
    st.caption("Fast mode: a run takes seconds." if fast_mode else
               "Comparing pictures while evolving: a run usually takes a few minutes, depending on your computer.")

# ---------------------------------------------------------------- starting pattern editor
start_pattern = None
if start_mode == "Draw my own pattern":
    n_tiles = grid_n - 1
    draft = st.session_state.get("draft")
    if draft is None or len(draft) != n_tiles ** 2:
        draft = ac.random_pattern(grid_n, seed=int(seed))
        st.session_state["draft"] = draft
    version = st.session_state.get("draft_version", 0)

    st.subheader("Your starting pattern")
    st.caption(f"Each of the {n_tiles} x {n_tiles} cells picks one of two arc directions: ticked = one direction, "
               "unticked = the other. Edit the table and watch the preview.")
    b1, b2, b3 = st.columns(3)
    new_draft = None
    if b1.button("Randomise"):
        new_draft = ac.random_pattern(grid_n, seed=(version + 1) * 7919 + int(seed))
    if b2.button("All unticked"):
        new_draft = [0] * (n_tiles ** 2)
    if b3.button("Checkerboard"):
        new_draft = [(i // n_tiles + i % n_tiles) % 2 for i in range(n_tiles ** 2)]
    if new_draft is not None:
        draft = new_draft
        st.session_state["draft"] = draft
        st.session_state["draft_version"] = version = version + 1

    table = pd.DataFrame(ac.pattern_to_rows(draft, grid_n), columns=[str(j + 1) for j in range(n_tiles)]).astype(bool)
    ed_col, prev_col = st.columns([3, 2])
    with ed_col:
        edited = st.data_editor(table, key=f"draft_editor_{grid_n}_{version}", hide_index=True)
    start_pattern = ac.rows_to_pattern(edited.values.tolist())
    st.session_state["draft"] = start_pattern
    with prev_col:
        shown = ac.effective_start_pattern(start_pattern, grid_n, symmetry_mode)
        st.image(ac.render_pattern_png(shown, grid_n), width=300,
                 caption="What the GA starts from" + (" (mirrored from the top-left quarter)"
                                                       if symmetry_mode == "mirror" else ""))
elif start_mode == "Evolve my last result" and last is not None and last.settings.grid_n == grid_n:
    start_pattern = list(last.chromosome)

# ---------------------------------------------------------------- helpers
def build_settings():
    """RunSettings from the sidebar; shows an error and stops the app if something is wrong."""
    settings = ac.RunSettings(grid_n=int(grid_n), symmetry_mode=symmetry_mode,
                              population_size=int(population_size), generations=int(generations),
                              sample_size=int(sample_size), seed=int(seed), fast_mode=bool(fast_mode))
    if start_pattern is not None:
        fraction, spread = ac.FREEDOM_CHOICES[freedom_label]
        settings.start_pattern, settings.start_fraction, settings.start_spread = start_pattern, fraction, spread
    elif start_mode == "Evolve my last result":
        st.error("Set the grid size to match your last result first.")
        st.stop()
    try:
        ac.validate_settings(settings)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    return settings


def show_result(result, png, match_png, start_png=None):
    """Keep a result in session_state: clicking a button reruns the whole script."""
    st.session_state["result"] = result
    st.session_state["png"] = png
    st.session_state["match_png"] = match_png
    st.session_state["start_png"] = start_png


# ---------------------------------------------------------------- run
if run_clicked:
    settings = build_settings()
    bar = st.progress(0.0, text="Starting...")
    chart_slot = st.empty()
    live = {"best": [], "average": []}

    def on_progress(done, total, stats, elapsed):
        live["best"].append(stats["best"])
        live["average"].append(stats["mean"])
        eta = ac.eta_seconds(elapsed, done, total)
        bar.progress(min(done / total, 1.0),
                     text=f"Generation {stats['generation']} of {total - 1} | "
                          f"best {'score' if settings.fast_mode else 'fitness'} {stats['best']:.3f} | "
                          f"time left: {fmt_seconds(eta)}")
        chart_slot.line_chart(live)

    try:
        result = ac.run_evolution(refs, settings, on_progress=on_progress)
    except Exception as e:  # show a readable message instead of a stack trace
        st.error(f"The run failed: {e}")
        st.stop()
    bar.progress(1.0, text=f"Done in {fmt_seconds(result.elapsed_s)}")
    chart_slot.empty()
    show_result(result, ac.render_png(result.genome), ac.match_png(result),
                ac.render_pattern_png(ac.effective_start_pattern(start_pattern, settings.grid_n, symmetry_mode),
                                      settings.grid_n) if start_pattern is not None else None)

if variants_clicked:
    settings = build_settings()
    vbar = st.progress(0.0, text="Making variants...")

    def on_variant(done, total, res):
        vbar.progress(done / total, text=f"Variant {done} of {total} | symmetry {res.symmetry:.2f} | "
                                         f"loop closure {res.loop_closure:.2f}")

    try:
        variants = ac.run_variants(refs, settings, n=6, on_progress=on_variant)
    except Exception as e:
        st.error(f"Could not make variants: {e}")
        st.stop()
    vbar.empty()
    st.session_state["gallery"] = [{"result": r, "png": ac.render_png(r.genome), "match_png": ac.match_png(r)}
                                   for r in variants]

# ---------------------------------------------------------------- result
result = st.session_state.get("result")
if result is None:
    st.info("Choose your settings on the left and press **Evolve a Kolam**.")
else:
    s = result.settings
    mode_name = {v: k for k, v in ac.SYMMETRY_CHOICES.items()}[s.symmetry_mode].split(" (")[0]
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Evolved Kolam")
        st.image(st.session_state["png"], width=520,
                 caption=f"Grid {s.grid_n} | symmetry: {mode_name} | seed {s.seed} | {result.elapsed_s:.0f}s")
    with right:
        st.subheader("How good is it?")
        c1, c2 = st.columns(2)
        c1.metric("Fitness", f"{result.best_fitness:.3f}",
                  help="Average of symmetry, loop closure and similarity (0-1, higher is better). "
                       "Forced symmetry raises this automatically.")
        c2.metric("Symmetry", f"{result.symmetry:.2f}", help="1.0 = perfectly symmetric.")
        c3, c4 = st.columns(2)
        c3.metric("Loop closure", f"{result.loop_closure:.2f}",
                  help="Share of the line that forms closed loops. Curves that run off the edge lower it.")
        c4.metric("Distance to closest real Kolam", f"{result.d_min:.2f} px",
                  help="Lower = more similar. Mostly reflects how dense the pattern is, not its shape.")
        st.download_button("Download picture (PNG)", data=st.session_state["png"],
                           file_name=f"kolam_grid{s.grid_n}_seed{s.seed}.png", mime="image/png")
        st.download_button("Download details (JSON)",
                           data=json.dumps(ac.result_summary(result), indent=2),
                           file_name=f"kolam_grid{s.grid_n}_seed{s.seed}.json", mime="application/json")

    if st.session_state.get("match_png"):
        st.subheader("Closest real Kolam in the dataset")
        m1, m2 = st.columns([1, 2])
        with m1:
            st.image(st.session_state["match_png"], width=260,
                     caption=f"{result.match_name} (line drawing)")
        with m2:
            st.write(f"Closest by pixel distance: **{result.d_min:.2f} px** (lower = more alike).")
            st.caption("This is the dataset image whose lines lie nearest to the evolved pattern. Because every "
                       "pattern the GA can build covers the canvas in a similar way, this measures how dense the "
                       "lines are more than how the shapes compare, so expect a loose match, not a copy.")

    if st.session_state.get("start_png"):
        st.subheader("Where it started")
        st.image(st.session_state["start_png"], width=260,
                 caption="The starting pattern (after any symmetry repair) that was evolved into the picture above.")

    st.subheader("Evolution progress")
    st.line_chart({"best": [h["best"] for h in result.history],
                   "average": [h["mean"] for h in result.history]})
    if s.fast_mode:
        st.caption("Score of the best and the average pattern in each generation (average of symmetry and loop "
                   "closure). The comparison with real Kolams is done once, at the end.")
    else:
        st.caption("Fitness of the best and the average pattern in each generation.")

gallery = st.session_state.get("gallery")
if gallery:
    st.subheader("Variants")
    st.caption("Same settings, different random seeds. Press **Show this one** to look at one in detail "
               "(and to use it for 'Evolve my last result').")
    for first in range(0, len(gallery), 3):
        for col, idx in zip(st.columns(3), range(first, min(first + 3, len(gallery)))):
            item = gallery[idx]
            r = item["result"]
            with col:
                st.image(item["png"], width=220,
                         caption=f"Seed {r.settings.seed} | loops {r.loop_closure:.2f} | distance {r.d_min:.2f} px")
                if st.button("Show this one", key=f"show_variant_{idx}"):
                    show_result(r, item["png"], item["match_png"])
                    st.rerun()

with st.expander("About this app"):
    st.write(
        "Each Kolam is a grid of tiles with one of two arc orientations. A genetic algorithm keeps a population "
        "of such grids, scores them for symmetry, closed loops and similarity to real Kolams, and breeds the "
        "best ones. With mirror symmetry switched on, only one quarter of the grid is evolved and the rest is "
        "reflected from it.")
    st.write(
        "Known limits: patterns are simpler than traditional fractal Kolams and have no dot lattice, and the "
        "similarity score mostly measures how dense the pattern is rather than its shape.")
