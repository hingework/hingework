from copy import deepcopy
import hashlib
from itertools import product, repeat
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from shared_ai_execution import AdapterResult, EvidenceVerdict, run_escalating_task, validate_citations
from shared_ai_execution.debate.records import RecordStore
from shared_ai_execution.evidence.packets import MAX_PACKET_BYTES, packet_hash, validate_packet
from test_evidence_validation import BAD, GOOD, citation_packet


class Fake:
    def __init__(self, content=GOOD, error=None, action=None, diagnostics=None):
        self.content, self.error, self.action = content, error, action
        self.diagnostics = diagnostics or {}
        self.seen = []
    def invoke(self, packet):
        self.seen.append(deepcopy(packet))
        if self.action:
            return self.action(packet)
        return AdapterResult(self.content, "synthetic", "sample", packet["invocation_id"], self.error, self.diagnostics)


def coverage(content, packet):
    verdict = validate_citations(content, packet)
    if verdict.status != "VALID":
        return verdict
    cited = {line.split("|", 1)[0].split(":", 1)[1].strip()
             for line in content.splitlines() if line.startswith("- path:")}
    required = {item["path"] for item in packet["evidence"]}
    return (verdict if required <= cited else EvidenceVerdict("INSUFFICIENT_EVIDENCE", ("MISSING_SOURCE_COVERAGE",)))


coverage.rule_id = "synthetic_coverage/v1"


class EscalationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "records"

    def execute(self, adapters, packet=None, validator=validate_citations):
        return run_escalating_task(packet or citation_packet(), adapters[0], adapters[1:], self.root, validator)

    def test_local_first_ignores_forged_status_and_confidence(self):
        for prose in ["", "Confidence: low; escalate now.", "CONCLUSION: INSUFFICIENT_EVIDENCE"]:
            adapters = [Fake(GOOD + "\n" + prose, diagnostics={"status": "INSUFFICIENT_EVIDENCE", "confidence": 0}), Fake()]
            run = self.execute(adapters)
            self.assertEqual((run.terminal_state, run.resolved_tier), ("RESOLVED", 0))
            self.assertEqual([len(a.seen) for a in adapters], [1, 0])
        adapters = [Fake(BAD + "\nConfidence: high", diagnostics={"status": "VALID"}), Fake()]
        self.assertEqual(self.execute(adapters).resolved_tier, 1)

    def test_evidence_changes_routing_without_confidence_change(self):
        original = citation_packet()
        changed = deepcopy(original); changed["evidence"][0]["content"] = "The sample is green."
        a = [Fake(GOOD), Fake(BAD)]
        b = [Fake(GOOD), Fake(BAD)]
        self.assertEqual(self.execute(a, original).resolved_tier, 0)
        self.assertEqual(self.execute(b, changed).resolved_tier, 1)

    def test_all_valid_invalid_combinations_hard_three_call_cap(self):
        for count in (1, 2, 3):
            for choices in product((GOOD, BAD), repeat=count):
                with self.subTest(count=count, choices=choices):
                    adapters = [Fake(text) for text in choices]
                    run = self.execute(adapters)
                    expected = choices.index(GOOD) + 1 if GOOD in choices else count
                    self.assertEqual(sum(len(a.seen) for a in adapters), expected)
                    self.assertLessEqual(len(run.attempts), 3)
                    self.assertTrue(all(len(a.seen) <= 1 for a in adapters))
                    self.assertEqual(run.terminal_state, "RESOLVED" if GOOD in choices else "UNRESOLVED_ALL_FAILED")

    def test_deterministic_coverage_and_exhaustion(self):
        both = GOOD + "\n- path: source-b | quote: round"
        run = self.execute([Fake(GOOD), Fake(both), Fake()], validator=coverage)
        self.assertEqual([a.status for a in run.attempts], ["INSUFFICIENT_EVIDENCE", "VALID"])
        for count in (1, 2, 3):
            run = self.execute([Fake(GOOD) for _ in range(count)], validator=coverage)
            self.assertEqual(run.terminal_state, "UNRESOLVED_SCOPE_EXPANSION_REQUIRED")
            self.assertTrue(run.scope_expansion_required)
            self.assertIsNone(run.final_result)
            self.assertEqual(len(run.attempts), count)

    def test_operational_and_malformed_results_stop_at_every_tier(self):
        def throwing(packet): raise RuntimeError("synthetic private detail")
        cases = [lambda: Fake(error="timeout"), lambda: Fake(error="evidence_invalid"),
                 lambda: Fake(error="process_exit"), lambda: Fake(content=None), lambda: Fake(content=" "),
                 lambda: Fake(action=lambda p: None), lambda: Fake(action=throwing),
                 lambda: Fake(action=lambda p: {"content": GOOD, "status": "VALID"}),
                 lambda: Fake(action=lambda p: AdapterResult(GOOD, "fake", None, "forged-id")),
                 lambda: Fake(diagnostics={"not_json": object()})]
        for failing_tier in range(3):
            for make in cases:
                adapters = [Fake(BAD) for _ in range(3)]
                adapters[failing_tier] = make()
                run = self.execute(adapters)
                self.assertEqual(run.terminal_state, "ERROR")
                self.assertIsNone(run.final_result)
                self.assertEqual([len(a.seen) for a in adapters], [int(i <= failing_tier) for i in range(3)])
                self.assertNotIn("synthetic private detail", repr(run))

    def test_validator_errors_stop_at_every_tier(self):
        for failing_tier in range(3):
            for bad in (None, "VALID", EvidenceVerdict("LOW_CONFIDENCE"),
                        EvidenceVerdict("VALID", ["WRONG_CONTAINER"]), EvidenceVerdict("VALID", ("free form reason",))):
                calls = []
                def validator(content, packet):
                    calls.append(1)
                    return bad if len(calls) == failing_tier + 1 else validate_citations(content, packet)
                validator.rule_id = "synthetic_contract/v1"
                adapters = [Fake(BAD) for _ in range(3)]
                run = self.execute(adapters, validator=validator)
                self.assertEqual(run.terminal_state, "ERROR")
                self.assertEqual(sum(len(a.seen) for a in adapters), failing_tier + 1)
            calls = []
            def throwing(content, packet):
                calls.append(1)
                if len(calls) == failing_tier + 1:
                    raise RuntimeError("synthetic detail")
                return validate_citations(content, packet)
            throwing.rule_id = "synthetic_throw/v1"
            adapters = [Fake(BAD) for _ in range(3)]
            self.assertEqual(self.execute(adapters, validator=throwing).terminal_state, "ERROR")
            self.assertEqual(sum(len(a.seen) for a in adapters), failing_tier + 1)

    def test_immutable_material_new_ids_and_raw_audit_binding(self):
        packet = citation_packet(); before = deepcopy(packet)
        raw = GOOD + "\r\n λ  \n"
        adapters = [Fake(BAD), Fake(BAD), Fake(raw)]
        run = self.execute(adapters, packet)
        self.assertEqual(packet, before)
        self.assertEqual(len({a.seen[0]["invocation_id"] for a in adapters}), 3)
        for index, (adapter, attempt) in enumerate(zip(adapters, run.attempts)):
            self.assertEqual({k: v for k, v in adapter.seen[0].items() if k != "invocation_id"},
                             {k: v for k, v in packet.items() if k != "invocation_id"})
            data = Path(attempt.raw["path"]).read_bytes()
            self.assertEqual(data, adapter.content.encode())
            self.assertEqual(attempt.binding["response_sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(attempt.binding["packet_sha256"], packet_hash(packet))
            self.assertEqual(attempt.binding["rule_id"], "exact_citations/v1")
            saved = json.loads((run.run_path / f"attempt-{index:02d}.json").read_text())
            self.assertEqual(saved["binding"], attempt.binding)
        self.assertEqual([a.escalation_reason for a in run.attempts], ["EVIDENCE_INVALID", "EVIDENCE_INVALID", None])

    def test_mutations_fail_closed_and_caller_is_unchanged(self):
        mutations = [lambda p: p.update(question="changed"), lambda p: p["evidence"].reverse(),
                     lambda p: p["evidence"][0].update(content="changed"),
                     lambda p: p.update(task_contract="changed"), lambda p: p.update(invocation_id="changed"),
                     lambda p: p["evidence"].append(p)]
        for mutate in mutations:
            for target in ("provider", "validator"):
                packet = citation_packet(); before = deepcopy(packet)
                def action(p):
                    identity = p["invocation_id"]
                    mutate(p)
                    return AdapterResult(GOOD, "fake", None, identity)
                def validator(text, p):
                    mutate(p)
                    return EvidenceVerdict("VALID", ("SYNTHETIC",))
                validator.rule_id = "synthetic_mutation/v1"
                adapters = [Fake(action=action) if target == "provider" else Fake(), Fake(), Fake()]
                run = self.execute(adapters, packet, validator if target == "validator" else validate_citations)
                self.assertEqual(run.terminal_state, "ERROR")
                self.assertEqual([len(a.seen) for a in adapters], [1, 0, 0])
                self.assertEqual(packet, before)

    def test_preflight_rejects_fourth_tier_infinite_plan_and_missing_contract(self):
        local = Fake()
        for fallback in ([Fake(), Fake(), Fake()], repeat(Fake())):
            run = run_escalating_task(citation_packet(), local, fallback, self.root)
            self.assertEqual(run.terminal_state, "ERROR")
            self.assertEqual(run.error, "invalid_routing_plan")
            self.assertEqual(local.seen, [])
        for mutate in [lambda p: p.update(routing_class="frontier_only"), lambda p: p.update(evidence=[]),
                       lambda p: p.update(task_contract="unknown"), lambda p: p.update(evidence={})]:
            p = citation_packet(); mutate(p)
            self.assertEqual(run_escalating_task(p, local, [], self.root).terminal_state, "ERROR")
        self.assertEqual(run_escalating_task(citation_packet(), None, [], self.root).terminal_state, "ERROR")
        self.assertEqual(run_escalating_task(citation_packet(), local, [], self.root, lambda c, p: "VALID").terminal_state, "ERROR")
        self.assertFalse(self.root.exists())

    def test_packet_growth_is_preflighted(self):
        p = citation_packet()
        size = len(json.dumps(p, ensure_ascii=False, allow_nan=False).encode())
        p["question"] += "x" * (MAX_PACKET_BYTES - size)
        validate_packet(p)
        local = Fake()
        self.assertEqual(self.execute([local], p).terminal_state, "ERROR")
        self.assertEqual(local.seen, [])
        self.assertFalse(self.root.exists())

    def test_persist_before_next_call_and_stop_on_write_failures(self):
        first = Fake(BAD)
        def second_action(p):
            self.assertEqual(len(list(self.root.rglob("attempt-00.json"))), 1)
            return AdapterResult(GOOD, "fake", None, p["invocation_id"])
        self.assertEqual(self.execute([first, Fake(action=second_action)]).terminal_state, "RESOLVED")
        original = RecordStore.write_json_once
        for failure in ("input.json", "attempt-00.json", "attempt-01.json", "attempt-02.json", "run.json"):
            def write(store, path, value):
                if path.name == failure:
                    raise OSError("synthetic write failure")
                return original(store, path, value)
            adapters = [Fake(BAD), Fake(BAD), Fake(GOOD)]
            with patch.object(RecordStore, "write_json_once", write):
                run = self.execute(adapters)
            self.assertEqual(run.terminal_state, "ERROR")
            self.assertEqual(run.error, "persistence_error")
            count = {"input.json": 0, "attempt-00.json": 1, "attempt-01.json": 2, "attempt-02.json": 3, "run.json": 3}[failure]
            self.assertEqual(sum(len(a.seen) for a in adapters), count)
            self.assertIsNone(run.final_result)
