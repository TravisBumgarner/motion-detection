from dataclasses import dataclass


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
    camera: CameraConfig = None
    detection: DetectionConfig = None
    storage: StorageConfig = None
    web: WebConfig = None


def load_config() -> Config:
    """Load configuration from environment variables with sensible defaults."""
    return Config()
