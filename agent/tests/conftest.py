from collections.abc import Iterator
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from agent import main
from backend.main import app


def connect_to_app(base_url: str) -> TestClient:
    return TestClient(app, base_url=f"http://testserver{urlsplit(base_url).path}")


@pytest.fixture
def backend(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("AEGIS_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("AEGIS_CHECK_DB", str(tmp_path / "checks.db"))
    monkeypatch.setattr(main, "connect", connect_to_app)
    with TestClient(app) as client:
        yield client
