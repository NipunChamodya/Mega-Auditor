from __future__ import annotations
import os, re, sys, zipfile
from pathlib import Path
from .models import LinkTarget

SCAN_EXTS = {".txt", ".md", ".csv", ".json", ".html", ".htm", ".log", ".url", ".xml", ".yaml", ".yml", ".docx", ".xlsx"}
MAX_SCAN_BYTES = 50 * 1024 * 1024
NEW_RE = re.compile(r"mega\.(?:nz|co\.nz)/(folder|file)/([A-Za-z0-9_-]{8})(?:#([A-Za-z0-9_-]*))?(?:/(folder|file)/([A-Za-z0-9_-]{8}))?", re.I)
OLD_RE = re.compile(r"mega\.(?:nz|co\.nz)/#(F?)!([A-Za-z0-9_-]{8})(?:!([A-Za-z0-9_-]*))?", re.I)

def extract(text: str, source: str) -> list[LinkTarget]:
    found: list[LinkTarget] = []
    for m in NEW_RE.finditer(text):
        found.append(LinkTarget(m.group(1).lower(), m.group(2), m.group(3) or "", m.group(5) or "", (m.group(4) or "").lower(), {source}))
    for m in OLD_RE.finditer(text):
        found.append(LinkTarget("folder" if m.group(1) else "file", m.group(2), m.group(3) or "", sources={source}))
    return found

def read_text(path: Path) -> tuple[str, str | None]:
    try:
        if path.stat().st_size > MAX_SCAN_BYTES:
            return "", f"skipped {path}: larger than {MAX_SCAN_BYTES // (1024*1024)} MB scan limit"
        ext = path.suffix.lower()
        if ext == ".docx":
            try:
                import docx
            except ImportError:
                return "", "optional dependency missing for .docx; install python-docx"
            doc = docx.Document(str(path))
            parts = [p.text for p in doc.paragraphs]
            parts.extend(cell.text for table in doc.tables for row in table.rows for cell in row.cells)
            return "\n".join(parts), None
        if ext == ".xlsx":
            try:
                import openpyxl
            except ImportError:
                return "", "optional dependency missing for .xlsx; install openpyxl"
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            try:
                return "\n".join(str(c) for ws in wb for row in ws.iter_rows(values_only=True) for c in row if c is not None), None
            finally:
                wb.close()
        return path.read_text(encoding="utf-8", errors="replace"), None
    except (OSError, UnicodeError, zipfile.BadZipFile) as exc:
        return "", f"could not read {path}: {exc}"

def gather(paths: list[str], output_dir: str) -> tuple[list[LinkTarget], list[str]]:
    if not paths:
        paths = ["links.txt"] if Path("links.txt").is_file() else ["."]
    found: list[LinkTarget] = []
    warnings: list[str] = []
    out_abs = Path(output_dir).resolve()
    for raw in paths:
        if raw == "-":
            found.extend(extract(sys.stdin.read(), "<stdin>")); continue
        p = Path(raw).expanduser()
        if p.is_file():
            candidates = [p]
        elif p.is_dir():
            candidates = []
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"node_modules", ".venv", "venv", "__pycache__"} and Path(root, d).resolve() != out_abs]
                candidates.extend(Path(root, name) for name in files if Path(name).suffix.lower() in SCAN_EXTS)
        else:
            warnings.append(f"Input not found: {raw}"); continue
        for candidate in candidates:
            if candidate.suffix.lower() not in SCAN_EXTS and candidate.is_file():
                # Explicitly supplied files may be extensionless or use an uncommon extension.
                if raw != str(candidate):
                    pass
                elif candidate.suffix:
                    continue
            text, warning = read_text(candidate)
            if warning: warnings.append(warning)
            found.extend(extract(text, str(candidate)))
    merged: dict[str, LinkTarget] = {}
    for target in found:
        old = merged.get(target.id)
        if old is None:
            merged[target.id] = target
        else:
            old.sources.update(target.sources)
            if (target.key_state == "format_plausible", len(target.key)) > (old.key_state == "format_plausible", len(old.key)):
                old.key = target.key
    return list(merged.values()), warnings
