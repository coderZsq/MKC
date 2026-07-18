# Error Handling Runbook

S5-6 standardizes recoverable errors across Gateway, AI Service, SSE streams,
and the Flutter client. Responses keep the existing envelope and include the
same error payload everywhere:

```json
{
  "code": "LLM_TIMEOUT",
  "message": "模型响应超时，请稍后重试",
  "trace_id": "abc",
  "retryable": true,
  "details": {}
}
```

## Error Codes

| Code | HTTP | Retry | User Message | Triage |
|---|---:|---:|---|---|
| FILE_TOO_LARGE | 413 | no | 文件超过大小限制 | Check upload limit and client file size. |
| TASK_NOT_FOUND | 404 | no | 任务不存在或已过期 | Verify task id, owner, and retention. |
| RETRIEVAL_TIMEOUT | 504 | yes | 检索超时，请稍后重试 | Check vector store latency and query fanout. |
| RETRIEVAL_UNAVAILABLE | 503 | yes | 检索服务暂不可用，请稍后重试 | Check Milvus/Chroma health and fallback logs. |
| LLM_TIMEOUT | 504 | yes | 模型响应超时，请稍后重试 | Check provider latency, retries, and prompt size. |
| LLM_UNAVAILABLE | 503 | yes | 模型服务暂不可用，请稍后重试 | Check provider auth, quota, endpoint, and fallback. |
| LLM_STREAM_ERROR | 500 | yes | 模型服务暂不可用，请稍后重试 | Inspect SSE logs with `trace_id`. |
| DEPENDENCY_UNAVAILABLE | 503 | yes | 依赖服务暂不可用，请稍后重试 | Check Redis, MinIO, DB, or AI Service status. |
| INTERNAL_ERROR | 500 | no | 服务繁忙，请稍后重试 | Search logs by `trace_id` and error code. |

## Retry Policy

Only idempotent or explicitly safe operations should be retried automatically:

- Safe: status polling, read APIs, SSE reconnect, retrieval, LLM stream retry by user action.
- Not safe by default: upload writes, task creation, message persistence, provider calls that may bill twice.
- Backoff defaults: max 2 retries, 300 ms base backoff for short dependency calls.

## Degradation

When retrieval succeeded but the LLM stream fails, AI Service may return a
degraded answer built from retrieved snippets and mark the `done` event with
`degraded: true`. If there is no useful context, it emits `event: error` with
the standardized payload.

## Security

Error messages are sanitized before returning to clients. Do not include stack
traces, SQL, credentials, local file paths, raw prompts, or document chunks in
client-facing errors. Logs should include `trace_id`, error code, and stable
context ids such as task id or resource id.
