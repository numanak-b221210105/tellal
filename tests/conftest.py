from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tellal.api import create_app
from tellal.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path, mode="demo", llm_enabled=False, public_url="https://tellal.example.com")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c
