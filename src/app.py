"""
app.py -- kolamNet Streamlit app (Day 13, Phase 13b: controls, live progress, result, download).

Run from src/:   streamlit run app.py

All logic lives in app_core.py; this file only draws the screen.
(Phase 13c will add the 'closest real Kolam' panel and a seed gallery.)
"""
import json

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

    with st.expander("Advanced"):
        population_size = st.slider("Population size", 6, 100, 30)
        generations = st.slider("Generations", 5, 100, 30)
        sample_size = st.slider("References compared per generation", 10, 200, 50,
                                help="Fewer = faster but noisier scoring.")

    run_clicked = st.button("Evolve a Kolam", type="primary")
    st.caption("A run usually takes a few minutes at the default settings; it depends on your computer.")

# ---------------------------------------------------------------- run
if run_clicked:
    settings = ac.RunSettings(grid_n=int(grid_n), symmetry_mode=symmetry_mode,
                              population_size=int(population_size), generations=int(generations),
                              sample_size=int(sample_size), seed=int(seed))
    try:
        ac.validate_settings(settings)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    bar = st.progress(0.0, text="Starting...")
    chart_slot = st.empty()
    live = {"best": [], "average": []}

    def on_progress(done, total, stats, elapsed):
        live["best"].append(stats["best"])
        live["average"].append(stats["mean"])
        eta = ac.eta_seconds(elapsed, done, total)
        bar.progress(min(done / total, 1.0),
                     text=f"Generation {stats['generation']} of {total - 1} | "
                          f"best fitness {stats['best']:.3f} | time left: {fmt_seconds(eta)}")
        chart_slot.line_chart(live)

    try:
        result = ac.run_evolution(refs, settings, on_progress=on_progress)
    except Exception as e:  # show a readable message instead of a stack trace
        st.error(f"The run failed: {e}")
        st.stop()
    bar.progress(1.0, text=f"Done in {fmt_seconds(result.elapsed_s)}")
    chart_slot.empty()
    # keep results in session_state: clicking a download button reruns the script
    st.session_state["result"] = result
    st.session_state["png"] = ac.render_png(result.genome)

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

    st.subheader("Evolution progress")
    st.line_chart({"best": [h["best"] for h in result.history],
                   "average": [h["mean"] for h in result.history]})
    st.caption("Fitness of the best and the average pattern in each generation.")

with st.expander("About this app"):
    st.write(
        "Each Kolam is a grid of tiles with one of two arc orientations. A genetic algorithm keeps a population "
        "of such grids, scores them for symmetry, closed loops and similarity to real Kolams, and breeds the "
        "best ones. With mirror symmetry switched on, only one quarter of the grid is evolved and the rest is "
        "reflected from it.")
    st.write(
        "Known limits: patterns are simpler than traditional fractal Kolams and have no dot lattice, and the "
        "similarity score mostly measures how dense the pattern is rather than its shape.")
