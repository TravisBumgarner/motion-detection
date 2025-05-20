from picamera2 import Picamera2
import cv2
import numpy as np
import time

camera = Picamera2()
camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))
camera.start()


def gen():
    global motion_status
    detected_motion = False
    last_mean = 0
    while True:
        frame = camera.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        result = np.abs(np.mean(gray) - last_mean)
        last_mean = np.mean(gray)
        if result > 0.3:
            detected_motion = True
            motion_status["detected"] = True
            motion_status["timestamp_last_detected"] = time.time()
        else:
            detected_motion = False
            motion_status["detected"] = False
        if detected_motion:
            ret, jpeg = cv2.imencode(".jpg", frame)
            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                + jpeg.tobytes()
                + b"\r\n"
            )

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
