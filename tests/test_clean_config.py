"""A stranger can load only the shipped templates and run without a backend."""
from contextlib import redirect_stdout
from dataclasses import asdict
import io
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from hingework import AdapterResult, ModelSpec, load_execution_config, run_local_council, run_escalating_task


class CleanConfigTests(unittest.TestCase):
    def test_shipped_templates_with_empty_environment_and_mock_providers(self):
        repository = Path(__file__).resolve().parents[1]
        env_text = (repository / ".env.example").read_text(encoding="utf-8")
        entries = dict(line.split("=", 1) for line in env_text.splitlines() if line and not line.startswith("#"))
        self.assertEqual(len(entries), 6)
        self.assertTrue(all(value == "" for value in entries.values()))
        before = (repository / "config/config.example.yaml").read_bytes()
        with tempfile.TemporaryDirectory() as storage, patch.dict(os.environ, {}, clear=True), \
             patch("requests.sessions.Session.request", side_effect=AssertionError("backend forbidden")), \
             patch("socket.create_connection", side_effect=AssertionError("network forbidden")), \
             patch("subprocess.Popen", side_effect=AssertionError("provider process forbidden")):
            # No automatic .env adoption: explicitly exercise absent and shipped-blank values.
            absent = load_execution_config(repository / "config/config.example.yaml")
            with patch.dict(os.environ, entries):
                config = load_execution_config(repository / "config/config.example.yaml")
            self.assertEqual(config, absent)
            self.assertTrue(all(value is None for value in asdict(config).values()))
            calls = []
            class MockAdapter:
                def __init__(self, name, content): self.name, self.content = name, content
                def invoke(self, packet):
                    calls.append(self.name)
                    return AdapterResult(self.content, "synthetic", self.name, packet["invocation_id"])
            factory = lambda name: MockAdapter(name, "Synthetic answer.")
            sequential = run_local_council("Describe the sample.", [], [ModelSpec("sample-a")], config, storage, factory)
            self.assertEqual(sequential.attempts[0].status, "PASS")
            packet = {"question": "What color is the sample?", "evidence": [{"path": "source-a", "content": "blue"}],
                      "invocation_id": "clean-config", "routing_class": "local_first", "task_contract": "citations_v1"}
            run = run_escalating_task(packet, MockAdapter("local", "- path: source-a | quote: green"),
                                      [MockAdapter("fallback", "- path: source-a | quote: blue")], storage)
            self.assertEqual(run.terminal_state, "RESOLVED")
            self.assertEqual([a.status for a in run.attempts], ["EVIDENCE_INVALID", "VALID"])
            self.assertEqual(calls, ["sample-a", "local", "fallback"])
        self.assertEqual((repository / "config/config.example.yaml").read_bytes(), before)

    def test_quickstart_examples_start_without_provider_configuration(self):
        repository = Path(__file__).resolve().parents[1]
        with patch.dict(os.environ, {}, clear=True), \
             patch("requests.sessions.Session.request", side_effect=AssertionError("backend forbidden")), \
             patch("socket.create_connection", side_effect=AssertionError("network forbidden")), \
             patch("subprocess.Popen", side_effect=AssertionError("provider process forbidden")):
            for name, expected in (("fake_council.py", "['PASS', 'PASS']"),
                                   ("escalation_synthetic.py", "RESOLVED ['EVIDENCE_INVALID', 'VALID']")):
                with self.subTest(example=name), redirect_stdout(io.StringIO()) as output:
                    runpy.run_path(str(repository / "examples" / name), run_name="__main__")
                self.assertEqual(output.getvalue().strip(), expected)
