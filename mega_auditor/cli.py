from __future__ import annotations
import argparse, json, sys, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from .scanner import gather
from .mega_client import RateLimiter, check_link
from .reporting.reports import write_reports

def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mega-auditor", description="Audit public MEGA links, classify learning materials, and create reversible reports.")
    p.add_argument("paths", nargs="*", help="input text/documents/folders; defaults to links.txt, or current directory if absent; use - for stdin")
    p.add_argument("--out", default="mega_results", help="report directory (default: mega_results)")
    p.add_argument("--workers", type=int, default=3, help="concurrent workers (default: 3)")
    p.add_argument("--rate", type=float, default=1.5, help="global API request rate per second (default: 1.5)")
    p.add_argument("--fresh", action="store_true", help="discard saved scan progress and start over")
    p.add_argument("--recheck", action="store_true", help="recheck every discovered link")
    p.add_argument("--classify-only", action="store_true", help="rebuild classification/reports from existing raw_results.json without API calls")
    p.add_argument("--filter-learning", action="store_true", help="prepare ordinary lists with confirmed learning links omitted")
    p.add_argument("--apply", action="store_true", help="actually write filtered report views; without this flag filtering is a dry run")
    p.add_argument("--min-confidence", type=float, default=0.72, help="minimum learning confidence from 0 to 1 (default: 0.72)")
    return p

def _load_json(path: Path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return default

def run(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.workers < 1 or args.rate <= 0 or not 0 <= args.min_confidence <= 1:
        print("workers must be >= 1, rate > 0, and min-confidence between 0 and 1", file=sys.stderr); return 2
    out = Path(args.out)
    if args.filter_learning and not args.apply:
        # This path intentionally performs no writes.
        raw = _load_json(out / "raw_results.json", None)
        if raw is None:
            print(f"No existing raw scan at {out / 'raw_results.json'}. Run a scan first.", file=sys.stderr); return 2
        from .classifier import classify
        selected = [r for r in raw if classify(r, args.min_confidence)["is_learning_material"] is True]
        print("DRY RUN — no files changed")
        print(f"Would omit {len(selected)} confirmed learning-material links from ordinary report lists.")
        print(f"Original raw records would remain in {out / 'raw_results.json'}.")
        print("Review learning_materials.csv and uncertain_classifications.csv before applying.")
        return 0
    if args.classify_only:
        raw = _load_json(out / "raw_results.json", None)
        if raw is None:
            print(f"No existing raw scan at {out / 'raw_results.json'}", file=sys.stderr); return 2
        summary = write_reports(raw, args.out, args.min_confidence, args.filter_learning and args.apply)
        print(summary); return 0
    targets, warnings = gather(args.paths, args.out)
    for warning in warnings: print(f"WARNING: {warning}", file=sys.stderr)
    if not targets:
        print("No MEGA links found in the selected inputs.", file=sys.stderr); return 1
    state_path = out / "state.jsonl"
    if args.fresh and state_path.exists(): state_path.unlink()
    state = {}
    if state_path.exists():
        for line in state_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line); state[row["id"]] = row
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    todo = [t for t in targets if args.recheck or t.id not in state or state[t.id].get("status") == "ERROR"]
    print(f"Found {len(targets)} unique links; cached {len(targets)-len(todo)}; checking {len(todo)}.")
    if todo:
        out.mkdir(parents=True, exist_ok=True); limiter = RateLimiter(args.rate); lock = threading.Lock()
        with state_path.open("a", encoding="utf-8") as sf:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = {pool.submit(check_link, t, limiter): t for t in todo}
                try:
                    for i, future in enumerate(as_completed(futures), 1):
                        target = futures[future]
                        try: row = future.result()
                        except Exception as exc:
                            row = {"id": target.id, "link": target.link, "kind": target.kind, "handle": target.handle,
                                   "key_state": target.key_state, "status": "ERROR", "reason": f"unexpected exception: {type(exc).__name__}: {exc}",
                                   "files": 0, "size_bytes": 0, "name": "", "preview": [], "sources": sorted(target.sources), "source_count": len(target.sources)}
                        state[target.id] = row
                        with lock: sf.write(json.dumps(row, ensure_ascii=False) + "\n"); sf.flush()
                        print(f"[{i}/{len(todo)}] {row.get('status')} | {row.get('name') or row['link']}")
                except KeyboardInterrupt:
                    print("\nInterrupted. Completed results were checkpointed; rerun to resume.", file=sys.stderr)
                    return 130
    # Refresh source references from this scan without discarding historical result data.
    results = []
    for target in targets:
        if target.id in state:
            row = dict(state[target.id]); row.update(link=target.link, sources=sorted(target.sources), source_count=len(target.sources))
            results.append(row)
    summary = write_reports(results, args.out, args.min_confidence, args.filter_learning and args.apply)
    print(summary); print(f"\nReports saved to: {out.resolve()}/")
    if args.filter_learning and args.apply:
        print("Filtered views were written. Raw scan data remains in raw_results.json and raw_results.csv.")
    return 0

def main() -> None:
    raise SystemExit(run())
