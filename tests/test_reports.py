import json, tempfile, unittest
from pathlib import Path
from mega_auditor.reporting.reports import write_reports

class ReportTests(unittest.TestCase):
    def test_filtering_keeps_raw_results_and_separates_learning(self):
        raw = [
            {"id":"file:12345678:", "link":"https://mega.nz/file/12345678#abc", "status":"WORKING", "reason":"ok", "key_state":"format_plausible", "files":1, "size_bytes":123, "name":"Java Beginner Course.pdf", "preview":[], "sources":["links.txt"], "source_count":1},
            {"id":"file:87654321:", "link":"https://mega.nz/file/87654321#abc", "status":"WORKING", "reason":"ok", "key_state":"format_plausible", "files":1, "size_bytes":456, "name":"Family Movie 1080p.mkv", "preview":[], "sources":["links.txt"], "source_count":1}
        ]
        with tempfile.TemporaryDirectory() as td:
            write_reports(raw, td, filter_learning=True)
            folder = Path(td)
            saved = json.loads((folder / "raw_results.json").read_text())
            self.assertEqual(len(saved), 2)
            self.assertEqual(len((folder / "learning_materials.txt").read_text().splitlines()), 1)
            ordinary = (folder / "working/all_working.txt").read_text()
            self.assertNotIn("12345678", ordinary)
            self.assertIn("87654321", ordinary)

if __name__ == "__main__": unittest.main()
