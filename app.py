from __future__ import annotations

import json
import threading
from pathlib import Path
from queue import Empty, Queue

import pandas as pd
import streamlit as st

from mega_auditor.gui_service import run_scan

st.set_page_config(page_title="MEGA Auditor", page_icon="🔎", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1.6rem; padding-bottom: 2rem; }
    [data-testid="stMetric"] { border: 1px solid rgba(128,128,128,.25); padding: 1rem; border-radius: .8rem; }
    .muted { color: var(--text-color); opacity: .7; }
</style>
""", unsafe_allow_html=True)

st.title("🔎 MEGA Auditor")
st.caption("Local dashboard · Public-link metadata checks only · No MEGA login or file downloads")

if "scan_events" not in st.session_state:
    st.session_state.scan_events = Queue()
if "scan_stop" not in st.session_state:
    st.session_state.scan_stop = threading.Event()
if "scan_thread" not in st.session_state:
    st.session_state.scan_thread = None
if "scan_state" not in st.session_state:
    st.session_state.scan_state = {
        "running": False, "started": False, "total": 0, "cached": 0,
        "todo": 0, "completed": 0, "rows": [], "warnings": [],
        "message": "Ready to scan.", "summary": "", "reports_dir": "",
    }

with st.sidebar:
    st.header("Scan settings")
    input_text = st.text_area(
        "Input paths (one per line)", value="links.txt", height=100,
        help="Paths are relative to the folder where you launch Streamlit, or absolute paths. You can enter files or folders.",
    )
    output_dir = st.text_input("Output folder", value="mega_results")
    workers = st.slider("Concurrent workers", min_value=1, max_value=8, value=3)
    rate = st.number_input("API requests per second", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
    confidence = st.slider("Learning-material confidence threshold", 0.0, 1.0, 0.72, 0.01)
    filter_learning = st.checkbox("Exclude confirmed learning items from ordinary reports", value=False)
    recheck = st.checkbox("Recheck links already in the checkpoint", value=False)
    st.caption("Use a conservative request rate. API responses can be inconclusive; INACCESSIBLE does not always mean permanently dead.")

state = st.session_state.scan_state
thread = st.session_state.scan_thread
is_alive = bool(thread and thread.is_alive())

col_start, col_stop, col_refresh = st.columns([1, 1, 1])
with col_start:
    start_clicked = st.button("▶ Start / Resume scan", type="primary", use_container_width=True, disabled=is_alive)
with col_stop:
    stop_clicked = st.button("■ Stop safely", use_container_width=True, disabled=not is_alive)
with col_refresh:
    refresh_clicked = st.button("↻ Refresh results", use_container_width=True)

if start_clicked:
    paths = [line.strip() for line in input_text.splitlines() if line.strip()]
    if not paths:
        st.error("Enter at least one input file or folder path.")
    else:
        st.session_state.scan_stop = threading.Event()
        st.session_state.scan_events = Queue()
        st.session_state.scan_state = {
            "running": True, "started": False, "total": 0, "cached": 0,
            "todo": 0, "completed": 0, "rows": [], "warnings": [],
            "message": "Starting scan…", "summary": "", "reports_dir": "",
        }
        worker = threading.Thread(
            target=run_scan,
            args=(paths, output_dir, workers, rate, confidence, filter_learning,
                  st.session_state.scan_stop, st.session_state.scan_events, recheck),
            daemon=True,
            name="mega-auditor-gui-scan",
        )
        st.session_state.scan_thread = worker
        worker.start()
        st.rerun()

if stop_clicked:
    st.session_state.scan_stop.set()
    state["message"] = "Stop requested. Finishing checkpoint handling…"

# Load reports from disk so the page can be reopened after a restart.
def load_report_rows(folder: str) -> list[dict]:
    path = Path(folder) / "classified_results.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []

# Drain worker events on each page refresh.
queue = st.session_state.scan_events
while True:
    try:
        event = queue.get_nowait()
    except Empty:
        break
    kind = event.get("type")
    if kind == "started":
        state.update(started=True, total=event["total"], cached=event["cached"], todo=event["todo"], completed=event["completed"])
        state["message"] = "Scanning links…"
    elif kind == "result":
        state["rows"].append(event["row"])
        state["completed"] = min(state.get("total", 0), state.get("cached", 0) + len(state["rows"]))
    elif kind == "warning":
        state["warnings"].append(event["message"])
    elif kind == "stopping":
        state["message"] = event["message"]
    elif kind == "finished":
        state["running"] = False
        state["message"] = event.get("message", "Finished.")
        state["summary"] = event.get("summary", "")
        state["reports_dir"] = event.get("reports_dir", output_dir)
        if event.get("ok"):
            state["rows"] = load_report_rows(state["reports_dir"])
            state["completed"] = event.get("results_count", len(state["rows"]))
            state["total"] = event.get("target_count", state.get("total", 0))
        else:
            st.error(state["message"])

# Load latest report on initial page view or explicit refresh.
if refresh_clicked or not state["rows"]:
    disk_rows = load_report_rows(output_dir)
    if disk_rows:
        state["rows"] = disk_rows
        state["reports_dir"] = str(Path(output_dir).resolve())

# Live progress panel is isolated so it refreshes while the worker runs.
@st.fragment(run_every="1s")
def progress_panel():
    s = st.session_state.scan_state
    q = st.session_state.scan_events
    while True:
        try:
            event = q.get_nowait()
        except Empty:
            break
        kind = event.get("type")
        if kind == "started":
            s.update(started=True, total=event["total"], cached=event["cached"], todo=event["todo"], completed=event["completed"])
            s["message"] = "Scanning links…"
        elif kind == "result":
            s["rows"].append(event["row"])
            s["completed"] = min(s.get("total", 0), s.get("cached", 0) + len(s["rows"]))
        elif kind == "warning":
            s["warnings"].append(event["message"])
        elif kind == "stopping":
            s["message"] = event["message"]
        elif kind == "finished":
            s["running"] = False
            s["message"] = event.get("message", "Finished.")
            s["summary"] = event.get("summary", "")
            s["reports_dir"] = event.get("reports_dir", output_dir)
            if event.get("ok"):
                s["rows"] = load_report_rows(s["reports_dir"])
                s["completed"] = event.get("results_count", len(s["rows"]))
                s["total"] = event.get("target_count", s.get("total", 0))
            else:
                s["error"] = s["message"]
    if s.get("error"):
        st.error(s["error"])
    st.write(s.get("message", "Ready to scan."))
    total = int(s.get("total", 0))
    completed = int(s.get("completed", 0))
    if total:
        st.progress(min(1.0, completed / total), text=f"{completed:,} / {total:,} links represented in current results")
    m1, m2, m3, m4 = st.columns(4)
    rows = s.get("rows", [])
    m1.metric("Discovered", f"{total:,}" if total else "—")
    m2.metric("Results available", f"{len(rows):,}")
    m3.metric("Working", sum(1 for r in rows if r.get("status") == "WORKING"))
    m4.metric("Needs review", sum(1 for r in rows if r.get("review_required")))

progress_panel()

for warning in state.get("warnings", [])[-5:]:
    st.warning(warning)

rows = state.get("rows", [])
if rows:
    st.subheader("Results")
    df = pd.DataFrame(rows)
    if "is_learning_material" in df.columns:
        df["learning_label"] = df["is_learning_material"].map({True: "Learning", False: "Not learning", None: "Uncertain"}).fillna("Uncertain")
    else:
        df["learning_label"] = "Unclassified"
    f1, f2, f3 = st.columns(3)
    with f1:
        statuses = sorted(str(v) for v in df.get("status", pd.Series(dtype=str)).dropna().unique())
        status_filter = st.multiselect("Status", statuses, default=statuses)
    with f2:
        learn_options = sorted(str(v) for v in df["learning_label"].dropna().unique())
        learning_filter = st.multiselect("Classification", learn_options, default=learn_options)
    with f3:
        search = st.text_input("Search title / category / source / link", placeholder="Type to filter results")

    filtered = df.copy()
    if "status" in filtered.columns and status_filter:
        filtered = filtered[filtered["status"].astype(str).isin(status_filter)]
    elif "status" in filtered.columns and not status_filter:
        filtered = filtered.iloc[0:0]
    filtered = filtered[filtered["learning_label"].astype(str).isin(learning_filter)] if learning_filter else filtered.iloc[0:0]
    if search.strip():
        searchable = [c for c in ["name", "primary_category", "classification_reason", "sources", "link", "status"] if c in filtered.columns]
        mask = filtered[searchable].astype(str).apply(lambda col: col.str.contains(search.strip(), case=False, na=False, regex=False)).any(axis=1)
        filtered = filtered[mask]

    preferred = ["status", "name", "size_bytes", "files", "learning_label", "learning_confidence", "primary_category", "review_required", "reason", "link", "sources"]
    display_cols = [c for c in preferred if c in filtered.columns]
    st.caption(f"Showing {len(filtered):,} of {len(df):,} records. Link metadata is based on public API responses and may be inconclusive.")
    st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("Download filtered results CSV", filtered.to_csv(index=False).encode("utf-8-sig"), "mega_filtered_results.csv", "text/csv", use_container_width=True)
    with c2:
        st.download_button("Download all loaded results JSON", json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8"), "mega_results.json", "application/json", use_container_width=True)
    with c3:
        report_dir = Path(state.get("reports_dir") or output_dir)
        summary_path = report_dir / "summary.txt"
        if summary_path.exists():
            st.download_button("Download summary", summary_path.read_bytes(), "summary.txt", "text/plain", use_container_width=True)

    if state.get("summary"):
        with st.expander("Scan summary"):
            st.code(state["summary"], language=None)
else:
    st.info("No report data loaded yet. Enter your input path in the sidebar and start a scan, or use Refresh results to load an existing report.")

st.divider()
st.caption("Security note: keep links.txt and generated scan reports private. The dashboard is intended for localhost use only.")
