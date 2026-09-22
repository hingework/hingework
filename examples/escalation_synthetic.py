"""Offline evidence-driven escalation using two synthetic adapters."""
from tempfile import TemporaryDirectory
from shared_ai_execution import AdapterResult, run_escalating_task


class FakeAdapter:
    def __init__(self, name, content): self.name, self.content = name, content
    def invoke(self, packet):
        return AdapterResult(self.content, "fake", self.name, packet["invocation_id"])


def main():
    packet = {"question": "What color is the sample?", "evidence": [{"path": "source-a", "content": "The sample is blue."}],
              "invocation_id": "example", "routing_class": "local_first", "task_contract": "citations_v1"}
    local = FakeAdapter("sample-local", "- path: source-a | quote: green")
    fallback = FakeAdapter("sample-fallback", "- path: source-a | quote: blue")
    with TemporaryDirectory() as records:
        run = run_escalating_task(packet, local, [fallback], records)
        print(run.terminal_state, [attempt.status for attempt in run.attempts])


if __name__ == "__main__":
    main()
