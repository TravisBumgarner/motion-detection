from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
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

    def _data_dir(self) -> Path:
        return Path(self._config.data_dir)

    def _find_mp4_files(self) -> list[Path]:
        data_dir = self._data_dir()
        if not data_dir.exists():
            return []
        return sorted(data_dir.rglob("*.mp4"), reverse=True)

    def _metadata_from_mp4(self, mp4: Path) -> ClipMetadata:
        timestamp = mp4.stem
        parent = mp4.parent
        return ClipMetadata(
            timestamp=timestamp,
            path=str(mp4),
            snapshot_path=str(parent / f"{timestamp}_snap.jpg"),
            thumbnail_path=str(parent / f"{timestamp}_thumb.jpg"),
            file_size=mp4.stat().st_size,
        )

    def get_clips(self) -> list[ClipMetadata]:
        mp4s = self._find_mp4_files()
        return [self._metadata_from_mp4(mp4) for mp4 in mp4s]

    def get_clip(self, timestamp: str) -> ClipMetadata | None:
        date_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
        mp4 = self._data_dir() / date_str / f"{timestamp}.mp4"
        if not mp4.exists():
            return None
        return self._metadata_from_mp4(mp4)

    def delete_clip(self, timestamp: str) -> bool:
        clip = self.get_clip(timestamp)
        if clip is None:
            return False

        for path_str in (clip.path, clip.snapshot_path, clip.thumbnail_path):
            p = Path(path_str)
            if p.exists():
                p.unlink()

        return True

    def enforce_retention(self) -> None:
        self._enforce_age_retention()
        self._enforce_size_retention()

    def _enforce_age_retention(self) -> None:
        cutoff = datetime.now() - timedelta(days=self._config.max_age_days)
        for clip in self.get_clips():
            clip_dt = datetime.strptime(clip.timestamp, "%Y%m%d_%H%M%S")
            if clip_dt < cutoff:
                self.delete_clip(clip.timestamp)

    def _enforce_size_retention(self) -> None:
        max_bytes = self._config.max_disk_usage_mb * 1024 * 1024
        while self.get_disk_usage() > max_bytes:
            clips = self.get_clips()
            if not clips:
                break
            # Delete the oldest clip (last in the newest-first list)
            self.delete_clip(clips[-1].timestamp)

    def get_disk_usage(self) -> int:
        data_dir = self._data_dir()
        if not data_dir.exists():
            return 0
        return sum(f.stat().st_size for f in data_dir.rglob("*") if f.is_file())
