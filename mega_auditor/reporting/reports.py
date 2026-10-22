from __future__ import annotations
import csv, json
from pathlib import Path
from typing import Any
from ..mega_client import human
from ..classifier import classify

GB = 1024**3
BUCKETS = [("01_under_100MB", 0, 100*1024**2), ("02_100MB_to_1GB", 100*1024**2, GB), ("03_1GB_to_5GB", GB, 5*GB), ("04_5GB_to_10GB", 5*GB, 10*GB), ("05_10GB_to_50GB", 10*GB, 50*GB), ("06_50GB_plus", 50*GB, float("inf"))]

def bucket(size: int) -> str:
    return next((name for name, lo, hi in BUCKETS if lo <= size < hi), BUCKETS[-1][0])
def write_lines(path: Path, values: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(v + "\n" for v in values), encoding="utf-8")

def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig"); return
    fields = list(dict.fromkeys(k for row in rows for k in row.keys()))
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)

def write_reports(results: list[dict[str, Any]], out_dir: str, min_confidence: float = 0.72, filter_learning: bool = False) -> str:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    enriched = []
    for raw in results:
        row = dict(raw)
        row["size_bucket"] = bucket(int(row.get("size_bytes") or 0)) if row.get("status") in {"WORKING", "EMPTY"} else ""
        row.update(classify(row, min_confidence))
        row["sources"] = row.get("sources") or []
        row["preview"] = row.get("preview") or []
        enriched.append(row)
    # Immutable audit records are written separately from derived category views.
    _write_csv(out / "raw_results.csv", results)
    (out / "raw_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_csv(out / "classified_results.csv", enriched)
    (out / "classified_results.json").write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")
    learning = [r for r in enriched if r["is_learning_material"] is True]
    uncertain = [r for r in enriched if r["review_required"]]
    _write_csv(out / "learning_materials.csv", learning)
    write_lines(out / "learning_materials.txt", [r["link"] for r in learning])
    _write_csv(out / "uncertain_classifications.csv", uncertain)
    _write_csv(out / "classification_exclusions.csv", learning if filter_learning else [])

    # All category views are rebuilt from the complete classified set. --filter-learning
    # omits only confirmed learning rows from the ordinary lists; raw results are untouched.
    view = [r for r in enriched if not (filter_learning and r["is_learning_material"] is True)]
    statuses: dict[str, list[dict[str, Any]]] = {}
    for row in view: statuses.setdefault(str(row.get("status", "UNKNOWN")), []).append(row)
    working = sorted([r for r in view if r.get("status") == "WORKING"], key=lambda r: -int(r.get("size_bytes") or 0))
    write_lines(out / "all_unique_links.txt", [r["link"] for r in sorted(view, key=lambda r: -int(r.get("size_bytes") or 0))])
    write_lines(out / "working/all_working.txt", [r["link"] for r in working])
    write_lines(out / "working/over_1GB.txt", [r["link"] for r in working if int(r.get("size_bytes") or 0) >= GB])
    write_lines(out / "working/under_1GB.txt", [r["link"] for r in working if int(r.get("size_bytes") or 0) < GB])
    for name, lo, hi in BUCKETS:
        write_lines(out / f"working/by_size/{name}.txt", [r["link"] for r in working if lo <= int(r.get("size_bytes") or 0) < hi])
    write_lines(out / "working/working_annotated.txt", [f"{r['link']}  # {human(int(r.get('size_bytes') or 0))} | {r.get('files',0)} files | {r.get('primary_category','')}" for r in working])
    for status, filename in [("EMPTY", "empty.txt"), ("INACCESSIBLE", "inaccessible_or_unavailable.txt"), ("TAKEDOWN", "taken_down.txt"), ("ERROR", "errors_retry_later.txt")]:
        write_lines(out / "other" / filename, [r["link"] for r in statuses.get(status, [])])
    # Keep key-state lists separate from status so their meanings are not conflated.
    write_lines(out / "other/alive_but_no_key.txt", [r["link"] for r in working if r.get("key_state") == "none"])
    write_lines(out / "other/key_format_suspicious.txt", [r["link"] for r in working if r.get("key_state") == "bad_format"])
    category_groups: dict[str, list[str]] = {}
    for r in enriched:
        category_groups.setdefault(str(r.get("primary_category", "uncertain/review_required")), []).append(r["link"])
    for category, links in category_groups.items():
        safe = category.replace("/", "__").replace(" ", "_")
        write_lines(out / "categories" / f"{safe}.txt", links)
    total = sum(int(r.get("size_bytes") or 0) for r in working)
    summary = ["MEGA AUDITOR 2.0 — SUMMARY", f"Total links: {len(enriched)}", f"Working links in current views: {len(working)}", f"Working size total (current views): {human(total)}", f"Learning materials identified: {len(learning)}", f"Needs review: {len(uncertain)}", f"Filtering confirmed learning from ordinary lists: {'YES' if filter_learning else 'NO'}", "", "Status counts:"]
    summary.extend(f"  {k}: {len(v)}" for k, v in sorted(statuses.items()))
    summary.extend(["", "Largest working links:"])
    summary.extend(f"  {human(int(r.get('size_bytes') or 0)):>10} | {r.get('name') or r['link']}" for r in working[:10])
    (out / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return "\n".join(summary)
