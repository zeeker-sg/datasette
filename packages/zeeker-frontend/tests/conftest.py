"""Shared fixtures for zeeker-frontend tests."""
import pytest
from fastapi.testclient import TestClient

from zeeker_frontend.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient bound to the placeholder app."""
    return TestClient(app)
