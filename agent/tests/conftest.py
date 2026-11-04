from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from agent import main
from backend.main import app


@pytest.fixture
def backend(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("AEGIS_DB", str(tmp_path / "test.db"))
    with TestClient(app) as client:
        monkeypatch.setattr(main, "client", client)
        yield client
