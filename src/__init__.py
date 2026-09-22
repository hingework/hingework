"""Explicit execution and immutable run artifacts; importing starts no work."""
from .adapters.providers import AdapterResult, ClaudeAdapter, CodexAdapter, OllamaAdapter
from .debate.records import RecordStore, RecordStoreError
from .evidence.packets import PacketError, render_prompt, validate_packet
from .orchestration.config import ExecutionConfig, ProviderConfigError, load_execution_config
from .orchestration.council import CouncilAttempt, CouncilRun, ModelSpec, run_local_council
from .evidence.validation import EvidenceVerdict, validate_citations
from .orchestration.escalation import EscalationAttempt, EscalationRun, run_escalating_task

__all__ = ["AdapterResult", "ClaudeAdapter", "CodexAdapter", "OllamaAdapter", "RecordStore",
           "RecordStoreError", "PacketError", "render_prompt", "validate_packet", "ExecutionConfig",
           "ProviderConfigError", "load_execution_config", "CouncilAttempt", "CouncilRun", "ModelSpec",
           "run_local_council", "EvidenceVerdict", "validate_citations", "EscalationAttempt",
           "EscalationRun", "run_escalating_task"]
