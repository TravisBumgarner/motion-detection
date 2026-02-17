from __future__ import annotations

import re
from dataclasses import asdict

import time

from flask import Flask, Response, abort, jsonify, render_template_string, request, send_from_directory

from motion_cam.config import WebConfig
from motion_cam.storage import StorageManager

CLIPS_PER_PAGE = 20

GALLERY_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Motion Cam</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; padding: 1rem; }
  h1 { margin-bottom: 1rem; }
  nav { margin-bottom: 1rem; }
  nav a { color: #6cf; margin-right: 1rem; text-decoration: none; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; }
  .card { background: #222; border-radius: 8px; overflow: hidden; }
  .card img { width: 100%; aspect-ratio: 16/9; object-fit: cover; }
  .card .info { padding: 0.5rem; font-size: 0.85rem; }
  .card a { color: inherit; text-decoration: none; }
  .pagination { margin-top: 1rem; text-align: center; }
  .pagination a { color: #6cf; margin: 0 0.5rem; }
</style>
</head>
<body>
<h1>Motion Cam</h1>
<nav>
  <a href="/">Gallery</a> <a href="/status">Status</a> <a href="/tuner">Tuner</a>
  <button onclick="deleteAll()" style="background:#c33;color:#fff;border:none;border-radius:4px;padding:0.3rem 0.8rem;cursor:pointer;font-size:0.85rem;">Delete All</button>
</nav>
<script>
function deleteAll() {
  if (!confirm('Delete ALL clips? This cannot be undone.')) return;
  fetch('/api/clips', {method: 'DELETE'}).then(function(r) { return r.json(); }).then(function() { location.reload(); });
}
</script>
<div class="grid">
{% for clip in clips %}
  <div class="card">
    <a href="/clip/{{ clip.timestamp }}">
      <img src="/media/{{ clip.thumbnail_path }}" alt="Clip {{ clip.timestamp }}">
      <div class="info">{{ clip.display_time }} &mdash; {{ clip.size_kb }} KB</div>
    </a>
  </div>
{% endfor %}
</div>
{% if total_pages > 1 %}
<div class="pagination">
  {% if page > 1 %}<a href="/?page={{ page - 1 }}">&laquo; Prev</a>{% endif %}
  Page {{ page }} / {{ total_pages }}
  {% if page < total_pages %}<a href="/?page={{ page + 1 }}">Next &raquo;</a>{% endif %}
</div>
{% endif %}
</body>
</html>
"""

DETAIL_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clip {{ clip.timestamp }}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; padding: 1rem; }
  h1 { margin-bottom: 1rem; font-size: 1.2rem; }
  nav { margin-bottom: 1rem; }
  nav a { color: #6cf; margin-right: 1rem; text-decoration: none; }
  video { width: 100%; max-width: 800px; border-radius: 8px; }
  .meta { margin-top: 1rem; }
  .meta dt { font-weight: bold; display: inline; }
  .meta dd { display: inline; margin-right: 1rem; }
  .snapshot { margin-top: 1rem; }
  .snapshot img { width: 100%; max-width: 800px; border-radius: 8px; }
</style>
</head>
<body>
<nav><a href="/">&laquo; Gallery</a> <a href="/status">Status</a> <a href="/tuner">Tuner</a></nav>
<h1>Clip {{ clip.display_time }}</h1>
<video controls autoplay>
  <source src="/media/{{ clip.video_path }}" type="video/mp4">
</video>
<dl class="meta">
  <dt>Timestamp:</dt><dd>{{ clip.timestamp }}</dd>
  <dt>Size:</dt><dd>{{ clip.size_kb }} KB</dd>
</dl>
<div class="snapshot">
  <h2>Snapshot</h2>
  <img src="/media/{{ clip.snapshot_path }}" alt="Snapshot">
</div>
</body>
</html>
"""

STATUS_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Status - Motion Cam</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; padding: 1rem; }
  h1 { margin-bottom: 1rem; }
  nav { margin-bottom: 1rem; }
  nav a { color: #6cf; margin-right: 1rem; text-decoration: none; }
  dl dt { font-weight: bold; margin-top: 0.5rem; }
  dl dd { margin-left: 1rem; }
</style>
</head>
<body>
<nav><a href="/">&laquo; Gallery</a> <a href="/tuner">Tuner</a></nav>
<h1>System Status</h1>
<dl>
  <dt>Total Clips</dt><dd>{{ clip_count }}</dd>
  <dt>Disk Usage</dt><dd>{{ disk_usage_mb }} MB</dd>
</dl>
</body>
</html>
"""


TUNER_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Camera Tuner</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; }
  .container { display: flex; height: 100vh; }
  .feed { flex: 1; display: flex; align-items: center; justify-content: center; background: #000; }
  .feed img { max-width: 100%; max-height: 100%; }
  .controls { width: 320px; padding: 1rem; overflow-y: auto; background: #1a1a1a; border-left: 1px solid #333; }
  h1 { font-size: 1.2rem; margin-bottom: 1rem; }
  h2 { font-size: 0.95rem; margin: 1rem 0 0.5rem; color: #aaa; }
  nav { margin-bottom: 1rem; }
  nav a { color: #6cf; margin-right: 1rem; text-decoration: none; }
  .field { margin-bottom: 0.75rem; }
  .field label { display: block; font-size: 0.85rem; margin-bottom: 0.25rem; }
  .field .row { display: flex; align-items: center; gap: 0.5rem; }
  .field input[type=range] { flex: 1; }
  .field .val { font-size: 0.8rem; min-width: 50px; text-align: right; font-variant-numeric: tabular-nums; }
  select { background: #222; color: #eee; border: 1px solid #444; border-radius: 4px; padding: 0.3rem; width: 100%; }
  button { background: #2a6; color: #fff; border: none; border-radius: 4px; padding: 0.5rem 1rem; cursor: pointer; width: 100%; font-size: 0.9rem; margin-top: 0.5rem; }
  button:hover { background: #3b7; }
  button.af { background: #36c; }
  button.af:hover { background: #47d; }
  .status { font-size: 0.8rem; color: #888; margin-top: 0.5rem; }
  #manual_focus_group { display: none; }
  #manual_focus_group.show { display: block; }
</style>
</head>
<body>
<div class="container">
  <div class="feed">
    <img id="stream" src="/tuner/stream">
  </div>
  <div class="controls">
    <h1>Camera Tuner</h1>
    <nav><a href="/">Gallery</a> <a href="/status">Status</a></nav>

    <h2>Focus</h2>
    <div class="field">
      <label>AF Mode</label>
      <select id="af_mode" onchange="afModeChanged()">
        <option value="continuous">Continuous AF</option>
        <option value="manual">Manual Focus</option>
      </select>
    </div>
    <button class="af" onclick="triggerAf()">Trigger Autofocus</button>
    <div id="manual_focus_group">
      <div class="field" style="margin-top:0.5rem">
        <label>Lens Position (0=infinity, 10=close)</label>
        <div class="row">
          <input type="range" id="lens_position" min="0" max="10" step="0.1" value="0">
          <span class="val" id="lens_position_val">0.0</span>
        </div>
      </div>
    </div>

    <h2>Image Controls (live)</h2>
    <div class="field">
      <label>Brightness</label>
      <div class="row">
        <input type="range" id="brightness" min="-1" max="1" step="0.05" value="0">
        <span class="val" id="brightness_val">0.00</span>
      </div>
    </div>
    <div class="field">
      <label>Contrast</label>
      <div class="row">
        <input type="range" id="contrast" min="0" max="4" step="0.1" value="1">
        <span class="val" id="contrast_val">1.0</span>
      </div>
    </div>
    <div class="field">
      <label>Saturation</label>
      <div class="row">
        <input type="range" id="saturation" min="0" max="4" step="0.1" value="1">
        <span class="val" id="saturation_val">1.0</span>
      </div>
    </div>
    <div class="field">
      <label>Sharpness</label>
      <div class="row">
        <input type="range" id="sharpness" min="0" max="8" step="0.25" value="1">
        <span class="val" id="sharpness_val">1.0</span>
      </div>
    </div>
    <div class="field">
      <label>Exposure Value</label>
      <div class="row">
        <input type="range" id="exposure_value" min="-4" max="4" step="0.25" value="0">
        <span class="val" id="exposure_value_val">0.0</span>
      </div>
    </div>

    <div class="status" id="status">Ready</div>
  </div>
</div>
<script>
var liveControls = ['brightness', 'contrast', 'saturation', 'sharpness', 'exposure_value'];

liveControls.forEach(function(id) {
  var el = document.getElementById(id);
  var valEl = document.getElementById(id + '_val');
  el.addEventListener('input', function() {
    valEl.textContent = parseFloat(el.value).toFixed(el.step.indexOf('.') >= 0 ? 2 : 0);
    applyLive(id, parseFloat(el.value));
  });
});

var lensEl = document.getElementById('lens_position');
var lensVal = document.getElementById('lens_position_val');
lensEl.addEventListener('input', function() {
  lensVal.textContent = parseFloat(lensEl.value).toFixed(1);
  fetch('/api/tuner/control', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({lens_position: parseFloat(lensEl.value)})
  }).then(function(r) { return r.json(); }).then(function(d) {
    document.getElementById('status').textContent = 'Lens position = ' + lensEl.value;
  });
});

function afModeChanged() {
  var mode = document.getElementById('af_mode').value;
  document.getElementById('manual_focus_group').className = mode === 'manual' ? 'show' : '';
  fetch('/api/tuner/af_mode', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({af_mode: mode, lens_position: parseFloat(lensEl.value)})
  }).then(function(r) { return r.json(); }).then(function(d) {
    document.getElementById('status').textContent = 'AF mode: ' + mode;
  });
}

function triggerAf() {
  fetch('/api/tuner/trigger_af', {method: 'POST'}).then(function(r) { return r.json(); }).then(function(d) {
    document.getElementById('status').textContent = 'Autofocus triggered';
  });
}

function applyLive(key, value) {
  fetch('/api/tuner/control', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({[key]: value})
  }).then(function(r) { return r.json(); }).then(function(d) {
    document.getElementById('status').textContent = 'Applied ' + key + ' = ' + value;
  });
}
</script>
</body>
</html>
"""


def _format_timestamp(ts: str) -> str:
    """Format YYYYMMDD_HHMMSS into a readable string."""
    return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}:{ts[13:15]}"


def _relative_path(absolute_path: str, data_dir: str) -> str:
    """Convert an absolute path to a path relative to the data directory."""
    if absolute_path.startswith(data_dir):
        rel = absolute_path[len(data_dir):]
        return rel.lstrip("/")
    return absolute_path


_TIMESTAMP_RE = re.compile(r"^\d{8}_\d{6}$")


def _validate_timestamp(timestamp: str) -> None:
    """Abort 404 if timestamp doesn't match expected YYYYMMDD_HHMMSS format."""
    if not _TIMESTAMP_RE.match(timestamp):
        abort(404)


def create_app(
    storage_manager: StorageManager,
    web_config: WebConfig,
    data_dir: str,
    camera=None,
) -> Flask:
    app = Flask(__name__)
    app.config["DATA_DIR"] = data_dir

    @app.route("/")
    def gallery():
        page = request.args.get("page", 1, type=int)
        all_clips = storage_manager.get_clips()
        total_pages = max(1, -(-len(all_clips) // CLIPS_PER_PAGE))  # ceil division
        start = (page - 1) * CLIPS_PER_PAGE
        end = start + CLIPS_PER_PAGE
        clips = [
            {
                "timestamp": c.timestamp,
                "thumbnail_path": _relative_path(c.thumbnail_path, data_dir),
                "display_time": _format_timestamp(c.timestamp),
                "size_kb": c.file_size // 1024,
            }
            for c in all_clips[start:end]
        ]
        return render_template_string(
            GALLERY_TEMPLATE, clips=clips, page=page, total_pages=total_pages
        )

    @app.route("/clip/<timestamp>")
    def clip_detail(timestamp: str):
        _validate_timestamp(timestamp)
        clip = storage_manager.get_clip(timestamp)
        if clip is None:
            abort(404)
        clip_data = {
            "timestamp": clip.timestamp,
            "display_time": _format_timestamp(clip.timestamp),
            "video_path": _relative_path(clip.path, data_dir),
            "snapshot_path": _relative_path(clip.snapshot_path, data_dir),
            "size_kb": clip.file_size // 1024,
        }
        return render_template_string(DETAIL_TEMPLATE, clip=clip_data)

    @app.route("/status")
    def status_page():
        clips = storage_manager.get_clips()
        disk_usage = storage_manager.get_disk_usage()
        return render_template_string(
            STATUS_TEMPLATE,
            clip_count=len(clips),
            disk_usage_mb=round(disk_usage / (1024 * 1024), 1),
        )

    @app.route("/api/clips")
    def api_clips():
        page = request.args.get("page", 1, type=int)
        all_clips = storage_manager.get_clips()
        start = (page - 1) * CLIPS_PER_PAGE
        end = start + CLIPS_PER_PAGE
        return jsonify([asdict(c) for c in all_clips[start:end]])

    @app.route("/api/clips", methods=["DELETE"])
    def api_delete_all_clips():
        count = storage_manager.delete_all_clips()
        return jsonify({"status": "deleted", "count": count})

    @app.route("/api/clips/<timestamp>", methods=["DELETE"])
    def api_delete_clip(timestamp: str):
        _validate_timestamp(timestamp)
        deleted = storage_manager.delete_clip(timestamp)
        if not deleted:
            abort(404)
        return jsonify({"status": "deleted", "timestamp": timestamp})

    @app.route("/api/status")
    def api_status():
        clips = storage_manager.get_clips()
        disk_usage = storage_manager.get_disk_usage()
        return jsonify({
            "clip_count": len(clips),
            "disk_usage": disk_usage,
        })

    @app.route("/media/<path:filename>")
    def serve_media(filename: str):
        return send_from_directory(data_dir, filename)

    @app.route("/tuner")
    def tuner_page():
        return render_template_string(TUNER_TEMPLATE)

    @app.route("/tuner/stream")
    def tuner_stream():
        if camera is None:
            abort(503)

        def generate():
            while True:
                frame = camera.capture_jpeg_frame()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
                time.sleep(0.05)

        return Response(
            generate(), mimetype="multipart/x-mixed-replace; boundary=frame"
        )

    @app.route("/api/tuner/control", methods=["POST"])
    def api_tuner_control():
        if camera is None:
            abort(503)
        data = request.get_json()
        ctrl_map = {
            "brightness": "Brightness",
            "contrast": "Contrast",
            "saturation": "Saturation",
            "sharpness": "Sharpness",
            "exposure_value": "ExposureValue",
            "lens_position": "LensPosition",
        }
        controls = {}
        for key, val in data.items():
            if key in ctrl_map:
                controls[ctrl_map[key]] = val
        if controls:
            camera.set_controls(controls)
        return jsonify({"status": "ok", "applied": list(data.keys())})

    @app.route("/api/tuner/af_mode", methods=["POST"])
    def api_tuner_af_mode():
        if camera is None:
            abort(503)
        data = request.get_json()
        mode = data.get("af_mode", "continuous")
        try:
            from libcamera import controls as lc

            if mode == "continuous":
                camera.set_controls({"AfMode": lc.AfModeEnum.Continuous})
            elif mode == "manual":
                lp = data.get("lens_position", 0.0)
                camera.set_controls(
                    {"AfMode": lc.AfModeEnum.Manual, "LensPosition": lp}
                )
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)})
        return jsonify({"status": "ok", "af_mode": mode})

    @app.route("/api/tuner/trigger_af", methods=["POST"])
    def api_tuner_trigger_af():
        if camera is None:
            abort(503)
        try:
            from libcamera import controls as lc

            camera.set_controls(
                {"AfMode": lc.AfModeEnum.Auto, "AfTrigger": lc.AfTriggerEnum.Start}
            )
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)})
        return jsonify({"status": "ok"})

    return app
