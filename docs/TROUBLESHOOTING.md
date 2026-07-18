# Troubleshooting

Use this guide for local development and PR verification. When an API response includes `trace_id`, search Gateway and AI Service logs with that value first.

## Quick Checks

```bash
git status --short --branch
kubectl get pods -n mkc-dev
curl http://localhost:8080/health
curl http://localhost:5001/api/v1/health
```

Application logs from `./scripts/local-dev-up.sh` live under `.mkc-dev/logs/`.

## Common Local Failures

| Symptom | Likely Cause | Fix |
|---|---|---|
| `local-dev-up.sh` says MySQL is unavailable | `port-forward.sh` is not running | Start `./infra/scripts/port-forward.sh` in another terminal |
| Tasks stay at `pending / 0%` | Celery worker is not running or cannot reach Redis | Check `.mkc-dev/logs/ai-worker.log` and `redis://:dev-redis@localhost:6379/1` |
| Gateway returns AI dependency errors | AI Service is down or internal key mismatch | Check `APP_AI_SERVICE_BASE_URL`, `APP_AI_SERVICE_INTERNAL_KEY`, and AI logs |
| Upload succeeds but parsing fails | Worker cannot read MinIO or file type is unsupported | Check MinIO credentials, bucket, and task error details |
| Embedding write fails with dimension mismatch | Embedding model and vector collection dimensions differ | Align `EMBEDDING_DIMENSIONS` and `VECTOR_STORE_DIMENSIONS`, then rebuild vectors |
| Flutter Web cannot call API | Wrong `BASE_URL` or CORS issue | Run with `--dart-define=BASE_URL=http://localhost:8080/api/v1` |
| SSE stops or never completes | Gateway, AI stream, or ingress buffering issue | Test locally without ingress, then inspect stream logs by `trace_id` |

## Dependency Commands

```bash
kubectl get pods -n mkc-dev
kubectl logs -n mkc-dev deployment/redis
kubectl logs -n mkc-dev statefulset/mysql
kubectl get pvc -n mkc-dev
kubectl describe pod -n mkc-dev <pod-name>
```

Port checks:

```bash
nc -z localhost 3306
nc -z localhost 6379
nc -z localhost 9000
nc -z localhost 19530
```

## AI Service

Run targeted health and worker checks:

```bash
curl http://localhost:5001/api/v1/health

cd ai-service
source .venv/bin/activate
set -a
source .env
set +a
DEBUG=false celery -A celery_workers.celery_app inspect registered
```

If local shell has `DEBUG=release` or another non-boolean value, run AI commands with `DEBUG=false` or `DEBUG=true` explicitly.

## Gateway

Run:

```bash
cd gateway
go test ./...
go run ./cmd/server
```

If Gateway starts in degraded mode, inspect `/health` for dependency status. MySQL and Redis failures usually mean port forwarding is missing or passwords do not match the values used by `infra/scripts/local-up.sh`.

## Flutter Client

Run:

```bash
cd client
flutter doctor
flutter analyze
flutter test
flutter run -d chrome \
  --dart-define=BASE_URL=http://localhost:8080/api/v1 \
  --dart-define=STORAGE_HOST=localhost
```

For Web uploads, prefer smaller smoke files while debugging. Browser memory, file picker behavior, and object URL handling can differ from desktop targets.

## Error Codes

Standard API and SSE errors include `code`, `message`, `trace_id`, `retryable`, and `details`. See [Error Handling Runbook](runbooks/error_handling.md) for the full table and retry policy.

High-signal codes:

| Code | Meaning |
|---|---|
| `UNAUTHORIZED` | Login state is missing or expired |
| `FILE_TOO_LARGE` | Upload exceeds configured limit |
| `FILE_UNSUPPORTED_TYPE` | File extension or MIME type is not accepted |
| `TASK_NOT_FOUND` | Task does not exist or belongs to another user |
| `RETRIEVAL_TIMEOUT` | Vector retrieval exceeded timeout |
| `LLM_TIMEOUT` | Model response exceeded timeout |
| `DEPENDENCY_UNAVAILABLE` | Redis, MinIO, DB, AI Service, or vector store is unavailable |

## Documentation Checks

```bash
npx --yes markdownlint-cli README.md 'docs/**/*.md'
npx --yes markdown-link-check README.md --config .markdown-link-check.json
find docs -name '*.md' -print0 | xargs -0 -n1 npx --yes markdown-link-check --config .markdown-link-check.json
```

If a link check fails on a local service URL, keep the URL in backticks when it is only an example endpoint.

## Related Runbooks

- [ASR upload pipeline](runbooks/asr-upload-pipeline-debug.md)
- [Monitoring](runbooks/monitoring.md)
- [Error handling](runbooks/error_handling.md)
- [Evaluation dataset](runbooks/evaluation_dataset.md)
- [LLM-as-judge evaluation](runbooks/llm_as_judge_eval_pipeline.md)
