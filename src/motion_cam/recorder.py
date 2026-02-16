from __future__ import annotations

from motion_cam.camera import CameraProtocol
from motion_cam.config import StorageConfig, DetectionConfig


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

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self, timestamp: str) -> None:
        pass

    def stop_recording(self) -> None:
        pass

    def check_max_duration(self) -> None:
        pass
