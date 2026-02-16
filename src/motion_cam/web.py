from __future__ import annotations

from flask import Flask

from motion_cam.config import StorageConfig, WebConfig
from motion_cam.storage import StorageManager


def create_app(
    storage_manager: StorageManager,
    web_config: WebConfig,
    data_dir: str,
) -> Flask:
    app = Flask(__name__)
    return app
