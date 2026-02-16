from __future__ import annotations

import logging
import signal
import time
from datetime import datetime

from motion_cam.camera import CameraService
from motion_cam.config import load_config
from motion_cam.detector import MotionDetector
from motion_cam.recorder import Recorder

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

    shutdown = False

    def handle_signal(signum: int, frame: object) -> None:
        nonlocal shutdown
        logger.info("Received signal %s, shutting down...", signum)
        shutdown = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    camera.start()
    logger.info("Motion detector started")

    last_motion_time = 0.0

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
