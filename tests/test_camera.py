from unittest.mock import MagicMock, patch

import numpy as np

from motion_cam.camera import CameraProtocol, CameraService
from motion_cam.config import CameraConfig


class TestCameraServiceProtocol:
    def test_implements_camera_protocol(self):
        """CameraService must satisfy CameraProtocol so downstream modules can depend on the interface."""
        config = CameraConfig()
        service = CameraService(config)
        # If CameraService doesn't have the right methods, this will fail at runtime
        proto_ref: CameraProtocol = service
        assert hasattr(proto_ref, "start")
        assert hasattr(proto_ref, "stop")
        assert hasattr(proto_ref, "capture_lores_frame")
        assert hasattr(proto_ref, "capture_snapshot")


class TestCaptureLoresFrame:
    def test_returns_y_channel_from_yuv420(self):
        """capture_lores_frame should extract just the Y (luminance) channel
        from the full YUV420 buffer. YUV420 has height*1.5 rows; Y is the
        first height rows."""
        config = CameraConfig(lores_resolution=(4, 4))
        service = CameraService(config)

        # YUV420 buffer: 4x4 Y plane + 2x2 U + 2x2 V = 6 rows x 4 cols
        y_plane = np.full((4, 4), 128, dtype=np.uint8)
        uv_plane = np.full((2, 4), 64, dtype=np.uint8)
        yuv420_buffer = np.vstack([y_plane, uv_plane])

        with patch.object(service, "_picam2") as mock_cam:
            mock_cam.capture_array.return_value = yuv420_buffer
            frame = service.capture_lores_frame()

        assert frame.shape == (4, 4)
        assert np.all(frame == 128)  # Only Y plane, not UV


class TestCaptureSnapshot:
    def test_saves_jpeg_to_given_path(self):
        """capture_snapshot must request a JPEG capture to the specified path."""
        config = CameraConfig()
        service = CameraService(config)

        with patch.object(service, "_picam2") as mock_cam:
            service.capture_snapshot("/tmp/test_snap.jpg")
            mock_cam.capture_file.assert_called_once_with("/tmp/test_snap.jpg")
