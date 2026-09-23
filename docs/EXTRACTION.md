# Extraction closeout — 2026-09-22

This dated record closes the extraction work. WORKLOG.md now tracks maintenance and outstanding publication gates. Detailed private inventories, creation evidence, scanner output and runtime artifacts remain outside the public repository.

## Included boundary

Include only what is necessary to understand, run, test or extend the general mechanism.

| Files/components | Why included |
|---|---|
| Seven modules under src/ | Provider adapters; explicit config; bounded packets; exact-citation validation; sequential council; evidence-driven escalation; exclusive raw records. |
| Package markers and pyproject.toml | Install the existing shared_ai_execution namespace from the requested physical layout, with explicit runtime dependencies and MIT metadata. |
| config/config.example.yaml and .env.example | Blank/reference-only configuration; mocks need no backend settings. |
| Three examples | Offline sequential execution, offline escalation, and a separately invoked configured provider request. |
| Synthetic tests | Packet/config boundaries, provider protocols, record preservation, evidence authority, capped calls, failure stops, safe imports and clean-template startup. |
| README.md, LICENSE, SECURITY.md | Usage, MIT terms, configuration adoption and explicit trust boundaries. |
| docs/DECISIONS.md and docs/PROVENANCE.md | Durable design choices, D003 divergence, exact owner attestation and concise reviewed lineage. |
| docs/EXTRACTION.md and docs/WORKLOG.md | Dated extraction evidence and a separate current maintenance handoff. |
| MANIFEST.in and .gitignore | Explicit source-distribution documents/examples; exclude runtime and build artifacts from normal tracking. |

## Excluded boundary

| Material | Reason excluded |
|---|---|
| Project/device integrations, private task schemas and operational configuration | Unnecessary to the generic hub; replaced by synthetic examples and explicit interfaces. |
| Machine/account identities, topology, endpoints, private paths, credentials and device identifiers | No public runtime requirement. The two exact owner-directed provenance/decision passages are narrowly documented text exceptions. |
| Operational logs, transcripts, evidence archives, screenshots, databases, model outputs, generated reports, backups, caches and runtime state | Not product source or reusable fixtures. Raw runtime preservation does not authorize publishing actual records. |
| Reader implementation/CLI and reader tests | Intentional v1 scope cut D001. |
| Full debate-store integration, model-mediated substance review, scheduler, viewer and speculative/dead features | Outside the supported standalone mechanism. |
| Original Git history/objects and private audit reports | Public history starts from the reviewed extraction; no upstream history is imported. |
| Provider executables, model weights and vendored dependencies | Separately installed components with their own terms; not redistributed here. |

## Implemented and verified

- **PROVEN — lineage:** the five original components and selected routing/citation core were cleared by component-specific local provenance review. No clean-room rewrite was required. The owner's attestation remains an attestation, not a legal determination.
- **PROVEN — ordering:** D003 was written before implementation files. Its removed legacy shortcuts are intentional. The reader remains deferred.
- **PROVEN — implementation:** the coordinator alone issues deterministic verdicts; operational errors stop; immutable input checks and write-before-next-call ordering are enforced. At most three coordinator adapter invocations are allowed.
- **PROVEN — Segment 3 validation:** 31 synthetic tests passed, including adversarial cases at each tier, repeated invalid evidence, malformed responses, throwing/mutating validators, insufficient coverage and excessive/infinite fallback plans. Wheel/editable installation, artifact membership, offline examples and synthetic Windows launch probes passed outside the checkout.
- **PROVEN — privacy:** each implementation batch passed known-string and working-tree Gitleaks 8.30.1 checks. Only exact owner-requested passages were exempted from private-name matching. A URL false positive in the private scanner was corrected without exempting source files.
- **PROVEN — source integrity:** 172 intermediate-source files and all reviewed upstream references retained their recorded hashes and timestamps. Source repositories were read-only throughout implementation.
- **PROVEN — reviewed corrections:** a real synthetic Windows command-script probe exposed quoting that mocked tests missed; the adapter and regression test were corrected. A packaging-harness argument reuse issue and documentation whitespace issue were corrected before handoff.
- **NOT TESTED — remaining live integrations:** CLI and cloud providers and arbitrary external validators have not been exercised live. The local smoke below does not establish compatibility for those integrations.

## Local Ollama live smoke — 2026-09-22 20:44 UTC

- **PROVEN — scope:** one benign synthetic prompt and exactly one generation request to a resident local model, executed without administrator privileges. No CLI provider, cloud provider, model pull or escalation was invoked. The test harness rejected additional generation requests and other provider invocations.

| Step | Result | Observed evidence |
|---|---|---|
| 1. Configuration loads | **PROVEN — PASS** | Public loader read an external temporary YAML file with whole-value process-environment references; required local-provider fields validated. Other providers remained unset. |
| 2. Provider adapter invokes real Ollama | **PROVEN — PASS** | Exactly one real adapter generation request; HTTP 200. Ambient proxies and redirects were disabled. |
| 3. Response parses correctly | **PROVEN — PASS** | Exactly one JSON parse; object envelope, done=true, nonempty text response, matching invocation identifier, no adapter error. Response length: 128 UTF-8 bytes. |
| 4. Validator receives/processes real response | **PROVEN — PASS** | One exact_citations/v1 invocation; validator-input and adapter-response SHA-256 values matched. Verdict VALID; reason EXACT_CITATIONS. Response was passed without rewriting; input packet remained unchanged. |
| 5. Clean exit | **PROVEN — PASS** | Supervised child exited with code 0 in 0.984 seconds; zero stderr bytes, no timeout, no hung child or unhandled exception. |

- **PROVEN — configuration/artifact isolation:** repository file hashes and timestamps were unchanged during execution. Temporary external configuration was deleted and process environment restored. Real endpoint/model settings and raw response artifacts remain outside the repository; none were copied into this worklog or repository files.
- **PROVEN — outcome:** first attempt passed all five steps; no implementation fix or failure-triggered synthetic test rerun was needed. Detailed process observations are retained in the private smoke evidence report.
- **SUPERSEDED — live-provider coverage:** the earlier no-live-provider coverage statement is superseded only for this local smoke. Other live providers remain NOT TESTED.

## Segment 4 closeout

- **PROVEN — documentation:** public quickstart, exact design principle, MIT terms and both required security-policy statements are recorded. Extraction chronology is closed here rather than carried forward in the maintenance log.
- **PROVEN — clean configuration:** both clean-template tests passed with an empty environment and with exactly the blank values shipped in .env.example. The shipped YAML resolved all provider fields to unset; synthetic sequential and escalation workflows and both offline quickstart scripts completed while HTTP, socket connections and provider subprocesses were blocked.
- **PROVEN — package closeout:** wheel and editable installation passed from outside the checkout; clean-template tests and offline examples passed against the installed package. Wheel MIT license expression/license file and README metadata were verified; source archive membership includes the required docs, templates and examples. No backend or global package installation was needed.
- **PROVEN — working-tree gate:** all 34 reviewed files passed known-string and Gitleaks 8.30.1 scanning before the first commit, with zero unapproved findings.
- **PROVEN — actual history gate:** the first implementation commit `7f457cf1fe9f7a80bc52c175525abddfe4d647d0` passed full-history and working-tree known-string/Gitleaks 8.30.1 scans with zero unapproved findings. Every decoded Git object, including old unreachable staging blobs, and Git text metadata were also scanned. Exact owner-text exceptions remained limited to the attestation and D003. The verification-only closeout commit is rescanned in the final handoff; no empty-history result is used as evidence.
- **SUPERSEDED — audit encoding:** the private history scanner initially decoded its exact-text exception source with the platform default encoding. Explicit UTF-8 restored exact matching and the full scan passed; no repository text or exception scope was broadened.
- **PROVEN — technical closeout:** the reviewed 34-file standalone scope is READY_TO_PUBLISH in the technical sense: implementation, documentation, license, synthetic/clean-config checks and fresh-history privacy checks are complete. This status does not grant publication authority or resolve contracts.
- **BLOCKED — publication:** employment/contract review and manual owner authorization remain required. A verified private vulnerability-reporting route must also be configured on the chosen host before public release; no endpoint is invented for this local-only repository.

## Identity annotation — 2026-09-23

**SUPERSEDED — package/import names only:** this closeout describes the original `local-agent-hub` distribution and `shared_ai_execution` namespace at public commits `7f457cf` and `8bf5210`. The later D004 rename amendment changes both public names to `hingework`; normalized distribution artifacts change from `local_agent_hub` to `hingework`. The original text above remains a historical record rather than being silently renamed.

**PROVEN — continuous provenance:** the five cleared modules and cleared escalation/validation components are the same implementations under the new package mapping. Their established provenance dispositions and the separate publication gates remain unchanged. PROVENANCE.md and its owner attestation are preserved verbatim; the original copyright attribution is retained. See the D004 amendment in [DECISIONS.md](DECISIONS.md) and current rename verification in [WORKLOG.md](WORKLOG.md).
