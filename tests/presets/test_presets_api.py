from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_create_and_get_preset(tmp_path, monkeypatch):
    # Point service storage to temp path for isolation
    monkeypatch.setenv("ALPHAFORGE_PRESET_PATH", str(tmp_path / "presets.json"))
    payload = {"name": "mean_rev_fast", "config": {"lookback": 20, "threshold": 1.5}}
    r = client.post("/presets", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == payload["name"]
    assert data["config"] == payload["config"]
    preset_id = data["preset_id"]

    # Retrieve
    r2 = client.get(f"/presets/{preset_id}")
    assert r2.status_code == 200
    assert r2.json()["preset_id"] == preset_id


def test_list_and_conflict_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHAFORGE_PRESET_PATH", str(tmp_path / "presets.json"))
    p = {"name": "trend_follow", "config": {"ma": 50}}
    r1 = client.post("/presets", json=p)
    assert r1.status_code == 200
    preset_id = r1.json()["preset_id"]

    # duplicate create (idempotent) should yield same id
    r2 = client.post("/presets", json=p)
    assert r2.status_code == 200
    assert r2.json()["preset_id"] == preset_id

    # list
    rlist = client.get("/presets")
    assert rlist.status_code == 200
    items = rlist.json()["items"]
    # Filter for our name to avoid interference if global defaults pre-populate
    ours = [it for it in items if it["preset_id"] == preset_id]
    assert len(ours) == 1


def test_delete_and_404(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHAFORGE_PRESET_PATH", str(tmp_path / "presets.json"))
    p = {"name": "scalp", "config": {"tick": 5}}
    r1 = client.post("/presets", json=p)
    preset_id = r1.json()["preset_id"]
    # delete
    rd = client.delete(f"/presets/{preset_id}")
    assert rd.status_code == 200
    # subsequent get 404
    r404 = client.get(f"/presets/{preset_id}")
    assert r404.status_code == 404
    body = r404.json()
    assert body["detail"] == "preset not found"
