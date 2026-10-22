<div align="center">

# 🔎 MEGA Auditor

### 🧭 Find • Check • Classify • Review • Report

**A local-first Python tool for auditing public MEGA links and organizing likely learning resources.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-555)](#-installation)
[![Interface](https://img.shields.io/badge/Interface-CLI%20%2B%20Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-Add%20a%20license-lightgrey)](#-license)

*Inspect public-link metadata. Keep your source files and reports under your control.*

</div>

---

## ✨ What is MEGA Auditor?

MEGA Auditor scans local text files and supported documents for public MEGA file/folder links. It deduplicates discovered links, checks available metadata through MEGA's public API, saves checkpoints so completed checks can be reused, and creates reports that are easier to search and review.

It also uses explainable heuristics to identify links that **may point to educational or learning material**—for example, programming courses, software-engineering notes, lectures, ebooks, and PDFs. The classifier uses available names, source paths, and metadata; it does not read the complete contents of remote files.

You can use it from the **terminal (CLI)** or run the **local browser dashboard (GUI)** on Windows, macOS, or Linux.

> ⚠️ **Important:** Only audit links and files you are authorized to access. Treat public links as sensitive: do not publish your personal `links.txt` or generated reports in a public repository.

## 🌟 Features

- 🔗 **Link discovery** — recognizes supported modern and legacy MEGA URL formats in local files.
- 🧹 **Deduplication** — checks each unique link once per scan input set while retaining source-file references.
- 🌐 **Metadata checks** — requests public-link metadata; it does not sign in to your MEGA account.
- 📁 **File and folder details** — records available names, file counts, sizes, and limited previews when metadata allows.
- 💾 **Checkpoint and resume** — saves completed results so a normal rerun can reuse them rather than rechecking everything.
- 🧠 **Learning-resource classification** — assigns categories, reasons, and a heuristic confidence score.
- 🧑‍⚖️ **Human review queue** — exports uncertain classifications for manual inspection.
- 🧾 **Multiple reports** — CSV, JSON, and plain-text link lists, including size-based groups.
- 🖥️ **Local web GUI** — monitor progress, filter results, inspect summary metrics, and download reports in a browser.
- 🛠️ **CLI options** — tune concurrency and request rate, force rechecks, rebuild reports, and preview/apply learning-material filtering.
- 🧪 **Automated tests** — tests for classification, report generation, and GUI scan-service behavior.

## 🧰 How it works

```text
Local input files / folders / links.txt
                 │
                 ▼
       🔎 Find MEGA URLs
                 │
                 ▼
      🧹 Deduplicate link targets
                 │
                 ▼
   🌐 Check public metadata via API
                 │
                 ▼
       💾 Save completed checkpoints
                 │
                 ▼
     🧠 Classify likely learning items
                 │
                 ▼
   📊 Generate reports and review lists
          ┌──────┴──────┐
          ▼             ▼
      CLI output     Local web GUI
```

### 🔐 Privacy and safety by design

- The app is intended to run locally. When launching the GUI with the commands below, it binds to `127.0.0.1` (localhost).
- Link metadata checks contact MEGA's API. **This is not an offline scanner.**
- The tool does not log in to MEGA or download remote files.
- `links.txt` and `mega_results/` are ignored by the included `.gitignore` by default. Check `git status` before committing.
- Filtering changes generated report views only; it does not delete local source files or remote content. Raw scan records are retained in `raw_results.csv` and `raw_results.json` when reports are generated.
- Do not expose the dashboard to your network or the public internet unless you have separately designed and secured that deployment.

## 🖥️ Installation

### Requirements

- Python **3.10 or newer** recommended.
- Internet access for metadata checks and dependency installation.
- A terminal: PowerShell or Command Prompt on Windows, Terminal on macOS, or a shell on Linux.
- A modern browser for the optional GUI.

Check Python:

```bash
python --version
```

On macOS/Linux, use `python3 --version` if `python` is not available. On Windows, `py --version` is also commonly available. If Python is not installed, install it from [python.org/downloads](https://www.python.org/downloads/) and reopen your terminal.

### 🪟 Windows — PowerShell

Open PowerShell in the project folder (the folder containing `main.py`, `app.py`, and `requirements.txt`).

```powershell
# Create a virtual environment
py -3 -m venv .venv

# Activate it
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, you can either use Command Prompt (instructions below) or allow activation for **this PowerShell process only**:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

#### Windows — Command Prompt (CMD)

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 🍎 macOS

Open Terminal in the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 🐧 Linux

On Debian/Ubuntu, if virtual-environment support is missing, install it first:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

Then, from the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On other Linux distributions, install Python 3, `venv`, and `pip` using your distribution's package manager.

> 💡 **Tip:** Activate `.venv` each time you open a new terminal before running the app. You only need to create the environment and install requirements once per project environment.

## 🚀 Run the browser GUI

The Streamlit dashboard is the easiest way to run a scan and review the results visually.

1. Activate the virtual environment using the command for your operating system above.
2. Confirm you are in the project folder.
3. Start the GUI:

```bash
streamlit run app.py --server.address 127.0.0.1
```

4. Open the local URL printed by Streamlit—usually [http://127.0.0.1:8501](http://127.0.0.1:8501).
5. In the sidebar, enter one or more input paths (one path per line). The default input is `links.txt`.
6. Set the report output folder (default `mega_results`), adjust the request rate/concurrency conservatively, and click **Start / Resume scan**.
7. Use **Refresh results**, filters, and the download buttons to inspect or export reports.

### ⏹️ Stop and resume

- In the GUI, **Stop safely** requests cancellation and keeps completed checkpoints. A request already in flight may take time to return.
- In the CLI, press `Ctrl+C`; completed checks are checkpointed. Run the same command again to resume using saved results.
- Use `--recheck` when you deliberately want to check discovered links again. This may take longer and sends more requests.
- The GUI's stop action is cooperative; it does not guarantee immediate cancellation of every already-started network request.

## ⌨️ Run from the command line (CLI)

All CLI commands below are run from the project folder with the virtual environment activated.

### 1. Scan `links.txt`

Create a text file named `links.txt` in the project folder, with **one link per line**. Keep it private. Then run:

```bash
python -m mega_auditor
```

If `links.txt` is absent, the scanner uses the current directory as its input. Explicitly selecting the input is safer and clearer for most workflows.

### 2. Scan specific files or folders

```bash
python -m mega_auditor links.txt
python -m mega_auditor ./my_link_notes.txt ./course_materials --out mega_results
```

Paths containing spaces should be quoted, for example:

```bash
python -m mega_auditor "./my course notes" --out mega_results
```

### 3. Useful options

```bash
# Show every available CLI option
python -m mega_auditor --help

# Lower concurrency and request rate for a cautious scan
python -m mega_auditor --workers 2 --rate 1

# Recheck all discovered links
python -m mega_auditor --recheck

# Rebuild classifications and reports from saved raw results without API calls
python -m mega_auditor --classify-only

# Preview which confirmed learning items would be excluded; this is a dry run
python -m mega_auditor --filter-learning

# After reviewing reports, write ordinary report views without confirmed learning items
python -m mega_auditor --filter-learning --apply

# Change the heuristic confidence threshold and rebuild reports
python -m mega_auditor --min-confidence 0.85 --classify-only

# Start a fresh checkpoint rather than reusing the current scan state
python -m mega_auditor --fresh
```

`--fresh` clears the saved checkpoint state before checking, but it does not mean “delete every previous report.” Keep backups of any reports you need.

## 📄 Input files

The scanner looks for links in these file types when traversing folders:

`.txt` · `.md` · `.csv` · `.json` · `.html` · `.htm` · `.log` · `.url` · `.xml` · `.yaml` · `.yml` · `.docx` · `.xlsx`

- `.docx` and `.xlsx` support is provided by installed dependencies in `requirements.txt`.
- Files larger than 50 MB are skipped.
- Hidden directories, `.venv`, `venv`, `node_modules`, `__pycache__`, and the selected report output directory are skipped during folder traversal.
- This tool extracts links from local text/document content. It does not crawl arbitrary websites or search the internet for new links.

## 🏷️ Understanding statuses

| Status | Meaning |
|---|---|
| `WORKING` | The API returned metadata for a file or a folder containing files. This does not guarantee every remote file can be downloaded. |
| `EMPTY` | A folder listing was returned but contained no files. It may contain subfolders or otherwise have content not represented as files by this check. |
| `INACCESSIBLE` | The API returned a response interpreted as inaccessible, unavailable, or the requested folder node was not found. Do not automatically treat this as proof the link is permanently dead. |
| `TAKEDOWN` | The API returned a response interpreted by the script as a takedown/blocked response. Verify manually if the distinction matters. |
| `ERROR` | The check failed, returned an unexpected response, or did not provide enough evidence to classify the link. Retry later if appropriate. |

The API can rate-limit requests, and results may vary with time or service behavior. Start with a conservative rate; increase concurrency only when needed.

## 🎓 Educational-material detection

The classifier uses explainable heuristics based on information available to the tool, such as decrypted names when available, source-file paths, and returned metadata. It can identify likely categories such as programming courses, lectures, study notes, ebooks, and related materials when evidence supports them.

- **Learning materials** — matches that meet the configured heuristic threshold.
- **Uncertain classifications** — ambiguous matches that should be reviewed by a person.
- **Confidence score** — a heuristic ranking, **not** a calibrated probability and not a guarantee of correctness.
- **False positives/negatives are possible** — a file name may be misleading, names may be unavailable, and the remote file's full contents are not inspected.

Recommended workflow: scan → review `learning_materials.csv` and `uncertain_classifications.csv` → preview filtering → apply filtering only if the results look correct.

## 📊 Reports generated

By default, reports are written under `mega_results/`.

| File or folder | Purpose |
|---|---|
| `raw_results.csv` / `raw_results.json` | Original scan observations; preserve these as the raw record. |
| `classified_results.csv` / `classified_results.json` | Results enriched with categories, reasons, confidence, and review flags. |
| `learning_materials.csv` / `learning_materials.txt` | Links classified as likely learning resources. |
| `uncertain_classifications.csv` | Ambiguous classifications for manual review. |
| `classification_exclusions.csv` | Confirmed learning rows excluded from ordinary views when filtering is applied. |
| `all_unique_links.txt` | Deduplicated links in the current ordinary view. |
| `working/` | Working links, including size ranges and annotated lists. |
| `other/` | Inaccessible/unavailable, takedown, error, and key-format review lists. |
| `categories/` | Link lists grouped by the classifier's primary category. |
| `summary.txt` | A human-readable scan summary. |
| `state.jsonl` | Append-only checkpoint records used for resume. |

Filtering affects generated ordinary report views only. Keep the raw CSV/JSON records if you need a complete record of checked links.

## 🧪 Run tests

With the virtual environment activated, from the project root:

```bash
python -m unittest discover -s tests -v
```

To check Python syntax for the main entry points:

```bash
python -m compileall main.py app.py mega_auditor tests
```

## 🗂️ Project structure

```text
mega_auditor_refactored/
├── app.py                       # Streamlit browser GUI
├── main.py                      # Simple CLI entry point
├── requirements.txt             # Python dependencies
├── config/
│   └── categories.json          # Classification category configuration
├── mega_auditor/
│   ├── __main__.py              # Enables: python -m mega_auditor
│   ├── cli.py                   # CLI arguments and orchestration
│   ├── scanner.py               # Local-file link extraction and deduplication
│   ├── mega_client.py           # Public metadata requests and rate limiting
│   ├── models.py                # Link-target data model
│   ├── gui_service.py           # Background scan service for the GUI
│   ├── classifier/              # Educational-resource heuristics
│   └── reporting/               # CSV/JSON/text report generation
└── tests/                       # Automated tests
```

## 🛠️ Troubleshooting

### `python: command not found`

- **Windows:** use `py -3` to create the environment, then activate `.venv`.
- **macOS/Linux:** use `python3` to create the environment, then activate `.venv`.
- Once the virtual environment is activated, `python` should normally be available.

### `ModuleNotFoundError: No module named 'requests'` (or another dependency)

Activate the environment and install requirements again:

```bash
python -m pip install -r requirements.txt
```

### Streamlit command not found

Confirm the virtual environment is active and dependencies installed. You can also launch it as a module:

```bash
python -m streamlit run app.py --server.address 127.0.0.1
```

### Few or no links found

Check that your input path is correct and the file contains recognizable MEGA URLs. The folder scanner only traverses its supported file extensions listed above. Make sure the input file is not empty and isn't being skipped due to its size.

### Many `INACCESSIBLE` or `ERROR` results

These results are not all proof of a permanently dead link. Network errors, API behavior, rate limits, access restrictions, and unsupported response cases can affect results. Reduce the request rate, retry later, and verify important links manually. Use `--recheck` only when you want to spend requests checking them again.

### The GUI does not open

Confirm the command was run from the project root, check the URL printed in Terminal, and keep the terminal process running while using the browser dashboard. If port 8501 is already in use, stop the other local Streamlit app or use another port, for example `--server.port 8502`.

## 🔄 Updating the project with Git

Keep private input files and generated reports out of Git. Review staged changes before every commit:

```bash
git status --short
git add .
git diff --cached
```

If the staged changes are correct:

```bash
git commit -m "Describe your changes"
git push
```

The included `.gitignore` excludes `links.txt` and `mega_results/` by default. If a sensitive link was already committed in an earlier commit, adding it to `.gitignore` does not remove it from Git history; treat it as exposed and take appropriate action.

## ⚖️ Responsible use

Use this tool only for lawful, authorized link auditing and personal organization. Respect the rights and privacy of link owners, platform terms, and applicable laws. Do not use it to distribute private material, bypass access controls, or claim that a link is permanently dead based on an inconclusive status.



**Made for careful link auditing and better-organized learning resources.** 🔎📚🛡️

</div>
