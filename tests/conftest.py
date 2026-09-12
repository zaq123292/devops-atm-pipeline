import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from app import create_app
from config import TestConfig

@pytest.fixture
def app(tmp_path):
    class IsolatedTestConfig(TestConfig):
        DATABASE = str(tmp_path / "atm-test.db")
    return create_app(IsolatedTestConfig)
@pytest.fixture
def client(app):
    return app.test_client()
def login(client):
    return client.post('/login', data={'card':'10000001','pin':'1234'})
