import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from motion_cam.config import DetectionConfig, StorageConfig
from motion_cam.recorder import Recorder


def _make_recorder(tmp_path: Path, max_clip_duration: int = 60) -> Recorder:
    camera = MagicMock()
    storage_config = StorageConfig(data_dir=str(tmp_path))
    detection_config = DetectionConfig(max_clip_duration=max_clip_duration)
    return Recorder(camera, storage_config, detection_config)


class TestStartRecording:
    def test_creates_date_directory_and_snapshot(self, tmp_path):
        """start_recording should create the YYYY-MM-DD directory and capture a snapshot."""
        recorder = _make_recorder(tmp_path)
        recorder.start_recording("20260215_120000")

        assert recorder.is_recording is True
        # Should have created a date-based subdirectory
        date_dir = tmp_path / "2026-02-15"
        assert date_dir.exists()

    def test_captures_snapshot_on_start(self, tmp_path):
        """start_recording should ask the camera to capture a JPEG snapshot."""
        recorder = _make_recorder(tmp_path)
        recorder.start_recording("20260215_120000")

        recorder._camera.capture_snapshot.assert_called_once()
        snap_path = recorder._camera.capture_snapshot.call_args[0][0]
        assert snap_path.endswith("_snap.jpg")


class TestStopRecording:
    def test_converts_h264_to_mp4_via_ffmpeg(self, tmp_path):
        """stop_recording should call ffmpeg to convert the .h264 file to .mp4."""
        recorder = _make_recorder(tmp_path)
        recorder.start_recording("20260215_120000")

        with patch("motion_cam.recorder.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
            recorder.stop_recording()

        assert recorder.is_recording is False
        # Should have called ffmpeg at least once (conversion + thumbnail)
        assert mock_run.call_count >= 1
        # First call should be the H264 → MP4 conversion
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "ffmpeg" in first_call_args
        assert any(arg.endswith(".h264") for arg in first_call_args)
        assert any(arg.endswith(".mp4") for arg in first_call_args)

    def test_generates_thumbnail_from_video(self, tmp_path):
        """stop_recording should extract a thumbnail frame from the video via ffmpeg."""
        recorder = _make_recorder(tmp_path)
        recorder.start_recording("20260215_120000")

        with patch("motion_cam.recorder.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
            recorder.stop_recording()

        # Should have a second ffmpeg call for thumbnail extraction
        thumb_calls = [
            call for call in mock_run.call_args_list
            if any("_thumb.jpg" in str(arg) for arg in call[0][0])
        ]
        assert len(thumb_calls) >= 1


class TestMaxClipDuration:
    def test_auto_stops_when_max_duration_exceeded(self, tmp_path):
        """check_max_duration should stop recording if max_clip_duration is exceeded."""
        recorder = _make_recorder(tmp_path, max_clip_duration=2)
        recorder.start_recording("20260215_120000")

        # Simulate time passing beyond max duration
        with patch("motion_cam.recorder.time.time", return_value=recorder._start_time + 3):
            with patch("motion_cam.recorder.subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
                recorder.check_max_duration()

        assert recorder.is_recording is False
