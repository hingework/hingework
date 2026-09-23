"""Offline sequential example. Run after explicitly installing the package."""
from tempfile import TemporaryDirectory
from hingework import AdapterResult, ExecutionConfig, ModelSpec, run_local_council


class FakeAdapter:
    def __init__(self, model): self.model = model
    def invoke(self, packet):
        return AdapterResult("Synthetic response.\n", "fake", self.model, packet["invocation_id"])


def main():
    with TemporaryDirectory() as records:
        run = run_local_council("Describe the sample.", [{"summary": "A sample is available."}],
                                [ModelSpec("sample-a"), ModelSpec("sample-b")], ExecutionConfig(), records, FakeAdapter)
        print([attempt.status for attempt in run.attempts])


if __name__ == "__main__":
    main()
