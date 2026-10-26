from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend import config
from backend.main import app

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'DB_PATH',tmp_path/'test.sqlite3')
    with TestClient(app) as client: yield client

@pytest.fixture
def admin_client(client):
    response=client.post('/api/auth/login',json={'username':config.ADMIN_ID,'password':config.ADMIN_PASSWORD})
    assert response.status_code==200
    return client

@pytest.fixture(autouse=True)
def isolate_live_polling(monkeypatch):
    # Unit/API tests use controlled provider fixtures, never external feeds.
    import asyncio
    async def idle(): await asyncio.Event().wait()
    monkeypatch.setattr("backend.services.live_service.poll",idle)
