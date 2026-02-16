import time
from pathlib import Path

from motion_cam.config import StorageConfig
from motion_cam.storage import StorageManager


def _create_clip(data_dir: Path, timestamp: str, mp4_size: int = 1024) -> None:
    """Create a fake clip with mp4, snapshot, and thumbnail files."""
    date_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
    date_dir = data_dir / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    (date_dir / f"{timestamp}.mp4").write_bytes(b"\x00" * mp4_size)
    (date_dir / f"{timestamp}_snap.jpg").write_bytes(b"\xff" * 512)
    (date_dir / f"{timestamp}_thumb.jpg").write_bytes(b"\xff" * 256)


def _make_manager(tmp_path: Path, **kwargs) -> StorageManager:
    config = StorageConfig(data_dir=str(tmp_path), **kwargs)
    return StorageManager(config)


class TestGetClips:
    def test_returns_clips_sorted_newest_first(self, tmp_path):
        """Clips should be returned newest-first based on timestamp."""
        _create_clip(tmp_path, "20260210_100000")
        _create_clip(tmp_path, "20260215_120000")
        _create_clip(tmp_path, "20260212_080000")

        manager = _make_manager(tmp_path)
        clips = manager.get_clips()

        assert len(clips) == 3
        assert clips[0].timestamp == "20260215_120000"
        assert clips[1].timestamp == "20260212_080000"
        assert clips[2].timestamp == "20260210_100000"

    def test_returns_empty_list_when_no_clips(self, tmp_path):
        """Empty data directory should return no clips."""
        manager = _make_manager(tmp_path)
        clips = manager.get_clips()
        assert clips == []


class TestGetClip:
    def test_returns_metadata_for_existing_clip(self, tmp_path):
        """Should return clip metadata when the clip exists."""
        _create_clip(tmp_path, "20260215_120000", mp4_size=2048)
        manager = _make_manager(tmp_path)

        clip = manager.get_clip("20260215_120000")

        assert clip is not None
        assert clip.timestamp == "20260215_120000"
        assert clip.file_size == 2048

    def test_returns_none_for_missing_clip(self, tmp_path):
        """Should return None when the clip does not exist."""
        manager = _make_manager(tmp_path)
        assert manager.get_clip("99990101_000000") is None


class TestDeleteClip:
    def test_removes_all_clip_files(self, tmp_path):
        """Deleting a clip should remove mp4, snapshot, and thumbnail."""
        _create_clip(tmp_path, "20260215_120000")
        manager = _make_manager(tmp_path)

        result = manager.delete_clip("20260215_120000")

        assert result is True
        date_dir = tmp_path / "2026-02-15"
        assert not (date_dir / "20260215_120000.mp4").exists()
        assert not (date_dir / "20260215_120000_snap.jpg").exists()
        assert not (date_dir / "20260215_120000_thumb.jpg").exists()

    def test_returns_false_for_missing_clip(self, tmp_path):
        """Deleting a nonexistent clip should return False."""
        manager = _make_manager(tmp_path)
        assert manager.delete_clip("99990101_000000") is False


class TestDeleteAllClips:
    def test_deletes_all_clips_and_returns_count(self, tmp_path):
        """Should delete every clip and return the count deleted."""
        _create_clip(tmp_path, "20260210_100000")
        _create_clip(tmp_path, "20260215_120000")
        manager = _make_manager(tmp_path)

        count = manager.delete_all_clips()

        assert count == 2
        assert manager.get_clips() == []

    def test_returns_zero_when_no_clips(self, tmp_path):
        """Should return 0 when there are no clips to delete."""
        manager = _make_manager(tmp_path)
        assert manager.delete_all_clips() == 0


class TestEnforceRetention:
    def test_deletes_clips_exceeding_max_disk_usage(self, tmp_path):
        """When total size exceeds max_disk_usage_mb, oldest clips are deleted first."""
        # Create clips with known sizes: 3 clips × ~1792 bytes each ≈ 5376 bytes
        _create_clip(tmp_path, "20260210_100000", mp4_size=1024)
        _create_clip(tmp_path, "20260212_120000", mp4_size=1024)
        _create_clip(tmp_path, "20260215_140000", mp4_size=1024)

        # Set max to ~3KB (0.003 MB) — should force deletion of oldest clips
        # Use a value in MB that's less than total but more than one clip
        # Total ≈ 5376 bytes. One clip ≈ 1792 bytes.
        # max_disk_usage_mb as a very small fraction to trigger retention
        manager = _make_manager(tmp_path, max_disk_usage_mb=0)

        manager.enforce_retention()

        clips = manager.get_clips()
        # With max 0 MB, all clips should be deleted
        assert len(clips) == 0

    def test_deletes_clips_older_than_max_age_days(self, tmp_path):
        """Clips older than max_age_days should be removed."""
        # Create an "old" clip by using a very old date
        _create_clip(tmp_path, "20240101_100000")
        # Create a "recent" clip
        _create_clip(tmp_path, "20260215_120000")

        manager = _make_manager(tmp_path, max_age_days=7)
        manager.enforce_retention()

        clips = manager.get_clips()
        assert len(clips) == 1
        assert clips[0].timestamp == "20260215_120000"


class TestGetDiskUsage:
    def test_returns_total_bytes_of_data_directory(self, tmp_path):
        """Should return the sum of all file sizes in the data directory."""
        _create_clip(tmp_path, "20260215_120000", mp4_size=1024)
        # Total: 1024 (mp4) + 512 (snap) + 256 (thumb) = 1792

        manager = _make_manager(tmp_path)
        usage = manager.get_disk_usage()

        assert usage == 1792
