import os
from unittest.mock import patch

from motion_cam.config import Config, load_config


class TestLoadConfigDefaults:
    def test_returns_config_object(self):
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
        assert isinstance(config, Config)

    def test_camera_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
        assert config.camera.main_resolution == (1280, 720)
        assert config.camera.lores_resolution == (320, 240)
        assert config.camera.framerate == 15

    def test_detection_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
        assert config.detection.min_contour_area == 500
        assert config.detection.blur_kernel_size == 21
        assert config.detection.cooldown == 5
        assert config.detection.max_clip_duration == 60

    def test_storage_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
        assert config.storage.max_age_days == 7
        assert config.storage.max_disk_usage_mb == 4096
        assert config.storage.data_dir != ""  # should have a real default path

    def test_web_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
        assert config.web.port == 8080
        assert config.web.host == "0.0.0.0"


class TestLoadConfigEnvOverrides:
    def test_camera_resolution_override(self):
        env = {"CAMERA_MAIN_RESOLUTION": "1920x1080", "CAMERA_LORES_RESOLUTION": "640x480"}
        with patch.dict(os.environ, env, clear=True):
            config = load_config()
        assert config.camera.main_resolution == (1920, 1080)
        assert config.camera.lores_resolution == (640, 480)

    def test_camera_framerate_override(self):
        with patch.dict(os.environ, {"CAMERA_FRAMERATE": "30"}, clear=True):
            config = load_config()
        assert config.camera.framerate == 30

    def test_detection_overrides(self):
        env = {
            "DETECTION_MIN_CONTOUR_AREA": "1000",
            "DETECTION_BLUR_KERNEL_SIZE": "15",
            "DETECTION_COOLDOWN": "10",
            "DETECTION_MAX_CLIP_DURATION": "120",
            "DETECTION_LEARNING_RATE": "0.5",
        }
        with patch.dict(os.environ, env, clear=True):
            config = load_config()
        assert config.detection.min_contour_area == 1000
        assert config.detection.blur_kernel_size == 15
        assert config.detection.cooldown == 10
        assert config.detection.max_clip_duration == 120
        assert config.detection.learning_rate == 0.5

    def test_storage_overrides(self):
        env = {
            "STORAGE_DATA_DIR": "/tmp/test-data",
            "STORAGE_MAX_AGE_DAYS": "14",
            "STORAGE_MAX_DISK_USAGE_MB": "8192",
        }
        with patch.dict(os.environ, env, clear=True):
            config = load_config()
        assert config.storage.data_dir == "/tmp/test-data"
        assert config.storage.max_age_days == 14
        assert config.storage.max_disk_usage_mb == 8192

    def test_web_overrides(self):
        env = {"WEB_PORT": "9090", "WEB_HOST": "127.0.0.1"}
        with patch.dict(os.environ, env, clear=True):
            config = load_config()
        assert config.web.port == 9090
        assert config.web.host == "127.0.0.1"

    def test_partial_override_keeps_other_defaults(self):
        with patch.dict(os.environ, {"WEB_PORT": "3000"}, clear=True):
            config = load_config()
        assert config.web.port == 3000
        assert config.web.host == "0.0.0.0"
        assert config.camera.framerate == 15
