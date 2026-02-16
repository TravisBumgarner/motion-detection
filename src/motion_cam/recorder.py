from __future__ import annotations

import subprocess
import time
from pathlib import Path

from motion_cam.camera import CameraProtocol
from motion_cam.config import DetectionConfig, StorageConfig


class Recorder:
    def __init__(
        self,
        camera: CameraProtocol,
        storage_config: StorageConfig,
        detection_config: DetectionConfig,
    ) -> None:
        self._camera = camera
        self._storage_config = storage_config
        self._detection_config = detection_config
        self._recording = False
        self._start_time: float = 0.0
        self._mp4_path: str = ""
        self._thumb_path: str = ""

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self, timestamp: str) -> None:
        # Parse timestamp "YYYYMMDD_HHMMSS" into date directory "YYYY-MM-DD"
        date_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
        date_dir = Path(self._storage_config.data_dir) / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        self._mp4_path = str(date_dir / f"{timestamp}.mp4")
        self._thumb_path = str(date_dir / f"{timestamp}_thumb.jpg")
        snap_path = str(date_dir / f"{timestamp}_snap.jpg")

        self._camera.capture_snapshot(snap_path)
        self._camera.start_recording(self._mp4_path)
        self._start_time = time.time()
        self._recording = True

    def stop_recording(self) -> None:
        if not self._recording:
            return

        self._recording = False
        self._camera.stop_recording()

        # Generate thumbnail from video (frame at 0.5s)
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", self._mp4_path,
                "-ss", "0.5", "-frames:v", "1",
                self._thumb_path,
            ],
            capture_output=True,
        )

    def check_max_duration(self) -> None:
        if not self._recording:
            return
        elapsed = time.time() - self._start_time
        if elapsed >= self._detection_config.max_clip_duration:
            self.stop_recording()
