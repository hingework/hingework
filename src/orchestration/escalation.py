"""One local call and at most two fallbacks, driven only by trusted evidence rules."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
from itertools import islice
import json
from pathlib import Path
import re
import uuid

from ..adapters.providers import AdapterResult
from ..debate.records import RecordStore
from ..evidence.packets import packet_hash, validate_citation_packet
from ..evidence.validation import EvidenceVerdict, validate_citations


@dataclass
class EscalationAttempt:
    tier: int
    invocation_id: str
    status: str = "ERROR"
    provider: str | None = None
    model: str | None = None
    reason_codes: tuple[str, ...] = ()
    raw: dict | None = None
    binding: dict = field(default_factory=dict)
    escalation_reason: str | None = None
    error: str | None = None
    diagnostics: dict = field(default_factory=dict)


@dataclass
class EscalationRun:
    terminal_state: str
    attempts: list[EscalationAttempt] = field(default_factory=list)
    final_result: AdapterResult | None = None
    resolved_tier: int | None = None
    scope_expansion_required: bool = False
    run_path: Path | None = None
    error: str | None = None


def _check_verdict(verdict):
    if (type(verdict) is not EvidenceVerdict
            or verdict.status not in ("VALID", "EVIDENCE_INVALID", "INSUFFICIENT_EVIDENCE")
            or type(verdict.reason_codes) is not tuple or len(verdict.reason_codes) > 32
            or any(not isinstance(code, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", code)
                   for code in verdict.reason_codes)):
        raise ValueError("invalid_validator_verdict")


def _unchanged(current, expected, original_hash):
    try:
        return current == expected and packet_hash(current) == original_hash
    except Exception:
        return False


def run_escalating_task(packet, local_adapter, fallback_adapters, record_root,
                        validator=validate_citations) -> EscalationRun:
    """Explicit opt-in. Operational failures stop; only evidence verdicts escalate.

    The first adapter is the caller-designated local/cheap executor. At most two
    fallback adapters may be supplied. There are no internal provider retries.
    A custom validator is trusted application code, must be pure/deterministic,
    and must declare a stable versioned ``rule_id``. Arbitrary Python extensions
    cannot be sandboxed or proved pure by this API. Packet data never selects one.
    """
    run = EscalationRun("ERROR")
    preflight_error = "invalid_packet"
    try:
        validate_citation_packet(packet)
        original = deepcopy(packet)
        original_hash = packet_hash(original)
        preflight_error = "invalid_routing_plan"
        # Read at most three fallback entries, so even an infinite iterable is rejected.
        fallbacks = tuple(islice(iter(fallback_adapters), 3))
        adapters = (local_adapter, *fallbacks)
        if len(fallbacks) > 2 or any(not callable(getattr(a, "invoke", None)) for a in adapters):
            raise ValueError("invalid_routing_plan")
        preflight_error = "invalid_validator_contract"
        rule_id = getattr(validator, "rule_id", None)
        if (not callable(validator) or not isinstance(rule_id, str)
                or not re.fullmatch(r"[A-Za-z0-9_.-]{1,96}/v[0-9]+", rule_id)):
            raise ValueError("invalid_validator_contract")
        identities = [f"task_{uuid.uuid4().hex}:{i}" for i in range(len(adapters))]
        preflight_error = "invalid_packet"
        # Replacement IDs must fit the packet byte limit before any provider/storage work.
        for identity in identities:
            validate_citation_packet({**original, "invocation_id": identity})
    except Exception:
        run.error = preflight_error
        return run

    try:
        store = RecordStore(record_root)
        run.run_path = store.create_run()
        store.write_json_once(run.run_path / "input.json", {"packet": original, "packet_hash": original_hash,
                              "rule_id": rule_id, "tier_count": len(adapters)})
    except Exception:
        run.error = "persistence_error"
        return run

    for index, adapter in enumerate(adapters):
        current = deepcopy(original)
        current["invocation_id"] = identities[index]
        expected = deepcopy(current)
        attempt = EscalationAttempt(index, identities[index])
        content = None
        result = None
        try:
            returned = adapter.invoke(current)
            if not isinstance(returned, AdapterResult):
                raise ValueError("malformed_provider_result")
            result = deepcopy(returned)
            if isinstance(result.content, str):
                content = result.content
            if (content is None or not isinstance(result.provider, str) or not result.provider
                    or (result.model is not None and not isinstance(result.model, str))
                    or result.invocation_id != identities[index]
                    or not isinstance(result.diagnostics, dict)
                    or (result.error is not None and not isinstance(result.error, str))):
                raise ValueError("malformed_provider_result")
            attempt.provider, attempt.model = result.provider, result.model
            attempt.diagnostics = deepcopy(result.diagnostics)
            json.dumps(attempt.diagnostics, allow_nan=False)
            response_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if result.error is not None:
                attempt.error = "provider_error"
                attempt.diagnostics["provider_error"] = result.error
            elif not content.strip():
                attempt.error = "empty_output"
            elif not _unchanged(current, expected, original_hash):
                attempt.error = "packet_mutation"
            else:
                validation_packet = deepcopy(expected)
                try:
                    verdict = validator(content, validation_packet)
                    _check_verdict(verdict)
                    if not _unchanged(validation_packet, expected, original_hash):
                        attempt.error = "packet_mutation"
                    else:
                        attempt.status = verdict.status
                        attempt.reason_codes = verdict.reason_codes
                        attempt.binding = {"rule_id": rule_id, "invocation_id": identities[index],
                                           "packet_sha256": original_hash, "response_sha256": response_hash}
                except Exception as exc:
                    attempt.error = "validator_error"
                    attempt.diagnostics["exception_type"] = type(exc).__name__
        except Exception as exc:
            attempt.error = "provider_contract_or_call_error"
            attempt.diagnostics = {"exception_type": type(exc).__name__}
        # Also check after a throwing provider, or a provider returning an operational error.
        if not _unchanged(current, expected, original_hash):
            attempt.status, attempt.error = "ERROR", "packet_mutation"
        if attempt.error:
            attempt.status = "ERROR"
        if attempt.status in ("EVIDENCE_INVALID", "INSUFFICIENT_EVIDENCE") and index + 1 < len(adapters):
            attempt.escalation_reason = attempt.status
        run.attempts.append(attempt)
        try:
            if content is not None:
                attempt.raw = store.write_raw_once(run.run_path / "raw" / f"{index:02d}.txt", content)
            store.write_json_once(run.run_path / f"attempt-{index:02d}.json", asdict(attempt))
        except Exception:
            run.error = "persistence_error"
            return run
        if attempt.status == "ERROR":
            run.error = attempt.error
            break
        if attempt.status == "VALID":
            run.terminal_state, run.final_result, run.resolved_tier = "RESOLVED", result, index
            break
        if index + 1 == len(adapters):
            run.scope_expansion_required = attempt.status == "INSUFFICIENT_EVIDENCE"
            run.terminal_state = ("UNRESOLVED_SCOPE_EXPANSION_REQUIRED" if run.scope_expansion_required
                                  else "UNRESOLVED_ALL_FAILED")

    try:
        store.write_json_once(run.run_path / "run.json", {"terminal_state": run.terminal_state,
                              "resolved_tier": run.resolved_tier, "scope_expansion_required": run.scope_expansion_required,
                              "error": run.error, "attempts": [asdict(a) for a in run.attempts]})
    except Exception:
        run.terminal_state, run.error = "ERROR", "persistence_error"
        run.final_result, run.resolved_tier, run.scope_expansion_required = None, None, False
    return run
