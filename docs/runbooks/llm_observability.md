# LLM Observability Runbook

S5-5 adds optional LLM call observation for debugging prompt quality, model
latency, token usage, and provider failures. It is disabled by default and
falls back to a noop observer when SDKs or credentials are unavailable.

## Configuration

Set the provider in `ai-service/config/ai.yaml` or the environment:

```text
LLM_OBSERVABILITY_PROVIDER=none
LLM_PROMPT_VERSION=qa_v1
LLM_OBSERVABILITY_REDACT=true
LLM_OBSERVABILITY_MAX_PROMPT_CHARS=2000
LLM_OBSERVABILITY_MAX_COMPLETION_CHARS=2000
```

Langfuse:

```text
LLM_OBSERVABILITY_PROVIDER=langfuse
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```

LangSmith:

```text
LLM_OBSERVABILITY_PROVIDER=langsmith
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=mkc-dev
```

## Recorded Fields

Each event includes `trace_id`, `prompt_version`, provider, model, latency,
token counts, status, and an optional error code. Prompt and completion text
are redacted and truncated before leaving the process.

## Safety

Keep this disabled in shared environments unless the target project has been
approved for storing sanitized prompts and completions. The observer redacts
common secret markers and truncates content, but it should not be treated as a
replacement for data classification or access control.

## Troubleshooting

- Missing credentials: the app logs `LLM_OBSERVER_CONFIG_MISSING` and continues.
- Export failure: the app logs `LLM observer export failed` and continues.
- No events visible: verify provider env vars and call `flush()` in one-off
  scripts before process exit.
