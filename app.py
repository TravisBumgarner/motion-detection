# install with: pip install flask picamera2
from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import numpy as np

app = Flask(__name__)
camera = Picamera2()
camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))
camera.start()


def gen():
    detected_motion = False
    last_mean = 0
    while True:
        ret, frame = camera.read()
        cv2.imshow("frame", frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        result = np.abs(np.mean(gray) - last_mean)
        print(result)
        last_mean = np.mean(gray)
        print(result)
        if result > 0.3:
            print("Motion detected!")
            print("Started recording.")
            detected_motion = True
        if detected_motion:
            out.write(frame)
            frame_rec_count = frame_rec_count + 1
    if (cv2.waitKey(1) & 0xFF == ord("q")) or frame_rec_count == 240:
        break


@app.route("/video_feed")
def video_feed():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
