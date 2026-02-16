from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from motion_cam.config import StorageConfig


@dataclass
class ClipMetadata:
    timestamp: str
    path: str
    snapshot_path: str
    thumbnail_path: str
    file_size: int


class StorageManager:
    def __init__(self, config: StorageConfig) -> None:
        self._config = config

    def get_clips(self) -> list[ClipMetadata]:
        return []

    def get_clip(self, timestamp: str) -> ClipMetadata | None:
        return None

    def delete_clip(self, timestamp: str) -> bool:
        return False

    def enforce_retention(self) -> None:
        pass

    def get_disk_usage(self) -> int:
        return 0
