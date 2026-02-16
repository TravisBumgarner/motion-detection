# motion-cam

A motion-activated camera system for Raspberry Pi Zero 2 W. Detects motion using OpenCV background subtraction, records MP4 video clips with snapshots, and serves a web portal for browsing captured media.

Built for detecting cockroaches in low-light conditions using IR-compatible cameras.

## Hardware

- **Raspberry Pi Zero 2 W**
- **Camera**: Pi Camera Module 3 NoIR (no IR filter) or Arducam IMX462 (ultra low-light, 0.01 lux)
- **IR illumination**: IR LED board/ring (invisible to insects)
- **Storage**: 32GB+ microSD card

## Raspberry Pi Setup

### 1. Flash Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Flash **Raspberry Pi OS Lite (64-bit)** to your microSD card
3. In the imager settings (gear icon), configure:
   - Hostname (e.g. `motioncam`)
   - Enable SSH
   - Set username/password
   - Configure WiFi
4. Insert the card and boot the Pi

### 2. Enable the Camera

SSH into the Pi and enable the camera interface:

```bash
sudo raspi-config
```

Navigate to **Interface Options > Camera** and enable it. Reboot when prompted.

Verify the camera is detected:

```bash
libcamera-hello --list-cameras
```

### 3. Install motion-cam

```bash
git clone https://github.com/TravisBumgarner/motion-detection.git
cd motion-detection
sudo ./bootstrap.sh
```

The bootstrap script will:
- Install system dependencies (python3, ffmpeg, etc.)
- Create a Python virtual environment
- Prompt you for configuration (detection sensitivity, storage location, etc.)
- Install and enable the systemd service

### 4. Start the Service

```bash
sudo systemctl start motion-cam
```

View logs:

```bash
sudo journalctl -u motion-cam -f
```

The web portal is available at `http://<pi-hostname>:8080`.

### 5. Verify It Works

1. Open `http://<pi-hostname>:8080` in a browser
2. Wave your hand in front of the camera
3. After a few seconds, a clip should appear in the gallery

## How It Works

```
Camera (picamera2) --> Motion Detector (OpenCV MOG2) --> Recorder (H264 + ffmpeg)
       |                                                        |
  dual-stream:                                            saves to disk:
  - 320x240 for detection                                - {timestamp}.mp4
  - 1280x720 for recording                               - {timestamp}_snap.jpg
                                                          - {timestamp}_thumb.jpg
                                                                |
                                                          Web Portal (Flask :8080)
```

**Motion detection pipeline:**
1. Capture low-res grayscale frame
2. Gaussian blur to reduce noise
3. MOG2 background subtractor with shadow detection
4. Threshold to remove shadow pixels (keeps only real foreground)
5. Morphological cleanup (erode + dilate)
6. Find contours, filter by minimum area
7. If qualifying contours found, motion is detected

This approach handles shadows, gradual lighting changes, and camera noise without false triggers.

## Configuration

Config is stored at `/etc/motion-cam/.env`. Edit and restart to apply:

```bash
sudo nano /etc/motion-cam/.env
sudo systemctl restart motion-cam
```

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMERA_MAIN_RESOLUTION` | `1280x720` | Recording resolution |
| `CAMERA_LORES_RESOLUTION` | `320x240` | Detection stream resolution |
| `CAMERA_FRAMERATE` | `15` | Frames per second |
| `DETECTION_MIN_CONTOUR_AREA` | `500` | Min pixel area to count as motion (lower = more sensitive) |
| `DETECTION_BLUR_KERNEL_SIZE` | `21` | Gaussian blur kernel (must be odd) |
| `DETECTION_LEARNING_RATE` | `-1` | Background model adaptation rate (-1 = auto) |
| `DETECTION_COOLDOWN` | `5` | Seconds of no motion before stopping recording |
| `DETECTION_MAX_CLIP_DURATION` | `60` | Max clip length in seconds |
| `STORAGE_DATA_DIR` | `~/motion-cam-data` | Where clips are saved |
| `STORAGE_MAX_AGE_DAYS` | `7` | Delete clips older than this |
| `STORAGE_MAX_DISK_USAGE_MB` | `4096` | Max disk usage before oldest clips are deleted |
| `WEB_PORT` | `8080` | Web portal port |
| `WEB_HOST` | `0.0.0.0` | Web portal bind address |

## Web Portal

- **Gallery** (`/`) -- Thumbnail grid of captured clips, paginated, newest first
- **Clip detail** (`/clip/<timestamp>`) -- Video player with snapshot and metadata
- **Status** (`/status`) -- Disk usage and clip count

**API:**
- `GET /api/clips?page=1` -- JSON list of clips
- `DELETE /api/clips/<timestamp>` -- Delete a clip
- `GET /api/status` -- System status JSON

## Project Structure

```
motion-cam/
  bootstrap.sh              # one-command Pi setup
  requirements.txt           # Python dependencies
  config/
    .env.example             # config template
  systemd/
    motion-cam.service       # systemd unit template
  src/
    motion_cam/
      config.py              # env-var config loader
      camera.py              # picamera2 dual-stream wrapper
      detector.py            # MOG2 motion detection
      recorder.py            # H264 recording + ffmpeg conversion
      storage.py             # clip management + retention
      web.py                 # Flask web portal
      main.py                # main loop + signal handling
  tests/
    test_config.py
    test_camera.py
    test_detector.py
    test_recorder.py
    test_storage.py
    test_web.py
```

## Managing the Service

```bash
# Start/stop/restart
sudo systemctl start motion-cam
sudo systemctl stop motion-cam
sudo systemctl restart motion-cam

# Check status
sudo systemctl status motion-cam

# View logs (live)
sudo journalctl -u motion-cam -f

# Disable auto-start on boot
sudo systemctl disable motion-cam
```

## Development

Run locally (without a Pi camera -- detection and recording won't work, but the web portal will):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest

# Run tests
PYTHONPATH=src pytest tests/ -v
```

## Tuning for Cockroaches

- **Lower `DETECTION_MIN_CONTOUR_AREA`** (e.g. 200-300) since cockroaches are small
- **Increase `CAMERA_FRAMERATE`** to 20-25 if the Pi can handle it -- faster movement needs higher FPS
- **Use an IR camera + IR LEDs** so the camera can see in the dark without visible light disturbing the roaches
- **Position the camera** 30-60cm from the area of interest for best detection of small insects
