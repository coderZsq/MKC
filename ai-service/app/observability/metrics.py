from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from flask import Flask, Response, current_app, has_app_context, request
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30)


class MetricsRegistry:
    def __init__(self, namespace: str = "mkc") -> None:
        self.registry = CollectorRegistry()
        self.http_requests = Counter(
            f"{namespace}_ai_http_requests_total",
            "AI Service HTTP requests by method, path, and status.",
            ("method", "path", "status"),
            registry=self.registry,
        )
        self.http_errors = Counter(
            f"{namespace}_ai_http_errors_total",
            "AI Service HTTP errors by method, path, and status.",
            ("method", "path", "status"),
            registry=self.registry,
        )
        self.http_latency = Histogram(
            f"{namespace}_ai_http_request_duration_seconds",
            "AI Service HTTP request latency in seconds.",
            ("method", "path"),
            buckets=LATENCY_BUCKETS,
            registry=self.registry,
        )
        self.retrieval_requests = Counter(
            f"{namespace}_ai_retrieval_requests_total",
            "Retrieval request count by operation and status.",
            ("operation", "status"),
            registry=self.registry,
        )
        self.embedding_requests = Counter(
            f"{namespace}_ai_embedding_requests_total",
            "Embedding request count by provider, model, and status.",
            ("provider", "model", "status"),
            registry=self.registry,
        )
        self.llm_requests = Counter(
            f"{namespace}_ai_llm_requests_total",
            "LLM request count by provider, model, and status.",
            ("provider", "model", "status"),
            registry=self.registry,
        )
        self.llm_tokens = Counter(
            f"{namespace}_ai_llm_tokens_total",
            "LLM token count by provider, model, and type.",
            ("provider", "model", "token_type"),
            registry=self.registry,
        )
        self.task_duration = Histogram(
            f"{namespace}_ai_task_duration_seconds",
            "AI task duration by task type and status.",
            ("task_type", "status"),
            buckets=LATENCY_BUCKETS,
            registry=self.registry,
        )

    def record_http(self, method: str, path: str, status: int, duration: float) -> None:
        path_label = safe_path(path)
        status_label = str(status)
        self.http_requests.labels(method=method, path=path_label, status=status_label).inc()
        self.http_latency.labels(method=method, path=path_label).observe(duration)
        if status >= 500:
            self.http_errors.labels(method=method, path=path_label, status=status_label).inc()

    def record_retrieval(self, operation: str, status: str) -> None:
        self.retrieval_requests.labels(
            operation=safe_label(operation),
            status=safe_label(status),
        ).inc()

    def record_llm(self, provider: str, model: str, status: str) -> None:
        self.llm_requests.labels(
            provider=safe_label(provider),
            model=safe_label(model),
            status=safe_label(status),
        ).inc()


def init_metrics(app: Flask) -> None:
    app.config.setdefault("METRICS_ENABLED", True)
    app.config.setdefault("METRICS_PATH", "/metrics")
    app.config.setdefault("METRICS_NAMESPACE", "mkc")
    if not app.config["METRICS_ENABLED"]:
        return

    registry = MetricsRegistry(namespace=app.config["METRICS_NAMESPACE"])
    app.extensions["metrics"] = registry

    @app.before_request
    def start_metrics_timer() -> None:
        request.environ["mkc.metrics.start"] = time.monotonic()

    @app.after_request
    def record_metrics(response: Response) -> Response:
        if request.path != app.config["METRICS_PATH"]:
            started_at = request.environ.get("mkc.metrics.start", time.monotonic())
            path = request.url_rule.rule if request.url_rule is not None else request.path
            registry.record_http(
                request.method,
                path,
                response.status_code,
                time.monotonic() - float(started_at),
            )
        return response

    app.add_url_rule(app.config["METRICS_PATH"], "metrics", metrics_handler(registry))


def metrics_handler(registry: MetricsRegistry) -> Callable[[], Response]:
    def _handler() -> Response:
        return Response(generate_latest(registry.registry), mimetype=CONTENT_TYPE_LATEST)

    return _handler


def get_metrics() -> MetricsRegistry | None:
    if not has_app_context():
        return None
    return current_app.extensions.get("metrics")


def safe_label(value: Any) -> str:
    text = str(value or "unknown")
    lowered = text.lower()
    if any(marker in lowered for marker in ("token", "secret", "jwt", "password", "question")):
        return "redacted"
    return text[:80]


def safe_path(path: str) -> str:
    return path or "unknown"
