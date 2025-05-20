# install with: pip install flask picamera2
from flask import Flask, Response, jsonify
from motion import gen

app = Flask(__name__)

motion_status = {"detected": False, "timestamp_last_detected": None}


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
