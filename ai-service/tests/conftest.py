import os

os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app


@pytest.fixture
def app() -> Flask:
    flask_app = create_app()
    flask_app.config.update({"TESTING": True})
    return flask_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()
