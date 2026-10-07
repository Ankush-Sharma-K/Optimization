"""
Smoke test for app.py WITHOUT Streamlit installed: a small fake `streamlit` module
records what the app draws, so we can check the script runs end to end, keeps its
results across reruns, and reports problems with st.error instead of crashing.
(It does NOT check how the page looks -- run `streamlit run app.py` for that.)
Run from src/:  python test_app_ui.py
"""
import os, sys, types, runpy, tempfile

calls = []
class Stop(Exception): pass

class Dummy:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, name):
        def f(*a, **k):
            calls.append((name, a, k)); return False if name == "button" else Dummy()
        return f

class State(dict):
    __getattr__ = dict.get
    def __setattr__(self, k, v): self[k] = v

overrides = {}
def install():
    st = types.ModuleType("streamlit")
    d = Dummy()
    def rec(name, ret=None):
        def f(*a, **k):
            calls.append((name, a, k)); return ret if ret is not None else Dummy()
        return f
    st.sidebar = d
    st.session_state = State()
    for n in ("set_page_config", "title", "caption", "header", "subheader", "markdown", "write", "info",
              "warning", "error", "download_button", "image", "line_chart", "progress", "empty", "expander", "metric"):
        setattr(st, n, rec(n))
    st.selectbox = lambda label, options, index=0, **k: (calls.append(("selectbox", (label,), k)), options[index])[1]
    st.slider = lambda label, lo, hi, value=None, **k: (calls.append(("slider", (label,), k)), overrides.get(label, value))[1]
    st.number_input = lambda label, **k: (calls.append(("number_input", (label,), k)), overrides.get(label, k.get("value")))[1]
    st.radio = lambda label, options, index=0, **k: (calls.append(("radio", (label, tuple(options)), k)),
                                                     overrides.get(label, options[index]))[1]
    st.data_editor = lambda df, **k: (calls.append(("data_editor", (), k)), df)[1]
    st.checkbox = lambda label, value=False, **k: (calls.append(("checkbox", (label,), k)), overrides.get(label, value))[1]
    st.button = lambda label, **k: (calls.append(("button", (label,), k)), overrides.get(label, False))[1]
    st.columns = lambda spec, **k: [Dummy() for _ in range(spec if isinstance(spec, int) else len(spec))]
    def cache_resource(*a, **k):
        return a[0] if a and callable(a[0]) else (lambda f: f)
    st.cache_resource = cache_resource
    def stop(): calls.append(("stop", (), {})); raise Stop()
    st.stop = stop
    sys.modules["streamlit"] = st
    return st

def names(n): return [c for c in calls if c[0] == n]
def run_app():
    calls.clear()
    try:
        runpy.run_path("app.py")
        return "finished"
    except Stop:
        return "stopped"

fails = 0
def check(name, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + name); fails += 0 if cond else 1

st = install()

# 1. first visit: nothing run yet
check("first visit finishes", run_app() == "finished")
check("shows the 'press Evolve' hint", any("Evolve" in str(c[1]) for c in names("info")))
check("no error, no result", not names("error") and st.session_state.get("result") is None)
check("sidebar widgets drawn", len(names("slider")) >= 4 and names("selectbox") and names("button"))

# 2. press Evolve with tiny settings
overrides.update({"Evolve a Kolam": True, "Population size": 6, "Generations": 5,
                  "References compared per generation": 10})
check("run finishes", run_app() == "finished")
res = st.session_state.get("result")
check("result stored in session_state", res is not None and res.settings.grid_n == 13)
check("png stored", st.session_state.get("png", b"")[:8] == b"\x89PNG\r\n\x1a\n")
prog = names("progress")
check("fast mode is on by default", res.settings.fast_mode is True)
check("progress bar updated every generation + start/done", len(prog) >= 6 + 2 and prog[-1][1][0] == 1.0)
check("live chart updated", len(names("line_chart")) >= 6)
check("no error raised", not names("error"))
check("4 metrics + 2 download buttons shown", len(names("metric")) == 4 and len(names("download_button")) == 2)
check("image shown", len(names("image")) == 1)

# 3. rerun (e.g. after clicking a download button): result survives, GA not re-run
overrides["Evolve a Kolam"] = False
before = res
check("rerun finishes", run_app() == "finished")
check("result kept, nothing recomputed", st.session_state["result"] is before and not names("progress"))
check("result still displayed", len(names("metric")) == 4 and len(names("image")) == 1)
check("'last result' option offered once a result exists",
      any("Evolve my last result" in c[1][1] for c in names("radio")))


# 3b. draw my own pattern
overrides.update({"Evolve a Kolam": True, "Where should evolution begin?": "Draw my own pattern"})
check("draw-mode run finishes", run_app() == "finished")
res2 = st.session_state["result"]
check("pattern editor shown", len(names("data_editor")) == 1)
check("start pattern passed to the GA", res2.settings.start_pattern is not None and len(res2.settings.start_pattern) == 144)
check("start picture stored", st.session_state["start_png"][:4] == b"\x89PNG")
check("start picture displayed with the result", len(names("image")) == 3 and not names("error"))
check("freedom mapped to settings", (res2.settings.start_fraction, res2.settings.start_spread) == (0.5, 0.05))

# 3c. evolve my last result
overrides["Where should evolution begin?"] = "Evolve my last result"
check("evolve-last run finishes", run_app() == "finished")
res3 = st.session_state["result"]
check("starts from the previous result", res3.settings.start_pattern == res2.chromosome and not names("error"))
# grid mismatch -> warning + error, no crash
overrides["Grid size (dots per side)"] = 11
check("grid mismatch stops with an error", run_app() == "stopped" and len(names("error")) == 1)
check("grid mismatch warning shown", any("last result used" in str(c[1]) for c in names("warning")))
overrides.pop("Grid size (dots per side)")
overrides.update({"Evolve a Kolam": False, "Where should evolution begin?": "Random start"})
run_app()
check("result survives mode changes", st.session_state["result"] is res3)

# 4. even grid + mirror shows the explanation
overrides.update({"Evolve a Kolam": False, "Grid size (dots per side)": 12})
run_app()
check("odd-tile mirror hint shown", any("middle row" in str(c[1]) for c in names("info")))
overrides.pop("Grid size (dots per side)")

# 5. missing reference data -> friendly error and stop
os.environ["KOLAM_PROCESSED_DIR"] = tempfile.mkdtemp()
for m in ("app_core",):
    sys.modules.pop(m, None)
st = install()
check("missing data stops the app", run_app() == "stopped")
check("missing data shows st.error", len(names("error")) == 1 and "reference" in str(names("error")[0][1]).lower())

print("\nALL PASSED" if fails == 0 else f"\n{fails} FAILED"); sys.exit(1 if fails else 0)
