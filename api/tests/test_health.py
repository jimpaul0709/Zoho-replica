from fastapi.testclient import TestClient

from workhub_api.main import app


def test_health_reaches_real_postgres() -> None:
    # API tests run against real Postgres (NFSD MNT-02): start it with `docker compose up -d db`.
    res = TestClient(app).get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
