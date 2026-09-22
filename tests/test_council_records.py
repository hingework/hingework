import hashlib
from pathlib import Path
import tempfile
import unittest

from shared_ai_execution import AdapterResult, ExecutionConfig, ModelSpec, RecordStore, RecordStoreError, run_local_council


class RecordsTests(unittest.TestCase):
    def test_sequential_order_raw_bytes_and_nonpath_model_names(self):
        with tempfile.TemporaryDirectory() as root:
            order = []
            raw = "  Résumé\r\n\n"
            class Fake:
                def __init__(self, name): self.name = name
                def invoke(self, packet):
                    if order:
                        self_outer.assertEqual(len(list(Path(root).rglob("attempt-00.json"))), 1)
                    order.append(self.name)
                    return AdapterResult(raw, "fake", self.name, packet["invocation_id"])
            self_outer = self
            names = ["../../sample-a", "sample-b"]
            run = run_local_council("Synthetic question", [], [ModelSpec(n) for n in names], ExecutionConfig(), root, Fake)
            self.assertEqual(order, names)
            for attempt in run.attempts:
                self.assertEqual(Path(attempt.raw["path"]).read_bytes(), raw.encode())
                self.assertEqual(attempt.raw["sha256"], hashlib.sha256(raw.encode()).hexdigest())
                self.assertTrue(Path(attempt.raw["path"]).is_relative_to(Path(root)))
            self.assertIn(raw.encode(), run.reconciliation_input.read_bytes())

    def test_exclusive_and_contained_writes(self):
        with tempfile.TemporaryDirectory() as root:
            store = RecordStore(Path(root) / "records")
            run = store.create_run("sample")
            store.write_raw_once(run / "raw/00.txt", "original")
            with self.assertRaises(FileExistsError):
                store.write_raw_once(run / "raw/00.txt", "changed")
            with self.assertRaises(RecordStoreError):
                store.write_json_once(Path(root) / "escape.json", {})
            with self.assertRaises(RecordStoreError):
                store.create_run("../escape")
            with self.assertRaises(FileExistsError):
                store.create_run("sample")
            self.assertEqual((run / "raw/00.txt").read_text(), "original")

    def test_preflight_has_no_storage_side_effect(self):
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "absent"
            with self.assertRaises(ValueError):
                run_local_council("Question", [], [ModelSpec("sample")], ExecutionConfig(), destination)
            self.assertFalse(destination.exists())
