from __future__ import annotations

from dataclasses import dataclass

import cv2
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
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def process_frame(self, frame: np.ndarray) -> MotionEvent:
        k = self._config.blur_kernel_size
        blurred = cv2.GaussianBlur(frame, (k, k), 0)

        lr = self._config.learning_rate
        fg_mask = self._bg_subtractor.apply(blurred, learningRate=lr if lr >= 0 else -1)

        # Remove shadows: MOG2 marks shadows as 127, foreground as 255
        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)

        # Morphological cleanup: erode to remove noise, dilate to fill gaps
        fg_mask = cv2.erode(fg_mask, self._kernel, iterations=1)
        fg_mask = cv2.dilate(fg_mask, self._kernel, iterations=2)

        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        qualifying = [c for c in contours if cv2.contourArea(c) >= self._config.min_contour_area]

        if not qualifying:
            return MotionEvent(detected=False, contour_count=0, largest_area=0)

        largest = max(cv2.contourArea(c) for c in qualifying)
        return MotionEvent(
            detected=True,
            contour_count=len(qualifying),
            largest_area=int(largest),
        )
