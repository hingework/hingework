import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hingework import ExecutionConfig, ProviderConfigError, load_execution_config
from hingework.orchestration.config import executable, local_url


class ConfigTests(unittest.TestCase):
    def load(self, text, suffix=".yaml"):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / ("config" + suffix)
            path.write_text(text, encoding="utf-8")
            return load_execution_config(path)

    def test_explicit_environment_and_no_ambient_override(self):
        with patch.dict(os.environ, {"SAMPLE_TIMEOUT": "7", "SAMPLE_COMMAND": "sample-cli", "SAMPLE_BLANK": " "}):
            c = self.load("codex_timeout_s: {env: SAMPLE_TIMEOUT}\ncodex_command: {env: SAMPLE_COMMAND}\nclaude_command: {env: SAMPLE_BLANK}")
            self.assertEqual((c.codex_timeout_s, c.resolve_codex(), c.claude_command), (7, "sample-cli", None))
            self.assertEqual(self.load("codex_timeout_s: 2").codex_timeout_s, 2)
            self.assertIsNone(ExecutionConfig().codex_command)

    def test_unselected_providers_can_be_unset(self):
        c = self.load('ollama_base_url: "http://localhost"\nollama_timeout_s: 2')
        c.require("ollama")
        with self.assertRaises(ProviderConfigError):
            c.resolve_codex()

    def test_reject_unsafe_duplicate_unknown_and_invalid_types(self):
        cases = ["codex_timeout_s: 1\ncodex_timeout_s: 2", "other: 1", "[]",
                 "codex_timeout_s: true", "codex_timeout_s: .nan", "codex_timeout_s: .inf",
                 "codex_timeout_s: 0", "codex_command: []", "codex_command: {env: X, other: 1}",
                 "codex_command: {env: 'not valid'}", "!!python/object/apply:os.system ['unused']",
                 "codex_command: {env: X, env: Y}"]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ProviderConfigError):
                self.load(text)
        with self.assertRaises(ProviderConfigError):
            self.load('{"codex_timeout_s":1,"codex_timeout_s":2}', ".json")
        self.assertEqual(self.load('{"codex_timeout_s":2}', ".json").codex_timeout_s, 2)

    def test_values_and_paths_are_not_echoed_in_errors(self):
        for text in ["codex_timeout_s: private-value", "ollama_base_url: private-value"]:
            try:
                self.load(text)
            except ProviderConfigError as exc:
                self.assertNotIn("private-value", str(exc))
            else:
                self.fail("expected error")

    def test_endpoint_and_executable_boundaries(self):
        for url in ["https://localhost", "http://example.invalid", "http://localhost/x",
                    "http://user@localhost", "http://localhost?", "http://localhost#",
                    "http://localhost:bad", "http://localhost:0", "http://localhost\n"]:
            with self.subTest(url=url), self.assertRaises(ProviderConfigError):
                local_url(url)
        self.assertEqual(local_url("http://localhost/"), "http://localhost")
        for name in ['bad&name.cmd', 'bad%name.cmd', 'bad!name.bat', 'bad"name.exe']:
            with self.assertRaises(ProviderConfigError):
                executable(name)
        self.assertEqual(executable("sample tool.cmd"), "sample tool.cmd")
