# install with: pip install flask picamera2
from flask import Flask, Response, jsonify
from picamera2 import Picamera2
import cv2
import numpy as np
import time

app = Flask(__name__)
camera = Picamera2()
camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))
camera.start()

motion_status = {"detected": False, "timestamp_last_detected": None}


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


@app.route("/video_feed")
def video_feed():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/")
def index():
    return """
    <html>
      <body>
        <h1>Live Video Feed</h1>
        <img src="/video_feed" width="640" height="480" />
        <div id="motion-status" style="margin-top:20px;font-size:1.2em;">Motion status: Unknown</div>
        <script>
          function pollStatus() {
            fetch('/status')
              .then(response => response.json())
              .then(data => {
                const statusDiv = document.getElementById('motion-status');
                let textContent = 'Motion status: ' + (data.detected ? 'Detected' : 'Not detected');
                if (data.timestamp_last_detected){
                  const date = new Date(data.timestamp_last_detected * 1000);
                  textContent += ' at ' + date.toLocaleTimeString();
                }
                statusDiv.textContent = textContent;
                statusDiv.style.color = data.detected ? 'red' : 'green';
              })
              .catch(() => {
                document.getElementById('motion-status').textContent = 'Motion status: Error';
              });
          }
          setInterval(pollStatus, 1000);
          pollStatus();
        </script>
      </body>
    </html>
    """


@app.route("/status")
def status():
    return jsonify(motion_status)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
