import json
import tempfile
import threading
import unittest
from queue import Queue
from pathlib import Path

from mega_auditor.gui_service import _load_state, run_scan


class GuiServiceTests(unittest.TestCase):
    def test_load_state_ignores_malformed_checkpoint_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.jsonl"
            path.write_text(
                json.dumps({"id": "folder:abc", "status": "WORKING"}) + "\n"
                + "not-json\n"
                + json.dumps({"status": "missing id"}) + "\n",
                encoding="utf-8",
            )
            state = _load_state(path)
            self.assertEqual(list(state), ["folder:abc"])
            self.assertEqual(state["folder:abc"]["status"], "WORKING")

    def test_missing_state_returns_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(_load_state(Path(directory) / "absent.jsonl"), {})

    def test_scan_without_links_finishes_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            events = Queue()
            run_scan(
                [str(Path(directory) / "missing.txt")],
                str(Path(directory) / "out"), 1, 1.0, 0.72, False,
                threading.Event(), events,
            )
            event_types = []
            while not events.empty():
                event_types.append(events.get_nowait()["type"])
            self.assertIn("finished", event_types)


if __name__ == "__main__":
    unittest.main()
