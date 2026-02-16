import numpy as np

from motion_cam.config import DetectionConfig
from motion_cam.detector import MotionDetector, MotionEvent


def _make_detector(min_contour_area=500, blur_kernel_size=21) -> MotionDetector:
    config = DetectionConfig(
        min_contour_area=min_contour_area,
        blur_kernel_size=blur_kernel_size,
    )
    return MotionDetector(config)


def _static_frame(value: int = 128, size: tuple[int, int] = (240, 320)) -> np.ndarray:
    """Create a uniform grayscale frame."""
    return np.full(size, value, dtype=np.uint8)


def _frame_with_object(
    bg_value: int = 128,
    obj_value: int = 255,
    obj_rect: tuple[int, int, int, int] = (50, 50, 80, 80),
    size: tuple[int, int] = (240, 320),
) -> np.ndarray:
    """Create a frame with a bright rectangular object on a uniform background."""
    frame = np.full(size, bg_value, dtype=np.uint8)
    y, x, h, w = obj_rect
    frame[y : y + h, x : x + w] = obj_value
    return frame


class TestMotionDetection:
    def test_no_motion_on_static_scene(self):
        """Identical frames should not trigger motion."""
        detector = _make_detector()
        frame = _static_frame()

        # Feed several identical frames to let background model learn
        for _ in range(30):
            event = detector.process_frame(frame)

        # After stabilization, static scene should not detect motion
        event = detector.process_frame(frame)
        assert event.detected is False

    def test_detects_new_object_appearing(self):
        """A large bright object appearing on a learned background should trigger detection."""
        detector = _make_detector(min_contour_area=100)
        bg = _static_frame(value=50)

        # Train background model
        for _ in range(50):
            detector.process_frame(bg)

        # Introduce a large object
        with_object = _frame_with_object(bg_value=50, obj_value=200, obj_rect=(50, 50, 60, 60))
        event = detector.process_frame(with_object)

        assert event.detected is True
        assert event.contour_count >= 1
        assert event.largest_area > 0

    def test_ignores_small_noise_below_min_contour_area(self):
        """Tiny specks smaller than min_contour_area should not trigger detection."""
        detector = _make_detector(min_contour_area=500)
        bg = _static_frame(value=50)

        for _ in range(50):
            detector.process_frame(bg)

        # Add a tiny 5x5 speck (area=25, well below 500)
        noisy = _frame_with_object(bg_value=50, obj_value=200, obj_rect=(100, 100, 5, 5))
        event = detector.process_frame(noisy)

        assert event.detected is False

    def test_returns_diagnostics(self):
        """MotionEvent should include contour_count and largest_area for tuning."""
        detector = _make_detector(min_contour_area=100)
        bg = _static_frame(value=50)

        for _ in range(50):
            detector.process_frame(bg)

        with_object = _frame_with_object(bg_value=50, obj_value=200, obj_rect=(50, 50, 40, 40))
        event = detector.process_frame(with_object)

        assert isinstance(event, MotionEvent)
        assert isinstance(event.contour_count, int)
        assert isinstance(event.largest_area, int)
        if event.detected:
            assert event.largest_area >= 100
