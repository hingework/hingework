"""Explicit, read-only configuration loading; no discovery or implicit defaults."""
from __future__ import annotations

from dataclasses import dataclass, fields
import ipaddress
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

import yaml


class ProviderConfigError(ValueError):
    pass


def positive_timeout(value: object, field: str = "timeout_s") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderConfigError(field + ":invalid_number")
    try:
        valid = math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise ProviderConfigError(field + ":invalid_number")
    return float(value)


def local_url(value: object) -> str:
    try:
        if not isinstance(value, str) or any(c.isspace() for c in value):
            raise ValueError
        parsed = urlsplit(value)
        host = parsed.hostname
        if (parsed.scheme != "http" or parsed.path not in ("", "/") or not host
                or parsed.username is not None or parsed.password is not None
                or "?" in value or "#" in value):
            raise ValueError
        if host != "localhost" and not ipaddress.ip_address(host).is_loopback:
            raise ValueError
        if parsed.port is not None and parsed.port <= 0:
            raise ValueError
    except (ValueError, TypeError):
        raise ProviderConfigError("ollama_base_url:invalid_local_endpoint") from None
    return value.rstrip("/")


def executable(value: object, field: str = "command") -> str:
    if (not isinstance(value, str) or not value.strip() or value.strip() != value
            or any(c in value for c in '\r\n\x00"')
            or (value.lower().endswith((".cmd", ".bat"))
                and any(c in value for c in '%!&|<>^'))):
        raise ProviderConfigError(field + ":invalid_executable")
    return value


@dataclass(frozen=True)
class ExecutionConfig:
    ollama_base_url: str | None = None
    ollama_timeout_s: float | None = None
    codex_timeout_s: float | None = None
    claude_timeout_s: float | None = None
    codex_command: str | None = None
    claude_command: str | None = None

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                continue
            if field.name.endswith("timeout_s"):
                positive_timeout(value, field.name)
            elif field.name.endswith("command"):
                executable(value, field.name)
            else:
                local_url(value)

    def require(self, provider: str) -> None:
        required = {"ollama": ("ollama_base_url", "ollama_timeout_s"),
                    "codex": ("codex_command", "codex_timeout_s"),
                    "claude": ("claude_command", "claude_timeout_s")}
        if provider not in required:
            raise ProviderConfigError("unknown_provider")
        for name in required[provider]:
            if getattr(self, name) is None:
                raise ProviderConfigError(name + ":required")

    def resolve_codex(self) -> str:
        self.require("codex")
        return self.codex_command

    def resolve_claude(self) -> str:
        self.require("claude")
        return self.claude_command


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if not isinstance(key, str) or key in result:
            raise ProviderConfigError("invalid_or_duplicate_key")
        result[key] = value
    return result


class _Loader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    return _unique_pairs((loader.construct_object(k), loader.construct_object(v)) for k, v in node.value)


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_execution_config(path: str | Path) -> ExecutionConfig:
    try:
        source = Path(path)
        text = source.read_text(encoding="utf-8")
        if source.suffix.lower() == ".json":
            raw = json.loads(text, object_pairs_hook=_unique_pairs)
        elif source.suffix.lower() in (".yaml", ".yml"):
            raw = yaml.load(text, Loader=_Loader)
        else:
            raise ProviderConfigError("unsupported_config_format")
        allowed = {field.name for field in fields(ExecutionConfig)}
        if not isinstance(raw, dict) or raw.keys() - allowed:
            raise ProviderConfigError("invalid_config_keys")
        resolved = {}
        for key, value in raw.items():
            if isinstance(value, dict):
                if (set(value) != {"env"} or not isinstance(value["env"], str)
                        or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value["env"])):
                    raise ProviderConfigError(key + ":invalid_env_reference")
                value = os.environ.get(value["env"]) or None
                if value is not None and not value.strip():
                    value = None
                if value is not None and key.endswith("timeout_s"):
                    try:
                        value = float(value)
                    except ValueError:
                        raise ProviderConfigError(key + ":invalid_number") from None
            resolved[key] = value
        return ExecutionConfig(**resolved)
    except ProviderConfigError:
        raise
    except (OSError, ValueError, TypeError, yaml.YAMLError, RecursionError):
        raise ProviderConfigError("config_read_or_parse_failed") from None
