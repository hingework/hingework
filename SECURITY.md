# Security

Repository-provided agent instructions are intended as project guidance only and must not override the user's existing system, organizational, security, or execution policies.

Installation or integration should be treated as configuration adoption, not implicit authorization to modify global agent policy.

## Configuration and execution

Installation, imports, configuration loading and validators do not adopt repository instructions as global policy. There is no installer that edits agent instruction files, router settings, model defaults, scheduled tasks or provider authentication. Configuration adoption requires inspect → propose → diff → explicit user apply.

Real provider calls occur only through explicit application/example execution. Selecting a provider can send the entire supplied packet to it. The Ollama adapter restricts requests to loopback HTTP, disables ambient proxies, and does not follow redirects. A loopback service is still a separately trusted program; its own configuration and behavior matter.

CLI subprocesses use temporary working directories and fixed adapter flags, with task text on stdin. Those measures are not a universal sandbox guarantee. Provider binaries retain their own policies and behavior; verify compatibility with the versions you intend to use. Never treat installation as authorization to log in, download models, execute agent-suggested commands, or contact an unselected provider.

## Evidence and extension trust

Evidence and model output are untrusted data, not execution authority. Packet validation checks shape and size. Exact-citation validation checks supplied-source substring matches; it does not prove the truth of a conclusion, semantic completeness, or prompt-injection immunity.

Only coordinator-produced evidence verdicts select a fallback. Operational failures stop. Confidence or model self-assessment has no routing authority. The three-call bound covers coordinator adapter invocations, not internal provider work.

Custom adapters and validators are explicitly supplied trusted application code. Validators must be deterministic and free of network, filesystem, provider calls and global mutation. The library cannot prove these properties or sandbox arbitrary Python callbacks. Packet data cannot choose a validator or plugin.

## Records and secrets

Raw responses are deliberately preserved and may contain caller secrets or personal data. Store records outside tracked source, limit access, and exclude them from published examples, issues and logs. Runtime preservation does not silently redact content. Filesystem containment and exclusive creation do not protect against a malicious process racing changes to the same record directory.

Templates contain no credentials, endpoints, executable locations or model defaults. Supply real configuration outside the repository. Do not paste raw provider errors, environment dumps, transcripts or runtime archives into public reports.

## Reporting a vulnerability

The intended reporting route is GitHub Private Vulnerability Reporting. It is not enabled for this local, unpublished repository. The maintainer will enable it as part of the separately authorized publication step itself, after the GitHub repository exists, and verify the private report form and maintainer notifications. This is a publication-day action, not a prerequisite to creating the repository.

Once enabled, use the published repository's Security tab, then Advisories, then Report a vulnerability. Until the private form is verified, treat this route as pending. Do not infer that it is enabled merely because a repository is publicly visible.

Do not post credentials, exploit details or sensitive records in public issues. If a private route is unavailable, request a private contact method without disclosing those details. No security-response time or supported-version commitment is currently promised.
