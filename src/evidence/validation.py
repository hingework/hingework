"""Pure exact-citation validation; no semantic sufficiency or confidence scoring."""
from dataclasses import dataclass
import re

from .packets import validate_citation_packet


@dataclass(frozen=True)
class EvidenceVerdict:
    status: str
    reason_codes: tuple[str, ...] = ()


_CITATION = re.compile(r"^\s*-\s*path:\s*(?P<path>[^|\r\n]+?)\s*\|\s*quote:\s*(?P<quote>[^\r\n]*)$")


def validate_citations(content: str, packet: dict) -> EvidenceVerdict:
    """Check every citation line against supplied source labels and exact substrings.

    At least one citation is required. Any malformed citation candidate fails the
    response, even when another citation is valid. Quoted wrappers are not stripped:
    the quote field is literal source text (apart from surrounding whitespace).
    This verifies citations, not whether arbitrary conclusions follow from them.
    """
    validate_citation_packet(packet)
    if not isinstance(content, str):
        raise ValueError("response_not_text")
    sources = {item["path"]: item["content"] for item in packet["evidence"]}
    count = 0
    for line in content.splitlines():
        # Catch incomplete/misspelled-format candidates as well as valid lines.
        if not re.match(r"^\s*(?:[-*]\s*)?(?:path|quote)\s*:", line, re.IGNORECASE):
            continue
        match = _CITATION.fullmatch(line)
        if not match:
            return EvidenceVerdict("EVIDENCE_INVALID", ("MALFORMED_CITATION",))
        path, quote = match["path"].strip(), match["quote"].strip()
        if path not in sources:
            return EvidenceVerdict("EVIDENCE_INVALID", ("UNKNOWN_SOURCE",))
        if not quote or quote not in sources[path]:
            return EvidenceVerdict("EVIDENCE_INVALID", ("QUOTE_NOT_FOUND",))
        count += 1
    if not count:
        return EvidenceVerdict("EVIDENCE_INVALID", ("NO_CITATIONS",))
    return EvidenceVerdict("VALID", ("EXACT_CITATIONS",))


validate_citations.rule_id = "exact_citations/v1"
