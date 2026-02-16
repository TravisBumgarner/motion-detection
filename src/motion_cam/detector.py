from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from motion_cam.config import DetectionConfig


@dataclass
class MotionEvent:
    detected: bool = False
    contour_count: int = 0
    largest_area: int = 0


class MotionDetector:
    def __init__(self, config: DetectionConfig) -> None:
        self._config = config

    def process_frame(self, frame: np.ndarray) -> MotionEvent:
        return MotionEvent()
