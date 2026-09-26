import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import serve_frontend


@pytest.fixture
def frontend_client(tmp_path) -> TestClient:
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('hi')")
    (tmp_path.parent / "secret.txt").write_text("secret")
    app = FastAPI()
    serve_frontend(app, tmp_path)
    return TestClient(app)


def test_spa_route_returns_index(frontend_client):
    response = frontend_client.get("/transactions")

    assert response.status_code == 200
    assert "root" in response.text


def test_serves_built_assets(frontend_client):
    assert frontend_client.get("/assets/app.js").text == "console.log('hi')"


@pytest.mark.parametrize("path", ["/api", "/api/unknown"])
def test_unknown_api_path_is_404(frontend_client, path):
    assert frontend_client.get(path).status_code == 404


def test_cannot_read_files_outside_dist(frontend_client):
    response = frontend_client.get("/..%2Fsecret.txt")

    assert "secret" not in response.text
