"""Stateless adapters. Invocation is explicit; errors have no routing authority."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import subprocess
import tempfile
import time

import requests

from ..evidence.packets import PacketError, render_prompt
from ..orchestration.config import executable, local_url, positive_timeout


@dataclass
class AdapterResult:
    content: str
    provider: str
    model: str | None
    invocation_id: str | None
    error: str | None = None
    diagnostics: dict = field(default_factory=dict)


def _started():
    return datetime.now(timezone.utc).isoformat(), time.perf_counter()


def _result(content, provider, model, invocation_id, error, started, clock, diagnostics=None):
    return AdapterResult(content, provider, model, invocation_id, error,
                         {**(diagnostics or {}), "started_at": started,
                          "elapsed_ms": round((time.perf_counter() - clock) * 1000),
                          "response_length": len(content)})


class OllamaAdapter:
    def __init__(self, base_url: str, model: str, timeout_s: float, think: bool | None = False):
        self.base_url = local_url(base_url)
        self.timeout_s = positive_timeout(timeout_s)
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model_required")
        if think is not None and type(think) is not bool:
            raise ValueError("invalid_think")
        self.model, self.think = model, think

    def invoke(self, packet: dict) -> AdapterResult:
        started, clock = _started()
        invocation_id = packet.get("invocation_id") if isinstance(packet, dict) else None
        def finish(content="", error=None, diagnostics=None):
            return _result(content, "ollama", self.model, invocation_id, error, started, clock, diagnostics)
        try:
            prompt = render_prompt(packet)
        except PacketError:
            return finish(error="invalid_packet")
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        if self.think is not None:
            payload["think"] = self.think
        try:
            with requests.Session() as session:
                # An explicit local endpoint must not be redirected or sent through ambient proxies.
                session.trust_env = False
                response = session.post(self.base_url + "/api/generate", json=payload,
                                        timeout=self.timeout_s, allow_redirects=False)
        except requests.Timeout:
            return finish(error="timeout")
        except requests.RequestException as exc:
            return finish(error="ollama_unreachable", diagnostics={"exception_type": type(exc).__name__})
        diagnostics = {"http_status": response.status_code}
        if response.status_code != 200:
            return finish(error="http_error", diagnostics=diagnostics)
        try:
            data = response.json()
        except ValueError:
            return finish(error="malformed_output", diagnostics=diagnostics)
        if not isinstance(data, dict):
            return finish(error="malformed_output", diagnostics=diagnostics)
        content = data.get("response")
        if not isinstance(content, str):
            return finish(error="malformed_output", diagnostics=diagnostics)
        error = "incomplete_response" if data.get("done") is not True else None
        if not content.strip() and error is None:
            error = "empty_output"
        return finish(content, error, diagnostics)


class _CliAdapter:
    provider = "cli"

    def __init__(self, command: str, timeout_s: float):
        self.command, self.timeout_s = executable(command), positive_timeout(timeout_s)

    def _run(self, args: list[str], prompt: str):
        if self.command.lower().endswith((".cmd", ".bat")) and os.name == "nt":
            # All arguments are fixed adapter flags; task text travels only on stdin.
            # Command metacharacters/expansions are rejected by executable().
            # Pass the complete command line as text: converting this through the
            # Windows C-runtime argv encoder would backslash-escape cmd's quotes.
            processor = subprocess.list2cmdline([os.environ.get("COMSPEC", "cmd.exe")])
            args = processor + ' /d /v:off /s /c "' + subprocess.list2cmdline(args) + '"'
        try:
            with tempfile.TemporaryDirectory(prefix="agent-hub-") as scratch:
                return subprocess.run(args, input=prompt, text=True, encoding="utf-8", errors="replace",
                                      cwd=scratch, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      timeout=self.timeout_s, check=False, shell=False), None
        except subprocess.TimeoutExpired:
            return None, "timeout"
        except OSError:
            return None, "launch_failed"

    def invoke(self, packet: dict) -> AdapterResult:
        started, clock = _started()
        invocation_id = packet.get("invocation_id") if isinstance(packet, dict) else None
        def finish(content="", error=None, diagnostics=None):
            return _result(content, self.provider, None, invocation_id, error, started, clock, diagnostics)
        try:
            prompt = render_prompt(packet)
        except PacketError:
            return finish(error="invalid_packet")
        completed, error = self._run([self.command, *self.arguments], prompt)
        if error:
            return finish(error=error)
        diagnostics = {"process_exit": completed.returncode,
                       "stderr_length": len(completed.stderr), "stdout_length": len(completed.stdout)}
        try:
            content, protocol_error = self._parse(completed.stdout)
        except (ValueError, TypeError, AttributeError):
            return finish(error="malformed_output", diagnostics=diagnostics)
        error = "process_exit" if completed.returncode else protocol_error
        if error is None and not content.strip():
            error = "empty_output"
        return finish(content, error, diagnostics)


class CodexAdapter(_CliAdapter):
    provider = "codex"
    arguments = ("exec", "--ephemeral", "--sandbox", "read-only", "--json", "--skip-git-repo-check", "-")

    @staticmethod
    def _parse(stdout):
        content, error = "", None
        for line in stdout.splitlines():
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError
            if event.get("type") in ("error", "turn.failed"):
                error = "provider_error"
            if event.get("type") == "item.completed":
                item = event.get("item")
                if not isinstance(item, dict):
                    raise ValueError
                if item.get("type") == "agent_message":
                    content = item.get("text")
                    if not isinstance(content, str):
                        raise ValueError
        return content, error


class ClaudeAdapter(_CliAdapter):
    provider = "claude"
    arguments = ("--print", "--output-format", "json", "--no-session-persistence", "--safe-mode", "--tools", "")

    @staticmethod
    def _parse(stdout):
        data = json.loads(stdout)
        if not isinstance(data, dict) or not isinstance(data.get("result"), str):
            raise ValueError
        return data["result"], "provider_error" if data.get("is_error") else None
