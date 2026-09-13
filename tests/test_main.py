from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    """Test that the accounts endpoint returns a 200 status code."""
    response = client.get("/accounts/")
    assert response.status_code == 200
    # Response may contain accounts if setup is complete, or empty list if not
    assert isinstance(response.json(), list)
