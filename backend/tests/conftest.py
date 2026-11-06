from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", backup_dir=tmp_path / "backups",
                    frontend_dir=tmp_path / "no-frontend", backup_retention=5,
                    backup_interval_minutes=0)


@pytest.fixture
def make_client(settings):
    """Start a fresh app instance (= a server process) against the same data dir."""
    clients = []

    def _make() -> TestClient:
        c = TestClient(create_app(settings))
        c.__enter__()  # runs lifespan startup (migrations, startup backup)
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


class Player:
    """One human with their own account/session, as a browser would be."""

    def __init__(self, client: TestClient, username: str):
        self.client = client
        r = client.post("/api/accounts", json={"username": username, "passphrase": "secret-pass"})
        assert r.status_code == 201, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['token']}"}

    def get(self, url, **kw):
        return self.client.get(url, headers=self.headers, **kw)

    def post(self, url, **kw):
        return self.client.post(url, headers=self.headers, **kw)

    def create_character(self, name: str, class_id: str) -> dict:
        r = self.post("/api/characters", json={"name": name, "class_id": class_id})
        assert r.status_code == 201, r.text
        return r.json()


@pytest.fixture
def two_players(client):
    a, b = Player(client, "alice"), Player(client, "bram")
    ca = a.create_character("Aldric", "sentinel")
    cb = b.create_character("Brisa", "arcanist")
    return a, ca, b, cb
