from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setenv("AEGIS_DB", str(tmp_path / "test.db"))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client
