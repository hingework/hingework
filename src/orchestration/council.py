"""Sequential caller-selected local execution; never adds a fallback tier."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable, Iterable

from .config import ExecutionConfig
from ..adapters.providers import AdapterResult, OllamaAdapter
from ..debate.records import RecordStore
from ..evidence.packets import validate_packet


@dataclass(frozen=True)
class ModelSpec:
    name: str


@dataclass
class CouncilAttempt:
    model: str
    status: str
    raw: dict
    diagnostics: dict


@dataclass
class CouncilRun:
    run_path: Path
    attempts: list[CouncilAttempt]
    reconciliation_input: Path


def run_local_council(prompt: str, evidence: object, models: Iterable[ModelSpec], config: ExecutionConfig,
                      record_root: str | Path, adapter_factory: Callable[[str], object] | None = None) -> CouncilRun:
    """Run each selected local model once, in order, preserving raw responses.

    Invalid envelopes or missing selected-provider config fail before record creation.
    An explicit adapter factory supports offline callers without provider configuration.
    """
    specs = list(models)
    if not specs or any(not isinstance(s, ModelSpec) or not isinstance(s.name, str) or not s.name.strip() for s in specs):
        raise ValueError("models_required")
    packet = {"question": prompt, "evidence": deepcopy(evidence), "invocation_id": "preflight",
              "routing_class": "local_first"}
    validate_packet(packet)
    if adapter_factory is None:
        config.require("ollama")
    store = RecordStore(record_root)
    run_path = store.create_run()
    store.write_json_once(run_path / "input.json", {"prompt": prompt, "evidence": evidence,
                           "models": [s.name for s in specs], "created_at": store.timestamp()})
    attempts = []
    for index, spec in enumerate(specs):
        adapter = adapter_factory(spec.name) if adapter_factory else OllamaAdapter(
            config.ollama_base_url, spec.name, config.ollama_timeout_s, think=False)
        current = deepcopy(packet)
        current["invocation_id"] = f"{run_path.name}:{index}"
        result = adapter.invoke(current)
        if not isinstance(result, AdapterResult) or not isinstance(result.content, str):
            raise ValueError("malformed_provider_result")
        status = "PASS" if result.error is None and result.content.strip() else (result.error or "empty_output")
        raw = store.write_raw_once(run_path / "raw" / f"{index:02d}.txt", result.content)
        attempt = CouncilAttempt(spec.name, status, raw, result.diagnostics)
        attempts.append(attempt)
        store.write_json_once(run_path / f"attempt-{index:02d}.json", {**asdict(attempt),
                              "provider": result.provider, "model_returned": result.model, "error": result.error})
    lines = ["COUNCIL TASK", prompt, "", "EVIDENCE", json.dumps(evidence, ensure_ascii=False, sort_keys=True), ""]
    for attempt in attempts:
        lines += [attempt.model.upper() + " RAW RESPONSE", Path(attempt.raw["path"]).read_bytes().decode("utf-8"),
                  "", attempt.model.upper() + " METADATA", json.dumps({"status": attempt.status,
                  "raw_sha256": attempt.raw["sha256"], "diagnostics": attempt.diagnostics}, ensure_ascii=False, sort_keys=True), ""]
    text = "\n".join(lines)
    recon = run_path / "reconciliation-input.txt"
    store.write_raw_once(recon, text)
    store.write_json_once(run_path / "run.json", {"attempts": [asdict(a) for a in attempts],
                          "reconciliation_input": str(recon),
                          "reconciliation_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    return CouncilRun(run_path, attempts, recon)
