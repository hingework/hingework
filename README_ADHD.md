<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/brand/hingework-mark-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/brand/hingework-mark-light.svg">
  <img src="assets/brand/hingework-mark-light.svg" alt="Hingework Split Bridge Hinge H" width="64">
</picture>

# Hingework — quick guide

**Help with work, without the guesswork.**

## What it does

Run local models sequentially, or opt into evidence-driven escalation.

In escalation mode: try local first, check evidence, then return or advance. At most **three calls**.

## Install

Python 3.11+. From the checkout, in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -c "import hingework"
```

Other platforms: use `python3` and `.venv/bin/python`.

## Run

Sequential mock execution:

```powershell
.\.venv\Scripts\python.exe examples/fake_council.py
```

```text
['PASS', 'PASS']
```

Opt-in mock escalation:

```powershell
.\.venv\Scripts\python.exe examples/escalation_synthetic.py
```

```text
RESOLVED ['EVIDENCE_INVALID', 'VALID']
```

No backend or credentials needed. Examples make no network requests; installation may download dependencies. Temporary records are removed when examples exit.

## What happens

Sequential `PASS`: a nonempty response without an adapter error. No evidence-driven routing.

Escalation `VALID`: the local answer passes and returns immediately, or a configured fallback passes after an evidence failure.

**Provider or validator error → stop.** Confidence never triggers escalation.

Default validation checks exact citations, not whether the answer is true. Real runs preserve adapter text; keep records outside tracked source.

## Tiny pipeline

```text
LOCAL → CHECK → VALID → RETURN
           ├→ evidence failure → NEXT, if configured
           │                    → CHECK again
           └→ no attempts left → STOP unresolved

Operational error → STOP
Cap: 1 local + up to 2 fallbacks
```

The coordinator owns the evidence check. Models cannot declare their own escalation verdict.

## Full guide

[README: configuration, architecture, tests, security](README.md)
