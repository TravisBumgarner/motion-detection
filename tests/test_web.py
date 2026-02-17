from pathlib import Path

import pytest

from motion_cam.config import StorageConfig, WebConfig
from motion_cam.storage import StorageManager
from motion_cam.web import create_app


def _create_clip(data_dir: Path, timestamp: str, mp4_size: int = 1024) -> None:
    """Create a fake clip with mp4, snapshot, and thumbnail files."""
    date_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
    date_dir = data_dir / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    (date_dir / f"{timestamp}.mp4").write_bytes(b"\x00" * mp4_size)
    (date_dir / f"{timestamp}_snap.jpg").write_bytes(b"\xff" * 512)
    (date_dir / f"{timestamp}_thumb.jpg").write_bytes(b"\xff" * 256)


@pytest.fixture
def app_with_clips(tmp_path):
    """Create a Flask test app with some fixture clips."""
    _create_clip(tmp_path, "20260210_100000")
    _create_clip(tmp_path, "20260212_120000")
    _create_clip(tmp_path, "20260215_140000")

    storage_config = StorageConfig(data_dir=str(tmp_path))
    manager = StorageManager(storage_config)
    web_config = WebConfig()
    app = create_app(manager, web_config, data_dir=str(tmp_path))
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app_with_clips):
    return app_with_clips.test_client()


class TestApiClips:
    def test_returns_json_list_of_clips(self, client):
        """GET /api/clips should return a JSON array of clip metadata."""
        resp = client.get("/api/clips")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 3
        # Newest first
        assert data[0]["timestamp"] == "20260215_140000"

    def test_pagination_limits_results(self, client, tmp_path):
        """GET /api/clips?page=1 should respect pagination."""
        resp = client.get("/api/clips?page=1")
        assert resp.status_code == 200
        data = resp.get_json()
        # With only 3 clips and 20 per page, page 1 has all 3
        assert len(data) <= 20


class TestApiDeleteAllClips:
    def test_deletes_all_clips(self, client):
        """DELETE /api/clips should remove all clips and return count."""
        resp = client.delete("/api/clips")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "deleted"
        assert data["count"] == 3

    def test_returns_zero_when_no_clips(self, tmp_path):
        """DELETE /api/clips should return count 0 when no clips exist."""
        storage_config = StorageConfig(data_dir=str(tmp_path))
        manager = StorageManager(storage_config)
        web_config = WebConfig()
        app = create_app(manager, web_config, data_dir=str(tmp_path))
        app.config["TESTING"] = True
        resp = app.test_client().delete("/api/clips")
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 0


class TestApiDeleteClip:
    def test_deletes_existing_clip(self, client, tmp_path):
        """DELETE /api/clips/<timestamp> should remove the clip and return 200."""
        resp = client.delete("/api/clips/20260215_140000")
        assert resp.status_code == 200

        # Verify it's gone
        resp2 = client.get("/api/clips")
        timestamps = [c["timestamp"] for c in resp2.get_json()]
        assert "20260215_140000" not in timestamps

    def test_returns_404_for_missing_clip(self, client):
        """DELETE /api/clips/<timestamp> should return 404 for nonexistent clip."""
        resp = client.delete("/api/clips/99990101_000000")
        assert resp.status_code == 404


class TestApiStatus:
    def test_returns_status_json(self, client):
        """GET /api/status should return disk usage and clip count."""
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "disk_usage" in data
        assert "clip_count" in data
        assert data["clip_count"] == 3


class TestGalleryPage:
    def test_gallery_returns_html(self, client):
        """GET / should return an HTML page."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"<html" in resp.data.lower() or b"<!doctype" in resp.data.lower()


class TestClipDetailPage:
    def test_detail_page_for_existing_clip(self, client):
        """GET /clip/<timestamp> should return 200 for an existing clip."""
        resp = client.get("/clip/20260215_140000")
        assert resp.status_code == 200

    def test_detail_page_returns_404_for_missing(self, client):
        """GET /clip/<timestamp> should return 404 for nonexistent clip."""
        resp = client.get("/clip/99990101_000000")
        assert resp.status_code == 404


class TestMediaServing:
    def test_serves_mp4_from_data_directory(self, client):
        """The app should serve MP4 files from the data directory."""
        resp = client.get("/media/2026-02-15/20260215_140000.mp4")
        assert resp.status_code == 200


class TestTunerPage:
    def test_tuner_returns_html(self, client):
        """GET /tuner should return an HTML page even without a camera."""
        resp = client.get("/tuner")
        assert resp.status_code == 200
        assert b"Camera Tuner" in resp.data

    def test_tuner_stream_returns_503_without_camera(self, client):
        """GET /tuner/stream should return 503 when no camera is available."""
        resp = client.get("/tuner/stream")
        assert resp.status_code == 503

    def test_tuner_control_returns_503_without_camera(self, client):
        """POST /api/tuner/control should return 503 when no camera."""
        resp = client.post(
            "/api/tuner/control",
            json={"brightness": 0.5},
        )
        assert resp.status_code == 503

    def test_tuner_af_mode_returns_503_without_camera(self, client):
        """POST /api/tuner/af_mode should return 503 when no camera."""
        resp = client.post(
            "/api/tuner/af_mode",
            json={"af_mode": "continuous"},
        )
        assert resp.status_code == 503

    def test_tuner_trigger_af_returns_503_without_camera(self, client):
        """POST /api/tuner/trigger_af should return 503 when no camera."""
        resp = client.post("/api/tuner/trigger_af")
        assert resp.status_code == 503
