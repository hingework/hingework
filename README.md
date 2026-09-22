# local-agent-hub

A small Python library for explicit provider execution, bounded evidence, and recorded results. Its distinguishing behavior is **evidence-driven escalation**: a deterministic validator checks each response before the coordinator decides whether another configured provider may run.

Local/cheap execution is attempted first. Escalation occurs only when deterministic evidence rules require it — not because a model reports low confidence or "thinks" another model should review.

## Quickstart without a backend

Requires Python 3.11 or newer. From this checkout in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe examples/fake_council.py
.\.venv\Scripts\python.exe examples/escalation_synthetic.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_clean_config.py -v
```

The first example prints two `PASS` results. The second prints `RESOLVED` with `EVIDENCE_INVALID` followed by `VALID`: the synthetic local answer has an incorrect citation, and the synthetic fallback has an exact citation. Examples keep their records in temporary directories and remove them afterward. Neither requires Ollama, a provider CLI, credentials, a model download, or any provider configuration. Package installation may download Python dependencies; the examples themselves make no network requests.

On other platforms, create the environment with `python3 -m venv .venv` and use `.venv/bin/python` for the remaining commands. The same package is imported as `shared_ai_execution`.

Run the full synthetic suite with `python -m unittest discover -s tests -v` using the environment's Python. The Windows-specific command-line test is skipped elsewhere.

## Execution and escalation

`run_local_council` runs the caller's local model sequence in order and records each result. It never adds a fallback provider. `run_escalating_task` is a separate, explicit opt-in API:

```python
run = run_escalating_task(
    packet,
    local_adapter,
    fallback_adapters,  # zero, one, or two explicit adapters
    record_root,
)
```

See the complete [offline escalation example](examples/escalation_synthetic.py) for a runnable packet and adapters. The first adapter is the caller-designated local/cheap executor. The coordinator makes at most three adapter calls: one local call followed, if needed, by at most two ordered fallbacks. It performs no retries, provider discovery, concurrent fallback calls, or evidence expansion.

| Coordinator result | Action |
|---|---|
| `VALID` | Stop with `RESOLVED`; identify the successful tier. |
| `EVIDENCE_INVALID` | Record the attempt, then advance if a configured tier remains; otherwise `UNRESOLVED_ALL_FAILED`. |
| `INSUFFICIENT_EVIDENCE` | Advance only when an explicitly supplied deterministic validator computes this verdict; exhaustion yields `UNRESOLVED_SCOPE_EXPANSION_REQUIRED`. Nothing is fetched automatically. |
| Operational/integration failure | Stop with `ERROR`. This includes provider errors, malformed envelopes, validator failures, input mutation, and record-write failures. |

The coordinator invokes the validator itself. Model confidence, requests for review, self-declared statuses, and provider diagnostics cannot authorize escalation. Each attempt gets the same original question, ordered evidence, and task contract, with a fresh invocation identifier. Previous model answers are not forwarded. Recorded verdicts bind the validator rule/version, invocation ID, packet hash, and raw-response hash.

The default `validate_citations` rule accepts packets with `task_contract="citations_v1"` and a nonempty list of unique `{path, content}` sources. Source paths are opaque labels; no files are opened. Response citations use this exact line format:

```text
- path: source-a | quote: blue
```

At least one citation must match. Every citation must name a supplied source and quote a nonempty substring of its content. Do not add quote wrappers unless they occur in the source. The default rule verifies citation mechanics, **not semantic correctness**, and never produces `INSUFFICIENT_EVIDENCE`. A custom pure, deterministic validator can implement a domain's coverage rule; it returns `EvidenceVerdict` and declares a versioned `rule_id`, such as `coverage/v1`.

## Configuration adoption

[config/config.example.yaml](config/config.example.yaml) contains only whole-value environment references. [.env.example](.env.example) lists their names with blank values. Loading the YAML with no variables set is valid and leaves all providers unset; mocks work in that state. Selecting a real provider requires its explicit endpoint/command and positive timeout. Model selection and record location are explicit invocation inputs.

There is no dotenv auto-loader, global configuration discovery, implicit executable selection, or setup hook. Configuration loading is read-only. Adopt configuration deliberately:

1. Inspect the template and the current configuration you intend to use.
2. Prepare a separate proposed configuration outside the checkout; keep actual values out of version control.
3. Review the diff against the intended target, redacting sensitive values.
4. Explicitly apply the proposal yourself. Importing or installing this package does not apply it.

`load_execution_config(path)` accepts an explicit JSON or YAML path, rejects duplicate/unknown keys, and resolves only named `{env: VARIABLE_NAME}` references. No ambient setting overrides a literal. Missing configuration fails before invocation; it does not authorize a fallback.

The provided Ollama adapter accepts only an explicit loopback HTTP endpoint and disables ambient proxies and redirects. CLI adapters require an explicit executable and timeout; authentication remains owned by the separately configured provider. [provider_request.py](examples/provider_request.py) is an optional single-provider example; unlike the quickstart, explicitly running it requires a configured backend and may send evidence to that provider.

## Storage and extension points

`RecordStore` writes exclusive per-run artifacts, preserves adapter response text as UTF-8 bytes, and records hashes. This is preservation of adapter text, not original network bytes. Treat runtime records as sensitive and keep them outside tracked source. Path containment checks do not provide isolation from another process concurrently manipulating the filesystem.

Extensions are ordinary trusted Python code: `invoke(packet) -> AdapterResult`, a deterministic validator, or the sequential adapter factory. The coordinator bounds its own calls; it cannot sandbox arbitrary extensions or control internal work performed by a provider. No scheduler, service, viewer, full debate state machine, or record-reader CLI is shipped. The reader is intentionally deferred under [D001](docs/DECISIONS.md).

## Layout and license

`src/adapters` holds providers; `src/evidence` holds bounded packets and validation; `src/debate` holds record storage; `src/orchestration` holds configuration, sequential execution and escalation. Explicit package mapping preserves the `shared_ai_execution` namespace. Tests and examples are synthetic.

The hub code is offered under the [MIT license](LICENSE). Separately installed dependencies, provider programs and model weights retain their own terms. See [provenance](docs/PROVENANCE.md), [architectural decisions](docs/DECISIONS.md), and [security guidance](SECURITY.md).
