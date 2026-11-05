from collections.abc import Iterator
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from agent import main as agent
from backend.main import app


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setenv("AEGIS_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("AEGIS_CHECK_DB", str(tmp_path / "checks.db"))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def agent_backend(monkeypatch):
    def connect(base_url: str) -> TestClient:
        return TestClient(app, base_url=f"http://testserver{urlsplit(base_url).path}")

    monkeypatch.setattr(agent, "connect", connect)
    monkeypatch.setenv("MODEL_NAME", "stub")
