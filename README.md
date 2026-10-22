# MEGA Auditor 2.0

A Python CLI that finds public MEGA URLs in local text/document files, checks public-link metadata through MEGA's API, resumes interrupted checks, and generates separate reports for status, file size, and likely educational material.

## Important limits

- It does not log in to MEGA or download the linked files.
- Classification uses decrypted names when available, input source paths, and metadata returned by the API. It does **not** inspect the full contents of remote files. Treat the confidence score as a prioritization aid, not ground truth.
- A key whose length looks correct is not necessarily a valid key. The code labels this `format_plausible`, not `valid`.
- API responses can be inconclusive. The tool avoids calling every unexpected response a dead link.
- Filtering changes generated report views only. It never deletes local source files or remote MEGA content.

## Install on macOS

```bash
cd mega_auditor_refactored
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Local web GUI (macOS)

Install the dependencies above, then launch the dashboard from the project folder:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1
```

Streamlit prints a local URL (normally `http://127.0.0.1:8501`). Open it in your browser. The dashboard accepts one or more local file/folder paths, shows scan progress, supports checkpoint-based resume, filters results, and downloads CSV/JSON reports. Use **Stop safely** to request cancellation; requests already in flight may take time to return. The GUI binds to localhost by default when launched with the command above and does not upload data to a remote dashboard service.

Keep `links.txt` and generated reports private. The GUI is a local interface to the existing scanner, not a guarantee that every API status is definitive.

## Scan

Place links in `links.txt`, then run:

```bash
python -m mega_auditor
```

Or scan explicit inputs:

```bash
python -m mega_auditor links.txt ~/Documents --out mega_results
```

The script scans supported files in folders and skips hidden directories, virtual environments, `node_modules`, the output directory, and files larger than 50 MB. It supports `.txt`, `.md`, `.csv`, `.json`, `.html`, `.htm`, `.log`, `.url`, `.xml`, `.yaml`, `.yml`, `.docx`, and `.xlsx`.

## Learning-material workflow

1. Run a scan. Reports include `learning_materials.csv`, `learning_materials.txt`, `uncertain_classifications.csv`, and `classified_results.csv`.
2. Review likely educational items and uncertain matches.
3. Preview filtering without changing any reports:

   ```bash
   python -m mega_auditor --filter-learning
   ```

4. Apply filtering to ordinary report lists only after review:

   ```bash
   python -m mega_auditor --filter-learning --apply
   ```

5. Rebuild classifications and reports from saved raw results without making API requests:

   ```bash
   python -m mega_auditor --classify-only
   python -m mega_auditor --classify-only --filter-learning --apply
   ```

The `raw_results.json` and `raw_results.csv` files are preserved as the full scan record. `--fresh` resets scan progress; `--recheck` checks every discovered link again.

## Useful options

```bash
python -m mega_auditor --help
python -m mega_auditor --workers 2 --rate 1
python -m mega_auditor --recheck
python -m mega_auditor --min-confidence 0.85 --classify-only
```

`--min-confidence` is a threshold on explainable heuristics, not a calibrated machine-learning probability.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Reports

- `raw_results.csv/json`: original scan observations, without classification fields.
- `classified_results.csv/json`: full results plus classification and reasons.
- `learning_materials.csv/txt`: items classified as learning materials.
- `uncertain_classifications.csv`: ambiguous cases for manual review.
- `classification_exclusions.csv`: records omitted from ordinary lists when filtering is applied.
- `categories/`: category-specific link lists.
- `working/by_size/`: working links separated into size buckets.
- `state.jsonl`: append-only scan checkpoints used to resume work.
