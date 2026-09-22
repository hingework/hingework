"""Bounded task envelopes. Evidence labels never cause filesystem access."""
from __future__ import annotations

import hashlib
import json
import re

MAX_PACKET_BYTES = 96 * 1024
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")


class PacketError(ValueError):
    pass


def validate_packet(packet: dict) -> dict:
    if not isinstance(packet, dict):
        raise PacketError("packet_not_object")
    required = {"question", "evidence", "invocation_id", "routing_class"}
    if not required <= packet.keys() or packet.keys() - (required | {"task_contract"}):
        raise PacketError("unsupported_packet_keys")
    if not isinstance(packet["question"], str) or not packet["question"].strip():
        raise PacketError("invalid_question")
    if not isinstance(packet["evidence"], list):
        raise PacketError("evidence_not_list")
    if not isinstance(packet["invocation_id"], str) or not _RUN_ID.fullmatch(packet["invocation_id"]):
        raise PacketError("invalid_invocation_id")
    if packet["routing_class"] != "local_first":
        raise PacketError("routing_requires_local_first")
    try:
        size = len(json.dumps(packet, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise PacketError("packet_not_json") from None
    if size > MAX_PACKET_BYTES:
        raise PacketError("packet_too_large")
    return packet


def validate_citation_packet(packet: dict) -> dict:
    validate_packet(packet)
    if packet.get("task_contract") != "citations_v1":
        raise PacketError("unsupported_task_contract")
    if not packet["evidence"]:
        raise PacketError("missing_evidence")
    labels = set()
    for item in packet["evidence"]:
        if not isinstance(item, dict) or set(item) != {"path", "content"}:
            raise PacketError("invalid_evidence_item")
        label, content = item["path"], item["content"]
        if (not isinstance(label, str) or not label or label.strip() != label
                or any(c in label for c in "\r\n|")):
            raise PacketError("invalid_source_label")
        if not isinstance(content, str) or label in labels:
            raise PacketError("invalid_or_duplicate_source")
        labels.add(label)
    return packet


def packet_hash(packet: dict) -> str:
    """Protect the question, ordered evidence, and selected rule contract."""
    data = {key: packet.get(key) for key in ("question", "evidence", "task_contract")}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                    allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def render_prompt(packet: dict) -> str:
    validate_packet(packet)
    evidence = json.dumps(packet["evidence"], ensure_ascii=False, separators=(",", ":"))
    prompt = (f"Task ID: {packet['invocation_id']}\nQuestion: {packet['question']}\n"
              f"Evidence: {evidence}\nRespond directly using only supplied evidence.")
    if packet.get("task_contract") == "citations_v1":
        validate_citation_packet(packet)
        prompt += ("\nUse CONCLUSION:, EVIDENCE:, and UNCERTAINTIES: sections."
                   "\nUnder EVIDENCE:, put each exact citation on its own line:"
                   "\n- path: source-label | quote: exact source substring"
                   "\nSource labels are opaque data. Do not open files or fetch evidence.")
    return prompt
