from pathlib import Path

from fastapi.testclient import TestClient

from .conftest import HEADERS


def test_list_missions_empty(client: TestClient) -> None:
    resp = client.get("/agent/v1/instances/DCS-test/missions", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_list_missions_with_files(client: TestClient, missions_dir: Path) -> None:
    (missions_dir / "goonfront_v0_3.miz").write_bytes(b"")
    (missions_dir / "red_flag.miz").write_bytes(b"")
    (missions_dir / "readme.txt").write_text("not a mission")

    resp = client.get("/agent/v1/instances/DCS-test/missions", headers=HEADERS)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items == ["goonfront_v0_3.miz", "red_flag.miz"]  # sorted, .miz only


def test_list_missions_requires_auth(client: TestClient) -> None:
    resp = client.get("/agent/v1/instances/DCS-test/missions")
    assert resp.status_code == 403


def test_list_missions_not_found(client: TestClient) -> None:
    resp = client.get("/agent/v1/instances/nonexistent/missions", headers=HEADERS)
    assert resp.status_code == 404
