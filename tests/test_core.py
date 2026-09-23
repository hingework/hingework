import json
import os
import subprocess
import unittest
from unittest.mock import Mock, patch

import requests

from hingework import ClaudeAdapter, CodexAdapter, OllamaAdapter, PacketError, validate_packet
from hingework.evidence.packets import MAX_PACKET_BYTES


def packet():
    return {"question": "What is supported?", "evidence": [], "invocation_id": "sample", "routing_class": "local_first"}


class CoreTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows command processor contract")
    def test_windows_command_script_uses_literal_fixed_command_line(self):
        with patch("hingework.adapters.providers.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, '{"result":"synthetic"}', "")
            p = packet(); p["question"] = "literal & % task"
            r = ClaudeAdapter("sample tool.cmd", 2).invoke(p)
            command = run.call_args.args[0]
            self.assertIsInstance(command, str)
            self.assertIn('/s /c ""sample tool.cmd" ', command)
            self.assertNotIn(p["question"], command)
            self.assertFalse(run.call_args.kwargs["shell"])
            self.assertIsNone(r.error)

    def test_envelope_and_byte_bound(self):
        validate_packet(packet())
        for field, value in [("evidence", {}), ("routing_class", "frontier_only"),
                             ("invocation_id", "../sample"), ("question", " ")]:
            p = packet(); p[field] = value
            with self.assertRaises(PacketError):
                validate_packet(p)
        p = packet(); p["question"] = "x" * MAX_PACKET_BYTES
        with self.assertRaises(PacketError):
            validate_packet(p)
        p = packet(); p["evidence"] = [float("nan")]
        with self.assertRaises(PacketError):
            validate_packet(p)

    def test_ollama_local_transport_and_raw_preservation(self):
        with patch("hingework.adapters.providers.requests.Session") as factory:
            session = factory.return_value.__enter__.return_value
            session.post.return_value = Mock(status_code=200)
            session.post.return_value.json.return_value = {"done": True, "response": "  λ\r\n"}
            result = OllamaAdapter("http://localhost", "sample", 2).invoke(packet())
            self.assertIsNone(result.error)
            self.assertEqual(result.content, "  λ\r\n")
            self.assertFalse(session.trust_env)
            self.assertFalse(session.post.call_args.kwargs["allow_redirects"])
            self.assertEqual(session.post.call_count, 1)

    def test_ollama_failures(self):
        cases = [(None, requests.Timeout(), "timeout"),
                 (None, requests.ConnectionError("private-detail"), "ollama_unreachable"),
                 ([], None, "malformed_output"), ({"done": True, "response": 4}, None, "malformed_output"),
                 ({"done": False, "response": "partial"}, None, "incomplete_response"),
                 ({"done": True, "response": " "}, None, "empty_output")]
        for data, exception, error in cases:
            with self.subTest(error=error), patch("hingework.adapters.providers.requests.Session") as factory:
                session = factory.return_value.__enter__.return_value
                session.post.side_effect = exception
                session.post.return_value = Mock(status_code=200)
                session.post.return_value.json.return_value = data
                r = OllamaAdapter("http://localhost", "sample", 2).invoke(packet())
                self.assertEqual(r.error, error)
                self.assertNotIn("private-detail", repr(r))

    def test_cli_protocols_and_no_shell_task_interpolation(self):
        raw = " answer λ\r\n"
        cases = [(CodexAdapter, json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": raw}})),
                 (ClaudeAdapter, json.dumps({"result": raw}))]
        for kind, stdout in cases:
            with self.subTest(kind=kind), patch("hingework.adapters.providers.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess([], 0, stdout, "")
                p = packet(); p["question"] = "literal & % text"
                r = kind("sample-cli", 2).invoke(p)
                self.assertEqual(r.content, raw)
                self.assertIsNone(r.error)
                self.assertFalse(run.call_args.kwargs["shell"])
                self.assertIn(p["question"], run.call_args.kwargs["input"])
                self.assertNotIn(p["question"], repr(run.call_args.args))

    def test_cli_malformed_error_and_timeout(self):
        cases = [(CodexAdapter, "[]"), (CodexAdapter, '{"type":"item.completed","item":null}'),
                 (CodexAdapter, '{"type":"item.completed","item":{"type":"agent_message","text":42}}'),
                 (ClaudeAdapter, '{"result":42}'), (ClaudeAdapter, "not json")]
        for kind, stdout in cases:
            with self.subTest(stdout=stdout), patch("hingework.adapters.providers.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess([], 0, stdout, "")
                self.assertEqual(kind("sample-cli", 2).invoke(packet()).error, "malformed_output")
        for kind in (CodexAdapter, ClaudeAdapter):
            with patch("hingework.adapters.providers.subprocess.run", side_effect=subprocess.TimeoutExpired("sample", 2)):
                self.assertEqual(kind("sample-cli", 2).invoke(packet()).error, "timeout")
            with patch("hingework.adapters.providers.subprocess.run") as run:
                p = packet(); p["evidence"] = {}
                self.assertEqual(kind("sample-cli", 2).invoke(p).error, "invalid_packet")
                run.assert_not_called()
