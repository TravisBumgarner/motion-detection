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
        self._picam2 = None

    def start(self) -> None:
        from picamera2 import Picamera2

        self._picam2 = Picamera2()
        main = {"size": self._config.main_resolution, "format": "RGB888"}
        lores = {"size": self._config.lores_resolution, "format": "YUV420"}
        video_config = self._picam2.create_video_configuration(main, lores=lores)
        self._picam2.configure(video_config)
        self._picam2.set_controls({"FrameRate": self._config.framerate})
        self._picam2.start()

    def stop(self) -> None:
        if self._picam2 is not None:
            self._picam2.stop()
            self._picam2.close()
            self._picam2 = None

    def capture_lores_frame(self) -> np.ndarray:
        w, h = self._config.lores_resolution
        buf = self._picam2.capture_array("lores")
        return buf[:h, :w]

    def capture_snapshot(self, path: str) -> None:
        self._picam2.capture_file(path)
