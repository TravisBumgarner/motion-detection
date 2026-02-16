from __future__ import annotations

import logging
import signal
import threading
import time
from datetime import datetime

from motion_cam.camera import CameraService
from motion_cam.config import load_config
from motion_cam.detector import MotionDetector
from motion_cam.recorder import Recorder
from motion_cam.storage import StorageManager
from motion_cam.web import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    camera = CameraService(config.camera)
    detector = MotionDetector(config.detection)
    recorder = Recorder(camera, config.storage, config.detection)
    storage = StorageManager(config.storage)

    # Start Flask web server in a background thread
    app = create_app(storage, config.web, data_dir=config.storage.data_dir)
    web_thread = threading.Thread(
        target=app.run,
        kwargs={"host": config.web.host, "port": config.web.port},
        daemon=True,
    )
    web_thread.start()
    logger.info("Web portal started on %s:%d", config.web.host, config.web.port)

    shutdown = False

    def handle_signal(signum: int, frame: object) -> None:
        nonlocal shutdown
        logger.info("Received signal %s, shutting down...", signum)
        shutdown = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    camera.start()
    logger.info("Motion detector started")

    storage.enforce_retention()

    last_motion_time = 0.0
    last_retention_check = time.time()

    try:
        while not shutdown:
            frame = camera.capture_lores_frame()
            event = detector.process_frame(frame)

            if event.detected:
                last_motion_time = time.time()
                if not recorder.is_recording:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    logger.info(
                        "Motion detected (contours=%d, area=%d), recording...",
                        event.contour_count,
                        event.largest_area,
                    )
                    recorder.start_recording(timestamp)
            elif recorder.is_recording:
                elapsed_since_motion = time.time() - last_motion_time
                if elapsed_since_motion >= config.detection.cooldown:
                    logger.info("Motion stopped, finalizing clip...")
                    recorder.stop_recording()

            recorder.check_max_duration()

            # Periodic retention check (every 10 minutes)
            if time.time() - last_retention_check >= 600:
                storage.enforce_retention()
                last_retention_check = time.time()

            # Sleep to maintain approximate frame rate
            time.sleep(1.0 / config.camera.framerate)
    finally:
        if recorder.is_recording:
            logger.info("Stopping active recording...")
            recorder.stop_recording()
        camera.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
