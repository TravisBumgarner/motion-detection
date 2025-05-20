# install with: pip install flask picamera2
from flask import Flask, Response, jsonify, send_from_directory, request
from picamera2 import Picamera2
import cv2
import numpy as np
import time
import os

app = Flask(__name__)
camera = Picamera2()
camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))
camera.start()

motion_status = {"detected": False, "timestamp_last_detected": None}

IMAGE_DIR = "motion_images"
os.makedirs(IMAGE_DIR, exist_ok=True)


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
            # Save image with timestamp
            filename = f"motion_{int(time.time())}.jpg"
            filepath = os.path.join(IMAGE_DIR, filename)
            cv2.imwrite(filepath, frame)
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


@app.route("/images")
def images():
    if request.args.get("delete") == "yes":
        for f in os.listdir(IMAGE_DIR):
            os.remove(os.path.join(IMAGE_DIR, f))
        return "<html><body><h2>All images deleted.</h2><a href='/images'>Back</a></body></html>"
    files = sorted(os.listdir(IMAGE_DIR))
    if not files:
        return "<html><body><h2>No images found.</h2></body></html>"
    idx = int(request.args.get("idx", 0))
    idx = max(0, min(idx, len(files) - 1))
    img_file = files[idx]
    html = f"""
    <html><body>
    <h2>Motion Images ({idx + 1} of {len(files)})</h2>
    <img src='/images/file/{img_file}' width='640' /><br/>
    <a href='/images?idx={max(idx - 1, 0)}'>&larr; Prev</a>
    <a href='/images?idx={min(idx + 1, len(files) - 1)}'>Next &rarr;</a><br/>
    <a href='/images?delete=yes' style='color:red;'>Delete All Images</a>
    </body></html>
    """
    return html


@app.route("/images/file/<filename>")
def image_file(filename):
    return send_from_directory(IMAGE_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
