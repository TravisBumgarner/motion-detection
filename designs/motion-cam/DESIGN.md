# Motion-Activated Camera for Cockroach Detection

## Overview

A motion-activated camera system designed to run on a Raspberry Pi Zero 2 W, optimized for detecting cockroaches in low-light conditions. The system captures video clips and photo snapshots when motion is detected, stores them locally, and serves a web portal for reviewing captured media.

## Hardware Requirements

- **Raspberry Pi Zero 2 W** (quad-core ARM Cortex-A53, 512MB RAM)
- **Camera**: Raspberry Pi Camera Module 3 NoIR (no IR filter) or Arducam IMX462 (ultra low-light, 0.01 lux minimum illumination)
- **IR illumination**: IR LED board or ring for invisible-to-insects illumination
- **Storage**: microSD card (32GB+) or USB storage

## Architecture

```
┌─────────────────────────────────────────────┐
│              Main Application               │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │ Camera   │→ │ Motion   │→ │ Recording │ │
│  │ Service  │  │ Detector │  │ Pipeline  │ │
│  └──────────┘  └──────────┘  └───────────┘ │
│                                     │       │
│  ┌──────────┐  ┌──────────────────┐ │       │
│  │ Storage  │← │                  │←┘       │
│  │ Manager  │  │                  │         │
│  └────┬─────┘  └──────────────────┘         │
│       │                                     │
│  ┌────▼─────┐                               │
│  │   Web    │  (Flask, port 8080)            │
│  │  Portal  │                               │
│  └──────────┘                               │
└─────────────────────────────────────────────┘
```

## Technical Approach

### Camera (picamera2)

Use picamera2's dual-stream configuration:
- **Low-resolution stream** (320x240, YUV420): Used for motion detection processing. Minimal CPU cost.
- **Main stream** (1280x720, H264): Used for recording video clips when motion is detected.

Frame rate set to 15 FPS to reduce CPU load on the Pi Zero 2 W. Camera runs headless (no preview window).

Reference: [picamera2 official motion detection example](https://github.com/raspberrypi/picamera2/blob/main/examples/capture_motion.py)

### Motion Detection

Uses OpenCV's MOG2 background subtractor with shadow filtering and contour
analysis. This approach learns the background over time, so gradual lighting
changes (clouds, sunrise/sunset) don't cause false triggers. It also has
built-in shadow detection that marks shadow pixels separately from actual
foreground objects.

**Pipeline:**
1. Capture low-res frame via `capture_array("lores")`
2. Extract Y channel (grayscale) from YUV420 data
3. Apply Gaussian blur to reduce noise (important in low-light/IR conditions)
4. Feed frame into MOG2 background subtractor with `detectShadows=True`
5. Threshold the foreground mask to remove shadow pixels (MOG2 marks shadows
   as gray (127) and foreground as white (255) — only keep white)
6. Apply morphological operations (erode + dilate) to clean up noise
7. Find contours in the cleaned mask
8. Filter contours by minimum area (`min_contour_area`, default 500 pixels)
9. If any contours exceed the minimum area, motion is detected

This approach reliably distinguishes real moving objects (cockroaches) from:
- **Shadows**: filtered by MOG2's shadow detection
- **Lighting changes**: handled by the adaptive background model
- **Camera noise**: filtered by blur + morphological operations
- **Tiny specks/dust**: filtered by minimum contour area

**Tunable parameters:**
- `learning_rate`: how fast the background model adapts (default -1, auto)
- `min_contour_area`: minimum pixel area to count as motion (default 500)
- `shadow_threshold`: MOG2 shadow detection threshold
- `blur_kernel_size`: Gaussian blur kernel size (default 21)
- `cooldown`: seconds after last motion before stopping recording (default 5)

CPU usage is slightly higher than raw MSE (~10-15% on Pi Zero 2 W) but still
well within budget. The headless `opencv-python-headless` package avoids
pulling in GUI dependencies.

### Recording Pipeline

When motion is detected:
1. Start H264 encoder on the main stream
2. Capture a JPEG snapshot at the moment of detection
3. Continue recording until no motion detected for a configurable cooldown period (default: 5 seconds)
4. Stop encoder, convert H264 to MP4 using ffmpeg (`ffmpeg -i input.h264 -c copy output.mp4`)
5. Generate a thumbnail from the video for the web gallery

Maximum clip duration capped at a configurable limit (default: 60 seconds) to prevent runaway recordings.

### Storage Management

- **Directory structure**: `~/motion-cam-data/YYYY-MM-DD/` organized by date
- **Files per event**: `{timestamp}.mp4`, `{timestamp}_snap.jpg`, `{timestamp}_thumb.jpg`
- **Retention policy**: Configurable max age (default: 7 days) and max disk usage (default: 4GB)
- **Cleanup**: Periodic check deletes oldest recordings when limits are exceeded

### Web Portal (Flask)

Lightweight Flask application serving on port 8080:
- **Gallery page**: Grid of thumbnails with timestamps, sorted newest-first, paginated
- **Detail view**: Video player for a clip, snapshot image, metadata (duration, timestamp, file size)
- **Live status**: Current detector state (watching/recording), disk usage, uptime
- **Settings page**: View/modify detection sensitivity, cooldown, retention settings
- **API endpoints**: JSON API for clip listing, deletion, and configuration

No authentication required (local network only). Static assets kept minimal for Pi Zero 2 W performance.

### Configuration

Environment-based configuration using `.env` file, following the same pattern
as `rasppi-utils`. Config stored at `/etc/motion-cam/.env` with chmod 600.

```env
# Camera
CAMERA_MAIN_RESOLUTION=1280x720
CAMERA_LORES_RESOLUTION=320x240
CAMERA_FRAMERATE=15

# Detection
DETECTION_MIN_CONTOUR_AREA=500
DETECTION_BLUR_KERNEL_SIZE=21
DETECTION_LEARNING_RATE=-1
DETECTION_COOLDOWN=5
DETECTION_MAX_CLIP_DURATION=60

# Storage
STORAGE_DATA_DIR=/home/pi/motion-cam-data
STORAGE_MAX_AGE_DAYS=7
STORAGE_MAX_DISK_USAGE_MB=4096

# Web
WEB_PORT=8080
WEB_HOST=0.0.0.0
```

A `.env.example` file is included in `config/` as a template.

### Deployment (rasppi-utils-style bootstrapping)

Follows the same idempotent bootstrap/sync pattern as `rasppi-utils`:

**bootstrap.sh** (run once with `sudo`):
1. Check root privileges
2. Install system dependencies: `python3`, `python3-pip`, `python3-venv`, `ffmpeg`
3. Create Python venv at `./.venv`
4. Install Python dependencies from `requirements.txt`
5. Create config directory at `/etc/motion-cam/` (chmod 755)
6. Prompt user for config values interactively (or copy `.env.example` if non-interactive)
7. Ensure user is in the `video` group for camera access
8. Create data directory
9. Install systemd service unit (with `{{INSTALL_DIR}}` placeholder replacement)
10. Enable and start the service

**systemd/motion-cam.service** (template):
```ini
[Unit]
Description=Motion-Activated Camera for Cockroach Detection
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={{INSTALL_DIR}}
ExecStart={{INSTALL_DIR}}/.venv/bin/python -m motion_cam.main
EnvironmentFile=/etc/motion-cam/.env
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Project layout** (updated):
```
motion-cam/
  bootstrap.sh            # one-time setup
  requirements.txt        # Python deps
  config/
    .env.example           # config template
  systemd/
    motion-cam.service     # systemd unit template
  src/
    motion_cam/
      __init__.py
      config.py            # loads env vars with defaults
      camera.py
      detector.py
      recorder.py
      storage.py
      web.py
      main.py
  tests/
    ...
```

## Dependencies

- Python 3.11+
- picamera2 (pre-installed on Raspberry Pi OS)
- numpy
- opencv-python-headless (MOG2 background subtraction, contour detection)
- Flask
- ffmpeg (system package)
- PyYAML

## References

- [picamera2 motion detection example](https://github.com/raspberrypi/picamera2/blob/main/examples/capture_motion.py)
- [picamera2 manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- [Arducam IMX462 ultra low-light camera](https://docs.arducam.com/Raspberry-Pi-Camera/Pivariety-Camera/IMX462/)
- [PICT insect camera trap system](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.13618)
- [picamera2-webstream Flask example](https://github.com/GlassOnTin/picamera2-webstream)
