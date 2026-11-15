import os
import tempfile

# Must be set before the app is imported.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db")
os.environ["JWT_SECRET"] = "test-secret-not-for-production"
os.environ["OPENAI_API_KEY"] = "sk-test-dummy"
os.environ["REMINDER_THRESHOLD_MINUTES"] = "0"
os.environ["REMINDER_INTERVAL_SECONDS"] = "3600"
os.environ["SEED_DEMO_DATA"] = "true"
os.environ["SEED_DEMO_PASSWORD"] = "Demo@1234"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client, email, password="Demo@1234"):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def customer(client):
    return login(client, "customer@campusbite.dev")


@pytest.fixture(scope="session")
def owner1(client):
    return login(client, "owner1@campusbite.dev")


@pytest.fixture(scope="session")
def owner2(client):
    return login(client, "owner2@campusbite.dev")


@pytest.fixture(scope="session")
def driver1(client):
    return login(client, "driver1@campusbite.dev")


@pytest.fixture(scope="session")
def driver2(client):
    return login(client, "driver2@campusbite.dev")
