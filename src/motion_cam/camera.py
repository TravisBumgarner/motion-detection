from __future__ import annotations

from typing import Protocol

import numpy as np

from motion_cam.config import CameraConfig


class CameraProtocol(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def capture_lores_frame(self) -> np.ndarray: ...
    def capture_snapshot(self, path: str) -> None: ...


class CameraService:
    def __init__(self, config: CameraConfig) -> None:
        self._config = config

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def capture_lores_frame(self) -> np.ndarray:
        return np.array([])

    def capture_snapshot(self, path: str) -> None:
        pass
