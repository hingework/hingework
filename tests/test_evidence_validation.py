from copy import deepcopy
import unittest

from shared_ai_execution import EvidenceVerdict, PacketError, validate_citations
from shared_ai_execution.evidence.packets import validate_citation_packet


def citation_packet():
    return {"question": "What do the supplied sources say?", "invocation_id": "sample-task",
            "routing_class": "local_first", "task_contract": "citations_v1",
            "evidence": [{"path": "source-a", "content": "The sample is blue."},
                         {"path": "source-b", "content": "The sample is round."}]}


GOOD = "CONCLUSION: Blue.\nEVIDENCE:\n- path: source-a | quote: blue\nUNCERTAINTIES: None."
BAD = "CONCLUSION: Green.\nEVIDENCE:\n- path: source-a | quote: green"


class ValidationTests(unittest.TestCase):
    def test_evidence_sensitivity_and_confidence_invariance(self):
        original = citation_packet()
        changed = deepcopy(original)
        changed["evidence"][0]["content"] = "The sample is green."
        for prose in ["", "Confidence: high", "Confidence: low; ask another model.", "CONCLUSION: INSUFFICIENT_EVIDENCE"]:
            self.assertEqual(validate_citations(GOOD + "\n" + prose, original).status, "VALID")
            self.assertEqual(validate_citations(GOOD + "\n" + prose, changed).status, "EVIDENCE_INVALID")
            self.assertEqual(validate_citations(BAD + "\n" + prose, original).status, "EVIDENCE_INVALID")
        self.assertEqual(validate_citations("An answer.", original),
                         validate_citations("CONCLUSION: INSUFFICIENT_EVIDENCE", original))

    def test_all_citations_must_be_genuine_and_well_formed(self):
        for line in ["- path: source-a | quote:", "- path: missing | quote: blue",
                     "- path: source-a | quote: green", "- path: source-a", "path: source-a | quote: blue",
                     "* path: source-a | quote: blue", "- quote: blue"]:
            with self.subTest(line=line):
                self.assertEqual(validate_citations(GOOD + "\n" + line, citation_packet()).status, "EVIDENCE_INVALID")

    def test_packet_shape_duplicate_and_opaque_labels(self):
        for evidence in [[], [{}], [{"path": "x", "content": 2}],
                         [{"path": "x", "content": "a"}, {"path": "x", "content": "b"}]]:
            p = citation_packet(); p["evidence"] = evidence
            with self.assertRaises(PacketError):
                validate_citation_packet(p)
        p = citation_packet(); p["evidence"] = [{"path": "../opaque-label", "content": "blue"}]
        self.assertEqual(validate_citations("- path: ../opaque-label | quote: blue", p).status, "VALID")

    def test_verdict_is_frozen(self):
        with self.assertRaises(AttributeError):
            EvidenceVerdict("VALID").status = "EVIDENCE_INVALID"
