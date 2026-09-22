"""Explicit single-provider request; never invoked by import or installation."""
import argparse
from shared_ai_execution import ClaudeAdapter, CodexAdapter, OllamaAdapter, load_execution_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--provider", choices=("ollama", "codex", "claude"), required=True)
    parser.add_argument("--model")
    args = parser.parse_args()
    config = load_execution_config(args.config)
    config.require(args.provider)
    if args.provider == "ollama":
        if not args.model:
            parser.error("--model is required for ollama")
        adapter = OllamaAdapter(config.ollama_base_url, args.model, config.ollama_timeout_s)
    elif args.provider == "codex":
        adapter = CodexAdapter(config.resolve_codex(), config.codex_timeout_s)
    else:
        adapter = ClaudeAdapter(config.resolve_claude(), config.claude_timeout_s)
    result = adapter.invoke({"question": "Describe this synthetic sample.", "evidence": ["The sample is blue."],
                             "invocation_id": "synthetic-example", "routing_class": "local_first"})
    print(result.error or result.content)


if __name__ == "__main__":
    main()
