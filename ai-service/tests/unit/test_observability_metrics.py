from __future__ import annotations

import json
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.observability.metrics import MetricsRegistry, init_metrics, safe_label


def test_ai_metrics_endpoint_returns_prometheus_text(client: FlaskClient) -> None:
    # MKC-TC-S5-4-002: AI Service /metrics returns Prometheus text.
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    metrics = client.get("/metrics")

    assert metrics.status_code == 200
    body = metrics.data.decode("utf-8")
    assert "mkc_ai_http_requests_total" in body
    assert "mkc_ai_http_request_duration_seconds_bucket" in body
    assert "jwt" not in body.lower()
    assert "authorization" not in body.lower()


def test_metrics_disabled_does_not_register_endpoint() -> None:
    # MKC-TC-S5-4-008: disabled metrics returns 404.
    app = Flask(__name__)
    app.config["METRICS_ENABLED"] = False
    init_metrics(app)

    response = app.test_client().get("/metrics")

    assert response.status_code == 404


def test_duplicate_registry_detected() -> None:
    # MKC-TC-S5-4-009: duplicate metric registration raises.
    registry = MetricsRegistry()

    with pytest.raises(ValueError):
        registry.registry.register(registry.http_requests)


def test_metric_labels_redact_sensitive_values() -> None:
    # MKC-TC-S5-4-006: labels do not keep raw sensitive content.
    assert safe_label("provider") == "provider"
    assert safe_label("Bearer jwt token") == "redacted"
    assert len(safe_label("x" * 200)) == 80


def test_observability_static_assets_are_valid_json() -> None:
    # MKC-TC-S5-4-004, MKC-TC-S5-4-005, MKC-TC-S5-4-011.
    root = Path(__file__).resolve().parents[3]
    overview = root / "infra" / "observability" / "grafana" / "dashboards" / "mkc-overview.json"
    ai = root / "infra" / "observability" / "grafana" / "dashboards" / "mkc-ai-service.json"

    for path in (overview, ai):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["title"]
        panel_titles = {panel["title"] for panel in payload["panels"]}
        assert panel_titles
