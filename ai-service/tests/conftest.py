import os

os.environ["INTERNAL_API_KEY"] = "test-internal-key"
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")
os.environ.setdefault("VECTOR_STORE_PROVIDER", "chroma")
os.environ.setdefault("LLM_PROVIDER", "mock")

import chromadb
import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.services.memory import MemoryConfig, build_memory_service
from app.vector_store import ChromaStore
from app.vector_store.config import build_vector_store_config


@pytest.fixture
def vector_store() -> ChromaStore:
    """Return an ephemeral in-memory Chroma vector store."""
    config = build_vector_store_config()
    return ChromaStore(config, client=chromadb.Client())


@pytest.fixture
def app(vector_store: ChromaStore) -> Flask:
    flask_app = create_app(vector_store=vector_store)
    flask_app.config.update({"TESTING": True})
    # Disable long-term memory by default so integration tests do not pollute the
    # shared vector store collection with memory vectors.
    flask_app.extensions["memory_service"] = build_memory_service(
        flask_app.extensions["embedding"],
        vector_store,
        config=MemoryConfig(enabled=False),
    )
    return flask_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()
