"""Background scan orchestration shared by the local Streamlit dashboard."""
from __future__ import annotations

import json
import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from queue import Queue
from typing import Any

from .mega_client import RateLimiter, check_link
from .reporting.reports import write_reports
from .scanner import gather


def _load_state(path: Path) -> dict[str, dict[str, Any]]:
    state: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return state
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
            if isinstance(row, dict) and row.get("id"):
                state[str(row["id"])] = row
        except (json.JSONDecodeError, TypeError):
            continue
    return state


def run_scan(
    paths: list[str],
    out_dir: str,
    workers: int,
    rate: float,
    min_confidence: float,
    filter_learning: bool,
    stop_event: threading.Event,
    events: Queue,
    recheck: bool = False,
) -> None:
    """Run a resumable scan and send small progress events to a thread-safe queue."""
    try:
        targets, warnings = gather(paths, out_dir)
        for warning in warnings:
            events.put({"type": "warning", "message": warning})
        if not targets:
            events.put({"type": "finished", "ok": False, "message": "No MEGA links found in the selected inputs."})
            return

        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        state_path = out / "state.jsonl"
        state = _load_state(state_path)
        todo = [t for t in targets if recheck or t.id not in state or state[t.id].get("status") == "ERROR"]
        completed_before = len(targets) - len(todo)
        events.put({
            "type": "started", "total": len(targets), "cached": completed_before,
            "todo": len(todo), "completed": completed_before,
        })

        if todo and not stop_event.is_set():
            limiter = RateLimiter(rate)
            lock = threading.Lock()
            state_file = state_path.open("a", encoding="utf-8")
            executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="mega-audit")
            futures = {executor.submit(check_link, target, limiter): target for target in todo}
            pending = set(futures)
            try:
                while pending and not stop_event.is_set():
                    done, pending = wait(pending, timeout=0.4, return_when=FIRST_COMPLETED)
                    for future in done:
                        target = futures[future]
                        try:
                            row = future.result()
                        except Exception as exc:  # defensive boundary around individual jobs
                            row = {
                                "id": target.id, "link": target.link, "kind": target.kind,
                                "handle": target.handle, "key_state": target.key_state,
                                "status": "ERROR", "reason": f"unexpected exception: {type(exc).__name__}: {exc}",
                                "files": 0, "size_bytes": 0, "name": "", "preview": [],
                                "sources": sorted(target.sources), "source_count": len(target.sources),
                            }
                        state[target.id] = row
                        with lock:
                            state_file.write(json.dumps(row, ensure_ascii=False) + "\n")
                            state_file.flush()
                        events.put({"type": "result", "row": row, "completed": len(targets) - len(pending) - (len(todo) - len(pending) - len(done))})
                stopped = stop_event.is_set()
                if stopped:
                    # Do not start queued requests after Stop. Any request already in-flight
                    # may finish in its worker, but will be retried on resume if not checkpointed.
                    for future in pending:
                        future.cancel()
                    events.put({"type": "stopping", "message": "Stopping safely; saved checkpoints will be kept."})
            finally:
                state_file.close()
                executor.shutdown(wait=False, cancel_futures=True)

        results = []
        for target in targets:
            if target.id in state:
                row = dict(state[target.id])
                row.update(link=target.link, sources=sorted(target.sources), source_count=len(target.sources))
                results.append(row)
        # Reports include all completed/cached rows, even if the user stopped partway through.
        summary = write_reports(results, out_dir, min_confidence, filter_learning)
        events.put({
            "type": "finished", "ok": True,
            "message": "Scan stopped and checkpointed." if stop_event.is_set() else "Scan complete.",
            "summary": summary, "results_count": len(results), "target_count": len(targets),
            "reports_dir": str(out.resolve()),
        })
    except Exception as exc:
        events.put({"type": "finished", "ok": False, "message": f"{type(exc).__name__}: {exc}"})
