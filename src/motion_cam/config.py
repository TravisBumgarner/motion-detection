import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_data_dir() -> str:
    home = Path.home()
    return str(home / "motion-cam-data")


def _parse_resolution(value: str) -> tuple[int, int]:
    w, h = value.split("x")
    return (int(w), int(h))


@dataclass(frozen=True)
class CameraConfig:
    main_resolution: tuple[int, int] = (1280, 720)
    lores_resolution: tuple[int, int] = (320, 240)
    framerate: int = 15


@dataclass(frozen=True)
class DetectionConfig:
    min_contour_area: int = 500
    blur_kernel_size: int = 21
    learning_rate: float = -1.0
    cooldown: int = 5
    max_clip_duration: int = 60


@dataclass(frozen=True)
class StorageConfig:
    data_dir: str = ""
    max_age_days: int = 7
    max_disk_usage_mb: int = 4096


@dataclass(frozen=True)
class WebConfig:
    port: int = 8080
    host: str = "0.0.0.0"


@dataclass(frozen=True)
class Config:
    camera: CameraConfig = field(default_factory=CameraConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    web: WebConfig = field(default_factory=WebConfig)


def load_config() -> Config:
    """Load configuration from environment variables with sensible defaults."""
    env = os.environ

    camera = CameraConfig(
        main_resolution=_parse_resolution(env.get("CAMERA_MAIN_RESOLUTION", "1280x720")),
        lores_resolution=_parse_resolution(env.get("CAMERA_LORES_RESOLUTION", "320x240")),
        framerate=int(env.get("CAMERA_FRAMERATE", "15")),
    )

    detection = DetectionConfig(
        min_contour_area=int(env.get("DETECTION_MIN_CONTOUR_AREA", "500")),
        blur_kernel_size=int(env.get("DETECTION_BLUR_KERNEL_SIZE", "21")),
        learning_rate=float(env.get("DETECTION_LEARNING_RATE", "-1")),
        cooldown=int(env.get("DETECTION_COOLDOWN", "5")),
        max_clip_duration=int(env.get("DETECTION_MAX_CLIP_DURATION", "60")),
    )

    storage = StorageConfig(
        data_dir=env.get("STORAGE_DATA_DIR", _default_data_dir()),
        max_age_days=int(env.get("STORAGE_MAX_AGE_DAYS", "7")),
        max_disk_usage_mb=int(env.get("STORAGE_MAX_DISK_USAGE_MB", "4096")),
    )

    web = WebConfig(
        port=int(env.get("WEB_PORT", "8080")),
        host=env.get("WEB_HOST", "0.0.0.0"),
    )

    return Config(camera=camera, detection=detection, storage=storage, web=web)
