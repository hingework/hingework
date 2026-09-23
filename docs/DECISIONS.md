# Architectural decisions

## D001 — Defer the record reader CLI from v1

**Status: PROVEN — owner-directed v1 scope decision, recorded 2026-09-22.** The reader surface is excluded from the implemented v1 scope.

**Decision:** the record reader CLI is an intentional v1 scope cut. Do not include the optional record-reader implementation, top-level reader launcher, reader-specific API exports or reader-specific tests in the initial public extraction. Do not advertise reader commands in the README or examples.

**Rationale:** v1 contains reusable execution, bounded evidence, sequential and evidence-driven orchestration, and persistence mechanisms. The reader CLI is an additional convenience surface for inspecting previously stored runs; it is not needed to execute or test those mechanisms. Its deferral is a product-scope decision, not a finding that reader code is unsafe or third-party-derived.

**Consequences:** retain the record writer, raw UTF-8 artifacts, metadata, hashes and deterministic reconciliation input. Synthetic persistence tests still read their temporary artifacts directly and verify integrity. Users can inspect the documented files with ordinary tools; v1 provides no dedicated reader CLI or reader API compatibility guarantee. Existing private installations are not changed.

**Revisit when:** an explicit supported use case requires browsing or verifying stored runs through a hub-provided API/CLI. Before inclusion, check provenance and the public-extraction rule, define the reader surface, and include synthetic tests for malformed records, integrity failures and path containment. Do not import real run archives as fixtures.

## D002 — Include bounded evidence-driven escalation

**Status: PROVEN — owner-directed scope restoration, recorded 2026-09-22.** The earlier omission-boundary Gate 2 PASS is **SUPERSEDED**. Implemented under D003; synthetic acceptance checks are recorded in EXTRACTION.md.

**Design principle, verbatim:**

Local/cheap execution is attempted first. Escalation occurs only when deterministic evidence rules require it — not because a model reports low confidence or "thinks" another model should review.

**Decision:** include an explicit local-first escalation entry point, a trusted validator-to-router result contract, and synthetic tests. Keep the existing sequential council API distinct. Run at most one local call and at most two caller-configured fallback calls, stopping on a VALID evidence verdict. Preserve the original bounded material and the full attempted-result trail. No automatic retry, evidence expansion, provider discovery, previous-answer forwarding or consensus claim.

**INFERRED — design consequences of the principle:** only trusted EVIDENCE_INVALID or INSUFFICIENT_EVIDENCE verdicts advance to a configured next tier. The coordinator runs the deterministic validator; model text, confidence, self-assigned verdicts and arbitrary provider diagnostics have no routing authority. Operational failures, contract errors, persistence failures and packet mutation stop. The default exact-citation checker does not claim general semantic-sufficiency detection; an explicit deterministic application validator may produce INSUFFICIENT_EVIDENCE.

**Explicit legacy differences:** do not retain the old model-declared-insufficiency shortcut, operational-error fallback or frontier-only bypass. Exclude project-specific/model-mediated substance review and the old store integration. These are deliberate constraints under the owner's current principle, not assertions that the legacy code already enforced them.

**Provenance:** the selected routing, bounded-chain and citation-validation functions have independently verified local creation/refactor histories and are CLEARED_FOR_EXTRACTION. Use concise component/revision attribution in the provenance document; keep detailed private session/history evidence outside the public repository. Contract review continues to gate actual publication.

**Acceptance:** tests must change evidence while holding confidence constant, and change confidence/review-request text while holding valid evidence constant. Also test deterministic insufficiency, tier exhaustion, immutable material, operational/mutation stops, raw preservation and explicit opt-in. Offline acceptance checks exercise these properties; live provider compatibility is a separate check.

## D003 — Deliberate public normalization

D003: The public escalation logic is deliberately stricter than the legacy GrowBot/production version. Three behaviors were intentionally removed to enforce the stated design principle (escalation is evidence-driven only, never confidence/self-assessment-driven): the model-declared INSUFFICIENT_EVIDENCE shortcut, the operational-error-triggers-escalation fallback, and the frontier_only bypass. Operational errors now stop rather than escalate. This is intentional normalization to the public design principle, not accidental feature loss — anyone comparing this to GrowBot history should read it as a deliberate divergence.

## D004 — Configuration and packaging

Explicit setuptools mapping preserves the `shared_ai_execution` import namespace in the requested physical layout. Configuration is loaded only from an explicit JSON/YAML file, with whole-value environment references. No config discovery, implicit executable selection, installer hooks or global policy writes. Any future adoption tooling must implement inspect → propose → diff → explicit user apply.

Raw adapter text is preserved as UTF-8 bytes; this does not claim preservation of original network bytes. Runtime records are excluded from distribution.

### D004 amendment — Public/package identity rename — 2026-09-23

**PROVEN — owner-directed rename:** the distribution name changes from `local-agent-hub` (normalized artifact prefix `local_agent_hub`) to `hingework`, and the import namespace changes from `shared_ai_execution` to `hingework`. The physical `src/` layout and explicit setuptools mapping remain. This dated amendment adds the requested rename decision to the existing D004; it does not erase or renumber the original configuration decision.

**PROVEN — clean break:** no deprecated import alias or compatibility shim is shipped. This is a pre-publication rename with no existing external users, as stated by the owner. Examples, test imports/mock targets, template environment names (`LOCAL_AGENT_HUB_*` to `HINGEWORK_*`), and temporary/probe naming follow the new identity. No external configuration is automatically migrated. API signatures, validation/routing rules, dependencies, and the version are unchanged.

**PROVEN — provenance continuity:** the provenance clearance already established for config, packets, providers, council, records, and the escalation/validation components applies unchanged to their renamed forms. This is a rename of the same code, not new implementation requiring provenance re-review. The original attestation, component revisions and ownership disposition in PROVENANCE.md remain verbatim. Existing copyright attribution is retained. The historical public commits `7f457cf` and `8bf5210` are not rewritten.

**SUPERSEDED — namespace only:** D004's earlier `shared_ai_execution` naming statement and EXTRACTION.md's original packaging description describe the pre-rename snapshot. Only those naming choices are superseded; their technical/provenance findings and publication gates still apply.

**NOT TESTED — registration acceptance:** the fresh PyPI lookup is recorded in WORKLOG.md. A public 404 is evidence of no visible project, not a reservation or a guarantee that an eventual upload will be accepted. No registration or publication is authorized here.

## D005 — Integration boundaries

Custom adapters and deterministic validators are explicitly supplied trusted application code. The coordinator limits its own adapter invocations to three; it cannot sandbox arbitrary extension code or limit work that an external provider performs internally. Default citation validation proves exact supplied-source matches, not semantic correctness. Source labels never trigger file reads.

Preflight rejects malformed input and missing selected-provider configuration before persistence or execution. Operational errors stop escalation. Temporary working directories and provider flags do not promise a universal sandbox for vendor CLIs. Windows command scripts receive only fixed adapter flags on the command line; task text is stdin-only. Native executable and command-script compatibility must be checked for supported provider versions before release.

## D006 — Public history and license metadata

The first public history is deliberately created from the reviewed standalone snapshot, using a descriptive implementation commit, followed by a verification-closeout commit. No private history is imported and no intermediate extraction states are presented as product history. Commit author/committer fields use the generic project contributor identity and a non-deliverable .invalid address, avoiding private workstation identity defaults. This metadata convention does not substitute for the owner attestation or establish publication rights.

The MIT notice uses the project contributor label. Modern SPDX/license-file package metadata requires setuptools 77 or newer; the runtime dependency set is unchanged. Dependencies, provider software and model weights retain their separate terms.
